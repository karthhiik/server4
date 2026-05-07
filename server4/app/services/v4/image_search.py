"""
V4 Image Search — verified person photo lookup with strict no-dummy policy.

Used by team_resolver to fetch real photos of team members. Uses the Serper
images endpoint (already wired via SERPER_KEYS) and applies layered verification:

  1. Domain allow-list — must come from a trusted source where a person photo
     is plausible (linkedin, crunchbase, github, gravatar, the company's own
     domain, or a reputable news domain).
  2. HEAD-fetch — image URL must return 200 + Content-Type: image/* + size in
     a sane range (3KB-5MB).
  3. Cross-corroboration — for non-LinkedIn/Crunchbase results, require at
     least two distinct candidates that look like the same image (matching
     filename root or domain) before accepting one.

When nothing passes verification we return None and the caller renders an
inline SVG initials avatar from `default_avatar_svg(name)`. We never reach
for stock-photo placeholders or "headshot" image generators.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import httpx
import structlog

from app.config import settings
from app.services.v4 import provider_health
from app.services.v4.key_pool import get_pool

logger = structlog.get_logger(__name__)


_TRUSTED_PHOTO_DOMAINS = {
    "media.licdn.com", "static.licdn.com",                  # LinkedIn CDN
    "images.crunchbase.com",                                 # Crunchbase CDN
    "avatars.githubusercontent.com",                         # GitHub
    "secure.gravatar.com", "www.gravatar.com",               # Gravatar
    "pbs.twimg.com",                                         # Twitter avatars
}
_TRUSTED_HOST_SUFFIXES = (
    ".linkedin.com", ".crunchbase.com", ".github.com",
    ".bloomberg.com", ".forbes.com", ".reuters.com",
    ".techcrunch.com", ".ft.com", ".wsj.com", ".hbr.org",
    ".medium.com",
)
_NEVER_PHOTO_HOSTS = {
    # Stock / pseudo-stock — explicitly banned
    "images.unsplash.com", "unsplash.com", "pexels.com",
    "images.pexels.com", "pixabay.com", "shutterstock.com",
    "istockphoto.com", "gettyimages.com",
    "thispersondoesnotexist.com",
    "ui-avatars.com", "robohash.org",
}

_MIN_BYTES = 3 * 1024
_MAX_BYTES = 5 * 1024 * 1024


@dataclass
class ImageCandidate:
    image_url: str
    source_page_url: str
    source_domain: str
    width: Optional[int] = None
    height: Optional[int] = None
    bytes: Optional[int] = None
    content_type: Optional[str] = None
    attribution: Optional[str] = None
    confidence: float = 0.0  # 0..1
    is_default_avatar: bool = False


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return ""


def _is_trusted_photo_host(url: str, allowed_company_host: Optional[str] = None) -> bool:
    host = _host(url)
    if not host or host in _NEVER_PHOTO_HOSTS:
        return False
    if host in _TRUSTED_PHOTO_DOMAINS:
        return True
    if any(host.endswith(suf) for suf in _TRUSTED_HOST_SUFFIXES):
        return True
    if allowed_company_host and host.endswith(allowed_company_host):
        return True
    return False


# ── Default avatar (deterministic SVG, embedded as data URL) ───────


_PALETTE = [
    "#1f6feb", "#0e9f6e", "#7e3af2", "#d97706", "#dc2626",
    "#0891b2", "#9333ea", "#15803d", "#b45309", "#db2777",
]


def default_avatar_svg(name: str) -> str:
    """Return a data: URL containing a deterministic SVG initials avatar.

    Same `name` always yields the same colour and initials — never random.
    """
    initials = "".join(part[0] for part in re.split(r"\s+", (name or "?").strip()) if part)[:2].upper() or "?"
    h = int(hashlib.sha256((name or "?").encode("utf-8")).hexdigest(), 16)
    bg = _PALETTE[h % len(_PALETTE)]
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
        f'<rect width="200" height="200" fill="{bg}"/>'
        '<text x="50%" y="50%" dy=".35em" text-anchor="middle" '
        'font-family="Inter,Arial,sans-serif" font-size="84" font-weight="600" '
        f'fill="#ffffff">{initials}</text>'
        '</svg>'
    )
    import base64
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def make_default_candidate(name: str, *, attribution: str = "default-avatar") -> ImageCandidate:
    return ImageCandidate(
        image_url=default_avatar_svg(name),
        source_page_url="",
        source_domain="default",
        attribution=attribution,
        confidence=0.0,
        is_default_avatar=True,
    )


# ── Provider: Serper Images ────────────────────────────────────────


async def _serper_images(client: httpx.AsyncClient, query: str, num: int = 8) -> list[dict]:
    if not provider_health.is_healthy("serper"):
        return []
    pool = get_pool("serper", settings.serper_keys)
    if pool.empty:
        return []
    key = await pool.acquire()
    if not key:
        return []
    try:
        r = await client.post(
            "https://google.serper.dev/images",
            timeout=8.0,
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            json={"q": query, "num": num},
        )
        if r.status_code != 200:
            await pool.report_failure(key, r.status_code)
            provider_health.record("serper", success=False)
            return []
        await pool.report_success(key)
        provider_health.record("serper", success=True)
        data = r.json() or {}
        return list(data.get("images") or [])
    except Exception as e:
        try:
            await pool.report_failure(key, 0)
        except Exception:
            pass
        provider_health.record("serper", success=False)
        logger.debug("image_serper_failed", error=str(e))
        return []


async def _verify_image_url(client: httpx.AsyncClient, url: str) -> Optional[dict]:
    """HEAD-fetch the image. Returns metadata dict on success, None on failure."""
    try:
        r = await client.head(
            url,
            timeout=5.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; PitchDeckBot/1.0)"},
        )
        if r.status_code != 200:
            # Some CDNs reject HEAD — try a tiny range GET as a fallback.
            r = await client.get(
                url,
                timeout=5.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; PitchDeckBot/1.0)",
                    "Range": "bytes=0-1023",
                },
            )
            if r.status_code not in (200, 206):
                return None
        ctype = (r.headers.get("content-type") or "").lower()
        if not ctype.startswith("image/"):
            return None
        clen_str = r.headers.get("content-length") or "0"
        try:
            clen = int(clen_str)
        except ValueError:
            clen = 0
        # Some CDNs omit content-length on partial responses — accept those if the
        # content-type was an image, but reject anything we can verify is too tiny.
        if clen and (clen < _MIN_BYTES or clen > _MAX_BYTES):
            return None
        return {"content_type": ctype, "bytes": clen or None}
    except Exception as e:
        logger.debug("image_verify_failed", url=url, error=str(e))
        return None


def _candidate_from_serper(item: dict) -> Optional[tuple[str, str]]:
    """Pull (image_url, source_page_url) from a Serper image result."""
    img = item.get("imageUrl") or item.get("thumbnailUrl") or ""
    page = item.get("link") or item.get("source") or ""
    if not img:
        return None
    return (img, page)


# ── Public entry ───────────────────────────────────────────────────


async def search_person_image(
    *,
    name: str,
    role_hint: Optional[str] = None,
    company: Optional[str] = None,
    company_domain: Optional[str] = None,
    timeout_s: float = 12.0,
) -> ImageCandidate:
    """Find a verified photo of `name`. Returns a real ImageCandidate when
    verification passes, otherwise a default-avatar candidate.
    Never returns a stock photo, AI-generated placeholder, or a `ui-avatars.com`
    URL — caller can rely on `is_default_avatar` to know which they got.
    """
    if not name or not name.strip():
        return make_default_candidate("?")

    queries: list[str] = []
    n = name.strip()
    if company:
        queries.append(f'"{n}" {company} headshot site:linkedin.com/in')
        queries.append(f'"{n}" {company} portrait')
    if role_hint:
        queries.append(f'"{n}" {role_hint} headshot')
    queries.append(f'"{n}" CEO founder headshot')
    queries.append(f'"{n}" linkedin profile photo')

    start = time.perf_counter()
    seen_imgs: set[str] = set()
    seen_hosts: dict[str, int] = {}
    candidates: list[tuple[str, str, str]] = []  # (image_url, page_url, host)

    async with httpx.AsyncClient() as client:
        for q in queries:
            if (time.perf_counter() - start) * 1000 > timeout_s * 1000:
                break
            results = await _serper_images(client, q, num=8)
            for item in results:
                pair = _candidate_from_serper(item)
                if not pair:
                    continue
                img_url, page_url = pair
                if img_url in seen_imgs:
                    continue
                seen_imgs.add(img_url)
                if not _is_trusted_photo_host(img_url, allowed_company_host=company_domain):
                    continue
                host = _host(img_url)
                seen_hosts[host] = seen_hosts.get(host, 0) + 1
                candidates.append((img_url, page_url, host))

        # Verification pass — try LinkedIn/Crunchbase/GitHub CDN first (highest trust).
        priority_hosts = ("media.licdn.com", "static.licdn.com",
                          "images.crunchbase.com", "avatars.githubusercontent.com")

        def _priority(c: tuple[str, str, str]) -> int:
            host = c[2]
            for i, h in enumerate(priority_hosts):
                if host == h:
                    return i
            return len(priority_hosts)

        for img_url, page_url, host in sorted(candidates, key=_priority):
            if (time.perf_counter() - start) * 1000 > timeout_s * 1000:
                break
            meta = await _verify_image_url(client, img_url)
            if not meta:
                continue
            # For non-priority hosts require at least 2 separate references
            # OR a clear company-domain match.
            is_priority = host in priority_hosts
            cross = seen_hosts.get(host, 0) >= 2
            company_match = bool(company_domain and host.endswith(company_domain))
            if not (is_priority or cross or company_match):
                continue
            confidence = 0.95 if is_priority else (0.8 if company_match else 0.65)
            logger.info(
                "v4_person_image_resolved",
                name=name, host=host, company=company,
                confidence=confidence,
                duration_ms=int((time.perf_counter() - start) * 1000),
            )
            return ImageCandidate(
                image_url=img_url,
                source_page_url=page_url,
                source_domain=host,
                content_type=meta.get("content_type"),
                bytes=meta.get("bytes"),
                attribution=host,
                confidence=confidence,
            )

    logger.info(
        "v4_person_image_default",
        name=name, company=company,
        n_candidates_seen=len(candidates),
        duration_ms=int((time.perf_counter() - start) * 1000),
    )
    return make_default_candidate(name)
