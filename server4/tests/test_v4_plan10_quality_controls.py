from __future__ import annotations

from app.services.image_pipeline.pipeline_router import ImageModelTier, ImagePipelineRouter
from app.services.v4.layout.rhythm_planner import plan_layout_rhythm
from app.services.v4.learning_store import _visibility_filters
from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.provenance_guard import apply_provenance_guard
from app.services.v4.quality_metrics import circuit_open, gate_decision, record_failure_window
from app.services.v4.research_collector import ResearchPacket
from app.services.v4.style_guard import apply_style_guard


def _research_without_claim_evidence() -> ResearchPacket:
    return ResearchPacket(
        query="business deck",
        industry=None,
        company_name=None,
        citations=[],
        news_citations=[],
        financial_data={},
        social_signals={},
        duration_ms=0,
    )


def test_provenance_guard_removes_unsupported_business_numbers() -> None:
    slide = GeneratedSlide(
        index=2,
        intent="market",
        layout="stat-hero",
        headline="Market Reaches $99M",
        subheadline="Unsupported numbers should not ship confidently",
        stat_blocks=[{"value": "$99M", "label": "unverified market claim"}],
        bullets=["Demand rises without a verified numeric claim"],
    )

    issues = apply_provenance_guard(
        [slide],
        research=_research_without_claim_evidence(),
        user_query="business deck",
        structured_context={},
    )

    assert issues
    assert slide.stat_blocks == []
    assert slide.requires_user_input is True
    assert slide.user_input_kind == "evidence"
    assert slide.user_input_reason == "unsupported_business_claims"
    assert "$99M" not in slide.headline


def test_style_guard_flags_generic_phrase_without_rewriting_user_facts() -> None:
    slide = GeneratedSlide(
        index=1,
        intent="solution",
        layout="two-column",
        headline="Specific Workflow For Finance Teams",
        subheadline="Our AI-powered solution improves review quality",
        body="The workflow keeps approvers focused on exceptions.",
    )

    issues = apply_style_guard([slide])

    assert any(issue.issue == "generic_phrase" for issue in issues)
    assert slide.subheadline == "Our AI-powered solution improves review quality"
    assert slide.raw["style_issues"]


def test_quality_gate_canary_and_circuit_breaker_are_deterministic() -> None:
    first = gate_decision("provenance", project_id="project-1", request_id="request-1")
    second = gate_decision("provenance", project_id="project-1", request_id="request-1")

    assert first.cohort_percent == second.cohort_percent
    key = "unit-test-schema-window"
    record_failure_window(key, window_s=60.0)
    record_failure_window(key, window_s=60.0)
    assert circuit_open(key, threshold=3, window_s=60.0) is False
    record_failure_window(key, window_s=60.0)
    assert circuit_open(key, threshold=3, window_s=60.0) is True


def test_learning_visibility_filters_exclude_unscoped_private_records() -> None:
    filters = _visibility_filters(
        user_id="user-1",
        project_id="project-1",
        tenant_id="tenant-1",
    )

    assert {"visibility_scope": "global"} in filters
    assert {"visibility_scope": "project", "project_id": "project-1"} in filters
    assert {"visibility_scope": "user", "user_id": "user-1"} in filters
    assert {"visibility_scope": "tenant", "tenant_id": "tenant-1"} in filters


def test_pollinations_is_not_reachable_when_disabled(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("app.services.image_pipeline.pipeline_router.settings.ALLOW_POLLINATIONS_IMAGES", False)
    router = ImagePipelineRouter()

    chain = router._build_chain(ImageModelTier.POLLINATIONS, set())

    assert ImageModelTier.POLLINATIONS not in chain
    assert chain[-1] == ImageModelTier.GRADIENT_SVG


def test_layout_rhythm_avoids_identical_adjacent_keys_when_candidates_allow() -> None:
    slides = [
        GeneratedSlide(index=0, intent="problem", layout="two-column", headline="Manual Review Creates Delay", bullets=["Approvals stall", "Exceptions spread"]),
        GeneratedSlide(index=1, intent="solution", layout="grid-3", headline="Workflow Routes Exceptions", bullets=["Capture requests", "Prioritize exceptions", "Resolve approvals"]),
        GeneratedSlide(index=2, intent="market", layout="stat-hero", headline="Demand Needs Evidence", stat_blocks=[{"value": "42", "label": "verified signal"}]),
    ]

    plan = plan_layout_rhythm(slides=slides)
    keys = [plan[i].key for i in sorted(plan)]

    assert len(keys) == 3
    assert keys[0] != keys[1]