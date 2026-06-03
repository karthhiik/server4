"""
V4 Critic Engine — Skeleton-of-Thought Phase 3 (quality gate + targeted re-gen).

Per `slide-generation-architecture` skill:
  Critic produces a per-slide score with a weighted rubric.
  Slides scoring < threshold trigger targeted re-generation (NOT a full deck rewrite).
  Max 2 refinement cycles to bound latency.

Rubric (weights from skill):
  narrative_fit     25
  specificity       25  (real numbers, named entities, concrete claims)
  variety           20  (no two adjacent slides feel identical)
  density_compliance 15
  coherence         15

Model: phi-4-reasoning (TaskType.REFINEMENT) — strong reasoning at low cost
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

from app.services.llm.model_router import ModelRouter, TaskType
from app.services.v4.parallel_writer import GeneratedSlide, ParallelWriter
from app.services.v4.skeleton_planner import DeckSkeleton, SlideSkeleton
from app.services.v4.research_collector import ResearchPacket
from app.services.v4.json_repair import safe_json_loads, JSONRepairFailedError
from app.services.v4.llm_safe import safe_complete
from app.services.v4.numeric_grounder import audit_slide
from app.services.v4.loop_guard import detect_loops, LoopGuardReport
from app.services.v4 import content_rules
from app.services.v4.aesthetic_scorer import score_slide_aesthetic
from app.config import settings

logger = structlog.get_logger(__name__)

_PREMIUM_CRITIC_LLM_BUDGET_SECONDS = 18.0
_DEFAULT_CRITIC_LLM_BUDGET_SECONDS = 12.0

_AI_CONTEXT_RE = re.compile(
    r"\b(ai|artificial intelligence|machine learning|ml|llm|genai|generative ai|agentic|copilot)\b",
    re.IGNORECASE,
)
_PITCH_CONTEXT_RE = re.compile(
    r"\b(pitch|investor|vc|venture|seed|series\s+[abc]|fundraise|fundraising|capital|raise)\b",
    re.IGNORECASE,
)
_MODERN_INVESTOR_SIGNALS = (
    "proprietary data",
    "revenue momentum",
    "production deployment",
    "production deployments",
    "gross margin",
    "gross margin trajectory",
    "compounding loop",
    "compounding loops",
    "unit economics",
    "retention",
    "usage depth",
    "workflow data",
)
_OLD_AI_PITCH_SIGNALS = (
    "founder pedigree",
    "mvp demo",
    "pilot logos",
    "logo slide",
    "tam slide",
    '"we use ai"',
    "we use ai",
    "ai-powered only",
)


@dataclass
class SlideScore:
    index: int
    overall: float                          # 0..10
    narrative_fit: float = 0.0
    specificity: float = 0.0
    variety: float = 0.0
    density_compliance: float = 0.0
    coherence: float = 0.0
    visual_quality: float = 0.0              # v2: composition, typography, color
    issues: list[str] = field(default_factory=list)
    needs_rewrite: bool = False


@dataclass
class CriticReport:
    overall: float                          # 0..10 weighted average
    slide_scores: list[SlideScore]
    needs_rewrite_indices: list[int]
    loop_report: Optional[LoopGuardReport] = None   # v12.1 — deck-wide repetition scan


_CRITIC_SYSTEM = """You are the Critic. Score every slide 0-10 on six dimensions:
  narrative_fit (20%), specificity (20%), variety (15%), density_compliance (15%), coherence (15%), visual_quality (15%)
  visual_quality covers: layout composition, typography contrast, color harmony, whitespace usage.

═══════════════════════════════════════════════════════════════════════════
CRITICAL — HEADLINE QUALITY GATES (CEO MANDATED)
═══════════════════════════════════════════════════════════════════════════
A headline is INVALID and must score specificity ≤ 3 if it matches ANY of these:

1. TEMPLATE HEADLINES (immediate -5 specificity):
   - "Our Unique Value Proposition" — this is a PowerPoint placeholder, NOT a headline
   - "Our Distinctive Edge" — ChatGPT fluff from 2022
   - "How We Operate" — could describe a laundromat
   - "Empowering Resilience" — empty corporate-speak
   - "Market Opportunity" / "The Problem" / "Our Solution" — category labels, not thesis statements

2. GENERICITY TEST (immediate -3 specificity):
   - Could this headline belong to ANY startup? If YES, it's too generic.
   - Does it contain the company name OR industry-specific term? If NO, it's too generic.
   - Example BAD: "Real-Time Coverage Outshines Legacy Models" (uses insurance term 'coverage' in energy deck)
   - Example GOOD: "2 State-Level Pilots + 1 Patent Pending" (specific to THIS company)

3. USER INPUT USAGE TEST (immediate -4 specificity for traction/ask slides):
   - Traction slide MUST mention user's actual pilots, customers, or metrics
   - Ask slide MUST mention user's actual funding amount and use of funds
   - If user provided "2 Pilot Programs (State-level) + 1 Patent Pending" and the traction
     headline is "Our Unique Value Proposition" — this is a CRITICAL FAILURE.

4. CROSS-INDUSTRY CONTAMINATION (immediate -5 specificity):
   - Insurance terminology (coverage, premium, underwriting, policy) in non-insurance decks
   - Fintech terminology in non-fintech decks
   - This indicates the AI didn't reset between sessions.

═══════════════════════════════════════════════════════════════════════════

Hard rules to penalize:
- Headline > 8 words OR < 3 words: density_compliance -3
- Bullet > 10 words: density_compliance -2 each
- More than 4 bullets: density_compliance -3
- Generic vague claims with no numbers/entities: specificity -4
- Two adjacent slides with same layout AND same intent: variety -3
- Slide adds nothing new (repeats prior slide): narrative_fit -4
- Market / traction / financial slides without a grounded numeric claim: specificity -3
- Market / traction / financial slides without a structured data block (stat/chart/table): coherence -2
- Ratan Tata's "Numbers Don't Lie": slides with numeric claims lacking evidence_refs: specificity -4
- AI startup investor decks must optimize for the current proof bar: proprietary data,
  revenue momentum, production deployments, gross margin trajectory, and compounding loops.
  Penalize old signals alone: founder pedigree, MVP demo, pilot logos, TAM slide, or "we use AI".
  If proof is absent, reward honest validation framing and penalize invented certainty.

═══════════════════════════════════════════════════════════════════════════
ANTI-AI-SLOP BLACKLIST (Open Design discipline)
═══════════════════════════════════════════════════════════════════════════
Penalize -3 variety AND -2 coherence for ANY of these visual/content slop patterns:
- Aggressive purple gradients used as decorative noise
- Generic emoji icons as bullet decorators (except product-specific context)
- "Rounded card with left-border accent" layout repeated more than once
- Hand-drawn SVG illustration humans (corporate clip-art vibes)
- Invented statistics without source attribution ("10x faster", "500% growth" with no context)
- "Transforming industries" / "Revolutionizing" / "Disrupting" — empty superlatives
- More than 2 exclamation marks in an entire deck
- Inter as a DISPLAY face (it's a body font — use it at h2 or below, not display/h1 at 68pt+)
- Background images behind text without proper contrast overlay
- Slides that are 100% text with no visual hierarchy element (chart/stat/image/diagram)

Return ONLY JSON:
{
  "slides": [
    {"index": 0, "narrative_fit": 8.5, "specificity": 7.0, "variety": 9.0,
     "density_compliance": 9.5, "coherence": 8.0, "issues": ["..."]}
  ]
}
"""


class CriticEngine:
    # CRITICAL FIX: Raise quality thresholds for investor-grade pitch decks
    # Previous threshold of 7.0 was too lenient, allowing low-quality slides
    # through. Investor-grade decks require 8.0+ threshold.
    REWRITE_THRESHOLD = 8.0
    # Founder replan — premium requires a higher local-shortcut bar before we
    # skip the LLM critic. Standard keeps the legacy bar (8.5) for latency.
    # Thresholds now configurable via settings for company policy compliance
    MAX_REFINEMENT_CYCLES = 3  # Increased from 2 to allow more refinement iterations
    # Intent set that defines "critical slides" for the premium Kimi 2.6
    # targeted rewrite pass. These are the slides investors remember;
    # any below-target outcome here is worth burning Kimi 2.6 budget on.
    PREMIUM_CRITICAL_INTENTS = {"title", "market", "traction", "competition", "ask", "team", "financials"}

    def __init__(self) -> None:
        self.router = ModelRouter.get_instance()
        self.writer = ParallelWriter()

    async def evaluate_and_refine(
        self,
        slides: list[GeneratedSlide],
        skeleton: DeckSkeleton,
        research: ResearchPacket,
        mode: str = "standard",
    ) -> tuple[list[GeneratedSlide], CriticReport]:
        """Evaluate the deck. If any slide scores below threshold, regenerate it (up to 2 cycles).

        Founder replan: premium mode additionally runs a Kimi 2.6 targeted-rewrite
        pass on investor-critical slides (title/market/traction/competition/ask)
        whose score is below settings.PREMIUM_CRITICAL_RESCORE_TARGET after the normal
        refinement loop converges.
        """
        report = await self.evaluate(slides, skeleton, research=research, mode=mode)

        cycles = 0
        max_cycles = self.MAX_REFINEMENT_CYCLES if mode == "premium" else 1
        while report.needs_rewrite_indices and cycles < max_cycles:
            cycles += 1
            logger.info("v4_critic_refinement_cycle",
                cycle=cycles, n_to_rewrite=len(report.needs_rewrite_indices))

            # Targeted re-gen: only the slides that failed
            tasks = []
            failed_skeletons: list[SlideSkeleton] = []
            for idx in report.needs_rewrite_indices:
                skel = skeleton.slides[idx]
                # Inject critic feedback into the skeleton purpose
                issues = next((s.issues for s in report.slide_scores if s.index == idx), [])
                if issues:
                    skel = SlideSkeleton(
                        index=skel.index,
                        intent=skel.intent,
                        purpose=f"{skel.purpose}\n\nCritic feedback to address: {'; '.join(issues)}",
                        headline_target=skel.headline_target,
                        key_points=skel.key_points,
                        density_target=skel.density_target,
                        layout_hint=skel.layout_hint,
                        evidence_refs=skel.evidence_refs,
                        visual_cue=skel.visual_cue,
                        thesis_sentence=skel.thesis_sentence,
                        generic_risk=skel.generic_risk,
                        required_quant_signals=skel.required_quant_signals,
                        trace_inputs=skel.trace_inputs,
                    )
                failed_skeletons.append(skel)
                tasks.append(self.writer.write_one(skel, research, mode, skeleton.project_id))

            new_slides = await asyncio.gather(*tasks, return_exceptions=True)
            for skel, new in zip(failed_skeletons, new_slides):
                if isinstance(new, Exception):
                    continue
                slides[skel.index] = new

            report = await self.evaluate(slides, skeleton, research=research, mode=mode)

        # Founder replan — premium Kimi 2.6 targeted rewrite pass.
        # Runs exactly once (no cycles) on investor-critical slides that still
        # score below settings.PREMIUM_CRITICAL_RESCORE_TARGET. Budgeted at the router
        # layer: if KIMI26_PREMIUM_MAX_CALLS is exhausted the call falls through
        # the normal reasoning chain so the pass still helps.
        if mode == "premium" and settings.ENABLE_KIMI26:
            slides, report = await self._premium_targeted_rewrite_kimi26(
                slides=slides,
                skeleton=skeleton,
                research=research,
                report=report,
            )

        return slides, report

    async def evaluate(
        self,
        slides: list[GeneratedSlide],
        skeleton: DeckSkeleton,
        research: Optional[ResearchPacket] = None,
        mode: str = "standard",
    ) -> CriticReport:
        # Build evidence haystack for numeric grounding (if research available)
        evidence_text = ""
        if research is not None:
            parts = []
            if research.query:
                parts.append(research.query)
            if research.raw and isinstance(research.raw, dict):
                if research.raw.get("original_query"):
                    parts.append(str(research.raw.get("original_query") or ""))
                if research.raw.get("structured_context"):
                    parts.append(json.dumps(research.raw.get("structured_context"), default=str, ensure_ascii=False))
            parts.extend(f"{c.title} {c.snippet}" for c in (research.citations + research.news_citations))
            evidence_text = " ".join(parts)

        # v12.1 — deck-wide repetition scan (pure, sub-ms). Findings feed
        # into per-slide penalties and rewrite feedback so loops trigger
        # targeted regeneration the same way a quality miss does.
        loop_report = detect_loops(slides)
        investor_context = self._build_investor_context(slides, skeleton, research)

        # Local rules-based pre-pass (cheap, deterministic)
        rewrite_threshold = self.REWRITE_THRESHOLD if mode == "premium" else 6.5
        local_scores = [
            self._local_score(
                s,
                slides,
                evidence_text,
                rewrite_threshold=rewrite_threshold,
                loop_report=loop_report,
                investor_context=investor_context,
            )
            for s in slides
        ]

        # Optionally augment with LLM holistic critique (skip if all locally above threshold)
        local_overall = sum(s.overall for s in local_scores) / max(1, len(local_scores))
        if mode == "standard":
            logger.info(
                "v4_standard_critic_local_only",
                overall=round(local_overall, 3),
                n_rewrites=sum(1 for s in local_scores if s.needs_rewrite),
            )
            return CriticReport(
                overall=local_overall,
                slide_scores=local_scores,
                needs_rewrite_indices=[s.index for s in local_scores if s.needs_rewrite],
                loop_report=loop_report,
            )

        shortcut_threshold = (
            settings.PREMIUM_SHORTCUT_THRESHOLD if mode == "premium"
            else settings.STANDARD_SHORTCUT_THRESHOLD
        )
        if local_overall >= shortcut_threshold and not any(s.needs_rewrite for s in local_scores):
            return CriticReport(
                overall=local_overall,
                slide_scores=local_scores,
                needs_rewrite_indices=[s.index for s in local_scores if s.needs_rewrite],
                loop_report=loop_report,
            )

        try:
            llm_budget = (
                _PREMIUM_CRITIC_LLM_BUDGET_SECONDS
                if mode == "premium"
                else _DEFAULT_CRITIC_LLM_BUDGET_SECONDS
            )
            llm_scores = await asyncio.wait_for(
                self._llm_critique(slides, skeleton),
                timeout=llm_budget,
            )
            # Blend: 50% local, 50% LLM
            merged: list[SlideScore] = []
            for ls, ms in zip(local_scores, llm_scores):
                merged.append(SlideScore(
                    index=ls.index,
                    narrative_fit=(ls.narrative_fit + ms.narrative_fit) / 2,
                    specificity=(ls.specificity + ms.specificity) / 2,
                    variety=(ls.variety + ms.variety) / 2,
                    density_compliance=(ls.density_compliance + ms.density_compliance) / 2,
                    coherence=(ls.coherence + ms.coherence) / 2,
                    visual_quality=(ls.visual_quality + ms.visual_quality) / 2,
                    issues=list(set(ls.issues + ms.issues))[:5],
                    overall=0,
                    needs_rewrite=False,
                ))
                merged[-1].overall = self._weighted(merged[-1])
                # Apply loop-guard penalty post-blend so a loop detected
                # at deck level can still tip an otherwise-average slide
                # into the rewrite bucket.
                loop_penalty = loop_report.per_slide_penalty.get(ls.index, 0.0)
                if loop_penalty > 0:
                    merged[-1].overall = max(0.0, merged[-1].overall - loop_penalty)
                    merged[-1].issues = list(dict.fromkeys(
                        merged[-1].issues + loop_report.per_slide_issues.get(ls.index, [])
                    ))[:6]
                merged[-1].needs_rewrite = merged[-1].overall < rewrite_threshold
            scores = merged
        except asyncio.TimeoutError:
            logger.warning(
                "v4_llm_critic_budget_exceeded_using_local",
                mode=mode,
                timeout_s=llm_budget,
                local_overall=round(local_overall, 3),
            )
            scores = local_scores
        except Exception as e:
            logger.warning("v4_llm_critic_failed_using_local", error=str(e))
            scores = local_scores

        overall = sum(s.overall for s in scores) / max(1, len(scores))
        return CriticReport(
            overall=overall,
            slide_scores=scores,
            needs_rewrite_indices=[s.index for s in scores if s.needs_rewrite],
            loop_report=loop_report,
        )

    # ── Scoring ────────────────────────────────────────────────────

    @staticmethod
    def _build_investor_context(
        slides: list[GeneratedSlide],
        skeleton: DeckSkeleton,
        research: Optional[ResearchPacket],
    ) -> dict[str, Any]:
        """Detect when the modern AI-startup investor proof gate applies."""
        skeleton_blob = " ".join(
            [
                skeleton.title or "",
                skeleton.narrative_arc or "",
                " ".join(
                    " ".join(
                        [
                            s.intent or "",
                            s.purpose or "",
                            s.headline_target or "",
                            " ".join(str(point or "") for point in (s.key_points or [])),
                        ]
                    )
                    for s in skeleton.slides
                ),
            ]
        )
        slide_blob = " ".join(
            " ".join(
                [
                    s.headline or "",
                    s.subheadline or "",
                    s.body or "",
                    " ".join(str(bullet or "") for bullet in (s.bullets or [])),
                ]
            )
            for s in slides
        )
        research_blob = ""
        if research is not None:
            research_blob = " ".join(
                [
                    research.query or "",
                    research.industry or "",
                    research.company_name or "",
                    " ".join(f"{c.title} {c.snippet}" for c in (research.citations + research.news_citations)),
                ]
            )
        blob = f"{skeleton_blob} {slide_blob} {research_blob}".lower()
        is_pitch = (
            "investor_pitch" in (skeleton.narrative_arc or "").lower()
            or bool(_PITCH_CONTEXT_RE.search(blob))
        )
        is_ai = bool(_AI_CONTEXT_RE.search(blob))
        return {
            "applies": is_pitch and is_ai,
            "is_pitch": is_pitch,
            "is_ai": is_ai,
        }

    @staticmethod
    def _apply_modern_investor_rules(
        score: SlideScore,
        issues: list[str],
        slide: GeneratedSlide,
        investor_context: Optional[dict[str, Any]],
    ) -> None:
        """Score AI pitch slides against current VC proof expectations."""
        if not investor_context or not investor_context.get("applies"):
            return

        text = " ".join(
            [
                slide.headline or "",
                slide.subheadline or "",
                slide.body or "",
                " ".join(str(bullet or "") for bullet in (slide.bullets or [])),
                " ".join(
                    f"{sb.get('value', '')} {sb.get('label', '')} {sb.get('caption', '')}"
                    for sb in (slide.stat_blocks or [])
                    if isinstance(sb, dict)
                ),
            ]
        ).lower()
        if not text.strip():
            return

        modern_hits = [signal for signal in _MODERN_INVESTOR_SIGNALS if signal in text]
        old_hits = [signal for signal in _OLD_AI_PITCH_SIGNALS if signal in text]
        honest_missing = any(
            phrase in text
            for phrase in (
                "data needed",
                "validation required",
                "validation pending",
                "benchmarks pending",
                "metrics pending",
                "input needed",
                "requires validation",
            )
        )
        intent = (slide.intent or "").lower()

        if old_hits and not modern_hits:
            score.specificity = max(0.0, score.specificity - 3.0)
            score.coherence = max(0.0, score.coherence - 3.0)
            score.narrative_fit = max(0.0, score.narrative_fit - 2.0)
            issues.append("modern_investor:old_signal_without_proof:" + old_hits[0])

        if intent in {"traction", "market", "business_model", "financials", "finances", "ask"}:
            if not modern_hits and not honest_missing:
                score.specificity = max(0.0, score.specificity - 2.0)
                score.narrative_fit = max(0.0, score.narrative_fit - 1.5)
                score.coherence = max(0.0, score.coherence - 1.5)
                issues.append("modern_investor:missing_proof_signal")

        if intent == "market" and "tam" in text and not any(
            term in text
            for term in (
                "sam",
                "som",
                "icp",
                "buyer",
                "budget",
                "source",
                "revenue",
                "deployment",
                "production",
                "proprietary data",
            )
        ):
            score.specificity = max(0.0, score.specificity - 2.0)
            issues.append("modern_investor:tam_without_buyer_or_proof")

        if intent in {"solution", "technology", "unique_advantage"} and "we use ai" in text and not modern_hits:
            score.specificity = max(0.0, score.specificity - 2.5)
            issues.append("modern_investor:ai_claim_without_data_moat")

    @staticmethod
    def _weighted(s: SlideScore) -> float:
        return (
            s.narrative_fit * 0.20
            + s.specificity * 0.20
            + s.variety * 0.15
            + s.density_compliance * 0.15
            + s.coherence * 0.15
            + s.visual_quality * 0.15
        )

    def _local_score(
        self,
        slide: GeneratedSlide,
        all_slides: list[GeneratedSlide],
        evidence_text: str = "",
        *,
        rewrite_threshold: float = 8.0,
        loop_report: Optional[LoopGuardReport] = None,
        investor_context: Optional[dict[str, Any]] = None,
    ) -> SlideScore:
        score = SlideScore(index=slide.index, overall=0)
        issues: list[str] = []
        generic_text = " ".join(
            [
                str(slide.headline or ""),
                str(slide.subheadline or ""),
                str(slide.body or ""),
                " ".join(str(bullet or "") for bullet in (slide.bullets or [])),
            ]
        ).lower()

        # Density compliance
        density = 10.0
        words = slide.headline.split()
        if not (3 <= len(words) <= 8):
            density -= 3
            issues.append(f"headline_word_count={len(words)} (need 3-8)")
        long_bullets = [b for b in slide.bullets if len(b.split()) > 10]
        if long_bullets:
            density -= 2 * len(long_bullets)
            issues.append(f"{len(long_bullets)}_long_bullets")
        if len(slide.bullets) > 4:
            density -= 3
            issues.append("too_many_bullets")
        score.density_compliance = max(0.0, min(10.0, density))

        # Specificity (look for digits, $, %, named entities markers)
        stat_text = " ".join(
            f"{sb.get('value', '')} {sb.get('label', '')} {sb.get('caption', '')}"
            for sb in (slide.stat_blocks or [])
            if isinstance(sb, dict)
        )
        body_text = " ".join([
            slide.headline,
            slide.subheadline or "",
            " ".join(str(bullet or "") for bullet in (slide.bullets or [])),
            slide.body or "",
            stat_text,
        ])
        has_numbers = any(ch.isdigit() for ch in body_text)
        has_money = "$" in body_text or "%" in body_text
        has_citations = bool(slide.citations)
        spec = 10.0

        # Numeric grounding penalty (anti-hallucination)
        # STANDARD-MODE RELAXATION: research APIs often fail on free tier,
        # so we penalize less harshly and skip numbers explicitly marked as estimates.
        if evidence_text and has_numbers:
            slide_dict = {
                "headline": slide.headline,
                "subheadline": slide.subheadline,
                "bullets": slide.bullets,
                "body": slide.body,
                "stat_blocks": slide.stat_blocks,
                "quote": slide.quote,
                "chart": slide.chart,
            }
            audit = audit_slide(slide_dict, evidence_text=evidence_text, slide_index=slide.index)
            if audit.total_tokens > 0 and audit.grounding_score < 1.0:
                # Skip stat_blocks whose labels explicitly say "projected" or "estimated"
                filtered_ungrounded = []
                for ut in audit.ungrounded:
                    skip = False
                    if ut.field.startswith("stat_blocks["):
                        idx_str = ut.field[len("stat_blocks["):].split("].")[0]
                        try:
                            sb_idx = int(idx_str)
                            sb = (slide.stat_blocks or [])[sb_idx]
                            lbl = str(sb.get("label", "")).lower()
                            if any(m in lbl for m in ["projected", "estimated", "(est.)", "(estimated)"]):
                                skip = True
                        except (ValueError, IndexError):
                            pass
                    if not skip:
                        filtered_ungrounded.append(ut)
                # Reduced penalty: 1.0 per token, max -3 (standard mode research is thin)
                penalty = min(3.0, 1.0 * len(filtered_ungrounded))
                spec -= penalty
                if filtered_ungrounded:
                    issues.append(
                        f"ungrounded_numbers={len(filtered_ungrounded)}:" +
                        ",".join(t.token for t in filtered_ungrounded[:3])
                    )
        score.specificity = max(0.0, min(10.0, spec))
        core_data_intents = {"market", "traction", "financials"}
        extended_data_intents = {"business_model", "ask"}
        if not has_numbers and slide.intent in core_data_intents:
            score.specificity = max(0.0, score.specificity - 3.0)
            issues.append("no_numbers_in_data_slide")
        if slide.intent in core_data_intents and not any([slide.stat_blocks, slide.chart, slide.table]):
            score.coherence = max(0.0, score.coherence - 2.0)
            issues.append("data_slide_missing_quant_block")
        if any(
            phrase in generic_text
            for phrase in (
                "our ai-powered solution",
                "growing demand for automation",
                "join us on this journey",
                "revolutionizing",
                "investment opportunity",
            )
        ):
            score.specificity = max(0.0, score.specificity - 2.0)
            issues.append("generic_claims")

        # Founder replan — template headline detector. Hard −5 specificity hit
        # when the slide headline matches any banned pattern, ensuring these
        # slides always fall below the rewrite threshold and get regenerated.
        # CEO-identified: "Our Unique Value Proposition" should score 0/10 specificity.
        if settings.ENABLE_TEMPLATE_DETECTOR:
            det = content_rules.detect_template_headline(slide.headline)
            if det.is_template:
                # INCREASED from -3 to -5 per CEO feedback
                score.specificity = max(0.0, score.specificity - 5.0)
                score.narrative_fit = max(0.0, score.narrative_fit - 3.0)
                issues.append(f"template_headline:{det.label}")
                # Add fix hint to issues for rewrite prompt
                if det.fix_hint:
                    issues.append(f"fix_hint:{det.fix_hint[:80]}")

        # Founder replan — broader generic-phrase detector powered by
        # content_rules. Catches variants the hard-coded list above misses.
        if settings.ENABLE_CONTENT_RULES_GATE:
            generic_hits = content_rules.detect_generic_phrases(
                slide.headline, slide.subheadline, slide.body, *slide.bullets,
            )
            if generic_hits:
                # INCREASED penalty from min(3.0, len(hits)) to min(5.0, len(hits) * 1.5)
                score.specificity = max(0.0, score.specificity - min(5.0, len(generic_hits) * 1.5))
                issues.append("generic_phrases:" + ",".join(generic_hits[:3]))

            # CEO-identified: Cross-industry contamination detection
            # Example: "coverage" (insurance) appearing in energy grid deck
            contamination = content_rules.detect_cross_industry_contamination(
                text=(
                    f"{slide.headline} {slide.subheadline or ''} {slide.body or ''} "
                    f"{' '.join(str(bullet or '') for bullet in (slide.bullets or []))}"
                ),
                current_industry=getattr(slide, 'industry', None),
            )
            if contamination:
                score.specificity = max(0.0, score.specificity - 5.0)
                issues.append(f"cross_industry_contamination:{','.join(contamination[:3])}")

            # CEO-identified: Headline quality validation
            # Headline must pass "could this only be about [company]?" test
            headline_quality = content_rules.validate_headline_quality(
                headline=slide.headline,
                company_name=getattr(slide, 'company_name', None),
                industry=getattr(slide, 'industry', None),
                user_input_keywords=getattr(slide, 'user_input_keywords', None),
            )
            if not headline_quality["is_valid"]:
                # Apply additional penalty based on quality score
                penalty = (5.0 - headline_quality["score"]) * 0.5
                score.specificity = max(0.0, score.specificity - penalty)
                issues.extend([f"headline_quality:{iss}" for iss in headline_quality["issues"][:3]])

            # Data-slide validator: marks insufficient quant or missing block.
            slide_dict = {
                "headline": slide.headline,
                "subheadline": slide.subheadline,
                "body": slide.body,
                "bullets": slide.bullets,
                "stat_blocks": slide.stat_blocks,
                "chart": slide.chart,
                "table": slide.table,
                "comparison": slide.comparison,
            }
            ds_issues = content_rules.validate_data_slide(
                intent=slide.intent, slide=slide_dict,
            )
            for ds in ds_issues:
                score.coherence = max(0.0, score.coherence - 1.5)
                score.specificity = max(0.0, score.specificity - 1.0)
                issues.append(f"data_slide:{ds.code}")

        # Variety vs neighbors
        variety = 10.0
        if slide.index > 0:
            prev = all_slides[slide.index - 1]
            if prev.layout == slide.layout and prev.intent == slide.intent:
                variety -= 4
                issues.append("identical_to_prev")
        score.variety = max(0.0, variety)

        # v10.2 — DSL block / layout_hint coherence:
        # if the layout demanded a structured block but the writer didn't emit one,
        # penalize density compliance (the slide is lying about its shape).
        layout = (slide.layout or "").lower()
        block_required = {
            "table": slide.table,
            "timeline": slide.timeline,
            "comparison": slide.comparison,
            "diagram": slide.diagram,
            "chart-focus": slide.chart,
            "quote": slide.quote,
            "stat-hero": slide.stat_blocks,
        }
        required = block_required.get(layout)
        if layout in block_required and not required:
            score.density_compliance = max(0.0, score.density_compliance - 3)
            issues.append(f"layout_{layout}_missing_block")
        # If the writer DID emit the block, check minimum richness.
        if slide.timeline and len(slide.timeline.get("events", [])) < 3:
            issues.append("timeline_too_few_events")
            score.density_compliance = max(0.0, score.density_compliance - 1.5)
        if slide.comparison and len(slide.comparison.get("columns", [])) < 2:
            issues.append("comparison_needs_2plus_columns")
            score.density_compliance = max(0.0, score.density_compliance - 1.5)
        if slide.table:
            rows = slide.table.get("rows", [])
            headers = slide.table.get("headers", [])
            if len(rows) < 2 or len(headers) < 2:
                issues.append("table_too_sparse")
                score.density_compliance = max(0.0, score.density_compliance - 1.5)
        if slide.diagram:
            nodes = slide.diagram.get("nodes", [])
            edges = slide.diagram.get("edges", [])
            if len(nodes) < 2 or len(edges) < 1:
                issues.append("diagram_disconnected")
                score.density_compliance = max(0.0, score.density_compliance - 1.5)

        # Narrative fit baseline (LLM critic refines this)
        has_any_block = any([
            slide.bullets, slide.body, slide.stat_blocks, slide.quote, slide.chart,
            slide.table, slide.timeline, slide.comparison, slide.diagram,
        ])
        headline_words = len((slide.headline or "").split())
        has_rich_content = (
            slide.bullets
            and (slide.body or slide.stat_blocks or slide.chart or slide.table
                 or len(slide.bullets) >= 3)
            and (3 <= headline_words <= 8)
        )
        score.narrative_fit = 9.0 if (slide.headline and has_rich_content) else (
            7.5 if (slide.headline and has_any_block) else 4.0
        )

        # Coherence baseline — higher for data slides with quant blocks
        if slide.headline:
            has_quant_block = any([
                slide.stat_blocks, slide.chart, slide.table,
                slide.comparison, slide.timeline,
            ])
            score.coherence = 9.0 if (has_rich_content or has_quant_block) else 7.5
        else:
            score.coherence = 4.0

        # Visual quality baseline — local heuristic, refined by aesthetic_scorer
        score.visual_quality = 7.0
        try:
            # Convert slide to dict format for aesthetic scorer
            slide_dict = {
                "headline": slide.headline or "",
                "body": slide.body or "",
                "bullets": slide.bullets or [],
                "layout": slide.layout or "default",
            }
            
            # Use empty design_tokens for now (can be enhanced later to pass from caller)
            design_tokens = {}
            
            # Calculate element count
            element_count = len(slide.bullets or []) + (1 if slide.headline else 0) + (1 if slide.body else 0)
            
            # Score aesthetic quality
            aesthetic_score = score_slide_aesthetic(
                slide=slide_dict,
                design_tokens=design_tokens,
                kit_id=slide.layout or "TitleHero",
                variant=slide.layout or "default",
                element_count=element_count,
            )
            
            # Use the overall aesthetic score
            score.visual_quality = aesthetic_score.overall
            
            # Add aesthetic critique to issues
            if aesthetic_score.critique:
                issues.extend(aesthetic_score.critique[:3])  # Add top 3 critiques
        except Exception as aesthetic_err:
            logger.warning(
                "aesthetic_scoring_failed",
                slide_index=slide.index,
                error=str(aesthetic_err)[:200],
            )
            # Fallback to baseline scoring
            if slide.layout in {"cinematic-cover", "cinematic-gradient", "editorial-left", "editorial-right"}:
                score.visual_quality = 8.5
            elif slide.layout in {"glass-grid", "glass-cards"}:
                score.visual_quality = 8.0
        
        # Penalize overused layouts
        layout_counts = {}
        for s in all_slides:
            layout_counts[s.layout] = layout_counts.get(s.layout, 0) + 1
        if layout_counts.get(slide.layout, 0) > len(all_slides) * 0.4:
            score.visual_quality -= 1.5
            issues.append("overused_layout")

        self._apply_modern_investor_rules(score, issues, slide, investor_context)

        score.issues = issues
        score.overall = self._weighted(score)

        # v12.1 — deck-wide loop penalties. `detect_loops` returns a
        # per-slide penalty in 0..4.0 accompanied by human-readable
        # findings; apply directly to the weighted overall AND merge
        # findings into the issues list so rewrites see them.
        if loop_report is not None:
            loop_penalty = loop_report.per_slide_penalty.get(slide.index, 0.0)
            if loop_penalty > 0:
                score.overall = max(0.0, score.overall - loop_penalty)
                loop_issues = loop_report.per_slide_issues.get(slide.index, [])
                score.issues = list(dict.fromkeys(score.issues + loop_issues))[:6]

        score.needs_rewrite = score.overall < rewrite_threshold
        return score

    # ── Founder replan — Kimi 2.6 targeted premium rewrite ─────────
    async def _premium_targeted_rewrite_kimi26(
        self,
        slides: list[GeneratedSlide],
        skeleton: DeckSkeleton,
        research: ResearchPacket,
        report: CriticReport,
    ) -> tuple[list[GeneratedSlide], CriticReport]:
        """Targeted rewrite of investor-critical slides via Kimi 2.6.

        Runs exactly once per deck. Rewrites only PREMIUM_CRITICAL_INTENTS
        slides that scored below settings.PREMIUM_CRITICAL_RESCORE_TARGET. Uses the
        PREMIUM_TARGETED_REWRITE TaskType so the router puts kimi-2.6 at the
        head of the chain and, if budget is exhausted, falls through to
        kimi-k2-thinking / deepseek-v3 automatically.
        """
        score_by_idx = {s.index: s for s in report.slide_scores}
        targets: list[int] = []
        for s in slides:
            if (s.intent or "").lower() not in self.PREMIUM_CRITICAL_INTENTS:
                continue
            sc = score_by_idx.get(s.index)
            if sc is None:
                continue
            if sc.overall < settings.PREMIUM_CRITICAL_RESCORE_TARGET:
                targets.append(s.index)
        if not targets:
            return slides, report

        # Only try to rewrite as many as the Kimi 2.6 budget allows; everything
        # above budget will transparently degrade via the router's fallback
        # chain (Kimi 2.0 / DeepSeek). We still attempt all targets — the
        # router skips cleanly.
        from app.services.v4.parallel_writer import _PREMIUM_WRITER_SYSTEM

        logger.info(
            "v4_critic_premium_kimi26_rewrite_start",
            n_targets=len(targets),
            project_id=skeleton.project_id,
        )

        async def _rewrite_one(idx: int) -> Optional[GeneratedSlide]:
            slide = slides[idx]
            skel = skeleton.slides[idx] if idx < len(skeleton.slides) else None
            issues = (score_by_idx[idx].issues if idx in score_by_idx else []) or []
            current_json = {
                "headline": slide.headline,
                "subheadline": slide.subheadline,
                "body": slide.body,
                "bullets": slide.bullets,
                "stat_blocks": slide.stat_blocks,
                "comparison": slide.comparison,
                "layout": slide.layout,
                "intent": slide.intent,
            }
            user_msg = (
                f"You are rewriting ONE slide in an investor pitch deck because the\n"
                f"critic flagged it. Produce a stronger JSON slide that fixes EVERY\n"
                f"listed issue. Do NOT introduce generic headlines or banned phrases.\n\n"
                f"Slide intent: {slide.intent}\n"
                f"Layout hint: {slide.layout}\n"
                f"Company: {research.company_name or 'unknown'}\n"
                f"Critic issues to fix: {issues}\n\n"
                f"Planner thesis sentence: "
                f"{(skel.thesis_sentence if skel else '') or '(derive from evidence)'}\n"
                f"Required quant signals: "
                f"{skel.required_quant_signals if skel else []}\n\n"
                f"Current slide JSON (rewrite this, do not echo):\n"
                f"{json.dumps(current_json, indent=1)[:1800]}\n\n"
                f"Scoped evidence (cite these URLs):\n"
                f"{research.as_prompt_context(max_chars=1800)}\n\n"
                f"Return the FULL improved slide as strict JSON."
            )
            try:
                resp = await safe_complete(
                    router=self.router,
                    primary_task=TaskType.PREMIUM_TARGETED_REWRITE,
                    fallback_task=TaskType.NARRATIVE_STORYTELLING,
                    messages=[
                        {"role": "system", "content": _PREMIUM_WRITER_SYSTEM},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.45,
                    max_tokens=1400,
                    response_format={"type": "json_object"},
                    presentation_id=skeleton.project_id,
                    phase=f"v4_critic_premium_rewrite_{idx}",
                    timeout_s=30.0,
                    fallback_timeout_s=22.0,
                )
                data = safe_json_loads(resp.content, context=f"critic_rewrite_{idx}")
                if not isinstance(data, dict):
                    return None
                # Apply patch over the current slide — keep everything that isn't
                # replaced. This avoids losing team_members, images, citations, etc.
                new = GeneratedSlide(
                    index=slide.index,
                    intent=slide.intent,
                    layout=str(data.get("layout") or slide.layout),
                    headline=str(data.get("headline") or slide.headline)[:140],
                    subheadline=(str(data["subheadline"])[:240]
                                 if data.get("subheadline") is not None else slide.subheadline),
                    bullets=[str(b)[:180] for b in (data.get("bullets") or slide.bullets)][:6],
                    body=(str(data["body"])[:800]
                          if data.get("body") is not None else slide.body),
                    stat_blocks=data.get("stat_blocks") or slide.stat_blocks,
                    quote=data.get("quote") or slide.quote,
                    chart=data.get("chart") or slide.chart,
                    table=data.get("table") or slide.table,
                    timeline=data.get("timeline") or slide.timeline,
                    comparison=data.get("comparison") or slide.comparison,
                    diagram=data.get("diagram") or slide.diagram,
                    image_prompt=data.get("image_prompt") or slide.image_prompt,
                    speaker_notes=data.get("speaker_notes") or slide.speaker_notes,
                    citations=data.get("citations") or slide.citations,
                    raw=dict(slide.raw) if slide.raw else {},
                    render_decision=slide.render_decision,
                    team_members=slide.team_members,
                )
                new.raw["kimi26_rewrite_applied"] = True
                return new
            except (JSONRepairFailedError, Exception) as e:  # noqa: BLE001
                logger.warning(
                    "v4_critic_kimi26_rewrite_failed",
                    index=idx, error=str(e)[:200],
                )
                return None

        results = await asyncio.gather(
            *[_rewrite_one(i) for i in targets],
            return_exceptions=False,
        )
        n_applied = 0
        for new in results:
            if new is not None:
                slides[new.index] = new
                n_applied += 1

        if n_applied == 0:
            logger.info(
                "v4_critic_premium_kimi26_rewrite_no_changes",
                project_id=skeleton.project_id,
            )
            return slides, report

        # Re-score the deck after rewrite so the returned CriticReport reflects
        # the improved state.
        new_report = await self.evaluate(slides, skeleton, research=research, mode="premium")
        logger.info(
            "v4_critic_premium_kimi26_rewrite_done",
            project_id=skeleton.project_id,
            n_applied=n_applied,
            new_overall=round(new_report.overall, 3),
            old_overall=round(report.overall, 3),
        )
        return slides, new_report

    async def _llm_critique(
        self,
        slides: list[GeneratedSlide],
        skeleton: DeckSkeleton,
    ) -> list[SlideScore]:
        compact = [
            {
                "index": s.index,
                "intent": s.intent,
                "layout": s.layout,
                "headline": s.headline,
                "bullets": s.bullets,
                "stat_blocks": s.stat_blocks,
                "has_chart": bool(s.chart),
            }
            for s in slides
        ]
        user_msg = f"""Deck title: {skeleton.title}
Narrative arc: {skeleton.narrative_arc}

Slides:
{json.dumps(compact, indent=1)[:6000]}

Score every slide. Return JSON only."""

        response = await safe_complete(
            router=self.router,
            primary_task=TaskType.REFINEMENT,
            # Founder fix (Apr 2026): critic must not degrade to a
            # classifier — keep it on the REFINEMENT tier. The router
            # rotates within REFINEMENT (gpt-4o-mini → mistral-medium
            # → nv-glm-4.7) before falling through to OpenRouter.
            fallback_task=TaskType.REFINEMENT,
            messages=[
                {"role": "system", "content": _CRITIC_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=2500,
            response_format={"type": "json_object"},
            presentation_id=skeleton.project_id,
            phase="v4_critic",
            timeout_s=55.0,
            fallback_timeout_s=40.0,
        )
        try:
            data = safe_json_loads(response.content, context="critic")
        except JSONRepairFailedError:
            logger.warning("v4_critic_json_unrecoverable", head=response.content[:200] if response.content else "")
            data = {}

        out: list[SlideScore] = []
        by_idx = {int(s.get("index", -1)): s for s in (data.get("slides") or [])}
        for s in slides:
            d = by_idx.get(s.index, {})
            score = SlideScore(
                index=s.index,
                narrative_fit=float(d.get("narrative_fit", 7)),
                specificity=float(d.get("specificity", 7)),
                variety=float(d.get("variety", 7)),
                density_compliance=float(d.get("density_compliance", 7)),
                coherence=float(d.get("coherence", 7)),
                issues=[str(x) for x in (d.get("issues") or [])][:5],
                overall=0,
            )
            score.overall = self._weighted(score)
            score.needs_rewrite = score.overall < self.REWRITE_THRESHOLD
            out.append(score)
        return out
