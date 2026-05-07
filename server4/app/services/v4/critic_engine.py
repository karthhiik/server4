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
from app.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class SlideScore:
    index: int
    overall: float                          # 0..10
    narrative_fit: float = 0.0
    specificity: float = 0.0
    variety: float = 0.0
    density_compliance: float = 0.0
    coherence: float = 0.0
    issues: list[str] = field(default_factory=list)
    needs_rewrite: bool = False


@dataclass
class CriticReport:
    overall: float                          # 0..10 weighted average
    slide_scores: list[SlideScore]
    needs_rewrite_indices: list[int]
    loop_report: Optional[LoopGuardReport] = None   # v12.1 — deck-wide repetition scan


_CRITIC_SYSTEM = """You are the Critic. Score every slide 0-10 on five dimensions:
  narrative_fit (25%), specificity (25%), variety (20%), density_compliance (15%), coherence (15%)

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

Return ONLY JSON:
{
  "slides": [
    {"index": 0, "narrative_fit": 8.5, "specificity": 7.0, "variety": 9.0,
     "density_compliance": 9.5, "coherence": 8.0, "issues": ["..."]}
  ]
}
"""


class CriticEngine:
    REWRITE_THRESHOLD = 7.0
    # Founder replan — premium requires a higher local-shortcut bar before we
    # skip the LLM critic. Standard keeps the legacy bar (8.5) for latency.
    SHORTCUT_THRESHOLD_STANDARD = 8.5
    SHORTCUT_THRESHOLD_PREMIUM = 9.2
    MAX_REFINEMENT_CYCLES = 2
    # Intent set that defines "critical slides" for the premium Kimi 2.6
    # targeted rewrite pass. These are the slides investors remember;
    # any below-9.0 outcome here is worth burning Kimi 2.6 budget on.
    PREMIUM_CRITICAL_INTENTS = {"title", "market", "traction", "competition", "ask"}
    PREMIUM_CRITICAL_RESCORE_TARGET = 9.0

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
        whose score is below PREMIUM_CRITICAL_RESCORE_TARGET after the normal
        refinement loop converges.
        """
        report = await self.evaluate(slides, skeleton, research=research, mode=mode)

        cycles = 0
        while report.needs_rewrite_indices and cycles < self.MAX_REFINEMENT_CYCLES:
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
        # score below PREMIUM_CRITICAL_RESCORE_TARGET. Budgeted at the router
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
            evidence_text = " ".join(
                f"{c.title} {c.snippet}"
                for c in (research.citations + research.news_citations)
            )

        # v12.1 — deck-wide repetition scan (pure, sub-ms). Findings feed
        # into per-slide penalties and rewrite feedback so loops trigger
        # targeted regeneration the same way a quality miss does.
        loop_report = detect_loops(slides)

        # Local rules-based pre-pass (cheap, deterministic)
        local_scores = [
            self._local_score(s, slides, evidence_text, loop_report=loop_report)
            for s in slides
        ]

        # Optionally augment with LLM holistic critique (skip if all locally above threshold)
        local_overall = sum(s.overall for s in local_scores) / max(1, len(local_scores))
        shortcut_threshold = (
            self.SHORTCUT_THRESHOLD_PREMIUM if mode == "premium"
            else self.SHORTCUT_THRESHOLD_STANDARD
        )
        if local_overall >= shortcut_threshold and not any(s.needs_rewrite for s in local_scores):
            return CriticReport(
                overall=local_overall,
                slide_scores=local_scores,
                needs_rewrite_indices=[s.index for s in local_scores if s.needs_rewrite],
                loop_report=loop_report,
            )

        try:
            llm_scores = await self._llm_critique(slides, skeleton)
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
                merged[-1].needs_rewrite = merged[-1].overall < self.REWRITE_THRESHOLD
            scores = merged
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
    def _weighted(s: SlideScore) -> float:
        return (
            s.narrative_fit * 0.25
            + s.specificity * 0.25
            + s.variety * 0.20
            + s.density_compliance * 0.15
            + s.coherence * 0.15
        )

    def _local_score(
        self,
        slide: GeneratedSlide,
        all_slides: list[GeneratedSlide],
        evidence_text: str = "",
        *,
        loop_report: Optional[LoopGuardReport] = None,
    ) -> SlideScore:
        score = SlideScore(index=slide.index, overall=0)
        issues: list[str] = []
        generic_text = " ".join([slide.headline, slide.subheadline or "", slide.body or "", " ".join(slide.bullets)]).lower()

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
        body_text = " ".join([slide.headline, slide.subheadline or "", " ".join(slide.bullets), slide.body or ""])
        has_numbers = any(ch.isdigit() for ch in body_text)
        has_money = "$" in body_text or "%" in body_text
        has_citations = bool(slide.citations)
        spec = 10.0

        # Numeric grounding penalty (anti-hallucination)
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
                # Each ungrounded number costs 1.5 specificity points (max -5)
                penalty = min(5.0, 1.5 * len(audit.ungrounded))
                spec -= penalty
                if audit.ungrounded:
                    issues.append(
                        f"ungrounded_numbers={len(audit.ungrounded)}:" +
                        ",".join(t.token for t in audit.ungrounded[:3])
                    )
        score.specificity = max(0.0, min(10.0, spec))
        if not has_numbers and slide.intent in {"market", "traction", "financials"}:
            score.specificity = max(0.0, score.specificity - 3.0)
            issues.append("no_numbers_in_data_slide")
        if slide.intent in {"market", "traction", "financials"} and not any([slide.stat_blocks, slide.chart, slide.table]):
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

        # Founder replan — template headline detector. Hard −3 specificity hit
        # when the slide headline matches any banned pattern, ensuring these
        # slides always fall below the rewrite threshold and get regenerated.
        if settings.ENABLE_TEMPLATE_DETECTOR:
            det = content_rules.detect_template_headline(slide.headline)
            if det.is_template:
                score.specificity = max(0.0, score.specificity - 3.0)
                score.narrative_fit = max(0.0, score.narrative_fit - 3.0)
                issues.append(f"template_headline:{det.label}")

        # Founder replan — broader generic-phrase detector powered by
        # content_rules. Catches variants the hard-coded list above misses.
        if settings.ENABLE_CONTENT_RULES_GATE:
            generic_hits = content_rules.detect_generic_phrases(
                slide.headline, slide.subheadline, slide.body, *slide.bullets,
            )
            if generic_hits:
                score.specificity = max(0.0, score.specificity - min(3.0, len(generic_hits)))
                issues.append("generic_phrases:" + ",".join(generic_hits[:3]))

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
        score.narrative_fit = 7.5 if slide.headline and has_any_block else 4.0

        # Coherence baseline
        score.coherence = 7.5 if slide.headline else 4.0

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

        score.needs_rewrite = score.overall < self.REWRITE_THRESHOLD
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
        slides that scored below PREMIUM_CRITICAL_RESCORE_TARGET. Uses the
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
            if sc.overall < self.PREMIUM_CRITICAL_RESCORE_TARGET:
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
