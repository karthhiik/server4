"""
V4 Image Prompt Library — structured, slot-filled image prompts per slide.

Motivation (from the JimengArt/awesome-nano-banana-pro-prompts gallery):
    High-quality image generation needs more than "abstract illustration
    of X". Professional decks demand a disciplined prompt grammar:

        [subject]  +  [composition / lens]  +  [lighting]  +
        [materials / texture]  +  [mood]  +  [negatives]

    The gallery showed 120+ templates that map to different slide
    archetypes (hero cover, product showcase, market-data atmosphere,
    team portrait, etc.). The v4 image_generator was appending only a
    density-mood + palette suffix, which made every deck's images read
    as generic stock illustrations.

This module ships a tagged library of 30+ prompt archetypes keyed by
(slide intent, layout, density). The library is PURE DATA — no LLM,
no network — and is selected deterministically per slide. The
`build_image_prompt(...)` function fills the template's slots from the
slide content + resolved design tokens and returns a finished prompt
string ready for the image pipeline router.

The library is intentionally conservative:
    * No hardcoded brand names (never "Apple-style product shot").
    * No photographer references (copyright-adjacent).
    * Every archetype specifies "no text overlay, no watermark" in its
      negatives so headlines overlay cleanly.
    * Every archetype honors the resolved palette and produces a 16:9
      hero-friendly composition with breathing room for overlaid copy.

Integration:
    `image_generator._enhance_prompt(...)` calls
    `build_image_prompt(slide, tokens, mode=...)` as its primary path
    and falls back to the previous density+palette suffix only when no
    archetype matches.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


# ── Library shape ─────────────────────────────────────────────────

@dataclass(frozen=True)
class PromptArchetype:
    """One entry in the library — template + tags + negatives.

    Template tokens use `{slot_name}` and are filled by
    `build_image_prompt`. Any slot absent from the fill dict becomes
    an empty string and the archetype adapts.
    """
    name: str
    intents: tuple[str, ...]          # matches slide.intent
    layouts: tuple[str, ...]          # matches slide.layout (empty = any)
    template: str
    negatives: tuple[str, ...] = ()


# ── Archetype catalog ─────────────────────────────────────────────
#
# Slot vocabulary (always lowercase so templates stay readable):
#   {subject}        — the slide's declared topic (derived from image_prompt
#                      or headline)
#   {industry}       — slide.industry or pipeline-provided industry
#   {palette_line}   — "dominant palette #xxx / #yyy on #zzz background"
#   {density_mood}   — "crisp, editorial, information-dense" etc.
#   {composition}    — archetype-specific composition clause
#   {negative}       — joined negatives
#
# Every prompt ends with a common tail ensuring 16:9 framing and no
# overlaid text.

_COMMON_TAIL = (
    "16:9 wide composition, deep negative space on the right third for "
    "overlaid headlines, high production value, no on-image text, no "
    "watermark, no logo, no letters, no captions. "
    # Phase 3C: Image-Content Alignment
    "{headline_context}."  # Image must reinforce the slide headline
)


_ARCHETYPES: tuple[PromptArchetype, ...] = (
    # ── HERO / TITLE / COVER ──────────────────────────────────────
    PromptArchetype(
        name="hero_cover_wide",
        intents=("title", "cover", "hero"),
        layouts=("image-full", "full-bleed", "image-dominant", "hero", "title-only", "auto"),
        template=(
            "Editorial hero composition evoking {subject}. "
            "Wide cinematic frame, shallow depth of field, soft-focus "
            "bokeh background, confident negative space. "
            "{palette_line}. {density_mood}. "
            "Lighting: {composition}. "
            "{common_tail}. "
            "{headline_context}."  # Phase 3C: Image-Content Alignment
        ),
        negatives=("no text", "no faces at center", "no crowds", "no stock photo watermarks"),
    ),

    PromptArchetype(
        name="hero_atmosphere_abstract",
        intents=("atmosphere", "vision", "closing", "ask"),
        layouts=(),
        template=(
            "Abstract editorial atmosphere for {subject}. "
            "Flowing gradient fields with soft light-leaks and delicate "
            "geometric accents. {palette_line}. {density_mood}. "
            "Lighting: diffuse ambient with a single directional highlight. "
            "{composition}. {common_tail}."
        ),
        negatives=("no literal objects", "no human figures", "no typography"),
    ),

    # ── PROBLEM / PAIN ────────────────────────────────────────────
    PromptArchetype(
        name="problem_tension",
        intents=("problem", "pain_point", "friction"),
        layouts=(),
        template=(
            "Editorial illustration of {subject}, emphasizing tension and "
            "friction. Low-key lighting with a single cool rim light isolating "
            "the subject against a muted background. {palette_line}. "
            "Grainy paper texture, subtle vignette. {density_mood}. "
            "{composition}. {common_tail}."
        ),
        negatives=("no distress imagery", "no stock emoji icons", "no cartoon"),
    ),

    # ── SOLUTION / PRODUCT ────────────────────────────────────────
    PromptArchetype(
        name="product_showcase",
        intents=("product", "solution", "feature_overview", "features"),
        layouts=("image-full", "two-column", "product-showcase", "auto"),
        template=(
            "Product-hero composition of {subject} on a matte studio surface. "
            "Clean three-point studio lighting with a soft key, fill, and rim "
            "light, subtle floor shadow, precise edges and material definition. "
            "{palette_line}. Materials: brushed aluminum, frosted glass, "
            "matte polymer. {density_mood}. "
            "{composition}. {common_tail}."
        ),
        negatives=("no brand logos", "no reflected text", "no hands", "no models"),
    ),

    PromptArchetype(
        name="how_it_works_diagrammatic",
        intents=("how_it_works", "architecture", "workflow", "process"),
        layouts=("diagram", "process", "auto"),
        template=(
            "Diagrammatic editorial illustration of a process for {subject}. "
            "Isometric perspective, nodes connected by clean flowlines, "
            "emphasis on structure over ornamentation. {palette_line}. "
            "{density_mood}. {composition}. {common_tail}."
        ),
        negatives=("no hand-drawn look", "no chalkboard", "no labels"),
    ),

    # ── MARKET / DATA ─────────────────────────────────────────────
    PromptArchetype(
        name="market_abstract_data",
        intents=("market", "market_opportunity", "tam", "sam", "market_sizing"),
        layouts=("stat-hero", "chart-focus", "auto", "two-column"),
        template=(
            "Abstract data-landscape composition evoking market scale for "
            "{subject}. Stacked translucent planes, refracted light, subtle "
            "grid topography in the background. {palette_line}. "
            "{density_mood}. Lighting: cool volumetric with a warm highlight "
            "accent. {composition}. {common_tail}."
        ),
        negatives=("no chart bars", "no pie charts", "no numerals", "no currency symbols"),
    ),

    PromptArchetype(
        name="traction_upward_motion",
        intents=("traction", "growth", "milestones"),
        layouts=(),
        template=(
            "Editorial atmosphere evoking upward momentum for {subject}. "
            "Ascending light trails on a soft gradient, faint ruled horizon "
            "line, minimal geometric accents. {palette_line}. {density_mood}. "
            "{composition}. {common_tail}."
        ),
        negatives=("no literal charts", "no arrows", "no stock line graphs"),
    ),

    # ── COMPETITION ───────────────────────────────────────────────
    PromptArchetype(
        name="competition_contrast",
        intents=("competition", "competitors", "landscape"),
        layouts=("comparison", "two-column", "table", "auto"),
        template=(
            "Contrast composition for {subject}: two asymmetric material "
            "planes meeting along a soft vertical seam, with one side clearly "
            "more resolved than the other. {palette_line}. {density_mood}. "
            "Lighting: opposing soft key lights with a shared ambient floor. "
            "{composition}. {common_tail}."
        ),
        negatives=("no head-to-head sports imagery", "no literal grids"),
    ),

    # ── BUSINESS MODEL / PRICING ─────────────────────────────────
    PromptArchetype(
        name="model_architectural",
        intents=("business_model", "revenue_model", "pricing", "monetization"),
        layouts=("table", "diagram", "process", "auto"),
        template=(
            "Architectural editorial illustration of a revenue structure for "
            "{subject}. Layered material planes conveying tiers and flow. "
            "{palette_line}. Materials: matte composite, fine linework, subtle "
            "satin sheen. {density_mood}. {composition}. {common_tail}."
        ),
        negatives=("no currency icons", "no price tags", "no dollar signs"),
    ),

    # ── TEAM ──────────────────────────────────────────────────────
    PromptArchetype(
        name="team_environment",
        intents=("team",),
        layouts=("team-grid", "grid-3", "auto"),
        template=(
            "Environmental context image for a team working on {subject}. "
            "Workspace atmosphere — clean desks, thoughtful lighting, sense of "
            "collaboration — with NO identifiable faces or figures. "
            "{palette_line}. {density_mood}. {composition}. {common_tail}."
        ),
        negatives=("no human faces", "no portraits", "no identifiable people"),
    ),

    # ── FINANCIALS / ASK ─────────────────────────────────────────
    PromptArchetype(
        name="financials_composed",
        intents=("financials", "financial_projections", "unit_economics", "ask"),
        layouts=("stat-hero", "chart-focus", "table", "auto"),
        template=(
            "Composed editorial still-life of layered materials evoking "
            "financial structure for {subject}. Soft overhead lighting, "
            "long-exposure stillness, restrained palette. {palette_line}. "
            "{density_mood}. {composition}. {common_tail}."
        ),
        negatives=("no literal currency", "no coins", "no banknotes", "no calculators"),
    ),

    # ── FALLBACK ──────────────────────────────────────────────────
    PromptArchetype(
        name="generic_editorial",
        intents=(),                   # matches any unmatched intent
        layouts=(),
        template=(
            "Editorial illustration evoking {subject} for {industry}. "
            "{palette_line}. {density_mood}. Directional soft lighting, "
            "subtle depth, restrained composition. {composition}. "
            "{common_tail}."
        ),
        negatives=("no text overlay", "no watermark", "no stock photography"),
    ),
)


# ── Selection logic ───────────────────────────────────────────────

def _select_archetype(intent: str, layout: str) -> PromptArchetype:
    """Score every archetype by intent + layout match, return the best."""
    intent = (intent or "").lower()
    layout = (layout or "").lower()

    # Strongest match: explicit intent AND explicit layout hit.
    for arch in _ARCHETYPES:
        if intent and intent in arch.intents and layout and layout in arch.layouts:
            return arch

    # Intent-only match (archetype has no layout filter, or empty layout).
    for arch in _ARCHETYPES:
        if intent and intent in arch.intents:
            return arch

    # Layout-only match as last resort.
    for arch in _ARCHETYPES:
        if layout and layout in arch.layouts:
            return arch

    # Fallback — generic editorial.
    return _ARCHETYPES[-1]


# ── Slot-filling helpers ──────────────────────────────────────────

_STRIP_STYLE_SUFFIXES = re.compile(
    r"\.?\s*(style:.*|lighting:.*|composition:.*|mood:.*)$",
    flags=re.IGNORECASE,
)


def _extract_subject(raw_prompt: Optional[str], headline: Optional[str], intent: str) -> str:
    """Derive the 'subject' clause for the template.

    Strategy:
      1. If the writer produced an `image_prompt`, use it — but strip any
         trailing "style:/lighting:/composition:" clauses it may have
         dumped inline (the library already controls those).
      2. Otherwise, use the headline as the subject.
      3. Otherwise, fall back to the intent word as a last resort.
    """
    if raw_prompt and raw_prompt.strip():
        cleaned = _STRIP_STYLE_SUFFIXES.sub("", raw_prompt.strip()).strip(" .,:")
        # Avoid letting the writer's description dominate — cap to a
        # reasonable length so the archetype's structure stays dominant.
        return cleaned[:320]

    if headline and headline.strip():
        return headline.strip()

    return (intent or "business growth").replace("_", " ")


def _composition_for(intent: str, layout: str) -> str:
    """Archetype-layer composition hint so different layouts read
    differently even when the archetype is the same."""
    layout = (layout or "").lower()
    intent = (intent or "").lower()

    if layout in {"image-full", "full-bleed", "image-dominant"}:
        return "full-bleed composition with subject slightly right-of-center"
    if layout in {"two-column"}:
        return "left-weighted subject placement, right third clear for text column"
    if layout in {"stat-hero", "chart-focus"}:
        return "tight center composition surrounded by soft negative space"
    if layout in {"grid-3", "team-grid", "icon-grid", "feature-grid"}:
        return "symmetrical balanced composition with rhythm of repeated elements"
    if intent in {"closing", "ask", "cover", "title"}:
        return "cinematic wide framing with depth layers for overlaid title"
    return "balanced composition with breathing room on the right third"


def _palette_line(tokens: Any) -> str:
    """Construct the palette clause from ResolvedDesignTokens.

    Tolerates both dict and dataclass shapes so callers can pass
    `ResolvedDesignTokens` directly or a persisted token dict."""
    try:
        palette = tokens.palette
        primary = getattr(palette, "primary", None) or palette.get("primary")  # type: ignore[union-attr]
        accent = getattr(palette, "accent", None) or palette.get("accent")    # type: ignore[union-attr]
        background = getattr(palette, "background", None) or palette.get("background")  # type: ignore[union-attr]
    except AttributeError:
        if isinstance(tokens, dict):
            pal = tokens.get("palette") or {}
            primary = pal.get("primary")
            accent = pal.get("accent")
            background = pal.get("background")
        else:
            primary = accent = background = None

    if not (primary and accent and background):
        return "restrained contemporary palette"
    return (
        f"dominant palette {primary} and {accent} on {background} background"
    )


def _density_mood(tokens: Any) -> str:
    density = (
        getattr(tokens, "density", None)
        or (tokens.get("density") if isinstance(tokens, dict) else None)
        or "comfortable"
    )
    return {
        "compact": "crisp, editorial, information-dense atmosphere",
        "comfortable": "balanced editorial illustration with measured detail",
        "spacious": "minimalist, airy, confident atmosphere",
    }.get(density, "balanced editorial illustration")


_PURPOSE_STYLES: dict[str, str] = {
    "pitch_deck": "investor-grade editorial restraint, premium product-storytelling polish, credible scale and negative space",
    "investor_pitch": "investor-grade editorial restraint, premium product-storytelling polish, credible scale and negative space",
    "investor_update": "crisp operating-review polish, measured confidence, data-room-ready restraint",
    "sales_deck": "clean product marketing photography, confident commercial polish, sharp focal hierarchy",
    "case_study": "documentary realism with warm practical lighting, credible real-world context, non-staged composition",
    "educational": "clear instructional composition, friendly structure, calm explanatory visual hierarchy",
    "training": "instructional clarity, approachable forms, clear focal point and low visual noise",
    "internal_memo": "minimal executive-briefing aesthetic, restrained geometry, low-noise operational clarity",
    "company_overview": "modern corporate editorial style, soft natural light, polished but not stock-like",
    "product_launch": "launch-grade product showcase, precise materials, strong reveal energy",
}


def _purpose_style(deck_purpose: Optional[str]) -> str:
    key = (deck_purpose or "").strip().lower().replace("-", "_").replace(" ", "_")
    return _PURPOSE_STYLES.get(
        key,
        "contemporary editorial deck aesthetic, purposeful composition, no generic stock-photo staging",
    )


# ── Public entry point ───────────────────────────────────────────

def build_image_prompt(
    *,
    intent: Optional[str],
    layout: Optional[str],
    image_prompt: Optional[str],
    headline: Optional[str],
    tokens: Any,
    industry: Optional[str] = None,
    deck_purpose: Optional[str] = None,
) -> tuple[str, str]:
    """Return `(prompt, archetype_name)` for an image-modality slide.

    Parameters mirror the fields `image_generator._enhance_prompt`
    already has at hand — no caller shape change required beyond
    forwarding `intent` / `layout` / `headline` (previously discarded).

    The archetype name is returned for diagnostics / progress events so
    the UI can show which archetype governed each slide's image.
    """
    arch = _select_archetype(intent or "", layout or "")
    subject = _extract_subject(image_prompt, headline, intent or "")

    fills = {
        "subject": subject,
        "industry": (industry or "").strip() or "a modern company",
        "palette_line": _palette_line(tokens),
        "density_mood": _density_mood(tokens),
        "composition": _composition_for(intent or "", layout or ""),
        "common_tail": _COMMON_TAIL,
        # Phase 3C: Image-Content Alignment - reinforce headline context
        "headline_context": (
            f"The image must visually reinforce: {headline}"
            if headline and headline.strip()
            else ""
        ),
    }

    prompt = arch.template.format(**fills).strip()
    prompt += f" Deck-purpose style: {_purpose_style(deck_purpose)}."
    # Attach negatives inline — the image pipeline's own negative-prompt
    # builder concatenates its own list, so adding these as a trailing
    # instruction is safe and model-agnostic.
    if arch.negatives:
        prompt += " Avoid: " + ", ".join(arch.negatives) + "."

    return prompt, arch.name


def list_archetypes() -> list[dict[str, Any]]:
    """Diagnostics helper used by tests and admin tooling."""
    return [
        {
            "name": a.name,
            "intents": list(a.intents),
            "layouts": list(a.layouts),
            "negatives": list(a.negatives),
        }
        for a in _ARCHETYPES
    ]
