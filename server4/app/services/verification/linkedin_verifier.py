"""
LinkedIn profile verification.
Uses Serper (already in stack) and optional Proxycurl/Scrapin + scrape-do.
Free approach: Google search via Serper for LinkedIn public page snippets.
"""

from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel
from rapidfuzz import fuzz

from app.config import settings
from app.services.llm.model_router import ModelRouter, TaskType


class LinkedInVerificationResult(BaseModel):
    url: Optional[str] = None
    exists: bool = False
    name_match_score: float = 0.0  # 0-100
    headline: Optional[str] = None
    company_in_headline: bool = False
    connection_count: Optional[int] = None
    error: Optional[str] = None


class LinkedInVerifier:
    """Async LinkedIn verifier using your existing search APIs."""

    def __init__(self):
        self.serper_keys = settings.serper_keys
        self.scrape_do_key = settings.SCRAPE_DO_API_KEY

    async def verify(
        self, linkedin_url: Optional[str], claimed_name: str, claimed_company: Optional[str] = None
    ) -> LinkedInVerificationResult:
        result = LinkedInVerificationResult(url=linkedin_url)

        if not linkedin_url:
            result.error = "No LinkedIn URL provided"
            return result

        # Normalize URL
        if not linkedin_url.startswith("http"):
            linkedin_url = f"https://{linkedin_url}"
        result.url = linkedin_url

        # Strategy 1: Try direct scrape via scrape-do proxy
        page_data = await self._scrape_via_proxy(linkedin_url)
        if page_data:
            result.exists = True
            result.headline = page_data.get("headline")
            result.name_match_score = self._score_name_match(
                claimed_name, page_data.get("name", "")
            )
            if claimed_company and result.headline:
                result.company_in_headline = claimed_company.lower() in result.headline.lower()
            return result

        # Strategy 2: Serper Google search for public snippet
        search_data = await self._search_via_serper(claimed_name, claimed_company)
        if search_data:
            result.exists = search_data.get("found", False)
            result.headline = search_data.get("headline")
            result.name_match_score = self._score_name_match(
                claimed_name, search_data.get("name", claimed_name)
            )
            if claimed_company:
                text = f"{search_data.get('headline', '')} {search_data.get('snippet', '')}"
                result.company_in_headline = claimed_company.lower() in text.lower()

        return result

    async def _scrape_via_proxy(self, url: str) -> Optional[Dict[str, str]]:
        """Scrape LinkedIn public page via ScrapeDo proxy (if key available)."""
        if not self.scrape_do_key:
            return None
        proxy_url = (
            f"https://api.scrape.do/?token={self.scrape_do_key}"
            f"&url={url}&render=true"
        )
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(proxy_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            })
            if r.status_code != 200:
                return None
            html = r.text
            # Rough heuristic extraction (improve with BeautifulSoup in production)
            name = self._extract_meta(html, "name")
            headline = self._extract_meta(html, "headline")
            if name or headline:
                return {"name": name, "headline": headline}
        return None

    async def _search_via_serper(
        self, name: str, company: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Use Serper Google search to find LinkedIn snippet."""
        if not self.serper_keys:
            return None
        query = f'"{name}" site:linkedin.com/in'
        if company:
            query += f' "{company}"'
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                "https://google.serper.dev/search",
                json={"q": query, "num": 5},
                headers={
                    "X-API-KEY": self.serper_keys[0],
                    "Content-Type": "application/json",
                },
            )
            if r.status_code != 200:
                return None
            data = r.json()
            organic = data.get("organic", [])
            if not organic:
                return None
            top = organic[0]
            snippet = top.get("snippet", "")
            title = top.get("title", "")
            # Heuristic: title often contains "Name - Title | LinkedIn"
            extracted_name = title.split("-")[0].split("|")[0].strip()
            return {
                "found": True,
                "name": extracted_name,
                "headline": title,
                "snippet": snippet,
                "link": top.get("link"),
            }

    def _score_name_match(self, claimed: str, scraped: str) -> float:
        """Fuzzy name match using RapidFuzz."""
        if not scraped:
            return 0.0
        return fuzz.token_sort_ratio(claimed.lower(), scraped.lower())

    def _extract_meta(self, html: str, key: str) -> str:
        """Crude meta extraction fallback. Use BeautifulSoup in production."""
        import re
        # Try Open Graph
        pattern = re.compile(
            rf'<meta[^>]+property=["\']og:{key}["\'][^>]+content=["\']([^"\']+)["\']',
            re.IGNORECASE,
        )
        m = pattern.search(html)
        if m:
            return m.group(1)
        # Try name variant
        pattern2 = re.compile(
            rf'<meta[^>]+name=["\']{key}["\'][^>]+content=["\']([^"\']+)["\']',
            re.IGNORECASE,
        )
        m2 = pattern2.search(html)
        if m2:
            return m2.group(1)
        return ""
