"""
Image Asset Manager — Redis cache + Azure Blob CDN + MongoDB tracking.

Handles:
- Redis hot cache: prompt_hash → CDN URL (30-day TTL)
- Azure Blob upload with SAS-protected download URLs
- MongoDB asset tracking for analytics and cost monitoring
- Batch operations for full-deck image generation
- Cache invalidation and cleanup
"""

import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional

import structlog

from app.config import settings
from app.services.image_pipeline.image_processor import (
    ImageFormat,
    ImageProcessor,
    ProcessedImage,
)
from app.services.image_pipeline.pipeline_router import (
    ImageGenerationResult,
    ImageModelTier,
    ImagePipelineRouter,
    PromptContext,
)
from app.services.storage.blob_service import BlobStorageService

logger = structlog.get_logger()

# ── Constants ────────────────────────────────────────────────────

REDIS_CACHE_TTL = 30 * 24 * 3600  # 30 days
IMAGE_CACHE_PREFIX = "imgv2:"
SAS_EXPIRY_HOURS = 24


def _compute_hash(text: str) -> str:
    """SHA256 hash truncated to 16 chars for cache keys."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _get_redis():
    """Lazy async Redis connection."""
    import redis.asyncio as aioredis
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


# ── Data types ───────────────────────────────────────────────────

@dataclass
class AssetRecord:
    """Single image asset record stored in MongoDB."""
    presentation_id: str
    slide_index: int
    blob_name: str
    download_url: str
    prompt_hash: str
    prompt_used: str
    provider: str
    model: str
    tier: str
    latency_ms: int
    original_size: int
    processed_size: int
    width: int
    height: int
    format: str
    cached: bool
    fallback_count: int
    created_at: float = field(default_factory=time.time)
    user_id: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "presentation_id": self.presentation_id,
            "slide_index": self.slide_index,
            "blob_name": self.blob_name,
            "download_url": self.download_url,
            "prompt_hash": self.prompt_hash,
            "prompt_used": self.prompt_used,
            "provider": self.provider,
            "model": self.model,
            "tier": self.tier,
            "latency_ms": self.latency_ms,
            "original_size": self.original_size,
            "processed_size": self.processed_size,
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "cached": self.cached,
            "fallback_count": self.fallback_count,
            "created_at": self.created_at,
            "user_id": self.user_id,
            "error": self.error,
        }


@dataclass
class AssetStats:
    """Aggregated statistics for image generation."""
    total_generated: int = 0
    total_cached: int = 0
    total_failures: int = 0
    avg_latency_ms: float = 0.0
    total_bytes_generated: int = 0
    provider_breakdown: dict = field(default_factory=dict)


class ImageAssetManager:
    """
    Full-lifecycle image asset management for presentations.

    Orchestrates:
    1. Cache check (Redis)
    2. Image generation (via PipelineRouter)
    3. Image processing (resize/optimize)
    4. Blob upload (Azure Blob CDN)
    5. Cache write (Redis)
    6. MongoDB logging (analytics/cost)

    Drop-in replacement for the old single-provider ImageService.
    """

    def __init__(self):
        self._router = ImagePipelineRouter()
        self._processor = ImageProcessor()
        self._blob_service: Optional[BlobStorageService] = None

    async def _get_blob_service(self) -> BlobStorageService:
        if self._blob_service is None:
            self._blob_service = BlobStorageService()
        return self._blob_service

    # ── Main API ─────────────────────────────────────────────────

    async def generate_slide_image(
        self,
        ctx: PromptContext,
        presentation_id: str,
        slide_index: int,
        user_id: str = "",
        preferred_tier: Optional[ImageModelTier] = None,
        skip_cache: bool = False,
    ) -> Optional[str]:
        """
        Generate, process, upload, cache, and log an image for a slide.

        Full pipeline:
        1. Check Redis cache → return cached URL if hit
        2. Generate via PipelineRouter (4-tier fallback)
        3. Validate and process (resize/optimize/format)
        4. Upload to Azure Blob Storage
        5. Cache URL in Redis
        6. Log to MongoDB

        Args:
            ctx: Full slide context for prompt building.
            presentation_id: Parent presentation ID.
            slide_index: Slide position index.
            user_id: User who initiated generation.
            preferred_tier: Force a specific provider tier.
            skip_cache: Bypass Redis cache check.

        Returns:
            SAS-protected download URL, or None on failure.
        """
        # Build prompt hash for caching
        from app.services.image_pipeline.prompt_builder import AdvancedPromptBuilder
        builder = AdvancedPromptBuilder()
        prompt = builder.build_prompt(ctx)
        prompt_hash = _compute_hash(prompt)
        cache_key = f"{IMAGE_CACHE_PREFIX}{prompt_hash}"

        # Step 1: Check Redis cache
        if not skip_cache:
            try:
                r = _get_redis()
                cached_url = await r.get(cache_key)
                if cached_url:
                    logger.info(
                        "image_cache_hit",
                        prompt_hash=prompt_hash,
                        slide_index=slide_index,
                    )
                    await self._log_to_mongo(AssetRecord(
                        presentation_id=presentation_id,
                        slide_index=slide_index,
                        blob_name="",
                        download_url=cached_url,
                        prompt_hash=prompt_hash,
                        prompt_used=prompt[:200],
                        provider="redis",
                        model="cached",
                        tier="cached",
                        latency_ms=0,
                        original_size=0,
                        processed_size=0,
                        width=0,
                        height=0,
                        format="",
                        cached=True,
                        fallback_count=0,
                        user_id=user_id,
                    ))
                    return cached_url
            except Exception:
                pass  # Redis unavailable — proceed to generation

        # Step 2: Generate image via pipeline router
        gen_result = await self._router.generate(
            ctx, preferred_tier=preferred_tier
        )
        if gen_result is None:
            await self._log_to_mongo(AssetRecord(
                presentation_id=presentation_id,
                slide_index=slide_index,
                blob_name="",
                download_url="",
                prompt_hash=prompt_hash,
                prompt_used=prompt[:200],
                provider="none",
                model="none",
                tier="none",
                latency_ms=0,
                original_size=0,
                processed_size=0,
                width=0,
                height=0,
                format="",
                cached=False,
                fallback_count=0,
                user_id=user_id,
                error="All image providers failed",
            ))
            return None

        # Step 3: Validate and process
        if not self._processor.validate(gen_result.image_bytes):
            logger.warning(
                "image_validation_failed_post_gen",
                provider=gen_result.provider,
                size=len(gen_result.image_bytes),
            )
            return None

        processed = self._processor.process(
            gen_result.image_bytes,
            target_width=1920,
            target_height=1080,
            output_format=ImageFormat.JPEG,
        )

        # Step 4: Upload to Blob Storage
        try:
            blob_service = await self._get_blob_service()
            blob_name = await blob_service.upload_file(
                file_data=processed.image_bytes,
                filename=f"slide_{slide_index:03d}_{prompt_hash}.jpg",
                content_type=processed.content_type,
                folder=f"images/{presentation_id}",
            )
            download_url = blob_service.generate_sas_download_url(
                blob_name, expiry_hours=SAS_EXPIRY_HOURS
            )
        except Exception as e:
            logger.error(
                "image_upload_failed",
                slide_index=slide_index,
                error=str(e),
            )
            await self._log_to_mongo(AssetRecord(
                presentation_id=presentation_id,
                slide_index=slide_index,
                blob_name="",
                download_url="",
                prompt_hash=prompt_hash,
                prompt_used=gen_result.prompt_used[:200],
                provider=gen_result.provider,
                model=gen_result.model,
                tier=gen_result.tier.value,
                latency_ms=gen_result.latency_ms,
                original_size=len(gen_result.image_bytes),
                processed_size=processed.processed_size,
                width=processed.width,
                height=processed.height,
                format=processed.format.value,
                cached=False,
                fallback_count=gen_result.fallback_count,
                user_id=user_id,
                error=f"Upload failed: {e}",
            ))
            return None

        # Step 5: Cache URL in Redis
        try:
            r = _get_redis()
            await r.setex(cache_key, REDIS_CACHE_TTL, download_url)
        except Exception:
            pass  # Non-critical

        # Step 6: Log to MongoDB
        record = AssetRecord(
            presentation_id=presentation_id,
            slide_index=slide_index,
            blob_name=blob_name,
            download_url=download_url,
            prompt_hash=prompt_hash,
            prompt_used=gen_result.prompt_used[:200],
            provider=gen_result.provider,
            model=gen_result.model,
            tier=gen_result.tier.value,
            latency_ms=gen_result.latency_ms,
            original_size=len(gen_result.image_bytes),
            processed_size=processed.processed_size,
            width=processed.width,
            height=processed.height,
            format=processed.format.value,
            cached=False,
            fallback_count=gen_result.fallback_count,
            user_id=user_id,
        )
        await self._log_to_mongo(record)

        logger.info(
            "image_asset_created",
            slide_index=slide_index,
            provider=gen_result.provider,
            model=gen_result.model,
            tier=gen_result.tier.value,
            latency_ms=gen_result.latency_ms,
            size_kb=processed.processed_size // 1024,
            fallbacks=gen_result.fallback_count,
        )

        return download_url

    # ── Batch API ────────────────────────────────────────────────

    async def generate_batch_images(
        self,
        slide_contexts: list[tuple[PromptContext, int]],
        presentation_id: str,
        user_id: str = "",
    ) -> dict[int, str]:
        """
        Generate images for multiple slides sequentially.

        Args:
            slide_contexts: List of (PromptContext, slide_index) tuples.
            presentation_id: Parent presentation ID.
            user_id: User who initiated generation.

        Returns:
            {slide_index: download_url} for successful generations.
        """
        results: dict[int, str] = {}

        for ctx, slide_index in slide_contexts:
            url = await self.generate_slide_image(
                ctx=ctx,
                presentation_id=presentation_id,
                slide_index=slide_index,
                user_id=user_id,
            )
            if url:
                results[slide_index] = url

        logger.info(
            "batch_images_complete",
            presentation_id=presentation_id,
            success_count=len(results),
            total_requested=len(slide_contexts),
        )
        return results

    # ── Cache management ─────────────────────────────────────────

    async def invalidate_cache(self, prompt_hash: str) -> bool:
        """Remove a specific prompt hash from Redis cache."""
        try:
            r = _get_redis()
            cache_key = f"{IMAGE_CACHE_PREFIX}{prompt_hash}"
            deleted = await r.delete(cache_key)
            return deleted > 0
        except Exception:
            return False

    async def invalidate_presentation_cache(
        self, presentation_id: str
    ) -> int:
        """Remove all cached images for a presentation."""
        try:
            from app.database import get_db
            db = get_db()
            records = await db.image_assets.find(
                {"presentation_id": presentation_id},
                {"prompt_hash": 1},
            ).to_list(None)

            r = _get_redis()
            count = 0
            for rec in records:
                key = f"{IMAGE_CACHE_PREFIX}{rec['prompt_hash']}"
                count += await r.delete(key)
            return count
        except Exception as e:
            logger.warning("cache_invalidation_failed", error=str(e))
            return 0

    # ── Stats / analytics ────────────────────────────────────────

    async def get_stats(self, presentation_id: Optional[str] = None) -> AssetStats:
        """Get aggregated image generation statistics."""
        try:
            from app.database import get_db
            db = get_db()

            query = {}
            if presentation_id:
                query["presentation_id"] = presentation_id

            pipeline = [
                {"$match": query},
                {
                    "$group": {
                        "_id": None,
                        "total": {"$sum": 1},
                        "cached": {
                            "$sum": {"$cond": ["$cached", 1, 0]}
                        },
                        "failures": {
                            "$sum": {"$cond": [{"$ne": ["$error", ""]}, 1, 0]}
                        },
                        "avg_latency": {"$avg": "$latency_ms"},
                        "total_bytes": {"$sum": "$processed_size"},
                    }
                },
            ]

            results = await db.image_assets.aggregate(pipeline).to_list(1)
            if not results:
                return AssetStats()

            r = results[0]
            return AssetStats(
                total_generated=r.get("total", 0),
                total_cached=r.get("cached", 0),
                total_failures=r.get("failures", 0),
                avg_latency_ms=r.get("avg_latency", 0.0),
                total_bytes_generated=r.get("total_bytes", 0),
            )
        except Exception as e:
            logger.warning("stats_query_failed", error=str(e))
            return AssetStats()

    def get_provider_status(self) -> dict[str, dict]:
        """Get current provider health status."""
        return self._router.get_provider_status()

    # ── Internal ─────────────────────────────────────────────────

    async def _log_to_mongo(self, record: AssetRecord) -> None:
        """Persist asset record to MongoDB."""
        try:
            from app.database import get_db
            db = get_db()
            await db.image_assets.insert_one(record.to_dict())
        except Exception as e:
            logger.warning("image_asset_log_failed", error=str(e))

    async def close(self) -> None:
        """Clean up resources."""
        if self._blob_service:
            await self._blob_service.close()
            self._blob_service = None
