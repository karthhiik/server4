"""Debug ValueSerp — print the raw response to find what we're missing."""
import asyncio
import json

import httpx

from app.config import settings


async def main():
    key = settings.valueserp_keys[0]
    print(f"Using key prefix: {key[:8]}...")
    params = {
        "api_key": key,
        "q": "AI invoice automation finance teams 2025",
        "num": 5,
        "output": "json",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get("https://api.valueserp.com/search", params=params)
        print(f"status: {r.status_code}")
        try:
            data = r.json()
        except Exception:
            print(f"non-json body: {r.text[:500]}")
            return
        # Top-level keys
        print(f"top keys: {list(data.keys())}")
        if "request_info" in data:
            print(f"request_info: {data['request_info']}")
        if "search_information" in data:
            print(f"search_information: {data['search_information']}")
        if "organic_results" in data:
            print(f"organic_results count: {len(data['organic_results'])}")
            if data["organic_results"]:
                print(f"first organic: {json.dumps(data['organic_results'][0], indent=2)[:600]}")
        else:
            print(f"NO organic_results — full body sample: {json.dumps(data, indent=2)[:1500]}")


if __name__ == "__main__":
    asyncio.run(main())
