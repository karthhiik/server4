"""Tests for the recency window resolver and query-now signal.

Plan 04 \u2014 see ``docs/founder-plans/04-research-freshness-and-tiering.md``.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.services.v4.research import (
    RecencyWindow,
    query_signals_now,
    resolve_recency_window,
)


class TestQuerySignalsNow:
    @pytest.mark.parametrize(
        "text",
        [
            "current AI market size",
            "today's funding round",
            "latest customer numbers",
            "real-time monitoring",
            "live conference talk",
            "this week in robotics",
            "Q3 2025 earnings",
            "FY 2026 outlook",
            "2027 roadmap",
        ],
    )
    def test_now_markers_detected(self, text: str) -> None:
        assert query_signals_now(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "history of computing",
            "long-term strategy",
            "the printing press",
            "",
        ],
    )
    def test_non_now_text_rejected(self, text: str) -> None:
        assert query_signals_now(text) is False

    def test_none_input_returns_false(self) -> None:
        assert query_signals_now(None) is False  # type: ignore[arg-type]


class TestResolveRecencyWindow:
    _TODAY = date(2025, 6, 15)

    def test_query_now_overrides_purpose(self) -> None:
        # Even a "loose" purpose collapses to ~180d when the query
        # itself is asking about the present.
        w = resolve_recency_window(
            purpose="case_study",
            user_query="current market leaders",
            today=self._TODAY,
        )
        assert w.label == "last_180d"
        assert (self._TODAY - w.earliest).days == 180
        assert w.decay_half_life_days == 120

    def test_tight_purpose_one_year(self) -> None:
        w = resolve_recency_window(
            purpose="pitch_deck",
            user_query="our company story",
            today=self._TODAY,
        )
        assert w.label == "last_365d"
        assert (self._TODAY - w.earliest).days == 365

    def test_medium_purpose_two_years(self) -> None:
        w = resolve_recency_window(
            purpose="company_overview",
            user_query="our story",
            today=self._TODAY,
        )
        assert w.label == "last_2y"
        assert (self._TODAY - w.earliest).days == 365 * 2

    def test_loose_purpose_three_years(self) -> None:
        w = resolve_recency_window(
            purpose="educational",
            user_query="history of compilers",
            today=self._TODAY,
        )
        assert w.label == "last_3y"
        assert (self._TODAY - w.earliest).days == 365 * 3

    def test_unknown_purpose_defaults_two_years(self) -> None:
        w = resolve_recency_window(
            purpose="banana",
            user_query="x",
            today=self._TODAY,
        )
        assert w.label == "last_2y"

    def test_purpose_enum_prefix_stripped(self) -> None:
        # Emit-friendly: pydantic enums dump as "PresentationPurpose.pitch_deck"
        w = resolve_recency_window(
            purpose="PresentationPurpose.pitch_deck",
            user_query="x",
            today=self._TODAY,
        )
        assert w.label == "last_365d"

    def test_days_back_is_capped_at_365(self) -> None:
        w = resolve_recency_window(
            purpose="educational",
            user_query="history of x",
            today=self._TODAY,
        )
        # days_back caps at 365 even for a 3-year window so providers
        # like Tavily don't silently truncate.
        assert w.days_back() == 365

    def test_days_back_floors_at_one(self) -> None:
        # Ridiculously tight window via direct construction.
        w = RecencyWindow(
            earliest=self._TODAY,
            boost_after=self._TODAY,
            label="zero",
            decay_half_life_days=30,
        )
        assert w.days_back(today=self._TODAY) == 1
