"""Pitch Deck Canvas CRUD routes and endpoints."""

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.dependencies import require_auth
from app.models.pitch_deck_models import (
    DeckShare,
    DeckStatus,
    ExecutiveSummaryContent,
    ExportRequest,
    FinancialsContent,
    HealthResponse,
    MarketContent,
    PitchDeck,
    PitchDeckCreate,
    PitchDeckMetrics,
    PitchDeckUpdate,
    ProductDemoContent,
    Slide,
    SlideCreate,
    SlideType,
    SlideUpdate,
    TeamContent,
    TractionContent,
)

router = APIRouter(prefix="/api/pitch-decks", tags=["Pitch Decks"])


def _doc_to_pitch_deck(doc: dict) -> PitchDeck:
    """Convert MongoDB document to PitchDeck model."""
    return PitchDeck(
        id=str(doc.get("_id", doc.get("id", ""))),
        business_plan_id=doc.get("business_plan_id", ""),
        title=doc.get("title", ""),
        subtitle=doc.get("subtitle"),
        status=DeckStatus(doc.get("status", "draft")),
        theme=doc.get("theme", "modern_blue"),
        slides=doc.get("slides", []),
        created_at=doc.get("created_at", datetime.now(timezone.utc)),
        updated_at=doc.get("updated_at", datetime.now(timezone.utc)),
        published_at=doc.get("published_at"),
        metrics=doc.get("metrics"),
        user_id=doc.get("user_id"),
    )


@router.get("/health", tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint (no auth required)."""
    return HealthResponse(
        status="ok",
        service="pitch-deck-service",
        version="1.0.0",
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_pitch_deck(
    body: PitchDeckCreate,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> PitchDeck:
    """Create a new pitch deck from business plan."""
    # Verify business plan exists
    business_plan = await db.business_plans.find_one(
        {"_id": ObjectId(body.business_plan_id)}
    )
    if not business_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business plan not found",
        )

    # Create pitch deck document
    deck_id = str(ObjectId())
    now = datetime.now(timezone.utc)

    deck_doc = {
        "_id": ObjectId(deck_id),
        "id": deck_id,
        "business_plan_id": body.business_plan_id,
        "user_id": user.get("user_id"),
        "title": body.title,
        "subtitle": body.subtitle,
        "status": DeckStatus.DRAFT.value,
        "theme": "modern_blue",
        "slides": [],
        "metrics": {
            "total_views": 0,
            "unique_viewers": 0,
            "average_session_time": 0,
            "shares_count": 0,
        },
        "created_at": now,
        "updated_at": now,
    }

    result = await db.pitch_decks.insert_one(deck_doc)
    deck_doc["_id"] = result.inserted_id
    return _doc_to_pitch_deck(deck_doc)


@router.get("")
async def list_pitch_decks(
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    """List all pitch decks for the user."""
    cursor = db.pitch_decks.find({"user_id": user.get("user_id")})
    cursor = cursor.skip(skip).limit(limit)
    decks = await cursor.to_list(limit)

    total = await db.pitch_decks.count_documents({"user_id": user.get("user_id")})

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "decks": [_doc_to_pitch_deck(doc) for doc in decks],
    }


@router.get("/{deck_id}")
async def get_pitch_deck(
    deck_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> PitchDeck:
    """Retrieve a specific pitch deck."""
    try:
        doc = await db.pitch_decks.find_one(
            {"_id": ObjectId(deck_id), "user_id": user.get("user_id")}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deck ID",
        )

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pitch deck not found",
        )

    return _doc_to_pitch_deck(doc)


@router.put("/{deck_id}")
async def update_pitch_deck(
    deck_id: str,
    body: PitchDeckUpdate,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> PitchDeck:
    """Update a pitch deck."""
    try:
        doc = await db.pitch_decks.find_one(
            {"_id": ObjectId(deck_id), "user_id": user.get("user_id")}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deck ID",
        )

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pitch deck not found",
        )

    # Prepare update data
    update_data = {}
    if body.title is not None:
        update_data["title"] = body.title
    if body.subtitle is not None:
        update_data["subtitle"] = body.subtitle
    if body.status is not None:
        update_data["status"] = body.status.value
    if body.theme is not None:
        update_data["theme"] = body.theme

    update_data["updated_at"] = datetime.now(timezone.utc)

    await db.pitch_decks.update_one(
        {"_id": ObjectId(deck_id)},
        {"$set": update_data},
    )

    # Fetch and return updated document
    updated_doc = await db.pitch_decks.find_one({"_id": ObjectId(deck_id)})
    return _doc_to_pitch_deck(updated_doc)


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pitch_deck(
    deck_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
):
    """Delete a pitch deck."""
    try:
        result = await db.pitch_decks.delete_one(
            {"_id": ObjectId(deck_id), "user_id": user.get("user_id")}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deck ID",
        )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pitch deck not found",
        )


# ── Slide Management ───────────────────────────────────────────

@router.post("/{deck_id}/slides", status_code=status.HTTP_201_CREATED)
async def create_slide(
    deck_id: str,
    body: SlideCreate,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Create a new slide in a pitch deck."""
    try:
        deck = await db.pitch_decks.find_one(
            {"_id": ObjectId(deck_id), "user_id": user.get("user_id")}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deck ID",
        )

    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pitch deck not found",
        )

    # Create slide
    slide_id = str(ObjectId())
    slide = {
        "id": slide_id,
        "order": body.order,
        "type": body.type.value,
        "title": body.title,
        "content": body.content,
        "speaker_notes": body.speaker_notes,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    # Add slide to deck
    await db.pitch_decks.update_one(
        {"_id": ObjectId(deck_id)},
        {
            "$push": {"slides": slide},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )

    return {"slide_id": slide_id, "slide": slide}


@router.get("/{deck_id}/slides")
async def list_slides(
    deck_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Get all slides in a pitch deck."""
    try:
        deck = await db.pitch_decks.find_one(
            {"_id": ObjectId(deck_id), "user_id": user.get("user_id")}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deck ID",
        )

    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pitch deck not found",
        )

    return {"slides": deck.get("slides", [])}


@router.get("/{deck_id}/slides/{slide_id}")
async def get_slide(
    deck_id: str,
    slide_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Get a specific slide."""
    try:
        deck = await db.pitch_decks.find_one(
            {"_id": ObjectId(deck_id), "user_id": user.get("user_id")}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deck ID",
        )

    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pitch deck not found",
        )

    slide = next(
        (s for s in deck.get("slides", []) if s.get("id") == slide_id),
        None,
    )

    if not slide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slide not found",
        )

    return slide


@router.put("/{deck_id}/slides/{slide_id}")
async def update_slide(
    deck_id: str,
    slide_id: str,
    body: SlideUpdate,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Update a slide."""
    try:
        deck = await db.pitch_decks.find_one(
            {"_id": ObjectId(deck_id), "user_id": user.get("user_id")}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deck ID",
        )

    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pitch deck not found",
        )

    slides = deck.get("slides", [])
    slide_index = next(
        (i for i, s in enumerate(slides) if s.get("id") == slide_id),
        -1,
    )

    if slide_index == -1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slide not found",
        )

    # Update slide fields
    slide = slides[slide_index]
    if body.order is not None:
        slide["order"] = body.order
    if body.title is not None:
        slide["title"] = body.title
    if body.content is not None:
        slide["content"] = body.content
    if body.speaker_notes is not None:
        slide["speaker_notes"] = body.speaker_notes

    slide["updated_at"] = datetime.now(timezone.utc)

    await db.pitch_decks.update_one(
        {"_id": ObjectId(deck_id)},
        {
            "$set": {
                "slides": slides,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )

    return slide


@router.delete("/{deck_id}/slides/{slide_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slide(
    deck_id: str,
    slide_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
):
    """Delete a slide."""
    try:
        deck = await db.pitch_decks.find_one(
            {"_id": ObjectId(deck_id), "user_id": user.get("user_id")}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deck ID",
        )

    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pitch deck not found",
        )

    slides = [s for s in deck.get("slides", []) if s.get("id") != slide_id]

    if len(slides) == len(deck.get("slides", [])):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slide not found",
        )

    await db.pitch_decks.update_one(
        {"_id": ObjectId(deck_id)},
        {
            "$set": {
                "slides": slides,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )


# ── Publishing & Sharing ───────────────────────────────────────────

@router.post("/{deck_id}/publish", status_code=status.HTTP_200_OK)
async def publish_deck(
    deck_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Publish a pitch deck."""
    try:
        deck = await db.pitch_decks.find_one(
            {"_id": ObjectId(deck_id), "user_id": user.get("user_id")}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deck ID",
        )

    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pitch deck not found",
        )

    now = datetime.now(timezone.utc)

    await db.pitch_decks.update_one(
        {"_id": ObjectId(deck_id)},
        {
            "$set": {
                "status": DeckStatus.PUBLISHED.value,
                "published_at": now,
                "updated_at": now,
            }
        },
    )

    updated_deck = await db.pitch_decks.find_one({"_id": ObjectId(deck_id)})
    return {
        "deck_id": deck_id,
        "status": "published",
        "published_at": now.isoformat(),
    }


@router.post("/{deck_id}/share")
async def share_deck(
    deck_id: str,
    body: DeckShare,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Share a pitch deck with recipients."""
    try:
        deck = await db.pitch_decks.find_one(
            {"_id": ObjectId(deck_id), "user_id": user.get("user_id")}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deck ID",
        )

    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pitch deck not found",
        )

    # Record share
    share_doc = {
        "_id": ObjectId(),
        "deck_id": deck_id,
        "shared_by": user.get("user_id"),
        "recipients": body.recipients,
        "created_at": datetime.now(timezone.utc),
    }

    result = await db.deck_shares.insert_one(share_doc)

    # Update metrics
    await db.pitch_decks.update_one(
        {"_id": ObjectId(deck_id)},
        {
            "$inc": {"metrics.shares_count": 1},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )

    return {
        "share_id": str(result.inserted_id),
        "recipients_count": len(body.recipients),
    }


# ── Themes ───────────────────────────────────────────

@router.post("/{deck_id}/theme")
async def apply_theme(
    deck_id: str,
    theme_data: dict,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Apply a theme to a pitch deck."""
    try:
        deck = await db.pitch_decks.find_one(
            {"_id": ObjectId(deck_id), "user_id": user.get("user_id")}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deck ID",
        )

    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pitch deck not found",
        )

    theme_name = theme_data.get("theme")

    await db.pitch_decks.update_one(
        {"_id": ObjectId(deck_id)},
        {
            "$set": {
                "theme": theme_name,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )

    return {"deck_id": deck_id, "theme": theme_name}


@router.get("/themes")
async def get_themes() -> dict:
    """Get available themes."""
    return {
        "themes": [
            {"id": "modern_blue", "name": "Modern Blue", "color": "#003366"},
            {"id": "corporate_gold", "name": "Corporate Gold", "color": "#B8860B"},
            {"id": "startup_neon", "name": "Startup Neon", "color": "#FF006E"},
            {"id": "minimalist", "name": "Minimalist", "color": "#FFFFFF"},
            {"id": "tech_dark", "name": "Tech Dark", "color": "#1A1A1A"},
            {"id": "vibrant", "name": "Vibrant", "color": "#FF6B35"},
        ]
    }


# ── Analytics ───────────────────────────────────────────

@router.post("/{deck_id}/track-view")
async def track_view(
    deck_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Track a view of a pitch deck."""
    try:
        deck = await db.pitch_decks.find_one({"_id": ObjectId(deck_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deck ID",
        )

    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pitch deck not found",
        )

    # Record view
    view_doc = {
        "_id": ObjectId(),
        "deck_id": deck_id,
        "user_id": user.get("user_id"),
        "viewed_at": datetime.now(timezone.utc),
    }

    await db.deck_views.insert_one(view_doc)

    # Update metrics
    await db.pitch_decks.update_one(
        {"_id": ObjectId(deck_id)},
        {
            "$inc": {"metrics.total_views": 1},
        },
    )

    return {"deck_id": deck_id, "tracked": True}


@router.get("/{deck_id}/analytics")
async def get_analytics(
    deck_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Get analytics for a pitch deck."""
    try:
        deck = await db.pitch_decks.find_one(
            {"_id": ObjectId(deck_id), "user_id": user.get("user_id")}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deck ID",
        )

    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pitch deck not found",
        )

    metrics = deck.get("metrics", {})
    views = await db.deck_views.count_documents({"deck_id": deck_id})
    unique_viewers = len(
        set(
            v["user_id"]
            for v in await db.deck_views.find({"deck_id": deck_id})
            .to_list(None)
        )
    )

    return {
        "deck_id": deck_id,
        "total_views": views,
        "unique_viewers": unique_viewers,
        "average_session_time": metrics.get("average_session_time", 0),
        "shares_count": metrics.get("shares_count", 0),
        "last_viewed": metrics.get("last_viewed"),
    }


# ── Export ───────────────────────────────────────────

@router.post("/{deck_id}/export")
async def export_deck(
    deck_id: str,
    body: ExportRequest,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Export a pitch deck."""
    try:
        deck = await db.pitch_decks.find_one(
            {"_id": ObjectId(deck_id), "user_id": user.get("user_id")}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deck ID",
        )

    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pitch deck not found",
        )

    # Create export record
    export_doc = {
        "_id": ObjectId(),
        "deck_id": deck_id,
        "user_id": user.get("user_id"),
        "format": body.format,
        "include_speaker_notes": body.include_speaker_notes,
        "include_animations": body.include_animations,
        "created_at": datetime.now(timezone.utc),
        "status": "processing",
    }

    result = await db.exports.insert_one(export_doc)

    # Generate file URL (simulated)
    file_ext = "pdf" if body.format == "pdf" else "pptx"
    file_url = f"https://storage.example.com/exports/{result.inserted_id}.{file_ext}"

    # Update export status
    await db.exports.update_one(
        {"_id": result.inserted_id},
        {"$set": {"status": "completed", "url": file_url}},
    )

    return {
        "export_id": str(result.inserted_id),
        "format": body.format,
        "url": file_url,
        "status": "completed",
    }
