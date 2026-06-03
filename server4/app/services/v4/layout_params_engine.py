"""
Layout Parameter Engine — Hybrid Generative Positioning

This module provides bounded generative positioning for slide kits.
Instead of hardcoding every pixel, the LLM generates 6 positioning
parameters per slide, which kits consume via CSS variables.

This is the "hybrid" approach: templates provide the safety floor,
parameters provide the generative ceiling. Every slide feels custom
while remaining deterministic, fast, and safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SlideLayoutParams:
    """Bounded positioning parameters for a single slide.

    All values are constrained to safe ranges. The LLM generates these
    from content analysis, and the layout engine validates/clamps them.
    """

    headline_alignment: str = "left"  # "left" | "center" | "right"
    headline_max_width_pct: int = 68   # 50-85
    vertical_position: str = "bottom"  # "top" | "center" | "bottom"
    image_treatment: str = "gradient-scrim"  # "full-bleed" | "masked" | "duotone" | "gradient-scrim" | "none"
    density_level: str = "balanced"  # "sparse" | "balanced" | "dense"
    emphasis: str = "typography"  # "typography" | "image" | "stats" | "quote" | "mixed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "headline_alignment": self.headline_alignment,
            "headline_max_width_pct": self.headline_max_width_pct,
            "vertical_position": self.vertical_position,
            "image_treatment": self.image_treatment,
            "density_level": self.density_level,
            "emphasis": self.emphasis,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SlideLayoutParams":
        return cls(
            headline_alignment=_clamp_str(data.get("headline_alignment"), {"left", "center", "right"}, "left"),
            headline_max_width_pct=_clamp_int(data.get("headline_max_width_pct"), 50, 85, 68),
            vertical_position=_clamp_str(data.get("vertical_position"), {"top", "center", "bottom"}, "bottom"),
            image_treatment=_clamp_str(
                data.get("image_treatment"),
                {"full-bleed", "masked", "duotone", "gradient-scrim", "none"},
                "gradient-scrim",
            ),
            density_level=_clamp_str(data.get("density_level"), {"sparse", "balanced", "dense"}, "balanced"),
            emphasis=_clamp_str(
                data.get("emphasis"),
                {"typography", "image", "stats", "quote", "mixed"},
                "typography",
            ),
        )


# ── Validation helpers ─────────────────────────────────────────────


def _clamp_str(value: Any, allowed: set[str], default: str) -> str:
    if isinstance(value, str) and value in allowed:
        return value
    return default


def _clamp_int(value: Any, min_val: int, max_val: int, default: int) -> int:
    try:
        v = int(value)
        return max(min_val, min(max_val, v))
    except (TypeError, ValueError):
        return default


# ── Content-aware inference ────────────────────────────────────────


def infer_layout_params(
    *,
    intent: str,
    layout_hint: str,
    headline: str,
    subheadline: Optional[str],
    body: Optional[str],
    bullets: list[str],
    stat_blocks: list[dict[str, str]],
    quote: Optional[dict[str, str]],
    chart: Optional[dict[str, Any]],
    image_url: Optional[str],
    density_target: str = "medium",
) -> SlideLayoutParams:
    """Infer layout parameters from content shape without LLM involvement.

    This is the fast, deterministic path used when the LLM does not
    provide explicit layout_params. It analyzes content density, intent,
    and available elements to pick safe defaults.
    """
    intent_lower = (intent or "").lower()
    layout = (layout_hint or "").lower()

    # Emphasis inference
    emphasis = "typography"
    if stat_blocks and len(stat_blocks) >= 2:
        emphasis = "stats"
    elif quote and quote.get("text"):
        emphasis = "quote"
    elif chart and chart.get("data"):
        emphasis = "mixed"
    elif image_url and not bullets and not body:
        emphasis = "image"

    # Density inference — explicit density_target overrides word count heuristic
    density = "balanced"
    if density_target == "minimal":
        density = "sparse"
    elif density_target == "high":
        density = "dense"
    else:
        content_word_count = (
            len((headline or "").split())
            + len((subheadline or "").split())
            + len((body or "").split())
            + sum(len(b.split()) for b in bullets)
        )
        if content_word_count < 15:
            density = "sparse"
        elif content_word_count > 80:
            density = "dense"

    # Vertical position inference
    vertical = "bottom"
    if intent_lower in {"title", "cover", "closing", "ask"}:
        vertical = "bottom"
    elif layout in {"title-only", "bullet-points"}:
        vertical = "center"
    elif emphasis == "stats":
        vertical = "center"

    # Headline alignment inference
    alignment = "left"
    if intent_lower in {"title", "cover", "vision", "closing"}:
        alignment = "left"
    elif emphasis == "stats" and len(stat_blocks) >= 3:
        alignment = "center"
    elif layout in {"quote", "testimonial-accent"}:
        alignment = "center"

    # Image treatment inference
    image_treatment = "gradient-scrim"
    if not image_url:
        image_treatment = "none"
    elif intent_lower in {"title", "cover"}:
        image_treatment = "gradient-scrim"
    elif layout in {"duotone-cover", "duotone-gradient"}:
        image_treatment = "duotone"
    elif layout in {"image-full", "hero"}:
        image_treatment = "full-bleed"

    # Headline max width inference
    max_width = 68
    if emphasis == "stats":
        max_width = 75
    elif density == "dense":
        max_width = 60
    elif len((headline or "").split()) <= 4:
        max_width = 55

    return SlideLayoutParams(
        headline_alignment=alignment,
        headline_max_width_pct=max_width,
        vertical_position=vertical,
        image_treatment=image_treatment,
        density_level=density,
        emphasis=emphasis,
    )


# ── Prompt fragment for LLM ──────────────────────────────────────


LAYOUT_PARAMS_PROMPT_FRAGMENT = """

LAYOUT PARAMETERS (generate alongside content):
After writing the slide content, choose positioning parameters that best serve this content.
These parameters control HOW the content is positioned on the slide (not WHAT the content is).

Generate a `layout_params` object with these exact fields:
{
  "headline_alignment": "left" | "center" | "right",
  "headline_max_width_pct": 50-85 (integer),
  "vertical_position": "top" | "center" | "bottom",
  "image_treatment": "full-bleed" | "masked" | "duotone" | "gradient-scrim" | "none",
  "density_level": "sparse" | "balanced" | "dense",
  "emphasis": "typography" | "image" | "stats" | "quote" | "mixed"
}

Guidelines:
- headline_alignment = "center" for stat-hero, quote, or testimonial slides
- headline_alignment = "left" for narrative, problem, solution, market slides
- vertical_position = "bottom" for title/cover slides (gives image breathing room)
- vertical_position = "center" for stat-heavy or data slides
- image_treatment = "duotone" when layout_hint is "duotone-cover" or "duotone-gradient"
- image_treatment = "gradient-scrim" for cinematic hero slides with text overlay
- image_treatment = "none" when there is no image
- density_level = "sparse" for title/cover slides with minimal text
- density_level = "dense" for market, traction, business_model slides with many stats
- emphasis = "stats" when stat_blocks are the primary content
- emphasis = "image" when the slide is primarily visual with minimal text
- emphasis = "typography" for text-driven narrative slides
"""


# ── Prop injection ─────────────────────────────────────────────────


def inject_layout_params(
    props: dict[str, Any],
    layout_params: Optional[SlideLayoutParams | dict[str, Any]],
) -> dict[str, Any]:
    """Embed validated layout params into kit props as `layoutParams`.

    Kits that understand layoutParams will read it and adjust positioning.
    Kits that don't simply ignore it — backward compatibility is preserved.
    """
    if layout_params is not None:
        if isinstance(layout_params, SlideLayoutParams):
            props["layoutParams"] = layout_params.to_dict()
        elif isinstance(layout_params, dict):
            props["layoutParams"] = SlideLayoutParams.from_dict(layout_params).to_dict()
    return props
