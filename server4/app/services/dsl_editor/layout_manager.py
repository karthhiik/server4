"""
Layout Manager -- Per-slide and per-deck layout switching with content reflow.

12 layout types (from V7 Plan Section 21.2):
    center-focus, two-column, three-column, split-screen,
    full-bleed-image, top-header, sidebar, grid-2x2, grid-3x1,
    timeline, comparison, quote

Content automatically reflows into the new layout structure.
Smart layout suggestion analyses content and recommends optimal layout.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import structlog

from app.models.dsl_v2 import (
    ElementStyle,
    ElementType,
    LayoutType,
    PresentationDSL,
    SlideDSL,
    SlideContentV2,
    SlideElement,
    SlidePosition,
    SlideSize,
    SlideType,
)

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Layout geometry definitions
# ---------------------------------------------------------------------------

# Predefined element placement rules per layout
# Each layout defines regions: {region_name: {x, y, width, height}}
LAYOUT_GEOMETRY: Dict[str, Dict[str, Dict[str, float]]] = {
    "center-focus": {
        "title": {"x": 0.1, "y": 0.25, "width": 0.8, "height": 0.15},
        "subtitle": {"x": 0.15, "y": 0.42, "width": 0.7, "height": 0.1},
        "body": {"x": 0.15, "y": 0.55, "width": 0.7, "height": 0.3},
    },
    "split-screen": {
        "title": {"x": 0.03, "y": 0.05, "width": 0.45, "height": 0.12},
        "body": {"x": 0.03, "y": 0.2, "width": 0.45, "height": 0.7},
        "visual": {"x": 0.52, "y": 0.05, "width": 0.45, "height": 0.9},
    },
    "text-left-visual-right": {
        "title": {"x": 0.03, "y": 0.08, "width": 0.45, "height": 0.12},
        "body": {"x": 0.03, "y": 0.22, "width": 0.45, "height": 0.65},
        "visual": {"x": 0.52, "y": 0.08, "width": 0.45, "height": 0.84},
    },
    "text-right-visual-left": {
        "title": {"x": 0.52, "y": 0.08, "width": 0.45, "height": 0.12},
        "body": {"x": 0.52, "y": 0.22, "width": 0.45, "height": 0.65},
        "visual": {"x": 0.03, "y": 0.08, "width": 0.45, "height": 0.84},
    },
    "top-bottom": {
        "title": {"x": 0.05, "y": 0.05, "width": 0.9, "height": 0.1},
        "body": {"x": 0.05, "y": 0.18, "width": 0.9, "height": 0.35},
        "visual": {"x": 0.05, "y": 0.56, "width": 0.9, "height": 0.4},
    },
    "grid-2x2": {
        "title": {"x": 0.05, "y": 0.03, "width": 0.9, "height": 0.1},
        "cell_0": {"x": 0.05, "y": 0.16, "width": 0.43, "height": 0.38},
        "cell_1": {"x": 0.52, "y": 0.16, "width": 0.43, "height": 0.38},
        "cell_2": {"x": 0.05, "y": 0.57, "width": 0.43, "height": 0.38},
        "cell_3": {"x": 0.52, "y": 0.57, "width": 0.43, "height": 0.38},
    },
    "grid-3x1": {
        "title": {"x": 0.05, "y": 0.03, "width": 0.9, "height": 0.1},
        "cell_0": {"x": 0.03, "y": 0.16, "width": 0.3, "height": 0.78},
        "cell_1": {"x": 0.35, "y": 0.16, "width": 0.3, "height": 0.78},
        "cell_2": {"x": 0.67, "y": 0.16, "width": 0.3, "height": 0.78},
    },
    "overlay": {
        "background": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
        "title": {"x": 0.1, "y": 0.3, "width": 0.8, "height": 0.15},
        "body": {"x": 0.15, "y": 0.5, "width": 0.7, "height": 0.2},
    },
    "comparison": {
        "title": {"x": 0.05, "y": 0.03, "width": 0.9, "height": 0.1},
        "left_col": {"x": 0.05, "y": 0.16, "width": 0.42, "height": 0.78},
        "right_col": {"x": 0.53, "y": 0.16, "width": 0.42, "height": 0.78},
    },
    "timeline": {
        "title": {"x": 0.05, "y": 0.03, "width": 0.9, "height": 0.1},
        "timeline_bar": {"x": 0.05, "y": 0.45, "width": 0.9, "height": 0.05},
        "body": {"x": 0.05, "y": 0.16, "width": 0.9, "height": 0.25},
        "details": {"x": 0.05, "y": 0.55, "width": 0.9, "height": 0.38},
    },
    "kpi-dashboard": {
        "title": {"x": 0.05, "y": 0.03, "width": 0.9, "height": 0.1},
        "metric_0": {"x": 0.03, "y": 0.16, "width": 0.22, "height": 0.35},
        "metric_1": {"x": 0.27, "y": 0.16, "width": 0.22, "height": 0.35},
        "metric_2": {"x": 0.51, "y": 0.16, "width": 0.22, "height": 0.35},
        "metric_3": {"x": 0.75, "y": 0.16, "width": 0.22, "height": 0.35},
        "chart": {"x": 0.05, "y": 0.55, "width": 0.9, "height": 0.4},
    },
    "quote": {
        "quote_mark": {"x": 0.08, "y": 0.2, "width": 0.1, "height": 0.15},
        "body": {"x": 0.12, "y": 0.3, "width": 0.76, "height": 0.3},
        "attribution": {"x": 0.3, "y": 0.65, "width": 0.4, "height": 0.1},
    },
    "bullets": {
        "title": {"x": 0.05, "y": 0.05, "width": 0.9, "height": 0.12},
        "body": {"x": 0.08, "y": 0.2, "width": 0.84, "height": 0.72},
    },
    "team-grid": {
        "title": {"x": 0.05, "y": 0.03, "width": 0.9, "height": 0.1},
        "member_0": {"x": 0.05, "y": 0.16, "width": 0.2, "height": 0.5},
        "member_1": {"x": 0.28, "y": 0.16, "width": 0.2, "height": 0.5},
        "member_2": {"x": 0.51, "y": 0.16, "width": 0.2, "height": 0.5},
        "member_3": {"x": 0.74, "y": 0.16, "width": 0.2, "height": 0.5},
    },
    "chart": {
        "title": {"x": 0.05, "y": 0.03, "width": 0.9, "height": 0.1},
        "chart_area": {"x": 0.05, "y": 0.16, "width": 0.9, "height": 0.78},
    },
    "blank": {},
}


class LayoutSuggestion:
    """AI-powered layout recommendation for a slide."""

    __slots__ = ("layout", "confidence", "reason", "content_fit_score")

    def __init__(
        self,
        layout: LayoutType,
        confidence: float,
        reason: str,
        content_fit_score: float = 0.0,
    ):
        self.layout = layout
        self.confidence = confidence
        self.reason = reason
        self.content_fit_score = content_fit_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layout": self.layout.value,
            "confidence": round(self.confidence, 2),
            "reason": self.reason,
            "content_fit_score": round(self.content_fit_score, 2),
        }


class ContentReflowResult:
    """Result of reflowing content into a new layout."""

    __slots__ = ("success", "layout", "elements_repositioned", "warnings", "error")

    def __init__(
        self,
        success: bool,
        layout: Optional[LayoutType] = None,
        elements_repositioned: int = 0,
        warnings: Optional[List[str]] = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.layout = layout
        self.elements_repositioned = elements_repositioned
        self.warnings = warnings or []
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "layout": self.layout.value if self.layout else None,
            "elements_repositioned": self.elements_repositioned,
            "warnings": self.warnings,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Layout Manager
# ---------------------------------------------------------------------------

class LayoutManager:
    """
    Handles layout switching with automatic content reflow.

    When a user changes a slide's layout, elements are repositioned
    according to the new layout's geometry rules. Content is never
    lost -- only repositioned.
    """

    def __init__(self, dsl: PresentationDSL):
        self._dsl = dsl

    @property
    def dsl(self) -> PresentationDSL:
        return self._dsl

    # ── Per-slide layout change ───────────────────────────────────

    def change_slide_layout(
        self,
        slide_id: str,
        new_layout: LayoutType,
        reflow: bool = True,
    ) -> ContentReflowResult:
        """
        Change a slide's layout and optionally reflow elements.

        If reflow=True, elements are repositioned according to the
        new layout's geometry. If False, only the layout enum changes.
        """
        slide = self._find_slide(slide_id)
        if slide is None:
            return ContentReflowResult(
                success=False, error=f"Slide '{slide_id}' not found"
            )

        old_layout = slide.layout
        slide.layout = new_layout

        if not reflow or old_layout == new_layout:
            return ContentReflowResult(
                success=True, layout=new_layout, elements_repositioned=0
            )

        # Reflow elements
        repositioned = self._reflow_elements(slide, new_layout)

        logger.info(
            "layout_changed",
            slide_id=slide_id,
            old=old_layout.value,
            new=new_layout.value,
            elements_moved=repositioned,
        )

        return ContentReflowResult(
            success=True,
            layout=new_layout,
            elements_repositioned=repositioned,
        )

    # ── Per-deck layout template ──────────────────────────────────

    def apply_deck_layout(
        self,
        layout: LayoutType,
        exclude_types: Optional[List[SlideType]] = None,
    ) -> Dict[str, Any]:
        """
        Apply a consistent layout across all content slides.
        Title and closing slides retain their default layout.
        """
        excluded = set(exclude_types or [SlideType.TITLE_SLIDE, SlideType.CLOSING_SLIDE])
        affected = 0

        for slide in self._dsl.slides:
            if slide.type in excluded:
                continue
            old = slide.layout
            slide.layout = layout
            self._reflow_elements(slide, layout)
            if old != layout:
                affected += 1

        logger.info("deck_layout_applied", layout=layout.value, affected=affected)

        return {
            "layout": layout.value,
            "slides_affected": affected,
            "total_slides": len(self._dsl.slides),
            "excluded_types": [t.value for t in excluded],
        }

    # ── Smart layout suggestion ───────────────────────────────────

    def suggest_layout(self, slide_id: str) -> List[LayoutSuggestion]:
        """
        Analyse slide content and suggest the best layout options.

        Heuristic scoring based on:
        - Content density (text length, bullet count)
        - Content type (has image, chart, team, timeline, etc.)
        - Slide type semantics
        """
        slide = self._find_slide(slide_id)
        if slide is None:
            return []

        suggestions: List[LayoutSuggestion] = []
        c = slide.content

        # Score each layout type
        for lt in LayoutType:
            score, reason = self._score_layout(slide, lt)
            if score > 0.1:
                suggestions.append(LayoutSuggestion(
                    layout=lt,
                    confidence=score,
                    reason=reason,
                    content_fit_score=score,
                ))

        # Sort by confidence, top 3
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions[:5]

    def suggest_layouts_for_deck(self) -> Dict[str, List[LayoutSuggestion]]:
        """Suggest layouts for every slide in the deck."""
        return {
            slide.id: self.suggest_layout(slide.id)
            for slide in self._dsl.slides
        }

    # ── Layout geometry queries ───────────────────────────────────

    def get_layout_geometry(self, layout: LayoutType) -> Dict[str, Dict[str, float]]:
        """Get the region geometry for a layout type."""
        return LAYOUT_GEOMETRY.get(layout.value, LAYOUT_GEOMETRY["center-focus"])

    def get_available_layouts(self) -> List[Dict[str, Any]]:
        """List all available layouts with metadata."""
        layouts = []
        for lt in LayoutType:
            geo = LAYOUT_GEOMETRY.get(lt.value, {})
            layouts.append({
                "id": lt.value,
                "name": lt.value.replace("-", " ").replace("_", " ").title(),
                "regions": list(geo.keys()),
                "region_count": len(geo),
            })
        return layouts

    # ── Internal scoring ──────────────────────────────────────────

    def _score_layout(
        self, slide: SlideDSL, layout: LayoutType
    ) -> Tuple[float, str]:
        """Score how well a layout fits the slide content."""
        c = slide.content
        score = 0.0
        reason = ""

        has_image = bool(c.image_url or c.image_prompt)
        has_chart = bool(c.chart_data)
        has_bullets = bool(c.bullets and len(c.bullets) > 0)
        has_team = bool(c.team_members and len(c.team_members) > 0)
        has_timeline = bool(c.timeline_items and len(c.timeline_items) > 0)
        has_comparison = bool(c.comparison_items and len(c.comparison_items) > 0)
        has_kpi = bool(c.kpi_metrics and len(c.kpi_metrics) > 0)
        has_quote = bool(c.quote_text)
        bullet_count = len(c.bullets) if c.bullets else 0
        text_heavy = bool(c.body_text and len(c.body_text) > 200)
        title_len = len(c.title) if c.title else 0

        if layout == LayoutType.CENTER_FOCUS:
            if slide.type == SlideType.TITLE_SLIDE:
                score, reason = 0.95, "Title slides work best centered"
            elif slide.type == SlideType.CLOSING_SLIDE:
                score, reason = 0.9, "Closing slides suit center focus"
            elif not has_image and not has_chart and bullet_count <= 3:
                score, reason = 0.6, "Simple content suits center layout"
            else:
                score, reason = 0.3, "Adequate fallback"

        elif layout == LayoutType.SPLIT_SCREEN:
            if has_image and (has_bullets or text_heavy):
                score, reason = 0.9, "Image + text = ideal split screen"
            elif has_chart and has_bullets:
                score, reason = 0.8, "Chart + bullets work well split"
            else:
                score, reason = 0.3, "Split screen needs two content areas"

        elif layout in (LayoutType.TEXT_LEFT_VISUAL_RIGHT, LayoutType.TEXT_RIGHT_VISUAL_LEFT):
            if has_image and (has_bullets or c.body_text):
                score, reason = 0.85, "Text + visual pairing"
            else:
                score, reason = 0.25, "Needs both text and visual"

        elif layout == LayoutType.GRID_2X2:
            if has_kpi and len(c.kpi_metrics or []) == 4:
                score, reason = 0.95, "4 KPIs = perfect 2x2 grid"
            elif bullet_count == 4:
                score, reason = 0.8, "4 bullets map to 4 cells"
            elif bullet_count >= 3:
                score, reason = 0.6, "Close to 4-cell layout"
            else:
                score, reason = 0.2, "Not enough items for grid"

        elif layout == LayoutType.GRID_3X1:
            if bullet_count == 3:
                score, reason = 0.9, "3 items = perfect 3-column"
            elif has_comparison and len(c.comparison_items or []) == 3:
                score, reason = 0.85, "3-way comparison"
            else:
                score, reason = 0.2, "Not enough items for 3-col"

        elif layout == LayoutType.BULLETS:
            if bullet_count >= 3:
                score, reason = 0.85, "Bullet-heavy content"
            elif text_heavy:
                score, reason = 0.5, "Text can be bulleted"
            else:
                score, reason = 0.2, "Not enough bullet content"

        elif layout == LayoutType.TIMELINE:
            if has_timeline:
                score, reason = 0.95, "Timeline data available"
            elif slide.type in (SlideType.TRACTION_SLIDE,):
                score, reason = 0.7, "Traction data suits timeline"
            else:
                score, reason = 0.1, "No timeline data"

        elif layout == LayoutType.COMPARISON:
            if has_comparison:
                score, reason = 0.95, "Comparison data available"
            elif slide.type == SlideType.COMPETITION_SLIDE:
                score, reason = 0.85, "Competition = comparison"
            else:
                score, reason = 0.1, "No comparison data"

        elif layout == LayoutType.QUOTE:
            if has_quote:
                score, reason = 0.95, "Quote content available"
            else:
                score, reason = 0.05, "No quote content"

        elif layout == LayoutType.KPI_DASHBOARD:
            if has_kpi:
                score, reason = 0.9, "KPI metrics available"
            elif has_chart and has_kpi:
                score, reason = 0.95, "KPIs + chart = dashboard"
            else:
                score, reason = 0.1, "No KPI data"

        elif layout == LayoutType.TEAM_GRID:
            if has_team:
                score, reason = 0.95, "Team data available"
            else:
                score, reason = 0.05, "No team data"

        elif layout == LayoutType.CHART:
            if has_chart:
                score, reason = 0.9, "Chart data available"
            else:
                score, reason = 0.1, "No chart data"

        elif layout == LayoutType.TOP_BOTTOM:
            if has_image and title_len > 30:
                score, reason = 0.7, "Header with visual below"
            else:
                score, reason = 0.3, "Generic top-bottom split"

        elif layout == LayoutType.OVERLAY:
            if has_image:
                score, reason = 0.7, "Image overlay with text"
            else:
                score, reason = 0.15, "Overlay needs background image"

        elif layout == LayoutType.BLANK:
            score, reason = 0.05, "Blank layout for special cases"

        return min(score, 1.0), reason

    # ── Content reflow ────────────────────────────────────────────

    def _reflow_elements(self, slide: SlideDSL, layout: LayoutType) -> int:
        """
        Reposition existing elements according to the target layout.
        Returns count of elements moved.
        """
        geometry = LAYOUT_GEOMETRY.get(layout.value, LAYOUT_GEOMETRY["center-focus"])
        if not geometry:
            return 0

        repositioned = 0

        for elem in slide.elements:
            region = self._map_element_to_region(elem, geometry)
            if region:
                geo = geometry[region]
                elem.position = SlidePosition(x=geo["x"], y=geo["y"])
                elem.size = SlideSize(width=geo["width"], height=geo["height"])
                repositioned += 1

        return repositioned

    def _map_element_to_region(
        self,
        elem: SlideElement,
        geometry: Dict[str, Dict[str, float]],
    ) -> Optional[str]:
        """Map an element to the best-fit region in a layout."""
        # Text elements with short content -> title region
        if elem.type == ElementType.TEXT:
            if len(elem.content) < 100 and "title" in geometry:
                return "title"
            if "body" in geometry:
                return "body"
            if "subtitle" in geometry:
                return "subtitle"

        # Image elements -> visual region
        if elem.type == ElementType.IMAGE:
            if "visual" in geometry:
                return "visual"
            if "background" in geometry:
                return "background"

        # Chart elements -> chart area
        if elem.type == ElementType.CHART:
            if "chart_area" in geometry:
                return "chart_area"
            if "chart" in geometry:
                return "chart"
            if "visual" in geometry:
                return "visual"

        # Fallback: first available region
        for region in geometry:
            return region

        return None

    def _find_slide(self, slide_id: str) -> Optional[SlideDSL]:
        for s in self._dsl.slides:
            if s.id == slide_id:
                return s
        return None
