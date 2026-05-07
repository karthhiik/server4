"""
Phase 8 — Image Pipeline API Routes.

Endpoints:
    POST /api/v2/images/generate          — Single image generation
    POST /api/v2/images/generate-batch     — Batch image generation
    GET  /api/v2/images/providers/status   — Provider health status
    POST /api/v2/images/providers/health   — Run health checks on all providers
    GET  /api/v2/images/stats              — Image generation statistics
    DELETE /api/v2/images/cache/{hash}     — Invalidate cached image
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import structlog

from app.config import settings
from app.services.image_pipeline import (
    ImageAssetManager,
    ImageModelTier,
    ImagePipelineRouter,
    PromptContext,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v2/images", tags=["images-v2"])


# ── Request/Response schemas ─────────────────────────────────────

class ImageGenerateRequest(BaseModel):
    """Request body for single image generation."""
    prompt: Optional[str] = Field(default=None, max_length=2000)
    title: str = Field(default="", max_length=200)
    subtitle: str = Field(default="", max_length=300)
    bullets: list[str] = Field(default_factory=list)
    slide_type: str = Field(default="custom")
    layout: str = Field(default="bullets")
    theme_id: str = Field(default="")
    primary_color: str = Field(default="#2563eb")
    accent_color: str = Field(default="#7c3aed")
    variant: str = Field(default="dark")
    presentation_id: str = Field(default="standalone")
    slide_index: int = Field(default=0)
    preferred_tier: Optional[str] = Field(default=None)


class ImageGenerateResponse(BaseModel):
    """Response for image generation."""
    success: bool
    image_url: Optional[str] = None
    provider: Optional[str] = None
    tier: Optional[str] = None
    latency_ms: Optional[int] = None
    error: Optional[str] = None


class BatchImageRequest(BaseModel):
    """Request body for batch image generation."""
    presentation_id: str
    slides: list[ImageGenerateRequest]


class BatchImageResponse(BaseModel):
    """Response for batch image generation."""
    success: bool
    results: dict[int, str]  # slide_index → image_url
    total_requested: int
    total_generated: int


class ProviderStatusResponse(BaseModel):
    """Response for provider status."""
    providers: dict[str, dict]


class StatsResponse(BaseModel):
    """Response for image generation statistics."""
    total_generated: int = 0
    total_cached: int = 0
    total_failures: int = 0
    avg_latency_ms: float = 0.0
    total_bytes_generated: int = 0


# ── Endpoints ────────────────────────────────────────────────────

@router.post("/generate", response_model=ImageGenerateResponse)
async def generate_image(request: ImageGenerateRequest):
    """Generate a single slide image using the 4-tier fallback pipeline."""
    ctx = PromptContext(
        title=request.title,
        subtitle=request.subtitle,
        bullets=request.bullets,
        slide_type=request.slide_type,
        layout=request.layout,
        theme_id=request.theme_id,
        primary_color=request.primary_color,
        accent_color=request.accent_color,
        variant=request.variant,
        slide_index=request.slide_index,
        custom_prompt=request.prompt,
    )

    preferred = None
    if request.preferred_tier:
        try:
            preferred = ImageModelTier(request.preferred_tier)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid tier: {request.preferred_tier}. "
                f"Valid: {[t.value for t in ImageModelTier]}",
            )
        if preferred == ImageModelTier.POLLINATIONS and not settings.ALLOW_POLLINATIONS_IMAGES:
            raise HTTPException(
                status_code=400,
                detail="Pollinations is disabled for production image generation",
            )

    asset_manager = ImageAssetManager()
    try:
        url = await asset_manager.generate_slide_image(
            ctx=ctx,
            presentation_id=request.presentation_id,
            slide_index=request.slide_index,
            preferred_tier=preferred,
        )

        if url:
            return ImageGenerateResponse(
                success=True,
                image_url=url,
            )
        else:
            return ImageGenerateResponse(
                success=False,
                error="All image providers failed",
            )
    except Exception as e:
        logger.error("image_generate_endpoint_error", error=str(e))
        return ImageGenerateResponse(
            success=False,
            error=str(e),
        )
    finally:
        await asset_manager.close()


@router.post("/generate-batch", response_model=BatchImageResponse)
async def generate_batch_images(request: BatchImageRequest):
    """Generate images for multiple slides in a presentation."""
    asset_manager = ImageAssetManager()

    try:
        slide_contexts = []
        for slide_req in request.slides:
            ctx = PromptContext(
                title=slide_req.title,
                subtitle=slide_req.subtitle,
                bullets=slide_req.bullets,
                slide_type=slide_req.slide_type,
                layout=slide_req.layout,
                theme_id=slide_req.theme_id,
                primary_color=slide_req.primary_color,
                accent_color=slide_req.accent_color,
                variant=slide_req.variant,
                slide_index=slide_req.slide_index,
                custom_prompt=slide_req.prompt,
            )
            slide_contexts.append((ctx, slide_req.slide_index))

        results = await asset_manager.generate_batch_images(
            slide_contexts=slide_contexts,
            presentation_id=request.presentation_id,
        )

        return BatchImageResponse(
            success=True,
            results=results,
            total_requested=len(request.slides),
            total_generated=len(results),
        )
    except Exception as e:
        logger.error("batch_generate_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await asset_manager.close()


@router.get("/providers/status", response_model=ProviderStatusResponse)
async def get_provider_status():
    """Get current health status of all image providers."""
    asset_manager = ImageAssetManager()
    status = asset_manager.get_provider_status()
    return ProviderStatusResponse(providers=status)


@router.post("/providers/health")
async def run_health_checks():
    """Run live health checks on all configured image providers."""
    router_instance = ImagePipelineRouter()
    results = await router_instance.health_check_all()
    return {
        "providers": results,
        "all_healthy": all(results.values()),
        "healthy_count": sum(1 for v in results.values() if v),
        "total_count": len(results),
    }


@router.get("/stats", response_model=StatsResponse)
async def get_image_stats(presentation_id: Optional[str] = None):
    """Get aggregated image generation statistics."""
    asset_manager = ImageAssetManager()
    stats = await asset_manager.get_stats(presentation_id)
    return StatsResponse(
        total_generated=stats.total_generated,
        total_cached=stats.total_cached,
        total_failures=stats.total_failures,
        avg_latency_ms=stats.avg_latency_ms,
        total_bytes_generated=stats.total_bytes_generated,
    )


@router.delete("/cache/{prompt_hash}")
async def invalidate_cache(prompt_hash: str):
    """Invalidate a cached image by prompt hash."""
    if len(prompt_hash) > 64:
        raise HTTPException(status_code=400, detail="Invalid prompt hash")

    asset_manager = ImageAssetManager()
    deleted = await asset_manager.invalidate_cache(prompt_hash)
    return {"success": deleted, "prompt_hash": prompt_hash}
