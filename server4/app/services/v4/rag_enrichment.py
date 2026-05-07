"""
Phase 7.5 (Day 15) — RAG enrichment via Tavily.

Goal: every numeric/factual claim that survives writer + hot-swap gets
a verifiable citation. We DO NOT fabricate data. If Tavily returns
nothing for a claim cluster, the slide stays without enrichment.

Public API
----------
    await enrich_compiled_slides(
        compiled_slides=[...],          # mutated in place
        emit=emit,                       # async callable, optional
        deck_title=...,                  # str, optional, used in queries
    ) -> dict   # {"n_enriched": int, "n_skipped": int, "duration_ms": int}

Wire shape (matches `SlideEnrichment` in
lliveupdatedstreaming/src/lib/sandboxProtocol.ts):
    {
      "sources": [
          {"url": str, "fetched_at": iso8601, "citation_label": str},
          ...
      ],
      "data_timestamp": iso8601,
      "refresh_hint": "static" | "rolling_30d" | "live"
    }

WS events emitted on the existing pipeline channel:
    - "slide_enriched"        per slide that got at least one source
    - "slide_enrichment_skipped" per slide with no citable claims
    - "rag_enrichment_complete" rollup at the end

Cost discipline (Tavily free tier = 1000 credits / month):
    * One Tavily query per slide max — no per-claim fanout.
    * Skip the slide entirely if zero citable claims are found.
    * Skip the whole pass if `TAVILY_API_KEY` is empty (graceful
      degradation; never raise).

Real-time invariant: never invent a source URL, never copy a snippet
into a claim it doesn't actually support.
"""

from __future__ import annotations

import re
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

EmitCallable = Callable[[str, dict[str, Any]], Awaitable[None]]

# ── Detection: which strings on a slide are citable claims ────────

# Regex catalogue — each one is a "this is a real-world fact, find me
# a source" signal. Anchored loosely so we tolerate writer variance.
_RE_PERCENT = re.compile(r"\b\d{1,3}(?:[.,]\d+)?\s*%")
_RE_MONEY = re.compile(
    r"(?i)(?:\$|usd|eur|€|£|gbp)\s*\d[\d.,]*\s*(?:thousand|million|billion|trillion|k|m|b|t)?\b"
)
_RE_BIG_NUMBER = re.compile(
    r"(?i)\b\d[\d.,]*\s*(?:thousand|million|billion|trillion|users?|customers?|companies|startups?|countries|years?)\b"
)
_RE_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_RE_CURRENT_HINT = re.compile(
    r"(?i)\b(?:current(?:ly)?|today|now|latest|live|real[-\s]?time|2024|2025|2026)\b"
)
_RE_ROLLING_HINT = re.compile(
    r"(?i)\b(?:last\s+(?:quarter|month|year)|past\s+\d+\s+(?:days|months|years)|recent(?:ly)?|trailing)\b"
)

_CITABLE_PATTERNS = (_RE_PERCENT, _RE_MONEY, _RE_BIG_NUMBER, _RE_YEAR)

# Visible-text keys per kit (mirrors the scorer & hot-swap modules).
_VISIBLE_KEYS: tuple[str, ...] = (
    "headline",
    "subheadline",
    "eyebrow",
    "body",
    "summary",
    "label",
    "caption",
    "description",
    "title",
    "value",
    "quote",
    "attribution",
)

_MAX_CLAIMS_PER_SLIDE = 5
_MAX_SOURCES_PER_SLIDE = 3
_TAVILY_TIMEOUT_S = 12.0


def _collect_claims(props: Mapping[str, Any]) -> list[str]:
    """Walk props and return the verbatim text of every visible field
    that contains at least one citable token. Order is depth-first
    visit order; preserves the same skip-keys as the scorer."""
    out: list[str] = []
    seen: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, str):
            text = node.strip()
            if not text or text in seen:
                return
            for pat in _CITABLE_PATTERNS:
                if pat.search(text):
                    seen.add(text)
                    out.append(text)
                    break
        elif isinstance(node, Mapping):
            for k, v in node.items():
                if isinstance(v, str):
                    if k in _VISIBLE_KEYS:
                        walk(v)
                else:
                    walk(v)
        elif isinstance(node, (list, tuple)):
            for item in node:
                walk(item)

    walk(props)
    return out[:_MAX_CLAIMS_PER_SLIDE]


def _build_query(headline: str, claims: Sequence[str], deck_title: str) -> str:
    """One short query per slide. Headline + the first claim gives
    Tavily enough context without exhausting the free tier."""
    parts: list[str] = []
    if deck_title:
        parts.append(deck_title.strip())
    if headline:
        parts.append(headline.strip())
    if claims:
        # Keep the first 2 claims so the query is anchored to real
        # numbers we want sources for.
        parts.extend(claims[:2])
    query = " ".join(p for p in parts if p)
    # Tavily caps queries around 400 chars; trim conservatively.
    return query[:380]


def _classify_refresh_hint(claims: Sequence[str]) -> str:
    # Plan 04 \u2014 single-source the "is this query about NOW?" check
    # via the recency module so any future tweak (new years, new
    # markers) flows through one regex.
    from app.services.v4.research import query_signals_now
    text = " ".join(claims)
    if query_signals_now(text):
        return "live"
    if _RE_ROLLING_HINT.search(text) or _RE_YEAR.search(text):
        return "rolling_30d"
    return "static"


def _domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def _citation_label(domain: str, claim_hint: str) -> str:
    """Short, human-readable label for the source.

    `domain` plus a tiny excerpt from the matched claim makes citations
    skimmable without leaking the entire snippet. We do NOT include the
    Tavily content blob — only what the source's own host announces.
    """
    excerpt = (claim_hint or "").strip()
    if len(excerpt) > 60:
        excerpt = excerpt[:57].rstrip() + "…"
    if not excerpt:
        return domain or "source"
    return f"{domain or 'source'} — {excerpt}"


async def _tavily_search(
    *, query: str, max_results: int = 5
) -> list[dict[str, Any]]:
    """Return raw Tavily result rows (`title`, `url`, `content`,
    `published_date`). Empty list on any failure."""
    api_key = getattr(settings, "TAVILY_API_KEY", None)
    if not api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=_TAVILY_TIMEOUT_S) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                    "include_answer": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            rows = data.get("results")
            if not isinstance(rows, list):
                return []
            return [r for r in rows if isinstance(r, dict) and r.get("url")]
    except Exception as e:  # noqa: BLE001
        logger.warning("v4_rag_tavily_failed", error=str(e), query=query[:80])
        return []


def _build_enrichment(
    *, claims: Sequence[str], rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any] | None:
    """Convert Tavily rows into the SlideEnrichment wire shape.

    Returns None if no rows resolve to a real URL — this is the
    no-fake-data invariant. We never invent a source.
    """
    sources: list[dict[str, str]] = []
    fetched_at = datetime.now(timezone.utc).isoformat()
    seen_urls: set[str] = set()

    for row in rows:
        url = (row.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        if not (url.startswith("http://") or url.startswith("https://")):
            continue
        seen_urls.add(url)
        domain = _domain_of(url)
        # Anchor the citation_label on the FIRST claim that originated
        # this query — never on the Tavily snippet, since we cannot
        # verify the snippet matches the claim.
        anchor = claims[0] if claims else ""
        sources.append({
            "url": url,
            "fetched_at": fetched_at,
            "citation_label": _citation_label(domain, anchor),
        })
        if len(sources) >= _MAX_SOURCES_PER_SLIDE:
            break

    if not sources:
        return None

    return {
        "sources": sources,
        "data_timestamp": fetched_at,
        "refresh_hint": _classify_refresh_hint(claims),
    }


# ── Public entry point ───────────────────────────────────────────


async def _safe_emit(
    emit: EmitCallable | None, stage: str, payload: dict[str, Any]
) -> None:
    if emit is None:
        return
    try:
        await emit(stage, payload)
    except Exception as e:  # noqa: BLE001
        logger.warning("v4_rag_emit_failed", stage=stage, error=str(e))


async def enrich_compiled_slides(
    *,
    compiled_slides: list[dict[str, Any]],
    emit: EmitCallable | None = None,
    deck_title: str = "",
) -> dict[str, int]:
    """Enrich every slide with verifiable Tavily sources for its
    numeric claims. Mutates `compiled_slides` in place; returns a
    rollup. Best-effort: never raises.
    """
    started = time.monotonic()
    n_enriched = 0
    n_skipped = 0
    n_no_claims = 0

    api_key = getattr(settings, "TAVILY_API_KEY", None)
    if not api_key:
        # Hard skip — emit a marker so the frontend knows enrichment
        # was disabled this run, never silently degrade.
        await _safe_emit(emit, "rag_enrichment_complete", {
            "n_enriched": 0,
            "n_skipped": len(compiled_slides),
            "n_no_claims": 0,
            "disabled": True,
            "duration_ms": 0,
        })
        return {"n_enriched": 0, "n_skipped": len(compiled_slides), "duration_ms": 0}

    for slide in compiled_slides:
        if not isinstance(slide, dict):
            n_skipped += 1
            continue
        artifacts = slide.get("artifacts") or {}
        kit_jsx = artifacts.get("kit_jsx") if isinstance(artifacts, Mapping) else None
        props = (
            kit_jsx.get("props_json")
            if isinstance(kit_jsx, Mapping)
            else None
        )
        if not isinstance(props, Mapping):
            n_skipped += 1
            continue

        slide_id = str(slide.get("slide_id") or "")
        headline = props.get("headline") if isinstance(props.get("headline"), str) else ""

        claims = _collect_claims(props)
        if not claims:
            n_no_claims += 1
            await _safe_emit(emit, "slide_enrichment_skipped", {
                "slide_id": slide_id,
                "reason": "no_citable_claims",
            })
            continue

        query = _build_query(headline or "", claims, deck_title)
        if not query.strip():
            n_skipped += 1
            await _safe_emit(emit, "slide_enrichment_skipped", {
                "slide_id": slide_id,
                "reason": "empty_query",
            })
            continue

        rows = await _tavily_search(query=query, max_results=5)
        enrichment = _build_enrichment(claims=claims, rows=rows)
        if enrichment is None:
            n_skipped += 1
            await _safe_emit(emit, "slide_enrichment_skipped", {
                "slide_id": slide_id,
                "reason": "no_sources_returned",
            })
            continue

        slide["enrichment"] = enrichment
        n_enriched += 1
        await _safe_emit(emit, "slide_enriched", {
            "slide_id": slide_id,
            "n_sources": len(enrichment["sources"]),
            "refresh_hint": enrichment["refresh_hint"],
        })

    duration_ms = int((time.monotonic() - started) * 1000)
    await _safe_emit(emit, "rag_enrichment_complete", {
        "n_enriched": n_enriched,
        "n_skipped": n_skipped,
        "n_no_claims": n_no_claims,
        "disabled": False,
        "duration_ms": duration_ms,
    })
    return {
        "n_enriched": n_enriched,
        "n_skipped": n_skipped,
        "n_no_claims": n_no_claims,
        "duration_ms": duration_ms,
    }


# Re-export internals for tests that need direct unit coverage.
__all__ = [
    "enrich_compiled_slides",
    "_collect_claims",
    "_build_query",
    "_classify_refresh_hint",
    "_build_enrichment",
    "_tavily_search",
]
