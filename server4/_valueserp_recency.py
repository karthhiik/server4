import asyncio
import httpx
from app.config import settings


async def go():
    async with httpx.AsyncClient(timeout=20) as c:
        params = {
            "api_key": settings.valueserp_keys[0],
            "q": "invoice automation 2025",
            "num": 5,
            "output": "json",
            "time_period": "last_year",
        }
        r = await c.get("https://api.valueserp.com/search", params=params)
        body = r.json()
        print("status:", r.status_code)
        print("top keys:", list(body.keys()))
        print("organic count:", len(body.get("organic_results", [])))
        # Try without time_period to see if that's the culprit
        params2 = dict(params)
        params2.pop("time_period")
        r2 = await c.get("https://api.valueserp.com/search", params=params2)
        body2 = r2.json()
        print("without time_period:", r2.status_code, "organic:", len(body2.get("organic_results", [])))


if __name__ == "__main__":
    asyncio.run(go())
