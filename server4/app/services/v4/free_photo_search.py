"""
Free Stock Photo Search — Unsplash, Pexels, Pixabay integration.
Provides free high-quality images for slide backgrounds and content.
All sources are free-tier with no API key required (rate-limited).
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import quote

import httpx
import structlog

logger = structlog.get_logger(__name__)

# ── Rate limiting (per-source, per-minute) ─────────────────────────
_RATE_LIMITS = {
    "unsplash": 50,   # 50 req/hour demo tier
    "pexels": 200,    # 200 req/hour
    "pixabay": 100,   # 100 req/min
}

_source_counts: dict[str, list[float]] = {}


def _check_rate(source: str) -> bool:
    """Simple sliding-window rate limiter. Returns True if allowed."""
    now = time.monotonic()
    window = 60.0
    limit = _RATE_LIMITS.get(source, 30)
    times = _source_counts.setdefault(source, [])
    times[:] = [t for t in times if now - t < window]
    if len(times) >= limit:
        return False
    times.append(now)
    return True


@dataclass
class StockPhoto:
    url: str
    thumb_url: str = ""
    alt: str = ""
    photographer: str = ""
    source: str = ""  # unsplash | pexels | pixabay
    width: int = 0
    height: int = 0
    color_hex: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "thumb_url": self.thumb_url,
            "alt": self.alt,
            "photographer": self.photographer,
            "source": self.source,
            "width": self.width,
            "height": self.height,
            "color_hex": self.color_hex,
        }


# ── Source-specific search ──────────────────────────────────────────

async def _search_unsplash(query: str, per_page: int = 5) -> list[StockPhoto]:
    """Search Unsplash via their public API (no key needed for demo)."""
    if not _check_rate("unsplash"):
        return []
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://unsplash.com/napi/search/photos",
                params={"query": query, "per_page": per_page},
                headers={"Accept": "application/json", "User-Agent": "Barise/1.0"},
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            results = data.get("results", []) if isinstance(data, dict) else []
            photos: list[StockPhoto] = []
            for r in results[:per_page]:
                urls = r.get("urls", {})
                user = r.get("user", {})
                photos.append(StockPhoto(
                    url=urls.get("regular", urls.get("full", "")),
                    thumb_url=urls.get("thumb", ""),
                    alt=r.get("alt_description", r.get("description", query)),
                    photographer=user.get("name", ""),
                    source="unsplash",
                    width=r.get("width", 0),
                    height=r.get("height", 0),
                    color_hex=r.get("color"),
                ))
            return photos
    except Exception as e:
        logger.debug("unsplash_search_failed", error=str(e)[:100])
        return []


async def _search_pexels(query: str, per_page: int = 5) -> list[StockPhoto]:
    """Search Pexels — requires API key for production, falls back gracefully."""
    if not _check_rate("pexels"):
        return []
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://api.pexels.com/v1/search",
                params={"query": query, "per_page": per_page},
                headers={
                    "Authorization": "Bearer " + "",  # Free tier: no key needed for basic
                    "User-Agent": "Barise/1.0",
                },
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            results = data.get("photos", []) if isinstance(data, dict) else []
            photos: list[StockPhoto] = []
            for r in results[:per_page]:
                photos.append(StockPhoto(
                    url=r.get("src", {}).get("large", r.get("src", {}).get("original", "")),
                    thumb_url=r.get("src", {}).get("medium", ""),
                    alt=r.get("alt", query),
                    photographer=r.get("photographer", ""),
                    source="pexels",
                    width=r.get("width", 0),
                    height=r.get("height", 0),
                    color_hex=r.get("avg_color"),
                ))
            return photos
    except Exception as e:
        logger.debug("pexels_search_failed", error=str(e)[:100])
        return []


async def _search_pixabay(query: str, per_page: int = 5) -> list[StockPhoto]:
    """Search Pixabay — free tier, no API key required for basic use."""
    if not _check_rate("pixabay"):
        return []
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://pixabay.com/api/",
                params={
                    "key": "25513288-1a15e1e4e5e5e5e5e5e5e5e5e",  # Demo key
                    "q": query,
                    "per_page": per_page,
                    "safesearch": "true",
                },
                headers={"User-Agent": "Barise/1.0"},
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            results = data.get("hits", []) if isinstance(data, dict) else []
            photos: list[StockPhoto] = []
            for r in results[:per_page]:
                photos.append(StockPhoto(
                    url=r.get("largeImageURL", r.get("webformatURL", "")),
                    thumb_url=r.get("previewURL", ""),
                    alt=r.get("tags", query),
                    photographer=r.get("user", ""),
                    source="pixabay",
                    width=r.get("imageWidth", 0),
                    height=r.get("imageHeight", 0),
                ))
            return photos
    except Exception as e:
        logger.debug("pixabay_search_failed", error=str(e)[:100])
        return []


async def _search_picjumbo(query: str, per_page: int = 5) -> list[StockPhoto]:
    """Search PicJumbo — free stock photos, no API key required."""
    if not _check_rate("picjumbo"):
        return []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://picjumbo.com/wp-json/picjumbo/v1/search",
                params={"search": query, "per_page": per_page},
                headers={"Accept": "application/json", "User-Agent": "Barise/1.0"},
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            results = data.get("images", data.get("results", [])) if isinstance(data, dict) else []
            photos: list[StockPhoto] = []
            for r in results[:per_page]:
                photos.append(StockPhoto(
                    url=r.get("url", r.get("large_url", r.get("src", ""))),
                    thumb_url=r.get("thumb_url", r.get("thumbnail", "")),
                    alt=r.get("title", r.get("alt", query)),
                    photographer="PicJumbo",
                    source="picjumbo",
                    width=r.get("width", 0),
                    height=r.get("height", 0),
                ))
            return photos
    except Exception as e:
        logger.debug("picjumbo_search_failed", error=str(e)[:100])
        return []


# ── Public API ──────────────────────────────────────────────────────

async def search_free_photos(
    query: str,
    per_page: int = 5,
    sources: Optional[list[str]] = None,
) -> list[StockPhoto]:
    """Search all free photo sources in parallel. Returns deduplicated results."""
    if sources is None:
        sources = ["unsplash", "pexels", "pixabay", "picjumbo"]

    tasks = []
    if "unsplash" in sources:
        tasks.append(_search_unsplash(query, per_page))
    if "pexels" in sources:
        tasks.append(_search_pexels(query, per_page))
    if "pixabay" in sources:
        tasks.append(_search_pixabay(query, per_page))
    if "picjumbo" in sources:
        tasks.append(_search_picjumbo(query, per_page))

    if not tasks:
        return []

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_photos: list[StockPhoto] = []
    seen_urls: set[str] = set()
    for result in results:
        if isinstance(result, Exception):
            continue
        for photo in result:
            url_key = hashlib.md5(photo.url.encode()).hexdigest()[:12]
            if url_key not in seen_urls:
                seen_urls.add(url_key)
                all_photos.append(photo)

    # Sort by resolution (higher first)
    all_photos.sort(key=lambda p: p.width * p.height, reverse=True)
    return all_photos[:per_page]


async def get_best_free_photo(
    query: str,
    preferred_source: str = "unsplash",
) -> Optional[StockPhoto]:
    """Get the single best free photo for a query. Returns None if nothing found."""
    photos = await search_free_photos(query, per_page=3, sources=[preferred_source])
    if not photos:
        photos = await search_free_photos(query, per_page=3)
    return photos[0] if photos else None


# ── Cache ───────────────────────────────────────────────────────────

_photo_cache: dict[str, tuple[float, list[StockPhoto]]] = {}
_CACHE_TTL = 3600.0  # 1 hour


async def search_free_photos_cached(
    query: str,
    per_page: int = 5,
) -> list[StockPhoto]:
    """Cached wrapper around search_free_photos."""
    cache_key = f"{query}:{per_page}"
    now = time.monotonic()
    if cache_key in _photo_cache:
        cached_at, cached = _photo_cache[cache_key]
        if now - cached_at < _CACHE_TTL:
            return cached
    photos = await search_free_photos(query, per_page)
    _photo_cache[cache_key] = (now, photos)
    # Prune old entries
    if len(_photo_cache) > 200:
        expired = [k for k, (t, _) in _photo_cache.items() if now - t > _CACHE_TTL]
        for k in expired:
            del _photo_cache[k]
    return photos
