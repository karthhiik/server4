"""
V4 LLM Safe-Call — timeout + hedged fallback wrapper around ModelRouter.

Plan-v4 additions (backward-compatible — all existing callers still work):
    * resumable=True + slot="..."  stashes partial output to Redis on failure
      so the fallback model picks up where the first one stopped.

Why this exists:
- A single Groq/Kimi/DeepSeek call can hang for 60s+ on a network blip,
  blocking the entire generation. Without a per-call timeout, one stuck
  writer ruins the whole pipeline.
- Hedged fallback: if the primary call times out OR raises, try the
  designated fallback model once. If that also fails, raise.

Usage:
    response = await safe_complete(
        router=self.router,
        primary_task=TaskType.OUTLINE_PLANNING,
        fallback_task=TaskType.TEMPLATE_FILL,
        messages=[...],
        timeout_s=25.0,
        resumable=True,
        slot=f"writer_{slide.index}",
        ...
    )
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

import structlog

from app.services.llm.model_router import ModelRouter, TaskType
from app.services.llm import partial_store
from app.services.llm.error_classifier import (
    ErrorClass,
    classify as classify_error,
)
from app.services.v4.errors import WriterTimeoutError

logger = structlog.get_logger(__name__)


# ── Task-tier guard ────────────────────────────────────────────────
# The senior-slide-engineer skill mandates: "No silent fallbacks to
# classifier models for narrative/critic/grader/judge tasks."
#
# These two sets are the contract. ``_NARRATIVE_TIER_TASKS`` is the set
# of tasks where weak-classifier models would silently degrade output
# quality (telegraphic phrases, "Transforming industries" slop, lost
# reasoning chains). ``_CLASSIFIER_TIER_TASKS`` is the set the guard
# refuses to accept as a *fallback* for narrative tasks.
#
# The guard runs at call-site (caller wiring), not at chain-level —
# every routing chain in ``model_router.py`` already ends with a strong
# safety tail (OpenRouter free-tier qwen + GPT-4o-mini for planning),
# which is the correct design. The guard prevents code from explicitly
# wiring narrative→classifier as a fallback.
_NARRATIVE_TIER_TASKS: frozenset[TaskType] = frozenset({
    TaskType.NARRATIVE_STORYTELLING,
    TaskType.PITCH_DEBATE,
    TaskType.DUAL_MODE_REWRITE,
    TaskType.STYLE_ADAPTATION,
    TaskType.PREMIUM_THESIS_PLANNING,
    TaskType.PREMIUM_TARGETED_REWRITE,
    TaskType.REFINEMENT,           # critic / grader / judge
    TaskType.CITATION_GUARD,
    TaskType.EVIDENCE_EXTRACTION,
    TaskType.CROSS_VALIDATION,
    TaskType.SPEAKER_NOTES,
    TaskType.OUTLINE_PLANNING,     # planner reasoning
    TaskType.DEEP_RESEARCH_PLAN,
})

_CLASSIFIER_TIER_TASKS: frozenset[TaskType] = frozenset({
    TaskType.INTENT_CLASSIFICATION,
    TaskType.ENTITY_EXTRACTION,
})


def _validate_task_tier_pairing(
    primary: TaskType, fallback: Optional[TaskType], phase: str,
) -> None:
    """Refuse narrative→classifier fallback wiring at call time.

    Raises ``ValueError`` so the bug surfaces in development / tests
    instead of silently producing low-quality content in production.
    """
    if fallback is None:
        return
    if primary in _NARRATIVE_TIER_TASKS and fallback in _CLASSIFIER_TIER_TASKS:
        raise ValueError(
            f"safe_complete: narrative-tier task {primary.name} cannot fall "
            f"back to classifier-tier task {fallback.name} (phase={phase!r}). "
            f"Use a refinement / template-fill / structured-json task as the "
            f"fallback instead. See senior-slide-engineer skill."
        )


_RESUME_HINT_TMPL = (
    "\n\n[RESUME HINT] A previous model started this task and was interrupted. "
    "Below is what it produced before stopping. Continue from where it stopped "
    "so the final output is coherent. Do not restart and do not apologize. "
    "If the expected format is JSON, return ONE complete valid JSON object "
    "that subsumes the partial content (not a diff).\n"
    "<PARTIAL_OUTPUT>\n{partial}\n</PARTIAL_OUTPUT>\n"
)


def _inject_resume_hint(
    messages: list[dict[str, str]],
    partial: str,
) -> list[dict[str, str]]:
    """Return a shallow copy of messages with the resume hint appended to
    the last user message (so the system prompt prefix cache stays intact)."""
    if not partial or not partial.strip():
        return messages
    out = [dict(m) for m in messages]
    for m in reversed(out):
        if m.get("role") == "user":
            m["content"] = (m.get("content") or "") + _RESUME_HINT_TMPL.format(
                partial=partial.strip()[-3500:]
            )
            return out
    out.append({"role": "user", "content": _RESUME_HINT_TMPL.format(partial=partial)})
    return out


def _extract_partial(err: BaseException) -> str:
    """Best-effort: some clients attach partial text on the exception."""
    for attr in ("partial", "partial_content", "content_so_far"):
        val = getattr(err, attr, None)
        if isinstance(val, str) and val.strip():
            return val
    return ""


async def safe_complete(
    *,
    router: ModelRouter,
    primary_task: TaskType,
    fallback_task: Optional[TaskType] = None,
    messages: list[dict[str, str]],
    timeout_s: float = 25.0,
    fallback_timeout_s: float = 20.0,
    presentation_id: Optional[str] = None,
    phase: str = "",
    resumable: bool = False,
    slot: Optional[str] = None,
    **complete_kwargs: Any,
):
    """Call router.complete with a hard timeout and one hedged fallback.

    Raises WriterTimeoutError if both attempts fail.

    When ``resumable`` is True and a ``presentation_id`` is supplied, any
    partial output carried on the primary exception is stashed in Redis and
    re-injected into the fallback call's user message as a RESUME HINT. This
    prevents starting-from-scratch on every model switch during a long slide
    generation.
    """
    slot_key = slot or phase or "default"
    use_resume = bool(resumable and presentation_id)

    # Tier guard: refuse narrative→classifier fallback wiring (skill rule).
    _validate_task_tier_pairing(primary_task, fallback_task, phase)

    # Phase A — primary
    try:
        resp = await asyncio.wait_for(
            router.complete(
                task_type=primary_task,
                messages=messages,
                presentation_id=presentation_id,
                phase=phase,
                **complete_kwargs,
            ),
            timeout=timeout_s,
        )
        # CRITICAL FIX: Detect empty/0-token responses and treat as failure
        # so the fallback chain can try the next model.
        if resp and hasattr(resp, "content") and resp.content and resp.content.strip():
            if use_resume:
                try:
                    await partial_store.clear_partial(presentation_id, phase, slot_key)
                except Exception:  # noqa: BLE001
                    pass
            return resp
        # Empty response — treat as failure to trigger fallback
        logger.warning(
            "v4_llm_primary_empty_response",
            phase=phase,
            task=primary_task.name,
            model=getattr(resp, "model", "unknown"),
            tokens=getattr(resp, "tokens_used", 0),
        )
        raise ValueError("Empty response from primary model")
    except (asyncio.TimeoutError, Exception) as primary_err:  # noqa: BLE001
        is_timeout = isinstance(primary_err, asyncio.TimeoutError)
        err_class = ErrorClass.TIMEOUT if is_timeout else classify_error(primary_err)

        partial_text = _extract_partial(primary_err)
        if use_resume and partial_text:
            try:
                await partial_store.save_partial(
                    presentation_id, phase, slot_key, partial_text,
                )
            except Exception:  # noqa: BLE001
                pass

        logger.warning(
            "v4_llm_primary_failed",
            phase=phase,
            task=primary_task.name,
            timeout=is_timeout,
            error_class=err_class.value,
            error=type(primary_err).__name__ if not is_timeout else "TimeoutError",
            timeout_s=timeout_s,
            has_partial=bool(partial_text),
        )
        if fallback_task is None:
            raise

        # Phase B — fallback, optionally with resume hint
        fb_messages = messages
        if use_resume:
            try:
                stashed = await partial_store.load_partial(
                    presentation_id, phase, slot_key,
                )
            except Exception:  # noqa: BLE001
                stashed = None
            if stashed:
                fb_messages = _inject_resume_hint(messages, stashed)

        try:
            resp = await asyncio.wait_for(
                router.complete(
                    task_type=fallback_task,
                    messages=fb_messages,
                    presentation_id=presentation_id,
                    phase=f"{phase}_fallback",
                    **complete_kwargs,
                ),
                timeout=fallback_timeout_s,
            )
            # CRITICAL FIX: Also detect empty responses in fallback path
            if not (resp and hasattr(resp, "content") and resp.content and resp.content.strip()):
                logger.warning(
                    "v4_llm_fallback_empty_response",
                    phase=phase,
                    fallback_task=fallback_task.name,
                    model=getattr(resp, "model", "unknown"),
                )
                raise ValueError("Empty response from fallback model")
            if use_resume:
                try:
                    await partial_store.clear_partial(
                        presentation_id, phase, slot_key,
                    )
                except Exception:  # noqa: BLE001
                    pass
            return resp
        except (asyncio.TimeoutError, Exception) as fb_err:  # noqa: BLE001
            logger.error(
                "v4_llm_fallback_failed",
                phase=phase,
                primary_task=primary_task.name,
                fallback_task=fallback_task.name,
                error=str(fb_err)[:300],
            )
            raise WriterTimeoutError(
                f"{phase}: primary={type(primary_err).__name__} fallback={type(fb_err).__name__}"
            ) from fb_err
