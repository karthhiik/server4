"""
Web scraping engine — multi-provider URL→content extraction.

Provider chain (best-quality first, broad-coverage last):
    Firecrawl → Jina → ScrapingBee → ScrapingDog (a.k.a. scrapingbog) →
    ScrapeDo → Apify (Website Content Crawler).

Each provider has its own key pool with round-robin rotation and per-key
cooldown on 429/5xx via :class:`KeyPool`. A provider that returns nothing
(or raises) is silently skipped and the chain continues. The first
provider returning a non-empty content payload wins.

All providers return the same shape::

    {"url": str, "title": str, "content": str (≤5000), "source": str}

This module is invoked by:
  - ``app.mcp.brain_mcp.research.research_router`` (ad-hoc engine routing)
  - ``app.services.orchestrator.orchestrator`` (research orchestration)
  - and indirectly by V4 deep-research when fact-evidence is needed.
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional

import httpx
import structlog

from app.config import settings
from app.services.v4.key_pool import get_pool

logger = structlog.get_logger(__name__)


# Reasonable extraction caps. Apify often returns many KB of markdown; we
# truncate to the same ceiling Firecrawl/Jina use so downstream code can
# treat all sources uniformly.
_MAX_CONTENT_CHARS = 5000

# httpx timeouts. Apify is slow because it spins up an Actor — give it more
# headroom so we don't false-fail. Other providers are HTTP-fast.
_FAST_TIMEOUT = 30.0
_APIFY_TIMEOUT = 90.0


def _classify_status(exc: Exception) -> int:
    """Translate an httpx exception into an int status code for the pool's
    cooldown logic. Returns 0 if the exception was not HTTP-status-bearing."""
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            return int(exc.response.status_code)
        except Exception:
            return 0
    return 0


def _strip_html(html: str) -> tuple[str, str]:
    """Minimal HTML→text + title extraction. Returns ``(title, text)``."""
    if not html:
        return "", ""
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""

    cleaned = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<style[^>]*>.*?</style>", " ", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    text = re.sub(r"\s+", " ", cleaned).strip()
    return title, text


class ScraperEngine:
    """Extracts clean content from URLs across a multi-provider chain."""

    async def extract_content(self, url: str) -> Optional[dict]:
        """Run the provider chain until one returns content."""
        providers = [
            ("firecrawl", self._extract_firecrawl),
            ("jina", self._extract_jina),
            ("scrapingbee", self._extract_scrapingbee),
            ("scrapingbog", self._extract_scrapingbog),
            ("scrape_do", self._extract_scrapedo),
            ("apify", self._extract_apify),
        ]

        for name, fn in providers:
            try:
                result = await fn(url)
                if result and result.get("content"):
                    logger.info("scrape_success", provider=name, url=url[:80])
                    return result
            except Exception as e:
                logger.warning("scrape_failed", provider=name, url=url[:80], error=str(e))
                continue

        return None

    async def batch_extract(self, urls: list[str], max_concurrent: int = 5) -> list[dict]:
        """Extract content for many URLs concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _extract_with_limit(u: str) -> Optional[dict]:
            async with semaphore:
                return await self.extract_content(u)

        tasks = [_extract_with_limit(u) for u in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, dict)]

    # ── Provider helpers ─────────────────────────────────────────────

    async def _extract_firecrawl(self, url: str) -> Optional[dict]:
        if not settings.FIRECRAWL_API_KEY:
            return None

        async with httpx.AsyncClient(timeout=_FAST_TIMEOUT) as client:
            resp = await client.post(
                "https://api.firecrawl.dev/v1/scrape",
                json={"url": url, "formats": ["markdown"]},
                headers={"Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()

        result = data.get("data", {}) or {}
        markdown = (result.get("markdown") or "").strip()
        if not markdown:
            return None
        return {
            "url": url,
            "title": (result.get("metadata", {}) or {}).get("title", "") or "",
            "content": markdown[:_MAX_CONTENT_CHARS],
            "source": "firecrawl",
        }

    async def _extract_jina(self, url: str) -> Optional[dict]:
        if not settings.JINA_API_KEY:
            return None

        async with httpx.AsyncClient(timeout=_FAST_TIMEOUT) as client:
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

        body = data.get("data", {}) or {}
        content = (body.get("content") or "").strip()
        if not content:
            return None
        return {
            "url": url,
            "title": body.get("title", "") or "",
            "content": content[:_MAX_CONTENT_CHARS],
            "source": "jina",
        }

    async def _extract_scrapingbee(self, url: str) -> Optional[dict]:
        """ScrapingBee — render-capable HTML fetcher.

        Endpoint: ``GET https://app.scrapingbee.com/api/v1/``
        Params:   ``api_key``, ``url``, ``render_js`` (bool string).
        """
        pool = get_pool("scrapingbee", settings.scrapingbee_keys)
        if pool.empty:
            return None
        key = await pool.acquire()
        if not key:
            return None
        try:
            async with httpx.AsyncClient(timeout=_FAST_TIMEOUT) as client:
                resp = await client.get(
                    "https://app.scrapingbee.com/api/v1/",
                    params={
                        "api_key": key,
                        "url": url,
                        "render_js": "false",
                    },
                )
                resp.raise_for_status()
                html = resp.text
            await pool.report_success(key)
        except Exception as e:
            await pool.report_failure(key, _classify_status(e))
            raise

        if not html or len(html) < 100:
            return None
        title, text = _strip_html(html)
        if not text:
            return None
        return {
            "url": url,
            "title": title,
            "content": text[:_MAX_CONTENT_CHARS],
            "source": "scrapingbee",
        }

    async def _extract_scrapingbog(self, url: str) -> Optional[dict]:
        """ScrapingDog (alias ``scrapingbog`` per env layout).

        Endpoint: ``GET https://api.scrapingdog.com/scrape``
        Params:   ``api_key``, ``url``, ``dynamic`` (bool string).
        """
        pool = get_pool("scrapingbog", settings.scrapingbog_keys)
        if pool.empty:
            return None
        key = await pool.acquire()
        if not key:
            return None
        try:
            async with httpx.AsyncClient(timeout=_FAST_TIMEOUT) as client:
                resp = await client.get(
                    "https://api.scrapingdog.com/scrape",
                    params={
                        "api_key": key,
                        "url": url,
                        "dynamic": "false",
                    },
                )
                resp.raise_for_status()
                html = resp.text
            await pool.report_success(key)
        except Exception as e:
            await pool.report_failure(key, _classify_status(e))
            raise

        if not html or len(html) < 100:
            return None
        title, text = _strip_html(html)
        if not text:
            return None
        return {
            "url": url,
            "title": title,
            "content": text[:_MAX_CONTENT_CHARS],
            "source": "scrapingbog",
        }

    async def _extract_scrapedo(self, url: str) -> Optional[dict]:
        """Scrape.do — proxy with optional headless render.

        Endpoint: ``GET https://api.scrape.do/``
        Params:   ``token``, ``url``, ``render`` (bool string).

        Uses the pooled ``scrape_do`` keys (legacy ``SCRAPE_DO_API_KEY`` is
        included in the pool by config so existing single-key callers keep
        working while new requests benefit from rotation).
        """
        pool = get_pool("scrape_do", settings.scrape_do_keys)
        if pool.empty:
            return None
        key = await pool.acquire()
        if not key:
            return None
        try:
            async with httpx.AsyncClient(timeout=_FAST_TIMEOUT) as client:
                resp = await client.get(
                    "https://api.scrape.do/",
                    params={
                        "token": key,
                        "url": url,
                        "render": "false",
                    },
                )
                resp.raise_for_status()
                html = resp.text
            await pool.report_success(key)
        except Exception as e:
            await pool.report_failure(key, _classify_status(e))
            raise

        if not html or len(html) < 100:
            return None
        title, text = _strip_html(html)
        if not text:
            return None
        return {
            "url": url,
            "title": title,
            "content": text[:_MAX_CONTENT_CHARS],
            "source": "scrape_do",
        }

    async def _extract_apify(self, url: str) -> Optional[dict]:
        """Apify — last-resort heavy-duty extractor via Website Content Crawler.

        Endpoint: ``POST https://api.apify.com/v2/acts/apify~website-content-crawler/run-sync-get-dataset-items``
        Auth:     ``token`` query param.
        Input:    ``{"startUrls":[{"url":...}], "maxCrawlDepth":0, "maxResults":1}``

        Apify is intentionally last in the chain — it can take 30–60s because
        it spins up an Actor. We use a longer timeout and accept the latency
        only when every cheaper provider has already failed.
        """
        pool = get_pool("apify", settings.apify_keys)
        if pool.empty:
            return None
        key = await pool.acquire()
        if not key:
            return None
        endpoint = (
            "https://api.apify.com/v2/acts/apify~website-content-crawler/"
            "run-sync-get-dataset-items"
        )
        payload = {
            "startUrls": [{"url": url}],
            "maxCrawlDepth": 0,
            "maxCrawlPages": 1,
            "maxResults": 1,
            "saveMarkdown": True,
            "saveHtml": False,
            "crawlerType": "cheerio",
        }
        try:
            async with httpx.AsyncClient(timeout=_APIFY_TIMEOUT) as client:
                resp = await client.post(
                    endpoint,
                    params={"token": key, "format": "json"},
                    json=payload,
                )
                resp.raise_for_status()
                items = resp.json()
            await pool.report_success(key)
        except Exception as e:
            await pool.report_failure(key, _classify_status(e))
            raise

        if not isinstance(items, list) or not items:
            return None
        first = items[0] or {}
        # Apify returns ``markdown`` for cheerio crawler; ``text`` is also
        # present on some actors. Prefer markdown when both exist.
        content = (first.get("markdown") or first.get("text") or "").strip()
        if not content:
            return None
        metadata = first.get("metadata") or {}
        return {
            "url": first.get("url") or url,
            "title": (metadata.get("title") or first.get("title") or "") or "",
            "content": content[:_MAX_CONTENT_CHARS],
            "source": "apify",
        }
