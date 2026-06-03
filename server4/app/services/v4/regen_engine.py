"""V4 regeneration engine.

Single-slide, batch/range, and full-deck regeneration all go through this
module. The invariant is simple: when a writer pass changes source slide data,
we recompile the ordered deck and persist `presentations.compiled_slides` in the
same operation, so the sandbox refresh path never serves stale artifacts.
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.llm.model_router import TaskType, get_model_router
from app.services.v4.design_resolver import resolve_design_tokens
from app.services.v4.design_memory import DesignMemory, apply_design_memory
from app.services.v4.design_system import (
    attach_design_system_to_html_artifact,
    attach_version_to_compiled_slides,
    build_design_system,
)
from app.services.v4.parallel_writer import GeneratedSlide, ParallelWriter
from app.services.v4.executive_polish_engine import polish_generated_slides
from app.services.v4.json_repair import JSONRepairFailedError, safe_json_loads
from app.services.v4.quality_scorer import attach_quality_scores
from app.services.v4.research_collector import Citation, ResearchPacket
from app.services.v4.slide_repair import repair_slide
from app.services.v4.skeleton_planner import DeckSkeleton, SlideSkeleton
from app.services.v4.slide_compiler import compile_slides

logger = structlog.get_logger(__name__)

MAX_BATCH_REGEN_SLIDES = 12
MAX_REGEN_CONCURRENCY = 4
_REGEN_LOCK_TTL_SECONDS = 180

_MODEL_FORCED_LOCK = asyncio.Lock()
_PROCESS_LOCKS_GUARD = asyncio.Lock()
_PROCESS_LOCKS: dict[str, asyncio.Lock] = {}

_TECHNICAL_TERM_PATTERNS = (
    re.compile(r"\bO\(\d+\)\b(?:\s+[A-Za-z][A-Za-z0-9-]+)?"),
    re.compile(r"\bIoT(?:\s+devices?)?\b"),
    re.compile(r"\bzero-knowledge\s+proofs?\b", re.IGNORECASE),
    re.compile(r"\bdecentralized\s+identifiers\s+\([A-Za-z0-9-]{2,}\)\b", re.IGNORECASE),
    re.compile(r"\bsub-millisecond\s+authentication\s+latency\b", re.IGNORECASE),
    re.compile(r"\blow-bandwidth\s+environments?\b", re.IGNORECASE),
    re.compile(r"\bhardware-root-of-trust(?:\s+integration)?\b", re.IGNORECASE),
    re.compile(r"\bself-healing(?:\s+security\s+layer|\s+policies)?\b", re.IGNORECASE),
    re.compile(r"\bNeural-Guardian(?:\s+consensus\s+algorithm)?\b"),
    re.compile(r"\b[A-Z]{2,}[A-Za-z0-9]*s?\b"),
    re.compile(r"\b[A-Za-z][A-Za-z0-9-]*(?:-[A-Za-z0-9]+)+\b"),
    re.compile(r"\b[A-Za-z][A-Za-z0-9-]+(?:\s+[A-Za-z][A-Za-z0-9-]+){0,3}\s+\([A-Za-z0-9-]{2,}\)"),
)
_TECHNICAL_TERM_STOPWORDS = {
    "api",
    "apis",
    "ceo",
    "cto",
    "vc",
    "vcs",
}
_ALLOWED_HYPHENATED_PHRASE_PREFIXES = (
    "zero-knowledge proof",
    "sub-millisecond authentication latency",
    "low-bandwidth environment",
    "hardware-root-of-trust integration",
    "self-healing security layer",
    "self-healing polic",
    "neural-guardian consensus algorithm",
)
_PROJECT_TERM_KEYS = (
    "prompt",
    "description",
    "title",
    "topic",
    "user_query",
    "original_prompt",
    "query",
)
_SLIDE_VISIBLE_FIELDS = (
    "headline",
    "subheadline",
    "body",
    "bullets",
    "stat_blocks",
    "quote",
    "chart",
    "table",
    "timeline",
    "comparison",
    "diagram",
)


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
    # When True, the regenerator merges new content into the prior slide
    # so user-edited text fields (headline / body / bullets / etc.) are
    # not silently overwritten by the LLM. Default True is the right
    # behavior for a real-time editor; callers that genuinely want a
    # full overwrite (e.g. deck-wide narrative re-pass) opt out by
    # passing False.
    preserve_user_edits: bool = True


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


def _collect_text(value: Any, *, max_depth: int = 4) -> list[str]:
    if max_depth < 0 or value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, (int, float, bool)):
        return [str(value)]
    if isinstance(value, list):
        out: list[str] = []
        for item in value[:30]:
            out.extend(_collect_text(item, max_depth=max_depth - 1))
        return out
    if isinstance(value, dict):
        out = []
        for item in list(value.values())[:50]:
            out.extend(_collect_text(item, max_depth=max_depth - 1))
        return out
    return []


def _slide_visible_text(slide: dict[str, Any]) -> str:
    parts: list[str] = []
    for field in _SLIDE_VISIBLE_FIELDS:
        parts.extend(_collect_text(slide.get(field), max_depth=4))
    return " ".join(parts)


def _generated_slide_visible_text(slide: GeneratedSlide) -> str:
    parts: list[str] = []
    for value in (
        slide.headline,
        slide.subheadline,
        slide.body,
        slide.bullets,
        slide.stat_blocks,
        slide.quote,
        slide.chart,
        slide.table,
        slide.timeline,
        slide.comparison,
        slide.diagram,
    ):
        parts.extend(_collect_text(value, max_depth=4))
    return " ".join(parts)


def _project_prompt_text(project: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in _PROJECT_TERM_KEYS:
        parts.extend(_collect_text(project.get(key), max_depth=2))
    v4_input = project.get("v4_input") if isinstance(project.get("v4_input"), dict) else {}
    for input_key in ("standard_input", "premium_prompt_input", "premium_structured_input"):
        raw = v4_input.get(input_key)
        if isinstance(raw, dict):
            for key in _PROJECT_TERM_KEYS:
                parts.extend(_collect_text(raw.get(key), max_depth=2))
    analysis = project.get("input_analysis") if isinstance(project.get("input_analysis"), dict) else {}
    entities = analysis.get("entities")
    if isinstance(entities, list):
        for entity in entities:
            if isinstance(entity, dict):
                parts.extend(_collect_text(entity.get("value"), max_depth=1))
    return " ".join(parts)


def _canonical_term_key(term: str) -> str:
    key = re.sub(r"[^a-z0-9()]+", " ", term.lower()).strip()
    return re.sub(r"\s+", " ", key)


def _term_present(term: str, text: str) -> bool:
    if not term or not text:
        return False
    term_norm = _canonical_term_key(term)
    text_norm = _canonical_term_key(text)
    if term_norm and term_norm in text_norm:
        return True
    compact_term = term_norm.replace(" ", "")
    compact_text = text_norm.replace(" ", "")
    return bool(compact_term and compact_term in compact_text)


def _dedupe_terms(terms: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in terms:
        term = re.sub(r"\s+", " ", str(raw).strip(" \t\r\n.,;:")).strip()
        if len(term) < 3:
            continue
        # Regexes must preserve technical nouns, not sentence fragments from
        # generated copy (for example "Zero-Trust models concentrate").
        if (
            len(term.split()) > 1
            and "-" in term
            and not any(term.lower().startswith(prefix) for prefix in _ALLOWED_HYPHENATED_PHRASE_PREFIXES)
        ):
            hyphenated = term.split()[0]
            if _term_present(hyphenated, term):
                term = hyphenated
        key = _canonical_term_key(term)
        if not key or key in seen or key in _TECHNICAL_TERM_STOPWORDS:
            continue
        if any(_term_present(term, existing) or _term_present(existing, term) for existing in out):
            continue
        seen.add(key)
        out.append(term)
    return out


def _extract_terms_from_text(source: str) -> list[str]:
    if not source:
        return []
    terms: list[str] = []
    for pattern in _TECHNICAL_TERM_PATTERNS:
        terms.extend(match.group(0) for match in pattern.finditer(source))
    quoted = re.findall(r"['\"]([^'\"]{3,80})['\"]", source)
    terms.extend(quoted)
    return _dedupe_terms(terms)[:20]


def _extract_project_terms(project: dict[str, Any]) -> list[str]:
    return _extract_terms_from_text(_project_prompt_text(project))


def _required_terms_for_regenerated_slide(
    *,
    project: dict[str, Any],
    prior: dict[str, Any],
    instruction: Optional[str],
    include_instruction_terms: bool = True,
) -> list[str]:
    prior_text = _slide_visible_text(prior)
    instruction_text = instruction or ""
    project_terms = _extract_project_terms(project)
    prior_terms = _extract_terms_from_text(prior_text)
    instruction_terms = _extract_terms_from_text(instruction_text) if include_instruction_terms else []
    source_terms = _dedupe_terms(project_terms + prior_terms + instruction_terms)
    if not source_terms:
        return []
    required: list[str] = []
    for term in source_terms:
        if _term_present(term, prior_text) or (include_instruction_terms and _term_present(term, instruction_text)):
            required.append(term)
    return _dedupe_terms(required)[:8]


def _augment_instruction_with_prompt_terms(
    instruction: Optional[str],
    *,
    project: dict[str, Any],
    prior: dict[str, Any],
) -> Optional[str]:
    required_terms = _required_terms_for_regenerated_slide(project=project, prior=prior, instruction=instruction)
    if not required_terms:
        return instruction
    base = (instruction or "").strip()
    term_line = (
        "Keep these original user/project terms represented in visible slide copy "
        f"where they remain truthful: {', '.join(required_terms)}."
    )
    if base:
        return f"{base}\n\n{term_line}"
    return term_line


def _join_terms_for_copy(terms: list[str]) -> str:
    if len(terms) <= 1:
        return terms[0] if terms else ""
    if len(terms) == 2:
        return f"{terms[0]} and {terms[1]}"
    return f"{', '.join(terms[:-1])}, and {terms[-1]}"


def _preserve_prior_prompt_terms(
    slide: GeneratedSlide,
    *,
    project: dict[str, Any],
    prior: dict[str, Any],
    instruction: Optional[str],
) -> None:
    required_terms = _required_terms_for_regenerated_slide(
        project=project,
        prior=prior,
        instruction=instruction,
        include_instruction_terms=False,
    )
    if not required_terms:
        return
    visible_text = _generated_slide_visible_text(slide)
    missing = [term for term in required_terms if not _term_present(term, visible_text)]
    if not missing:
        return

    # Push the missing terms into speaker_notes only — never visible
    # copy. Earlier this routine appended a synthetic "Technical scope
    # covers X, Y." sentence to the subheadline or bullets to force
    # term retention, but that string is not investor copy and leaked
    # into share viewers / PDFs as visible nonsense. Speaker notes are
    # hidden from viewers and remain a useful coaching channel for the
    # author.
    coaching = (
        "Coaching: surface these original prompt terms in the next edit if "
        f"they remain truthful — {_join_terms_for_copy(missing[:4])}."
    )
    existing_notes = (slide.speaker_notes or "").strip()
    if coaching not in existing_notes:
        slide.speaker_notes = (
            f"{existing_notes}\n\n{coaching}".strip()
            if existing_notes
            else coaching
        )[:1500]
    raw = dict(slide.raw or {})
    raw["preserved_prompt_terms"] = missing[:8]
    slide.raw = raw


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

    raw = dict(snapshot.get("raw") or {})
    if "structured_context" not in raw and "structured_context" in project:
        raw["structured_context"] = project["structured_context"]

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
        raw=raw,
    )


def _project_allows_images(project: dict[str, Any]) -> bool:
    """Return whether regeneration may introduce/keep image-backed slides."""
    mode = str(project.get("v4_mode") or project.get("mode") or "standard").lower()
    v4_input = project.get("v4_input") if isinstance(project.get("v4_input"), dict) else {}
    if mode == "standard":
        standard = v4_input.get("standard_input") if isinstance(v4_input.get("standard_input"), dict) else {}
        return bool(standard.get("generate_images", False))
    prompt = v4_input.get("premium_prompt_input") if isinstance(v4_input.get("premium_prompt_input"), dict) else {}
    structured = v4_input.get("premium_structured_input") if isinstance(v4_input.get("premium_structured_input"), dict) else {}
    if "generate_images" in prompt:
        return bool(prompt.get("generate_images"))
    if "generate_images" in structured:
        return bool(structured.get("generate_images"))
    return mode == "premium"


def _fallback_regenerated_slide(prior: dict[str, Any], instruction: Optional[str], error: str) -> GeneratedSlide:
    """Preserve a slide when free-tier providers are unavailable.

    This is an honest regeneration fallback: it does not invent new claims, it
    keeps the last known-good slide, and it records the provider failure in raw
    metadata so the editor can surface that a deterministic fallback was used.
    """
    slide = _slide_doc_to_generated(prior)
    raw = dict(slide.raw or {})
    raw["source_model"] = "deterministic_regen_fallback"
    raw["regeneration_fallback_reason"] = (error or "provider unavailable")[:300]
    if instruction:
        raw["regeneration_instruction"] = instruction[:600]
    slide.raw = raw
    slide.rationale = (slide.rationale or prior.get("rationale") or "Preserved previous slide during provider fallback")
    return slide


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
        links=list(doc.get("links") or []),
        raw=dict(doc.get("raw") or {}),
        render_decision=doc.get("render_decision") or None,
        team_members=list(doc.get("team_members") or []),
        requires_user_input=bool(doc.get("requires_user_input", False)),
        user_input_kind=doc.get("user_input_kind") or None,
        user_input_reason=doc.get("user_input_reason") or None,
        company_icon_url=doc.get("company_icon_url") or None,
        company_icon_hidden=bool(doc.get("company_icon_hidden", False)),
        company_icon_position=doc.get("company_icon_position") or None,
        company_icon_opacity=doc.get("company_icon_opacity"),
        rationale=str(doc.get("rationale") or ""),
        purpose=str(doc.get("purpose") or ""),
        background_color=doc.get("background_color") or None,
        background_gradient=doc.get("background_gradient") or None,
        icons=list(doc.get("icons") or []),
    )


def _ensure_design_tokens(project: dict[str, Any]) -> dict[str, Any]:
    tokens = project.get("design_tokens")
    if isinstance(tokens, dict) and tokens.get("palette") and tokens.get("fonts"):
        base = tokens
    else:
        base = resolve_design_tokens(
            design_profile=project.get("design_profile") if isinstance(project.get("design_profile"), dict) else None,
            purpose=project.get("purpose") or None,
            industry=project.get("industry") or None,
        ).to_dict()
    # Apply stored design memory (user overrides, kit preferences, visual direction)
    mem_raw = project.get("design_memory")
    if mem_raw and isinstance(mem_raw, dict):
        try:
            memory = DesignMemory.from_dict(mem_raw)
            base = apply_design_memory(memory, base)
        except Exception:
            pass
    return base


def _compile_ordered_deck(
    *,
    slide_docs: list[dict[str, Any]],
    project: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], Optional[dict[str, Any]]]:
    ordered_docs = sorted(slide_docs, key=lambda doc: int(doc.get("index", 0)))
    generated = [_slide_doc_to_generated(doc) for doc in ordered_docs]
    image_urls = {slide.index: slide.image_url for slide in generated if slide.image_url}
    design_tokens = _ensure_design_tokens(project)
    compiled = compile_slides(
        slides=generated,
        image_urls=image_urls,
        deck_title=project.get("title") or None,
        company_icon_url=project.get("company_icon_url") or None,
        design_tokens=design_tokens,
        template_id=project.get("template_id"),
        effects=(project.get("design_profile") or {}).get("effects")
        if isinstance(project.get("design_profile"), dict)
        else None,
    )
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
    allow_images: bool,
    preserve_user_edits: bool = True,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    team_members = list(new_slide.team_members or prior.get("team_members") or [])
    requires_input = bool(
        new_slide.requires_user_input
        or (prior.get("requires_user_input") and not team_members)
    )

    # Detect which text fields the user has edited since the last
    # regeneration. We compare the prior doc against its own snapshot
    # of the last AI-generated values (raw.last_generated_*). If a
    # field differs, it was edited by the user and must be preserved.
    prior_raw = prior.get("raw") if isinstance(prior.get("raw"), dict) else {}
    def _user_edited(field: str) -> bool:
        if not preserve_user_edits:
            return False
        baseline = prior_raw.get(f"last_generated_{field}") if isinstance(prior_raw, dict) else None
        current = prior.get(field)
        if baseline is None or current is None:
            return False
        return current != baseline

    new_raw = dict(new_slide.raw or {})
    # Snapshot what the LLM produced this round so the *next* regen can
    # tell user-edited fields apart from machine-overwritten ones.
    new_raw.setdefault("last_generated_headline", new_slide.headline)
    new_raw.setdefault("last_generated_subheadline", new_slide.subheadline)
    new_raw.setdefault("last_generated_body", new_slide.body)
    new_raw.setdefault("last_generated_bullets", list(new_slide.bullets or []))
    new_raw.setdefault("last_generated_speaker_notes", new_slide.speaker_notes)

    headline = prior.get("headline") if _user_edited("headline") else new_slide.headline
    subheadline = prior.get("subheadline") if _user_edited("subheadline") else new_slide.subheadline
    body = prior.get("body") if _user_edited("body") else new_slide.body
    bullets = prior.get("bullets") if _user_edited("bullets") else list(new_slide.bullets or [])
    speaker_notes = prior.get("speaker_notes") if _user_edited("speaker_notes") else new_slide.speaker_notes
    render_decision = new_slide.render_decision if isinstance(new_slide.render_decision, dict) else None
    image_prompt = new_slide.image_prompt
    has_image_asset = bool(new_slide.image_url or prior.get("image_url"))
    wants_image = bool(image_prompt) or (
        isinstance(render_decision, dict)
        and str(render_decision.get("modality") or "").lower() == "image"
    )
    if (not allow_images) or (wants_image and not has_image_asset):
        image_prompt = None
        render_decision = {
            "modality": "text",
            "renderer": "html",
            "reason": (
                "images disabled for this project"
                if not allow_images
                else "regeneration did not produce an image asset"
            ),
        }

    update_doc: dict[str, Any] = {
        "intent": new_slide.intent,
        "layout": new_slide.layout,
        "headline": headline,
        "subheadline": subheadline,
        "bullets": list(bullets or []),
        "body": body,
        "stat_blocks": list(new_slide.stat_blocks or []),
        "quote": new_slide.quote,
        "chart": new_slide.chart,
        "table": new_slide.table,
        "timeline": new_slide.timeline,
        "comparison": new_slide.comparison,
        "diagram": new_slide.diagram,
        "image_prompt": image_prompt,
        "speaker_notes": speaker_notes,
        "citations": list(new_slide.citations or []),
        "links": list(new_slide.links or prior.get("links") or []),
        "render_decision": render_decision,
        "team_members": team_members,
        "requires_user_input": requires_input,
        "user_input_kind": (new_slide.user_input_kind or prior.get("user_input_kind")) if requires_input else None,
        "user_input_reason": (new_slide.user_input_reason or prior.get("user_input_reason")) if requires_input else None,
        "company_icon_url": new_slide.company_icon_url or prior.get("company_icon_url"),
        "company_icon_hidden": bool(prior.get("company_icon_hidden", False)),
        "company_icon_position": prior.get("company_icon_position"),
        "company_icon_opacity": prior.get("company_icon_opacity"),
        "rationale": new_slide.rationale or prior.get("rationale", ""),
        "purpose": new_slide.purpose or prior.get("purpose", ""),
        "background_color": prior.get("background_color"),
        "background_gradient": prior.get("background_gradient"),
        "icons": list(prior.get("icons") or new_slide.icons or []),
        "raw": new_raw,
        "source_model": _source_model_for(new_slide, target_model),
        "version": int(prior.get("version", 1)) + 1,
        "updated_at": now,
        "regenerated_at": now,
    }
    if preserve_images and allow_images and has_image_asset:
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
                    "image_intent", "speaker_notes", "citations", "links", "layout",
                    "team_members", "requires_user_input", "user_input_kind",
                    "user_input_reason", "company_icon_url", "company_icon_hidden",
                    "company_icon_position", "company_icon_opacity", "background_color",
                    "background_gradient", "icons", "rationale", "purpose",
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
        docs = await db.slides.find({
            "$or": [{"project_id": project_id}, {"presentation_id": project_id}]
        }).sort("index", 1).to_list(length=300)
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
        allow_images = _project_allows_images(project)
        purpose = project.get("purpose") or ""
        writer = ParallelWriter()
        concurrency = max(1, min(int(request.concurrency or 1), MAX_REGEN_CONCURRENCY))
        if target_model:
            concurrency = 1
        semaphore = asyncio.Semaphore(concurrency)

        async def write_target(idx: int) -> GeneratedSlide:
            instruction = _augment_instruction_with_prompt_terms(
                per_slide_instructions.get(idx) or request.instruction,
                project=project,
                prior=docs_by_index[idx],
            )
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
            instruction = _augment_instruction_with_prompt_terms(
                per_slide_instructions.get(idx) or request.instruction,
                project=project,
                prior=docs_by_index[idx],
            )
            if isinstance(raw, Exception):
                fallback = _fallback_regenerated_slide(docs_by_index[idx], instruction, str(raw))
                generated_by_index[idx] = fallback
                outcomes.append(RegeneratedSlideOutcome(index=idx, ok=True))
                logger.warning(
                    "v4_regen.provider_failed_using_deterministic_fallback",
                    project_id=project_id,
                    slide_index=idx,
                    error=str(raw)[:300],
                )
                continue
            try:
                polish_generated_slides([raw])
                repair_slide(raw, skeleton_by_index.get(idx), research)
                _preserve_prior_prompt_terms(
                    raw,
                    project=project,
                    prior=docs_by_index[idx],
                    instruction=instruction,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("v4_regen.postprocess_failed", project_id=project_id, slide_index=idx, error=str(exc)[:200])
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

        # ─────────────────────────────────────────────────────────
        # Deck-level headline diversity gate.
        #
        # On a deck-wide regen (`regenerate-deck` / `regenerate-batch`)
        # the per-slide writers run independently and frequently echo
        # the same noun phrase across slides ("We are building a
        # marketplace", "We are building a marketplace for X", …).
        # The original generation pipeline catches this with
        # `score_deck_diversity` + a rewrite pass on the critic. The
        # regen engine bypassed it, which let regenerated decks ship
        # with 4+ near-duplicate headlines.
        #
        # Run the same diversity scorer here. For every slide whose
        # headline is flagged as a near-duplicate we re-issue the
        # writer with an explicit "make this headline distinct"
        # instruction. We only retry once — it is enough to break the
        # echo and avoids unbounded re-rolls.
        # ─────────────────────────────────────────────────────────
        if request.change_type in ("regenerate-deck", "regenerate-batch") and len(generated_by_index) >= 3:
            try:
                from app.services.v4.headline_diversity_scorer import score_deck_diversity
            except Exception:  # noqa: BLE001
                score_deck_diversity = None  # type: ignore[assignment]

            if score_deck_diversity is not None:
                ordered_for_scoring = [
                    generated_by_index[i] for i in sorted(generated_by_index.keys())
                ]
                ordered_indices = sorted(generated_by_index.keys())
                try:
                    diversity = score_deck_diversity(ordered_for_scoring)
                except Exception as div_err:  # noqa: BLE001
                    logger.debug(
                        "v4_regen.diversity_score_failed",
                        project_id=project_id,
                        error=str(div_err)[:200],
                    )
                    diversity = None  # type: ignore[assignment]

                if diversity is not None and diversity.flagged_indices:
                    flagged_real_indices = [
                        ordered_indices[pos]
                        for pos in diversity.flagged_indices
                        if 0 <= pos < len(ordered_indices)
                    ]
                    logger.warning(
                        "v4_regen.headline_diversity_low",
                        project_id=project_id,
                        score=getattr(diversity, "score", None),
                        flagged=flagged_real_indices,
                        issues=getattr(diversity, "issues", []),
                    )
                    seen_phrases = []
                    for ref_idx in ordered_indices:
                        if ref_idx in flagged_real_indices:
                            continue
                        head = (generated_by_index[ref_idx].headline or "").strip()
                        if head:
                            seen_phrases.append(head)
                    avoid_clause = ""
                    if seen_phrases:
                        avoid_clause = (
                            " Avoid repeating these existing headlines verbatim or as paraphrases: "
                            + " | ".join(seen_phrases[:6])
                            + "."
                        )

                    async def rewrite_for_diversity(idx: int) -> GeneratedSlide:
                        rewrite_instruction = (
                            "Rewrite this slide's headline to be specific and distinct from the rest of the deck. "
                            "Use a concrete noun phrase, a verb that has not been used elsewhere, and at least one "
                            "metric, name, or fact tied to the user's actual prompt."
                            + avoid_clause
                        )
                        merged_instruction = _augment_instruction_with_prompt_terms(
                            rewrite_instruction,
                            project=project,
                            prior=docs_by_index[idx],
                        )
                        target_skeleton = augment_skeleton_with_instruction(
                            skeleton_by_index[idx], merged_instruction
                        )
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

                    rewrite_results = await asyncio.gather(
                        *(rewrite_for_diversity(i) for i in flagged_real_indices),
                        return_exceptions=True,
                    )
                    for idx, raw in zip(flagged_real_indices, rewrite_results):
                        if isinstance(raw, Exception):
                            logger.debug(
                                "v4_regen.diversity_rewrite_failed",
                                project_id=project_id,
                                slide_index=idx,
                                error=str(raw)[:200],
                            )
                            continue
                        try:
                            polish_generated_slides([raw])
                            repair_slide(raw, skeleton_by_index.get(idx), research)
                            _preserve_prior_prompt_terms(
                                raw,
                                project=project,
                                prior=docs_by_index[idx],
                                instruction=request.instruction,
                            )
                        except Exception as exc:  # noqa: BLE001
                            logger.debug(
                                "v4_regen.diversity_postprocess_failed",
                                project_id=project_id,
                                slide_index=idx,
                                error=str(exc)[:200],
                            )
                        generated_by_index[idx] = raw
                    logger.info(
                        "v4_regen.headline_diversity_pass_applied",
                        project_id=project_id,
                        rewritten=flagged_real_indices,
                    )

                # Final dedup safety net. Even after a rewrite pass the
                # writers can converge on near-duplicate phrasings (e.g.
                # "We connect installers with homeowners" appearing twice).
                # Walk the deck in order and append a discriminating
                # suffix to any headline that exactly repeats — or has
                # Jaccard >= 0.7 with — an earlier one. The suffix uses
                # the slide intent so the result still reads cleanly
                # without firing another LLM round.
                def _bag(text: str) -> set[str]:
                    return set(t for t in text.lower().split() if len(t) > 1)

                seen_bags: list[tuple[set[str], str]] = []
                for ord_idx in sorted(generated_by_index.keys()):
                    slide_obj = generated_by_index[ord_idx]
                    head = (slide_obj.headline or "").strip()
                    if not head:
                        continue
                    bag = _bag(head)
                    too_similar = False
                    if bag:
                        for prev_bag, prev_head in seen_bags:
                            if not prev_bag:
                                continue
                            inter = len(bag & prev_bag)
                            union = len(bag | prev_bag)
                            if union and (
                                head.lower() == prev_head.lower()
                                or inter / union >= 0.7
                            ):
                                too_similar = True
                                break
                    if too_similar:
                        intent_label = (
                            str(slide_obj.intent or "").replace("_", " ").strip().title()
                        )
                        if intent_label and intent_label.lower() not in head.lower():
                            slide_obj.headline = f"{head}: {intent_label}"
                        else:
                            slide_obj.headline = f"{head} (slide {ord_idx + 1})"
                        logger.info(
                            "v4_regen.headline_dedup_suffix",
                            project_id=project_id,
                            slide_index=ord_idx,
                            from_head=head,
                            to_head=slide_obj.headline,
                        )
                    seen_bags.append((_bag(slide_obj.headline or ""), slide_obj.headline or ""))

        next_docs_by_index = {int(doc.get("index", -1)): dict(doc) for doc in docs}
        update_docs_by_index: dict[int, dict[str, Any]] = {}
        for idx, new_slide in generated_by_index.items():
            prior = docs_by_index[idx]
            update_doc = _build_slide_update_doc(
                new_slide,
                prior,
                target_model=target_model,
                preserve_images=request.preserve_images,
                allow_images=allow_images,
                preserve_user_edits=request.preserve_user_edits,
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
