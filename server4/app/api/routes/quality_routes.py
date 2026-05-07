"""
Phase 11 — Quality API Routes.

REST endpoints for the QA + Polish + Delivery system:
- POST /audit/accessibility — WCAG 2.1 AA audit
- POST /audit/visual-regression — SSIM golden-master comparison
- POST /audit/comprehensive — Full multi-dimension quality report
- GET  /health/components — Deep health check of all 8 components
- POST /load-test — Run simulated load test
- GET  /modes — List all presentation modes
- GET  /modes/{renderer} — Get supported modes for a renderer
- POST /modes/reading — Transform DSL to reading mode
- POST /modes/adapt — Adapt rendered output for a target mode
- GET  /stats — Quality system statistics
- GET  /error-budget — Current error budget status
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.slides_new.quality.models import (
    PresentationMode,
    QualityDimension,
    WCAGLevel,
)
from app.services.slides_new.quality.accessibility_engine import (
    AccessibilityAuditor,
    contrast_ratio,
    passes_wcag_aa,
)
from app.services.slides_new.quality.visual_regression import (
    VisualRegressionService,
)
from app.services.slides_new.quality.presentation_modes import (
    PresentationModeManager,
    check_mode_compatibility,
    get_all_modes,
    get_mode_config,
)
from app.services.slides_new.quality.production_hardening import (
    HealthCheckEngine,
    LoadTestSimulator,
    ErrorBudgetTracker,
    ProductionReadinessAssessor,
)
from app.services.slides_new.quality.quality_orchestrator import (
    QualityOrchestrator,
)
from app.services.slides_new.renderers.base_renderer import RendererType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/quality", tags=["quality-v2"])


# ═══════════════════════════════════════════════════════════════════
# SINGLETONS
# ═══════════════════════════════════════════════════════════════════

_auditor = AccessibilityAuditor()
_vr_service = VisualRegressionService()
_mode_manager = PresentationModeManager()
_health_engine = HealthCheckEngine()
_load_tester = LoadTestSimulator()
_error_tracker = ErrorBudgetTracker()
_orchestrator = QualityOrchestrator()


# ═══════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════


class AuditRequest(BaseModel):
    presentation_dsl: Dict[str, Any] = Field(..., description="Full presentation DSL dict")
    wcag_level: str = Field(default="AA", description="Target WCAG level: A, AA, or AAA")


class VisualRegressionRequest(BaseModel):
    presentation_id: str = Field(..., description="Presentation ID")
    slide_id: str = Field(..., description="Slide ID")
    renderer: str = Field(default="reveal.js", description="Renderer type")
    image_data: List[int] = Field(default_factory=list, description="Flat RGB pixel list")
    width: int = Field(default=1920, description="Image width")
    height: int = Field(default=1080, description="Image height")
    update_baseline: bool = Field(default=False, description="Force update golden master")


class ComprehensiveAuditRequest(BaseModel):
    presentation_dsl: Dict[str, Any] = Field(...)
    presentation_id: str = Field(default="")
    run_visual: bool = Field(default=False)
    run_production: bool = Field(default=False)


class ContrastCheckRequest(BaseModel):
    foreground: str = Field(..., description="Foreground hex color")
    background: str = Field(..., description="Background hex color")
    is_large_text: bool = Field(default=False)


class ModeAdaptRequest(BaseModel):
    html: str = Field(default="", description="Rendered HTML")
    css: str = Field(default="", description="Rendered CSS")
    mode: str = Field(default="presentation", description="Target mode")
    renderer: str = Field(default="reveal.js", description="Renderer type")


class LoadTestRequest(BaseModel):
    operation: str = Field(default="render", description="Operation to test")
    concurrent_users: int = Field(default=10, ge=1, le=100)
    requests_per_user: int = Field(default=5, ge=1, le=50)


# ═══════════════════════════════════════════════════════════════════
# ACCESSIBILITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════


@router.post("/audit/accessibility")
async def audit_accessibility(req: AuditRequest):
    """Run WCAG 2.1 accessibility audit on a presentation DSL."""
    try:
        level_map = {"A": WCAGLevel.A, "AA": WCAGLevel.AA, "AAA": WCAGLevel.AAA}
        level = level_map.get(req.wcag_level.upper(), WCAGLevel.AA)
        auditor = AccessibilityAuditor(target_level=level)
        report = auditor.audit_presentation(req.presentation_dsl)
        _error_tracker.record_request(True)
        return {"status": "ok", "report": report.to_dict()}
    except Exception as e:
        _error_tracker.record_request(False)
        logger.exception("Accessibility audit failed")
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/contrast-check")
async def check_contrast(req: ContrastCheckRequest):
    """Check contrast ratio between two colors."""
    ratio = contrast_ratio(req.foreground, req.background)
    passed_aa, _ = passes_wcag_aa(req.foreground, req.background, req.is_large_text)
    threshold = 3.0 if req.is_large_text else 4.5
    return {
        "foreground": req.foreground,
        "background": req.background,
        "ratio": round(ratio, 2),
        "threshold": threshold,
        "passed_aa": passed_aa,
        "is_large_text": req.is_large_text,
    }


# ═══════════════════════════════════════════════════════════════════
# VISUAL REGRESSION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════


@router.post("/audit/visual-regression")
async def audit_visual_regression(req: VisualRegressionRequest):
    """Compare a slide screenshot against its golden master."""
    try:
        if req.update_baseline and req.image_data:
            _vr_service.update_baseline(
                req.presentation_id, req.slide_id, req.renderer,
                req.image_data, req.width, req.height,
            )
            return {"status": "ok", "action": "baseline_updated"}

        if req.image_data:
            result = _vr_service.compare_slide(
                req.presentation_id, req.slide_id, req.renderer,
                req.image_data, req.width, req.height,
            )
            _error_tracker.record_request(True)
            return {"status": "ok", "result": result.to_dict()}

        return {"status": "ok", "message": "No image data provided"}
    except Exception as e:
        _error_tracker.record_request(False)
        logger.exception("Visual regression failed")
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.get("/visual-regression/stats")
async def visual_regression_stats():
    """Get visual regression service statistics."""
    return {"status": "ok", "stats": _vr_service.get_statistics()}


# ═══════════════════════════════════════════════════════════════════
# COMPREHENSIVE AUDIT
# ═══════════════════════════════════════════════════════════════════


@router.post("/audit/comprehensive")
async def audit_comprehensive(req: ComprehensiveAuditRequest):
    """Run full multi-dimension quality audit."""
    try:
        report = await _orchestrator.run_comprehensive_audit(
            presentation_dsl=req.presentation_dsl,
            presentation_id=req.presentation_id,
            run_visual=req.run_visual,
            run_production=req.run_production,
        )
        _error_tracker.record_request(True)
        return {"status": "ok", "report": report.to_dict()}
    except Exception as e:
        _error_tracker.record_request(False)
        logger.exception("Comprehensive audit failed")
        raise HTTPException(status_code=500, detail=str(e)[:200])


# ═══════════════════════════════════════════════════════════════════
# HEALTH & PRODUCTION
# ═══════════════════════════════════════════════════════════════════


@router.get("/health/components")
async def health_components():
    """Deep health check of all 8 service components."""
    try:
        results = await _health_engine.check_all()
        return {
            "status": "ok",
            "overall": _health_engine.get_overall_status().value,
            "components": {k: v.to_dict() for k, v in results.items()},
        }
    except Exception as e:
        logger.exception("Health check failed")
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/load-test")
async def run_load_test(req: LoadTestRequest):
    """Run a simulated load test."""
    try:
        result = await _load_tester.run_test(
            operation=req.operation,
            concurrent_users=req.concurrent_users,
            requests_per_user=req.requests_per_user,
        )
        return {"status": "ok", "result": result.to_dict()}
    except Exception as e:
        logger.exception("Load test failed")
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.get("/error-budget")
async def error_budget():
    """Get current error budget status."""
    return {"status": "ok", "budget": _error_tracker.get_summary()}


@router.get("/production-readiness")
async def production_readiness():
    """Assess production readiness."""
    try:
        assessor = ProductionReadinessAssessor()
        result = await assessor.assess()
        return {"status": "ok", "assessment": result}
    except Exception as e:
        logger.exception("Production readiness check failed")
        raise HTTPException(status_code=500, detail=str(e)[:200])


# ═══════════════════════════════════════════════════════════════════
# PRESENTATION MODE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════


@router.get("/modes")
async def list_modes():
    """List all presentation modes with configurations."""
    return {"status": "ok", "modes": _mode_manager.get_all_modes()}


@router.get("/modes/{renderer}")
async def renderer_modes(renderer: str):
    """Get supported modes for a specific renderer."""
    try:
        rt = RendererType(renderer)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown renderer: {renderer}. Valid: {[r.value for r in RendererType]}",
        )
    modes = _mode_manager.get_renderer_modes(rt)
    return {"status": "ok", "renderer": renderer, "modes": modes}


@router.post("/modes/reading")
async def transform_reading_mode(req: AuditRequest):
    """Transform presentation DSL into reading mode content."""
    try:
        result = _mode_manager.transform_for_reading(req.presentation_dsl)
        return {"status": "ok", "reading_content": result}
    except Exception as e:
        logger.exception("Reading mode transform failed")
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/modes/adapt")
async def adapt_mode(req: ModeAdaptRequest):
    """Adapt rendered output for a target presentation mode."""
    try:
        mode = PresentationMode(req.mode)
        renderer = RendererType(req.renderer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = _mode_manager.adapt_output(req.html, req.css, mode, renderer)
    return {"status": "ok", "adapted": result}


# ═══════════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════════


@router.get("/stats")
async def quality_stats():
    """Get quality system statistics."""
    return {
        "status": "ok",
        "orchestrator": _orchestrator.get_stats(),
        "accessibility": _auditor.get_stats(),
        "visual_regression": _vr_service.get_statistics(),
        "modes": _mode_manager.get_stats(),
        "error_budget": _error_tracker.get_summary(),
    }
