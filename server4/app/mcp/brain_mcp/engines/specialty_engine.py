"""
Specialty data engine for facts, quotes, company info, historical events,
and science imagery via API Ninjas and NASA APOD.
"""

from typing import Optional

import httpx

from app.config import settings

import structlog

logger = structlog.get_logger()


class SpecialtyEngine:
    """Fetches specialty data from API Ninjas and NASA."""

    _NINJAS_BASE = "https://api.api-ninjas.com/v1"

    @staticmethod
    async def _ninjas_get(endpoint: str, params: Optional[dict] = None) -> dict:
        """Shared helper for API Ninjas GET requests."""
        if not settings.API_NINJAS_KEY:
            raise ConnectionError("API Ninjas not configured")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{SpecialtyEngine._NINJAS_BASE}/{endpoint}",
                params=params or {},
                headers={"X-Api-Key": settings.API_NINJAS_KEY},
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    async def get_facts(topic: str) -> list[dict]:
        """Get interesting facts from API Ninjas.

        API: GET https://api.api-ninjas.com/v1/facts
        Header: X-Api-Key
        Note: The facts endpoint returns random facts; topic is not a filter
        param but we log it for context.
        """
        try:
            data = await SpecialtyEngine._ninjas_get("facts")
            # API returns a list of {"fact": "..."} objects
            results = []
            if isinstance(data, list):
                for item in data:
                    results.append({
                        "fact": item.get("fact", ""),
                        "topic": topic,
                        "provider": "api_ninjas",
                    })
            return results
        except Exception as e:
            logger.warning("ninjas_facts_failed", topic=topic, error=str(e))
            return []

    @staticmethod
    async def get_quotes(category: str = "business") -> list[dict]:
        """Get quotes from API Ninjas.

        API: GET https://api.api-ninjas.com/v1/quotes?category={category}
        Categories: business, success, leadership, technology, etc.
        """
        try:
            data = await SpecialtyEngine._ninjas_get(
                "quotes", params={"category": category}
            )
            results = []
            if isinstance(data, list):
                for item in data:
                    results.append({
                        "quote": item.get("quote", ""),
                        "author": item.get("author", ""),
                        "category": item.get("category", category),
                        "provider": "api_ninjas",
                    })
            return results
        except Exception as e:
            logger.warning("ninjas_quotes_failed", category=category, error=str(e))
            return []

    @staticmethod
    async def get_company_info(name: str) -> dict:
        """Get company data from API Ninjas.

        API: GET https://api.api-ninjas.com/v1/company?name={name}
        Returns: ticker, revenue, employees, industry, founded year, etc.
        """
        try:
            data = await SpecialtyEngine._ninjas_get(
                "company", params={"name": name}
            )
            if isinstance(data, list) and data:
                c = data[0]
                return {
                    "name": c.get("name", name),
                    "ticker": c.get("ticker", ""),
                    "revenue": c.get("revenue"),
                    "employees": c.get("number_of_employees"),
                    "industry": c.get("industry", ""),
                    "sector": c.get("sector", ""),
                    "founded_year": c.get("founded"),
                    "headquarters": c.get("headquarters", ""),
                    "ceo": c.get("ceo", ""),
                    "provider": "api_ninjas",
                }
            return {"name": name, "error": "No data found", "provider": "api_ninjas"}
        except Exception as e:
            logger.warning("ninjas_company_failed", name=name, error=str(e))
            return {"name": name, "error": str(e), "provider": "api_ninjas"}

    @staticmethod
    async def get_nasa_apod() -> dict:
        """Get NASA Astronomy Picture of the Day.

        API: GET https://api.nasa.gov/planetary/apod?api_key={key}
        Falls back to DEMO_KEY if no key is configured (low rate limit).
        """
        api_key = settings.NASA_APOD_API_KEY or "DEMO_KEY"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.nasa.gov/planetary/apod",
                    params={"api_key": api_key},
                )
                resp.raise_for_status()
                data = resp.json()

            return {
                "title": data.get("title", ""),
                "explanation": data.get("explanation", ""),
                "url": data.get("url", ""),
                "hdurl": data.get("hdurl", ""),
                "date": data.get("date", ""),
                "media_type": data.get("media_type", ""),
                "copyright": data.get("copyright", ""),
                "provider": "nasa_apod",
            }
        except Exception as e:
            logger.warning("nasa_apod_failed", error=str(e))
            return {"error": str(e), "provider": "nasa_apod"}

    @staticmethod
    async def get_historical_events(
        year: int, month: int, day: int
    ) -> list[dict]:
        """Get historical events from API Ninjas.

        API: GET https://api.api-ninjas.com/v1/historicalevents
        Params: year, month, day (all optional)
        """
        try:
            params = {}
            if year:
                params["year"] = str(year)
            if month:
                params["month"] = str(month)
            if day:
                params["day"] = str(day)

            data = await SpecialtyEngine._ninjas_get(
                "historicalevents", params=params
            )

            results = []
            if isinstance(data, list):
                for item in data:
                    results.append({
                        "year": item.get("year", ""),
                        "month": item.get("month", ""),
                        "day": item.get("day", ""),
                        "event": item.get("event", ""),
                        "provider": "api_ninjas",
                    })
            return results
        except Exception as e:
            logger.warning(
                "ninjas_historical_failed",
                year=year,
                month=month,
                day=day,
                error=str(e),
            )
            return []
