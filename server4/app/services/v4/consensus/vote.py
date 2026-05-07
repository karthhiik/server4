"""
V4 Consensus — voting / merging utilities.

Based on Du et al. 2023 "Improving Factuality and Reasoning in Language
Models through Multiagent Debate" (arxiv:2305.14325) "most_frequent" pattern:
when multiple agents produce answers, pick the modal response for structured
fields. For free-form text we fall back to a model-driven aggregator (see
panel.py) because majority voting is meaningless on prose.

Also provides token-weighted merging primitives used by the premium debate
round to blend complementary drafts.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Iterable, Optional


def _norm_key(v: Any) -> str:
    """Stable canonical key for counting equality."""
    if v is None:
        return "∅"
    if isinstance(v, str):
        return " ".join(v.strip().lower().split())
    if isinstance(v, (int, float, bool)):
        return f"{type(v).__name__}:{v}"
    if isinstance(v, (list, tuple)):
        return "[" + "|".join(_norm_key(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + "|".join(
            f"{k}={_norm_key(v[k])}" for k in sorted(v.keys())
        ) + "}"
    return str(v)


def most_frequent(
    drafts: Iterable[dict[str, Any]],
    field: str,
    *,
    key_fn: Optional[Callable[[Any], str]] = None,
) -> tuple[Any, int, int]:
    """Return (winning_value, count, total_voters) for ``field`` across drafts.

    Equivalent to Du et al.'s consensus by majority vote. Ties are broken by
    first-seen order (stable). ``key_fn`` overrides the normalization used to
    group values — useful when you want case-preserving text with
    case-insensitive voting.
    """
    values: list[Any] = []
    keys: list[str] = []
    for d in drafts:
        if not isinstance(d, dict):
            continue
        v = d.get(field)
        if v is None or v == "":
            continue
        values.append(v)
        keys.append((key_fn or _norm_key)(v))

    if not values:
        return None, 0, 0

    counts = Counter(keys)
    winner_key, win_count = counts.most_common(1)[0]
    # return the *first* original value that produced the winning key
    for v, k in zip(values, keys):
        if k == winner_key:
            return v, win_count, len(values)
    return values[0], win_count, len(values)


def quorum_reached(
    drafts: list[dict[str, Any]],
    min_drafters: int = 2,
) -> bool:
    """True when we have at least ``min_drafters`` non-empty drafts."""
    return sum(1 for d in drafts if isinstance(d, dict) and d) >= min_drafters


def weighted_merge(
    drafts: list[dict[str, Any]],
    weights: Optional[list[float]] = None,
    *,
    fields: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Merge N drafts by taking the highest-weighted non-empty value per field.

    When ``weights`` is omitted, we use 1.0 each. When two drafts tie, the
    earlier draft wins (treat as primary). This is a deterministic fallback
    used when the aggregator model fails — guarantees *something* ships.
    """
    if not drafts:
        return {}
    if weights is None or len(weights) != len(drafts):
        weights = [1.0] * len(drafts)

    # Collect the superset of field names (preserve first-seen order)
    seen: list[str] = []
    seen_set: set[str] = set()
    for d in drafts:
        if not isinstance(d, dict):
            continue
        for k in d.keys():
            if k not in seen_set:
                seen.append(k)
                seen_set.add(k)
    keys = fields or seen

    out: dict[str, Any] = {}
    for field in keys:
        best_val: Any = None
        best_w: float = -1.0
        for d, w in zip(drafts, weights):
            if not isinstance(d, dict):
                continue
            v = d.get(field)
            if v in (None, "", [], {}):
                continue
            if w > best_w:
                best_val = v
                best_w = w
        if best_val is not None:
            out[field] = best_val
    return out


def agreement_ratio(drafts: list[dict[str, Any]], field: str) -> float:
    """Return winning_count / total for ``field`` — 0..1. Used as a quality
    signal: a field where all drafters agree is more trustworthy than one
    where every drafter returned something different."""
    _, count, total = most_frequent(drafts, field)
    if total == 0:
        return 0.0
    return count / total
