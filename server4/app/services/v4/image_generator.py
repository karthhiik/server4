"""
V4 Image Generator — non-blocking bridge between writer output and the
image pipeline router.

Runs as Stage 4.7 in `content_pipeline.py`, AFTER writer + visual_decider
but BEFORE (or in parallel with) critic. Generation does not block the
return of the pipeline result — each image resolves asynchronously and
publishes a `slide_image_ready` event to Redis pub/sub. The frontend
swaps placeholder → real URL live.

Behavior:
  - Selects slides where `render_decision.modality == "image"`.
  - Enhances `image_prompt` with palette tokens + brand style suffix so
    every image in a deck reads as one consistent visual system.
  - Maps intent → ImageIntent (title → HERO_BACKGROUND; closing → HERO;
    atmosphere / section → CONTENT_ILLUSTRATION; everything else keeps
    its writer-chosen prompt).
  - Caps concurrency at 4 (default). Each image is 5-17s wall-clock;
    4-way parallel keeps total time under 25s for 12-slide decks.
  - Failure → fallback to gradient placeholder (no crash, no stock
    photo — gradient is deterministic from palette).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from bson import ObjectId

import structlog

import httpx

from app.services.image_pipeline.pipeline_router import (
    ImageGenerationResult,
    ImageModelTier,
    ImagePipelineRouter,
)
from app.services.image_pipeline.prompt_builder import ImageIntent, PromptContext
from app.services.v4.design_resolver import ResolvedDesignTokens
from app.services.v4.image_prompt_library import build_image_prompt
from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.visual_rhythm import catalog_anti_pattern_prompt_suffix
from app.config import settings

logger = structlog.get_logger(__name__)


# Progress emitter signature — matches ProgressCallback in content_pipeline.
ProgressEmit = Callable[[str, dict[str, Any]], Awaitable[None]]


@dataclass
class ImageJob:
    slide_index: int
    slide_id: str
    prompt: str
    intent: ImageIntent
    preferred_tier: Optional[ImageModelTier]
    position: str = "foreground"
    slide_layout: str = ""
    slide_intent: str = ""


# ── Intent mapping (slide.intent → ImageIntent) ────────────────────

_INTENT_TO_IMAGE: dict[str, ImageIntent] = {
    "title":       ImageIntent.HERO_BACKGROUND,
    "cover":       ImageIntent.HERO_BACKGROUND,
    "closing":     ImageIntent.HERO_BACKGROUND,
    "ask":         ImageIntent.HERO_BACKGROUND,
    "vision":      ImageIntent.HERO_BACKGROUND,
    "atmosphere":  ImageIntent.CONTENT_ILLUSTRATION,
    "section":     ImageIntent.CONTENT_ILLUSTRATION,
    "product":     ImageIntent.PRODUCT_SHOWCASE,
    "solution":    ImageIntent.CONTENT_ILLUSTRATION,
    "market":      ImageIntent.DATA_CONTEXT,
    "how_it_works":ImageIntent.CONTENT_ILLUSTRATION,
    "team":        ImageIntent.TEAM_PORTRAIT,
}


# ── Tier preference map ────────────────────────────────────────────
# Hero shots → FLUX Kontext (best quality, ~17s, paid).
# Supporting images → faster/cheaper tiers. Router handles fallback.

_INTENT_TIER: dict[ImageIntent, Optional[ImageModelTier]] = {
    ImageIntent.HERO_BACKGROUND:      ImageModelTier.AZURE_FLUX,
    ImageIntent.PRODUCT_SHOWCASE:     ImageModelTier.AZURE_FLUX,
    ImageIntent.CREATIVE_ARTISTIC:    ImageModelTier.AZURE_FLUX,
    ImageIntent.CONTENT_ILLUSTRATION: None,  # let router pick
    ImageIntent.DATA_CONTEXT:         None,
    ImageIntent.TEAM_PORTRAIT:        None,
}


# ── Image position map ─────────────────────────────────────────────
# Tells the renderer HOW to compose the image with the slide content:
#   "background"  → full-bleed behind text (with overlay scrim)
#   "foreground"  → side-panel hero (e.g. 50/50 split with copy)
#   "inline"      → small thumbnail/figure embedded in body
# Drives both sandbox preview + final renderer. Layout-aware: a
# hero/cover slide always renders the image as background even if the
# writer wrote bullets, while a market slide uses an inline figure.
_INTENT_POSITION: dict[ImageIntent, str] = {
    ImageIntent.HERO_BACKGROUND:      "background",
    ImageIntent.CREATIVE_ARTISTIC:    "background",
    ImageIntent.PRODUCT_SHOWCASE:     "foreground",
    ImageIntent.TEAM_PORTRAIT:        "foreground",
    ImageIntent.CONTENT_ILLUSTRATION: "foreground",
    ImageIntent.DATA_CONTEXT:         "inline",
}

# Layouts that explicitly want a full-bleed image regardless of intent.
_FULL_BLEED_LAYOUTS = {"full_bleed", "overlay", "center_focus", "hero", "cover"}
# Layouts that explicitly want a side-by-side hero image.
_SPLIT_LAYOUTS = {"split_50_50", "image_left_text_right", "image_right_text_left", "hero_split"}


def _resolve_image_position(
    image_intent: ImageIntent,
    layout: str,
    slide_intent: str,
) -> str:
    """Decide background / foreground / inline from intent + layout.

    Layout wins over intent (a designer-chosen full_bleed should always
    render full-bleed even if the slide is technically a "team" intent).
    """
    layout_key = (layout or "").lower()
    if layout_key in _FULL_BLEED_LAYOUTS:
        return "background"
    if layout_key in _SPLIT_LAYOUTS:
        return "foreground"
    # Title / closing / ask / vision are visually anchored — always
    # background even with non-hero layouts because they read as a
    # cover.
    if (slide_intent or "").lower() in {"title", "cover", "closing", "ask", "vision"}:
        return "background"
    return _INTENT_POSITION.get(image_intent, "foreground")


def _brand_style_suffix(tokens: ResolvedDesignTokens) -> str:
    """Generate a consistent style suffix from the design tokens so every
    image in the deck reads as one visual system."""
    p = tokens.palette
    density_mood = {
        "compact":     "crisp, editorial, information-dense",
        "comfortable": "balanced editorial illustration",
        "spacious":    "minimalist, airy, confident",
    }[tokens.density]
    dominant = f"dominant palette {p.primary} and {p.accent} on {p.background}"
    avoid = catalog_anti_pattern_prompt_suffix(tokens.to_dict())
    return (
        f"{density_mood}, {dominant}, 16:9 wide composition, "
        "subtle depth, high production value, no text overlay, "
        f"leaves breathing room for overlaid headlines, {avoid}"
    )


def _enhance_prompt(
    raw_prompt: str,
    slide_intent: str,
    tokens: ResolvedDesignTokens,
    *,
    slide_layout: str = "",
    slide_headline: str = "",
    industry: str = "",
    deck_purpose: str = "",
) -> tuple[str, str]:
    """Build the final image prompt using the v12.1 image_prompt_library.

    Returns `(prompt, archetype_name)`. The archetype name is kept for
    diagnostic events so the UI can show which template governed each
    slide's image. Library tolerates missing raw_prompt / headline and
    always produces a coherent, palette-consistent prompt.
    """
    if not settings.ENABLE_IMAGE_PROMPT_ENRICHMENT:
        prompt = raw_prompt or slide_headline or slide_intent or "presentation visual"
        return prompt[:1200], "disabled"
    prompt, archetype = build_image_prompt(
        intent=slide_intent,
        layout=slide_layout,
        image_prompt=raw_prompt,
        headline=slide_headline,
        tokens=tokens,
        industry=industry,
        deck_purpose=deck_purpose,
    )
    avoid = catalog_anti_pattern_prompt_suffix(tokens.to_dict())
    if avoid and "ai-purple" not in prompt.lower():
        prompt = f"{prompt} Avoid: {avoid}."
    return prompt[:1200], archetype


def _pick_image_intent(slide_intent: str) -> ImageIntent:
    key = (slide_intent or "").lower()
    return _INTENT_TO_IMAGE.get(key, ImageIntent.CONTENT_ILLUSTRATION)


def _preferred_tier(image_intent: ImageIntent, mode: str) -> Optional[ImageModelTier]:
    # In standard mode, skip the expensive tier to keep deck-gen cheap.
    if mode != "premium":
        return None
    return _INTENT_TIER.get(image_intent)


def _should_generate(slide: GeneratedSlide) -> bool:
    """True if this slide's visual decision says 'image' AND we have a
    prompt to work with."""
    rd = slide.render_decision or {}
    if (rd.get("modality") or "").lower() != "image":
        return False
    # Must have SOME prompt. Even a weak writer prompt is enough; we
    # enhance it with deck-level style.
    return True


def _job_for(slide: GeneratedSlide, tokens: ResolvedDesignTokens, mode: str) -> ImageJob:
    image_intent = _pick_image_intent(slide.intent)
    prompt, archetype = _enhance_prompt(
        slide.image_prompt or "",
        slide.intent or "",
        tokens,
        slide_layout=slide.layout or "",
        slide_headline=slide.headline or "",
        industry=getattr(slide, "industry", "") or "",
        deck_purpose=getattr(slide, "purpose", "") or "",
    )
    position = _resolve_image_position(image_intent, slide.layout or "", slide.intent or "")
    job = ImageJob(
        slide_index=slide.index,
        slide_id=getattr(slide, "id", None) or f"slide-{slide.index}",
        prompt=prompt,
        intent=image_intent,
        preferred_tier=_preferred_tier(image_intent, mode),
        position=position,
        slide_layout=slide.layout or "",
        slide_intent=slide.intent or "",
    )
    # Carry archetype for diagnostics via the downstream emit()
    setattr(job, "archetype", archetype)
    return job


async def _upload_to_blob(image_bytes: bytes, slide_id: str, project_id: str) -> str:
    """Persist generated image bytes and return a URL the sandbox can load.

    Founder Plan-v5 (Apr 2026): primary path is the *local* image store
    (`app/services/storage/local_image_store.py`). We write bytes to
    `server4/uploads/slide_images/{project_id}/{slide_id}.png` and
    return a same-origin absolute URL served by `app/routers/v4_images.py`.
    This eliminates the broken-image bug caused by Azure SAS expiry,
    Blob CORS, and missing dev credentials.

    Azure Blob upload is preserved as a best-effort backup — if the
    deployment has `BLOB_STORAGE_CONNECTION_STRING` configured we still
    push a copy for durability, but we never depend on its URL for
    rendering. The local URL is what gets persisted into
    `db.slides[i].image_url` and into `compiled_slides[i].kit_jsx
    .props_json.imageUrl`.
    """
    # Function name is preserved for backward compatibility with the
    # rest of `image_generator.py`. The semantics changed; the name did
    # not, on purpose, so the diff stays surgical.
    from app.services.storage.local_image_store import store_image

    try:
        local_url = store_image(
            project_id=project_id,
            slide_id=slide_id,
            image_bytes=image_bytes,
        )
    except Exception as e:
        logger.warning(
            "local_image_store_failed_using_data_url",
            slide_id=slide_id,
            project_id=project_id,
            error=str(e),
        )
        import base64
        b64 = base64.b64encode(image_bytes).decode("ascii")
        return f"data:image/png;base64,{b64}"

    # Best-effort Azure Blob backup. Never blocks the primary path.
    try:
        from app.services.storage.blob_service import BlobStorageService
        svc = BlobStorageService.get_instance()
        await svc.upload_file(
            file_data=image_bytes,
            filename=f"{slide_id}.png",
            content_type="image/png",
            folder=f"slide-images/{project_id}",
        )
    except Exception as e:
        # Expected when blob is not configured (local dev). Don't log
        # at warning level — that's just noise. Debug only.
        logger.debug(
            "blob_backup_skipped",
            slide_id=slide_id,
            error=str(e),
        )

    return local_url


async def _run_one(
    *,
    job: ImageJob,
    router: ImagePipelineRouter,
    tokens: ResolvedDesignTokens,
    project_id: str,
    mode: str,
    emit: Optional[ProgressEmit],
) -> tuple[int, Optional[str], Optional[str]]:
    """Run a single image generation. Returns (slide_index, url_or_none,
    tier_or_none). Publishes per-slide events via `emit`."""
    t0 = time.perf_counter()
    if emit:
        await emit("slide_image_started", {
            "index": job.slide_index,
            "intent": job.intent.value,
            "preferred_tier": job.preferred_tier.value if job.preferred_tier else None,
            "archetype": getattr(job, "archetype", None),
            "position": job.position,
        })

    ctx = PromptContext(
        custom_prompt=job.prompt,
        primary_color=tokens.palette.primary,
        accent_color=tokens.palette.accent,
        variant="dark" if tokens.palette.background.lower() in {"#0b0d12", "#000", "#000000"} else "light",
    )
    try:
        skip_tiers = [ImageModelTier.AZURE_FLUX] if mode != "premium" else None
        result: Optional[ImageGenerationResult] = await router.generate(
            ctx, preferred_tier=job.preferred_tier, skip_tiers=skip_tiers
        )
    except Exception as e:
        logger.warning("image_gen_unexpected_error",
                       index=job.slide_index, error=str(e))
        result = None

    if not result:
        # ── Free stock photo fallback ──────────────────────────────
        # When AI generation fails (rate limits, timeouts, all tiers
        # exhausted), try Unsplash/Pexels/Pixabay for real photography.
        # This is free, fast (<2s), and produces better results than
        # gradient placeholders for hero/background images.
        try:
            from app.services.v4.free_photo_search import get_best_free_photo
            stock = await get_best_free_photo(job.prompt[:200])
            if stock and stock.url:
                # Upload the stock photo to our blob storage for stability
                async with httpx.AsyncClient(timeout=15.0) as client:
                    img_resp = await client.get(stock.url)
                    if img_resp.status_code == 200:
                        url = await _upload_to_blob(img_resp.content, job.slide_id, project_id)
                        if url:
                            logger.info("free_stock_photo_used",
                                       index=job.slide_index, source=stock.source)
                            if emit:
                                await emit("slide_image_ready", {
                                    "index": job.slide_index,
                                    "url": url,
                                    "tier": "free_stock",
                                    "provider": stock.source,
                                    "latency_ms": int((time.perf_counter() - t0) * 1000),
                                    "fallback_count": 0,
                                    "position": job.position,
                                    "image_intent": job.intent.value,
                                })
                            return job.slide_index, url, "free_stock"
        except Exception as stock_err:
            logger.debug("free_stock_fallback_failed", error=str(stock_err)[:100])

        if emit:
            await emit("slide_image_failed", {
                "index": job.slide_index,
                "reason": "all_tiers_exhausted",
                "duration_ms": int((time.perf_counter() - t0) * 1000),
            })
        return job.slide_index, None, None

    try:
        url = await _upload_to_blob(result.image_bytes, job.slide_id, project_id)
    except Exception as e:
        logger.warning("image_upload_failed", index=job.slide_index, error=str(e))
        return job.slide_index, None, result.tier.value

    # Persist image URL to MongoDB so reloads after generation still
    # show the image. The Redis `slide_image_ready` event below patches
    # the live in-memory deck for connected clients.
    # NOTE: we use upsert=True because Stage 4.7 may complete BEFORE the
    # router has finished its slide_docs insertion. Without upsert, the
    # update would silently match zero documents and the URL would be
    # lost. The router uses `$setOnInsert` for image fields, so this
    # row is preserved when the writer later upserts the slide content.
    try:
        from app.database import get_db  # local import to avoid cycles
        db = get_db()
        # Match on either schema key — V4 inserts both, but if the image
        # stage races ahead of the router's slide upsert (rare, but the
        # `$setOnInsert` block here is intended to handle exactly that),
        # we want to be certain we don't accidentally orphan a doc.
        await db.slides.update_one(
            {
                "$or": [
                    {"presentation_id": project_id, "index": job.slide_index},
                    {"project_id": project_id, "index": job.slide_index},
                ],
            },
            {
                "$set": {
                    "image_url": url,
                    "image_source": result.tier.value,
                    "image_position": job.position,
                    "image_intent": job.intent.value,
                    "presentation_id": project_id,
                    "project_id": project_id,
                    "index": job.slide_index,
                },
                "$setOnInsert": {
                    "_id": str(ObjectId()),
                },
            },
            upsert=True,
        )
    except Exception as e:
        logger.warning("image_db_persist_failed",
                       index=job.slide_index, error=str(e))

    if emit:
        await emit("slide_image_ready", {
            "index": job.slide_index,
            "url": url,
            "tier": result.tier.value,
            "provider": result.provider,
            "latency_ms": result.latency_ms,
            "fallback_count": result.fallback_count,
            "position": job.position,
            "image_intent": job.intent.value,
        })
    return job.slide_index, url, result.tier.value


async def generate_images(
    *,
    slides: list[GeneratedSlide],
    tokens: ResolvedDesignTokens,
    project_id: str,
    mode: str = "standard",
    concurrency: int = 4,
    emit: Optional[ProgressEmit] = None,
) -> list[GeneratedSlide]:
    """Generate images for every image-modality slide in parallel.

    Mutates slides in place (sets `slide.imageUrl` and `slide.image_source`)
    and returns the same list for chaining convenience.

    NON-BLOCKING INTENT: callers should treat this as fire-and-await-later.
    The pipeline can return to the user before this resolves; per-slide
    completions stream via Redis pub/sub through `emit`.
    """
    jobs = [_job_for(s, tokens, mode) for s in slides if _should_generate(s)]
    if not jobs:
        if emit:
            await emit("image_stage_skipped", {"reason": "no_image_modality_slides"})
        return slides

    if emit:
        await emit("image_stage_started", {
            "n_jobs": len(jobs),
            "concurrency": concurrency,
        })

    router = ImagePipelineRouter()
    sem = asyncio.Semaphore(concurrency)

    async def _bounded(job: ImageJob) -> tuple[int, Optional[str], Optional[str]]:
        async with sem:
            return await _run_one(
                job=job, router=router, tokens=tokens,
                project_id=project_id, mode=mode, emit=emit,
            )

    t0 = time.perf_counter()
    results = await asyncio.gather(*[_bounded(j) for j in jobs], return_exceptions=True)

    idx_to_slide = {s.index: s for s in slides}
    idx_to_job = {j.slide_index: j for j in jobs}
    n_ok = 0
    for res in results:
        if isinstance(res, Exception):
            logger.warning("image_job_raised", error=str(res))
            continue
        index, url, tier = res
        slide = idx_to_slide.get(index)
        job = idx_to_job.get(index)
        if slide and url:
            # v12.1 — write to the declared snake_case dataclass fields
            # so `asdict()` captures them in artifacts. We also mirror
            # to the legacy camelCase attrs that downstream consumers
            # (slide_compiler, generation_v4, content_pipeline) still
            # read, so the transition is non-breaking.
            slide.image_url = url
            slide.image_source = tier
            setattr(slide, "imageUrl", url)
            setattr(slide, "image_source", tier)
            if job:
                slide.image_position = job.position
                slide.image_intent = job.intent.value
                setattr(slide, "image_position", job.position)
                setattr(slide, "image_intent", job.intent.value)
            n_ok += 1

    if emit:
        await emit("image_stage_complete", {
            "n_total": len(jobs),
            "n_success": n_ok,
            "duration_ms": int((time.perf_counter() - t0) * 1000),
        })
    return slides
