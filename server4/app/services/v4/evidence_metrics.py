"""Slice 3 (Provider-Failure Visibility) — evidence-density metrics.

Computes a small, deterministic verdict from a ResearchPacket so the
generation router can persist it on the deck and the frontend can show
a non-blocking warning when research silently degraded.

The contract (additive only — never raises):

    compute_evidence_metrics(research_packet, mode) -> {
        "failed_providers": list[str],     # providers that returned 0 useful
                                           #   citations or raised
        "degraded_evidence": bool,         # True when any of:
                                           #   * len(failed_providers) >= 2
                                           #   * evidence_density < 0.5
                                           #   * total citations == 0
        "evidence_density": float,         # in [0, 1] — kept_citations / target
        "provider_summary": dict[str, dict],  # echoed from the packet, safe-copied
    }

Targets per mode:
    standard -> 8 kept citations
    premium  -> 20 kept citations

Unknown / empty modes fall back to the standard target.

Why this lives in its own module:
    * keeps content_pipeline.py focused on orchestration
    * keeps this helper trivially unit-testable with SimpleNamespace
      fakes (no need to import the full pipeline)
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

import structlog

logger = structlog.get_logger(__name__)


# Per-mode citation targets. Picked to match what the writer prompts
# already saturate: standard mode injects ~6-8 top citations into prompts,
# premium injects up to ~20 across deck-level + per-slide research.
_MODE_TARGETS: dict[str, int] = {
    "standard": 8,
    "premium": 20,
}
_DEFAULT_TARGET = 8

# Density thresholds. ``degraded`` triggers when the deck visibly under-
# saturates its target.
_DEGRADED_DENSITY = 0.5
# A provider is "failed" for surfacing purposes when it raised or
# returned zero citations (status "failed" or "empty").
_FAILED_STATES = frozenset({"failed", "empty"})
# Two or more failed providers makes the deck noticeably partial even
# when the kept-citation count is otherwise above the floor (e.g. one
# strong provider carrying the rest of a fan-out).
_DEGRADED_FAILED_PROVIDER_COUNT = 2


def _target_for_mode(mode: Optional[str]) -> int:
    """Pick a citation target for the mode.

    Unknown/empty/None modes fall back to the standard target so older
    callers and edge cases (e.g. mode resolved late in the pipeline)
    never raise here.
    """
    if not mode:
        return _DEFAULT_TARGET
    return _MODE_TARGETS.get(str(mode).strip().lower(), _DEFAULT_TARGET)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_provider_entry(entry: Any) -> dict[str, Any]:
    """Coerce a provider summary entry to a JSON-safe dict.

    Tolerates missing keys, non-dict shapes, and odd types so the
    metrics call can never blow up on a malformed packet.
    """
    if not isinstance(entry, Mapping):
        return {"status": "unknown", "citation_count": 0, "latency_ms": 0}
    out: dict[str, Any] = {
        "status": str(entry.get("status") or "unknown"),
        "citation_count": _safe_int(entry.get("citation_count"), 0),
        "latency_ms": _safe_int(entry.get("latency_ms"), 0),
    }
    failure_reason = entry.get("failure_reason")
    if failure_reason:
        out["failure_reason"] = str(failure_reason)[:200]
    return out


def _kept_citation_count(research_packet: Any) -> int:
    """Count citations that survived ranking + recency filtering."""
    citations = getattr(research_packet, "citations", None) or []
    news = getattr(research_packet, "news_citations", None) or []
    try:
        return len(citations) + len(news)
    except TypeError:
        return 0


def compute_evidence_metrics(
    research_packet: Any,
    mode: Optional[str] = None,
) -> dict[str, Any]:
    """Derive a small evidence-quality verdict from a ResearchPacket.

    Never raises. Returns sensible defaults if ``research_packet`` is
    None or missing fields. The output is JSON-serializable.
    """
    target = _target_for_mode(mode)

    raw_summary: Mapping[str, Any] = {}
    if research_packet is not None:
        candidate = getattr(research_packet, "provider_summary", None)
        if isinstance(candidate, Mapping):
            raw_summary = candidate

    provider_summary: dict[str, dict[str, Any]] = {}
    failed_providers: list[str] = []
    for name, entry in raw_summary.items():
        coerced = _coerce_provider_entry(entry)
        provider_summary[str(name)] = coerced
        if coerced.get("status") in _FAILED_STATES:
            failed_providers.append(str(name))
    # Deterministic ordering — keeps Mongo writes diff-friendly and
    # frontend rendering stable across reloads.
    failed_providers.sort()

    kept = _kept_citation_count(research_packet)
    if target <= 0:
        density = 0.0
    else:
        density = min(1.0, kept / float(target))
    if kept == 0:
        density = 0.0

    degraded = (
        len(failed_providers) >= _DEGRADED_FAILED_PROVIDER_COUNT
        or density < _DEGRADED_DENSITY
        or kept == 0
    )

    metrics = {
        "failed_providers": failed_providers,
        "degraded_evidence": bool(degraded),
        "evidence_density": round(float(density), 4),
        "provider_summary": provider_summary,
    }

    logger.info(
        "v4_evidence_metrics",
        mode=mode,
        target=target,
        kept=kept,
        density=metrics["evidence_density"],
        n_failed_providers=len(failed_providers),
        degraded=metrics["degraded_evidence"],
    )

    return metrics


__all__ = ["compute_evidence_metrics"]
