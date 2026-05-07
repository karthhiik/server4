"""
New Slide Generation API Routes
Exposes the new multi-agent slide generation system.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.database import get_db
from app.services.slides_new.orchestrator.pipeline import PipelineOrchestrator

router = APIRouter(prefix="/api/slides-new", tags=["Slide Generation (New)"])


class GeneratePresentationRequest(BaseModel):
    topic: str
    description: str
    purpose: str
    audience: str
    slide_count: Optional[int] = 10
    writing_style: Optional[str] = "general"
    company_name: Optional[str] = None
    preset: Optional[str] = "yc_pitch"


class GenerateWithFeedbackRequest(GeneratePresentationRequest):
    max_retries: Optional[int] = 2


@router.post("/generate")
async def generate_presentation(
    request: GeneratePresentationRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Generate a presentation using the new multi-agent pipeline.

    Pipeline: CEO -> Researcher -> Designer -> Assembler -> QA
    """
    orchestrator = PipelineOrchestrator(db)

    result = await orchestrator.generate_presentation(
        topic=request.topic,
        description=request.description,
        purpose=request.purpose,
        audience=request.audience,
        slide_count=request.slide_count,
        writing_style=request.writing_style,
        company_name=request.company_name,
    )

    if not result.get("success", False):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Generation failed"),
        )

    return result


@router.post("/generate-with-feedback")
async def generate_with_feedback(
    request: GenerateWithFeedbackRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Generate presentation with QA feedback loop.
    If QA fails, regenerates with feedback up to max_retries.
    """
    orchestrator = PipelineOrchestrator(db)

    result = await orchestrator.generate_with_feedback(
        topic=request.topic,
        description=request.description,
        purpose=request.purpose,
        audience=request.audience,
        slide_count=request.slide_count,
        writing_style=request.writing_style,
        company_name=request.company_name,
        max_retries=request.max_retries,
    )

    if not result.get("success", False):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Generation failed after retries"),
        )

    return result


@router.get("/health")
async def health_check():
    """Health check for new slide generation system"""
    return {
        "status": "healthy",
        "pipeline": "multi-agent",
        "agents": ["ceo", "researcher", "designer", "assembler", "qa"],
    }
