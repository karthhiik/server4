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
