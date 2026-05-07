from __future__ import annotations

import json

import pytest

from app.services.llm.model_router import TaskType
from app.services.v4.parallel_writer import ParallelWriter
from app.services.v4.research_collector import ResearchPacket
from app.services.v4.schema_guard import SchemaValidationError, validate_planner_slides, validate_writer_output
from app.services.v4.skeleton_planner import SlideSkeleton


class _Response:
    def __init__(self, content: str) -> None:
        self.content = content
        self.tokens_used = 0


def _packet() -> ResearchPacket:
    return ResearchPacket(
        query="Acme investor pitch",
        industry=None,
        company_name="Acme",
        citations=[],
        news_citations=[],
        financial_data={},
        social_signals={},
        duration_ms=0,
    )


def test_writer_schema_rejects_empty_content() -> None:
    with pytest.raises(SchemaValidationError):
        validate_writer_output('{"headline":"Team"}', slide_index=3)


def test_planner_schema_rejects_non_object_slide() -> None:
    with pytest.raises(SchemaValidationError):
        validate_planner_slides(["bad"], project_id="project-1")


@pytest.mark.asyncio
async def test_writer_schema_invalid_retries_fallback_task(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[TaskType] = []

    async def fake_safe_complete(**kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs["primary_task"])
        if len(calls) == 1:
            return _Response('{"headline":""}')
        return _Response(json.dumps({
            "headline": "Acme Shortens Close Cycles",
            "subheadline": "Finance teams move from approvals to action faster",
            "body": "Acme gives finance teams a concrete workflow for faster invoice approvals without inventing traction data.",
            "speaker_notes": "Use this slide to explain the core workflow and why it matters.",
            "citations": [],
        }))

    monkeypatch.setattr("app.services.v4.parallel_writer.safe_complete", fake_safe_complete)

    writer = ParallelWriter.__new__(ParallelWriter)
    writer.router = object()
    slide = SlideSkeleton(
        index=0,
        intent="solution",
        purpose="Explain the solution without fake traction.",
        headline_target="Solution",
        key_points=["Automates invoice approval routing"],
        layout_hint="two-column",
    )

    result = await writer.write_one(
        slide,
        _packet(),
        mode="standard",
        project_id="project-1",
        pre_scoped=[],
        purpose="investor_pitch",
    )

    assert calls == [TaskType.TEMPLATE_FILL, TaskType.NARRATIVE_STORYTELLING]
    assert result.headline == "Acme Shortens Close Cycles"
    assert result.raw["headline"] == "Acme Shortens Close Cycles"
