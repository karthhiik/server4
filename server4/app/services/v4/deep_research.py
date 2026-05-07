"""
V4 Deep Research Loop — iterative gap-driven research for premium decks.

Pattern (from dzhng/deep-research and AnotiaWang/deep-research-web-ui):
    Single-shot search returns 15-30 citations for one query. For a pitch
    deck that's enough ~70% of the time; the other 30% the deck wants
    specific evidence the planner never asks for — competitor pricing,
    CAGR for an adjacent market, a founder quote, a recent funding round.

This module runs the research in two (capped) phases:

    Phase 1 — seed
        Call `ResearchCollector.collect(user_query)`. Accept whatever
        comes back. This is the normal, single-shot baseline that
        standard mode also uses.

    Phase 2 — gap expansion
        Deterministically (no LLM) scan the packet for missing evidence
        classes:
            * market_size      — is there a $/%/B/M token in any citation?
            * competitor       — do citations mention competitors by name?
            * traction         — is there ARR / MRR / users / deployment data?
            * recent_news      — any news citations dated in the last 6 months?
            * financial        — any financial_data populated?
        Each missing class spawns ONE follow-up search. Queries are
        templated (no LLM round-trip) so we keep the 30s time budget
        realistic. The follow-ups fan out in parallel via
        ResearchCollector (depth="fast") and the merged packet replaces
        the original.

    Hard caps:
        - Max 1 expansion phase (≤6 parallel follow-up queries).
        - Total wall-clock budget 22s INCLUDING phase 1.
        - If phase 1 already satisfies all gaps, phase 2 is skipped.
        - If phase 2 times out, we return phase-1 packet unchanged — the
          pipeline must never block on deep research.

Public API:

    loop = DeepResearchLoop(collector=ResearchCollector())
    packet = await loop.run(
        user_query=...,
        industry=...,
        company_name=...,
        mode="premium",
        research_depth="deep",
        emit=emit,          # optional ProgressCallback
    )

Returns the SAME `ResearchPacket` type as `ResearchCollector.collect`,
so every downstream consumer (skeleton_planner, parallel_writer,
critic_engine, numeric_grounder) works without modification.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import replace as dc_replace
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Iterable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.v4.research import DepthProfile, RecencyWindow

import structlog

from app.services.v4.research_collector import (
    Citation,
    ResearchCollector,
    ResearchPacket,
)

logger = structlog.get_logger(__name__)


ProgressEmit = Callable[[str, dict[str, Any]], Awaitable[None]]


# Total wall-clock budget for the whole loop. `mode="premium"` already
# gets 8-12s for the single-shot deep call, so we allow up to ~14s for
# the expansion.
_TOTAL_BUDGET_S = 22.0

# Cap on expansion breadth: never more than 4 parallel follow-ups. Each
# is a "fast" depth call (~3s), so a 4-way fan-out completes in ~4s.
_MAX_EXPANSION_QUERIES = 4

# Regexes for deterministic gap detection.
_MONEY_RE = re.compile(r"\$\s?\d[\d,.]*\s?[KMBTkmbt]?|\b\d[\d,.]*\s?%|\b\d[\d,.]*\s?(?:billion|million|trillion)\b")
_COMPETITOR_MARKERS = (
    "competitor", "competitors", "compared to", "versus", "vs.", "alternative to",
    "alternatives", "rivals",
)
_TRACTION_MARKERS = (
    "arr", "mrr", "users", "customers", "revenue", "funding", "series a",
    "series b", "seed round", "deployments", "installs", "signups",
)


# ── Deterministic gap analysis ─────────────────────────────────────

def _citation_corpus(packet: ResearchPacket) -> str:
    """Concatenated lower-case title+snippet across every citation.

    Used only for substring containment checks — cheap."""
    parts: list[str] = []
    for c in (packet.citations + packet.news_citations):
        parts.append((c.title or "").lower())
        parts.append((c.snippet or "").lower())
    return " ".join(parts)


def _has_recent_news(packet: ResearchPacket, months: int = 6) -> bool:
    if not packet.news_citations:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=30 * months)
    for c in packet.news_citations:
        if not c.published_at:
            continue
        try:
            dt = datetime.fromisoformat(c.published_at.replace("Z", "+00:00"))
        except Exception:
            continue
        if dt >= cutoff:
            return True
    return False


def _analyze_gaps(packet: ResearchPacket) -> list[str]:
    """Return the list of evidence classes that are missing or thin.

    Keys are: "market_size", "competitor", "traction", "recent_news",
    "financial"."""
    gaps: list[str] = []
    corpus = _citation_corpus(packet)

    if not _MONEY_RE.search(corpus):
        gaps.append("market_size")
    if not any(m in corpus for m in _COMPETITOR_MARKERS):
        gaps.append("competitor")
    if not any(m in corpus for m in _TRACTION_MARKERS):
        gaps.append("traction")
    if not _has_recent_news(packet):
        gaps.append("recent_news")
    if not packet.financial_data:
        gaps.append("financial")

    return gaps


def _build_followup_queries(
    base_query: str,
    industry: Optional[str],
    company_name: Optional[str],
    gaps: Iterable[str],
) -> list[tuple[str, str]]:
    """Template follow-up queries from the detected gaps.

    Returns list of (gap_key, query). Caller truncates to
    _MAX_EXPANSION_QUERIES."""
    anchor = (company_name or industry or base_query[:80]).strip()
    queries: list[tuple[str, str]] = []

    for gap in gaps:
        if gap == "market_size":
            queries.append((
                "market_size",
                f"{anchor} total addressable market size TAM SAM CAGR forecast 2025",
            ))
        elif gap == "competitor":
            queries.append((
                "competitor",
                f"{anchor} competitors alternatives comparison leading players",
            ))
        elif gap == "traction":
            queries.append((
                "traction",
                f"{anchor} revenue ARR customers funding round growth traction",
            ))
        elif gap == "recent_news":
            # Add a year anchor so search engines prefer recent results.
            year = datetime.now(timezone.utc).year
            queries.append((
                "recent_news",
                f"{anchor} news announcement {year}",
            ))
        elif gap == "financial":
            queries.append((
                "financial",
                f"{anchor} revenue earnings financial performance valuation",
            ))
    return queries


# ── Merging ────────────────────────────────────────────────────────

def _merge_packets(base: ResearchPacket, extras: list[ResearchPacket]) -> ResearchPacket:
    """Union-merge the base packet with every expansion packet,
    de-duplicating citations by URL and preserving the base's query /
    industry / company_name / cache_hit."""
    seen_urls: set[str] = set()
    merged_citations: list[Citation] = []
    merged_news: list[Citation] = []

    def _push(cites: list[Citation], bucket: list[Citation]) -> None:
        for c in cites:
            if not c.url or c.url in seen_urls:
                continue
            seen_urls.add(c.url)
            bucket.append(c)

    _push(base.citations, merged_citations)
    _push(base.news_citations, merged_news)

    # Carry financial_data / social_signals forward; prefer the first
    # non-empty dict that appears across extras (they're all cheap
    # metadata and first-seen wins).
    financial_data = dict(base.financial_data or {})
    social_signals = dict(base.social_signals or {})

    for ex in extras:
        _push(ex.citations, merged_citations)
        _push(ex.news_citations, merged_news)
        for k, v in (ex.financial_data or {}).items():
            if k not in financial_data:
                financial_data[k] = v
        for k, v in (ex.social_signals or {}).items():
            if k not in social_signals:
                social_signals[k] = v

    merged_duration = (base.duration_ms or 0) + sum(ex.duration_ms or 0 for ex in extras)

    return dc_replace(
        base,
        citations=merged_citations[:40],          # slightly higher cap than base (30)
        news_citations=merged_news[:20],          # (base caps at 15)
        financial_data=financial_data,
        social_signals=social_signals,
        duration_ms=merged_duration,
    )


# ── Public entry point ─────────────────────────────────────────────

class DeepResearchLoop:
    """Iterative, gap-driven wrapper around ResearchCollector.

    Stateless: instantiate per request. Thread-safe because every async
    method uses only its own locals + the shared collector's HTTP
    client."""

    def __init__(self, collector: Optional[ResearchCollector] = None) -> None:
        self.collector = collector or ResearchCollector()

    async def run(
        self,
        *,
        user_query: str,
        industry: Optional[str] = None,
        company_name: Optional[str] = None,
        mode: str = "premium",
        research_depth: Optional[str] = None,
        emit: Optional[ProgressEmit] = None,
        profile: Optional["DepthProfile"] = None,
        recency: Optional["RecencyWindow"] = None,
        purpose: Optional[str] = None,
    ) -> ResearchPacket:
        # Late import keeps deep_research importable without forcing
        # the research subpackage at module-load time.
        from app.services.v4.research import (
            DepthProfile,
            RecencyWindow,
            profile_for,
            resolve_recency_window,
        )
        from datetime import date as _date

        if profile is None:
            profile = profile_for(mode, research_depth)
        if recency is None:
            recency = resolve_recency_window(
                purpose=purpose,
                user_query=user_query,
                today=_date.today(),
            )

        start = time.perf_counter()

        # Phase 1 — seed single-shot call. The collector now keys its
        # cache on profile label + recency window, so no leakage
        # between fast/standard/deep tiers.
        seed = await self.collector.collect(
            query=user_query,
            industry=industry,
            company_name=company_name,
            mode=mode,
            research_depth=research_depth,
            profile=profile,
            recency=recency,
            purpose=purpose,
        )

        # Plan 04 — only the deep profile runs the gap-driven loop.
        # Fast and standard return the seed packet as-is.
        if not profile.enable_followup_loop:
            if emit:
                await emit("deep_research_info", {
                    "phase": "seed_only",
                    "reason": f"profile_{profile.label}_no_followup",
                    "profile": profile.label,
                    "recency": recency.label,
                    "n_citations": len(seed.citations),
                    "n_news": len(seed.news_citations),
                })
            return seed

        # Phase 1-b: deterministic gap scan.
        gaps = _analyze_gaps(seed)
        if emit:
            await emit("deep_research_gaps", {
                "n_citations": len(seed.citations),
                "n_news": len(seed.news_citations),
                "gaps": gaps,
            })

        if not gaps:
            return seed

        # Budget check — if phase 1 already ate most of the budget, skip
        # expansion rather than risk blocking.
        remaining = _TOTAL_BUDGET_S - (time.perf_counter() - start)
        if remaining < 6.0:
            if emit:
                await emit("deep_research_info", {
                    "phase": "expansion_skipped",
                    "reason": "insufficient_budget",
                    "remaining_s": round(remaining, 2),
                })
            return seed

        followups = _build_followup_queries(user_query, industry, company_name, gaps)
        followups = followups[:_MAX_EXPANSION_QUERIES]
        if not followups:
            return seed

        if emit:
            await emit("deep_research_expansion_started", {
                "n_queries": len(followups),
                "queries": [q for _, q in followups],
            })

        # Phase 2 — fan out in parallel at "fast" depth. Each call uses
        # the collector's own Redis cache, so repeat queries across
        # generations are effectively free.
        expansion_tasks = [
            self.collector.collect(
                query=q,
                industry=industry,
                company_name=company_name,
                mode=mode,
                research_depth="fast",
                # Follow-ups inherit the recency window so we don't
                # accidentally pull pre-window evidence to fill a gap.
                recency=recency,
                purpose=purpose,
            )
            for _gap, q in followups
        ]

        try:
            expansion = await asyncio.wait_for(
                asyncio.gather(*expansion_tasks, return_exceptions=True),
                timeout=max(4.0, remaining - 1.0),
            )
        except asyncio.TimeoutError:
            logger.info(
                "v4_deep_research_expansion_timeout",
                n_queries=len(followups),
                remaining_s=remaining,
            )
            if emit:
                await emit("deep_research_expansion_timeout", {
                    "n_queries": len(followups),
                    "phase": "expansion",
                })
            return seed

        # Keep only the ones that returned valid packets.
        good_packets: list[ResearchPacket] = []
        for (gap, _q), res in zip(followups, expansion):
            if isinstance(res, ResearchPacket):
                good_packets.append(res)
            else:
                logger.debug(
                    "v4_deep_research_expansion_branch_failed",
                    gap=gap,
                    error=str(res) if isinstance(res, BaseException) else "non_packet",
                )

        if not good_packets:
            if emit:
                await emit("deep_research_info", {
                    "phase": "expansion_empty",
                    "reason": "all_followups_failed",
                })
            return seed

        merged = _merge_packets(seed, good_packets)
        if emit:
            await emit("deep_research_expansion_complete", {
                "n_followups": len(good_packets),
                "n_new_citations": len(merged.citations) - len(seed.citations),
                "n_new_news": len(merged.news_citations) - len(seed.news_citations),
                "total_duration_ms": int((time.perf_counter() - start) * 1000),
                "gaps_addressed": [g for g, _ in followups],
            })
        logger.info(
            "v4_deep_research_complete",
            n_citations_before=len(seed.citations),
            n_citations_after=len(merged.citations),
            n_followups=len(good_packets),
            gaps=gaps,
        )
        return merged
