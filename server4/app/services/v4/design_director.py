"""
V4 Design Director — LLM-powered visual treatment for every slide.
Runs AFTER parallel_writer (content) and BEFORE slide_compiler (assembly).
NEVER modifies slide content — only adds visual treatment (layoutParams).
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

from app.services.llm.model_router import ModelRouter, TaskType
from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.json_repair import safe_json_loads
from app.services.v4.llm_safe import safe_complete

logger = structlog.get_logger(__name__)


@dataclass
class VisualTreatment:
    """Rich visual instructions for a single slide. Content is NEVER modified."""
    headline_alignment: str = "left"
    headline_max_width_pct: int = 65
    vertical_position: str = "center"
    density_level: str = "balanced"
    emphasis: str = "typography"
    variant: str = "solid"
    image_treatment: str = "gradient-scrim"
    decorative_style: str = "minimal"
    background_pattern: Optional[str] = None
    accent_placement: str = "top-left"
    icon_style: str = "lucide"
    icon_map: list[str] = field(default_factory=list)
    accent_color_use: str = "subtle"
    gradient_angle: int = 135
    overlay_opacity: float = 0.15
    entry_animation: str = "fade-up"
    stagger_children: bool = True
    emphasis_animation: Optional[str] = None
    section_gap_multiplier: float = 1.0
    content_padding_multiplier: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "headline_alignment": self.headline_alignment,
            "headline_max_width_pct": self.headline_max_width_pct,
            "vertical_position": self.vertical_position,
            "density_level": self.density_level,
            "emphasis": self.emphasis,
            "variant": self.variant,
            "image_treatment": self.image_treatment,
            "decorative_style": self.decorative_style,
            "background_pattern": self.background_pattern,
            "accent_placement": self.accent_placement,
            "icon_style": self.icon_style,
            "icon_map": self.icon_map,
            "accent_color_use": self.accent_color_use,
            "gradient_angle": self.gradient_angle,
            "overlay_opacity": self.overlay_opacity,
            "entry_animation": self.entry_animation,
            "stagger_children": self.stagger_children,
            "emphasis_animation": self.emphasis_animation,
            "section_gap_multiplier": self.section_gap_multiplier,
            "content_padding_multiplier": self.content_padding_multiplier,
        }


def _safe_default_treatment() -> VisualTreatment:
    return VisualTreatment()


def _deterministic_treatment(
    slide: GeneratedSlide, position: int, total: int, design_tokens: dict[str, Any]
) -> VisualTreatment:
    """Fast deterministic visual treatment — no LLM call needed.
    Uses slide intent, content type, and position to derive smart defaults.
    Runs in <1ms per slide."""
    intent = (slide.intent or "").lower()
    has_image = bool(getattr(slide, "image_url", None))
    has_chart = bool(slide.chart and slide.chart.get("data"))
    has_table = bool(slide.table and slide.table.get("rows"))
    has_timeline = bool(slide.timeline and slide.timeline.get("events"))
    has_comparison = bool(slide.comparison and slide.comparison.get("columns"))
    has_diagram = bool(slide.diagram and slide.diagram.get("nodes"))
    has_stats = bool(slide.stat_blocks)
    has_bullets = bool(slide.bullets)
    is_first = position == 0
    is_last = position == total - 1

    # Determine variant based on content. Keep it deterministic, but vary
    # treatment enough that the deck feels directed instead of stamped.
    variant = "solid"
    if has_image:
        variant = "image"
    elif intent in {"title", "cover", "closing", "thanks"}:
        variant = "gradient"
    elif has_table or has_comparison or has_diagram:
        variant = "glass" if position % 2 else "solid"
    elif has_stats or has_chart:
        variant = "duotone" if position % 2 else "glass"
    elif position % 5 == 2:
        variant = "duotone"

    # Alignment: title/cover centered, rest left
    alignment = "center" if intent in {"title", "cover", "closing", "thanks"} else "left"

    # Density
    density = "balanced"
    if has_stats or has_chart:
        density = "sparse"
    elif has_table or has_comparison or has_timeline or has_diagram:
        density = "balanced"
    elif has_bullets and len(slide.bullets) > 4:
        density = "dense"

    # Emphasis
    emphasis = "typography"
    if has_stats:
        emphasis = "stats"
    elif has_image:
        emphasis = "image"
    elif has_chart:
        emphasis = "mixed"
    elif has_table or has_timeline or has_comparison or has_diagram:
        emphasis = "mixed"

    # Decorative style from visual direction
    visual_dir = design_tokens.get("visual_direction", "")
    decorative = "minimal"
    if "cyber" in visual_dir or "tech" in visual_dir or has_diagram:
        decorative = "tech"
    elif "luxury" in visual_dir or "gold" in visual_dir:
        decorative = "luxury"
    elif "bold" in visual_dir or "expressive" in visual_dir:
        decorative = "bold"

    pattern_cycle = ["grid", "dots", "gradient-mesh", "waves", "noise"]
    background_pattern: Optional[str] = pattern_cycle[position % len(pattern_cycle)]
    if has_chart or has_stats:
        background_pattern = "gradient-mesh"
    elif has_diagram:
        background_pattern = "grid"
    elif has_table or has_comparison:
        background_pattern = "dots"
    elif intent in {"title", "cover"}:
        background_pattern = "waves"

    # Icon map for feature slides
    icon_map: list[str] = []
    if has_bullets:
        icon_sets = [
            ["Target", "Zap", "Shield", "TrendingUp", "Layers", "Star"],
            ["Database", "Rocket", "Gauge", "Workflow", "BarChart3", "Lock"],
            ["SearchCheck", "Network", "DollarSign", "Boxes", "Repeat2", "Sparkles"],
        ]
        default_icons = icon_sets[position % len(icon_sets)]
        icon_map = [default_icons[i % len(default_icons)] for i in range(len(slide.bullets))]

    # Image treatment
    image_treatment = "gradient-scrim" if has_image else "none"

    return VisualTreatment(
        headline_alignment=alignment,
        headline_max_width_pct=72 if alignment == "center" else (58 + ((position % 3) * 6)),
        vertical_position="center" if is_first else ("top" if has_table or has_timeline or has_comparison or has_diagram else "center"),
        density_level=density,
        emphasis=emphasis,
        variant=variant,
        image_treatment=image_treatment,
        decorative_style=decorative,
        background_pattern=background_pattern,
        accent_placement=(["top-right", "bottom-left", "top-left", "bottom-right"][position % 4] if alignment == "left" else "none"),
        icon_style="lucide" if has_bullets else "none",
        icon_map=icon_map,
        accent_color_use="moderate" if position % 3 == 1 else "subtle",
        gradient_angle=(120 + position * 23) % 360,
        overlay_opacity=0.14 if has_image else 0.08,
        entry_animation=["fade-up", "slide-in", "zoom"][position % 3],
        stagger_children=has_bullets,
        emphasis_animation="pulse" if has_stats else None,
        section_gap_multiplier=1.0,
        content_padding_multiplier=1.0,
    )


class DesignDirector:
    """LLM-powered visual design stage using DESIGNER_LAYOUT models."""

    def __init__(self) -> None:
        self.router = ModelRouter()

    async def direct_slides(
        self,
        slides: list[GeneratedSlide],
        design_tokens: dict[str, Any],
        deck_purpose: str = "",
        deck_title: str = "",
        template_id: Optional[str] = None,
        mode: str = "standard",
    ) -> list[GeneratedSlide]:
        if not slides:
            return slides

        start = time.monotonic()

        # ── Standard mode: fast deterministic design (NO LLM calls) ──
        # Standard mode must be fast (<30s total). LLM design calls per
        # slide add 2-4s each, which is unacceptable. Use smart defaults
        # derived from slide intent and content type instead.
        if mode == "standard":
            for i, s in enumerate(slides):
                s.layout_params = _deterministic_treatment(s, i, len(slides), design_tokens).to_dict()
            self._enforce_rhythm(slides)
            elapsed = int((time.monotonic() - start) * 1000)
            logger.info("design_director_standard_fast", slide_count=len(slides), duration_ms=elapsed)
            return slides

        # ── Premium mode: full LLM design treatment ──────────────────
        tasks = [
            self._direct_one(s, design_tokens, deck_purpose, deck_title, template_id, i, len(slides), mode)
            for i, s in enumerate(slides)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("design_director_slide_failed", slide_index=i, error=str(result)[:200])
                slides[i].layout_params = _deterministic_treatment(
                    slides[i], i, len(slides), design_tokens
                ).to_dict()
            else:
                slides[i].layout_params = result.to_dict()
        self._enforce_rhythm(slides)

        elapsed = int((time.monotonic() - start) * 1000)
        logger.info("design_director_complete", slide_count=len(slides), duration_ms=elapsed)
        return slides

    @staticmethod
    def _enforce_rhythm(slides: list[GeneratedSlide]) -> None:
        """Avoid consecutive slides sharing the same treatment signature."""
        placements = ["top-right", "bottom-left", "top-left", "bottom-right"]
        variants = ["solid", "glass", "duotone", "gradient"]
        previous = ""
        for i, slide in enumerate(slides):
            lp = slide.layout_params or {}
            signature = "|".join(str(lp.get(k, "")) for k in ("variant", "accent_placement", "emphasis"))
            if i > 0 and signature == previous:
                lp["accent_placement"] = placements[i % len(placements)]
                lp["variant"] = variants[i % len(variants)]
                lp["gradient_angle"] = (int(lp.get("gradient_angle") or 135) + 37) % 360
                slide.layout_params = lp
                signature = "|".join(str(lp.get(k, "")) for k in ("variant", "accent_placement", "emphasis"))
            previous = signature

    async def _direct_one(
        self, slide: GeneratedSlide, design_tokens: dict[str, Any],
        deck_purpose: str, deck_title: str, template_id: Optional[str],
        position: int, total: int, mode: str,
    ) -> VisualTreatment:
        prompt = _build_design_prompt(slide, design_tokens, deck_purpose, deck_title, template_id, position, total)
        try:
            response = await safe_complete(
                router=self.router,
                primary_task=TaskType.DESIGNER_LAYOUT,
                fallback_task=TaskType.LAYOUT_OPTIMIZATION,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                mode=mode,
                max_tokens=800,
                temperature=0.7,
                phase=f"v4_design_director_{slide.index}",
                timeout_s=12.0 if mode == "premium" else 6.0,
                fallback_timeout_s=8.0,
            )
            content = response.content if hasattr(response, 'content') else str(response)
            data = safe_json_loads(content)
            return VisualTreatment(
                headline_alignment=data.get("headline_alignment", "left"),
                headline_max_width_pct=data.get("headline_max_width_pct", 65),
                vertical_position=data.get("vertical_position", "center"),
                density_level=data.get("density_level", "balanced"),
                emphasis=data.get("emphasis", "typography"),
                variant=data.get("variant", "solid"),
                image_treatment=data.get("image_treatment", "gradient-scrim"),
                decorative_style=data.get("decorative_style", "minimal"),
                background_pattern=data.get("background_pattern"),
                accent_placement=data.get("accent_placement", "top-left"),
                icon_style=data.get("icon_style", "lucide"),
                icon_map=data.get("icon_map", []),
                accent_color_use=data.get("accent_color_use", "subtle"),
                gradient_angle=data.get("gradient_angle", 135),
                overlay_opacity=data.get("overlay_opacity", 0.15),
                entry_animation=data.get("entry_animation", "fade-up"),
                stagger_children=data.get("stagger_children", True),
                emphasis_animation=data.get("emphasis_animation"),
                section_gap_multiplier=data.get("section_gap_multiplier", 1.0),
                content_padding_multiplier=data.get("content_padding_multiplier", 1.0),
            )
        except Exception as e:
            logger.warning("design_director_llm_failed", slide_index=slide.index, error=str(e)[:200])
            return _deterministic_treatment(slide, position, total, design_tokens)


def _build_design_prompt(
    slide: GeneratedSlide, design_tokens: dict[str, Any],
    deck_purpose: str, deck_title: str, template_id: Optional[str],
    position: int, total: int,
) -> str:
    palette = design_tokens.get("palette", {})
    typography = design_tokens.get("typography", {})
    visual_direction = design_tokens.get("visual_direction", "minimal_dark")
    style_family = design_tokens.get("style_family", "modern_professional")
    heading_cfg = typography.get("heading", "Inter") if isinstance(typography, dict) else "Inter"
    body_cfg = typography.get("body", "Inter") if isinstance(typography, dict) else "Inter"
    heading_font = heading_cfg.get("family", "Inter") if isinstance(heading_cfg, dict) else str(heading_cfg or "Inter")
    body_font = body_cfg.get("family", "Inter") if isinstance(body_cfg, dict) else str(body_cfg or "Inter")

    has_image = bool(getattr(slide, "image_url", None))
    has_chart = bool(slide.chart and slide.chart.get("data"))
    has_stats = bool(slide.stat_blocks)
    has_bullets = bool(slide.bullets)
    has_quote = bool(slide.quote and slide.quote.get("text"))
    has_team = bool(slide.team_members)
    has_timeline = bool(slide.timeline)
    has_comparison = bool(slide.comparison)
    has_diagram = bool(slide.diagram)
    has_table = bool(slide.table)

    content_type = "text"
    if has_chart: content_type = "chart"
    elif has_stats: content_type = "stats"
    elif has_image: content_type = "image_text"
    elif has_quote: content_type = "quote"
    elif has_table: content_type = "table"
    elif has_timeline: content_type = "timeline"
    elif has_comparison: content_type = "comparison"
    elif has_diagram: content_type = "diagram"
    elif has_team: content_type = "team"
    elif has_bullets: content_type = "features"

    template_context = ""
    if template_id:
        try:
            from app.services.v4.template_engine import TemplateEngine

            template = TemplateEngine().get(template_id)
            if template:
                kit_sequence = [
                    str(z.get("kit_component") or "")
                    for z in template.layout_structure.get("zones", [])
                    if isinstance(z, dict) and z.get("kit_component")
                ]
                template_context = (
                    f"\nTEMPLATE: {template.name} ({template.category})\n"
                    f"Selected zone: {getattr(slide, 'template_zone_id', None) or 'auto'}; "
                    f"preferred kit: {getattr(slide, 'template_kit_component', None) or 'auto'}\n"
                    f"Deck rhythm kits: {', '.join(kit_sequence[:12])}\n"
                    "Use this as visual rhythm guidance. Do not display template labels.\n"
                )
        except Exception:
            template_context = f"\nTEMPLATE: {template_id}\n"

    is_first = position == 0
    is_last = position == total - 1

    return f"""You are a world-class presentation designer at a top agency. Design visual treatment for ONE slide.

DESIGN SYSTEM: direction={visual_direction}, style={style_family}
Colors: primary={palette.get('primary','#3B82F6')}, accent={palette.get('accent','#F59E0B')}, bg={palette.get('background','#0F172A')}
Fonts: heading={heading_font}, body={body_font}
{template_context}

SLIDE: position={position+1}/{total} ({'opener' if is_first else 'closer' if is_last else 'body'}), intent={slide.intent}, content_type={content_type}, has_image={has_image}
Headline: "{slide.headline[:120]}"

DESIGN THIS SLIDE. Output JSON only. Think: what makes this slide feel CRAFTED, not templated?

{{
    "headline_alignment": "left|center|right",
    "headline_max_width_pct": 40-90,
    "vertical_position": "top|center|bottom",
    "density_level": "sparse|balanced|dense",
    "emphasis": "typography|image|stats|quote|mixed",
    "variant": "solid|gradient|image|glass|duotone",
    "image_treatment": "full-bleed|masked|duotone|gradient-scrim|none",
    "decorative_style": "minimal|geometric|organic|tech|luxury|bold",
    "background_pattern": null or "dots|grid|waves|gradient-mesh|noise",
    "accent_placement": "top-left|top-right|bottom-left|bottom-right|none",
    "icon_style": "lucide|custom|none",
    "icon_map": ["IconName1","IconName2",...],
    "accent_color_use": "subtle|moderate|bold|none",
    "gradient_angle": 0-360,
    "overlay_opacity": 0.0-0.5,
    "entry_animation": "fade-up|slide-in|zoom|none",
    "stagger_children": true/false,
    "emphasis_animation": null or "pulse|glow|float",
    "section_gap_multiplier": 0.7-1.5,
    "content_padding_multiplier": 0.8-1.3
}}

RULES:
- Title/cover slides: bold typography, centered or left-aligned, gradient or image variant
- Stats/metrics: big numbers, stat emphasis, sparse density
- Features/bullets: icon_map with relevant Lucide icons, glass or solid variant
- Team: centered, balanced density, subtle accents
- Chart/data: emphasis on the data, clean backgrounds
- Closing/thanks: bold, centered, image variant if image available
- NEVER use the same treatment for consecutive slides — vary rhythm
- Match decorative_style to the visual_direction mood"""
