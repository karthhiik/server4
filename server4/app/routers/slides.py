"""
Slide editing endpoints — text editing, layout change, undo/redo,
reorder, add, delete, and AI-assisted actions.
"""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.dependencies import require_auth, check_generation_rate_limit
from app.models.slide import (
    AISlideAction,
    SlideContent,
    SlideLayout,
    SlideLayoutChange,
    SlideReorder,
    SlideResponse,
    SlideUpdate,
)
from app.services.llm import ModelRouter, TaskType
from app.mcp.brain_mcp.refiners.content_refiner import ContentRefiner

router = APIRouter(prefix="/api", tags=["Slides"])


def _doc_to_response(doc: dict) -> SlideResponse:
    content_data = doc.get("content", {})
    return SlideResponse(
        id=str(doc["_id"]),
        presentation_id=doc["presentation_id"],
        index=doc["index"],
        layout=doc.get("layout", "bullets"),
        content=SlideContent(**content_data) if isinstance(content_data, dict) else SlideContent(),
        version=doc.get("version", 1),
        created_at=doc.get("created_at", datetime.utcnow()),
        updated_at=doc.get("updated_at", datetime.utcnow()),
    )


async def _verify_ownership(db, presentation_id: str, user_id: str) -> dict:
    pres = await db.presentations.find_one({"_id": presentation_id, "user_id": user_id})
    if not pres:
        raise HTTPException(status_code=404, detail="Presentation not found")
    return pres


async def _save_version(db, slide_doc: dict, change_type: str) -> None:
    """Save current slide state as a version for undo/redo."""
    await db.slide_versions.insert_one({
        "_id": str(ObjectId()),
        "slide_id": str(slide_doc["_id"]),
        "version": slide_doc.get("version", 1),
        "layout": slide_doc.get("layout"),
        "content": slide_doc.get("content", {}),
        "change_type": change_type,
        "created_at": datetime.utcnow(),
    })


# ── Get slides for a presentation ────────────────────────────

@router.get("/presentations/{presentation_id}/slides")
async def get_slides(
    presentation_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> list[SlideResponse]:
    await _verify_ownership(db, presentation_id, user["user_id"])
    cursor = db.slides.find({"presentation_id": presentation_id}).sort("index", 1)
    docs = await cursor.to_list(100)
    return [_doc_to_response(d) for d in docs]


# ── Update slide content ─────────────────────────────────────

@router.put("/slides/{slide_id}")
async def update_slide(
    slide_id: str,
    body: SlideUpdate,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> SlideResponse:
    slide = await db.slides.find_one({"_id": slide_id})
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    await _verify_ownership(db, slide["presentation_id"], user["user_id"])

    # Save current state for undo
    await _save_version(db, slide, "edit")

    update: dict = {"updated_at": datetime.utcnow(), "version": slide.get("version", 1) + 1}
    if body.content is not None:
        update["content"] = body.content.model_dump(exclude_none=True)

    result = await db.slides.find_one_and_update(
        {"_id": slide_id},
        {"$set": update},
        return_document=True,
    )
    return _doc_to_response(result)


# ── Change slide layout ──────────────────────────────────────

@router.put("/slides/{slide_id}/layout")
async def change_layout(
    slide_id: str,
    body: SlideLayoutChange,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> SlideResponse:
    slide = await db.slides.find_one({"_id": slide_id})
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    await _verify_ownership(db, slide["presentation_id"], user["user_id"])

    # Save current state for undo
    await _save_version(db, slide, "layout_change")

    # Re-flow content for the new layout using AI if needed
    content = slide.get("content", {})
    new_layout = body.layout.value
    old_layout = slide.get("layout", "bullets")

    if old_layout != new_layout:
        content = await _reflow_content_for_layout(content, old_layout, new_layout)

    result = await db.slides.find_one_and_update(
        {"_id": slide_id},
        {"$set": {
            "layout": new_layout,
            "content": content,
            "version": slide.get("version", 1) + 1,
            "updated_at": datetime.utcnow(),
        }},
        return_document=True,
    )
    return _doc_to_response(result)


# ── Add new slide ─────────────────────────────────────────────

@router.post("/presentations/{presentation_id}/slides", status_code=status.HTTP_201_CREATED)
async def add_slide(
    presentation_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
    after_index: Optional[int] = None,
) -> SlideResponse:
    await _verify_ownership(db, presentation_id, user["user_id"])

    # Determine insert position
    max_doc = await db.slides.find_one(
        {"presentation_id": presentation_id},
        sort=[("index", -1)],
    )
    max_index = max_doc["index"] if max_doc else -1

    if after_index is not None and after_index <= max_index:
        new_index = after_index + 1
        # Shift subsequent slides
        await db.slides.update_many(
            {"presentation_id": presentation_id, "index": {"$gte": new_index}},
            {"$inc": {"index": 1}},
        )
    else:
        new_index = max_index + 1

    slide_id = str(ObjectId())
    doc = {
        "_id": slide_id,
        "presentation_id": presentation_id,
        "index": new_index,
        "layout": "blank",
        "content": {"title": "New Slide"},
        "version": 1,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.slides.insert_one(doc)

    # Update slide count
    count = await db.slides.count_documents({"presentation_id": presentation_id})
    await db.presentations.update_one(
        {"_id": presentation_id},
        {"$set": {"slide_count": count, "updated_at": datetime.utcnow()}},
    )

    return _doc_to_response(doc)


# ── Delete slide ──────────────────────────────────────────────

@router.delete("/presentations/{presentation_id}/slides/{slide_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slide(
    presentation_id: str,
    slide_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> None:
    await _verify_ownership(db, presentation_id, user["user_id"])

    slide = await db.slides.find_one({"_id": slide_id, "presentation_id": presentation_id})
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")

    await db.slides.delete_one({"_id": slide_id})
    await db.slide_versions.delete_many({"slide_id": slide_id})

    # Re-index remaining slides
    await db.slides.update_many(
        {"presentation_id": presentation_id, "index": {"$gt": slide["index"]}},
        {"$inc": {"index": -1}},
    )

    count = await db.slides.count_documents({"presentation_id": presentation_id})
    await db.presentations.update_one(
        {"_id": presentation_id},
        {"$set": {"slide_count": count, "updated_at": datetime.utcnow()}},
    )


# ── Reorder slides ────────────────────────────────────────────

@router.put("/presentations/{presentation_id}/slides/reorder")
async def reorder_slides(
    presentation_id: str,
    body: SlideReorder,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> list[SlideResponse]:
    await _verify_ownership(db, presentation_id, user["user_id"])

    for new_index, slide_id in enumerate(body.slide_ids):
        await db.slides.update_one(
            {"_id": slide_id, "presentation_id": presentation_id},
            {"$set": {"index": new_index, "updated_at": datetime.utcnow()}},
        )

    cursor = db.slides.find({"presentation_id": presentation_id}).sort("index", 1)
    docs = await cursor.to_list(100)
    return [_doc_to_response(d) for d in docs]


# ── Undo / Redo ───────────────────────────────────────────────

@router.post("/slides/{slide_id}/undo")
async def undo_slide(
    slide_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> SlideResponse:
    slide = await db.slides.find_one({"_id": slide_id})
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    await _verify_ownership(db, slide["presentation_id"], user["user_id"])

    current_version = slide.get("version", 1)
    prev = await db.slide_versions.find_one(
        {"slide_id": slide_id, "version": current_version - 1},
    )
    if not prev:
        # Try to find the most recent version before current
        prev = await db.slide_versions.find_one(
            {"slide_id": slide_id, "version": {"$lt": current_version}},
            sort=[("version", -1)],
        )
    if not prev:
        raise HTTPException(status_code=400, detail="Nothing to undo")

    # Save current as a "redo point"
    await _save_version(db, slide, "undo")

    result = await db.slides.find_one_and_update(
        {"_id": slide_id},
        {"$set": {
            "layout": prev["layout"],
            "content": prev["content"],
            "version": prev["version"],
            "updated_at": datetime.utcnow(),
        }},
        return_document=True,
    )
    return _doc_to_response(result)


@router.post("/slides/{slide_id}/redo")
async def redo_slide(
    slide_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> SlideResponse:
    slide = await db.slides.find_one({"_id": slide_id})
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    await _verify_ownership(db, slide["presentation_id"], user["user_id"])

    current_version = slide.get("version", 1)
    next_ver = await db.slide_versions.find_one(
        {"slide_id": slide_id, "version": {"$gt": current_version}},
        sort=[("version", 1)],
    )
    if not next_ver:
        raise HTTPException(status_code=400, detail="Nothing to redo")

    result = await db.slides.find_one_and_update(
        {"_id": slide_id},
        {"$set": {
            "layout": next_ver["layout"],
            "content": next_ver["content"],
            "version": next_ver["version"],
            "updated_at": datetime.utcnow(),
        }},
        return_document=True,
    )
    return _doc_to_response(result)


@router.get("/slides/{slide_id}/history")
async def get_slide_history(
    slide_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> list[dict]:
    slide = await db.slides.find_one({"_id": slide_id})
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    await _verify_ownership(db, slide["presentation_id"], user["user_id"])

    cursor = db.slide_versions.find({"slide_id": slide_id}).sort("version", -1).limit(50)
    versions = await cursor.to_list(50)

    return [
        {
            "version": v["version"],
            "change_type": v.get("change_type", "edit"),
            "layout": v.get("layout"),
            "created_at": v.get("created_at"),
        }
        for v in versions
    ]


# ── AI-assisted editing ──────────────────────────────────────

@router.post("/slides/{slide_id}/rewrite")
async def ai_rewrite_slide(
    slide_id: str,
    body: AISlideAction,
    user: dict = Depends(check_generation_rate_limit),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> SlideResponse:
    return await _ai_edit_slide(db, slide_id, user, "rewrite", body.instruction or "Improve this slide content")


@router.post("/slides/{slide_id}/expand")
async def ai_expand_slide(
    slide_id: str,
    user: dict = Depends(check_generation_rate_limit),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> SlideResponse:
    return await _ai_edit_slide(db, slide_id, user, "expand", "Expand the bullet points with more detail")


@router.post("/slides/{slide_id}/summarize")
async def ai_summarize_slide(
    slide_id: str,
    user: dict = Depends(check_generation_rate_limit),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> SlideResponse:
    return await _ai_edit_slide(db, slide_id, user, "summarize", "Make this more concise")


@router.post("/slides/{slide_id}/translate")
async def ai_translate_slide(
    slide_id: str,
    body: AISlideAction,
    user: dict = Depends(check_generation_rate_limit),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> SlideResponse:
    if not body.target_language:
        raise HTTPException(status_code=400, detail="target_language required")
    return await _ai_edit_slide(
        db, slide_id, user, "translate",
        f"Translate all text to {body.target_language}",
        task_type=TaskType.TRANSLATION_QUICK_EDIT,
    )


@router.post("/slides/{slide_id}/style-rewrite")
async def ai_style_rewrite_slide(
    slide_id: str,
    body: AISlideAction,
    user: dict = Depends(check_generation_rate_limit),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> SlideResponse:
    """Rewrite slide content in a specific writing style (yc_pitch, narrative, executive, etc.)."""
    if not body.writing_style:
        raise HTTPException(status_code=400, detail="writing_style required")

    slide = await db.slides.find_one({"_id": slide_id})
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    await _verify_ownership(db, slide["presentation_id"], user["user_id"])

    await _save_version(db, slide, "ai_style_rewrite")

    refiner = ContentRefiner()
    new_content = await refiner.style_rewrite(
        content=slide.get("content", {}),
        style=body.writing_style,
        layout=slide.get("layout", "bullets"),
        purpose=body.instruction or "",
        presentation_id=slide["presentation_id"],
    )

    result = await db.slides.find_one_and_update(
        {"_id": slide_id},
        {"$set": {
            "content": new_content,
            "version": slide.get("version", 1) + 1,
            "updated_at": datetime.utcnow(),
        }},
        return_document=True,
    )
    return _doc_to_response(result)


@router.get("/styles")
async def get_available_styles() -> list[dict]:
    """Return all available content writing styles."""
    return ContentRefiner.get_available_styles()


# ── Internal helpers ──────────────────────────────────────────

async def _ai_edit_slide(
    db: AsyncIOMotorDatabase,
    slide_id: str,
    user: dict,
    change_type: str,
    instruction: str,
    task_type: TaskType = TaskType.REFINEMENT,
) -> SlideResponse:
    slide = await db.slides.find_one({"_id": slide_id})
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    await _verify_ownership(db, slide["presentation_id"], user["user_id"])

    await _save_version(db, slide, f"ai_{change_type}")

    import json
    router = ModelRouter.get_instance()
    response = await router.complete(
        task_type=task_type,
        messages=[
            {"role": "system", "content": (
                "You are a slide content editor. Given the current slide content and an instruction, "
                "return the UPDATED content as a JSON object with the same field structure. "
                "IMPORTANT: Return ONLY valid JSON, no markdown."
            )},
            {"role": "user", "content": (
                f"Current slide content:\n{json.dumps(slide.get('content', {}))}\n\n"
                f"Instruction: {instruction}\n\n"
                f"Return the updated content as JSON."
            )},
        ],
        max_tokens=2000,
    )

    try:
        new_content = json.loads(response.content.strip())
    except json.JSONDecodeError:
        new_content = slide.get("content", {})
        if "title" in new_content:
            new_content["body_text"] = response.content[:500]

    result = await db.slides.find_one_and_update(
        {"_id": slide_id},
        {"$set": {
            "content": new_content,
            "version": slide.get("version", 1) + 1,
            "updated_at": datetime.utcnow(),
        }},
        return_document=True,
    )
    return _doc_to_response(result)


async def _reflow_content_for_layout(
    content: dict, old_layout: str, new_layout: str
) -> dict:
    """
    Adapt content from one layout to another.
    Uses LLM for complex transitions, simple mapping for obvious ones.
    """
    import json

    # Simple mappings that don't need AI
    if new_layout == "blank":
        return content
    if old_layout == "blank":
        return content

    try:
        router = ModelRouter.get_instance()
        response = await router.complete(
            task_type=TaskType.CONTENT_FIT_RESIZE,
            messages=[
                {"role": "system", "content": (
                    f"Adapt slide content from '{old_layout}' layout to '{new_layout}' layout. "
                    "Keep all important information but restructure it to fit the new layout. "
                    "Return ONLY valid JSON with appropriate fields for the new layout."
                )},
                {"role": "user", "content": json.dumps(content)},
            ],
            max_tokens=1500,
        )
        return json.loads(response.content.strip())
    except Exception:
        return content
