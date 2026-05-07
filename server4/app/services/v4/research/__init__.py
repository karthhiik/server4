"""V4 research subpackage: recency contract + depth profiles.

This subpackage carries the freshness/tiering primitives consumed by
``research_collector.py`` and ``deep_research.py``. Modules are pure
(no I/O, no global state) so they are trivially unit-testable.
"""

from app.services.v4.research.recency import (
    RecencyWindow,
    query_signals_now,
    resolve_recency_window,
    freshness_score,
    combined_score,
    staleness_label,
    parse_iso_datetime,
)
from app.services.v4.research.depth_profiles import (
    DepthProfile,
    DEPTH_PROFILES,
    profile_for,
    derive_profile_label,
)

__all__ = [
    "RecencyWindow",
    "query_signals_now",
    "resolve_recency_window",
    "freshness_score",
    "combined_score",
    "staleness_label",
    "parse_iso_datetime",
    "DepthProfile",
    "DEPTH_PROFILES",
    "profile_for",
    "derive_profile_label",
]
