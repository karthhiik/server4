"""
Crypto and historical financial data engine using CoinDesk and EODHD APIs.
"""

from datetime import datetime, timedelta
from typing import Optional

import httpx

from app.config import settings

import structlog

logger = structlog.get_logger()


class CryptoEngine:
    """Fetches crypto market data from CoinDesk and historical data from EODHD."""

    @staticmethod
    async def get_crypto_price(symbol: str = "BTC") -> dict:
        """Get current crypto price from CoinDesk API v2.

        API: https://api.coindesk.com/v2/price/spot?currency=USD
        CoinDesk v2 is public (no key required for basic spot), but we pass
        the key via header when available for higher rate limits.
        """
        try:
            headers = {"Accept": "application/json"}
            if settings.COINDESK_API_KEY:
                headers["x-api-key"] = settings.COINDESK_API_KEY

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.coindesk.com/v2/price/spot",
                    params={"currency": "USD", "asset": symbol.upper()},
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

            price_data = data.get("data", {})
            return {
                "symbol": symbol.upper(),
                "price_usd": price_data.get("amount"),
                "currency": "USD",
                "timestamp": price_data.get("timestamp", ""),
                "provider": "coindesk",
            }
        except Exception as e:
            logger.warning("coindesk_price_failed", symbol=symbol, error=str(e))
            return {"symbol": symbol.upper(), "price_usd": None, "error": str(e), "provider": "coindesk"}

    @staticmethod
    async def get_crypto_historical(symbol: str, days: int = 30) -> dict:
        """Get historical crypto data from CoinDesk.

        API: https://api.coindesk.com/v1/bpi/historical/close.json
        The v1 BPI endpoint is public and returns daily close prices.
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.coindesk.com/v1/bpi/historical/close.json",
                    params={
                        "start": start_date.strftime("%Y-%m-%d"),
                        "end": end_date.strftime("%Y-%m-%d"),
                        "currency": "USD",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            bpi = data.get("bpi", {})
            prices = [{"date": k, "price": v} for k, v in sorted(bpi.items())]
            return {
                "symbol": symbol.upper(),
                "days": days,
                "data_points": len(prices),
                "prices": prices,
                "provider": "coindesk",
            }
        except Exception as e:
            logger.warning("coindesk_historical_failed", symbol=symbol, error=str(e))
            return {"symbol": symbol.upper(), "prices": [], "error": str(e), "provider": "coindesk"}

    @staticmethod
    async def get_eodhd_fundamentals(ticker: str) -> dict:
        """Get fundamental data from EODHD API.

        API: https://eodhd.com/api/fundamentals/{ticker}.US?api_token={key}&fmt=json
        Returns: company overview, financials, valuation metrics.
        """
        if not settings.EODHD_API_KEY:
            return {"ticker": ticker, "error": "EODHD not configured", "provider": "eodhd"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"https://eodhd.com/api/fundamentals/{ticker}.US",
                    params={"api_token": settings.EODHD_API_KEY, "fmt": "json"},
                )
                resp.raise_for_status()
                data = resp.json()

            general = data.get("General", {})
            highlights = data.get("Highlights", {})
            valuation = data.get("Valuation", {})

            return {
                "ticker": ticker,
                "name": general.get("Name", ""),
                "sector": general.get("Sector", ""),
                "industry": general.get("Industry", ""),
                "market_cap": highlights.get("MarketCapitalization"),
                "pe_ratio": highlights.get("PERatio"),
                "eps": highlights.get("EarningsShare"),
                "dividend_yield": highlights.get("DividendYield"),
                "revenue": highlights.get("Revenue"),
                "profit_margin": highlights.get("ProfitMargin"),
                "enterprise_value": valuation.get("EnterpriseValue"),
                "provider": "eodhd",
            }
        except Exception as e:
            logger.warning("eodhd_fundamentals_failed", ticker=ticker, error=str(e))
            return {"ticker": ticker, "error": str(e), "provider": "eodhd"}

    @staticmethod
    async def get_eodhd_macro(
        country: str = "USA", indicator: str = "gdp_current_usd"
    ) -> dict:
        """Get macroeconomic indicators from EODHD.

        API: https://eodhd.com/api/macro-indicator/{country}
        Indicators: gdp_current_usd, inflation_consumer_prices_annual,
                    population_total, unemployment_total, etc.
        """
        if not settings.EODHD_API_KEY:
            return {"country": country, "error": "EODHD not configured", "provider": "eodhd"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://eodhd.com/api/macro-indicator/{country}",
                    params={
                        "api_token": settings.EODHD_API_KEY,
                        "indicator": indicator,
                        "fmt": "json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            # EODHD returns a list of observations sorted by date
            if isinstance(data, list) and data:
                # Take last 5 data points for trend
                recent = data[-5:] if len(data) >= 5 else data
                return {
                    "country": country,
                    "indicator": indicator,
                    "latest_value": data[-1].get("Value") if data else None,
                    "latest_date": data[-1].get("Date") if data else None,
                    "trend": [
                        {"date": d.get("Date"), "value": d.get("Value")}
                        for d in recent
                    ],
                    "total_observations": len(data),
                    "provider": "eodhd",
                }
            return {
                "country": country,
                "indicator": indicator,
                "data": data,
                "provider": "eodhd",
            }
        except Exception as e:
            logger.warning(
                "eodhd_macro_failed",
                country=country,
                indicator=indicator,
                error=str(e),
            )
            return {"country": country, "indicator": indicator, "error": str(e), "provider": "eodhd"}

    @staticmethod
    async def get_eodhd_historical(
        ticker: str, period: str = "m", days: int = 365
    ) -> dict:
        """Get end-of-day historical prices from EODHD.

        API: https://eodhd.com/api/eod/{ticker}.US?period={d|w|m}&fmt=json
        period: 'd' daily, 'w' weekly, 'm' monthly
        """
        if not settings.EODHD_API_KEY:
            return {"ticker": ticker, "error": "EODHD not configured", "provider": "eodhd"}

        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://eodhd.com/api/eod/{ticker}.US",
                    params={
                        "api_token": settings.EODHD_API_KEY,
                        "period": period,
                        "from": start_date.strftime("%Y-%m-%d"),
                        "to": end_date.strftime("%Y-%m-%d"),
                        "fmt": "json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            if isinstance(data, list):
                prices = [
                    {
                        "date": d.get("date"),
                        "open": d.get("open"),
                        "high": d.get("high"),
                        "low": d.get("low"),
                        "close": d.get("close"),
                        "volume": d.get("volume"),
                    }
                    for d in data
                ]
                return {
                    "ticker": ticker,
                    "period": period,
                    "data_points": len(prices),
                    "prices": prices,
                    "provider": "eodhd",
                }
            return {"ticker": ticker, "prices": [], "provider": "eodhd"}
        except Exception as e:
            logger.warning("eodhd_historical_failed", ticker=ticker, error=str(e))
            return {"ticker": ticker, "prices": [], "error": str(e), "provider": "eodhd"}
