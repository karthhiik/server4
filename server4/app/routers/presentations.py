"""Presentations CRUD — root collection operations."""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.dependencies import require_auth
from app.models.presentation import (
    CreatedFrom,
    GenerationState,
    PresentationCreate,
    PresentationMode,
    PresentationResponse,
    PresentationUpdate,
)

router = APIRouter(prefix="/api/presentations", tags=["Presentations"])


def _doc_to_response(doc: dict) -> PresentationResponse:
    return PresentationResponse(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        title=doc["title"],
        description=doc.get("description"),
        mode=doc.get("mode", "standard"),
        created_from=doc.get("created_from", "ai"),
        template_id=doc.get("template_id"),
        theme_id=doc.get("theme_id"),
        slide_count=doc.get("slide_count", 0),
        thumbnail_url=doc.get("thumbnail_url"),
        generation_state=doc.get("generation_state", "idle"),
        generation_progress=doc.get("generation_progress", 0),
        generation_message=doc.get("generation_message", ""),
        created_at=doc.get("created_at", datetime.utcnow()),
        updated_at=doc.get("updated_at", datetime.utcnow()),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_presentation(
    body: PresentationCreate,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> PresentationResponse:
    doc = {
        "_id": str(ObjectId()),
        "user_id": user["user_id"],
        "title": body.title,
        "description": body.description,
        "mode": body.mode.value,
        "created_from": body.created_from.value,
        "template_id": body.template_id,
        "theme_id": body.theme_id,
        "slide_count": 0,
        "thumbnail_url": None,
        "generation_state": GenerationState.IDLE.value,
        "generation_progress": 0,
        "generation_message": "",
        "generation_error": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.presentations.insert_one(doc)
    return _doc_to_response(doc)


@router.get("")
async def list_presentations(
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[PresentationResponse]:
    cursor = (
        db.presentations.find({"user_id": user["user_id"]})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    docs = await cursor.to_list(limit)
    return [_doc_to_response(d) for d in docs]


@router.get("/{presentation_id}")
async def get_presentation(
    presentation_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> PresentationResponse:
    doc = await db.presentations.find_one({
        "_id": presentation_id,
        "user_id": user["user_id"],
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Presentation not found")
    return _doc_to_response(doc)


@router.put("/{presentation_id}")
async def update_presentation(
    presentation_id: str,
    body: PresentationUpdate,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> PresentationResponse:
    update = {"updated_at": datetime.utcnow()}
    if body.title is not None:
        update["title"] = body.title
    if body.description is not None:
        update["description"] = body.description
    if body.theme_id is not None:
        update["theme_id"] = body.theme_id

    result = await db.presentations.find_one_and_update(
        {"_id": presentation_id, "user_id": user["user_id"]},
        {"$set": update},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Presentation not found")
    return _doc_to_response(result)


@router.delete("/{presentation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_presentation(
    presentation_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> None:
    result = await db.presentations.delete_one({
        "_id": presentation_id,
        "user_id": user["user_id"],
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Presentation not found")

    # Cascade delete slides and versions
    slide_ids = await db.slides.distinct("_id", {"presentation_id": presentation_id})
    if slide_ids:
        await db.slide_versions.delete_many({"slide_id": {"$in": slide_ids}})
    await db.slides.delete_many({"presentation_id": presentation_id})


@router.post("/{presentation_id}/duplicate")
async def duplicate_presentation(
    presentation_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> PresentationResponse:
    original = await db.presentations.find_one({
        "_id": presentation_id,
        "user_id": user["user_id"],
    })
    if not original:
        raise HTTPException(status_code=404, detail="Presentation not found")

    new_id = str(ObjectId())
    new_doc = {
        **original,
        "_id": new_id,
        "title": f"{original['title']} (Copy)",
        "generation_state": GenerationState.READY_FOR_EDITING.value,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.presentations.insert_one(new_doc)

    # Duplicate slides
    slides = await db.slides.find({"presentation_id": presentation_id}).to_list(100)
    for slide in slides:
        new_slide_id = str(ObjectId())
        await db.slides.insert_one({
            **slide,
            "_id": new_slide_id,
            "presentation_id": new_id,
            "version": 1,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })

    return _doc_to_response(new_doc)
