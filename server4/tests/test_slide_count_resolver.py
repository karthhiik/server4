"""Tests for ``app.services.v4.slide_count_resolver``.

Plan 02 (Slide Count Bug v2) — see ``docs/founder-plans/02-slide-count-bug.md``.
"""

from __future__ import annotations

import pytest

from app.services.v4.slide_count_resolver import resolve_requested_count


class TestUserExplicit:
    def test_user_value_takes_priority_over_analyzer(self) -> None:
        assert (
            resolve_requested_count(
                user_supplied=15,
                analyzer_suggested=10,
                purpose="pitch_deck",
                mode="standard",
            )
            == 15
        )

    def test_user_value_takes_priority_over_purpose_default(self) -> None:
        assert (
            resolve_requested_count(
                user_supplied=3,
                analyzer_suggested=None,
                purpose="pitch_deck",
                mode="premium",
            )
            == 3
        )

    @pytest.mark.parametrize("supplied,expected", [(0, 1), (-3, 1), (51, 50), (999, 50)])
    def test_user_value_is_clamped(self, supplied: int, expected: int) -> None:
        assert (
            resolve_requested_count(
                user_supplied=supplied,
                analyzer_suggested=None,
                purpose="pitch_deck",
                mode="standard",
            )
            == expected
        )


class TestAnalyzerSuggested:
    def test_analyzer_used_when_user_is_none(self) -> None:
        assert (
            resolve_requested_count(
                user_supplied=None,
                analyzer_suggested=14,
                purpose="pitch_deck",
                mode="standard",
            )
            == 14
        )

    def test_analyzer_value_is_clamped(self) -> None:
        assert (
            resolve_requested_count(
                user_supplied=None,
                analyzer_suggested=99,
                purpose="pitch_deck",
                mode="standard",
            )
            == 50
        )


class TestPurposeDefault:
    @pytest.mark.parametrize(
        "purpose,expected",
        [
            ("pitch_deck", 12),
            ("sales_deck", 7),
            ("internal_memo", 5),
            ("training", 8),
            ("case_study", 9),
            ("company_overview", 10),
            ("conference_talk", 12),
        ],
    )
    def test_purpose_default(self, purpose: str, expected: int) -> None:
        assert (
            resolve_requested_count(
                user_supplied=None,
                analyzer_suggested=None,
                purpose=purpose,
                mode="standard",
            )
            == expected
        )


class TestModeDefault:
    def test_premium_default_when_purpose_unknown(self) -> None:
        assert (
            resolve_requested_count(
                user_supplied=None,
                analyzer_suggested=None,
                purpose="completely_unknown_purpose",
                mode="premium",
            )
            == 10
        )

    def test_standard_default_when_purpose_unknown(self) -> None:
        assert (
            resolve_requested_count(
                user_supplied=None,
                analyzer_suggested=None,
                purpose="completely_unknown_purpose",
                mode="standard",
            )
            == 8
        )


class TestHardDefault:
    def test_returns_int_when_everything_is_none(self) -> None:
        result = resolve_requested_count(
            user_supplied=None,
            analyzer_suggested=None,
            purpose=None,
            mode=None,
        )
        assert isinstance(result, int)
        assert 1 <= result <= 50


class TestNeverReturnsNone:
    @pytest.mark.parametrize(
        "u,a,p,m",
        [
            (None, None, None, None),
            (None, None, "pitch_deck", None),
            (None, None, None, "premium"),
            (None, 10, None, None),
            (5, None, None, None),
        ],
    )
    def test_always_returns_int(self, u, a, p, m) -> None:
        result = resolve_requested_count(
            user_supplied=u,
            analyzer_suggested=a,
            purpose=p,
            mode=m,
        )
        assert isinstance(result, int)
        assert 1 <= result <= 50
