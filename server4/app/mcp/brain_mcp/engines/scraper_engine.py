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
        """Extract content with fallback: Firecrawl → Jina → ScrapeDo."""
        providers = [
            ("firecrawl", self._extract_firecrawl),
            ("jina", self._extract_jina),
            ("scrapedo", self._extract_scrapedo),
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

    async def _extract_scrapedo(self, url: str) -> Optional[dict]:
        """Extract content via ScrapeDo proxy for anti-bot bypass.

        API: https://api.scrape.do/?api_key={key}&url={url}&render=true
        ScrapeDo renders the page via headless browser and returns HTML.
        We extract text content from the rendered HTML.
        """
        if not settings.SCRAPE_DO_API_KEY:
            raise ConnectionError("ScrapeDo not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://api.scrape.do/",
                params={
                    "api_key": settings.SCRAPE_DO_API_KEY,
                    "url": url,
                    "render": "true",
                },
            )
            resp.raise_for_status()
            # ScrapeDo returns raw HTML; extract text
            html_content = resp.text

        if not html_content or len(html_content) < 100:
            return None

        # Basic text extraction: strip tags
        import re

        text = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        if not text:
            return None

        # Try to extract title from HTML
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else ""

        return {
            "url": url,
            "title": title,
            "content": text[:5000],
            "source": "scrapedo",
        }
