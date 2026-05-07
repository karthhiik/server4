"""Tests for depth profile selection.

Plan 04 \u2014 see ``docs/founder-plans/04-research-freshness-and-tiering.md``.
"""

from __future__ import annotations

import pytest

from app.services.v4.research import DEPTH_PROFILES, profile_for, derive_profile_label


class TestDeriveProfileLabel:
    @pytest.mark.parametrize(
        "depth,expected",
        [("fast", "fast"), ("standard", "standard"), ("deep", "deep")],
    )
    def test_explicit_depth_wins(self, depth: str, expected: str) -> None:
        assert derive_profile_label(mode="standard", research_depth=depth) == expected

    def test_unknown_depth_falls_back_to_mode(self) -> None:
        # Unknown research_depth values must not silently downgrade
        # the deep tier.
        assert derive_profile_label(mode="premium", research_depth="banana") == "deep"
        assert derive_profile_label(mode="standard", research_depth="banana") == "standard"

    def test_premium_mode_default_deep(self) -> None:
        assert derive_profile_label(mode="premium") == "deep"

    def test_standard_mode_default_standard(self) -> None:
        assert derive_profile_label(mode="standard") == "standard"

    def test_other_mode_default_standard(self) -> None:
        # Non-premium modes default to standard — fast is reserved for
        # explicit follow-up calls inside the deep-research loop.
        assert derive_profile_label(mode="lite") == "standard"


class TestProfileFor:
    def test_fast_profile_shape(self) -> None:
        p = profile_for("standard", "fast")
        assert p.label == "fast"
        assert p.web_providers == ("tavily", "serper")
        assert p.news_providers == ("newsapi",)
        assert p.max_results_per_provider == 5
        assert p.per_provider_timeout_s == pytest.approx(4.0)
        assert p.enable_followup_loop is False
        assert p.enable_social is False
        assert p.enable_financial is False

    def test_standard_profile_shape(self) -> None:
        p = profile_for("standard")
        assert p.label == "standard"
        assert "exa" in p.web_providers
        assert p.news_providers == ("newsapi",)
        assert p.max_results_per_provider == 6
        assert p.per_provider_timeout_s == pytest.approx(6.0)
        assert p.enable_followup_loop is False

    def test_deep_profile_shape(self) -> None:
        p = profile_for("premium")
        assert p.label == "deep"
        assert set(p.web_providers) == {"tavily", "serper", "exa", "you_com", "jina"}
        assert set(p.news_providers) == {"newsapi", "newsdata", "guardian"}
        assert p.max_results_per_provider == 8
        assert p.per_provider_timeout_s == pytest.approx(10.0)
        assert p.enable_followup_loop is True
        assert p.enable_social is True
        assert p.enable_financial is True

    def test_registry_keys(self) -> None:
        assert set(DEPTH_PROFILES.keys()) == {"fast", "standard", "deep"}
