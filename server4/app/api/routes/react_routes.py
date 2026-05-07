"""
Phase 6 — React + Three.js Renderer API Routes.

Endpoints:
- POST /api/v2/react/compile          — Compile PresentationDSL → React + Three.js bundle
- POST /api/v2/react/preview-slide     — Preview single slide as React JSX
- GET  /api/v2/react/scene-types       — List available 3D scene types
- POST /api/v2/react/performance-check — Budget analysis for 3D scenes
- POST /api/v2/react/vfx-analyze       — Run VFX Agent on slides (classify for 3D)
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.dsl_v2 import PresentationDSL, SlideDSL
from app.services.slides_new.renderers.react_compiler import ReactCompiler
from app.services.slides_new.renderers.performance_guardrails import (
    PerformanceGuardrails,
    QualityLevel,
    SCENE_COMPLEXITY,
    PRESENTATION_BUDGET,
)
from app.services.slides_new.renderers.react_templates import (
    SCENE_TEMPLATES,
    COMPONENT_TEMPLATES,
    get_scene_template,
    list_scene_names,
    list_component_names,
    get_3d_capable_layouts,
)
from app.services.slides_new.agents.vfx_agent import (
    classify_slide_for_3d,
    get_available_scene_types,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/react", tags=["react-renderer-v2"])


# ═══════════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════


class ReactCompileRequest(BaseModel):
    """Request to compile a PresentationDSL into a React + Three.js bundle."""

    presentation: PresentationDSL
    theme_id: Optional[str] = None
    quality: str = Field(
        default="high",
        description="Quality level: high, medium, low, fallback_2d",
    )
    enable_3d: bool = Field(
        default=True,
        description="Enable Three.js 3D scenes. Disable for 2D-only output.",
    )


class ReactCompileResponse(BaseModel):
    """Compiled React + Three.js output."""

    app_tsx: str = Field(..., description="Main App.tsx source code")
    theme_css: str = Field(..., description="Theme CSS variables")
    vite_config: str = Field(..., description="Vite configuration")
    import_manifest: dict[str, Any] = Field(
        default_factory=dict, description="Package dependencies"
    )
    scene_configs: list[dict[str, Any]] = Field(
        default_factory=list, description="Three.js scene configurations"
    )
    lazy_load_plan: list[dict[str, Any]] = Field(
        default_factory=list, description="Lazy loading directives"
    )
    slide_count: int = 0
    success: bool = True
    error: Optional[str] = None


class PreviewSlideRequest(BaseModel):
    """Request to preview a single slide as React JSX."""

    slide: SlideDSL
    theme_id: Optional[str] = None
    quality: str = Field(default="high")


class PreviewSlideResponse(BaseModel):
    """Single slide React JSX preview."""

    jsx: str
    css: str
    success: bool = True
    error: Optional[str] = None


class SceneTypeInfo(BaseModel):
    """Information about a Three.js scene type."""

    name: str
    r3f_component: str
    default_camera_fov: int
    default_camera_z: float
    estimated_polygons: int
    estimated_particles: int
    estimated_memory_mb: float
    default_config: dict[str, Any] = Field(default_factory=dict)


class PerformanceCheckRequest(BaseModel):
    """Request to check 3D performance budget."""

    scenes: list[dict[str, Any]] = Field(
        ...,
        description="List of scene dicts with 'slide_index' and 'scene_type' keys",
    )
    quality: str = Field(default="high")


class PerformanceCheckResponse(BaseModel):
    """Performance budget analysis result."""

    passed: bool
    total_3d_slides: int
    total_polygons: int = 0
    total_memory_mb: float = 0.0
    recommended_quality: str = "high"
    violations: list[dict[str, Any]] = Field(default_factory=list)
    per_scene: list[dict[str, Any]] = Field(default_factory=list)


class VFXClassifyRequest(BaseModel):
    """Request to classify a single slide for 3D potential."""

    slide_type: str
    layout: str = "center-focus"
    title: str = ""
    body: str = ""


class VFXClassifyResponse(BaseModel):
    """VFX classification result."""

    score: float
    scene_candidates: list[str]
    reasons: list[str]
    qualifies: bool


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════


@router.post("/compile", response_model=ReactCompileResponse)
async def compile_react_presentation(request: ReactCompileRequest):
    """
    Compile a PresentationDSL into a full React + Three.js bundle.

    Returns App.tsx, theme CSS, Vite config, import manifest,
    Three.js scene configs, and lazy-load plan.
    """
    try:
        compiler = ReactCompiler()
        result = compiler.render_presentation(request.presentation)

        assets = result.assets or {}

        return ReactCompileResponse(
            app_tsx=result.html,
            theme_css=result.css,
            vite_config=result.js,
            import_manifest=assets.get("import_manifest", {}),
            scene_configs=assets.get("scene_configs", []),
            lazy_load_plan=assets.get("lazy_load_plan", []),
            slide_count=len(request.presentation.slides),
            success=True,
        )

    except Exception as e:
        logger.exception("react_compile_error", exc_info=e)
        return ReactCompileResponse(
            app_tsx="",
            theme_css="",
            vite_config="",
            slide_count=0,
            success=False,
            error=str(e),
        )


@router.post("/preview-slide", response_model=PreviewSlideResponse)
async def preview_slide_react(request: PreviewSlideRequest):
    """
    Render a single slide as React JSX for live preview.
    """
    try:
        compiler = ReactCompiler()
        result = compiler.render_slide(request.slide)

        return PreviewSlideResponse(
            jsx=result.html,
            css=result.css,
            success=True,
        )

    except Exception as e:
        logger.exception("react_preview_error", exc_info=e)
        return PreviewSlideResponse(
            jsx="",
            css="",
            success=False,
            error=str(e),
        )


@router.get("/scene-types", response_model=list[SceneTypeInfo])
async def list_scene_types():
    """
    List all available Three.js scene types with their metadata,
    default configs, and estimated complexity.
    """
    result = []
    for name, template in SCENE_TEMPLATES.items():
        complexity = SCENE_COMPLEXITY.get(name, {})
        result.append(SceneTypeInfo(
            name=name,
            r3f_component=template.r3f_component,
            default_camera_fov=template.camera_fov,
            default_camera_z=template.camera_z,
            estimated_polygons=complexity.get("polygons", 0),
            estimated_particles=complexity.get("particles", 0),
            estimated_memory_mb=complexity.get("memory_mb", 0),
            default_config=template.default_config,
        ))
    return result


@router.post("/performance-check", response_model=PerformanceCheckResponse)
async def check_performance_budget(request: PerformanceCheckRequest):
    """
    Analyse 3D performance budget for a set of scenes.
    Returns pass/fail, violations, and per-scene analysis.
    """
    try:
        quality = QualityLevel(request.quality)
    except ValueError:
        quality = QualityLevel.HIGH

    guardrails = PerformanceGuardrails()

    # Per-scene analysis
    per_scene = []
    for scene_def in request.scenes:
        scene_type = scene_def.get("scene_type", "")
        if not scene_type:
            continue

        report = guardrails.analyze_scene(scene_type, quality)
        per_scene.append({
            "slide_index": scene_def.get("slide_index", -1),
            "scene_type": scene_type,
            "quality": report.quality_level.value,
            "passed": report.passed,
            "polygons": report.polygons,
            "particles": report.particles,
            "memory_mb": report.estimated_memory_mb,
            "fallback_2d": report.fallback_2d,
            "violations": [
                {
                    "metric": v.metric,
                    "limit": v.limit,
                    "actual": v.actual,
                    "severity": v.severity,
                }
                for v in report.violations
            ],
        })

    # Presentation-level analysis
    pres_report = guardrails.analyze_presentation(request.scenes)

    return PerformanceCheckResponse(
        passed=pres_report.passed,
        total_3d_slides=pres_report.total_3d_slides,
        total_polygons=pres_report.total_polygons,
        total_memory_mb=pres_report.total_memory_mb,
        recommended_quality=pres_report.recommended_quality.value,
        violations=[
            {
                "metric": v.metric,
                "limit": v.limit,
                "actual": v.actual,
                "severity": v.severity,
                "recommendation": v.recommendation,
            }
            for v in pres_report.violations
        ],
        per_scene=per_scene,
    )


@router.post("/vfx-analyze", response_model=VFXClassifyResponse)
async def analyze_slide_vfx(request: VFXClassifyRequest):
    """
    Classify a single slide for 3D potential using VFX Agent heuristics.
    Useful for frontend to show 3D toggle suggestions.
    """
    result = classify_slide_for_3d(
        slide_type=request.slide_type,
        layout=request.layout,
        title=request.title,
        body=request.body,
    )
    return VFXClassifyResponse(**result)


@router.get("/capabilities")
async def get_react_renderer_capabilities():
    """
    Return metadata about the React renderer's capabilities.
    Useful for frontend feature detection.
    """
    return {
        "renderer": "react-threejs",
        "version": "6.0.0",
        "features": {
            "three_js": True,
            "framer_motion": True,
            "lazy_loading": True,
            "adaptive_quality": True,
            "dark_mode": True,
            "vite_hmr": True,
        },
        "scene_types": list_scene_names(),
        "layout_types": list_component_names(),
        "3d_capable_layouts": get_3d_capable_layouts(),
        "quality_levels": [q.value for q in QualityLevel],
        "presentation_budget": {
            "max_3d_slides": PRESENTATION_BUDGET["max_3d_slides"],
            "max_total_memory_mb": PRESENTATION_BUDGET["max_total_memory_mb"],
            "max_total_polygons": PRESENTATION_BUDGET["max_total_polygons"],
        },
    }
