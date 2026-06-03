"""
Share-link analytics aggregation.

Pure aggregation functions over ``share_view_events`` documents. Every
metric is computed from real, persisted events — no demo data, no
fake sessions, no inferred viewers. When there isn't enough signal, the
returned shape says so explicitly via ``"sufficient_signal": False``.

Events used (matching ``track_share_event`` in v4_editor.py)::

    view_start | slide_advance | view_end | completed | heartbeat
    slide_click | viewer_identified | edit_started | edit_saved | download

Metrics produced
----------------

* ``opens`` — total ``view_start`` events (raw open count, not unique)
* ``views`` — count of unique viewer_session_id values
* ``unique_viewers`` — count of unique viewer identities (email when
  collected, else session id)
* ``avg_dwell_seconds`` — mean active dwell across sessions
* ``median_dwell_seconds`` — robust midpoint dwell
* ``completion_rate`` — fraction of sessions that hit ``completed``
* ``total_slides_viewed`` — count of ``slide_advance`` events
* ``last_viewed_hours_ago`` — hours since the most recent event
* ``slide_attention`` — list of ``{slide_index, sum_dwell_ms,
  exits, sessions}`` so the UI can highlight the strongest slide
  and the biggest drop-off
* ``month_activity`` — current-month daily open/session buckets from
  real ``view_start`` events
* ``viewer_sessions`` — recent session summaries for the real-time feed
* ``ghost_viewers`` — sessions that opened but produced no
  ``slide_advance`` for ``ghost_after_days`` days
* ``viewer_segments`` — warm / engaged / cold / ghost labels derived
  only from observed session behavior
* ``action_insights`` — deterministic next-action prompts based on
  enough real sessions, never generated from invented viewers
* ``sufficient_signal`` — True iff at least ``min_sessions`` sessions
  are present (default 3); below that, the UI should show "not enough
  signal yet" instead of inventing patterns

The aggregator is pure — same input → same output. Easy to unit-test.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

import structlog

logger = structlog.get_logger(__name__)


_VALID_EVENT_TYPES: frozenset[str] = frozenset({
    "view_start",
    "slide_advance",
    "view_end",
    "completed",
    "heartbeat",
    "slide_click",
    "edit_started",
    "edit_saved",
    "download",
    "viewer_identified",
    "viewer_note_shown",
    "viewer_note_dismissed",
})


def _ensure_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    if pct <= 0:
        return sorted_vals[0]
    if pct >= 100:
        return sorted_vals[-1]
    idx = int(round((pct / 100.0) * (len(sorted_vals) - 1)))
    return sorted_vals[max(0, min(len(sorted_vals) - 1, idx))]


def aggregate_share_analytics(
    *,
    events: Iterable[dict[str, Any]],
    total_slides: int,
    now: Optional[datetime] = None,
    min_sessions_for_signal: int = 3,
    ghost_after_days: int = 4,
) -> dict[str, Any]:
    """Aggregate raw events into the analytics payload.

    ``events`` is a list of share_view_events docs (already filtered to
    one share_id). ``total_slides`` is needed so completion is computed
    against a real ceiling (some decks are 6 slides, others 18).
    """
    now = _ensure_aware(now) or datetime.now(timezone.utc)

    sessions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    open_count = 0
    advance_count = 0
    download_count = 0
    edit_count = 0
    note_shown_count = 0
    note_dismissed_count = 0
    note_dismissed_sessions: set[str] = set()
    completed_sessions: set[str] = set()
    viewer_emails: set[str] = set()
    latest_at: Optional[datetime] = None
    per_slide_dwell: dict[int, int] = defaultdict(int)
    per_slide_exits: dict[int, int] = defaultdict(int)
    per_slide_sessions: dict[int, set[str]] = defaultdict(set)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_open_counts: dict[str, int] = defaultdict(int)
    month_sessions: dict[str, set[str]] = defaultdict(set)

    for ev in events:
        et = (ev.get("event_type") or "").strip()
        if et not in _VALID_EVENT_TYPES:
            continue
        sid = str(ev.get("viewer_session_id") or "")
        if not sid:
            sid = "anonymous"
        sessions[sid].append(ev)

        slide_index = ev.get("slide_index")
        try:
            slide_index = int(slide_index) if slide_index is not None else 0
        except (TypeError, ValueError):
            slide_index = 0
        dwell_ms = ev.get("dwell_ms")
        try:
            dwell_ms = max(0, int(dwell_ms) if dwell_ms is not None else 0)
        except (TypeError, ValueError):
            dwell_ms = 0

        if et == "view_start":
            open_count += 1
            occurred = _ensure_aware(ev.get("occurred_at"))
            if occurred and occurred >= month_start and occurred <= now:
                day_key = occurred.date().isoformat()
                month_open_counts[day_key] += 1
                month_sessions[day_key].add(sid)
        elif et == "slide_advance":
            advance_count += 1
            per_slide_dwell[slide_index] += dwell_ms
            per_slide_sessions[slide_index].add(sid)
        elif et == "view_end":
            per_slide_dwell[slide_index] += dwell_ms
            per_slide_exits[slide_index] += 1
            per_slide_sessions[slide_index].add(sid)
        elif et == "completed":
            completed_sessions.add(sid)
            per_slide_dwell[slide_index] += dwell_ms
            per_slide_sessions[slide_index].add(sid)
        elif et == "heartbeat":
            per_slide_dwell[slide_index] += dwell_ms
            per_slide_sessions[slide_index].add(sid)
        elif et == "download":
            download_count += 1
        elif et in {"edit_started", "edit_saved"}:
            edit_count += 1
        elif et == "viewer_note_shown":
            note_shown_count += 1
        elif et == "viewer_note_dismissed":
            note_dismissed_count += 1
            note_dismissed_sessions.add(sid)

        email = (ev.get("viewer_email") or ev.get("identified_email") or "").strip().lower()
        if email:
            viewer_emails.add(email)

        occurred = _ensure_aware(ev.get("occurred_at"))
        if occurred and (latest_at is None or occurred > latest_at):
            latest_at = occurred

    n_sessions = len(sessions)

    # Per-session totals.
    session_dwells: list[int] = []
    session_summaries: list[dict[str, Any]] = []
    for sid, evs in sessions.items():
        dwell = sum(int(e.get("dwell_ms") or 0) for e in evs)
        session_dwells.append(dwell)
        # Identify the session's email, latest event, last slide.
        email = ""
        name = ""
        username = ""
        user_id = ""
        last_at: Optional[datetime] = None
        last_slide = 0
        for e in evs:
            em = (e.get("viewer_email") or e.get("identified_email") or "").strip().lower()
            if em:
                email = em
            nm = (e.get("viewer_name") or "").strip()
            if nm:
                name = nm
            un = (e.get("viewer_username") or "").strip()
            if un:
                username = un
            uid = (e.get("viewer_user_id") or "").strip()
            if uid:
                user_id = uid
            occurred = _ensure_aware(e.get("occurred_at"))
            if occurred and (last_at is None or occurred > last_at):
                last_at = occurred
            si = e.get("slide_index")
            try:
                if si is not None:
                    last_slide = int(si)
            except (TypeError, ValueError):
                pass
        session_summaries.append({
            "session_id": sid,
            "viewer_user_id": user_id or None,
            "viewer_name": name or None,
            "viewer_username": username or None,
            "viewer_email": email or None,
            "dwell_ms": dwell,
            "last_slide": last_slide,
            "last_event_at": last_at.isoformat() if last_at else None,
            "completed": sid in completed_sessions,
            "events": len(evs),
        })

    # Sort recent sessions to the top of the feed.
    session_summaries.sort(
        key=lambda s: s.get("last_event_at") or "",
        reverse=True,
    )

    # Slide attention map.
    slide_attention: list[dict[str, Any]] = []
    for idx in range(total_slides):
        slide_attention.append({
            "slide_index": idx,
            "sum_dwell_ms": int(per_slide_dwell.get(idx, 0)),
            "exits": int(per_slide_exits.get(idx, 0)),
            "sessions": len(per_slide_sessions.get(idx, set())),
        })

    strongest_slide = None
    biggest_dropoff_slide = None
    if any(s["sum_dwell_ms"] > 0 for s in slide_attention):
        strongest = max(slide_attention, key=lambda s: s["sum_dwell_ms"])
        strongest_slide = {
            "slide_index": strongest["slide_index"],
            "sum_dwell_ms": strongest["sum_dwell_ms"],
        }
    if any(s["exits"] > 0 for s in slide_attention):
        biggest = max(slide_attention, key=lambda s: s["exits"])
        biggest_dropoff_slide = {
            "slide_index": biggest["slide_index"],
            "exits": biggest["exits"],
        }

    # Ghost detector — sessions that opened but never advanced past
    # slide 0 within the ghost window. We look for ``view_start`` events
    # without any matching ``slide_advance`` from the same session, and
    # whose latest event is older than ghost_after_days days ago.
    ghost_threshold = now - timedelta(days=ghost_after_days)
    ghost_viewers: list[dict[str, Any]] = []
    ghost_session_ids: set[str] = set()
    for sid, evs in sessions.items():
        types = [e.get("event_type") for e in evs]
        if "view_start" not in types:
            continue
        if "slide_advance" in types:
            continue
        latest_session_at = None
        for e in evs:
            occ = _ensure_aware(e.get("occurred_at"))
            if occ and (latest_session_at is None or occ > latest_session_at):
                latest_session_at = occ
        if latest_session_at and latest_session_at <= ghost_threshold:
            email = ""
            for e in evs:
                em = (e.get("viewer_email") or e.get("identified_email") or "").strip().lower()
                if em:
                    email = em
                    break
            ghost_viewers.append({
                "session_id": sid,
                "viewer_email": email or None,
                "opened_at": latest_session_at.isoformat() if latest_session_at else None,
                "days_since_open": round(
                    (now - latest_session_at).total_seconds() / 86400.0, 1
                ),
            })
            ghost_session_ids.add(sid)

    avg_dwell_s = (
        round((sum(session_dwells) / 1000) / n_sessions, 2)
        if n_sessions else 0.0
    )
    median_dwell_s = round(_percentile(session_dwells, 50) / 1000.0, 2)
    completion_rate = (
        round(len(completed_sessions) / n_sessions, 3)
        if n_sessions else 0.0
    )
    last_viewed_hours_ago = None
    if latest_at:
        delta = now - latest_at
        last_viewed_hours_ago = round(delta.total_seconds() / 3600.0, 2)

    month_activity: list[dict[str, Any]] = []
    day_cursor = month_start.date()
    today = now.date()
    while day_cursor <= today:
        key = day_cursor.isoformat()
        month_activity.append({
            "date": key,
            "opens": int(month_open_counts.get(key, 0)),
            "sessions": len(month_sessions.get(key, set())),
        })
        day_cursor = day_cursor + timedelta(days=1)

    sufficient_signal = n_sessions >= min_sessions_for_signal
    viewer_segments = _segment_viewers(
        sessions=session_summaries,
        ghost_session_ids=ghost_session_ids,
        total_slides=total_slides,
    )
    viewer_note = {
        "shown": note_shown_count,
        "dismissed": note_dismissed_count,
        "dismissed_sessions": len(note_dismissed_sessions),
        "dismissal_rate": (
            round(note_dismissed_count / note_shown_count, 3)
            if note_shown_count else 0.0
        ),
    }
    action_insights = _build_action_insights(
        views=n_sessions,
        sufficient_signal=sufficient_signal,
        completion_rate=completion_rate,
        avg_dwell_s=avg_dwell_s,
        strongest_slide=strongest_slide,
        biggest_dropoff_slide=biggest_dropoff_slide,
        ghost_viewers=ghost_viewers,
        viewer_segments=viewer_segments,
        min_sessions_for_signal=min_sessions_for_signal,
        viewer_note=viewer_note,
    )

    return {
        "opens": open_count,
        "views": n_sessions,
        "unique_viewers": len(viewer_emails) if viewer_emails else n_sessions,
        "completed_sessions": len(completed_sessions),
        "completion_rate": completion_rate,
        "avg_dwell_seconds": avg_dwell_s,
        "median_dwell_seconds": median_dwell_s,
        "total_slides_viewed": advance_count,
        "downloads": download_count,
        "edits": edit_count,
        "viewer_note": viewer_note,
        "last_viewed_hours_ago": last_viewed_hours_ago,
        "strongest_slide": strongest_slide,
        "biggest_dropoff_slide": biggest_dropoff_slide,
        "slide_attention": slide_attention,
        "month_activity": {
            "month": now.strftime("%Y-%m"),
            "days": month_activity,
        },
        "viewer_sessions": session_summaries[:50],
        "ghost_viewers": ghost_viewers,
        "viewer_emails": sorted(viewer_emails),
        "viewer_segments": viewer_segments,
        "action_insights": action_insights,
        "sufficient_signal": sufficient_signal,
    }


def _segment_viewers(
    *,
    sessions: list[dict[str, Any]],
    ghost_session_ids: set[str],
    total_slides: int,
) -> dict[str, Any]:
    """Classify sessions from observed behavior only.

    Warm = completed, reached the last slide, or spent at least 60s.
    Cold = very short session with almost no activity.
    Ghost = opened days ago and never advanced.
    Everything else remains engaged. These labels are behavioral
    heuristics, not identity or intent claims.
    """
    counts = {"warm": 0, "engaged": 0, "cold": 0, "ghost": 0}
    classified: list[dict[str, Any]] = []
    last_slide_threshold = max(0, total_slides - 1)

    for session in sessions:
        sid = str(session.get("session_id") or "")
        dwell_ms = int(session.get("dwell_ms") or 0)
        events = int(session.get("events") or 0)
        last_slide = int(session.get("last_slide") or 0)
        completed = bool(session.get("completed"))

        if sid in ghost_session_ids:
            segment = "ghost"
            reason = "opened but never advanced after the ghost window"
        elif completed or last_slide >= last_slide_threshold or dwell_ms >= 60_000:
            segment = "warm"
            reason = "completed, reached the end, or spent at least 60 seconds"
        elif dwell_ms < 15_000 and events <= 2:
            segment = "cold"
            reason = "short session with minimal interaction"
        else:
            segment = "engaged"
            reason = "active session with some slide interaction"

        counts[segment] += 1
        classified.append({
            "session_id": sid,
            "viewer_email": session.get("viewer_email"),
            "viewer_name": session.get("viewer_name"),
            "viewer_username": session.get("viewer_username"),
            "viewer_user_id": session.get("viewer_user_id"),
            "segment": segment,
            "reason": reason,
            "dwell_ms": dwell_ms,
            "last_slide": last_slide,
            "completed": completed,
        })

    return {"counts": counts, "sessions": classified}


def _build_action_insights(
    *,
    views: int,
    sufficient_signal: bool,
    completion_rate: float,
    avg_dwell_s: float,
    strongest_slide: dict[str, Any] | None,
    biggest_dropoff_slide: dict[str, Any] | None,
    ghost_viewers: list[dict[str, Any]],
    viewer_segments: dict[str, Any],
    min_sessions_for_signal: int,
    viewer_note: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return deterministic next actions from observed analytics only."""
    insights: list[dict[str, Any]] = []

    if views < min_sessions_for_signal:
        insights.append({
            "id": "collect_more_signal",
            "question": "Is there enough signal to make a deck decision?",
            "answer": "No",
            "action": (
                f"Wait for at least {min_sessions_for_signal} viewer sessions before judging slide performance."
            ),
            "severity": "info",
            "evidence": {"views": views, "required_sessions": min_sessions_for_signal},
        })
        return insights

    warm_count = int((viewer_segments.get("counts") or {}).get("warm") or 0)
    cold_count = int((viewer_segments.get("counts") or {}).get("cold") or 0)

    if warm_count:
        insights.append({
            "id": "prioritize_warm_viewers",
            "question": "Which viewers should be followed up first?",
            "answer": "Warm viewers",
            "action": "Prioritize sessions that completed, reached the end, or spent at least 60 seconds.",
            "severity": "positive",
            "evidence": {"warm_sessions": warm_count},
        })

    if strongest_slide:
        insights.append({
            "id": "reuse_strongest_slide",
            "question": "Which slide appears to hold attention?",
            "answer": f"Slide {int(strongest_slide['slide_index']) + 1}",
            "action": "Use this slide as the anchor in follow-up messages and investor conversations.",
            "severity": "positive",
            "evidence": strongest_slide,
        })

    if biggest_dropoff_slide:
        insights.append({
            "id": "review_dropoff_slide",
            "question": "Where are viewers dropping?",
            "answer": f"Slide {int(biggest_dropoff_slide['slide_index']) + 1}",
            "action": "Review this slide for unclear copy, weak proof, heavy layout, or a premature ask.",
            "severity": "warning",
            "evidence": biggest_dropoff_slide,
        })

    if completion_rate < 0.5:
        insights.append({
            "id": "improve_completion",
            "question": "Are viewers reaching the end?",
            "answer": "Completion is below 50%",
            "action": "Shorten the path to the core proof and move the strongest evidence earlier.",
            "severity": "warning",
            "evidence": {"completion_rate": completion_rate},
        })

    if ghost_viewers:
        insights.append({
            "id": "follow_up_ghosts",
            "question": "Which viewers opened but went quiet?",
            "answer": f"{len(ghost_viewers)} ghost session(s)",
            "action": "Follow up only with identified viewers; keep anonymous sessions as aggregate signal.",
            "severity": "warning",
            "evidence": {"ghost_sessions": len(ghost_viewers)},
        })

    if cold_count and avg_dwell_s < 20:
        insights.append({
            "id": "tighten_opening",
            "question": "Is the opening holding attention?",
            "answer": "Early sessions are short",
            "action": "Tighten the first two slides and make the problem, traction, or proof visible sooner.",
            "severity": "warning",
            "evidence": {"cold_sessions": cold_count, "avg_dwell_seconds": avg_dwell_s},
        })

    note_shown = int(viewer_note.get("shown") or 0)
    note_dismissed = int(viewer_note.get("dismissed") or 0)
    dismissal_rate = float(viewer_note.get("dismissal_rate") or 0)
    if note_shown and dismissal_rate >= 0.5:
        insights.append({
            "id": "simplify_viewer_note",
            "question": "Is the viewer note helping or distracting?",
            "answer": "Many viewers hide the note",
            "action": "Shorten the note, make it one clear ask, or remove it from this share link if it interrupts reading.",
            "severity": "warning",
            "evidence": {
                "note_shown": note_shown,
                "note_dismissed": note_dismissed,
                "dismissal_rate": dismissal_rate,
            },
        })
    elif note_shown and dismissal_rate == 0 and completion_rate >= 0.5:
        insights.append({
            "id": "keep_viewer_note",
            "question": "Should this share note stay?",
            "answer": "No viewer has hidden it",
            "action": "Keep the note if it explains the ask or next step; continue watching completion and drop-off before changing it.",
            "severity": "positive",
            "evidence": {
                "note_shown": note_shown,
                "note_dismissed": note_dismissed,
                "completion_rate": completion_rate,
            },
        })

    return insights


def compare_versions(
    *,
    version_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Compare aggregated analytics across two or more share-link versions.

    ``version_results`` maps share_id (or label) → analytics payload.
    Returns a dict highlighting which version performed better on
    each axis. When fewer than 2 versions are supplied, returns
    ``{"sufficient_signal": False}``.
    """
    if len(version_results) < 2:
        return {"sufficient_signal": False, "reason": "need_at_least_2_versions"}

    axes = ("avg_dwell_seconds", "completion_rate", "median_dwell_seconds")
    best_per_axis: dict[str, dict[str, Any]] = {}
    for axis in axes:
        ranking = sorted(
            version_results.items(),
            key=lambda item: float(item[1].get(axis) or 0),
            reverse=True,
        )
        if not ranking:
            continue
        winner_id, winner_payload = ranking[0]
        best_per_axis[axis] = {
            "winner_share_id": winner_id,
            "winner_value": winner_payload.get(axis),
            "ranking": [
                {"share_id": sid, "value": payload.get(axis)}
                for sid, payload in ranking
            ],
        }

    return {
        "sufficient_signal": True,
        "best_per_axis": best_per_axis,
        "version_count": len(version_results),
    }
