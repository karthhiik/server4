"""Unit tests for the v12.1 deep_research iterative loop.

The loop itself is tested with a fake ResearchCollector (no network)
so we can verify gap analysis, follow-up query generation, and
packet-merging logic deterministically.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pytest

from app.services.v4.deep_research import (
    DeepResearchLoop,
    _analyze_gaps,
    _build_followup_queries,
    _has_recent_news,
    _merge_packets,
)
from app.services.v4.research_collector import Citation, ResearchPacket


# ── Fixtures ─────────────────────────────────────────────────────

def _rich_packet() -> ResearchPacket:
    return ResearchPacket(
        query="acme",
        industry="fintech",
        company_name="Acme",
        citations=[
            Citation(
                title="Acme raises $24M Series A",
                url="https://techcrunch.com/acme-series-a",
                snippet="Acme closed a $24M round at a $200M valuation competitors include Stripe.",
                source="tavily",
                source_authority=0.95,
            ),
            Citation(
                title="Fintech market CAGR 18% through 2028",
                url="https://gartner.com/fintech-2025",
                snippet="The total addressable market is $420B growing 18% annually.",
                source="serper",
                source_authority=0.95,
            ),
        ],
        news_citations=[
            Citation(
                title="Acme launches product in Europe",
                url="https://reuters.com/acme-eu",
                snippet="Acme expands ARR to $5M with 120 customers.",
                source="newsapi",
                source_authority=0.95,
                published_at=datetime.now(timezone.utc).isoformat(),
            ),
        ],
        financial_data={"revenue_ttm_usd": 5_000_000},
        social_signals={},
        duration_ms=1200,
    )


def _thin_packet() -> ResearchPacket:
    """Packet missing everything the gap-analyzer cares about."""
    return ResearchPacket(
        query="obscure topic",
        industry=None,
        company_name=None,
        citations=[
            Citation(
                title="A general overview of the topic",
                url="https://example.com/a",
                snippet="This is a general description of the topic area.",
                source="tavily",
                source_authority=0.5,
            ),
        ],
        news_citations=[],
        financial_data={},
        social_signals={},
        duration_ms=1000,
    )


# ── Gap analysis ─────────────────────────────────────────────────

def test_rich_packet_has_no_gaps() -> None:
    gaps = _analyze_gaps(_rich_packet())
    assert gaps == []


def test_thin_packet_detects_all_gaps() -> None:
    gaps = _analyze_gaps(_thin_packet())
    assert "market_size" in gaps
    assert "competitor" in gaps
    assert "traction" in gaps
    assert "recent_news" in gaps
    assert "financial" in gaps


def test_has_recent_news_with_fresh_date() -> None:
    packet = _rich_packet()
    assert _has_recent_news(packet) is True


def test_has_recent_news_with_old_dates() -> None:
    packet = _rich_packet()
    # Overwrite all news to be 2 years old.
    old = (datetime.now(timezone.utc) - timedelta(days=720)).isoformat()
    for c in packet.news_citations:
        c.published_at = old
    assert _has_recent_news(packet) is False


# ── Follow-up query generation ───────────────────────────────────

def test_followups_include_anchor_and_keywords() -> None:
    qs = _build_followup_queries(
        base_query="fintech pitch",
        industry="fintech",
        company_name="Acme",
        gaps=["market_size", "competitor", "traction", "recent_news", "financial"],
    )
    assert len(qs) == 5
    assert all("Acme" in q for _, q in qs)
    kinds = {gap for gap, _ in qs}
    assert kinds == {"market_size", "competitor", "traction", "recent_news", "financial"}
    # market_size query mentions TAM
    market_q = next(q for g, q in qs if g == "market_size")
    assert "TAM" in market_q or "market" in market_q.lower()


def test_followups_empty_when_no_gaps() -> None:
    assert _build_followup_queries("x", None, None, []) == []


# ── Packet merging ───────────────────────────────────────────────

def test_merge_dedupes_by_url() -> None:
    a = _rich_packet()
    b = _rich_packet()  # identical URLs
    merged = _merge_packets(a, [b])
    assert len(merged.citations) == len(a.citations)
    assert len(merged.news_citations) == len(a.news_citations)


def test_merge_adds_new_citations() -> None:
    a = _rich_packet()
    b = ResearchPacket(
        query="q", industry=None, company_name=None,
        citations=[Citation(
            title="New competitor analysis",
            url="https://bloomberg.com/new-piece",
            snippet="new info",
            source="exa", source_authority=0.95,
        )],
        news_citations=[],
        financial_data={"runway_months": 18},
        social_signals={},
        duration_ms=300,
    )
    merged = _merge_packets(a, [b])
    assert len(merged.citations) == len(a.citations) + 1
    assert merged.financial_data["runway_months"] == 18
    # Base financial data still present
    assert "revenue_ttm_usd" in merged.financial_data


# ── End-to-end loop with fake collector ───────────────────────────

class _FakeCollector:
    def __init__(self, initial: ResearchPacket, followup: Optional[ResearchPacket] = None):
        self.initial = initial
        self.followup = followup or ResearchPacket(
            query="fu", industry=None, company_name=None,
            citations=[Citation(
                title="Market size fintech",
                url=f"https://followup/{id(self)}",
                snippet="The TAM is $420B growing at 18% CAGR.",
                source="tavily", source_authority=0.8,
            )],
            news_citations=[], financial_data={}, social_signals={}, duration_ms=250,
        )
        self.call_count = 0
        self.last_mode = None

    async def collect(self, query: str, industry=None, company_name=None, mode="standard",
                      research_depth=None, profile=None, recency=None, purpose=None) -> ResearchPacket:
        self.call_count += 1
        self.last_mode = mode
        if self.call_count == 1:
            return self.initial
        return self.followup


@pytest.mark.asyncio
async def test_standard_mode_skips_expansion() -> None:
    collector = _FakeCollector(_thin_packet())
    loop = DeepResearchLoop(collector=collector)  # type: ignore[arg-type]
    packet = await loop.run(
        user_query="anything",
        mode="standard",
    )
    # Only the seed call
    assert collector.call_count == 1
    assert packet is collector.initial


@pytest.mark.asyncio
async def test_premium_mode_expands_on_thin_packet() -> None:
    collector = _FakeCollector(_thin_packet())
    loop = DeepResearchLoop(collector=collector)  # type: ignore[arg-type]
    packet = await loop.run(
        user_query="obscure topic",
        company_name="TestCo",
        mode="premium",
        research_depth="deep",
    )
    # Seed + at least one follow-up
    assert collector.call_count > 1
    # Merged packet has more citations than seed
    assert len(packet.citations) > len(collector.initial.citations)


@pytest.mark.asyncio
async def test_premium_mode_skips_when_no_gaps() -> None:
    collector = _FakeCollector(_rich_packet())
    loop = DeepResearchLoop(collector=collector)  # type: ignore[arg-type]
    packet = await loop.run(
        user_query="acme",
        company_name="Acme",
        mode="premium",
        research_depth="deep",
    )
    # Only seed — rich packet has no gaps
    assert collector.call_count == 1
    assert packet is collector.initial


@pytest.mark.asyncio
async def test_emit_callback_receives_stages() -> None:
    events: list[tuple[str, dict]] = []

    async def emit(stage: str, payload: dict) -> None:
        events.append((stage, payload))

    collector = _FakeCollector(_thin_packet())
    loop = DeepResearchLoop(collector=collector)  # type: ignore[arg-type]
    await loop.run(
        user_query="test",
        company_name="TestCo",
        mode="premium",
        research_depth="deep",
        emit=emit,
    )
    stages = [s for s, _ in events]
    assert "deep_research_gaps" in stages
    assert "deep_research_expansion_started" in stages
    assert "deep_research_expansion_complete" in stages
