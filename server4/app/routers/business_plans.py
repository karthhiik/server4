"""Business Plans CRUD routes and endpoints."""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.dependencies import require_auth
from app.models.business_plan import (
    BusinessPlanCreate,
    BusinessPlanListResponse,
    BusinessPlanResponse,
    BusinessPlanStatus,
    BusinessPlanUpdate,
    CitationCreate,
    CitationResponse,
    HealthResponse,
    SectionUpdate,
    VersionResponse,
)

router = APIRouter(prefix="/api/business-plans", tags=["Business Plans"])


def _doc_to_response(doc: dict) -> BusinessPlanResponse:
    """Convert MongoDB document to response model."""
    return BusinessPlanResponse(
        id=str(doc["_id"]),
        company_name=doc.get("company_name", ""),
        industry=doc.get("industry", ""),
        business_type=doc.get("business_type", ""),
        description=doc.get("description", ""),
        status=doc.get("status", BusinessPlanStatus.DRAFT),
        created_at=doc.get("created_at", datetime.utcnow()),
        updated_at=doc.get("updated_at", datetime.utcnow()),
        user_id=doc.get("user_id"),
        sections=doc.get("sections", {}),
        versions=doc.get("versions", []),
        citations=doc.get("citations", []),
    )


@router.get("/health", tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint (no auth required)."""
    return HealthResponse(
        status="ok",
        service="business-plan-service",
        version="1.0.0",
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_business_plan(
    body: BusinessPlanCreate,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> BusinessPlanResponse:
    """Create a new business plan."""
    doc = {
        "_id": str(ObjectId()),
        "user_id": user.get("user_id"),
        "company_name": body.company_name,
        "industry": body.industry,
        "business_type": body.business_type,
        "description": body.description,
        "target_market": body.target_market,
        "current_stage": body.current_stage,
        "team_size": body.team_size,
        "status": BusinessPlanStatus.DRAFT.value,
        "sections": {},
        "versions": [
            {
                "version_id": str(ObjectId()),
                "version_number": 1,
                "created_at": datetime.utcnow(),
                "status": "created",
            }
        ],
        "citations": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.business_plans.insert_one(doc)
    return _doc_to_response(doc)


@router.get("")
async def list_business_plans(
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> BusinessPlanListResponse:
    """List all business plans for the user."""
    cursor = (
        db.business_plans.find({"user_id": user.get("user_id")})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    docs = await cursor.to_list(limit)
    total = await db.business_plans.count_documents(
        {"user_id": user.get("user_id")}
    )
    return BusinessPlanListResponse(
        items=[_doc_to_response(d) for d in docs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{plan_id}")
async def get_business_plan(
    plan_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> BusinessPlanResponse:
    """Get a specific business plan by ID."""
    doc = await db.business_plans.find_one({
        "_id": plan_id,
        "user_id": user.get("user_id"),
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Business plan not found")
    return _doc_to_response(doc)


@router.put("/{plan_id}")
async def update_business_plan(
    plan_id: str,
    body: BusinessPlanUpdate,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> BusinessPlanResponse:
    """Update a business plan."""
    update = {"updated_at": datetime.utcnow()}
    if body.company_name is not None:
        update["company_name"] = body.company_name
    if body.industry is not None:
        update["industry"] = body.industry
    if body.description is not None:
        update["description"] = body.description
    if body.status is not None:
        update["status"] = body.status.value

    result = await db.business_plans.find_one_and_update(
        {"_id": plan_id, "user_id": user.get("user_id")},
        {"$set": update},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Business plan not found")
    return _doc_to_response(result)


@router.patch("/{plan_id}/sections/{section_id}")
async def update_section(
    plan_id: str,
    section_id: str,
    body: SectionUpdate,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> BusinessPlanResponse:
    """Update a specific section in a business plan."""
    result = await db.business_plans.find_one_and_update(
        {"_id": plan_id, "user_id": user.get("user_id")},
        {
            "$set": {
                f"sections.{section_id}": {
                    "content": body.content,
                    "metadata": body.metadata,
                    "updated_at": datetime.utcnow(),
                },
                "updated_at": datetime.utcnow(),
            }
        },
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Business plan not found")
    return _doc_to_response(result)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business_plan(
    plan_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> None:
    """Delete a business plan."""
    result = await db.business_plans.delete_one({
        "_id": plan_id,
        "user_id": user.get("user_id"),
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Business plan not found")


@router.get("/{plan_id}/versions")
async def get_plan_versions(
    plan_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> list[VersionResponse]:
    """Get version history for a business plan."""
    doc = await db.business_plans.find_one({
        "_id": plan_id,
        "user_id": user.get("user_id"),
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Business plan not found")

    versions = doc.get("versions", [])
    return [
        VersionResponse(
            version_id=v.get("version_id", ""),
            version_number=v.get("version_number", 0),
            created_at=v.get("created_at", datetime.utcnow()),
            created_by=v.get("created_by"),
            status=v.get("status", ""),
            summary=v.get("summary"),
        )
        for v in versions
    ]


@router.post("/{plan_id}/versions/{version_id}/restore")
async def restore_version(
    plan_id: str,
    version_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> BusinessPlanResponse:
    """Restore a business plan to a previous version."""
    doc = await db.business_plans.find_one({
        "_id": plan_id,
        "user_id": user.get("user_id"),
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Business plan not found")

    # Find the version to restore
    version_to_restore = None
    for v in doc.get("versions", []):
        if v.get("version_id") == version_id:
            version_to_restore = v
            break

    if not version_to_restore:
        raise HTTPException(status_code=404, detail="Version not found")

    # Update the plan with the restored version
    update = {
        "$set": {
            "sections": version_to_restore.get("sections", {}),
            "updated_at": datetime.utcnow(),
            "restored_from_version": version_id,
        }
    }

    result = await db.business_plans.find_one_and_update(
        {"_id": plan_id, "user_id": user.get("user_id")},
        update,
        return_document=True,
    )
    return _doc_to_response(result)


@router.get("/{plan_id}/export")
async def export_plan(
    plan_id: str,
    format: str = Query("pdf", description="Export format (pdf or csv)"),
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
):
    """Export a business plan in the specified format."""
    doc = await db.business_plans.find_one({
        "_id": plan_id,
        "user_id": user.get("user_id"),
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Business plan not found")

    if format not in ["pdf", "csv"]:
        raise HTTPException(status_code=400, detail="Invalid export format")

    # Simulate export generation
    if format == "pdf":
        return {
            "format": "pdf",
            "filename": f"{doc.get('company_name', 'plan')}_business_plan.pdf",
            "content_type": "application/pdf",
            "size": 1024000,
        }
    else:  # csv
        return {
            "format": "csv",
            "filename": f"{doc.get('company_name', 'plan')}_business_plan.csv",
            "content_type": "text/csv",
            "size": 50000,
        }


@router.get("/{plan_id}/citations")
async def get_citations(
    plan_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> list[CitationResponse]:
    """Get citations for a business plan."""
    doc = await db.business_plans.find_one({
        "_id": plan_id,
        "user_id": user.get("user_id"),
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Business plan not found")

    citations = doc.get("citations", [])
    return [
        CitationResponse(
            source=c.get("source", ""),
            title=c.get("title", ""),
            url=c.get("url"),
            date_accessed=c.get("date_accessed"),
        )
        for c in citations
    ]

@router.post("/{plan_id}/citations", status_code=status.HTTP_201_CREATED)
async def add_citations(
    plan_id: str,
    body: CitationCreate,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> CitationResponse:
    """Add a citation to a business plan."""
    doc = await db.business_plans.find_one({
        "_id": plan_id,
        "user_id": user.get("user_id"),
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Business plan not found")

    citation = {
        "id": str(ObjectId()),
        "source": body.source,
        "title": body.title,
        "url": body.url,
        "date_accessed": body.date_accessed or datetime.utcnow(),
    }

    await db.business_plans.update_one(
        {"_id": plan_id},
        {"$push": {"citations": citation}, "$set": {"updated_at": datetime.utcnow()}},
    )

    return CitationResponse(
        source=citation["source"],
        title=citation["title"],
        url=citation["url"],
        date_accessed=citation["date_accessed"],
    )
