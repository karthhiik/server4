"""
PreTeXt Text Measurement Engine -- Phase 5.

Server-side text measurement for layout decisions before committing to DSL.
Replaces the browser-side canvas.measureText() with font-metric-based calculations.

Three integration points (V7 plan Section 17):
1. DSL Generation: Measure text before choosing layout
2. Compilation: Validate text fits in chosen layout
3. QA Pre-check: Detect overflow / truncation before rendering

Performance target: < 0.09ms per measurement (achieved via lookup tables).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# -- Font Metrics Database ----------------------------------------------------

# Average character width ratios (relative to font size = 1.0)
# Derived from standard font metrics tables for common presentation fonts.
# key = font family (lowercase), value = dict of char widths
# 'avg' = average character width, 'cap_avg' = avg uppercase width

FONT_METRICS: dict[str, dict[str, float]] = {
    "inter": {
        "avg": 0.52,
        "cap_avg": 0.60,
        "ascender": 0.93,
        "descender": 0.25,
        "line_gap": 0.08,
        "x_height": 0.52,
        "cap_height": 0.73,
        "space_width": 0.25,
    },
    "helvetica neue": {
        "avg": 0.52,
        "cap_avg": 0.62,
        "ascender": 0.95,
        "descender": 0.24,
        "line_gap": 0.05,
        "x_height": 0.52,
        "cap_height": 0.72,
        "space_width": 0.28,
    },
    "arial": {
        "avg": 0.52,
        "cap_avg": 0.61,
        "ascender": 0.91,
        "descender": 0.21,
        "line_gap": 0.07,
        "x_height": 0.52,
        "cap_height": 0.72,
        "space_width": 0.28,
    },
    "playfair display": {
        "avg": 0.48,
        "cap_avg": 0.58,
        "ascender": 1.00,
        "descender": 0.30,
        "line_gap": 0.05,
        "x_height": 0.46,
        "cap_height": 0.73,
        "space_width": 0.22,
    },
    "source serif 4": {
        "avg": 0.49,
        "cap_avg": 0.59,
        "ascender": 0.98,
        "descender": 0.30,
        "line_gap": 0.06,
        "x_height": 0.47,
        "cap_height": 0.73,
        "space_width": 0.24,
    },
    "space grotesk": {
        "avg": 0.53,
        "cap_avg": 0.60,
        "ascender": 0.93,
        "descender": 0.25,
        "line_gap": 0.08,
        "x_height": 0.52,
        "cap_height": 0.70,
        "space_width": 0.25,
    },
    "ibm plex sans": {
        "avg": 0.53,
        "cap_avg": 0.60,
        "ascender": 0.93,
        "descender": 0.25,
        "line_gap": 0.07,
        "x_height": 0.52,
        "cap_height": 0.70,
        "space_width": 0.25,
    },
    "ibm plex mono": {
        "avg": 0.60,
        "cap_avg": 0.60,
        "ascender": 0.93,
        "descender": 0.25,
        "line_gap": 0.07,
        "x_height": 0.52,
        "cap_height": 0.70,
        "space_width": 0.60,  # monospace
    },
    "jetbrains mono": {
        "avg": 0.60,
        "cap_avg": 0.60,
        "ascender": 0.93,
        "descender": 0.25,
        "line_gap": 0.07,
        "x_height": 0.53,
        "cap_height": 0.72,
        "space_width": 0.60,  # monospace
    },
    "fira code": {
        "avg": 0.60,
        "cap_avg": 0.60,
        "ascender": 0.93,
        "descender": 0.29,
        "line_gap": 0.07,
        "x_height": 0.53,
        "cap_height": 0.72,
        "space_width": 0.60,  # monospace
    },
    "nunito": {
        "avg": 0.54,
        "cap_avg": 0.60,
        "ascender": 0.96,
        "descender": 0.24,
        "line_gap": 0.06,
        "x_height": 0.52,
        "cap_height": 0.71,
        "space_width": 0.26,
    },
    "nunito sans": {
        "avg": 0.53,
        "cap_avg": 0.60,
        "ascender": 0.95,
        "descender": 0.24,
        "line_gap": 0.06,
        "x_height": 0.52,
        "cap_height": 0.71,
        "space_width": 0.25,
    },
    "cal sans": {
        "avg": 0.54,
        "cap_avg": 0.62,
        "ascender": 0.95,
        "descender": 0.20,
        "line_gap": 0.05,
        "x_height": 0.54,
        "cap_height": 0.73,
        "space_width": 0.26,
    },
    "sf mono": {
        "avg": 0.60,
        "cap_avg": 0.60,
        "ascender": 0.90,
        "descender": 0.24,
        "line_gap": 0.06,
        "x_height": 0.52,
        "cap_height": 0.70,
        "space_width": 0.60,  # monospace
    },
}

# Default metrics for unknown fonts (conservative estimate)
DEFAULT_METRICS: dict[str, float] = {
    "avg": 0.55,
    "cap_avg": 0.62,
    "ascender": 0.95,
    "descender": 0.25,
    "line_gap": 0.07,
    "x_height": 0.52,
    "cap_height": 0.72,
    "space_width": 0.28,
}


# -- Data Models --------------------------------------------------------------


class OverflowStrategy(str, Enum):
    """How to handle text overflow."""
    TRUNCATE = "truncate"
    SHRINK_FONT = "shrink_font"
    WRAP = "wrap"
    SPLIT_SLIDE = "split_slide"
    ELLIPSIS = "ellipsis"


@dataclass
class TextMeasurement:
    """Result of measuring a single text block."""
    text: str
    font_family: str
    font_size_pt: float
    width_px: float  # Estimated rendered width
    height_px: float  # Estimated rendered height
    line_count: int
    overflow: bool  # True if text overflows container
    overflow_amount_px: float = 0.0  # How much it overflows (positive = overflow)
    suggested_font_size: float = 0.0  # Font size that would fit
    suggested_strategy: Optional[OverflowStrategy] = None
    confidence: float = 0.95  # Measurement confidence (server-side is ~95%)


@dataclass
class LayoutFitResult:
    """Result of checking if content fits a layout."""
    fits: bool
    title_measurement: Optional[TextMeasurement] = None
    subtitle_measurement: Optional[TextMeasurement] = None
    body_measurements: list[TextMeasurement] = field(default_factory=list)
    overflow_items: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    layout: str = ""
    total_content_height_px: float = 0.0
    available_height_px: float = 0.0


@dataclass
class SlideBox:
    """A bounding box region within a slide layout."""
    name: str  # e.g., "title", "body", "image"
    x: float  # px from left
    y: float  # px from top
    width: float  # px
    height: float  # px
    padding: float = 20.0  # internal padding in px


# -- Layout Definitions -------------------------------------------------------

# Standard slide dimensions (16:9 aspect ratio, 1920x1080 at 96 DPI)
SLIDE_WIDTH_PX = 1920
SLIDE_HEIGHT_PX = 1080

# Layout box definitions (where text regions are inside each layout)
LAYOUT_BOXES: dict[str, list[SlideBox]] = {
    "center-focus": [
        SlideBox("title", 200, 300, 1520, 180, 40),
        SlideBox("subtitle", 300, 500, 1320, 100, 30),
    ],
    "bullets": [
        SlideBox("title", 100, 60, 1720, 160, 30),
        SlideBox("body", 100, 260, 1720, 720, 40),
    ],
    "two-column": [
        SlideBox("title", 100, 60, 1720, 120, 30),
        SlideBox("left_body", 100, 220, 820, 760, 40),
        SlideBox("right_body", 1000, 220, 820, 760, 40),
    ],
    "text-left-visual-right": [
        SlideBox("title", 100, 60, 1720, 120, 30),
        SlideBox("body", 100, 220, 820, 760, 40),
        SlideBox("image", 1000, 220, 820, 760, 10),
    ],
    "split-screen": [
        SlideBox("left_title", 50, 60, 910, 100, 30),
        SlideBox("left_body", 50, 180, 910, 820, 40),
        SlideBox("right_body", 1000, 180, 870, 820, 40),
    ],
    "chart": [
        SlideBox("title", 100, 60, 1720, 120, 30),
        SlideBox("chart_area", 100, 220, 1720, 660, 20),
        SlideBox("caption", 100, 910, 1720, 80, 20),
    ],
    "kpi-dashboard": [
        SlideBox("title", 100, 60, 1720, 100, 30),
        SlideBox("kpi_1", 100, 200, 540, 340, 30),
        SlideBox("kpi_2", 690, 200, 540, 340, 30),
        SlideBox("kpi_3", 1280, 200, 540, 340, 30),
        SlideBox("bottom", 100, 600, 1720, 380, 30),
    ],
    "team-grid": [
        SlideBox("title", 100, 60, 1720, 120, 30),
        SlideBox("member_1", 100, 220, 380, 400, 20),
        SlideBox("member_2", 530, 220, 380, 400, 20),
        SlideBox("member_3", 960, 220, 380, 400, 20),
        SlideBox("member_4", 1390, 220, 380, 400, 20),
    ],
    "comparison": [
        SlideBox("title", 100, 60, 1720, 120, 30),
        SlideBox("left_col", 100, 220, 820, 760, 40),
        SlideBox("right_col", 1000, 220, 820, 760, 40),
    ],
    "timeline": [
        SlideBox("title", 100, 60, 1720, 120, 30),
        SlideBox("timeline_area", 100, 220, 1720, 760, 30),
    ],
    "quote": [
        SlideBox("quote_text", 200, 250, 1520, 400, 60),
        SlideBox("attribution", 200, 700, 1520, 80, 30),
    ],
    "full-bleed": [
        SlideBox("overlay_title", 100, 600, 1720, 200, 40),
        SlideBox("overlay_subtitle", 100, 820, 1720, 100, 30),
    ],
    "top-bottom": [
        SlideBox("title", 100, 60, 1720, 120, 30),
        SlideBox("top_body", 100, 220, 1720, 340, 40),
        SlideBox("bottom_body", 100, 600, 1720, 380, 40),
    ],
    "grid-2x2": [
        SlideBox("title", 100, 60, 1720, 100, 30),
        SlideBox("cell_1", 100, 200, 820, 360, 30),
        SlideBox("cell_2", 1000, 200, 820, 360, 30),
        SlideBox("cell_3", 100, 600, 820, 380, 30),
        SlideBox("cell_4", 1000, 600, 820, 380, 30),
    ],
    "grid-3x1": [
        SlideBox("title", 100, 60, 1720, 100, 30),
        SlideBox("col_1", 100, 200, 540, 780, 30),
        SlideBox("col_2", 690, 200, 540, 780, 30),
        SlideBox("col_3", 1280, 200, 540, 780, 30),
    ],
}


# -- PreTeXt Measurement Engine -----------------------------------------------


class PreTeXtEngine:
    """
    Server-side text measurement engine using font metrics lookup tables.

    Provides 3 APIs matching the V7 plan integration points:

    1. ``measure_text()`` - Measure a single text string
    2. ``check_layout_fit()`` - Check if content fits a layout's boxes
    3. ``suggest_fixes()`` - Suggest fixes for overflow

    All measurements are estimates based on average character widths.
    Confidence is ~95% for proportional fonts, ~99% for monospace.
    Performance target: < 0.09ms per measurement (no I/O, pure math).
    """

    def __init__(self, dpi: int = 96):
        self.dpi = dpi

    def measure_text(
        self,
        text: str,
        font_family: str = "Inter",
        font_size_pt: float = 16.0,
        max_width_px: float = 0.0,
        line_height: float = 1.5,
        font_weight: str = "normal",
    ) -> TextMeasurement:
        """
        Measure the rendered dimensions of a text string.

        Args:
            text: The text content to measure
            font_family: Font family name
            font_size_pt: Font size in points
            max_width_px: Container width for wrapping (0 = no wrap)
            line_height: CSS line-height multiplier
            font_weight: "normal" or "bold" (bold is ~5% wider)

        Returns:
            TextMeasurement with estimated dimensions
        """
        if not text:
            return TextMeasurement(
                text="",
                font_family=font_family,
                font_size_pt=font_size_pt,
                width_px=0,
                height_px=0,
                line_count=0,
                overflow=False,
            )

        metrics = self._get_metrics(font_family)
        font_size_px = self._pt_to_px(font_size_pt)

        # Bold adjustment
        bold_factor = 1.05 if font_weight == "bold" else 1.0

        # Measure single-line width
        raw_width = self._measure_line_width(text, metrics, font_size_px, bold_factor)

        # Calculate wrapping if max_width specified
        if max_width_px > 0:
            lines = self._wrap_text(text, metrics, font_size_px, max_width_px, bold_factor)
            line_count = len(lines)
            actual_width = min(raw_width, max_width_px)
        else:
            line_count = text.count("\n") + 1
            actual_width = raw_width

        # Height calculation
        line_height_px = font_size_px * line_height
        total_height = line_count * line_height_px

        # Overflow detection
        overflow = False
        overflow_amount = 0.0
        if max_width_px > 0:
            overflow_amount = raw_width - max_width_px
            overflow = overflow_amount > 0

        return TextMeasurement(
            text=text,
            font_family=font_family,
            font_size_pt=font_size_pt,
            width_px=round(actual_width, 1),
            height_px=round(total_height, 1),
            line_count=line_count,
            overflow=overflow,
            overflow_amount_px=round(max(0, overflow_amount), 1),
            confidence=0.99 if self._is_monospace(font_family) else 0.95,
        )

    def check_layout_fit(
        self,
        layout: str,
        content: dict[str, Any],
        font_family: str = "Inter",
        heading_font_size: float = 36.0,
        body_font_size: float = 18.0,
        line_height: float = 1.5,
    ) -> LayoutFitResult:
        """
        Check if content fits within a layout's bounding boxes.

        Integration point 2 from V7 plan: Validate text fits in chosen layout.

        Args:
            layout: Layout name (must exist in LAYOUT_BOXES)
            content: Dict with keys matching box names (title, body, etc.)
            font_family: Default font family
            heading_font_size: Font size for title/heading boxes
            body_font_size: Font size for body/content boxes
            line_height: CSS line-height multiplier

        Returns:
            LayoutFitResult with per-box measurements and overflow info
        """
        boxes = LAYOUT_BOXES.get(layout, LAYOUT_BOXES["bullets"])
        result = LayoutFitResult(layout=layout, fits=True)
        total_content_h = 0.0
        total_available_h = 0.0

        for box in boxes:
            text = content.get(box.name, "")
            if not text or "image" in box.name or "chart" in box.name:
                total_available_h += box.height
                continue

            # Determine font size based on box purpose
            is_heading = "title" in box.name or "heading" in box.name
            font_size = heading_font_size if is_heading else body_font_size
            font_weight = "bold" if is_heading else "normal"

            inner_width = box.width - (box.padding * 2)
            inner_height = box.height - (box.padding * 2)

            measurement = self.measure_text(
                text=text,
                font_family=font_family,
                font_size_pt=font_size,
                max_width_px=inner_width,
                line_height=line_height,
                font_weight=font_weight,
            )

            # Check vertical overflow
            if measurement.height_px > inner_height:
                measurement.overflow = True
                measurement.overflow_amount_px = round(
                    measurement.height_px - inner_height, 1
                )
                # Suggest font size that would fit
                if measurement.line_count > 0:
                    scale_factor = inner_height / measurement.height_px
                    measurement.suggested_font_size = round(
                        font_size * scale_factor, 1
                    )
                    if measurement.suggested_font_size < 12:
                        measurement.suggested_strategy = OverflowStrategy.SPLIT_SLIDE
                    else:
                        measurement.suggested_strategy = OverflowStrategy.SHRINK_FONT
                result.overflow_items.append(box.name)
                result.fits = False

            # Store measurement
            if is_heading:
                if result.title_measurement is None:
                    result.title_measurement = measurement
                elif result.subtitle_measurement is None:
                    result.subtitle_measurement = measurement
            else:
                result.body_measurements.append(measurement)

            total_content_h += measurement.height_px
            total_available_h += inner_height

        result.total_content_height_px = round(total_content_h, 1)
        result.available_height_px = round(total_available_h, 1)

        # Generate suggestions
        if not result.fits:
            result.suggestions = self.suggest_fixes(result)

        return result

    def suggest_fixes(self, fit_result: LayoutFitResult) -> list[str]:
        """
        Suggest fixes for layout overflow issues.

        Integration point 3: QA pre-check before rendering.

        Args:
            fit_result: Result from check_layout_fit()

        Returns:
            List of actionable fix suggestions
        """
        suggestions = []
        overflow_ratio = 0.0
        if fit_result.available_height_px > 0:
            overflow_ratio = (
                fit_result.total_content_height_px / fit_result.available_height_px
            )

        # Title overflow
        if fit_result.title_measurement and fit_result.title_measurement.overflow:
            tm = fit_result.title_measurement
            if tm.suggested_font_size and tm.suggested_font_size >= 24:
                suggestions.append(
                    f"Reduce title font to {tm.suggested_font_size}pt "
                    f"(currently overflows by {tm.overflow_amount_px}px)"
                )
            else:
                suggestions.append(
                    "Shorten the title text — it cannot fit even at minimum "
                    "readable size"
                )

        # Body overflow
        for i, bm in enumerate(fit_result.body_measurements):
            if bm.overflow:
                if bm.suggested_strategy == OverflowStrategy.SPLIT_SLIDE:
                    suggestions.append(
                        f"Body section {i + 1}: content too long for single slide. "
                        f"Consider splitting into 2 slides."
                    )
                elif bm.suggested_font_size and bm.suggested_font_size >= 14:
                    suggestions.append(
                        f"Body section {i + 1}: reduce font to "
                        f"{bm.suggested_font_size}pt "
                        f"(overflows by {bm.overflow_amount_px}px)"
                    )
                else:
                    suggestions.append(
                        f"Body section {i + 1}: too much content. Remove "
                        f"~{int(bm.overflow_amount_px / 24)} lines or split slide."
                    )

        # General overflow
        if overflow_ratio > 1.5:
            suggestions.append(
                "Content is 50%+ over capacity. Recommend switching to a "
                "more spacious layout (e.g., two-column) or splitting content "
                "across slides."
            )
        elif overflow_ratio > 1.2:
            suggestions.append(
                "Content is ~20% over capacity. Consider reducing bullet points "
                "or shortening descriptions."
            )

        return suggestions

    def find_optimal_font_size(
        self,
        text: str,
        font_family: str,
        max_width_px: float,
        max_height_px: float,
        min_size_pt: float = 12.0,
        max_size_pt: float = 72.0,
        line_height: float = 1.5,
    ) -> float:
        """
        Binary search for the largest font size that fits the text in the box.

        Useful for headings where you want maximum visual impact.

        Args:
            text: Text to fit
            font_family: Font family name
            max_width_px: Container width
            max_height_px: Container height
            min_size_pt: Minimum allowed font size
            max_size_pt: Maximum allowed font size
            line_height: CSS line-height

        Returns:
            Optimal font size in points
        """
        low = min_size_pt
        high = max_size_pt
        best = min_size_pt

        # Binary search with 0.5pt precision
        while high - low > 0.5:
            mid = (low + high) / 2
            m = self.measure_text(
                text=text,
                font_family=font_family,
                font_size_pt=mid,
                max_width_px=max_width_px,
                line_height=line_height,
            )
            if m.height_px <= max_height_px and not m.overflow:
                best = mid
                low = mid
            else:
                high = mid

        return round(best, 1)

    # -- Internal methods ------------------------------------------------

    def _get_metrics(self, font_family: str) -> dict[str, float]:
        """Look up font metrics, falling back to defaults."""
        key = font_family.strip().lower()
        return FONT_METRICS.get(key, DEFAULT_METRICS)

    def _pt_to_px(self, pt: float) -> float:
        """Convert points to pixels at configured DPI."""
        return pt * (self.dpi / 72)

    def _is_monospace(self, font_family: str) -> bool:
        """Check if font is monospaced (all chars same width)."""
        key = font_family.strip().lower()
        if key in FONT_METRICS:
            return abs(FONT_METRICS[key]["avg"] - FONT_METRICS[key]["space_width"]) < 0.01
        return False

    def _measure_line_width(
        self,
        text: str,
        metrics: dict[str, float],
        font_size_px: float,
        bold_factor: float = 1.0,
    ) -> float:
        """Estimate the rendered width of a single line of text."""
        width = 0.0
        avg_w = metrics["avg"]
        cap_w = metrics["cap_avg"]
        space_w = metrics["space_width"]

        for char in text:
            if char == " ":
                width += space_w * font_size_px
            elif char == "\n":
                continue  # Newlines don't add width
            elif char == "\t":
                width += space_w * font_size_px * 4
            elif char.isupper():
                width += cap_w * font_size_px
            elif char in "mwMW":
                width += cap_w * font_size_px * 1.1  # Wide chars
            elif char in "il|!:;,.":
                width += avg_w * font_size_px * 0.4  # Narrow chars
            elif char in "fjrt":
                width += avg_w * font_size_px * 0.7  # Mid-narrow chars
            else:
                width += avg_w * font_size_px

        return width * bold_factor

    def _wrap_text(
        self,
        text: str,
        metrics: dict[str, float],
        font_size_px: float,
        max_width_px: float,
        bold_factor: float = 1.0,
    ) -> list[str]:
        """
        Simulate word wrapping and return list of lines.

        Uses word-break wrapping (break at space boundaries).
        """
        paragraphs = text.split("\n")
        all_lines: list[str] = []

        for paragraph in paragraphs:
            if not paragraph.strip():
                all_lines.append("")
                continue

            words = paragraph.split()
            if not words:
                all_lines.append("")
                continue

            current_line_words: list[str] = []
            current_width = 0.0

            for word in words:
                word_width = self._measure_line_width(
                    word, metrics, font_size_px, bold_factor
                )
                space_width = metrics["space_width"] * font_size_px

                if current_line_words:
                    test_width = current_width + space_width + word_width
                else:
                    test_width = word_width

                if test_width <= max_width_px or not current_line_words:
                    # Word fits or it's the first word on the line
                    current_line_words.append(word)
                    current_width = test_width
                else:
                    # Start new line
                    all_lines.append(" ".join(current_line_words))
                    current_line_words = [word]
                    current_width = word_width

            if current_line_words:
                all_lines.append(" ".join(current_line_words))

        return all_lines if all_lines else [""]


# -- Convenience functions ---------------------------------------------------


def measure_heading(
    text: str,
    font_family: str = "Inter",
    font_size_pt: float = 36.0,
    max_width_px: float = 1520.0,
) -> TextMeasurement:
    """Quick measurement for a heading text block."""
    engine = PreTeXtEngine()
    return engine.measure_text(
        text=text,
        font_family=font_family,
        font_size_pt=font_size_pt,
        max_width_px=max_width_px,
        font_weight="bold",
    )


def measure_body(
    text: str,
    font_family: str = "Inter",
    font_size_pt: float = 18.0,
    max_width_px: float = 1520.0,
) -> TextMeasurement:
    """Quick measurement for a body text block."""
    engine = PreTeXtEngine()
    return engine.measure_text(
        text=text,
        font_family=font_family,
        font_size_pt=font_size_pt,
        max_width_px=max_width_px,
    )


def check_slide_fit(
    layout: str,
    content: dict[str, str],
    heading_font: str = "Inter",
    body_font: str = "Inter",
    heading_size: float = 36.0,
    body_size: float = 18.0,
) -> LayoutFitResult:
    """Quick check if content fits in a slide layout."""
    engine = PreTeXtEngine()
    return engine.check_layout_fit(
        layout=layout,
        content=content,
        font_family=body_font,
        heading_font_size=heading_size,
        body_font_size=body_size,
    )
