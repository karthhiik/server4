"""Plan 05 regression tests for the standard-mode speed budget."""

from __future__ import annotations

from app.services.llm.model_router import ModelRouter, ROUTING_TABLE, TaskType
from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.research_collector import ResearchPacket
from app.services.v4.skeleton_planner import SkeletonPlanner
from app.services.v4.slide_compiler import compile_slide


def _empty_packet() -> ResearchPacket:
    return ResearchPacket(
        query="AI onboarding training deck",
        industry=None,
        company_name=None,
        citations=[],
        news_citations=[],
        financial_data={},
        social_signals={},
        duration_ms=0,
    )


def test_standard_mode_narrative_chain_uses_fast_configured_models() -> None:
    standard_chain = ModelRouter._chain_for(
        TaskType.NARRATIVE_STORYTELLING,
        mode="standard",
    )

    assert standard_chain[:3] == ["groq", "gpt-4o-mini", "cf-qwen"]
    assert "openrouter" in standard_chain
    assert "kimi-k2-thinking" not in standard_chain[:4]
    assert "deepseek-v3" not in standard_chain[:4]


def test_default_narrative_chain_remains_premium_quality() -> None:
    assert ModelRouter._chain_for(TaskType.NARRATIVE_STORYTELLING) == ROUTING_TABLE[
        TaskType.NARRATIVE_STORYTELLING
    ]
    assert ModelRouter._chain_for(TaskType.NARRATIVE_STORYTELLING)[0] == "deepseek-v3"


def test_standard_timeout_fallback_uses_purpose_arc() -> None:
    planner = SkeletonPlanner.__new__(SkeletonPlanner)
    deck = planner._fallback_standard_skeleton(
        project_id="proj-1",
        user_query="Create an educational deck about AI onboarding",
        analysis={"detected_purpose": "educational"},
        research=_empty_packet(),
        target_slide_count=3,
    )

    assert deck.narrative_arc == "educational"
    assert len(deck.slides) == 3
    assert all(slide.headline_target for slide in deck.slides)
    assert all(slide.generic_risk == "high" for slide in deck.slides)


def test_compile_marks_image_modality_slide_as_pending_without_url() -> None:
    slide = GeneratedSlide(
        index=0,
        intent="title",
        layout="title-only",
        headline="Fast Content Reveal",
        subheadline="Images stream in after the first usable slide appears",
        render_decision={"modality": "image", "renderer": "hero"},
    )

    compiled = compile_slide(slide=slide, image_url=None, deck_title="Speed Deck")
    props = compiled["artifacts"]["kit_jsx"]["props_json"]

    assert compiled["pending_image"] is True
    assert props["pendingImage"] is True
    assert props["imageIntent"] == "hero"
    assert not compiled["assets"]


def test_compile_clears_pending_when_image_url_exists() -> None:
    slide = GeneratedSlide(
        index=0,
        intent="title",
        layout="title-only",
        headline="Fast Content Reveal",
        render_decision={"modality": "image", "renderer": "hero"},
    )

    compiled = compile_slide(
        slide=slide,
        image_url="/api/v4/images/proj/slide-000.png",
        deck_title="Speed Deck",
    )
    props = compiled["artifacts"]["kit_jsx"]["props_json"]

    assert compiled["pending_image"] is False
    assert "pendingImage" not in props
    assert props["imageUrl"] == "/api/v4/images/proj/slide-000.png"
    assert compiled["assets"][0]["url"] == "/api/v4/images/proj/slide-000.png"