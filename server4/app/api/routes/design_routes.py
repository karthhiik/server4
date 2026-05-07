"""
Phase 5 -- Design Intelligence API Routes.

Endpoints:
- POST /api/v2/design/discover-styles       — Visual Style Discovery (3 previews)
- POST /api/v2/design/brand-dna/extract      — Extract Brand DNA from colors/image
- POST /api/v2/design/analyze-quality        — Anti-AI-Slop analysis on slide data
- POST /api/v2/design/measure-text           — PreTeXt text measurement
- POST /api/v2/design/check-layout-fit       — Check if content fits a layout
- POST /api/v2/design/pipeline               — Full design intelligence pipeline
- GET  /api/v2/design/presets                — List all style presets
- GET  /api/v2/design/layouts                — List all layout definitions
- GET  /api/v2/design/typography-rules       — List typography rule sets
- GET  /api/v2/design/animation-rules        — List animation rule sets
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.slides_new.design.design_intelligence import (
    DesignIntelligenceEngine,
    DesignQuality,
    PresentationDesignResult,
)
from app.services.slides_new.design.brand_dna import BrandDNA
from app.services.slides_new.design.anti_slop import SlopReport
from app.services.slides_new.design.pretext_engine import (
    LAYOUT_BOXES,
    TextMeasurement,
)
from app.services.slides_new.design.style_discovery import (
    ANIMATION_RULES,
    STYLE_PRESETS,
    TYPOGRAPHY_RULES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/design", tags=["design-intelligence-v2"])

# Singleton engine
_engine = DesignIntelligenceEngine()


# ═══════════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════


class StyleDiscoveryRequest(BaseModel):
    """Request for Visual Style Discovery."""
    topic: str = Field(default="", description="Presentation topic")
    purpose: str = Field(default="", description="Purpose (e.g., investor pitch)")
    audience: str = Field(default="", description="Target audience")
    industry: str = Field(default="", description="Industry vertical")
    mood: str = Field(default="", description="Desired mood override")
    count: int = Field(default=3, ge=1, le=6, description="Number of previews")


class StylePreviewResponse(BaseModel):
    """A single style preview."""
    preset_id: str
    preset_name: str
    family: str
    character: str
    when_to_use: str
    sample_colors: list[str]
    sample_fonts: dict[str, str]
    confidence: float


class StyleDiscoveryResponse(BaseModel):
    """Response from Visual Style Discovery."""
    previews: list[StylePreviewResponse]
    recommended_index: int
    topic: str
    purpose: str
    reasoning: str


class BrandDNAExtractRequest(BaseModel):
    """Request to extract Brand DNA from color list."""
    hex_colors: list[str] = Field(
        default_factory=list,
        description="List of hex colors (e.g., ['#1A1A2E', '#E94560'])",
    )


class BrandDNAResponse(BaseModel):
    """Response with extracted Brand DNA."""
    primary_color: str
    secondary_color: str
    accent_color: str
    palette: list[str]
    heading_font: str
    body_font: str
    mono_font: str
    whitespace_ratio: float
    detected_mood: str
    visual_style: str
    confidence: float


class AnalyzeQualityRequest(BaseModel):
    """Request for anti-AI-slop analysis."""
    slide_data: dict[str, Any] = Field(
        ..., description="Slide properties to analyze"
    )


class SlopViolationResponse(BaseModel):
    """A single slop violation."""
    category: str
    severity: str
    indicator: str
    description: str
    suggestion: str
    auto_fixable: bool
    confidence: float


class AnalyzeQualityResponse(BaseModel):
    """Response from anti-slop analysis."""
    violations: list[SlopViolationResponse]
    slop_score: float
    quality_score: float
    is_clean: bool
    fixes_available: int


class MeasureTextRequest(BaseModel):
    """Request to measure text dimensions."""
    text: str = Field(..., description="Text to measure")
    font_family: str = Field(default="Inter", description="Font family")
    font_size_pt: float = Field(default=16.0, ge=6, le=200, description="Font size in pt")
    max_width_px: float = Field(default=0.0, ge=0, description="Container width (0=no wrap)")
    line_height: float = Field(default=1.5, ge=1.0, le=3.0, description="Line height")
    font_weight: str = Field(default="normal", description="normal or bold")


class MeasureTextResponse(BaseModel):
    """Response with text measurement."""
    width_px: float
    height_px: float
    line_count: int
    overflow: bool
    overflow_amount_px: float
    suggested_font_size: float
    confidence: float


class CheckLayoutFitRequest(BaseModel):
    """Request to check if content fits a layout."""
    layout: str = Field(..., description="Layout name (e.g., 'bullets', 'two-column')")
    content: dict[str, str] = Field(
        ..., description="Content keyed by box name (title, body, etc.)"
    )
    heading_font: str = Field(default="Inter")
    body_font: str = Field(default="Inter")
    heading_size: float = Field(default=36.0)
    body_size: float = Field(default=18.0)


class LayoutFitResponse(BaseModel):
    """Response from layout fit check."""
    fits: bool
    overflow_items: list[str]
    suggestions: list[str]
    total_content_height_px: float
    available_height_px: float


class DesignPipelineRequest(BaseModel):
    """Request for the full design intelligence pipeline."""
    slides: list[dict[str, Any]] = Field(
        ..., description="List of slide content dicts"
    )
    topic: str = Field(default="", description="Presentation topic")
    purpose: str = Field(default="", description="Purpose")
    audience: str = Field(default="", description="Target audience")
    industry: str = Field(default="", description="Industry")
    quality: str = Field(
        default="standard",
        description="Quality tier: draft, standard, premium",
    )
    selected_preset: Optional[str] = Field(
        default=None, description="Override style preset ID"
    )
    brand_colors: list[str] = Field(
        default_factory=list,
        description="Brand colors for DNA extraction (optional)",
    )


class SlideDesignSpecResponse(BaseModel):
    """Design spec for a single slide."""
    slide_index: int
    slide_type: str
    layout: str
    typography_scale: str
    animation_preset: str
    layout_reasoning: str
    text_fits: bool
    text_suggestions: list[str]
    slop_clean: bool
    adjusted_font_sizes: dict[str, float]


class DesignPipelineResponse(BaseModel):
    """Response from the full design pipeline."""
    slide_specs: list[SlideDesignSpecResponse]
    global_slop_score: float
    total_overflow_slides: int
    quality_tier: str
    processing_time_ms: float
    is_production_ready: bool
    warnings: list[str]


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════


@router.post("/discover-styles", response_model=StyleDiscoveryResponse)
async def discover_styles(req: StyleDiscoveryRequest):
    """Run Visual Style Discovery — returns N style previews ranked by relevance."""
    try:
        result = _engine.discover_styles(
            topic=req.topic,
            purpose=req.purpose,
            audience=req.audience,
            industry=req.industry,
            count=req.count,
        )
        previews = [
            StylePreviewResponse(
                preset_id=p.preset_id,
                preset_name=p.preset_name,
                family=p.family.value,
                character=p.character,
                when_to_use=p.when_to_use,
                sample_colors=p.sample_colors,
                sample_fonts=p.sample_fonts,
                confidence=p.confidence,
            )
            for p in result.previews
        ]
        return StyleDiscoveryResponse(
            previews=previews,
            recommended_index=result.recommended_index,
            topic=result.topic,
            purpose=result.purpose,
            reasoning=result.reasoning,
        )
    except Exception as e:
        logger.exception("Style discovery failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brand-dna/extract", response_model=BrandDNAResponse)
async def extract_brand_dna(req: BrandDNAExtractRequest):
    """Extract Brand DNA from a list of hex colors."""
    try:
        dna = _engine.extract_brand_dna(hex_colors=req.hex_colors)
        return BrandDNAResponse(
            primary_color=dna.primary_color,
            secondary_color=dna.secondary_color,
            accent_color=dna.accent_color,
            palette=dna.palette,
            heading_font=dna.heading_font,
            body_font=dna.body_font,
            mono_font=dna.mono_font,
            whitespace_ratio=dna.whitespace_ratio,
            detected_mood=dna.detected_mood.value,
            visual_style=dna.visual_style.value,
            confidence=dna.confidence,
        )
    except Exception as e:
        logger.exception("Brand DNA extraction failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-quality", response_model=AnalyzeQualityResponse)
async def analyze_quality(req: AnalyzeQualityRequest):
    """Run anti-AI-slop analysis on a slide."""
    try:
        report = _engine.analyze_slide_quality(req.slide_data)
        violations = [
            SlopViolationResponse(
                category=v.category.value,
                severity=v.severity.value,
                indicator=v.indicator,
                description=v.description,
                suggestion=v.suggestion,
                auto_fixable=v.auto_fixable,
                confidence=v.confidence,
            )
            for v in report.violations
        ]
        return AnalyzeQualityResponse(
            violations=violations,
            slop_score=report.slop_score,
            quality_score=report.quality_score,
            is_clean=report.is_clean,
            fixes_available=report.fixes_available,
        )
    except Exception as e:
        logger.exception("Quality analysis failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/measure-text", response_model=MeasureTextResponse)
async def measure_text(req: MeasureTextRequest):
    """Measure text rendered dimensions using PreTeXt engine."""
    try:
        m = _engine.measure_text(
            text=req.text,
            font_family=req.font_family,
            font_size_pt=req.font_size_pt,
            max_width_px=req.max_width_px,
        )
        return MeasureTextResponse(
            width_px=m.width_px,
            height_px=m.height_px,
            line_count=m.line_count,
            overflow=m.overflow,
            overflow_amount_px=m.overflow_amount_px,
            suggested_font_size=m.suggested_font_size,
            confidence=m.confidence,
        )
    except Exception as e:
        logger.exception("Text measurement failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-layout-fit", response_model=LayoutFitResponse)
async def check_layout_fit(req: CheckLayoutFitRequest):
    """Check if text content fits within a slide layout."""
    if req.layout not in LAYOUT_BOXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown layout '{req.layout}'. Available: {list(LAYOUT_BOXES.keys())}",
        )
    try:
        result = _engine.check_slide_text_fit(
            layout=req.layout,
            content=req.content,
            heading_font=req.heading_font,
            body_font=req.body_font,
        )
        return LayoutFitResponse(
            fits=result.fits,
            overflow_items=result.overflow_items,
            suggestions=result.suggestions,
            total_content_height_px=result.total_content_height_px,
            available_height_px=result.available_height_px,
        )
    except Exception as e:
        logger.exception("Layout fit check failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipeline", response_model=DesignPipelineResponse)
async def run_design_pipeline(req: DesignPipelineRequest):
    """Run the full design intelligence pipeline on a presentation."""
    # Validate quality tier
    quality_map = {
        "draft": DesignQuality.DRAFT,
        "standard": DesignQuality.STANDARD,
        "premium": DesignQuality.PREMIUM,
    }
    quality = quality_map.get(req.quality)
    if quality is None:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid quality tier '{req.quality}'. Use: draft, standard, premium",
        )

    # Extract brand DNA if colors provided
    brand_dna = None
    if req.brand_colors:
        brand_dna = _engine.extract_brand_dna(hex_colors=req.brand_colors)

    try:
        result = _engine.run_full_pipeline(
            slides=req.slides,
            topic=req.topic,
            purpose=req.purpose,
            audience=req.audience,
            industry=req.industry,
            brand_dna=brand_dna,
            quality=quality,
            selected_preset=req.selected_preset,
        )
        specs = [
            SlideDesignSpecResponse(
                slide_index=s.slide_index,
                slide_type=s.slide_type,
                layout=s.layout,
                typography_scale=s.typography_scale,
                animation_preset=s.animation_preset,
                layout_reasoning=s.layout_reasoning,
                text_fits=s.text_fits,
                text_suggestions=s.text_suggestions,
                slop_clean=s.slop_clean,
                adjusted_font_sizes=s.adjusted_font_sizes,
            )
            for s in result.slide_specs
        ]
        return DesignPipelineResponse(
            slide_specs=specs,
            global_slop_score=result.global_slop_score,
            total_overflow_slides=result.total_overflow_slides,
            quality_tier=result.quality_tier.value,
            processing_time_ms=result.processing_time_ms,
            is_production_ready=result.is_production_ready,
            warnings=result.warnings,
        )
    except Exception as e:
        logger.exception("Design pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presets")
async def list_presets():
    """List all available style presets with metadata."""
    return {
        preset_id: {
            "family": meta["family"].value,
            "character": meta["character"],
            "when_to_use": meta["when_to_use"],
            "keywords": meta["keywords"],
            "industries": meta["industries"],
        }
        for preset_id, meta in STYLE_PRESETS.items()
    }


@router.get("/layouts")
async def list_layouts():
    """List all available layout definitions with bounding boxes."""
    return {
        layout_name: [
            {
                "name": box.name,
                "x": box.x,
                "y": box.y,
                "width": box.width,
                "height": box.height,
                "padding": box.padding,
            }
            for box in boxes
        ]
        for layout_name, boxes in LAYOUT_BOXES.items()
    }


@router.get("/typography-rules")
async def list_typography_rules():
    """List all typography rule sets."""
    return TYPOGRAPHY_RULES


@router.get("/animation-rules")
async def list_animation_rules():
    """List all animation rule sets."""
    return ANIMATION_RULES
