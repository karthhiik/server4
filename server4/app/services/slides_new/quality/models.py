"""
Quality Models — Phase 11.

All data models for the QA + Polish + Delivery system:
- Visual regression (SSIM golden-master comparison)
- Accessibility (WCAG 2.1 AA compliance)
- Presentation / Reading mode configuration
- Production hardening (load testing, health checks)
- Unified quality orchestration
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ═══════════════════════════════════════════════════════════════════
# VISUAL REGRESSION MODELS
# ═══════════════════════════════════════════════════════════════════


class RegressionStatus(str, Enum):
    """Result of a visual regression comparison."""
    PASS = "pass"
    FAIL = "fail"
    NEW_BASELINE = "new_baseline"
    ERROR = "error"


class DiffRegion(str, Enum):
    """Region classification in diff maps."""
    LAYOUT_SHIFT = "layout_shift"
    COLOR_CHANGE = "color_change"
    TEXT_CHANGE = "text_change"
    ELEMENT_MISSING = "element_missing"
    ELEMENT_ADDED = "element_added"
    STRUCTURAL = "structural"


@dataclass
class PixelStats:
    """Low-level pixel statistics for an image region."""
    width: int = 0
    height: int = 0
    total_pixels: int = 0
    mean_r: float = 0.0
    mean_g: float = 0.0
    mean_b: float = 0.0
    variance: float = 0.0
    checksum: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "total_pixels": self.total_pixels,
            "mean_r": round(self.mean_r, 4),
            "mean_g": round(self.mean_g, 4),
            "mean_b": round(self.mean_b, 4),
            "variance": round(self.variance, 4),
            "checksum": self.checksum,
        }


@dataclass
class SSIMResult:
    """Result of Structural Similarity Index computation."""
    score: float = 0.0              # -1.0 to 1.0 (1.0 = identical)
    luminance: float = 0.0          # Luminance component
    contrast: float = 0.0           # Contrast component
    structure: float = 0.0          # Structure component
    window_size: int = 11           # Sliding window size used
    k1: float = 0.01               # Stability constant 1
    k2: float = 0.03               # Stability constant 2
    dynamic_range: int = 255        # Pixel value range (8-bit)
    computation_time_ms: float = 0.0

    @property
    def is_similar(self) -> bool:
        """SSIM >= 0.85 is considered structurally similar."""
        return self.score >= 0.85

    @property
    def dissimilarity(self) -> float:
        """DSSIM = (1 - SSIM) / 2."""
        return (1.0 - self.score) / 2.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 6),
            "luminance": round(self.luminance, 6),
            "contrast": round(self.contrast, 6),
            "structure": round(self.structure, 6),
            "is_similar": self.is_similar,
            "dissimilarity": round(self.dissimilarity, 6),
            "window_size": self.window_size,
            "computation_time_ms": round(self.computation_time_ms, 2),
        }


@dataclass
class DiffMapEntry:
    """A single region of visual difference."""
    region: DiffRegion
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    severity: float = 0.0   # 0-1 how severe the diff is
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "region": self.region.value,
            "x": self.x, "y": self.y,
            "width": self.width, "height": self.height,
            "severity": round(self.severity, 4),
            "description": self.description,
        }


@dataclass
class GoldenMaster:
    """Reference screenshot for regression testing."""
    id: str = ""
    slide_id: str = ""
    presentation_id: str = ""
    renderer: str = ""
    resolution: tuple[int, int] = (1920, 1080)
    pixel_data: bytes = b""
    pixel_stats: Optional[PixelStats] = None
    created_at: float = 0.0
    theme_id: str = ""
    version: int = 1

    def __post_init__(self):
        if not self.id:
            self.id = f"gm_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()
        if self.pixel_data and not self.pixel_stats:
            self.pixel_stats = PixelStats(
                width=self.resolution[0],
                height=self.resolution[1],
                total_pixels=self.resolution[0] * self.resolution[1],
                checksum=hashlib.sha256(self.pixel_data).hexdigest()[:16],
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "slide_id": self.slide_id,
            "presentation_id": self.presentation_id,
            "renderer": self.renderer,
            "resolution": list(self.resolution),
            "pixel_stats": self.pixel_stats.to_dict() if self.pixel_stats else None,
            "created_at": self.created_at,
            "theme_id": self.theme_id,
            "version": self.version,
        }


@dataclass
class VisualRegressionResult:
    """Complete visual regression comparison result."""
    slide_id: str = ""
    status: RegressionStatus = RegressionStatus.PASS
    ssim: Optional[SSIMResult] = None
    diff_regions: list[DiffMapEntry] = field(default_factory=list)
    golden_master_id: str = ""
    threshold: float = 0.85
    pixel_diff_percentage: float = 0.0
    error: Optional[str] = None
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    @property
    def passed(self) -> bool:
        return self.status == RegressionStatus.PASS

    @property
    def diff_count(self) -> int:
        return len(self.diff_regions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slide_id": self.slide_id,
            "status": self.status.value,
            "ssim": self.ssim.to_dict() if self.ssim else None,
            "diff_regions": [d.to_dict() for d in self.diff_regions],
            "golden_master_id": self.golden_master_id,
            "threshold": self.threshold,
            "pixel_diff_percentage": round(self.pixel_diff_percentage, 4),
            "passed": self.passed,
            "diff_count": self.diff_count,
            "error": self.error,
            "timestamp": self.timestamp,
        }


# ═══════════════════════════════════════════════════════════════════
# ACCESSIBILITY MODELS
# ═══════════════════════════════════════════════════════════════════


class WCAGLevel(str, Enum):
    """WCAG conformance level."""
    A = "A"
    AA = "AA"
    AAA = "AAA"


class A11ySeverity(str, Enum):
    """Accessibility violation severity."""
    CRITICAL = "critical"
    SERIOUS = "serious"
    MODERATE = "moderate"
    MINOR = "minor"


class A11yCategory(str, Enum):
    """Categories of accessibility checks."""
    COLOR_CONTRAST = "color_contrast"
    TEXT_SIZE = "text_size"
    ALT_TEXT = "alt_text"
    HEADING_HIERARCHY = "heading_hierarchy"
    SEMANTIC_STRUCTURE = "semantic_structure"
    KEYBOARD_NAV = "keyboard_nav"
    ARIA_LABELS = "aria_labels"
    FOCUS_ORDER = "focus_order"
    TOUCH_TARGET = "touch_target"
    MOTION_SAFE = "motion_safe"
    LANGUAGE = "language"
    LINK_PURPOSE = "link_purpose"


@dataclass
class ContrastCheck:
    """Result of a single WCAG contrast check."""
    foreground: str = ""
    background: str = ""
    ratio: float = 0.0
    required_ratio: float = 4.5
    level: WCAGLevel = WCAGLevel.AA
    text_size: str = "normal"  # "normal" or "large"
    passed: bool = False
    element_id: str = ""
    element_type: str = ""

    def __post_init__(self):
        req = 3.0 if self.text_size == "large" else 4.5
        self.required_ratio = req
        self.passed = self.ratio >= req

    def to_dict(self) -> dict[str, Any]:
        return {
            "foreground": self.foreground,
            "background": self.background,
            "ratio": round(self.ratio, 2),
            "required_ratio": self.required_ratio,
            "level": self.level.value,
            "text_size": self.text_size,
            "passed": self.passed,
            "element_id": self.element_id,
            "element_type": self.element_type,
        }


@dataclass
class A11yViolation:
    """A single accessibility violation."""
    id: str = ""
    category: A11yCategory = A11yCategory.COLOR_CONTRAST
    severity: A11ySeverity = A11ySeverity.MODERATE
    wcag_criterion: str = ""       # e.g. "1.4.3"
    wcag_level: WCAGLevel = WCAGLevel.AA
    description: str = ""
    element_id: str = ""
    slide_id: str = ""
    impact: str = ""
    suggestion: str = ""
    auto_fixable: bool = False

    def __post_init__(self):
        if not self.id:
            self.id = f"a11y_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "severity": self.severity.value,
            "wcag_criterion": self.wcag_criterion,
            "wcag_level": self.wcag_level.value,
            "description": self.description,
            "element_id": self.element_id,
            "slide_id": self.slide_id,
            "impact": self.impact,
            "suggestion": self.suggestion,
            "auto_fixable": self.auto_fixable,
        }


@dataclass
class AccessibilityReport:
    """Complete accessibility audit result."""
    presentation_id: str = ""
    wcag_level: WCAGLevel = WCAGLevel.AA
    passed: bool = False
    score: float = 0.0            # 0-100
    violations: list[A11yViolation] = field(default_factory=list)
    contrast_checks: list[ContrastCheck] = field(default_factory=list)
    slides_audited: int = 0
    total_elements_checked: int = 0
    auto_fixes_available: int = 0
    auto_fixes_applied: int = 0
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    @property
    def critical_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == A11ySeverity.CRITICAL)

    @property
    def serious_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == A11ySeverity.SERIOUS)

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    @property
    def contrast_pass_rate(self) -> float:
        if not self.contrast_checks:
            return 100.0
        passed = sum(1 for c in self.contrast_checks if c.passed)
        return (passed / len(self.contrast_checks)) * 100.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "presentation_id": self.presentation_id,
            "wcag_level": self.wcag_level.value,
            "passed": self.passed,
            "score": round(self.score, 1),
            "violation_count": self.violation_count,
            "critical_count": self.critical_count,
            "serious_count": self.serious_count,
            "contrast_pass_rate": round(self.contrast_pass_rate, 1),
            "violations": [v.to_dict() for v in self.violations],
            "contrast_checks": [c.to_dict() for c in self.contrast_checks],
            "slides_audited": self.slides_audited,
            "total_elements_checked": self.total_elements_checked,
            "auto_fixes_available": self.auto_fixes_available,
            "auto_fixes_applied": self.auto_fixes_applied,
            "timestamp": self.timestamp,
        }


# ═══════════════════════════════════════════════════════════════════
# PRESENTATION MODE MODELS
# ═══════════════════════════════════════════════════════════════════


class PresentationMode(str, Enum):
    """Primary display modes for presentation output."""
    READING = "reading"
    PRESENTATION = "presentation"
    OVERVIEW = "overview"
    SPEAKER = "speaker"
    PRINT = "print"


class NavigationType(str, Enum):
    """How the user navigates through content."""
    SCROLL = "scroll"           # Continuous scroll (reading mode)
    KEYBOARD = "keyboard"       # Arrow keys, space (presentation)
    CLICK = "click"             # Click-to-advance
    AUTO = "auto"               # Timed auto-advance


@dataclass
class ModeFeature:
    """A single feature toggle for a presentation mode."""
    name: str
    enabled: bool = True
    description: str = ""
    configurable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "description": self.description,
            "configurable": self.configurable,
        }


@dataclass
class ModeConfig:
    """Configuration for a presentation display mode."""
    mode: PresentationMode
    navigation: NavigationType = NavigationType.KEYBOARD
    features: list[ModeFeature] = field(default_factory=list)
    css_class: str = ""
    layout: str = ""                    # "slideshow", "scroll", "grid"
    show_speaker_notes: bool = False
    show_slide_numbers: bool = True
    show_progress_bar: bool = True
    show_toc_sidebar: bool = False
    enable_transitions: bool = True
    enable_fragments: bool = True
    enable_timer: bool = False
    dark_mode: Optional[bool] = None    # None = system default
    auto_advance_ms: int = 0            # 0 = no auto
    aspect_ratio: str = "16:9"

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "navigation": self.navigation.value,
            "features": [f.to_dict() for f in self.features],
            "css_class": self.css_class,
            "layout": self.layout,
            "show_speaker_notes": self.show_speaker_notes,
            "show_slide_numbers": self.show_slide_numbers,
            "show_progress_bar": self.show_progress_bar,
            "show_toc_sidebar": self.show_toc_sidebar,
            "enable_transitions": self.enable_transitions,
            "enable_fragments": self.enable_fragments,
            "enable_timer": self.enable_timer,
            "dark_mode": self.dark_mode,
            "auto_advance_ms": self.auto_advance_ms,
            "aspect_ratio": self.aspect_ratio,
        }


@dataclass
class SlideReadingContent:
    """Enriched slide content for reading mode."""
    slide_id: str = ""
    title: str = ""
    body_html: str = ""
    speaker_notes: str = ""
    expanded_details: str = ""
    annotations: list[str] = field(default_factory=list)
    toc_entry: str = ""
    section: str = ""
    word_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "slide_id": self.slide_id,
            "title": self.title,
            "body_html": self.body_html,
            "speaker_notes": self.speaker_notes,
            "expanded_details": self.expanded_details,
            "annotations": self.annotations,
            "toc_entry": self.toc_entry,
            "section": self.section,
            "word_count": self.word_count,
        }


# ═══════════════════════════════════════════════════════════════════
# PRODUCTION HARDENING MODELS
# ═══════════════════════════════════════════════════════════════════


class HealthStatus(str, Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceComponent(str, Enum):
    """Individual service components to monitor."""
    LLM_ROUTER = "llm_router"
    IMAGE_PIPELINE = "image_pipeline"
    RENDER_ENGINE = "render_engine"
    DATABASE = "database"
    REDIS_CACHE = "redis_cache"
    WEBSOCKET = "websocket"
    EXPORT_PIPELINE = "export_pipeline"
    STATE_SYNC = "state_sync"


@dataclass
class ComponentHealth:
    """Health status for a single component."""
    component: ServiceComponent
    status: HealthStatus = HealthStatus.UNKNOWN
    latency_ms: float = 0.0
    last_check: float = 0.0
    error_count: int = 0
    error_rate: float = 0.0       # errors per minute
    details: str = ""

    def __post_init__(self):
        if not self.last_check:
            self.last_check = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component.value,
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 2),
            "last_check": self.last_check,
            "error_count": self.error_count,
            "error_rate": round(self.error_rate, 4),
            "details": self.details,
        }


@dataclass
class LoadTestResult:
    """Result of a load test simulation."""
    id: str = ""
    concurrent_users: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    requests_per_second: float = 0.0
    error_types: dict[str, int] = field(default_factory=dict)
    duration_seconds: float = 0.0
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.id:
            self.id = f"lt_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100.0

    @property
    def passed(self) -> bool:
        return self.success_rate >= 95.0 and self.p95_latency_ms < 5000

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "concurrent_users": self.concurrent_users,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round(self.success_rate, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p50_latency_ms": round(self.p50_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "p99_latency_ms": round(self.p99_latency_ms, 2),
            "max_latency_ms": round(self.max_latency_ms, 2),
            "requests_per_second": round(self.requests_per_second, 2),
            "error_types": self.error_types,
            "duration_seconds": round(self.duration_seconds, 2),
            "passed": self.passed,
            "timestamp": self.timestamp,
        }


# ═══════════════════════════════════════════════════════════════════
# UNIFIED QUALITY REPORT
# ═══════════════════════════════════════════════════════════════════


class QualityDimension(str, Enum):
    """Dimensions of the unified quality assessment."""
    VISUAL_REGRESSION = "visual_regression"
    ACCESSIBILITY = "accessibility"
    ANTI_SLOP = "anti_slop"
    CONTENT_QUALITY = "content_quality"
    PERFORMANCE = "performance"
    PRODUCTION_READINESS = "production_readiness"


@dataclass
class DimensionScore:
    """Score for a single quality dimension."""
    dimension: QualityDimension
    score: float = 0.0          # 0-100
    weight: float = 1.0
    passed: bool = False
    details: dict[str, Any] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "score": round(self.score, 1),
            "weight": self.weight,
            "passed": self.passed,
            "details": self.details,
            "issues": self.issues,
        }


@dataclass
class UnifiedQualityReport:
    """Comprehensive quality report across all dimensions."""
    id: str = ""
    presentation_id: str = ""
    overall_score: float = 0.0       # Weighted average 0-100
    overall_grade: str = ""          # A+, A, B+, B, C, D, F
    passed: bool = False
    dimensions: list[DimensionScore] = field(default_factory=list)
    visual_regression: Optional[VisualRegressionResult] = None
    accessibility: Optional[AccessibilityReport] = None
    production_ready: bool = False
    total_issues: int = 0
    critical_issues: int = 0
    recommendations: list[str] = field(default_factory=list)
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.id:
            self.id = f"qr_{uuid.uuid4().hex[:10]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def compute_overall(self):
        """Compute overall score from dimension scores."""
        if not self.dimensions:
            self.overall_score = 0.0
            self.overall_grade = "F"
            self.passed = False
            return

        total_weight = sum(d.weight for d in self.dimensions)
        if total_weight == 0:
            self.overall_score = 0.0
        else:
            self.overall_score = sum(
                d.score * d.weight for d in self.dimensions
            ) / total_weight

        self.overall_grade = _score_to_grade(self.overall_score)
        self.total_issues = sum(len(d.issues) for d in self.dimensions)
        self.critical_issues = sum(
            1 for d in self.dimensions
            for issue in d.issues if "critical" in issue.lower()
        )
        self.passed = self.overall_score >= 70.0 and self.critical_issues == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "presentation_id": self.presentation_id,
            "overall_score": round(self.overall_score, 1),
            "overall_grade": self.overall_grade,
            "passed": self.passed,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "visual_regression": (
                self.visual_regression.to_dict() if self.visual_regression else None
            ),
            "accessibility": (
                self.accessibility.to_dict() if self.accessibility else None
            ),
            "production_ready": self.production_ready,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
        }


def _score_to_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 97:
        return "A+"
    elif score >= 93:
        return "A"
    elif score >= 90:
        return "A-"
    elif score >= 87:
        return "B+"
    elif score >= 83:
        return "B"
    elif score >= 80:
        return "B-"
    elif score >= 77:
        return "C+"
    elif score >= 73:
        return "C"
    elif score >= 70:
        return "C-"
    elif score >= 60:
        return "D"
    else:
        return "F"
