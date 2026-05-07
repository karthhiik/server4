"""V4 regeneration engine.

Single-slide, batch/range, and full-deck regeneration all go through this
module. The invariant is simple: when a writer pass changes source slide data,
we recompile the ordered deck and persist `presentations.compiled_slides` in the
same operation, so the sandbox refresh path never serves stale artifacts.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.llm.model_router import TaskType, get_model_router
from app.services.v4.design_resolver import resolve_design_tokens
from app.services.v4.design_system import (
    attach_design_system_to_html_artifact,
    attach_version_to_compiled_slides,
    build_design_system,
)
from app.services.v4.parallel_writer import GeneratedSlide, ParallelWriter
from app.services.v4.json_repair import JSONRepairFailedError, safe_json_loads
from app.services.v4.quality_scorer import attach_quality_scores
from app.services.v4.research_collector import Citation, ResearchPacket
from app.services.v4.skeleton_planner import DeckSkeleton, SlideSkeleton
from app.services.v4.slide_compiler import compile_slides

logger = structlog.get_logger(__name__)

MAX_BATCH_REGEN_SLIDES = 12
MAX_REGEN_CONCURRENCY = 4
_REGEN_LOCK_TTL_SECONDS = 180

_MODEL_FORCED_LOCK = asyncio.Lock()
_PROCESS_LOCKS_GUARD = asyncio.Lock()
_PROCESS_LOCKS: dict[str, asyncio.Lock] = {}


class RegenerationValidationError(ValueError):
    """Raised when a regeneration request is malformed."""


class RegenerationBusy(RuntimeError):
    """Raised when another regeneration is already running for the deck."""


@dataclass
class RegenerationRequest:
    slide_indices: list[int]
    instruction: Optional[str] = None
    per_slide_instructions: dict[int, str] = field(default_factory=dict)
    target_model: Optional[str] = None
    preserve_images: bool = True
    concurrency: int = 2
    change_type: str = "regenerate-batch"
    update_deck_regenerated_at: bool = False


@dataclass
class RegeneratedSlideOutcome:
    index: int
    ok: bool
    slide_doc: Optional[dict[str, Any]] = None
    slide_id: Optional[str] = None
    artifact_version: Optional[int] = None
    error: Optional[str] = None

    def to_public(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "ok": self.ok,
            "slide_id": self.slide_id,
            "artifact_version": self.artifact_version,
            "error": self.error,
        }


@dataclass
class RegenerationResult:
    ok: bool
    outcomes: list[RegeneratedSlideOutcome]
    refreshed_docs: list[dict[str, Any]]
    compiled_slides: list[dict[str, Any]]
    design_tokens: dict[str, Any]
    design_system: Optional[dict[str, Any]]

    @property
    def succeeded_indices(self) -> list[int]:
        return [outcome.index for outcome in self.outcomes if outcome.ok]

    @property
    def failed_indices(self) -> list[int]:
        return [outcome.index for outcome in self.outcomes if not outcome.ok]


@dataclass
class ElementRegenerationResult:
    ok: bool
    path: str
    value: Any = None
    task_type: Optional[str] = None
    reason: Optional[str] = None
    changed: bool = False


@dataclass
class _ProjectLock:
    key: str
    token: str
    redis: Any = None
    local_lock: Optional[asyncio.Lock] = None

    async def release(self) -> None:
        if self.redis is not None:
            script = (
                "if redis.call('get', KEYS[1]) == ARGV[1] then "
                "return redis.call('del', KEYS[1]) else return 0 end"
            )
            try:
                await self.redis.eval(script, 1, self.key, self.token)
            except Exception as exc:  # noqa: BLE001
                logger.warning("v4_regen.redis_lock_release_failed", key=self.key, error=str(exc)[:200])
            return
        if self.local_lock is not None and self.local_lock.locked():
            self.local_lock.release()


async def _local_lock_for(key: str) -> asyncio.Lock:
    async with _PROCESS_LOCKS_GUARD:
        lock = _PROCESS_LOCKS.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _PROCESS_LOCKS[key] = lock
        return lock


async def _acquire_project_lock(project_id: str) -> _ProjectLock:
    key = f"v4:regen_lock:{project_id}"
    token = uuid.uuid4().hex
    try:
        from app.utils.rate_limiter import get_redis

        redis = await get_redis()
        acquired = await redis.set(key, token, nx=True, ex=_REGEN_LOCK_TTL_SECONDS)
        if acquired:
            return _ProjectLock(key=key, token=token, redis=redis)
        raise RegenerationBusy("another regeneration is already running for this project")
    except RegenerationBusy:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("v4_regen.redis_lock_unavailable", project_id=project_id, error=str(exc)[:200])

    local_lock = await _local_lock_for(key)
    if local_lock.locked():
        raise RegenerationBusy("another regeneration is already running for this project")
    await local_lock.acquire()
    return _ProjectLock(key=key, token=token, local_lock=local_lock)


def normalize_slide_indices(
    indices: list[int],
    *,
    max_count: int = MAX_BATCH_REGEN_SLIDES,
) -> list[int]:
    if not indices:
        raise RegenerationValidationError("slide_indices must include at least one slide")
    normalized: list[int] = []
    seen: set[int] = set()
    for raw in indices:
        try:
            idx = int(raw)
        except (TypeError, ValueError) as exc:
            raise RegenerationValidationError("slide_indices must contain integers") from exc
        if idx < 0:
            raise RegenerationValidationError("slide_indices cannot include negative values")
        if idx in seen:
            continue
        seen.add(idx)
        normalized.append(idx)
    if len(normalized) > max_count:
        raise RegenerationValidationError(f"cannot regenerate more than {max_count} slides at once")
    return normalized


def _clamp_text(value: Optional[str], *, limit: int) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text[:limit] if text else None


def _normalize_per_slide_instructions(raw: dict[Any, Any] | None) -> dict[int, str]:
    out: dict[int, str] = {}
    for key, value in (raw or {}).items():
        try:
            idx = int(key)
        except (TypeError, ValueError) as exc:
            raise RegenerationValidationError("per_slide_instructions keys must be slide indices") from exc
        if idx < 0:
            raise RegenerationValidationError("per_slide_instructions cannot include negative indices")
        text = _clamp_text(str(value), limit=600)
        if text:
            out[idx] = text
    return out


def rebuild_skeleton(project: dict[str, Any], slide_docs: list[dict[str, Any]]) -> Optional[DeckSkeleton]:
    snapshot = project.get("v4_skeleton")
    if isinstance(snapshot, dict) and isinstance(snapshot.get("slides"), list):
        slides: list[SlideSkeleton] = []
        for position, raw in enumerate(snapshot["slides"]):
            if not isinstance(raw, dict):
                continue
            slides.append(
                SlideSkeleton(
                    index=int(raw.get("index", position)),
                    intent=str(raw.get("intent") or ""),
                    purpose=str(raw.get("purpose") or raw.get("rationale") or ""),
                    headline_target=str(raw.get("headline_target") or ""),
                    key_points=[str(point) for point in (raw.get("key_points") or [])][:8],
                    density_target=str(raw.get("density_target") or "medium"),
                    layout_hint=str(raw.get("layout_hint") or "auto"),
                    evidence_refs=[str(ref) for ref in (raw.get("evidence_refs") or [])][:12],
                    visual_cue=str(raw.get("visual_cue") or ""),
                    thesis_sentence=str(raw.get("thesis_sentence") or raw.get("rationale") or "")[:280],
                    generic_risk=str(raw.get("generic_risk") or "low"),
                    required_quant_signals=[
                        str(signal)[:80] for signal in (raw.get("required_quant_signals") or [])
                    ][:8],
                    trace_inputs=[str(item)[:120] for item in (raw.get("trace_inputs") or [])][:12],
                )
            )
        return DeckSkeleton(
            project_id=str(project.get("_id", "")),
            title=str(snapshot.get("title") or project.get("title") or ""),
            narrative_arc=str(snapshot.get("narrative_arc") or project.get("narrative_arc") or ""),
            slides=slides,
            raw_planner_output={},
        )

    if not slide_docs:
        return None
    return DeckSkeleton(
        project_id=str(project.get("_id", "")),
        title=str(project.get("title") or ""),
        narrative_arc=str(project.get("narrative_arc") or ""),
        slides=[
            SlideSkeleton(
                index=int(doc.get("index", position)),
                intent=str(doc.get("intent") or ""),
                purpose=str(doc.get("rationale") or doc.get("purpose") or ""),
                headline_target=str(doc.get("headline") or ""),
                key_points=[str(point) for point in (doc.get("bullets") or [])][:5],
                density_target="medium",
                layout_hint=str(doc.get("layout") or "auto"),
                evidence_refs=[
                    str(citation.get("url"))
                    for citation in (doc.get("citations") or [])
                    if isinstance(citation, dict) and citation.get("url")
                ][:12],
                visual_cue="",
                thesis_sentence=str(doc.get("subheadline") or doc.get("headline") or "")[:280],
                generic_risk="low",
                required_quant_signals=[],
                trace_inputs=[],
            )
            for position, doc in enumerate(slide_docs)
        ],
        raw_planner_output={},
    )


def rebuild_research(project: dict[str, Any]) -> ResearchPacket:
    snapshot = project.get("v4_research_snapshot") or {}

    def cite(raw: dict[str, Any]) -> Citation:
        return Citation(
            title=str(raw.get("title") or "")[:240],
            url=str(raw.get("url") or ""),
            snippet=str(raw.get("snippet") or "")[:600],
            source=str(raw.get("source") or "snapshot"),
            source_authority=float(raw.get("source_authority", 0.5) or 0.5),
            published_at=raw.get("published_at"),
        )

    return ResearchPacket(
        query=str(snapshot.get("query") or project.get("title") or ""),
        industry=snapshot.get("industry") or project.get("industry"),
        company_name=snapshot.get("company_name") or project.get("company_name"),
        citations=[cite(citation) for citation in (snapshot.get("citations") or []) if isinstance(citation, dict)],
        news_citations=[
            cite(citation) for citation in (snapshot.get("news_citations") or []) if isinstance(citation, dict)
        ],
        financial_data=dict(snapshot.get("financial_data") or {}),
        social_signals=dict(snapshot.get("social_signals") or {}),
        duration_ms=0,
        cache_hit=True,
    )


def augment_skeleton_with_instruction(
    skeleton: SlideSkeleton,
    instruction: Optional[str],
) -> SlideSkeleton:
    extra = _clamp_text(instruction, limit=600)
    if not extra:
        return skeleton
    purpose = (skeleton.purpose or "").strip()
    purpose = f"{purpose}\n\nUSER REVISION REQUEST: {extra}".strip()
    return SlideSkeleton(
        index=skeleton.index,
        intent=skeleton.intent,
        purpose=purpose,
        headline_target=skeleton.headline_target,
        key_points=list(skeleton.key_points),
        density_target=skeleton.density_target,
        layout_hint=skeleton.layout_hint,
        evidence_refs=list(skeleton.evidence_refs),
        visual_cue=skeleton.visual_cue,
        thesis_sentence=skeleton.thesis_sentence,
        generic_risk=skeleton.generic_risk,
        required_quant_signals=list(skeleton.required_quant_signals),
        trace_inputs=list(skeleton.trace_inputs),
    )


def _slide_doc_to_generated(doc: dict[str, Any]) -> GeneratedSlide:
    return GeneratedSlide(
        index=int(doc.get("index", 0)),
        intent=str(doc.get("intent") or ""),
        layout=str(doc.get("layout") or "auto"),
        headline=str(doc.get("headline") or ""),
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


def _ensure_design_tokens(project: dict[str, Any]) -> dict[str, Any]:
    tokens = project.get("design_tokens")
    if isinstance(tokens, dict) and tokens.get("palette") and tokens.get("fonts"):
        return tokens
    return resolve_design_tokens(
        design_profile=project.get("design_profile") if isinstance(project.get("design_profile"), dict) else None,
        purpose=project.get("purpose") or None,
        industry=project.get("industry") or None,
    ).to_dict()


def _compile_ordered_deck(
    *,
    slide_docs: list[dict[str, Any]],
    project: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], Optional[dict[str, Any]]]:
    ordered_docs = sorted(slide_docs, key=lambda doc: int(doc.get("index", 0)))
    generated = [_slide_doc_to_generated(doc) for doc in ordered_docs]
    image_urls = {slide.index: slide.image_url for slide in generated if slide.image_url}
    compiled = compile_slides(
        slides=generated,
        image_urls=image_urls,
        deck_title=project.get("title") or None,
        company_icon_url=project.get("company_icon_url") or None,
    )
    design_tokens = _ensure_design_tokens(project)
    design_system: Optional[dict[str, Any]] = None
    try:
        design_system = build_design_system(design_tokens, deck_title=project.get("title") or None)
        attach_version_to_compiled_slides(compiled, design_system["version"])
        attach_design_system_to_html_artifact(compiled, design_system)
    except Exception as exc:  # noqa: BLE001
        logger.warning("v4_regen.design_system_failed", error=str(exc)[:200])
    attach_quality_scores(compiled, design_tokens)
    return compiled, design_tokens, design_system


def _source_model_for(new_slide: GeneratedSlide, target_model: Optional[str]) -> Optional[str]:
    if target_model:
        return target_model
    raw = new_slide.raw if isinstance(new_slide.raw, dict) else {}
    source_model = raw.get("source_model") or raw.get("model")
    return str(source_model) if source_model else None


def _build_slide_update_doc(
    new_slide: GeneratedSlide,
    prior: dict[str, Any],
    *,
    target_model: Optional[str],
    preserve_images: bool,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    team_members = list(new_slide.team_members or prior.get("team_members") or [])
    requires_input = bool(
        new_slide.requires_user_input
        or (prior.get("requires_user_input") and not team_members)
    )
    update_doc: dict[str, Any] = {
        "intent": new_slide.intent,
        "layout": new_slide.layout,
        "headline": new_slide.headline,
        "subheadline": new_slide.subheadline,
        "bullets": list(new_slide.bullets or []),
        "body": new_slide.body,
        "stat_blocks": list(new_slide.stat_blocks or []),
        "quote": new_slide.quote,
        "chart": new_slide.chart,
        "table": new_slide.table,
        "timeline": new_slide.timeline,
        "comparison": new_slide.comparison,
        "diagram": new_slide.diagram,
        "image_prompt": new_slide.image_prompt,
        "speaker_notes": new_slide.speaker_notes,
        "citations": list(new_slide.citations or []),
        "render_decision": new_slide.render_decision,
        "team_members": team_members,
        "requires_user_input": requires_input,
        "user_input_kind": (new_slide.user_input_kind or prior.get("user_input_kind")) if requires_input else None,
        "user_input_reason": (new_slide.user_input_reason or prior.get("user_input_reason")) if requires_input else None,
        "company_icon_url": new_slide.company_icon_url or prior.get("company_icon_url"),
        "rationale": new_slide.rationale or prior.get("rationale", ""),
        "purpose": new_slide.purpose or prior.get("purpose", ""),
        "raw": dict(new_slide.raw or {}),
        "source_model": _source_model_for(new_slide, target_model),
        "version": int(prior.get("version", 1)) + 1,
        "updated_at": now,
        "regenerated_at": now,
    }
    if preserve_images:
        for field_name in ("image_url", "image_source", "image_position", "image_intent"):
            value = getattr(new_slide, field_name, None) or prior.get(field_name)
            if value:
                update_doc[field_name] = value
    else:
        update_doc.update({
            "image_url": None,
            "image_source": None,
            "image_position": None,
            "image_intent": None,
        })
    return update_doc


async def _snapshot_slide(db: AsyncIOMotorDatabase, slide: dict[str, Any], change_type: str) -> None:
    try:
        await db.slide_versions.insert_one({
            "_id": str(ObjectId()),
            "slide_id": str(slide["_id"]),
            "project_id": slide["project_id"],
            "index": slide.get("index"),
            "version": int(slide.get("version", 1)),
            "snapshot": {
                key: slide.get(key)
                for key in (
                    "headline", "subheadline", "bullets", "body", "stat_blocks",
                    "quote", "chart", "table", "timeline", "comparison", "diagram",
                    "image_prompt", "image_url", "image_source", "image_position",
                    "image_intent", "speaker_notes", "citations", "layout",
                    "team_members", "requires_user_input", "user_input_kind",
                    "user_input_reason", "company_icon_url", "rationale", "purpose",
                )
            },
            "change_type": change_type,
            "created_at": datetime.now(timezone.utc),
        })
    except Exception as exc:  # noqa: BLE001
        logger.warning("v4_regen.snapshot_failed", error=str(exc)[:200])


async def _write_with_optional_forced_model(
    *,
    writer: ParallelWriter,
    skeleton: SlideSkeleton,
    research: ResearchPacket,
    mode: str,
    project_id: str,
    purpose: str,
    design_tokens: dict[str, Any],
    structured_context: dict[str, Any],
    target_model: Optional[str],
) -> GeneratedSlide:
    if not target_model:
        return await writer.write_one(
            skeleton,
            research,
            mode,
            project_id,
            purpose=purpose,
            design_tokens=design_tokens,
            structured_context=structured_context,
        )

    async with _MODEL_FORCED_LOCK:
        router = get_model_router()
        prior_forced = router.forced_model
        router.set_forced_model(target_model)
        try:
            return await writer.write_one(
                skeleton,
                research,
                mode,
                project_id,
                purpose=purpose,
                design_tokens=design_tokens,
                structured_context=structured_context,
            )
        finally:
            router.set_forced_model(prior_forced)


async def _validate_target_model(target_model: Optional[str]) -> None:
    if not target_model:
        return
    async with _MODEL_FORCED_LOCK:
        router = get_model_router()
        prior_forced = router.forced_model
        try:
            router.set_forced_model(target_model)
        except ValueError as exc:
            raise RegenerationValidationError(str(exc)) from exc
        finally:
            router.set_forced_model(prior_forced)


async def _emit_updates(
    *,
    project_id: str,
    outcomes: list[RegeneratedSlideOutcome],
    trigger: str,
) -> None:
    try:
        from app.services.v4.content_pipeline import make_redis_progress_emitter

        emit = make_redis_progress_emitter(project_id)
        for outcome in outcomes:
            if not outcome.ok:
                continue
            await emit("slide_updated", {
                "slide_id": outcome.slide_id,
                "slide_index": outcome.index,
                "artifact_version": outcome.artifact_version,
                "fields_changed": ["generated_slide", "compiled_artifact"],
                "trigger": trigger,
            })
        await emit("slide_regeneration_complete", {
            "trigger": trigger,
            "succeeded_indices": [outcome.index for outcome in outcomes if outcome.ok],
            "failed_indices": [outcome.index for outcome in outcomes if not outcome.ok],
        })
    except Exception as exc:  # noqa: BLE001
        logger.warning("v4_regen.emit_failed", project_id=project_id, error=str(exc)[:200])


def _compact_json(value: Any, *, limit: int = 1800) -> str:
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        raw = json.dumps(str(value), ensure_ascii=False)
    return raw[:limit]


def _resolve_compiled_prop(root: Any, path: str) -> Any:
    if not isinstance(path, str) or not path.strip():
        raise RegenerationValidationError("path is required")
    cursor = root
    for part in path.split("."):
        if part == "":
            raise RegenerationValidationError("path contains an empty segment")
        if isinstance(cursor, list):
            try:
                idx = int(part)
            except ValueError as exc:
                raise RegenerationValidationError(f"path segment {part!r} expects a list index") from exc
            if idx < 0 or idx >= len(cursor):
                raise RegenerationValidationError(f"path index {idx} is out of range")
            cursor = cursor[idx]
        elif isinstance(cursor, dict):
            if part not in cursor:
                raise RegenerationValidationError(f"path {path!r} does not exist")
            cursor = cursor[part]
        else:
            raise RegenerationValidationError(f"path {path!r} cannot be resolved")
    return cursor


def _element_value_bucket(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    if value is None:
        return "null"
    return type(value).__name__


def _shape_compatible(reference: Any, candidate: Any) -> bool:
    ref_bucket = _element_value_bucket(reference)
    next_bucket = _element_value_bucket(candidate)
    if ref_bucket != next_bucket:
        if {ref_bucket, next_bucket} == {"string", "null"}:
            return True
        return False
    if isinstance(reference, dict):
        if not isinstance(candidate, dict):
            return False
        if set(candidate.keys()) != set(reference.keys()):
            return False
        return all(_shape_compatible(reference[key], candidate[key]) for key in reference.keys())
    if isinstance(reference, list):
        if not isinstance(candidate, list) or len(candidate) != len(reference):
            return False
        return all(_shape_compatible(a, b) for a, b in zip(reference, candidate))
    return True


def _is_asset_path(path: str) -> bool:
    leaf = path.split(".")[-1]
    return leaf in {"imageUrl", "logoUrl", "photoUrl", "image_url", "logo_url", "photo_url"}


def _is_fact_sensitive(path: str, kind: Optional[str], value: Any) -> bool:
    lowered = path.lower()
    if kind in {"number", "stat", "chart-series", "chart-datum"}:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return True
    return any(token in lowered for token in ("stat", "value", "data", "source", "citation", "revenue", "tam", "cagr"))


def _select_element_task(*, project_mode: str, path: str, kind: Optional[str], value: Any, instruction: Optional[str]) -> TaskType:
    text = (instruction or "").lower()
    premium_rewrite = (
        project_mode == "premium"
        and any(token in text for token in ("investor", "stronger", "premium", "sharpen", "rewrite"))
    )
    if premium_rewrite:
        return TaskType.PREMIUM_TARGETED_REWRITE
    if _is_fact_sensitive(path, kind, value):
        return TaskType.CITATION_GUARD
    if isinstance(value, (dict, list)):
        return TaskType.TEMPLATE_FILL
    return TaskType.STYLE_ADAPTATION


async def regenerate_one_field(
    *,
    project_id: str,
    project: dict[str, Any],
    slide_doc: dict[str, Any],
    compiled_props: dict[str, Any],
    path: str,
    instruction: Optional[str] = None,
    kind: Optional[str] = None,
) -> ElementRegenerationResult:
    """Regenerate exactly one compiled props path, without persisting.

    The caller owns optimistic locking and artifact persistence. This helper
    only uses cached deck context plus the real model router to produce a value
    compatible with the current path. It never creates image URLs or verified
    facts; unsupported requests come back as an explicit refusal.
    """
    current_value = _resolve_compiled_prop(compiled_props, path)
    if _is_asset_path(path):
        return ElementRegenerationResult(
            ok=False,
            path=path,
            reason="image elements require the approved image swap or image-generation pipeline, not text regeneration",
        )

    docs = [slide_doc]
    skeleton = rebuild_skeleton(project, docs)
    skel_slide: Optional[SlideSkeleton] = None
    if skeleton:
        slide_index = int(slide_doc.get("index", 0))
        skel_slide = next((slide for slide in skeleton.slides if int(slide.index) == slide_index), None)
    research = rebuild_research(project)
    design_tokens = _ensure_design_tokens(project)
    project_mode = str(project.get("v4_mode") or project.get("mode") or "standard")
    task_type = _select_element_task(
        project_mode=project_mode,
        path=path,
        kind=kind,
        value=current_value,
        instruction=instruction,
    )
    router = get_model_router()
    value_bucket = _element_value_bucket(current_value)
    system = (
        "You regenerate exactly one selected element in an investor-grade presentation. "
        "Use only the provided slide, deck, and research context. Never invent numbers, customers, team members, credentials, URLs, citations, or market claims. "
        "For factual or numeric elements, preserve existing verified numbers unless the provided research context directly supports a change. "
        "Return strict JSON only: {\"ok\": true, \"value\": <new value>, \"notes\": \"short\"} or {\"ok\": false, \"reason\": \"short refusal\"}."
    )
    user_msg = (
        f"Deck title: {project.get('title') or ''}\n"
        f"Company: {project.get('company_name') or research.company_name or 'unknown'}\n"
        f"Purpose: {project.get('purpose') or ''}\n"
        f"Slide index: {slide_doc.get('index')}\n"
        f"Slide intent/layout: {slide_doc.get('intent') or ''} / {slide_doc.get('layout') or ''}\n"
        f"Slide headline: {slide_doc.get('headline') or ''}\n"
        f"Skeleton target: {(skel_slide.headline_target if skel_slide else '') or ''}\n"
        f"Skeleton purpose: {(skel_slide.purpose if skel_slide else '') or ''}\n"
        f"Selected path: {path}\n"
        f"Selected element kind: {kind or 'unknown'}\n"
        f"Current value type: {value_bucket}\n"
        f"Current value JSON:\n{_compact_json(current_value, limit=1600)}\n\n"
        f"Full compiled props context (do not rewrite other paths):\n{_compact_json(compiled_props, limit=2400)}\n\n"
        f"Research context:\n{research.as_prompt_context(max_chars=1800) or '(no external research snapshot available)'}\n\n"
        f"User instruction: {(instruction or 'Improve this selected element for clarity and investor-grade specificity while preserving truthfulness.')[:600]}\n\n"
        "Constraints: return a value with the same JSON type and shape as the current value. For objects, keep exactly the same keys. For arrays, keep exactly the same length. Do not include markdown."
    )
    try:
        response = await router.complete(
            task_type,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.35,
            max_tokens=900,
            response_format={"type": "json_object"},
            presentation_id=project_id,
            phase=f"v4_element_regen_{slide_doc.get('index', 0)}",
            mode=project_mode,
        )
        data = safe_json_loads(response.content, context=f"element_regen:{project_id}:{path}")
    except JSONRepairFailedError as exc:
        raise RegenerationValidationError("element regeneration returned malformed JSON") from exc

    if not isinstance(data, dict):
        raise RegenerationValidationError("element regeneration returned a non-object response")
    if data.get("ok") is False:
        return ElementRegenerationResult(
            ok=False,
            path=path,
            task_type=task_type.value,
            reason=str(data.get("reason") or "element regeneration was refused")[:500],
        )
    if "value" not in data:
        raise RegenerationValidationError("element regeneration response omitted value")
    next_value = data.get("value")
    if not _shape_compatible(current_value, next_value):
        raise RegenerationValidationError("element regeneration changed the selected value shape")
    return ElementRegenerationResult(
        ok=True,
        path=path,
        value=next_value,
        task_type=task_type.value,
        changed=next_value != current_value,
    )


async def regenerate_slides(
    *,
    db: AsyncIOMotorDatabase,
    project_id: str,
    project: dict[str, Any],
    request: RegenerationRequest,
) -> RegenerationResult:
    indices = normalize_slide_indices(request.slide_indices)
    per_slide_instructions = _normalize_per_slide_instructions(request.per_slide_instructions)
    target_model = _clamp_text(request.target_model, limit=120)
    await _validate_target_model(target_model)

    project_lock = await _acquire_project_lock(project_id)
    try:
        docs = await db.slides.find({"project_id": project_id}).sort("index", 1).to_list(length=300)
        if not docs:
            raise RegenerationValidationError("project has no slides to regenerate")

        docs_by_index = {int(doc.get("index", -1)): doc for doc in docs}
        missing = [idx for idx in indices if idx not in docs_by_index]
        if missing:
            raise RegenerationValidationError(f"slides not found: {missing}")

        skeleton = rebuild_skeleton(project, docs)
        if not skeleton:
            raise RegenerationValidationError("cannot rebuild generation skeleton")
        skeleton_by_index = {int(slide.index): slide for slide in skeleton.slides}
        missing_skeleton = [idx for idx in indices if idx not in skeleton_by_index]
        if missing_skeleton:
            raise RegenerationValidationError(f"slides missing from skeleton: {missing_skeleton}")

        research = rebuild_research(project)
        design_tokens = _ensure_design_tokens(project)
        structured_context = project.get("structured_context") if isinstance(project.get("structured_context"), dict) else {}
        mode = project.get("v4_mode") or project.get("mode") or "standard"
        purpose = project.get("purpose") or ""
        writer = ParallelWriter()
        concurrency = max(1, min(int(request.concurrency or 1), MAX_REGEN_CONCURRENCY))
        if target_model:
            concurrency = 1
        semaphore = asyncio.Semaphore(concurrency)

        async def write_target(idx: int) -> GeneratedSlide:
            instruction = per_slide_instructions.get(idx) or request.instruction
            target_skeleton = augment_skeleton_with_instruction(skeleton_by_index[idx], instruction)
            async with semaphore:
                return await _write_with_optional_forced_model(
                    writer=writer,
                    skeleton=target_skeleton,
                    research=research,
                    mode=mode,
                    project_id=project_id,
                    purpose=purpose,
                    design_tokens=design_tokens,
                    structured_context=structured_context,
                    target_model=target_model,
                )

        raw_results = await asyncio.gather(
            *(write_target(idx) for idx in indices),
            return_exceptions=True,
        )

        outcomes: list[RegeneratedSlideOutcome] = []
        generated_by_index: dict[int, GeneratedSlide] = {}
        for idx, raw in zip(indices, raw_results):
            if isinstance(raw, Exception):
                outcomes.append(RegeneratedSlideOutcome(index=idx, ok=False, error=str(raw)[:500]))
                continue
            generated_by_index[idx] = raw
            outcomes.append(RegeneratedSlideOutcome(index=idx, ok=True))

        if not generated_by_index:
            return RegenerationResult(
                ok=False,
                outcomes=outcomes,
                refreshed_docs=docs,
                compiled_slides=list(project.get("compiled_slides") or []),
                design_tokens=design_tokens,
                design_system=project.get("design_system") if isinstance(project.get("design_system"), dict) else None,
            )

        next_docs_by_index = {int(doc.get("index", -1)): dict(doc) for doc in docs}
        update_docs_by_index: dict[int, dict[str, Any]] = {}
        for idx, new_slide in generated_by_index.items():
            prior = docs_by_index[idx]
            update_doc = _build_slide_update_doc(
                new_slide,
                prior,
                target_model=target_model,
                preserve_images=request.preserve_images,
            )
            update_docs_by_index[idx] = update_doc
            next_doc = dict(prior)
            next_doc.update(update_doc)
            next_docs_by_index[idx] = next_doc

        next_docs = [next_docs_by_index[int(doc.get("index", -1))] for doc in docs]
        compiled_slides, resolved_tokens, design_system = _compile_ordered_deck(
            slide_docs=next_docs,
            project={**project, "design_tokens": design_tokens},
        )
        compiled_by_index = {
            int(compiled.get("slide_index", -1)): compiled
            for compiled in compiled_slides
            if isinstance(compiled, dict)
        }

        for idx, update_doc in update_docs_by_index.items():
            await _snapshot_slide(db, docs_by_index[idx], request.change_type)
            await db.slides.update_one({"_id": docs_by_index[idx]["_id"]}, {"$set": update_doc})

        presentation_set: dict[str, Any] = {
            "compiled_slides": compiled_slides,
            "design_tokens": resolved_tokens,
            "updated_at": datetime.now(timezone.utc),
            "last_slide_regenerated_at": datetime.now(timezone.utc),
        }
        if design_system:
            presentation_set["design_system"] = design_system
        if request.update_deck_regenerated_at:
            presentation_set["deck_regenerated_at"] = datetime.now(timezone.utc)
        await db.presentations.update_one({"_id": project_id}, {"$set": presentation_set})

        for outcome in outcomes:
            if not outcome.ok:
                continue
            outcome.slide_doc = next_docs_by_index.get(outcome.index)
            compiled = compiled_by_index.get(outcome.index) or {}
            outcome.slide_id = compiled.get("slide_id")
            artifact_version = compiled.get("artifact_version")
            outcome.artifact_version = int(artifact_version) if isinstance(artifact_version, int) else None

        await _emit_updates(project_id=project_id, outcomes=outcomes, trigger=request.change_type)

        logger.info(
            "v4_regen.completed",
            project_id=project_id,
            trigger=request.change_type,
            succeeded=[outcome.index for outcome in outcomes if outcome.ok],
            failed=[outcome.index for outcome in outcomes if not outcome.ok],
        )
        return RegenerationResult(
            ok=all(outcome.ok for outcome in outcomes),
            outcomes=outcomes,
            refreshed_docs=next_docs,
            compiled_slides=compiled_slides,
            design_tokens=resolved_tokens,
            design_system=design_system,
        )
    finally:
        await project_lock.release()