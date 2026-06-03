"""Slot-level composition metadata for compiled V4 slides.

The current renderer is kit-based. This module adds a stable composition
contract on top of that path: each compiled slide carries virtual-canvas slots
that validators, exports, and future renderers can inspect without parsing JSX.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


VIRTUAL_CANVAS: dict[str, Any] = {
    "width": 1920,
    "height": 1080,
    "safe_zone": {"top": 48, "bottom": 48, "left": 64, "right": 64},
    "grid": {"columns": 12, "gutter": 24, "baseline": 8},
}


@dataclass(frozen=True)
class ContentSlot:
    id: str
    semantic_role: str
    visual_priority: int
    x_pct: float
    y_pct: float
    width_pct: float
    height_pct: float
    min_chars: int = 0
    max_chars: int = 240
    max_lines: int = 3
    font_level: str = "body"
    allowed_types: tuple[str, ...] = ("text",)
    required: bool = False
    overflow_strategy: str = "summarize"
    alignment: str = "left"
    tone: str = "confident"
    data_binding: str | None = None
    content_preview: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "semantic_role": self.semantic_role,
            "visual_priority": self.visual_priority,
            "x_pct": self.x_pct,
            "y_pct": self.y_pct,
            "width_pct": self.width_pct,
            "height_pct": self.height_pct,
            "min_chars": self.min_chars,
            "max_chars": self.max_chars,
            "max_lines": self.max_lines,
            "font_level": self.font_level,
            "allowed_types": list(self.allowed_types),
            "required": self.required,
            "overflow_strategy": self.overflow_strategy,
            "alignment": self.alignment,
            "tone": self.tone,
            "data_binding": self.data_binding,
            "content_preview": self.content_preview[:120],
        }


@dataclass(frozen=True)
class SlideCompositionPlan:
    canvas: dict[str, Any]
    layout_key: str
    kit_component: str
    density: str
    slots: list[ContentSlot] = field(default_factory=list)
    fallback_layouts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "canvas": self.canvas,
            "layout_key": self.layout_key,
            "kit_component": self.kit_component,
            "density": self.density,
            "slots": [slot.to_dict() for slot in self.slots],
            "fallback_layouts": self.fallback_layouts,
        }


FALLBACK_LAYOUTS: dict[str, list[str]] = {
    "StatHero": ["ChartBlock", "FeatureGrid", "TitleHero"],
    "ChartBlock": ["StatHero", "DataTable", "FeatureGrid"],
    "FeatureGrid": ["BentoGrid", "ComparisonBlock", "TitleHero"],
    "TimelineBlock": ["Roadmap", "ProcessFlow", "FeatureGrid"],
    "ComparisonBlock": ["FeatureGrid", "DataTable", "TitleHero"],
    "DiagramBlock": ["ProcessFlow", "FeatureGrid", "TitleHero"],
    "FullBleedImage": ["EditorialImage", "SplitContent", "TitleHero"],
    "TitleHero": ["CinematicHero", "DuotoneHero", "QuoteBlock"],
}


def build_composition_plan(
    *,
    kit_component: str,
    props: Mapping[str, Any],
    layout_key: str,
    density: str,
) -> SlideCompositionPlan:
    slots = _slots_for_kit(kit_component, props)
    return SlideCompositionPlan(
        canvas=VIRTUAL_CANVAS.copy(),
        layout_key=layout_key,
        kit_component=kit_component,
        density=density,
        slots=slots,
        fallback_layouts=FALLBACK_LAYOUTS.get(kit_component, ["TitleHero"]),
    )


def _slots_for_kit(kit: str, props: Mapping[str, Any]) -> list[ContentSlot]:
    align = _layout_alignment(props)
    headline = str(props.get("headline") or props.get("title") or "")
    subheadline = str(props.get("subheadline") or props.get("subtitle") or "")

    if kit in {"TitleHero", "CinematicHero", "DuotoneHero", "FullBleedImage"}:
        return [
            ContentSlot("headline", "primary_persuasion", 10, 6, 48, 68, 20, 4, 110, 2, "display", required=True, alignment=align, content_preview=headline),
            ContentSlot("subheadline", "explanation", 7, 6, 70, 58, 12, 0, 180, 3, "h3", alignment=align, content_preview=subheadline),
        ]
    if kit in {"StatHero", "FloatingStat"}:
        return [
            ContentSlot("headline", "primary_persuasion", 9, 10, 12, 80, 16, 4, 120, 2, "h1", required=True, alignment=align, content_preview=headline),
            ContentSlot("stats", "evidence", 10, 10, 38, 80, 38, 1, 80, 1, "display", ("number", "text"), True, "morph_layout", align, data_binding="stat_blocks"),
        ]
    if kit == "ChartBlock":
        return [
            ContentSlot("headline", "primary_persuasion", 8, 6, 8, 58, 14, 4, 120, 2, "h2", required=True, alignment=align, content_preview=headline),
            ContentSlot("chart", "evidence", 10, 8, 30, 84, 52, 1, 0, 1, "body", ("chart",), True, "morph_layout", "center", data_binding="chart"),
        ]
    if kit in {"DiagramBlock", "TimelineBlock", "ProcessFlow", "Roadmap"}:
        return [
            ContentSlot("headline", "primary_persuasion", 8, 6, 8, 62, 14, 4, 120, 2, "h2", required=True, alignment=align, content_preview=headline),
            ContentSlot("visual", "explanation", 9, 8, 30, 84, 52, 1, 120, 4, "body", ("diagram", "timeline"), True, "morph_layout", "center"),
        ]
    if kit in {"FeatureGrid", "GlassCard", "BentoGrid", "ComparisonBlock", "TeamGrid"}:
        return [
            ContentSlot("headline", "primary_persuasion", 8, 6, 8, 62, 14, 4, 120, 2, "h2", required=True, alignment=align, content_preview=headline),
            ContentSlot("cards", "evidence", 8, 6, 30, 88, 54, 1, 120, 4, "body", ("text", "icon", "table"), True, "split_slot", "left"),
        ]
    return [
        ContentSlot("headline", "primary_persuasion", 8, 8, 12, 72, 16, 4, 120, 2, "h2", required=True, alignment=align, content_preview=headline),
        ContentSlot("body", "explanation", 6, 8, 34, 72, 46, 0, 360, 6, "body", alignment=align),
    ]


def _layout_alignment(props: Mapping[str, Any]) -> str:
    lp = props.get("layoutParams")
    if isinstance(lp, Mapping):
        value = lp.get("headline_alignment")
        if value in {"left", "center", "right"}:
            return str(value)
    return "left"
