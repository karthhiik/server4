"""Tests verifying each provider correctly translates ``RecencyWindow``
into its native API parameter.

We don't hit real APIs; instead we monkeypatch ``ResearchCollector._http``
to return a stub httpx client that captures the outgoing request body
or query params, and stub ``get_pool`` so providers don't need real
keys. This lets us assert the exact wire format Plan 04 mandates.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
import pytest

from app.services.v4 import provider_health
from app.services.v4.research import RecencyWindow, profile_for
from app.services.v4 import research_collector as rc_mod
from app.services.v4.research_collector import ResearchCollector


class _StubPool:
    empty = False

    async def acquire(self) -> str:
        return "fake-key"

    async def report_success(self, key: str) -> None:
        return None

    async def report_failure(self, key: str, status: int | None = None) -> None:
        return None

    def telemetry(self) -> dict[str, Any]:
        return {"keys": []}


@pytest.fixture
def recency() -> RecencyWindow:
    today = date.today()
    return RecencyWindow(
        earliest=today - timedelta(days=180),
        boost_after=today - timedelta(days=60),
        label="last_180d",
        decay_half_life_days=120,
    )


def _stub_client(captured: dict[str, Any]) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["params"] = dict(request.url.params)
        captured["headers"] = dict(request.headers)
        if request.content:
            try:
                import json as _json
                captured["json"] = _json.loads(request.content)
            except Exception:
                captured["body"] = request.content.decode("utf-8", errors="ignore")
        if "tavily" in str(request.url):
            return httpx.Response(200, json={"results": []})
        if "serper" in str(request.url):
            return httpx.Response(200, json={"organic": []})
        if "exa.ai" in str(request.url):
            return httpx.Response(200, json={"results": []})
        if "newsapi" in str(request.url):
            return httpx.Response(200, json={"articles": []})
        if "newsdata" in str(request.url):
            return httpx.Response(200, json={"results": []})
        if "guardianapis" in str(request.url):
            return httpx.Response(200, json={"response": {"results": []}})
        if "ydc-index" in str(request.url):
            return httpx.Response(200, json={"hits": []})
        if "s.jina.ai" in str(request.url):
            return httpx.Response(200, json={"data": []})
        return httpx.Response(200, json={})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def collector(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, Any] = {}
    client = _stub_client(captured)

    async def _http(self):
        return client

    monkeypatch.setattr(ResearchCollector, "_http", _http)
    monkeypatch.setattr(rc_mod, "get_pool", lambda *_a, **_kw: _StubPool())
    monkeypatch.setattr(provider_health, "is_healthy", lambda *_a, **_kw: True)
    monkeypatch.setattr(provider_health, "record", lambda *_a, **_kw: None)
    monkeypatch.setattr(provider_health, "mute", lambda *_a, **_kw: None)
    return ResearchCollector(), captured


class TestTavilyTranslation:
    @pytest.mark.asyncio
    async def test_days_param_set_from_recency(self, collector, recency, monkeypatch):
        rc, captured = collector
        from app.config import settings
        monkeypatch.setattr(settings, "TAVILY_API_KEY", "fake")
        await rc._tavily("ai market", recency=recency, profile=profile_for("standard"))
        assert captured["json"]["max_results"] == profile_for("standard").max_results_per_provider
        assert captured["json"]["days"] == 180
        assert captured["json"]["topic"] == "general"

    @pytest.mark.asyncio
    async def test_days_capped_at_365(self, collector, monkeypatch):
        rc, captured = collector
        from app.config import settings
        monkeypatch.setattr(settings, "TAVILY_API_KEY", "fake")
        today = date.today()
        big = RecencyWindow(
            earliest=today - timedelta(days=365 * 3),
            boost_after=today - timedelta(days=180),
            label="last_3y",
            decay_half_life_days=730,
        )
        await rc._tavily("x", recency=big, profile=profile_for("premium"))
        assert captured["json"]["days"] == 365


class TestSerperTbsBuckets:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "days,expected_tbs",
        [(7, "qdr:w"), (30, "qdr:m"), (180, "qdr:y"), (365, "qdr:y")],
    )
    async def test_tbs_bucketing(self, collector, days, expected_tbs):
        rc, captured = collector
        today = date.today()
        w = RecencyWindow(
            earliest=today - timedelta(days=days),
            boost_after=today - timedelta(days=max(1, days // 3)),
            label=f"last_{days}d",
            decay_half_life_days=days,
        )
        await rc._serper("x", recency=w, profile=profile_for("standard"))
        assert captured["json"]["num"] == profile_for("standard").max_results_per_provider
        assert captured["json"]["tbs"] == expected_tbs


class TestExaStartPublishedDate:
    @pytest.mark.asyncio
    async def test_iso_utc_date(self, collector, recency):
        rc, captured = collector
        await rc._exa("x", recency=recency, profile=profile_for("premium"))
        body = captured["json"]
        assert body["numResults"] == profile_for("premium").max_results_per_provider
        assert "startPublishedDate" in body
        val = body["startPublishedDate"]
        assert val.startswith(recency.earliest.isoformat())
        assert "00:00" in val


class TestNewsApiFromDate:
    @pytest.mark.asyncio
    async def test_from_uses_recency_earliest(self, collector, recency, monkeypatch):
        rc, captured = collector
        from app.config import settings
        monkeypatch.setattr(settings, "NEWSAPI_KEY", "fake")
        await rc._newsapi("x", recency=recency, profile=profile_for("standard"))
        assert captured["params"]["pageSize"] == str(profile_for("standard").max_results_per_provider)
        assert captured["params"]["from"] == recency.earliest.strftime("%Y-%m-%d")


class TestNewsdataAndGuardian:
    @pytest.mark.asyncio
    async def test_newsdata_from_date(self, collector, recency, monkeypatch):
        rc, captured = collector
        from app.config import settings
        monkeypatch.setattr(settings, "NEWSDATA_API_KEY", "fake")
        await rc._newsdata("x", recency=recency, profile=profile_for("premium"))
        assert captured["params"]["from_date"] == recency.earliest.strftime("%Y-%m-%d")

    @pytest.mark.asyncio
    async def test_guardian_from_date(self, collector, recency, monkeypatch):
        rc, captured = collector
        from app.config import settings
        monkeypatch.setattr(settings, "GUARDIAN_API_KEY", "fake")
        await rc._guardian("x", recency=recency, profile=profile_for("premium"))
        assert captured["params"]["page-size"] == str(profile_for("premium").max_results_per_provider)
        assert captured["params"]["from-date"] == recency.earliest.strftime("%Y-%m-%d")


class TestYouAndJinaAreUnchanged:
    @pytest.mark.asyncio
    async def test_you_com_no_recency_param(self, collector):
        rc, captured = collector
        await rc._you_com("x", profile=profile_for("premium"))
        assert captured["params"]["num_web_results"] == str(profile_for("premium").max_results_per_provider)
        assert all(
            k not in captured["params"]
            for k in ("from", "from_date", "from-date", "startPublishedDate", "days")
        )

    @pytest.mark.asyncio
    async def test_jina_no_recency_param(self, collector):
        rc, captured = collector
        await rc._jina_reader_search("x", profile=profile_for("premium"))
        assert all(
            k not in captured["params"]
            for k in ("from", "from_date", "from-date", "startPublishedDate", "days")
        )
