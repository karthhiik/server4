"""
Financial data engine — Polygon.io, Financial Modeling Prep, Census.
"""

from typing import Optional

import httpx

from app.config import settings

import structlog

logger = structlog.get_logger()


class FinancialEngine:
    """Fetches financial company/stock data from Polygon, FMP, Census."""

    async def get_company_financials(self, ticker: str) -> dict:
        """Aggregate financial data for a company ticker."""
        results = {}

        polygon_data = await self._fetch_polygon_ticker(ticker)
        if polygon_data:
            results["company_info"] = polygon_data

        fmp_data = await self._fetch_fmp_profile(ticker)
        if fmp_data:
            results["profile"] = fmp_data

        return results

    async def get_census_data(self, topic: str) -> Optional[dict]:
        """Fetch US Census data for demographic/economic context."""
        if not settings.CENSUS_API_KEY:
            return None

        # Common Census variables
        variables = "NAME,B01001_001E,B19013_001E,B25077_001E"  # Pop, Median Income, Median Home Value

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.census.gov/data/2022/acs/acs5",
                    params={"get": variables, "for": "state:*", "key": settings.CENSUS_API_KEY},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if len(data) > 1:
                        headers = data[0]
                        return {"headers": headers, "sample_rows": data[1:6], "total_rows": len(data) - 1}
        except Exception as e:
            logger.warning("census_fetch_failed", error=str(e))
        return None

    async def _fetch_polygon_ticker(self, ticker: str) -> Optional[dict]:
        if not settings.POLYGON_API_KEY:
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://api.polygon.io/v3/reference/tickers/{ticker.upper()}",
                    params={"apiKey": settings.POLYGON_API_KEY},
                )
                if resp.status_code == 200:
                    result = resp.json().get("results", {})
                    return {
                        "name": result.get("name", ""),
                        "market_cap": result.get("market_cap"),
                        "description": (result.get("description") or "")[:300],
                        "homepage": result.get("homepage_url", ""),
                        "employees": result.get("total_employees"),
                        "sic_description": result.get("sic_description", ""),
                    }
        except Exception as e:
            logger.warning("polygon_fetch_failed", error=str(e))
        return None

    async def _fetch_fmp_profile(self, ticker: str) -> Optional[dict]:
        if not settings.FMP_API_KEY:
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://financialmodelingprep.com/api/v3/profile/{ticker.upper()}",
                    params={"apikey": settings.FMP_API_KEY},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data:
                        p = data[0]
                        return {
                            "company_name": p.get("companyName", ""),
                            "industry": p.get("industry", ""),
                            "sector": p.get("sector", ""),
                            "market_cap": p.get("mktCap"),
                            "price": p.get("price"),
                            "beta": p.get("beta"),
                            "revenue": p.get("revenue"),
                            "ceo": p.get("ceo", ""),
                        }
        except Exception as e:
            logger.warning("fmp_fetch_failed", error=str(e))
        return None
