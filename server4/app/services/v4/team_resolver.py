"""
V4 Team Resolver — produce structured `TeamMember` objects for the team slide.

Resolution order (each step short-circuits if it returns at least 1 member):

  1. User-supplied (interactive answer or premium structured input)
  2. Uploaded document chunks (regex over uploaded research citations only)
  3. Company-preflight team_seed_urls (verified LinkedIn /in/ profiles)
  4. (Premium only) one targeted Serper search for "<company> founders team"
     restricted to linkedin.com/in and crunchbase.com
  5. Fallback: empty list — caller decides whether to ask the user

After resolution, every member gets a verified photo via `image_search` —
either a real URL (LinkedIn CDN, Crunchbase, GitHub, etc.) or a deterministic
SVG initials avatar. Never a stock photo.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

import httpx
import structlog

from app.config import settings
from app.services.v4 import provider_health
from app.services.v4.image_search import (
    ImageCandidate,
    make_default_candidate,
    search_person_image,
)
from app.services.v4.key_pool import get_pool
from app.services.v4.research_collector import Citation, ResearchPacket

logger = structlog.get_logger(__name__)


# ── Data model ─────────────────────────────────────────────────────


@dataclass
class TeamMember:
    name: str
    role: Optional[str] = None
    bio: Optional[str] = None
    linkedin_url: Optional[str] = None
    photo_url: Optional[str] = None
    photo_source: Optional[str] = None
    photo_attribution: Optional[str] = None
    is_default_avatar: bool = False
    source: str = "unknown"  # "user" | "uploaded_document" | "preflight" | "search"
    confidence: float = 0.0  # 0..1

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


# ── Extraction helpers ─────────────────────────────────────────────


_ROLE_TOKEN = (
    r"(?:CEO|CTO|CFO|COO|CMO|CRO|CPO|CDO|CIO|"
    r"Co-?[Ff]ounder|Founder|Founding\s+Engineer|"
    r"VP\s+(?:of\s+)?[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?|"
    r"Head\s+of\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?|"
    r"President|Chairman|Chairwoman|Director|Engineering\s+Lead)"
)
# "Jane Doe, CEO" / "Jane Doe — Co-founder" / "CEO Jane Doe" / "CEO: Jane Doe"
_NAME_THEN_ROLE = re.compile(
    rf"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){{1,3}})\s*[,—\-:|·]\s*({_ROLE_TOKEN})\b"
)
_ROLE_THEN_NAME = re.compile(
    rf"\b({_ROLE_TOKEN})\s*[:\-—]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){{1,3}})\b"
)
# "/in/jane-doe-12345"
_LINKEDIN_HANDLE_RE = re.compile(r"linkedin\.com/in/([a-zA-Z0-9\-_%]+)", re.IGNORECASE)


def _name_from_handle(handle: str) -> str:
    """Convert "jane-doe-1234" → "Jane Doe"."""
    parts = re.split(r"[-_%]+", handle)
    parts = [p for p in parts if p and not p.isdigit() and len(p) <= 20]
    parts = [p[:1].upper() + p[1:].lower() for p in parts][:3]
    return " ".join(parts).strip()


def _normalize_name(name: str) -> str:
    name = re.sub(r"\s+", " ", (name or "").strip())
    return name[:80]


def _dedupe(members: list[TeamMember]) -> list[TeamMember]:
    seen: set[str] = set()
    out: list[TeamMember] = []
    for m in members:
        key = m.name.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out


# ── Step 1: from user answer ───────────────────────────────────────


def members_from_user_answer(answer: dict[str, Any]) -> list[TeamMember]:
    out: list[TeamMember] = []
    items = answer.get("members") if isinstance(answer, dict) else None
    if not isinstance(items, list):
        return out
    for raw in items[:8]:
        if not isinstance(raw, dict):
            continue
        name = _normalize_name(str(raw.get("name") or ""))
        if not name:
            continue
        role = str(raw.get("role") or "").strip()[:80] or None
        bio = str(raw.get("bio") or "").strip()[:240] or None
        linkedin = str(raw.get("linkedin_url") or "").strip() or None
        photo = str(raw.get("photo_url") or "").strip() or None
        out.append(TeamMember(
            name=name,
            role=role,
            bio=bio,
            linkedin_url=linkedin,
            photo_url=photo,
            source="user",
            confidence=1.0,
        ))
    return _dedupe(out)


# ── Step 2: from uploaded document citations ───────────────────────


def members_from_uploaded_docs(research: ResearchPacket) -> list[TeamMember]:
    text_blobs: list[str] = []
    for c in research.citations:
        if c.source == "uploaded_document":
            text_blobs.append(c.snippet or "")
    if not text_blobs:
        return []
    blob = "\n".join(text_blobs)
    out: list[TeamMember] = []
    for m in _NAME_THEN_ROLE.finditer(blob):
        name = _normalize_name(m.group(1))
        role = m.group(2).strip()
        if name:
            out.append(TeamMember(name=name, role=role, source="uploaded_document", confidence=0.9))
    for m in _ROLE_THEN_NAME.finditer(blob):
        role = m.group(1).strip()
        name = _normalize_name(m.group(2))
        if name:
            out.append(TeamMember(name=name, role=role, source="uploaded_document", confidence=0.9))
    return _dedupe(out)[:6]


# ── Step 3: from preflight LinkedIn seed URLs ──────────────────────


def members_from_preflight_seeds(seed_urls: Iterable[str]) -> list[TeamMember]:
    out: list[TeamMember] = []
    for url in (seed_urls or []):
        m = _LINKEDIN_HANDLE_RE.search(url or "")
        if not m:
            continue
        name = _name_from_handle(m.group(1))
        if not name or " " not in name:
            # Single-word handles → not a credible founder name.
            continue
        out.append(TeamMember(
            name=name,
            linkedin_url=url,
            source="preflight",
            confidence=0.7,
        ))
    return _dedupe(out)[:6]


# ── Step 4: targeted search (premium only) ─────────────────────────


async def _serper_search_team(client: httpx.AsyncClient, company: str) -> list[Citation]:
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
            "https://google.serper.dev/search",
            timeout=8.0,
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            json={"q": f'"{company}" (founder OR co-founder OR CEO) site:linkedin.com/in', "num": 8},
        )
        if r.status_code != 200:
            await pool.report_failure(key, r.status_code)
            provider_health.record("serper", success=False)
            return []
        await pool.report_success(key)
        provider_health.record("serper", success=True)
        out: list[Citation] = []
        for item in (r.json() or {}).get("organic", []):
            url = item.get("link") or ""
            if "linkedin.com/in/" not in url.lower():
                continue
            out.append(Citation(
                title=(item.get("title") or "")[:200],
                url=url,
                snippet=(item.get("snippet") or "")[:300],
                source="team_search",
                source_authority=0.85,
            ))
        return out
    except Exception as e:
        try:
            await pool.report_failure(key, 0)
        except Exception:
            pass
        provider_health.record("serper", success=False)
        logger.debug("v4_team_search_failed", error=str(e))
        return []


_LINKEDIN_TITLE_RE = re.compile(
    r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*[-—|·,]\s*([^\-—|·]{2,80})",
)


def _parse_linkedin_search_result(c: Citation) -> Optional[TeamMember]:
    """LinkedIn search-result titles look like 'Jane Doe - CEO at Acme | LinkedIn'."""
    title = c.title or ""
    m = _LINKEDIN_TITLE_RE.match(title)
    if m:
        name = _normalize_name(m.group(1))
        role = m.group(2).strip().replace(" at ", " · ")[:80]
    else:
        # Fall back to handle-derived name.
        h = _LINKEDIN_HANDLE_RE.search(c.url or "")
        if not h:
            return None
        name = _name_from_handle(h.group(1))
        role = None
    if not name or " " not in name:
        return None
    return TeamMember(
        name=name,
        role=role,
        linkedin_url=c.url,
        source="search",
        confidence=0.75,
    )


# ── Photo enrichment ───────────────────────────────────────────────


def _company_domain(company_url: Optional[str]) -> Optional[str]:
    if not company_url:
        return None
    try:
        host = urlparse(company_url).netloc.lower().lstrip("www.")
        return host or None
    except Exception:
        return None


async def enrich_with_photos(
    members: list[TeamMember],
    *,
    company: Optional[str],
    company_url: Optional[str],
    timeout_per_member_s: float = 10.0,
) -> list[TeamMember]:
    if not members:
        return members
    domain = _company_domain(company_url)

    async def _one(m: TeamMember) -> TeamMember:
        if m.photo_url:
            # User-supplied photo URL — verify minimally (must look like an image URL).
            host = urlparse(m.photo_url).netloc.lower().lstrip("www.")
            if host and ("." in host) and (m.photo_url.lower().endswith(
                (".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif")
            ) or host.endswith(("licdn.com", "crunchbase.com", "githubusercontent.com"))):
                m.photo_source = host
                m.is_default_avatar = False
                return m
            # Otherwise discard and search.
            m.photo_url = None
        cand: ImageCandidate = await search_person_image(
            name=m.name,
            role_hint=m.role,
            company=company,
            company_domain=domain,
            timeout_s=timeout_per_member_s,
        )
        m.photo_url = cand.image_url
        m.photo_source = cand.source_domain
        m.photo_attribution = cand.attribution
        m.is_default_avatar = cand.is_default_avatar
        return m

    # Photos one-at-a-time to respect Serper rate limits.
    out: list[TeamMember] = []
    start = time.perf_counter()
    for m in members:
        if (time.perf_counter() - start) * 1000 > 60_000:
            # Hard cap: never burn more than 60s on photos.
            m.photo_url = m.photo_url or make_default_candidate(m.name).image_url
            m.is_default_avatar = True
            m.photo_source = m.photo_source or "default"
            out.append(m)
            continue
        out.append(await _one(m))
    return out


# ── Public entry ───────────────────────────────────────────────────


async def resolve_team(
    *,
    company: Optional[str],
    company_url: Optional[str],
    research: ResearchPacket,
    preflight_team_seeds: list[str] | None = None,
    user_answer: Optional[dict[str, Any]] = None,
    mode: str = "standard",
) -> list[TeamMember]:
    """Run the resolution chain. Does NOT enrich photos here — call
    `enrich_with_photos` separately when you're ready to spend the time budget.
    """
    # Step 1
    if user_answer:
        members = members_from_user_answer(user_answer)
        if members:
            return members

    # Step 2
    members = members_from_uploaded_docs(research)
    if members:
        return members

    # Step 3
    if preflight_team_seeds:
        members = members_from_preflight_seeds(preflight_team_seeds)
        if members:
            return members

    # Step 4 (premium only)
    if mode == "premium" and company:
        async with httpx.AsyncClient() as client:
            cites = await _serper_search_team(client, company)
        out: list[TeamMember] = []
        for c in cites[:6]:
            mm = _parse_linkedin_search_result(c)
            if mm:
                out.append(mm)
        out = _dedupe(out)
        if out:
            return out

    return []

