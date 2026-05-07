"""
World News API for international news coverage.
https://worldnewsapi.com/docs/
"""

import httpx

from app.config import settings

import structlog

logger = structlog.get_logger()


class WorldNewsEngine:
    """International news from World News API."""

    BASE_URL = "https://api.worldnewsapi.com"

    @staticmethod
    async def search_news(
        query: str, max_results: int = 10, language: str = "en"
    ) -> list[dict]:
        """Search news globally.

        API: GET /search-news?text={query}&language={lang}&number={max}
        Header: x-api-key
        Returns: [{title, text, url, publish_date, source_country, author}]
        """
        if not settings.WORLD_NEWS_API_KEY:
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{WorldNewsEngine.BASE_URL}/search-news",
                    params={
                        "text": query,
                        "language": language,
                        "number": min(max_results, 50),
                    },
                    headers={"x-api-key": settings.WORLD_NEWS_API_KEY},
                )
                resp.raise_for_status()
                data = resp.json()

            articles = data.get("news", [])
            results = []
            for a in articles[:max_results]:
                results.append({
                    "title": a.get("title", ""),
                    "text": (a.get("text") or "")[:500],
                    "url": a.get("url", ""),
                    "publish_date": a.get("publish_date", ""),
                    "source_country": a.get("source_country", ""),
                    "author": a.get("author", ""),
                    "source": a.get("source", ""),
                    "provider": "world_news",
                })
            return results
        except Exception as e:
            logger.warning("world_news_search_failed", query=query[:50], error=str(e))
            return []

    @staticmethod
    async def get_top_news(
        country: str = "us", max_results: int = 10
    ) -> list[dict]:
        """Get top news by country.

        API: GET /top-news?source-country={country}&language=en
        """
        if not settings.WORLD_NEWS_API_KEY:
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{WorldNewsEngine.BASE_URL}/top-news",
                    params={
                        "source-country": country,
                        "language": "en",
                    },
                    headers={"x-api-key": settings.WORLD_NEWS_API_KEY},
                )
                resp.raise_for_status()
                data = resp.json()

            # top-news returns {top_news: [{news: [...]}]}
            top_news = data.get("top_news", [])
            results = []
            for category in top_news:
                for a in category.get("news", []):
                    if len(results) >= max_results:
                        break
                    results.append({
                        "title": a.get("title", ""),
                        "text": (a.get("text") or "")[:500],
                        "url": a.get("url", ""),
                        "publish_date": a.get("publish_date", ""),
                        "source_country": a.get("source_country", country),
                        "author": a.get("author", ""),
                        "source": a.get("source", ""),
                        "provider": "world_news",
                    })
                if len(results) >= max_results:
                    break

            return results
        except Exception as e:
            logger.warning("world_news_top_failed", country=country, error=str(e))
            return []
