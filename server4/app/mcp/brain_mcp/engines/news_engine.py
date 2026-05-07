"""
News aggregation engine — NewsAPI, NewsData, The Guardian, World News.
"""

from typing import Optional

import httpx

from app.config import settings

import structlog

logger = structlog.get_logger()


class NewsEngine:
    """Fetches recent news from multiple providers with fallback."""

    async def search_news(self, query: str, max_results: int = 5) -> list[dict]:
        """Search news with fallback chain: NewsAPI → NewsData → Guardian → World News."""
        providers = [
            ("newsapi", self._search_newsapi),
            ("newsdata", self._search_newsdata),
            ("guardian", self._search_guardian),
            ("world_news", self._search_world_news),
        ]

        for name, fn in providers:
            try:
                results = await fn(query, max_results)
                if results:
                    logger.info("news_search_success", provider=name, count=len(results))
                    return results
            except Exception as e:
                logger.warning("news_search_failed", provider=name, error=str(e))
                continue

        return []

    async def _search_newsapi(self, query: str, max_results: int) -> list[dict]:
        if not settings.NEWSAPI_KEY:
            raise ConnectionError("NewsAPI not configured")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://newsapi.org/v2/everything",
                params={"q": query, "pageSize": max_results, "sortBy": "relevancy", "apiKey": settings.NEWSAPI_KEY},
            )
            resp.raise_for_status()
            data = resp.json()

        return [
            {"title": a["title"], "source": a.get("source", {}).get("name", ""), "url": a.get("url", ""), "published": a.get("publishedAt", "")}
            for a in data.get("articles", [])[:max_results]
        ]

    async def _search_newsdata(self, query: str, max_results: int) -> list[dict]:
        if not settings.NEWSDATA_API_KEY:
            raise ConnectionError("NewsData not configured")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://newsdata.io/api/1/news",
                params={"q": query, "apikey": settings.NEWSDATA_API_KEY, "language": "en"},
            )
            resp.raise_for_status()
            data = resp.json()

        return [
            {"title": a.get("title", ""), "source": a.get("source_id", ""), "url": a.get("link", ""), "published": a.get("pubDate", "")}
            for a in data.get("results", [])[:max_results]
        ]

    async def _search_guardian(self, query: str, max_results: int) -> list[dict]:
        if not settings.GUARDIAN_API_KEY:
            raise ConnectionError("Guardian not configured")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://content.guardianapis.com/search",
                params={"q": query, "api-key": settings.GUARDIAN_API_KEY, "page-size": max_results, "order-by": "relevance"},
            )
            resp.raise_for_status()
            data = resp.json()

        return [
            {"title": r.get("webTitle", ""), "source": "The Guardian", "url": r.get("webUrl", ""), "published": r.get("webPublicationDate", "")}
            for r in data.get("response", {}).get("results", [])[:max_results]
        ]

    async def _search_world_news(self, query: str, max_results: int) -> list[dict]:
        """World News API for international coverage.

        API: GET https://api.worldnewsapi.com/search-news
        Header: x-api-key
        """
        if not settings.WORLD_NEWS_API_KEY:
            raise ConnectionError("World News API not configured")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.worldnewsapi.com/search-news",
                params={
                    "text": query,
                    "language": "en",
                    "number": max_results,
                },
                headers={"x-api-key": settings.WORLD_NEWS_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()

        return [
            {
                "title": a.get("title", ""),
                "source": a.get("source", ""),
                "url": a.get("url", ""),
                "published": a.get("publish_date", ""),
            }
            for a in data.get("news", [])[:max_results]
        ]
