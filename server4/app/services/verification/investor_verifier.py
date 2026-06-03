"""
Investor-specific verification.
SEC EDGAR (free, no API key), Crunchbase, and portfolio cross-reference.
"""

from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from app.config import settings


class InvestorVerificationResult(BaseModel):
    is_investor: bool = False
    sec_edgar_filing_found: bool = False
    form_adv_filed: bool = False
    cik: Optional[str] = None
    crunchbase_exists: bool = False
    portfolio_companies_verified: int = 0
    claimed_portfolio_count: int = 0
    error: Optional[str] = None


class InvestorVerifier:
    """Async investor verifier using free government and research APIs."""

    SEC_USER_AGENT = "BarisePlatform/1.0 (contact@barise.local)"

    def __init__(self):
        self.serper_keys = settings.serper_keys

    async def verify(
        self,
        name: Optional[str],
        firm_name: Optional[str],
        claimed_portfolio: Optional[List[str]] = None,
    ) -> InvestorVerificationResult:
        result = InvestorVerificationResult(
            claimed_portfolio_count=len(claimed_portfolio or [])
        )

        entity = firm_name or name
        if not entity:
            result.error = "No investor name or firm name provided"
            return result

        # 1. SEC EDGAR search (free)
        edgar = await self._search_edgar(entity)
        if edgar:
            result.sec_edgar_filing_found = edgar.get("has_filings", False)
            result.cik = edgar.get("cik")
            # Check for Form ADV (RIA registration)
            result.form_adv_filed = await self._check_form_adv(entity)

        # 2. Crunchbase existence
        result.crunchbase_exists = await self._check_crunchbase(entity)

        # 3. Portfolio company verification
        if claimed_portfolio:
            verified = 0
            for company in claimed_portfolio[:10]:  # limit checks
                if await self._company_exists(company):
                    verified += 1
            result.portfolio_companies_verified = verified

        result.is_investor = (
            result.sec_edgar_filing_found
            or result.crunchbase_exists
            or result.portfolio_companies_verified > 0
        )
        return result

    async def _search_edgar(self, entity: str) -> Optional[Dict[str, Any]]:
        """Search SEC EDGAR for entity filings.
        Endpoint: cik-submissions endpoint or browse-edgar HTML.
        Uses SEC public company search.
        """
        headers = {"User-Agent": self.SEC_USER_AGENT}
        # EDGAR search via their suggest endpoint
        search_url = f"https://www.sec.gov/cgi-bin/browse-edgar"
        params = {
            "action": "getcompany",
            "type": "",
            "dateb": "",
            "owner": "include",
            "count": "40",
            "search_text": entity,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
                r = await client.get(search_url, params=params)
                if r.status_code == 200:
                    html = r.text
                    # Heuristic: if page contains CIK or form table, entity exists
                    has_cik = "CIK=" in html or "cik=" in html
                    # Extract first CIK if present
                    import re
                    cik_match = re.search(r'CIK[=](\d+)', html)
                    cik = cik_match.group(1) if cik_match else None
                    return {"has_filings": has_cik, "cik": cik}
        except Exception as e:
            return {"has_filings": False, "error": str(e)}
        return None

    async def _check_form_adv(self, entity: str) -> bool:
        """Check if entity has filed Form ADV (Investment Adviser)."""
        headers = {"User-Agent": self.SEC_USER_AGENT}
        params = {
            "action": "getcompany",
            "type": "ADV",
            "dateb": "",
            "owner": "include",
            "count": "10",
            "search_text": entity,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
                r = await client.get(
                    "https://www.sec.gov/cgi-bin/browse-edgar", params=params
                )
                return r.status_code == 200 and "No matching " not in r.text
        except Exception:
            return False

    async def _check_crunchbase(self, entity: str) -> bool:
        """Use Serper to check if entity has a Crunchbase page."""
        if not self.serper_keys:
            return False
        query = f'"{entity}" site:crunchbase.com/organization'
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    "https://google.serper.dev/search",
                    json={"q": query, "num": 5},
                    headers={
                        "X-API-KEY": self.serper_keys[0],
                        "Content-Type": "application/json",
                    },
                )
                if r.status_code == 200:
                    organic = r.json().get("organic", [])
                    return any("crunchbase.com/organization" in item.get("link", "") for item in organic)
        except Exception:
            pass
        return False

    async def _company_exists(self, company_name: str) -> bool:
        """Check if a company exists via Google search (Serper)."""
        if not self.serper_keys:
            return False
        query = f'"{company_name}" startup OR company'
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    "https://google.serper.dev/search",
                    json={"q": query, "num": 3},
                    headers={
                        "X-API-KEY": self.serper_keys[0],
                        "Content-Type": "application/json",
                    },
                )
                if r.status_code == 200:
                    organic = r.json().get("organic", [])
                    return len(organic) > 0
        except Exception:
            pass
        return False
