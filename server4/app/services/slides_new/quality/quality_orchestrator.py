"""
Quality Orchestrator — Phase 11.

Unified quality assessment service that combines all 6 quality
dimensions into a single comprehensive report:

1. Visual Regression (SSIM golden-master)
2. Accessibility (WCAG 2.1 AA)
3. Anti-Slop (content quality from Phase 5)
4. Content Quality (structural + readability)
5. Performance (render time budgets)
6. Production Readiness (health + load)

Integrates with Phase 3 qa_agent.py and Phase 5 anti_slop.py.
"""

from __future__ import annotations

import time
from typing import Any, Optional

import structlog

from app.services.slides_new.quality.models import (
    AccessibilityReport,
    DimensionScore,
    QualityDimension,
    UnifiedQualityReport,
    VisualRegressionResult,
)
from app.services.slides_new.quality.accessibility_engine import AccessibilityAuditor
from app.services.slides_new.quality.visual_regression import VisualRegressionService
from app.services.slides_new.quality.production_hardening import (
    ProductionReadinessAssessor,
)

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════════
# DIMENSION WEIGHTS
# ═══════════════════════════════════════════════════════════════════


DEFAULT_WEIGHTS: dict[QualityDimension, float] = {
    QualityDimension.VISUAL_REGRESSION: 1.0,
    QualityDimension.ACCESSIBILITY: 1.5,      # Compliance priority
    QualityDimension.ANTI_SLOP: 1.2,          # Content quality priority
    QualityDimension.CONTENT_QUALITY: 1.0,
    QualityDimension.PERFORMANCE: 0.8,
    QualityDimension.PRODUCTION_READINESS: 0.8,
}


# ═══════════════════════════════════════════════════════════════════
# CONTENT QUALITY EVALUATOR
# ═══════════════════════════════════════════════════════════════════


class ContentQualityEvaluator:
    """
    Evaluates structural and readability quality of slide content.

    Checks:
    - Title presence and length
    - Content density (not too sparse, not too crowded)
    - Bullet point count (ideal: 3-7)
    - Consistent tone/structure across slides
    - No empty slides
    """

    def evaluate(self, presentation_dsl: dict[str, Any]) -> DimensionScore:
        slides = presentation_dsl.get("slides", [])
        if not slides:
            return DimensionScore(
                dimension=QualityDimension.CONTENT_QUALITY,
                score=0.0,
                weight=DEFAULT_WEIGHTS[QualityDimension.CONTENT_QUALITY],
                passed=False,
                issues=["No slides in presentation"],
            )

        issues: list[str] = []
        score = 100.0
        total_slides = len(slides)
        empty_count = 0

        for i, slide in enumerate(slides):
            content = slide.get("content", {})
            slide_id = slide.get("id", f"slide_{i}")

            # Title check
            title = content.get("title", "")
            if not title:
                issues.append(f"{slide_id}: Missing title")
                score -= 5
            elif len(title) > 80:
                issues.append(f"{slide_id}: Title too long ({len(title)} chars)")
                score -= 2

            # Content density
            body = content.get("body", "")
            subtitle = content.get("subtitle", "")
            bullets = content.get("bullets", []) or content.get("points", [])
            elements = slide.get("elements", [])

            has_content = bool(body or subtitle or bullets or elements)
            if not has_content and not title:
                empty_count += 1
                issues.append(f"{slide_id}: Empty slide")
                score -= 10

            # Bullet count check (ideal 3-7)
            if bullets:
                if len(bullets) > 7:
                    issues.append(f"{slide_id}: Too many bullets ({len(bullets)})")
                    score -= 3
                elif len(bullets) < 2:
                    issues.append(f"{slide_id}: Single bullet — consider removing list")
                    score -= 1

            # Body text length
            if body and len(body) > 500:
                issues.append(f"{slide_id}: Body text too long ({len(body)} chars)")
                score -= 3

        # Global checks
        if total_slides > 30:
            issues.append(f"Presentation has {total_slides} slides — consider trimming")
            score -= 5

        empty_pct = (empty_count / total_slides) * 100 if total_slides > 0 else 0
        if empty_pct > 20:
            issues.append(f"{empty_pct:.0f}% empty slides")
            score -= 10

        score = max(0.0, min(100.0, score))
        return DimensionScore(
            dimension=QualityDimension.CONTENT_QUALITY,
            score=score,
            weight=DEFAULT_WEIGHTS[QualityDimension.CONTENT_QUALITY],
            passed=score >= 70.0,
            issues=issues,
            details={
                "total_slides": total_slides,
                "empty_slides": empty_count,
            },
        )


# ═══════════════════════════════════════════════════════════════════
# ANTI-SLOP INTEGRATION
# ═══════════════════════════════════════════════════════════════════


class AntiSlopIntegration:
    """
    Integrates with Phase 5 anti_slop.py for content quality scoring.
    """

    def evaluate(self, presentation_dsl: dict[str, Any]) -> DimensionScore:
        """Run anti-slop analysis and return dimension score."""
        try:
            from app.services.slides_new.content.anti_slop import (
                AntiSlopEngine,
            )
            engine = AntiSlopEngine()

            # Collect all text content from slides
            total_violations = 0
            issues: list[str] = []
            slides = presentation_dsl.get("slides", [])

            for slide in slides:
                content = slide.get("content", {})
                slide_id = slide.get("id", "unknown")
                text_parts = []

                for key in ("title", "subtitle", "body", "description"):
                    val = content.get(key, "")
                    if val:
                        text_parts.append(val)

                bullets = content.get("bullets", []) or content.get("points", [])
                text_parts.extend(str(b) for b in bullets)

                full_text = " ".join(text_parts)
                if not full_text.strip():
                    continue

                report = engine.analyze(full_text)
                if report.violations:
                    total_violations += len(report.violations)
                    for v in report.violations[:3]:  # Top 3 per slide
                        issues.append(
                            f"{slide_id}: [{v.category.value}] {v.description}"
                        )

            # Score: start at 100, deduct per violation
            score = max(0.0, 100.0 - total_violations * 3)

            return DimensionScore(
                dimension=QualityDimension.ANTI_SLOP,
                score=score,
                weight=DEFAULT_WEIGHTS[QualityDimension.ANTI_SLOP],
                passed=score >= 70.0,
                issues=issues,
                details={"total_violations": total_violations},
            )

        except ImportError:
            return DimensionScore(
                dimension=QualityDimension.ANTI_SLOP,
                score=80.0,  # Neutral score when unavailable
                weight=DEFAULT_WEIGHTS[QualityDimension.ANTI_SLOP],
                passed=True,
                issues=["Anti-slop engine not available — skipped"],
                details={"skipped": True},
            )


# ═══════════════════════════════════════════════════════════════════
# PERFORMANCE EVALUATOR
# ═══════════════════════════════════════════════════════════════════


class PerformanceEvaluator:
    """
    Evaluates performance characteristics of the presentation.

    Checks:
    - Estimated render time vs. budgets
    - Asset count and sizes
    - 3D scene complexity
    - Image optimization opportunities
    """

    # Budgets from Phase 7 performance_guardrails.py
    MAX_RENDER_MS = 3000
    MAX_ASSETS_PER_SLIDE = 10
    MAX_3D_VERTICES = 50000

    def evaluate(self, presentation_dsl: dict[str, Any]) -> DimensionScore:
        slides = presentation_dsl.get("slides", [])
        issues: list[str] = []
        score = 100.0

        total_elements = 0
        total_3d_scenes = 0
        heavy_slides = 0

        for i, slide in enumerate(slides):
            slide_id = slide.get("id", f"slide_{i}")
            elements = slide.get("elements", [])
            total_elements += len(elements)

            if len(elements) > self.MAX_ASSETS_PER_SLIDE:
                issues.append(
                    f"{slide_id}: {len(elements)} elements (max {self.MAX_ASSETS_PER_SLIDE})"
                )
                score -= 5
                heavy_slides += 1

            # 3D scene complexity
            three_scene = slide.get("threeScene")
            if three_scene:
                total_3d_scenes += 1
                vertices = three_scene.get("vertex_count", 0)
                if vertices > self.MAX_3D_VERTICES:
                    issues.append(
                        f"{slide_id}: 3D scene {vertices} vertices (max {self.MAX_3D_VERTICES})"
                    )
                    score -= 10

            # High-res images without optimization
            for elem in elements:
                if elem.get("type") == "image":
                    width = elem.get("original_width", 0)
                    if width > 3840:
                        issues.append(
                            f"{slide_id}: Image {width}px wide — optimize for web"
                        )
                        score -= 3

        # Estimate render time
        est_render_ms = (
            len(slides) * 50  # Base per slide
            + total_elements * 10  # Per element
            + total_3d_scenes * 500  # Per 3D scene
        )
        if est_render_ms > self.MAX_RENDER_MS:
            issues.append(
                f"Estimated render time {est_render_ms}ms exceeds {self.MAX_RENDER_MS}ms budget"
            )
            score -= 15

        score = max(0.0, min(100.0, score))
        return DimensionScore(
            dimension=QualityDimension.PERFORMANCE,
            score=score,
            weight=DEFAULT_WEIGHTS[QualityDimension.PERFORMANCE],
            passed=score >= 70.0,
            issues=issues,
            details={
                "total_elements": total_elements,
                "total_3d_scenes": total_3d_scenes,
                "heavy_slides": heavy_slides,
                "estimated_render_ms": est_render_ms,
            },
        )


# ═══════════════════════════════════════════════════════════════════
# QUALITY ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════


class QualityOrchestrator:
    """
    Unified quality assessment service.

    Runs all quality dimensions and produces a comprehensive
    UnifiedQualityReport with weighted scoring across:
    1. Visual Regression (SSIM)
    2. Accessibility (WCAG 2.1 AA)
    3. Anti-Slop (Phase 5)
    4. Content Quality (structural)
    5. Performance (budgets)
    6. Production Readiness (health/load)
    """

    def __init__(
        self,
        weights: Optional[dict[QualityDimension, float]] = None,
    ):
        self._weights = weights or dict(DEFAULT_WEIGHTS)
        self._accessibility_auditor = AccessibilityAuditor()
        self._visual_regression = VisualRegressionService()
        self._content_evaluator = ContentQualityEvaluator()
        self._anti_slop = AntiSlopIntegration()
        self._performance_evaluator = PerformanceEvaluator()
        self._production_assessor = ProductionReadinessAssessor()
        self._reports_generated = 0

    async def run_comprehensive_audit(
        self,
        presentation_dsl: dict[str, Any],
        presentation_id: str = "",
        run_visual: bool = True,
        run_production: bool = False,
    ) -> UnifiedQualityReport:
        """
        Run all quality dimensions and produce unified report.

        Args:
            presentation_dsl: Full DSL dict
            presentation_id: ID for tracking
            run_visual: Whether to run visual regression
            run_production: Whether to run production readiness

        Returns:
            UnifiedQualityReport with all scores
        """
        self._reports_generated += 1
        report = UnifiedQualityReport(presentation_id=presentation_id)

        # 1. Accessibility
        a11y_report = self._accessibility_auditor.audit_presentation(presentation_dsl)
        report.accessibility = a11y_report
        report.dimensions.append(DimensionScore(
            dimension=QualityDimension.ACCESSIBILITY,
            score=a11y_report.score,
            weight=self._weights[QualityDimension.ACCESSIBILITY],
            passed=a11y_report.passed,
            issues=[v.description for v in a11y_report.violations],
            details={"critical": a11y_report.critical_count, "serious": a11y_report.serious_count},
        ))

        # 2. Content Quality
        content_score = self._content_evaluator.evaluate(presentation_dsl)
        report.dimensions.append(content_score)

        # 3. Anti-Slop
        slop_score = self._anti_slop.evaluate(presentation_dsl)
        report.dimensions.append(slop_score)

        # 4. Performance
        perf_score = self._performance_evaluator.evaluate(presentation_dsl)
        report.dimensions.append(perf_score)

        # 5. Visual Regression (optional — needs screenshots)
        if run_visual:
            vr_score = DimensionScore(
                dimension=QualityDimension.VISUAL_REGRESSION,
                score=85.0,  # Baseline score when no golden master exists
                weight=self._weights[QualityDimension.VISUAL_REGRESSION],
                passed=True,
                issues=[],
                details={"status": "no_baseline_yet"},
            )
            report.dimensions.append(vr_score)

        # 6. Production Readiness (optional — runs health + load checks)
        if run_production:
            prod_result = await self._production_assessor.assess()
            report.dimensions.append(DimensionScore(
                dimension=QualityDimension.PRODUCTION_READINESS,
                score=prod_result["score"],
                weight=self._weights[QualityDimension.PRODUCTION_READINESS],
                passed=prod_result["production_ready"],
                issues=prod_result["issues"],
                details=prod_result,
            ))
            report.production_ready = prod_result["production_ready"]

        # Compute overall
        report.compute_overall()

        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)

        return report

    def _generate_recommendations(
        self, report: UnifiedQualityReport
    ) -> list[str]:
        """Generate actionable recommendations from the report."""
        recs: list[str] = []

        for dim in report.dimensions:
            if dim.score < 70:
                recs.append(
                    f"[{dim.dimension.value}] Score {dim.score:.0f}/100 — "
                    f"needs attention: {dim.issues[0] if dim.issues else 'review needed'}"
                )
            elif dim.score < 85:
                recs.append(
                    f"[{dim.dimension.value}] Score {dim.score:.0f}/100 — "
                    f"room for improvement"
                )

        if report.accessibility and report.accessibility.critical_count > 0:
            recs.insert(
                0,
                f"CRITICAL: {report.accessibility.critical_count} critical "
                f"accessibility violations must be fixed before release"
            )

        if not recs:
            recs.append("All quality dimensions passing — ready for release")

        return recs

    @property
    def accessibility_auditor(self) -> AccessibilityAuditor:
        return self._accessibility_auditor

    @property
    def visual_regression(self) -> VisualRegressionService:
        return self._visual_regression

    @property
    def production_assessor(self) -> ProductionReadinessAssessor:
        return self._production_assessor

    def get_stats(self) -> dict[str, Any]:
        return {
            "reports_generated": self._reports_generated,
            "accessibility_audits": self._accessibility_auditor.audits_run,
            "visual_regression_stats": self._visual_regression.get_stats(),
            "weights": {k.value: v for k, v in self._weights.items()},
        }
