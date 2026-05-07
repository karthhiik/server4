"""
Quality Module — Phase 11: QA + Polish + Delivery.

Provides:
- Visual regression testing (SSIM golden-master)
- Accessibility auditing (WCAG 2.1 AA)
- Presentation mode management (Reading/Presentation/Speaker/Overview/Print)
- Production hardening (health checks, load tests, error budget)
- Unified quality orchestration across all dimensions
"""

from app.services.slides_new.quality.models import (
    # Visual Regression
    RegressionStatus,
    DiffRegion,
    PixelStats,
    SSIMResult,
    DiffMapEntry,
    GoldenMaster,
    VisualRegressionResult,
    # Accessibility
    WCAGLevel,
    A11ySeverity,
    A11yCategory,
    ContrastCheck,
    A11yViolation,
    AccessibilityReport,
    # Presentation Modes
    PresentationMode,
    NavigationType,
    ModeFeature,
    ModeConfig,
    SlideReadingContent,
    # Production Hardening
    HealthStatus,
    ServiceComponent,
    ComponentHealth,
    LoadTestResult,
    # Unified Quality
    QualityDimension,
    DimensionScore,
    UnifiedQualityReport,
)

from app.services.slides_new.quality.visual_regression import (
    SSIMEngine,
    DiffMapGenerator,
    GoldenMasterStore,
    VisualRegressionService,
    ScreenshotCapture,
)

from app.services.slides_new.quality.accessibility_engine import (
    AccessibilityAuditor,
    contrast_ratio,
    passes_wcag_aa,
    passes_wcag_aaa,
    relative_luminance,
    suggest_contrast_fix,
    hex_to_rgb,
)

from app.services.slides_new.quality.presentation_modes import (
    PresentationModeManager,
    PresentationModeAdapter,
    ReadingModeTransformer,
    get_mode_config,
    get_all_modes,
    check_mode_compatibility,
    get_supported_modes,
)

from app.services.slides_new.quality.production_hardening import (
    HealthCheckEngine,
    LoadTestSimulator,
    ErrorBudgetTracker,
    ProductionReadinessAssessor,
)

from app.services.slides_new.quality.quality_orchestrator import (
    QualityOrchestrator,
    ContentQualityEvaluator,
    AntiSlopIntegration,
    PerformanceEvaluator,
    DEFAULT_WEIGHTS,
)

__all__ = [
    # Models
    "RegressionStatus", "DiffRegion", "PixelStats", "SSIMResult",
    "DiffMapEntry", "GoldenMaster", "VisualRegressionResult",
    "WCAGLevel", "A11ySeverity", "A11yCategory", "ContrastCheck",
    "A11yViolation", "AccessibilityReport",
    "PresentationMode", "NavigationType", "ModeFeature", "ModeConfig",
    "SlideReadingContent",
    "HealthStatus", "ServiceComponent", "ComponentHealth", "LoadTestResult",
    "QualityDimension", "DimensionScore", "UnifiedQualityReport",
    # Visual Regression
    "SSIMEngine", "DiffMapGenerator", "GoldenMasterStore",
    "VisualRegressionService", "ScreenshotCapture",
    # Accessibility
    "AccessibilityAuditor", "contrast_ratio", "passes_wcag_aa",
    "passes_wcag_aaa", "relative_luminance", "suggest_contrast_fix", "hex_to_rgb",
    # Presentation Modes
    "PresentationModeManager", "PresentationModeAdapter",
    "ReadingModeTransformer", "get_mode_config", "get_all_modes",
    "check_mode_compatibility", "get_supported_modes",
    # Production Hardening
    "HealthCheckEngine", "LoadTestSimulator", "ErrorBudgetTracker",
    "ProductionReadinessAssessor",
    # Quality Orchestrator
    "QualityOrchestrator", "ContentQualityEvaluator",
    "AntiSlopIntegration", "PerformanceEvaluator", "DEFAULT_WEIGHTS",
]
