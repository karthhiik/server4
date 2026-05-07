"""
Multi-provider web search engine with round-robin and fallback.
Providers: Serper (3 keys) → Tavily → SerpAPI (2 keys) → Exa.ai → You.com
"""

import time
import threading
from typing import Optional

import httpx

from app.config import settings

import structlog

logger = structlog.get_logger()


class SearchEngine:
    """
    Multi-source web search with automatic failover and round-robin key rotation.
    """

    def __init__(self):
        self._serper_keys = settings.serper_keys
        self._serper_index = 0
        self._serpapi_keys = [k for k in [settings.SERPAPI_KEY, settings.SERPAPI_KEY_2] if k]
        self._serpapi_index = 0
        self._lock = threading.Lock()

    async def search(
        self,
        query: str,
        search_type: str = "general",
        max_results: int = 10,
    ) -> dict:
        """
        Search with automatic failover chain:
        Serper → Tavily → SerpAPI → Exa → You.com → empty results
        """
        providers = [
            ("serper", self._search_serper),
            ("tavily", self._search_tavily),
            ("serpapi", self._search_serpapi),
            ("exa", self._search_exa),
            ("scrapedo", self._search_scrapedo),
            ("search_api", self._search_api_search),
        ]

        for name, fn in providers:
            try:
                start = time.monotonic()
                results = await fn(query, max_results)
                elapsed = int((time.monotonic() - start) * 1000)
                logger.info("search_success", provider=name, query=query[:50], results=len(results.get("results", [])), latency_ms=elapsed)
                return results
            except Exception as e:
                logger.warning("search_failed", provider=name, query=query[:50], error=str(e))
                continue

        logger.error("all_search_providers_failed", query=query[:50])
        return {"results": [], "query": query, "provider": "none", "error": "All providers failed"}

    async def _search_serper(self, query: str, max_results: int) -> dict:
        if not self._serper_keys:
            raise ConnectionError("No Serper keys")

        with self._lock:
            key = self._serper_keys[self._serper_index % len(self._serper_keys)]
            self._serper_index += 1

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://google.serper.dev/search",
                json={"q": query, "num": max_results},
                headers={"X-API-KEY": key, "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("organic", [])[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })

        return {"results": results, "query": query, "provider": "serper"}

    async def _search_tavily(self, query: str, max_results: int) -> dict:
        if not settings.TAVILY_API_KEY:
            raise ConnectionError("Tavily not configured")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.TAVILY_API_KEY,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("results", [])[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", "")[:300],
            })

        return {"results": results, "query": query, "provider": "tavily"}

    async def _search_serpapi(self, query: str, max_results: int) -> dict:
        if not self._serpapi_keys:
            raise ConnectionError("No SerpAPI keys")

        with self._lock:
            key = self._serpapi_keys[self._serpapi_index % len(self._serpapi_keys)]
            self._serpapi_index += 1

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": key, "num": max_results, "engine": "google"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("organic_results", [])[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })

        return {"results": results, "query": query, "provider": "serpapi"}

    async def _search_exa(self, query: str, max_results: int) -> dict:
        if not settings.EXA_API_KEY:
            raise ConnectionError("Exa not configured")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.exa.ai/search",
                json={
                    "query": query,
                    "num_results": max_results,
                    "use_autoprompt": True,
                },
                headers={
                    "x-api-key": settings.EXA_API_KEY,
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("results", [])[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("text", "")[:300] if item.get("text") else "",
            })

        return {"results": results, "query": query, "provider": "exa"}

    async def _search_scrapedo(self, query: str, max_results: int = 10) -> dict:
        """Search via ScrapeDo proxy — for sites that block direct requests.

        API: https://api.scrape.do/search?api_key={key}&q={query}
        ScrapeDo proxies Google search results through rotating IPs.
        """
        if not settings.SCRAPE_DO_API_KEY:
            raise ConnectionError("ScrapeDo not configured")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.scrape.do/search",
                params={
                    "api_key": settings.SCRAPE_DO_API_KEY,
                    "q": query,
                    "num": max_results,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("organic_results", data.get("results", []))[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", item.get("url", "")),
                "snippet": item.get("snippet", item.get("description", "")),
            })

        return {"results": results, "query": query, "provider": "scrapedo"}

    async def _search_api_search(self, query: str, max_results: int = 10) -> dict:
        """Generic Search API fallback.

        API: https://www.searchapi.io/api/v1/search
        Uses the Search API service as a last-resort provider.
        """
        if not settings.SEARCH_API_KEY:
            raise ConnectionError("Search API not configured")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://www.searchapi.io/api/v1/search",
                params={
                    "engine": "google",
                    "q": query,
                    "num": max_results,
                    "api_key": settings.SEARCH_API_KEY,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("organic_results", [])[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })

        return {"results": results, "query": query, "provider": "search_api"}

    async def search_with_health(
        self,
        query: str,
        circuit_breaker=None,
        emitter=None,
        slide_id: str = "",
        max_results: int = 10,
    ) -> dict:
        """Search with circuit breaker gating.

        Checks circuit breaker health BEFORE trying each provider.
        Emits events via ContentEventEmitter when provided.
        """
        providers = [
            ("serper", self._search_serper),
            ("tavily", self._search_tavily),
            ("serpapi", self._search_serpapi),
            ("exa", self._search_exa),
            ("scrapedo", self._search_scrapedo),
            ("search_api", self._search_api_search),
        ]

        for name, fn in providers:
            # Check circuit breaker before attempting
            if circuit_breaker and not circuit_breaker.allow_request(name):
                logger.info("search_circuit_open", provider=name, query=query[:50])
                continue

            try:
                if emitter and slide_id:
                    await emitter.source_fetching(slide_id, name)

                start = time.monotonic()
                results = await fn(query, max_results)
                elapsed = int((time.monotonic() - start) * 1000)

                result_count = len(results.get("results", []))
                logger.info(
                    "search_health_success",
                    provider=name,
                    query=query[:50],
                    results=result_count,
                    latency_ms=elapsed,
                )

                if circuit_breaker:
                    circuit_breaker.record_success(name)
                if emitter and slide_id:
                    await emitter.source_fetched(slide_id, name, result_count)

                return results
            except Exception as e:
                logger.warning(
                    "search_health_failed",
                    provider=name,
                    query=query[:50],
                    error=str(e),
                )
                if circuit_breaker:
                    circuit_breaker.record_failure(name)
                if emitter and slide_id:
                    await emitter.source_failed(
                        slide_id, name, "error", str(e)[:200]
                    )
                continue

        logger.error("all_search_health_providers_failed", query=query[:50])
        return {
            "results": [],
            "query": query,
            "provider": "none",
            "error": "All providers failed (circuit breaker)",
        }
