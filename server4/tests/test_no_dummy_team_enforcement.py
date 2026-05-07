from __future__ import annotations

import asyncio

import pytest

from app.services.v4 import content_pipeline
from app.services.v4 import team_resolver
from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.research_collector import ResearchPacket
from app.services.v4.slide_compiler import compile_slide


def test_placeholder_team_factory_is_not_available() -> None:
    assert not hasattr(team_resolver, "default_team_members")


def test_unresolved_team_compiles_without_fake_members() -> None:
    slide = GeneratedSlide(
        index=8,
        intent="team",
        layout="team-grid",
        headline="Team",
        subheadline="Verified team details are pending",
        team_members=[],
        requires_user_input=True,
        user_input_kind="team_members",
        user_input_reason="team_members_unresolved",
    )

    compiled = compile_slide(slide=slide)
    props = compiled["artifacts"]["kit_jsx"]["props_json"]

    assert compiled["kit_component"] == "TeamGrid"
    assert props["members"] == []
    assert props["requiresUserInput"] is True
    assert props["userInputKind"] == "team_members"
    assert "TBD" not in compiled["jsx_source"]
    assert "Founder & CEO" not in compiled["jsx_source"]


def _empty_research() -> ResearchPacket:
    return ResearchPacket(
        query="investor deck",
        industry=None,
        company_name=None,
        citations=[],
        news_citations=[],
        financial_data={},
        social_signals={},
        duration_ms=0,
    )


@pytest.mark.asyncio
async def test_team_resolution_timeout_returns_empty_without_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    async def slow_resolve_team(**kwargs):  # type: ignore[no-untyped-def]
        await asyncio.sleep(0.05)
        return []

    monkeypatch.setattr(team_resolver, "resolve_team", slow_resolve_team)
    monkeypatch.setattr(content_pipeline, "TEAM_RESOLUTION_TIMEOUT_S", 0.001)

    events: list[tuple[str, dict]] = []

    async def emit(stage: str, payload: dict) -> None:
        events.append((stage, payload))

    members = await content_pipeline._resolve_team_members_with_budget(
        company=None,
        company_url=None,
        research=_empty_research(),
        preflight_team_seeds=[],
        user_answer=None,
        mode="standard",
        project_id="project-1",
        emit=emit,
    )

    assert members == []
    assert any(
        stage == "stage_info" and payload.get("reason") == "team_resolution_timeout"
        for stage, payload in events
    )


def test_mark_team_slide_unresolved_sets_required_fields() -> None:
    slide = GeneratedSlide(
        index=4,
        intent="team",
        layout="team-grid",
        headline="Team",
        team_members=[{"name": "Unverified Entry", "role": "Unverified Role"}],
    )

    content_pipeline._mark_team_slide_unresolved(slide)

    assert slide.team_members == []
    assert slide.requires_user_input is True
    assert slide.user_input_kind == "team_members"
    assert slide.user_input_reason == "team_members_unresolved"
