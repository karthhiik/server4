"""AI generation endpoints — trigger presentation generation pipeline."""

import asyncio
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.dependencies import check_generation_rate_limit, optional_auth
from app.models.presentation import (
    GenerationInput,
    GenerationState,
    TemplateGenerationInput,
)
from app.services.orchestrator.orchestrator import PresentationOrchestrator
from app.services.orchestrator.progress_tracker import progress_tracker

router = APIRouter(prefix="/api/generate", tags=["Generation"])


async def _run_generation(
    orchestrator: PresentationOrchestrator,
    project_id: str,
    input_data: GenerationInput,
    user_id: str,
):
    """Background task for AI generation."""
    try:
        await orchestrator.generate_presentation(project_id, input_data, user_id)
    except Exception:
        pass  # Error already handled by state machine


async def _run_template_generation(
    orchestrator: PresentationOrchestrator,
    project_id: str,
    input_data: TemplateGenerationInput,
    user_id: str,
):
    """Background task for template generation."""
    try:
        await orchestrator.generate_from_template(project_id, input_data, user_id)
    except Exception:
        pass


@router.post("/ai")
async def generate_ai_presentation(
    body: GenerationInput,
    background_tasks: BackgroundTasks,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """
    Trigger AI presentation generation.
    Returns immediately with project_id. Track progress via WebSocket.
    """
    # Fallback user_id for unauthenticated requests (dev/testing only)
    user_id = user["user_id"] if user else "dev-test-user"
    user_role = user.get("role", "guest") if user else "guest"
    is_premium = user_role == "premium"

    # Enforce slide count limits
    max_slides = 50 if body.mode.value == "premium" or is_premium else 15
    if body.slide_count > max_slides:
        raise HTTPException(
            status_code=400,
            detail=f"Max {max_slides} slides for {body.mode.value} mode",
        )

    # Create presentation record
    project_id = str(ObjectId())
    await db.presentations.insert_one(
        {
            "_id": project_id,
            "user_id": user_id,
            "title": body.topic,
            "description": body.description,
            "mode": body.mode.value,
            "created_from": "ai",
            "theme_id": body.theme_id,
            "slide_count": 0,
            "generation_state": GenerationState.IDLE.value,
            "generation_progress": 0,
            "generation_message": "Starting...",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )

    # Start generation in background
    orchestrator = PresentationOrchestrator(db, progress_tracker)
    background_tasks.add_task(_run_generation, orchestrator, project_id, body, user_id)

    return {
        "project_id": project_id,
        "status": "started",
        "message": "Generation started. Connect to WebSocket for progress.",
        "ws_url": f"/ws/generation/{project_id}",
    }


@router.post("/template")
async def generate_from_template(
    body: TemplateGenerationInput,
    background_tasks: BackgroundTasks,
    user: dict = Depends(check_generation_rate_limit),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """
    Trigger template-based generation.
    Fills template placeholders with AI + user content.
    """
    # Verify template exists
    template = await db.templates.find_one({"_id": body.template_id})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    project_id = str(ObjectId())
    await db.presentations.insert_one(
        {
            "_id": project_id,
            "user_id": user["user_id"],
            "title": template["name"],
            "description": template.get("description"),
            "mode": body.mode.value,
            "created_from": "template",
            "template_id": body.template_id,
            "theme_id": body.theme_id or template.get("default_theme"),
            "slide_count": 0,
            "generation_state": GenerationState.IDLE.value,
            "generation_progress": 0,
            "generation_message": "Starting...",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )

    orchestrator = PresentationOrchestrator(db, progress_tracker)
    background_tasks.add_task(
        _run_template_generation, orchestrator, project_id, body, user["user_id"]
    )

    return {
        "project_id": project_id,
        "status": "started",
        "ws_url": f"/ws/generation/{project_id}",
    }


@router.get("/status/{project_id}")
async def get_generation_status(
    project_id: str,
    user: dict = Depends(check_generation_rate_limit),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Poll generation status (alternative to WebSocket)."""
    doc = await db.presentations.find_one(
        {
            "_id": project_id,
            "user_id": user["user_id"],
        }
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Presentation not found")

    return {
        "project_id": project_id,
        "state": doc.get("generation_state", "idle"),
        "progress": doc.get("generation_progress", 0),
        "message": doc.get("generation_message", ""),
        "error": doc.get("generation_error"),
    }
