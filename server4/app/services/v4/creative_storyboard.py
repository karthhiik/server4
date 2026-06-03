"""Deterministic creative storyboard for V4 decks.

This module is a compile-time creative director. It never rewrites slide
content and never calls an LLM. It reads the real generated slide fields and
produces visual guidance that downstream layout/rhythm/rendering layers can
use to make the deck feel intentionally directed instead of template-stamped.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class SlideCreativeDirection:
    """Visual direction for one slide, derived only from existing slide data."""

    slide_index: int
    role: str
    preferred_kits: tuple[str, ...]
    background_style: str
    background_pattern: str
    image_role: str
    density_target: str
    emphasis: str
    headline_alignment: str
    vertical_position: str
    accent_placement: str
    gradient_angle: int
    overlay_opacity: float
    review_reasons: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slide_index": self.slide_index,
            "role": self.role,
            "preferred_kits": list(self.preferred_kits),
            "background_style": self.background_style,
            "background_pattern": self.background_pattern,
            "image_role": self.image_role,
            "density_target": self.density_target,
            "emphasis": self.emphasis,
            "headline_alignment": self.headline_alignment,
            "vertical_position": self.vertical_position,
            "accent_placement": self.accent_placement,
            "gradient_angle": self.gradient_angle,
            "overlay_opacity": self.overlay_opacity,
            "review_reasons": list(self.review_reasons),
        }


def build_creative_storyboard(
    *,
    slides: list[Any],
    deck_title: Optional[str] = None,
    deck_purpose: str = "",
    design_tokens: Optional[Mapping[str, Any]] = None,
    template_id: Optional[str] = None,
    image_urls: Optional[Mapping[int, str]] = None,
) -> dict[int, SlideCreativeDirection]:
    """Build a per-slide creative direction map.

    The output is deterministic and scoped to visual treatment only. It uses
    template/theme data as boundaries, not as replacement content.
    """
    if not slides:
        return {}

    image_urls = image_urls or {}
    seed = _stable_seed("|".join([
        str(deck_title or ""),
        str(deck_purpose or ""),
        str(template_id or ""),
        str((design_tokens or {}).get("visual_direction") or ""),
    ]))
    total = len(slides)
    out: dict[int, SlideCreativeDirection] = {}

    previous_background = ""
    previous_role = ""
    for position, slide in enumerate(slides):
        slide_index = int(getattr(slide, "index", position) or position)
        role = _role_for_slide(slide, position, total)
        if role == previous_role and role not in {"proof", "data"}:
            role = _alternate_role(role, slide, position, total)

        content = _content_profile(slide, bool(image_urls.get(slide_index)))
        preferred_kits = _preferred_kits(role, content)
        background_style = _background_style(role, content)
        background_pattern = _background_pattern(role, content, position, seed)
        if background_pattern == previous_background:
            background_pattern = _cycle_pattern(position + seed + 1)

        image_role = _image_role(role, content)
        density_target = _density_target(role, content)
        emphasis = _emphasis(role, content)
        headline_alignment = "center" if role in {"opener", "ask", "closing", "quote"} else "left"
        vertical_position = _vertical_position(role, content)
        accent_placement = _accent_placement(position, seed, headline_alignment)
        gradient_angle = (90 + (position * 29) + (seed % 73)) % 360
        overlay_opacity = _overlay_opacity(background_style, content)

        direction = SlideCreativeDirection(
            slide_index=slide_index,
            role=role,
            preferred_kits=preferred_kits,
            background_style=background_style,
            background_pattern=background_pattern,
            image_role=image_role,
            density_target=density_target,
            emphasis=emphasis,
            headline_alignment=headline_alignment,
            vertical_position=vertical_position,
            accent_placement=accent_placement,
            gradient_angle=gradient_angle,
            overlay_opacity=overlay_opacity,
            review_reasons=_review_reasons(role, content),
        )
        out[slide_index] = direction
        previous_background = background_pattern
        previous_role = role

    return out


def merge_direction_into_layout_params(
    existing: Optional[Mapping[str, Any]],
    direction: Optional[SlideCreativeDirection],
) -> dict[str, Any]:
    """Merge storyboard metadata into layoutParams without discarding existing keys."""
    merged = dict(existing or {})
    if not direction:
        return merged

    # Respect explicit design-director choices, then fill missing/weak spots.
    merged.setdefault("headline_alignment", direction.headline_alignment)
    merged.setdefault("vertical_position", direction.vertical_position)
    merged.setdefault("density_level", direction.density_target)
    merged.setdefault("emphasis", direction.emphasis)
    merged.setdefault("background_pattern", direction.background_pattern)
    merged.setdefault("accent_placement", direction.accent_placement)
    merged.setdefault("gradient_angle", direction.gradient_angle)
    merged.setdefault("overlay_opacity", direction.overlay_opacity)

    merged["creative_role"] = direction.role
    merged["background_style"] = direction.background_style
    merged["image_role"] = direction.image_role
    merged["preferred_kits"] = list(direction.preferred_kits)
    merged["visual_review_reasons"] = list(direction.review_reasons)
    return merged


def _stable_seed(value: str) -> int:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _content_profile(slide: Any, has_resolved_image: bool) -> dict[str, bool | int]:
    bullets = list(getattr(slide, "bullets", None) or [])
    body = str(getattr(slide, "body", None) or "")
    return {
        "has_image": has_resolved_image or bool(getattr(slide, "image_url", None) or getattr(slide, "image_prompt", None)),
        "has_chart": bool(getattr(slide, "chart", None)),
        "has_table": bool(getattr(slide, "table", None)),
        "has_timeline": bool(getattr(slide, "timeline", None)),
        "has_comparison": bool(getattr(slide, "comparison", None)),
        "has_diagram": bool(getattr(slide, "diagram", None)),
        "has_stats": bool(getattr(slide, "stat_blocks", None)),
        "has_quote": bool(getattr(slide, "quote", None)),
        "has_team": bool(getattr(slide, "team_members", None)),
        "bullet_count": len(bullets),
        "word_count": len(" ".join([body, " ".join(str(b) for b in bullets)]).split()),
    }


def _role_for_slide(slide: Any, position: int, total: int) -> str:
    intent = str(getattr(slide, "intent", "") or "").lower().replace("_", " ")
    layout = str(getattr(slide, "layout", "") or "").lower()
    if position == 0 or any(k in intent for k in ("title", "cover", "intro")):
        return "opener"
    if position >= total - 1 or any(k in intent for k in ("ask", "closing", "thanks")):
        return "ask" if "ask" in intent else "closing"
    if any(k in intent for k in ("problem", "pain", "challenge")):
        return "problem"
    if any(k in intent for k in ("solution", "product", "demo")):
        return "solution"
    if any(k in intent for k in ("market", "financial", "traction", "metric", "revenue")):
        return "data"
    if any(k in intent for k in ("team", "founder", "advisor")):
        return "trust"
    if any(k in intent for k in ("roadmap", "timeline", "process", "how")) or "timeline" in layout:
        return "process"
    if any(k in intent for k in ("competition", "comparison", "pricing")):
        return "comparison"
    if any(k in intent for k in ("quote", "testimonial", "customer")):
        return "quote"
    return "proof" if position / max(total - 1, 1) > 0.55 else "narrative"


def _alternate_role(role: str, slide: Any, position: int, total: int) -> str:
    if role == "narrative":
        return "proof"
    if role == "proof":
        return "narrative"
    return _role_for_slide(slide, position, total)


def _preferred_kits(role: str, content: Mapping[str, Any]) -> tuple[str, ...]:
    if content.get("has_team"):
        return ("TeamMemberStrip", "TeamGrid")
    if content.get("has_chart") or content.get("has_stats"):
        return ("MetricsDashboard", "StatHero", "ChartBlock", "FloatingStat")
    if content.get("has_table"):
        return ("DataTable", "MetricsDashboard")
    if content.get("has_timeline"):
        return ("Roadmap", "TimelineBlock", "ProcessFlow")
    if content.get("has_comparison"):
        return ("ProblemSolution", "ComparisonBlock", "BeforeAfter")
    if content.get("has_diagram"):
        return ("ProcessFlow", "DiagramBlock")
    if role in {"opener", "ask", "closing"}:
        return ("CoverSlide", "CinematicHero", "TitleHero", "DuotoneHero")
    if role == "solution" and content.get("has_image"):
        return ("AppMockup", "SplitContent", "SplitOverlap", "EditorialImage")
    if role in {"problem", "comparison"}:
        return ("ProblemSolution", "ComparisonBlock", "BentoGrid")
    if role == "quote":
        return ("QuoteHighlight", "TestimonialCard", "QuoteBlock")
    return ("BentoGrid", "ValuePropGrid", "FeatureGrid", "SplitContent")


def _background_style(role: str, content: Mapping[str, Any]) -> str:
    if content.get("has_image") and role in {"opener", "solution", "quote", "closing"}:
        return "image-led"
    if content.get("has_chart") or content.get("has_stats") or content.get("has_table"):
        return "data-surface"
    if role in {"opener", "ask", "closing"}:
        return "brand-hero"
    if role in {"problem", "comparison"}:
        return "contrast-surface"
    return "editorial-surface"


def _background_pattern(role: str, content: Mapping[str, Any], position: int, seed: int) -> str:
    if content.get("has_chart") or content.get("has_stats"):
        return "radial"
    if content.get("has_table") or content.get("has_comparison"):
        return "grid"
    if content.get("has_diagram") or role == "process":
        return "lines"
    if role in {"opener", "closing", "ask"}:
        return "waves"
    return _cycle_pattern(position + seed)


def _cycle_pattern(index: int) -> str:
    patterns = ("grid", "dots", "waves", "geometric", "lines", "radial")
    return patterns[index % len(patterns)]


def _image_role(role: str, content: Mapping[str, Any]) -> str:
    if not content.get("has_image"):
        return "none"
    if role in {"opener", "closing"}:
        return "hero-background"
    if role == "solution":
        return "product-proof"
    if role == "trust":
        return "portrait-proof"
    return "supporting-visual"


def _density_target(role: str, content: Mapping[str, Any]) -> str:
    if role in {"opener", "ask", "closing", "quote"}:
        return "sparse"
    if content.get("has_table") or content.get("has_comparison") or int(content.get("bullet_count") or 0) >= 5:
        return "dense"
    return "balanced"


def _emphasis(role: str, content: Mapping[str, Any]) -> str:
    if content.get("has_chart") or content.get("has_stats"):
        return "stats"
    if content.get("has_image"):
        return "image"
    if role in {"problem", "comparison"}:
        return "tension"
    if role in {"ask", "closing"}:
        return "decisive"
    return "typography"


def _vertical_position(role: str, content: Mapping[str, Any]) -> str:
    if role in {"opener", "ask", "closing"}:
        return "center"
    if content.get("has_table") or content.get("has_timeline") or content.get("has_comparison"):
        return "top"
    return "center"


def _accent_placement(position: int, seed: int, alignment: str) -> str:
    if alignment == "center":
        return "none"
    placements = ("top-right", "bottom-left", "top-left", "bottom-right")
    return placements[(position + seed) % len(placements)]


def _overlay_opacity(background_style: str, content: Mapping[str, Any]) -> float:
    if background_style == "image-led":
        return 0.38
    if content.get("has_chart") or content.get("has_stats"):
        return 0.12
    return 0.08


def _review_reasons(role: str, content: Mapping[str, Any]) -> tuple[str, ...]:
    reasons = [f"role:{role}"]
    if content.get("has_image"):
        reasons.append("image-aware")
    if content.get("has_chart") or content.get("has_stats"):
        reasons.append("data-emphasis")
    if content.get("has_table") or content.get("has_comparison"):
        reasons.append("dense-layout")
    return tuple(reasons)


__all__ = [
    "SlideCreativeDirection",
    "build_creative_storyboard",
    "merge_direction_into_layout_params",
]
