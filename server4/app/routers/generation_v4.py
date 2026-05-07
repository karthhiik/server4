"""
V4 Generation Routes — Intelligent Input + Skeleton-of-Thought Content Pipeline.

Three endpoints:
  POST /api/v4/analyze-input     — Pre-flight analysis (returns InputAnalysisResult)
  POST /api/v4/generate          — Run the V4 content pipeline (NEW, no legacy reuse)
  GET  /api/v4/generation/{id}   — Get current generation status + recent progress events

Design notes:
- This router does NOT call the legacy orchestrator. It calls V4ContentPipeline
  directly (per the "no buggy build code" mandate).
- Generated slides are persisted to the `slides` collection with normalized fields.
- Live progress is published to Redis pub/sub on `v4:progress:{project_id}` so the
  existing WebSocket layer can stream stage events to the frontend.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form
from motor.motor_asyncio import AsyncIOMotorDatabase

import structlog

from app.config import settings
from app.database import get_db
from app.dependencies import optional_auth
from app.models.generation_input_v4 import (
    GenerationInputV4,
    InputAnalysisResult,
)
from app.models.presentation import GenerationState
from app.services.input_analyzer import InputAnalyzer
from app.services.llm.model_router import get_model_router
from app.services.v4 import V4ContentPipeline
from app.services.v4.content_pipeline import make_redis_progress_emitter
from app.services.v4.slide_count_resolver import resolve_requested_count

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v4", tags=["Generation V4"])


# ── Persistence helpers (skeleton + slim research snapshot) ─────────


def _serialize_skeleton_slide(s: Any) -> dict[str, Any]:
    """Serialize a SlideSkeleton dataclass to a JSON-safe dict for Mongo."""
    return {
        "index": getattr(s, "index", 0),
        "intent": getattr(s, "intent", ""),
        "purpose": getattr(s, "purpose", ""),
        "headline_target": getattr(s, "headline_target", ""),
        "key_points": list(getattr(s, "key_points", []) or []),
        "density_target": getattr(s, "density_target", ""),
        "layout_hint": getattr(s, "layout_hint", ""),
        "evidence_refs": list(getattr(s, "evidence_refs", []) or []),
        "visual_cue": getattr(s, "visual_cue", ""),
        "rationale": getattr(s, "rationale", ""),
    }


def _slim_research_snapshot(research: Any) -> dict[str, Any]:
    """Cheap, regen-friendly research representation. Stores enough to
    rebuild a usable ResearchPacket for single-slide regeneration without
    re-running paid research APIs."""
    def _slim_cite(c: Any) -> dict[str, Any]:
        return {
            "title": (getattr(c, "title", "") or "")[:240],
            "url": getattr(c, "url", "") or "",
            "snippet": (getattr(c, "snippet", "") or "")[:600],
            "source": getattr(c, "source", "") or "",
            "source_authority": float(getattr(c, "source_authority", 0.5) or 0.5),
            "published_at": getattr(c, "published_at", None),
        }
    return {
        "query": getattr(research, "query", "") or "",
        "industry": getattr(research, "industry", None),
        "company_name": getattr(research, "company_name", None),
        "citations": [_slim_cite(c) for c in (getattr(research, "citations", []) or [])][:60],
        "news_citations": [_slim_cite(c) for c in (getattr(research, "news_citations", []) or [])][:30],
        "financial_data": getattr(research, "financial_data", {}) or {},
        "social_signals": getattr(research, "social_signals", {}) or {},
    }


# ═══════════════════════════════════════════════════════════════════
# PRE-FLIGHT: ANALYZE INPUT
# ═══════════════════════════════════════════════════════════════════

@router.post("/analyze-input", response_model=InputAnalysisResult)
async def analyze_input(
    body: GenerationInputV4,
    user: dict | None = Depends(optional_auth),
) -> InputAnalysisResult:
    """Run pre-flight analyzer to extract entities, missing context, suggested slide types."""
    analyzer = InputAnalyzer()
    return await analyzer.analyze(body)


# ═══════════════════════════════════════════════════════════════════
# GENERATE — V4 Skeleton-of-Thought pipeline
# ═══════════════════════════════════════════════════════════════════

@router.post("/generate")
async def generate_v4(
    body: GenerationInputV4,
    background_tasks: BackgroundTasks,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    user_id = user["user_id"] if user else "dev-test-user"
    user_role = (user or {}).get("role", "guest")
    is_premium_user = user_role == "premium"
    # In non-production environments every authenticated user can use premium
    # mode so local testing never trips the subscription gate. Production still
    # enforces the role check below.
    is_dev_env = settings.ENVIRONMENT != "production"

    # ── Mode permission gate ──
    if (
        body.mode == "premium"
        and not is_premium_user
        and user_id != "dev-test-user"
        and not is_dev_env
    ):
        raise HTTPException(
            status_code=403,
            detail="Premium mode requires a premium subscription",
        )

    # ── Slide count limits ──
    # Single universal cap. Pydantic already enforces ge=1, le=50 on every
    # slide_count field; this guard is defense-in-depth and yields a
    # cleaner 400 message if a malformed payload bypasses validation.
    max_slides = 50
    min_slides = 1
    target_count = body.effective_slide_count
    if target_count is not None and (target_count < min_slides or target_count > max_slides):
        raise HTTPException(
            status_code=400,
            detail=f"slide_count must be between {min_slides} and {max_slides}",
        )

    # ── Run input analysis (cheap, fast) ──
    analyzer = InputAnalyzer()
    analysis = await analyzer.analyze(body)

    # ── Plan 02: resolve final slide count BEFORE the pipeline starts ──
    # The resolver is the single source of truth for deck length. Past
    # this line, ``target_count`` is guaranteed to be a non-None int in
    # ``[1, 50]``; downstream code (skeleton planner, parallel writer,
    # slide compiler, image pipeline) treats it as required.
    resolved_count = resolve_requested_count(
        user_supplied=body.effective_slide_count,
        analyzer_suggested=analysis.suggested_slide_count,
        purpose=analysis.detected_purpose.value if analysis.detected_purpose else None,
        mode=body.mode,
        project_id=None,  # presentation row not yet created
    )
    target_count = resolved_count

    # ── Resolve user-selected slide types (Premium only) ──
    user_slide_types: Optional[list[str]] = _resolve_slide_types(body, analysis)

    # ── Resolve company / industry from structured input or analysis ──
    company_name = analysis.detected_company_name
    industry = analysis.detected_industry
    if body.premium_structured_input and body.premium_structured_input.company:
        company_name = company_name or body.premium_structured_input.company.name
        industry = industry or body.premium_structured_input.company.industry

    # ── Create presentation record ──
    project_id = str(ObjectId())
    title = body.effective_topic
    if company_name:
        title = f"{company_name} — {analysis.detected_purpose.value.replace('_', ' ').title()}"

    theme_id = _extract_theme_id(body)
    brand_payload = _extract_brand(body)
    design_profile = {
        "theme_id": theme_id,
        "brand": brand_payload,
        "user_provided": bool(brand_payload) or bool(theme_id),
    }

    await db.presentations.insert_one({
        "_id": project_id,
        "user_id": user_id,
        "title": title[:200],
        "description": _extract_description(body),
        "mode": body.mode,
        "created_from": "ai_v4",
        "theme_id": theme_id,
        "design_profile": design_profile,
        "slide_count": 0,
        "generation_state": GenerationState.IDLE.value,
        "generation_progress": 0,
        "generation_message": "Starting V4 pipeline...",
        "generation_error": None,
        "input_method": body.input_method.value,
        "input_analysis": analysis.model_dump(),
        "v4_input": body.model_dump(),
        "user_slide_types": user_slide_types,
        "industry": industry,
        "company_name": company_name,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })

    # ── Build structured context (Premium): real team, financials,
    #    competitors, market, fundraising, content directives. This is the
    #    data that was previously dropped between router and writer.
    from app.services.v4.structured_context import build_structured_context
    if body.premium_structured_input is not None:
        structured_context = build_structured_context(
            body.premium_structured_input.model_dump(exclude_none=True)
        )
    elif body.premium_prompt_input is not None:
        # premium_prompt_input carries only a prompt + optional directives
        pp = body.premium_prompt_input.model_dump(exclude_none=True)
        directives = pp.get("content_directives")
        structured_context = {"content_directives": directives} if directives else {}
    else:
        structured_context = {}

    # ── Kick off the V4 pipeline in the background ──
    background_tasks.add_task(
        _run_v4_pipeline,
        project_id=project_id,
        user_id=user_id,
        user_query=_build_user_query(body),
        analysis_dump=analysis.model_dump(),
        mode=body.mode,
        purpose=analysis.detected_purpose.value,
        industry=industry,
        company_name=company_name,
        user_slide_types=user_slide_types,
        target_slide_count=target_count,
        structured_context=structured_context,
    )

    return {
        "project_id": project_id,
        "status": "started",
        "mode": body.mode,
        "pipeline": "v4_skeleton_of_thought",
        "analysis": {
            "detected_purpose": analysis.detected_purpose.value,
            "detected_audience": analysis.detected_audience,
            "suggested_slide_count": analysis.suggested_slide_count,
            "input_richness_score": analysis.input_richness_score,
            "missing_context_count": len(analysis.missing_context),
            "entities_found": len(analysis.entities),
            "user_slide_types": user_slide_types,
        },
        "ws_url": f"/ws/v4/progress/{project_id}",
        "legacy_ws_url": f"/ws/generation/{project_id}",
        "progress_channel": f"v4:progress:{project_id}",
    }


# ═══════════════════════════════════════════════════════════════════
# STATUS
# ═══════════════════════════════════════════════════════════════════

@router.get("/generation/{project_id}")
async def get_generation_status(
    project_id: str,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    user_id = user["user_id"] if user else "dev-test-user"
    doc = await db.presentations.find_one({"_id": project_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Generation not found")
    if doc.get("user_id") != user_id and user_id != "dev-test-user":
        raise HTTPException(status_code=404, detail="Generation not found")

    # Fetch the last 30 progress events from Redis (best-effort)
    progress_log: list[dict] = []
    try:
        from app.utils.rate_limiter import get_redis
        import json as _json
        r = await get_redis()
        if r is not None:
            entries = await r.lrange(f"v4:progress_log:{project_id}", -30, -1)
            progress_log = [_json.loads(e) for e in entries]
    except Exception:
        pass

    return {
        "project_id": project_id,
        "status": doc.get("generation_state", "idle"),
        "progress": doc.get("generation_progress", 0),
        "message": doc.get("generation_message", ""),
        "error": doc.get("generation_error"),
        "slide_count": doc.get("slide_count", 0),
        "mode": doc.get("mode", "standard"),
        "title": doc.get("title"),
        "input_analysis": doc.get("input_analysis"),
        "overall_score": doc.get("overall_score"),
        "generation_id": doc.get("generation_id"),
        "duration_ms": doc.get("duration_ms"),
        "llm_trace_summary": doc.get("llm_trace_summary") or [],
        "llm_trace_count": doc.get("llm_trace_count", 0),
        "progress_log": progress_log,
    }


@router.get("/generation/{project_id}/slides")
async def get_compiled_slides(
    project_id: str,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Sandbox-ready payload: compiled JSX slides + resolved design tokens.

    The editor calls this once the SSE stream emits `completed` (or
    `compiled_slides_ready`) to hydrate the `SandboxFrame` iframe.
    """
    user_id = user["user_id"] if user else "dev-test-user"
    doc = await db.presentations.find_one(
        {"_id": project_id},
        {
            "user_id": 1,
            "title": 1,
            "compiled_slides": 1,
            "design_tokens": 1,
            "narrative_arc": 1,
            "generation_state": 1,
            "slide_count": 1,
            "overall_score": 1,
            # v3-final Phase 1 — deck-level slots (Day 1 wires them; later
            # phases populate). Always projected so consumers get a stable
            # schema even when generation predates the schema bump.
            "design_system": 1,
            "brand_kit": 1,
        },
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Generation not found")
    if doc.get("user_id") != user_id and user_id != "dev-test-user":
        raise HTTPException(status_code=404, detail="Generation not found")

    return {
        "project_id": project_id,
        "status": doc.get("generation_state", "idle"),
        "title": doc.get("title"),
        "narrative_arc": doc.get("narrative_arc"),
        "slide_count": doc.get("slide_count", 0),
        "overall_score": doc.get("overall_score"),
        "compiled_slides": doc.get("compiled_slides") or [],
        "design_tokens": doc.get("design_tokens") or {},
        # v3-final Phase 1 — emit None (not {}) when unpopulated so
        # frontend can distinguish "not yet generated" from "generated empty".
        "design_system": doc.get("design_system"),
        "brand_kit": doc.get("brand_kit"),
    }


# ═══════════════════════════════════════════════════════════════════
# DOCUMENT UPLOAD — extract + embed user-provided source material
# ═══════════════════════════════════════════════════════════════════

_ALLOWED_EXTS = {".pdf", ".docx", ".txt", ".md", ".csv", ".json"}
_MAX_BYTES = 15 * 1024 * 1024  # 15 MB hard cap


@router.post("/documents/upload")
async def upload_source_document(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Upload a source document, extract its text, chunk it, and embed into the
    per-project Chroma store so the generator can retrieve it during research.

    Supported: PDF, DOCX, TXT, MD, CSV, JSON (up to 15 MB).
    """
    import asyncio as _asyncio
    import hashlib as _hashlib
    import tempfile as _tempfile
    from pathlib import Path as _Path

    from app.services.v4.document_extractor import extract_document, chunk_text
    from app.services.v4.research_store import persist_document_chunks

    if not file.filename:
        raise HTTPException(status_code=400, detail="filename required")
    ext = _Path(file.filename).suffix.lower()
    if ext not in _ALLOWED_EXTS:
        raise HTTPException(status_code=415, detail=f"unsupported type {ext}; allowed={sorted(_ALLOWED_EXTS)}")

    # Auth/ownership check — caller must own the project (or be dev-test).
    user_id = user["user_id"] if user else "dev-test-user"
    proj = await db.presentations.find_one({"_id": project_id}, {"user_id": 1})
    if proj and proj.get("user_id") not in (user_id, "dev-test-user") and user_id != "dev-test-user":
        raise HTTPException(status_code=404, detail="project not found")

    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="empty file")
    if len(raw) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"file exceeds {_MAX_BYTES // (1024*1024)}MB limit")

    doc_hash = _hashlib.sha256(raw).hexdigest()[:24]

    # Write to temp, extract, delete.
    tmp_path: _Path | None = None
    try:
        with _tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tf:
            tf.write(raw)
            tmp_path = _Path(tf.name)
        extracted = await _asyncio.to_thread(extract_document, tmp_path)
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass

    if extracted.error:
        raise HTTPException(status_code=422, detail=f"extraction failed: {extracted.error}")
    if not extracted.text or len(extracted.text.strip()) < 20:
        raise HTTPException(status_code=422, detail="document appears empty after extraction")

    chunks = chunk_text(extracted.text, chunk_chars=1200, overlap=150)
    n_persisted = await persist_document_chunks(
        project_id=project_id,
        doc_id=doc_hash,
        chunks=chunks,
        metadata={
            "filename": file.filename[:200],
            "mime_type": extracted.mime_type,
            "word_count": extracted.word_count,
        },
    )

    # Record an audit row on the project doc.
    try:
        await db.presentations.update_one(
            {"_id": project_id},
            {"$push": {"source_documents": {
                "doc_id": doc_hash,
                "filename": file.filename[:200],
                "mime_type": extracted.mime_type,
                "word_count": extracted.word_count,
                "n_chunks": len(chunks),
                "n_persisted": n_persisted,
                "uploaded_at": datetime.now(timezone.utc),
                "uploaded_by": user_id,
            }}},
        )
    except Exception as e:
        logger.warning("doc_upload.audit_failed", error=str(e))

    return {
        "ok": True,
        "doc_id": doc_hash,
        "filename": file.filename,
        "mime_type": extracted.mime_type,
        "word_count": extracted.word_count,
        "n_chunks": len(chunks),
        "n_persisted": n_persisted,
        "embedded": n_persisted > 0,
    }


# ═══════════════════════════════════════════════════════════════════
# BACKGROUND TASK — V4 pipeline runner
# ═══════════════════════════════════════════════════════════════════

async def _run_v4_pipeline(
    *,
    project_id: str,
    user_id: str,
    user_query: str,
    analysis_dump: dict[str, Any],
    mode: str,
    purpose: str,
    industry: Optional[str],
    company_name: Optional[str],
    user_slide_types: Optional[list[str]],
    target_slide_count: Optional[int],
    structured_context: Optional[dict[str, Any]] = None,
) -> None:
    """Run the full V4 pipeline, persist slides, update generation state."""
    db = get_db()
    progress_emitter = make_redis_progress_emitter(project_id)
    model_router = get_model_router()
    llm_trace_summary: list[dict[str, Any]] = []
    llm_trace_count = 0

    async def _emit_and_persist(stage: str, payload: dict[str, Any]) -> None:
        """Emit to Redis and update the presentation doc with coarse progress."""
        await progress_emitter(stage, payload)
        progress_pct = _stage_to_progress(stage, payload)
        update: dict[str, Any] = {
            "generation_message": _stage_message(stage, payload),
            "updated_at": datetime.now(timezone.utc),
        }
        if progress_pct is not None:
            update["generation_progress"] = progress_pct
            update["generation_state"] = GenerationState.GENERATING_CONTENT.value
        try:
            await db.presentations.update_one({"_id": project_id}, {"$set": update})
        except Exception:
            pass

    try:
        await _emit_and_persist("pipeline_start", {"mode": mode})
        model_router.start_trace(project_id)

        pipeline = V4ContentPipeline()
        # Load presentation-level optional inputs (premium icon upload,
        # user-provided design profile from the Design step, and any
        # team photos prefilled via POST /team-prefill before generation).
        proj = await db.presentations.find_one(
            {"_id": project_id},
            {"company_icon_url": 1, "design_profile": 1, "team_prefill": 1},
        )
        company_icon_url = (proj or {}).get("company_icon_url")
        design_profile = (proj or {}).get("design_profile")
        team_prefill = (proj or {}).get("team_prefill") or []

        # Merge team_prefill into structured_context so the team_resolver
        # can skip person-image search for user-supplied photos.
        merged_ctx: dict[str, Any] = dict(structured_context or {})
        if team_prefill:
            merged_ctx["team_prefill"] = team_prefill

        result = await pipeline.generate(
            project_id=project_id,
            user_id=user_id,
            user_query=user_query,
            analysis=analysis_dump,
            mode=mode,
            purpose=purpose,
            industry=industry,
            company_name=company_name,
            user_slide_types=user_slide_types,
            target_slide_count=target_slide_count,
            company_icon_url=company_icon_url,
            design_profile=design_profile,
            structured_context=merged_ctx,
            progress=_emit_and_persist,
        )
        llm_trace = model_router.consume_trace(project_id)
        llm_trace_summary = model_router.summarize_trace(llm_trace)
        llm_trace_count = len(llm_trace)

        # ── Persist slides to MongoDB ──
        # NOTE: `db.slides` has a unique index on `(presentation_id, index)`
        # (see app/database.py::_create_indexes). In the v4 pipeline the
        # project IS the presentation, so we MUST populate `presentation_id`
        # or every slide gets `presentation_id: null`, colliding on the
        # second insert with "Duplicate key violation on presentation_id_1_index_1".
        # We keep `project_id` too because v4_editor.py queries by it.
        # NOTE on race with the image stage:
        # The Stage 4.7 image generator runs concurrently with this code path
        # and writes `image_url`/`image_source` directly to `db.slides` via
        # update_one as each image completes. Some of those updates may
        # finish *before* this insertion runs (especially for fast tiers).
        # If we insert_many with `image_url: None`, we silently clobber any
        # image URL that was written first.
        # We therefore upsert per-slide and use `$setOnInsert` for the
        # image fields, so concurrently-written image data is preserved.
        # We also use `$set` for the slide content (which the image stage
        # never touches) and `$setOnInsert` for the immutable `_id`.
        for s in result.slides:
            existing_image_url = getattr(s, "imageUrl", None) or getattr(s, "image_url", None)
            existing_image_source = getattr(s, "image_source", None)
            existing_image_position = getattr(s, "image_position", None)
            existing_image_intent = getattr(s, "image_intent", None)
            doc_set = {
                "presentation_id": project_id,
                "project_id": project_id,
                "index": s.index,
                "intent": s.intent,
                "layout": s.layout,
                "headline": s.headline,
                "subheadline": s.subheadline,
                "bullets": s.bullets,
                "body": s.body,
                "stat_blocks": s.stat_blocks,
                "quote": s.quote,
                "chart": s.chart,
                "table": s.table,
                "timeline": s.timeline,
                "comparison": s.comparison,
                "diagram": s.diagram,
                "image_prompt": s.image_prompt,
                "speaker_notes": s.speaker_notes,
                "citations": s.citations,
                "render_decision": s.render_decision,
                "team_members": getattr(s, "team_members", []) or [],
                "requires_user_input": bool(getattr(s, "requires_user_input", False)),
                "user_input_kind": getattr(s, "user_input_kind", None),
                "user_input_reason": getattr(s, "user_input_reason", None),
                "company_icon_url": getattr(s, "company_icon_url", None),
                "rationale": getattr(s, "rationale", "") or "",
                "purpose": getattr(s, "purpose", "") or purpose or "",
                "raw": s.raw,
            }
            doc_set_on_insert = {
                "_id": str(ObjectId()),
                "created_at": datetime.now(timezone.utc),
                # Only seed image fields if doc is new; the image stage may
                # have already written them via its own update_one.
                "image_url": existing_image_url,
                "image_source": existing_image_source,
                "image_position": existing_image_position,
                "image_intent": existing_image_intent,
            }
            # If this code path itself produced an image_url (rare; only
            # when the orchestrator already wrote it onto the GeneratedSlide),
            # we still want it persisted on top of any earlier null write.
            if existing_image_url:
                doc_set["image_url"] = existing_image_url
                doc_set["image_source"] = existing_image_source
                if existing_image_position:
                    doc_set["image_position"] = existing_image_position
                if existing_image_intent:
                    doc_set["image_intent"] = existing_image_intent
            await db.slides.update_one(
                {"presentation_id": project_id, "index": s.index},
                {"$set": doc_set, "$setOnInsert": doc_set_on_insert},
                upsert=True,
            )

        await db.presentations.update_one(
            {"_id": project_id},
            {"$set": {
                "title": result.deck_title[:200],
                "narrative_arc": result.narrative_arc,
                "purpose": purpose or "",
                "intent_summary": [s.intent for s in result.slides],
                "v4_skeleton": {
                    "title": result.skeleton.title,
                    "narrative_arc": result.skeleton.narrative_arc,
                    "slides": [_serialize_skeleton_slide(s) for s in result.skeleton.slides],
                },
                "v4_research_snapshot": _slim_research_snapshot(result.research),
                "v4_mode": result.mode,
                "slide_count": len(result.slides),
                "generation_state": GenerationState.COMPLETED.value,
                "generation_progress": 100,
                "generation_message": "Complete",
                "overall_score": result.critic.overall,
                "duration_ms": result.duration_ms,
                "generation_id": result.generation_id,
                "llm_trace_summary": llm_trace_summary,
                "llm_trace_count": llm_trace_count,
                "design_tokens": result.design_tokens,
                "compiled_slides": result.compiled_slides,
                # v3-final Phase 1 — deck-level slots persisted Day 1.
                # `design_system` populated by Phase 2 (Day 2),
                # `brand_kit` by Phase 2.2 (v1.1). Until then the
                # pipeline returns None for both, matching the GET
                # contract above.
                "design_system": result.design_system,
                "brand_kit": result.brand_kit,
                "completed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }},
        )

        await progress_emitter("persisted", {
            "n_slides": len(result.slides),
            "overall_score": round(result.critic.overall, 2),
            "llm_trace_summary": llm_trace_summary,
            "llm_trace_count": llm_trace_count,
        })

    except Exception as e:
        logger.exception("v4_pipeline_failed", project_id=project_id, error=str(e))
        if not llm_trace_summary and llm_trace_count == 0:
            llm_trace = model_router.consume_trace(project_id)
            llm_trace_summary = model_router.summarize_trace(llm_trace)
            llm_trace_count = len(llm_trace)
        try:
            await db.presentations.update_one(
                {"_id": project_id},
                {"$set": {
                    "generation_state": GenerationState.FAILED.value,
                    "generation_error": str(e)[:1000],
                    "generation_message": "Generation failed",
                    "llm_trace_summary": llm_trace_summary,
                    "llm_trace_count": llm_trace_count,
                    "updated_at": datetime.now(timezone.utc),
                }},
            )
            await progress_emitter("error", {
                "error": str(e)[:500],
                "llm_trace_summary": llm_trace_summary,
                "llm_trace_count": llm_trace_count,
            })
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

# Coarse progress mapping per stage emitted by V4ContentPipeline
_STAGE_PROGRESS: dict[str, int] = {
    "pipeline_start": 5,
    "conversational_qa": 10,
    "research": 25,
    "skeleton": 45,
    "writers": 80,
    "critic": 95,
    "complete": 100,
}


def _stage_to_progress(stage: str, payload: dict[str, Any]) -> Optional[int]:
    if stage == "stage_complete":
        return _STAGE_PROGRESS.get(payload.get("stage", ""))
    if stage == "complete":
        return 100
    if stage == "pipeline_start":
        return 5
    return None


def _stage_message(stage: str, payload: dict[str, Any]) -> str:
    if stage == "stage_start":
        s = payload.get("stage", "?")
        return {
            "conversational_qa": "A few quick questions to build your deck...",
            "exemplars": "Loading lessons from past decks",
            "research": "Gathering research from real sources",
            "skeleton": "Planning the deck structure",
            "writers": f"Writing {payload.get('n_slides', '?')} slides in parallel",
            "critic": "Evaluating quality and refining",
        }.get(s, f"Running {s}")
    if stage == "stage_complete":
        return f"Finished: {payload.get('stage', '?')}"
    if stage == "complete":
        return f"Complete — score {payload.get('overall_score', '?')}/10"
    if stage == "skeleton_ready":
        return f"Outline ready ({len(payload.get('slides', []))} slides)"
    if stage == "slide_drafted":
        return f"Drafted slide {payload.get('index')}: {payload.get('headline', '')[:60]}"
    if stage == "error":
        return f"Error: {payload.get('error', '')[:120]}"
    return stage


def _resolve_slide_types(
    body: GenerationInputV4,
    analysis: InputAnalysisResult,
) -> Optional[list[str]]:
    """Premium uses user-picked or analyzer-suggested slide types. Standard auto-decides."""
    if body.mode != "premium":
        return None

    # 1. Explicit user picks via content directives
    directives = None
    if body.premium_structured_input:
        directives = body.premium_structured_input.content_directives
    elif body.premium_prompt_input:
        directives = body.premium_prompt_input.content_directives

    if directives and directives.include_slides:
        explicit = list(directives.include_slides)
        if directives.exclude_slides:
            explicit = [s for s in explicit if s not in set(directives.exclude_slides)]
        if explicit:
            return explicit

    # 2. Fall back to analyzer suggestions
    if analysis.suggested_slide_types:
        suggested = list(analysis.suggested_slide_types)
        if directives and directives.exclude_slides:
            suggested = [s for s in suggested if s not in set(directives.exclude_slides)]
        return suggested

    return None


def _build_user_query(body: GenerationInputV4) -> str:
    """Compose a single rich query string from whichever input variant is active."""
    if body.standard_input:
        return body.standard_input.prompt
    if body.premium_prompt_input:
        return body.premium_prompt_input.prompt
    if body.premium_structured_input:
        s = body.premium_structured_input
        parts = [f"Topic: {s.topic}", f"Audience: {s.audience}", s.description]
        if s.company:
            parts.append(f"Company: {s.company.name} ({s.company.industry or 'industry n/a'})")
            if s.company.tagline:
                parts.append(f"Tagline: {s.company.tagline}")
        if s.financials:
            fin = s.financials
            metrics = []
            if fin.arr: metrics.append(f"ARR ${fin.arr:,.0f}")
            if fin.mrr: metrics.append(f"MRR ${fin.mrr:,.0f}")
            if fin.customers_count: metrics.append(f"{fin.customers_count} customers")
            if fin.revenue_growth_pct: metrics.append(f"{fin.revenue_growth_pct}% growth")
            if metrics:
                parts.append("Metrics: " + ", ".join(metrics))
        if s.market and (s.market.tam or s.market.sam):
            parts.append(f"Market: TAM={s.market.tam or '?'}, SAM={s.market.sam or '?'}")
        if s.competitors:
            parts.append("Competitors: " + ", ".join(c.name for c in s.competitors[:5]))
        if s.fundraising and s.fundraising.amount:
            parts.append(f"Raising: ${s.fundraising.amount:,.0f} ({s.fundraising.round_type or 'round'})")
        return "\n".join(parts)
    return "Untitled presentation"


def _extract_description(body: GenerationInputV4) -> str:
    if body.standard_input:
        return body.standard_input.prompt[:2000]
    if body.premium_structured_input:
        return body.premium_structured_input.description[:2000]
    if body.premium_prompt_input:
        return body.premium_prompt_input.prompt[:2000]
    return ""


def _extract_theme_id(body: GenerationInputV4) -> str | None:
    if body.standard_input:
        return body.standard_input.theme_id
    if body.premium_structured_input:
        return body.premium_structured_input.theme_id
    if body.premium_prompt_input:
        return body.premium_prompt_input.theme_id
    return None


def _extract_brand(body: GenerationInputV4) -> dict[str, Any] | None:
    """Return the active BrandAssets payload as a dict, or None if user skipped design.

    All brand fields are optional; returning a dict here signals the downstream
    designer/renderers to honor user choices. When None, the pipeline is free to
    auto-select palette + typography based on purpose and tone.
    """
    brand = None
    if body.standard_input:
        brand = body.standard_input.brand
    elif body.premium_prompt_input:
        brand = body.premium_prompt_input.brand
    elif body.premium_structured_input:
        brand = body.premium_structured_input.brand
    if brand is None:
        return None
    # Strip None-valued keys so downstream can tell "user set primary only" from "user set nothing".
    dumped = brand.model_dump(exclude_none=True)
    return dumped or None
