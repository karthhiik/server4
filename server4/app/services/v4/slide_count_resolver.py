"""Slide-count resolver — single source of truth for the requested deck length.

Plan 02 (Slide Count Bug v2) — see ``docs/founder-plans/02-slide-count-bug.md``.

Contract:
    ``resolve_requested_count`` returns a non-None ``int`` in ``[1, 50]``.
    Every consumer (skeleton planner, content pipeline, parallel writer,
    image generator, slide compiler) must take its target slide count from
    this function and from nowhere else. The user's optional ``slide_count``
    field on ``StandardGenerationInput`` / ``PremiumPromptInput`` /
    ``PremiumStructuredInput`` is the only optional input; everything past
    the router boundary sees the resolved integer.

The resolver is pure: no I/O, no LLM calls, no DB. It is safe to invoke
synchronously from request handlers.
"""

from __future__ import annotations

from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# Hard universal limits matching the Pydantic ``ge=1, le=50`` field
# constraints in ``app.models.generation_input_v4``.
_MIN_COUNT: int = 1
_MAX_COUNT: int = 50

# Per-purpose deck length defaults derived from real pitch-deck research and
# the existing ``CANONICAL_*_PITCH_STRUCTURE`` arrays in
# ``skeleton_planner.py`` (11 / 10 intents respectively, compressed).
#
# Keys are values of ``app.models.generation_input_v4.PresentationPurpose``
# (string Enum, ``.value`` form). Add new purposes here when extending the
# Enum.
_DEFAULT_BY_PURPOSE: dict[str, int] = {
    "pitch_deck":       12,
    "investor_update":  10,
    "sales_deck":        7,
    "product_launch":    9,
    "quarterly_review": 10,
    "board_meeting":     8,
    "conference_talk":  12,
    "training":          8,
    "project_proposal":  9,
    "case_study":        9,
    "company_overview": 10,
    "demo_day":          8,
    "educational":       8,
    "internal_memo":     5,
    "custom":            8,
}

# Mode-level fallback when neither the user nor the analyzer offered a
# count and the purpose is missing from ``_DEFAULT_BY_PURPOSE``. Premium
# decks are richer by default; standard decks stay tighter to keep the
# generation budget under control.
_MODE_DEFAULT: dict[str, int] = {
    "premium":  10,
    "standard":  8,
}

# Soft warning threshold above which long-deck drift risk in the planner
# (LLM frequently caps at ~25 in a single response) becomes material.
# We do NOT cap or modify the value — the user's request is honored — but
# we emit a structlog warning so observability dashboards can surface it.
_LONG_DECK_WARN_AT: int = 25


def _clamp(value: int) -> int:
    """Pin ``value`` into ``[_MIN_COUNT, _MAX_COUNT]``."""
    return max(_MIN_COUNT, min(_MAX_COUNT, int(value)))


def resolve_requested_count(
    *,
    user_supplied: Optional[int],
    analyzer_suggested: Optional[int],
    purpose: Optional[str],
    mode: Optional[str],
    project_id: Optional[str] = None,
) -> int:
    """Return the deck slide count to use for the rest of the pipeline.

    Resolution priority (first matching wins):
      1. ``user_supplied`` — the explicit value from the request body.
      2. ``analyzer_suggested`` — the InputAnalyzer's heuristic.
      3. ``_DEFAULT_BY_PURPOSE[purpose]``.
      4. ``_MODE_DEFAULT[mode]``.
      5. Hard fallback of ``8``.

    All return values are clamped to ``[1, 50]``. The function never
    returns ``None`` and never raises.

    ``project_id`` is purely for log correlation and is optional.
    """
    path: str
    candidate: Optional[int]

    if user_supplied is not None:
        candidate = _clamp(user_supplied)
        path = "user_explicit"
    elif analyzer_suggested is not None:
        candidate = _clamp(analyzer_suggested)
        path = "analyzer_suggested"
    elif purpose and purpose in _DEFAULT_BY_PURPOSE:
        candidate = _DEFAULT_BY_PURPOSE[purpose]
        path = "purpose_default"
    elif mode and mode in _MODE_DEFAULT:
        candidate = _MODE_DEFAULT[mode]
        path = "mode_default"
    else:
        candidate = 8
        path = "hard_default"

    final = _clamp(candidate)

    logger.info(
        "slide_count_resolved",
        project_id=project_id,
        final_count=final,
        path=path,
        user_supplied=user_supplied,
        analyzer_suggested=analyzer_suggested,
        purpose=purpose,
        mode=mode,
    )
    if final >= _LONG_DECK_WARN_AT:
        logger.warning(
            "slide_count_high",
            project_id=project_id,
            count=final,
            threshold=_LONG_DECK_WARN_AT,
            note=(
                "long decks have higher LLM drift risk; planner repair loop "
                "and gpt-4o-mini final safety tail will compensate"
            ),
        )
    return final


__all__ = [
    "resolve_requested_count",
]
