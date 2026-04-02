"""
Image Service — AI-powered slide image generation with graceful fallback.

Architecture:
- Redis hot cache: prompt_hash → URL (TTL 30 days)
- MongoDB cold storage: generation logs for cost tracking
- Graceful fallback to gradient placeholders when image generation fails
- File size validation: discard <5KB, compress >2MB

Updated 2026-04-02: Removed Phoenix/Lucid workers (both returning 500).
Images now use gradient placeholders with optional future AI generation.
"""

import hashlib
import io
import time
from enum import Enum
from typing import Optional

import structlog

from app.config import settings
from app.services.storage.blob_service import BlobStorageService

logger = structlog.get_logger()

# ── Constants ────────────────────────────────────────────────────

REDIS_CACHE_TTL = 30 * 24 * 3600  # 30 days
MIN_IMAGE_SIZE = 5 * 1024  # 5KB — below this is likely blank/error
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2MB — above this needs compression
IMAGE_CACHE_PREFIX = "img_cache:"
IMAGE_EXPIRY_HOURS = 24  # SAS token expiry for image downloads

# ── Theme style keyword mappings for prompt injection ────────────

_THEME_STYLE_KEYWORDS = {
    "tech-neon": "cyberpunk, glowing neon accents, dark background, circuit board patterns, futuristic, digital art, vibrant purple and blue gradients",
    "startup-gradient": "modern startup, vibrant gradient background, energetic, bold colors, dynamic composition, professional yet creative",
    "minimal-mono": "minimalist, clean white background, subtle gray tones, lots of negative space, professional, understated elegance",
    "corporate-blue": "corporate professional, navy blue tones, clean lines, business presentation style, trustworthy, formal",
    "nature-earth": "natural earth tones, green and brown palette, organic shapes, sustainability theme, bright natural lighting, eco-friendly",
    "medical-clean": "sterile laboratory environment, bright lighting, white and blue palette, clinical, clean medical aesthetic, professional healthcare",
    "academic-serif": "academic scholarly style, warm paper tones, classic typography feel, university setting, research-oriented, intellectual",
    "creative-bold": "bold creative design, vibrant colors, artistic composition, modern gallery style, expressive, eye-catching",
}

# ── Layout-to-image-type mapping ─────────────────────────────────


class ImageType(Enum):
    HERO = "hero"
    GENERAL = "general"
    CREATIVE = "creative"
    DATA_VIZ = "data_viz"


_LAYOUT_IMAGE_TYPE = {
    "title-hero": ImageType.HERO,
    "full-image": ImageType.HERO,
    "bullets-with-image": ImageType.GENERAL,
    "quote": ImageType.CREATIVE,
    "chart": ImageType.DATA_VIZ,
    "comparison": ImageType.GENERAL,
    "timeline": ImageType.GENERAL,
    "team-grid": ImageType.GENERAL,
    "kpi-dashboard": ImageType.DATA_VIZ,
    "two-column": ImageType.GENERAL,
    "bullets": ImageType.GENERAL,
    "blank": ImageType.GENERAL,
}


def _get_redis():
    """Lazy Redis connection for image cache."""
    import redis.asyncio as aioredis

    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


def _compute_prompt_hash(prompt: str) -> str:
    """Compute SHA256 hash of prompt for cache key."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def _compress_image_if_needed(
    image_bytes: bytes, max_size: int = MAX_IMAGE_SIZE
) -> bytes:
    """Compress image if it exceeds max_size. Returns compressed bytes."""
    if len(image_bytes) <= max_size:
        return image_bytes

    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        output = io.BytesIO()

        quality = 85
        while quality > 20:
            output.seek(0)
            output.truncate()
            if img.mode in ("RGBA", "P"):
                img.convert("RGB").save(output, format="JPEG", quality=quality)
            else:
                img.save(output, format="JPEG", quality=quality)
            if output.tell() <= max_size:
                break
            quality -= 10

        compressed = output.getvalue()
        logger.info(
            "image_compressed",
            original_kb=len(image_bytes) // 1024,
            compressed_kb=len(compressed) // 1024,
            quality=quality,
        )
        return compressed
    except Exception:
        logger.warning("image_compression_failed", fallback=True)
        return image_bytes


def _build_image_prompt(
    content: dict, layout: str, theme: dict, slide_index: int = 0
) -> str:
    """
    Build a theme-aware image generation prompt.

    Injects theme style keywords, primary color, and layout context
    to ensure visual consistency with the presentation theme.
    """
    title = content.get("title", "")
    bullets = content.get("bullets", [])
    primary_color = theme.get("colors", {}).get("primary", "#2563eb")

    # Extract theme ID for style keyword lookup
    theme_id = theme.get("theme_id", "")
    style_keywords = _THEME_STYLE_KEYWORDS.get(theme_id, "professional, clean design")

    # Determine image type from layout
    image_type = _LAYOUT_IMAGE_TYPE.get(layout, ImageType.GENERAL)

    # Build context from slide content
    context_parts = []
    if title:
        context_parts.append(f"Topic: {title}")
    if bullets:
        context_parts.append(
            f"Key points: {', '.join(str(b)[:50] for b in bullets[:3])}"
        )

    context = (
        ". ".join(context_parts)
        if context_parts
        else "Professional business presentation"
    )

    # Type-specific prompt templates
    type_prompts = {
        ImageType.HERO: (
            f"Stunning hero presentation background for '{title}'. "
            f"Style: {style_keywords}. "
            f"Color palette dominated by {primary_color}. "
            f"{context}. "
            f"High-quality, professional, no text, no logos, no watermarks, "
            f"abstract background suitable for overlaying presentation title text. "
            f"Aspect ratio 16:9, cinematic composition."
        ),
        ImageType.CREATIVE: (
            f"Creative artistic background for presentation quote slide. "
            f"Style: {style_keywords}. "
            f"Color palette: {primary_color}. "
            f"{context}. "
            f"Abstract, inspirational, no text, no logos, no watermarks, "
            f"evocative imagery suitable for a quote overlay. "
            f"Aspect ratio 16:9."
        ),
        ImageType.DATA_VIZ: (
            f"Professional data visualization background for presentation. "
            f"Style: {style_keywords}. "
            f"Color palette: {primary_color}. "
            f"{context}. "
            f"Clean, modern, subtle geometric patterns suggesting data and analytics. "
            f"No text, no logos, no watermarks, no actual charts. "
            f"Aspect ratio 16:9."
        ),
        ImageType.GENERAL: (
            f"Abstract professional presentation background for '{title}'. "
            f"Style: {style_keywords}. "
            f"Color palette dominated by {primary_color}. "
            f"{context}. "
            f"Modern corporate style, clean and professional, "
            f"no text, no logos, no watermarks, suitable for slide content overlay. "
            f"Aspect ratio 16:9."
        ),
    }

    return type_prompts.get(image_type, type_prompts[ImageType.GENERAL])


# ── Image Service ────────────────────────────────────────────────


class ImageService:
    """
    AI-powered image generation for presentation slides.

    Features:
    - Redis hot cache for prompt → URL lookups (sub-millisecond)
    - Lucid (Cloudflare) model for image generation
    - Theme-aware prompt construction
    - File size validation and compression
    - MongoDB cost logging
    - Graceful degradation on failure (gradient placeholders)
    """

    def __init__(self):
        self._blob_service: Optional[BlobStorageService] = None

    async def _get_blob_service(self) -> BlobStorageService:
        if self._blob_service is None:
            self._blob_service = BlobStorageService()
        return self._blob_service

    async def generate_slide_image(
        self,
        content: dict,
        layout: str,
        theme: dict,
        presentation_id: str,
        slide_index: int = 0,
        user_id: str = "",
    ) -> Optional[str]:
        """
        Generate an AI image for a slide.

        Flow:
        1. Check Redis cache (hot cache, sub-ms)
        2. If miss, generate via Lucid (Cloudflare)
        3. Validate file size
        4. Upload to Blob Storage
        5. Cache URL in Redis
        6. Log to MongoDB for cost tracking

        Returns: SAS-protected download URL, or None on failure.
        """
        prompt = _build_image_prompt(content, layout, theme, slide_index)
        prompt_hash = _compute_prompt_hash(prompt)
        cache_key = f"{IMAGE_CACHE_PREFIX}{prompt_hash}"

        # Step 1: Check Redis hot cache
        try:
            r = _get_redis()
            cached_url = await r.get(cache_key)
            if cached_url:
                logger.info(
                    "image_cache_hit",
                    prompt_hash=prompt_hash,
                    slide_index=slide_index,
                )
                await self._log_generation(
                    presentation_id=presentation_id,
                    slide_index=slide_index,
                    model="cached",
                    provider="redis",
                    latency_ms=0,
                    file_size=0,
                    cached=True,
                    user_id=user_id,
                )
                return cached_url
        except Exception:
            pass  # Redis unavailable — proceed to generation

        # Step 2: Generate image via Lucid (Cloudflare)
        start = time.monotonic()
        image_bytes = None
        model_used = "cf-lucid"
        provider = "cloudflare"

        try:
            from app.services.llm.cloudflare_client import create_cf_lucid_client

            client = create_cf_lucid_client()
            image_bytes = await client.generate_image(prompt)
        except Exception as e:
            logger.warning(
                "image_model_failed",
                model=model_used,
                error=str(e),
                fallback="gradient_placeholder",
            )
            await self._log_generation(
                presentation_id=presentation_id,
                slide_index=slide_index,
                model=model_used,
                provider=provider,
                latency_ms=int((time.monotonic() - start) * 1000),
                file_size=0,
                cached=False,
                user_id=user_id,
                error=str(e),
            )
            # Graceful fallback: return None (slide will render without image)
            return None

        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Step 3: Validate file size
        if len(image_bytes) < MIN_IMAGE_SIZE:
            logger.warning(
                "image_too_small_discarded",
                size_bytes=len(image_bytes),
                slide_index=slide_index,
            )
            await self._log_generation(
                presentation_id=presentation_id,
                slide_index=slide_index,
                model=model_used,
                provider=provider,
                latency_ms=elapsed_ms,
                file_size=len(image_bytes),
                cached=False,
                user_id=user_id,
                error="Image too small (<5KB), likely blank or error",
            )
            return None

        # Step 4: Compress if needed
        if len(image_bytes) > MAX_IMAGE_SIZE:
            image_bytes = _compress_image_if_needed(image_bytes)

        # Step 5: Upload to Blob Storage
        try:
            blob_service = await self._get_blob_service()
            blob_name = (
                f"images/{presentation_id}/slide_{slide_index:03d}_{prompt_hash}.jpg"
            )
            await blob_service.upload_file(
                file_data=image_bytes,
                filename=f"slide_{slide_index:03d}.jpg",
                content_type="image/jpeg",
                folder=f"images/{presentation_id}",
            )
            download_url = blob_service.generate_sas_download_url(
                blob_name, expiry_hours=IMAGE_EXPIRY_HOURS
            )
        except Exception as e:
            logger.error(
                "image_upload_failed",
                slide_index=slide_index,
                error=str(e),
            )
            await self._log_generation(
                presentation_id=presentation_id,
                slide_index=slide_index,
                model=model_used,
                provider=provider,
                latency_ms=elapsed_ms,
                file_size=len(image_bytes),
                cached=False,
                user_id=user_id,
                error=str(e),
            )
            return None

        # Step 6: Cache URL in Redis
        try:
            r = _get_redis()
            await r.setex(cache_key, REDIS_CACHE_TTL, download_url)
        except Exception:
            pass  # Non-critical — image still usable without cache

        # Step 7: Log to MongoDB
        await self._log_generation(
            presentation_id=presentation_id,
            slide_index=slide_index,
            model=model_used,
            provider=provider,
            latency_ms=elapsed_ms,
            file_size=len(image_bytes),
            cached=False,
            user_id=user_id,
        )

        logger.info(
            "image_generated",
            slide_index=slide_index,
            model=model_used,
            size_kb=len(image_bytes) // 1024,
            latency_ms=elapsed_ms,
        )

        return download_url

    async def generate_batch_images(
        self,
        slides: list[dict],
        theme: dict,
        presentation_id: str,
        user_id: str = "",
    ) -> dict[int, str]:
        """
        Generate images for all slides that support them.

        Returns: {slide_index: image_url} for successfully generated images.
        Designed for fire-and-forget — does not block the main generation loop.
        """
        results = {}

        for i, slide in enumerate(slides):
            layout = slide.get("layout", "bullets")
            content = slide.get("content", {})

            # Skip layouts that don't benefit from AI images
            if layout in ("chart", "kpi-dashboard", "team-grid", "blank"):
                continue

            url = await self.generate_slide_image(
                content=content,
                layout=layout,
                theme=theme,
                presentation_id=presentation_id,
                slide_index=i,
                user_id=user_id,
            )
            if url:
                results[i] = url

        logger.info(
            "batch_images_generated",
            presentation_id=presentation_id,
            count=len(results),
            total_slides=len(slides),
        )
        return results

    async def _log_generation(
        self,
        presentation_id: str,
        slide_index: int,
        model: str,
        provider: str,
        latency_ms: int,
        file_size: int,
        cached: bool,
        user_id: str = "",
        error: str = "",
    ) -> None:
        """Log image generation to MongoDB for cost tracking and analytics."""
        try:
            from app.database import get_db

            db = get_db()
            await db.generation_logs.insert_one(
                {
                    "presentation_id": presentation_id,
                    "slide_index": slide_index,
                    "phase": "image_generation",
                    "model": model,
                    "provider": provider,
                    "latency_ms": latency_ms,
                    "file_size": file_size,
                    "cached": cached,
                    "user_id": user_id,
                    "error": error,
                    "created_at": time.time(),
                }
            )
        except Exception as e:
            logger.warning("image_log_failed", error=str(e))

    async def close(self) -> None:
        """Close blob service connection."""
        if self._blob_service:
            await self._blob_service.close()
            self._blob_service = None
