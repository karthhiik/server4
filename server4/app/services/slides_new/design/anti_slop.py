"""
Anti-AI-Slop Processor -- Phase 5.

Detects and eliminates generic AI aesthetics from generated slides.
Based on frontend-slides design principles and the V7 plan's
AntiAISlopProcessor specification.

The processor analyzes rendered slide properties and flags common
AI-generated design anti-patterns, then suggests corrections aligned
with the active visual preset.

Pipeline:
1. Analyze slide design properties (colors, layout, typography, spacing)
2. Score each property against slop indicator rules
3. Flag violations with severity + suggested fix
4. Auto-correct fixable issues
5. Return quality report with overall slop score
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# -- Slop Indicators ---------------------------------------------------------


class SlopSeverity(str, Enum):
    """Severity levels for slop detection."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SlopCategory(str, Enum):
    """Categories of AI-slop indicators."""
    COLOR = "color"
    LAYOUT = "layout"
    TYPOGRAPHY = "typography"
    SPACING = "spacing"
    CONTENT = "content"
    IMAGERY = "imagery"
    ANIMATION = "animation"


@dataclass
class SlopViolation:
    """A single detected slop violation."""
    category: SlopCategory
    severity: SlopSeverity
    indicator: str
    description: str
    suggestion: str
    auto_fixable: bool = False
    fix_applied: bool = False
    confidence: float = 1.0


@dataclass
class SlopReport:
    """Complete slop analysis report for a slide or presentation."""
    violations: list[SlopViolation] = field(default_factory=list)
    slop_score: float = 0.0  # 0 = no slop, 100 = maximum slop
    quality_score: float = 100.0  # 100 = perfect, 0 = terrible
    fixes_applied: int = 0
    fixes_available: int = 0
    summary: str = ""

    @property
    def is_clean(self) -> bool:
        return self.slop_score < 15.0

    @property
    def critical_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == SlopSeverity.CRITICAL)

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == SlopSeverity.ERROR)


# -- Slop Rules Engine -------------------------------------------------------


# Color rules
GENERIC_GRADIENT_PATTERNS = [
    (r"#(?:667eea|764ba2)", "Default Tailwind/AI gradient blue-purple"),
    (r"#(?:6366f1|818cf8)", "Generic indigo gradient"),
    (r"#(?:3b82f6|8b5cf6)", "Blue-violet AI default"),
    (r"linear-gradient.*(?:135deg|45deg).*(?:#667|#764|#6366)", "Generic diagonal gradient"),
]

OVERUSED_AI_COLORS = {
    "#667eea", "#764ba2", "#6366f1", "#818cf8",
    "#4f46e5", "#7c3aed", "#8b5cf6",  # generic purples
}

# Typography rules
GENERIC_FONT_COMBOS = [
    ("Arial", "Arial"),
    ("Helvetica", "Helvetica"),
    ("sans-serif", "sans-serif"),
]

# Overused AI-default fonts (commonly used by LLMs in slide generation)
OVERUSED_AI_FONTS = {
    "Poppins", "Montserrat", "Open Sans", "Lato",
    "Roboto", "Raleway", "Nunito Sans",
}

# Layout rules
MAX_REASONABLE_BULLETS = 6
MAX_WORDS_PER_BULLET = 15
MIN_FONT_SIZE_PT = 18
MAX_SLIDES_PITCH_DECK = 15


class SlopRule:
    """Base class for a single slop detection rule."""

    def __init__(
        self,
        name: str,
        category: SlopCategory,
        severity: SlopSeverity,
        description: str,
        weight: float = 1.0,
    ):
        self.name = name
        self.category = category
        self.severity = severity
        self.description = description
        self.weight = weight

    def check(self, slide_data: dict[str, Any]) -> Optional[SlopViolation]:
        """Override in subclasses to implement detection logic."""
        raise NotImplementedError


class GenericGradientRule(SlopRule):
    """Detects generic AI-default gradients (blue-purple diagonal)."""

    def __init__(self):
        super().__init__(
            name="generic_gradient",
            category=SlopCategory.COLOR,
            severity=SlopSeverity.ERROR,
            description="Generic gradient backgrounds (blue-purple default)",
            weight=2.0,
        )

    def check(self, slide_data: dict[str, Any]) -> Optional[SlopViolation]:
        bg = slide_data.get("background", {})

        # Handle string-format background (e.g., "linear-gradient(...)")
        if isinstance(bg, str):
            bg_str = bg.lower()
            if "gradient" not in bg_str:
                return None
            # Check for overused AI gradient colors
            for color in OVERUSED_AI_COLORS:
                if color.lstrip("#").lower() in bg_str:
                    return SlopViolation(
                        category=self.category,
                        severity=self.severity,
                        indicator=self.name,
                        description=f"Generic AI gradient detected: {bg}",
                        suggestion="Replace with brand-specific colors or a solid background",
                        auto_fixable=True,
                        confidence=0.9,
                    )
            # Check patterns
            for pattern, desc in GENERIC_GRADIENT_PATTERNS:
                if re.search(pattern, bg_str):
                    return SlopViolation(
                        category=self.category,
                        severity=self.severity,
                        indicator=self.name,
                        description=f"Generic AI gradient detected: {desc}",
                        suggestion="Replace with brand-specific colors or a solid background",
                        auto_fixable=True,
                        confidence=0.85,
                    )
            return None

        # Handle dict-format background
        bg_type = bg.get("type", "") if isinstance(bg, dict) else ""
        colors = bg.get("colors", []) if isinstance(bg, dict) else []

        if "gradient" not in bg_type.lower():
            return None

        for color in colors:
            color_lower = color.lower()
            if color_lower in OVERUSED_AI_COLORS:
                return SlopViolation(
                    category=self.category,
                    severity=self.severity,
                    indicator=self.name,
                    description=f"Generic AI gradient detected: {colors}",
                    suggestion="Replace with brand-specific colors or a solid background",
                    auto_fixable=True,
                    confidence=0.9,
                )
        return None


class CenteredEverythingRule(SlopRule):
    """Detects slides where everything is center-aligned (lazy AI default)."""

    def __init__(self):
        super().__init__(
            name="centered_everything",
            category=SlopCategory.LAYOUT,
            severity=SlopSeverity.WARNING,
            description="Center-everything layout (no visual hierarchy)",
            weight=1.5,
        )

    def check(self, slide_data: dict[str, Any]) -> Optional[SlopViolation]:
        elements = slide_data.get("elements", [])
        if not elements:
            return None

        # Count center-aligned elements
        center_count = 0
        for elem in elements:
            # Check nested style.textAlign
            style = elem.get("style", {})
            text_align = style.get("textAlign", "").lower() if isinstance(style, dict) else ""
            # Also check flat elem.align
            if not text_align:
                text_align = str(elem.get("align", "")).lower()
            # Also check top-level text_align
            if not text_align:
                text_align = str(slide_data.get("text_align", "")).lower()
            if text_align == "center":
                center_count += 1

        # If >80% are centered, flag it
        if len(elements) >= 3 and center_count / len(elements) > 0.8:
            return SlopViolation(
                category=self.category,
                severity=self.severity,
                indicator=self.name,
                description=f"{center_count}/{len(elements)} elements are center-aligned",
                suggestion="Use left-aligned text for content slides, center for titles only",
                auto_fixable=True,
                confidence=0.85,
            )
        return None


class TooManyBulletsRule(SlopRule):
    """Detects slides with too many bullet points (>6)."""

    def __init__(self):
        super().__init__(
            name="too_many_bullets",
            category=SlopCategory.CONTENT,
            severity=SlopSeverity.ERROR,
            description="Too much text (>6 bullets per slide)",
            weight=2.0,
        )

    def check(self, slide_data: dict[str, Any]) -> Optional[SlopViolation]:
        # Check nested format: content.bullets
        content = slide_data.get("content", {})
        bullets = content.get("bullets", []) if isinstance(content, dict) else []
        body_lines = content.get("body", "").count("\n") + 1 if isinstance(content, dict) and content.get("body") else 0

        # Also check flat format: slide_data.bullets
        if not bullets:
            bullets = slide_data.get("bullets", [])
        if body_lines == 0 and slide_data.get("body"):
            body_lines = slide_data["body"].count("\n") + 1

        total_items = len(bullets) + body_lines
        if total_items > MAX_REASONABLE_BULLETS:
            return SlopViolation(
                category=self.category,
                severity=self.severity,
                indicator=self.name,
                description=f"{total_items} items on slide (max {MAX_REASONABLE_BULLETS})",
                suggestion="Split into 2 slides or summarize key points",
                auto_fixable=False,
                confidence=0.95,
            )
        return None


class NoWhitespaceRule(SlopRule):
    """Detects cramped layouts with insufficient breathing room."""

    def __init__(self):
        super().__init__(
            name="no_whitespace",
            category=SlopCategory.SPACING,
            severity=SlopSeverity.WARNING,
            description="Cramped layout (insufficient whitespace)",
            weight=1.5,
        )

    def check(self, slide_data: dict[str, Any]) -> Optional[SlopViolation]:
        elements = slide_data.get("elements", [])
        if len(elements) < 3:
            return None

        # Calculate coverage — sum of element areas
        total_area = 0.0
        slide_w = slide_data.get("slide_width", 1)
        slide_h = slide_data.get("slide_height", 1)
        slide_area = slide_w * slide_h if slide_w > 1 and slide_h > 1 else 1.0

        for elem in elements:
            # Check nested size format
            size = elem.get("size", {})
            w = size.get("width", 0) if isinstance(size, dict) else 0
            h = size.get("height", 0) if isinstance(size, dict) else 0
            # Also check flat width/height
            if w == 0:
                w = elem.get("width", 0)
            if h == 0:
                h = elem.get("height", 0)
            total_area += w * h

        # Normalize to ratio if using absolute pixel values
        if slide_area > 1:
            coverage = total_area / slide_area
        else:
            coverage = total_area

        if coverage > 0.85:
            return SlopViolation(
                category=self.category,
                severity=self.severity,
                indicator=self.name,
                description=f"Elements cover {coverage:.0%} of slide area (>85%)",
                suggestion="Add padding and whitespace for visual breathing room",
                auto_fixable=True,
                confidence=0.8,
            )
        return None


class RainbowColorsRule(SlopRule):
    """Detects excessive color usage (>4 distinct hues)."""

    def __init__(self):
        super().__init__(
            name="rainbow_colors",
            category=SlopCategory.COLOR,
            severity=SlopSeverity.WARNING,
            description="Too many colors (rainbow effect)",
            weight=1.0,
        )

    def check(self, slide_data: dict[str, Any]) -> Optional[SlopViolation]:
        colors_used = set()

        # Check nested elements format
        for elem in slide_data.get("elements", []):
            style = elem.get("style", {})
            for key in ("color", "backgroundColor", "borderColor"):
                c = style.get(key, "")
                if c and c.startswith("#") and len(c) >= 7:
                    colors_used.add(c.lower())

        bg = slide_data.get("background", {})
        if isinstance(bg, dict):
            bg_colors = bg.get("colors", [])
            for c in bg_colors:
                if c and c.startswith("#"):
                    colors_used.add(c.lower())

        # Also check flat format: slide_data.colors
        flat_colors = slide_data.get("colors", [])
        if isinstance(flat_colors, list):
            for c in flat_colors:
                if isinstance(c, str) and c.startswith("#") and len(c) >= 7:
                    colors_used.add(c.lower())

        # Extract unique hues
        hues = set()
        for hex_c in colors_used:
            try:
                from app.services.slides_new.design.brand_dna import _hex_to_rgb, _rgb_to_hsl
                r, g, b = _hex_to_rgb(hex_c)
                h, s, _ = _rgb_to_hsl(r, g, b)
                if s > 15:  # Only count chromatic colors
                    hues.add(int(h / 30))  # Quantize to 30-degree buckets
            except Exception:
                pass

        if len(hues) > 4:
            return SlopViolation(
                category=self.category,
                severity=self.severity,
                indicator=self.name,
                description=f"{len(hues)} distinct hue families used on one slide",
                suggestion="Limit to 2-3 colors from the brand palette",
                auto_fixable=False,
                confidence=0.8,
            )
        return None


class EqualSpacingRule(SlopRule):
    """Detects equal spacing everywhere (no visual hierarchy via spacing)."""

    def __init__(self):
        super().__init__(
            name="equal_spacing",
            category=SlopCategory.SPACING,
            severity=SlopSeverity.INFO,
            description="Equal spacing everywhere (no hierarchy)",
            weight=0.5,
        )

    def check(self, slide_data: dict[str, Any]) -> Optional[SlopViolation]:
        # Check flat format: spacing array directly
        flat_spacing = slide_data.get("spacing", [])
        if isinstance(flat_spacing, list) and len(flat_spacing) >= 4:
            avg_gap = sum(flat_spacing) / len(flat_spacing)
            if avg_gap > 0:
                all_equal = all(
                    abs(g - avg_gap) / max(abs(avg_gap), 0.01) < 0.1
                    for g in flat_spacing
                )
                if all_equal:
                    return SlopViolation(
                        category=self.category,
                        severity=self.severity,
                        indicator=self.name,
                        description="All element spacing is identical",
                        suggestion="Use varied spacing to create visual hierarchy (tighter for related items)",
                        auto_fixable=True,
                        confidence=0.7,
                    )

        elements = slide_data.get("elements", [])
        if len(elements) < 3:
            return None

        # Check vertical gaps between elements sorted by Y position
        sorted_elems = sorted(
            elements,
            key=lambda e: e.get("position", {}).get("y", e.get("y", 0)),
        )

        gaps = []
        for i in range(1, len(sorted_elems)):
            prev = sorted_elems[i - 1]
            curr = sorted_elems[i]
            y_prev = prev.get("position", {}).get("y", prev.get("y", 0))
            h_prev = prev.get("size", {}).get("height", prev.get("height", 0))
            y_curr = curr.get("position", {}).get("y", curr.get("y", 0))
            gap = y_curr - (y_prev + h_prev)
            gaps.append(gap)

        if not gaps:
            return None

        # If all gaps are within 10% of each other, flag as equal
        avg_gap = sum(gaps) / len(gaps)
        if avg_gap == 0:
            return None

        all_equal = all(abs(g - avg_gap) / max(abs(avg_gap), 0.01) < 0.1 for g in gaps)
        if all_equal and len(gaps) >= 3:
            return SlopViolation(
                category=self.category,
                severity=self.severity,
                indicator=self.name,
                description="All element spacing is identical",
                suggestion="Use varied spacing to create visual hierarchy (tighter for related items)",
                auto_fixable=True,
                confidence=0.7,
            )
        return None


class GenericFontRule(SlopRule):
    """Detects generic font combinations without personality."""

    def __init__(self):
        super().__init__(
            name="generic_fonts",
            category=SlopCategory.TYPOGRAPHY,
            severity=SlopSeverity.WARNING,
            description="Generic sans-serif without personality",
            weight=1.0,
        )

    def check(self, slide_data: dict[str, Any]) -> Optional[SlopViolation]:
        fonts_used = set()

        # Check nested elements format
        for elem in slide_data.get("elements", []):
            style = elem.get("style", {})
            font = style.get("fontFamily", "")
            if font:
                fonts_used.add(font.strip().strip("'\"" ).split(",")[0].strip())

        # Also check flat format: slide_data.heading_font / body_font
        for key in ("heading_font", "body_font", "font_family"):
            font = slide_data.get(key, "")
            if font:
                fonts_used.add(font.strip().strip("'\"" ).split(",")[0].strip())

        # Check for generic font combos
        for heading, body in GENERIC_FONT_COMBOS:
            if heading in fonts_used or body in fonts_used:
                return SlopViolation(
                    category=self.category,
                    severity=self.severity,
                    indicator=self.name,
                    description=f"Generic font detected: {fonts_used}",
                    suggestion="Use curated font pairs (e.g., DM Sans + Inter, Outfit + DM Sans)",
                    auto_fixable=True,
                    confidence=0.75,
                )

        # Check for overused AI-default fonts
        overused = fonts_used & OVERUSED_AI_FONTS
        if len(overused) >= 1:
            return SlopViolation(
                category=self.category,
                severity=self.severity,
                indicator=self.name,
                description=f"Overused AI-default font(s) detected: {overused}",
                suggestion="Use distinctive font pairs (e.g., Space Grotesk + IBM Plex Sans)",
                auto_fixable=True,
                confidence=0.7,
            )
        return None


class PerfectSymmetryRule(SlopRule):
    """Detects too-perfect symmetry (needs intentional asymmetry)."""

    def __init__(self):
        super().__init__(
            name="perfect_symmetry",
            category=SlopCategory.LAYOUT,
            severity=SlopSeverity.INFO,
            description="Too-perfect symmetry (needs intentional asymmetry)",
            weight=0.5,
        )

    def check(self, slide_data: dict[str, Any]) -> Optional[SlopViolation]:
        elements = slide_data.get("elements", [])
        if len(elements) < 4:
            return None

        # Check if all elements are perfectly centered horizontally
        x_positions = [
            e.get("position", {}).get("x", e.get("x", 0)) for e in elements
        ]
        widths = [
            e.get("size", {}).get("width", e.get("width", 0)) for e in elements
        ]

        # Also detect all-same-size elements (another symptom of AI slop)
        heights = [
            e.get("size", {}).get("height", e.get("height", 0)) for e in elements
        ]
        if widths and heights:
            all_same_size = (
                len(set(widths)) == 1
                and len(set(heights)) == 1
                and widths[0] > 0
            )
            if all_same_size and len(elements) >= 4:
                return SlopViolation(
                    category=self.category,
                    severity=self.severity,
                    indicator=self.name,
                    description=f"All {len(elements)} elements have identical size ({widths[0]}x{heights[0]})",
                    suggestion="Break symmetry with intentional offset or varied widths",
                    auto_fixable=False,
                    confidence=0.65,
                )

        centers = [x + w / 2 for x, w in zip(x_positions, widths)]
        if not centers:
            return None

        avg_center = sum(centers) / len(centers)
        all_centered = all(abs(c - avg_center) < 0.02 for c in centers)

        if all_centered and len(elements) >= 4:
            return SlopViolation(
                category=self.category,
                severity=self.severity,
                indicator=self.name,
                description="All elements perfectly centered on the same axis",
                suggestion="Break symmetry with intentional offset or varied widths",
                auto_fixable=False,
                confidence=0.65,
            )
        return None


class SmallFontRule(SlopRule):
    """Detects text that's too small for presentation readability."""

    def __init__(self):
        super().__init__(
            name="small_font",
            category=SlopCategory.TYPOGRAPHY,
            severity=SlopSeverity.ERROR,
            description="Font size too small for presentations",
            weight=2.0,
        )

    def check(self, slide_data: dict[str, Any]) -> Optional[SlopViolation]:
        # Check nested elements
        for elem in slide_data.get("elements", []):
            style = elem.get("style", {})
            font_size = style.get("fontSize", "")

            # Parse font size (handle "18px", "14pt", "sm", etc.)
            size_val = _parse_font_size(font_size)
            if size_val is not None and size_val < MIN_FONT_SIZE_PT:
                return SlopViolation(
                    category=self.category,
                    severity=self.severity,
                    indicator=self.name,
                    description=f"Font size {font_size} is below minimum {MIN_FONT_SIZE_PT}pt",
                    suggestion=f"Increase to at least {MIN_FONT_SIZE_PT}pt for readability",
                    auto_fixable=True,
                    confidence=0.9,
                )

        # Also check flat format: slide_data.font_size
        flat_font_size = slide_data.get("font_size", "")
        if flat_font_size:
            size_val = _parse_font_size(flat_font_size)
            if size_val is not None and size_val < MIN_FONT_SIZE_PT:
                return SlopViolation(
                    category=self.category,
                    severity=self.severity,
                    indicator=self.name,
                    description=f"Font size {flat_font_size} is below minimum {MIN_FONT_SIZE_PT}pt",
                    suggestion=f"Increase to at least {MIN_FONT_SIZE_PT}pt for readability",
                    auto_fixable=True,
                    confidence=0.9,
                )
        return None


# -- Anti-AI-Slop Processor --------------------------------------------------


# Size class name to point mapping
_SIZE_MAP = {
    "xs": 12, "sm": 14, "base": 16, "md": 18,
    "lg": 20, "xl": 24, "2xl": 28, "3xl": 32,
    "4xl": 36, "5xl": 48, "6xl": 64,
}


def _parse_font_size(val: Any) -> Optional[float]:
    """Parse font size string to numeric value in pt."""
    if isinstance(val, (int, float)):
        return float(val)
    if not isinstance(val, str):
        return None
    val = val.strip().lower()
    # Named sizes
    if val in _SIZE_MAP:
        return float(_SIZE_MAP[val])
    # "18px" → ~13.5pt (px * 0.75)
    match = re.match(r"([\d.]+)\s*px", val)
    if match:
        return float(match.group(1)) * 0.75
    # "14pt" → 14
    match = re.match(r"([\d.]+)\s*pt", val)
    if match:
        return float(match.group(1))
    # "1.5rem" → ~24pt (rem * 16)
    match = re.match(r"([\d.]+)\s*rem", val)
    if match:
        return float(match.group(1)) * 16 * 0.75
    # Bare number
    try:
        return float(val)
    except ValueError:
        return None


class AntiAISlopProcessor:
    """
    Detects and eliminates generic AI aesthetics from generated slides.

    Based on frontend-slides design principles:
    - No generic gradient backgrounds (blue-purple default)
    - No stock-photo-style imagery
    - No centered-everything layout
    - No too-perfect symmetry (needs intentional asymmetry)
    - No overuse of icons from a single icon pack
    - No generic sans-serif without personality
    - No equal spacing everywhere (needs visual hierarchy)
    - No cramped layouts (whitespace matters)
    - No rainbow color usage (too many colors)

    Usage:
        processor = AntiAISlopProcessor()
        report = processor.analyze_slide(slide_data)
        if not report.is_clean:
            fixed_data = processor.auto_fix(slide_data, report)
    """

    def __init__(self):
        self._rules: list[SlopRule] = [
            GenericGradientRule(),
            CenteredEverythingRule(),
            TooManyBulletsRule(),
            NoWhitespaceRule(),
            RainbowColorsRule(),
            EqualSpacingRule(),
            GenericFontRule(),
            PerfectSymmetryRule(),
            SmallFontRule(),
        ]

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    def analyze_slide(self, slide_data: dict[str, Any]) -> SlopReport:
        """
        Analyze a single slide for AI-slop indicators.

        Args:
            slide_data: Dict with keys like 'elements', 'background',
                       'content', 'style', etc. — flat or DSL-like structure

        Returns:
            SlopReport with violations, scores, and fix suggestions
        """
        violations = []
        total_weight = 0.0
        slop_weight = 0.0

        for rule in self._rules:
            total_weight += rule.weight
            violation = rule.check(slide_data)
            if violation is not None:
                violations.append(violation)
                slop_weight += rule.weight * violation.confidence

        # Compute scores
        slop_score = (slop_weight / total_weight * 100) if total_weight > 0 else 0
        quality_score = max(0, 100 - slop_score)

        fixes_available = sum(1 for v in violations if v.auto_fixable)

        # Generate summary
        if not violations:
            summary = "Clean design — no AI-slop detected"
        elif slop_score < 25:
            summary = f"Minor issues: {len(violations)} indicator(s) flagged"
        elif slop_score < 50:
            summary = f"Moderate slop: {len(violations)} indicator(s) need attention"
        else:
            summary = f"High AI-slop: {len(violations)} critical indicators detected"

        return SlopReport(
            violations=violations,
            slop_score=round(slop_score, 1),
            quality_score=round(quality_score, 1),
            fixes_applied=0,
            fixes_available=fixes_available,
            summary=summary,
        )

    def analyze_presentation(
        self,
        slides: list[dict[str, Any]],
    ) -> SlopReport:
        """
        Analyze an entire presentation for AI-slop indicators.
        Aggregates per-slide reports into a single presentation-level report.
        """
        all_violations = []
        total_slop = 0.0

        for slide in slides:
            report = self.analyze_slide(slide)
            all_violations.extend(report.violations)
            total_slop += report.slop_score

        avg_slop = total_slop / len(slides) if slides else 0
        quality = max(0, 100 - avg_slop)
        fixes = sum(1 for v in all_violations if v.auto_fixable)

        # Deck-level checks
        if len(slides) > MAX_SLIDES_PITCH_DECK:
            all_violations.append(SlopViolation(
                category=SlopCategory.CONTENT,
                severity=SlopSeverity.WARNING,
                indicator="too_many_slides",
                description=f"Presentation has {len(slides)} slides (max {MAX_SLIDES_PITCH_DECK})",
                suggestion="Consolidate or remove slides to keep audience engaged",
                auto_fixable=False,
                confidence=0.9,
            ))

        summary = f"Deck analysis: {len(slides)} slides, {len(all_violations)} issues, avg slop {avg_slop:.0f}%"

        return SlopReport(
            violations=all_violations,
            slop_score=round(avg_slop, 1),
            quality_score=round(quality, 1),
            fixes_applied=0,
            fixes_available=fixes,
            summary=summary,
        )

    def auto_fix(
        self,
        slide_data: dict[str, Any],
        report: SlopReport | None = None,
        brand_palette: list[str] | None = None,
        preferred_fonts: tuple[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Apply automatic fixes to slide data based on the slop report.

        Args:
            slide_data: Original slide data dict (will be copied, not mutated)
            report: SlopReport from analyze_slide (auto-generated if None)
            brand_palette: Optional brand colors to replace generic ones
            preferred_fonts: Optional (heading_font, body_font)

        Returns:
            New slide data dict with fixes applied
        """
        import copy
        fixed = copy.deepcopy(slide_data)

        if report is None:
            report = self.analyze_slide(slide_data)

        fixes_applied = 0

        for violation in report.violations:
            if not violation.auto_fixable:
                continue

            if violation.indicator == "generic_gradient":
                # Replace gradient colors with brand palette or solid bg
                if brand_palette and len(brand_palette) >= 2:
                    fixed.setdefault("background", {})["colors"] = brand_palette[:2]
                else:
                    fixed["background"] = {"type": "solid", "colors": ["#0F172A"]}
                violation.fix_applied = True
                fixes_applied += 1

            elif violation.indicator == "centered_everything":
                # Set content elements to left-aligned (keep title centered)
                for elem in fixed.get("elements", []):
                    elem_type = elem.get("type", "")
                    if elem_type != "text" or "heading" in elem.get("content", "").lower():
                        continue
                    elem.setdefault("style", {})["textAlign"] = "left"
                violation.fix_applied = True
                fixes_applied += 1

            elif violation.indicator == "no_whitespace":
                # Scale elements down by 10% to add breathing room
                for elem in fixed.get("elements", []):
                    size = elem.get("size", {})
                    if "width" in size:
                        size["width"] = round(size["width"] * 0.9, 3)
                    if "height" in size:
                        size["height"] = round(size["height"] * 0.9, 3)
                violation.fix_applied = True
                fixes_applied += 1

            elif violation.indicator == "generic_fonts":
                if preferred_fonts:
                    for elem in fixed.get("elements", []):
                        style = elem.get("style", {})
                        if "fontFamily" in style:
                            style["fontFamily"] = preferred_fonts[0]
                else:
                    for elem in fixed.get("elements", []):
                        style = elem.get("style", {})
                        if style.get("fontFamily") in ("Arial", "Helvetica", "sans-serif"):
                            style["fontFamily"] = "Inter"
                violation.fix_applied = True
                fixes_applied += 1

            elif violation.indicator == "small_font":
                for elem in fixed.get("elements", []):
                    style = elem.get("style", {})
                    if "fontSize" in style:
                        size_val = _parse_font_size(style["fontSize"])
                        if size_val is not None and size_val < MIN_FONT_SIZE_PT:
                            style["fontSize"] = f"{MIN_FONT_SIZE_PT}pt"
                violation.fix_applied = True
                fixes_applied += 1

            elif violation.indicator == "equal_spacing":
                # Add progressive spacing (tighter at top, wider at bottom)
                elements = fixed.get("elements", [])
                sorted_elems = sorted(
                    elements,
                    key=lambda e: e.get("position", {}).get("y", 0),
                )
                for i, elem in enumerate(sorted_elems):
                    pos = elem.get("position", {})
                    if "y" in pos and i > 0:
                        # Add increasingly larger gaps
                        offset = 0.01 * i
                        pos["y"] = round(pos["y"] + offset, 3)
                violation.fix_applied = True
                fixes_applied += 1

        report.fixes_applied = fixes_applied
        return fixed

    def get_rule_names(self) -> list[str]:
        """Return all rule names for testing/inspection."""
        return [r.name for r in self._rules]
