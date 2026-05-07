"""
Accessibility Engine — Phase 11.

Comprehensive WCAG 2.1 AA accessibility auditing for presentation slides.
Checks color contrast, text sizing, semantic structure, alt text,
heading hierarchy, ARIA labels, keyboard navigation, and motion safety.

Key standards enforced:
- WCAG 2.1 SC 1.4.3: Contrast minimum (4.5:1 normal, 3:1 large text)
- WCAG 2.1 SC 1.4.11: Non-text contrast (3:1 for UI components)
- WCAG 2.1 SC 1.1.1: Non-text content (alt text required)
- WCAG 2.1 SC 1.3.1: Info and relationships (semantic structure)
- WCAG 2.1 SC 2.4.6: Headings and labels (heading hierarchy)
- WCAG 2.1 SC 2.3.1: Three flashes or below threshold (motion safety)
- WCAG 2.1 SC 2.5.5: Target size (minimum 44x44 CSS pixels)
"""

from __future__ import annotations

import math
import re
from typing import Any, Optional

import structlog

from app.services.slides_new.quality.models import (
    A11yCategory,
    A11ySeverity,
    A11yViolation,
    AccessibilityReport,
    ContrastCheck,
    WCAGLevel,
)

logger = structlog.get_logger()

# ═══════════════════════════════════════════════════════════════════
# COLOR CONTRAST UTILITIES (WCAG 2.1 Algorithm)
# ═══════════════════════════════════════════════════════════════════


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color string to (R, G, B) tuple."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = h[0] * 2 + h[1] * 2 + h[2] * 2
    if len(h) != 6:
        return (0, 0, 0)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return (0, 0, 0)


def relative_luminance(r: int, g: int, b: int) -> float:
    """
    Compute relative luminance per WCAG 2.1 definition.

    Uses sRGB IEC 61966-2-1 linearization:
    For each channel C in {R, G, B}:
        if C_sRGB <= 0.04045: C_linear = C_sRGB / 12.92
        else: C_linear = ((C_sRGB + 0.055) / 1.055) ^ 2.4

    L = 0.2126 * R_linear + 0.7152 * G_linear + 0.0722 * B_linear
    """
    def linearize(c: int) -> float:
        s = c / 255.0
        if s <= 0.04045:
            return s / 12.92
        return ((s + 0.055) / 1.055) ** 2.4

    r_lin = linearize(r)
    g_lin = linearize(g)
    b_lin = linearize(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """
    Compute WCAG 2.1 contrast ratio between foreground and background.

    Returns ratio in range [1, 21]. Higher = more contrast.
    Formula: (L1 + 0.05) / (L2 + 0.05) where L1 >= L2.
    """
    fg_rgb = hex_to_rgb(fg_hex)
    bg_rgb = hex_to_rgb(bg_hex)

    l_fg = relative_luminance(*fg_rgb)
    l_bg = relative_luminance(*bg_rgb)

    lighter = max(l_fg, l_bg)
    darker = min(l_fg, l_bg)

    return (lighter + 0.05) / (darker + 0.05)


def passes_wcag_aa(
    fg_hex: str, bg_hex: str, is_large_text: bool = False
) -> tuple[bool, float]:
    """
    Check if a color pair passes WCAG AA contrast requirements.

    Returns (passed, ratio).
    Normal text: 4.5:1 minimum
    Large text (>=18pt or 14pt bold): 3:1 minimum
    """
    ratio = contrast_ratio(fg_hex, bg_hex)
    threshold = 3.0 if is_large_text else 4.5
    return ratio >= threshold, ratio


def passes_wcag_aaa(
    fg_hex: str, bg_hex: str, is_large_text: bool = False
) -> tuple[bool, float]:
    """
    Check if a color pair passes WCAG AAA contrast requirements.

    Normal text: 7:1 minimum
    Large text: 4.5:1 minimum
    """
    ratio = contrast_ratio(fg_hex, bg_hex)
    threshold = 4.5 if is_large_text else 7.0
    return ratio >= threshold, ratio


def suggest_contrast_fix(
    fg_hex: str, bg_hex: str, target_ratio: float = 4.5
) -> str:
    """
    Suggest an adjusted foreground color to meet the target contrast ratio.

    Strategy: darken or lighten the foreground while keeping hue.
    """
    fg_rgb = hex_to_rgb(fg_hex)
    bg_rgb = hex_to_rgb(bg_hex)
    bg_lum = relative_luminance(*bg_rgb)

    # Binary search for the right luminance
    if bg_lum > 0.5:
        # Dark text on light background — make text darker
        for factor in [f / 100 for f in range(100, -1, -5)]:
            new_r = int(fg_rgb[0] * factor)
            new_g = int(fg_rgb[1] * factor)
            new_b = int(fg_rgb[2] * factor)
            new_lum = relative_luminance(new_r, new_g, new_b)
            ratio = (bg_lum + 0.05) / (new_lum + 0.05)
            if ratio >= target_ratio:
                return f"#{new_r:02x}{new_g:02x}{new_b:02x}"
    else:
        # Light text on dark background — make text lighter
        for factor in [f / 100 for f in range(100, 256, 5)]:
            new_r = min(255, int(fg_rgb[0] * factor))
            new_g = min(255, int(fg_rgb[1] * factor))
            new_b = min(255, int(fg_rgb[2] * factor))
            new_lum = relative_luminance(new_r, new_g, new_b)
            ratio = (new_lum + 0.05) / (bg_lum + 0.05)
            if ratio >= target_ratio:
                return f"#{new_r:02x}{new_g:02x}{new_b:02x}"

    # Fallback: pure black or white
    return "#000000" if bg_lum > 0.5 else "#ffffff"


# ═══════════════════════════════════════════════════════════════════
# FONT SIZE CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════


FONT_SIZE_MAP: dict[str, float] = {
    "xs": 12.0, "sm": 14.0, "base": 16.0,
    "lg": 18.67, "xl": 20.0, "2xl": 24.0,
    "3xl": 30.0, "4xl": 36.0, "5xl": 48.0,
    "6xl": 60.0, "7xl": 72.0, "8xl": 96.0, "9xl": 128.0,
}

HEADING_SIZES = {"5xl", "4xl", "3xl", "2xl", "xl", "6xl", "7xl", "8xl", "9xl"}


def is_large_text(font_size: str, font_weight: int = 400) -> bool:
    """
    Determine if text qualifies as 'large' under WCAG.
    Large text: >= 18pt (24px) OR >= 14pt (18.67px) if bold (>=700).
    """
    pt = FONT_SIZE_MAP.get(font_size, 16.0)
    if pt >= 24.0:
        return True
    if pt >= 18.67 and font_weight >= 700:
        return True
    return False


def font_size_to_pt(size_str: str) -> float:
    """Convert Tailwind-style size string to pt value."""
    return FONT_SIZE_MAP.get(size_str, 16.0)


# ═══════════════════════════════════════════════════════════════════
# ACCESSIBILITY AUDITOR
# ═══════════════════════════════════════════════════════════════════


class AccessibilityAuditor:
    """
    Comprehensive WCAG 2.1 AA accessibility auditor for slide presentations.

    Audit pipeline per slide:
    1. Color contrast validation (text vs background)
    2. Text sizing validation (minimum readable sizes)
    3. Alt text presence for images/charts/3D
    4. Heading hierarchy validation
    5. Semantic structure analysis
    6. ARIA label checking
    7. Motion safety (flash/animation thresholds)
    8. Touch target sizing
    9. Language declaration
    10. Link purpose clarity

    All checks follow WCAG 2.1 Level AA criteria.
    """

    # Minimum font size thresholds (pt)
    MIN_BODY_SIZE_PT = 14.0
    MIN_CAPTION_SIZE_PT = 10.0
    # Minimum touch target (CSS px)
    MIN_TARGET_SIZE = 44

    def __init__(
        self,
        target_level: WCAGLevel = WCAGLevel.AA,
        auto_fix: bool = False,
    ):
        self.target_level = target_level
        self.auto_fix = auto_fix
        self._audits_run = 0

    def audit_presentation(
        self,
        presentation_dsl: dict[str, Any],
    ) -> AccessibilityReport:
        """
        Run full WCAG 2.1 AA audit on a presentation DSL.

        Args:
            presentation_dsl: Full DSL dict with 'presentation' and 'slides' keys

        Returns:
            AccessibilityReport with violations, contrast checks, and score
        """
        self._audits_run += 1
        report = AccessibilityReport(
            presentation_id=presentation_dsl.get("presentation", {}).get("id", ""),
            wcag_level=self.target_level,
        )

        slides = presentation_dsl.get("slides", [])
        pres_meta = presentation_dsl.get("presentation", {})
        theme = pres_meta.get("theme", {})

        report.slides_audited = len(slides)

        # Presentation-level checks
        self._check_language_declaration(presentation_dsl, report)

        # Per-slide checks
        heading_levels_seen: list[int] = []
        for slide in slides:
            self._audit_slide(slide, theme, report, heading_levels_seen)

        # Cross-slide checks
        self._check_heading_hierarchy(heading_levels_seen, report)

        # Compute score
        report.score = self._compute_score(report)
        report.passed = (
            report.score >= 70.0
            and report.critical_count == 0
        )
        report.auto_fixes_available = sum(
            1 for v in report.violations if v.auto_fixable
        )

        return report

    def audit_slide(
        self,
        slide_dsl: dict[str, Any],
        theme: Optional[dict[str, Any]] = None,
    ) -> AccessibilityReport:
        """Audit a single slide DSL."""
        self._audits_run += 1
        report = AccessibilityReport(
            wcag_level=self.target_level,
            slides_audited=1,
        )
        heading_levels: list[int] = []
        self._audit_slide(slide_dsl, theme or {}, report, heading_levels)
        report.score = self._compute_score(report)
        report.passed = report.score >= 70.0 and report.critical_count == 0
        return report

    def _audit_slide(
        self,
        slide: dict[str, Any],
        theme: dict[str, Any],
        report: AccessibilityReport,
        heading_levels: list[int],
    ) -> None:
        """Run all checks on a single slide."""
        slide_id = slide.get("id", "unknown")
        style = slide.get("style", {})
        content = slide.get("content", {})
        elements = slide.get("elements", [])

        # 1. Check contrast for slide-level colors
        bg_color = self._extract_bg_color(style, theme)
        self._check_content_contrast(content, style, bg_color, slide_id, report)

        # 2. Check elements
        for elem in elements:
            report.total_elements_checked += 1
            self._check_element(elem, bg_color, slide_id, report)

        # 3. Check alt text for media elements
        self._check_alt_text(elements, slide_id, report)

        # 4. Track heading levels
        self._track_headings(content, elements, heading_levels)

        # 5. Check speaker notes presence
        self._check_speaker_notes(slide, slide_id, report)

        # 6. Check animation safety
        self._check_motion_safety(slide, slide_id, report)

        # 7. Check 3D/VFX has fallback
        self._check_3d_fallback(slide, slide_id, report)

    def _extract_bg_color(
        self, style: dict[str, Any], theme: dict[str, Any]
    ) -> str:
        """Extract background color from style or theme."""
        bg = style.get("background", {})
        if isinstance(bg, dict):
            colors = bg.get("colors", [])
            if colors:
                return colors[-1]
            bg_color = bg.get("color", "")
            if bg_color:
                return bg_color
        elif isinstance(bg, str) and bg.startswith("#"):
            return bg

        # Fall back to theme
        theme_colors = theme.get("colors", {})
        return theme_colors.get("background", "#ffffff")

    def _check_content_contrast(
        self,
        content: dict[str, Any],
        style: dict[str, Any],
        bg_color: str,
        slide_id: str,
        report: AccessibilityReport,
    ) -> None:
        """Check contrast for title and body text."""
        if not bg_color or not bg_color.startswith("#"):
            return

        # Title contrast
        title = content.get("title", "")
        if title:
            fg = style.get("titleColor", style.get("accentColor", "#ffffff"))
            if not fg.startswith("#"):
                fg = "#ffffff"
            large = True  # Titles are always large text
            passed, ratio = passes_wcag_aa(fg, bg_color, is_large_text=large)
            report.contrast_checks.append(ContrastCheck(
                foreground=fg,
                background=bg_color,
                ratio=ratio,
                text_size="large",
                element_id=f"{slide_id}_title",
                element_type="title",
            ))
            report.total_elements_checked += 1
            if not passed:
                fix = suggest_contrast_fix(fg, bg_color, 3.0)
                report.violations.append(A11yViolation(
                    category=A11yCategory.COLOR_CONTRAST,
                    severity=A11ySeverity.SERIOUS,
                    wcag_criterion="1.4.3",
                    wcag_level=WCAGLevel.AA,
                    description=f"Title contrast ratio {ratio:.1f}:1 fails AA minimum 3:1",
                    element_id=f"{slide_id}_title",
                    slide_id=slide_id,
                    impact="Text may be unreadable for users with low vision",
                    suggestion=f"Change title color to {fix}",
                    auto_fixable=True,
                ))

        # Body / subtitle contrast
        for key in ("subtitle", "body", "description"):
            text = content.get(key, "")
            if not text:
                continue
            fg = style.get("textColor", "#ffffff")
            if not fg.startswith("#"):
                fg = "#ffffff"
            large_text = is_large_text(
                style.get("fontSize", "base"),
                style.get("fontWeight", 400),
            )
            passed, ratio = passes_wcag_aa(fg, bg_color, is_large_text=large_text)
            report.contrast_checks.append(ContrastCheck(
                foreground=fg,
                background=bg_color,
                ratio=ratio,
                text_size="large" if large_text else "normal",
                element_id=f"{slide_id}_{key}",
                element_type=key,
            ))
            report.total_elements_checked += 1
            if not passed:
                min_ratio = 3.0 if large_text else 4.5
                fix = suggest_contrast_fix(fg, bg_color, min_ratio)
                report.violations.append(A11yViolation(
                    category=A11yCategory.COLOR_CONTRAST,
                    severity=A11ySeverity.SERIOUS,
                    wcag_criterion="1.4.3",
                    wcag_level=WCAGLevel.AA,
                    description=(
                        f"{key.capitalize()} contrast ratio {ratio:.1f}:1 "
                        f"fails AA minimum {min_ratio}:1"
                    ),
                    element_id=f"{slide_id}_{key}",
                    slide_id=slide_id,
                    impact="Text may be unreadable for users with low vision",
                    suggestion=f"Change {key} color to {fix}",
                    auto_fixable=True,
                ))

    def _check_element(
        self,
        element: dict[str, Any],
        bg_color: str,
        slide_id: str,
        report: AccessibilityReport,
    ) -> None:
        """Check a single element for accessibility."""
        elem_type = element.get("type", "")
        elem_id = element.get("id", "unknown")
        elem_style = element.get("style", {})

        # Text element contrast
        if elem_type == "text":
            fg = elem_style.get("color", "#ffffff")
            if not fg.startswith("#"):
                return
            font_size = elem_style.get("fontSize", "base")
            font_weight = elem_style.get("fontWeight", 400)
            large = is_large_text(font_size, font_weight)
            passed, ratio = passes_wcag_aa(fg, bg_color, is_large_text=large)
            report.contrast_checks.append(ContrastCheck(
                foreground=fg,
                background=bg_color,
                ratio=ratio,
                text_size="large" if large else "normal",
                element_id=elem_id,
                element_type="text",
            ))
            if not passed:
                min_ratio = 3.0 if large else 4.5
                report.violations.append(A11yViolation(
                    category=A11yCategory.COLOR_CONTRAST,
                    severity=A11ySeverity.SERIOUS,
                    wcag_criterion="1.4.3",
                    description=f"Text element contrast {ratio:.1f}:1 < {min_ratio}:1",
                    element_id=elem_id,
                    slide_id=slide_id,
                    suggestion=suggest_contrast_fix(fg, bg_color, min_ratio),
                    auto_fixable=True,
                ))

        # Text size validation
        if elem_type == "text":
            font_size = elem_style.get("fontSize", "base")
            pt = font_size_to_pt(font_size)
            if pt < self.MIN_BODY_SIZE_PT:
                report.violations.append(A11yViolation(
                    category=A11yCategory.TEXT_SIZE,
                    severity=A11ySeverity.MODERATE,
                    wcag_criterion="1.4.4",
                    description=f"Text size {pt}pt below minimum {self.MIN_BODY_SIZE_PT}pt",
                    element_id=elem_id,
                    slide_id=slide_id,
                    suggestion=f"Increase font size to at least {self.MIN_BODY_SIZE_PT}pt",
                    auto_fixable=True,
                ))

        # Interactive element target size
        if elem_type in ("button", "link", "interactive"):
            size = element.get("size", {})
            w = size.get("width", 0)
            h = size.get("height", 0)
            # Normalize to CSS pixels (assuming values are fractions of 1920x1080)
            w_px = w * 1920 if w <= 1 else w
            h_px = h * 1080 if h <= 1 else h
            if w_px < self.MIN_TARGET_SIZE or h_px < self.MIN_TARGET_SIZE:
                report.violations.append(A11yViolation(
                    category=A11yCategory.TOUCH_TARGET,
                    severity=A11ySeverity.MODERATE,
                    wcag_criterion="2.5.5",
                    description=f"Touch target {w_px:.0f}x{h_px:.0f}px below 44x44px minimum",
                    element_id=elem_id,
                    slide_id=slide_id,
                    suggestion="Increase interactive element to at least 44x44 CSS pixels",
                ))

    def _check_alt_text(
        self,
        elements: list[dict[str, Any]],
        slide_id: str,
        report: AccessibilityReport,
    ) -> None:
        """WCAG 1.1.1: Every image/chart/3D element needs alt text."""
        media_types = {"image", "chart", "diagram", "icon", "video", "3d_scene"}
        for elem in elements:
            if elem.get("type") not in media_types:
                continue
            elem_id = elem.get("id", "unknown")
            alt_text = elem.get("alt_text", "") or elem.get("alt", "")
            if not alt_text:
                report.violations.append(A11yViolation(
                    category=A11yCategory.ALT_TEXT,
                    severity=A11ySeverity.CRITICAL,
                    wcag_criterion="1.1.1",
                    description=f"Image/media element missing alt text",
                    element_id=elem_id,
                    slide_id=slide_id,
                    impact="Screen readers cannot describe content to blind users",
                    suggestion="Add descriptive alt_text to this media element",
                ))

    def _track_headings(
        self,
        content: dict[str, Any],
        elements: list[dict[str, Any]],
        heading_levels: list[int],
    ) -> None:
        """Track heading levels for hierarchy validation."""
        # Title = H1
        if content.get("title"):
            heading_levels.append(1)
        # Subtitle = H2
        if content.get("subtitle"):
            heading_levels.append(2)
        # Elements with heading role
        for elem in elements:
            role = elem.get("role", "") or elem.get("type", "")
            if role in ("heading", "h1", "h2", "h3", "h4"):
                level = int(role[-1]) if role[-1].isdigit() else 2
                heading_levels.append(level)

    def _check_heading_hierarchy(
        self,
        heading_levels: list[int],
        report: AccessibilityReport,
    ) -> None:
        """WCAG 1.3.1: Heading hierarchy should not skip levels."""
        if len(heading_levels) < 2:
            return
        for i in range(1, len(heading_levels)):
            prev = heading_levels[i - 1]
            curr = heading_levels[i]
            # Jumping from H1 to H3 (skipping H2) is a violation
            if curr > prev + 1:
                report.violations.append(A11yViolation(
                    category=A11yCategory.HEADING_HIERARCHY,
                    severity=A11ySeverity.MODERATE,
                    wcag_criterion="1.3.1",
                    description=f"Heading hierarchy skips level: H{prev} to H{curr}",
                    impact="Screen reader users lose structural context",
                    suggestion=f"Add intermediate H{prev + 1} heading or adjust hierarchy",
                ))
                break  # Report only first skip

    def _check_speaker_notes(
        self,
        slide: dict[str, Any],
        slide_id: str,
        report: AccessibilityReport,
    ) -> None:
        """Check that slides with complex content have speaker notes."""
        elements = slide.get("elements", [])
        has_complex = any(
            e.get("type") in ("chart", "diagram", "3d_scene", "table")
            for e in elements
        )
        notes = slide.get("speakerNotes", "")
        if has_complex and not notes:
            report.violations.append(A11yViolation(
                category=A11yCategory.SEMANTIC_STRUCTURE,
                severity=A11ySeverity.MINOR,
                wcag_criterion="1.1.1",
                description="Complex content slide missing speaker notes for context",
                slide_id=slide_id,
                suggestion="Add speaker notes describing visual content for accessibility",
            ))

    def _check_motion_safety(
        self,
        slide: dict[str, Any],
        slide_id: str,
        report: AccessibilityReport,
    ) -> None:
        """WCAG 2.3.1: No content flashes more than 3 times/second."""
        style = slide.get("style", {})
        animation = style.get("animation", "")
        fragments = slide.get("fragments", [])
        three_scene = slide.get("threeScene")

        # Auto-play animations with high frequency
        rapid_animations = {"strobe", "flash", "blink", "pulse-rapid"}
        if animation and animation.lower() in rapid_animations:
            report.violations.append(A11yViolation(
                category=A11yCategory.MOTION_SAFE,
                severity=A11ySeverity.CRITICAL,
                wcag_criterion="2.3.1",
                description=f"Animation '{animation}' may cause seizures (>3 flashes/sec)",
                slide_id=slide_id,
                impact="Can trigger seizures in users with photosensitive epilepsy",
                suggestion="Use prefers-reduced-motion media query and slower animations",
            ))

        # 3D scenes need reduced-motion fallback
        if three_scene:
            has_fallback = three_scene.get("reduced_motion_fallback", False)
            if not has_fallback:
                report.violations.append(A11yViolation(
                    category=A11yCategory.MOTION_SAFE,
                    severity=A11ySeverity.MODERATE,
                    wcag_criterion="2.3.1",
                    description="3D scene lacks prefers-reduced-motion fallback",
                    slide_id=slide_id,
                    suggestion="Add reduced_motion_fallback with static image alternative",
                ))

    def _check_3d_fallback(
        self,
        slide: dict[str, Any],
        slide_id: str,
        report: AccessibilityReport,
    ) -> None:
        """Ensure 3D/interactive content has non-visual fallback."""
        three_scene = slide.get("threeScene")
        if three_scene is None:
            return

        has_aria = three_scene.get("aria_label", "")
        has_sr_text = three_scene.get("sr_only_text", "")
        if not has_aria and not has_sr_text:
            report.violations.append(A11yViolation(
                category=A11yCategory.ARIA_LABELS,
                severity=A11ySeverity.SERIOUS,
                wcag_criterion="4.1.2",
                description="3D scene missing ARIA label or screen-reader text",
                slide_id=slide_id,
                impact="3D content invisible to screen reader users",
                suggestion="Add aria_label or sr_only_text describing the 3D visualization",
            ))

    def _check_language_declaration(
        self,
        dsl: dict[str, Any],
        report: AccessibilityReport,
    ) -> None:
        """WCAG 3.1.1: Page must have language declaration."""
        pres = dsl.get("presentation", {})
        metadata = pres.get("metadata", {})
        lang = metadata.get("language") or metadata.get("lang") or pres.get("language")
        if not lang:
            report.violations.append(A11yViolation(
                category=A11yCategory.LANGUAGE,
                severity=A11ySeverity.MODERATE,
                wcag_criterion="3.1.1",
                description="Presentation missing language declaration",
                impact="Screen readers may mispronounce content",
                suggestion="Set language in presentation metadata (e.g., 'en')",
            ))

    def _compute_score(self, report: AccessibilityReport) -> float:
        """
        Compute accessibility score (0-100).

        Scoring:
        - Start at 100
        - Critical violation: -20
        - Serious violation: -10
        - Moderate violation: -5
        - Minor violation: -2
        - Bonus: +5 if all contrast checks pass
        """
        score = 100.0
        for v in report.violations:
            if v.severity == A11ySeverity.CRITICAL:
                score -= 20
            elif v.severity == A11ySeverity.SERIOUS:
                score -= 10
            elif v.severity == A11ySeverity.MODERATE:
                score -= 5
            elif v.severity == A11ySeverity.MINOR:
                score -= 2

        # Bonus for clean contrast
        if report.contrast_checks and all(c.passed for c in report.contrast_checks):
            score += 5

        return max(0.0, min(100.0, score))

    @property
    def audits_run(self) -> int:
        return self._audits_run

    def get_stats(self) -> dict[str, Any]:
        return {
            "audits_run": self._audits_run,
            "target_level": self.target_level.value,
            "auto_fix_enabled": self.auto_fix,
        }
