from __future__ import annotations

import pytest

from app.services.image_pipeline.pipeline_router import ImageModelTier, ImagePipelineRouter
from app.services.image_pipeline.prompt_builder import PromptContext
from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.provenance_guard import apply_provenance_guard
from app.services.v4.research_collector import ResearchPacket
from app.services.v4.schema_guard import SchemaValidationError, validate_planner_slides, validate_writer_output
from app.services.v4.slide_compiler import compile_slide


def _empty_research() -> ResearchPacket:
    return ResearchPacket(
        query="real startup deck",
        industry=None,
        company_name=None,
        citations=[],
        news_citations=[],
        financial_data={},
        social_signals={},
        duration_ms=0,
    )


def test_writer_and_planner_schema_failures_do_not_normalize_into_fake_content() -> None:
    with pytest.raises(SchemaValidationError):
        validate_writer_output('{"headline":"   ","bullets":[]}', slide_index=0)

    with pytest.raises(SchemaValidationError):
        validate_planner_slides([{"layout_hint": ""}], project_id="project-failure")


def test_unsupported_numbers_are_removed_instead_of_persisted_confidently() -> None:
    slide = GeneratedSlide(
        index=3,
        intent="traction",
        layout="stat-hero",
        headline="Revenue reached $42M",
        stat_blocks=[{"value": "$42M", "label": "unverified revenue"}],
        bullets=["Momentum needs a verified source before it ships."],
    )

    issues = apply_provenance_guard([slide], research=_empty_research(), user_query="startup deck", structured_context={})

    assert issues
    assert slide.stat_blocks == []
    assert slide.requires_user_input is True
    assert slide.user_input_kind == "evidence"
    assert "$42M" not in slide.headline


def test_unresolved_team_slide_compiles_without_fake_people() -> None:
    slide = GeneratedSlide(
        index=8,
        intent="team",
        layout="team-grid",
        headline="Team details needed",
        requires_user_input=True,
        user_input_kind="team_members",
        user_input_reason="no_verified_members",
        team_members=[],
    )

    compiled = compile_slide(slide=slide)
    props = compiled["artifacts"]["kit_jsx"]["props_json"]

    assert compiled["kit_component"] == "TeamGrid"
    assert props["members"] == []
    assert props["requiresUserInput"] is True
    assert "founder" not in str(props).lower()
    assert "cto" not in str(props).lower()


@pytest.mark.asyncio
async def test_all_image_providers_skipped_returns_no_fake_image() -> None:
    router = ImagePipelineRouter()
    result = await router.generate(
        PromptContext(title="No provider should fabricate a visual", slide_index=2),
        skip_tiers=[
            ImageModelTier.AZURE_FLUX,
            ImageModelTier.NVIDIA_SD3,
            ImageModelTier.CF_PHOENIX,
            ImageModelTier.CF_LUCID,
            ImageModelTier.POLLINATIONS,
            ImageModelTier.GRADIENT_SVG,
        ],
    )

    assert result is None
