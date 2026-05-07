"""
V3 Generation API routes — Unified pipeline REST endpoints.

Prefix: /api/v3
Endpoints:
  POST /generate                    — Start V3 generation (standard or premium)
  GET  /deck/{deck_id}/status       — Poll generation status
  GET  /deck/{deck_id}/result       — Get full generation result
  GET  /deck/{deck_id}/evidence     — Get evidence report (premium only)
  POST /deck/{deck_id}/cancel       — Cancel in-progress generation
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3", tags=["v3-generation"])


# ═══════════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════


class V3GenerateRequest(BaseModel):
    """V3 generation request body."""

    topic: str
    description: str = ""
    audience: str = "investors"
    purpose: str = "pitch"
    mode: str = Field(default="standard", pattern="^(standard|premium)$")
    slide_count: int = Field(default=10, ge=3, le=30)
    writing_style: str = "yc_crisp"
    theme_id: Optional[str] = None
    custom_colors: Optional[dict] = None
    language: str = "en"
    generate_notes: bool = True
    target_formats: list[str] = Field(default_factory=lambda: ["revealjs"])
    company_name: Optional[str] = None
    outline: Optional[dict] = None
    user_id: str = ""


class V3GenerateResponse(BaseModel):
    """Response from POST /api/v3/generate."""

    deck_id: str
    task_id: str
    mode: str
    status: str
    message: str


class V3StatusResponse(BaseModel):
    """Response from GET /api/v3/deck/{deck_id}/status."""

    deck_id: str
    status: str
    mode: str = "standard"
    topic: str = ""
    total_slides: int = 0
    total_slides_generated: int = 0
    quality_score: float = 0.0
    total_time_ms: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    errors: list = Field(default_factory=list)


class V3EvidenceResponse(BaseModel):
    """Response from GET /api/v3/deck/{deck_id}/evidence."""

    deck_id: str
    evidence_report: dict
    coherence_score: float = 0.0


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════


@router.post("/generate", response_model=V3GenerateResponse)
async def start_v3_generation(request: V3GenerateRequest):
    """
    Start a V3 unified generation.

    Tries to dispatch a Celery task if a worker is reachable.
    Otherwise falls back to running the pipeline inline as a
    background ``asyncio.Task`` so the endpoint returns immediately.
    """
    import asyncio

    deck_id = str(uuid.uuid4())
    request_dict = request.model_dump()

    # ── Decide execution mode ─────────────────────────────────
    # In development (or when CELERY_WORKERS_ENABLED is not set), run the
    # pipeline inline as an asyncio background task.  In production with
    # workers, dispatch to Celery.
    use_celery = settings.ENVIRONMENT == "production"
    task_id = f"inline-{deck_id}"

    if use_celery:
        try:
            from app.tasks.unified_tasks import generate_unified_deck

            queue = "content-fast" if request.mode == "standard" else "content-premium"
            time_limit = 120 if request.mode == "standard" else 600

            task = generate_unified_deck.apply_async(
                args=[deck_id, request_dict],
                queue=queue,
                time_limit=time_limit,
                soft_time_limit=max(time_limit - 30, 30),
            )
            task_id = task.id
            logger.info(
                "v3_generation_dispatched",
                deck_id=deck_id,
                task_id=task_id,
                mode=request.mode,
                queue=queue,
            )
        except Exception as exc:
            logger.warning("Celery dispatch failed, falling back to inline: %s", exc)
            use_celery = False

    if not use_celery:
        # ── Run in a background thread with its own event loop ─
        # The pipeline may contain blocking calls deep inside LLM
        # client libraries.  Running in a thread prevents the main
        # uvicorn event loop from freezing.
        import threading

        def _run_in_thread():
            import asyncio as _aio
            loop = _aio.new_event_loop()
            _aio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    _run_inline_generation(deck_id, request_dict)
                )
            finally:
                loop.close()

        t = threading.Thread(
            target=_run_in_thread, daemon=True, name=f"gen-{deck_id[:8]}"
        )
        t.start()
        logger.info(
            "v3_generation_inline",
            deck_id=deck_id,
            mode=request.mode,
        )

    return V3GenerateResponse(
        deck_id=deck_id,
        task_id=task_id,
        mode=request.mode,
        status="queued",
        message=f"{request.mode.title()} generation started"
        + (" (inline)" if not use_celery else ""),
    )


async def _run_inline_generation(deck_id: str, request_dict: dict):
    """Run the unified pipeline in a background thread (own event loop).

    Creates its own MongoDB and Redis connections since motor/aioredis
    clients cannot be shared across event loops.
    """
    import time as _time
    from datetime import datetime, timezone
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.services.unified_pipeline import (
        UnifiedGenerationRequest,
        UnifiedPipelineService,
    )

    mode = request_dict.get("mode", "standard")
    start = _time.time()

    # Own connections for this thread's event loop
    mongo_client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = mongo_client[settings.MONGODB_DB_NAME]

    # Mark as running
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

    # Optional Redis event emitter
    emitter = None
    redis_client = None
    try:
        from app.mcp.brain_mcp.research.content_events import ContentEventEmitter

        redis_client = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
        emitter = ContentEventEmitter(deck_id, redis_client)
        emitter._channel = f"deck:{deck_id}:v3:events"
        emitter._log_key = f"deck:{deck_id}:v3:events:log"
    except Exception:
        pass

    try:
        request_obj = UnifiedGenerationRequest(**request_dict)
        pipeline = UnifiedPipelineService(db)

        result = await pipeline.generate(
            request=request_obj,
            deck_id=deck_id,
            event_emitter=emitter,
        )

        result_dict = result.model_dump()
        result_dict["completed_at"] = datetime.now(timezone.utc).isoformat()

        await db.deck_runs_v3.update_one(
            {"deck_id": deck_id},
            {"$set": {
                **result_dict,
                "status": "completed" if result.success else "failed",
            }},
            upsert=True,
        )
        logger.info(
            "v3_inline_completed",
            deck_id=deck_id,
            slides=len(result.slides),
            quality=result.quality_score,
            time_ms=_time.time() - start,
        )

        # ── Post-generation: compile reveal.js HTML ──────────
        try:
            from app.services.v3_editor_bridge import transform_v3_result_to_dsl
            from app.services.slides_new.renderers.reveal_compiler import (
                RevealCompiler,
            )

            run_doc = await db.deck_runs_v3.find_one({"deck_id": deck_id})
            if run_doc:
                dsl = transform_v3_result_to_dsl(run_doc)
                compiler = RevealCompiler()
                render_output = compiler.render_presentation(dsl)
                if render_output.success:
                    await db.deck_runs_v3.update_one(
                        {"deck_id": deck_id},
                        {"$set": {"reveal_html": render_output.html}},
                    )
                    logger.info(
                        "v3_reveal_compiled",
                        deck_id=deck_id,
                        slide_count=render_output.slide_count,
                    )
        except Exception as compile_err:
            logger.warning("reveal compile failed (non-fatal): %s", compile_err)

    except Exception as e:
        logger.exception("v3_inline_failed: %s", e)
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
    finally:
        if redis_client:
            try:
                await redis_client.aclose()
            except Exception:
                pass
        mongo_client.close()


@router.get("/deck/{deck_id}/status", response_model=V3StatusResponse)
async def get_v3_status(deck_id: str):
    """Poll V3 generation status from MongoDB."""
    db = get_db()
    run = await db.deck_runs_v3.find_one({"deck_id": deck_id})

    if not run:
        raise HTTPException(status_code=404, detail="Deck run not found")

    return V3StatusResponse(
        deck_id=deck_id,
        status=run.get("status", "unknown"),
        mode=run.get("mode", "standard"),
        topic=run.get("topic", ""),
        total_slides=len(run.get("slides", [])),
        total_slides_generated=len(run.get("slides", [])),
        quality_score=run.get("quality_score", 0.0),
        total_time_ms=run.get("total_time_ms", 0.0),
        started_at=run.get("started_at"),
        completed_at=run.get("completed_at"),
        errors=run.get("errors", []),
    )


@router.get("/deck/{deck_id}/result")
async def get_v3_result(deck_id: str):
    """Get the full V3 generation result from MongoDB."""
    db = get_db()
    run = await db.deck_runs_v3.find_one({"deck_id": deck_id})

    if not run:
        raise HTTPException(status_code=404, detail="Deck run not found")

    status = run.get("status", "unknown")
    if status in ("running", "queued"):
        raise HTTPException(
            status_code=202,
            detail="Generation still in progress",
        )

    # Remove MongoDB internal fields
    run.pop("_id", None)
    return run


@router.get("/deck/{deck_id}/preview")
async def get_v3_preview(deck_id: str):
    """Compile the V3 result into a self-contained reveal.js HTML document.

    If a cached ``reveal_html`` field exists in the run document it is
    returned immediately, otherwise the slides are compiled on-the-fly.
    """
    from fastapi.responses import HTMLResponse
    from app.services.v3_editor_bridge import transform_v3_result_to_dsl
    from app.services.slides_new.renderers.reveal_compiler import RevealCompiler

    db = get_db()
    run = await db.deck_runs_v3.find_one({"deck_id": deck_id})

    if not run:
        raise HTTPException(status_code=404, detail="Deck run not found")

    status = run.get("status", "unknown")
    if status != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot preview: generation status is '{status}'",
        )

    # Return cached HTML if available
    cached_html = run.get("reveal_html")
    if cached_html:
        return HTMLResponse(content=cached_html, media_type="text/html")

    # Compile on-the-fly
    try:
        dsl = transform_v3_result_to_dsl(run)
        compiler = RevealCompiler()
        output = compiler.render_presentation(dsl)

        if not output.success:
            raise HTTPException(
                status_code=500,
                detail=f"Reveal.js compilation failed: {output.error}",
            )

        # Cache for next request
        await db.deck_runs_v3.update_one(
            {"deck_id": deck_id},
            {"$set": {"reveal_html": output.html}},
        )

        return HTMLResponse(content=output.html, media_type="text/html")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("preview_compile_failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deck/{deck_id}/evidence", response_model=V3EvidenceResponse)
async def get_v3_evidence(deck_id: str):
    """Get evidence report for a premium deck. Returns 404 for standard decks."""
    db = get_db()
    run = await db.deck_runs_v3.find_one({"deck_id": deck_id})

    if not run:
        raise HTTPException(status_code=404, detail="Deck run not found")

    mode = run.get("mode", "standard")
    if mode != "premium":
        raise HTTPException(
            status_code=404,
            detail="Evidence report only available for premium mode decks",
        )

    evidence_report = run.get("evidence_report")
    if not evidence_report:
        raise HTTPException(
            status_code=404,
            detail="Evidence report not yet generated",
        )

    return V3EvidenceResponse(
        deck_id=deck_id,
        evidence_report=evidence_report,
        coherence_score=run.get("coherence_score", 0.0),
    )


@router.post("/deck/{deck_id}/cancel")
async def cancel_v3_generation(deck_id: str):
    """
    Cancel an in-progress V3 generation.

    Sets a Redis key that the Celery task checks between phases.
    """
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
        await redis_client.set(
            f"deck:{deck_id}:cancel", "1", ex=600
        )
        await redis_client.aclose()
    except Exception as e:
        logger.warning("Redis cancel set failed: %s", e)

    # Also update MongoDB status
    db = get_db()
    await db.deck_runs_v3.update_one(
        {"deck_id": deck_id, "status": "running"},
        {"$set": {"status": "cancelling"}},
    )

    return {"deck_id": deck_id, "status": "cancelling", "message": "Cancel signal sent"}


# ═══════════════════════════════════════════════════════════════════════
# V3 → EDITOR BRIDGE
# ═══════════════════════════════════════════════════════════════════════


class V3SessionResponse(BaseModel):
    """Response from POST /api/v3/deck/{deck_id}/session."""

    deck_id: str
    presentation_id: str
    session_active: bool
    slide_count: int
    message: str


@router.post("/deck/{deck_id}/session", response_model=V3SessionResponse)
async def create_editor_session_from_v3(deck_id: str):
    """
    Create an editor session from a completed V3 generation.

    Transforms the V3 result into a PresentationDSL and opens an editor session.
    The ``presentation_id`` returned is the key for all subsequent editor operations.

    Requires V3 generation to be completed (status == 'completed').
    """
    from app.services.v3_editor_bridge import transform_v3_result_to_dsl
    from app.api.routes.editor_routes import _sessions, _EditorSession

    db = get_db()
    run = await db.deck_runs_v3.find_one({"deck_id": deck_id})

    if not run:
        raise HTTPException(status_code=404, detail="Deck run not found")

    status = run.get("status", "unknown")
    if status != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot create session: generation status is '{status}' (expected 'completed')",
        )

    # Transform V3 result → PresentationDSL
    dsl = transform_v3_result_to_dsl(run)
    presentation_id = dsl.presentation.id

    # Open editor session (reuse if already open)
    if presentation_id not in _sessions:
        session = _EditorSession(dsl)
        session.versions.create_snapshot(dsl, description="v3_bridge_opened")
        _sessions[presentation_id] = session
        logger.info("Editor session created via V3 bridge: %s", presentation_id)
    else:
        logger.info("Editor session already active: %s", presentation_id)

    return V3SessionResponse(
        deck_id=deck_id,
        presentation_id=presentation_id,
        session_active=True,
        slide_count=len(dsl.slides),
        message="Editor session ready",
    )
