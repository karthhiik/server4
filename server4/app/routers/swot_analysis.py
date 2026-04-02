"""SWOT Analysis routes and endpoints."""

from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.models.swot_models import (
    ExportFormat,
    HealthResponse,
    SWOTAnalysisCreate,
    SWOTAnalysisResponse,
    SWOTItemCreate,
    SWOTItemUpdate,
    SWOTScores,
)
from app.services.swot_analysis_service import SWOTAnalysisService

router = APIRouter(prefix="/api/swot-analysis", tags=["SWOT Analysis"])


def _doc_to_response(doc: dict) -> SWOTAnalysisResponse:
    """Convert MongoDB document to response model."""
    return SWOTAnalysisResponse(
        id=doc["_id"],
        business_plan_id=doc.get("business_plan_id"),
        title=doc.get("title"),
        strengths=doc.get("strengths", []),
        weaknesses=doc.get("weaknesses", []),
        opportunities=doc.get("opportunities", []),
        threats=doc.get("threats", []),
        generated_at=doc.get("generated_at", doc.get("created_at")),
        updated_at=doc.get("updated_at"),
    )


@router.get("/health", tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint (no auth required)."""
    return HealthResponse(
        status="ok",
        service="swot-analysis-service",
        version="1.0.0",
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_swot_analysis(
    body: SWOTAnalysisCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SWOTAnalysisResponse:
    """Generate SWOT analysis from business plan.

    Args:
        body: SWOT creation parameters (business_plan_id required)
        db: Database connection

    Returns:
        Generated SWOT analysis
    """
    if not body.business_plan_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="business_plan_id is required",
        )

    service = SWOTAnalysisService(db)

    try:
        swot_doc = await service.generate_swot_analysis(body.business_plan_id)
        return _doc_to_response(swot_doc)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{analysis_id}")
async def get_swot_analysis(
    analysis_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SWOTAnalysisResponse:
    """Retrieve SWOT analysis by ID.

    Args:
        analysis_id: ID of the SWOT analysis
        db: Database connection

    Returns:
        SWOT analysis document
    """
    service = SWOTAnalysisService(db)

    try:
        doc = await service.get_swot_analysis(analysis_id)
        return _doc_to_response(doc)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{analysis_id}/items", status_code=status.HTTP_201_CREATED)
async def add_swot_item(
    analysis_id: str,
    quadrant: str = Query(..., description="Quadrant: strengths, weaknesses, opportunities, or threats"),
    body: SWOTItemCreate = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Add a new item to a SWOT quadrant.

    Args:
        analysis_id: ID of the SWOT analysis
        quadrant: Target quadrant
        body: Item data
        db: Database connection

    Returns:
        Created item
    """
    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body is required",
        )

    service = SWOTAnalysisService(db)

    try:
        item = await service.add_swot_item(
            analysis_id, quadrant, body.model_dump(exclude_none=True)
        )
        return item
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch("/{analysis_id}/items/{item_id}")
async def update_swot_item(
    analysis_id: str,
    item_id: str,
    body: SWOTItemUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Update a SWOT item.

    Args:
        analysis_id: ID of the SWOT analysis
        item_id: ID of the item to update
        body: Updated item data
        db: Database connection

    Returns:
        Updated item
    """
    service = SWOTAnalysisService(db)

    try:
        item = await service.update_swot_item(
            analysis_id, item_id, body.model_dump(exclude_none=True)
        )
        if "error" in item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=item["error"],
            )
        return item
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{analysis_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_swot_item(
    analysis_id: str,
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Delete a SWOT item.

    Args:
        analysis_id: ID of the SWOT analysis
        item_id: ID of the item to delete
        db: Database connection
    """
    service = SWOTAnalysisService(db)

    try:
        success = await service.delete_swot_item(analysis_id, item_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {item_id} not found",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{analysis_id}/scores")
async def get_swot_scores(
    analysis_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Get calculated SWOT scores and metrics.

    Args:
        analysis_id: ID of the SWOT analysis
        db: Database connection

    Returns:
        Calculated scores (averages, ratios, health)
    """
    service = SWOTAnalysisService(db)

    try:
        scores = await service.calculate_swot_scores(analysis_id)
        return scores
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{analysis_id}/recommendations")
async def get_swot_recommendations(
    analysis_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list:
    """Generate strategic recommendations from SWOT.

    Args:
        analysis_id: ID of the SWOT analysis
        db: Database connection

    Returns:
        List of strategic recommendations (SO, ST, WO, WT strategies)
    """
    service = SWOTAnalysisService(db)

    try:
        recommendations = await service.generate_recommendations(analysis_id)
        return recommendations
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{analysis_id}/export")
async def export_swot_analysis(
    analysis_id: str,
    format: str = Query(..., description="Export format: json, markdown, pdf, or png"),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Export SWOT analysis in specified format.

    Args:
        analysis_id: ID of the SWOT analysis
        format: Export format (json, markdown, pdf, png)
        db: Database connection

    Returns:
        Exported content
    """
    service = SWOTAnalysisService(db)

    try:
        if format not in [f.value for f in ExportFormat]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format. Must be one of: {[f.value for f in ExportFormat]}",
            )

        content = await service.export_swot_analysis(analysis_id, format)
        return {
            "format": format,
            "content": content,
            "analysis_id": analysis_id,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
