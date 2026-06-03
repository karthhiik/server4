"""V4 research depth profiles.

Replaces the magic-string ``research_depth`` used by
``ResearchCollector.collect`` with a typed contract.

A profile is the *budget* for one research stage. It says which
providers may be called, how many results to ask for, how long each
provider may take, and which expensive optional layers (social,
financial, deep-research follow-up loop) are enabled.

Constants are tuned against the actual providers wired in
``server4/.env`` (see Plan 04 §1.1). Provider names match the
coroutine method names on ``ResearchCollector`` minus the leading
underscore so the collector can dispatch by string.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class DepthProfile:
    """Typed budget for one research stage.

    Frozen dataclass — instances live in a module-level dict and are
    safe to share across coroutines.
    """

    label: str
    web_providers: Tuple[str, ...]
    news_providers: Tuple[str, ...]
    max_results_per_provider: int
    per_provider_timeout_s: float
    enable_social: bool
    enable_financial: bool
    enable_followup_loop: bool


# Provider strings must match coroutine names on ``ResearchCollector``.
# Web providers: tavily, serper, exa, you_com, jina.
# News providers: newsapi, newsdata, guardian.

DEPTH_PROFILES: dict[str, DepthProfile] = {
    # "fast" is the budget the deep-research expansion loop uses for
    # follow-up queries. Two web providers, NewsAPI only, very tight
    # timeout. Calibrated so a 4-way fan-out completes within ~5s
    # wall clock.
    "fast": DepthProfile(
        label="fast",
        web_providers=("tavily", "serper"),
        news_providers=(),
        max_results_per_provider=5,
        per_provider_timeout_s=4.0,
        enable_social=False,
        enable_financial=False,
        enable_followup_loop=False,
    ),
    # "standard" is what every non-premium request uses. Strict
    # subset of "deep" — drops You.com / Jina / NewsData / Guardian /
    # social / financial / follow-up loop. 6s per provider.
    # Current free-tier path: Tavily + Serper + Linkup + SearchAPI as
    # AI-search fallbacks. Linkup and SearchAPI sit AFTER the proven
    # Tavily/Serper pair so they only fire when those return sparse
    # data — but the parallel fan-out means a healthy day still hits
    # all four for richer evidence. ScrapingBog/ScrapingBee/Apify are
    # content-extraction providers, not search engines, so they don't
    # appear here.
    "standard": DepthProfile(
        label="standard",
        web_providers=("tavily", "serper", "linkup", "searchapi"),
        news_providers=("newsdata",),
        max_results_per_provider=6,
        per_provider_timeout_s=6.0,
        enable_social=False,
        enable_financial=False,
        enable_followup_loop=False,
    ),
    # "deep" matches the previous behaviour — full provider suite,
    # follow-up expansion enabled, generous 10s per provider.
    # Premium keeps optional providers in the chain; key-pool guards skip
    # providers that are not configured in the local .env.
    # 2026-05-25: extended with Linkup, SearchAPI, Zenserp, ValueSerp
    # for richer SERP coverage. The fan-out is parallel so adding
    # providers raises evidence breadth without adding wall-clock time.
    "deep": DepthProfile(
        label="deep",
        web_providers=(
            "tavily", "serper", "you_com", "jina", "exa",
            "linkup", "searchapi", "zenserp", "valueserp",
        ),
        news_providers=("newsdata", "newsapi", "guardian"),
        max_results_per_provider=8,
        per_provider_timeout_s=10.0,
        enable_social=False,
        enable_financial=False,
        # Deep profile is the only tier that runs the gap-driven
        # follow-up loop. Fast and standard return the seed packet
        # as-is to keep their wall-clock budgets honest.
        enable_followup_loop=True,
    ),
}


def derive_profile_label(
    *,
    mode: str,
    research_depth: str | None = None,
) -> str:
    """Map legacy (mode, research_depth) pairs to a profile label.

    Used during the deprecation overlap where some callers still pass
    ``research_depth="standard"`` etc. New callers should pass a
    ``DepthProfile`` directly via ``profile_for(mode)``.
    """

    if research_depth in DEPTH_PROFILES:
        return research_depth
    if mode == "premium":
        return "deep"
    return "standard"


def profile_for(mode: str, research_depth: str | None = None) -> DepthProfile:
    """Resolve the canonical ``DepthProfile`` for this request."""

    label = derive_profile_label(mode=mode, research_depth=research_depth)
    return DEPTH_PROFILES[label]
