"""V4 slide → CompiledSlide adapter (template-bound v1).

This module is the bridge between the V4 content pipeline's
`GeneratedSlide` dataclass and the sandbox's `CompiledSlide` wire
shape declared in `lliveupdatedstreaming/src/lib/sandboxProtocol.ts`.

Design decisions:
- Template-bound ONLY. We never emit freeform JSX in v1 — every slide
  maps to one of the 10 kit components with a JSON `/* PROPS */`
  fence consumed by `SlideRuntime.parsePropsFromJsx()`.
- Zero LLM calls. This is a pure data transform. Deterministic,
  testable, fast (<5ms per slide).
- All kit component names and prop shapes MUST match the kit modules
  under `lliveupdatedstreaming/sandbox/src/kit/`. Any mismatch here
  surfaces as a "slide compile error" in the sandbox frame.
- Intent → kit mapping chooses the BEST visual for the slide's
  dominant content. If a slide has both bullets and a chart, we
  prefer ChartBlock (data beats text).
- Imagery: we pass `imageUrl` through when the image pipeline has
  already resolved it. If the image is still generating, we emit an
  image-less variant and the frontend patches it in when the
  `slide_image_ready` event arrives.

Security: `_js_string(value)` JSON-encodes every embedded string so
a malicious headline like `</script><script>alert(1)` cannot escape
the PROPS block. The sandbox consumes PROPS via `JSON.parse`, not
`eval`.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Optional

from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4 import content_rules
from app.services.v4.content_sanitizer import sanitize_display_text
from app.services.v4.visual_element_validator import ensure_valid_visual_element
from app.services.v4.animation_ir import build_animation_ir
from app.services.v4.html_transformer import build_html_css_js
from app.services.v4.engine_transformer import build_engine
from app.services.v4.motion_spec import (
    build_layer_metadata,
    build_motion_spec,
    build_render_qa_plan,
)
from app.services.v4.slide_intelligence import build_slide_intelligence_spec
from app.services.v4.reveal_legacy_transformer import build_reveal_legacy
from app.services.v4.layout.intent_engine import LayoutCandidate, select_layout
from app.services.v4.layout.rhythm_planner import plan_layout_rhythm
from app.services.v4.slide_uniqueness_engine import apply_uniqueness_pass
from app.services.v4.layout.slide_composition import build_composition_plan
from app.services.v4.creative_storyboard import (
    SlideCreativeDirection,
    build_creative_storyboard,
    merge_direction_into_layout_params,
)
from app.services.v4.validators import validate_compiled_slide
from app.services.v4.viz_engine import icon_for, select_chart_type
from app.services.v4.asset_positioning import AssetPositioningAgent
from app.config import settings

# ── v3-final Phase 1 — multi-target artifacts schema ────────────────
# Day 1 lands the wire-shape; only `artifacts.kit_jsx` is populated in
# this commit (from existing real data — never dummy values). The
# other three slots stay `None` until their owning phase ships:
#     html_css_js  → Phase 4  (HTML transformer, Day 6-7)
#     engine       → Phase 5  (Custom Presentation Engine, Day 9-10)
#     reveal_legacy→ Phase 5  (Reveal-legacy section, Day 9-10)
# `quality_score` stays `None` until Phase 4.5 (Day 8) populates it.
# `enrichment`     stays `None` until Phase 7.5 (Day 15).
# Keeping `None` (not empty stubs) makes "is this artifact ready?"
# trivially detectable in downstream callers — no truthiness traps.

# Bumped on every recompile of a slide; used as the cache key in the
# frontend useCompiledDeck hook (Phase 7) and as the artifact-freshness
# token for the upcoming hot-swap WS event (Phase 6).
_ARTIFACT_SCHEMA_VERSION = 2

# ── Type Scale Enforcement ───────────────────────────────────────────

# Base font sizes in pixels for each typographic level
_TYPE_SCALE_BASE = {
    "display": 72.0,
    "h1": 56.0,
    "h2": 48.0,
    "h3": 36.0,
    "body": 18.0,
    "caption": 14.0,
}

# Minimum font sizes (WCAG AA compliance)
_MIN_FONT_SIZES = {
    "body": 16.0,  # 16px minimum for normal text
    "caption": 14.0,  # 14px minimum for caption text
    "h3": 24.0,  # 24px minimum for headings
}


def _repair_short_text_fragment(text: Any) -> str:
    """Repair known model truncation fragments before visual props render."""
    repaired = " ".join(str(text or "").split())
    replacements = [
        (r"\bshutting down the flee(?:t+)?\b", "shutting down the fleet"),
        (r"\bown deployment riskoyment risk\b", "own deployment risk"),
        (r"\bown depl\b", "own deployment risk"),
        (r"\bsecurity and operatio\b", "security and operational value"),
        (r"\bsecurity and op\b", "security and operational value"),
        (
            r"\bmeasurable reliability and latency proofity and latency proof\b",
            "measurable reliability and latency proof",
        ),
        (r"\bmeasurable reliabil\b", "measurable reliability and latency proof"),
    ]
    for pattern, good in replacements:
        repaired = re.sub(pattern, good, repaired, flags=re.IGNORECASE)
    repaired = re.sub(
        r"\bcompromised nodes can be isolated without shutting down the fleet\b",
        "Compromised nodes isolate without fleet shutdown",
        repaired,
        flags=re.IGNORECASE,
    )
    return repaired


def _enforce_type_scale(
    props: dict[str, Any],
    design_tokens: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Enforce type scale based on design tokens.
    
    Adjusts font sizes in props to match the design token type scale,
    ensuring WCAG compliance and visual hierarchy.
    
    Args:
        props: Kit component props (may contain fontSize, headingFontSize, etc.)
        design_tokens: Design tokens with type_scale information
    
    Returns:
        Props with enforced font sizes
    """
    if not design_tokens:
        return props
    
    # Extract type scale from design tokens
    type_scale = design_tokens.get("type_scale", {})
    if not type_scale:
        return props
    
    # Get scale multipliers (default to 1.0 if not specified)
    display_scale = type_scale.get("display", 1.0)
    h1_scale = type_scale.get("h1", 1.0)
    h2_scale = type_scale.get("h2", 1.0)
    h3_scale = type_scale.get("h3", 1.0)
    body_scale = type_scale.get("body", 1.0)
    caption_scale = type_scale.get("caption", 1.0)
    
    # Apply scale to props based on font size keys
    if "fontSize" in props:
        base_size = props["fontSize"]
        if isinstance(base_size, (int, float)):
            # Determine which level this is based on size
            if base_size >= 56:
                props["fontSize"] = max(_MIN_FONT_SIZES["h3"], _TYPE_SCALE_BASE["display"] * display_scale)
            elif base_size >= 48:
                props["fontSize"] = max(_MIN_FONT_SIZES["h3"], _TYPE_SCALE_BASE["h1"] * h1_scale)
            elif base_size >= 36:
                props["fontSize"] = max(_MIN_FONT_SIZES["h3"], _TYPE_SCALE_BASE["h2"] * h2_scale)
            elif base_size >= 24:
                props["fontSize"] = max(_MIN_FONT_SIZES["h3"], _TYPE_SCALE_BASE["h3"] * h3_scale)
            elif base_size >= 16:
                props["fontSize"] = max(_MIN_FONT_SIZES["body"], _TYPE_SCALE_BASE["body"] * body_scale)
            else:
                props["fontSize"] = max(_MIN_FONT_SIZES["caption"], _TYPE_SCALE_BASE["caption"] * caption_scale)
    
    # Apply scale to specific heading font sizes if present
    if "headingFontSize" in props:
        base_size = props["headingFontSize"]
        if isinstance(base_size, (int, float)):
            props["headingFontSize"] = max(_MIN_FONT_SIZES["h3"], _TYPE_SCALE_BASE["h1"] * h1_scale)
    
    if "subheadingFontSize" in props:
        base_size = props["subheadingFontSize"]
        if isinstance(base_size, (int, float)):
            props["subheadingFontSize"] = max(_MIN_FONT_SIZES["h3"], _TYPE_SCALE_BASE["h2"] * h2_scale)
    
    if "bodyFontSize" in props:
        base_size = props["bodyFontSize"]
        if isinstance(base_size, (int, float)):
            props["bodyFontSize"] = max(_MIN_FONT_SIZES["body"], _TYPE_SCALE_BASE["body"] * body_scale)
    
    if "captionFontSize" in props:
        base_size = props["captionFontSize"]
        if isinstance(base_size, (int, float)):
            props["captionFontSize"] = max(_MIN_FONT_SIZES["caption"], _TYPE_SCALE_BASE["caption"] * caption_scale)
    
    # Log type scale enforcement
    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        f"type_scale_enforced: display={display_scale:.2f}, h1={h1_scale:.2f}, body={body_scale:.2f}"
    )
    
    return props


# ── Kit component names (MUST stay in sync with
#     lliveupdatedstreaming/sandbox/src/kit/index.ts)  ──────────────

KIT_TITLE_HERO = "TitleHero"
KIT_STAT_HERO = "StatHero"
KIT_CHART_BLOCK = "ChartBlock"
KIT_TIMELINE_BLOCK = "TimelineBlock"
KIT_COMPARISON_BLOCK = "ComparisonBlock"
KIT_FEATURE_GRID = "FeatureGrid"
KIT_TEAM_GRID = "TeamGrid"
KIT_QUOTE_BLOCK = "QuoteBlock"
KIT_FULL_BLEED_IMAGE = "FullBleedImage"
KIT_DIAGRAM_BLOCK = "DiagramBlock"
KIT_BENTO_GRID = "BentoGrid"
KIT_SPLIT_CONTENT = "SplitContent"
KIT_COVER_SLIDE = "CoverSlide"
KIT_SOCIAL_PROOF = "SocialProof"
KIT_TESTIMONIAL_CARD = "TestimonialCard"
KIT_QUOTE_HIGHLIGHT = "QuoteHighlight"
KIT_APP_MOCKUP = "AppMockup"
KIT_BEFORE_AFTER = "BeforeAfter"
KIT_PRICING_TABLE = "PricingTable"
KIT_ROADMAP = "Roadmap"
KIT_LOGO_MARQUEE = "LogoMarquee"
KIT_PROCESS_FLOW = "ProcessFlow"
KIT_DATA_TABLE = "DataTable"
KIT_PROBLEM_SOLUTION = "ProblemSolution"
KIT_METRICS_DASHBOARD = "MetricsDashboard"
KIT_TEAM_MEMBER_STRIP = "TeamMemberStrip"
KIT_VALUE_PROP_GRID = "ValuePropGrid"
KIT_CINEMATIC_HERO = "CinematicHero"
KIT_GLASS_CARD = "GlassCard"
KIT_EDITORIAL_IMAGE = "EditorialImage"
KIT_DUOTONE_HERO = "DuotoneHero"
KIT_FLOATING_STAT = "FloatingStat"
KIT_SPLIT_OVERLAP = "SplitOverlap"

_KIT_SET = {
    KIT_TITLE_HERO,
    KIT_STAT_HERO,
    KIT_CHART_BLOCK,
    KIT_TIMELINE_BLOCK,
    KIT_COMPARISON_BLOCK,
    KIT_FEATURE_GRID,
    KIT_TEAM_GRID,
    KIT_QUOTE_BLOCK,
    KIT_FULL_BLEED_IMAGE,
    KIT_DIAGRAM_BLOCK,
    KIT_BENTO_GRID,
    KIT_SPLIT_CONTENT,
    KIT_COVER_SLIDE,
    KIT_SOCIAL_PROOF,
    KIT_TESTIMONIAL_CARD,
    KIT_QUOTE_HIGHLIGHT,
    KIT_APP_MOCKUP,
    KIT_BEFORE_AFTER,
    KIT_PRICING_TABLE,
    KIT_ROADMAP,
    KIT_LOGO_MARQUEE,
    KIT_PROCESS_FLOW,
    KIT_DATA_TABLE,
    KIT_PROBLEM_SOLUTION,
    KIT_METRICS_DASHBOARD,
    KIT_TEAM_MEMBER_STRIP,
    KIT_VALUE_PROP_GRID,
    KIT_CINEMATIC_HERO,
    KIT_GLASS_CARD,
    KIT_EDITORIAL_IMAGE,
    KIT_DUOTONE_HERO,
    KIT_FLOATING_STAT,
    KIT_SPLIT_OVERLAP,
}


# ── Intent canonicalization ────────────────────────────────────────
# Real writer output uses free-form intent verbs in standard mode
# ("Introduction", "Introduce", "Explore", "Inform", "Engage",
# "Conclude") and canonical YC slugs in premium mode ("title",
# "problem", "market", "team"). The dispatcher only understands YC
# slugs, so free-form intents fall through to FeatureGrid — which is
# the exact template-stamp failure mode. Canonicalize here so both
# tiers reach the right kit.

_INTENT_ALIASES: dict[str, str] = {
    # title / cover
    "introduction": "title",
    "introductions": "title",
    "introduce": "title",
    "intro": "title",
    "opener": "title",
    "cover": "title",
    "welcome": "title",
    "title": "title",
    # closing family
    "conclude": "closing",
    "conclusion": "closing",
    "closing": "closing",
    "wrap-up": "closing",
    "wrap up": "closing",
    "thanks": "thanks",
    "thank you": "thanks",
    "thank_you": "thanks",
    "thank-you": "thanks",
    "thankyou": "thanks",
    "contact": "thanks",
    "ask": "ask",
    "call-to-action": "ask",
    "call to action": "ask",
    # team
    "team": "team",
    "the team": "team",
    "founders": "team",
    "leadership": "team",
    # metrics / traction
    "traction": "traction",
    "metrics": "metrics",
    "kpi": "metrics",
    "kpis": "metrics",
    "highlight": "metrics",
    "highlights": "metrics",
}


def _canonical_intent(raw: Optional[str]) -> str:
    if not raw:
        return ""
    key = raw.strip().lower()
    return _INTENT_ALIASES.get(key, key)


# ── Public API ────────────────────────────────────────────────────


def compile_slides(
    *,
    slides: list[GeneratedSlide],
    image_urls: Optional[Mapping[int, str]] = None,
    deck_title: Optional[str] = None,
    company_icon_url: Optional[str] = None,
    design_tokens: Optional[dict[str, Any]] = None,
    template_id: Optional[str] = None,
    effects: Optional[Mapping[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Turn a list of GeneratedSlide → list of CompiledSlide dicts.

    `image_urls` is an optional map of slide_index → resolved image
    URL. Slides whose index is not present in the map are compiled
    without an image (and will be patched later by the frontend when
    `slide_image_ready` arrives over the SSE stream).
    """
    image_urls = image_urls or {}
    clean_deck_title = _display_title(deck_title)
    compiled: list[dict[str, Any]] = []
    selected_layouts: list[str] = []
    deck_total = len(slides)
    deck_purpose = getattr(slides[0], "purpose", "") if slides else ""
    creative_storyboard: dict[int, SlideCreativeDirection] = {}
    try:
        creative_storyboard = build_creative_storyboard(
            slides=slides,
            deck_title=clean_deck_title,
            deck_purpose=deck_purpose,
            design_tokens=design_tokens,
            template_id=template_id,
            image_urls=image_urls,
        )
    except Exception as exc:  # noqa: BLE001
        import structlog as _sl
        _sl.get_logger(__name__).warning(
            "creative_storyboard_failed", error=str(exc)[:200]
        )
    rhythm_plan: dict[int, LayoutCandidate] = {}
    if settings.ENABLE_LAYOUT_RHYTHM_GATE and deck_total > 1:
        try:
            rhythm_plan = plan_layout_rhythm(
                slides=slides,
                deck_purpose=deck_purpose,
                image_urls=image_urls,
                creative_directions={
                    idx: direction.to_dict()
                    for idx, direction in creative_storyboard.items()
                },
            )
        except Exception:
            rhythm_plan = {}
    for deck_index, s in enumerate(slides):
        image_url = image_urls.get(s.index)
        effective_company_icon_url = None if getattr(s, "company_icon_hidden", False) else (
            s.company_icon_url or company_icon_url
        )
        compiled_slide = _compile_one(
            slide=s,
            image_url=image_url,
            deck_title=clean_deck_title,
            company_icon_url=effective_company_icon_url,
            deck_index=deck_index,
            deck_total=deck_total,
            previous_layouts=tuple(selected_layouts),
            layout_candidate=rhythm_plan.get(s.index),
            creative_direction=creative_storyboard.get(s.index),
            design_tokens=design_tokens,
            template_id=template_id,
            effects=effects,
        )
        layout_key = (compiled_slide.get("layout_intent") or {}).get("key")
        if isinstance(layout_key, str) and layout_key:
            selected_layouts.append(layout_key)
        compiled.append(compiled_slide)
    # Final pass: apply the deck-level uniqueness signature so every
    # deck (and every slide within a deck) has a distinct visual rhythm.
    # Pure cosmetic — content is never touched. Idempotent so re-running
    # the pipeline doesn't drift the output.
    try:
        deck_seed = (
            getattr(slides[0], "project_id", None)
            or getattr(slides[0], "deck_id", None)
            or clean_deck_title
            or ""
        ) if slides else ""
        industry = ""
        if design_tokens and isinstance(design_tokens, dict):
            industry = (
                str(design_tokens.get("industry") or "")
                or str(design_tokens.get("category") or "")
            )
        apply_uniqueness_pass(
            compiled,
            deck_seed=str(deck_seed)[:120],
            deck_purpose=str(deck_purpose),
            industry=industry,
        )
    except Exception as exc:  # noqa: BLE001
        # Cosmetic only — never block compilation.
        import structlog as _sl
        _sl.get_logger(__name__).warning(
            "uniqueness_pass_failed", error=str(exc)[:200]
        )
    return compiled


_TITLE_LABEL_LINE = re.compile(
    r"^\s*(topic|audience|goal|context|purpose|brief|ask|stage)\s*:",
    re.IGNORECASE,
)


def _display_title(raw: Optional[str]) -> Optional[str]:
    """Return a display-friendly deck title.

    - Strip leading ``Topic:/Audience:/Goal:`` label lines — those describe
      the brief, not the deck.
    - Collapse internal newlines/whitespace.
    - Cap at 120 chars on a word boundary (no mid-word ellipsis).
    """
    if not raw:
        return raw
    text = str(raw).replace("\r", "\n")
    kept: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or _TITLE_LABEL_LINE.match(stripped):
            continue
        kept.append(stripped)
    cleaned = " ".join(kept) if kept else " ".join(text.split())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,;:-")
    if not cleaned:
        return None
    if len(cleaned) <= 120:
        return cleaned
    cut = cleaned[:120].rsplit(" ", 1)[0]
    return (cut or cleaned[:120]).rstrip(" ,;:-") + "…"


def compile_slide(
    *,
    slide: GeneratedSlide,
    image_url: Optional[str] = None,
    deck_title: Optional[str] = None,
    company_icon_url: Optional[str] = None,
    design_tokens: Optional[dict[str, Any]] = None,
    template_id: Optional[str] = None,
    effects: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Single-slide convenience wrapper (used by incremental patches)."""
    return _compile_one(
        slide=slide,
        image_url=image_url,
        deck_title=deck_title,
        company_icon_url=None if getattr(slide, "company_icon_hidden", False) else (
            slide.company_icon_url or company_icon_url
        ),
        design_tokens=design_tokens,
        template_id=template_id,
        effects=effects,
    )


# ── Internal ──────────────────────────────────────────────────────


def _source_slide_contract(slide: GeneratedSlide) -> dict[str, Any]:
    """Serializable source-of-truth payload for export fidelity."""
    contract = {
        "index": slide.index,
        "intent": slide.intent or "",
        "layout": slide.layout or "",
        "headline": slide.headline or "",
        "subheadline": slide.subheadline or "",
        "body": slide.body or "",
        "bullets": list(slide.bullets or []),
        "stat_blocks": list(slide.stat_blocks or []),
        "quote": slide.quote or None,
        "chart": slide.chart or None,
        "table": slide.table or None,
        "timeline": slide.timeline or None,
        "comparison": slide.comparison or None,
        "diagram": slide.diagram or None,
        "image_prompt": slide.image_prompt or "",
        "image_url": slide.image_url or "",
        "image_source": slide.image_source or "",
        "image_position": slide.image_position or "",
        "image_intent": slide.image_intent or "",
        "speaker_notes": slide.speaker_notes or "",
        "citations": list(slide.citations or []),
        "links": list(slide.links or []),
        "team_members": list(slide.team_members or []),
        "company_icon_url": slide.company_icon_url or "",
        "company_icon_hidden": bool(slide.company_icon_hidden),
        "company_icon_position": slide.company_icon_position or "",
        "company_icon_opacity": slide.company_icon_opacity,
        "background_color": slide.background_color or "",
        "background_gradient": slide.background_gradient or "",
        "icons": list(slide.icons or []),
        "layout_params": dict(slide.layout_params or {}),
        "requires_user_input": bool(slide.requires_user_input),
        "user_input_kind": slide.user_input_kind or "",
        "user_input_reason": slide.user_input_reason or "",
    }
    return json.loads(json.dumps(contract, ensure_ascii=False))


def _compile_one(
    *,
    slide: GeneratedSlide,
    image_url: Optional[str],
    deck_title: Optional[str],
    company_icon_url: Optional[str],
    deck_index: int = 0,
    deck_total: int = 1,
    previous_layouts: tuple[str, ...] = (),
    layout_candidate: Optional[LayoutCandidate] = None,
    creative_direction: Optional[SlideCreativeDirection] = None,
    design_tokens: Optional[dict[str, Any]] = None,
    template_id: Optional[str] = None,
    effects: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    if layout_candidate is None:
        layout_candidate = select_layout(
            slide=slide,
            deck_purpose=getattr(slide, "purpose", "") or "",
            deck_index=deck_index,
            deck_total=deck_total,
            previous_layouts=previous_layouts,
            image_available=bool(image_url),
            template_id=template_id,
        )
    kit, props = _choose_kit_and_props(
        slide=slide,
        image_url=image_url,
        deck_title=deck_title,
        company_icon_url=company_icon_url,
        layout_candidate=layout_candidate,
        design_tokens=design_tokens,
    )
    assert kit in _KIT_SET, f"internal: kit {kit!r} not in registry"
    
    # ── Design Director integration: pass rich visual treatment ──
    # The Design Director (LLM stage) sets slide.layout_params with
    # visual treatment decisions. We pass these through as layoutParams
    # so every kit component can use them for spacing, alignment,
    # decorative elements, and animation hints.
    if isinstance(props, dict):
        props.setdefault("intent", slide.intent or "")
        dd_params = getattr(slide, "layout_params", None)
        merged_layout_params = merge_direction_into_layout_params(
            dd_params if isinstance(dd_params, dict) else None,
            creative_direction,
        )
        if merged_layout_params:
            props["layoutParams"] = merged_layout_params
    
    # Apply type scale enforcement based on design tokens
    if isinstance(props, dict):
        props = _enforce_type_scale(props, design_tokens)
        props = _clean_render_props(props)

    # Apply asset positioning for slides with images
    if image_url and isinstance(props, dict):
        try:
            agent = AssetPositioningAgent(vision_enabled=False)
            # Map slide layout to asset positioning layout archetype
            layout_map = {
                "image-full": "hero_with_subtitle",
                "image-left": "content_with_image_left",
                "image-right": "content_with_image_right",
                "title-only": "cover_slide",
                "hero": "hero_with_subtitle",
                "cover": "cover_slide",
            }
            slide_layout = slide.layout or "auto"
            asset_layout = layout_map.get(slide_layout, slide_layout)
            if asset_layout not in agent._LAYOUT_FOCALS:
                asset_layout = "hero_with_subtitle"
            
            positioned = agent.position_image(
                image_url=image_url,
                slide_layout=asset_layout,
                content_density=getattr(slide, "density_target", "medium"),
            )
            # Merge positioning props into kit props
            props.update(positioned.to_props())
        except Exception:
            # Silently fall back on positioning errors
            pass

    # Add company logo watermark (non-intrusive, bottom-right corner)
    # This watermark doesn't affect slide content or elements
    if company_icon_url and isinstance(props, dict):
        position = getattr(slide, "company_icon_position", None) or "bottom-right"
        opacity = getattr(slide, "company_icon_opacity", None)
        if not isinstance(opacity, (int, float)):
            opacity = 0.15
        opacity = max(0.05, min(0.6, float(opacity)))
        props["watermark"] = {
            "imageUrl": company_icon_url,
            "position": position,
            "opacity": opacity,
            "size": "small",
        }

    pending_image = _image_pending(slide=slide, image_url=image_url)
    if pending_image:
        props["pendingImage"] = True
        image_intent = getattr(slide, "image_intent", None) or (slide.render_decision or {}).get("renderer")
        if image_intent:
            props["imageIntent"] = str(image_intent)

    # Uniformly attach grounding sources so every kit can render a
    # "Sources" footer. Only include when the slide actually has citations;
    # otherwise leave the prop absent (kits treat missing sources as hidden).
    sources = _sources_from_slide(slide)
    if sources:
        props["sources"] = sources
    links = _links_from_slide(slide, sources=sources)
    if links:
        props["links"] = links
        if _canonical_intent(slide.intent) in {"thanks", "ask", "closing"}:
            cta = next((link for link in links if link.get("target") == "button"), links[0])
            props["cta"] = {"label": cta.get("label") or "Open link", "href": cta.get("url")}
            props["ctaLabel"] = cta.get("label") or "Open link"
            props["ctaUrl"] = cta.get("url")

    slide_id = f"slide-{slide.index:03d}"
    jsx = _render_jsx(kit=kit, props=props)

    # Phase 3 (Day 4-5) — unified AnimationIR feeds all four targets.
    # Built deterministically from the legacy animation_plan; stored
    # both at the top level (legacy back-compat) AND on every artifact
    # blob so transformers don't need to re-derive it.
    animation_plan = _default_animation_plan(
        intent=slide.intent,
        layout=slide.layout or "",
        kit=kit,
        effects=effects,
    )
    animation_ir = build_animation_ir(animation_plan)

    # Phase 1 — populate artifacts.kit_jsx from real generation output.
    # The other three artifact slots stay None until their owning phase
    # ships (see header comment for the schedule).
    kit_jsx_artifact = {
        "source": jsx,
        "kit_component": kit,
        "layout_intent": {
            **layout_candidate.to_dict(),
            "key": layout_candidate.key,
            "resolved_kit": kit,
        },
        # Deep-copy props so downstream mutation (e.g. image patching)
        # does not corrupt the cached artifact.
        "props_json": json.loads(json.dumps(props, ensure_ascii=False)),
        # 12-char SHA1 prefix is enough to disambiguate cache entries
        # without bloating the wire payload.
        "fingerprint": hashlib.sha1(jsx.encode("utf-8")).hexdigest()[:12],
    }
    source_slide = _source_slide_contract(slide)
    if creative_direction:
        source_slide["creative_direction"] = creative_direction.to_dict()
        source_slide["layout_params"] = merge_direction_into_layout_params(
            source_slide.get("layout_params") if isinstance(source_slide.get("layout_params"), dict) else None,
            creative_direction,
        )
    kit_jsx_artifact["source_slide"] = source_slide

    composition_plan = build_composition_plan(
        kit_component=kit,
        props=props,
        layout_key=layout_candidate.key,
        density=layout_candidate.features.density,
    ).to_dict()

    # Phase 4 (Day 6-7) — HTML/CSS/JS transformer artifact.
    # Phase 5 (Day 9-10) — Custom engine artifact (T1 preview ops).
    engine_artifact = build_engine(
        kit=kit,
        props=props,
        animation_ir=animation_ir,
        design_system=None,
        slide_id=slide_id,
    )
    layer_metadata = build_layer_metadata(
        slide_id=slide_id,
        kit=kit,
        engine_artifact=engine_artifact,
        animation_ir=animation_ir,
    )
    slide_motion_spec = getattr(slide, "motion_spec", None)
    motion_spec = (
        json.loads(json.dumps(slide_motion_spec, ensure_ascii=False))
        if isinstance(slide_motion_spec, dict) and not effects
        else build_motion_spec(
            intent=slide.intent,
            layout=slide.layout or "",
            kit=kit,
            animation_plan=animation_plan,
            animation_ir=animation_ir,
            layer_metadata=layer_metadata,
            effects=effects,
        )
    )
    render_qa_plan = build_render_qa_plan(
        motion_spec=motion_spec,
        layer_metadata=layer_metadata,
    )
    interaction_spec = build_slide_intelligence_spec(
        slide_id=slide_id,
        slide_index=slide.index,
        intent=slide.intent,
        layout=slide.layout or "",
        kit=kit,
        props=props,
        layer_metadata=layer_metadata,
        motion_spec=motion_spec,
        design_tokens=design_tokens,
        template_id=template_id,
    )
    kit_jsx_artifact["motion_spec"] = motion_spec
    kit_jsx_artifact["layer_metadata"] = layer_metadata
    kit_jsx_artifact["interaction_spec"] = interaction_spec

    html_css_js_artifact = build_html_css_js(
        kit=kit,
        props=props,
        animation_ir=animation_ir,
        design_system=None,
        slide_id=slide_id,
        deck_title=deck_title,
        motion_spec=motion_spec,
        layer_metadata=layer_metadata,
    )

    # Phase 5 (Day 9-10) — Reveal-legacy artifact (legacy HTML export).
    if isinstance(html_css_js_artifact, dict):
        html_css_js_artifact["interaction_spec"] = interaction_spec

    reveal_legacy_artifact = build_reveal_legacy(
        kit=kit,
        props=props,
        animation_ir=animation_ir,
        design_system=None,
        slide_id=slide_id,
    )

    compiled_slide = {
        "slide_id": slide_id,
        "slide_index": slide.index,
        "intent": slide.intent or "",
        # Export fidelity contract. The kit props are allowed to optimize
        # presentation mechanics, but they must not become the only source of
        # truth for visible copy; sanitizers/layout adapters can legitimately
        # strip malformed render props. Keeping the original slide payload here
        # lets PDF/PPTX export preserve exactly what the content stage produced.
        "source_slide": source_slide,
        # Legacy mirror — top-level `jsx_source` continues to feed the
        # current sandbox runtime path. Removed in a later release once
        # all consumers read from `artifacts.kit_jsx.source`.
        "jsx_source": jsx,
        "imports": {"@kit": "1.0.0"},
        "assets": _collect_assets(slide=slide, image_url=image_url, company_icon_url=company_icon_url),
        "pending_image": pending_image,
        "layout_intent": {
            **layout_candidate.to_dict(),
            "key": layout_candidate.key,
            "resolved_kit": kit,
        },
        "composition_plan": composition_plan,
        "animation_plan": animation_plan,
        "animation_ir": animation_ir,
        "motion_spec": motion_spec,
        "html_layer_metadata": layer_metadata,
        "render_qa": render_qa_plan,
        "poster_frame": motion_spec.get("poster_frame") if isinstance(motion_spec, dict) else None,
        "interaction_spec": interaction_spec,
        "creative_direction": creative_direction.to_dict() if creative_direction else None,
        "visual_review": _build_visual_review(
            creative_direction=creative_direction,
            layout_candidate=layout_candidate,
            kit=kit,
            props=props,
            composition_plan=composition_plan,
        ),
        "kit_component": kit,
        # ── v3-final Phase 1 schema additions ──────────────────────
        "artifacts": {
            "kit_jsx": kit_jsx_artifact,
            "html_css_js": html_css_js_artifact,  # Phase 4 (Day 6-7) ✓
            "engine": engine_artifact,            # Phase 5 (Day 9-10) ✓
            "reveal_legacy": reveal_legacy_artifact,  # Phase 5 (Day 9-10) ✓
        },
        "artifact_version": _ARTIFACT_SCHEMA_VERSION,
        # FK to the deck-level design system (Phase 2, Day 2). Filled by
        # content_pipeline once Phase 2 lands; until then None is the
        # honest answer.
        "design_system_version": None,
        # Phase 5 Quality Gate (Day 8+).
        "quality_score": _compute_quality_score(
            slide=slide, kit=kit, props=props,
            image_url=image_url or "", animation_ir=animation_ir
        ),
        # Filled by Phase 7.5 RAG enrichment (Day 15) when a slide
        # contains data placeholders that get web-search-resolved.
        "enrichment": None,
        # Per-slide design tokens (augment deck-level tokens for kit-aware rendering)
        "design_tokens": design_tokens,
        # Template ID that guided layout selection for this slide
        "template_id": template_id,
        "template_zone_id": getattr(slide, "template_zone_id", None) or None,
        "template_kit_component": getattr(slide, "template_kit_component", None) or None,
        # CTO CRITICAL: Per-slide background overrides from editor
        "background_color": getattr(slide, "background_color", None) or None,
        "background_gradient": getattr(slide, "background_gradient", None) or None,
    }
    compiled_slide["l1_validation"] = validate_compiled_slide(compiled_slide).to_dict()
    return compiled_slide


# ── Phase 5: Quality Gate Implementation ────────────────────────────

def _compute_quality_score(
    *,
    slide: GeneratedSlide,
    kit: str,
    props: Mapping[str, Any],
    image_url: str,
    animation_ir: Optional[Any] = None,
) -> Optional[float]:
    """Compute quality score (0-10) for compiled slide.
    
    Returns None if quality check is disabled or not applicable.
    Scores:
      - 10.0 = Perfect (all checks pass)
      - 7.0+ = Good (minor issues)
      - 4.0+ = Acceptable (some issues)
      - < 4.0 = Poor (major issues)
    """
    score = 10.0
    issues: list[str] = []

    # 1. Content density check
    headline = (props.get("headline") or "").strip()
    body = (props.get("body_text") or props.get("body") or props.get("subheadline") or "").strip()
    bullets = props.get("bullets") or []
    has_chart = bool(props.get("chartData") or props.get("chart"))
    has_image = bool(image_url)
    structured_content = any(
        bool(props.get(key))
        for key in (
            "features",
            "items",
            "cards",
            "rows",
            "columns",
            "milestones",
            "events",
            "nodes",
            "timeline",
            "stats",
            "statBlocks",
            "table",
            "comparison",
            "diagram",
            "quote",
        )
    )

    if not headline:
        issues.append("MISSING_HEADLINE")
        score -= 2.0
    
    if not body and not bullets and not has_chart and not structured_content:
        issues.append("LOW_CONTENT")
        score -= 1.5
    
    # 2. Image-content alignment (Phase 3C)
    image_intent = getattr(slide, "image_intent", None)
    if image_intent and not has_image:
        issues.append("IMAGE_MISSING_FOR_INTENT")
        score -= 1.5
    
    if has_image and headline:
        # Basic check: image should relate to headline
        headline_lower = headline.lower()
        if any(word in headline_lower for word in ["chart", "graph", "data", "metric"]):
            if "chart" not in image_url.lower() and "graph" not in image_url.lower():
                issues.append("IMAGE_CONTENT_MISMATCH")
                score -= 1.0
    
    # 3. Layout rhythm check (Phase 2B)
    # Check for 16:9 compliance using passed animation_ir
    if animation_ir:
        canvas = (animation_ir if isinstance(animation_ir, dict) else {}).get("canvas", {})
        width = canvas.get("width", 0)
        height = canvas.get("height", 0)
        if width > 0 and height > 0:
            ratio = width / height
            expected = 16.0 / 9.0
            if abs(ratio - expected) > 0.05:  # > 5% deviation
                issues.append("NOT_16_9")
                score -= 1.0
    
    # 4. "Numbers Don't Lie" rule (Phase 3B)
    if image_intent and "stat" in str(image_intent).lower():
        has_numbers = any(char.isdigit() for char in headline)
        if not has_numbers:
            issues.append("NUMBERS_RULE_VIOLATION")
            score -= 1.5
    
    # 5. Design system compliance
    if "fontSize" in props:
        font_size = props["fontSize"]
        if isinstance(font_size, (int, float)) and font_size < 16:
            issues.append("FONT_TOO_SMALL")
            score -= 0.5
    
    # Clamp score
    score = max(0.0, min(10.0, score))
    
    # Log issues for debugging
    if issues:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Quality gate: score={score:.1f}, issues={issues}")
    
    return round(score, 1)


def _build_visual_review(
    *,
    creative_direction: Optional[SlideCreativeDirection],
    layout_candidate: LayoutCandidate,
    kit: str,
    props: Mapping[str, Any],
    composition_plan: Mapping[str, Any],
) -> dict[str, Any]:
    """Attach lightweight visual QA metadata for editor/review surfaces.

    This is diagnostic only; it does not block slide generation and does not
    rewrite content. The frontend can surface it as professional review hints.
    """
    layout_params = props.get("layoutParams") if isinstance(props, Mapping) else None
    if not isinstance(layout_params, Mapping):
        layout_params = {}
    direction = creative_direction.to_dict() if creative_direction else {}
    preferred_kits = set(direction.get("preferred_kits") or [])
    issues: list[str] = []
    strengths: list[str] = []

    if preferred_kits and kit in preferred_kits:
        strengths.append("kit_matches_storyboard")
    elif preferred_kits:
        issues.append("kit_outside_storyboard_preference")

    if layout_params.get("background_style"):
        strengths.append("background_directed")
    else:
        issues.append("background_style_missing")

    if layout_params.get("image_role") and layout_params.get("image_role") != "none":
        strengths.append("image_role_defined")

    if layout_params.get("density_level") == direction.get("density_target"):
        strengths.append("density_matches_storyboard")

    composition_overall = None
    if isinstance(composition_plan, Mapping):
        raw_overall = composition_plan.get("overall")
        if isinstance(raw_overall, (int, float)):
            composition_overall = float(raw_overall)
    if composition_overall is not None:
        if composition_overall >= 0.72:
            strengths.append("composition_pass")
        else:
            issues.append("composition_needs_review")

    return {
        "schema_version": 1,
        "role": direction.get("role"),
        "background_style": layout_params.get("background_style") or direction.get("background_style"),
        "image_role": layout_params.get("image_role") or direction.get("image_role"),
        "density_target": direction.get("density_target"),
        "resolved_kit": kit,
        "layout_key": layout_candidate.key,
        "strengths": strengths,
        "issues": issues,
        "review_reasons": direction.get("review_reasons") or [],
    }





def _render_jsx(*, kit: str, props: Mapping[str, Any]) -> str:
    """Emit the template-bound JSX source.

    Format consumed by `SlideRuntime.parsePropsFromJsx()`:
        /* PROPS
        {...JSON...}
        */
        import { <Kit> } from "@kit";
        export default function Slide(props) { return <Kit {...props} />; }
    """
    # sort_keys → deterministic output; stable output hashing for
    # caching / cache-busting in the sandbox.
    props_json = json.dumps(props, indent=2, sort_keys=True, ensure_ascii=False).replace("*/", "*\\/")
    return (
        "/* PROPS\n"
        f"{props_json}\n"
        "*/\n"
        f'import {{ {kit} }} from "@kit";\n'
        "export default function Slide(props) {\n"
        f"  return <{kit} {{...props}} />;\n"
        "}\n"
    )


def _collect_assets(
    *, slide: GeneratedSlide, image_url: Optional[str], company_icon_url: Optional[str] = None
) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    if image_url:
        assets.append(
            {
                "kind": "image",
                "id": f"slide-{slide.index}-primary",
                "url": image_url,
                "alt": (slide.image_prompt or slide.headline or "")[:200],
            }
        )
    effective_company_icon_url = company_icon_url or slide.company_icon_url
    if effective_company_icon_url:
        assets.append(
            {
                "kind": "logo",
                "id": "company-logo",
                "url": effective_company_icon_url,
                "alt": "company logo",
            }
        )
    return assets


def _image_pending(*, slide: GeneratedSlide, image_url: Optional[str]) -> bool:
    if image_url:
        return False
    decision = getattr(slide, "render_decision", None) or {}
    return str(decision.get("modality") or "").lower() == "image"


def _sources_from_slide(slide: GeneratedSlide, max_n: int = 4) -> list[dict[str, str]]:
    """Compile the slide's grounding citations into the display ``sources`` shape.

    The writer stores citations as ``[{'url': ..., 'title': ...}]`` or raw
    URLs. We normalise, de-duplicate on hostname+path, and clip to ``max_n``.
    Every kit component's props include this array so the sandbox can render
    a small "Sources" footer with clickable links — critical for investor
    trust and for meeting the critic's citation-presence rule.
    """
    raw = getattr(slide, "citations", None) or []
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        url: Optional[str] = None
        title: Optional[str] = None
        if isinstance(item, str):
            url = item
        elif isinstance(item, Mapping):
            url = str(item.get("url") or item.get("href") or "").strip() or None
            title = str(item.get("title") or item.get("name") or "").strip() or None
        if not url:
            continue
        key = re.sub(r"[#?].*$", "", url).lower()
        if key in seen:
            continue
        seen.add(key)
        entry: dict[str, str] = {"url": url[:500]}
        if title:
            entry["title"] = title[:160]
        else:
            # Derive a short label from the hostname when the writer didn't
            # provide a title.
            try:
                host = re.sub(r"^https?://(www\.)?", "", url).split("/", 1)[0]
                if host:
                    entry["title"] = host[:80]
            except Exception:  # noqa: BLE001
                pass
        out.append(entry)
        if len(out) >= max_n:
            break
    return out


def _links_from_slide(
    slide: GeneratedSlide,
    *,
    sources: Optional[list[dict[str, str]]] = None,
    max_n: int = 6,
) -> list[dict[str, str]]:
    """Compile real slide links for preview + export surfaces.

    Links are deterministic: they come from validated writer links and
    citation sources. We do not synthesize URLs from copy that lacks an
    explicit URL field.
    """
    raw_links = getattr(slide, "links", None) or []
    out: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(label: str, url: str, target: str = "text") -> None:
        if not isinstance(url, str):
            return
        clean = url.strip()
        if not clean.lower().startswith(("http://", "https://")):
            return
        if clean in seen:
            return
        seen.add(clean)
        out.append({
            "label": (label or clean).strip()[:120],
            "url": clean[:500],
            "target": target if target in {"text", "button", "image", "source"} else "text",
        })

    for item in raw_links:
        if not isinstance(item, Mapping):
            continue
        add(
            str(item.get("label") or item.get("title") or "Open link"),
            str(item.get("url") or item.get("href") or ""),
            str(item.get("target") or "text").strip().lower(),
        )

    for src in sources or []:
        if isinstance(src, Mapping):
            add(str(src.get("title") or "Source"), str(src.get("url") or ""), "source")

    return out[:max_n]


def _add_visual_element_to_props(slide: GeneratedSlide, props: dict[str, Any]) -> dict[str, Any]:
    """Add visual_element from visual_elements_engine to slide props.

    Args:
        slide: The generated slide
        props: The current props dictionary

    Returns:
        Updated props with visual_element if present
    """
    visual_element = getattr(slide, "visual_element", None)
    if visual_element and isinstance(visual_element, dict):
        props["visual_element"] = visual_element
    return props


def _default_animation_plan(
    *,
    intent: str,
    layout: str = "",
    kit: str = "",
    effects: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Produce a deterministic, intent-aware animation plan.

    The frontend sandbox ``SlideRuntime`` consumes this map and drives Motion
    One / Framer Motion entry/emphasis/hover/exit primitives. Empty arrays
    used to render static slides; now every slide ships with tuned defaults
    so the deck feels alive without any LLM call.
    """
    intent_key = (intent or "").lower()
    layout_key = (layout or "").lower()
    kit_key = (kit or "").strip()

    transition = "fade"
    if intent_key in {"traction", "metrics", "financials"}:
        transition = "slide"
    elif intent_key in {"vision", "title", "thanks", "cover"}:
        transition = "zoom"
    elif intent_key in {"how_it_works", "process"}:
        transition = "wipe"

    # Entry choreography per kit component. Stagger delays are multiples of 80ms
    # to stay under the 400ms perceived-instant threshold.
    entry: list[dict[str, Any]] = []
    if kit_key == "TitleHero":
        entry = [
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 520, "delay_ms": 80,  "easing": "ease-out"},
            {"target": "subheadline",  "effect": "fade-up",    "duration_ms": 480, "delay_ms": 240, "easing": "ease-out"},
            {"target": "eyebrow",      "effect": "fade",       "duration_ms": 360, "delay_ms": 40,  "easing": "linear"},
        ]
    elif kit_key == "StatHero":
        entry = [
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 440, "delay_ms": 80,  "easing": "ease-out"},
            {"target": "subheadline",  "effect": "fade",       "duration_ms": 360, "delay_ms": 200, "easing": "linear"},
            {"target": "stats",        "effect": "count-up",   "duration_ms": 900, "delay_ms": 320, "stagger_ms": 120, "easing": "ease-out"},
        ]
    elif kit_key == "ChartBlock":
        entry = [
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 380, "delay_ms": 60,  "easing": "ease-out"},
            {"target": "chart",        "effect": "draw",       "duration_ms": 900, "delay_ms": 240, "easing": "ease-in-out"},
        ]
    elif kit_key == "FeatureGrid":
        entry = [
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 380, "delay_ms": 60,  "easing": "ease-out"},
            {"target": "features",     "effect": "fade-up",    "duration_ms": 420, "delay_ms": 200, "stagger_ms": 80,  "easing": "ease-out"},
        ]
    elif kit_key == "TeamGrid":
        entry = [
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 380, "delay_ms": 60,  "easing": "ease-out"},
            {"target": "members",      "effect": "fade-up",    "duration_ms": 460, "delay_ms": 200, "stagger_ms": 100, "easing": "ease-out"},
        ]
    elif kit_key == "DiagramBlock":
        entry = [
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 380, "delay_ms": 60,  "easing": "ease-out"},
            {"target": "nodes",        "effect": "pop",        "duration_ms": 360, "delay_ms": 200, "stagger_ms": 100, "easing": "ease-out"},
            {"target": "edges",        "effect": "draw",       "duration_ms": 600, "delay_ms": 600, "easing": "ease-in-out"},
        ]
    elif kit_key == "TimelineBlock":
        entry = [
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 380, "delay_ms": 60,  "easing": "ease-out"},
            {"target": "milestones",   "effect": "slide-in",   "duration_ms": 420, "delay_ms": 200, "stagger_ms": 120, "easing": "ease-out"},
        ]
    elif kit_key == "ComparisonBlock":
        entry = [
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 380, "delay_ms": 60,  "easing": "ease-out"},
            {"target": "columns",      "effect": "fade-up",    "duration_ms": 420, "delay_ms": 200, "stagger_ms": 140, "easing": "ease-out"},
        ]
    elif kit_key == "QuoteBlock":
        entry = [
            {"target": "quote",        "effect": "fade-up",    "duration_ms": 560, "delay_ms": 120, "easing": "ease-out"},
            {"target": "attribution",  "effect": "fade",       "duration_ms": 360, "delay_ms": 520, "easing": "linear"},
        ]
    elif kit_key == "FullBleedImage":
        entry = [
            {"target": "image",        "effect": "ken-burns",  "duration_ms": 7000, "delay_ms": 0,   "easing": "ease-in-out"},
            {"target": "headline",     "effect": "fade-up",    "duration_ms": 520,  "delay_ms": 240, "easing": "ease-out"},
        ]

    emphasis: list[dict[str, Any]] = []
    if kit_key == "StatHero":
        emphasis = [{"target": "stats", "effect": "pulse", "duration_ms": 600, "trigger": "on-enter"}]
    elif kit_key == "ChartBlock":
        emphasis = [{"target": "chart", "effect": "highlight-peak", "duration_ms": 600, "trigger": "on-visible"}]

    hover: list[dict[str, Any]] = []
    if kit_key in {"FeatureGrid", "TeamGrid", "ComparisonBlock"}:
        hover = [{"target": "card", "effect": "lift", "duration_ms": 180, "easing": "ease-out"}]

    exit_plan: list[dict[str, Any]] = [
        {"target": "all", "effect": "fade", "duration_ms": 220, "easing": "ease-in"},
    ]

    plan = {
        "entry": entry,
        "emphasis": emphasis,
        "hover": hover,
        "exit": exit_plan,
        "transition": transition,
    }
    return _apply_effects_to_animation_plan(plan, effects, kit_key=kit_key)


def _apply_effects_to_animation_plan(
    plan: dict[str, Any],
    effects: Optional[Mapping[str, Any]],
    *,
    kit_key: str,
) -> dict[str, Any]:
    if not isinstance(effects, Mapping):
        return plan

    transition = str(effects.get("transition") or "").strip().lower()
    if transition in {"fade", "slide", "zoom", "wipe", "morph"}:
        plan["transition"] = transition

    intensity = str(effects.get("intensity") or "low").strip().lower()
    multiplier = {"low": 0.88, "medium": 1.0, "high": 1.16}.get(intensity, 1.0)
    reveal = str(effects.get("reveal") or "stagger").strip().lower()
    chart_motion = str(effects.get("chartMotion") or "none").strip().lower()
    image_motion = str(effects.get("imageMotion") or "none").strip().lower()

    for entry in plan.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        entry["duration_ms"] = int(max(180, min(1400, round(float(entry.get("duration_ms") or 400) * multiplier))))
        target = str(entry.get("target") or "").lower()
        if reveal == "none":
            entry["delay_ms"] = 0
            entry.pop("stagger_ms", None)
        elif reveal in {"bullet-by-bullet", "section-by-section"} and target in {"features", "bullets", "columns", "milestones", "stats"}:
            entry["stagger_ms"] = 160 if reveal == "bullet-by-bullet" else 220
        if target in {"chart", "stats"} and chart_motion != "none":
            entry["effect"] = "count-up" if chart_motion == "count-up" else "draw"
            if chart_motion == "bar-grow":
                entry["effect"] = "bar-grow"
        if target in {"image", "background"} and image_motion != "none":
            entry["effect"] = "ken-burns" if image_motion == "ken-burns" else image_motion

    if kit_key in {"FullBleedImage", "CinematicHero", "DuotoneHero"} and image_motion != "none":
        plan.setdefault("emphasis", []).append({
            "target": "image",
            "effect": image_motion,
            "duration_ms": 1200 if image_motion != "ken-burns" else 7000,
            "trigger": "on-enter",
        })
    return plan


def _inject_design_tokens(
    props: dict[str, Any],
    design_tokens: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Embed design tokens into kit props so components can read palette, fonts, etc.

    Tokens are passed as a `designTokens` prop. Kits that don't consume it
    simply ignore it; kits that do can render with theme-aware colors,
    typography, and spacing.
    """
    if design_tokens:
        props["designTokens"] = design_tokens
    return props


# ── Kit dispatcher ────────────────────────────────────────────────


_VISIBLE_PROP_TEXT_KEYS = {
    "headline", "subheadline", "title", "description", "detail",
    "body", "bodyText", "body_text", "text", "copy", "label", "caption",
    "date", "phase", "name", "quote", "attribution", "eyebrow",
    "footer", "value", "before", "after", "stat", "ctaLabel",
}
_VISIBLE_LIST_KEYS = {
    "bullets", "features", "items", "cards", "milestones", "steps",
    "headers", "rows", "columns", "nodes", "edges", "stats", "metrics",
}
_PROP_CLEAN_SKIP_KEYS = {
    "designTokens", "layoutParams", "watermark", "sources", "links",
    "imageUrl", "logoUrl", "ctaUrl", "href", "url",
}


def _clean_render_props(value: Any, *, key: str = "", parent_key: str = "") -> Any:
    """Last-resort copy cleanup before JSX/HTML/engine artifacts are built."""
    if key in _PROP_CLEAN_SKIP_KEYS:
        return value
    if isinstance(value, dict):
        return {
            k: _clean_render_props(v, key=str(k), parent_key=key)
            for k, v in value.items()
        }
    if isinstance(value, list):
        cleaned = [
            _clean_render_props(item, key=key, parent_key=key)
            for item in value
        ]
        return [item for item in cleaned if item not in ("", None, [], {})]
    if isinstance(value, str) and (key in _VISIBLE_PROP_TEXT_KEYS or parent_key in _VISIBLE_LIST_KEYS):
        return _clean_render_text(value)
    return value


def _clean_render_text(value: str) -> str:
    raw = str(value)
    cleaned = sanitize_display_text(raw)
    if cleaned is None:
        return ""
    # Preserve benign whitespace/newlines for existing editor/export
    # contracts. Only replace when sanitizer changed actual content.
    if cleaned == re.sub(r"\s+", " ", raw).strip():
        return raw
    return cleaned


def _choose_kit_and_props(
    *,
    slide: GeneratedSlide,
    image_url: Optional[str],
    deck_title: Optional[str],
    company_icon_url: Optional[str],
    layout_candidate: LayoutCandidate,
    design_tokens: Optional[dict[str, Any]] = None,
) -> tuple[str, dict[str, Any]]:
    """Pick the best kit component for this slide and assemble its props.

    Plan 06 routes through the layout intent engine first. The engine is
    still bounded by the same hard validity gates as the old dispatcher:
    a ChartBlock needs chart data, a ComparisonBlock needs rows, and so on.
    If a candidate cannot be rendered safely, we fall back to the previous
    structured-content priority order.

    NEW: Includes visual_element support from visual_elements_engine.
    """
    intent = _canonical_intent(slide.intent)
    layout = (getattr(slide, "layout", "") or "").lower()
    kit: str = ""
    props: dict[str, Any] = {}

    if intent == "team" and getattr(slide, "requires_user_input", False):
        kit, props = KIT_TEAM_GRID, _team_props(slide)

    elif (rescued := _rescue_from_layout_and_bullets(slide=slide, layout=layout)) is not None:
        kit, props = rescued
        props = _add_visual_element_to_props(slide, props)
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )

    elif (chosen := _props_for_candidate(
        slide=slide,
        image_url=image_url,
        deck_title=deck_title,
        company_icon_url=company_icon_url,
        candidate=layout_candidate,
        layout=layout,
    )) is not None:
        kit, props = chosen
        props = _add_visual_element_to_props(slide, props)
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )

    # Defensive fallback: explicit structured payloads take priority over
    # intent tags if the candidate was not renderable.
    elif slide.team_members:
        props = _team_props(slide)
        props = _add_visual_element_to_props(slide, props)
        kit = KIT_TEAM_GRID
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )
    elif slide.chart and _chart_has_data(slide.chart):
        props = _chart_props(slide)
        props = _add_visual_element_to_props(slide, props)
        kit = KIT_CHART_BLOCK
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )
    elif slide.table and _table_has_rows(slide.table):
        props = _table_props(slide)
        props = _add_visual_element_to_props(slide, props)
        kit = KIT_DATA_TABLE
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )
    elif slide.timeline and slide.timeline.get("events"):
        props = _timeline_props(slide)
        props = _add_visual_element_to_props(slide, props)
        kit = KIT_TIMELINE_BLOCK
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )
    # Founder replan — ComparisonBlock hard gate: MUST carry >= 2 rows across
    # its columns. A zero-row comparison renders as an empty box in the
    # sandbox and is worse than falling through to a different kit.
    elif (
        slide.comparison
        and slide.comparison.get("columns")
        and content_rules.comparison_row_count(
            {"comparison": slide.comparison}
        ) >= 2
    ):
        props = _comparison_props(slide)
        props = _add_visual_element_to_props(slide, props)
        kit = KIT_COMPARISON_BLOCK
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )
    elif slide.diagram and slide.diagram.get("nodes"):
        props = _diagram_props(slide)
        props = _add_visual_element_to_props(slide, props)
        kit = KIT_DIAGRAM_BLOCK
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )
    elif slide.quote and slide.quote.get("text"):
        props = _quote_props(slide)
        props = _add_visual_element_to_props(slide, props)
        kit = KIT_QUOTE_BLOCK
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )
    # Founder replan — StatHero hard gate: at least one stat block MUST have
    # a non-empty value, else the kit renders as empty chrome.
    elif slide.stat_blocks and any(
        isinstance(b, dict) and str(b.get("value") or "").strip()
        for b in slide.stat_blocks
    ):
        props = _stat_props(slide)
        props = _add_visual_element_to_props(slide, props)
        kit = KIT_STAT_HERO
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )

    # 1b. LAYOUT-HINT RESCUE — writers often encode structural intent in
    # the `layout` string ("Quote with background image", "Step-by-step
    # guide", "Competitive matrix", "Revenue projection") but fail to
    # populate the corresponding structured field. We detect these
    # hints and synthesize structure from body/bullets so the deck
    # doesn't collapse into a wall of FeatureGrids.
    elif (rescued := _rescue_from_layout_and_bullets(slide=slide, layout=layout)) is not None:
        kit, props = rescued
        props = _add_visual_element_to_props(slide, props)
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )

    # 2. Intent-driven fallbacks.
    elif intent in {"title", "cover"}:
        # CinematicHero for dramatic/expressive visual directions
        if layout_candidate.layout_variant in ("cinematic-cover", "cinematic-gradient"):
            props = _cinematic_props(slide, image_url)
            props = _add_visual_element_to_props(slide, props)
            kit = KIT_CINEMATIC_HERO
        else:
            props = _title_props(
                slide=slide,
                image_url=image_url,
                deck_title=deck_title,
                company_icon_url=company_icon_url,
            )
            props = _add_visual_element_to_props(slide, props)
            kit = KIT_TITLE_HERO
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )
    elif intent == "team":
        props = _team_props(slide)
        props = _add_visual_element_to_props(slide, props)
        kit = KIT_TEAM_GRID
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )
    elif intent in {"thanks", "ask", "closing"} and image_url:
        props = _full_bleed_props(slide=slide, image_url=image_url)
        props = _add_visual_element_to_props(slide, props)
        kit = KIT_FULL_BLEED_IMAGE
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )

    # 2c. Numeric bullets → StatHero (promotes "87% reduction / $2.4B TAM"
    # out of a bullet list into a big-number block).
    elif (promoted_stats := _promote_numeric_bullets(slide.bullets)) and len(promoted_stats) >= 2:
        props = {
            "headline": slide.headline or "",
            "stats": promoted_stats,
            **({"subheadline": slide.subheadline} if slide.subheadline else {}),
        }
        props = _add_visual_element_to_props(slide, props)
        kit = KIT_STAT_HERO
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )

    # 3. Bullets → GlassCard for premium feature layouts, else FeatureGrid
    elif slide.bullets and _looks_like_feature_list(slide.bullets):
        if _should_use_bento(slide, intent, layout_candidate.layout_variant):
            props = _bento_grid_props(slide)
            kit = KIT_BENTO_GRID
        elif layout_candidate.layout_variant in ("glass-grid", "glass-cards"):
            props = _glass_card_props(slide)
            kit = KIT_GLASS_CARD
        else:
            props = _feature_grid_props(slide)
            kit = KIT_FEATURE_GRID
        props = _add_visual_element_to_props(slide, props)
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )

    # 3b. Body text + optional image → EditorialImage for story/case-study content
    elif slide.body and (intent in {"case_study", "story", "content", "about"} or layout_candidate.layout_variant in ("editorial-left", "editorial-right")):
        props = _editorial_props(slide, image_url)
        props = _add_visual_element_to_props(slide, props)
        kit = KIT_EDITORIAL_IMAGE
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )

    # 3c. SplitOverlap for narrative/content with image and overlap layout
    elif layout_candidate.layout_variant in ("split-overlap-left", "split-overlap-right"):
        props = _split_overlap_props(slide, image_url)
        props = _add_visual_element_to_props(slide, props)
        kit = KIT_SPLIT_OVERLAP
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )

    # 3d. FloatingStat for floating glass stat cards with stats
    elif layout_candidate.layout_variant in ("floating-stats",) and slide.stat_blocks:
        props = _floating_stat_props(slide)
        props = _add_visual_element_to_props(slide, props)
        kit = KIT_FLOATING_STAT
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )

    # 3e. DuotoneHero for dramatic/gradient cover with image
    elif layout_candidate.layout_variant in ("duotone-cover", "duotone-gradient"):
        props = _duotone_props(slide, image_url)
        props = _add_visual_element_to_props(slide, props)
        kit = KIT_DUOTONE_HERO
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )

    # 4. Image-forward slide with no richer structure.
    elif (image_url or _image_pending(slide=slide, image_url=image_url)) and not slide.bullets and not slide.body:
        props = _full_bleed_props(slide=slide, image_url=image_url)
        props = _add_visual_element_to_props(slide, props)
        kit = KIT_FULL_BLEED_IMAGE
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )

    # 5. Last resort: TitleHero absorbs any content-light slide.
    else:
        props = _title_props(
            slide=slide,
            image_url=image_url,
            deck_title=deck_title,
            company_icon_url=company_icon_url,
        )
        props = _add_visual_element_to_props(slide, props)
        kit = KIT_TITLE_HERO
        props = _apply_layout_variant_props(
            kit=kit, props=props, candidate=layout_candidate, image_url=image_url
        )

    # Inject layout parameters (v13 hybrid generative positioning). If the
    # writer omitted them, infer deterministic safe defaults so every kit gets
    # the same bounded positioning contract.
    from app.services.v4.layout_params_engine import infer_layout_params, inject_layout_params
    layout_params = slide.layout_params or infer_layout_params(
        intent=slide.intent,
        layout_hint=slide.layout,
        headline=slide.headline,
        subheadline=slide.subheadline,
        body=slide.body,
        bullets=slide.bullets,
        stat_blocks=slide.stat_blocks,
        quote=slide.quote,
        chart=slide.chart,
        image_url=image_url,
        density_target=getattr(slide, "density_target", "medium"),
    )
    props = inject_layout_params(props, layout_params)
    return kit, _inject_design_tokens(props, design_tokens)


def _props_for_candidate(
    *,
    slide: GeneratedSlide,
    image_url: Optional[str],
    deck_title: Optional[str],
    company_icon_url: Optional[str],
    candidate: LayoutCandidate,
    layout: str,
) -> Optional[tuple[str, dict[str, Any]]]:
    kit = candidate.kit_id
    if kit == KIT_TEAM_GRID and slide.team_members:
        return kit, _team_props(slide)
    if kit == KIT_CHART_BLOCK and slide.chart and _chart_has_data(slide.chart):
        return kit, _chart_props(slide)
    if kit == KIT_DATA_TABLE and slide.table and _table_has_rows(slide.table):
        return kit, _table_props(slide)
    if kit == KIT_TIMELINE_BLOCK:
        if slide.timeline and slide.timeline.get("events"):
            return kit, _timeline_props(slide)
        rescued = _rescue_from_layout_and_bullets(slide=slide, layout=layout)
        if rescued and rescued[0] == KIT_TIMELINE_BLOCK:
            return rescued
    if kit == KIT_COMPARISON_BLOCK:
        if (
            slide.comparison
            and slide.comparison.get("columns")
            and content_rules.comparison_row_count({"comparison": slide.comparison}) >= 2
        ):
            return kit, _comparison_props(slide)
        rescued = _rescue_from_layout_and_bullets(slide=slide, layout=layout)
        if rescued and rescued[0] == KIT_COMPARISON_BLOCK:
            return rescued
    if kit == KIT_DIAGRAM_BLOCK:
        if slide.diagram and slide.diagram.get("nodes"):
            return kit, _diagram_props(slide)
        rescued = _rescue_from_layout_and_bullets(slide=slide, layout=layout)
        if rescued and rescued[0] == KIT_DIAGRAM_BLOCK:
            return rescued
    if kit == KIT_QUOTE_BLOCK:
        if slide.quote and (slide.quote.get("text") or slide.quote.get("quote")):
            return kit, _quote_props(slide)
        rescued = _rescue_from_layout_and_bullets(slide=slide, layout=layout)
        if rescued and rescued[0] == KIT_QUOTE_BLOCK:
            return rescued
    if kit == KIT_STAT_HERO:
        if slide.stat_blocks and any(isinstance(b, dict) and str(b.get("value") or "").strip() for b in slide.stat_blocks):
            return kit, _stat_props(slide)
        stats = _promote_numeric_bullets(slide.bullets)
        if stats:
            props: dict[str, Any] = {"headline": slide.headline or "", "stats": stats}
            if slide.subheadline:
                props["subheadline"] = slide.subheadline
            return kit, props
    if kit == KIT_FEATURE_GRID and slide.bullets and _looks_like_feature_list(slide.bullets):
        return kit, _feature_grid_props(slide)
    if kit == KIT_FULL_BLEED_IMAGE and (image_url or _image_pending(slide=slide, image_url=image_url)):
        return kit, _full_bleed_props(slide=slide, image_url=image_url)
    if kit == KIT_TITLE_HERO:
        strong_signals = {
            "chart", "timeline", "comparison", "diagram", "quote",
            "team", "stats", "features", "image",
        }
        if (
            candidate.features.intent not in {"title", "cover"}
            and strong_signals.intersection(candidate.features.signals)
        ):
            return None
        return kit, _title_props(
            slide=slide,
            image_url=image_url,
            deck_title=deck_title,
            company_icon_url=company_icon_url,
        )
    return None


def _apply_layout_variant_props(
    *,
    kit: str,
    props: dict[str, Any],
    candidate: LayoutCandidate,
    image_url: Optional[str],
) -> dict[str, Any]:
    variant = candidate.layout_variant
    if kit == KIT_STAT_HERO:
        if variant in {"centered-stat", "market-scale"} or len(props.get("stats") or []) == 1:
            props["align"] = "center"
    elif kit == KIT_TIMELINE_BLOCK:
        if variant in {"roadmap-vertical"}:
            props["orientation"] = "vertical"
        elif variant in {"roadmap-horizontal", "process-flow"}:
            props["orientation"] = "horizontal"
    elif kit == KIT_QUOTE_BLOCK:
        if variant in {"testimonial-accent"}:
            props["variant"] = "accent"
    elif kit == KIT_FULL_BLEED_IMAGE:
        if variant == "editorial-bleed-right":
            props["align"] = "bottom-right"
            props["overlay"] = "scrim-bottom"
        elif variant == "duotone-proof":
            props["overlay"] = "duotone"
            props["align"] = "center"
        else:
            props.setdefault("overlay", "scrim-bottom")
            props.setdefault("align", "bottom-left")
        if image_url:
            props["imageUrl"] = image_url
    elif kit == KIT_FEATURE_GRID:
        if variant in {"benefits-two-col", "issue-solution-grid"}:
            props["columns"] = 2
        elif variant == "feature-cards-4":
            props["columns"] = 4
        elif variant == "feature-cards-3":
            props["columns"] = 3
        _normalize_feature_grid_balance(props)
    return props


# ── Prop builders ─────────────────────────────────────────────────


def _title_props(
    *,
    slide: GeneratedSlide,
    image_url: Optional[str],
    deck_title: Optional[str],
    company_icon_url: Optional[str],
) -> dict[str, Any]:
    variant = "image" if image_url else "gradient"
    eyebrow = (slide.purpose or "").replace("_", " ").upper() or None
    # Prefer deck_title as the footer for cover slides.
    footer = deck_title if (slide.intent or "").lower() in {"title", "cover"} else None
    props = {
        "headline": slide.headline or deck_title or "Untitled",
        "variant": variant,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    if eyebrow:
        props["eyebrow"] = eyebrow
    if footer:
        props["footer"] = footer
    if image_url:
        props["imageUrl"] = image_url
    if company_icon_url:
        props["logoUrl"] = company_icon_url
    return props


def _stat_props(slide: GeneratedSlide) -> dict[str, Any]:
    stats = []
    for sb in slide.stat_blocks[:4]:
        item: dict[str, Any] = {
            "value": str(sb.get("value") or sb.get("number") or ""),
            "label": str(sb.get("label") or sb.get("caption") or ""),
        }
        if sb.get("delta"):
            item["delta"] = str(sb["delta"])
        trend = sb.get("trend")
        if trend in {"up", "down", "flat"}:
            item["trend"] = trend
        stats.append(item)
    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "stats": stats,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _chart_props(slide: GeneratedSlide) -> dict[str, Any]:
    # Validate chart data first
    validated = ensure_valid_visual_element("chart", slide.chart)
    if not validated:
        if isinstance(slide.chart, Mapping) and slide.chart.get("data"):
            validated = dict(slide.chart)
        else:
            # Return minimal props to avoid broken render
            return {"headline": slide.headline or "", "type": "bar", "data": [], "xKey": "name"}
    
    chart = validated
    data = chart.get("data") or []
    # Normalize to list[dict]. If the LLM produced [{x,y}] already, good.
    if data and isinstance(data[0], (list, tuple)):
        # [[label, value], ...] shape
        data = [{"name": str(r[0]), "value": float(r[1])} for r in data if len(r) >= 2]
    labels = [
        str(row.get("label") or row.get("name") or row.get("x") or "")
        for row in data
        if isinstance(row, Mapping)
    ]
    ctype_raw = str(
        chart.get("type")
        or select_chart_type(slide.intent or slide.layout or "", labels=labels)
    ).lower()

    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "type": ctype_raw,
        "data": data,
        "xKey": str(
            chart.get("xKey")
            or chart.get("x_key")
            or ((slide.chart or {}).get("xKey") if isinstance(slide.chart, Mapping) else None)
            or ((slide.chart or {}).get("x_key") if isinstance(slide.chart, Mapping) else None)
            or "name"
        ),
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    # Pie + radar use value/name keys; bar/line/area use y-keys.
    if ctype_raw in {"pie", "radar", "donut"}:
        props["valueKey"] = str(chart.get("valueKey") or chart.get("value_key") or "value")
        props["nameKey"] = props["xKey"]
    else:
        y_keys = chart.get("yKeys") or chart.get("y_keys") or ["value"]
        if isinstance(y_keys, str):
            y_keys = [y_keys]
        props["yKeys"] = list(y_keys)
        if chart.get("seriesLabels") or chart.get("series_labels"):
            props["seriesLabels"] = chart.get("seriesLabels") or chart.get("series_labels")
    if chart.get("source"):
        props["source"] = str(chart["source"])
    return props


def _table_has_rows(table: Mapping[str, Any]) -> bool:
    headers = table.get("headers")
    rows = table.get("rows")
    return (
        isinstance(headers, list)
        and bool(headers)
        and isinstance(rows, list)
        and any(isinstance(row, (list, tuple)) and any(str(cell).strip() for cell in row) for row in rows)
    )


def _table_props(slide: GeneratedSlide) -> dict[str, Any]:
    table = slide.table if isinstance(slide.table, Mapping) else {}
    headers = [str(h) for h in (table.get("headers") or []) if str(h).strip()]
    rows: list[list[str]] = []
    for row in table.get("rows") or []:
        if not isinstance(row, (list, tuple)):
            continue
        cleaned_row = [str(cell) for cell in row]
        if any(cell.strip() for cell in cleaned_row):
            rows.append(cleaned_row)
    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "headers": headers,
        "rows": rows,
        "table": {"headers": headers, "rows": rows},
        "table_data": {"headers": headers, "rows": rows},
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    highlight = table.get("highlightColumn") or table.get("highlight_column")
    if isinstance(highlight, int):
        props["highlightColumn"] = highlight
    return props


def _timeline_props(slide: GeneratedSlide) -> dict[str, Any]:
    # Validate timeline data first
    validated = ensure_valid_visual_element("timeline", slide.timeline)
    if not validated:
        # Return minimal props to avoid broken render
        return {"headline": slide.headline or "", "orientation": "horizontal", "milestones": []}
    
    timeline = validated
    events = timeline.get("events") or []
    milestones = []
    for e in events:
        m: dict[str, Any] = {
            "date": _repair_short_text_fragment(e.get("date") or e.get("when") or ""),
            "title": _repair_short_text_fragment(e.get("title") or e.get("name") or ""),
        }
        if e.get("description"):
            m["description"] = _repair_short_text_fragment(e["description"])
        if e.get("done") is True:
            m["done"] = True
        milestones.append(m)
    orientation = str(timeline.get("orientation") or "horizontal").lower()
    if orientation not in {"horizontal", "vertical"}:
        orientation = "horizontal"
    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "orientation": orientation,
        "milestones": milestones,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _comparison_props(slide: GeneratedSlide) -> dict[str, Any]:
    # Validate comparison data first
    validated = ensure_valid_visual_element("comparison", slide.comparison)
    if not validated:
        # Return minimal props to avoid broken render
        return {"headline": slide.headline or "", "columns": [], "rows": []}
    
    cmp = validated
    raw_cols = cmp.get("columns") or []
    # Two shapes seen in v4 output:
    #   (a) {columns:[{name, highlight?, rows:[{feature,value}]}]}
    #   (b) {columns:[{title, items:[...]}]} + optional features[]
    columns = []
    rows_by_feature: dict[str, dict[str, Any]] = {}
    features: list[str] = list(cmp.get("features") or [])
    if not features and isinstance(cmp.get("rows"), list):
        features = [_repair_short_text_fragment(row) for row in cmp.get("rows") or [] if isinstance(row, str) and row.strip()]

    for i, c in enumerate(raw_cols):
        col: dict[str, Any] = {"name": _repair_short_text_fragment(c.get("name") or c.get("title") or f"Column {i + 1}")}
        if c.get("highlight"):
            col["highlight"] = True
        if c.get("tagline"):
            col["tagline"] = _repair_short_text_fragment(c["tagline"])
        columns.append(col)

        # Shape (a): inline rows
        for row in c.get("rows") or []:
            feat = _repair_short_text_fragment(row.get("feature") or row.get("name") or "")
            if not feat:
                continue
            rows_by_feature.setdefault(feat, {"feature": feat, "values": [None] * len(raw_cols)})
            rows_by_feature[feat]["values"][i] = _repair_short_text_fragment(row.get("value"))

        # Shape (b): items list implicitly mapped to features[]
        for j, item in enumerate(c.get("items") or []):
            if j >= len(features):
                continue
            feat = features[j]
            rows_by_feature.setdefault(feat, {"feature": feat, "values": [None] * len(raw_cols)})
            rows_by_feature[feat]["values"][i] = _repair_short_text_fragment(item)

        # Shape (c): column-local features used by some deterministic fallbacks.
        for row in c.get("features") or []:
            if not isinstance(row, dict):
                continue
            feat = _repair_short_text_fragment(row.get("label") or row.get("feature") or row.get("name") or "")
            if not feat:
                continue
            rows_by_feature.setdefault(feat, {"feature": feat, "values": [None] * len(raw_cols)})
            rows_by_feature[feat]["values"][i] = _repair_short_text_fragment(row.get("value"))

    # Shape (d): top-level rows with ordered or named values, used by HTML/PDF
    # comparison exports and some deterministic fallbacks.
    for row in cmp.get("rows") or []:
        if not isinstance(row, dict):
            continue
        feat = _repair_short_text_fragment(row.get("feature") or row.get("name") or row.get("label") or "")
        if not feat:
            continue
        values = row.get("values")
        if feat not in rows_by_feature:
            rows_by_feature[feat] = {"feature": feat, "values": [None] * len(raw_cols)}
        if isinstance(values, list):
            for i, value in enumerate(values[:len(raw_cols)]):
                if value is not None:
                    rows_by_feature[feat]["values"][i] = _repair_short_text_fragment(value)
        elif isinstance(values, dict):
            for i, c in enumerate(raw_cols):
                name = c.get("name") or c.get("title") or f"Column {i + 1}"
                value = values.get(name)
                if value is not None:
                    rows_by_feature[feat]["values"][i] = _repair_short_text_fragment(value)

    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "columns": columns,
        "rows": list(rows_by_feature.values()),
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _diagram_props(slide: GeneratedSlide) -> dict[str, Any]:
    # Validate diagram data first
    validated = ensure_valid_visual_element("diagram", slide.diagram)
    if not validated:
        # Return minimal props to avoid broken render
        return {"headline": slide.headline or "", "nodes": [], "edges": []}
    
    dg = validated
    raw_nodes = dg.get("nodes") or []
    nodes = []
    node_ids = set()
    # Auto-layout fallback: spread nodes along a horizontal line if no
    # coordinates were provided.
    n = max(len(raw_nodes), 1)
    for i, raw in enumerate(raw_nodes):
        nid = str(raw.get("id") or f"n{i}")
        node_ids.add(nid)
        node: dict[str, Any] = {
            "id": nid,
            "label": _repair_short_text_fragment(raw.get("label") or raw.get("name") or nid),
            "x": float(raw.get("x")) if raw.get("x") is not None else (i + 1) / (n + 1),
            "y": float(raw.get("y")) if raw.get("y") is not None else 0.5,
        }
        if raw.get("variant") in {"primary", "secondary", "muted"}:
            node["variant"] = raw["variant"]
        nodes.append(node)

    edges = []
    for raw in dg.get("edges") or []:
        f = str(raw.get("from") or raw.get("source") or "")
        t = str(raw.get("to") or raw.get("target") or "")
        if f not in node_ids or t not in node_ids:
            continue
        edge: dict[str, Any] = {"from": f, "to": t}
        if raw.get("label"):
            edge["label"] = _repair_short_text_fragment(raw["label"])
        if raw.get("style") in {"solid", "dashed"}:
            edge["style"] = raw["style"]
        edges.append(edge)

    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "nodes": nodes,
        "edges": edges,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _quote_props(slide: GeneratedSlide) -> dict[str, Any]:
    q = slide.quote or {}
    props: dict[str, Any] = {
        "quote": str(q.get("text") or q.get("quote") or ""),
        "attribution": str(q.get("attribution") or q.get("author") or ""),
    }
    if q.get("role"):
        props["role"] = str(q["role"])
    if q.get("photo_url") or q.get("photoUrl"):
        props["photoUrl"] = str(q.get("photo_url") or q.get("photoUrl"))
    return props


def _team_props(slide: GeneratedSlide) -> dict[str, Any]:
    members = []
    for m in slide.team_members[:8]:
        tm: dict[str, Any] = {
            "name": str(m.get("name") or ""),
            "role": str(m.get("role") or ""),
        }
        if m.get("photo_url") and not m.get("is_default_avatar"):
            tm["photoUrl"] = str(m["photo_url"])
        if m.get("bio"):
            tm["bio"] = str(m["bio"])
        if m.get("linkedin_url"):
            tm["linkedInUrl"] = str(m["linkedin_url"])
        members.append(tm)

    # Column count: 2 members → 2, 3 → 3, 4-8 → 4.
    cols = 2 if len(members) <= 2 else (3 if len(members) == 3 else 4)
    props: dict[str, Any] = {
        "headline": slide.headline or "Team",
        "members": members,
        "columns": cols,
    }
    if getattr(slide, "requires_user_input", False):
        props["requiresUserInput"] = True
        if getattr(slide, "user_input_kind", None):
            props["userInputKind"] = str(slide.user_input_kind)
        if getattr(slide, "user_input_reason", None):
            props["userInputReason"] = str(slide.user_input_reason)
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _feature_grid_props(slide: GeneratedSlide) -> dict[str, Any]:
    features = []
    for b in slide.bullets[:6]:
        text = str(b).strip()
        if not text:
            continue
        # Try "Title — description" or "Title: description" split.
        title, _, desc = text.partition("—")
        if not desc:
            title, _, desc = text.partition(":")
        features.append(
            {
                "title": (title or text).strip(),
                "description": desc.strip() or None,
                # Icon hint based on simple keyword detection — the kit
                # falls back to a neutral Target icon when unknown.
                "icon": _guess_icon(title or text),
            }
        )
    features = _merge_fifth_feature(features)
    cols = _balanced_feature_grid_columns(len(features))
    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "features": features,
        "columns": cols,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _should_use_bento(slide: GeneratedSlide, intent: str, variant: str) -> bool:
    """Use asymmetric cards for proof/narrative slides to avoid box monotony."""
    if variant in {"bento-proof", "bento-insight"}:
        return True
    intent_key = (intent or "").lower()
    if intent_key in {
        "problem", "why_now", "solution", "moat", "differentiation",
        "value", "proof", "traction", "go_to_market",
    }:
        return len(slide.bullets or []) in {3, 4}
    return bool(getattr(slide, "index", 0) % 4 == 2 and len(slide.bullets or []) in {3, 4})


def _bento_grid_props(slide: GeneratedSlide) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for i, bullet in enumerate((slide.bullets or [])[:6]):
        text = str(bullet).strip()
        if not text:
            continue
        title, _, desc = text.partition("â€”")
        if not desc:
            title, _, desc = text.partition(":")
        item: dict[str, Any] = {
            "title": (title or text).strip(),
            "description": desc.strip() or None,
            "icon": _guess_icon(title or text),
            "accent": i == 1,
        }
        if i == 0 and len(slide.bullets or []) >= 4:
            item["span"] = "2"
        items.append(item)
    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "items": items,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _merge_fifth_feature(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep FeatureGrid rows balanced without dropping the fifth point."""
    if len(features) != 5:
        return features
    merged = [dict(item) for item in features[:4]]
    overflow = features[4]
    title = str(overflow.get("title") or "").strip()
    desc = str(overflow.get("description") or "").strip()
    overflow_text = " - ".join(part for part in (title, desc) if part)
    if overflow_text:
        prior_desc = str(merged[-1].get("description") or "").strip()
        merged[-1]["description"] = f"{prior_desc} {overflow_text}".strip() if prior_desc else overflow_text
    return merged


def _balanced_feature_grid_columns(feature_count: int, preferred: Any = None) -> int:
    valid = {2, 3, 4}
    try:
        preferred_int = int(preferred) if preferred is not None else None
    except (TypeError, ValueError):
        preferred_int = None
    if preferred_int in valid and (feature_count <= preferred_int or feature_count % preferred_int == 0):
        return preferred_int
    if feature_count <= 2:
        return 2
    if feature_count == 3:
        return 3
    if feature_count == 4:
        return 2
    if feature_count == 6:
        return 3
    return 4


def _normalize_feature_grid_balance(props: dict[str, Any]) -> None:
    features = [f for f in (props.get("features") or []) if isinstance(f, dict)]
    if not features:
        return
    if len(features) == 5:
        features = _merge_fifth_feature(features)
        props["features"] = features
    props["columns"] = _balanced_feature_grid_columns(len(features), props.get("columns"))


def _full_bleed_props(
    *, slide: GeneratedSlide, image_url: Optional[str]
) -> dict[str, Any]:
    props: dict[str, Any] = {
        "overlay": "scrim-bottom",
        "align": "bottom-left",
    }
    if image_url:
        props["imageUrl"] = image_url
    if slide.headline:
        props["headline"] = slide.headline
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _cinematic_props(slide: GeneratedSlide, image_url: Optional[str]) -> dict[str, Any]:
    """Build props for CinematicHero kit."""
    variant = "image" if image_url else "gradient"
    props: dict[str, Any] = {
        "headline": slide.headline or "Untitled",
        "variant": variant,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    if image_url:
        props["imageUrl"] = image_url
    if slide.purpose:
        props["eyebrow"] = slide.purpose.replace("_", " ").upper()
    return props


def _glass_card_props(slide: GeneratedSlide) -> dict[str, Any]:
    """Build props for GlassCard kit from bullets."""
    items = []
    for b in slide.bullets[:6]:
        text = str(b).strip()
        if not text:
            continue
        title, _, desc = text.partition("—")
        if not desc:
            title, _, desc = text.partition(":")
        items.append({
            "title": (title or text).strip(),
            "description": desc.strip() or None,
            "icon": _guess_icon(title or text),
        })
    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "items": items,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _editorial_props(slide: GeneratedSlide, image_url: Optional[str]) -> dict[str, Any]:
    """Build props for EditorialImage kit."""
    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "body": slide.body or "",
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    if image_url:
        props["imageUrl"] = image_url
    if slide.purpose:
        props["eyebrow"] = slide.purpose.replace("_", " ").upper()
    # Detect quote in body
    if slide.body and '"' in slide.body:
        parts = slide.body.split('"')
        if len(parts) >= 3:
            props["quote"] = parts[1]
            # Try to find attribution after the quote
            after = parts[2].strip()
            if after.startswith("—") or after.startswith("-"):
                props["quoteAttribution"] = after.lstrip("—- ").strip()
    return props


def _duotone_props(slide: GeneratedSlide, image_url: Optional[str]) -> dict[str, Any]:
    """Build props for DuotoneHero kit."""
    props: dict[str, Any] = {
        "headline": slide.headline or "Untitled",
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    if image_url:
        props["imageUrl"] = image_url
    if slide.purpose:
        props["eyebrow"] = slide.purpose.replace("_", " ").upper()
    return props


def _floating_stat_props(slide: GeneratedSlide) -> dict[str, Any]:
    """Build props for FloatingStat kit from stat_blocks."""
    stats = []
    for sb in slide.stat_blocks[:4]:
        item: dict[str, Any] = {
            "value": str(sb.get("value") or sb.get("number") or ""),
            "label": str(sb.get("label") or sb.get("caption") or ""),
        }
        if sb.get("delta"):
            item["delta"] = str(sb["delta"])
        stats.append(item)
    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "stats": stats,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _split_overlap_props(slide: GeneratedSlide, image_url: Optional[str]) -> dict[str, Any]:
    """Build props for SplitOverlap kit."""
    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "body": slide.body or "",
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    if image_url:
        props["imageUrl"] = image_url
    if slide.purpose:
        props["eyebrow"] = slide.purpose.replace("_", " ").upper()
    return props


# ── Small helpers ─────────────────────────────────────────────────


def _chart_has_data(chart: Mapping[str, Any]) -> bool:
    data = chart.get("data")
    return bool(data) and isinstance(data, list) and len(data) > 0


def _looks_like_feature_list(bullets: list[str]) -> bool:
    """Heuristic: short bullets (<14 words) → grid; long → prose."""
    if len(bullets) < 2:
        return False
    avg_words = sum(len(b.split()) for b in bullets) / max(len(bullets), 1)
    return avg_words <= 14 and len(bullets) <= 6


_ICON_HINTS = {
    # keyword substring → lucide icon name
    "growth": "TrendingUp",
    "revenue": "DollarSign",
    "users": "Users",
    "user": "User",
    "team": "Users",
    "security": "Shield",
    "secure": "Shield",
    "speed": "Zap",
    "fast": "Zap",
    "data": "Database",
    "ai": "Sparkles",
    "automation": "Cpu",
    "global": "Globe",
    "world": "Globe",
    "mobile": "Smartphone",
    "cloud": "Cloud",
    "chart": "BarChart3",
    "analytics": "BarChart3",
    "launch": "Rocket",
    "market": "Target",
    "feedback": "MessageSquare",
    "design": "Palette",
    "code": "Code2",
    "integration": "Plug",
    "money": "DollarSign",
    "cost": "DollarSign",
    "time": "Clock",
    "award": "Award",
    "star": "Star",
    "shield": "Shield",
}


def _guess_icon(text: str) -> str:
    mapped = icon_for(text)
    if mapped:
        return mapped
    lo = text.lower()
    for kw, icon in _ICON_HINTS.items():
        if kw in lo:
            return icon
    return "Target"


# ── Layout-hint rescue ────────────────────────────────────────────
# Writers routinely encode visual intent in the free-form `layout`
# string ("Quote with background image", "Step-by-step guide",
# "Competitive-matrix", "Revenue-projection") without populating the
# corresponding structured field. We keyword-scan the layout and
# reconstitute the visual from body + bullets so every deck ships with
# real visual diversity instead of 10 identical FeatureGrids.

_LAYOUT_QUOTE_HINTS = ("quote", "testimonial", "citation")
_LAYOUT_TIMELINE_HINTS = ("timeline", "step", "phase", "roadmap", "journey", "process", "milestone")
_LAYOUT_COMPARISON_HINTS = ("compar", "vs.", " vs ", "matrix", "versus", "side-by-side", "side by side")
_LAYOUT_DIAGRAM_HINTS = ("diagram", "flow", "architecture", "system map", "network")
_LAYOUT_STAT_HINTS = ("stat", "metric", "kpi", "big number", "big-number", "numbers")
_LAYOUT_IMAGE_FULL_HINTS = ("full-bleed", "full bleed", "hero image", "image-full", "image full", "background image")
_LAYOUT_TITLE_HINTS = ("title-only", "title only", "cover", "opener")


def _rescue_from_layout_and_bullets(
    *, slide: GeneratedSlide, layout: str
) -> Optional[tuple[str, dict[str, Any]]]:
    """Inspect `slide.layout` and content to rescue a premium kit when
    the writer failed to populate a structured field. Returns None if
    no rescue applies; caller then falls through to the normal path.

    Rescue priority (first match wins):
      1. Quote-layout + detectable quotation content → QuoteBlock
      2. Timeline/step layout + enumerated bullets → TimelineBlock
      3. Comparison/matrix layout + paired bullets → ComparisonBlock
      4. Stats/metric layout + numeric bullets → StatHero
      5. Full-bleed layout + image prompt → FullBleedImage (caller
         supplies image_url separately; rescue only fires when the
         writer EXPLICITLY asked for full-bleed)
      6. Title/cover layout → TitleHero
    """
    bullets = list(slide.bullets or [])
    body = (slide.body or "").strip()

    # 1. Quote rescue
    if any(h in layout for h in _LAYOUT_QUOTE_HINTS):
        q = _extract_quote(body=body, bullets=bullets)
        if q:
            return KIT_QUOTE_BLOCK, q

    # 2. Timeline rescue
    if any(h in layout for h in _LAYOUT_TIMELINE_HINTS):
        milestones = _extract_timeline(bullets=bullets, body=body)
        if len(milestones) >= 2:
            props: dict[str, Any] = {
                "headline": slide.headline or "",
                "orientation": "horizontal" if len(milestones) <= 5 else "vertical",
                "milestones": milestones,
            }
            if slide.subheadline:
                props["subheadline"] = slide.subheadline
            return KIT_TIMELINE_BLOCK, props

    # 3. Comparison rescue
    if any(h in layout for h in _LAYOUT_COMPARISON_HINTS):
        cmp_props = _extract_comparison(slide=slide, bullets=bullets)
        if cmp_props is not None:
            # Founder replan — hard gate: rescued comparison must have >= 2 rows.
            if content_rules.comparison_row_count(
                {"comparison": cmp_props}
            ) >= 2:
                return KIT_COMPARISON_BLOCK, cmp_props

    # 3b. Diagram rescue
    if any(h in layout for h in _LAYOUT_DIAGRAM_HINTS):
        diagram_props = _extract_diagram(slide=slide, bullets=bullets, body=body)
        if diagram_props is not None:
            return KIT_DIAGRAM_BLOCK, diagram_props

    # 4. Stats rescue
    if any(h in layout for h in _LAYOUT_STAT_HINTS):
        stats = _promote_numeric_bullets(bullets)
        if stats:
            props = {
                "headline": slide.headline or "",
                "stats": stats,
            }
            if slide.subheadline:
                props["subheadline"] = slide.subheadline
            return KIT_STAT_HERO, props

    # 5. Title rescue (only fires when the layout EXPLICITLY says so —
    # we never hijack a content slide into a TitleHero).
    if any(h in layout for h in _LAYOUT_TITLE_HINTS):
        # Fall back through to the normal title_props path by returning
        # a hint the caller understands. We can't call _title_props here
        # without the image_url/deck_title, so return None and let the
        # intent-path pick it up (index==0 catches cover anyway).
        return None

    return None


_QUOTE_RE = re.compile(r'["“”](.{8,240}?)["“”](?:\s*[—\-–]\s*(.{2,80}))?', re.DOTALL)


def _extract_quote(*, body: str, bullets: list[str]) -> Optional[dict[str, Any]]:
    """Pull a quote + attribution from body or bullets. Recognises
    curly + straight quotes and em-dash / hyphen attribution."""
    candidates: list[str] = []
    if body:
        candidates.append(body)
    candidates.extend(bullets)
    for text in candidates:
        m = _QUOTE_RE.search(text)
        if m:
            quote_text = m.group(1).strip()
            attrib = (m.group(2) or "").strip()
            out: dict[str, Any] = {
                "quote": quote_text,
                "attribution": attrib,
            }
            return out
    # Fallback: a single long bullet that reads like a quotation
    # (no trailing period + contains a verb-subject pattern). Too
    # heuristic to be reliable — only fire on strong signals.
    return None


_TIMELINE_PREFIX_RE = re.compile(
    r"^(?:"
    r"(?P<d1>Q[1-4]\s*\d{2,4})"           # Q1 2025 / Q3 24
    r"|(?P<d2>\d{4})"                      # 2025
    r"|(?P<d3>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{2,4})"
    r"|(?P<d4>Phase\s*\d+)"               # Phase 1
    r"|(?P<d5>Step\s*\d+)"                # Step 1
    r"|(?P<d6>Month\s*\d+)"               # Month 3
    r")\s*[:\-–—]\s*(?P<rest>.+)$",
    re.IGNORECASE,
)


def _extract_timeline(*, bullets: list[str], body: str) -> list[dict[str, Any]]:
    """Turn 'Q1 2025: ship MVP' / 'Phase 2 — onboard 50 customers'
    bullets into milestone records. Skips bullets that don't match."""
    out: list[dict[str, Any]] = []
    for b in bullets:
        text = (b or "").strip()
        if not text:
            continue
        m = _TIMELINE_PREFIX_RE.match(text)
        if m:
            date = (
                m.group("d1") or m.group("d2") or m.group("d3")
                or m.group("d4") or m.group("d5") or m.group("d6") or ""
            ).strip()
            rest = m.group("rest").strip()
            title_part, _, desc = rest.partition(" — ")
            if not desc:
                title_part, _, desc = rest.partition(": ")
            out.append(
                {
                    "date": date,
                    "title": (title_part or rest)[:80],
                    **({"description": desc} if desc else {}),
                }
            )
    if not out:
        plain_steps = [str(b or "").strip() for b in bullets if str(b or "").strip()]
        if len(plain_steps) >= 2:
            for i, text in enumerate(plain_steps[:6]):
                text = _repair_short_text_fragment(text)
                title_part, sep, desc = text.partition(" - ")
                if not sep:
                    title_part, sep, desc = text.partition(":")
                title_part = (title_part or text).strip()
                desc = desc.strip()
                out.append(
                    {
                        "date": f"{i + 1:02d}",
                        "title": title_part[:80],
                        **({"description": desc} if desc else {}),
                    }
                )
    return out


def _extract_comparison(
    *, slide: GeneratedSlide, bullets: list[str]
) -> Optional[dict[str, Any]]:
    """Turn 'Old: slow / New: fast' bullet pairs into a two-column
    comparison. Also handles 'feature: A vs B' patterns."""
    if len(bullets) < 2:
        return None
    rows: list[dict[str, Any]] = []
    col_labels: list[str] = []
    for b in bullets:
        text = (b or "").strip()
        if " vs " in text.lower():
            left, _, right = text.partition(" vs ")
            # "Price vs Quality" is a dimension, not a row — unreliable.
            # Skip for now; only accept key:value:value tuples.
            continue
        # "Label: value_a vs value_b"
        if ":" in text and (" vs " in text.lower() or " | " in text):
            head, _, tail = text.partition(":")
            parts = re.split(r"\s+vs\s+|\s+\|\s+", tail.strip(), maxsplit=1)
            if len(parts) == 2:
                rows.append({"feature": head.strip(), "values": [parts[0].strip(), parts[1].strip()]})
                continue
    if len(rows) < 2:
        return None
    # Derive column labels from the first row's values only if nothing else
    # is available. Falls back to "Option A / Option B" which is legible.
    col_labels = ["Current", "Proposed"]
    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "columns": [{"name": col_labels[0]}, {"name": col_labels[1], "highlight": True}],
        "rows": rows,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


def _extract_diagram(
    *, slide: GeneratedSlide, bullets: list[str], body: str
) -> Optional[dict[str, Any]]:
    """Build a simple left-to-right flow diagram from named bullets.

    The writer already authored the labels; we only infer the flow order.
    This avoids fake structure while rescuing common layouts like
    "architecture flow" where the structured diagram field is missing.
    """
    candidates = [b.strip() for b in bullets if str(b).strip()]
    if len(candidates) < 2 and body:
        candidates = [p.strip() for p in re.split(r"[\n;]+", body) if p.strip()]
    if len(candidates) < 2:
        return None
    candidates = candidates[:6]
    nodes: list[dict[str, Any]] = []
    total = len(candidates)
    for i, text in enumerate(candidates):
        text = _repair_short_text_fragment(text)
        title, _, desc = text.partition(" — ")
        if not desc:
            title, _, desc = text.partition(":")
        if not desc and "," in text:
            title, _, desc = text.partition(",")
        title = (title or text).strip()
        desc = desc.strip()
        if not desc and len(title.split()) > 6:
            words = title.split()
            title = " ".join(words[:4])
            desc = " ".join(words[4:])
        node: dict[str, Any] = {
            "id": f"n{i + 1}",
            "label": _repair_short_text_fragment(title)[:64],
            "x": (i + 1) / (total + 1),
            "y": 0.46 if i % 2 == 0 else 0.58,
        }
        if desc:
            node["description"] = _repair_short_text_fragment(desc)
        nodes.append(node)
    edges = [{"from": f"n{i + 1}", "to": f"n{i + 2}"} for i in range(total - 1)]
    props: dict[str, Any] = {
        "headline": slide.headline or "",
        "nodes": nodes,
        "edges": edges,
    }
    if slide.subheadline:
        props["subheadline"] = slide.subheadline
    return props


_NUMBER_IN_TEXT_RE = re.compile(
    r"(?P<num>"
    r"[$£€]?\d[\d,]*(?:\.\d+)?\s*[%KMBT]?\b"   # $2.4B  87%  3.5x
    r"|\d+\s*x"
    r")",
    re.IGNORECASE,
)


def _promote_numeric_bullets(bullets: list[str]) -> list[dict[str, Any]]:
    """Scan bullets for strong numeric leads (e.g. '87% reduction in
    review time') and promote them into StatHero stat_blocks. We keep
    up to 4; if fewer than 2 qualify, return [] and let the caller
    fall through to FeatureGrid."""
    stats: list[dict[str, Any]] = []
    for b in bullets:
        text = (b or "").strip()
        if not text:
            continue
        m = _NUMBER_IN_TEXT_RE.search(text)
        if not m:
            continue
        value = m.group("num").strip().rstrip(".,:;")
        # label = the rest of the bullet, minus the number + noise words
        label = (text[: m.start()] + text[m.end():]).strip(" -—:;,.")
        # Drop generic fillers
        label = re.sub(r"^(of|in|per|with|by)\s+", "", label, flags=re.IGNORECASE)
        label = label[:60].strip()
        if not label:
            continue
        stats.append({"value": value, "label": label})
        if len(stats) >= 4:
            break
    # Quality floor: at least 2 stats AND each stat has a non-empty label.
    if len(stats) < 2:
        return []
    return stats
