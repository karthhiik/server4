"""
Web scraping engine — Firecrawl and Jina for content extraction.
"""

from typing import Optional

import httpx

from app.config import settings

import structlog

logger = structlog.get_logger()


class ScraperEngine:
    """Extracts clean content from URLs using Firecrawl and Jina."""

    async def extract_content(self, url: str) -> Optional[dict]:
        """Extract content with fallback: Firecrawl → Jina."""
        providers = [
            ("firecrawl", self._extract_firecrawl),
            ("jina", self._extract_jina),
        ]

        for name, fn in providers:
            try:
                result = await fn(url)
                if result:
                    logger.info("scrape_success", provider=name, url=url[:80])
                    return result
            except Exception as e:
                logger.warning("scrape_failed", provider=name, url=url[:80], error=str(e))
                continue

        return None

    async def batch_extract(self, urls: list[str], max_concurrent: int = 5) -> list[dict]:
        """Extract content from multiple URLs."""
        import asyncio
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _extract_with_limit(url: str) -> Optional[dict]:
            async with semaphore:
                return await self.extract_content(url)

        tasks = [_extract_with_limit(u) for u in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, dict)]

    async def _extract_firecrawl(self, url: str) -> Optional[dict]:
        if not settings.FIRECRAWL_API_KEY:
            raise ConnectionError("Firecrawl not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.firecrawl.dev/v1/scrape",
                json={"url": url, "formats": ["markdown"]},
                headers={"Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()

        result = data.get("data", {})
        markdown = result.get("markdown", "")
        if not markdown:
            return None

        return {
            "url": url,
            "title": result.get("metadata", {}).get("title", ""),
            "content": markdown[:5000],
            "source": "firecrawl",
        }

    async def _extract_jina(self, url: str) -> Optional[dict]:
        if not settings.JINA_API_KEY:
            raise ConnectionError("Jina not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"https://r.jina.ai/{url}",
                headers={
                    "Authorization": f"Bearer {settings.JINA_API_KEY}",
                    "Accept": "application/json",
                    "X-Return-Format": "markdown",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data.get("data", {}).get("content", "")
        if not content:
            return None

        return {
            "url": url,
            "title": data.get("data", {}).get("title", ""),
            "content": content[:5000],
            "source": "jina",
        }
