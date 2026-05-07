"""One-shot verification of v4 slide + image generation health.

Reads the most recent presentations + slides from MongoDB and reports:
  - How many slides each recent presentation has
  - Whether requested slide count matches actual slide count
  - How many slides have a non-null image_url (per the new persistence path)
  - The latest WS image events implied by image_source provenance
"""
from __future__ import annotations

import asyncio
import os
from collections import Counter
from datetime import datetime, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

MONGO_URI = os.environ["MONGODB_URI"]
DB_NAME = os.environ.get("MONGODB_DB_NAME", "barise_auth_db")


async def main() -> None:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]

    print(f"DB: {DB_NAME}\n")

    # ── Recent presentations ──
    presentations = await db.presentations.find(
        {}, sort=[("created_at", -1)]
    ).to_list(length=10)
    if not presentations:
        print("No presentations found.")
        return

    print(f"Found {len(presentations)} recent presentations.\n")

    for pres in presentations:
        pid = pres.get("_id")
        title = pres.get("title") or pres.get("topic") or "(no title)"
        mode = pres.get("mode") or "(no mode)"
        purpose = pres.get("purpose") or "(no purpose)"
        requested = (
            pres.get("requested_slide_count")
            or pres.get("slide_count")
            or pres.get("target_slide_count")
        )
        created = pres.get("created_at")
        if isinstance(created, datetime):
            created = created.astimezone(timezone.utc).isoformat()

        slides = await db.slides.find(
            {"$or": [{"presentation_id": pid}, {"project_id": pid}]}
        ).sort("index", 1).to_list(length=200)

        n = len(slides)
        with_img = sum(1 for s in slides if s.get("image_url"))
        sources = Counter(s.get("image_source") for s in slides if s.get("image_url"))

        match = "OK" if (requested is None or requested == n) else f"MISMATCH (req={requested})"

        print(f"[{created}]  {pid}")
        print(f"  title       : {title[:80]}")
        print(f"  mode/purpose: {mode} / {purpose}")
        print(f"  slides      : {n}  ({match})")
        print(f"  with image  : {with_img}/{n}")
        if sources:
            src_str = ", ".join(f"{k or 'unknown'}={v}" for k, v in sources.items())
            print(f"  image tiers : {src_str}")
        if slides:
            sample = slides[0]
            print(f"  sample slide: idx={sample.get('index')} layout={sample.get('layout')} "
                  f"headline={(sample.get('headline') or '')[:60]!r} "
                  f"image_url={'YES' if sample.get('image_url') else 'no'}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
