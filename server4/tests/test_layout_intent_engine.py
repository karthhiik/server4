"""Plan 06 tests for the deterministic layout intent engine."""

from __future__ import annotations

from app.services.v4.layout.intent_engine import extract_features, select_layout
from app.services.v4.layout.library import LAYOUT_LIBRARY
from app.services.v4.parallel_writer import GeneratedSlide


def test_layout_library_has_plan_06_variant_floor() -> None:
    assert len(LAYOUT_LIBRARY) >= 30
    keys = {spec.key for spec in LAYOUT_LIBRARY}
    assert len(keys) == len(LAYOUT_LIBRARY)


def test_extract_features_detects_density_and_signals() -> None:
    slide = GeneratedSlide(
        index=2,
        intent="traction",
        layout="metrics",
        headline="Growth keeps compounding",
        bullets=["12K active teams", "142% net retention", "$4.2M ARR"],
    )
    features = extract_features(slide, deck_purpose="pitch_deck", deck_index=2, deck_total=8)
    assert features.intent == "traction"
    assert features.has_stats is True
    assert "stats" in features.signals
    assert features.position == "early"


def test_select_layout_prefers_structured_chart_over_generic_content() -> None:
    slide = GeneratedSlide(
        index=3,
        intent="market",
        layout="chart focus",
        headline="The market is expanding",
        chart={"type": "bar", "data": [{"name": "2024", "value": 10}]},
        bullets=["The category is moving from tools to platforms"],
    )
    candidate = select_layout(slide=slide, deck_purpose="pitch_deck", deck_index=3, deck_total=10)
    assert candidate.kit_id == "ChartBlock"
    assert candidate.layout_variant in {"chart-focus", "chart-with-thesis", "market-data"}
    assert "requires:chart" in candidate.rationale


def test_select_layout_penalizes_recent_repetition() -> None:
    slide = GeneratedSlide(
        index=4,
        intent="solution",
        layout="feature grid",
        headline="Workflow advantage",
        bullets=[
            "Fast setup — onboard in minutes",
            "Secure workflow — permissions built in",
            "Global reach — deploy across teams",
        ],
    )
    first = select_layout(slide=slide, deck_index=1, deck_total=6)
    second = select_layout(
        slide=slide,
        deck_index=2,
        deck_total=6,
        previous_layouts=(first.key, first.key),
    )
    assert second.key != first.key
    assert "diversity" in second.rationale or second.layout_variant != first.layout_variant