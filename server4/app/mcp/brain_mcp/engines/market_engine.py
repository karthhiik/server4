"""
Market data engine — aggregates data from FRED, Census, World Bank,
Alpha Vantage, Finnhub, and Financial Modeling Prep.
"""

from typing import Optional

import httpx

from app.config import settings

import structlog

logger = structlog.get_logger()


class MarketDataEngine:
    """Fetches market, financial, and economic data from multiple APIs."""

    async def get_market_overview(self, industry: str) -> dict:
        """Aggregate market data from multiple sources."""
        results = {}

        # Try FRED for economic indicators
        fred_data = await self._fetch_fred_data(industry)
        if fred_data:
            results["economic_indicators"] = fred_data

        # Try Alpha Vantage for sector performance
        sector_data = await self._fetch_sector_performance()
        if sector_data:
            results["sector_performance"] = sector_data

        # Try Finnhub for market news
        news = await self._fetch_finnhub_news(industry)
        if news:
            results["market_news"] = news

        # Try EODHD for macro indicators
        macro_data = await self._fetch_eodhd_macro(industry)
        if macro_data:
            results["macro_indicators"] = macro_data

        return results

    async def _fetch_fred_data(self, topic: str) -> Optional[dict]:
        """Fetch economic data from FRED (Federal Reserve)."""
        if not settings.FRED_API_KEY:
            return None

        # Key series IDs for common economic indicators
        series_map = {
            "gdp": "GDP",
            "unemployment": "UNRATE",
            "inflation": "CPIAUCSL",
            "interest_rate": "FEDFUNDS",
            "consumer_spending": "PCE",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                data = {}
                for name, series_id in series_map.items():
                    resp = await client.get(
                        "https://api.stlouisfed.org/fred/series/observations",
                        params={
                            "series_id": series_id,
                            "api_key": settings.FRED_API_KEY,
                            "file_type": "json",
                            "sort_order": "desc",
                            "limit": 4,
                        },
                    )
                    if resp.status_code == 200:
                        obs = resp.json().get("observations", [])
                        if obs:
                            data[name] = {
                                "value": obs[0].get("value"),
                                "date": obs[0].get("date"),
                            }
                return data if data else None
        except Exception as e:
            logger.warning("fred_fetch_failed", error=str(e))
            return None

    async def _fetch_sector_performance(self) -> Optional[dict]:
        """Fetch sector performance from Alpha Vantage."""
        if not settings.ALPHA_VANTAGE_API_KEY:
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://www.alphavantage.co/query",
                    params={
                        "function": "SECTOR",
                        "apikey": settings.ALPHA_VANTAGE_API_KEY,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # Extract real-time and 1-year performance
                    realtime = data.get("Rank A: Real-Time Performance", {})
                    yearly = data.get("Rank G: Year Performance", {})
                    return {"realtime": realtime, "yearly": yearly}
        except Exception as e:
            logger.warning("alpha_vantage_failed", error=str(e))
        return None

    async def _fetch_finnhub_news(self, topic: str) -> Optional[list]:
        """Fetch market news from Finnhub."""
        if not settings.FINNHUB_API_KEY:
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://finnhub.io/api/v1/news",
                    params={
                        "category": "general",
                        "token": settings.FINNHUB_API_KEY,
                    },
                )
                if resp.status_code == 200:
                    articles = resp.json()[:5]
                    return [
                        {"headline": a.get("headline", ""), "source": a.get("source", ""), "url": a.get("url", "")}
                        for a in articles
                    ]
        except Exception as e:
            logger.warning("finnhub_failed", error=str(e))
        return None

    async def _fetch_eodhd_macro(self, topic: str) -> Optional[dict]:
        """EODHD macroeconomic indicators.

        Fetches GDP and inflation data from EODHD for the USA.
        API: https://eodhd.com/api/macro-indicator/{country}
        """
        if not settings.EODHD_API_KEY:
            return None

        indicators = {
            "gdp": "gdp_current_usd",
            "inflation": "inflation_consumer_prices_annual",
            "unemployment": "unemployment_total",
        }

        try:
            data = {}
            async with httpx.AsyncClient(timeout=10.0) as client:
                for name, indicator in indicators.items():
                    resp = await client.get(
                        "https://eodhd.com/api/macro-indicator/USA",
                        params={
                            "api_token": settings.EODHD_API_KEY,
                            "indicator": indicator,
                            "fmt": "json",
                        },
                    )
                    if resp.status_code == 200:
                        obs = resp.json()
                        if isinstance(obs, list) and obs:
                            latest = obs[-1]
                            data[name] = {
                                "value": latest.get("Value"),
                                "date": latest.get("Date"),
                            }
            return data if data else None
        except Exception as e:
            logger.warning("eodhd_macro_failed", topic=topic, error=str(e))
            return None
