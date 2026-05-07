"""
V2 Content Generation API — Evidence-based slide content.

Endpoints:
- POST /api/v2/deck/{deck_id}/generate-content — Start content generation
- GET  /api/v2/deck/{deck_id}/status — Get generation status
- GET  /api/v2/deck/{deck_id}/contracts — Get generated slide contracts
- GET  /api/v2/deck/{deck_id}/evidence — Get evidence packets
- POST /api/v2/deck/{deck_id}/regenerate-slide/{slide_id} — Retry one slide
- GET  /api/v2/styles — List available writing styles
- GET  /api/v2/providers/health — Provider health status
- GET  /api/v2/deck/{deck_id}/task-status/{task_id} — Celery task status
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["content-generation-v2"])


# ═══════════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════


class ContentGenerationRequest(BaseModel):
    """Request body for starting content generation."""

    topic: str
    description: str = ""
    audience: str = "investors"
    budget_mode: str = "lean"
    style: str = "yc_crisp"
    outline: dict = Field(default_factory=dict)


class ContentGenerationResponse(BaseModel):
    """Response after queuing a content generation task."""

    deck_id: str
    task_id: str
    status: str
    message: str


class SlideRegenerateRequest(BaseModel):
    """Request body for regenerating a single slide."""

    topic: str = ""
    kind: str = "problem"
    budget_mode: str = "lean"


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "/deck/{deck_id}/generate-content",
    response_model=ContentGenerationResponse,
)
async def start_content_generation(
    deck_id: str,
    request: ContentGenerationRequest,
):
    """Start background content generation via Celery."""
    from app.tasks.research_tasks import generate_deck_content

    if not request.topic:
        raise HTTPException(status_code=400, detail="topic is required")

    if not request.outline.get("slides"):
        raise HTTPException(
            status_code=400,
            detail="outline must contain a 'slides' array",
        )

    task = generate_deck_content.delay(
        deck_id=deck_id,
        outline=request.outline,
        budget_mode=request.budget_mode,
        style=request.style,
        topic=request.topic,
        audience=request.audience,
    )

    return ContentGenerationResponse(
        deck_id=deck_id,
        task_id=task.id,
        status="started",
        message="Content generation started. Connect to WebSocket for progress.",
    )


@router.get("/deck/{deck_id}/status")
async def get_generation_status(deck_id: str):
    """Get current generation status from MongoDB."""
    db = get_db()
    run = await db.deck_runs.find_one(
        {"deck_id": deck_id},
        {
            "_id": 0,
            "deck_id": 1,
            "status": 1,
            "topic": 1,
            "style": 1,
            "budget_mode": 1,
            "audience": 1,
            "total_slides": 1,
            "total_slides_generated": 1,
            "total_slides_failed": 1,
            "total_fact_packets": 1,
            "total_time_ms": 1,
            "started_at": 1,
            "completed_at": 1,
            "errors": 1,
        },
    )
    if not run:
        raise HTTPException(status_code=404, detail="Deck run not found")
    return run


@router.get("/deck/{deck_id}/contracts")
async def get_slide_contracts(deck_id: str):
    """Get generated slide content contracts."""
    db = get_db()
    run = await db.deck_runs.find_one(
        {"deck_id": deck_id}, {"_id": 0, "contracts": 1}
    )
    if not run:
        raise HTTPException(status_code=404, detail="Deck run not found")
    return {"deck_id": deck_id, "contracts": run.get("contracts", [])}


@router.get("/deck/{deck_id}/evidence")
async def get_evidence(deck_id: str):
    """Get evidence graph and fact packets."""
    db = get_db()
    run = await db.deck_runs.find_one(
        {"deck_id": deck_id},
        {
            "_id": 0,
            "evidence_graph": 1,
            "total_fact_packets": 1,
            "community_summaries": 1,
        },
    )
    if not run:
        raise HTTPException(status_code=404, detail="Deck run not found")
    return {
        "deck_id": deck_id,
        "evidence_graph": run.get("evidence_graph"),
        "total_fact_packets": run.get("total_fact_packets", 0),
        "community_summaries": run.get("community_summaries"),
    }


@router.post("/deck/{deck_id}/regenerate-slide/{slide_id}")
async def regenerate_slide(
    deck_id: str,
    slide_id: str,
    request: SlideRegenerateRequest,
):
    """Regenerate content for a single slide."""
    from app.tasks.research_tasks import research_slide_task

    task = research_slide_task.delay(
        slide_id=slide_id,
        slide_kind=request.kind,
        queries=[request.topic] if request.topic else [],
        budget_mode=request.budget_mode,
        topic=request.topic,
    )
    return {
        "deck_id": deck_id,
        "slide_id": slide_id,
        "task_id": task.id,
        "status": "started",
    }


@router.get("/deck/{deck_id}/task-status/{task_id}")
async def get_task_status(deck_id: str, task_id: str):
    """Get Celery task status for polling clients without WebSocket."""
    from app.tasks.celery_app import celery_app

    result = celery_app.AsyncResult(task_id)
    response = {
        "deck_id": deck_id,
        "task_id": task_id,
        "state": result.state,
    }

    if result.state == "PROGRESS":
        response["meta"] = result.info
    elif result.state == "SUCCESS":
        response["result"] = result.result
    elif result.state == "FAILURE":
        response["error"] = str(result.result) if result.result else "Unknown error"

    return response


@router.get("/styles")
async def list_styles():
    """List all available writing styles."""
    from app.mcp.brain_mcp.prompts.style_catalog import STYLE_CATALOG

    return {
        "styles": [
            {"id": s.style_id, "family": s.family, "tone": s.tone}
            for s in STYLE_CATALOG.values()
        ],
        "total": len(STYLE_CATALOG),
    }


@router.get("/providers/health")
async def get_provider_health():
    """Get health status of all research providers."""
    import redis.asyncio as aioredis
    from app.config import settings
    from app.mcp.brain_mcp.research.circuit_breaker import CircuitBreaker

    redis_client = None
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
        breaker = CircuitBreaker(redis_client)
        health = await breaker.get_all_health()
        return {
            "providers": {
                k: v.to_dict() if hasattr(v, "to_dict") else v
                for k, v in health.items()
            }
        }
    except Exception as e:
        logger.warning("Failed to get provider health: %s", e)
        return {"error": str(e), "providers": {}}
    finally:
        if redis_client:
            await redis_client.aclose()
