"""Phase 7.5 — RAG enrichment unit tests.

We never hit the real Tavily API. `_tavily_search` is replaced with a
deterministic fake at the module level, so we can verify:
    * Citable claim detection picks real numeric/factual signals.
    * No-fake-data invariant: empty Tavily result → no enrichment.
    * Queries are bounded and never empty.
    * `refresh_hint` classification is correct for live/rolling/static.
    * The pipeline-facing `enrich_compiled_slides` mutates slides in
      place, emits the right events, and skips slides without claims.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.services.v4 import rag_enrichment as rag


def _make_slide(slide_id: str, props: dict[str, Any]) -> dict[str, Any]:
    return {
        "slide_id": slide_id,
        "slide_index": 0,
        "artifacts": {
            "kit_jsx": {
                "kit_component": "StatHero",
                "props_json": props,
                "source": "//",
                "fingerprint": f"fp-{slide_id}",
            },
            "html_css_js": None,
            "engine": None,
            "reveal_legacy": None,
        },
    }


class _Recorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, stage: str, payload: dict[str, Any]) -> None:
        self.events.append((stage, payload))

    def stages(self) -> list[str]:
        return [s for s, _ in self.events]


# ── Claim detection ──────────────────────────────────────────────


def test_collect_claims_picks_percentages_and_money():
    props = {
        "headline": "We grew 87% YoY",
        "stats": [
            {"value": "$2.4B", "label": "TAM"},
            {"value": "120k", "label": "users"},
            {"value": "fast", "label": "speed"},  # no number → ignored
        ],
        "body": "Founded in 2018, we serve 50 countries.",
    }
    claims = rag._collect_claims(props)
    text = " ".join(claims)
    assert "87%" in text
    assert "$2.4B" in text
    assert "2018" in text
    assert "50 countries" in text


def test_collect_claims_returns_empty_for_pure_text():
    props = {
        "headline": "Welcome",
        "subheadline": "Glad you're here",
        "body": "We help teams ship faster.",
    }
    assert rag._collect_claims(props) == []


def test_collect_claims_caps_at_max():
    props = {
        "stats": [
            {"value": f"{i}%", "label": f"L{i}"} for i in range(20)
        ],
    }
    claims = rag._collect_claims(props)
    assert len(claims) <= rag._MAX_CLAIMS_PER_SLIDE


# ── Refresh hint ─────────────────────────────────────────────────


def test_refresh_hint_live():
    assert rag._classify_refresh_hint(["currently $2B in revenue"]) == "live"


def test_refresh_hint_rolling():
    assert rag._classify_refresh_hint(["last quarter we grew 12%"]) == "rolling_30d"
    # A historical year (not in the "current" set) → rolling_30d.
    assert rag._classify_refresh_hint(["2018 market size $5B"]) == "rolling_30d"


def test_refresh_hint_static():
    assert rag._classify_refresh_hint(["100 employees"]) == "static"


# ── Query building ────────────────────────────────────────────────


def test_build_query_includes_headline_and_first_claims():
    q = rag._build_query("Market size", ["$2.4B TAM", "20% CAGR"], "FinTech 2025")
    assert "FinTech 2025" in q
    assert "Market size" in q
    assert "$2.4B" in q
    assert len(q) <= 380


# ── Enrichment construction ───────────────────────────────────────


def test_build_enrichment_returns_none_on_empty_rows():
    out = rag._build_enrichment(claims=["87%"], rows=[])
    assert out is None


def test_build_enrichment_drops_non_http_urls_and_dedupes():
    rows = [
        {"url": "https://example.com/a"},
        {"url": "https://example.com/a"},  # dup
        {"url": "ftp://nope.example.com"},  # bad scheme
        {"url": ""},                        # empty
        {"url": "https://example.org/b"},
    ]
    out = rag._build_enrichment(claims=["87% growth"], rows=rows)
    assert out is not None
    urls = [s["url"] for s in out["sources"]]
    assert urls == ["https://example.com/a", "https://example.org/b"]
    # Citation labels should NOT contain Tavily snippets, only domain + claim hint.
    for s in out["sources"]:
        assert "87%" in s["citation_label"]


def test_build_enrichment_caps_at_max_sources():
    rows = [{"url": f"https://example{i}.com/p"} for i in range(10)]
    out = rag._build_enrichment(claims=["50 countries"], rows=rows)
    assert out is not None
    assert len(out["sources"]) == rag._MAX_SOURCES_PER_SLIDE


# ── Pipeline-facing function ──────────────────────────────────────


def _patch_tavily(monkeypatch: pytest.MonkeyPatch, rows: list[dict[str, Any]]) -> None:
    async def fake(*, query: str, max_results: int = 5):
        return rows
    monkeypatch.setattr(rag, "_tavily_search", fake)
    # Force the API-key gate to "configured" without touching real settings.
    monkeypatch.setattr(rag.settings, "TAVILY_API_KEY", "test-key")


def test_enrich_compiled_slides_attaches_enrichment(monkeypatch):
    _patch_tavily(monkeypatch, [
        {"url": "https://nasdaq.com/article", "title": "x", "content": "y"},
        {"url": "https://crunchbase.com/foo", "title": "x", "content": "y"},
    ])
    slides = [
        _make_slide("s1", {
            "headline": "Market is $2.4B",
            "stats": [{"value": "$2.4B", "label": "TAM"}],
        }),
    ]
    rec = _Recorder()
    out = asyncio.run(rag.enrich_compiled_slides(
        compiled_slides=slides, emit=rec, deck_title="Deck"
    ))
    assert out["n_enriched"] == 1
    assert slides[0]["enrichment"]["sources"][0]["url"].startswith("https://nasdaq.com")
    assert "slide_enriched" in rec.stages()
    assert "rag_enrichment_complete" in rec.stages()


def test_enrich_skips_slides_with_no_claims(monkeypatch):
    _patch_tavily(monkeypatch, [
        {"url": "https://example.com/should-not-be-used"},
    ])
    slides = [
        _make_slide("s1", {"headline": "Welcome", "body": "Glad you're here"}),
    ]
    rec = _Recorder()
    out = asyncio.run(rag.enrich_compiled_slides(
        compiled_slides=slides, emit=rec
    ))
    assert out["n_enriched"] == 0
    assert "enrichment" not in slides[0]
    assert "slide_enrichment_skipped" in rec.stages()


def test_enrich_no_fake_sources_when_tavily_returns_empty(monkeypatch):
    _patch_tavily(monkeypatch, [])
    slides = [
        _make_slide("s1", {
            "headline": "We have $50M ARR",
            "stats": [{"value": "$50M", "label": "ARR"}],
        }),
    ]
    rec = _Recorder()
    out = asyncio.run(rag.enrich_compiled_slides(
        compiled_slides=slides, emit=rec
    ))
    assert out["n_enriched"] == 0
    assert "enrichment" not in slides[0]
    skipped = [p for s, p in rec.events if s == "slide_enrichment_skipped"]
    assert len(skipped) == 1
    assert skipped[0]["reason"] == "no_sources_returned"


def test_enrich_disabled_when_no_api_key(monkeypatch):
    # Force the empty-key path explicitly.
    monkeypatch.setattr(rag.settings, "TAVILY_API_KEY", "")
    slides = [
        _make_slide("s1", {"headline": "$2B market"}),
        _make_slide("s2", {"headline": "10% growth"}),
    ]
    rec = _Recorder()
    out = asyncio.run(rag.enrich_compiled_slides(
        compiled_slides=slides, emit=rec
    ))
    assert out["n_enriched"] == 0
    assert all("enrichment" not in s for s in slides)
    complete = [p for st, p in rec.events if st == "rag_enrichment_complete"]
    assert complete and complete[0]["disabled"] is True


def test_enrich_emit_failure_does_not_crash(monkeypatch):
    _patch_tavily(monkeypatch, [{"url": "https://x.com/a"}])

    async def bad_emit(*_args, **_kwargs):
        raise RuntimeError("ws closed")

    slides = [
        _make_slide("s1", {"headline": "$2B market"}),
    ]
    # Must not raise.
    out = asyncio.run(rag.enrich_compiled_slides(
        compiled_slides=slides, emit=bad_emit
    ))
    # And must still attach enrichment despite the emit failures.
    assert out["n_enriched"] == 1
    assert slides[0]["enrichment"]["sources"][0]["url"] == "https://x.com/a"
