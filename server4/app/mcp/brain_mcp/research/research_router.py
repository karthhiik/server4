"""
Intent-based multi-provider research router.

The brain of the V7 research system.  Given a slide kind and topic,
selects the correct evidence types, routes to providers via the registry
and circuit breaker, executes queries in parallel, and returns normalised
FactPackets.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from app.mcp.brain_mcp.research.models import (
    BudgetMode,
    ClaimType,
    FactPacket,
    ProviderStatus,
    SlideKind,
    SourceType,
)
from app.mcp.brain_mcp.research.provider_registry import ProviderRegistry
from app.mcp.brain_mcp.research.circuit_breaker import CircuitBreaker
from app.mcp.brain_mcp.research.content_events import ContentEventEmitter
from app.mcp.brain_mcp.research.fact_packets import FactPacketFactory

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# EVIDENCE-TYPE → PROVIDER MAPPING
# ═══════════════════════════════════════════════════════════════════════

EVIDENCE_TYPE_MAP: dict[str, list[str]] = {
    "macro_economic": ["world_bank", "fred", "census"],
    "company_news": ["finnhub", "guardian", "newsdata", "world_news"],
    "startup_discovery": [
        "tavily", "exa", "serper", "serpapi", "you_com", "search_api",
    ],
    "financial_data": ["finnhub", "polygon", "fmp", "coindesk", "eodhd"],
    "content_extraction": ["jina", "firecrawl", "scrapedo"],
    "academic": ["core", "github", "exa"],
    "social_proof": ["github", "reddit", "producthunt", "youtube"],
    "specialty": ["api_ninjas", "nasa_apod", "coindesk", "abuseipdb"],
}


# ═══════════════════════════════════════════════════════════════════════
# SLIDE KIND → REQUIRED EVIDENCE TYPES
# ═══════════════════════════════════════════════════════════════════════

SLIDE_EVIDENCE_REQUIREMENTS: dict[SlideKind, list[str]] = {
    SlideKind.title: [],
    SlideKind.problem: ["startup_discovery", "company_news", "macro_economic"],
    SlideKind.solution: ["startup_discovery", "social_proof"],
    SlideKind.market: ["macro_economic", "financial_data", "startup_discovery"],
    SlideKind.competition: ["startup_discovery", "financial_data", "social_proof"],
    SlideKind.gtm: ["startup_discovery", "social_proof"],
    SlideKind.traction: ["social_proof", "financial_data"],
    SlideKind.financial: ["financial_data", "macro_economic"],
    SlideKind.team: [],
    SlideKind.ask: ["financial_data"],
    SlideKind.why_now: ["macro_economic", "company_news", "academic"],
    SlideKind.product_demo: ["social_proof"],
    SlideKind.appendix: [],
}


# ═══════════════════════════════════════════════════════════════════════
# PROVIDER → ENGINE DISPATCH TABLE
# ═══════════════════════════════════════════════════════════════════════

# Maps a provider name to the tuple (engine_module, engine_class, method, source_type)
# Engines are lazily instantiated inside _call_provider.

_PROVIDER_ENGINE_MAP: dict[str, dict[str, str]] = {
    # Search engines
    "serper":     {"engine": "search", "method": "search", "source_type": "web_extracted"},
    "tavily":     {"engine": "search", "method": "search", "source_type": "web_extracted"},
    "serpapi":    {"engine": "search", "method": "search", "source_type": "web_extracted"},
    "exa":        {"engine": "search", "method": "search", "source_type": "web_extracted"},
    "you_com":    {"engine": "search", "method": "search", "source_type": "web_extracted"},
    "search_api": {"engine": "search", "method": "search", "source_type": "web_extracted"},
    # Market / macro
    "fred":          {"engine": "market", "method": "get_market_overview", "source_type": "government_data"},
    "world_bank":    {"engine": "market", "method": "get_market_overview", "source_type": "government_data"},
    "alpha_vantage": {"engine": "market", "method": "get_market_overview", "source_type": "financial_api"},
    "finnhub":       {"engine": "market", "method": "get_market_overview", "source_type": "financial_api"},
    # Financial
    "polygon": {"engine": "financial", "method": "get_company_financials", "source_type": "financial_api"},
    "fmp":     {"engine": "financial", "method": "get_company_financials", "source_type": "financial_api"},
    "census":  {"engine": "financial", "method": "get_census_data", "source_type": "government_data"},
    # News
    "newsapi":         {"engine": "news", "method": "search_news", "source_type": "news_article"},
    "newsdata":        {"engine": "news", "method": "search_news", "source_type": "news_article"},
    "guardian":        {"engine": "news", "method": "search_news", "source_type": "news_article"},
    "world_news":      {"engine": "news", "method": "search_news", "source_type": "news_article"},
    # Social
    "reddit":      {"engine": "social", "method": "search_reddit", "source_type": "social_signal"},
    "github":      {"engine": "social", "method": "search_github", "source_type": "social_signal"},
    "youtube":     {"engine": "social", "method": "search_youtube", "source_type": "social_signal"},
    "producthunt": {"engine": "social", "method": "search_reddit", "source_type": "social_signal"},
    # Academic
    "core": {"engine": "academic", "method": "search_papers", "source_type": "academic_paper"},
    # Scraper
    "jina":      {"engine": "scraper", "method": "extract_content", "source_type": "web_extracted"},
    "firecrawl": {"engine": "scraper", "method": "extract_content", "source_type": "web_extracted"},
    "scrapedo":  {"engine": "scraper", "method": "extract_content", "source_type": "web_extracted"},
    # Specialty — directly handled inside _call_provider
    "coindesk":   {"engine": "specialty", "method": "direct", "source_type": "financial_api"},
    "eodhd":      {"engine": "specialty", "method": "direct", "source_type": "financial_api"},
    "api_ninjas": {"engine": "specialty", "method": "direct", "source_type": "web_extracted"},
    "nasa_apod":  {"engine": "specialty", "method": "direct", "source_type": "web_extracted"},
    "abuseipdb":  {"engine": "specialty", "method": "direct", "source_type": "web_extracted"},
}


# ═══════════════════════════════════════════════════════════════════════
# BUDGET LIMITS
# ═══════════════════════════════════════════════════════════════════════

_BUDGET_LIMITS: dict[BudgetMode, dict[str, int]] = {
    BudgetMode.lean: {
        "max_providers_per_evidence_type": 2,
        "max_parallel": 3,
        "max_depth": 1,
        "max_queries_per_type": 2,
        "max_total_providers": 6,
    },
    BudgetMode.balanced: {
        "max_providers_per_evidence_type": 3,
        "max_parallel": 5,
        "max_depth": 2,
        "max_queries_per_type": 3,
        "max_total_providers": 12,
    },
    BudgetMode.hero: {
        "max_providers_per_evidence_type": 5,
        "max_parallel": 8,
        "max_depth": 3,
        "max_queries_per_type": 5,
        "max_total_providers": 20,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# MINIMUM EVIDENCE THRESHOLDS  (slide kind → min FactPackets)
# ═══════════════════════════════════════════════════════════════════════

_MIN_EVIDENCE: dict[SlideKind, int] = {
    SlideKind.title: 0,
    SlideKind.problem: 3,
    SlideKind.solution: 2,
    SlideKind.market: 5,
    SlideKind.competition: 4,
    SlideKind.gtm: 2,
    SlideKind.traction: 3,
    SlideKind.financial: 4,
    SlideKind.team: 0,
    SlideKind.ask: 2,
    SlideKind.why_now: 3,
    SlideKind.product_demo: 1,
    SlideKind.appendix: 0,
}


class ResearchRouter:
    """Intent-based research router that selects providers by evidence type."""

    def __init__(
        self,
        registry: ProviderRegistry,
        circuit_breaker: CircuitBreaker,
        emitter: ContentEventEmitter,
    ) -> None:
        self._registry = registry
        self._cb = circuit_breaker
        self._emitter = emitter
        self._engines: dict[str, Any] = {}

    # ── Main entry point ────────────────────────────────────────

    async def research_slide(
        self,
        slide_id: str,
        slide_kind: SlideKind,
        queries: list[str],
        topic: str,
        budget_mode: BudgetMode = BudgetMode.lean,
        max_depth: int = 1,
    ) -> list[FactPacket]:
        """
        Route research to the correct providers based on slide kind.

        1. Determine required evidence types from SLIDE_EVIDENCE_REQUIREMENTS.
        2. For each evidence type, get provider chain from registry.
        3. Filter by circuit breaker health and budget.
        4. Execute queries in parallel across providers.
        5. Normalise results into FactPackets.
        6. Emit progress events.
        7. Optionally deepen if evidence is insufficient.
        """
        evidence_types = SLIDE_EVIDENCE_REQUIREMENTS.get(slide_kind, [])
        if not evidence_types:
            logger.info(
                "No evidence required for slide_kind=%s (slide_id=%s)",
                slide_kind.value,
                slide_id,
            )
            return []

        limits = self._get_budget_limits(budget_mode)
        effective_max_depth = min(max_depth, limits["max_depth"])

        all_packets: list[FactPacket] = []
        current_depth = 0

        while current_depth < effective_max_depth:
            current_depth += 1
            logger.info(
                "Research depth=%d/%d for slide=%s kind=%s evidence_types=%s",
                current_depth,
                effective_max_depth,
                slide_id,
                slide_kind.value,
                evidence_types,
            )

            # Fire off chains for each evidence type in parallel
            chain_tasks = []
            for ev_type in evidence_types:
                chain_tasks.append(
                    self._execute_provider_chain(
                        slide_id=slide_id,
                        evidence_type=ev_type,
                        queries=queries,
                        budget_mode=budget_mode,
                    )
                )

            chain_results = await asyncio.gather(*chain_tasks, return_exceptions=True)

            for idx, result in enumerate(chain_results):
                ev_type = evidence_types[idx]
                if isinstance(result, Exception):
                    logger.error(
                        "Provider chain for evidence_type=%s failed: %s",
                        ev_type,
                        result,
                    )
                    continue
                if result:
                    all_packets.extend(result)

            # Deduplicate after each depth pass
            all_packets = FactPacketFactory.deduplicate(all_packets)

            # Check if we should go deeper
            if not self._should_deepen(all_packets, slide_kind, current_depth, effective_max_depth):
                break

            logger.info(
                "Deepening research for slide=%s (have %d packets, need %d)",
                slide_id,
                len(all_packets),
                _MIN_EVIDENCE.get(slide_kind, 0),
            )

        logger.info(
            "Research complete for slide=%s: %d FactPackets from depth=%d",
            slide_id,
            len(all_packets),
            current_depth,
        )
        return all_packets

    # ── Provider chain execution ────────────────────────────────

    async def _execute_provider_chain(
        self,
        slide_id: str,
        evidence_type: str,
        queries: list[str],
        budget_mode: BudgetMode,
    ) -> list[FactPacket]:
        """Execute a chain of providers for one evidence type.

        Stop when sufficient evidence is found or all providers exhausted.
        """
        limits = self._get_budget_limits(budget_mode)
        max_providers = limits["max_providers_per_evidence_type"]
        max_parallel = limits["max_parallel"]
        max_queries = limits["max_queries_per_type"]

        # Get the EVIDENCE_TYPE_MAP providers, filtered by registry availability
        raw_chain = EVIDENCE_TYPE_MAP.get(evidence_type, [])
        available_chain: list[str] = []

        for provider_name in raw_chain:
            if not self._registry.is_available(provider_name):
                await self._emitter.provider_skipped(
                    slide_id, provider_name, "not_configured",
                )
                continue

            health = await self._cb.check_health(provider_name)
            if health.status == ProviderStatus.open_circuit:
                await self._emitter.provider_skipped(
                    slide_id, provider_name, f"circuit_open until {health.circuit_open_until}",
                )
                continue

            available_chain.append(provider_name)
            if len(available_chain) >= max_providers:
                break

        if not available_chain:
            logger.warning(
                "No available providers for evidence_type=%s slide=%s",
                evidence_type,
                slide_id,
            )
            return []

        # Limit queries per budget
        effective_queries = queries[:max_queries]
        all_packets: list[FactPacket] = []

        # Build tasks: each (provider, query) pair
        tasks: list[tuple[str, str]] = []
        for provider_name in available_chain:
            for query in effective_queries:
                tasks.append((provider_name, query))

        # Execute in batches of max_parallel
        for batch_start in range(0, len(tasks), max_parallel):
            batch = tasks[batch_start: batch_start + max_parallel]
            coros = [
                self._call_provider(prov, q, slide_id)
                for prov, q in batch
            ]
            results = await asyncio.gather(*coros, return_exceptions=True)

            for idx, result in enumerate(results):
                prov_name = batch[idx][0]
                if isinstance(result, Exception):
                    logger.warning(
                        "Provider %s call failed in batch: %s",
                        prov_name,
                        result,
                    )
                    continue
                if result:
                    all_packets.extend(result)

        return all_packets

    # ── Single-provider call ────────────────────────────────────

    async def _call_provider(
        self,
        provider_name: str,
        query: str,
        slide_id: str,
    ) -> list[FactPacket]:
        """
        Call a single provider, record health via circuit breaker, emit events.

        Maps provider names to actual engine calls using _PROVIDER_ENGINE_MAP.
        """
        mapping = _PROVIDER_ENGINE_MAP.get(provider_name)
        if not mapping:
            logger.warning("No engine mapping for provider=%s", provider_name)
            return []

        await self._emitter.source_fetching(slide_id, provider_name)
        start_ms = time.monotonic()

        try:
            raw_results = await self._dispatch_engine_call(
                provider_name, mapping, query,
            )
            elapsed_ms = (time.monotonic() - start_ms) * 1000

            # Record success in circuit breaker
            await self._cb.record_success(provider_name, elapsed_ms)

            # Convert raw results → FactPackets
            packets = self._normalise_results(
                provider_name, mapping, raw_results, query,
            )

            await self._emitter.source_fetched(
                slide_id, provider_name, len(packets),
            )
            logger.info(
                "Provider %s returned %d packets for query='%s' in %.0fms",
                provider_name,
                len(packets),
                query[:60],
                elapsed_ms,
            )
            return packets

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start_ms) * 1000
            error_type = type(exc).__name__
            await self._cb.record_failure(provider_name, error_type)
            await self._emitter.source_failed(
                slide_id,
                provider_name,
                error_type,
                f"Will try next provider in chain",
            )
            logger.warning(
                "Provider %s failed for query='%s': %s (%.0fms)",
                provider_name,
                query[:60],
                exc,
                elapsed_ms,
            )
            return []

    # ── Engine dispatch ─────────────────────────────────────────

    async def _dispatch_engine_call(
        self,
        provider_name: str,
        mapping: dict[str, str],
        query: str,
    ) -> Any:
        """Instantiate (cached) engine and call the mapped method."""
        engine_key = mapping["engine"]
        method_name = mapping["method"]

        engine = self._get_or_create_engine(engine_key)
        if engine is None:
            raise RuntimeError(f"Could not create engine for {engine_key}")

        if engine_key == "search":
            return await engine.search(query=query, max_results=10)

        if engine_key == "market":
            return await engine.get_market_overview(industry=query)

        if engine_key == "financial":
            if method_name == "get_census_data":
                return await engine.get_census_data(topic=query)
            # For company financials, use query as ticker if short, else search
            ticker = query.split()[0].upper() if len(query.split()) == 1 else query[:8]
            return await engine.get_company_financials(ticker=ticker)

        if engine_key == "news":
            results = await engine.search_news(query=query, max_results=5)
            return {"results": results, "provider": provider_name}

        if engine_key == "social":
            if provider_name == "reddit":
                results = await engine.search_reddit(query=query, max_results=5)
            elif provider_name == "github":
                results = await engine.search_github(query=query, max_results=5)
            elif provider_name == "youtube":
                results = await engine.search_youtube(query=query, max_results=5)
            elif provider_name == "producthunt":
                # ProductHunt uses Reddit search as a proxy (same engine)
                results = await engine.search_reddit(query=f"{query} producthunt", max_results=5)
            else:
                results = []
            return {"results": results, "provider": provider_name}

        if engine_key == "academic":
            results = await engine.search_papers(query=query, max_results=5)
            return {"results": results, "provider": provider_name}

        if engine_key == "scraper":
            # Scraper expects a URL; for query-based calls, skip gracefully
            if query.startswith(("http://", "https://")):
                result = await engine.extract_content(url=query)
                return {"results": [result] if result else [], "provider": provider_name}
            logger.debug("Scraper engine skipped for non-URL query: %s", query[:60])
            return {"results": [], "provider": provider_name}

        if engine_key == "specialty":
            return await self._call_specialty_provider(provider_name, query)

        raise RuntimeError(f"Unknown engine_key={engine_key}")

    def _get_or_create_engine(self, engine_key: str) -> Any:
        """Lazily instantiate and cache engine instances."""
        if engine_key in self._engines:
            return self._engines[engine_key]

        engine: Any = None
        if engine_key == "search":
            from app.mcp.brain_mcp.engines.search_engine import SearchEngine
            engine = SearchEngine()
        elif engine_key == "market":
            from app.mcp.brain_mcp.engines.market_engine import MarketDataEngine
            engine = MarketDataEngine()
        elif engine_key == "financial":
            from app.mcp.brain_mcp.engines.financial_engine import FinancialEngine
            engine = FinancialEngine()
        elif engine_key == "news":
            from app.mcp.brain_mcp.engines.news_engine import NewsEngine
            engine = NewsEngine()
        elif engine_key == "social":
            from app.mcp.brain_mcp.engines.social_engine import SocialEngine
            engine = SocialEngine()
        elif engine_key == "academic":
            from app.mcp.brain_mcp.engines.academic_engine import AcademicEngine
            engine = AcademicEngine()
        elif engine_key == "scraper":
            from app.mcp.brain_mcp.engines.scraper_engine import ScraperEngine
            engine = ScraperEngine()

        if engine is not None:
            self._engines[engine_key] = engine
        return engine

    async def _call_specialty_provider(
        self, provider_name: str, query: str,
    ) -> dict[str, Any]:
        """Direct HTTP calls for specialty providers not covered by existing engines."""
        import httpx
        from app.config import settings

        results: list[dict[str, Any]] = []

        if provider_name == "coindesk" and getattr(settings, "COINDESK_API_KEY", ""):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        "https://api.coindesk.com/v1/bpi/currentprice.json",
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        bpi = data.get("bpi", {}).get("USD", {})
                        results.append({
                            "claim": f"Bitcoin price: ${bpi.get('rate', 'N/A')} USD",
                            "source_name": "CoinDesk",
                            "source_url": "https://www.coindesk.com/price/bitcoin/",
                            "date_published": data.get("time", {}).get("updated"),
                        })
            except Exception as exc:
                logger.warning("CoinDesk specialty call failed: %s", exc)

        elif provider_name == "api_ninjas" and getattr(settings, "API_NINJAS_KEY", ""):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        "https://api.api-ninjas.com/v1/facts",
                        params={"limit": 3},
                        headers={"X-Api-Key": settings.API_NINJAS_KEY},
                    )
                    if resp.status_code == 200:
                        for fact in resp.json():
                            results.append({
                                "claim": fact.get("fact", ""),
                                "source_name": "API Ninjas",
                            })
            except Exception as exc:
                logger.warning("API Ninjas specialty call failed: %s", exc)

        elif provider_name == "nasa_apod" and getattr(settings, "NASA_API_KEY", ""):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        "https://api.nasa.gov/planetary/apod",
                        params={"api_key": settings.NASA_API_KEY},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        results.append({
                            "claim": data.get("explanation", "")[:300],
                            "source_name": "NASA APOD",
                            "source_url": data.get("url"),
                            "date_published": data.get("date"),
                        })
            except Exception as exc:
                logger.warning("NASA APOD specialty call failed: %s", exc)

        elif provider_name == "eodhd" and getattr(settings, "EODHD_API_KEY", ""):
            try:
                ticker = query.split()[0].upper() if query else "AAPL"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"https://eodhd.com/api/real-time/{ticker}.US",
                        params={"api_token": settings.EODHD_API_KEY, "fmt": "json"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        results.append({
                            "claim": f"{ticker} close: ${data.get('close', 'N/A')}, "
                                     f"change: {data.get('change_p', 'N/A')}%",
                            "source_name": "EODHD",
                            "numeric_value": data.get("close"),
                            "numeric_unit": "USD",
                        })
            except Exception as exc:
                logger.warning("EODHD specialty call failed: %s", exc)

        return {"results": results, "provider": provider_name}

    # ── Result normalisation ────────────────────────────────────

    def _normalise_results(
        self,
        provider_name: str,
        mapping: dict[str, str],
        raw: Any,
        query: str,
    ) -> list[FactPacket]:
        """Convert raw engine output into FactPackets using FactPacketFactory."""
        source_type_str = mapping.get("source_type", "web_extracted")
        try:
            source_type = SourceType(source_type_str)
        except ValueError:
            source_type = SourceType.web_extracted

        packets: list[FactPacket] = []

        if raw is None:
            return packets

        # Handle dict responses  ────────────────────────────────
        if isinstance(raw, dict):
            # Standard {"results": [...]} format
            results_list = raw.get("results", [])
            if isinstance(results_list, list):
                for item in results_list:
                    if isinstance(item, dict):
                        fp = self._item_to_fact_packet(item, provider_name, source_type)
                        if fp:
                            packets.append(fp)

            # Market/financial engines return nested dicts of data
            if not results_list:
                for key, value in raw.items():
                    if key in ("provider", "query", "error"):
                        continue
                    claim = self._dict_value_to_claim(key, value)
                    if claim:
                        packets.append(
                            FactPacketFactory.create(
                                claim=claim,
                                source_name=provider_name,
                                provider=provider_name,
                                source_type=source_type,
                                extraction_method="api_structured",
                            )
                        )

        # Handle list responses (news, social) ──────────────────
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    fp = self._item_to_fact_packet(item, provider_name, source_type)
                    if fp:
                        packets.append(fp)

        return packets

    def _item_to_fact_packet(
        self,
        item: dict[str, Any],
        provider_name: str,
        source_type: SourceType,
    ) -> Optional[FactPacket]:
        """Convert a single result dict into a FactPacket."""
        claim = (
            item.get("claim")
            or item.get("snippet")
            or item.get("title")
            or item.get("description")
            or item.get("abstract")
        )
        if not claim or not claim.strip():
            return None

        return FactPacketFactory.create(
            claim=str(claim).strip(),
            source_name=item.get("source_name", item.get("source", provider_name)),
            provider=provider_name,
            source_type=source_type,
            source_url=item.get("source_url") or item.get("url") or item.get("link"),
            date_published=item.get("date_published") or item.get("published") or item.get("date"),
            numeric_value=item.get("numeric_value"),
            numeric_unit=item.get("numeric_unit"),
            extraction_method="api_structured" if item.get("numeric_value") else "scraped",
            raw_snippet=item.get("raw_snippet") or item.get("snippet"),
        )

    @staticmethod
    def _dict_value_to_claim(key: str, value: Any) -> Optional[str]:
        """Convert a key-value pair from a nested dict into a human-readable claim."""
        if value is None:
            return None
        if isinstance(value, dict):
            parts = []
            for k, v in value.items():
                if v is not None:
                    parts.append(f"{k}: {v}")
            if parts:
                label = key.replace("_", " ").title()
                return f"{label} — {', '.join(parts)}"
            return None
        if isinstance(value, (int, float)):
            label = key.replace("_", " ").title()
            return f"{label}: {value}"
        if isinstance(value, str) and value.strip():
            label = key.replace("_", " ").title()
            return f"{label}: {value}"
        return None

    # ── Depth control ───────────────────────────────────────────

    def _should_deepen(
        self,
        packets: list[FactPacket],
        slide_kind: SlideKind,
        current_depth: int,
        max_depth: int,
    ) -> bool:
        """Check if we need deeper research (insufficient evidence)."""
        if current_depth >= max_depth:
            return False

        min_required = _MIN_EVIDENCE.get(slide_kind, 0)
        if len(packets) >= min_required:
            return False

        # Also check confidence — if we have packets but all are low confidence
        if packets:
            avg_conf = sum(p.confidence for p in packets) / len(packets)
            if avg_conf < 0.5:
                logger.info(
                    "Average confidence %.2f is below 0.5, deepening research",
                    avg_conf,
                )
                return True

        # Not enough packets
        return True

    # ── Budget helpers ──────────────────────────────────────────

    @staticmethod
    def _get_budget_limits(budget_mode: BudgetMode) -> dict[str, int]:
        """Return max providers / parallel / depth per budget mode."""
        return _BUDGET_LIMITS.get(budget_mode, _BUDGET_LIMITS[BudgetMode.lean])
