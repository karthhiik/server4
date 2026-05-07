"""
Performance Guardrails — Phase 6.

Enforces rendering budgets for Three.js 3D scenes to guarantee
smooth presentation playback. Provides:

- Scene complexity budget (polygons, particles, textures, memory)
- Adaptive quality system (high → medium → low → 2D fallback)
- Lazy-loading directives for Three.js chunks
- Per-slide and per-presentation budget accounting
- WebGL capability detection hints
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ═══════════════════════════════════════════════════════════════════
# QUALITY TIERS
# ═══════════════════════════════════════════════════════════════════


class QualityLevel(str, Enum):
    """Rendering quality tiers with automatic downgrade."""
    HIGH = "high"       # Full 3D, particles, reflections
    MEDIUM = "medium"   # Reduced particles, simplified geometry
    LOW = "low"         # Minimal 3D, flat textures, no post-processing
    FALLBACK_2D = "2d"  # Pure CSS/SVG fallback, no WebGL


class DeviceClass(str, Enum):
    """Target device classification for performance tuning."""
    DESKTOP_HIGH = "desktop_high"     # Dedicated GPU, 16GB+ RAM
    DESKTOP_LOW = "desktop_low"       # Integrated GPU, 8GB RAM
    MOBILE = "mobile"                 # Phone/tablet
    EMBEDDED = "embedded"             # Kiosk, low-power device


# ═══════════════════════════════════════════════════════════════════
# BUDGET CONSTANTS
# ═══════════════════════════════════════════════════════════════════


# Per-slide scene limits by quality level
QUALITY_BUDGETS: dict[QualityLevel, dict[str, int | float]] = {
    QualityLevel.HIGH: {
        "max_polygons": 50_000,
        "max_particles": 10_000,
        "max_textures": 8,
        "max_texture_resolution": 2048,
        "max_draw_calls": 100,
        "memory_budget_mb": 50,
        "target_fps": 60,
        "max_lights": 8,
        "max_animations": 20,
        "shadow_map_size": 2048,
    },
    QualityLevel.MEDIUM: {
        "max_polygons": 20_000,
        "max_particles": 3_000,
        "max_textures": 4,
        "max_texture_resolution": 1024,
        "max_draw_calls": 50,
        "memory_budget_mb": 30,
        "target_fps": 30,
        "max_lights": 4,
        "max_animations": 10,
        "shadow_map_size": 1024,
    },
    QualityLevel.LOW: {
        "max_polygons": 5_000,
        "max_particles": 500,
        "max_textures": 2,
        "max_texture_resolution": 512,
        "max_draw_calls": 20,
        "memory_budget_mb": 15,
        "target_fps": 30,
        "max_lights": 2,
        "max_animations": 5,
        "shadow_map_size": 0,     # No shadows
    },
    QualityLevel.FALLBACK_2D: {
        "max_polygons": 0,
        "max_particles": 0,
        "max_textures": 0,
        "max_texture_resolution": 0,
        "max_draw_calls": 0,
        "memory_budget_mb": 5,
        "target_fps": 60,
        "max_lights": 0,
        "max_animations": 3,
        "shadow_map_size": 0,
    },
}

# Presentation-wide limits
PRESENTATION_BUDGET = {
    "max_3d_slides": 6,            # Max slides with 3D scenes
    "total_memory_mb": 150,        # Total 3D memory across all slides
    "total_polygons": 200_000,     # Combined scene complexity
    "max_concurrent_scenes": 2,    # Preloaded scenes (current + next)
    "threejs_chunk_size_kb": 450,  # Base Three.js bundle size
}

# Scene complexity estimates (polygon counts per scene type)
SCENE_COMPLEXITY: dict[str, dict[str, int]] = {
    "globe": {
        "polygons": 15_000,
        "particles": 500,
        "textures": 2,
        "draw_calls": 15,
        "estimated_memory_mb": 12,
    },
    "bar-chart": {
        "polygons": 3_000,
        "particles": 0,
        "textures": 1,
        "draw_calls": 30,
        "estimated_memory_mb": 5,
    },
    "particles": {
        "polygons": 100,
        "particles": 5_000,
        "textures": 1,
        "draw_calls": 5,
        "estimated_memory_mb": 8,
    },
    "scatter": {
        "polygons": 5_000,
        "particles": 200,
        "textures": 1,
        "draw_calls": 25,
        "estimated_memory_mb": 6,
    },
    "floating-cards": {
        "polygons": 2_000,
        "particles": 0,
        "textures": 6,
        "draw_calls": 20,
        "estimated_memory_mb": 10,
    },
    "data-flow": {
        "polygons": 4_000,
        "particles": 1_000,
        "textures": 2,
        "draw_calls": 35,
        "estimated_memory_mb": 8,
    },
    "custom": {
        "polygons": 10_000,
        "particles": 1_000,
        "textures": 4,
        "draw_calls": 40,
        "estimated_memory_mb": 15,
    },
}


# ═══════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════


@dataclass
class BudgetViolation:
    """A single budget limit violation."""
    metric: str
    limit: int | float
    actual: int | float
    severity: str           # "warning" | "error"
    recommendation: str


@dataclass
class SceneBudgetReport:
    """Budget analysis for a single 3D scene."""
    scene_type: str
    quality_level: QualityLevel
    polygons: int = 0
    particles: int = 0
    textures: int = 0
    draw_calls: int = 0
    estimated_memory_mb: float = 0.0
    violations: list[BudgetViolation] = field(default_factory=list)
    passed: bool = True
    downgraded_from: Optional[QualityLevel] = None
    lazy_load: bool = True
    fallback_2d: bool = False

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "error")


@dataclass
class PresentationBudgetReport:
    """Budget analysis for an entire presentation's 3D content."""
    total_3d_slides: int = 0
    total_polygons: int = 0
    total_memory_mb: float = 0.0
    scene_reports: list[SceneBudgetReport] = field(default_factory=list)
    violations: list[BudgetViolation] = field(default_factory=list)
    passed: bool = True
    recommended_quality: QualityLevel = QualityLevel.HIGH
    lazy_load_plan: dict[int, bool] = field(default_factory=dict)

    @property
    def total_violations(self) -> int:
        total = len(self.violations)
        for sr in self.scene_reports:
            total += sr.violation_count
        return total


@dataclass
class LazyLoadDirective:
    """Instructions for lazy-loading a 3D slide."""
    slide_index: int
    scene_type: str
    preload: bool           # Whether to preload when adjacent slide is visible
    placeholder: str        # "skeleton" | "static_image" | "gradient"
    estimated_load_ms: int  # Estimated load time in ms
    priority: int           # 1 = current slide, 2 = adjacent, 3 = distant


# ═══════════════════════════════════════════════════════════════════
# PERFORMANCE GUARDRAILS ENGINE
# ═══════════════════════════════════════════════════════════════════


class PerformanceGuardrails:
    """
    Enforces Three.js rendering budgets and generates adaptive quality
    directives, lazy-loading plans, and 2D fallback strategies.

    Usage:
        guardrails = PerformanceGuardrails()
        report = guardrails.analyze_scene("globe", quality=QualityLevel.HIGH)
        pres_report = guardrails.analyze_presentation(scenes)
        directives = guardrails.generate_lazy_load_plan(scenes, current_slide=0)
    """

    def __init__(self, device_class: DeviceClass = DeviceClass.DESKTOP_HIGH):
        self._device = device_class
        self._initial_quality = self._device_quality(device_class)

    @staticmethod
    def _device_quality(device: DeviceClass) -> QualityLevel:
        """Map device class to initial quality level."""
        return {
            DeviceClass.DESKTOP_HIGH: QualityLevel.HIGH,
            DeviceClass.DESKTOP_LOW: QualityLevel.MEDIUM,
            DeviceClass.MOBILE: QualityLevel.LOW,
            DeviceClass.EMBEDDED: QualityLevel.FALLBACK_2D,
        }.get(device, QualityLevel.MEDIUM)

    # ── Scene Analysis ────────────────────────────────────────

    def analyze_scene(
        self,
        scene_type: str,
        quality: Optional[QualityLevel] = None,
        custom_complexity: Optional[dict[str, int]] = None,
    ) -> SceneBudgetReport:
        """
        Analyze a single 3D scene against the budget for a given quality level.
        Auto-downgrades quality if the scene exceeds the budget.

        Args:
            scene_type: One of SCENE_COMPLEXITY keys (globe, particles, etc.)
            quality: Desired quality level; defaults to device-appropriate level
            custom_complexity: Override complexity estimates

        Returns:
            SceneBudgetReport with violations, final quality, and directives
        """
        if quality is None:
            quality = self._initial_quality

        complexity = dict(custom_complexity or SCENE_COMPLEXITY.get(scene_type, SCENE_COMPLEXITY["custom"]))
        original_quality = quality

        # Try current quality; downgrade if violations are critical
        for attempt_quality in _quality_ladder(quality):
            budget = QUALITY_BUDGETS[attempt_quality]
            violations = self._check_budget(complexity, budget, attempt_quality)

            errors = [v for v in violations if v.severity == "error"]
            if not errors:
                # This quality level works
                return SceneBudgetReport(
                    scene_type=scene_type,
                    quality_level=attempt_quality,
                    polygons=complexity.get("polygons", 0),
                    particles=complexity.get("particles", 0),
                    textures=complexity.get("textures", 0),
                    draw_calls=complexity.get("draw_calls", 0),
                    estimated_memory_mb=complexity.get("estimated_memory_mb", 0.0),
                    violations=violations,  # may have warnings
                    passed=True,
                    downgraded_from=original_quality if attempt_quality != original_quality else None,
                    lazy_load=True,
                    fallback_2d=(attempt_quality == QualityLevel.FALLBACK_2D),
                )

        # All quality levels failed — force 2D fallback
        return SceneBudgetReport(
            scene_type=scene_type,
            quality_level=QualityLevel.FALLBACK_2D,
            polygons=complexity.get("polygons", 0),
            particles=complexity.get("particles", 0),
            textures=complexity.get("textures", 0),
            draw_calls=complexity.get("draw_calls", 0),
            estimated_memory_mb=complexity.get("estimated_memory_mb", 0.0),
            violations=violations,
            passed=False,
            downgraded_from=original_quality,
            lazy_load=False,
            fallback_2d=True,
        )

    def analyze_presentation(
        self,
        scenes: list[dict[str, Any]],
    ) -> PresentationBudgetReport:
        """
        Analyze all 3D scenes in a presentation against the global budget.

        Args:
            scenes: List of dicts with "slide_index" and "scene_type" keys,
                    and optionally "custom_complexity".

        Returns:
            PresentationBudgetReport with per-scene reports and global violations.
        """
        report = PresentationBudgetReport()
        report.total_3d_slides = len(scenes)
        report.recommended_quality = self._initial_quality

        # Check slide count limit
        if len(scenes) > PRESENTATION_BUDGET["max_3d_slides"]:
            report.violations.append(BudgetViolation(
                metric="3d_slide_count",
                limit=PRESENTATION_BUDGET["max_3d_slides"],
                actual=len(scenes),
                severity="warning",
                recommendation=(
                    f"Presentation has {len(scenes)} 3D slides; "
                    f"recommended max is {PRESENTATION_BUDGET['max_3d_slides']}. "
                    "Consider converting some to 2D for better performance."
                ),
            ))

        total_poly = 0
        total_mem = 0.0

        for scene_info in scenes:
            slide_idx = scene_info.get("slide_index", 0)
            scene_type = scene_info.get("scene_type", "custom")
            custom = scene_info.get("custom_complexity")

            scene_report = self.analyze_scene(scene_type, custom_complexity=custom)
            report.scene_reports.append(scene_report)
            report.lazy_load_plan[slide_idx] = scene_report.lazy_load

            total_poly += scene_report.polygons
            total_mem += scene_report.estimated_memory_mb

            # Track any scene-level downgrade
            if scene_report.downgraded_from is not None:
                # Use the worst quality seen as the recommendation
                if _quality_rank(scene_report.quality_level) > _quality_rank(report.recommended_quality):
                    report.recommended_quality = scene_report.quality_level

        report.total_polygons = total_poly
        report.total_memory_mb = total_mem

        # Presentation-wide polygon check
        if total_poly > PRESENTATION_BUDGET["total_polygons"]:
            report.violations.append(BudgetViolation(
                metric="total_polygons",
                limit=PRESENTATION_BUDGET["total_polygons"],
                actual=total_poly,
                severity="warning",
                recommendation=(
                    "Total polygon count exceeds budget. "
                    "Reduce complexity on some 3D slides or switch to 2D fallbacks."
                ),
            ))

        # Presentation-wide memory check
        if total_mem > PRESENTATION_BUDGET["total_memory_mb"]:
            report.violations.append(BudgetViolation(
                metric="total_memory_mb",
                limit=PRESENTATION_BUDGET["total_memory_mb"],
                actual=total_mem,
                severity="error",
                recommendation=(
                    f"Total 3D memory ({total_mem:.0f}MB) exceeds "
                    f"{PRESENTATION_BUDGET['total_memory_mb']}MB budget. "
                    "Reduce texture resolution or scene count."
                ),
            ))
            report.passed = False

        # Check if any scene report failed
        if any(not sr.passed for sr in report.scene_reports):
            report.passed = False

        return report

    # ── Lazy Loading ──────────────────────────────────────────

    def generate_lazy_load_plan(
        self,
        scenes: list[dict[str, Any]],
        current_slide: int = 0,
        total_slides: int = 10,
    ) -> list[LazyLoadDirective]:
        """
        Generate a lazy-loading plan for all 3D slides in the presentation.

        Slides adjacent to the current slide are preloaded; distant slides
        are loaded on-demand.

        Args:
            scenes: List of dicts with "slide_index" and "scene_type"
            current_slide: Currently visible slide index
            total_slides: Total number of slides

        Returns:
            List of LazyLoadDirective for each 3D slide
        """
        directives: list[LazyLoadDirective] = []

        for scene_info in scenes:
            slide_idx = scene_info.get("slide_index", 0)
            scene_type = scene_info.get("scene_type", "custom")
            distance = abs(slide_idx - current_slide)

            if distance == 0:
                priority = 1
                preload = True
                placeholder = "skeleton"
            elif distance <= 1:
                priority = 2
                preload = True
                placeholder = "skeleton"
            elif distance <= 3:
                priority = 3
                preload = False
                placeholder = "gradient"
            else:
                priority = 4
                preload = False
                placeholder = "static_image"

            # Estimate load time based on scene complexity
            complexity = SCENE_COMPLEXITY.get(scene_type, SCENE_COMPLEXITY["custom"])
            base_load_ms = 200  # Base Three.js init
            mem_factor = int(complexity.get("estimated_memory_mb", 10) * 15)
            estimated_load_ms = base_load_ms + mem_factor

            directives.append(LazyLoadDirective(
                slide_index=slide_idx,
                scene_type=scene_type,
                preload=preload,
                placeholder=placeholder,
                estimated_load_ms=estimated_load_ms,
                priority=priority,
            ))

        # Sort by priority (load current slide first)
        directives.sort(key=lambda d: d.priority)
        return directives

    # ── Adaptive Quality ──────────────────────────────────────

    @staticmethod
    def adaptive_quality(current_fps: float) -> QualityLevel:
        """
        Determine quality level based on current framerate.
        Called at runtime by the frontend; included here for
        contract definition and testing.

        Args:
            current_fps: Measured frames per second

        Returns:
            Recommended QualityLevel
        """
        if current_fps >= 55:
            return QualityLevel.HIGH
        if current_fps >= 40:
            return QualityLevel.MEDIUM
        if current_fps >= 20:
            return QualityLevel.LOW
        return QualityLevel.FALLBACK_2D

    @staticmethod
    def get_quality_config(quality: QualityLevel) -> dict[str, Any]:
        """
        Return the full budget configuration for a quality level.
        Useful for the frontend to configure the Three.js renderer.
        """
        return dict(QUALITY_BUDGETS.get(quality, QUALITY_BUDGETS[QualityLevel.MEDIUM]))

    @staticmethod
    def get_scene_complexity(scene_type: str) -> dict[str, int]:
        """Return estimated complexity for a scene type."""
        return dict(SCENE_COMPLEXITY.get(scene_type, SCENE_COMPLEXITY["custom"]))

    # ── Private Helpers ───────────────────────────────────────

    @staticmethod
    def _check_budget(
        complexity: dict[str, int | float],
        budget: dict[str, int | float],
        quality: QualityLevel,
    ) -> list[BudgetViolation]:
        """Check complexity against a budget, returning violations."""
        violations: list[BudgetViolation] = []

        checks = [
            ("polygons", "max_polygons", "Reduce geometry detail or scene type"),
            ("particles", "max_particles", "Reduce particle count for this quality"),
            ("textures", "max_textures", "Reduce number of textures"),
            ("draw_calls", "max_draw_calls", "Merge geometries to reduce draw calls"),
            ("estimated_memory_mb", "memory_budget_mb", "Reduce texture resolution or geometry count"),
        ]

        for metric_key, budget_key, recommendation in checks:
            actual = complexity.get(metric_key, 0)
            limit = budget.get(budget_key, 0)
            if limit > 0 and actual > limit:
                # Memory overshoot > 50% is error; else warning
                overshoot = (actual - limit) / limit if limit > 0 else 1.0
                severity = "error" if overshoot > 0.5 else "warning"
                violations.append(BudgetViolation(
                    metric=metric_key,
                    limit=limit,
                    actual=actual,
                    severity=severity,
                    recommendation=f"{recommendation} (at {quality.value} quality)",
                ))

        return violations


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════


def _quality_ladder(start: QualityLevel) -> list[QualityLevel]:
    """Return quality levels to try, starting from `start` and descending."""
    order = [QualityLevel.HIGH, QualityLevel.MEDIUM, QualityLevel.LOW, QualityLevel.FALLBACK_2D]
    start_idx = order.index(start) if start in order else 0
    return order[start_idx:]


def _quality_rank(q: QualityLevel) -> int:
    """Lower quality = higher rank number (worse)."""
    return {
        QualityLevel.HIGH: 0,
        QualityLevel.MEDIUM: 1,
        QualityLevel.LOW: 2,
        QualityLevel.FALLBACK_2D: 3,
    }.get(q, 1)
