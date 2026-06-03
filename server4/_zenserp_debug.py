import asyncio
import json
import httpx
from app.config import settings


async def go():
    key = settings.zenserp_keys[0]
    print(f"Using zenserp key prefix: {key[:8]}...")
    async with httpx.AsyncClient(timeout=20) as c:
        # 3 attempts with different params
        for attempt, params in enumerate([
            {"q": "AI invoice automation 2025", "num": 5},
            {"q": "AI invoice automation 2025", "num": 5, "tbs": "qdr:y"},
            {"q": "invoice automation finance teams", "num": 5},
        ], 1):
            r = await c.get(
                "https://app.zenserp.com/api/v2/search",
                params=params,
                headers={"apikey": key},
            )
            print(f"\n--- attempt {attempt}: status={r.status_code}")
            try:
                body = r.json()
            except Exception:
                print(f"non-json body: {r.text[:300]}")
                continue
            print(f"top keys: {list(body.keys())}")
            for k in ("organic", "results", "data", "error", "message"):
                if k in body:
                    val = body[k]
                    if isinstance(val, list):
                        print(f"  {k}: list[{len(val)}]")
                        if val:
                            sample = json.dumps(val[0], indent=2)[:400]
                            print(f"  first item: {sample}")
                    else:
                        print(f"  {k}: {str(val)[:200]}")


if __name__ == "__main__":
    asyncio.run(go())
