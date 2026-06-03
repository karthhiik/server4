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

import asyncio
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from motor.motor_asyncio import AsyncIOMotorDatabase

import structlog

from app.config import settings
from app.utils.upload_security import enforce_upload_constraints
from app.database import get_db
from app.dependencies import optional_auth, require_auth
from app.models.generation_input_v4 import (
    AudienceSophistication,
    ExtractedEntity,
    FundingStage,
    GenerationInputV4,
    InputAnalysisResult,
    MissingContext,
    PresentationPurpose,
)
from app.models.presentation import GenerationState
from app.services.input_analyzer import InputAnalyzer
from app.services.llm.model_router import get_model_router
from app.services.v4 import V4ContentPipeline
from app.services.v4.content_pipeline import make_redis_progress_emitter
from app.services.v4.slide_count_resolver import resolve_requested_count
from app.services.v4.token_tracker import aggregate_token_usage
from app.services.llm.cost_table import estimate_cost_from_token_usage
from app.services.v4.session_manager import SessionManager
from app.services.v4.conversational_question_generator import ConversationalQuestionGenerator
from app.services.v4.auto_purpose_selector import AutoPurposeSelector
from app.services.v4.purpose_configs import PURPOSE_CONFIGS
from app.services.v4.design_memory import extract_design_memory
from app.services.v4.production_quality_gate import (
    compute_export_readiness,
    summarize_production_quality_gate,
)
from app.services.observability import counter_snapshot

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

@router.get("/layouts")
async def list_canonical_layouts() -> dict[str, Any]:
    """Return the canonical layout catalog the V4 generator emits.

    Frontends (``barise-editorial-main`` and ``lliveupdatedstreaming``)
    consume this instead of maintaining their own alias maps. The payload
    is a stable contract: the ``layouts[].id`` set is the canonical 13
    layouts, ``alias_map`` is the lowercase-hyphenated lookup the FE uses
    to normalize writer / editor / legacy strings.

    Stays in sync with:
    - ``app.services.v4.skeleton_planner._CANONICAL_LAYOUTS``
    - ``app.routers.v4_editor._ALLOWED_LAYOUTS``
    - The kit names in ``lliveupdatedstreaming/sandbox/src/kit/index.ts``

    No auth required — this is a static catalog with no PII.
    """
    from app.services.v4.layout.canonical import catalog_payload

    return catalog_payload()


@router.get("/modes")
async def list_generation_modes() -> dict[str, Any]:
    """Return the generation modes server4 actually accepts.

    The frontend Mode stage reads this lightweight contract so the visible
    Standard/Premium choices stay aligned with the Pydantic request model,
    production premium gating, and edit capabilities.
    """
    max_slides = 50
    stages = ["mode", "brief", "archive", "direction", "machine", "edit", "studio", "press"]
    return {
        "version": "v4",
        "default_mode": "standard",
        "modes": [
            {
                "id": "standard",
                "label": "Standard Mode",
                "input_methods": ["prompt"],
                "default_input_method": "prompt",
                "default_generate_images": False,
                "default_generate_notes": False,
                "min_slides": 1,
                "max_slides": max_slides,
                "purpose_default": PresentationPurpose.SEED_ROUND.value,
                "writing_style_default": "yc_crisp",
                "supports": {
                    "templates": True,
                    "themes": True,
                    "visual_direction": True,
                    "effects": True,
                    "brand": True,
                    "team_members": False,
                    "structured_financials": False,
                    "speaker_notes": False,
                    "image_generation": True,
                    "slide_editing": True,
                    "deck_editing": True,
                },
                "stages": stages,
                "summary": "Fast prompt-first generation for a founder draft with editable slide content.",
            },
            {
                "id": "premium",
                "label": "Premium Mode",
                "input_methods": ["prompt", "structured"],
                "default_input_method": "prompt",
                "default_generate_images": True,
                "default_generate_notes": True,
                "min_slides": 1,
                "max_slides": max_slides,
                "purpose_default": PresentationPurpose.PITCH_DECK.value,
                "writing_style_default": "yc_crisp",
                "requires_subscription_in_production": True,
                "supports": {
                    "templates": True,
                    "themes": True,
                    "visual_direction": True,
                    "effects": True,
                    "brand": True,
                    "team_members": True,
                    "structured_financials": True,
                    "speaker_notes": True,
                    "image_generation": True,
                    "slide_editing": True,
                    "deck_editing": True,
                },
                "stages": stages,
                "summary": "Research, brand, team, evidence, image, and speaker-note aware generation.",
            },
        ],
    }


@router.get("/admin/metrics")
async def get_v4_admin_metrics(user: dict = Depends(require_auth)) -> dict:
    """V4 counter snapshot. Admin-only and hidden from non-admin callers."""
    role = user.get("role", "")
    set_role = user.get("setuserrole", "")
    if role != "admin" and set_role != "admin":
        raise HTTPException(status_code=404, detail="Not Found")
    return await counter_snapshot()


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
    request_id = str(uuid4())
    try:
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            project_id=None,
            user_id=user_id,
        )
    except Exception:
        pass
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

    # ── Run submit-time input analysis (strictly local, deterministic) ──
    #
    # The full analyzer is still available at /api/v4/analyze-input for
    # pre-flight UX, but generation submission must not block on model
    # fallbacks before the client receives a project_id. A previous premium
    # run waited on several exhausted/slow free-tier providers here and timed
    # out before the background task could even start. This local analysis is
    # grounded only in user-provided fields and keeps the real-time contract
    # stable under provider pressure.
    analysis = _build_fast_generation_analysis(body)

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
    visual_direction = _extract_visual_direction(body)
    body_template_id = _extract_template_id(body)
    effects_payload = _extract_effects(body)
    design_profile = {
        "theme_id": theme_id,
        "brand": brand_payload,
        "user_provided": (
            bool(brand_payload)
            or bool(theme_id)
            or bool(visual_direction)
            or bool(body_template_id)
            or bool(effects_payload)
        ),
        "visual_direction": visual_direction,
        "template_id": body_template_id,
        "effects": effects_payload,
    }

    await db.presentations.insert_one({
        "_id": project_id,
        "user_id": user_id,
        "title": title[:200],
        "description": _extract_description(body),
        "mode": body.mode,
        "created_from": "ai_v4",
        "request_id": request_id,
        "theme_id": theme_id,
        "template_id": body_template_id,
        "design_profile": design_profile,
        "slide_count": 0,
        "target_slide_count": target_count,
        "requested_slide_count": body.effective_slide_count,
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

    # ── Extract template_id from design_profile or input ──
    template_id = design_profile.get("template_id") if design_profile else None

    # ── Resolve generate_images flag while `body` is still in scope ──
    generate_images = _extract_generate_images(body)

    # ── Kick off the V4 pipeline ──
    # Slice 2 (Durable V4 Generation): when ``settings.V4_USE_CELERY_QUEUE``
    # is true the deck is dispatched to the content-fast / content-premium
    # queue so it survives an API process restart. When false (default), the
    # legacy in-process FastAPI BackgroundTasks path runs unchanged.
    pipeline_kwargs = dict(
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
        template_id=template_id,
        generate_images=generate_images,
        request_id=request_id,
    )
    dispatch = await _dispatch_v4_pipeline(
        background_tasks=background_tasks,
        db=db,
        project_id=project_id,
        mode=body.mode,
        pipeline_kwargs=pipeline_kwargs,
    )

    return {
        "project_id": project_id,
        "request_id": request_id,
        "status": "started",
        "mode": body.mode,
        "pipeline": "v4_skeleton_of_thought",
        # Slice 2: optional fields. Older clients ignoring unknown keys
        # keep working; newer clients can poll the Celery job state.
        "execution": dispatch["execution"],  # "celery" | "background_tasks"
        "celery_task_id": dispatch.get("celery_task_id"),
        "queue": dispatch.get("queue"),
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
        r = await asyncio.wait_for(get_redis(), timeout=0.25)
        if r is not None:
            entries = await asyncio.wait_for(
                r.lrange(f"v4:progress_log:{project_id}", -30, -1),
                timeout=0.4,
            )
            progress_log = [_json.loads(e) for e in entries]
    except Exception:
        pass

    drafted_slide_indices: set[int] = set()
    for event in progress_log:
        if event.get("stage") != "slide_drafted":
            continue
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        try:
            drafted_slide_indices.add(int(payload.get("index")))
        except (TypeError, ValueError):
            continue

    return {
        "project_id": project_id,
        "request_id": doc.get("request_id"),
        "status": doc.get("generation_state", "idle"),
        "progress": doc.get("generation_progress", 0),
        "message": doc.get("generation_message", ""),
        "error": doc.get("generation_error"),
        "slide_count": doc.get("slide_count", 0),
        "target_slide_count": doc.get("target_slide_count")
        or (doc.get("input_analysis") or {}).get("suggested_slide_count")
        or doc.get("slide_count", 0),
        "drafted_slide_count": len(drafted_slide_indices),
        "mode": doc.get("mode", "standard"),
        "title": doc.get("title"),
        "input_analysis": doc.get("input_analysis"),
        "overall_score": doc.get("overall_score"),
        "production_quality_gate": doc.get("production_quality_gate"),
        # Slice 1: stable export-readiness contract derived at completion
        # time. Older decks (pre-Slice 1) will have these as None; the
        # frontend treats None as "unknown" and is conservative.
        "export_ready": doc.get("export_ready"),
        "quality_state": doc.get("quality_state"),
        "export_blockers": doc.get("export_blockers") or [],
        # Slice 3 (Provider-Failure Visibility): null on older decks —
        # the frontend renders nothing when these are null/undefined.
        "failed_providers": doc.get("failed_providers") or [],
        "degraded_evidence": doc.get("degraded_evidence"),
        "evidence_density": doc.get("evidence_density"),
        "provider_summary": doc.get("provider_summary") or {},
        # Slice 2: surface durable-job metadata when present.
        "execution": "celery" if doc.get("celery_task_id") else "background_tasks",
        "celery_task_id": doc.get("celery_task_id"),
        "celery_queue": doc.get("celery_queue"),
        "generation_id": doc.get("generation_id"),
        "duration_ms": doc.get("duration_ms"),
        "llm_trace_summary": doc.get("llm_trace_summary") or [],
        "llm_trace_count": doc.get("llm_trace_count", 0),
        "token_usage": doc.get("token_usage"),
        "cost_estimate": doc.get("cost_estimate"),
        "design_tokens": doc.get("design_tokens") or {},
        "design_recommendation": doc.get("design_recommendation")
        or ((doc.get("design_tokens") or {}).get("catalog_recommendation") if isinstance(doc.get("design_tokens"), dict) else None),
        "stage_timings": doc.get("stage_timings") or [],
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
            "template_id": 1,
            "narrative_arc": 1,
            "generation_state": 1,
            "slide_count": 1,
            "overall_score": 1,
            "production_quality_gate": 1,
            "export_ready": 1,
            "quality_state": 1,
            "export_blockers": 1,
            # Slice 3 (Provider-Failure Visibility) — projected even
            # for older decks; the GET payload returns null/[] in that
            # case and the frontend renders nothing.
            "failed_providers": 1,
            "degraded_evidence": 1,
            "evidence_density": 1,
            "provider_summary": 1,
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
        "production_quality_gate": doc.get("production_quality_gate"),
        "export_ready": doc.get("export_ready"),
        "quality_state": doc.get("quality_state"),
        "export_blockers": doc.get("export_blockers") or [],
        # Slice 3 (Provider-Failure Visibility): null on older decks.
        "failed_providers": doc.get("failed_providers") or [],
        "degraded_evidence": doc.get("degraded_evidence"),
        "evidence_density": doc.get("evidence_density"),
        "provider_summary": doc.get("provider_summary") or {},
        "compiled_slides": doc.get("compiled_slides") or [],
        "design_tokens": doc.get("design_tokens") or {},
        "design_recommendation": doc.get("design_recommendation")
        or ((doc.get("design_tokens") or {}).get("catalog_recommendation") if isinstance(doc.get("design_tokens"), dict) else None),
        "template_id": doc.get("template_id"),
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

    raw = await enforce_upload_constraints(
        file,
        allowed_exts=_ALLOWED_EXTS,
        max_bytes=_MAX_BYTES,
    )
    ext = _Path(file.filename or "").suffix.lower()

    # Auth/ownership check — caller must own the project (or be dev-test).
    user_id = user["user_id"] if user else "dev-test-user"
    proj = await db.presentations.find_one({"_id": project_id}, {"user_id": 1})
    if not proj:
        raise HTTPException(status_code=404, detail="project not found")
    if proj and proj.get("user_id") not in (user_id, "dev-test-user") and user_id != "dev-test-user":
        raise HTTPException(status_code=404, detail="project not found")

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

# ═══════════════════════════════════════════════════════════════════
# Slice 2 (Durable V4 Generation): dispatcher
# ═══════════════════════════════════════════════════════════════════
#
# When ``settings.V4_USE_CELERY_QUEUE`` is true, the pipeline is dispatched
# to the Celery ``content-fast`` (standard) or ``content-premium`` queue.
# Otherwise the legacy FastAPI ``BackgroundTasks`` path runs in-process.
#
# The dispatcher always falls back to BackgroundTasks if Celery dispatch
# raises (broker unreachable, serialisation error, etc.) so a misconfigured
# deployment never silently loses generations.
#
# This is purely additive — when the flag is off the dispatch path is
# byte-identical to the pre-Slice-2 behaviour.

async def _dispatch_v4_pipeline(
    *,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase,
    project_id: str,
    mode: str,
    pipeline_kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Dispatch the V4 pipeline to Celery or to FastAPI BackgroundTasks.

    Returns a small dict the route includes verbatim in its response so
    clients can observe the execution channel and the Celery task id when
    it exists. The shape is documented in ``POST /api/v4/generate``.
    """
    use_celery = bool(getattr(settings, "V4_USE_CELERY_QUEUE", False))
    if not use_celery:
        background_tasks.add_task(_run_v4_pipeline, **pipeline_kwargs)
        return {"execution": "background_tasks"}

    queue = (
        settings.V4_CELERY_QUEUE_PREMIUM
        if mode == "premium"
        else settings.V4_CELERY_QUEUE_STANDARD
    )
    try:
        # Imported lazily so a missing celery install (dev) doesn't kill
        # API import. The settings flag wouldn't be on without celery
        # available in production.
        from app.tasks.v4_generation_tasks import run_v4_generation

        async_result = run_v4_generation.apply_async(
            kwargs=pipeline_kwargs,
            queue=queue,
        )
        celery_task_id = str(async_result.id) if async_result is not None else None
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "v4_celery_dispatch_failed_falling_back_to_background_tasks",
            project_id=project_id,
            error=str(exc)[:240],
        )
        background_tasks.add_task(_run_v4_pipeline, **pipeline_kwargs)
        return {"execution": "background_tasks", "celery_dispatch_error": str(exc)[:240]}

    # Best-effort row tag so GET /generation/{id} can surface the
    # Celery task id and the reaper can identify v4-celery rows.
    try:
        await asyncio.wait_for(
            db.presentations.update_one(
                {"_id": project_id},
                {"$set": {
                    "celery_task_id": celery_task_id,
                    "celery_queue": queue,
                    "generation_message": "Queued for V4 worker",
                    "updated_at": datetime.now(timezone.utc),
                }},
            ),
            timeout=1.0,
        )
    except Exception:
        # Persistence failure here is non-fatal; the worker still starts.
        pass

    return {
        "execution": "celery",
        "celery_task_id": celery_task_id,
        "queue": queue,
    }


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
    template_id: Optional[str] = None,
    generate_images: bool = False,
    request_id: Optional[str] = None,
) -> None:
    """Run the full V4 pipeline, persist slides, update generation state."""
    db = get_db()
    progress_emitter = make_redis_progress_emitter(project_id)
    model_router = get_model_router()
    llm_trace_summary: list[dict[str, Any]] = []
    llm_trace_count = 0
    request_id = request_id or str(uuid4())
    try:
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            project_id=project_id,
            user_id=user_id,
        )
    except Exception:
        pass
    stage_timings: list[dict[str, Any]] = []
    last_stage: str | None = None
    last_stage_started_ms = int(time.time() * 1000)

    async def _emit_and_persist(stage: str, payload: dict[str, Any]) -> None:
        """Emit to Redis and update the presentation doc with coarse progress."""
        nonlocal last_stage, last_stage_started_ms, stage_timings
        await progress_emitter(stage, payload)
        if stage == "slide_drafted":
            return
        now_ms = int(time.time() * 1000)
        timing = {
            "stage": last_stage or stage,
            "duration_ms": max(0, now_ms - last_stage_started_ms),
            "started_at_ms": last_stage_started_ms,
        }
        stage_timings = (stage_timings + [timing])[-30:]
        logger.info(
            "v4_stage_timing",
            project_id=project_id,
            request_id=request_id,
            **timing,
        )
        last_stage = stage
        last_stage_started_ms = now_ms
        progress_pct = _stage_to_progress(stage, payload)
        update: dict[str, Any] = {
            "generation_message": _stage_message(stage, payload),
            "request_id": request_id,
            "stage_timings": stage_timings,
            "updated_at": datetime.now(timezone.utc),
        }
                ),
                timeout=1.0,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "v4_optional_project_context_timeout",
                project_id=project_id,
                error=str(exc)[:160],
            )
            proj = {}
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
            template_id=template_id,
            progress=_emit_and_persist,
            generate_images=generate_images,
        )
        llm_trace = model_router.consume_trace(project_id)
        llm_trace_summary = model_router.summarize_trace(llm_trace)
        llm_trace_count = len(llm_trace)

        # ── Token usage aggregation ──
        token_usage_summary = aggregate_token_usage(
            trace=llm_trace,
            generation_id=result.generation_id,
            project_id=project_id,
            mode=mode,
        )
        token_usage_compact = token_usage_summary.to_compact_dict()
        cost_estimate = estimate_cost_from_token_usage(token_usage_summary)
        await progress_emitter("token_usage", token_usage_compact)

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
        compiled_quality_by_index = {
            int(c.get("slide_index", i) if isinstance(c, dict) else i): (
                c.get("production_quality_gate") if isinstance(c, dict) else None
            )
            for i, c in enumerate(result.compiled_slides or [])
        }
        deck_production_quality_gate = (
            result.production_quality_gate
            if getattr(result, "production_quality_gate", None)
            else summarize_production_quality_gate(result.compiled_slides or [])
        )
        # ── Slice 1 (Trust Honesty) ────────────────────────────────
        # Derive a small, frontend-safe export-readiness verdict from the
        # gate so the editor / export route never has to re-implement
        # this logic. We keep generation_state == COMPLETED for legacy
        # contract preservation, but the truth lives in these fields.
        export_readiness = compute_export_readiness(deck_production_quality_gate)

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
                "links": getattr(s, "links", []),
                "render_decision": s.render_decision,
                "team_members": getattr(s, "team_members", []) or [],
                "requires_user_input": bool(getattr(s, "requires_user_input", False)),
                "user_input_kind": getattr(s, "user_input_kind", None),
                "user_input_reason": getattr(s, "user_input_reason", None),
                "company_icon_url": getattr(s, "company_icon_url", None),
                "rationale": getattr(s, "rationale", "") or "",
                "purpose": getattr(s, "purpose", "") or purpose or "",
                "raw": s.raw,
                # CTO CRITICAL: Per-slide background overrides from editor
                "background_color": getattr(s, "background_color", None) or None,
                "background_gradient": getattr(s, "background_gradient", None) or None,
                "layout_params": getattr(s, "layout_params", None) or None,
                "template_id": getattr(s, "template_id", None) or template_id,
                "template_zone_id": getattr(s, "template_zone_id", None),
                "template_kit_component": getattr(s, "template_kit_component", None),
                "template_required": bool(getattr(s, "template_required", True)),
                "template_placeholder_rules": getattr(s, "template_placeholder_rules", {}) or {},
                "icons": list(getattr(s, "icons", []) or []),
                "production_quality_gate": compiled_quality_by_index.get(int(s.index)),
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
                "token_usage": token_usage_summary.to_dict(),
                "cost_estimate": cost_estimate,
                "request_id": request_id,
                "stage_timings": stage_timings[-30:],
                "design_tokens": result.design_tokens,
                "design_recommendation": (
                    result.design_tokens.get("catalog_recommendation")
                    if isinstance(result.design_tokens, dict)
                    else None
                ),
                "design_memory": extract_design_memory(
                    design_tokens=result.design_tokens,
                ).to_dict(),
                "compiled_slides": result.compiled_slides,
                "template_id": template_id,
                # v3-final Phase 1 — deck-level slots persisted Day 1.
                # `design_system` populated by Phase 2 (Day 2),
                # `brand_kit` by Phase 2.2 (v1.1). Until then the
                # pipeline returns None for both, matching the GET
                # contract above.
                "design_system": result.design_system,
                "brand_kit": result.brand_kit,
                "production_quality_gate": deck_production_quality_gate,
                # Slice 1: persisted alongside the full gate so consumers
                # (editor, export, frontend) can branch on a stable contract
                # without re-deriving readiness. ``generation_state`` stays
                # ``completed`` for backwards compatibility.
                "export_ready": bool(export_readiness.get("export_ready")),
                "quality_state": str(export_readiness.get("quality_state") or "unknown"),
                "export_blockers": list(export_readiness.get("export_blockers") or []),
                # Slice 3 (Provider-Failure Visibility): persisted from
                # the pipeline result. Older decks have these as None
                # via a missing key — readers project them with `or`
                # defaults below.
                "failed_providers": list(getattr(result, "failed_providers", []) or []),
                "degraded_evidence": bool(getattr(result, "degraded_evidence", False)),
                "evidence_density": float(getattr(result, "evidence_density", 0.0) or 0.0),
                "provider_summary": dict(getattr(result, "provider_summary", {}) or {}),
                "completed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }},
        )

        await progress_emitter("compiled_slides_ready", {
            "n_slides": len(result.compiled_slides or []),
            "source_slides": len(result.slides),
            "overall_score": round(result.critic.overall, 2),
        })

        await progress_emitter("persisted", {
            "n_slides": len(result.slides),
            "overall_score": round(result.critic.overall, 2),
            "llm_trace_summary": llm_trace_summary,
            "llm_trace_count": llm_trace_count,
            "token_usage": token_usage_compact,
            "cost_estimate": cost_estimate,
            "request_id": request_id,
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
                    "request_id": request_id,
                    "stage_timings": stage_timings[-30:],
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
    "input_validation": 7,
    "conversational_qa": 10,
    "exemplars": 12,
    "company_preflight": 15,
    "research": 25,
    "research_and_skeleton_parallel": 35,
    "skeleton": 45,
    "skeleton_planning": 45,
    "skeleton_ready": 55,
    "writers": 80,
    "parallel_writers": 80,
    "slide_drafted": 82,
    "critic": 95,
    "slide_validation": 90,
    "semantic_intent_analysis": 91,
    "headline_quality_gate": 92,
    "quality_gate": 93,
    "unified_quality_gate": 94,
    "auto_regeneration": 95,
    "visual_asset_generation": 96,
    "production_quality_gate": 98,
    "design_direction": 97,
    "theme_consistency_check": 98,
    "persist": 99,
    "complete": 100,
}


_TECHNICAL_CONCEPT_SLIDE_TYPES: list[str] = [
    "title",
    "problem",
    "solution",
    "architecture",
    "how_it_works",
    "performance_benchmark",
    "scalability_advantage",
    "hardware_integration",
    "consensus_algorithm",
    "market",
    "business_model",
    "competition",
    "go_to_market",
    "ask",
    "thank_you",
]

_GENERIC_PITCH_SLIDE_TYPES: list[str] = [
    "title",
    "problem",
    "solution",
    "how_it_works",
    "market",
    "business_model",
    "competition",
    "go_to_market",
    "ask",
    "closing",
]


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
            "research_and_skeleton_parallel": "Researching sources and planning the deck structure",
            "skeleton": "Planning the deck structure",
            "skeleton_planning": "Planning the deck structure",
            "writers": f"Writing {payload.get('n_slides', '?')} slides in parallel",
            "parallel_writers": f"Writing {payload.get('n_slides', '?')} slides in parallel",
            "critic": "Evaluating quality and refining",
            "semantic_intent_analysis": "Checking slide intent and narrative flow",
            "headline_quality_gate": "Tightening slide headlines",
            "quality_gate": "Checking content quality",
            "unified_quality_gate": "Checking export readiness",
            "production_quality_gate": "Checking production readiness",
            "visual_asset_generation": "Preparing visual assets",
            "design_direction": "Applying design direction",
            "theme_consistency_check": "Checking theme consistency",
            "persist": "Saving deck",
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


def _extract_labeled_value(text: str, label: str) -> str | None:
    pattern = rf"{re.escape(label)}\s*:\s*(.+?)(?=\n[A-Za-z][A-Za-z ]{{1,40}}\s*:|$)"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    value = " ".join(match.group(1).strip().split())
    return value.rstrip(".") or None


def _coerce_purpose(value: Any) -> PresentationPurpose:
    if isinstance(value, PresentationPurpose):
        return value
    if isinstance(value, str):
        try:
            return PresentationPurpose(value)
        except ValueError:
            normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
            if normalized in {"investor_pitch", "vc_pitch", "fundraising", "pitch"}:
                return PresentationPurpose.PITCH_DECK
            if normalized in {"seed_round_pitch", "seed_round", "seed_pitch"}:
                return PresentationPurpose.SEED_ROUND
            if normalized in {"partnership_proposal", "partner_proposal", "partnership"}:
                return PresentationPurpose.PARTNERSHIP
            if normalized in {"strategic_partnership", "strategic_partner"}:
                return PresentationPurpose.STRATEGIC_PARTNERSHIP
            if normalized in {"project_proposal", "proposal"}:
                return PresentationPurpose.PROJECT_PROPOSAL
    return PresentationPurpose.PITCH_DECK


def _prompt_text_for_analysis(body: GenerationInputV4) -> str:
    if body.standard_input:
        return body.standard_input.prompt
    if body.premium_prompt_input:
        return body.premium_prompt_input.prompt
    if body.premium_structured_input:
        inp = body.premium_structured_input
        return "\n".join(
            part
            for part in [
                f"Presentation Topic: {inp.topic}",
                f"Description: {inp.description}",
                f"Target Audience: {inp.audience}",
                f"Purpose: {inp.purpose.value}",
                f"Slide Count: {inp.slide_count}" if inp.slide_count else "",
            ]
            if part
        )
    return ""


def _is_technical_security_prompt(text: str) -> bool:
    lowered = text.lower()
    technical_hits = (
        "zero-trust",
        "zero trust",
        "decentralized identifier",
        "did",
        "zero-knowledge",
        "zk",
        "hardware-root-of-trust",
        "root of trust",
        "edge computing",
        "iot",
        "consensus algorithm",
        "sub-millisecond",
        "low-bandwidth",
    )
    return sum(1 for token in technical_hits if token in lowered) >= 3


def _infer_audience(text: str, mode: str) -> tuple[str, AudienceSophistication]:
    audience = _extract_labeled_value(text, "Target Audience")
    if not audience:
        audience = "Investors" if mode == "standard" else "Technical buyers and investors"

    lowered = audience.lower() + " " + text.lower()
    if any(token in lowered for token in ("technical vc", "security architect", "architects", "engineer", "developer")):
        sophistication = AudienceSophistication.TECHNICAL
    elif any(token in lowered for token in ("investor", "vc", "venture", "founder")):
        sophistication = AudienceSophistication.INVESTOR
    else:
        sophistication = AudienceSophistication.BUSINESS
    return audience[:300], sophistication


def _infer_industry(text: str) -> str | None:
    lowered = text.lower()
    product_text = re.sub(
        r"target audience\s*:\s*.+?(?=\n[A-Za-z][A-Za-z ]{1,40}\s*:|$)",
        " ",
        lowered,
        flags=re.IGNORECASE | re.DOTALL,
    )
    product_text = re.sub(
        r"\b(?:fintech|vc|venture|investor|underwriter|lloyd'?s)[\w\s-]{0,80}\b(?:audience|investors?|underwriters?)\b",
        " ",
        product_text,
        flags=re.IGNORECASE,
    )

    if any(token in product_text for token in ("post-quantum", "post quantum", "lattice-based", "lattice based", "heritage data", "digital vault", "quantum-y2k", "quantum y2k")):
        return "Post-Quantum Data Archiving"
    if any(token in product_text for token in ("satellite", "orbital", "space exploration", "space-as-a-service", "space as a service", "aerospace")) and any(
        token in product_text for token in ("insurance", "coverage", "underwriting", "payout", "risk assessment", "threat-index", "threat index")
    ):
        return "Space Cyber Insurance"
    if any(token in product_text for token in ("satellite", "orbital", "space exploration", "space-as-a-service", "space as a service", "aerospace")):
        return "Space Technology"
    if any(token in product_text for token in ("cyber-insurance", "cyber insurance", "insurance", "coverage", "underwriting", "policy", "claims", "payout")):
        return "Cyber Insurance"
    if any(token in product_text for token in ("zero-trust", "zero trust", "identity", "security", "zk proof", "zero-knowledge")):
        return "Cybersecurity"
    if any(token in product_text for token in ("iot", "edge computing", "edge device")):
        return "Edge Computing"
    if "health" in product_text or "clinical" in product_text:
        return "HealthTech"
    if "fintech" in product_text or "payments" in product_text or "banking" in product_text:
        return "FinTech"
    return None


def _extract_company_name(text: str) -> str | None:
    explicit = _extract_labeled_value(text, "Company")
    if explicit:
        return explicit.split("(", 1)[0].strip()[:200] or None
    # Do not promote quoted product/algorithm names to company names. This is
    # deliberately conservative so technical concept prompts do not create
    # fake startup identities.
    return None


def _fast_entities_from_prompt(text: str) -> list[ExtractedEntity]:
    candidates: list[tuple[str, str, tuple[str, ...]]] = [
        ("technology", "decentralized identifiers (DIDs)", ("decentralized identifiers", "dids")),
        ("technology", "zero-knowledge proofs", ("zero-knowledge", "zk proofs", "zkp")),
        ("technology", "hardware-root-of-trust", ("hardware-root-of-trust", "root of trust", "secure element", "tpm")),
        ("technology", "Neural-Guardian", ("neural-guardian",)),
        ("technology", "IoT devices", ("iot", "device fleet")),
        ("technology", "edge computing", ("edge computing",)),
        ("metric", "sub-millisecond authentication latency", ("sub-millisecond", "<1 ms", "less than 1 ms")),
        ("metric", "O(1) scalability", ("o(1)", "constant-time", "constant time")),
        ("market", "low-bandwidth environments", ("low-bandwidth", "bandwidth-constrained")),
    ]
    lowered = text.lower()
    entities: list[ExtractedEntity] = []
    for entity_type, value, needles in candidates:
        if any(needle in lowered for needle in needles):
            entities.append(ExtractedEntity(type=entity_type, value=value, confidence=0.95))
    return entities


def _fast_missing_context(text: str, purpose: PresentationPurpose) -> list[MissingContext]:
    if purpose != PresentationPurpose.PITCH_DECK:
        return []

    lowered = text.lower()
    missing: list[MissingContext] = []
    if not any(token in lowered for token in ("arr", "mrr", "revenue", "customer", "traction", "pilot", "deployment")):
        missing.append(MissingContext(
            field="traction_or_financials",
            importance="recommended",
            suggestion="No traction or financial evidence was provided; omit factual traction claims unless the user supplies them.",
        ))
    if not any(token in lowered for token in ("raising", "funding", "ask", "use of funds", "seed", "series a")):
        missing.append(MissingContext(
            field="fundraising_ask",
            importance="optional",
            suggestion="No specific fundraising ask was provided; keep the ask slide as a discussion prompt, not a fabricated amount.",
        ))
    return missing


def _build_fast_generation_analysis(body: GenerationInputV4) -> InputAnalysisResult:
    """Build a submit-time analysis without network calls or provider fallbacks.

    This helper is intentionally conservative: it extracts only facts visible
    in the request payload and never invents company, traction, funding, team,
    or market-size data. The heavier LLM analyzer remains a separate preflight
    endpoint, but generation itself must return a project id quickly.
    """
    if body.premium_structured_input is not None:
        # Structured input is already field-validated and does not call an LLM.
        return InputAnalyzer()._analyze_premium_structured(body.premium_structured_input)

    text = _prompt_text_for_analysis(body)
    purpose = _coerce_purpose(body.effective_purpose)
    if explicit_purpose := _extract_labeled_value(text, "Purpose"):
        purpose = _coerce_purpose(explicit_purpose)
        if "investor" in explicit_purpose.lower():
            purpose = PresentationPurpose.PITCH_DECK

    audience, sophistication = _infer_audience(text, body.mode)
    is_technical = _is_technical_security_prompt(text)
    industry = _infer_industry(text)
    company_name = _extract_company_name(text)
    slide_types = (
        list(_TECHNICAL_CONCEPT_SLIDE_TYPES)
        if purpose == PresentationPurpose.PITCH_DECK and is_technical
        else list(_GENERIC_PITCH_SLIDE_TYPES)
    )

    return InputAnalysisResult(
        detected_purpose=purpose,
        detected_audience=audience,
        audience_sophistication=AudienceSophistication.TECHNICAL if is_technical else sophistication,
        detected_industry=industry,
        detected_company_name=company_name,
        detected_stage=FundingStage.NOT_APPLICABLE,
        entities=_fast_entities_from_prompt(text),
        suggested_narrative_arc="problem_solution",
        suggested_slide_count=body.effective_slide_count or len(slide_types),
        suggested_slide_types=slide_types,
        missing_context=_fast_missing_context(text, purpose),
        input_richness_score=0.85 if is_technical else 0.55,
        confidence=0.9 if is_technical else 0.72,
    )


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


def _extract_generate_images(body: GenerationInputV4) -> bool:
    """Whether to run the image generation stage during the pipeline.

    - Standard mode: hard-coded False on the input model (cheap/fast path),
      but we still consult `generate_images` so a future toggle can flip it
      without a router change.
    - Premium prompt / structured: defaults to True per the input schema;
      respects user opt-out.
    """
    if body.premium_structured_input is not None:
        return bool(body.premium_structured_input.generate_images)
    if body.premium_prompt_input is not None:
        return bool(body.premium_prompt_input.generate_images)
    if body.standard_input is not None:
        return bool(getattr(body.standard_input, "generate_images", False))
    return False


def _extract_theme_id(body: GenerationInputV4) -> str | None:
    if body.standard_input:
        return body.standard_input.theme_id
    if body.premium_structured_input:
        return body.premium_structured_input.theme_id
    if body.premium_prompt_input:
        return body.premium_prompt_input.theme_id
    return None


def _extract_template_id(body: GenerationInputV4) -> str | None:
    """Return the user's selected template id (v2 template engine) if any.

    Standard mode exposes this on the input page (InlineTemplatePicker);
    Premium mode currently exposes it on the dedicated TemplateStep.
    """
    if body.standard_input and body.standard_input.template_id:
        return body.standard_input.template_id
    if body.premium_structured_input and body.premium_structured_input.template_id:
        return body.premium_structured_input.template_id
    if body.premium_prompt_input and body.premium_prompt_input.template_id:
        return body.premium_prompt_input.template_id
    return None


def _extract_visual_direction(body: GenerationInputV4) -> str | None:
    """Return the visual direction ID if one was chosen by the user."""
    if body.standard_input and body.standard_input.visual_direction:
        return body.standard_input.visual_direction
    if body.premium_structured_input and body.premium_structured_input.visual_direction:
        return body.premium_structured_input.visual_direction
    if body.premium_prompt_input and body.premium_prompt_input.visual_direction:
        return body.premium_prompt_input.visual_direction
    return None


def _extract_effects(body: GenerationInputV4) -> dict[str, Any] | None:
    """Return the selected motion/effects contract, if provided."""
    effects = None
    if body.standard_input:
        effects = body.standard_input.effects
    elif body.premium_prompt_input:
        effects = body.premium_prompt_input.effects
    elif body.premium_structured_input:
        effects = body.premium_structured_input.effects
    if effects is None:
        return None
    payload = effects.model_dump(exclude_none=True)
    return payload if payload else None


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


# ═══════════════════════════════════════════════════════════════════
# WEBSOCKET — Purpose Selection & Question-Asking Flow
# ═══════════════════════════════════════════════════════════════════

@router.websocket("/ws/generation/{generation_id}")
async def generation_websocket(
    websocket: WebSocket,
    generation_id: str,
) -> None:
    """WebSocket for real-time purpose selection and question-asking flow.

    Flow:
    1. Accept connection
    2. Receive user prompt
    3. Auto-select purpose
    4. Send detected purpose for confirmation/override
    5. Wait for user to confirm or override purpose
    6. Generate purpose-aware questions (if needed)
    7. Send questions with skip option
    8. Collect answers or skip
    9. Continue with generation
    """
    await websocket.accept()

    session_manager = SessionManager()
    auto_purpose_selector = AutoPurposeSelector()
    question_generator = ConversationalQuestionGenerator()

    try:
        # Receive initial data
        data = await websocket.receive_json()
        user_input = data.get("prompt", "")
        mode = data.get("mode", "standard")
        user_id = data.get("user_id", "dev-test-user")

        if not user_input:
            await websocket.send_json({
                "type": "error",
                "error": "prompt_required",
                "message": "Prompt is required",
            })
            return

        logger.info(
            "websocket_connection_received",
            generation_id=generation_id,
            user_id=user_id,
            mode=mode,
            prompt_length=len(user_input),
        )

        # Initialize session
        await session_manager.save_session(
            user_id=user_id,
            generation_id=generation_id,
            session_data={
                "user_input": user_input,
                "mode": mode,
                "stage": "purpose_selection",
            },
        )

        # Auto-select purpose
        available_purposes = list(PURPOSE_CONFIGS.keys())
        detected_purpose, confidence = await auto_purpose_selector.select_purpose(
            user_input,
            available_purposes,
        )

        # Get purpose config for tooltip
        purpose_config = PURPOSE_CONFIGS.get(detected_purpose)
        purpose_tooltip = None
        if purpose_config:
            from app.services.v4.purpose_configs import PURPOSE_TOOLTIPS
            purpose_tooltip = PURPOSE_TOOLTIPS.get(detected_purpose)

        # Send detected purpose for user confirmation/override
        await websocket.send_json({
            "type": "purpose_detected",
            "purpose": detected_purpose,
            "confidence": round(confidence, 2),
            "all_purposes": available_purposes,
            "purpose_label": purpose_config.website_label if purpose_config else detected_purpose,
            "purpose_tooltip": purpose_tooltip,
        })

        # Wait for user to confirm or override purpose
        purpose_response = await websocket.receive_json()
        response_type = purpose_response.get("type", "")

        if response_type == "purpose_override":
            final_purpose = purpose_response.get("purpose", detected_purpose)
        else:
            final_purpose = detected_purpose

        # Update session with final purpose
        await session_manager.update_session_field(
            user_id=user_id,
            generation_id=generation_id,
            field="purpose",
            value=final_purpose,
        )

        # Generate questions based on final purpose
        question_response = await question_generator.generate_questions(
            user_input=user_input,
            purpose=final_purpose,
            context={},
        )

        # Send questions (optional - user can skip)
        if question_response.should_ask_questions:
            questions_data = [
                {
                    "id": q.id,
                    "question": q.question,
                    "question_type": q.question_type,
                    "required": q.required,
                }
                for q in question_response.questions
            ]

            await websocket.send_json({
                "type": "questions",
                "questions": questions_data,
                "can_skip": True,
                "richness_score": round(question_response.richness_score, 2),
                "reason": question_response.reason,
            })

            # Collect answers or skip
            answers = {}
            if question_response.questions:
                for question in question_response.questions:
                    try:
                        response = await websocket.receive_json()
                        action = response.get("action", "")

                        if action == "skip_all":
                            break
                        elif action == "skip_question":
                            continue
                        elif action == "answer":
                            answers[question.id] = response.get("answer", "")

                    except WebSocketDisconnect:
                        logger.info(
                            "websocket_disconnected_during_questions",
                            generation_id=generation_id,
                            question_id=question.id,
                        )
                        return
        else:
            await websocket.send_json({
                "type": "no_questions_needed",
                "richness_score": round(question_response.richness_score, 2),
                "reason": question_response.reason,
            })

        # Update session with answers
        await session_manager.update_session_field(
            user_id=user_id,
            generation_id=generation_id,
            field="question_answers",
            value=answers,
        )

        # Signal generation start
        await websocket.send_json({
            "type": "generation_start",
            "purpose": final_purpose,
            "purpose_label": PURPOSE_CONFIGS.get(final_purpose).website_label if final_purpose in PURPOSE_CONFIGS else final_purpose,
            "has_answers": len(answers) > 0,
            "questions_answered": len(answers),
        })

        # Update session stage
        await session_manager.update_session_field(
            user_id=user_id,
            generation_id=generation_id,
            field="stage",
            value="ready_for_generation",
        )

        logger.info(
            "websocket_handshake_complete",
            generation_id=generation_id,
            user_id=user_id,
            final_purpose=final_purpose,
            questions_answered=len(answers),
        )

    except WebSocketDisconnect:
        logger.info(
            "websocket_disconnected",
            generation_id=generation_id,
        )
    except Exception as e:
        logger.error(
            "websocket_error",
            generation_id=generation_id,
            error=str(e)[:200],
            exc_info=True,
        )
        try:
            await websocket.send_json({
                "type": "error",
                "error": "internal_error",
                "message": str(e)[:200],
            })
        except Exception:
            pass
    finally:
        # Clean up session if needed
        try:
            await session_manager.delete_session(
                user_id=user_id if 'user_id' in locals() else "unknown",
                generation_id=generation_id,
            )
        except Exception:
            pass
