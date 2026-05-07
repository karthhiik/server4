"""Unit tests for the v12.1 loop_guard deterministic repetition detector.

Pure-logic tests: no network, no LLM, no DB. They verify each detector
fires on its target pattern and does NOT fire on healthy content.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from app.services.v4.loop_guard import (
    LoopGuardReport,
    detect_loops,
    _detect_bullet_loops,
    _detect_headline_duplicates,
    _detect_intent_imbalance,
    _detect_stutter,
    _detect_template_stamp,
)


@dataclass
class FakeSlide:
    """Minimal duck-type matching GeneratedSlide for the guard's needs."""
    index: int
    headline: str = ""
    subheadline: str = ""
    body: str = ""
    bullets: list[str] = field(default_factory=list)
    layout: str = "two-column"
    intent: str = "content"


def _healthy_deck() -> list[FakeSlide]:
    return [
        FakeSlide(0, headline="Transforming Procurement With AI", layout="title-only", intent="title"),
        FakeSlide(1, headline="Manual Invoice Review Burns 40 Hours Weekly", layout="stat-hero",
                  intent="problem", bullets=["AP teams lose 12 hours weekly on data entry"]),
        FakeSlide(2, headline="Agentic Workflows Automate Review", layout="diagram", intent="solution",
                  bullets=["LLM parses line items", "Policy engine flags anomalies"]),
        FakeSlide(3, headline="$24B Market Growing 18% Annually", layout="stat-hero", intent="market",
                  bullets=["Mid-market AP automation: $8B addressable"]),
        FakeSlide(4, headline="Pilots Save 38% of AP Hours", layout="chart-focus", intent="traction",
                  bullets=["5 design partners live", "96% invoice accuracy"]),
        FakeSlide(5, headline="Seed Round Accelerates GTM", layout="title-only", intent="ask"),
    ]


def test_healthy_deck_has_no_findings() -> None:
    report = detect_loops(_healthy_deck())
    assert isinstance(report, LoopGuardReport)
    assert report.is_clean
    assert report.n_findings == 0
    assert report.per_slide_penalty == {}


def test_headline_duplicates_flagged() -> None:
    slides = [
        FakeSlide(0, headline="Transforming Procurement With Agentic AI", intent="title"),
        FakeSlide(1, headline="Transforming Procurement Using Agentic AI", intent="solution"),
    ]
    findings = _detect_headline_duplicates(slides)
    assert len(findings) == 1
    assert findings[0].kind == "headline_dup"
    assert set(findings[0].slide_indices) == {0, 1}


def test_bullet_loop_flags_repeated_prefix() -> None:
    slides = [
        FakeSlide(i, headline=f"Slide {i}",
                  bullets=["We will leverage AI to automate workflows", "Other thing"])
        for i in range(4)
    ]
    findings = _detect_bullet_loops(slides)
    assert len(findings) == 1
    assert findings[0].kind == "bullet_loop"
    assert len(findings[0].slide_indices) == 4


def test_stutter_flagged_inside_body() -> None:
    slides = [
        FakeSlide(0, headline="Fine Headline",
                  body="We need to drive drive adoption across all regions"),
    ]
    findings = _detect_stutter(slides)
    assert len(findings) == 1
    assert findings[0].kind == "stutter"
    assert findings[0].slide_indices == [0]


def test_stutter_ignores_short_repeats() -> None:
    # "no no" is emphasis, not a bug — detector should not fire.
    slides = [FakeSlide(0, headline="Go go team", body="it it is ok")]
    assert _detect_stutter(slides) == []


def test_template_stamp_needs_five_plus() -> None:
    slides = [
        FakeSlide(i, headline=f"We Deliver Value For Users {i}", layout="two-column",
                  intent="content")
        for i in range(5)
    ]
    findings = _detect_template_stamp(slides)
    assert len(findings) == 1
    assert findings[0].kind == "template_stamp"
    assert len(findings[0].slide_indices) == 5


def test_template_stamp_does_not_fire_on_varied_verbs() -> None:
    # Same layout, different starter verbs — no stamp.
    headlines = [
        "Transforming The Way Teams Operate",
        "Scaling Procurement Across Industries",
        "Building Durable Market Leadership",
        "Shipping Continuously To Enterprise",
        "Launching In Two New Markets",
    ]
    slides = [FakeSlide(i, headline=h, layout="two-column") for i, h in enumerate(headlines)]
    assert _detect_template_stamp(slides) == []


def test_intent_imbalance_fires_on_two_intents() -> None:
    slides = [FakeSlide(i, headline=f"Slide {i}", intent="content") for i in range(6)]
    findings = _detect_intent_imbalance(slides)
    assert len(findings) == 1
    assert findings[0].kind == "intent_imbalance"
    # Flags every slide in the deck
    assert len(findings[0].slide_indices) == 6


def test_intent_imbalance_ignores_small_decks() -> None:
    slides = [FakeSlide(i, headline=f"Slide {i}", intent="content") for i in range(4)]
    assert _detect_intent_imbalance(slides) == []


def test_detect_loops_folds_penalties_into_per_slide_dict() -> None:
    bad_slides = [
        FakeSlide(0, headline="Transforming Procurement With AI", intent="title"),
        FakeSlide(1, headline="Transforming Procurement With AI", intent="solution"),
        FakeSlide(2, headline="Other Thing", intent="market", body="the the market"),
    ]
    report = detect_loops(bad_slides)
    assert not report.is_clean
    # Slide 0 and 1 duplicated, slide 2 has stutter
    assert 0 in report.per_slide_penalty
    assert 1 in report.per_slide_penalty
    assert 2 in report.per_slide_penalty
    # Penalties are capped at 4.0
    for v in report.per_slide_penalty.values():
        assert 0 < v <= 4.0
    # Issues carry a "loop_" prefix so critic knows the origin
    for issues in report.per_slide_issues.values():
        assert any(i.startswith("loop_") for i in issues)


def test_to_dict_shape_is_stable() -> None:
    report = detect_loops(_healthy_deck())
    payload = report.to_dict()
    assert payload["n_findings"] == 0
    assert isinstance(payload["findings"], list)
    assert isinstance(payload["per_slide_penalty"], dict)


def test_empty_slides_noop() -> None:
    report = detect_loops([])
    assert report.is_clean
    assert report.n_findings == 0
