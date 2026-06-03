"""
FastAPI router for Barise v4 deck generation and management.

Endpoints:
  POST   /api/v4/decks
  GET    /api/v4/decks/{deck_id}
  PATCH  /api/v4/decks/{deck_id}/slides/{slide_no}
  POST   /api/v4/decks/{deck_id}/match-investors
  POST   /api/v4/decks/{deck_id}/export
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.models.v4 import (
    CompiledSlide,
    CreateDeckRequest,
    DeckResponse,
    ExportRequest,
    Presentation,
    ResolvedDesignTokens,
    SlideContent,
    SlidePatchRequest,
)
from app.services.v4.design_resolver import resolve_design_tokens
from app.services.v4.export_adapter import ExportAdapter
from app.services.v4.investor_intelligence import InvestorIntelligenceEngine
from app.services.v4.live_metrics import LiveMetricResolver
from app.services.v4.slide_compiler import SlideCompiler

router = APIRouter(prefix="/api/v4", tags=["v4"])

# NOTE: Assume db is injected as dependency or available globally
# For production, use: from fastapi import Depends
# and define: async def get_db() -> Any: ...
# then use: async def create_deck(..., db: Any = Depends(get_db))
# For now, we'll show the pattern with explicit db parameter


@router.post("/decks", response_model=DeckResponse)
async def create_deck(request: CreateDeckRequest, db: Any) -> DeckResponse:
    """
    Create a new presentation deck.

    Args:
        request: CreateDeckRequest with title, user_id, brief, mode, etc.
        db: MongoDB async client

    Returns:
        DeckResponse with deck_id and empty slides
    """
    # Resolve design tokens
    design_tokens = resolve_design_tokens(
        theme_id=request.theme_id,
        visual_direction=request.visual_direction,
        brand_kit=request.brand_kit,
        purpose="pitch" if request.brief else None,
    )

    # Create presentation
    deck_id = str(uuid4())
    presentation = Presentation(
        deck_id=deck_id,
        title=request.title,
        user_id=request.user_id,
        design_tokens=design_tokens,
        slides=[],
        status="draft",
        mode=request.mode,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # Save to MongoDB
    presentations_collection = db["presentations"]
    await presentations_collection.insert_one(
        {
            **presentation.model_dump(),
            "_id": deck_id,
        }
    )

    return DeckResponse(
        success=True,
        deck_id=deck_id,
        message="Deck created successfully",
        slides=[],
    )


@router.get("/decks/{deck_id}", response_model=DeckResponse)
async def get_deck(deck_id: str, db: Any, live: bool = False) -> DeckResponse:
    """
    Retrieve a deck.

    Args:
        deck_id: Presentation ID
        db: MongoDB async client
        live: If True, inject live metrics; if False, return as-is

    Returns:
        DeckResponse with full slides
    """
    presentations_collection = db["presentations"]

    # Load deck
    deck_doc = await presentations_collection.find_one({"deck_id": deck_id})
    if not deck_doc:
        raise HTTPException(status_code=404, detail="Deck not found")

    # Parse slides
    slides = [CompiledSlide(**slide) for slide in deck_doc.get("slides", [])]

    # Inject live metrics if requested
    if live:
        resolver = LiveMetricResolver(db)
        slides = [await resolver.inject_metrics_into_slide(slide) for slide in slides]

    return DeckResponse(
        success=True,
        deck_id=deck_id,
        message="Deck retrieved",
        slides=slides,
    )


@router.patch("/decks/{deck_id}/slides/{slide_no}")
async def patch_slide(
    deck_id: str,
    slide_no: int,
    request: SlidePatchRequest,
    db: Any,
) -> Dict[str, Any]:
    """
    Update a slide.

    Args:
        deck_id: Presentation ID
        slide_no: 1-indexed slide number
        request: SlidePatchRequest with content, layout_type, design_tokens
        db: MongoDB async client

    Returns:
        Updated slide
    """
    presentations_collection = db["presentations"]

    # Load deck
    deck_doc = await presentations_collection.find_one({"deck_id": deck_id})
    if not deck_doc:
        raise HTTPException(status_code=404, detail="Deck not found")

    slides = [CompiledSlide(**slide) for slide in deck_doc.get("slides", [])]
    if slide_no < 1 or slide_no > len(slides):
        raise HTTPException(status_code=404, detail="Slide not found")

    # Get slide (0-indexed)
    slide = slides[slide_no - 1]

    # Apply patches
    if request.content:
        slide.content = request.content
    if request.layout_type:
        slide.layout_type = request.layout_type
    if request.design_tokens:
        slide.design_tokens = request.design_tokens

    # Recompile if content or layout changed
    if request.content or request.layout_type:
        tokens = slide.design_tokens or ResolvedDesignTokens(
            palette=deck_doc["design_tokens"]["palette"],
            fonts=deck_doc["design_tokens"]["fonts"],
        )
        compiler = SlideCompiler(tokens)
        slide = compiler.compile_slide(
            slide_index=slide_no - 1,
            intent=slide.intent,
            content=slide.content,
            slide_id=slide.slide_id,
        )
        slide.version += 1

    slide.updated_at = datetime.utcnow()

    # Update in deck
    slides[slide_no - 1] = slide

    # Save to MongoDB
    deck_doc["slides"] = [s.model_dump() for s in slides]
    deck_doc["updated_at"] = datetime.utcnow()
    await presentations_collection.update_one(
        {"deck_id": deck_id},
        {"$set": deck_doc},
    )

    return {"success": True, "slide": slide.model_dump()}


@router.post("/decks/{deck_id}/match-investors")
async def match_investors(
    deck_id: str,
    db: Any,
) -> Dict[str, Any]:
    """
    Match investors for a deck.

    Args:
        deck_id: Presentation ID
        db: MongoDB async client

    Returns:
        Investors and pitch strategy
    """
    presentations_collection = db["presentations"]

    # Load deck
    deck_doc = await presentations_collection.find_one({"deck_id": deck_id})
    if not deck_doc:
        raise HTTPException(status_code=404, detail="Deck not found")

    # Extract params from metadata or deck
    brief = deck_doc.get("brief", "")
    stage = deck_doc.get("stage", "seed")
    sector = deck_doc.get("sector", "technology")
    target_raise = float(deck_doc.get("target_raise", 1000000))

    # Match investors
    engine = InvestorIntelligenceEngine(db)
    investors = await engine.match_investors(
        deck_id=deck_id,
        brief=brief,
        stage=stage,
        sector=sector,
        target_raise=target_raise,
    )

    # Generate pitch strategy for top investor
    slides = [CompiledSlide(**slide) for slide in deck_doc.get("slides", [])]
    strategy = {}
    if investors:
        strategy = await engine.generate_pitch_strategy(investors[0], slides)

    return {
        "success": True,
        "investors": [inv.model_dump() for inv in investors],
        "strategy": strategy,
    }


@router.post("/decks/{deck_id}/export")
async def export_deck(
    deck_id: str,
    request: ExportRequest,
    db: Any,
) -> Dict[str, Any]:
    """
    Export deck to PDF, PPTX, or HTML.

    Args:
        deck_id: Presentation ID
        request: ExportRequest with format
        db: MongoDB async client

    Returns:
        Download URL and metadata
    """
    presentations_collection = db["presentations"]

    # Load deck
    deck_doc = await presentations_collection.find_one({"deck_id": deck_id})
    if not deck_doc:
        raise HTTPException(status_code=404, detail="Deck not found")

    # Parse slides
    slides = [CompiledSlide(**slide) for slide in deck_doc.get("slides", [])]

    # Resolve metrics for export (snapshot)
    if request.format in ["pdf", "pptx"]:
        resolver = LiveMetricResolver(db)
        slides = [await resolver.inject_metrics_into_slide(slide) for slide in slides]

    # Parse design tokens
    design_tokens = ResolvedDesignTokens(**deck_doc["design_tokens"])

    # Export
    adapter = ExportAdapter(slides, design_tokens)

    export_id = str(uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=24)

    if request.format == "html":
        html_content = adapter.to_html()
        # In production: save to S3 or similar
        # For now, return base64 or URL
        return {
            "success": True,
            "format": "html",
            "export_id": export_id,
            "expires_at": expires_at.isoformat(),
            "content": html_content[:500],  # Sample
        }
    elif request.format == "pptx":
        try:
            pptx_bytes = adapter.to_pptx()
            # In production: save to S3
            return {
                "success": True,
                "format": "pptx",
                "export_id": export_id,
                "expires_at": expires_at.isoformat(),
                "size_bytes": len(pptx_bytes),
            }
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="PPTX export not available. Install python-pptx.",
            )
    elif request.format == "pdf":
        html_content = adapter.to_html()
        # In production: use weasyprint or similar
        # return PDF bytes
        return {
            "success": True,
            "format": "pdf",
            "export_id": export_id,
            "expires_at": expires_at.isoformat(),
        }
    else:
        raise HTTPException(status_code=400, detail="Invalid export format")
