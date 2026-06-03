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
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

import httpx
import structlog

from app.config import settings
from app.services.observability import counter
from app.services.v4 import provider_health
from app.services.v4.key_pool import get_pool
from app.services.v4.free_research_provider import get_free_research_provider, FreeCitation
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


# ── India Detection ─────────────────────────────────────────────────

_INDIA_SIGNALS = {
    "keywords": {
        "india", "indian", "bharat", "delhi", "mumbai", "bangalore", "bengaluru",
        "chennai", "hyderabad", "pune", "kolkata", "ahmedabad", "jaipur", "surat",
        "lucknow", "kanpur", "nagpur", "indore", "thane", "bhopal", "visakhapatnam",
        "pimpri", "patna", "vadodara", "ghaziabad", "ludhiana", "agra", "nashik",
        "faridabad", "meerut", "rajkot", "varanasi", "srinagar", "aurangabad",
        "dhanbad", "amritsar", "navi mumbai", "allahabad", "ranchi", "howrah",
        "jabalpur", "gwalior", "vijayawada", "jodhpur", "madurai", "raipur",
        "kota", "guwahati", "chandigarh", "solapur", "hubli", "mysore", "tiruchirappalli",
        "tiruppur", "gurgaon", "aligarh", "jalandhar", "bhubaneswar", "salem",
        "mira-bhayandar", "varanasi", "thane", "bhiwandi", "saharanpur", "guntur",
        "amravati", "bikaner", "noida", "jamshedpur", "bareilly", "howrah", "tumkur",
        "cuttack", "warangal", "tirupati", "mangalore", "belgaum", "dehradun",
        "muzaffarnagar", "nellore", "jammu", "bhatpara", "kollam", "kakinada",
        "berhampur", "ambattur", "tanuku", "bally", "kharagpur", "tinsukia",
        "nizamabad", "durgapur", "bhimavaram", "nagercoil", "bhagalpur", "rourkela",
        "ramagundam", "silchar", "ulhasnagar", "jorhat", "deoghar", "chhapra",
        "haldia", "khandwa", "nandyal", "morena", "amroha", "anantapur",
        "bhind", "bhilwara", "bhiwani", "bokaro", "chittoor", "darbhanga",
        "dehri", "dhanbad", "dibrugarh", "dimapur", "etawah", "faizabad", "giridih",
        "guntakal", "hajipur", "hissar", "hospet", "jind", "jagdalpur", "jehanabad",
        "khammam", "kota", "kumbakonam", "machilipatnam", "madhyamgram", "mahbubnagar",
        "mahesana", "mehsana", "mirzapur", "moradabad", "muzaffarpur", "mysore",
        "nanded", "narsinghpur", "nellore", "nizamabad", "ongole", "panipat", "purnia",
        "raebareli", "raiganj", "rajkot", "ramagundam", "ratlam", "rohtak", "sagar",
        "saharsa", "sambalpur", "sangli-miraj & kupwad", "santipur", "shimla", "sikar",
        "silchar", "singrauli", "sirsa", "sultanpur", "surat", "tenali", "thoothukudi",
        "tumkur", "udaipur", "ujjain", "vellore", "veraval", "vijayanagaram", "visakhapatnam",
        "vizianagaram", "warangal", "yavatmal",
        "karnataka", "maharashtra", "tamil nadu", "telangana", "gujarat", "rajasthan",
        "west bengal", "madhya pradesh", "uttar pradesh", "kerala", "andhra pradesh",
        "bihar", "punjab", "haryana", "odisha", "jharkhand", "chhattisgarh", "uttarakhand",
        "himachal pradesh", "goa", "jammu & kashmir", "assam", "meghalaya", "manipur",
        "tripura", "nagaland", "mizoram", "arunachal pradesh", "sikkim",
        "rupee", "rs.", "₹", "crore", "lakh", "arab", "kharab",
        "rbi", "reserve bank of india", "sebi", "nse", "bse", "nifty", "sensex",
        "flipkart", "paytm", "zomato", "swiggy", "ola", "uber india", "byju's",
        "infosys", "tcs", "wipro", "hcl", "tech mahindra", "reliance", "tata",
        "adani", "ambani", "mukesh ambani", "gautam adani", "ratan tata",
        "pm modi", "narendra modi", "modi", "bjp", "inc", "congress", "aap",
        "startup india", "make in india", "digital india", "swachh bharat",
    },
    "domains": {
        ".in", ".co.in", ".ac.in", ".edu.in", ".gov.in", ".nic.in", ".org.in",
        "inc42.com", "yourstory.com", "economictimes.indiatimes.com", "timesofindia.indiatimes.com",
        "hindustantimes.com", "thehindu.com", "indiatimes.com", "moneycontrol.com",
        "business-standard.com", "livemint.com", "financial-express.com", "news18.com",
        "ndtv.com", "indianexpress.com", "deccanherald.com", "telegraphindia.com",
        "theprint.in", "scroll.in", "thewire.in", "altnews.in", "newslaundry.com",
    },
    "companies": {
        "flipkart", "paytm", "zomato", "swiggy", "ola", "byju's", "infosys", "tcs",
        "wipro", "hcl", "tech mahindra", "reliance", "tata group", "tata motors",
        "tata steel", "tata power", "tata consultancy services", "adani group",
        "adani enterprises", "adani ports", "hdfc", "icici", "sbi", "axis bank",
        "kotak", "hul", "itc", "larsen & toubro", "mahindra & mahindra",
        "maruti suzuki", "bajaj auto", "hero motocorp", "titan", "britannia",
        "nestle india", "hindustan unilever", "itc limited", "dr. reddy's",
        "sun pharma", "cipla", "lupin", "australian", "divi's laboratories",
        "zomato", "delhivery", "nykaa", "freshworks", "razorpay", "phonepe",
        "gupshup", "sharechat", "byju's", "unacademy", "vedantu", "whitehat jr",
        "zerodha", "groww", "upstox", "coin", "paytm money", "zerodha",
        "policybazaar", "aegon life", "paisabazaar", "bankbazaar", "bigbasket",
        "grofers", "blinkit", "dunzo", "shadowfax", "ekart", "e-kart",
        "myntra", "ajio", "nykaa", "purplle", "myglamm", "tata cliq",
        "croma", "reliance digital", "vijay sales", "samsung india", "lg india",
        "whirlpool india", "godrej", "dabur", "emami", "marico", "colgate-palmolive india",
        "hindustan unilever", "itc", "nestle india", "britannia", "amul",
        "mother dairy", "parle", "britannia", "cadbury india", "mondelez india",
    },
}


def is_india_relevant(
    query: str,
    company_name: Optional[str] = None,
    industry: Optional[str] = None,
) -> bool:
    """Detect if the research request is India-relevant.
    
    Returns True if:
    - Query contains India-specific keywords
    - Company is Indian (known Indian companies)
    - URLs in query are Indian domains
    - Industry is India-focused
    
    Used to trigger India-specific research sources (Inc42, YourStory, ET).
    """
    query_lower = query.lower()
    company_lower = (company_name or "").lower()
    industry_lower = (industry or "").lower()
    
    def _contains_signal(text: str, signal: str) -> bool:
        if not text or not signal:
            return False
        signal = signal.strip().lower()
        if not signal:
            return False
        # Short tokens like "inc" must not match inside words such as
        # "computing". Exact word boundaries prevent false India routing.
        if len(signal) <= 3 or re.fullmatch(r"[a-z0-9]+", signal):
            return bool(re.search(rf"\b{re.escape(signal)}\b", text))
        return signal in text

    # Check keywords
    for keyword in _INDIA_SIGNALS["keywords"]:
        if (
            _contains_signal(query_lower, keyword)
            or _contains_signal(company_lower, keyword)
            or _contains_signal(industry_lower, keyword)
        ):
            return True
    
    # Check domains in query
    for domain in _INDIA_SIGNALS["domains"]:
        if _contains_signal(query_lower, domain):
            return True
    
    # Check company names
    for company in _INDIA_SIGNALS["companies"]:
        if _contains_signal(company_lower, company):
            return True
    
    return False


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
    raw: dict[str, Any] = field(default_factory=dict)  # Raw metadata for purpose-aware research
    # Slice 3 (Provider-Failure Visibility) — per-provider outcome map.
    # Keyed by provider name (e.g. "tavily", "exa", "newsapi"). Each
    # value is {status, citation_count, latency_ms, failure_reason?}.
    # Older callers that construct ResearchPacket directly (tests,
    # cached payload restoration) get an empty dict by default and
    # remain unchanged.
    provider_summary: dict[str, dict[str, Any]] = field(default_factory=dict)

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

    @staticmethod
    def _provider_query(
        query: str,
        *,
        industry: Optional[str] = None,
        company_name: Optional[str] = None,
        max_chars: int = 120,
    ) -> str:
        """Convert a form-like prompt into a compact search query.

        Search APIs reject or degrade on long multiline prompt blobs. The
        provider query should carry the product/topic and the technical terms,
        while the original prompt remains available to the planner/writer.
        """
        raw = (query or "").strip()
        if not raw:
            return ""

        label_re = (
            r"(?:presentation\s+topic|topic|title)\s*:\s*"
            r"(.+?)"
            r"(?=(?:\s*[\.\n]\s*)?"
            r"(?:description|target\s+audience|audience|purpose|slide\s+count|key\s+points)\s*:|$)"
        )
        match = re.search(label_re, raw, re.IGNORECASE | re.DOTALL)
        parts: list[str] = []
        if match:
            parts.append(match.group(1))
        elif len(raw) <= max_chars and "\n" not in raw:
            parts.append(raw)
        else:
            first_sentence = re.split(r"[\.\n]", raw, maxsplit=1)[0]
            parts.append(first_sentence)

        lower = raw.lower()
        term_map = {
            "zero-trust": "zero-trust",
            "zero trust": "zero-trust",
            "edge computing": "edge computing",
            "iot": "IoT",
            "decentralized identifiers": "decentralized identifiers",
            "did": "DIDs",
            "zero-knowledge": "zero-knowledge proofs",
            "zk": "zero-knowledge proofs",
            "hardware-root-of-trust": "hardware root of trust",
            "hardware root of trust": "hardware root of trust",
            "sub-millisecond": "sub-millisecond latency",
            "low-bandwidth": "low-bandwidth",
            "neural-guardian": "Neural-Guardian consensus",
            "o(1)": "O(1) scalability",
        }
        for needle, term in term_map.items():
            if needle in lower and term not in parts:
                parts.append(term)

        if industry:
            parts.append(industry)
        if company_name:
            parts.append(company_name)

        compact = " ".join(str(p).strip() for p in parts if str(p).strip())
        compact = re.sub(r"\$([^$]+)\$", r"\1", compact)
        compact = re.sub(r"[^A-Za-z0-9\s\-/().]", " ", compact)
        compact = re.sub(r"\s+", " ", compact).strip()
        if len(compact) > max_chars:
            compact = compact[:max_chars].rsplit(" ", 1)[0].strip()
        return compact or raw[:max_chars].strip()

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

        original_query = query
        query = self._provider_query(
            query,
            industry=industry,
            company_name=company_name,
        )

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
        # Slice 3 — wrap each provider with a tracker so we can record
        # per-provider {status, latency_ms, citation_count, failure_reason}
        # without touching the individual provider methods. The tracker
        # is best-effort: failures inside it never break collection.
        provider_summary: dict[str, dict[str, Any]] = {}

        def _track_provider(name: str, coro):
            async def _wrapped():
                started = time.perf_counter()
                try:
                    result = await coro
                except Exception as exc:  # noqa: BLE001
                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    provider_summary[name] = {
                        "status": "failed",
                        "citation_count": 0,
                        "latency_ms": elapsed_ms,
                        "failure_reason": str(exc)[:200],
                    }
                    await counter("v4.provider.failed", {"provider": name, "mode": mode})
                    raise
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                count = len(result) if isinstance(result, list) else 0
                # Distinguish "ran clean but returned nothing" from "ok".
                # An empty list could mean: muted, empty key pool, or zero
                # results. We mark "empty" so the metrics layer can spot
                # silent degradation.
                provider_summary[name] = {
                    "status": "ok" if count > 0 else "empty",
                    "citation_count": count,
                    "latency_ms": elapsed_ms,
                }
                return result
            return _wrapped()

        web_tasks: list = []
        for name in profile.web_providers:
            coro = self._dispatch_web_provider(name, query, recency, profile)
            if coro is not None:
                web_tasks.append(_track_provider(name, coro))
        news_tasks: list = []
        for name in profile.news_providers:
            coro = self._dispatch_news_provider(name, query, recency, profile)
            if coro is not None:
                news_tasks.append(_track_provider(name, coro))
        
        # India-specific news providers when India is detected
        if is_india_relevant(query, company_name, industry):
            india_providers = ["inc42", "yourstory", "economic_times"]
            for name in india_providers:
                coro = self._dispatch_news_provider(name, query, recency, profile)
                if coro is not None:
                    news_tasks.append(_track_provider(name, coro))
            logger.info("v4_india_detected", query=query[:80], providers=india_providers)

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

        # Free research fallback when citations are sparse
        if len(citations) < 3:
            logger.info("v4_research_fallback_triggered", n_existing=len(citations))
            try:
                free_citations = await self._free_research_fallback(query, profile=profile)
                for c in free_citations:
                    if c.url and c.url not in seen_urls:
                        seen_urls.add(c.url)
                        citations.append(c)
            except Exception as e:
                logger.warning("v4_research_fallback_failed", error=str(e))

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
            provider_summary=provider_summary,
        )
        if original_query != query:
            packet.raw["original_query"] = original_query
            packet.raw["provider_query"] = query

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

    async def collect_purpose_aware(
        self,
        user_prompt: str,
        purpose: str,
        mode: str = "standard",
        industry: Optional[str] = None,
        company_name: Optional[str] = None,
        research_depth: Optional[str] = None,
        profile: Optional[DepthProfile] = None,
        recency: Optional[RecencyWindow] = None,
    ) -> ResearchPacket:
        """Collect research with purpose-specific focus (EXTENDED METHOD).

        This method adjusts research depth and focus based on the presentation purpose.
        For Standard Mode, it uses purpose configuration to tailor the research.

        Args:
            user_prompt: User's input prompt
            purpose: Selected presentation purpose (e.g., "deep_tech", "vc_pitch")
            mode: Generation mode ("standard" or "premium")
            industry: Industry context
            company_name: Company name for financial lookups
            research_depth: Legacy depth string (for backwards compatibility)
            profile: Depth profile (overrides purpose-based selection)
            recency: Recency window (overrides purpose-based selection)

        Returns:
            ResearchPacket with purpose-tailored evidence
        """
        # Get purpose configuration
        from app.services.v4.purpose_configs import PURPOSE_CONFIGS
        config = PURPOSE_CONFIGS.get(purpose)

        # Adjust research depth based on purpose
        if config and profile is None:
            if config.technical_depth == "high":
                depth_profile = "technical_deep"
            elif config.focus_area == "The Market":
                depth_profile = "market_intelligence"
            elif config.focus_area == "The ROI":
                depth_profile = "financial_deep"
            else:
                depth_profile = "standard"
            
            # Override research_depth if not explicitly provided
            if research_depth is None:
                research_depth = depth_profile

        # Call the existing collect method with purpose-aware parameters
        packet = await self.collect(
            query=user_prompt,
            industry=industry,
            company_name=company_name,
            mode=mode,
            research_depth=research_depth,
            profile=profile,
            recency=recency,
            purpose=purpose,
        )

        # Ensure evidence sources are included
        if not packet.financial_data:
            packet.financial_data = {}
        if not packet.social_signals:
            packet.social_signals = {}

        # Add purpose metadata to the packet
        packet.raw["purpose"] = purpose
        if config:
            packet.raw["purpose_focus_area"] = config.focus_area
            packet.raw["purpose_technical_depth"] = config.technical_depth

        logger.info(
            "purpose_aware_research_complete",
            purpose=purpose,
            focus_area=config.focus_area if config else None,
            technical_depth=config.technical_depth if config else None,
            n_citations=len(packet.citations),
            n_news=len(packet.news_citations),
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
        if name == "linkup":
            return self._linkup(query, recency=recency, profile=profile)
        if name == "searchapi":
            return self._searchapi(query, recency=recency, profile=profile)
        if name == "zenserp":
            return self._zenserp(query, recency=recency, profile=profile)
        if name == "valueserp":
            return self._valueserp(query, recency=recency, profile=profile)
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
        if name == "inc42":
            return self._inc42_rss(query, recency=recency, profile=profile)
        if name == "yourstory":
            return self._yourstory_rss(query, recency=recency, profile=profile)
        if name == "economic_times":
            return self._economic_times_rss(query, recency=recency, profile=profile)
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
        # Tavily search using official tavily-python SDK with key pool rotation
        if not provider_health.is_healthy("tavily"):
            return []
        pool = get_pool("tavily", settings.tavily_keys)
        if pool.empty:
            return []
        key = await pool.acquire()
        if not key:
            return []
        limit = self._result_limit(profile, 8)
        timeout_s = profile.per_provider_timeout_s if profile else self.HTTP_TIMEOUT
        try:
            body: dict[str, Any] = {
                "query": query,
                "search_depth": "basic",
                "max_results": limit,
                "topic": "general",
            }
            if recency is not None:
                body["days"] = min(recency.days_back(), 365)

            client = await self._http()
            r = await client.post(
                "https://api.tavily.com/search",
                json=body,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                timeout=httpx.Timeout(timeout_s),
            )
            r.raise_for_status()
            response = r.json()
            
            await pool.report_success(key)
            provider_health.record("tavily", success=True)
            
            out: list[Citation] = []
            for item in response.get("results", []):
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
            await pool.report_failure(key, _classify_status(e))
            provider_health.record("tavily", success=False)
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
        # You.com search using official youdotcom SDK with key pool rotation
        if not provider_health.is_healthy("you_com"):
            return []
        pool = get_pool("you_com", settings.you_com_keys)
        if pool.empty:
            return []
        key = await pool.acquire()
        if not key:
            return []
        limit = self._result_limit(profile, 8)
        timeout_s = profile.per_provider_timeout_s if profile else self.HTTP_TIMEOUT
        try:
            from youdotcom import You

            def _search() -> Any:
                # The official SDK is synchronous. Keep it off the
                # FastAPI event loop so health/status endpoints remain live
                # while a provider is slow or rate-limited.
                you = You(api_key_auth=key)
                return you.search.unified(query=query, count=limit)

            response = await asyncio.wait_for(
                asyncio.to_thread(_search),
                timeout=timeout_s,
            )
            
            await pool.report_success(key)
            provider_health.record("you_com", success=True)
            
            out: list[Citation] = []
            # Handle response structure from SDK
            results = response.get("results", {}) if isinstance(response, dict) else {}
            web_results = results.get("web", []) if isinstance(results, dict) else []
            
            for item in web_results[:limit]:
                url = item.get("url", "")
                out.append(Citation(
                    title=item.get("title", ""),
                    url=url,
                    snippet=" ".join(item.get("snippets", []))[:500] if item.get("snippets") else (item.get("description", "")[:500]),
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

    # ── New AI-search / web-search providers (added 2026-05-25) ──────
    # Each follows the canonical Tavily template: health gate, key pool
    # acquisition, profile-driven timeout/limit, recency translation,
    # provider-specific request, Citation mapping, success/failure
    # bookkeeping, silent skip on exception. All four are standard SERP
    # APIs that return ``organic`` / ``results`` arrays of titled URLs.

    async def _linkup(
        self,
        query: str,
        *,
        recency: Optional[RecencyWindow] = None,
        profile: Optional[DepthProfile] = None,
    ) -> list[Citation]:
        """Linkup AI-search engine — https://api.linkup.so/v1/search.

        Uses POST with JSON body. ``includeImages`` is omitted because
        the collector wants snippets and URLs only. ``depth=standard``
        gives a balance of latency and result quality; ``deep`` adds
        ~3s per call. We map the user's ``recency`` window to the
        ``fromDate`` ISO-8601 parameter when the API supports it.
        """
        if not provider_health.is_healthy("linkup"):
            return []
        pool = get_pool("linkup", settings.linkup_keys)
        if pool.empty:
            return []
        key = await pool.acquire()
        if not key:
            return []
        timeout_s = profile.per_provider_timeout_s if profile else self.HTTP_TIMEOUT
        limit = self._result_limit(profile, 8)
        body: dict[str, Any] = {
            "q": query,
            "depth": "deep" if profile and profile.label == "deep" else "standard",
            "outputType": "searchResults",
            "includeImages": False,
        }
        if recency is not None:
            body["fromDate"] = recency.earliest.isoformat()
        try:
            client = await self._http()
            r = await client.post(
                "https://api.linkup.so/v1/search",
                json=body,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(timeout_s),
            )
            r.raise_for_status()
            data = r.json()
            await pool.report_success(key)
            provider_health.record("linkup", success=True)
            results = data.get("results") or data.get("data") or []
            out: list[Citation] = []
            for item in results[:limit]:
                if not isinstance(item, dict):
                    continue
                url = item.get("url") or item.get("link") or ""
                if not url:
                    continue
                snippet = (
                    item.get("content")
                    or item.get("snippet")
                    or item.get("description")
                    or ""
                )
                out.append(Citation(
                    title=item.get("title", ""),
                    url=url,
                    snippet=str(snippet)[:500],
                    source="linkup",
                    source_authority=_score_authority(url),
                    published_at=item.get("publishedDate")
                    or item.get("date")
                    or item.get("published_at"),
                ))
            return out
        except Exception as e:
            status_code = _classify_status(e)
            await pool.report_failure(key, status_code)
            provider_health.record("linkup", success=False)
            if _is_terminal_provider_status(status_code):
                logger.info("v4_linkup_unavailable", error=str(e), status=status_code)
            else:
                logger.warning("v4_linkup_failed", error=str(e), status=status_code)
            return []

    async def _searchapi(
        self,
        query: str,
        *,
        recency: Optional[RecencyWindow] = None,
        profile: Optional[DepthProfile] = None,
    ) -> list[Citation]:
        """SearchAPI Google SERP — https://www.searchapi.io/api/v1/search.

        Uses GET with query params; key is supplied as ``api_key``.
        Recency is mapped to the Google ``tbs`` parameter (qdr:w/m/y)
        the same way Serper handles it, so we get consistent freshness
        behavior across engines.
        """
        if not provider_health.is_healthy("searchapi"):
            return []
        pool = get_pool("searchapi", settings.searchapi_keys)
        if pool.empty:
            return []
        key = await pool.acquire()
        if not key:
            return []
        timeout_s = profile.per_provider_timeout_s if profile else self.HTTP_TIMEOUT
        limit = self._result_limit(profile, 10)
        params: dict[str, Any] = {
            "engine": "google",
            "q": query,
            "num": limit,
            "api_key": key,
        }
        if recency is not None:
            days = recency.days_back()
            if days <= 7:
                params["tbs"] = "qdr:w"
            elif days <= 30:
                params["tbs"] = "qdr:m"
            elif days <= 365:
                params["tbs"] = "qdr:y"
        try:
            client = await self._http()
            r = await client.get(
                "https://www.searchapi.io/api/v1/search",
                params=params,
                timeout=httpx.Timeout(timeout_s),
            )
            r.raise_for_status()
            data = r.json()
            await pool.report_success(key)
            provider_health.record("searchapi", success=True)
            organic = data.get("organic_results") or []
            out: list[Citation] = []
            for item in organic[:limit]:
                url = item.get("link") or item.get("url") or ""
                if not url:
                    continue
                out.append(Citation(
                    title=item.get("title", ""),
                    url=url,
                    snippet=(item.get("snippet") or "")[:500],
                    source="searchapi",
                    source_authority=_score_authority(url),
                    published_at=item.get("date"),
                ))
            return out
        except Exception as e:
            status_code = _classify_status(e)
            await pool.report_failure(key, status_code)
            provider_health.record("searchapi", success=False)
            if _is_terminal_provider_status(status_code):
                logger.info("v4_searchapi_unavailable", error=str(e), status=status_code)
            else:
                logger.warning("v4_searchapi_failed", error=str(e), status=status_code)
            return []

    async def _zenserp(
        self,
        query: str,
        *,
        recency: Optional[RecencyWindow] = None,
        profile: Optional[DepthProfile] = None,
    ) -> list[Citation]:
        """Zenserp Google SERP — https://app.zenserp.com/api/v2/search.

        GET with ``q`` and ``apikey`` (NOT a Bearer header). Recency
        again uses Google ``tbs`` mapping for consistency.
        """
        if not provider_health.is_healthy("zenserp"):
            return []
        pool = get_pool("zenserp", settings.zenserp_keys)
        if pool.empty:
            return []
        key = await pool.acquire()
        if not key:
            return []
        timeout_s = profile.per_provider_timeout_s if profile else self.HTTP_TIMEOUT
        limit = self._result_limit(profile, 10)
        params: dict[str, Any] = {"q": query, "num": limit}
        if recency is not None:
            days = recency.days_back()
            if days <= 7:
                params["tbs"] = "qdr:w"
            elif days <= 30:
                params["tbs"] = "qdr:m"
            elif days <= 365:
                params["tbs"] = "qdr:y"
        try:
            client = await self._http()
            r = await client.get(
                "https://app.zenserp.com/api/v2/search",
                params=params,
                headers={"apikey": key},
                timeout=httpx.Timeout(timeout_s),
            )
            r.raise_for_status()
            data = r.json()
            await pool.report_success(key)
            provider_health.record("zenserp", success=True)
            organic = data.get("organic") or []
            out: list[Citation] = []
            for item in organic[:limit]:
                url = item.get("url") or item.get("link") or ""
                if not url:
                    continue
                out.append(Citation(
                    title=item.get("title", ""),
                    url=url,
                    snippet=(item.get("description") or item.get("snippet") or "")[:500],
                    source="zenserp",
                    source_authority=_score_authority(url),
                    published_at=item.get("date"),
                ))
            return out
        except Exception as e:
            status_code = _classify_status(e)
            await pool.report_failure(key, status_code)
            provider_health.record("zenserp", success=False)
            if _is_terminal_provider_status(status_code):
                logger.info("v4_zenserp_unavailable", error=str(e), status=status_code)
            else:
                logger.warning("v4_zenserp_failed", error=str(e), status=status_code)
            return []

    async def _valueserp(
        self,
        query: str,
        *,
        recency: Optional[RecencyWindow] = None,
        profile: Optional[DepthProfile] = None,
    ) -> list[Citation]:
        """ValueSerp Google SERP — https://api.valueserp.com/search.

        GET with ``api_key`` and ``q``. Returns ``organic_results``.
        """
        if not provider_health.is_healthy("valueserp"):
            return []
        pool = get_pool("valueserp", settings.valueserp_keys)
        if pool.empty:
            return []
        key = await pool.acquire()
        if not key:
            return []
        timeout_s = profile.per_provider_timeout_s if profile else self.HTTP_TIMEOUT
        limit = self._result_limit(profile, 10)
        params: dict[str, Any] = {
            "api_key": key,
            "q": query,
            "num": limit,
            "output": "json",
        }
        if recency is not None:
            days = recency.days_back()
            if days <= 7:
                params["time_period"] = "last_week"
            elif days <= 30:
                params["time_period"] = "last_month"
            elif days <= 365:
                params["time_period"] = "last_year"
        try:
            client = await self._http()
            r = await client.get(
                "https://api.valueserp.com/search",
                params=params,
                timeout=httpx.Timeout(timeout_s),
            )
            r.raise_for_status()
            data = r.json()
            await pool.report_success(key)
            provider_health.record("valueserp", success=True)
            organic = data.get("organic_results") or []
            out: list[Citation] = []
            for item in organic[:limit]:
                url = item.get("link") or item.get("url") or ""
                if not url:
                    continue
                out.append(Citation(
                    title=item.get("title", ""),
                    url=url,
                    snippet=(item.get("snippet") or "")[:500],
                    source="valueserp",
                    source_authority=_score_authority(url),
                    published_at=item.get("date"),
                ))
            return out
        except Exception as e:
            status_code = _classify_status(e)
            await pool.report_failure(key, status_code)
            provider_health.record("valueserp", success=False)
            if _is_terminal_provider_status(status_code):
                logger.info("v4_valueserp_unavailable", error=str(e), status=status_code)
            else:
                logger.warning("v4_valueserp_failed", error=str(e), status=status_code)
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

    async def _inc42_rss(
        self,
        query: str,
        *,
        recency: Optional[RecencyWindow] = None,
        profile: Optional[DepthProfile] = None,
    ) -> list[Citation]:
        """Fetch Inc42 RSS feed for Indian startup news."""
        timeout_s = profile.per_provider_timeout_s if profile else self.HTTP_TIMEOUT
        limit = self._result_limit(profile, 8)
        try:
            client = await self._http()
            r = await client.get(
                "https://inc42.com/feed/",
                timeout=httpx.Timeout(timeout_s),
            )
            r.raise_for_status()
            import xml.etree.ElementTree as ET
            root = ET.fromstring(r.content)
            out: list[Citation] = []
            for item in root.findall(".//item")[:limit]:
                title = item.find("title")
                link = item.find("link")
                description = item.find("description")
                pub_date = item.find("pubDate")
                
                if title is not None and link is not None:
                    title_text = title.text or ""
                    url = link.text or ""
                    # Strip HTML from description
                    desc_text = ""
                    if description is not None and description.text:
                        import re
                        desc_text = re.sub(r'<[^>]+>', '', description.text)[:500]
                    
                    # Filter by query relevance
                    query_lower = query.lower()
                    if query_lower in title_text.lower() or query_lower in desc_text.lower():
                        out.append(Citation(
                            title=title_text,
                            url=url,
                            snippet=desc_text,
                            source="inc42",
                            source_authority=0.8,  # High authority for Indian startups
                            published_at=pub_date.text if pub_date is not None else None,
                        ))
            return out
        except Exception as e:
            logger.warning("v4_inc42_rss_failed", error=str(e))
            return []

    async def _yourstory_rss(
        self,
        query: str,
        *,
        recency: Optional[RecencyWindow] = None,
        profile: Optional[DepthProfile] = None,
    ) -> list[Citation]:
        """Fetch YourStory RSS feed for Indian startup news."""
        timeout_s = profile.per_provider_timeout_s if profile else self.HTTP_TIMEOUT
        limit = self._result_limit(profile, 8)
        try:
            client = await self._http()
            r = await client.get(
                "https://yourstory.com/feed",
                timeout=httpx.Timeout(timeout_s),
            )
            r.raise_for_status()
            import xml.etree.ElementTree as ET
            root = ET.fromstring(r.content)
            out: list[Citation] = []
            for item in root.findall(".//item")[:limit]:
                title = item.find("title")
                link = item.find("link")
                description = item.find("description")
                pub_date = item.find("pubDate")
                
                if title is not None and link is not None:
                    title_text = title.text or ""
                    url = link.text or ""
                    # Strip HTML from description
                    desc_text = ""
                    if description is not None and description.text:
                        import re
                        desc_text = re.sub(r'<[^>]+>', '', description.text)[:500]
                    
                    # Filter by query relevance
                    query_lower = query.lower()
                    if query_lower in title_text.lower() or query_lower in desc_text.lower():
                        out.append(Citation(
                            title=title_text,
                            url=url,
                            snippet=desc_text,
                            source="yourstory",
                            source_authority=0.8,  # High authority for Indian startups
                            published_at=pub_date.text if pub_date is not None else None,
                        ))
            return out
        except Exception as e:
            logger.warning("v4_yourstory_rss_failed", error=str(e))
            return []

    async def _economic_times_rss(
        self,
        query: str,
        *,
        recency: Optional[RecencyWindow] = None,
        profile: Optional[DepthProfile] = None,
    ) -> list[Citation]:
        """Fetch Economic Times RSS feed for Indian business news."""
        timeout_s = profile.per_provider_timeout_s if profile else self.HTTP_TIMEOUT
        limit = self._result_limit(profile, 8)
        try:
            client = await self._http()
            r = await client.get(
                "https://economictimes.indiatimes.com/rssfeeds/default.cms",
                timeout=httpx.Timeout(timeout_s),
            )
            r.raise_for_status()
            import xml.etree.ElementTree as ET
            root = ET.fromstring(r.content)
            out: list[Citation] = []
            for item in root.findall(".//item")[:limit]:
                title = item.find("title")
                link = item.find("link")
                description = item.find("description")
                pub_date = item.find("pubDate")
                
                if title is not None and link is not None:
                    title_text = title.text or ""
                    url = link.text or ""
                    # Strip HTML from description
                    desc_text = ""
                    if description is not None and description.text:
                        import re
                        desc_text = re.sub(r'<[^>]+>', '', description.text)[:500]
                    
                    # Filter by query relevance
                    query_lower = query.lower()
                    if query_lower in title_text.lower() or query_lower in desc_text.lower():
                        out.append(Citation(
                            title=title_text,
                            url=url,
                            snippet=desc_text,
                            source="economic_times",
                            source_authority=0.85,  # High authority for Indian business
                            published_at=pub_date.text if pub_date is not None else None,
                        ))
            return out
        except Exception as e:
            logger.warning("v4_economic_times_rss_failed", error=str(e))
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

    async def _free_research_fallback(
        self,
        query: str,
        *,
        profile: Optional[DepthProfile] = None,
    ) -> list[Citation]:
        """
        Free research fallback using Wikipedia and DuckDuckGo.
        
        Called when paid APIs fail or return empty results.
        Works without any API keys - perfect for Docker deployment.
        """
        try:
            provider = get_free_research_provider()
            limit = self._result_limit(profile, 8)
            result = await provider.research(query, max_results=limit)
            
            # Convert FreeCitation to Citation
            out: list[Citation] = []
            for fc in result.citations:
                out.append(Citation(
                    title=fc.title,
                    url=fc.url,
                    snippet=fc.snippet,
                    source=fc.source,
                    source_authority=fc.source_authority,
                    published_at=fc.published_at,
                ))
            
            logger.info(
                "v4_free_research_success",
                query=query[:50],
                sources=result.sources_used,
                n_citations=len(out),
            )
            return out
        except Exception as e:
            logger.warning("v4_free_research_failed", error=str(e))
            return []
