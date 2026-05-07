"""
V4 Parallel Writer — Skeleton-of-Thought Phase 2 (parallel slide expansion).

Per `slide-generation-architecture` skill:
  Phase 2 (Parallel Expansion, ~10s): N parallel writer calls, one per slide.
  Each writer receives ONLY its slice — its skeleton + scoped research.
  Writers produce schema-enforced JSON.

Per `pitch-deck-research` skill density caps:
  - Headline: 3-8 words
  - Key bullets: ≤4 per slide, ≤10 words each
  - "So What" filter: every line must answer why the audience cares.

Premium model: narrative chain (NARRATIVE_STORYTELLING)
Standard model: fast fill chain (TEMPLATE_FILL) with narrative fallback
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Awaitable

import structlog

from app.services.llm.model_router import ModelRouter, TaskType
from app.services.v4.research_collector import ResearchPacket, Citation
from app.services.v4.skeleton_planner import SlideSkeleton, DeckSkeleton
from app.services.v4.json_repair import safe_json_loads, JSONRepairFailedError
from app.services.v4.llm_safe import safe_complete
from app.services.v4.visual_decider import decide_visual
from app.services.v4.dsl_validators import (
    normalize_table,
    normalize_timeline,
    normalize_comparison,
    normalize_diagram,
)
from app.services.v4.slide_repair import repair_slide
from app.services.v4 import content_rules
from app.services.v4.schema_guard import SchemaValidationError, validate_writer_output
from app.services.v4.quality_metrics import (
    QualityEvent,
    circuit_open,
    gate_decision,
    record_failure_window,
    record_quality_event,
)
from app.config import settings

logger = structlog.get_logger(__name__)


COMPANY_SPECIFIC_INTENTS = {"traction", "team", "financials", "ask"}
_EXAMPLE_HINTS = (
    "pitch deck", "pitch-deck", "template", "examples", "example",
    "slidebean", "failory", "bestpitchdeck", "mideahub", "forumvc",
    "qubit", "beyondlabs", "vip.graphics", "financialmodelslab", "businessplan-templates",
)


@dataclass
class GeneratedSlide:
    index: int
    intent: str
    layout: str
    headline: str
    subheadline: Optional[str] = None
    bullets: list[str] = field(default_factory=list)
    body: Optional[str] = None
    stat_blocks: list[dict[str, str]] = field(default_factory=list)   # [{"value":"$2.4B","label":"TAM"}]
    quote: Optional[dict[str, str]] = None                            # {"text":"...","attribution":"..."}
    chart: Optional[dict[str, Any]] = None                            # {"type":"bar","data":[...]}
    # v10.2 DSL extension — code-rendered visual blocks
    table: Optional[dict[str, Any]] = None       # {"headers":[...],"rows":[[...]],"caption":...}
    timeline: Optional[dict[str, Any]] = None    # {"events":[{"date":..,"title":..,"description":..}]}
    comparison: Optional[dict[str, Any]] = None  # {"columns":[{"title":..,"items":[..]}]}
    diagram: Optional[dict[str, Any]] = None     # {"nodes":[...],"edges":[...],"layout":"flow"}
    image_prompt: Optional[str] = None
    # v12.1 — image fields populated by `image_generator.generate_images()`
    # AFTER the writer phase. Declared here (instead of being set as
    # runtime attrs) so they survive `asdict()` serialization in the
    # live test harness and any downstream JSON dumps. Empty / None
    # means no image was produced for this slide — never substitute.
    image_url: Optional[str] = None
    image_source: Optional[str] = None      # tier name: "flux" | "sd3" | "phoenix" | "lucid" | "gradient_svg"
    image_position: Optional[str] = None    # "background" | "right" | "left" | "full"
    image_intent: Optional[str] = None      # "hero" | "support" | "pattern" | "decoration"
    speaker_notes: Optional[str] = None
    citations: list[dict[str, str]] = field(default_factory=list)     # [{"url":"...","title":"..."}]
    raw: dict[str, Any] = field(default_factory=dict)
    # v10.3 — system-decided visual modality (code | image | none)
    render_decision: Optional[dict[str, Any]] = None
    # v11 — structured team-member objects (only populated for intent=="team").
    # Each entry: {name, role, bio, linkedin_url, photo_url, photo_source,
    # photo_attribution, is_default_avatar, source, confidence}
    team_members: list[dict[str, Any]] = field(default_factory=list)
    requires_user_input: bool = False
    user_input_kind: Optional[str] = None
    user_input_reason: Optional[str] = None
    # v11 — company icon URL (only populated when user uploaded one in
    # premium mode). Used by title-slide and team-slide renderers.
    company_icon_url: Optional[str] = None
    # v12 — narrative rationale carried from the planner ("why this slide
    # exists") and the deck-level purpose (e.g. investor_pitch, educational,
    # sales_pitch). Surfaced in the Content Display stage as a hover tooltip
    # so the user understands the editorial decision behind every slide.
    rationale: str = ""
    purpose: str = ""


# ── URL hygiene ────────────────────────────────────────────────────

def _sanitize_url(raw: str) -> str:
    """Clean a citation URL coming back from an LLM.

    LLMs occasionally hallucinate a duplicated scheme prefix (we have seen
    `httpshttps://...` and `https://https://...`), wrap URLs in quotes, or
    return whitespace-padded values. This collapses those into a clean
    `http(s)://...` URL or returns "" if the value is unusable.
    """
    if not raw:
        return ""
    s = str(raw).strip().strip("\"'").strip()
    if not s:
        return ""
    low = s.lower()
    # Collapse "httpshttps://..." → "https://...".
    for sch in ("https", "http"):
        glued = sch + sch + "://"
        if low.startswith(glued):
            s = sch + "://" + s[len(glued):]
            low = s.lower()
            break
    # Collapse "https://https://..." → "https://...".
    for sch in ("https://", "http://"):
        if low.startswith(sch):
            rest = s[len(sch):]
            rest_low = rest.lower()
            for inner in ("https://", "http://"):
                if rest_low.startswith(inner):
                    s = sch + rest[len(inner):]
                    break
            break
    # Must end up with a real scheme; reject otherwise.
    if not s.lower().startswith(("http://", "https://")):
        return ""
    return s[:1024]


# ── Prompts ────────────────────────────────────────────────────────

_PREMIUM_WRITER_SYSTEM = """You are an elite slide composer for an investor-grade pitch deck.

You receive ONE slide skeleton and a small slice of research. Produce ONE slide that
reads like a senior designer + senior writer collaborated on it. Every slide must
carry a clear narrative voice — not a list of telegraphic phrases.

THESIS-FIRST HEADLINE RULE (most important):
- Every headline must be a THESIS only this company could honestly claim.
- When `planner_generic_risk` in the user message is "high", the planner
  gave you a placeholder headline — DO NOT echo it. Use `planner_thesis_sentence`
  and the evidence below to craft a brand-new specific headline.
- Good: "$4.2B SMB Payments, 18% YoY", "Close Invoices In 90 Seconds",
  "Built Payments At Stripe And Square".
- Bad (NEVER ship): "Market Opportunity", "Our Business Model",
  "The Team", "Competitive Landscape", "Join Our Journey".

""" + content_rules.prompt_rules_block() + """

Hard constraints:
- STRUCTURED USER INPUT block (when present in the user message) is AUTHORITATIVE.
  Every number, name, customer, investor, and market size listed there MUST appear
  on the slide where relevant — verbatim, never paraphrased. The USER is the source
  of truth; research is supporting evidence only. If the structured block lists a
  financial metric, IT MUST appear as a stat_block or chart datum. If it lists a
  team member, IT MUST appear by real name — never invent "Alex Chen".
- planner_directive in the user message is INSTRUCTION, not slide copy. Do NOT
  echo phrases like "Show the pain", "Highlight", "Demonstrate", "Explain",
  "Describe" verbatim into headline / subheadline / body. Translate the directive
  into audience-facing prose.
- Headline: 3-8 words, punchy, specific (not generic).
- Subheadline: ALWAYS provide a 6-14 word descriptive subtitle that frames the
  slide's argument. Never leave subheadline empty/null. It is the slide's thesis line.
- Bullets: 3-4 items (or 0 only if a structured block fully replaces them).
  Each bullet 6-14 words, written as a descriptive phrase that passes the "So What"
  filter. NEVER use telegraphic 2-4 word phrases like 'Manual processes error-prone' —
  write 'Manual invoice approvals introduce errors and slow finance teams'.
- Body: For layouts in {title-slide, title-only, bullet-points, two-column,
  image-full, image-left, image-right}, ALWAYS include `body` as a 2-3 sentence
  narrative paragraph (40-90 words) that gives the slide its story arc. Skip `body`
  ONLY when a structured visual block (chart/table/timeline/diagram/comparison/
  stat-hero) is the primary content.
- Speaker notes: ALWAYS include `speaker_notes` (2-3 sentences, what the presenter
  would actually say while this slide is on screen).
- Density target is a floor, not a ceiling: 'minimal'=headline+subheadline+body;
  'low'=add 2 bullets; 'medium'=3 bullets + body; 'high'=4 bullets + body OR full
  structured block. Never strip subheadline or speaker_notes regardless of density.
- Cite specific numbers and source URLs from the research when claims are quantitative.
- NEVER invent statistics. If research lacks a number, omit the claim — but keep the
  qualitative narrative.
- Intent-specific truthfulness rules:
        title -> if company_name is provided, the headline must include it.
        market -> use only market-wide or segment-wide evidence; prefer TAM/SAM/SOM-style
                            stat blocks or a chart when grounded.
        traction / financials / ask -> NEVER use numbers from generic pitch-deck examples,
                            other startups, or template sites. Only use numbers that appear in the
                            user query, uploaded documents, or citations clearly about this company.
        ask -> if no explicit raise amount/equity is provided, do NOT invent one. Frame the
                     ask around milestones and use of funds without a fake amount.
        team -> never fabricate founder names, bios, exits, titles, or years of experience.
- Match the layout_hint with the matching content shape:
    stat-hero -> populate `stat_blocks` (1-3 items)
    chart-focus -> populate `chart`
    quote -> populate `quote`
    grid-3 -> 3 bullets or 3 stat_blocks
    comparison -> populate `comparison` with 2-3 columns (each {title, items[]})
    image-full -> minimal text + image_prompt
    title-only -> headline + subheadline only
    table -> populate `table` with headers+rows (max 6 cols, 8 rows)
    timeline -> populate `timeline.events[]` (3-7 items, each {date, title, description?})
    diagram -> populate `diagram` with nodes+edges (React Flow shape, max 12 nodes)
    process -> use `diagram` (layout="flow") OR numbered bullets

Return ONLY JSON. Include only the fields the layout needs:
{"headline":"...","subheadline":"...","bullets":["..."],"body":"...",
 "stat_blocks":[{"value":"...","label":"..."}],
 "quote":{"text":"...","attribution":"..."},
 "chart":{"type":"bar|line|pie","data":[{"label":"...","value":...}]},
 "table":{"caption":"...","headers":["..."],"rows":[["..."]]},
 "timeline":{"orientation":"horizontal|vertical","events":[{"date":"...","title":"...","description":"..."}]},
 "comparison":{"columns":[{"title":"...","items":["..."],"highlight":false}]},
 "diagram":{"layout":"flow|tree|cycle","nodes":[{"id":"a","label":"...","type":"input|output|default"}],"edges":[{"from":"a","to":"b","label":"..."}]},
 "image_prompt":"...","speaker_notes":"...",
 "citations":[{"url":"...","title":"..."}]}
Omit fields that don't apply to the layout. Do not duplicate content across blocks.
"""

_STANDARD_WRITER_SYSTEM = """You compose a single slide for a real investor pitch deck.
Return ONLY JSON. Every slide must read with narrative voice — not telegraphic phrases.

THESIS-FIRST HEADLINE RULE:
- Every headline must be a SPECIFIC thesis, never a category label.
- If `planner_generic_risk` = "high", rewrite the headline from the
  `planner_thesis_sentence` and the scoped evidence.

""" + content_rules.prompt_rules_block() + """

STRUCTURED USER INPUT rule: when the user message contains a "STRUCTURED USER INPUT"
block, its facts are AUTHORITATIVE. Use the user's exact company name, team names,
financial metrics, market sizes, and fundraising asks verbatim. Never invent numbers
or names when structured data is provided.

BANNED generic phrases (never write these as headlines/subheadlines): "Transforming
industries", "Scaling revenue", "AI-driven automation", "Unlock potential", "Drive
growth", "Revolutionary solution", "Next generation", "Unique features",
"Market need", "Cutting edge". Replace with a concrete claim tied to the company
or its numbers.

Mandatory fields on EVERY slide:
- headline: 3-8 words, specific, no generic claims.
- subheadline: 6-14 words. A descriptive subtitle that frames the slide's argument.
  NEVER leave this null or empty.
- speaker_notes: 2-3 sentences the presenter would actually say.

For layouts in {title-slide, title-only, bullet-points, two-column, image-full,
image-left, image-right}: ALSO include `body` as a 2-3 sentence paragraph (40-90
words) giving the slide its story arc.

Bullets: 3-4 items, each 6-14 words, descriptive (NOT telegraphic). Bad:
"Manual processes error-prone". Good: "Manual invoice approvals introduce errors
and slow finance teams".

Match the layout_hint with one matching structured block (in addition to the
fields above — body may be omitted only when a structured block is the primary
content):
  table     -> {"table":{"headers":[],"rows":[[]]}}
  timeline  -> {"timeline":{"events":[{"date":"","title":"","description":""}]}}
  comparison-> {"comparison":{"columns":[{"title":"","items":[]}]}}
  diagram   -> {"diagram":{"nodes":[{"id":"a","label":""}],"edges":[{"from":"a","to":"b"}]}}
  stat-hero -> {"stat_blocks":[{"value":"","label":""}]}
  chart-focus -> {"chart":{"type":"bar|line|pie","data":[{"label":"","value":0}]}}
  quote     -> {"quote":{"text":"","attribution":""}}

Shape:
{"headline":"3-8 words","subheadline":"6-14 words REQUIRED",
"bullets":["6-14 words each"],"body":"2-3 sentence narrative when layout supports it",
"stat_blocks":[],"table":null,"timeline":null,"comparison":null,"diagram":null,
"chart":null,"quote":null,"image_prompt":"optional",
"speaker_notes":"REQUIRED 2-3 sentences","citations":[]}

No invented stats. Do NOT output generic claims ("Unique features", "Market need").
Ground bullets in facts. If no facts available, describe concrete mechanics narratively.
For traction/financials/ask/team slides, honesty beats specificity: omit the unsupported
detail rather than importing facts from unrelated startups."""


# ── Design-token context for the writer ───────────────────────────
# Appended to the USER message (never the system prompt) so DeepSeek's
# shared-prefix cache still hits on the ~80% stable head. Tokens that
# are `None` or missing are silently skipped so legacy callers that
# don't pass design_tokens get the old behavior.

_DENSITY_RULES: dict[str, str] = {
    "compact": (
        "Density=COMPACT: headline 3-5 words, subheadline 6-10 words, "
        "bullets 0-3 items of 6-9 words each. Favor stat_blocks or one "
        "structured block over prose. Body paragraph only when layout demands it."
    ),
    "comfortable": (
        "Density=COMFORTABLE: headline 4-7 words, subheadline 8-14 words, "
        "bullets 3-4 items of 6-12 words each. Body 40-70 words when the "
        "layout is prose-oriented (title-slide, bullet-points, two-column, image-*)."
    ),
    "spacious": (
        "Density=SPACIOUS: headline 4-8 words, subheadline 8-14 words, "
        "bullets 2-3 items of 8-14 words each. Favor body paragraphs "
        "(60-90 words) over bullet lists. Let content breathe."
    ),
}


def _format_design_context(design_tokens: Optional[dict[str, Any]]) -> str:
    """Build a short design brief appended to the writer's user message.

    Shape of `design_tokens` matches ResolvedDesignTokens.to_dict() from
    `app.services.v4.design_resolver`. All keys are optional \u2014 we degrade
    gracefully when the caller passes None or a partial dict.
    """
    if not design_tokens:
        return ""

    density = (design_tokens.get("density") or "comfortable").lower()
    density_rule = _DENSITY_RULES.get(density, _DENSITY_RULES["comfortable"])

    palette = design_tokens.get("palette") or {}
    fonts = design_tokens.get("fonts") or {}
    primary = palette.get("primary") or "#2563eb"
    accent = palette.get("accent") or "#7c3aed"
    bg = palette.get("background") or "#0b0d12"
    chart_colors = palette.get("chart") or [primary, accent]
    heading_font = fonts.get("heading") or "Inter"
    body_font = fonts.get("body") or heading_font

    lines = [
        "",
        "Design brief (HONOR these constraints when producing content):",
        f"- {density_rule}",
        (
            "- Palette context: deck primary="
            f"{primary}, accent={accent}, background={bg}. "
            f"Heading font={heading_font}, body font={body_font}."
        ),
        (
            "- When producing a `chart` block, choose chart colors ONLY from this "
            f"deck palette list: {chart_colors[:5]}. Prefer the first 2-3 for "
            "primary data series."
        ),
        (
            "- When producing `stat_blocks`, keep the `value` string tight "
            "(3-8 chars) so it renders as large display type; put units in `label`."
        ),
    ]
    # Brand guidelines text (free-form notes from user) pass through verbatim
    provided_by = (design_tokens.get("provided_by") or "").lower()
    if provided_by in {"user", "hybrid"}:
        lines.append(
            "- The user explicitly chose this palette and/or typography. "
            "Stay faithful to it \u2014 do not propose alternative color schemes."
        )
    return "\n".join(lines) + "\n"


class ParallelWriter:
    """Fan-out parallel slide writers using asyncio.gather."""

    MAX_CONCURRENCY = 6   # cap parallel LLM calls to respect provider rate limits

    def __init__(self) -> None:
        self.router = ModelRouter.get_instance()

    async def write_all(
        self,
        skeleton: DeckSkeleton,
        research: ResearchPacket,
        mode: str = "standard",
        purpose: str = "",
        design_tokens: Optional[dict[str, Any]] = None,
        structured_context: Optional[dict[str, Any]] = None,
        on_slide_done: Optional[Callable[[GeneratedSlide], Awaitable[None]]] = None,
    ) -> list[GeneratedSlide]:
        """Write every slide in parallel, bounded by MAX_CONCURRENCY.

        Reranking is done SEQUENTIALLY first (CPU cross-encoder cannot be
        used in parallel — N writers competing for the same single-threaded
        model would all time out). After scoping is complete, the LLM-bound
        writers fan out concurrently.

        `design_tokens` — optional resolved token set (see
        `app.services.v4.design_resolver.resolve_design_tokens`). When
        supplied, it is folded into each writer's user message so the LLM
        honors the user's density + palette choices. System prompt is NOT
        mutated — this keeps DeepSeek's prefix cache hitting on the shared
        ~80% prefix across the N fan-out calls.
        """
        # 0) Warm reranker ONCE before sequential rerank pre-scoping.
        # This avoids warming it 7+ times (once per slide) which wastes 26s each.
        try:
            from app.services.v4.embeddings import get_reranker
            reranker = await get_reranker()
            if reranker is not None:
                logger.info("v4_reranker_warmed", stage="before_scope")
        except Exception:
            pass

        # 1) Sequential rerank pre-scoping (CPU-bound, cannot parallelize)
        scoped_map: dict[int, list[Citation]] = {}
        for s in skeleton.slides:
            scoped_map[s.index] = await self._scope_research(s, research)

        # 2) Parallel LLM writers (I/O-bound, can fan out)
        # Plan 05: True parallelism with explicit task creation.
        # MAX_CONCURRENCY=6 means at most 6 LLM calls run concurrently.
        sem = asyncio.Semaphore(self.MAX_CONCURRENCY)

        async def _bounded_and_notify(s: SlideSkeleton, idx: int) -> tuple[int, GeneratedSlide]:
            async with sem:
                try:
                    res = await self.write_one(
                        s, research, mode, skeleton.project_id,
                        pre_scoped=scoped_map.get(s.index),
                        purpose=purpose,
                        design_tokens=design_tokens,
                        structured_context=structured_context,
                    )
                    return idx, res
                except Exception as e:
                    logger.warning("v4_writer_slide_failed",
                        index=s.index, intent=s.intent, error=str(e))
                    return idx, self._fallback_slide(s)

        # Create ALL tasks first (schedule them immediately for true parallelism)
        # This ensures all coroutines are started, and semaphore limits concurrency
        tasks = [asyncio.create_task(_bounded_and_notify(s, i))
                 for i, s in enumerate(skeleton.slides)]
        slides: list[GeneratedSlide | None] = [None] * len(skeleton.slides)

        # as_completed yields tasks as they finish (true parallelism)
        for fut in asyncio.as_completed(tasks):
            idx, res = await fut
            slides[idx] = res
            if on_slide_done is not None:
                try:
                    await on_slide_done(res)
                except Exception as e:
                    logger.warning("v4_writer_on_slide_done_failed", error=str(e))

        # We guarantee all indices are filled heavily by the try/except
        return [s for s in slides if s is not None]

    async def write_one(
        self,
        slide: SlideSkeleton,
        research: ResearchPacket,
        mode: str,
        project_id: str,
        pre_scoped: Optional[list[Citation]] = None,
        purpose: str = "",
        design_tokens: Optional[dict[str, Any]] = None,
        structured_context: Optional[dict[str, Any]] = None,
    ) -> GeneratedSlide:
        scoped_citations = (
            pre_scoped if pre_scoped is not None
            else await self._scope_research(slide, research)
        )
        scoped_block = self._format_evidence_chunks(scoped_citations)
        design_block = _format_design_context(design_tokens)
        # Inject authoritative premium data relevant to this slide's intent.
        # These facts OVERRIDE research evidence when they conflict — user-
        # supplied numbers are ground truth.
        from app.services.v4.structured_context import format_for_writer
        structured_block = format_for_writer(slide.intent or "", structured_context or {})

        # Phase 12 — few-shot anchor (intent-keyed cadence reference).
        # Returns "" when no anchor matches OR when the kill-switch is off.
        # The anchor block is appended to the user message only, so the
        # provider's shared-prefix prompt cache still hits on the system
        # prompt across all N parallel writer calls.
        few_shot_block = ""
        try:
            from app.config import settings as _settings
            if getattr(_settings, "ENABLE_FEW_SHOT_ANCHORS", True):
                from app.services.v4.few_shot_anchors import format_few_shot
                few_shot_block = format_few_shot(
                    slide.intent or "", slide.layout_hint
                )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "v4_few_shot_anchor_failed",
                index=slide.index,
                intent=slide.intent,
                error=str(e)[:200],
            )
            few_shot_block = ""

        user_msg = f"""Slide {slide.index} skeleton:
intent: {slide.intent}
planner_directive (this is INSTRUCTION for you, NOT copy to display on the slide; never echo it verbatim into headline/subheadline/body): {slide.purpose}
headline_target: {slide.headline_target}
planner_thesis_sentence: {slide.thesis_sentence or '(none — derive from evidence)'}
planner_generic_risk: {slide.generic_risk}   # when 'high', DO NOT echo headline_target
required_quant_signals: {slide.required_quant_signals}
key_points: {slide.key_points}
density_target: {slide.density_target}
layout_hint: {slide.layout_hint}
visual_cue: {slide.visual_cue}
    company_name: {research.company_name or 'unknown'}
    company_specific_evidence_available: {bool([c for c in scoped_citations if self._is_company_specific_citation(c, research)])}

Scoped evidence chunks (treat each item as source-grounding; cite the URL in citations when used):
{scoped_block}
{structured_block}{design_block}{few_shot_block}
Produce the slide JSON now. The subheadline must be a NEW thesis line written
for the audience — it must NOT repeat the planner_directive."""

        if mode == "premium":
            task = TaskType.NARRATIVE_STORYTELLING
            fallback = TaskType.TEMPLATE_FILL
            system = _PREMIUM_WRITER_SYSTEM
            temperature = 0.6
            max_tokens = 1200
            timeout_s = 25.0
        else:
            # Plan 05: standard writer is the real-time path. Use the
            # mode-aware fast fill chain first, then narrative only as the
            # quality fallback. Premium keeps the deeper narrative route.
            task = TaskType.TEMPLATE_FILL
            fallback = TaskType.NARRATIVE_STORYTELLING
            routing_gate = gate_decision(
                "standard_routing",
                project_id=project_id,
                request_id=f"{project_id}:{slide.index}",
            )
            if routing_gate.enabled:
                task = TaskType.NARRATIVE_STORYTELLING
                fallback = TaskType.TEMPLATE_FILL
            system = _STANDARD_WRITER_SYSTEM
            temperature = 0.5
            max_tokens = 900
            timeout_s = 15.0  # Groq avg 2-4s per call, 15s allows for retries

        # ── Plan-v4 Section K: multi-model consensus panel ──────────
        # Gated behind settings.ENABLE_CONSENSUS so the legacy single-model
        # path remains exercisable. Consensus returns a JSON content string
        # fully compatible with our existing _parse_writer_output.
        from app.config import settings as _settings
        use_consensus = mode == "premium" and getattr(_settings, "ENABLE_CONSENSUS", False)

        if use_consensus:
            from app.services.v4.consensus import run_consensus

            skel_dict = {
                "index": slide.index,
                "intent": slide.intent,
                "purpose": slide.purpose,
                "headline_target": slide.headline_target,
                "key_points": slide.key_points,
                "density_target": slide.density_target,
                "layout_hint": slide.layout_hint,
                "visual_cue": slide.visual_cue,
            }
            budget = (
                float(getattr(_settings, "CONSENSUS_PREMIUM_BUDGET_S", 25.0))
                if mode == "premium"
                else float(getattr(_settings, "CONSENSUS_STANDARD_BUDGET_S", 15.0))
            )
            try:
                cons = await run_consensus(
                    router=self.router,
                    mode="premium" if mode == "premium" else "standard",
                    system=system,
                    user_msg=user_msg,
                    project_id=project_id,
                    phase=f"v4_writer_{slide.index}",
                    temperature=temperature,
                    max_tokens=max_tokens,
                    skeleton=skel_dict,
                    scoped_evidence=scoped_block,
                    design_context=design_block,
                    budget_s=budget,
                )
                if cons.content and cons.content.strip():
                    logger.info(
                        "v4_consensus_complete",
                        index=slide.index,
                        mode=cons.mode,
                        latency_ms=cons.latency_ms,
                        drafters=cons.drafters_used,
                        degraded=cons.council_degraded,
                        regen=cons.regen_triggered,
                        grader_scores=cons.grader_scores,
                    )
                    # Synthesize a minimal response-like object
                    class _ConsensusResponse:
                        def __init__(self, content: str, tokens: int):
                            self.content = content
                            self.tokens_used = tokens
                    response = _ConsensusResponse(
                        cons.content, cons.tokens_used,
                    )
                else:
                    logger.warning(
                        "v4_consensus_empty_falling_back_to_single",
                        index=slide.index, degraded=cons.council_degraded,
                    )
                    response = None
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "v4_consensus_failed_falling_back",
                    index=slide.index, error=str(e)[:200],
                )
                response = None
        else:
            response = None

        if response is None:
                response = await safe_complete(
                    router=self.router,
                    primary_task=task,
                    fallback_task=fallback,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                    presentation_id=project_id,
                    phase=f"v4_writer_{slide.index}",
                    # Standard mode: 15s timeout (Groq usually 2-4s, allow headroom)
                    # Premium mode: 30s timeout (better models, more complex output)
                    timeout_s=timeout_s,
                    fallback_timeout_s=25.0 if mode == "premium" else 15.0,
                    mode=mode,
                    resumable=True,
                    slot=f"writer_single_{slide.index}",
                )
        try:
            if settings.ENABLE_SCHEMA_GATE:
                writer_data = validate_writer_output(response.content, slide_index=slide.index)
            else:
                writer_data = safe_json_loads(response.content, context=f"writer:slide={slide.index}")
        except (SchemaValidationError, JSONRepairFailedError) as schema_err:
            breaker_key = f"writer_schema:{project_id}"
            failure_count = record_failure_window(breaker_key)
            await record_quality_event(QualityEvent(
                event="writer_schema_failed",
                project_id=project_id,
                gate="schema",
                severity="warning",
                tags={"slide_index": slide.index, "intent": slide.intent, "failure_count": failure_count},
                payload={"error": str(schema_err)[:240]},
            ))
            if circuit_open(breaker_key, threshold=3):
                fallback_slide = self._fallback_slide(slide)
                fallback_slide.raw = {
                    "fallback_reason": "writer_schema_circuit_open",
                    "schema_error": str(schema_err)[:240],
                }
                await record_quality_event(QualityEvent(
                    event="writer_schema_circuit_open",
                    project_id=project_id,
                    gate="schema",
                    severity="error",
                    tags={"slide_index": slide.index, "intent": slide.intent},
                ))
                return fallback_slide
            logger.warning(
                "v4_writer_schema_invalid_retrying",
                index=slide.index,
                primary_task=task.value,
                fallback_task=fallback.value,
                error=str(schema_err)[:240],
            )
            try:
                retry_response = await safe_complete(
                    router=self.router,
                    primary_task=fallback,
                    fallback_task=None,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=max(0.25, temperature - 0.1),
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                    presentation_id=project_id,
                    phase=f"v4_writer_{slide.index}_schema_retry",
                    timeout_s=25.0 if mode == "premium" else 6.0,
                    mode=mode,
                    resumable=True,
                    slot=f"writer_schema_retry_{slide.index}",
                )
                if settings.ENABLE_SCHEMA_GATE:
                    writer_data = validate_writer_output(
                        retry_response.content,
                        slide_index=slide.index,
                    )
                else:
                    writer_data = safe_json_loads(retry_response.content, context=f"writer:slide={slide.index}:retry")
                await record_quality_event(QualityEvent(
                    event="writer_schema_retry_succeeded",
                    project_id=project_id,
                    gate="schema",
                    tags={"slide_index": slide.index, "intent": slide.intent},
                ))
            except Exception as retry_err:  # noqa: BLE001
                await record_quality_event(QualityEvent(
                    event="writer_schema_retry_failed",
                    project_id=project_id,
                    gate="schema",
                    severity="error",
                    tags={"slide_index": slide.index, "intent": slide.intent},
                    payload={"error": str(retry_err)[:240]},
                ))
                logger.warning(
                    "v4_writer_schema_retry_failed_using_skeleton",
                    index=slide.index,
                    error=str(retry_err)[:240],
                )
                fallback_slide = self._fallback_slide(slide)
                fallback_slide.raw = {
                    "fallback_reason": "writer_schema_invalid",
                    "schema_error": str(schema_err)[:240],
                }
                return fallback_slide

        gs = self._parse_writer_output(slide, writer_data)
        # Deterministic post-processor — fixes structural issues that the
        # critic would otherwise penalize (headline length, missing layout
        # blocks, ungrounded numbers, no-numbers-in-data-slide).
        try:
            repair_slide(gs, skeleton=slide, research=research)
            # Recompute visual decision after repair (stat_blocks/chart may now exist)
            try:
                decision = decide_visual({
                    "intent": gs.intent,
                    "layout": gs.layout,
                    "visual_cue": slide.visual_cue,
                    "headline": gs.headline,
                    "subheadline": gs.subheadline,
                    "body": gs.body,
                    "bullets": gs.bullets,
                    "stat_blocks": gs.stat_blocks,
                    "quote": gs.quote,
                    "chart": gs.chart,
                    "table": gs.table,
                    "timeline": gs.timeline,
                    "comparison": gs.comparison,
                    "diagram": gs.diagram,
                    "image_prompt": gs.image_prompt,
                })
                gs.render_decision = {
                    "modality": decision.modality,
                    "reason": decision.reason,
                    "code_block": decision.code_block,
                    "renderer": decision.suggested_renderer,
                }
            except Exception:  # noqa: BLE001
                pass
        except Exception as e:  # noqa: BLE001 — repair must never crash a write
            logger.warning("writer_repair_failed", index=slide.index, error=str(e))
        # Stamp narrative rationale (planner's per-slide purpose) and the
        # deck-level purpose so the editor UI can explain *why* this slide
        # exists in this deck.
        gs.rationale = (slide.purpose or "").strip()
        gs.purpose = (purpose or "").strip()
        return gs

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _format_evidence_chunks(citations: list[Citation], max_items: int = 6) -> str:
        if not citations:
            return "(no specific research scoped to this slide)"

        lines: list[str] = []
        for idx, cite in enumerate(citations[:max_items], start=1):
            source_label = "uploaded_chunk" if cite.source == "uploaded_document" else cite.source
            snippet = " ".join((cite.snippet or "").split())[:320]
            lines.append(
                f"- chunk {idx} | source={source_label} | title={cite.title[:120]} | "
                f"url={cite.url} | evidence={snippet}"
            )
        return "\n".join(lines)

    @staticmethod
    def _citation_blob(cite: Citation) -> str:
        return f"{cite.title} {cite.snippet} {cite.url}".lower()

    @classmethod
    def _is_example_citation(cls, cite: Citation) -> bool:
        blob = cls._citation_blob(cite)
        return any(marker in blob for marker in _EXAMPLE_HINTS)

    @staticmethod
    def _has_uploaded_company_evidence(research: ResearchPacket) -> bool:
        cites = list(research.citations) + list(research.news_citations)
        return any(c.source == "uploaded_document" for c in cites)

    @classmethod
    def _is_company_named_web_citation(cls, cite: Citation, research: ResearchPacket) -> bool:
        if cite.source == "uploaded_document":
            return False
        company = (research.company_name or "").strip().lower()
        if not company or len(company) < 3:
            return False
        return company in cls._citation_blob(cite)

    @classmethod
    def _is_company_specific_citation(cls, cite: Citation, research: ResearchPacket) -> bool:
        return cite.source == "uploaded_document"

    async def _scope_research(self, slide: SlideSkeleton, research: ResearchPacket) -> list[Citation]:
        """Pick research most relevant to this slide's intent.

        v10.3: cross-encoder rerank when available, fall back to keyword overlap.
        Planner-referenced citations always come first.
        """
        intent = (slide.intent or "").lower().strip()
        all_cites = list(research.citations) + list(research.news_citations)

        if not self._has_uploaded_company_evidence(research):
            filtered = [c for c in all_cites if not self._is_company_named_web_citation(c, research)]
            if filtered:
                all_cites = filtered

        if intent in COMPANY_SPECIFIC_INTENTS:
            all_cites = [c for c in all_cites if self._is_company_specific_citation(c, research)]
        elif intent == "market":
            filtered = [c for c in all_cites if not self._is_example_citation(c)]
            if filtered:
                all_cites = filtered

        if not all_cites:
            return []

        ref_set = set(slide.evidence_refs or [])
        ref_scoped: list[Citation] = [c for c in all_cites if c.url in ref_set]
        rest = [c for c in all_cites if c.url not in ref_set]

        query = f"{slide.intent.replace('_', ' ')} {slide.headline_target} {' '.join(slide.key_points)}".strip()

        # Try cross-encoder rerank — only if model is already warm; otherwise
        # kick off background warm-up and use keyword fallback for this call.
        try:
            from app.services.v4.reranker import get_reranker
            reranker = await get_reranker()
            if reranker.is_loaded():
                # CPU inference budget: bge-reranker-v2-m3 (568M params) costs
                # ~200-400ms per (query,passage) pair on CPU. We cap pool=12 and
                # truncate passages to 220 chars so each slide's rerank stays
                # under ~5s. Total deck cost ≈ N_slides × 5s, run sequentially
                # via the writer semaphore.
                pool = rest[:12]
                passages = [
                    f"{(c.title or '')[:120]}. {(c.snippet or '')[:220]}"
                    for c in pool
                ]
                top = await asyncio.wait_for(reranker.top_k(query, passages, k=12), timeout=20.0)
                ranked = [pool[i] for i, _ in top]
                picks = ref_scoped + [c for c in ranked if c not in ref_scoped]
                logger.info("v4_scope_rerank_used", index=slide.index, pool=len(pool), kept=len(picks[:6]))
                return picks[:6]
            else:
                if reranker.load_failed() is None:
                    asyncio.create_task(reranker.warm(timeout_s=120.0))
                    logger.debug("v4_scope_rerank_warming", index=slide.index)
                else:
                    logger.debug("v4_scope_rerank_disabled", reason=reranker.load_failed())
        except Exception as e:
            logger.debug(
                "v4_scope_rerank_unavailable",
                error_type=type(e).__name__,
                error=str(e) or repr(e),
            )

        # Fallback: keyword overlap
        intent_keywords = slide.intent.lower().split("_") + slide.headline_target.lower().split()
        scored: list[tuple[float, Citation]] = []
        for c in rest:
            text = (c.title + " " + c.snippet).lower()
            score = sum(1 for k in intent_keywords if len(k) > 3 and k in text)
            score += c.source_authority
            scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return ref_scoped + [c for _, c in scored if c not in ref_scoped][: 6 - len(ref_scoped)]

    def _parse_writer_output(self, skel: SlideSkeleton, raw: str | dict[str, Any]) -> GeneratedSlide:
        if isinstance(raw, dict):
            data = raw
        else:
            try:
                data = safe_json_loads(raw, context=f"writer:slide={skel.index}")
            except JSONRepairFailedError:
                logger.warning("v4_writer_json_unrecoverable", index=skel.index, head=raw[:200] if raw else "")
                data = {}

        # Defensive: some models return a list instead of an object.
        if not isinstance(data, dict):
            data = {}

        # Enforce density caps defensively (relaxed: bullets may be more descriptive)
        bullets = [str(b)[:200] for b in (data.get("bullets") or [])][:4]
        bullets = [self._truncate_words(b, 16) for b in bullets]
        headline = self._truncate_words(str(data.get("headline") or skel.headline_target), 10)

        # stat_blocks may arrive as list-of-strings or list-of-dicts depending on model.
        stat_blocks: list[dict[str, str]] = []
        for s in (data.get("stat_blocks") or [])[:4]:
            if isinstance(s, dict):
                stat_blocks.append({
                    "value": str(s.get("value", ""))[:30],
                    "label": str(s.get("label", ""))[:60],
                })
            elif isinstance(s, str) and s.strip():
                # e.g. "$2.4B TAM" -> split into value + label heuristically
                parts = s.strip().split(" ", 1)
                stat_blocks.append({
                    "value": parts[0][:30],
                    "label": (parts[1] if len(parts) > 1 else "")[:60],
                })

        # citations may arrive as list-of-strings (raw urls) or list-of-dicts.
        citations: list[dict[str, str]] = []
        for c in (data.get("citations") or [])[:6]:
            if isinstance(c, dict):
                url_clean = _sanitize_url(str(c.get("url", "")))
                if not url_clean:
                    continue
                citations.append({
                    "url": url_clean,
                    "title": str(c.get("title", ""))[:200],
                })
            elif isinstance(c, str) and c.strip():
                url_clean = _sanitize_url(c)
                if url_clean:
                    citations.append({"url": url_clean, "title": ""})

        gs = GeneratedSlide(
            index=skel.index,
            intent=skel.intent,
            layout=skel.layout_hint,
            headline=headline,
            subheadline=str(data.get("subheadline"))[:200] if data.get("subheadline") else None,
            bullets=bullets,
            body=str(data.get("body"))[:1200] if data.get("body") else None,
            stat_blocks=stat_blocks,
            quote=data.get("quote") if isinstance(data.get("quote"), dict) else None,
            chart=data.get("chart") if isinstance(data.get("chart"), dict) else None,
            table=normalize_table(data.get("table")),
            timeline=normalize_timeline(data.get("timeline")),
            comparison=normalize_comparison(data.get("comparison")),
            diagram=normalize_diagram(data.get("diagram")),
            image_prompt=str(data.get("image_prompt"))[:500] if data.get("image_prompt") else None,
            speaker_notes=str(data.get("speaker_notes"))[:1500] if data.get("speaker_notes") else None,
            citations=citations,
            raw=data,
        )
        # Degeneracy guard — if the writer produced essentially no content
        # (e.g. one bogus {"Team Size": "14"} stat_block with no bullets, no
        # body, no real headline), seed the slide from the planner's
        # skeleton key_points so the slide is still useful. Without this
        # guard, degenerate outputs survive into the critic and skew the
        # deck downward.
        content_signals = (
            len(gs.bullets)
            + len(gs.stat_blocks)
            + (1 if (gs.body or "").strip() else 0)
            + (1 if gs.quote else 0)
            + (1 if gs.chart and (gs.chart.get("data") or []) else 0)
            + (1 if gs.table and (gs.table.get("rows") or []) else 0)
            + (1 if gs.timeline and (gs.timeline.get("events") or []) else 0)
            + (1 if gs.comparison and (gs.comparison.get("columns") or []) else 0)
            + (1 if gs.diagram and (gs.diagram.get("nodes") or []) else 0)
        )
        # Heuristic for "stat is really a single off-topic measure" — e.g.
        # a how_it_works slide whose only stat_block is {"Team Size": "14"}.
        off_topic_stat = False
        if (
            len(gs.stat_blocks) == 1
            and not gs.bullets
            and not (gs.body or "").strip()
            and (skel.intent or "").lower() in {"how_it_works", "solution", "problem", "business_model", "competition", "technology"}
        ):
            sb_label = (gs.stat_blocks[0].get("label") or "").lower()
            # Team-Size / headcount / founded-date stats don't belong on
            # process/solution/problem slides.
            if any(tok in sb_label for tok in ("team size", "headcount", "founded", "year")):
                off_topic_stat = True

        if (content_signals < 2 or off_topic_stat) and skel.key_points:
            seeded = [str(p).strip() for p in skel.key_points if str(p).strip()]
            if seeded:
                gs.bullets = seeded[:4]
            if off_topic_stat:
                # Drop the misleading stat when repopulating from bullets.
                gs.stat_blocks = []
            # FIX: Never use purpose as body fallback - purpose is "pitch_deck", not content
            # If body is empty, try to construct from key_points or leave empty
            if not (gs.body or "").strip():
                # Use key_points joined as body (already seeded above), or use headline as context
                if seeded:
                    gs.body = ". ".join(seeded[:3])[:600]
                # If still no body, leave it empty - don't fallback to purpose
        # v10.3 — deterministic system decision: code vs image vs none
        try:
            decision = decide_visual({
                "intent": gs.intent,
                "layout": gs.layout,
                "visual_cue": skel.visual_cue,
                "headline": gs.headline,
                "subheadline": gs.subheadline,
                "body": gs.body,
                "bullets": gs.bullets,
                "stat_blocks": gs.stat_blocks,
                "quote": gs.quote,
                "chart": gs.chart,
                "table": gs.table,
                "timeline": gs.timeline,
                "comparison": gs.comparison,
                "diagram": gs.diagram,
                "image_prompt": gs.image_prompt,
            })
            gs.render_decision = {
                "modality": decision.modality,
                "reason": decision.reason,
                "code_block": decision.code_block,
                "renderer": decision.suggested_renderer,
            }
        except Exception as e:
            logger.debug("visual_decider_failed", index=skel.index, error=str(e))
        return gs

    @staticmethod
    def _truncate_words(text: str, max_words: int) -> str:
        words = text.split()
        return " ".join(words[:max_words])

    @staticmethod
    def _fallback_slide(skel: SlideSkeleton) -> GeneratedSlide:
        return GeneratedSlide(
            index=skel.index,
            intent=skel.intent,
            layout=skel.layout_hint or "two-column",
            headline=skel.headline_target or skel.intent.replace("_", " ").title(),
            bullets=skel.key_points[:3],
            speaker_notes=skel.purpose,
            rationale=(skel.purpose or "").strip(),
        )
