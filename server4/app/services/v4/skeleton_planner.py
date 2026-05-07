# V4 Skeleton Planner - Skeleton-of-Thought generation.
#
# Per `slide-generation-architecture` skill:
#   Phase 1 (Skeleton, ~3s): ONE planner call produces the full deck skeleton.
#   Each slide skeleton has intent, purpose, density target, layout hint, key points.
#
# Per `pitch-deck-research` skill: 
#   Premium uses canonical YC pitch-deck structure as a strong default scaffold, 
#   augmented or trimmed by user-selected slide types. 
#   Standard auto-detects intent and produces a coherent deck without user input. 
#
# Premium model: Kimi/Kimi 2.6 planning chain - long-form reasoning. 
# Standard model: fast template/JSON chain with a hard real-time fallback. 

import asyncio
import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

import structlog

from app.services.llm.model_router import ModelRouter, TaskType
from app.services.v4.research_collector import ResearchPacket
from app.services.v4.json_repair import safe_json_loads, JSONRepairFailedError
from app.services.v4.llm_safe import safe_complete
from app.services.v4 import content_rules
from app.services.v4.schema_guard import validate_planner_slides
from app.services.v4.quality_metrics import gate_decision, record_quality_event, QualityEvent
from app.config import settings

logger = structlog.get_logger(__name__)

# Plan 05 - standard mode is the real-time tier. Premium keeps its deeper
# planner budget; standard gets one fast LLM window plus a
# deterministic fallback.
STANDARD_SKELETON_TIMEOUT_S = 7.0
STANDARD_SKELETON_PRIMARY_TIMEOUT_S = 5.0 
STANDARD_SKELETON_FALLBACK_TIMEOUT_S = 3.0 

# Canonical investor deck when company-specific facts are actually available. 
CANONICAL_COMPANY_PITCH_STRUCTURE: list[dict[str, str]] = [
    {"intent": "title",       "purpose": "Hook the viewer with company name + one-line value prop"},
    {"intent": "problem",     "purpose": "Define the painful, urgent, valuable problem"},
    {"intent": "solution",    "purpose": "Show how we solve it - concretely, not abstractly"},
    {"intent": "unique_advantage", "purpose": "Your unique value proposition that investors remember - one clear differentiator"},
    {"intent": "how_it_works", "purpose": "Explain the mechanism in 3 steps or less"},
    {"intent": "market",        "purpose": "Quantify TAM/SAM/SOM with credible sources"},
    {"intent": "traction",    "purpose": "Prove momentum with metrics that compound"},
    {"intent": "business_model", "purpose": "Show how we make money and why margins are good"},
    {"intent": "competition",   "purpose": "Map competitors and our durable advantage"},
    {"intent": "team",         "purpose": "Why us - founder/market fit and key strengths"},
    {"intent": "finances",     "purpose": "Forward projections grounded in unit economics - ONLY use numbers from evidence"},
    {"intent": "ask",          "purpose": "What we want and what it unlocks"},
]

# Investor concept deck when the prompt lacks company-specific founder, 
# traction, or financial data. This avoids inventing numbers or bios. 
CANONICAL_CONCEPT_PITCH_STRUCTURE: list[dict[str, str]] = [
    {"intent": "title",         "purpose": "Hook the viewer with company name + one-line value prop"},
    {"intent": "problem",       "purpose": "Define the painful, urgent, valuable problem"},
    {"intent": "solution",      "purpose": "Show how the product solves the problem concretely"},
    {"intent": "unique_advantage", "purpose": "One clear differentiator that investors remember - unique value proposition"},
    {"intent": "usp",              "purpose": "One sentence that sets us apart from ALL competitors"},
    {"intent": "how_it_works",  "purpose": "Demonstrate the workflow in 3 steps or less"},
    {"intent": "market",        "purpose": "Quantify the market if evidence exists; otherwise explain demand drivers"},
    {"intent": "business_model", "purpose": "Explain pricing, buyer, and revenue logic without fake metrics"},
    {"intent": "competition",   "purpose": "Show alternatives and our differentiated position"},
    {"intent": "go_to_market",  "purpose": "Show how we will acquire customers efficiently"},
    {"intent": "technology",    "purpose": "Explain the product's moat, automation engine, or defensibility"},
    {"intent": "ask",           "purpose": "Explain what capital or strategic support unlocks next milestones"},
]

# Backward-compatible alias used in older code paths. 
CANONICAL_PITCH_STRUCTURE = CANONICAL_COMPANY_PITCH_STRUCTURE

_INTENT_ALIASES: dict[str, str] = {
    "introduction": "title",
    "cover": "title",
    "opening": "title",
    "identify_problem": "problem",
    "challenges": "problem",
    "present_solution": "solution",
    "product": "solution",
    "product_demo": "how_it_works",
    "workflow": "how_it_works",
    "process": "how_it_works",
    "market_opportunity": "market",
    "validation": "traction",
    "milestones": "traction",
    "business": "business_model",
    "revenue_model": "business_model",
    "competitive_landscape": "competition",
    "competitors": "competition",
    "founding_team": "team",
    "funding_ask": "ask",
    "investment": "ask",
    "funding": "ask",
    "call_to_action": "ask",
    "technology_moat": "technology",
    "moat": "technology",
    "gtm": "go_to_market",
}

_LAYOUT_ALIASES: dict[str, str] = {
    # legacy aliases
    "title_image": "image-full",
    "bullet_points": "bullet-points",
    "image_bullets": "two-column",
    "stats_image": "stat-hero",
    "call_to_action": "title-only",
    # free-form strings seen in real standard-mode LLM output 
    # snap to the canonical layout vocabulary so the writer can map
    # to a structured block. 
    "logo-image": "title-only",
    "logo_image": "title-only",
    "text-bullets": "bullet-points",
    "text_bullets": "bullet-points",
    "bullets-with-icons": "grid-3",
    "bullets_with_icons": "grid-3",
    "image-centric": "image-full",
    "image_centric": "image-full",
    "text-based": "two-column",
    "text_based": "two-column",
    "visuals": "image-full",
    "visual": "image-full",
    "step-by-step": "timeline",
    "step_by_step": "timeline",
    "step-by-step-guide": "timeline",
    "roadmap": "timeline",
    "journey": "timeline",
    "milestones": "timeline",
    "phases": "timeline",
    "quote-with-background-image": "quote",
    "quote_with_background_image": "quote",
    "testimonial": "quote",
    "competitive-matrix": "comparison",
    "competitive_matrix": "comparison",
    "matrix": "comparison",
    "vs": "comparison",
    "versus": "comparison",
    "side-by-side": "comparison",
    "side_by_side": "comparison",
    "revenue-projection": "chart-focus",
    "revenue_projection": "chart-focus",
    "stats-graph": "chart-focus",
    "stats_graph": "chart-focus",
    "chart": "chart-focus",
    "graph": "chart-focus",
    "data": "chart-focus",
    "timeline-image": "timeline",
    "timeline_image": "timeline",
    "diagram-image": "diagram",
    "diagram_image": "diagram",
    "architecture": "diagram",
    "flow": "diagram",
    "flow-chart": "diagram",
    "flow_chart": "diagram",
    "flowchart": "diagram",
    "team-photos": "two-column",
    "team_photos": "two-column",
    "team-grid": "two-column",
    "team_grid": "two-column",
    "call-to-action-button": "title-only",
    "cta": "title-only",
    "big-numbers": "stat-hero",
    "big_numbers": "stat-hero",
    "kpi": "stat-hero",
    "metrics": "stat-hero",
    "3-column": "grid-3",
    "3_column": "grid-3",
    "three-column": "grid-3",
    "three_column": "grid-3",
    "columns": "grid-3",
    "grid": "grid-3",
    "cards": "grid-3",
    "feature-grid": "grid-3",
    "feature_grid": "grid-3",
    "features": "grid-3",
    "text-heavy": "bullet-points",
    "text_heavy": "bullet-points",
    "text-with-image": "two-column",
    "text_with_image": "two-column",
    "text-summary": "bullet-points",
    "text_summary": "bullet-points",
    "summary": "bullet-points",
    "overview": "bullet-points",
    "conclusion": "title-only",
    "closing": "title-only",
    "intro": "title-only",
    "introduction": "title-only",
}

_CANONICAL_LAYOUTS: frozenset[str] = frozenset({
    "title-only",
    "two-column",
    "stat-hero",
    "grid-3",
    "chart-focus",
    "image-full",
    "quote",
    "comparison",
    "timeline",
    "table",
    "diagram",
    "process",
    "bullet-points",
    "auto",
})


@dataclass
class SlideSkeleton:
    index: int
    intent: str                    # e.g. "problem", "market", "feature_overview"
    purpose: str                   # one-sentence reason this slide exists
    headline_target: str           # draft headline (writer will refine)
    key_points: list[str] = field(default_factory=list)
    density_target: str = "medium" # "minimal" | "low" | "medium" | "high"
    layout_hint: str = "auto"      # "title-only" | "two-column" | "stat-hero" | "grid-3" | etc.
    evidence_refs: list[str] = field(default_factory=list)  # citation URLs the writer should use
    visual_cue: Optional[str] = None  # e.g. "chart", "image", "icon-grid"
    # Founder replan - optional traceability fields (backward compatible). 
    # These flow to the writer so it knows when to rewrite a borderline
    # planner-emitted headline vs. use it verbatim. 
    thesis_sentence: str = ""                 # 1-sentence argument this slide must make
    generic_risk: str = "low"                 # "low" | "high" - template-detector verdict
    required_quant_signals: list[str] = field(default_factory=list)  # hints for writer
    trace_inputs: list[str] = field(default_factory=list)             # citation fingerprints


@dataclass
class DeckSkeleton:
    project_id: str
    title: str
    narrative_arc: str             # "investor_pitch" | "training" | "report" | etc. 
    slides: list[SlideSkeleton]
    raw_planner_output: dict[str, Any] = field(default_factory=dict)


class SkeletonPlanner:
    """Skeleton-of-Thought planner for V4 pipeline."""

    def __init__(self, model_tier: str = "standard"):
        self.model_tier = model_tier
        self.model_router = ModelRouter()
        self._fallback_max_slides = 10

    async def plan(self, project_id: str, user_query: str, research: ResearchPacket, 
             slide_count: Optional[int] = None, narrative_arc: str = "investor_pitch") -> DeckSkeleton:
        """Run the 2-phase planner (premium) or 1-shot (standard)."""
        if self.model_tier == "premium":
            return await self._plan_premium(project_id, user_query, research, slide_count, narrative_arc)
        else:
            return await self._plan_standard(project_id, user_query, research, slide_count, narrative_arc)

    async def _plan_premium(self, project_id: str, user_query: str, 
                          research: ResearchPacket, slide_count: Optional[int], 
                          narrative_arc: str) -> DeckSkeleton:
        """Premium: 3-slide skeleton with full reasoning chain."""
        # Build the prompt
        system = self._build_system_prompt(research, narrative_arc)
        user = self._build_user_prompt(user_query, research, slide_count, narrative_arc)
        
        try:
            raw = await safe_complete(
                router=self.model_router,
                primary_task=TaskType.OUTLINE_PLANNING,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                timeout_s=STANDARD_SKELETON_TIMEOUT_S,
            )
            slides_data = self._parse_planner_output(raw, research, slide_count)
            return self._build_deck(project_id, slides_data, narrative_arc, research)
        except Exception as e:
            logger.warning("Premium planner failed, falling back", error=str(e))
            return self._fallback_skeleton(project_id, user_query, research, slide_count, narrative_arc)

    async def _plan_standard(self, project_id: str, user_query: str, 
                           research: ResearchPacket, slide_count: Optional[int], 
                           narrative_arc: str) -> DeckSkeleton:
        """Standard: fast 1-shot with JSON-mode fallback."""
        # Try primary model
        try:
            system = self._build_system_prompt(research, narrative_arc)
            user = self._build_user_prompt(user_query, research, slide_count, narrative_arc)
            raw = await safe_complete(
                router=self.model_router,
                primary_task=TaskType.OUTLINE_PLANNING,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                timeout_s=STANDARD_SKELETON_PRIMARY_TIMEOUT_S,
            )
            slides_data = self._parse_planner_output(raw, research, slide_count)
            return self._build_deck(project_id, slides_data, narrative_arc, research)
        except Exception as e:
            logger.warning("Primary model failed, trying fallback", error=str(e))
            try:
                raw = await safe_complete(
                    router=self.model_router,
                    primary_task=TaskType.OUTLINE_PLANNING,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    timeout_s=STANDARD_SKELETON_FALLBACK_TIMEOUT_S,
                )
                slides_data = self._parse_planner_output(raw, research, slide_count)
                return self._build_deck(project_id, slides_data, narrative_arc, research)
            except Exception as e2:
                logger.warning("Fallback also failed, using deterministic skeleton", error=str(e2))
                return self._fallback_skeleton(project_id, user_query, research, slide_count, narrative_arc)

    def _build_system_prompt(self, research: ResearchPacket, narrative_arc: str) -> str:
        """Build the system prompt for the planner."""
        lines = [
            "You are the Strategist for an elite presentation generator.",
            "You produce a complete deck skeleton - NOT slide content yet, just structure.",
            "",
            "THESIS-FIRST RULE (most important):",
            "- Every `headline_target` must be A THESIS, not a category label.",
            "- A thesis only makes sense for THIS company with THESE specific numbers.",
            "- If a headline could be pasted onto any other startup's deck, REWRITE it.",
            "- Good examples: \"$4.2B SMB Payments, Growing 18% YoY\", \"Close Invoices In 90 Seconds\",",
            "  \"3x Quarterly Revenue Growth, Zero Churn\", \"Built Payments At Stripe And Square\".",
            "- Bad examples (NEVER output): \"Market Opportunity\", \"Our Business Model\",",
            "  \"How It Works\", \"The Team\", \"Competitive Landscape\",",
            "  \"Join Our Journey\", \"Early Validation Signals\", \"What Capital Unlocks\".",
            "",
            "Also for every slide, emit a `thesis_sentence` (one full sentence) that spells",
            "out the argument the slide must make. The writer uses this to stay on-thesis.",
            "",
            "Hard rules (from pitch deck research):",
            "- Respect the EXACT requested slide count. Never return more or fewer slides.",
            "- Every slide must pass the \"So What\" filter: it must move the narrative forward.",
            "- Density caps: headlines 3-8 words, key points 2-4 per slide, 3-10 words each.",
            "- No two adjacent slides may share the same intent or layout_hint.",
            "- Every claim worth proving must reference an `evidence_ref` URL from the research.",
            "- The deck must follow the requested narrative arc end-to-end.",
            "- Never invent company-specific facts. If the research lacks founder names, traction",
            "  metrics, revenue, funding amount, or valuation, choose a concept-investor slide",
            "  that can be supported honestly instead of fabricating numbers or bios.",
            "- For market/traction/financials/competition slides, include `required_quant_signals`",
            "  - a list of c1-2 specific numbers or metric labels the writer MUST include.",
            "- **Ratan Tata's \"Numbers Don't Lie\" rule**: For market/traction/financials slides, ",
            "      ONLY include numbers from research evidence. If no evidence exists, state 'Data to be validated' rather than inventing numbers.",
            "- Pick layout_hint from this vocabulary based on the slide's content shape:",
            "  title-only, two-column, stat-hero, grid-3, chart-focus, image-full, quote, comparison, timeling, diagram, process.",
            "  Use `table` for any tabular comparison of 3+ attributes across 3+ entities.",
            "  Use `timeline` for sequential events (history, roadmap, funding rounds).",
            "  Use `comparison` for parallel option/before-after evaluation (NOT for tabular data).",
            "  Use `diagram` for architectures, processes with branching, network maps.",
            "",
            "Return ONLY valid JSON:",
            "{",
            "  \"title\": \"<deck title>\",",
            "  \"narrative_arc\": \"<arc>\",",
            "  \"slides\": [",
            "    {\"index\": 0, \"intent\": \"<intent>\", \"layout_hint\": \"<layout>\", \"headline_target\": \"<3-8 word SPECIFIC thesis - see rules above>\",",
            "      \"key_points\": [\"concrete point>\", \"...\"], \"density_target\": <2-4>, \"visual_cue\": \"<image-intent>\",",
            "      \"thesis_sentence\": \"one full sentence that spells out what this slide must prove>\",",
            "      \"generic_risk\": \"<high|medium|low>\",  \"required_quant_signals\": [\"<specific number or metric label>\", ...],",
            "      \"evidence_refs\": [\"<url>\", ...]}",
            "  ]",
            "}",
        ]
        
        # Phase 3C: Image-Content Alignment
        lines.extend([
            "",
            "For image generation, each slide MUST have a relevant image that reinforces the headline.",
            "When building image prompts, include the slide's headline and key_points as context.",
            "The image must visually reinforce: {headline}",
            "Example: For a market slide with headline \"The $4.2B SMB Payments Market\", ",
            "  the image prompt should reference \"financial growth, payment technology\" not generic \"business scene\".",
        ])
        
        return "\n".join(lines)

    def _build_user_prompt(self, user_query: str, research: ResearchPacket, 
                           slide_count: Optional[int], narrative_arc: str) -> str:
        """Build the user prompt with research context."""
        company = research.company_name or "the company"
        lines = [
            f"User request: {user_query}",
            f"Company: {company}",
            f"Narrative arc: {narrative_arc}",
            f"Target slide count: {slide_count or 'follow structure'}",
            "",
            "Research citations:",
        ]
        for cite in research.top_citations(5):
            lines.append(f"  - {cite.title}: {cite.snippet}")
        lines.append("")
        lines.append("Generate the deck skeleton now.")
        return "\n".join(lines)

    def _parse_planner_output(self, raw: str, research: ResearchPacket, 
                               slide_count: Optional[int]) -> list[dict]:
        """Parse and validate the planner's JSON output."""
        try:
            data = safe_json_loads(raw)
            if not isinstance(data, dict):
                raise ValueError("Planner output is not a dict")
            slides = data.get("slides", [])
            if not isinstance(slides, list):
                raise ValueError("Slides is not a list")
            # Validate with schema guard
            validate_planner_slides(slides)
            # Cap to requested count
            if slide_count and len(slides) > slide_count:
                slides = slides[:slide_count]
            return slides
        except (JSONRepairFailedError, ValueError) as e:
            logger.error("Failed to parse planner output", error=str(e))
            raise

    def _build_deck(self, project_id: str, slides_data: list[dict], 
                     narrative_arc: str, research: ResearchPacket) -> DeckSkeleton:
        """Build a DeckSkeleton from parsed data."""
        # Get canonical structure for this narrative arc
        canonical = CANONICAL_PITCH_STRUCTURE
        if narrative_arc == "investor_pitch":
            canonical = CANONICAL_COMPANY_PITCH_STRUCTURE
        
        # Map intents to canonical structure
        intent_layout: dict[str, str] = {}
        for item in canonical:
            intent = item["intent"]
            intent_layout[intent] = item.get("layout_hint", "two-column")
        
        # Build slides
        slides = []
        for i, slide_data in enumerate(slides_data):
            intent = slide_data.get("intent", "unknown")
            # Map aliases
            intent = _INTENT_ALIASES.get(intent, intent)
            
            slide = SlideSkeleton(
                index=i,
                intent=intent,
                purpose=f"Cover {intent.replace('_', ' ')} for this pitch",
                headline_target=slide_data.get("headline_target", f"Slide {i+1}"),
                key_points=slide_data.get("key_points", []),
                density_target=slide_data.get("density_target", "medium"),
                layout_hint=intent_layout.get(intent, slide_data.get("layout_hint", "two-column")),
                evidence_refs=slide_data.get("evidence_refs", []),
                visual_cue=slide_data.get("visual_cue"),
                thesis_sentence=slide_data.get("thesis_sentence", ""),
                generic_risk=slide_data.get("generic_risk", "medium"),
                required_quant_signals=slide_data.get("required_quant_signals", []),
                trace_inputs=slide_data.get("trace_inputs", []),
            )
            slides.append(slide)
        
        # Build title
        raw_title = slides_data[0].get("title") if slides_data else None
        title = self._clean_title_from_query(user_query, research.company_name if research else None)
        
        return DeckSkeleton(
            project_id=project_id,
            title=title[:120],
            narrative_arc=narrative_arc or "custom",
            slides=slides,
            raw_planner_output={"slides": slides_data},
        )

    def _clean_title_from_query(self, user_query: str, company: Optional[str]) -> str:
        """Extract a clean deck title from a free-form user query."""
        q = (user_query or "").replace("\r", "\n")
        # Strip leading label lines
        kept_lines: list[str] = []
        for line in q.split("\n"):
            line = line.strip()
            if not line:
                continue
            if re.match(r"^(topic|audience|goal|context|purpose|brief|ask|stage)\s*:", line, re.I):
                continue
            kept_lines.append(line)
        body = " ".join(kept_lines) if kept_lines else q.replace("\n", " ")
        body = re.sub(r"\s+", " ", body).strip()
        
        if company:
            return f"{company[:60]} Investor Pitch"
        
        # First sentence, or first 80 chars on word boundary
        first_sentence = re.split(r"(?<=[.!?])\s+", body, maxsplit=1)[0] if body else ""
        title = first_sentence or body
        if len(title) <= 80:
            return title or "Investor Pitch Deck"
        cut = title[:80].rsplit(" ", 1)[0]
        return (cut or title[:80]).rstrip(" ,;:-") + "..."

    def _seed_key_points(self, intent: str, user_query: str, research: ResearchPacket) -> list[str]:
        """Seed 2-3 domain-aware key_points for a fallback slide."""
        intent_lower = (intent or "").lower()
        query = (user_query or "").strip()
        cites = list((research.citations or []) + (research.news_citations or []))
        
        # 1. Mine research for intent-relevant snippets
        intent_tokens = {
            "problem": ("problem", "challenge", "pain", "gap", "issue", "struggle"),
            "solution": ("solution", "solve", "platform", "product", "technology", "enable"),
            "market": ("market", "tam", "sam", "cagr", "growth", "opportunity", "demand"),
            "traction": ("customers", "revenue", "growth", "arr", "mrr", "users", "adoption"),
            "team": ("founder", "ceo", "cto", "team", "leadership", "experience"),
            "business_model": ("revenue", "pricing", "subscription", "saas", "margin", "model"),
            "competition": ("competitor", "alternative", "vs", "versus", "differentiator", "moat"),
            "technology": ("technology", "algorithm", "patent", "ip", "defensibility", "moat"),
            "ask": ("raise", "fund", "capital", "round", "investment", "milestone"),
            "how_it_works": ("workflow", "step", "process", "pipeline", "stage", "how"),
            "go_to_market": ("channel", "sales", "acquisition", "marketing", "partner", "distribution"),
        }.get(intent_lower, tuple())
        
        seeds: list[str] = []
        for cite in cites[:20]:
            blob = f"{cite.title or ''} {cite.snippet or ''}"
            blob_low = blob.lower()
            if intent_tokens and not any(tok in blob_low for tok in intent_tokens):
                continue
            # Take a clean sentence
            sent = re.split(r"(?<=[.!?])\s+", blob.strip())[0]
            sent = re.sub(r"\s+", " ", sent).strip()
            if 20 <= len(sent) <= 160 and sent not in seeds:
                seeds.append(sent)
            if len(seeds) >= 3:
                break
        
        # 2. Fall back to user-query-derived statement
        if not seeds and query:
            tokens = [t.strip() for t in re.split(r"[.\\n]", query) if len(t.strip()) > 15]
            seeds.extend(tokens[:3])
        
        # 3. Intent-generic prompts (never finance-boilerplate)
        if not seeds:
            generic = {
                "problem": [f"The core problem this addresses for {query[:60]}", "Who feels this pain most acutely", "Why existing solutions fall short"],
                "solution": [f"How the product solves {query[:60]}", "What makes the approach differentiated", "What users can do now that they couldn't before"],
                "market": ["Where demand is concentrated today", "What drives sustained growth", "Why timing is right now"],
                "traction": ["Key milestones achieved to date", "What growth looks like", "Early customer signals"],
                "team": ["Founder-market fit", "Complementary domain expertise", "Key hires and advisors"],
                "business_model": ["How revenue is earned", "Unit economics outlook", "Path to margin expansion"],
                "competition": ["Primary alternatives today", "Our durable differentiation", "Why customers switch"],
                "technology": ["Core technical capability", "Defensibility and moat", "Roadmap of capability"],
                "ask": ["What we're raising", "What capital unlocks next", "Key milestones to next round"],
                "how_it_works": ["Step one - capture", "Step two - process", "Step three - act"],
                "go_to_market": ["Primary acquisition channel", "Pricing and packaging", "Scaling go-to-market"],
            }
            seeds = generic.get(intent_lower, [f"Key point about {intent_lower.replace('_', ' ')}"])
        
        return [s[:140] for s in seeds[:3]]

    def _fallback_skeleton(self, project_id: str, user_query: str, 
                          research: ResearchPacket, slide_count: Optional[int] = None, 
                          narrative_arc: str = "investor_pitch") -> DeckSkeleton:
        """Deterministic last-resort skeleton if all LLM calls fail."""
        cap = (
            slide_count
            if slide_count and slide_count > 0
            else self._fallback_max_slides
        )
        cap = min(cap, self._fallback_max_slides)
        # Define intents based on narrative_arc
        if narrative_arc == "investor_pitch":
            intents = [item["intent"] for item in CANONICAL_COMPANY_PITCH_STRUCTURE]
        else:
            intents = [item["intent"] for item in CANONICAL_CONCEPT_PITCH_STRUCTURE]
        intents = intents[:cap]
        
        # Intent-appropriate layout map (vs previous round-robin)
        _intent_layout: dict[str, str] = {
            "title":          "title-only",
            "problem":        "two-column",
            "solution":       "two-column",
            "how_it_works":   "diagram",
            "market":         "stat-hero",
            "traction":       "stat-hero",
            "business_model": "two-column",
            "competition":    "comparison",
            "team":           "team-grid",
            "technology":     "two-column",
            "finances":      "chart-focus",
            "go_to_market":   "two-column",
            "ask":            "stat-hero",
            "vision":         "image-full",
        }
        
        slides: list[SlideSkeleton] = []
        for i, intent in enumerate(intents):
            fallback_headline = self._default_headline_for_intent(
                intent, research.company_name if research else None
            )
            slides.append(SlideSkeleton(
                index=i,
                intent=intent,
                purpose=f"Cover {intent.replace('_', ' ')} for this pitch",
                headline_target=fallback_headline,
                key_points=self._seed_key_points(intent, user_query, research),
                density_target="medium",
                layout_hint=_intent_layout.get(intent, "two-column"),
                evidence_refs=[c.url for c in research.top_citations(2)],
                generic_risk="high",
            ))
        
        company = (research.company_name or "").strip() if research else ""
        title = self._clean_title_from_query(user_query, company or None)
        return DeckSkeleton(
            project_id=project_id,
            title=title[:120],
            # Real narrative arc name - never the string "fallback"
            narrative_arc=narrative_arc or "custom",
            slides=slides,
        )

    def _default_headline_for_intent(self, intent: str, company: Optional[str]) -> str:
        """Generate a default headline for an intent."""
        company_str = f" at {company}" if company else ""
        defaults = {
            "title":          f"{company or 'Your Company'} Investor Pitch",
            "problem":        f"Defining the Pain{company_str}",
            "solution":       f"How We Solve It{company_str}",
            "unique_advantage": f"Our Unique Value Proposition",
            "usp":             f"What Sets Us Apart",
            "how_it_works":   f"How It Works in 3 Steps",
            "market":         f"Quantifying the Market Opportunity",
            "traction":       f"Proving Momentum",
            "business_model": f"How We Make Money",
            "competition":    f"Our Competitive Advantage",
            "team":           f"Why This Team Wins",
            "finances":      f"Forward Projections",
            "ask":            f"What We're Raising",
            "go_to_market":   f"Go-To-Market Strategy",
            "technology":     f"Technology Moat",
        }
        return defaults.get(intent, f"Cover {intent.replace('_', ' ')}")
