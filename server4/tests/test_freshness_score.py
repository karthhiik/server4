"""Tests for ``freshness_score`` and ``combined_score``.

Plan 04 \u2014 exponential decay + authority blend.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.services.v4.research import (
    RecencyWindow,
    combined_score,
    freshness_score,
    staleness_label,
)
from app.services.v4.research.recency import _UNDATED_FRESHNESS


_NOW = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


class TestFreshnessScore:
    def test_today_is_one(self) -> None:
        assert freshness_score(_NOW.isoformat(), now=_NOW) == pytest.approx(1.0, abs=1e-6)

    def test_one_half_life_drops_to_half(self) -> None:
        published = (_NOW - timedelta(days=180)).isoformat()
        assert freshness_score(published, now=_NOW, half_life_days=180) == pytest.approx(0.5, abs=1e-6)

    def test_two_half_lives_quarter(self) -> None:
        published = (_NOW - timedelta(days=360)).isoformat()
        assert freshness_score(published, now=_NOW, half_life_days=180) == pytest.approx(0.25, abs=1e-6)

    def test_undated_returns_baseline(self) -> None:
        assert freshness_score(None, now=_NOW) == _UNDATED_FRESHNESS
        assert freshness_score("", now=_NOW) == _UNDATED_FRESHNESS

    def test_unparseable_returns_baseline(self) -> None:
        assert freshness_score("not-a-date", now=_NOW) == _UNDATED_FRESHNESS

    def test_future_date_clamped_to_one(self) -> None:
        future = (_NOW + timedelta(days=10)).isoformat()
        assert freshness_score(future, now=_NOW) == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.parametrize(
        "raw",
        [
            "2025-06-15T12:00:00Z",
            "2025-06-15T12:00:00+00:00",
            "2025-06-15",
            "Sun, 15 Jun 2025 12:00:00 GMT",
        ],
    )
    def test_iso_variants_accepted(self, raw: str) -> None:
        # All four formats represent the same instant; freshness = 1.
        score = freshness_score(raw, now=_NOW, half_life_days=365)
        assert 0.99 <= score <= 1.0


class TestCombinedScore:
    def test_default_weight_blend(self) -> None:
        # authority=0.8, freshness=0.5 with default weight=0.45 \u2192
        # 0.55*0.8 + 0.45*0.5 = 0.665
        published = (_NOW - timedelta(days=180)).isoformat()
        assert combined_score(
            source_authority=0.8,
            published_at=published,
            now=_NOW,
            half_life_days=180,
        ) == pytest.approx(0.665, abs=1e-6)

    def test_pure_authority_when_weight_zero(self) -> None:
        published = (_NOW - timedelta(days=1000)).isoformat()
        assert combined_score(
            source_authority=0.7,
            published_at=published,
            now=_NOW,
            half_life_days=180,
            recency_weight=0.0,
        ) == pytest.approx(0.7, abs=1e-6)


class TestStalenessLabel:
    def test_undated(self) -> None:
        window = RecencyWindow(
            earliest=date(2024, 1, 1),
            boost_after=date(2025, 1, 1),
            label="last_2y",
            decay_half_life_days=365,
        )
        assert staleness_label(None, window=window, today=_NOW.date()) == "undated"

    def test_fresh_within_boost(self) -> None:
        window = RecencyWindow(
            earliest=date(2024, 1, 1),
            boost_after=date(2025, 5, 1),
            label="last_2y",
            decay_half_life_days=365,
        )
        published = "2025-06-01"
        assert staleness_label(published, window=window, today=_NOW.date()) == "fresh"

    def test_aging_between_earliest_and_boost(self) -> None:
        window = RecencyWindow(
            earliest=date(2024, 1, 1),
            boost_after=date(2025, 5, 1),
            label="last_2y",
            decay_half_life_days=365,
        )
        assert staleness_label("2024-08-01", window=window, today=_NOW.date()) == "aging"

    def test_stale_before_earliest(self) -> None:
        window = RecencyWindow(
            earliest=date(2024, 1, 1),
            boost_after=date(2025, 5, 1),
            label="last_2y",
            decay_half_life_days=365,
        )
        assert staleness_label("2020-08-01", window=window, today=_NOW.date()) == "stale"
