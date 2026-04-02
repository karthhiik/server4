"""
Academic research engine — CORE API for academic papers.
"""

from typing import Optional

import httpx

from app.config import settings

import structlog

logger = structlog.get_logger()


class AcademicEngine:
    """Searches academic papers via CORE API."""

    async def search_papers(self, query: str, max_results: int = 5) -> list[dict]:
        """Search academic papers using CORE."""
        if not settings.CORE_API_KEY:
            return []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://api.core.ac.uk/v3/search/works",
                    params={"q": query, "limit": max_results},
                    headers={"Authorization": f"Bearer {settings.CORE_API_KEY}"},
                )
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("results", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "authors": [a.get("name", "") for a in item.get("authors", [])[:3]],
                    "year": item.get("yearPublished"),
                    "abstract": (item.get("abstract") or "")[:300],
                    "url": item.get("downloadUrl") or item.get("sourceFulltextUrls", [""])[0] if item.get("sourceFulltextUrls") else "",
                    "citations": item.get("citationCount", 0),
                })

            logger.info("academic_search_success", count=len(results))
            return results
        except Exception as e:
            logger.warning("academic_search_failed", error=str(e))
            return []
