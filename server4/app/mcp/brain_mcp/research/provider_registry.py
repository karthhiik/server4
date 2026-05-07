"""
Provider Registry — complete inventory of 40+ external API providers.

Reads the app Settings to determine which providers are configured
(env vars set) and exposes ordered provider chains by evidence type.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from app.config import Settings, settings as _default_settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# PROVIDER CONFIG
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ProviderConfig:
    """Static configuration for a single external provider."""

    name: str
    category: str  # "search"|"scrape"|"news"|"financial"|"social"|"academic"|"specialty"|"llm"
    daily_limit: int
    monthly_limit: int
    rate_limit_per_minute: int
    cost_per_call: float
    env_vars: list[str] = field(default_factory=list)
    is_configured: bool = False
    priority: int = 50  # lower = higher priority

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "daily_limit": self.daily_limit,
            "monthly_limit": self.monthly_limit,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "cost_per_call": self.cost_per_call,
            "env_vars": list(self.env_vars),
            "is_configured": self.is_configured,
            "priority": self.priority,
        }


# ═══════════════════════════════════════════════════════════════════════
# EVIDENCE-TYPE → PROVIDER CHAIN MAPPING
# ═══════════════════════════════════════════════════════════════════════

# Ordered by priority (first = try first). Only providers in the chain
# that are both configured and within limits will be attempted.

_EVIDENCE_CHAINS: dict[str, list[str]] = {
    # General web search
    "web_search": [
        "serper", "tavily", "exa", "serpapi", "you_com", "search_api",
    ],
    # Company / market intelligence
    "market_intelligence": [
        "serper", "tavily", "exa", "firecrawl", "jina", "serpapi",
    ],
    # News / current events
    "news": [
        "guardian", "newsapi", "newsdata", "world_news_api", "serper",
    ],
    # Financial / macro data
    "financial": [
        "fred", "finnhub", "polygon", "fmp", "alpha_vantage", "eodhd",
    ],
    # Crypto / blockchain
    "crypto": [
        "coindesk", "polygon", "finnhub",
    ],
    # Social proof / traction
    "social": [
        "reddit", "github", "youtube", "producthunt",
    ],
    # Academic / research papers
    "academic": [
        "core", "serper", "exa",
    ],
    # Macro / public data
    "macro": [
        "fred", "world_bank", "census",
    ],
    # Deep scraping (JS-heavy or anti-bot sites)
    "scrape": [
        "firecrawl", "jina", "scrapedo",
    ],
    # Science / niche
    "specialty": [
        "api_ninjas", "nasa_apod",
    ],
    # Competitor analysis
    "competitor": [
        "exa", "serper", "tavily", "firecrawl", "github", "producthunt",
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════════════════════


class ProviderRegistry:
    """
    Central registry that knows every provider, its limits, and whether
    the required env vars are present.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or _default_settings
        self._providers: dict[str, ProviderConfig] = {}
        self._build_registry()

    # ── Public API ──────────────────────────────────────────────

    def get_provider(self, name: str) -> ProviderConfig | None:
        return self._providers.get(name)

    def get_providers_for_category(self, category: str) -> list[ProviderConfig]:
        return sorted(
            [p for p in self._providers.values() if p.category == category],
            key=lambda p: p.priority,
        )

    def is_available(self, name: str) -> bool:
        """True if the provider is configured (env vars present)."""
        prov = self._providers.get(name)
        return prov is not None and prov.is_configured

    def get_chain(self, evidence_type: str) -> list[str]:
        """Return ordered provider names for an evidence type, filtered to configured only."""
        chain = _EVIDENCE_CHAINS.get(evidence_type, [])
        return [name for name in chain if self.is_available(name)]

    def all_providers(self) -> dict[str, ProviderConfig]:
        return dict(self._providers)

    def configured_providers(self) -> list[ProviderConfig]:
        return [p for p in self._providers.values() if p.is_configured]

    def summary(self) -> dict[str, Any]:
        """Quick overview for logging / health endpoint."""
        total = len(self._providers)
        configured = sum(1 for p in self._providers.values() if p.is_configured)
        by_category: dict[str, int] = {}
        for p in self._providers.values():
            if p.is_configured:
                by_category[p.category] = by_category.get(p.category, 0) + 1
        return {
            "total_providers": total,
            "configured": configured,
            "unconfigured": total - configured,
            "by_category": by_category,
        }

    # ── Internal build ──────────────────────────────────────────

    def _is_env_set(self, *attr_names: str) -> bool:
        """Check if at least one of the given Settings attributes has a non-empty value."""
        for attr in attr_names:
            val = getattr(self._settings, attr, "")
            if val:
                return True
        return False

    def _register(self, config: ProviderConfig) -> None:
        self._providers[config.name] = config

    def _build_registry(self) -> None:
        s = self._settings

        # ── Web Search ──────────────────────────────────────────

        self._register(ProviderConfig(
            name="serper",
            category="search",
            daily_limit=83,       # ~2500/month ÷ 30 per key, 3 keys
            monthly_limit=7500,   # 3 keys × 2500
            rate_limit_per_minute=60,
            cost_per_call=0.0,
            env_vars=["SERPER_API_KEY"],
            is_configured=self._is_env_set("SERPER_API_KEY"),
            priority=10,
        ))

        self._register(ProviderConfig(
            name="serpapi",
            category="search",
            daily_limit=16,       # 500/month ÷ 30, 2 keys
            monthly_limit=500,    # 2 keys × 250
            rate_limit_per_minute=50,
            cost_per_call=0.0,
            env_vars=["SERPAPI_KEY"],
            is_configured=self._is_env_set("SERPAPI_KEY"),
            priority=30,
        ))

        self._register(ProviderConfig(
            name="tavily",
            category="search",
            daily_limit=33,       # 1000/month ÷ 30
            monthly_limit=1000,
            rate_limit_per_minute=60,
            cost_per_call=0.0,
            env_vars=["TAVILY_API_KEY"],
            is_configured=self._is_env_set("TAVILY_API_KEY"),
            priority=15,
        ))

        self._register(ProviderConfig(
            name="exa",
            category="search",
            daily_limit=33,       # ~1000/month ÷ 30
            monthly_limit=1000,
            rate_limit_per_minute=60,
            cost_per_call=0.0,
            env_vars=["EXA_API_KEY"],
            is_configured=self._is_env_set("EXA_API_KEY"),
            priority=20,
        ))

        self._register(ProviderConfig(
            name="you_com",
            category="search",
            daily_limit=100,
            monthly_limit=3000,
            rate_limit_per_minute=30,
            cost_per_call=0.0,
            env_vars=["YOU_COM_API_KEY"],
            is_configured=self._is_env_set("YOU_COM_API_KEY"),
            priority=40,
        ))

        self._register(ProviderConfig(
            name="search_api",
            category="search",
            daily_limit=50,
            monthly_limit=1500,
            rate_limit_per_minute=30,
            cost_per_call=0.0,
            env_vars=["SEARCH_API_KEY"],
            is_configured=bool(os.getenv("search_api", "")),
            priority=50,
        ))

        # ── Scraping ────────────────────────────────────────────

        self._register(ProviderConfig(
            name="firecrawl",
            category="scrape",
            daily_limit=50,
            monthly_limit=500,    # one-time credits pool
            rate_limit_per_minute=2,  # 2 concurrent
            cost_per_call=0.0,
            env_vars=["FIRECRAWL_API_KEY"],
            is_configured=self._is_env_set("FIRECRAWL_API_KEY"),
            priority=10,
        ))

        self._register(ProviderConfig(
            name="jina",
            category="scrape",
            daily_limit=500,
            monthly_limit=15000,
            rate_limit_per_minute=20,  # reader throttle
            cost_per_call=0.0,
            env_vars=["JINA_API_KEY"],
            is_configured=self._is_env_set("JINA_API_KEY"),
            priority=20,
        ))

        self._register(ProviderConfig(
            name="scrapedo",
            category="scrape",
            daily_limit=100,
            monthly_limit=3000,
            rate_limit_per_minute=30,
            cost_per_call=0.0,
            env_vars=["SCRAPE_DO_API_KEY"],
            is_configured=bool(os.getenv("SCRAPE_DO_API_KEY", "")),
            priority=30,
        ))

        # ── News ────────────────────────────────────────────────

        self._register(ProviderConfig(
            name="newsapi",
            category="news",
            daily_limit=100,
            monthly_limit=3000,
            rate_limit_per_minute=10,
            cost_per_call=0.0,
            env_vars=["NEWSAPI_KEY"],
            is_configured=self._is_env_set("NEWSAPI_KEY"),
            priority=20,
        ))

        self._register(ProviderConfig(
            name="newsdata",
            category="news",
            daily_limit=200,
            monthly_limit=6000,
            rate_limit_per_minute=10,
            cost_per_call=0.0,
            env_vars=["NEWSDATA_API_KEY"],
            is_configured=self._is_env_set("NEWSDATA_API_KEY"),
            priority=30,
        ))

        self._register(ProviderConfig(
            name="guardian",
            category="news",
            daily_limit=500,
            monthly_limit=15000,
            rate_limit_per_minute=1,  # 1/sec → 60/min cap
            cost_per_call=0.0,
            env_vars=["GUARDIAN_API_KEY"],
            is_configured=self._is_env_set("GUARDIAN_API_KEY"),
            priority=10,
        ))

        self._register(ProviderConfig(
            name="world_news_api",
            category="news",
            daily_limit=100,
            monthly_limit=3000,
            rate_limit_per_minute=30,
            cost_per_call=0.0,
            env_vars=["WORLD_NEWS_API_KEY"],
            is_configured=self._is_env_set("WORLD_NEWS_API_KEY"),
            priority=25,
        ))

        # ── Financial ───────────────────────────────────────────

        self._register(ProviderConfig(
            name="fred",
            category="financial",
            daily_limit=5000,
            monthly_limit=150000,
            rate_limit_per_minute=120,
            cost_per_call=0.0,
            env_vars=["FRED_API_KEY"],
            is_configured=self._is_env_set("FRED_API_KEY"),
            priority=5,
        ))

        self._register(ProviderConfig(
            name="alpha_vantage",
            category="financial",
            daily_limit=25,
            monthly_limit=750,
            rate_limit_per_minute=5,
            cost_per_call=0.0,
            env_vars=["ALPHA_VANTAGE_API_KEY"],
            is_configured=self._is_env_set("ALPHA_VANTAGE_API_KEY"),
            priority=40,
        ))

        self._register(ProviderConfig(
            name="finnhub",
            category="financial",
            daily_limit=1500,
            monthly_limit=45000,
            rate_limit_per_minute=60,
            cost_per_call=0.0,
            env_vars=["FINNHUB_API_KEY"],
            is_configured=self._is_env_set("FINNHUB_API_KEY"),
            priority=15,
        ))

        self._register(ProviderConfig(
            name="polygon",
            category="financial",
            daily_limit=500,
            monthly_limit=15000,
            rate_limit_per_minute=5,
            cost_per_call=0.0,
            env_vars=["POLYGON_API_KEY"],
            is_configured=self._is_env_set("POLYGON_API_KEY"),
            priority=20,
        ))

        self._register(ProviderConfig(
            name="fmp",
            category="financial",
            daily_limit=250,
            monthly_limit=7500,
            rate_limit_per_minute=10,
            cost_per_call=0.0,
            env_vars=["FMP_API_KEY"],
            is_configured=self._is_env_set("FMP_API_KEY"),
            priority=25,
        ))

        self._register(ProviderConfig(
            name="eodhd",
            category="financial",
            daily_limit=100,
            monthly_limit=3000,
            rate_limit_per_minute=10,
            cost_per_call=0.0,
            env_vars=["EODHD_API_KEY"],
            is_configured=bool(os.getenv("EODHD_API_key", "")),
            priority=35,
        ))

        self._register(ProviderConfig(
            name="coindesk",
            category="financial",
            daily_limit=500,
            monthly_limit=15000,
            rate_limit_per_minute=30,
            cost_per_call=0.0,
            env_vars=["COINDESK_API_KEY"],
            is_configured=bool(os.getenv("coindesk.com_api_key", "")),
            priority=30,
        ))

        # ── Macro / Public Data ─────────────────────────────────

        self._register(ProviderConfig(
            name="census",
            category="financial",
            daily_limit=500,
            monthly_limit=15000,
            rate_limit_per_minute=60,
            cost_per_call=0.0,
            env_vars=["CENSUS_API_KEY"],
            is_configured=self._is_env_set("CENSUS_API_KEY"),
            priority=15,
        ))

        self._register(ProviderConfig(
            name="world_bank",
            category="financial",
            daily_limit=10000,   # no auth needed
            monthly_limit=300000,
            rate_limit_per_minute=120,
            cost_per_call=0.0,
            env_vars=[],
            is_configured=True,  # no auth needed
            priority=10,
        ))

        # ── Social ──────────────────────────────────────────────

        self._register(ProviderConfig(
            name="reddit",
            category="social",
            daily_limit=1000,
            monthly_limit=30000,
            rate_limit_per_minute=60,
            cost_per_call=0.0,
            env_vars=["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"],
            is_configured=(
                self._is_env_set("REDDIT_CLIENT_ID")
                and self._is_env_set("REDDIT_CLIENT_SECRET")
            ),
            priority=10,
        ))

        self._register(ProviderConfig(
            name="github",
            category="social",
            daily_limit=5000,
            monthly_limit=150000,
            rate_limit_per_minute=83,  # 5000/hr
            cost_per_call=0.0,
            env_vars=["GITHUB_TOKEN"],
            is_configured=self._is_env_set("GITHUB_TOKEN"),
            priority=15,
        ))

        self._register(ProviderConfig(
            name="youtube",
            category="social",
            daily_limit=100,     # 10000 units/day, search = 100 units each
            monthly_limit=3000,
            rate_limit_per_minute=10,
            cost_per_call=0.0,
            env_vars=["YOUTUBE_API_KEY"],
            is_configured=self._is_env_set("YOUTUBE_API_KEY"),
            priority=20,
        ))

        self._register(ProviderConfig(
            name="producthunt",
            category="social",
            daily_limit=200,
            monthly_limit=6000,
            rate_limit_per_minute=20,
            cost_per_call=0.0,
            env_vars=["PRODUCTHUNT_API_KEY"],
            is_configured=self._is_env_set("PRODUCTHUNT_API_KEY"),
            priority=25,
        ))

        # ── Academic ────────────────────────────────────────────

        self._register(ProviderConfig(
            name="core",
            category="academic",
            daily_limit=1000,
            monthly_limit=30000,
            rate_limit_per_minute=6,   # 1 batch or 5 single per 10s
            cost_per_call=0.0,
            env_vars=["CORE_API_KEY"],
            is_configured=self._is_env_set("CORE_API_KEY"),
            priority=10,
        ))

        # ── Specialty ───────────────────────────────────────────

        self._register(ProviderConfig(
            name="api_ninjas",
            category="specialty",
            daily_limit=500,
            monthly_limit=15000,
            rate_limit_per_minute=30,
            cost_per_call=0.0,
            env_vars=["API_NINJAS_KEY"],
            is_configured=bool(os.getenv("API_NINJAS_KEY", "")),
            priority=10,
        ))

        self._register(ProviderConfig(
            name="nasa_apod",
            category="specialty",
            daily_limit=1000,
            monthly_limit=30000,
            rate_limit_per_minute=60,  # 1000/hr
            cost_per_call=0.0,
            env_vars=["NASA_APOD_API"],
            is_configured=bool(os.getenv("NASA_APDO_API", "")),
            priority=20,
        ))

        self._register(ProviderConfig(
            name="abuseipdb",
            category="specialty",
            daily_limit=100,
            monthly_limit=3000,
            rate_limit_per_minute=10,
            cost_per_call=0.0,
            env_vars=["ABUSEIPDB_API"],
            is_configured=bool(os.getenv("ABUSELPDB_API", "")),
            priority=50,
        ))

        # ── LLM providers ──────────────────────────────────────

        self._register(ProviderConfig(
            name="azure_kimi",
            category="llm",
            daily_limit=10000,
            monthly_limit=300000,
            rate_limit_per_minute=60,
            cost_per_call=0.001,   # subscription
            env_vars=["AZURE_KIMI_ENDPOINT", "AZURE_KIMI_API_KEY"],
            is_configured=(
                self._is_env_set("AZURE_KIMI_ENDPOINT")
                and self._is_env_set("AZURE_KIMI_API_KEY")
            ),
            priority=5,
        ))

        self._register(ProviderConfig(
            name="phi4_reasoning",
            category="llm",
            daily_limit=10000,
            monthly_limit=300000,
            rate_limit_per_minute=60,
            cost_per_call=0.001,
            env_vars=["PHI4_REASONING_ENDPOINT", "PHI4_REASONING_API_KEY"],
            is_configured=(
                self._is_env_set("PHI4_REASONING_ENDPOINT")
                and self._is_env_set("PHI4_REASONING_API_KEY")
            ),
            priority=8,
        ))

        self._register(ProviderConfig(
            name="deepseek",
            category="llm",
            daily_limit=10000,
            monthly_limit=300000,
            rate_limit_per_minute=60,
            cost_per_call=0.001,
            env_vars=["DEEPSEEK_ENDPOINT", "DEEPSEEK_API_KEY"],
            is_configured=(
                self._is_env_set("DEEPSEEK_ENDPOINT")
                and self._is_env_set("DEEPSEEK_API_KEY")
            ),
            priority=10,
        ))

        self._register(ProviderConfig(
            name="gpt4o_mini",
            category="llm",
            daily_limit=10000,
            monthly_limit=300000,
            rate_limit_per_minute=100,
            cost_per_call=0.0005,
            env_vars=["AZURE_GPT4O_MINI_ENDPOINT", "AZURE_GPT4O_MINI_API_KEY"],
            is_configured=(
                self._is_env_set("AZURE_GPT4O_MINI_ENDPOINT")
                and self._is_env_set("AZURE_GPT4O_MINI_API_KEY")
            ),
            priority=12,
        ))

        self._register(ProviderConfig(
            name="mistral",
            category="llm",
            daily_limit=10000,
            monthly_limit=300000,
            rate_limit_per_minute=60,
            cost_per_call=0.001,
            env_vars=["MISTRAL_ENDPOINT", "MISTRAL_API_KEY"],
            is_configured=(
                self._is_env_set("MISTRAL_ENDPOINT")
                and self._is_env_set("MISTRAL_API_KEY")
            ),
            priority=15,
        ))

        self._register(ProviderConfig(
            name="groq",
            category="llm",
            daily_limit=50000,
            monthly_limit=1500000,
            rate_limit_per_minute=30,  # per key
            cost_per_call=0.0,
            env_vars=["GROQ_API_KEY_0"],
            is_configured=bool(s.groq_keys),
            priority=18,
        ))

        self._register(ProviderConfig(
            name="cf_glm",
            category="llm",
            daily_limit=50000,
            monthly_limit=1500000,
            rate_limit_per_minute=120,
            cost_per_call=0.0,
            env_vars=["CF_WORKER_GLM_URL"],
            is_configured=self._is_env_set("CF_WORKER_GLM_URL"),
            priority=25,
        ))

        self._register(ProviderConfig(
            name="cf_qwen",
            category="llm",
            daily_limit=50000,
            monthly_limit=1500000,
            rate_limit_per_minute=120,
            cost_per_call=0.0,
            env_vars=["CF_WORKER_QWEN_URL"],
            is_configured=self._is_env_set("CF_WORKER_QWEN_URL"),
            priority=25,
        ))

        self._register(ProviderConfig(
            name="cf_gemma",
            category="llm",
            daily_limit=50000,
            monthly_limit=1500000,
            rate_limit_per_minute=120,
            cost_per_call=0.0,
            env_vars=["CF_WORKER_GEMMA_URL"],
            is_configured=self._is_env_set("CF_WORKER_GEMMA_URL"),
            priority=25,
        ))

        self._register(ProviderConfig(
            name="openrouter",
            category="llm",
            daily_limit=10000,
            monthly_limit=300000,
            rate_limit_per_minute=30,
            cost_per_call=0.0,
            env_vars=["OPENROUTE_SERVICE_API_KEY"],
            is_configured=self._is_env_set("OPENROUTE_SERVICE_API_KEY"),
            priority=50,
        ))

        self._register(ProviderConfig(
            name="huggingface",
            category="llm",
            daily_limit=100000,
            monthly_limit=3000000,
            rate_limit_per_minute=300,
            cost_per_call=0.0,
            env_vars=["HUGGINGFACE_API_TOKEN"],
            is_configured=self._is_env_set("HUGGINGFACE_API_TOKEN"),
            priority=30,
        ))

        # ── Image generation ────────────────────────────────────

        self._register(ProviderConfig(
            name="azure_flux",
            category="llm",
            daily_limit=500,
            monthly_limit=15000,
            rate_limit_per_minute=10,
            cost_per_call=0.01,
            env_vars=["AZURE_FLUX_ENDPOINT", "AZURE_FLUX_API_KEY"],
            is_configured=(
                self._is_env_set("AZURE_FLUX_ENDPOINT")
                and self._is_env_set("AZURE_FLUX_API_KEY")
            ),
            priority=5,
        ))

        self._register(ProviderConfig(
            name="cf_phoenix",
            category="llm",
            daily_limit=50000,
            monthly_limit=1500000,
            rate_limit_per_minute=60,
            cost_per_call=0.0,
            env_vars=["CF_WORKER_PHOENIX_URL"],
            is_configured=self._is_env_set("CF_WORKER_PHOENIX_URL"),
            priority=15,
        ))

        self._register(ProviderConfig(
            name="cf_lucid",
            category="llm",
            daily_limit=50000,
            monthly_limit=1500000,
            rate_limit_per_minute=60,
            cost_per_call=0.0,
            env_vars=["CF_WORKER_LUCID_URL"],
            is_configured=self._is_env_set("CF_WORKER_LUCID_URL"),
            priority=20,
        ))

        configured_count = sum(1 for p in self._providers.values() if p.is_configured)
        logger.info(
            "ProviderRegistry initialised: %d/%d providers configured",
            configured_count,
            len(self._providers),
        )
