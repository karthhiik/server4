"""
V4 Editor Routes — production endpoints powering the Content/Display stage.

Lifecycle: V4 generation persists slides to `db.slides` (one doc per slide,
keyed by `project_id` + `index`) and stores a skeleton + slim research
snapshot on the presentation doc. This router is the single read/write
surface the frontend talks to during the Content stage.

Endpoints:
  GET    /api/v4/projects/{project_id}/slides
         List slides (ordered by index) with full DSL for the editor.

  PATCH  /api/v4/projects/{project_id}/slides/{slide_no}
         Partial update of a single slide. Snapshots prior state into
         `db.slide_versions` so undo is non-lossy.

  PATCH  /api/v4/projects/{project_id}/slides/reorder
      Persist a complete slide order, keeping `db.slides`, compiled
      sandbox artifacts, skeleton metadata, and live editor clients in sync.

  POST   /api/v4/projects/{project_id}/slides/{slide_no}/regenerate
         Re-run the writer for a single slide. Optionally accepts a free-form
         user instruction (Guided mode) and an explicit `target_model`
         (premium Variant mode). Reuses the cached skeleton + research
      snapshot to avoid re-running paid research APIs, then refreshes the
      compiled sandbox artifact for that slide.

  POST   /api/v4/projects/{project_id}/slides/regenerate-batch
      Re-run a bounded set of slide writers and refresh compiled artifacts
      in one deck-consistent pass.

  POST   /api/v4/projects/{project_id}/regenerate-deck
         Re-run all writers in parallel using the cached skeleton + research.
         Premium-only. Used when the user wants a fresh narrative pass.

  POST   /api/v4/projects/{project_id}/slides/{slide_no}/team-member
         Multipart: upsert a team member on a slide. Optional file upload
         for the photo; otherwise falls back to provided photo_url, then to
         a deterministic SVG initials avatar.

  DELETE /api/v4/projects/{project_id}/slides/{slide_no}/team-member/{member_idx}
         Remove a team member entry.

Ownership: every request is verified against `presentations.user_id`. The
"dev-test-user" sentinel is honored in dev to keep parity with other routers.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import structlog
from bson import ObjectId
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field

from app.database import get_db
from app.config import settings
from app.dependencies import optional_auth
from app.services.v4.image_search import make_default_candidate, search_person_image
from app.services.v4.research_collector import Citation, ResearchPacket
from app.services.v4.regen_engine import (
    MAX_BATCH_REGEN_SLIDES,
    MAX_REGEN_CONCURRENCY,
    RegenerationBusy,
    RegenerationRequest,
    RegenerationValidationError,
    regenerate_one_field,
    regenerate_slides,
)
from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.quality_metrics import QualityEvent, record_quality_event
from app.services.v4.skeleton_planner import DeckSkeleton, SlideSkeleton

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v4", tags=["V4 Editor"])


# ═══════════════════════════════════════════════════════════════════
# Constants


# ═══════════════════════════════════════════════════════════════════

_TEAM_PHOTO_ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
_TEAM_PHOTO_MAX_BYTES = 8 * 1024 * 1024  # 8 MB
_TEAM_PHOTO_DIR = Path("uploads") / "team_photos"
_MAX_TEAM_MEMBERS = 8
_OPERATION_LEDGER_COLLECTION = "v4_operation_ledger"
_OPERATION_HISTORY_LIMIT = 100
_CLIENT_OPERATION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}$")

# Deck-level regen is heavy; allow at most one per minute per project.
_DECK_REGEN_COOLDOWN_SECONDS = 60
_DISPLAY_REPAIR_ATTEMPTS: dict[str, list[float]] = {}

_REGEN_PROJECT_PROJECTION = {
    "user_id": 1,
    "mode": 1,
    "title": 1,
    "narrative_arc": 1,
    "purpose": 1,
    "company_name": 1,

    "company_icon_url": 1,
    "industry": 1,
    "design_profile": 1,
    "design_tokens": 1,
    "design_system": 1,
    "brand_kit": 1,


    "structured_context": 1,
    "compiled_slides": 1,
    "v4_skeleton": 1,
    "v4_research_snapshot": 1,
    "v4_mode": 1,
    "deck_regenerated_at": 1,
}


# ═══════════════════════════════════════════════════════════════════
# Auth + ownership helpers
# ═══════════════════════════════════════════════════════════════════



async def _load_owned_project(
    db: AsyncIOMotorDatabase,
    project_id: str,
    user: Optional[dict],
    *,
    projection: Optional[dict] = None,


) -> dict:
    user_id = user["user_id"] if user else "dev-test-user"
    proj = await db.presentations.find_one({"_id": project_id}, projection or None)
    if not proj:
        raise HTTPException(status_code=404, detail="project not found")
    owner = proj.get("user_id")
    if owner not in (user_id, "dev-test-user") and user_id != "dev-test-user":
        raise HTTPException(status_code=404, detail="project not found")
    return proj


def _is_premium_user(user: Optional[dict]) -> bool:
    if not user:
        return True  # dev-test-user is treated as premium for local dev
    role = (user or {}).get("role", "guest")
    return role in {"premium", "admin"}


# ═══════════════════════════════════════════════════════════════════
# Slide serialization
# ═══════════════════════════════════════════════════════════════════



def _slide_doc_to_dto(doc: dict) -> dict[str, Any]:
    """Public DTO sent to the frontend. Strips Mongo internals + raw."""
    return {

        "id": str(doc["_id"]),
        "project_id": doc["project_id"],
        "index": doc["index"],
        "intent": doc.get("intent", ""),
        "layout": doc.get("layout", ""),
        "headline": doc.get("headline", ""),
        "subheadline": doc.get("subheadline", "") or "",
        "bullets": list(doc.get("bullets") or []),

        "body": doc.get("body", "") or "",
        "stat_blocks": list(doc.get("stat_blocks") or []),
        "quote": doc.get("quote") or None,
        "chart": doc.get("chart") or None,
        "table": doc.get("table") or None,
        "timeline": doc.get("timeline") or None,
        "comparison": doc.get("comparison") or None,
        "diagram": doc.get("diagram") or None,

        "image_prompt": doc.get("image_prompt") or "",
        "image_url": doc.get("image_url") or None,
        "image_source": doc.get("image_source") or None,
        "image_position": doc.get("image_position") or None,
        "image_intent": doc.get("image_intent") or None,
        "speaker_notes": doc.get("speaker_notes") or "",
        "citations": list(doc.get("citations") or []),
        "render_decision": doc.get("render_decision") or None,
        "team_members": list(doc.get("team_members") or []),
        "requires_user_input": bool(doc.get("requires_user_input", False)),
        "user_input_kind": doc.get("user_input_kind") or None,
        "user_input_reason": doc.get("user_input_reason") or None,
        "company_icon_url": doc.get("company_icon_url"),
        "rationale": doc.get("rationale") or "",

        "purpose": doc.get("purpose") or "",
        "source_model": doc.get("source_model") or None,
        "score": doc.get("score"),
        "version": int(doc.get("version", 1)),
        "updated_at": doc.get("updated_at"),
    }


# ═══════════════════════════════════════════════════════════════════
# GET slides
# ═══════════════════════════════════════════════════════════════════




@router.get("/projects/{project_id}/slides")
async def list_slides(
    project_id: str,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict[str, Any]:
    proj = await _load_owned_project(
        db, project_id, user,
        projection={
            "user_id": 1, "mode": 1, "title": 1, "purpose": 1,

            "narrative_arc": 1, "slide_count": 1, "company_icon_url": 1,
            "intent_summary": 1, "company_name": 1,
        },
    )
    cursor = db.slides.find({
        "$or": [{"project_id": project_id}, {"presentation_id": project_id}]
    }).sort("index", 1)
    docs = await cursor.to_list(length=200)
    return {
        "project": {
            "id": project_id,
            "title": proj.get("title", ""),
            "mode": proj.get("mode", "standard"),
            "purpose": proj.get("purpose", "") or "",
            "narrative_arc": proj.get("narrative_arc", "") or "",
            "slide_count": int(proj.get("slide_count", len(docs))),
            "company_icon_url": proj.get("company_icon_url"),
            "company_name": proj.get("company_name") or None,
            "intent_summary": list(proj.get("intent_summary") or []),
        },
        "slides": [_slide_doc_to_dto(d) for d in docs],
    }


# ═══════════════════════════════════════════════════════════════════
# GET PPTX export (Phase 13 — 80% fidelity static export)
# ═══════════════════════════════════════════════════════════════════


def _safe_filename_slug(value: str, fallback: str = "presentation") -> str:
    """Sanitize a deck title for use in Content-Disposition.

    We strip every char that isn't alphanumeric, hyphen, or underscore
    so the filename is safe across Windows/macOS/Linux and won't
    require quoting. Empty result → fallback.
    """
    s = re.sub(r"[^A-Za-z0-9_\-]+", "_", (value or "").strip())
    s = s.strip("_")[:80]
    return s or fallback


@router.get("/projects/{project_id}/export/pptx")
async def export_project_pptx(
    project_id: str,
    force: bool = False,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> Response:
    """Stream a .pptx export of the v4 deck.

    Sync only — for the typical 8-15 slide deck, building the file is
    well under one second. Larger decks may move to a Celery worker
    later.
    """
    proj = await _load_owned_project(
        db, project_id, user,
        projection={
            "user_id": 1, "title": 1, "design_tokens": 1,
            "company_name": 1, "purpose": 1, "slide_count": 1,
            "export_ready": 1, "quality_state": 1, "export_blockers": 1,
        },
    )
    is_premium = _is_premium_user(user)
    export_ready = proj.get("export_ready", True)
    if not export_ready and not (force and is_premium):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=409,
            content={
                "code": "export_blocked_quality_gate",
                "message": "This deck has unresolved production-quality blockers and cannot be exported.",
                "quality_state": proj.get("quality_state", "blocked"),
                "export_blockers": proj.get("export_blockers", []),
            },
        )

    cursor = db.slides.find({
        "$or": [{"project_id": project_id}, {"presentation_id": project_id}]
    }).sort("index", 1)
    docs = await cursor.to_list(length=200)
    if not docs:
        raise HTTPException(
            status_code=409,
            detail="No slides exist for this project yet — generate the deck first.",
        )

    slide_dtos = [_slide_doc_to_dto(d) for d in docs]
    design_tokens = proj.get("design_tokens") or None
    metadata = {
        "title": proj.get("title") or "",
        "company": proj.get("company_name") or "",
    }

    # Local import — keeps python-pptx out of cold-start path for routes
    # that never export.
    from app.services.v4.pptx_export import V4PptxBuilder

    try:
        builder = V4PptxBuilder()
        pptx_bytes = builder.build(slide_dtos, design_tokens, metadata)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "v4_pptx_export_failed",
            project_id=project_id,
            error=str(exc)[:200],
        )
        raise HTTPException(status_code=500, detail="PPTX export failed") from exc

    fname = _safe_filename_slug(proj.get("title") or "presentation") + ".pptx"
    return Response(
        content=pptx_bytes,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "presentationml.presentation"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{fname}"',
            "Content-Length": str(len(pptx_bytes)),
        },
    )


@router.get("/projects/{project_id}/export/pdf")
async def export_project_pdf(
    project_id: str,
    force: bool = False,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> Response:
    """Stream a .pdf export of the v4 deck.

    Uses V4PDFBuilder which renders compiled slides via Playwright for
    pixel-perfect output. Falls back to a minimal valid PDF if Playwright
    is unavailable in the container.
    """
    proj = await _load_owned_project(
        db, project_id, user,
        projection={
            "user_id": 1, "title": 1, "design_tokens": 1,
            "company_name": 1, "purpose": 1, "slide_count": 1,
            "export_ready": 1, "quality_state": 1, "export_blockers": 1,
        },
    )
    is_premium = _is_premium_user(user)
    export_ready = proj.get("export_ready", True)
    if not export_ready and not (force and is_premium):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=409,
            content={
                "code": "export_blocked_quality_gate",
                "message": "This deck has unresolved production-quality blockers and cannot be exported.",
                "quality_state": proj.get("quality_state", "blocked"),
                "export_blockers": proj.get("export_blockers", []),
            },
        )

    cursor = db.slides.find({
        "$or": [{"project_id": project_id}, {"presentation_id": project_id}]
    }).sort("index", 1)
    docs = await cursor.to_list(length=200)
    if not docs:
        raise HTTPException(
            status_code=409,
            detail="No slides exist for this project yet — generate the deck first.",
        )

    slide_dtos = [_slide_doc_to_dto(d) for d in docs]
    design_tokens = proj.get("design_tokens") or {}
    metadata = {
        "title": proj.get("title") or "",
        "company": proj.get("company_name") or "",
    }

    from app.services.v4.pdf_export import V4PDFBuilder

    try:
        builder = V4PDFBuilder()
        pdf_bytes = await builder.build_async(slide_dtos, design_tokens, metadata)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "v4_pdf_export_failed",
            project_id=project_id,
            error=str(exc)[:200],
        )
        raise HTTPException(status_code=500, detail="PDF export failed") from exc

    fname = _safe_filename_slug(proj.get("title") or "presentation") + ".pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{fname}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.get("/projects/{project_id}/export/docx")
async def export_project_docx(
    project_id: str,
    request: Request,
    force: bool = False,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> Response:
    """Stream a .docx export of the v4 deck.

    Renders screenshots of the compiled slides via Playwright and wraps them
    into a Word document.
    """
    proj = await _load_owned_project(
        db, project_id, user,
        projection={
            "user_id": 1, "title": 1, "design_tokens": 1,
            "company_name": 1, "purpose": 1, "slide_count": 1,
            "export_ready": 1, "quality_state": 1, "export_blockers": 1,
        },
    )
    is_premium = _is_premium_user(user)
    export_ready = proj.get("export_ready", True)
    if not export_ready and not (force and is_premium):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=409,
            content={
                "code": "export_blocked_quality_gate",
                "message": "This deck has unresolved production-quality blockers and cannot be exported.",
                "quality_state": proj.get("quality_state", "blocked"),
                "export_blockers": proj.get("export_blockers", []),
            },
        )

    cursor = db.slides.find({
        "$or": [{"project_id": project_id}, {"presentation_id": project_id}]
    }).sort("index", 1)
    docs = await cursor.to_list(length=200)
    if not docs:
        raise HTTPException(
            status_code=409,
            detail="No slides exist for this project yet — generate the deck first.",
        )

    # Extract auth token from request to pass to screenshot generator
    auth_token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        auth_token = auth_header.split(" ")[1]
    else:
        auth_token = request.cookies.get("barise_auth")

    # Capture screenshots of all slides
    from app.services.v4.slide_screenshot import capture_deck_screenshots
    from app.services.v4.screenshot_exports import build_docx_from_screenshots

    slide_count = len(docs)
    frontend_origin = getattr(settings, "FRONTEND_ORIGIN", None) or "http://localhost:8080"

    try:
        pngs = await capture_deck_screenshots(
            project_id=project_id,
            slide_count=slide_count,
            frontend_origin=frontend_origin,
            auth_token=auth_token,
        )
        if not pngs:
            raise ValueError("Failed to capture slide screenshots")
        docx_bytes = build_docx_from_screenshots(pngs, proj.get("title") or "presentation")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "v4_docx_export_failed",
            project_id=project_id,
            error=str(exc)[:200],
        )
        raise HTTPException(status_code=500, detail="DOCX export failed") from exc

    fname = _safe_filename_slug(proj.get("title") or "presentation") + ".docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{fname}"',
            "Content-Length": str(len(docx_bytes)),
        },
    )


@router.get("/projects/{project_id}/export/json")
async def export_project_json(
    project_id: str,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> Response:
    """Export the full v4 deck as lossless JSON.

    Useful for backups, migration, and version control. Returns every
    slide DTO plus project metadata as a single JSON document.
    """
    proj = await _load_owned_project(
        db, project_id, user,
        projection={
            "user_id": 1, "title": 1, "design_tokens": 1,
            "company_name": 1, "purpose": 1, "slide_count": 1,
            "narrative_arc": 1, "industry": 1,
        },
    )
    cursor = db.slides.find({
        "$or": [{"project_id": project_id}, {"presentation_id": project_id}]
    }).sort("index", 1)
    docs = await cursor.to_list(length=200)
    if not docs:
        raise HTTPException(
            status_code=409,
            detail="No slides exist for this project yet — generate the deck first.",
        )

    slide_dtos = [_slide_doc_to_dto(d) for d in docs]
    export_payload = {
        "project_id": project_id,
        "title": proj.get("title") or "",
        "company_name": proj.get("company_name") or "",
        "purpose": proj.get("purpose") or "",
        "narrative_arc": proj.get("narrative_arc") or "",
        "industry": proj.get("industry") or "",
        "design_tokens": proj.get("design_tokens") or {},
        "slide_count": len(slide_dtos),
        "slides": slide_dtos,
    }

    export_json = json.dumps(export_payload, default=str, ensure_ascii=False)
    fname = _safe_filename_slug(proj.get("title") or "presentation") + ".barise.json"
    return Response(
        content=export_json.encode("utf-8"),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{fname}"',
            "Content-Length": str(len(export_json.encode("utf-8"))),
        },
    )


# ═══════════════════════════════════════════════════════════════════
# PATCH slide (partial edit)
# ═══════════════════════════════════════════════════════════════════


class _ReorderSlidesBody(BaseModel):
    # Existing slide indexes in the desired visual order. Indexes are
    # stable identifiers for the current persisted deck during this call;
    # the route rewrites them to 0..N-1 after validation.
    order: list[int] = Field(..., min_length=1, max_length=200)


def _validated_reorder(order: list[int], existing_indices: list[int]) -> list[int]:
    normalized = [int(i) for i in order]
    expected = set(existing_indices)
    actual = set(normalized)
    if len(normalized) != len(existing_indices):
        raise ValueError("order must include every slide exactly once")
    if len(actual) != len(normalized):
        raise ValueError("order contains duplicate slide indexes")
    if actual != expected:
        unknown = sorted(actual - expected)
        missing = sorted(expected - actual)
        detail = []
        if unknown:
            detail.append(f"unknown={unknown[:8]}")
        if missing:
            detail.append(f"missing={missing[:8]}")
        suffix = f" ({'; '.join(detail)})" if detail else ""
        raise ValueError(f"order does not match current slides{suffix}")
    return normalized


def _reindex_skeleton(v4_skeleton: Any, order: list[int]) -> Any:
    if not isinstance(v4_skeleton, dict) or not isinstance(v4_skeleton.get("slides"), list):
        return v4_skeleton
    slides = v4_skeleton.get("slides") or []
    by_index: dict[int, dict[str, Any]] = {}
    for fallback_index, slide in enumerate(slides):
        if not isinstance(slide, dict):
            continue
        raw_index = slide.get("index", fallback_index)
        if isinstance(raw_index, bool):
            continue
        try:
            by_index[int(raw_index)] = slide
        except (TypeError, ValueError):
            continue
    if set(by_index) != set(order):
        return v4_skeleton

    next_skeleton = copy.deepcopy(v4_skeleton)
    next_skeleton["slides"] = [
        {**copy.deepcopy(by_index[old_index]), "index": new_index}
        for new_index, old_index in enumerate(order)
    ]
    return next_skeleton


def _reindex_compiled_slides(compiled_slides: list[Any], order: list[int]) -> list[dict[str, Any]]:
    by_index: dict[int, dict[str, Any]] = {}
    for fallback_index, slide in enumerate(compiled_slides):
        if not isinstance(slide, dict):
            continue
        raw_index = slide.get("slide_index", fallback_index)
        if isinstance(raw_index, bool):
            continue
        try:
            by_index[int(raw_index)] = slide
        except (TypeError, ValueError):
            continue
    if set(by_index) != set(order):
        raise ValueError("compiled slide order is out of sync with slide documents")

    reordered: list[dict[str, Any]] = []
    for new_index, old_index in enumerate(order):
        slide = copy.deepcopy(by_index[old_index])
        slide["slide_index"] = new_index
        reordered.append(slide)
    return reordered


@router.patch("/projects/{project_id}/slides/reorder")
async def reorder_slides(
    project_id: str,
    body: _ReorderSlidesBody,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict[str, Any]:
    proj = await _load_owned_project(
        db,
        project_id,
        user,
        projection={
            "user_id": 1,
            "compiled_slides": 1,
            "v4_skeleton": 1,
            "intent_summary": 1,
        },
    )
    slide_docs = await db.slides.find({
        "$or": [{"project_id": project_id}, {"presentation_id": project_id}]
    }).sort("index", 1).to_list(length=200)
    if not slide_docs:
        raise HTTPException(status_code=409, detail="No slides exist for this project yet.")

    existing_indices = [int(doc.get("index", i)) for i, doc in enumerate(slide_docs)]
    try:
        order = _validated_reorder(body.order, existing_indices)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    old_position = {old_index: new_index for new_index, old_index in enumerate(order)}
    if all(old_position.get(idx) == pos for pos, idx in enumerate(existing_indices)):
        return {
            "ok": True,
            "order": order,
            "slides": [_slide_doc_to_dto(doc) for doc in slide_docs],
            "noop": True,
        }

    compiled_slides = list(proj.get("compiled_slides") or [])
    if compiled_slides:
        try:
            next_compiled_slides = _reindex_compiled_slides(compiled_slides, order)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    else:
        next_compiled_slides = []

    now = datetime.now(timezone.utc)
    by_index = {int(doc.get("index", i)): doc for i, doc in enumerate(slide_docs)}
    updated_docs: list[dict[str, Any]] = []
    for new_index, old_index in enumerate(order):
        doc = by_index[old_index]
        await db.slides.update_one(
            {"_id": doc["_id"]},
            {"$set": {"index": new_index, "updated_at": now}},
        )
        updated_docs.append({**doc, "index": new_index, "updated_at": now})

    set_doc: dict[str, Any] = {
        "updated_at": now,
        "slide_count": len(updated_docs),
    }
    if compiled_slides:
        set_doc["compiled_slides"] = next_compiled_slides
    next_skeleton = _reindex_skeleton(proj.get("v4_skeleton"), order)
    if next_skeleton is not proj.get("v4_skeleton"):
        set_doc["v4_skeleton"] = next_skeleton
    intent_summary = list(proj.get("intent_summary") or [])
    if len(intent_summary) == len(order) and all(0 <= old_index < len(intent_summary) for old_index in order):
        set_doc["intent_summary"] = [intent_summary[old_index] for old_index in order]

    await db.presentations.update_one({"_id": project_id}, {"$set": set_doc})

    try:
        from app.services.v4.content_pipeline import make_redis_progress_emitter
        emit = make_redis_progress_emitter(project_id)
        await emit("slides_reordered", {
            "order": order,
            "slide_count": len(updated_docs),
            "compiled": bool(compiled_slides),
        })
    except Exception as e:  # noqa: BLE001
        logger.warning("v4_reorder_emit_failed", project_id=project_id, error=str(e))

    logger.info("v4_editor.reorder_slides", project_id=project_id, order=order)
    return {
        "ok": True,
        "order": order,
        "slides": [_slide_doc_to_dto(doc) for doc in updated_docs],
        "noop": False,
    }


class _SlidePatch(BaseModel):
    expected_slide_version: Optional[int] = Field(default=None, ge=1)
    headline: Optional[str] = None
    subheadline: Optional[str] = None
    bullets: Optional[list[str]] = None
    body: Optional[str] = None
    speaker_notes: Optional[str] = None
    layout: Optional[str] = None
    image_prompt: Optional[str] = None
    stat_blocks: Optional[list[dict[str, Any]]] = None
    quote: Optional[dict[str, Any]] = None
    chart: Optional[dict[str, Any]] = None
    table: Optional[dict[str, Any]] = None
    timeline: Optional[dict[str, Any]] = None
    comparison: Optional[dict[str, Any]] = None
    diagram: Optional[dict[str, Any]] = None
    team_members: Optional[list[dict[str, Any]]] = None
    requires_user_input: Optional[bool] = None
    user_input_kind: Optional[str] = None
    user_input_reason: Optional[str] = None
    company_icon_url: Optional[str] = None
    # Frontend-friendly aliases (mapped to canonical names below).
    title: Optional[str] = None
    notes: Optional[str] = None


# Editor-side layout vocabulary. MUST stay aligned with
# `skeleton_planner._CANONICAL_LAYOUTS` so any layout the V4 generator
# legitimately emits can also be set via PATCH. We additionally accept
# a few legacy aliases (`title`, `bullets`, `chart`, `stat-grid`,
# `three-column`, `image-left`, `image-right`, `team`) that older
# frontends still send.
_ALLOWED_LAYOUTS = {
    # Canonical V4 layouts (skeleton_planner._CANONICAL_LAYOUTS)
    "title-only", "two-column", "stat-hero", "grid-3", "chart-focus",
    "image-full", "quote", "comparison", "timeline", "table",
    "diagram", "process", "bullet-points", "auto",
    # Legacy aliases kept for backward compatibility with older
    # frontend callers and editor UIs.
    "title", "three-column", "bullets", "stat-grid", "chart",
    "image-left", "image-right", "team",
}


def _slide_version_conflict_detail(
    *,
    project_id: str,
    slide_no: int,
    expected_slide_version: int | None,
    current_slide: dict[str, Any] | None,
) -> dict[str, Any]:
    current_version = None
    current_slide_id = None
    current_slide_dto = None
    if current_slide:
        current_version = int(current_slide.get("version", 1))
        current_slide_id = str(current_slide.get("_id"))
        current_slide_dto = _slide_doc_to_dto(current_slide)
    return {
        "code": "stale_slide_version",
        "message": "Slide changed since this edit started. Reload the latest slide before saving again.",
        "project_id": project_id,
        "slide_index": slide_no,
        "slide_id": current_slide_id,
        "expected_slide_version": expected_slide_version,
        "current_slide_version": current_version,
        "current_slide": current_slide_dto,
    }


def _artifact_version_conflict_detail(
    *,
    project_id: str,
    slide_no: int,
    expected_artifact_version: int | None,
    current_slide: dict[str, Any] | None,
) -> dict[str, Any]:
    current_version = None
    current_slide_id = None
    if isinstance(current_slide, dict):
        value = current_slide.get("artifact_version")
        current_version = value if isinstance(value, int) else None
        current_slide_id = current_slide.get("slide_id")
    return {
        "code": "stale_artifact_version",
        "message": "Preview changed since this edit started. Reload the latest slide before saving again.",
        "project_id": project_id,
        "slide_index": slide_no,
        "current_slide_id": current_slide_id,
        "expected_artifact_version": expected_artifact_version,
        "current_artifact_version": current_version,
        "current_slide": current_slide if isinstance(current_slide, dict) else None,
    }


async def _snapshot_slide(db: AsyncIOMotorDatabase, slide: dict, change_type: str) -> None:
    try:
        await db.slide_versions.insert_one({
            "_id": str(ObjectId()),
            "slide_id": str(slide["_id"]),
            "project_id": slide["project_id"],
            "index": slide.get("index"),
            "version": int(slide.get("version", 1)),
            "snapshot": {
                k: slide.get(k)
                for k in (
                    "headline", "subheadline", "bullets", "body", "stat_blocks",
                    "quote", "chart", "table", "timeline", "comparison", "diagram",
                    "image_prompt", "speaker_notes", "citations", "layout",
                    "team_members", "requires_user_input", "user_input_kind",
                    "user_input_reason", "company_icon_url", "rationale", "purpose",
                )
            },
            "change_type": change_type,
            "created_at": datetime.now(timezone.utc),
        })
    except Exception as e:  # noqa: BLE001 — never let snapshotting kill the write
        logger.warning("v4_editor.snapshot_failed", error=str(e))


@router.patch("/projects/{project_id}/slides/{slide_no}")
async def patch_slide(
    project_id: str,
    slide_no: int,
    body: _SlidePatch,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict[str, Any]:
    proj = await _load_owned_project(
        db,
        project_id,
        user,
        projection={
            "user_id": 1,
            "mode": 1,
            "compiled_slides": 1,
            "title": 1,
            "company_icon_url": 1,
        },
    )

    slide = await db.slides.find_one({
        "$or": [{"project_id": project_id}, {"presentation_id": project_id}],
        "index": slide_no,
    })
    if not slide:
        raise HTTPException(status_code=404, detail=f"slide {slide_no} not found")

    expected_slide_version = body.expected_slide_version
    current_slide_version = int(slide.get("version", 1))
    if expected_slide_version is not None and expected_slide_version != current_slide_version:
        raise HTTPException(
            status_code=409,
            detail=_slide_version_conflict_detail(
                project_id=project_id,
                slide_no=slide_no,
                expected_slide_version=expected_slide_version,
                current_slide=slide,
            ),
        )

    patch: dict[str, Any] = body.model_dump(exclude_none=True)
    patch.pop("expected_slide_version", None)
    # Frontend aliases → canonical
    if "title" in patch and "headline" not in patch:
        patch["headline"] = patch.pop("title")
    else:
        patch.pop("title", None)
    if "notes" in patch and "speaker_notes" not in patch:
        patch["speaker_notes"] = patch.pop("notes")
    else:
        patch.pop("notes", None)

    if not patch:
        raise HTTPException(status_code=400, detail="empty patch")

    # Defensive validation
    if "headline" in patch:
        patch["headline"] = str(patch["headline"]).strip()[:240]
    if "subheadline" in patch:
        patch["subheadline"] = str(patch["subheadline"]).strip()[:320]
    if "bullets" in patch:
        bs = [str(b).strip()[:280] for b in (patch["bullets"] or []) if str(b).strip()]
        patch["bullets"] = bs[:8]
    if "body" in patch:
        patch["body"] = str(patch["body"])[:4000]
    if "speaker_notes" in patch:
        patch["speaker_notes"] = str(patch["speaker_notes"])[:4000]
    if "layout" in patch and patch["layout"] not in _ALLOWED_LAYOUTS:
        raise HTTPException(
            status_code=422,
            detail=f"invalid layout; allowed={sorted(_ALLOWED_LAYOUTS)}",
        )
    if "team_members" in patch:
        if not isinstance(patch["team_members"], list):
            raise HTTPException(status_code=422, detail="team_members must be a list")
        patch["team_members"] = patch["team_members"][:_MAX_TEAM_MEMBERS]
        if patch["team_members"]:
            patch["requires_user_input"] = False
            patch["user_input_kind"] = None
            patch["user_input_reason"] = None
    if patch.get("requires_user_input") is False:
        patch.setdefault("user_input_kind", None)
        patch.setdefault("user_input_reason", None)

    patch["updated_at"] = datetime.now(timezone.utc)
    new_version = current_slide_version + 1
    patch["version"] = new_version

    compiled_refresh: dict[str, Any] | None = None
    compiled_artifact_version: int | None = None
    compiled_slides = list(proj.get("compiled_slides") or [])
    target_pos = _compiled_slide_position(compiled_slides, slide_no)
    if target_pos >= 0:
        existing_compiled = compiled_slides[target_pos] if isinstance(compiled_slides[target_pos], dict) else {}
        from app.services.v4.slide_compiler import compile_slide

        candidate_slide = {**slide, **patch}
        compiled_refresh = compile_slide(
            slide=_generated_slide_from_doc(candidate_slide),
            image_url=candidate_slide.get("image_url") or None,
            deck_title=proj.get("title") or None,
            company_icon_url=proj.get("company_icon_url") or candidate_slide.get("company_icon_url") or None,
        )
        compiled_refresh["artifact_version"] = _next_artifact_version(existing_compiled)
        if isinstance(existing_compiled, dict) and existing_compiled.get("design_system_version"):
            compiled_refresh["design_system_version"] = existing_compiled.get("design_system_version")
        compiled_artifact_version = compiled_refresh.get("artifact_version") if isinstance(compiled_refresh.get("artifact_version"), int) else None

    updated = await db.slides.find_one_and_update(
        {"_id": slide["_id"], "version": current_slide_version},
        {"$set": patch},
        return_document=True,
    )
    if not updated:
        latest = await db.slides.find_one({"_id": slide["_id"]})
        raise HTTPException(
            status_code=409,
            detail=_slide_version_conflict_detail(
                project_id=project_id,
                slide_no=slide_no,
                expected_slide_version=expected_slide_version or current_slide_version,
                current_slide=latest,
            ),
        )

    await _snapshot_slide(db, slide, "patch")

    if compiled_refresh is not None and target_pos >= 0:
        await db.presentations.update_one(
            {"_id": project_id},
            {"$set": {
                f"compiled_slides.{target_pos}": compiled_refresh,
                "updated_at": datetime.now(timezone.utc),
            }},
        )

    # Bump presentation updated_at so list views re-render.
    await db.presentations.update_one(
        {"_id": project_id},
        {"$set": {"updated_at": datetime.now(timezone.utc)}},
    )

    logger.info(
        "v4_editor.patch_slide",
        project_id=project_id, slide_no=slide_no, fields=list(patch.keys()),
        version=new_version, artifact_version=compiled_artifact_version,
    )
    try:
        from app.services.v4.content_pipeline import make_redis_progress_emitter
        emit = make_redis_progress_emitter(project_id)
        await emit("slide_updated", {
            "slide_id": f"slide-{int(updated.get('index', slide_no)):03d}",
            "slide_index": updated.get("index", slide_no),
            "version": new_version,
            "artifact_version": compiled_artifact_version,
            "fields_changed": sorted(k for k in patch.keys() if k not in {"updated_at", "version"}),
            "trigger": "slide_patch",
        })
    except Exception as e:  # noqa: BLE001
        logger.warning("v4_slide_patch_emit_failed", project_id=project_id, error=str(e))
    return {"ok": True, "slide": _slide_doc_to_dto(updated)}


# ═══════════════════════════════════════════════════════════════════
# Phase 8 — thin-slice edit ops on compiled artifacts
# ═══════════════════════════════════════════════════════════════════
#
# The classic PATCH above mutates the GeneratedSlide-shaped doc in
# `db.slides` and requires a downstream re-compile to refresh the
# rendered artifacts. The slice endpoint below is the fast path: it
# edits a single leaf inside the already-compiled `kit_jsx.props_json`
# stored on `presentations.compiled_slides[i]`, recompiles only the
# four artifacts for that one slide, re-scores quality, bumps
# `artifact_version`, and emits a `slide_updated` WS event so the
# editor refreshes in place.
#
# No LLM call. No paid API. The user's value is preserved verbatim.


class _SliceOp(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    path: str = Field(..., min_length=1, max_length=200)
    value: Any = None
    op: Optional[str] = Field(default="replace", max_length=32)
    from_path: Optional[str] = Field(default=None, alias="from", max_length=200)


class _SlicePatch(BaseModel):
    expected_artifact_version: Optional[int] = Field(default=None, ge=1)
    operation_id: Optional[str] = Field(default=None, min_length=1, max_length=120)
    client_id: Optional[str] = Field(default=None, min_length=1, max_length=120)
    ops: list[_SliceOp] = Field(..., min_length=1, max_length=25)


class _ElementRegenerateBody(BaseModel):
    expected_artifact_version: Optional[int] = Field(default=None, ge=1)
    operation_id: Optional[str] = Field(default=None, min_length=1, max_length=120)
    client_id: Optional[str] = Field(default=None, min_length=1, max_length=120)
    path: str = Field(..., min_length=1, max_length=200)
    kind: Optional[str] = Field(default=None, max_length=40)
    instruction: Optional[str] = Field(default=None, max_length=600)


class _CompiledHistoryMoveBody(BaseModel):
    expected_artifact_version: Optional[int] = Field(default=None, ge=1)
    operation_id: Optional[str] = Field(default=None, min_length=1, max_length=120)
    client_id: Optional[str] = Field(default=None, min_length=1, max_length=120)


class _DisplayRepairBody(BaseModel):
    issue_code: Optional[str] = Field(default=None, max_length=80)
    source: Optional[str] = Field(default="preview", max_length=80)


def _compiled_slide_position(compiled_slides: list[Any], slide_no: int) -> int:
    for i, cs in enumerate(compiled_slides):
        if not isinstance(cs, dict):
            continue
        idx = cs.get("slide_index")
        if isinstance(idx, int) and idx == slide_no:
            return i
    if 0 <= slide_no < len(compiled_slides):
        return slide_no
    return -1


def _operation_user_id(user: dict | None) -> str:
    if not user:
        return "dev-test-user"
    value = user.get("user_id") or user.get("sub") or user.get("id")
    return str(value or "anonymous")[:160]


def _validate_client_operation_id(value: str | None, *, field: str) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not _CLIENT_OPERATION_ID_RE.match(trimmed):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_operation_id",
                "field": field,
                "message": f"{field} must start with an alphanumeric character and contain only letters, numbers, '.', ':', '_' or '-'.",
            },
        )
    return trimmed


def _new_operation_id(prefix: str, supplied: str | None = None) -> str:
    checked = _validate_client_operation_id(supplied, field="operation_id")
    return checked or f"{prefix}:{ObjectId()}"


def _ledger_collection(db: AsyncIOMotorDatabase):
    return db[_OPERATION_LEDGER_COLLECTION]


async def _ensure_operation_id_available(db: AsyncIOMotorDatabase, operation_id: str) -> None:
    existing = await _ledger_collection(db).find_one({"_id": operation_id}, {"_id": 1})
    if existing:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "duplicate_operation_id",
                "operation_id": operation_id,
                "message": "This edit operation was already recorded. Reload history before retrying.",
            },
        )


def _compiled_snapshot_hash(slide: dict[str, Any]) -> str:
    raw = json.dumps(slide, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _summarize_operation(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation_id": doc.get("_id") or doc.get("operation_id"),
        "trigger": doc.get("trigger"),
        "project_id": doc.get("project_id"),
        "slide_id": doc.get("slide_id"),
        "slide_index": doc.get("slide_index"),
        "client_id": doc.get("client_id"),
        "user_id": doc.get("user_id"),
        "fields_changed": list(doc.get("fields_changed") or []),
        "before_artifact_version": doc.get("before_artifact_version"),
        "after_artifact_version": doc.get("after_artifact_version"),
        "before_hash": doc.get("before_hash"),
        "after_hash": doc.get("after_hash"),
        "undo_of": doc.get("undo_of"),
        "redo_of": doc.get("redo_of"),
        "undone_at": doc.get("undone_at"),
        "redone_at": doc.get("redone_at"),
        "invalidated_at": doc.get("invalidated_at"),
        "created_at": doc.get("created_at"),
    }


async def _insert_operation_ledger_entry(
    db: AsyncIOMotorDatabase,
    *,
    operation_id: str,
    project_id: str,
    slide_id: str | None,
    slide_index: int | None,
    before_slide: dict[str, Any],
    after_slide: dict[str, Any],
    trigger: str,
    user_id: str,
    client_id: str,
    fields_changed: list[str],
    ops: list[dict[str, Any]] | None = None,
    undo_of: str | None = None,
    redo_of: str | None = None,
) -> dict[str, Any]:
    before_version = before_slide.get("artifact_version") if isinstance(before_slide, dict) else None
    after_version = after_slide.get("artifact_version") if isinstance(after_slide, dict) else None
    doc = {
        "_id": operation_id,
        "operation_id": operation_id,
        "project_id": project_id,
        "slide_id": slide_id,
        "slide_index": slide_index,
        "trigger": trigger,
        "user_id": user_id,
        "client_id": client_id,
        "fields_changed": fields_changed,
        "ops": ops or [],
        "before_artifact_version": before_version,
        "after_artifact_version": after_version,
        "before_hash": _compiled_snapshot_hash(before_slide),
        "after_hash": _compiled_snapshot_hash(after_slide),
        "before_compiled_slide": copy.deepcopy(before_slide),
        "after_compiled_slide": copy.deepcopy(after_slide),
        "undo_of": undo_of,
        "redo_of": redo_of,
        "created_at": datetime.now(timezone.utc),
    }
    await _ledger_collection(db).insert_one(doc)
    return doc


async def _invalidate_redo_stack(
    db: AsyncIOMotorDatabase,
    *,
    project_id: str,
    slide_id: str | None,
    slide_index: int | None,
    operation_id: str,
) -> None:
    query: dict[str, Any] = {
        "project_id": project_id,
        "trigger": "undo",
        "redone_at": {"$exists": False},
        "invalidated_at": {"$exists": False},
    }
    if slide_id:
        query["slide_id"] = slide_id
    elif slide_index is not None:
        query["slide_index"] = slide_index
    await _ledger_collection(db).update_many(
        query,
        {"$set": {
            "invalidated_at": datetime.now(timezone.utc),
            "invalidated_by": operation_id,
        }},
    )


async def _find_last_undoable_operation(
    db: AsyncIOMotorDatabase,
    *,
    project_id: str,
    slide_id: str | None,
    slide_index: int | None,
) -> dict[str, Any] | None:
    query: dict[str, Any] = {
        "project_id": project_id,
        "trigger": {"$in": ["slice_edit", "element_regenerate", "redo"]},
        "undone_at": {"$exists": False},
    }
    if slide_id:
        query["slide_id"] = slide_id
    elif slide_index is not None:
        query["slide_index"] = slide_index
    docs = await _ledger_collection(db).find(query).sort("created_at", -1).limit(1).to_list(length=1)
    return docs[0] if docs else None


async def _find_last_redoable_operation(
    db: AsyncIOMotorDatabase,
    *,
    project_id: str,
    slide_id: str | None,
    slide_index: int | None,
) -> dict[str, Any] | None:
    query: dict[str, Any] = {
        "project_id": project_id,
        "trigger": "undo",
        "redone_at": {"$exists": False},
        "invalidated_at": {"$exists": False},
    }
    if slide_id:
        query["slide_id"] = slide_id
    elif slide_index is not None:
        query["slide_index"] = slide_index
    docs = await _ledger_collection(db).find(query).sort("created_at", -1).limit(1).to_list(length=1)
    return docs[0] if docs else None


async def _compiled_history_flags(
    db: AsyncIOMotorDatabase,
    *,
    project_id: str,
    slide_id: str | None,
    slide_index: int | None,
) -> dict[str, bool]:
    undoable = await _find_last_undoable_operation(
        db,
        project_id=project_id,
        slide_id=slide_id,
        slide_index=slide_index,
    )
    redoable = await _find_last_redoable_operation(
        db,
        project_id=project_id,
        slide_id=slide_id,
        slide_index=slide_index,
    )
    return {"can_undo": undoable is not None, "can_redo": redoable is not None}


def _history_position_conflict_detail(
    *,
    project_id: str,
    slide_no: int,
    expected_artifact_version: int | None,
    required_artifact_version: int | None,
    current_slide: dict[str, Any] | None,
    action: str,
) -> dict[str, Any]:
    detail = _artifact_version_conflict_detail(
        project_id=project_id,
        slide_no=slide_no,
        expected_artifact_version=expected_artifact_version,
        current_slide=current_slide,
    )
    detail["code"] = "stale_history_position"
    detail["message"] = f"Cannot {action}; the slide has changed since that history entry was created."
    detail["required_artifact_version"] = required_artifact_version
    return detail


async def _emit_compiled_history_update(
    project_id: str,
    *,
    slide: dict[str, Any],
    fields_changed: list[str],
    trigger: str,
) -> None:
    try:
        from app.services.v4.content_pipeline import make_redis_progress_emitter
        emit = make_redis_progress_emitter(project_id)
        await emit("slide_updated", {
            "slide_id": slide.get("slide_id"),
            "slide_index": slide.get("slide_index"),
            "artifact_version": slide.get("artifact_version"),
            "fields_changed": fields_changed,
            "quality_score": slide.get("quality_score"),
            "trigger": trigger,
        })
    except Exception as e:  # noqa: BLE001
        logger.warning("v4_compiled_history_emit_failed", project_id=project_id, error=str(e))


async def _repair_attempt_allowed(
    db: AsyncIOMotorDatabase,
    key: str,
    *,
    max_attempts: int = 1,
    window_s: float = 300.0,
    project_id: str | None = None,
    slide_no: int | None = None,
    issue_code: str | None = None,
    repair_type: str | None = None,
) -> bool:
    try:
        collection = db[settings.QUALITY_METRICS_COLLECTION]
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_s)
        count = await collection.count_documents({
            "event": "display_repair_attempt",
            "tags.circuit_key": key,
            "created_at": {"$gte": cutoff},
        })
        if count >= max_attempts:
            return False
        await collection.insert_one({
            "event": "display_repair_attempt",
            "project_id": project_id,
            "gate": "display_runtime",
            "severity": "info",
            "metric_value": float(count + 1),
            "tags": {
                "circuit_key": key,
                "slide_index": slide_no,
                "issue_code": issue_code or "manual",
                "repair_type": repair_type or "unknown",
            },
            "payload": {},
            "created_at": datetime.now(timezone.utc),
        })
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("v4_display_repair_attempt_metric_failed", key=key, error=str(exc))

    now = time.monotonic()
    entries = [t for t in _DISPLAY_REPAIR_ATTEMPTS.get(key, []) if now - t <= window_s]
    if len(entries) >= max_attempts:
        _DISPLAY_REPAIR_ATTEMPTS[key] = entries
        return False
    entries.append(now)
    _DISPLAY_REPAIR_ATTEMPTS[key] = entries
    return True


def _generated_slide_from_doc(doc: dict[str, Any]) -> GeneratedSlide:
    return GeneratedSlide(
        index=int(doc.get("index", 0)),
        intent=str(doc.get("intent", "")),
        layout=str(doc.get("layout", "")),
        headline=str(doc.get("headline", "")),
        subheadline=doc.get("subheadline") or None,
        bullets=list(doc.get("bullets") or []),
        body=doc.get("body") or None,
        stat_blocks=list(doc.get("stat_blocks") or []),
        quote=doc.get("quote") or None,
        chart=doc.get("chart") or None,
        table=doc.get("table") or None,
        timeline=doc.get("timeline") or None,
        comparison=doc.get("comparison") or None,
        diagram=doc.get("diagram") or None,
        image_prompt=doc.get("image_prompt") or None,
        image_url=doc.get("image_url") or None,
        image_source=doc.get("image_source") or None,
        image_position=doc.get("image_position") or None,
        image_intent=doc.get("image_intent") or None,
        speaker_notes=doc.get("speaker_notes") or None,
        citations=list(doc.get("citations") or []),
        raw=dict(doc.get("raw") or {}),
        render_decision=doc.get("render_decision") or None,
        team_members=list(doc.get("team_members") or []),
        requires_user_input=bool(doc.get("requires_user_input", False)),
        user_input_kind=doc.get("user_input_kind") or None,
        user_input_reason=doc.get("user_input_reason") or None,
        company_icon_url=doc.get("company_icon_url") or None,
        rationale=str(doc.get("rationale") or ""),
        purpose=str(doc.get("purpose") or ""),
    )


async def _emit_display_repair(
    project_id: str,
    stage: str,
    payload: dict[str, Any],
) -> None:
    try:
        from app.services.v4.content_pipeline import make_redis_progress_emitter
        emit = make_redis_progress_emitter(project_id)
        await emit(stage, payload)
    except Exception as e:  # noqa: BLE001
        logger.warning("v4_display_repair_emit_failed", project_id=project_id, stage=stage, error=str(e))


async def _persist_recompiled_slide(
    *,
    db: AsyncIOMotorDatabase,
    project_id: str,
    compiled_slides: list[Any],
    target_pos: int,
    compiled: dict[str, Any],
) -> None:
    array_key = f"compiled_slides.{target_pos}"
    await db.presentations.update_one(
        {"_id": project_id},
        {"$set": {array_key: compiled, "updated_at": datetime.now(timezone.utc)}},
    )
    if 0 <= target_pos < len(compiled_slides):
        compiled_slides[target_pos] = compiled


def _next_artifact_version(existing: dict[str, Any] | None) -> int:
    current = existing.get("artifact_version") if isinstance(existing, dict) else None
    if not isinstance(current, int) or current < 1:
        current = 1
    return current + 1


@router.patch("/projects/{project_id}/slides/{slide_no}/slice")
async def patch_slide_slice(
    project_id: str,
    slide_no: int,
    body: _SlicePatch,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict[str, Any]:
    proj = await _load_owned_project(
        db, project_id, user,
        projection={
            "user_id": 1,
            "compiled_slides": 1,
            "design_tokens": 1,
        },
    )
    compiled_slides = list(proj.get("compiled_slides") or [])
    if not compiled_slides:
        raise HTTPException(status_code=409, detail="deck has not been compiled yet")

    # Resolve the slide by either `slide_index` or `index`. We accept
    # numeric `slide_no` as the public API; underlying compiled_slides
    # index by `slide_index`.
    target_pos = -1
    for i, cs in enumerate(compiled_slides):
        if not isinstance(cs, dict):
            continue
        idx = cs.get("slide_index")
        if isinstance(idx, int) and idx == slide_no:
            target_pos = i
            break
    if target_pos == -1 and 0 <= slide_no < len(compiled_slides):
        target_pos = slide_no
    if target_pos == -1:
        raise HTTPException(status_code=404, detail=f"compiled slide {slide_no} not found")

    target_slide = compiled_slides[target_pos]
    current_artifact_version = target_slide.get("artifact_version") if isinstance(target_slide, dict) else None
    if not isinstance(current_artifact_version, int) or current_artifact_version < 1:
        current_artifact_version = 1
    before_slide = copy.deepcopy(target_slide) if isinstance(target_slide, dict) else {}
    expected_artifact_version = body.expected_artifact_version
    if expected_artifact_version is not None and expected_artifact_version != current_artifact_version:
        raise HTTPException(
            status_code=409,
            detail=_artifact_version_conflict_detail(
                project_id=project_id,
                slide_no=slide_no,
                expected_artifact_version=expected_artifact_version,
                current_slide=target_slide if isinstance(target_slide, dict) else None,
            ),
        )
    operation_id = _new_operation_id("slice", body.operation_id)
    await _ensure_operation_id_available(db, operation_id)
    client_id = _validate_client_operation_id(body.client_id, field="client_id") or "server"
    ops_dicts = [op.model_dump(exclude_none=False) for op in body.ops]
    design_tokens = proj.get("design_tokens") or {}

    # Local import — keeps the router cheap to import in tests that
    # don't hit this endpoint.
    from app.services.v4.slice_editor import apply_slice_ops, SliceEditError

    try:
        result = apply_slice_ops(
            slide=target_slide,
            ops=ops_dicts,
            design_tokens=design_tokens,
        )
    except SliceEditError as e:
        raise HTTPException(
            status_code=422,
            detail={"code": e.code, "path": e.path, "message": str(e)},
        )

    # Persist the mutated slide back into the array. We use a
    # positional `$set` on the exact array index so concurrent edits
    # to other slides don't get clobbered. The artifact_version predicate
    # is the race-after-check guard recommended by MongoDB's atomic update
    # docs: if another editor changed this same compiled artifact after we
    # read it, this write no longer matches and becomes a 409.
    array_key = f"compiled_slides.{target_pos}"
    update_result = await db.presentations.update_one(
        {
            "_id": project_id,
            f"compiled_slides.{target_pos}.slide_id": target_slide.get("slide_id"),
            f"compiled_slides.{target_pos}.artifact_version": current_artifact_version,
        },
        {"$set": {
            array_key: target_slide,
            "updated_at": datetime.now(timezone.utc),
        }},
    )
    if getattr(update_result, "matched_count", 1) == 0:
        latest_proj = await db.presentations.find_one(
            {"_id": project_id},
            {"compiled_slides": 1},
        )
        latest_slides = list((latest_proj or {}).get("compiled_slides") or [])
        latest_pos = _compiled_slide_position(latest_slides, slide_no)
        latest_slide = latest_slides[latest_pos] if latest_pos >= 0 else None
        raise HTTPException(
            status_code=409,
            detail=_artifact_version_conflict_detail(
                project_id=project_id,
                slide_no=slide_no,
                expected_artifact_version=expected_artifact_version or current_artifact_version,
                current_slide=latest_slide if isinstance(latest_slide, dict) else None,
            ),
        )

    if not result.get("noop"):
        await _invalidate_redo_stack(
            db,
            project_id=project_id,
            slide_id=target_slide.get("slide_id"),
            slide_index=target_slide.get("slide_index"),
            operation_id=operation_id,
        )
        await _insert_operation_ledger_entry(
            db,
            operation_id=operation_id,
            project_id=project_id,
            slide_id=target_slide.get("slide_id"),
            slide_index=target_slide.get("slide_index"),
            before_slide=before_slide,
            after_slide=copy.deepcopy(target_slide),
            trigger="slice_edit",
            user_id=_operation_user_id(user),
            client_id=client_id,
            fields_changed=list(result.get("fields_changed") or []),
            ops=ops_dicts,
        )

    # Emit `slide_updated` over the existing v4 progress channel so
    # any open editor sandbox refreshes in place.
    if not result.get("noop"):
        try:
            from app.services.v4.content_pipeline import make_redis_progress_emitter
            emit = make_redis_progress_emitter(project_id)
            await emit("slide_updated", {
                "slide_id": target_slide.get("slide_id"),
                "slide_index": target_slide.get("slide_index"),
                "artifact_version": result["artifact_version"],
                "fields_changed": result["fields_changed"],
                "quality_score": result["quality_score"],
                "trigger": "slice_edit",
            })
        except Exception as e:  # noqa: BLE001
            logger.warning("v4_slice_emit_failed", project_id=project_id, error=str(e))

    logger.info(
        "v4_editor.patch_slide_slice",
        project_id=project_id, slide_no=slide_no,
        fields_changed=result["fields_changed"],
        artifact_version=result["artifact_version"],
        noop=result.get("noop", False),
    )
    return {
        "ok": True,
        "slide_id": target_slide.get("slide_id"),
        "slide_index": target_slide.get("slide_index"),
        "fields_changed": result["fields_changed"],
        "artifact_version": result["artifact_version"],
        "quality_score": result["quality_score"],
        "noop": result.get("noop", False),
        "operation_id": operation_id,
    }


@router.post("/projects/{project_id}/slides/{slide_no}/elements/regenerate")
async def regenerate_slide_element(
    project_id: str,
    slide_no: int,
    body: _ElementRegenerateBody,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict[str, Any]:
    proj = await _load_owned_project(
        db,
        project_id,
        user,
        projection=_REGEN_PROJECT_PROJECTION,
    )
    compiled_slides = list(proj.get("compiled_slides") or [])
    if not compiled_slides:
        raise HTTPException(status_code=409, detail="deck has not been compiled yet")
    target_pos = _compiled_slide_position(compiled_slides, slide_no)
    if target_pos < 0:
        raise HTTPException(status_code=404, detail=f"compiled slide {slide_no} not found")
    target_slide = compiled_slides[target_pos]
    if not isinstance(target_slide, dict):
        raise HTTPException(status_code=409, detail="compiled slide is malformed")

    current_artifact_version = target_slide.get("artifact_version") if isinstance(target_slide.get("artifact_version"), int) else 1
    if body.expected_artifact_version is not None and body.expected_artifact_version != current_artifact_version:
        raise HTTPException(
            status_code=409,
            detail=_artifact_version_conflict_detail(
                project_id=project_id,
                slide_no=slide_no,
                expected_artifact_version=body.expected_artifact_version,
                current_slide=target_slide,
            ),
        )

    artifacts = target_slide.get("artifacts") if isinstance(target_slide.get("artifacts"), dict) else {}
    kit_jsx = artifacts.get("kit_jsx") if isinstance(artifacts, dict) else {}
    props = kit_jsx.get("props_json") if isinstance(kit_jsx, dict) else None
    if not isinstance(props, dict):
        raise HTTPException(status_code=409, detail="compiled slide is missing editable props")
    slide_doc = await db.slides.find_one({
        "$or": [{"project_id": project_id}, {"presentation_id": project_id}],
        "index": slide_no,
    })
    if not slide_doc:
        raise HTTPException(status_code=404, detail=f"slide {slide_no} not found")

    operation_id = _new_operation_id("element-regenerate", body.operation_id)
    await _ensure_operation_id_available(db, operation_id)
    client_id = _validate_client_operation_id(body.client_id, field="client_id") or "server"
    before_slide = copy.deepcopy(target_slide)

    try:
        regen = await regenerate_one_field(
            project_id=project_id,
            project=proj,
            slide_doc=slide_doc,
            compiled_props=props,
            path=body.path,
            instruction=body.instruction,
            kind=body.kind,
        )
    except RegenerationValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "element_regeneration_invalid", "path": body.path, "message": str(exc)},
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.warning("v4_element_regen_failed", project_id=project_id, slide_no=slide_no, path=body.path, error=str(exc)[:300])
        raise HTTPException(status_code=502, detail="element regeneration failed") from exc

    if not regen.ok:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "element_regeneration_refused",
                "path": body.path,
                "message": regen.reason or "element regeneration was refused",
                "task_type": regen.task_type,
            },
        )

    from app.services.v4.slice_editor import SliceEditError, apply_slice_ops

    op = {"path": body.path, "value": regen.value, "op": "replace"}
    try:
        result = apply_slice_ops(
            slide=target_slide,
            ops=[op],
            design_tokens=proj.get("design_tokens") or {},
        )
    except SliceEditError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": exc.code, "path": exc.path, "message": str(exc)},
        ) from exc

    array_key = f"compiled_slides.{target_pos}"
    update_result = await db.presentations.update_one(
        {
            "_id": project_id,
            f"compiled_slides.{target_pos}.slide_id": target_slide.get("slide_id"),
            f"compiled_slides.{target_pos}.artifact_version": current_artifact_version,
        },
        {"$set": {
            array_key: target_slide,
            "updated_at": datetime.now(timezone.utc),
            "last_element_regenerated_at": datetime.now(timezone.utc),
        }},
    )
    if getattr(update_result, "matched_count", 1) == 0:
        latest_proj = await db.presentations.find_one({"_id": project_id}, {"compiled_slides": 1})
        latest_slides = list((latest_proj or {}).get("compiled_slides") or [])
        latest_pos = _compiled_slide_position(latest_slides, slide_no)
        latest_slide = latest_slides[latest_pos] if latest_pos >= 0 else None
        raise HTTPException(
            status_code=409,
            detail=_artifact_version_conflict_detail(
                project_id=project_id,
                slide_no=slide_no,
                expected_artifact_version=body.expected_artifact_version or current_artifact_version,
                current_slide=latest_slide if isinstance(latest_slide, dict) else None,
            ),
        )

    if not result.get("noop"):
        await _invalidate_redo_stack(
            db,
            project_id=project_id,
            slide_id=target_slide.get("slide_id"),
            slide_index=target_slide.get("slide_index"),
            operation_id=operation_id,
        )
        await _insert_operation_ledger_entry(
            db,
            operation_id=operation_id,
            project_id=project_id,
            slide_id=target_slide.get("slide_id"),
            slide_index=target_slide.get("slide_index"),
            before_slide=before_slide,
            after_slide=copy.deepcopy(target_slide),
            trigger="element_regenerate",
            user_id=_operation_user_id(user),
            client_id=client_id,
            fields_changed=list(result.get("fields_changed") or []),
            ops=[{**op, "task_type": regen.task_type, "instruction": body.instruction}],
        )
        await _emit_compiled_history_update(
            project_id,
            slide=target_slide,
            fields_changed=list(result.get("fields_changed") or []),
            trigger="element_regenerate",
        )
        try:
            from app.services.v4.content_pipeline import make_redis_progress_emitter
            emit = make_redis_progress_emitter(project_id)
            await emit("slide_element_regenerated", {
                "slide_id": target_slide.get("slide_id"),
                "slide_index": target_slide.get("slide_index"),
                "artifact_version": result.get("artifact_version"),
                "path": body.path,
                "task_type": regen.task_type,
            })
        except Exception as exc:  # noqa: BLE001
            logger.warning("v4_element_regen_emit_failed", project_id=project_id, error=str(exc)[:200])

    logger.info(
        "v4_editor.regenerate_slide_element",
        project_id=project_id,
        slide_no=slide_no,
        path=body.path,
        task_type=regen.task_type,
        artifact_version=result.get("artifact_version"),
        noop=result.get("noop", False),
    )
    return {
        "ok": True,
        "slide_id": target_slide.get("slide_id"),
        "slide_index": target_slide.get("slide_index"),
        "path": body.path,
        "value": regen.value,
        "task_type": regen.task_type,
        "fields_changed": result.get("fields_changed") or [],
        "artifact_version": result.get("artifact_version"),
        "quality_score": result.get("quality_score"),
        "noop": result.get("noop", False),
        "operation_id": operation_id,
    }


@router.get("/projects/{project_id}/slides/{slide_no}/history")
async def get_compiled_slide_history(
    project_id: str,
    slide_no: int,
    limit: int = Query(default=50, ge=1, le=_OPERATION_HISTORY_LIMIT),
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict[str, Any]:
    proj = await _load_owned_project(
        db,
        project_id,
        user,
        projection={"user_id": 1, "compiled_slides": 1},
    )
    compiled_slides = list(proj.get("compiled_slides") or [])
    target_pos = _compiled_slide_position(compiled_slides, slide_no)
    if target_pos < 0:
        raise HTTPException(status_code=404, detail=f"compiled slide {slide_no} not found")
    target_slide = compiled_slides[target_pos]
    if not isinstance(target_slide, dict):
        raise HTTPException(status_code=409, detail="compiled slide is malformed")

    slide_id = target_slide.get("slide_id")
    slide_index = target_slide.get("slide_index") if isinstance(target_slide.get("slide_index"), int) else slide_no
    query: dict[str, Any] = {"project_id": project_id}
    if slide_id:
        query["slide_id"] = slide_id
    else:
        query["slide_index"] = slide_index
    docs = await _ledger_collection(db).find(query).sort("created_at", -1).limit(limit).to_list(length=limit)
    flags = await _compiled_history_flags(
        db,
        project_id=project_id,
        slide_id=slide_id,
        slide_index=slide_index,
    )
    return {
        "ok": True,
        "project_id": project_id,
        "slide_id": slide_id,
        "slide_index": slide_index,
        "artifact_version": target_slide.get("artifact_version"),
        "history": [_summarize_operation(doc) for doc in docs],
        **flags,
    }


@router.post("/projects/{project_id}/slides/{slide_no}/undo")
async def undo_compiled_slide_operation(
    project_id: str,
    slide_no: int,
    body: _CompiledHistoryMoveBody | None = None,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict[str, Any]:
    body = body or _CompiledHistoryMoveBody()
    proj = await _load_owned_project(
        db,
        project_id,
        user,
        projection={"user_id": 1, "compiled_slides": 1},
    )
    compiled_slides = list(proj.get("compiled_slides") or [])
    target_pos = _compiled_slide_position(compiled_slides, slide_no)
    if target_pos < 0:
        raise HTTPException(status_code=404, detail=f"compiled slide {slide_no} not found")
    current_slide = compiled_slides[target_pos]
    if not isinstance(current_slide, dict):
        raise HTTPException(status_code=409, detail="compiled slide is malformed")

    current_version = current_slide.get("artifact_version") if isinstance(current_slide.get("artifact_version"), int) else 1
    if body.expected_artifact_version is not None and body.expected_artifact_version != current_version:
        raise HTTPException(
            status_code=409,
            detail=_artifact_version_conflict_detail(
                project_id=project_id,
                slide_no=slide_no,
                expected_artifact_version=body.expected_artifact_version,
                current_slide=current_slide,
            ),
        )

    slide_id = current_slide.get("slide_id")
    slide_index = current_slide.get("slide_index") if isinstance(current_slide.get("slide_index"), int) else slide_no
    operation = await _find_last_undoable_operation(
        db,
        project_id=project_id,
        slide_id=slide_id,
        slide_index=slide_index,
    )
    if not operation:
        raise HTTPException(status_code=409, detail={"code": "nothing_to_undo", "message": "No saved compiled edit is available to undo."})
    required_version = operation.get("after_artifact_version")
    if isinstance(required_version, int) and current_version != required_version:
        raise HTTPException(
            status_code=409,
            detail=_history_position_conflict_detail(
                project_id=project_id,
                slide_no=slide_no,
                expected_artifact_version=body.expected_artifact_version,
                required_artifact_version=required_version,
                current_slide=current_slide,
                action="undo",
            ),
        )

    restored = copy.deepcopy(operation.get("before_compiled_slide") or {})
    if not isinstance(restored, dict) or not restored.get("slide_id"):
        raise HTTPException(status_code=409, detail={"code": "history_snapshot_missing", "message": "Undo snapshot is missing for this edit."})
    restored["artifact_version"] = _next_artifact_version(current_slide)
    restored["slide_id"] = current_slide.get("slide_id")
    restored["slide_index"] = current_slide.get("slide_index")
    now = datetime.now(timezone.utc)
    update_result = await db.presentations.update_one(
        {
            "_id": project_id,
            f"compiled_slides.{target_pos}.slide_id": current_slide.get("slide_id"),
            f"compiled_slides.{target_pos}.artifact_version": current_version,
        },
        {"$set": {f"compiled_slides.{target_pos}": restored, "updated_at": now}},
    )
    if getattr(update_result, "matched_count", 1) == 0:
        latest_proj = await db.presentations.find_one({"_id": project_id}, {"compiled_slides": 1})
        latest_slides = list((latest_proj or {}).get("compiled_slides") or [])
        latest_pos = _compiled_slide_position(latest_slides, slide_no)
        latest_slide = latest_slides[latest_pos] if latest_pos >= 0 else None
        raise HTTPException(
            status_code=409,
            detail=_history_position_conflict_detail(
                project_id=project_id,
                slide_no=slide_no,
                expected_artifact_version=body.expected_artifact_version,
                required_artifact_version=required_version if isinstance(required_version, int) else None,
                current_slide=latest_slide if isinstance(latest_slide, dict) else None,
                action="undo",
            ),
        )

    operation_id = _new_operation_id("undo", body.operation_id)
    await _ensure_operation_id_available(db, operation_id)
    client_id = _validate_client_operation_id(body.client_id, field="client_id") or "server"
    await _ledger_collection(db).update_one(
        {"_id": operation.get("_id")},
        {"$set": {"undone_at": now, "undo_operation_id": operation_id}},
    )
    undo_doc = await _insert_operation_ledger_entry(
        db,
        operation_id=operation_id,
        project_id=project_id,
        slide_id=restored.get("slide_id"),
        slide_index=restored.get("slide_index"),
        before_slide=copy.deepcopy(current_slide),
        after_slide=copy.deepcopy(restored),
        trigger="undo",
        user_id=_operation_user_id(user),
        client_id=client_id,
        fields_changed=list(operation.get("fields_changed") or []),
        ops=list(operation.get("ops") or []),
        undo_of=str(operation.get("_id") or operation.get("operation_id")),
    )
    await _emit_compiled_history_update(
        project_id,
        slide=restored,
        fields_changed=list(operation.get("fields_changed") or []),
        trigger="undo",
    )
    flags = await _compiled_history_flags(
        db,
        project_id=project_id,
        slide_id=restored.get("slide_id"),
        slide_index=restored.get("slide_index"),
    )
    return {
        "ok": True,
        "operation_id": operation_id,
        "undone_operation_id": operation.get("_id") or operation.get("operation_id"),
        "slide_id": restored.get("slide_id"),
        "slide_index": restored.get("slide_index"),
        "artifact_version": restored.get("artifact_version"),
        "history_entry": _summarize_operation(undo_doc),
        **flags,
    }


@router.post("/projects/{project_id}/slides/{slide_no}/redo")
async def redo_compiled_slide_operation(
    project_id: str,
    slide_no: int,
    body: _CompiledHistoryMoveBody | None = None,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict[str, Any]:
    body = body or _CompiledHistoryMoveBody()
    proj = await _load_owned_project(
        db,
        project_id,
        user,
        projection={"user_id": 1, "compiled_slides": 1},
    )
    compiled_slides = list(proj.get("compiled_slides") or [])
    target_pos = _compiled_slide_position(compiled_slides, slide_no)
    if target_pos < 0:
        raise HTTPException(status_code=404, detail=f"compiled slide {slide_no} not found")
    current_slide = compiled_slides[target_pos]
    if not isinstance(current_slide, dict):
        raise HTTPException(status_code=409, detail="compiled slide is malformed")
    current_version = current_slide.get("artifact_version") if isinstance(current_slide.get("artifact_version"), int) else 1
    if body.expected_artifact_version is not None and body.expected_artifact_version != current_version:
        raise HTTPException(
            status_code=409,
            detail=_artifact_version_conflict_detail(
                project_id=project_id,
                slide_no=slide_no,
                expected_artifact_version=body.expected_artifact_version,
                current_slide=current_slide,
            ),
        )

    slide_id = current_slide.get("slide_id")
    slide_index = current_slide.get("slide_index") if isinstance(current_slide.get("slide_index"), int) else slide_no
    operation = await _find_last_redoable_operation(
        db,
        project_id=project_id,
        slide_id=slide_id,
        slide_index=slide_index,
    )
    if not operation:
        raise HTTPException(status_code=409, detail={"code": "nothing_to_redo", "message": "No undone compiled edit is available to redo."})
    required_version = operation.get("after_artifact_version")
    if isinstance(required_version, int) and current_version != required_version:
        raise HTTPException(
            status_code=409,
            detail=_history_position_conflict_detail(
                project_id=project_id,
                slide_no=slide_no,
                expected_artifact_version=body.expected_artifact_version,
                required_artifact_version=required_version,
                current_slide=current_slide,
                action="redo",
            ),
        )

    restored = copy.deepcopy(operation.get("before_compiled_slide") or {})
    if not isinstance(restored, dict) or not restored.get("slide_id"):
        raise HTTPException(status_code=409, detail={"code": "history_snapshot_missing", "message": "Redo snapshot is missing for this edit."})
    restored["artifact_version"] = _next_artifact_version(current_slide)
    restored["slide_id"] = current_slide.get("slide_id")
    restored["slide_index"] = current_slide.get("slide_index")
    now = datetime.now(timezone.utc)
    update_result = await db.presentations.update_one(
        {
            "_id": project_id,
            f"compiled_slides.{target_pos}.slide_id": current_slide.get("slide_id"),
            f"compiled_slides.{target_pos}.artifact_version": current_version,
        },
        {"$set": {f"compiled_slides.{target_pos}": restored, "updated_at": now}},
    )
    if getattr(update_result, "matched_count", 1) == 0:
        latest_proj = await db.presentations.find_one({"_id": project_id}, {"compiled_slides": 1})
        latest_slides = list((latest_proj or {}).get("compiled_slides") or [])
        latest_pos = _compiled_slide_position(latest_slides, slide_no)
        latest_slide = latest_slides[latest_pos] if latest_pos >= 0 else None
        raise HTTPException(
            status_code=409,
            detail=_history_position_conflict_detail(
                project_id=project_id,
                slide_no=slide_no,
                expected_artifact_version=body.expected_artifact_version,
                required_artifact_version=required_version if isinstance(required_version, int) else None,
                current_slide=latest_slide if isinstance(latest_slide, dict) else None,
                action="redo",
            ),
        )

    operation_id = _new_operation_id("redo", body.operation_id)
    await _ensure_operation_id_available(db, operation_id)
    client_id = _validate_client_operation_id(body.client_id, field="client_id") or "server"
    await _ledger_collection(db).update_one(
        {"_id": operation.get("_id")},
        {"$set": {"redone_at": now, "redo_operation_id": operation_id}},
    )
    redo_doc = await _insert_operation_ledger_entry(
        db,
        operation_id=operation_id,
        project_id=project_id,
        slide_id=restored.get("slide_id"),
        slide_index=restored.get("slide_index"),
        before_slide=copy.deepcopy(current_slide),
        after_slide=copy.deepcopy(restored),
        trigger="redo",
        user_id=_operation_user_id(user),
        client_id=client_id,
        fields_changed=list(operation.get("fields_changed") or []),
        ops=list(operation.get("ops") or []),
        redo_of=str(operation.get("undo_of") or operation.get("_id") or operation.get("operation_id")),
    )
    await _emit_compiled_history_update(
        project_id,
        slide=restored,
        fields_changed=list(operation.get("fields_changed") or []),
        trigger="redo",
    )
    flags = await _compiled_history_flags(
        db,
        project_id=project_id,
        slide_id=restored.get("slide_id"),
        slide_index=restored.get("slide_index"),
    )
    return {
        "ok": True,
        "operation_id": operation_id,
        "redone_operation_id": operation.get("_id") or operation.get("operation_id"),
        "slide_id": restored.get("slide_id"),
        "slide_index": restored.get("slide_index"),
        "artifact_version": restored.get("artifact_version"),
        "history_entry": _summarize_operation(redo_doc),
        **flags,
    }


@router.post("/projects/{project_id}/slides/{slide_no}/recompile")
async def recompile_slide_display_artifact(
    project_id: str,
    slide_no: int,
    body: _DisplayRepairBody | None = None,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict[str, Any]:
    proj = await _load_owned_project(
        db, project_id, user,
        projection={
            "user_id": 1,
            "compiled_slides": 1,
            "title": 1,
            "company_icon_url": 1,
        },
    )
    compiled_slides = list(proj.get("compiled_slides") or [])
    if not compiled_slides:
        raise HTTPException(status_code=409, detail="deck has not been compiled yet")
    target_pos = _compiled_slide_position(compiled_slides, slide_no)
    if target_pos < 0:
        raise HTTPException(status_code=404, detail=f"compiled slide {slide_no} not found")

    existing = compiled_slides[target_pos] if isinstance(compiled_slides[target_pos], dict) else {}
    slide_doc = await db.slides.find_one({
        "$or": [{"project_id": project_id}, {"presentation_id": project_id}],
        "index": slide_no,
    })
    if not slide_doc:
        raise HTTPException(status_code=404, detail=f"slide {slide_no} not found")

    circuit_key = f"recompile:{project_id}:{slide_no}:{(body.issue_code if body else None) or 'manual'}"
    if not await _repair_attempt_allowed(
        db,
        circuit_key,
        max_attempts=1,
        project_id=project_id,
        slide_no=slide_no,
        issue_code=(body.issue_code if body else None),
        repair_type="recompile",
    ):
        await _emit_display_repair(project_id, "slide_needs_regeneration", {
            "slide_id": existing.get("slide_id"),
            "slide_index": slide_no,
            "issue_code": (body.issue_code if body else None),
            "reason": "display_recompile_circuit_open",
        })
        raise HTTPException(status_code=409, detail="display repair circuit open")

    from app.services.v4.slide_compiler import compile_slide

    compiled = compile_slide(
        slide=_generated_slide_from_doc(slide_doc),
        image_url=slide_doc.get("image_url") or None,
        deck_title=proj.get("title") or None,
        company_icon_url=proj.get("company_icon_url") or slide_doc.get("company_icon_url") or None,
    )
    compiled["artifact_version"] = _next_artifact_version(existing)
    if isinstance(existing, dict) and existing.get("design_system_version"):
        compiled["design_system_version"] = existing.get("design_system_version")

    await _persist_recompiled_slide(
        db=db,
        project_id=project_id,
        compiled_slides=compiled_slides,
        target_pos=target_pos,
        compiled=compiled,
    )
    await _emit_display_repair(project_id, "slide_recompiled", {
        "slide_id": compiled.get("slide_id"),
        "slide_index": compiled.get("slide_index"),
        "artifact_version": compiled.get("artifact_version"),
        "issue_code": (body.issue_code if body else None),
        "source": (body.source if body else "preview"),
    })
    await record_quality_event(QualityEvent(
        event="display_recompile",
        project_id=project_id,
        severity="info",
        tags={"issue_code": (body.issue_code if body else None) or "manual"},
        payload={"slide_index": slide_no, "artifact_version": compiled.get("artifact_version")},
    ))
    logger.info("v4_editor.display_recompile", project_id=project_id, slide_no=slide_no, artifact_version=compiled.get("artifact_version"))
    return {
        "ok": True,
        "slide_id": compiled.get("slide_id"),
        "slide_index": compiled.get("slide_index"),
        "artifact_version": compiled.get("artifact_version"),
    }


@router.post("/projects/{project_id}/slides/{slide_no}/repair")
async def repair_slide_display_artifact(
    project_id: str,
    slide_no: int,
    body: _DisplayRepairBody | None = None,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict[str, Any]:
    disallowed = {"data_empty_required", "asset_image_pending_timeout"}
    issue_code = (body.issue_code if body else None) or "manual"
    if issue_code in disallowed:
        raise HTTPException(status_code=422, detail="display repair cannot fabricate missing content or image assets")

    proj = await _load_owned_project(
        db, project_id, user,
        projection={"user_id": 1, "compiled_slides": 1, "design_tokens": 1},
    )
    compiled_slides = list(proj.get("compiled_slides") or [])
    if not compiled_slides:
        raise HTTPException(status_code=409, detail="deck has not been compiled yet")
    target_pos = _compiled_slide_position(compiled_slides, slide_no)
    if target_pos < 0:
        raise HTTPException(status_code=404, detail=f"compiled slide {slide_no} not found")
    target_slide = compiled_slides[target_pos]
    if not isinstance(target_slide, dict):
        raise HTTPException(status_code=409, detail="compiled slide is not repairable")

    circuit_key = f"repair:{project_id}:{slide_no}:{issue_code}"
    if not await _repair_attempt_allowed(
        db,
        circuit_key,
        max_attempts=1,
        project_id=project_id,
        slide_no=slide_no,
        issue_code=issue_code,
        repair_type="structural_artifact",
    ):
        await _emit_display_repair(project_id, "slide_needs_regeneration", {
            "slide_id": target_slide.get("slide_id"),
            "slide_index": slide_no,
            "issue_code": issue_code,
            "reason": "display_repair_circuit_open",
        })
        raise HTTPException(status_code=409, detail="display repair circuit open")

    artifacts = target_slide.get("artifacts") if isinstance(target_slide.get("artifacts"), dict) else {}
    kit_jsx = artifacts.get("kit_jsx") if isinstance(artifacts, dict) else None
    props = kit_jsx.get("props_json") if isinstance(kit_jsx, dict) else None
    kit = (kit_jsx.get("kit_component") if isinstance(kit_jsx, dict) else None) or target_slide.get("kit_component")
    if not isinstance(props, dict) or not isinstance(kit, str) or not kit:
        await _emit_display_repair(project_id, "slide_repair_failed", {
            "slide_id": target_slide.get("slide_id"),
            "slide_index": slide_no,
            "issue_code": issue_code,
            "reason": "missing_kit_artifact_props",
        })
        raise HTTPException(status_code=409, detail="slide requires content-preserving recompile")

    from app.services.v4.slice_editor import _rebuild_artifacts
    from app.services.v4.quality_scorer import score_slide

    repaired = copy.deepcopy(target_slide)
    _rebuild_artifacts(slide=repaired, kit=kit, props=copy.deepcopy(props))
    repaired["quality_score"] = score_slide(
        kit=kit,
        props=props,
        design_tokens=proj.get("design_tokens") or {},
    )
    repaired["artifact_version"] = _next_artifact_version(target_slide)

    await _persist_recompiled_slide(
        db=db,
        project_id=project_id,
        compiled_slides=compiled_slides,
        target_pos=target_pos,
        compiled=repaired,
    )
    await _emit_display_repair(project_id, "slide_recompiled", {
        "slide_id": repaired.get("slide_id"),
        "slide_index": repaired.get("slide_index"),
        "artifact_version": repaired.get("artifact_version"),
        "issue_code": issue_code,
        "source": (body.source if body else "preview"),
        "repair_type": "structural_artifact",
    })
    await record_quality_event(QualityEvent(
        event="display_repair",
        project_id=project_id,
        severity="info",
        tags={"issue_code": issue_code},
        payload={"slide_index": slide_no, "artifact_version": repaired.get("artifact_version")},
    ))
    logger.info("v4_editor.display_repair", project_id=project_id, slide_no=slide_no, issue_code=issue_code, artifact_version=repaired.get("artifact_version"))
    return {
        "ok": True,
        "slide_id": repaired.get("slide_id"),
        "slide_index": repaired.get("slide_index"),
        "artifact_version": repaired.get("artifact_version"),
    }


# ═══════════════════════════════════════════════════════════════════
# Skeleton + research reconstruction (for regen)
# ═══════════════════════════════════════════════════════════════════


def _rebuild_skeleton(proj: dict, slides_docs: list[dict]) -> Optional[DeckSkeleton]:
    """Rebuild a DeckSkeleton from the persisted v4_skeleton dict, falling
    back to reconstructing one from live slide docs if the snapshot is
    missing (older generations)."""
    skel = proj.get("v4_skeleton")
    if isinstance(skel, dict) and isinstance(skel.get("slides"), list):
        return DeckSkeleton(
            project_id=proj["_id"],
            title=skel.get("title", proj.get("title", "")),
            narrative_arc=skel.get("narrative_arc", proj.get("narrative_arc", "")),
            slides=[
                SlideSkeleton(
                    index=int(s.get("index", i)),
                    intent=str(s.get("intent", "")),
                    purpose=str(s.get("purpose", "")),
                    headline_target=str(s.get("headline_target", "")),
                    key_points=list(s.get("key_points", []) or []),
                    density_target=str(s.get("density_target", "medium")),
                    layout_hint=str(s.get("layout_hint", "")),
                    evidence_refs=list(s.get("evidence_refs", []) or []),
                    visual_cue=str(s.get("visual_cue", "")),
                )
                for i, s in enumerate(skel["slides"])
            ],
            raw_planner_output={},
        )
    if not slides_docs:
        return None
    return DeckSkeleton(
        project_id=proj["_id"],
        title=proj.get("title", ""),
        narrative_arc=proj.get("narrative_arc", ""),
        slides=[
            SlideSkeleton(
                index=int(d.get("index", i)),
                intent=str(d.get("intent", "")),
                purpose=str(d.get("rationale") or d.get("purpose", "")),
                headline_target=str(d.get("headline", "")),
                key_points=list(d.get("bullets", []) or [])[:5],
                density_target="medium",
                layout_hint=str(d.get("layout", "")),
                evidence_refs=[c.get("url", "") for c in (d.get("citations") or []) if c.get("url")],
                visual_cue="",
            )
            for i, d in enumerate(slides_docs)
        ],
        raw_planner_output={},
    )


def _rebuild_research(proj: dict) -> ResearchPacket:
    snap = proj.get("v4_research_snapshot") or {}

    def _cite(d: dict[str, Any]) -> Citation:
        return Citation(
            title=str(d.get("title", ""))[:240],
            url=str(d.get("url", "")),
            snippet=str(d.get("snippet", ""))[:600],
            source=str(d.get("source", "snapshot")),
            source_authority=float(d.get("source_authority", 0.5) or 0.5),
            published_at=d.get("published_at"),
        )

    return ResearchPacket(
        query=str(snap.get("query", proj.get("title", ""))),
        industry=snap.get("industry"),
        company_name=snap.get("company_name") or proj.get("company_name"),
        citations=[_cite(c) for c in (snap.get("citations") or [])],
        news_citations=[_cite(c) for c in (snap.get("news_citations") or [])],
        financial_data=dict(snap.get("financial_data") or {}),
        social_signals=dict(snap.get("social_signals") or {}),
        duration_ms=0,
        cache_hit=True,
    )


def _augment_skeleton_with_instruction(
    skel_slide: SlideSkeleton, instruction: Optional[str],
) -> SlideSkeleton:
    if not instruction or not instruction.strip():
        return skel_slide
    extra = instruction.strip()[:400]
    new_purpose = (skel_slide.purpose or "").strip()
    if extra:
        new_purpose = f"{new_purpose}\n\nUSER REVISION REQUEST: {extra}".strip()
    return SlideSkeleton(
        index=skel_slide.index,
        intent=skel_slide.intent,
        purpose=new_purpose,
        headline_target=skel_slide.headline_target,
        key_points=list(skel_slide.key_points),
        density_target=skel_slide.density_target,
        layout_hint=skel_slide.layout_hint,
        evidence_refs=list(skel_slide.evidence_refs),
        visual_cue=skel_slide.visual_cue,
    )


# ═══════════════════════════════════════════════════════════════════
# POST regenerate single slide
# ═══════════════════════════════════════════════════════════════════


class _RegenBody(BaseModel):
    instruction: Optional[str] = Field(default=None, max_length=600)
    target_model: Optional[str] = Field(default=None, max_length=120)


class _BatchRegenBody(_RegenBody):
    slide_indices: list[int] = Field(..., min_length=1, max_length=MAX_BATCH_REGEN_SLIDES)
    per_slide_instructions: dict[int, str] = Field(default_factory=dict)
    preserve_images: bool = True
    concurrency: int = Field(default=2, ge=1, le=MAX_REGEN_CONCURRENCY)


def _regen_error_to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, RegenerationBusy):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, RegenerationValidationError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="regeneration failed")


@router.post("/projects/{project_id}/slides/{slide_no}/regenerate")
async def regenerate_slide(
    project_id: str,
    slide_no: int,
    body: _RegenBody,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict[str, Any]:
    proj = await _load_owned_project(db, project_id, user, projection=_REGEN_PROJECT_PROJECTION)
    if body.target_model and not _is_premium_user(user):
        raise HTTPException(status_code=403, detail="model selection requires premium")
    try:
        result = await regenerate_slides(
            db=db,
            project_id=project_id,
            project=proj,
            request=RegenerationRequest(
                slide_indices=[slide_no],
                instruction=body.instruction,
                target_model=body.target_model,
                preserve_images=True,
                concurrency=1,
                change_type="regenerate",
            ),
        )
    except (RegenerationBusy, RegenerationValidationError) as exc:
        raise _regen_error_to_http(exc) from exc

    outcome = next((o for o in result.outcomes if o.index == slide_no), None)
    if not outcome or not outcome.ok or not outcome.slide_doc:
        detail = outcome.error if outcome and outcome.error else "slide regeneration failed"
        raise HTTPException(status_code=502, detail=detail)

    logger.info(
        "v4_editor.regenerate_slide",
        project_id=project_id, slide_no=slide_no,
        forced_model=body.target_model, has_instruction=bool(body.instruction),
        artifact_version=outcome.artifact_version,
    )
    return {
        "ok": True,
        "slide": _slide_doc_to_dto(outcome.slide_doc),
        "slide_id": outcome.slide_id,
        "artifact_version": outcome.artifact_version,
    }


@router.post("/projects/{project_id}/slides/regenerate-batch")
async def regenerate_slide_batch(
    project_id: str,
    body: _BatchRegenBody,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict[str, Any]:
    proj = await _load_owned_project(db, project_id, user, projection=_REGEN_PROJECT_PROJECTION)
    if body.target_model and not _is_premium_user(user):
        raise HTTPException(status_code=403, detail="model selection requires premium")
    try:
        result = await regenerate_slides(
            db=db,
            project_id=project_id,
            project=proj,
            request=RegenerationRequest(
                slide_indices=body.slide_indices,
                instruction=body.instruction,
                per_slide_instructions=body.per_slide_instructions,
                target_model=body.target_model,
                preserve_images=body.preserve_images,
                concurrency=body.concurrency,
                change_type="regenerate-batch",
            ),
        )
    except (RegenerationBusy, RegenerationValidationError) as exc:
        raise _regen_error_to_http(exc) from exc

    regenerated_docs = [o.slide_doc for o in result.outcomes if o.ok and o.slide_doc]
    logger.info(
        "v4_editor.regenerate_slide_batch",
        project_id=project_id,
        succeeded=result.succeeded_indices,
        failed=result.failed_indices,
    )
    return {
        "ok": result.ok,
        "slides": [_slide_doc_to_dto(doc) for doc in regenerated_docs],
        "results": [o.to_public() for o in result.outcomes],
        "succeeded_indices": result.succeeded_indices,
        "failed_indices": result.failed_indices,
    }


# ═══════════════════════════════════════════════════════════════════
# POST regenerate full deck (premium only, rate-limited)
# ═══════════════════════════════════════════════════════════════════


@router.post("/projects/{project_id}/regenerate-deck")
async def regenerate_deck(
    project_id: str,
    body: _RegenBody,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict[str, Any]:
    proj = await _load_owned_project(db, project_id, user, projection=_REGEN_PROJECT_PROJECTION)
    if proj.get("mode") != "premium":
        raise HTTPException(status_code=403, detail="deck regeneration is premium-only")
    if not _is_premium_user(user):
        raise HTTPException(status_code=403, detail="premium subscription required")

    last = proj.get("deck_regenerated_at")
    if last:
        delta = (datetime.now(timezone.utc) - last).total_seconds()
        if delta < _DECK_REGEN_COOLDOWN_SECONDS:
            raise HTTPException(
                status_code=429,
                detail=f"deck regeneration cooldown — retry in {int(_DECK_REGEN_COOLDOWN_SECONDS - delta)}s",
            )

    docs = await db.slides.find({
        "$or": [{"project_id": project_id}, {"presentation_id": project_id}]
    }).sort("index", 1).to_list(length=200)
    if not docs:
        raise HTTPException(status_code=409, detail="project has no slides to regenerate")
    indices = [int(doc.get("index", i)) for i, doc in enumerate(docs)]
    try:
        result = await regenerate_slides(
            db=db,
            project_id=project_id,
            project=proj,
            request=RegenerationRequest(
                slide_indices=indices,
                instruction=body.instruction,
                target_model=body.target_model,
                preserve_images=True,
                concurrency=MAX_REGEN_CONCURRENCY,
                change_type="regenerate-deck",
                update_deck_regenerated_at=True,
            ),
        )
    except (RegenerationBusy, RegenerationValidationError) as exc:
        raise _regen_error_to_http(exc) from exc

    logger.info(
        "v4_editor.regenerate_deck",
        project_id=project_id,
        n_slides=len(result.refreshed_docs),
        forced_model=body.target_model,
        succeeded=result.succeeded_indices,
        failed=result.failed_indices,
    )
    return {
        "ok": result.ok,
        "slides": [_slide_doc_to_dto(d) for d in sorted(result.refreshed_docs, key=lambda x: int(x.get("index", 0)))],
        "results": [o.to_public() for o in result.outcomes],
        "succeeded_indices": result.succeeded_indices,
        "failed_indices": result.failed_indices,
    }


# ═══════════════════════════════════════════════════════════════════
# Team-member upsert / delete
# ═══════════════════════════════════════════════════════════════════


_NAME_RE = re.compile(r"[^\w\s\-'.]")


def _safe_name_part(name: str, max_len: int = 24) -> str:
    s = _NAME_RE.sub("", name).strip().replace(" ", "-")
    return (s or "member")[:max_len]


async def _save_team_photo(
    project_id: str, slide_no: int, member_name: str, file: UploadFile,
) -> str:
    if not file.filename:
        raise HTTPException(status_code=400, detail="filename required")
    ext = Path(file.filename).suffix.lower()
    if ext not in _TEAM_PHOTO_ALLOWED_EXT:
        raise HTTPException(
            status_code=415,
            detail=f"unsupported photo type {ext}; allowed={sorted(_TEAM_PHOTO_ALLOWED_EXT)}",
        )
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty file")
    if len(raw) > _TEAM_PHOTO_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"photo exceeds {_TEAM_PHOTO_MAX_BYTES // (1024*1024)}MB limit",
        )
    _TEAM_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(raw).hexdigest()[:12]
    safe = _safe_name_part(member_name)
    out = _TEAM_PHOTO_DIR / f"{project_id}-{slide_no}-{safe}-{digest}{ext}"
    out.write_bytes(raw)
    return f"/uploads/team_photos/{out.name}"


async def _save_project_team_photo(
    project_id: str, member_name: str, file: UploadFile,
) -> str:
    """Same as `_save_team_photo` but not tied to a slide — used for the
    pre-generation prefill endpoint.  Saved files are namespaced by project
    id so that the parallel writer can later look them up by name."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="filename required")
    ext = Path(file.filename).suffix.lower()
    if ext not in _TEAM_PHOTO_ALLOWED_EXT:
        raise HTTPException(
            status_code=415,
            detail=f"unsupported photo type {ext}; allowed={sorted(_TEAM_PHOTO_ALLOWED_EXT)}",
        )
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty file")
    if len(raw) > _TEAM_PHOTO_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"photo exceeds {_TEAM_PHOTO_MAX_BYTES // (1024*1024)}MB limit",
        )
    _TEAM_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(raw).hexdigest()[:12]
    safe = _safe_name_part(member_name)
    out = _TEAM_PHOTO_DIR / f"{project_id}-prefill-{safe}-{digest}{ext}"
    out.write_bytes(raw)
    return f"/uploads/team_photos/{out.name}"


@router.post("/projects/{project_id}/team-prefill")
async def prefill_team_members(
    project_id: str,
    # Parallel arrays — the frontend submits `names[]`, `roles[]`, `files[]`.
    # Each index must line up; empty file slots are allowed (user can mix
    # uploaded and auto-scraped headshots).
    names: list[str] = Form(default=[]),
    roles: list[str] = Form(default=[]),
    credentials: list[str] = Form(default=[]),
    files: list[UploadFile] = File(default=[]),
    user: Optional[dict] = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Attach user-uploaded team photos + metadata to a project BEFORE the
    parallel writer runs.

    The writer reads `presentations.team_prefill` and, for each entry that
    has a `photo_url`, skips the person-image search and uses the uploaded
    image directly.  Entries without a photo still get auto-scraped.
    """
    await _load_owned_project(db, project_id, user, projection={"_id": 1, "user_id": 1})

    if len(names) > _MAX_TEAM_MEMBERS:
        raise HTTPException(
            status_code=400,
            detail=f"at most {_MAX_TEAM_MEMBERS} team members allowed",
        )

    members: list[dict[str, Any]] = []
    for i, raw_name in enumerate(names):
        name = (raw_name or "").strip()
        if not name:
            continue
        role = roles[i].strip() if i < len(roles) and roles[i] else ""
        creds = credentials[i].strip() if i < len(credentials) and credentials[i] else ""
        photo_url: str = ""
        upload = files[i] if i < len(files) else None
        if upload is not None and getattr(upload, "filename", ""):
            photo_url = await _save_project_team_photo(project_id, name, upload)
        members.append({
            "name": name[:80],
            "role": role[:80],
            "credentials": creds[:240],
            "photo_url": photo_url,
            "user_supplied_photo": bool(photo_url),
        })

    await db.presentations.update_one(
        {"_id": project_id},
        {"$set": {"team_prefill": members, "team_prefill_updated_at": datetime.now(timezone.utc)}},
    )
    logger.info(
        "v4_team_prefill_saved",
        project_id=project_id,
        member_count=len(members),
        with_photos=sum(1 for m in members if m["photo_url"]),
    )
    return {"ok": True, "members": members, "count": len(members)}


@router.post("/projects/{project_id}/slides/{slide_no}/team-member")
async def upsert_team_member(
    project_id: str,
    slide_no: int,
    name: str = Form(..., max_length=80),
    role: Optional[str] = Form(default=None, max_length=80),
    bio: Optional[str] = Form(default=None, max_length=240),
    linkedin_url: Optional[str] = Form(default=None, max_length=400),
    photo_url: Optional[str] = Form(default=None, max_length=1000),
    member_index: Optional[int] = Form(default=None, ge=0, le=_MAX_TEAM_MEMBERS - 1),
    file: Optional[UploadFile] = File(default=None),
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict[str, Any]:
    """Upsert a single team member on a slide.

    - If `member_index` is provided AND in range, replace that entry; else
      append (capped at `_MAX_TEAM_MEMBERS`).
    - Photo resolution order: uploaded `file` → provided `photo_url`
      (re-resolved to verify reachability) → search by name → SVG initials
      default avatar. Stock photos are NEVER used.
    """
    proj = await _load_owned_project(
        db, project_id, user,
        projection={"user_id": 1, "mode": 1, "company_name": 1},
    )
    slide_doc = await db.slides.find_one({
        "$or": [{"project_id": project_id}, {"presentation_id": project_id}],
        "index": slide_no,
    })
    if not slide_doc:
        raise HTTPException(status_code=404, detail=f"slide {slide_no} not found")

    clean_name = (name or "").strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="name required")

    final_photo_url: Optional[str] = None
    photo_source: Optional[str] = None
    is_default = False

    if file is not None:
        final_photo_url = await _save_team_photo(project_id, slide_no, clean_name, file)
        photo_source = "user_upload"
    elif photo_url and photo_url.strip():
        # Trust user-provided URL; light validation only.
        url = photo_url.strip()
        if not url.lower().startswith(("http://", "https://", "/uploads/")):
            raise HTTPException(status_code=422, detail="photo_url must be http(s) or /uploads path")
        final_photo_url = url
        photo_source = "user_url"
    else:
        # Auto-resolve via image_search for a real headshot.
        try:
            cand = await search_person_image(
                name=clean_name,
                role_hint=role,
                company=proj.get("company_name"),
                company_domain=None,
                timeout_s=8.0,
            )
            final_photo_url = cand.image_url
            photo_source = cand.source_domain
            is_default = cand.is_default_avatar
        except Exception as e:  # noqa: BLE001
            logger.warning("v4_editor.photo_resolve_failed", error=str(e))
            cand = make_default_candidate(clean_name)
            final_photo_url = cand.image_url
            photo_source = "default"
            is_default = True

    new_member = {
        "name": clean_name[:80],
        "role": (role or "").strip()[:80] or None,
        "bio": (bio or "").strip()[:240] or None,
        "linkedin_url": (linkedin_url or "").strip() or None,
        "photo_url": final_photo_url,
        "photo_source": photo_source,
        "photo_attribution": None,
        "is_default_avatar": is_default,
        "source": "user",
        "confidence": 1.0,
    }

    members = list(slide_doc.get("team_members") or [])
    if member_index is not None and 0 <= member_index < len(members):
        members[member_index] = new_member
    else:
        if len(members) >= _MAX_TEAM_MEMBERS:
            raise HTTPException(status_code=409, detail=f"max {_MAX_TEAM_MEMBERS} team members per slide")
        members.append(new_member)

    await _snapshot_slide(db, slide_doc, "team-member-upsert")
    new_version = int(slide_doc.get("version", 1)) + 1
    updated = await db.slides.find_one_and_update(
        {"_id": slide_doc["_id"]},
        {"$set": {
            "team_members": members,
            "requires_user_input": False,
            "user_input_kind": None,
            "user_input_reason": None,
            "version": new_version,
            "updated_at": datetime.now(timezone.utc),
        }},
        return_document=True,
    )
    return {"ok": True, "slide": _slide_doc_to_dto(updated), "member": new_member}


@router.delete("/projects/{project_id}/slides/{slide_no}/team-member/{member_idx}")
async def delete_team_member(
    project_id: str,
    slide_no: int,
    member_idx: int,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict[str, Any]:
    await _load_owned_project(db, project_id, user, projection={"user_id": 1, "mode": 1})
    slide_doc = await db.slides.find_one({
        "$or": [{"project_id": project_id}, {"presentation_id": project_id}],
        "index": slide_no,
    })
    if not slide_doc:
        raise HTTPException(status_code=404, detail=f"slide {slide_no} not found")
    members = list(slide_doc.get("team_members") or [])
    if not (0 <= member_idx < len(members)):
        raise HTTPException(status_code=404, detail="team member index out of range")

    await _snapshot_slide(db, slide_doc, "team-member-delete")
    members.pop(member_idx)
    requires_input = len(members) == 0 and (slide_doc.get("intent") or "").lower() == "team"
    new_version = int(slide_doc.get("version", 1)) + 1
    updated = await db.slides.find_one_and_update(
        {"_id": slide_doc["_id"]},
        {"$set": {
            "team_members": members,
            "requires_user_input": requires_input,
            "user_input_kind": "team_members" if requires_input else None,
            "user_input_reason": "team_members_unresolved" if requires_input else None,
            "version": new_version,
            "updated_at": datetime.now(timezone.utc),
        }},
        return_document=True,
    )
    return {"ok": True, "slide": _slide_doc_to_dto(updated)}
