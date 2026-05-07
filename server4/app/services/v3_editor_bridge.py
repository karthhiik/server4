"""
V3 → Editor Bridge Service.

Transforms V3 generation results (raw dicts from ``deck_runs_v3``)
into validated ``PresentationDSL`` objects that the editor session can ingest.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from app.models.dsl_v2 import (
    BackgroundStyle,
    BackgroundType,
    GenerationMetadataV2,
    LayoutType,
    PresentationCore,
    PresentationDSL,
    PresentationMetadata,
    SlideContentV2,
    SlideDSL,
    SlideStyle,
    SlideType,
    ThemeDSL,
    ThemeVariant,
)

logger = logging.getLogger(__name__)


# ── Mapping tables ────────────────────────────────────────────────

# Map CEO/orchestrator layout strings → DSL LayoutType
_LAYOUT_MAP: Dict[str, LayoutType] = {
    "title-hero": LayoutType.CENTER_FOCUS,
    "two-column": LayoutType.SPLIT_SCREEN,
    "bullets": LayoutType.BULLETS,
    "bullets-with-image": LayoutType.TEXT_LEFT_VISUAL_RIGHT,
    "chart": LayoutType.CHART,
    "team-grid": LayoutType.TEAM_GRID,
    "comparison": LayoutType.COMPARISON,
    "kpi-dashboard": LayoutType.KPI_DASHBOARD,
    "timeline": LayoutType.TIMELINE,
    "quote": LayoutType.QUOTE,
    # Fallbacks
    "center-focus": LayoutType.CENTER_FOCUS,
    "split-screen": LayoutType.SPLIT_SCREEN,
    "full-bleed": LayoutType.FULL_BLEED,
}

# Map slide purpose/kind → DSL SlideType
_KIND_TO_TYPE: Dict[str, SlideType] = {
    "title": SlideType.TITLE_SLIDE,
    "problem": SlideType.PROBLEM_SLIDE,
    "solution": SlideType.SOLUTION_SLIDE,
    "market": SlideType.MARKET_SLIDE,
    "traction": SlideType.TRACTION_SLIDE,
    "financial": SlideType.FINANCIAL_SLIDE,
    "team": SlideType.TEAM_SLIDE,
    "competition": SlideType.COMPETITION_SLIDE,
    "ask": SlideType.CLOSING_SLIDE,
    "gtm": SlideType.BUSINESS_MODEL_SLIDE,
    "product_demo": SlideType.CUSTOM,
    "why_now": SlideType.CUSTOM,
    "appendix": SlideType.CUSTOM,
}


def _map_layout(raw: str) -> LayoutType:
    return _LAYOUT_MAP.get(raw, LayoutType.CENTER_FOCUS)


def _map_slide_type(kind: str) -> SlideType:
    return _KIND_TO_TYPE.get(kind, SlideType.CUSTOM)


def _transform_slide(raw: Dict[str, Any], index: int) -> SlideDSL:
    """Convert a single V3 result slide dict into a SlideDSL."""
    slide_id = raw.get("id") or f"slide-{uuid.uuid4().hex[:12]}"
    kind = raw.get("kind", raw.get("type", "custom"))
    layout_str = raw.get("layout", "center-focus")

    # Build structured content - V3 uses "content" dict with nested fields
    content_data: Dict[str, Any] = {}
    raw_content = raw.get("content", {})
    if isinstance(raw_content, dict):
        # V3 uses "headline" for title
        content_data["title"] = raw_content.get("headline", raw.get("title", ""))

        # Map V3 content fields to DSL
        if raw_content.get("bullets"):
            content_data["bullets"] = raw_content.get("bullets")
        if raw_content.get("subtitle"):
            content_data["subtitle"] = raw_content.get("subtitle")
        if raw_content.get("body_text"):
            content_data["body_text"] = raw_content.get("body_text")

        # Map quote
        quote = raw_content.get("quote", {})
        if isinstance(quote, dict):
            if quote.get("text"):
                content_data["quote_text"] = quote.get("text")
            if quote.get("author"):
                content_data["quote_author"] = quote.get("author")

        # Map data points to chart_data
        data = raw_content.get("data", [])
        if data and isinstance(data, list):
            chart_data = {
                "labels": [d.get("label", "") for d in data if d.get("label")],
                "values": [d.get("value", "") for d in data if d.get("value")],
                "sources": [d.get("source", "") for d in data if d.get("source")],
            }
            content_data["chart_data"] = chart_data

        # Map image
        if raw_content.get("image_url"):
            content_data["image_url"] = raw_content.get("image_url")

    else:
        # Fallback to top-level title
        content_data["title"] = raw.get("title", "")

    # FIX: Build style from nested design structure (V3 output has design.background)
    style_data: Dict[str, Any] = {}
    design_data = raw.get("design", {})

    # First check design.background (V3 structure)
    bg = design_data.get("background") if isinstance(design_data, dict) else None
    # Fallback to old location
    if not bg:
        bg = raw.get("background") or raw.get("style", {}).get("background")

    if bg and isinstance(bg, dict):
        # Convert V3 background to DSL format
        style_data["background"] = _convert_v3_background_to_dsl(bg)

    return SlideDSL(
        index=index,
        id=slide_id,
        type=_map_slide_type(kind),
        layout=_map_layout(layout_str),
        section=raw.get("section"),
        content=SlideContentV2(**content_data),
        style=SlideStyle(**style_data) if style_data else SlideStyle(),
        elements=[],
        speakerNotes=raw.get("speaker_notes") or raw.get("speakerNotes"),
    )


def _convert_v3_background_to_dsl(bg: Dict[str, Any]) -> Dict[str, Any]:
    """Convert V3 background format to DSL BackgroundStyle format."""
    from app.models.dsl_v2 import BackgroundType

    bg_type_str = bg.get("type", "solid").lower().replace("-", "_")

    # Map V3 types to DSL types
    type_map = {
        "gradient_linear": BackgroundType.GRADIENT_LINEAR,
        "gradient_radial": BackgroundType.GRADIENT_RADIAL,
        "gradient_conic": BackgroundType.GRADIENT_CONIC,
        "gradient_mesh": BackgroundType.GRADIENT_LINEAR,  # Fallback to linear
        "image": BackgroundType.IMAGE,
        "solid": BackgroundType.SOLID,
        "pattern": BackgroundType.SOLID,  # Fallback - pattern is overlay
        "noise": BackgroundType.SOLID,  # Fallback - noise is overlay
        "glass": BackgroundType.SOLID,  # Fallback - glass is effect
    }

    dsl_type = type_map.get(bg_type_str, BackgroundType.SOLID)

    converted = {
        "type": dsl_type,
        "colors": bg.get("colors", ["#1a1a2e"]),
    }

    # Add gradient angle
    if bg.get("angle"):
        converted["angle"] = bg.get("angle")

    # Add image URL if present
    if bg.get("image_url"):
        converted["image_url"] = bg.get("image_url")

    # Add image prompt for AI generation
    if bg.get("image_prompt"):
        converted["image_prompt"] = bg.get("image_prompt")

    # Add overlay settings
    if bg.get("overlay_color"):
        converted["overlay_color"] = bg.get("overlay_color")
    if bg.get("overlay_opacity") is not None:
        converted["overlay_opacity"] = bg.get("overlay_opacity")

    # Add blur for glass effects
    if bg.get("blur") is not None:
        converted["blur"] = bg.get("blur")

    # Add pattern
    if bg.get("pattern"):
        pattern_str = bg.get("pattern").lower()
        pattern_map = {
            "dots": "dots",
            "grid": "grid",
            "diagonal_lines": "diagonal_lines",
            "cross_hatch": "cross_hatch",
            "waves": "waves",
            "hexagons": "hexagons",
            "topography": "topography",
        }
        from app.models.dsl_v2 import PatternType

        if pattern_str in pattern_map:
            try:
                converted["pattern"] = PatternType(pattern_map[pattern_str])
            except ValueError:
                pass

    if bg.get("pattern_opacity") is not None:
        converted["pattern_opacity"] = bg.get("pattern_opacity")

    # Add noise intensity
    if bg.get("noise_intensity") is not None:
        converted["noise_intensity"] = bg.get("noise_intensity")

    # Add mesh points for gradient-mesh
    if bg.get("mesh_points"):
        converted["mesh_points"] = bg.get("mesh_points")

    return converted


def transform_v3_result_to_dsl(v3_result: Dict[str, Any]) -> PresentationDSL:
    """
    Transform a raw V3 generation result (from MongoDB ``deck_runs_v3``)
    into a validated ``PresentationDSL`` for the editor.

    Args:
        v3_result: Full document from ``deck_runs_v3`` collection.

    Returns:
        PresentationDSL ready to be passed to ``POST /api/v2/editor/sessions/open``.
    """
    presentation_id = (
        v3_result.get("presentation_id")
        or v3_result.get("deck_id")
        or str(uuid.uuid4())
    )
    topic = v3_result.get("topic", "Untitled Presentation")
    mode = v3_result.get("mode", "standard")

    # Transform slides - use V3 slides if available, otherwise build from strategy
    raw_slides = v3_result.get("slides", [])

    # FIX: If slides array is empty but strategy exists, generate slides from strategy structure
    if not raw_slides:
        strategy = v3_result.get("strategy", {})
        structure = strategy.get("structure", [])
        research = v3_result.get("research", {})
        research_items = research.get("research_items", [])

        if structure:
            raw_slides = []
            for i, slide_template in enumerate(structure):
                # Find corresponding research
                slide_research = {}
                for r in research_items:
                    if r.get("slide_index") == i:
                        slide_research = r
                        break

                # Build slide from strategy structure + research
                slide = {
                    "id": f"slide-{uuid.uuid4().hex[:12]}",
                    "kind": slide_template.get("kind", "custom"),
                    "layout": slide_template.get("layout", "center-focus"),
                    "title": slide_template.get("title", ""),
                    "content": {
                        "title": slide_template.get("title", ""),
                        "purpose": slide_template.get("purpose", ""),
                        "content_hints": slide_template.get("content_hints", ""),
                    },
                    "speakerNotes": "",
                }

                # Add research data to content if available
                if slide_research:
                    key_takeaways = slide_research.get("key_takeaways", [])
                    if key_takeaways:
                        slide["content"]["bullets"] = key_takeaways[:5]

                    data_points = slide_research.get("data_points", [])
                    if data_points:
                        slide["content"]["data_points"] = [
                            f"{dp.get('value', '')} {dp.get('label', '')}"
                            for dp in data_points[:3]
                        ]

                raw_slides.append(slide)

    slides: List[SlideDSL] = []
    for i, raw in enumerate(raw_slides):
        try:
            slides.append(_transform_slide(raw, i))
        except Exception as e:
            logger.warning("Skipping slide %d during bridge transform: %s", i, e)
            slides.append(
                SlideDSL(
                    index=i,
                    id=f"slide-{uuid.uuid4().hex[:12]}",
                    type=SlideType.CUSTOM,
                    layout=LayoutType.CENTER_FOCUS,
                    content=SlideContentV2(title=f"Slide {i + 1}"),
                )
            )

    # Ensure at least one slide
    if not slides:
        slides = [
            SlideDSL(
                index=0,
                id=f"slide-{uuid.uuid4().hex[:12]}",
                type=SlideType.TITLE_SLIDE,
                layout=LayoutType.CENTER_FOCUS,
                content=SlideContentV2(title=topic),
            )
        ]

    # Build theme from design data
    design = v3_result.get("design") or {}
    theme_overrides = design.get("theme_overrides", design.get("customOverrides", {}))
    theme = ThemeDSL(
        id=design.get("theme_id", "default"),
        variant=ThemeVariant.DARK,
        preset=design.get("preset"),
        customOverrides=theme_overrides,
    )

    # Build generation metadata
    quality_score = v3_result.get("quality_score", 0.0)
    gen_meta = GenerationMetadataV2(
        qualityScore=int(quality_score * 100)
        if quality_score <= 1.0
        else int(quality_score),
        modelUsage={"pipeline": "v3-unified", "mode": mode},
        totalCost="$0.00",
    )

    return PresentationDSL(
        version="2.0",
        presentation=PresentationCore(
            id=presentation_id,
            title=topic,
            archetype=v3_result.get("strategy", {}).get("archetype"),
            theme=theme,
            metadata=PresentationMetadata(
                language=v3_result.get("language", "en"),
                version=1,
                tags=["v3-generated", f"mode-{mode}"],
            ),
        ),
        slides=slides,
        generationMetadata=gen_meta,
    )
