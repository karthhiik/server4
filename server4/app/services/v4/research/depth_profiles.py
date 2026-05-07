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
        news_providers=("newsapi",),
        max_results_per_provider=5,
        per_provider_timeout_s=4.0,
        enable_social=False,
        enable_financial=False,
        enable_followup_loop=False,
    ),
    # "standard" is what every non-premium request uses. Strict
    # subset of "deep" — drops You.com / Jina / NewsData / Guardian /
    # social / financial / follow-up loop. 6s per provider.
    "standard": DepthProfile(
        label="standard",
        web_providers=("tavily", "serper", "exa"),
        news_providers=("newsapi",),
        max_results_per_provider=6,
        per_provider_timeout_s=6.0,
        enable_social=False,
        enable_financial=False,
        enable_followup_loop=False,
    ),
    # "deep" matches the previous behaviour — full provider suite,
    # follow-up expansion enabled, generous 10s per provider.
    "deep": DepthProfile(
        label="deep",
        web_providers=("tavily", "serper", "exa", "you_com", "jina"),
        news_providers=("newsapi", "newsdata", "guardian"),
        max_results_per_provider=8,
        per_provider_timeout_s=10.0,
        enable_social=True,
        enable_financial=True,
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
