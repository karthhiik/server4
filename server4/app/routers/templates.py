"""Template library and template-based generation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.dependencies import require_auth
from app.models.template import TemplateResponse

router = APIRouter(prefix="/api/templates", tags=["Templates"])


@router.get("")
async def list_templates(
    category: str = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> list[TemplateResponse]:
    """List available templates. No auth required for browsing."""
    query = {}
    if category:
        query["category"] = category

    cursor = db.templates.find(query).sort("usage_count", -1).skip(offset)
    docs = await cursor.to_list(limit)

    return [
        TemplateResponse(
            id=str(d["_id"]),
            name=d["name"],
            category=d["category"],
            description=d.get("description", ""),
            thumbnail_url=d.get("thumbnail_url"),
            slide_count=d.get("slide_count", 0),
            mode_available=d.get("mode_available", ["standard", "premium"]),
            default_theme=d.get("default_theme", "corporate-blue"),
            usage_count=d.get("usage_count", 0),
            avg_rating=d.get("avg_rating"),
        )
        for d in docs
    ]


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Get full template details including slide definitions."""
    doc = await db.templates.find_one({"_id": template_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")

    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("/categories/list")
async def list_categories(
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> list[str]:
    """Get all available template categories."""
    return await db.templates.distinct("category")
