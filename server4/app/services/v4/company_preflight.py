"""
V4 Company Preflight — first-pass company understanding before market research.

When the user query mentions a company name and/or URL we fetch the actual page,
extract real metadata (title, description, h1, summary), and run a small set of
targeted searches that look for the company on trusted sources (LinkedIn,
Crunchbase, GitHub, the company's own domain). Output is a `CompanyContext`
dataclass with ONLY verified citations — never invented data.

Premium mode runs the full preflight (page fetch + 4 targeted searches +
LinkedIn discovery). Standard mode runs a lighter version (page fetch + 1
search) so it stays fast.

Hooked into `V4ContentPipeline.generate` as Stage 1.5 — runs in parallel with
exemplar load, blocks the research stage until done so the research query can
be enriched with verified company facts.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
import structlog

from app.config import settings
from app.services.v4 import provider_health
from app.services.v4.key_pool import get_pool
from app.services.v4.research_collector import Citation

logger = structlog.get_logger(__name__)


# ── Data model ─────────────────────────────────────────────────────


@dataclass
class CompanyContext:
    """Verified, evidence-only company information."""

    name: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None      # extracted from <meta description> or first <p>
    title: Optional[str] = None            # extracted from <title>
    h1: Optional[str] = None               # extracted from first <h1>
    sector: Optional[str] = None           # only set when explicitly stated on the page
    linkedin_url: Optional[str] = None
    crunchbase_url: Optional[str] = None
    github_url: Optional[str] = None
    twitter_url: Optional[str] = None
    sources: list[Citation] = field(default_factory=list)   # the actual pages we read
    team_seed_urls: list[str] = field(default_factory=list)  # discovered LinkedIn /in/ URLs
    fetched: bool = False                  # True only when we actually loaded the URL
    duration_ms: int = 0

    def is_empty(self) -> bool:
        return not (self.name or self.url or self.sources)

    def as_prompt_context(self, max_chars: int = 1200) -> str:
        """Compact text block for injection into LLM prompts."""
        parts: list[str] = []
        if self.name:
            parts.append(f"Company: {self.name}")
        if self.url:
            parts.append(f"Website: {self.url}")
        if self.title and self.title != self.name:
            parts.append(f"Page title: {self.title}")
        if self.h1:
            parts.append(f"Hero line: {self.h1}")
        if self.description:
            parts.append(f"About: {self.description}")
        if self.linkedin_url:
            parts.append(f"LinkedIn: {self.linkedin_url}")
        if self.crunchbase_url:
            parts.append(f"Crunchbase: {self.crunchbase_url}")
        if self.github_url:
            parts.append(f"GitHub: {self.github_url}")
        if self.team_seed_urls:
            parts.append("Team profiles found: " + ", ".join(self.team_seed_urls[:6]))
        text = "\n".join(parts)
        return text[:max_chars]


# ── URL / name detection ───────────────────────────────────────────

# Match http(s)://… or bare-domain example.com/path patterns.
_URL_RE = re.compile(
    r"(?P<u>(?:https?://)?(?:www\.)?[a-z0-9][a-z0-9\-]{1,62}(?:\.[a-z0-9][a-z0-9\-]{1,62}){1,3}(?:/[\w\-./%?=&#+~]*)?)",
    re.IGNORECASE,
)
# Block-list: bare-domain matches that are clearly not company URLs.
_DOMAIN_STOPLIST = {
    "e.g", "i.e", "etc", "vs", "ie", "eg",
    "linkedin.com", "twitter.com", "x.com", "facebook.com",
    "instagram.com", "youtube.com", "google.com", "wikipedia.org",
    "github.com",  # GitHub user/repo URLs handled separately
}
_VALID_TLDS = {
    "com", "io", "ai", "co", "org", "net", "app", "dev", "tech", "xyz",
    "us", "uk", "eu", "de", "fr", "in", "ca", "au", "nz", "jp", "cn",
    "biz", "info", "us", "me", "tv", "cloud", "store", "shop",
}


def _looks_like_company_url(candidate: str) -> Optional[str]:
    """Return a normalized https URL or None."""
    s = candidate.strip().rstrip(".,;:)]'\"")
    if not s:
        return None
    if not re.match(r"^https?://", s, re.IGNORECASE):
        s = "https://" + s
    try:
        parsed = urlparse(s)
    except Exception:
        return None
    host = (parsed.netloc or "").lower()
    if not host or "." not in host:
        return None
    host_parts = host.split(".")
    tld = host_parts[-1]
    if tld not in _VALID_TLDS:
        return None
    if host.lstrip("www.") in _DOMAIN_STOPLIST:
        return None
    return f"{parsed.scheme}://{host}{parsed.path or ''}"


def extract_company_signals(
    user_query: str,
    analysis: dict[str, Any],
) -> tuple[Optional[str], Optional[str]]:
    """Return (company_name, company_url) discovered in the prompt or analysis.

    Conservative: a name from analysis is only kept when it actually appears in
    the user query (case-insensitive substring) — otherwise it's likely an
    over-eager LLM guess.
    """
    name = (analysis.get("detected_company_name") or "").strip() or None
    if name and name.lower() not in (user_query or "").lower():
        # The LLM guessed the name; treat it as a soft hint, not verified.
        soft_name: Optional[str] = name
        name = None
    else:
        soft_name = name

    url: Optional[str] = None
    for m in _URL_RE.finditer(user_query or ""):
        candidate = m.group("u")
        norm = _looks_like_company_url(candidate)
        if norm:
            url = norm
            break

    # Also check structured input for a company URL hint.
    extra = analysis.get("entities") or []
    if not url and isinstance(extra, list):
        for e in extra:
            val = (e.get("value") if isinstance(e, dict) else str(e)) or ""
            for m in _URL_RE.finditer(str(val)):
                norm = _looks_like_company_url(m.group("u"))
                if norm:
                    url = norm
                    break
            if url:
                break

    return (name or soft_name, url)


# ── HTML extraction ────────────────────────────────────────────────

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_DESC_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']{20,400})["\']',
    re.IGNORECASE,
)
_OG_DESC_RE = re.compile(
    r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']{20,400})["\']',
    re.IGNORECASE,
)
_OG_SITE_RE = re.compile(
    r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']{2,80})["\']',
    re.IGNORECASE,
)
_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_LINKEDIN_COMPANY_RE = re.compile(r"linkedin\.com/company/[a-zA-Z0-9\-_%]+", re.IGNORECASE)
_LINKEDIN_PROFILE_RE = re.compile(r"linkedin\.com/in/[a-zA-Z0-9\-_%]+", re.IGNORECASE)
_CRUNCHBASE_RE = re.compile(r"crunchbase\.com/organization/[a-zA-Z0-9\-_%]+", re.IGNORECASE)
_GITHUB_RE = re.compile(r"github\.com/[a-zA-Z0-9\-_]+", re.IGNORECASE)
_TWITTER_RE = re.compile(r"(?:twitter\.com|x\.com)/[a-zA-Z0-9_]{2,15}", re.IGNORECASE)


def _clean_text(raw: str, max_len: int = 320) -> str:
    text = _TAG_RE.sub(" ", raw or "")
    text = _WS_RE.sub(" ", text).strip()
    return text[:max_len]


def _parse_company_page(url: str, html: str) -> dict[str, Any]:
    """Extract name/title/description/social from raw HTML. Pure regex (no BS4)."""
    info: dict[str, Any] = {"url": url}
    if not html:
        return info
    if (m := _TITLE_RE.search(html)):
        info["title"] = _clean_text(m.group(1), 200)
    if (m := _META_DESC_RE.search(html)) or (m := _OG_DESC_RE.search(html)):
        info["description"] = _clean_text(m.group(1), 320)
    if (m := _OG_SITE_RE.search(html)):
        info["og_site_name"] = _clean_text(m.group(1), 80)
    if (m := _H1_RE.search(html)):
        info["h1"] = _clean_text(m.group(1), 200)
    # Socials — only first match each.
    if (m := _LINKEDIN_COMPANY_RE.search(html)):
        info["linkedin_url"] = "https://www." + m.group(0)
    if (m := _CRUNCHBASE_RE.search(html)):
        info["crunchbase_url"] = "https://www." + m.group(0)
    if (m := _GITHUB_RE.search(html)):
        info["github_url"] = "https://" + m.group(0)
    if (m := _TWITTER_RE.search(html)):
        info["twitter_url"] = "https://" + m.group(0)
    # Team profile seeds — collect /in/ links from the page.
    info["team_seeds"] = sorted({
        "https://www." + p for p in _LINKEDIN_PROFILE_RE.findall(html)
    })[:8]
    return info


# ── Provider helpers (reuse research_collector keys) ───────────────


async def _fetch_html(client: httpx.AsyncClient, url: str, timeout: float = 8.0) -> Optional[str]:
    try:
        r = await client.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; PitchDeckBot/1.0; "
                    "+https://example.com/bot)"
                ),
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        if r.status_code != 200:
            return None
        ctype = (r.headers.get("content-type") or "").lower()
        if "html" not in ctype and "xml" not in ctype:
            return None
        # Cap to 250KB; landing pages above that are usually ad-heavy SPAs.
        return r.text[:250_000]
    except Exception as e:
        logger.debug("preflight_fetch_failed", url=url, error=str(e))
        return None


async def _serper_search(client: httpx.AsyncClient, query: str, num: int = 5) -> list[dict[str, Any]]:
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
            json={"q": query, "num": num},
        )
        if r.status_code != 200:
            await pool.report_failure(key, r.status_code)
            provider_health.record("serper", success=False)
            return []
        await pool.report_success(key)
        provider_health.record("serper", success=True)
        data = r.json() or {}
        return list(data.get("organic") or [])
    except Exception as e:
        try:
            await pool.report_failure(key, 0)
        except Exception:
            pass
        provider_health.record("serper", success=False)
        logger.debug("preflight_serper_failed", error=str(e))
        return []


async def _tavily_search(client: httpx.AsyncClient, query: str, max_results: int = 5) -> list[dict[str, Any]]:
    key = getattr(settings, "TAVILY_API_KEY", None)
    if not key:
        return []
    try:
        r = await client.post(
            "https://api.tavily.com/search",
            timeout=8.0,
            json={
                "api_key": key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
                "include_answer": False,
            },
        )
        if r.status_code != 200:
            return []
        data = r.json() or {}
        return list(data.get("results") or [])
    except Exception as e:
        logger.debug("preflight_tavily_failed", error=str(e))
        return []


# ── Main entry ─────────────────────────────────────────────────────


async def run_preflight(
    *,
    name: Optional[str],
    url: Optional[str],
    mode: str = "standard",
    user_query: str = "",
) -> CompanyContext:
    """Run a verified company preflight. Returns CompanyContext with sources only
    populated from URLs we actually fetched and validated.

    Premium mode: full path (page fetch + 3 targeted searches + LinkedIn).
    Standard mode: page fetch + 1 search if a URL exists, else 1 search only.
    """
    start = time.perf_counter()
    ctx = CompanyContext(name=name, url=url)

    if not name and not url:
        ctx.duration_ms = int((time.perf_counter() - start) * 1000)
        return ctx

    deep = mode == "premium"

    async with httpx.AsyncClient() as client:
        # Step 1 — if no URL but a name exists, try one search to discover it.
        if not url and name:
            results = await _serper_search(client, f'"{name}" official site', num=5)
            if not results:
                results = await _tavily_search(client, f'"{name}" official site', max_results=5)
            for r in results:
                cand = r.get("link") or r.get("url") or ""
                norm = _looks_like_company_url(cand)
                if not norm:
                    continue
                host = urlparse(norm).netloc.lower().lstrip("www.")
                # Reject aggregators / social hubs as "official site"
                if host in {
                    "linkedin.com", "twitter.com", "x.com", "facebook.com",
                    "crunchbase.com", "wikipedia.org", "youtube.com",
                    "instagram.com", "github.com", "medium.com", "substack.com",
                }:
                    continue
                # Domain must contain a token of the company name (loose check).
                name_token = re.sub(r"[^a-z0-9]", "", name.lower())[:6]
                if name_token and name_token in host.replace(".", ""):
                    url = norm
                    ctx.url = url
                    break

        # Step 2 — fetch the URL if we have one, parse metadata.
        if url:
            html = await _fetch_html(client, url, timeout=10.0 if deep else 7.0)
            if html:
                parsed = _parse_company_page(url, html)
                ctx.fetched = True
                ctx.title = parsed.get("title")
                ctx.description = parsed.get("description")
                ctx.h1 = parsed.get("h1")
                ctx.linkedin_url = parsed.get("linkedin_url")
                ctx.crunchbase_url = parsed.get("crunchbase_url")
                ctx.github_url = parsed.get("github_url")
                ctx.twitter_url = parsed.get("twitter_url")
                ctx.team_seed_urls = parsed.get("team_seeds") or []
                if not ctx.name:
                    # Prefer og:site_name; fall back to the title up to a separator.
                    cand_name = parsed.get("og_site_name") or (
                        re.split(r"[-|–:•·]", parsed.get("title") or "")[0].strip()
                    )
                    if cand_name and 1 < len(cand_name) <= 60:
                        ctx.name = cand_name
                ctx.sources.append(Citation(
                    title=parsed.get("title") or url,
                    url=url,
                    snippet=parsed.get("description") or parsed.get("h1") or "",
                    source="company_preflight",
                    source_authority=0.97,
                ))

        # Step 3 — additional verification searches.
        verify_queries: list[tuple[str, str]] = []
        nm = ctx.name or name
        if nm:
            if deep:
                verify_queries = [
                    (f'"{nm}" site:linkedin.com/company', "linkedin"),
                    (f'"{nm}" site:crunchbase.com', "crunchbase"),
                    (f'"{nm}" funding raised', "news"),
                    (f'"{nm}" CEO founder team', "team"),
                ]
            else:
                # Standard: just one consolidated search to confirm existence.
                verify_queries = [(f'"{nm}" company', "general")]

        async def _do_search(q: str, label: str) -> list[Citation]:
            results = await _serper_search(client, q, num=4)
            if not results:
                results = await _tavily_search(client, q, max_results=4)
            cites: list[Citation] = []
            for r in results[:4]:
                u = r.get("link") or r.get("url") or ""
                if not u:
                    continue
                cites.append(Citation(
                    title=(r.get("title") or "")[:200],
                    url=u,
                    snippet=(r.get("snippet") or r.get("content") or "")[:300],
                    source=f"preflight_{label}",
                    source_authority=0.85,
                ))
                # Pull socials we haven't seen yet.
                if not ctx.linkedin_url and (m := _LINKEDIN_COMPANY_RE.search(u)):
                    ctx.linkedin_url = "https://www." + m.group(0)
                if not ctx.crunchbase_url and (m := _CRUNCHBASE_RE.search(u)):
                    ctx.crunchbase_url = "https://www." + m.group(0)
                # Collect team seed URLs from search result URLs too.
                if (m := _LINKEDIN_PROFILE_RE.search(u)) and len(ctx.team_seed_urls) < 8:
                    seed = "https://www." + m.group(0)
                    if seed not in ctx.team_seed_urls:
                        ctx.team_seed_urls.append(seed)
            return cites

        if verify_queries:
            results = await asyncio.gather(
                *(_do_search(q, label) for q, label in verify_queries),
                return_exceptions=True,
            )
            for batch in results:
                if isinstance(batch, list):
                    ctx.sources.extend(batch)

    ctx.duration_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "v4_company_preflight",
        name=ctx.name,
        url=ctx.url,
        mode=mode,
        fetched=ctx.fetched,
        n_sources=len(ctx.sources),
        n_team_seeds=len(ctx.team_seed_urls),
        duration_ms=ctx.duration_ms,
    )
    return ctx
