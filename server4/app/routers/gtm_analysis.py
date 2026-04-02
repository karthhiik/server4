"""GTM Analysis routes and endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.models.gtm_models import (
    ExportFormat,
    GTMAnalysisCreate,
    GTMAnalysisResponse,
    HealthResponse,
    MarketSegmentCreate,
    MarketSegmentUpdate,
    SalesChannelCreate,
    SalesChannelUpdate,
)
from app.services.gtm_service import GTMAnalysisService

router = APIRouter(prefix="/api/gtm-analysis", tags=["GTM Analysis"])


def _doc_to_response(doc: dict) -> GTMAnalysisResponse:
    """Convert MongoDB document to response model."""
    return GTMAnalysisResponse(
        id=doc["_id"],
        business_plan_id=doc.get("business_plan_id"),
        target_markets=doc.get("target_markets", []),
        sales_channels=doc.get("sales_channels", []),
        pricing_strategy=doc.get("pricing_strategy"),
        positioning_statement=doc.get("positioning_statement"),
        competitive_differentiation=doc.get("competitive_differentiation"),
        execution_timeline=doc.get("execution_timeline", []),
        success_metrics=doc.get("success_metrics"),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
    )


@router.get("/health", tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint (no auth required)."""
    return HealthResponse(
        status="ok",
        service="gtm-analysis-service",
        version="1.0.0",
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_gtm_analysis(
    body: GTMAnalysisCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> GTMAnalysisResponse:
    """Generate GTM analysis from business plan.

    Args:
        body: GTM creation parameters (business_plan_id required)
        db: Database connection

    Returns:
        Generated GTM analysis
    """
    if not body.business_plan_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="business_plan_id is required",
        )

    service = GTMAnalysisService(db)

    try:
        gtm_doc = await service.generate_gtm_analysis(body.business_plan_id)
        return _doc_to_response(gtm_doc)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{gtm_id}")
async def get_gtm_analysis(
    gtm_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> GTMAnalysisResponse:
    """Retrieve a GTM analysis by ID.

    Args:
        gtm_id: ID of the GTM analysis
        db: Database connection

    Returns:
        GTM analysis
    """
    service = GTMAnalysisService(db)

    try:
        gtm_doc = await service.get_gtm_analysis(gtm_id)
        return _doc_to_response(gtm_doc)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{gtm_id}/segments", status_code=status.HTTP_201_CREATED)
async def add_market_segment(
    gtm_id: str,
    body: MarketSegmentCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Add a market segment to GTM analysis.

    Args:
        gtm_id: ID of the GTM analysis
        body: Market segment data
        db: Database connection

    Returns:
        Created segment
    """
    service = GTMAnalysisService(db)

    try:
        segment = await service.add_market_segment(gtm_id, body.dict(exclude_none=True))
        return segment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.patch("/{gtm_id}/segments/{segment_id}")
async def update_market_segment(
    gtm_id: str,
    segment_id: str,
    body: MarketSegmentUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Update a market segment.

    Args:
        gtm_id: ID of the GTM analysis
        segment_id: ID of the segment
        body: Update data
        db: Database connection

    Returns:
        Updated segment
    """
    service = GTMAnalysisService(db)

    try:
        segment = await service.update_market_segment(
            gtm_id, segment_id, body.dict(exclude_none=True)
        )
        return segment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{gtm_id}/segments/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_market_segment(
    gtm_id: str,
    segment_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    """Delete a market segment.

    Args:
        gtm_id: ID of the GTM analysis
        segment_id: ID of the segment
        db: Database connection
    """
    service = GTMAnalysisService(db)

    try:
        deleted = await service.delete_market_segment(gtm_id, segment_id)
        if not deleted:
            raise ValueError(f"Segment {segment_id} not found")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{gtm_id}/channels", status_code=status.HTTP_201_CREATED)
async def add_sales_channel(
    gtm_id: str,
    body: SalesChannelCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Add a sales channel to GTM analysis.

    Args:
        gtm_id: ID of the GTM analysis
        body: Sales channel data
        db: Database connection

    Returns:
        Created channel
    """
    service = GTMAnalysisService(db)

    try:
        channel = await service.add_sales_channel(gtm_id, body.dict(exclude_none=True))
        return channel
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.patch("/{gtm_id}/channels/{channel_id}")
async def update_sales_channel(
    gtm_id: str,
    channel_id: str,
    body: SalesChannelUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Update a sales channel.

    Args:
        gtm_id: ID of the GTM analysis
        channel_id: ID of the channel
        body: Update data
        db: Database connection

    Returns:
        Updated channel
    """
    service = GTMAnalysisService(db)

    try:
        channel = await service.update_sales_channel(
            gtm_id, channel_id, body.dict(exclude_none=True)
        )
        return channel
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{gtm_id}/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sales_channel(
    gtm_id: str,
    channel_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    """Delete a sales channel.

    Args:
        gtm_id: ID of the GTM analysis
        channel_id: ID of the channel
        db: Database connection
    """
    service = GTMAnalysisService(db)

    try:
        deleted = await service.delete_sales_channel(gtm_id, channel_id)
        if not deleted:
            raise ValueError(f"Channel {channel_id} not found")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{gtm_id}/metrics")
async def get_gtm_metrics(
    gtm_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Calculate and retrieve GTM metrics.

    Args:
        gtm_id: ID of the GTM analysis
        db: Database connection

    Returns:
        Calculated metrics
    """
    service = GTMAnalysisService(db)

    try:
        metrics = await service.calculate_metrics(gtm_id)
        return metrics
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{gtm_id}/unit-economics")
async def get_unit_economics(
    gtm_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Get unit economics for GTM strategy.

    Args:
        gtm_id: ID of the GTM analysis
        db: Database connection

    Returns:
        Unit economics metrics
    """
    service = GTMAnalysisService(db)

    try:
        economics = await service.calculate_unit_economics(gtm_id)
        return economics
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{gtm_id}/execution-plan")
async def get_execution_plan(
    gtm_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Get execution plan with timeline and milestones.

    Args:
        gtm_id: ID of the GTM analysis
        db: Database connection

    Returns:
        Execution plan
    """
    service = GTMAnalysisService(db)

    try:
        plan = await service.generate_execution_plan(gtm_id)
        return plan
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{gtm_id}/export")
async def export_gtm_analysis(
    gtm_id: str,
    format: str = Query("json", description="Export format (json, markdown, pdf, png)"),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Export GTM analysis in specified format.

    Args:
        gtm_id: ID of the GTM analysis
        format: Export format
        db: Database connection

    Returns:
        Exported content
    """
    service = GTMAnalysisService(db)

    try:
        # Validate format
        valid_formats = [f.value for f in ExportFormat]
        if format not in valid_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format. Must be one of: {', '.join(valid_formats)}",
            )

        content = await service.export_gtm_analysis(gtm_id, format)
        return {"format": format, "content": content}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
