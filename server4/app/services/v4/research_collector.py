"""
V4 Research Collector — Multi-API parallel evidence gathering.

Uses ONLY APIs verified present in the project's `.env.example`:
  Web search:    Tavily, Serper (3 keys), Exa, You.com, SearchAPI, SerpAPI (2 keys)
  Content extract: Jina Reader, Firecrawl, scrape.do
  News:          NewsAPI, NewsData, Guardian, World News
  Financial:     Alpha Vantage, Finnhub, Polygon, FMP, FRED
  Social proof:  Reddit, GitHub, ProductHunt, YouTube
  Academic:      CORE

Architecture (NEW — not reusing legacy research_router):
- Each provider is an isolated async coroutine that returns List[Citation]
- All providers fan out in parallel via asyncio.gather
- Failures are swallowed per-provider (graceful degradation)
- Results de-duplicated by URL, ranked by source authority + freshness
- Cached in MongoDB (TTL = 24h for news, 7d for static content)
- Cached in Redis (15-minute hot cache keyed by query hash)

Premium mode hits ALL relevant providers in parallel (richest evidence).
Standard mode hits only Tavily + Serper + NewsAPI (fast, cheap, sufficient).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

import httpx
import structlog

from app.config import settings
from app.services.v4 import provider_health
from app.services.v4.key_pool import get_pool
from app.services.v4.research.depth_profiles import (
    DEPTH_PROFILES,
    DepthProfile,
    derive_profile_label,
    profile_for,
)
from app.services.v4.research.recency import (
    RecencyWindow,
    combined_score,
    resolve_recency_window,
    staleness_label,
    parse_iso_datetime,
)

logger = structlog.get_logger(__name__)


def _classify_status(exc: Exception) -> int:
    """Map an httpx error to an HTTP status (or 0 for non-HTTP failures)."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    if isinstance(exc, httpx.TimeoutException):
        return 504
    return 0


def _is_terminal_provider_status(status_code: int) -> bool:
    return status_code in {401, 403, 426}

# ── Data models ─────────────────────────────────────────────────────

@dataclass
class Citation:
    """A single piece of evidence from one source."""
    title: str
    url: str
    snippet: str
    source: str                      # "tavily" | "serper" | "newsapi" | etc.
    source_authority: float = 0.5    # 0..1, derived from domain
    published_at: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)
    # Plan 04 — populated post-rank in ResearchCollector.collect when a
    # RecencyWindow is in scope. Defaults preserve backwards compatibility
    # for any code path that builds Citation objects directly.
    freshness: float = 0.0           # 0..1, exponential decay against window half-life
    rank_score: float = 0.0          # 0..1, blended authority + freshness
    staleness: str = "undated"       # "fresh" | "aging" | "stale" | "undated"


@dataclass
class ResearchPacket:
    """Aggregated research for a generation request."""
    query: str
    industry: Optional[str]
    company_name: Optional[str]
    citations: list[Citation]
    news_citations: list[Citation]
    financial_data: dict[str, Any]
    social_signals: dict[str, Any]
    duration_ms: int
    cache_hit: bool = False

    def top_citations(self, n: int = 10) -> list[Citation]:
        """Best-ranked citations for prompt injection.

        Sorts by ``rank_score`` (numeric authority+freshness blend
        populated by ``ResearchCollector.collect`` after Plan 04).
        Falls back to ``source_authority`` when ``rank_score`` is the
        default 0.0 \u2014 keeps direct ``ResearchPacket`` constructors that
        bypass the collector working without modification.
        """
        def _key(c: Citation) -> tuple[float, float, str]:
            score = c.rank_score if c.rank_score > 0 else c.source_authority
            return (score, c.source_authority, c.published_at or "")

        return sorted(
            self.citations + self.news_citations,
            key=_key,
            reverse=True,
        )[:n]

    def as_prompt_context(self, max_chars: int = 4000) -> str:
        """Format the research as a compact context block for LLM prompts."""
        lines: list[str] = []
        for c in self.top_citations(12):
            meta: list[str] = []
            if c.staleness:
                meta.append(f"staleness={c.staleness}")
            if c.freshness > 0:
                meta.append(f"freshness={c.freshness:.2f}")
            meta_text = f" ({', '.join(meta)})" if meta else ""
            line = f"- [{c.source}]{meta_text} {c.title}: {c.snippet[:200]}"
            if c.url:
                line += f" ({c.url})"
            lines.append(line)
        text = "\n".join(lines)
        if self.financial_data:
            text += "\n\nFinancial signals:\n" + json.dumps(self.financial_data, indent=1)[:800]
        if self.social_signals:
            text += "\n\nSocial signals:\n" + json.dumps(self.social_signals, indent=1)[:600]
        return text[:max_chars]


# ── Domain authority scoring ────────────────────────────────────────

_HIGH_AUTHORITY = {
    "techcrunch.com", "bloomberg.com", "reuters.com", "ft.com", "wsj.com",
    "forbes.com", "hbr.org", "mit.edu", "stanford.edu", "ycombinator.com",
    "a16z.com", "sequoiacap.com", "crunchbase.com", "pitchbook.com",
    "gartner.com", "mckinsey.com", "statista.com", "sec.gov", "imf.org",
    "worldbank.org", "oecd.org", "nature.com", "science.org",
}
_MED_AUTHORITY = {
    "medium.com", "substack.com", "wired.com", "theverge.com", "venturebeat.com",
    "businessinsider.com", "fastcompany.com", "inc.com", "fortune.com",
}


def _score_authority(url: str) -> float:
    if not url:
        return 0.3
    try:
        domain = url.split("/")[2].lower().lstrip("www.")
    except IndexError:
        return 0.3
    if any(domain.endswith(d) for d in _HIGH_AUTHORITY):
        return 0.95
    if any(domain.endswith(d) for d in _MED_AUTHORITY):
        return 0.7
    if domain.endswith((".gov", ".edu", ".org")):
        return 0.85
    return 0.5


# ── Research Collector ─────────────────────────────────────────────

class ResearchCollector:
    """Parallel multi-source evidence gatherer.

    Usage:
        collector = ResearchCollector()
        packet = await collector.collect(
            query="AI legal document review market",
            industry="legal tech",
            company_name="Acme AI",
            mode="premium",
        )
    """

    HTTP_TIMEOUT = 12.0
    REDIS_TTL_SEC = 900            # 15-minute hot cache
    MONGO_TTL_DAYS = 1             # 24h persistence

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None
        self._mongo = None
        self._redis = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.HTTP_TIMEOUT,
                limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
            )
        return self._client

    @staticmethod
    def _result_limit(profile: Optional[DepthProfile], default: int) -> int:
        if profile is None:
            return default
        return max(1, profile.max_results_per_provider)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── Cache layer ────────────────────────────────────────────────

    @staticmethod
    def _cache_key(query: str, mode: str) -> str:
        h = hashlib.sha256(f"{query}|{mode}".encode()).hexdigest()[:24]
        return f"v4:research:{h}"

    async def _redis_get(self, key: str) -> Optional[dict]:
        try:
            from app.utils.rate_limiter import get_redis
            r = await get_redis()
            if r is None:
                return None
            raw = await r.get(key)
            return json.loads(raw) if raw else None
        except Exception:
            return None

    async def _redis_set(self, key: str, value: dict) -> None:
        try:
            from app.utils.rate_limiter import get_redis
            r = await get_redis()
            if r is None:
                return
            await r.setex(key, self.REDIS_TTL_SEC, json.dumps(value, default=str))
        except Exception:
            pass

    async def _mongo_get(self, key: str) -> Optional[dict]:
        try:
            from app.database import get_db
            db = get_db()
            doc = await db["v4_research_cache"].find_one({"_id": key})
            if not doc:
                return None
            if doc.get("expires_at") and doc["expires_at"] < datetime.now(timezone.utc):
                return None
            return doc.get("payload")
        except Exception:
            return None

    async def _mongo_set(self, key: str, payload: dict) -> None:
        try:
            from app.database import get_db
            db = get_db()
            await db["v4_research_cache"].update_one(
                {"_id": key},
                {"$set": {
                    "payload": payload,
                    "cached_at": datetime.now(timezone.utc),
                    "expires_at": datetime.now(timezone.utc) + timedelta(days=self.MONGO_TTL_DAYS),
                }},
                upsert=True,
            )
        except Exception:
            pass

    # ── Public entry point ─────────────────────────────────────────

    async def collect(
        self,
        query: str,
        industry: Optional[str] = None,
        company_name: Optional[str] = None,
        mode: str = "standard",
        research_depth: Optional[str] = None,
        profile: Optional[DepthProfile] = None,
        recency: Optional[RecencyWindow] = None,
        purpose: Optional[str] = None,
    ) -> ResearchPacket:
        """Run all relevant providers in parallel and assemble a packet.

        New signature (Plan 04):
            ``profile`` and ``recency`` are the canonical inputs.
            Callers should compute them once at pipeline boundary and
            pass them straight through. The legacy ``research_depth``
            string is still accepted for backwards compatibility \u2014 it
            resolves to a profile via ``derive_profile_label``.
            ``purpose`` is used only when ``recency`` is omitted; it
            seeds ``resolve_recency_window``.

        Profile labels and meaning:
            - "fast"     \u2192 Tavily + Serper + NewsAPI, 4s/provider
            - "standard" \u2192 adds Exa, 6s/provider
            - "deep"     \u2192 full suite incl. You.com, Jina, NewsData,
                          Guardian, social, financial, 10s/provider
        """

        # Resolve the profile. Prefer explicit param, fall back to the
        # legacy string, then to mode-based default.
        if profile is None:
            profile = profile_for(mode, research_depth)
        depth_label = profile.label

        # Resolve the recency window. Prefer explicit param, fall back
        # to a window derived from purpose+query.
        if recency is None:
            recency = resolve_recency_window(
                purpose=purpose,
                user_query=query,
                today=date.today(),
            )

        start = time.perf_counter()
        # Cache key includes profile label + recency label so different
        # tiers / windows don't collide. Without this a "deep+last_180d"
        # packet could serve a "standard+last_2y" lookup and silently
        # leak older citations into the tighter window.
        cache_key = self._cache_key(
            f"{query}|p={depth_label}|r={recency.label}|e={recency.earliest.isoformat()}",
            mode,
        )

        # Check Redis hot cache first
        cached = await self._redis_get(cache_key)
        if not cached:
            cached = await self._mongo_get(cache_key)
        if cached:
            packet = ResearchPacket(**{**cached, "cache_hit": True,
                "citations": [Citation(**c) for c in cached.get("citations", [])],
                "news_citations": [Citation(**c) for c in cached.get("news_citations", [])],
            })
            return packet

        # Build provider task list from the typed profile.
        web_tasks: list = []
        for name in profile.web_providers:
            coro = self._dispatch_web_provider(name, query, recency, profile)
            if coro is not None:
                web_tasks.append(coro)
        news_tasks: list = []
        for name in profile.news_providers:
            coro = self._dispatch_news_provider(name, query, recency, profile)
            if coro is not None:
                news_tasks.append(coro)

        financial_task: Optional[asyncio.Task] = None
        social_tasks: list = []

        if profile.enable_financial and company_name:
            financial_task = asyncio.create_task(self._financial_lookup(company_name))
        if profile.enable_social:
            social_tasks = [
                self._reddit_search(query),
                self._github_search(query),
            ]

        # Fan out everything concurrently
        web_results, news_results, social_results = await asyncio.gather(
            asyncio.gather(*web_tasks, return_exceptions=True),
            asyncio.gather(*news_tasks, return_exceptions=True),
            asyncio.gather(*social_tasks, return_exceptions=True) if social_tasks else asyncio.sleep(0, result=[]),
            return_exceptions=False,
        )

        # Flatten + de-dupe web citations
        citations: list[Citation] = []
        seen_urls: set[str] = set()
        for batch in web_results:
            if isinstance(batch, Exception) or not batch:
                continue
            for c in batch:
                if c.url and c.url not in seen_urls:
                    seen_urls.add(c.url)
                    citations.append(c)

        # News citations
        news_citations: list[Citation] = []
        for batch in news_results:
            if isinstance(batch, Exception) or not batch:
                continue
            for c in batch:
                if c.url and c.url not in seen_urls:
                    seen_urls.add(c.url)
                    news_citations.append(c)

        # Social signals
        social_signals: dict[str, Any] = {}
        if social_tasks:
            for label, batch in zip(["reddit", "github"], social_results):
                if isinstance(batch, Exception) or not batch:
                    continue
                social_signals[label] = batch[:5]

        # Financial data
        financial_data: dict[str, Any] = {}
        if financial_task is not None:
            try:
                financial_data = await financial_task
            except Exception as e:
                logger.warning("v4_research_financial_failed", error=str(e))

        # Plan 04 \u2014 hard recency floor + numeric ranking + staleness label.
        now_utc = datetime.now(timezone.utc)
        today_local = now_utc.date()
        citations, dropped_web = self._apply_recency_and_score(
            citations, recency=recency, now=now_utc, today=today_local,
        )
        news_citations, dropped_news = self._apply_recency_and_score(
            news_citations, recency=recency, now=now_utc, today=today_local,
        )

        duration_ms = int((time.perf_counter() - start) * 1000)
        packet = ResearchPacket(
            query=query,
            industry=industry,
            company_name=company_name,
            citations=citations[:30],
            news_citations=news_citations[:15],
            financial_data=financial_data,
            social_signals=social_signals,
            duration_ms=duration_ms,
        )

        # Persist to caches (best-effort)
        try:
            payload = asdict(packet)
            await self._redis_set(cache_key, payload)
            await self._mongo_set(cache_key, payload)
        except Exception:
            pass

        logger.info(
            "v4_research_complete",
            query=query[:80],
            mode=mode,
            profile=depth_label,
            recency=recency.label,
            earliest=recency.earliest.isoformat(),
            duration_ms=duration_ms,
            n_citations=len(packet.citations),
            n_news=len(packet.news_citations),
            n_dropped_stale=dropped_web + dropped_news,
        )
        return packet

    # ── Provider dispatch + ranking helpers ────────────────────────

    def _dispatch_web_provider(
        self,
        name: str,
        query: str,
        recency: RecencyWindow,
        profile: DepthProfile,
    ):
        if name == "tavily":
            return self._tavily(query, recency=recency, profile=profile)
        if name == "serper":
            return self._serper(query, recency=recency, profile=profile)
        if name == "exa":
            return self._exa(query, recency=recency, profile=profile)
        if name == "you_com":
            return self._you_com(query, profile=profile)
        if name == "jina":
            return self._jina_reader_search(query, profile=profile)
        logger.warning("v4_research_unknown_web_provider", provider=name)
        return None

    def _dispatch_news_provider(
        self,
        name: str,
        query: str,
        recency: RecencyWindow,
        profile: DepthProfile,
    ):
        if name == "newsapi":
            return self._newsapi(query, recency=recency, profile=profile)
        if name == "newsdata":
            return self._newsdata(query, recency=recency, profile=profile)
        if name == "guardian":
            return self._guardian(query, recency=recency, profile=profile)
        logger.warning("v4_research_unknown_news_provider", provider=name)
        return None

    @staticmethod
    def _apply_recency_and_score(
        items: list["Citation"],
        *,
        recency: RecencyWindow,
        now: datetime,
        today: date,
    ) -> tuple[list["Citation"], int]:
        """Drop citations strictly older than ``recency.earliest``,
        annotate freshness/rank/staleness on the survivors, and return
        them re-sorted by rank descending. Undated citations survive
        but get the default undated freshness (0.3).
        """

        kept: list[Citation] = []
        dropped = 0
        for c in items:
            parsed = parse_iso_datetime(c.published_at)
            if parsed is not None and parsed.date() < recency.earliest:
                dropped += 1
                continue
            score = combined_score(
                source_authority=c.source_authority,
                published_at=c.published_at,
                now=now,
                half_life_days=recency.decay_half_life_days,
            )
            from app.services.v4.research.recency import freshness_score as _fs
            c.freshness = _fs(
                c.published_at,
                now=now,
                half_life_days=recency.decay_half_life_days,
            )
            c.rank_score = score
            c.staleness = staleness_label(
                c.published_at, window=recency, today=today,
            )
            kept.append(c)
        kept.sort(key=lambda x: x.rank_score, reverse=True)
        return kept, dropped

    # ── Individual providers ───────────────────────────────────────

    async def _tavily(
        self,
        query: str,
        *,
        recency: Optional[RecencyWindow] = None,
        profile: Optional[DepthProfile] = None,
    ) -> list[Citation]:
        if not settings.TAVILY_API_KEY:
            return []
        timeout_s = profile.per_provider_timeout_s if profile else self.HTTP_TIMEOUT
        limit = self._result_limit(profile, 8)
        body: dict[str, Any] = {
            "api_key": settings.TAVILY_API_KEY,
            "query": query,
            "max_results": limit,
            "search_depth": "advanced",
            "include_answer": False,
        }
        if recency is not None:
            # Tavily caps `days` at 365; days_back already truncates.
            body["days"] = recency.days_back()
            body["topic"] = "general"
        try:
            client = await self._http()
            r = await client.post(
                "https://api.tavily.com/search",
                json=body,
                timeout=httpx.Timeout(timeout_s),
            )
            r.raise_for_status()
            data = r.json()
            out: list[Citation] = []
            for item in data.get("results", []):
                url = item.get("url", "")
                out.append(Citation(
                    title=item.get("title", ""),
                    url=url,
                    snippet=(item.get("content") or "")[:500],
                    source="tavily",
                    source_authority=_score_authority(url),
                    published_at=item.get("published_date"),
                ))
            return out
        except Exception as e:
            logger.warning("v4_tavily_failed", error=str(e))
            return []

    async def _serper(
        self,
        query: str,
        *,
        recency: Optional[RecencyWindow] = None,
        profile: Optional[DepthProfile] = None,
    ) -> list[Citation]:
        if not provider_health.is_healthy("serper"):
            return []
        pool = get_pool("serper", settings.serper_keys)
        if pool.empty:
            return []
        key = await pool.acquire()
        if not key:
            return []
        timeout_s = profile.per_provider_timeout_s if profile else self.HTTP_TIMEOUT
        limit = self._result_limit(profile, 10)
        body: dict[str, Any] = {"q": query, "num": limit}
        if recency is not None:
            days = recency.days_back()
            if days <= 7:
                body["tbs"] = "qdr:w"
            elif days <= 30:
                body["tbs"] = "qdr:m"
            elif days <= 365:
                body["tbs"] = "qdr:y"
            # else: no tbs — Serper has no ">1y" filter, post-hoc handles it.
        try:
            client = await self._http()
            r = await client.post(
                "https://google.serper.dev/search",
                json=body,
                headers={"X-API-KEY": key, "Content-Type": "application/json"},
                timeout=httpx.Timeout(timeout_s),
            )
            r.raise_for_status()
            data = r.json()
            await pool.report_success(key)
            provider_health.record("serper", success=True)
            out: list[Citation] = []
            for item in data.get("organic", []):
                url = item.get("link", "")
                out.append(Citation(
                    title=item.get("title", ""),
                    url=url,
                    snippet=item.get("snippet", "")[:500],
                    source="serper",
                    source_authority=_score_authority(url),
                    published_at=item.get("date"),
                ))
            return out
        except Exception as e:
            await pool.report_failure(key, _classify_status(e))
            provider_health.record("serper", success=False)
            logger.warning("v4_serper_failed", error=str(e))
            return []

    async def _exa(
        self,
        query: str,
        *,
        recency: Optional[RecencyWindow] = None,
        profile: Optional[DepthProfile] = None,
    ) -> list[Citation]:
        if not provider_health.is_healthy("exa"):
            return []
        pool = get_pool("exa", settings.exa_keys)
        if pool.empty:
            return []
        key = await pool.acquire()
        if not key:
            return []
        timeout_s = profile.per_provider_timeout_s if profile else self.HTTP_TIMEOUT
        limit = self._result_limit(profile, 8)
        body: dict[str, Any] = {
            "query": query,
            "numResults": limit,
            "useAutoprompt": True,
        }
        if recency is not None:
            # Exa expects ISO-8601 in UTC.
            body["startPublishedDate"] = (
                datetime.combine(recency.earliest, datetime.min.time())
                .replace(tzinfo=timezone.utc)
                .isoformat()
            )
        try:
            client = await self._http()
            r = await client.post(
                "https://api.exa.ai/search",
                json=body,
                headers={"x-api-key": key},
                timeout=httpx.Timeout(timeout_s),
            )
            r.raise_for_status()
            data = r.json()
            await pool.report_success(key)
            provider_health.record("exa", success=True)
            out: list[Citation] = []
            for item in data.get("results", []):
                url = item.get("url", "")
                out.append(Citation(
                    title=item.get("title", ""),
                    url=url,
                    snippet=(item.get("text") or item.get("highlight") or "")[:500],
                    source="exa",
                    source_authority=_score_authority(url),
                    published_at=item.get("publishedDate"),
                ))
            return out
        except Exception as e:
            await pool.report_failure(key, _classify_status(e))
            provider_health.record("exa", success=False)
            logger.warning("v4_exa_failed", error=str(e))
            return []

    async def _you_com(
        self,
        query: str,
        *,
        profile: Optional[DepthProfile] = None,
    ) -> list[Citation]:
        # You.com search has no native recency filter — the post-hoc
        # ``_apply_recency_and_score`` floor handles the staleness drop.
        if not provider_health.is_healthy("you_com"):
            return []
        pool = get_pool("you_com", settings.you_com_keys)
        if pool.empty:
            return []
        key = await pool.acquire()
        if not key:
            return []
        timeout_s = profile.per_provider_timeout_s if profile else self.HTTP_TIMEOUT
        limit = self._result_limit(profile, 8)
        try:
            client = await self._http()
            r = await client.get(
                "https://api.ydc-index.io/search",
                params={"query": query, "num_web_results": limit},
                headers={"X-API-Key": key},
                timeout=httpx.Timeout(timeout_s),
            )
            r.raise_for_status()
            data = r.json()
            await pool.report_success(key)
            provider_health.record("you_com", success=True)
            out: list[Citation] = []
            for item in (data.get("hits") or [])[:limit]:
                url = item.get("url", "")
                out.append(Citation(
                    title=item.get("title", ""),
                    url=url,
                    snippet=" ".join(item.get("snippets", []))[:500],
                    source="you.com",
                    source_authority=_score_authority(url),
                ))
            return out
        except Exception as e:
            status_code = _classify_status(e)
            await pool.report_failure(key, status_code)
            provider_health.record("you_com", success=False)
            if _is_terminal_provider_status(status_code):
                pool_state = pool.telemetry()
                if pool_state.get("keys") and all(k.get("cooling") for k in pool_state["keys"]):
                    provider_health.mute("you_com", reason=f"http_{status_code}")
                logger.info("v4_you_unavailable", error=str(e), status=status_code)
            else:
                logger.warning("v4_you_failed", error=str(e), status=status_code)
            return []

    async def _jina_reader_search(
        self,
        query: str,
        *,
        profile: Optional[DepthProfile] = None,
    ) -> list[Citation]:
        """Jina's `s.jina.ai` semantic search endpoint.

        Jina has no native recency parameter — the post-hoc recency
        floor in ``_apply_recency_and_score`` enforces the window.
        """
        if not provider_health.is_healthy("jina"):
            return []
        pool = get_pool("jina", settings.jina_keys)
        if pool.empty:
            return []
        key = await pool.acquire()
        if not key:
            return []
        timeout_s = profile.per_provider_timeout_s if profile else self.HTTP_TIMEOUT
        limit = self._result_limit(profile, 6)
        try:
            client = await self._http()
            r = await client.get(
                f"https://s.jina.ai/{query}",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Accept": "application/json",
                },
                timeout=httpx.Timeout(timeout_s),
            )
            r.raise_for_status()
            data = r.json()
            await pool.report_success(key)
            provider_health.record("jina", success=True)
            results = data.get("data", []) if isinstance(data, dict) else []
            out: list[Citation] = []
            for item in results[:limit]:
                url = item.get("url", "")
                out.append(Citation(
                    title=item.get("title", ""),
                    url=url,
                    snippet=(item.get("description") or item.get("content") or "")[:500],
                    source="jina",
                    source_authority=_score_authority(url),
                ))
            return out
        except Exception as e:
            await pool.report_failure(key, _classify_status(e))
            provider_health.record("jina", success=False)
            logger.warning("v4_jina_failed", error=str(e))
            return []

    async def _newsapi(
        self,
        query: str,
        *,
        recency: Optional[RecencyWindow] = None,
        profile: Optional[DepthProfile] = None,
    ) -> list[Citation]:
        if not settings.NEWSAPI_KEY or not provider_health.is_healthy("newsapi"):
            return []
        timeout_s = profile.per_provider_timeout_s if profile else self.HTTP_TIMEOUT
        limit = self._result_limit(profile, 10)
        # NewsAPI free tier limits historical reach. Respect the window
        # but never go beyond ~30 days on the developer tier; broader
        # windows still work — NewsAPI just clamps server-side.
        if recency is not None:
            from_date = recency.earliest.strftime("%Y-%m-%d")
        else:
            from_date = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")
        try:
            client = await self._http()
            r = await client.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "pageSize": limit,
                    "sortBy": "relevancy",
                    "language": "en",
                    "from": from_date,
                },
                headers={"X-Api-Key": settings.NEWSAPI_KEY},
                timeout=httpx.Timeout(timeout_s),
            )
            r.raise_for_status()
            data = r.json()
            out: list[Citation] = []
            for item in data.get("articles", []):
                url = item.get("url", "")
                out.append(Citation(
                    title=item.get("title", ""),
                    url=url,
                    snippet=(item.get("description") or "")[:500],
                    source="newsapi",
                    source_authority=_score_authority(url),
                    published_at=item.get("publishedAt"),
                ))
            provider_health.record("newsapi", success=True)
            return out
        except Exception as e:
            status_code = _classify_status(e)
            provider_health.record("newsapi", success=False)
            if _is_terminal_provider_status(status_code):
                provider_health.mute("newsapi", reason=f"http_{status_code}")
                logger.info("v4_newsapi_unavailable", error=str(e), status=status_code)
            else:
                logger.warning("v4_newsapi_failed", error=str(e), status=status_code)
            return []

    async def _newsdata(
        self,
        query: str,
        *,
        recency: Optional[RecencyWindow] = None,
        profile: Optional[DepthProfile] = None,
    ) -> list[Citation]:
        if not settings.NEWSDATA_API_KEY:
            return []
        timeout_s = profile.per_provider_timeout_s if profile else self.HTTP_TIMEOUT
        limit = self._result_limit(profile, 8)
        params: dict[str, Any] = {
            "apikey": settings.NEWSDATA_API_KEY,
            "q": query,
            "language": "en",
        }
        if recency is not None:
            params["from_date"] = recency.earliest.strftime("%Y-%m-%d")
        try:
            client = await self._http()
            r = await client.get(
                "https://newsdata.io/api/1/news",
                params=params,
                timeout=httpx.Timeout(timeout_s),
            )
            r.raise_for_status()
            data = r.json()
            out: list[Citation] = []
            for item in (data.get("results") or [])[:limit]:
                url = item.get("link", "")
                out.append(Citation(
                    title=item.get("title", ""),
                    url=url,
                    snippet=(item.get("description") or "")[:500],
                    source="newsdata",
                    source_authority=_score_authority(url),
                    published_at=item.get("pubDate"),
                ))
            return out
        except Exception as e:
            logger.warning("v4_newsdata_failed", error=str(e))
            return []

    async def _guardian(
        self,
        query: str,
        *,
        recency: Optional[RecencyWindow] = None,
        profile: Optional[DepthProfile] = None,
    ) -> list[Citation]:
        if not settings.GUARDIAN_API_KEY:
            return []
        timeout_s = profile.per_provider_timeout_s if profile else self.HTTP_TIMEOUT
        limit = self._result_limit(profile, 6)
        params: dict[str, Any] = {
            "q": query,
            "api-key": settings.GUARDIAN_API_KEY,
            "show-fields": "trailText",
            "page-size": limit,
        }
        if recency is not None:
            params["from-date"] = recency.earliest.strftime("%Y-%m-%d")
        try:
            client = await self._http()
            r = await client.get(
                "https://content.guardianapis.com/search",
                params=params,
                timeout=httpx.Timeout(timeout_s),
            )
            r.raise_for_status()
            data = r.json()
            out: list[Citation] = []
            for item in data.get("response", {}).get("results", []):
                url = item.get("webUrl", "")
                out.append(Citation(
                    title=item.get("webTitle", ""),
                    url=url,
                    snippet=(item.get("fields", {}).get("trailText") or "")[:500],
                    source="guardian",
                    source_authority=0.9,  # Guardian is a high-authority outlet
                    published_at=item.get("webPublicationDate"),
                ))
            return out
        except Exception as e:
            logger.warning("v4_guardian_failed", error=str(e))
            return []

    async def _reddit_search(self, query: str) -> list[dict]:
        """Public reddit search — no auth required for read-only."""
        try:
            client = await self._http()
            r = await client.get(
                "https://www.reddit.com/search.json",
                params={"q": query, "limit": 6, "sort": "relevance"},
                headers={"User-Agent": settings.REDDIT_USER_AGENT or "barise-research/1.0"},
            )
            r.raise_for_status()
            children = r.json().get("data", {}).get("children", [])
            return [
                {
                    "title": c["data"].get("title", ""),
                    "subreddit": c["data"].get("subreddit", ""),
                    "score": c["data"].get("score", 0),
                    "url": "https://reddit.com" + c["data"].get("permalink", ""),
                }
                for c in children[:6]
            ]
        except Exception as e:
            logger.warning("v4_reddit_failed", error=str(e))
            return []

    async def _github_search(self, query: str) -> list[dict]:
        """Search GitHub repos for relevant projects (signals market activity)."""
        if not settings.GITHUB_TOKEN:
            return []
        try:
            client = await self._http()
            r = await client.get(
                "https://api.github.com/search/repositories",
                params={"q": query, "sort": "stars", "per_page": 6},
                headers={
                    "Authorization": f"token {settings.GITHUB_TOKEN}",
                    "Accept": "application/vnd.github+json",
                },
            )
            r.raise_for_status()
            items = r.json().get("items", [])
            return [
                {
                    "name": it.get("full_name", ""),
                    "stars": it.get("stargazers_count", 0),
                    "description": (it.get("description") or "")[:250],
                    "url": it.get("html_url", ""),
                }
                for it in items[:6]
            ]
        except Exception as e:
            logger.warning("v4_github_failed", error=str(e))
            return []

    async def _financial_lookup(self, company_name: str) -> dict[str, Any]:
        """Attempt a quick financial profile lookup via Alpha Vantage / Finnhub."""
        out: dict[str, Any] = {}
        if settings.FINNHUB_API_KEY:
            try:
                client = await self._http()
                # Try symbol lookup
                r = await client.get(
                    "https://finnhub.io/api/v1/search",
                    params={"q": company_name, "token": settings.FINNHUB_API_KEY},
                )
                r.raise_for_status()
                results = r.json().get("result", [])
                if results:
                    sym = results[0].get("symbol")
                    if sym:
                        # Get profile
                        rp = await client.get(
                            "https://finnhub.io/api/v1/stock/profile2",
                            params={"symbol": sym, "token": settings.FINNHUB_API_KEY},
                        )
                        if rp.status_code == 200:
                            out["finnhub_profile"] = rp.json()
            except Exception as e:
                logger.warning("v4_finnhub_failed", error=str(e))
        return out
