from __future__ import annotations

import pytest

from app.services.v4.regen_engine import (
    ElementRegenerationResult,
    RegenerationValidationError,
    _compile_ordered_deck,
    _slide_doc_to_generated,
    normalize_slide_indices,
    regenerate_one_field,
)


def _slide_doc(index: int, headline: str) -> dict:
    return {
        "_id": f"slide-{index}",
        "project_id": "project-1",
        "index": index,
        "intent": "title" if index == 0 else "problem",
        "layout": "title-only" if index == 0 else "two-column",
        "headline": headline,
        "subheadline": "A precise thesis line",
        "bullets": ["Evidence-led point", "Second point"],
        "body": "",
        "stat_blocks": [],
        "citations": [],
        "version": 1,
    }


def test_normalize_slide_indices_dedupes_and_preserves_order() -> None:
    assert normalize_slide_indices([2, 1, 2, 0]) == [2, 1, 0]


def test_normalize_slide_indices_rejects_negative_values() -> None:
    with pytest.raises(RegenerationValidationError):
        normalize_slide_indices([0, -1])


def test_slide_doc_to_generated_preserves_existing_image_fields() -> None:
    doc = _slide_doc(0, "Opening")
    doc.update({
        "image_url": "/api/v4/assets/generated/hero.webp",
        "image_source": "flux",
        "image_position": "background",
        "image_intent": "hero",
    })

    slide = _slide_doc_to_generated(doc)

    assert slide.image_url == "/api/v4/assets/generated/hero.webp"
    assert slide.image_source == "flux"
    assert slide.image_position == "background"
    assert slide.image_intent == "hero"


def test_compile_ordered_deck_refreshes_full_artifact_set() -> None:
    docs = [
        _slide_doc(0, "Original opening"),
        _slide_doc(1, "Regenerated problem"),
    ]
    project = {
        "_id": "project-1",
        "title": "Investor Deck",
        "purpose": "investor_pitch",
        "industry": "AI productivity",
    }

    compiled, design_tokens, design_system = _compile_ordered_deck(slide_docs=docs, project=project)

    assert len(compiled) == 2
    assert design_tokens["palette"]
    assert design_system["version"]
    assert all(slide["design_system_version"] == design_system["version"] for slide in compiled)
    assert all("quality_score" in slide for slide in compiled)
    assert compiled[1]["artifacts"]["kit_jsx"]["props_json"]["headline"] == "Regenerated problem"


@pytest.mark.asyncio
async def test_regenerate_one_field_refuses_image_urls_without_pipeline() -> None:
    result = await regenerate_one_field(
        project_id="project-1",
        project={"_id": "project-1", "title": "Investor Deck"},
        slide_doc=_slide_doc(0, "Opening"),
        compiled_props={"headline": "Opening", "imageUrl": "/api/v4/images/project-1/slide.png"},
        path="imageUrl",
        instruction="make a new hero image",
        kind="image",
    )

    assert isinstance(result, ElementRegenerationResult)
    assert result.ok is False
    assert "image" in (result.reason or "")


@pytest.mark.asyncio
async def test_regenerate_one_field_uses_router_and_preserves_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        content = '{"ok": true, "value": "Sharper opening"}'

    class FakeRouter:
        async def complete(self, task_type, messages, **kwargs):
            assert task_type.value == "style_adaptation"
            assert "Selected path: headline" in messages[1]["content"]
            return FakeResponse()

    monkeypatch.setattr("app.services.v4.regen_engine.get_model_router", lambda: FakeRouter())

    result = await regenerate_one_field(
        project_id="project-1",
        project={"_id": "project-1", "title": "Investor Deck", "mode": "standard"},
        slide_doc=_slide_doc(0, "Opening"),
        compiled_props={"headline": "Opening", "subheadline": "A precise thesis line"},
        path="headline",
        instruction="make it sharper",
        kind="text",
    )

    assert result.ok is True
    assert result.value == "Sharper opening"
    assert result.changed is True


@pytest.mark.asyncio
async def test_regenerate_one_field_rejects_shape_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        content = '{"ok": true, "value": {"headline": "Wrong shape"}}'

    class FakeRouter:
        async def complete(self, task_type, messages, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.services.v4.regen_engine.get_model_router", lambda: FakeRouter())

    with pytest.raises(RegenerationValidationError):
        await regenerate_one_field(
            project_id="project-1",
            project={"_id": "project-1", "title": "Investor Deck", "mode": "standard"},
            slide_doc=_slide_doc(0, "Opening"),
            compiled_props={"headline": "Opening"},
            path="headline",
            instruction="make it sharper",
            kind="text",
        )