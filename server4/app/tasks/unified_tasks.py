"""
V3 Unified Celery tasks — background processing for Standard and Premium modes.

Standard tasks route to ``content-fast`` queue (short timeout, high concurrency).
Premium tasks route to ``content-premium`` queue (long timeout, low concurrency).

Queue routing is done at dispatch time via ``task.apply_async(queue=...)``.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_event_loop():
    """Get or create an event loop for async code in Celery workers."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


@celery_app.task(bind=True, max_retries=1, time_limit=600, soft_time_limit=540)
def generate_unified_deck(self, deck_id: str, request_dict: dict):
    """
    V3 unified deck generation task.

    Dispatched to either ``content-fast`` or ``content-premium`` queue.
    Wraps the async UnifiedPipelineService.generate() call.

    Args:
        deck_id: Unique deck run identifier
        request_dict: Serialised UnifiedGenerationRequest
    """
    loop = _get_event_loop()
    return loop.run_until_complete(
        _generate_unified_async(self, deck_id, request_dict)
    )


async def _generate_unified_async(task, deck_id: str, request_dict: dict):
    """Async implementation of V3 unified generation."""
    import redis.asyncio as aioredis
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.config import settings
    from app.services.unified_pipeline import (
        UnifiedGenerationRequest,
        UnifiedPipelineService,
    )
    from app.mcp.brain_mcp.research.content_events import ContentEventEmitter

    start_time = time.time()
    mode = request_dict.get("mode", "standard")

    # ── Initialize connections ───────────────────────────────
    redis_client = None
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
    except Exception as e:
        logger.warning("Redis unavailable for V3 events: %s", e)

    mongo_client = None
    db = None
    try:
        mongo_client = AsyncIOMotorClient(settings.MONGODB_URI)
        db = mongo_client[settings.MONGODB_DB_NAME]
    except Exception as e:
        logger.warning("MongoDB unavailable: %s", e)

    # V3-specific event channel
    emitter = ContentEventEmitter(deck_id, redis_client)
    emitter._channel = f"deck:{deck_id}:v3:events"
    emitter._log_key = f"deck:{deck_id}:v3:events:log"

    # ── Mark run as started ──────────────────────────────────
    if db is not None:
        await db.deck_runs_v3.update_one(
            {"deck_id": deck_id},
            {
                "$set": {
                    "deck_id": deck_id,
                    "user_id": request_dict.get("user_id", ""),
                    "status": "running",
                    "mode": mode,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "topic": request_dict.get("topic", ""),
                    "audience": request_dict.get("audience", "investors"),
                }
            },
            upsert=True,
        )

    try:
        # ── Check for cancellation ───────────────────────────
        if redis_client:
            cancelled = await redis_client.get(f"deck:{deck_id}:cancel")
            if cancelled:
                logger.info("v3_task_cancelled_before_start", deck_id=deck_id)
                if db is not None:
                    await db.deck_runs_v3.update_one(
                        {"deck_id": deck_id},
                        {"$set": {"status": "cancelled"}},
                    )
                return {"deck_id": deck_id, "status": "cancelled"}

        # ── Build request and run pipeline ───────────────────
        request = UnifiedGenerationRequest(**request_dict)
        pipeline = UnifiedPipelineService(db)

        result = await pipeline.generate(
            request=request,
            deck_id=deck_id,
            event_emitter=emitter,
        )

        # ── Save result to MongoDB ───────────────────────────
        result_dict = result.model_dump()
        result_dict["completed_at"] = datetime.now(timezone.utc).isoformat()

        if db is not None:
            await db.deck_runs_v3.update_one(
                {"deck_id": deck_id},
                {"$set": {
                    **result_dict,
                    "status": "completed" if result.success else "failed",
                }},
                upsert=True,
            )

        # Update Celery state for polling
        task.update_state(
            state="SUCCESS" if result.success else "FAILURE",
            meta={
                "deck_id": deck_id,
                "mode": mode,
                "success": result.success,
                "total_slides": len(result.slides),
                "quality_score": result.quality_score,
                "total_time_ms": result.total_time_ms,
            },
        )

        return {
            "deck_id": deck_id,
            "status": "completed" if result.success else "failed",
            "mode": mode,
            "total_slides": len(result.slides),
            "quality_score": result.quality_score,
            "total_time_ms": result.total_time_ms,
        }

    except Exception as e:
        logger.exception("V3 generation failed: %s", e)
        if db is not None:
            await db.deck_runs_v3.update_one(
                {"deck_id": deck_id},
                {
                    "$set": {
                        "status": "failed",
                        "error": str(e),
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
                upsert=True,
            )
        raise
    finally:
        if redis_client:
            await redis_client.aclose()
        if mongo_client:
            mongo_client.close()
