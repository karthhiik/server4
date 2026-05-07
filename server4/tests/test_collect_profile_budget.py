"""Tests for ``ResearchCollector.collect`` profile dispatch + recency floor.

Plan 04 \u2014 verifies that:
1. Each profile picks the right provider set.
2. Citations strictly older than ``recency.earliest`` are dropped.
3. Surviving citations are annotated with freshness/rank/staleness.
4. Top-citations sort uses ``rank_score`` (not lexical date string).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.services.v4.research import RecencyWindow, profile_for
from app.services.v4.research_collector import (
    Citation,
    ResearchCollector,
    ResearchPacket,
)


@pytest.fixture
def recency() -> RecencyWindow:
    today = date(2025, 6, 15)
    return RecencyWindow(
        earliest=today - timedelta(days=180),
        boost_after=today - timedelta(days=60),
        label="last_180d",
        decay_half_life_days=120,
    )


class TestApplyRecencyAndScore:
    def test_drops_citations_older_than_window(self, recency) -> None:
        items = [
            Citation(
                title="too old", url="http://a", snippet="", source="x",
                source_authority=0.9, published_at="2020-01-01",
            ),
            Citation(
                title="in window", url="http://b", snippet="", source="x",
                source_authority=0.5, published_at="2025-04-01",
            ),
        ]
        kept, dropped = ResearchCollector._apply_recency_and_score(
            items,
            recency=recency,
            now=datetime(2025, 6, 15, tzinfo=timezone.utc),
            today=date(2025, 6, 15),
        )
        assert dropped == 1
        assert len(kept) == 1
        assert kept[0].url == "http://b"

    def test_undated_citations_survive(self, recency) -> None:
        items = [
            Citation(
                title="undated", url="http://u", snippet="", source="x",
                source_authority=0.6, published_at=None,
            ),
        ]
        kept, dropped = ResearchCollector._apply_recency_and_score(
            items,
            recency=recency,
            now=datetime(2025, 6, 15, tzinfo=timezone.utc),
            today=date(2025, 6, 15),
        )
        assert dropped == 0
        assert kept[0].staleness == "undated"
        assert kept[0].rank_score > 0  # blended score still produced

    def test_sorted_by_rank_descending(self, recency) -> None:
        # Same authority, different freshness \u2014 newer should win.
        items = [
            Citation(
                title="older", url="http://o", snippet="", source="x",
                source_authority=0.7, published_at="2025-01-01",
            ),
            Citation(
                title="newer", url="http://n", snippet="", source="x",
                source_authority=0.7, published_at="2025-06-01",
            ),
        ]
        kept, _ = ResearchCollector._apply_recency_and_score(
            items,
            recency=recency,
            now=datetime(2025, 6, 15, tzinfo=timezone.utc),
            today=date(2025, 6, 15),
        )
        assert kept[0].url == "http://n"
        assert kept[0].rank_score > kept[1].rank_score


class TestProfileBudget:
    def test_fast_profile_provider_lists(self) -> None:
        p = profile_for("standard", "fast")
        assert "exa" not in p.web_providers
        assert "you_com" not in p.web_providers
        assert p.news_providers == ("newsapi",)

    def test_standard_profile_includes_exa(self) -> None:
        p = profile_for("standard")
        assert "exa" in p.web_providers
        assert "you_com" not in p.web_providers
        assert "jina" not in p.web_providers

    def test_deep_profile_full_suite(self) -> None:
        p = profile_for("premium")
        assert {"tavily", "serper", "exa", "you_com", "jina"} <= set(p.web_providers)
        assert {"newsapi", "newsdata", "guardian"} <= set(p.news_providers)


class TestTopCitationsRanking:
    def test_top_citations_uses_rank_score(self) -> None:
        # rank_score should beat plain authority + lexical date sort.
        c_old_high = Citation(
            title="auth", url="http://a", snippet="", source="x",
            source_authority=0.9, rank_score=0.4,
        )
        c_new_low = Citation(
            title="fresh", url="http://b", snippet="", source="x",
            source_authority=0.4, rank_score=0.8,
        )
        packet = ResearchPacket(
            query="q",
            industry=None,
            company_name=None,
            citations=[c_old_high, c_new_low],
            news_citations=[],
            financial_data={},
            social_signals={},
            duration_ms=0,
        )
        top = packet.top_citations(n=2)
        assert top[0].url == "http://b"
        assert top[1].url == "http://a"

    def test_top_citations_falls_back_to_authority_when_rank_zero(self) -> None:
        # Direct ResearchPacket constructions (no collector) keep working.
        c1 = Citation(title="a", url="http://a", snippet="", source="x",
                      source_authority=0.9)
        c2 = Citation(title="b", url="http://b", snippet="", source="x",
                      source_authority=0.5)
        packet = ResearchPacket(
            query="q",
            industry=None,
            company_name=None,
            citations=[c2, c1],
            news_citations=[],
            financial_data={},
            social_signals={},
            duration_ms=0,
        )
        top = packet.top_citations(n=2)
        assert top[0].url == "http://a"

    def test_prompt_context_exposes_staleness_and_freshness(self) -> None:
        citation = Citation(
            title="Fresh market signal",
            url="https://reuters.com/markets/example",
            snippet="Recent pricing and adoption data",
            source="newsapi",
            source_authority=0.95,
            freshness=0.87,
            rank_score=0.91,
            staleness="fresh",
        )
        packet = ResearchPacket(
            query="q",
            industry=None,
            company_name=None,
            citations=[citation],
            news_citations=[],
            financial_data={},
            social_signals={},
            duration_ms=0,
        )

        context = packet.as_prompt_context()

        assert "staleness=fresh" in context
        assert "freshness=0.87" in context
        assert "Fresh market signal" in context
