"""
DSL Validator -- Deep validation beyond Pydantic model constraints.

Layer 1: Structural (Pydantic handles)
Layer 2: Semantic (this module)
    - Presentation-mode content density rules (V7 Plan §15.1)
    - Accessibility checks (contrast, alt text)
    - Slide count constraints
    - Pitch deck anti-pitfall rules
    - Layout-content coherence
"""

import re
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

from app.models.dsl_v2 import (
    ElementType,
    LayoutType,
    PresentationDSL,
    SlideDSL,
    SlideContentV2,
    SlideType,
)

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Severity & Issue types
# ---------------------------------------------------------------------------

class IssueSeverity(str, Enum):
    ERROR = "error"      # Must fix before export
    WARNING = "warning"  # Should fix for quality
    INFO = "info"        # Suggestion / best practice


class IssueCategory(str, Enum):
    CONTENT_DENSITY = "content-density"
    ACCESSIBILITY = "accessibility"
    STRUCTURE = "structure"
    PITCH_QUALITY = "pitch-quality"
    LAYOUT = "layout"
    CONSISTENCY = "consistency"


class ValidationIssue:
    """Single validation finding."""

    __slots__ = ("severity", "category", "slide_id", "message", "field", "suggestion")

    def __init__(
        self,
        severity: IssueSeverity,
        category: IssueCategory,
        message: str,
        slide_id: Optional[str] = None,
        field: Optional[str] = None,
        suggestion: Optional[str] = None,
    ):
        self.severity = severity
        self.category = category
        self.message = message
        self.slide_id = slide_id
        self.field = field
        self.suggestion = suggestion

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "slide_id": self.slide_id,
            "field": self.field,
            "suggestion": self.suggestion,
        }


class ValidationReport:
    """Aggregated validation results."""

    __slots__ = ("issues", "score", "passed")

    def __init__(self):
        self.issues: List[ValidationIssue] = []
        self.score: int = 100
        self.passed: bool = True

    def add(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)
        if issue.severity == IssueSeverity.ERROR:
            self.score = max(0, self.score - 10)
            self.passed = False
        elif issue.severity == IssueSeverity.WARNING:
            self.score = max(0, self.score - 3)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.INFO)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "issues": [i.to_dict() for i in self.issues],
        }


# ---------------------------------------------------------------------------
# Content density limits (V7 Plan §15.1)
# ---------------------------------------------------------------------------

PRESENTATION_LIMITS = {
    "title_max_words": 8,
    "subtitle_max_words": 12,
    "bullet_max_items": 5,
    "bullet_max_words": 15,
    "body_max_words": 60,
    "speaker_notes_min_points": 3,
}

# Slide count boundaries
MIN_SLIDES = 6
MAX_SLIDES = 30
OPTIMAL_RANGE = (8, 15)


# ---------------------------------------------------------------------------
# Hex colour helpers
# ---------------------------------------------------------------------------

_HEX_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def _hex_to_rgb(hex_str: str) -> Optional[tuple]:
    """Parse #RGB, #RRGGBB, or #RRGGBBAA to (R, G, B)."""
    if not hex_str or not _HEX_RE.match(hex_str):
        return None
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    elif len(h) == 8:
        h = h[:6]
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _relative_luminance(rgb: tuple) -> float:
    """WCAG 2.1 relative luminance."""
    vals = []
    for c in rgb:
        s = c / 255.0
        vals.append(s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4)
    return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]


def _contrast_ratio(c1: tuple, c2: tuple) -> float:
    """WCAG contrast ratio between two RGB tuples."""
    l1 = _relative_luminance(c1) + 0.05
    l2 = _relative_luminance(c2) + 0.05
    return max(l1, l2) / min(l1, l2)


def _word_count(text: Optional[str]) -> int:
    if not text:
        return 0
    return len(text.split())


# ---------------------------------------------------------------------------
# DSL Validator
# ---------------------------------------------------------------------------

class DSLValidator:
    """
    Validates a PresentationDSL beyond Pydantic model constraints.

    Runs all checks and returns a ValidationReport with scored issues.
    """

    def __init__(self, dsl: PresentationDSL):
        self._dsl = dsl

    @property
    def dsl(self) -> PresentationDSL:
        return self._dsl

    def validate(self) -> ValidationReport:
        """Run all validation checks."""
        report = ValidationReport()

        self._check_structure(report)
        self._check_content_density(report)
        self._check_accessibility(report)
        self._check_pitch_quality(report)
        self._check_layout_coherence(report)
        self._check_consistency(report)

        logger.info(
            "dsl_validated",
            passed=report.passed,
            score=report.score,
            errors=report.error_count,
            warnings=report.warning_count,
        )
        return report

    def validate_slide(self, slide_id: str) -> ValidationReport:
        """Validate a single slide."""
        report = ValidationReport()
        slide = self._find_slide(slide_id)
        if slide is None:
            report.add(ValidationIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.STRUCTURE,
                message=f"Slide '{slide_id}' not found",
            ))
            return report

        self._check_slide_content_density(report, slide)
        self._check_slide_accessibility(report, slide)
        self._check_slide_layout(report, slide)
        return report

    # ── Structure checks ──────────────────────────────────────────

    def _check_structure(self, report: ValidationReport) -> None:
        n = len(self._dsl.slides)

        # Slide count
        if n < MIN_SLIDES:
            report.add(ValidationIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.STRUCTURE,
                message=f"Too few slides ({n}). Minimum is {MIN_SLIDES}.",
                suggestion=f"Add more slides to cover core pitch sections.",
            ))
        elif n > MAX_SLIDES:
            report.add(ValidationIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.STRUCTURE,
                message=f"Too many slides ({n}). Maximum recommended is {MAX_SLIDES}.",
                suggestion="Consider consolidating or removing low-value slides.",
            ))
        elif not (OPTIMAL_RANGE[0] <= n <= OPTIMAL_RANGE[1]):
            report.add(ValidationIssue(
                severity=IssueSeverity.INFO,
                category=IssueCategory.STRUCTURE,
                message=f"Slide count ({n}) outside optimal range {OPTIMAL_RANGE}.",
                suggestion="8-15 slides is the sweet spot for pitch decks.",
            ))

        # Title slide presence
        has_title = any(s.type == SlideType.TITLE_SLIDE for s in self._dsl.slides)
        if not has_title:
            report.add(ValidationIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.STRUCTURE,
                message="Missing a title slide.",
                suggestion="Add a title slide as the first slide.",
            ))
        else:
            # Title slide should be first
            first = self._dsl.slides[0]
            if first.type != SlideType.TITLE_SLIDE:
                report.add(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.STRUCTURE,
                    message="Title slide is not the first slide.",
                    slide_id=first.id,
                    suggestion="Move the title slide to index 0.",
                ))

        # Closing slide presence
        has_closing = any(s.type == SlideType.CLOSING_SLIDE for s in self._dsl.slides)
        if not has_closing:
            report.add(ValidationIssue(
                severity=IssueSeverity.INFO,
                category=IssueCategory.STRUCTURE,
                message="No closing/CTA slide found.",
                suggestion="Add a closing slide with a clear call to action.",
            ))

        # Index continuity (Pydantic validates, but double-check)
        indexes = [s.index for s in self._dsl.slides]
        if sorted(indexes) != list(range(n)):
            report.add(ValidationIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.STRUCTURE,
                message="Slide indexes are not contiguous.",
            ))

        # Duplicate IDs
        ids = [s.id for s in self._dsl.slides]
        if len(ids) != len(set(ids)):
            report.add(ValidationIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.STRUCTURE,
                message="Duplicate slide IDs detected.",
            ))

    # ── Content density checks (V7 §15.1) ────────────────────────

    def _check_content_density(self, report: ValidationReport) -> None:
        for slide in self._dsl.slides:
            self._check_slide_content_density(report, slide)

    def _check_slide_content_density(self, report: ValidationReport, slide: SlideDSL) -> None:
        c = slide.content
        limits = PRESENTATION_LIMITS

        # Title length
        tw = _word_count(c.title)
        if tw > limits["title_max_words"]:
            report.add(ValidationIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.CONTENT_DENSITY,
                message=f"Title has {tw} words (max {limits['title_max_words']}): '{c.title[:50]}...'",
                slide_id=slide.id,
                field="content.title",
                suggestion="Shorten the title for stage readability.",
            ))

        # Subtitle length
        if c.subtitle:
            sw = _word_count(c.subtitle)
            if sw > limits["subtitle_max_words"]:
                report.add(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.CONTENT_DENSITY,
                    message=f"Subtitle has {sw} words (max {limits['subtitle_max_words']}).",
                    slide_id=slide.id,
                    field="content.subtitle",
                    suggestion="Shorten the subtitle.",
                ))

        # Bullet count and length
        if c.bullets:
            if len(c.bullets) > limits["bullet_max_items"]:
                report.add(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.CONTENT_DENSITY,
                    message=f"Too many bullets ({len(c.bullets)}, max {limits['bullet_max_items']}).",
                    slide_id=slide.id,
                    field="content.bullets",
                    suggestion="Keep to 5 key points maximum.",
                ))

            for idx, bullet in enumerate(c.bullets):
                bw = _word_count(bullet)
                if bw > limits["bullet_max_words"]:
                    report.add(ValidationIssue(
                        severity=IssueSeverity.INFO,
                        category=IssueCategory.CONTENT_DENSITY,
                        message=f"Bullet #{idx+1} has {bw} words (max {limits['bullet_max_words']}).",
                        slide_id=slide.id,
                        field=f"content.bullets[{idx}]",
                        suggestion="Start with action verb or metric, keep concise.",
                    ))

        # Body text length
        if c.body_text:
            bw = _word_count(c.body_text)
            if bw > limits["body_max_words"]:
                report.add(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.CONTENT_DENSITY,
                    message=f"Body text has {bw} words (max {limits['body_max_words']}).",
                    slide_id=slide.id,
                    field="content.body_text",
                    suggestion="Move details to speaker notes or reading mode.",
                ))

        # Empty slide check
        has_content = any([
            c.title, c.body_text, c.bullets,
            c.chart_data, c.team_members, c.timeline_items,
            c.comparison_items, c.kpi_metrics, c.quote_text,
            c.image_url, c.image_prompt,
        ])
        if not has_content:
            report.add(ValidationIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.CONTENT_DENSITY,
                message="Slide has no content.",
                slide_id=slide.id,
                suggestion="Add content or remove the slide.",
            ))

    # ── Accessibility checks ──────────────────────────────────────

    def _check_accessibility(self, report: ValidationReport) -> None:
        for slide in self._dsl.slides:
            self._check_slide_accessibility(report, slide)

    def _check_slide_accessibility(self, report: ValidationReport, slide: SlideDSL) -> None:
        # Check image alt text
        for elem in slide.elements:
            if elem.type == ElementType.IMAGE and not elem.alt_text:
                report.add(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.ACCESSIBILITY,
                    message=f"Image element '{elem.id}' missing alt text.",
                    slide_id=slide.id,
                    field=f"elements.{elem.id}.alt_text",
                    suggestion="Add descriptive alt text for screen readers.",
                ))

        # Check text contrast against background
        bg_colors = slide.style.background.colors
        if bg_colors:
            bg_rgb = _hex_to_rgb(bg_colors[0])
            if bg_rgb:
                for elem in slide.elements:
                    if elem.type == ElementType.TEXT and elem.style.color:
                        fg_rgb = _hex_to_rgb(elem.style.color)
                        if fg_rgb:
                            ratio = _contrast_ratio(fg_rgb, bg_rgb)
                            if ratio < 4.5:
                                report.add(ValidationIssue(
                                    severity=IssueSeverity.WARNING,
                                    category=IssueCategory.ACCESSIBILITY,
                                    message=(
                                        f"Text element '{elem.id}' has low contrast "
                                        f"ratio ({ratio:.1f}:1, minimum 4.5:1)."
                                    ),
                                    slide_id=slide.id,
                                    field=f"elements.{elem.id}.style.color",
                                    suggestion="Increase contrast for readability.",
                                ))

        # Font size check
        for elem in slide.elements:
            if elem.type == ElementType.TEXT and elem.style.fontSize:
                if elem.style.fontSize < 14:
                    report.add(ValidationIssue(
                        severity=IssueSeverity.INFO,
                        category=IssueCategory.ACCESSIBILITY,
                        message=f"Element '{elem.id}' font size {elem.style.fontSize}px may be too small for projection.",
                        slide_id=slide.id,
                        field=f"elements.{elem.id}.style.fontSize",
                        suggestion="Use at least 18px for body text on projected slides.",
                    ))

    # ── Pitch quality checks ─────────────────────────────────────

    def _check_pitch_quality(self, report: ValidationReport) -> None:
        slide_types = [s.type for s in self._dsl.slides]

        # Essential pitch sections
        essential = {
            SlideType.PROBLEM_SLIDE: "Problem",
            SlideType.SOLUTION_SLIDE: "Solution",
            SlideType.MARKET_SLIDE: "Market",
        }
        for st, name in essential.items():
            if st not in slide_types:
                report.add(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.PITCH_QUALITY,
                    message=f"Missing essential pitch section: {name}.",
                    suggestion=f"Every pitch deck should have a {name} slide.",
                ))

        # Anti-pitfall: "No Competition" claim
        for slide in self._dsl.slides:
            if slide.type == SlideType.COMPETITION_SLIDE:
                text = (slide.content.body_text or "") + " ".join(slide.content.bullets or [])
                if re.search(r"no\s+compet", text, re.IGNORECASE):
                    report.add(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        category=IssueCategory.PITCH_QUALITY,
                        message="Anti-pitfall: Claiming 'No Competition' is an investor red flag.",
                        slide_id=slide.id,
                        field="content",
                        suggestion="Every startup has competition. Show alternatives and why you win.",
                    ))

        # Anti-pitfall: Market slide should have TAM/SAM/SOM with bottom-up
        for slide in self._dsl.slides:
            if slide.type == SlideType.MARKET_SLIDE:
                text = (slide.content.body_text or "") + " ".join(slide.content.bullets or [])
                title = slide.content.title or ""
                combined = title + " " + text
                has_market_sizing = any(
                    kw in combined.lower()
                    for kw in ["tam", "sam", "som", "market size", "addressable"]
                )
                if not has_market_sizing:
                    report.add(ValidationIssue(
                        severity=IssueSeverity.INFO,
                        category=IssueCategory.PITCH_QUALITY,
                        message="Market slide may lack TAM/SAM/SOM sizing.",
                        slide_id=slide.id,
                        suggestion="Include bottom-up market sizing (TAM > SAM > SOM).",
                    ))

        # Speaker notes coverage
        slides_without_notes = [
            s for s in self._dsl.slides
            if not s.speakerNotes and s.type not in (SlideType.TITLE_SLIDE, SlideType.CLOSING_SLIDE)
        ]
        if slides_without_notes:
            report.add(ValidationIssue(
                severity=IssueSeverity.INFO,
                category=IssueCategory.PITCH_QUALITY,
                message=f"{len(slides_without_notes)} content slides lack speaker notes.",
                suggestion="Add 3-5 talking points per slide for presenter preparation.",
            ))

    # ── Layout coherence checks ───────────────────────────────────

    def _check_layout_coherence(self, report: ValidationReport) -> None:
        for slide in self._dsl.slides:
            self._check_slide_layout(report, slide)

    def _check_slide_layout(self, report: ValidationReport, slide: SlideDSL) -> None:
        c = slide.content

        # Timeline layout needs timeline data
        if slide.layout == LayoutType.TIMELINE and not c.timeline_items:
            report.add(ValidationIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.LAYOUT,
                message="Slide uses timeline layout but has no timeline data.",
                slide_id=slide.id,
                suggestion="Add timeline_items or switch to a different layout.",
            ))

        # Comparison layout needs comparison data
        if slide.layout == LayoutType.COMPARISON and not c.comparison_items:
            report.add(ValidationIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.LAYOUT,
                message="Slide uses comparison layout but has no comparison data.",
                slide_id=slide.id,
                suggestion="Add comparison_items or switch to a different layout.",
            ))

        # Team grid layout needs team data
        if slide.layout == LayoutType.TEAM_GRID and not c.team_members:
            report.add(ValidationIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.LAYOUT,
                message="Slide uses team-grid layout but has no team data.",
                slide_id=slide.id,
                suggestion="Add team_members or switch to a different layout.",
            ))

        # KPI dashboard needs metrics
        if slide.layout == LayoutType.KPI_DASHBOARD and not c.kpi_metrics:
            report.add(ValidationIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.LAYOUT,
                message="Slide uses KPI dashboard layout but has no KPI metrics.",
                slide_id=slide.id,
                suggestion="Add kpi_metrics or switch to a different layout.",
            ))

        # Chart layout needs chart data
        if slide.layout == LayoutType.CHART and not c.chart_data:
            report.add(ValidationIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.LAYOUT,
                message="Slide uses chart layout but has no chart data.",
                slide_id=slide.id,
                suggestion="Add chart_data or switch layout.",
            ))

        # Quote layout needs quote content
        if slide.layout == LayoutType.QUOTE and not c.quote_text:
            report.add(ValidationIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.LAYOUT,
                message="Slide uses quote layout but has no quote text.",
                slide_id=slide.id,
                suggestion="Add quote_text or switch layout.",
            ))

    # ── Consistency checks ────────────────────────────────────────

    def _check_consistency(self, report: ValidationReport) -> None:
        if not self._dsl.slides:
            return

        # Check for section coverage
        sections = [s.section for s in self._dsl.slides if s.section]
        if sections:
            orphans = [s for s in self._dsl.slides if not s.section]
            if orphans and len(orphans) < len(self._dsl.slides):
                report.add(ValidationIssue(
                    severity=IssueSeverity.INFO,
                    category=IssueCategory.CONSISTENCY,
                    message=f"{len(orphans)} slide(s) not assigned to any section.",
                    suggestion="Assign all slides to sections for better navigation.",
                ))

        # Theme consistency: check if all slides use same accent color
        accent_colors = set()
        for slide in self._dsl.slides:
            if slide.style.accentColor:
                accent_colors.add(slide.style.accentColor.lower())
        if len(accent_colors) > 3:
            report.add(ValidationIssue(
                severity=IssueSeverity.INFO,
                category=IssueCategory.CONSISTENCY,
                message=f"Using {len(accent_colors)} different accent colors.",
                suggestion="Limit accent colors to 2-3 for brand consistency.",
            ))

        # Presentation title check
        if not self._dsl.presentation.title:
            report.add(ValidationIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.CONSISTENCY,
                message="Presentation has no title.",
            ))

    # ── Helpers ───────────────────────────────────────────────────

    def _find_slide(self, slide_id: str) -> Optional[SlideDSL]:
        for s in self._dsl.slides:
            if s.id == slide_id:
                return s
        return None
