"""V4 research recency contract.

Pure module. No I/O, no globals beyond compiled regex literals. Every
function is deterministic; every dataclass is frozen so the values
flowing through ``ResearchCollector`` can be safely stuffed into log
events, cache keys, and SSE payloads without aliasing surprises.

The plan that motivates this file is
``docs/founder-plans/04-research-freshness-and-tiering.md``.

Three responsibilities:

1. ``RecencyWindow`` — the typed contract that providers translate
   to their own date-filter parameter.
2. ``resolve_recency_window`` — purpose-driven recency selection,
   with a query-level "user is asking about *now*" override.
3. ``freshness_score`` / ``combined_score`` / ``staleness_label`` —
   numeric ranking and staleness annotation that replace the
   lexical ``(authority, published_at_string)`` sort that lived
   inside ``ResearchPacket.top_citations``.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional

# ---------------------------------------------------------------------
# Purpose buckets — keep these strings in sync with the 15 values of
# ``app.models.generation_input_v4.PresentationPurpose``. We compare
# lower-cased strings so callers can pass either the enum's ``.value``
# or the bare string from analyzer output.
# ---------------------------------------------------------------------

_TIGHT_PURPOSES: frozenset[str] = frozenset({
    "pitch_deck",
    "investor_update",
    "demo_day",
    "quarterly_review",
    "board_meeting",
    "sales_deck",
    "product_launch",
})

_MEDIUM_PURPOSES: frozenset[str] = frozenset({
    "company_overview",
    "case_study",
    "project_proposal",
    "conference_talk",
    "internal_memo",
})

_LOOSE_PURPOSES: frozenset[str] = frozenset({
    "educational",
    "training",
    "custom",
})


# ---------------------------------------------------------------------
# Heuristic temporal-intent detector.
#
# Single source of truth — ``rag_enrichment.py`` is updated to delegate
# its ``_RE_CURRENT_HINT`` check to ``query_signals_now`` so we never
# split the heuristic across two regexes.
#
# Pattern intent:
#   - explicit "now/today/latest/live/real-time" markers
#   - "this week/month/quarter/year"
#   - quarter literals like ``Q1 2026`` / ``q3 2027``
#   - fiscal year literals like ``FY 2026``
#   - any 4-digit year from 2024 onward (the regex covers 2024..2099 to
#     stay correct as the calendar advances; 2024-2026 was hard-coded
#     in the original ``rag_enrichment.py`` regex which would silently
#     stop matching in 2027)
# ---------------------------------------------------------------------

_NOW_MARKERS: re.Pattern[str] = re.compile(
    r"(?ix)"
    r"\b("
    r"current(?:ly)?"
    r"|today"
    r"|now"
    r"|latest"
    r"|live"
    r"|real[-\s]?time"
    r"|this\s+(?:week|month|quarter|year)"
    r"|q[1-4]\s*20\d{2}"
    r"|fy\s*20\d{2}"
    r"|20(?:2[4-9]|[3-9]\d)"
    r")\b"
)


def query_signals_now(user_query: Optional[str]) -> bool:
    """True if the user query contains a temporal-now marker.

    Defensive against ``None`` and non-string input so callers can hand
    us raw analyzer fields without pre-checks.
    """

    if not user_query:
        return False
    if not isinstance(user_query, str):
        try:
            user_query = str(user_query)
        except Exception:
            return False
    return bool(_NOW_MARKERS.search(user_query))


# ---------------------------------------------------------------------
# RecencyWindow dataclass
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class RecencyWindow:
    """Typed recency contract passed from the pipeline to providers.

    Fields:
        earliest:               hard floor — citations strictly older
                                than this date are dropped.
        boost_after:            soft floor — citations newer than this
                                receive a ranking boost.
        label:                  short human-readable tag emitted in
                                logs / SSE events.
        decay_half_life_days:   half-life used by ``freshness_score``.
                                Tight windows pick a short half-life so
                                older content decays fast; loose
                                windows tolerate older content.

    Frozen so the same instance can flow into a Redis cache key
    component without risk of mutation downstream.
    """

    earliest: date
    boost_after: date
    label: str
    decay_half_life_days: int

    def days_back(self, today: Optional[date] = None) -> int:
        """Return ``(today - earliest).days`` for providers that take
        an integer day count (Tavily ``days``). Capped at 365 because
        Tavily silently caps anything larger; callers get explicit
        truncation rather than silent server-side adjustment."""

        ref = today or date.today()
        delta = (ref - self.earliest).days
        if delta < 1:
            return 1
        return min(delta, 365)


# ---------------------------------------------------------------------
# resolve_recency_window — purpose-driven selection with query override
# ---------------------------------------------------------------------


def resolve_recency_window(
    *,
    purpose: Optional[str],
    user_query: Optional[str],
    today: Optional[date] = None,
) -> RecencyWindow:
    """Pick the right ``RecencyWindow`` for this request.

    Order of precedence:
      1. Query-level "user is asking about NOW" — tightest window.
      2. Purpose-bucket lookup.
      3. Conservative default for unknown purposes.

    Pure function. No imports of upstream models so this stays cheap
    to test in isolation.
    """

    ref = today or date.today()
    purpose_str = (purpose or "").strip().lower()
    if purpose_str.startswith("presentationpurpose."):
        # Defensive: someone passed ``str(enum)`` instead of ``enum.value``.
        purpose_str = purpose_str.split(".", 1)[1]

    if query_signals_now(user_query):
        return RecencyWindow(
            earliest=ref - timedelta(days=180),
            boost_after=ref - timedelta(days=90),
            label="last_180d",
            decay_half_life_days=120,
        )

    if purpose_str in _TIGHT_PURPOSES:
        return RecencyWindow(
            earliest=ref - timedelta(days=365),
            boost_after=ref - timedelta(days=180),
            label="last_365d",
            decay_half_life_days=180,
        )

    if purpose_str in _MEDIUM_PURPOSES:
        return RecencyWindow(
            earliest=ref - timedelta(days=730),
            boost_after=ref - timedelta(days=365),
            label="last_2y",
            decay_half_life_days=365,
        )

    if purpose_str in _LOOSE_PURPOSES:
        return RecencyWindow(
            earliest=ref - timedelta(days=365 * 3),
            boost_after=ref - timedelta(days=365),
            label="last_3y",
            decay_half_life_days=730,
        )

    # Unknown purpose — be conservative (2-year window).
    return RecencyWindow(
        earliest=ref - timedelta(days=730),
        boost_after=ref - timedelta(days=365),
        label="last_2y",
        decay_half_life_days=365,
    )


# ---------------------------------------------------------------------
# Freshness scoring
# ---------------------------------------------------------------------


_UNDATED_FRESHNESS: float = 0.3
"""Score awarded to citations with no parseable ``published_at``.

Set deliberately above 0.0 because some providers (You.com, Jina,
GitHub repos) genuinely don't carry publication dates and we don't
want to nuke them entirely; set well below 0.5 so a known-recent dated
citation always outranks an undated one.
"""


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse the wide variety of ISO-ish strings providers return.

    Handles:
      * ``2025-09-15T10:30:00Z``                   (NewsAPI)
      * ``2025-09-15T10:30:00+00:00``              (Exa)
      * ``2025-09-15``                              (Tavily occasionally)
      * ``2025-09-15 10:30:00``                    (NewsData)
      * ``Mon, 15 Sep 2025 10:30:00 GMT``          (Reddit / occasional)

    Returns ``None`` rather than raising for any unparseable input.
    """

    if not value or not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None

    # Normalise the trailing ``Z`` form that ``fromisoformat`` only
    # accepts on Python 3.11+.
    iso_candidate = candidate.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(iso_candidate)
    except ValueError:
        # Date-only string?
        try:
            dt = datetime.strptime(candidate, "%Y-%m-%d")
        except ValueError:
            # RFC 2822 (Reddit style)?
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(candidate)
            except (TypeError, ValueError):
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def freshness_score(
    published_at: Optional[str],
    *,
    now: Optional[datetime] = None,
    half_life_days: int = 365,
) -> float:
    """Exponential decay freshness score in ``[0, 1]``.

    A citation published ``half_life_days`` ago scores 0.5; one
    published ``2 * half_life_days`` ago scores 0.25; an undated
    citation scores ``_UNDATED_FRESHNESS`` (0.3); a future-dated
    citation is clamped to 1.0 (some providers report the index/crawl
    time rather than the publish time, so future timestamps do happen
    and are not bugs to flag).
    """

    if half_life_days <= 0:
        half_life_days = 365
    parsed = parse_iso_datetime(published_at)
    if parsed is None:
        return _UNDATED_FRESHNESS
    ref = now or datetime.now(timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    age_days = (ref - parsed).total_seconds() / 86400.0
    if age_days <= 0:
        return 1.0
    return math.pow(0.5, age_days / float(half_life_days))


def combined_score(
    *,
    source_authority: float,
    published_at: Optional[str],
    now: Optional[datetime] = None,
    half_life_days: int,
    recency_weight: float = 0.45,
) -> float:
    """Weighted blend of authority and freshness.

    ``recency_weight`` defaults to 0.45 — high enough that a recent
    medium-authority outlet (e.g. TechCrunch, score 0.7) outranks a
    five-year-old top-tier outlet (score 0.95) on a tight window, but
    low enough that a fresh blog (0.5) cannot outrank a fresh Reuters
    citation (0.95).

    Authority and freshness both live in ``[0, 1]``, so the blended
    score is also in ``[0, 1]`` regardless of weight.
    """

    rw = max(0.0, min(1.0, recency_weight))
    a = max(0.0, min(1.0, float(source_authority)))
    f = freshness_score(published_at, now=now, half_life_days=half_life_days)
    return rw * f + (1.0 - rw) * a


# ---------------------------------------------------------------------
# Staleness annotation (for UI badges, no persistence)
# ---------------------------------------------------------------------


def staleness_label(
    published_at: Optional[str],
    *,
    window: RecencyWindow,
    today: Optional[date] = None,
) -> str:
    """Bucket a citation against the window into ``fresh`` / ``aging``
    / ``stale`` / ``undated``.

    ``fresh``    — published on or after ``boost_after``.
    ``aging``    — between ``earliest`` and ``boost_after``.
    ``stale``    — strictly older than ``earliest`` (these are dropped
                   by the hard-floor filter, but the label still gets
                   computed for the in-memory rejection log).
    ``undated``  — citation has no parseable date.
    """

    parsed = parse_iso_datetime(published_at)
    if parsed is None:
        return "undated"
    ref = today or date.today()
    pub_date = parsed.date()
    if pub_date >= window.boost_after:
        return "fresh"
    if pub_date >= window.earliest:
        return "aging"
    # Future-dated still treated as fresh — see freshness_score docstring.
    if pub_date > ref:
        return "fresh"
    return "stale"
