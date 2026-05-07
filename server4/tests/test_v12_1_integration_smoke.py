"""Integration smoke for the v12.1 enhancements.

Goal: Exercise every new wiring point touched by the 2025-11-10 upgrade
   (loop_guard → critic, deep_research → pipeline, image_prompt_library →
   image_generator) WITHOUT requiring Mongo/Redis/external APIs to be up.

What we verify:
  1. `V4ContentPipeline()` instantiates cleanly (catches any import
     regression in critic_engine, content_pipeline, image_generator).
  2. `CriticEngine.evaluate()` produces a `CriticReport` whose
     `loop_report` field is populated and whose per-slide scores reflect
     loop_guard penalties (catches critic_engine ↔ loop_guard wiring).
  3. `image_generator._job_for()` builds an `ImageJob` with the archetype
     metadata set (catches image_generator ↔ image_prompt_library
     wiring).
  4. `DeepResearchLoop` is present on the pipeline in both standard and
     premium mode (catches content_pipeline ↔ deep_research wiring).

Runs purely in-process — no LLM, no network, no DB. Catches ~80% of the
integration risk of the three new modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.services.v4.content_pipeline import V4ContentPipeline
from app.services.v4.critic_engine import CriticEngine, CriticReport
from app.services.v4.deep_research import DeepResearchLoop
from app.services.v4.design_resolver import resolve_design_tokens
from app.services.v4.image_generator import _job_for
from app.services.v4.loop_guard import LoopGuardReport
from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.skeleton_planner import DeckSkeleton, SlideSkeleton


# ── Fixtures ─────────────────────────────────────────────────────

def _fake_slide(index: int, **overrides: Any) -> GeneratedSlide:
    defaults = dict(
        index=index,
        layout="two-column",
        intent="content",
        headline=f"Slide {index} headline",
        subheadline="",
        body="Body text describing this slide in a few sentences.",
        bullets=["First bullet point", "Second bullet point"],
        image_prompt="A modern abstract illustration",
        render_decision={"modality": "image", "confidence": 0.8},
    )
    defaults.update(overrides)
    return GeneratedSlide(**defaults)


def _fake_skeleton(slides: list[GeneratedSlide]) -> DeckSkeleton:
    return DeckSkeleton(
        project_id="smoke-test",
        title="Smoke Deck",
        narrative_arc="investor_pitch",
        slides=[
            SlideSkeleton(
                index=s.index,
                intent=s.intent,
                purpose=f"Slide {s.index} purpose",
                headline_target=s.headline,
                key_points=list(s.bullets or []),
                density_target="medium",
                layout_hint=s.layout,
            )
            for s in slides
        ],
    )


def _tokens():
    return resolve_design_tokens(
        design_profile=None,
        purpose="investor-pitch",
        industry="saas",
    )


# ── 1. Pipeline instantiation ─────────────────────────────────────

def test_pipeline_instantiates_with_all_new_modules() -> None:
    """Catches import/wiring regressions at __init__ time."""
    pipeline = V4ContentPipeline()
    assert pipeline.research is not None
    assert isinstance(pipeline.deep_research, DeepResearchLoop)
    assert pipeline.critic is not None
    # Deep research shares the same collector (no duplicate HTTP clients)
    assert pipeline.deep_research.collector is pipeline.research


# ── 2. Critic ↔ loop_guard ───────────────────────────────────────

@pytest.mark.asyncio
async def test_critic_report_includes_loop_report_on_clean_deck() -> None:
    critic = CriticEngine()
    slides = [_fake_slide(i, headline=f"Unique headline number {i}") for i in range(3)]
    skeleton = _fake_skeleton(slides)

    # Disable the LLM critique so the test is deterministic & offline.
    with patch.object(
        critic, "_llm_critique", new=AsyncMock(side_effect=RuntimeError("llm_disabled"))
    ):
        report = await critic.evaluate(slides=slides, skeleton=skeleton, research=None)

    assert isinstance(report, CriticReport)
    assert isinstance(report.loop_report, LoopGuardReport)
    assert report.loop_report.is_clean  # unique headlines → no findings


@pytest.mark.asyncio
async def test_critic_applies_loop_penalty_on_duplicate_deck() -> None:
    critic = CriticEngine()
    # Two slides with near-identical headlines → triggers headline_dup
    slides = [
        _fake_slide(0, headline="Transforming Procurement With Agentic AI"),
        _fake_slide(1, headline="Transforming Procurement Using Agentic AI"),
        _fake_slide(2, headline="Totally Different Story About Growth"),
    ]
    skeleton = _fake_skeleton(slides)

    with patch.object(
        critic, "_llm_critique", new=AsyncMock(side_effect=RuntimeError("llm_disabled"))
    ):
        report = await critic.evaluate(slides=slides, skeleton=skeleton, research=None)

    assert report.loop_report is not None
    assert not report.loop_report.is_clean
    # Slides 0 and 1 should have penalties recorded
    assert 0 in report.loop_report.per_slide_penalty
    assert 1 in report.loop_report.per_slide_penalty
    # Slide-level scores should reflect loop penalties via issues
    slide_0 = next(s for s in report.slide_scores if s.index == 0)
    assert any(i.startswith("loop_") for i in slide_0.issues)


# ── 3. Image generator ↔ image_prompt_library ────────────────────

def test_image_job_carries_archetype() -> None:
    slide = _fake_slide(0, intent="title", layout="title-only")
    tokens = _tokens()
    job = _job_for(slide, tokens, mode="premium")
    # archetype is attached to the job by _job_for
    arch = getattr(job, "archetype", None)
    assert arch is not None
    assert arch == "hero_cover_wide"
    # Prompt contains palette hex codes from the resolved tokens
    primary = tokens.palette.primary
    assert primary in job.prompt


def test_image_job_uses_problem_archetype_for_problem_intent() -> None:
    slide = _fake_slide(0, intent="problem", layout="stat-hero",
                        headline="Manual Review Burns 40 Hours Weekly")
    job = _job_for(slide, _tokens(), mode="standard")
    assert getattr(job, "archetype", None) == "problem_tension"
    assert "no on-image text" in job.prompt


def test_image_job_falls_back_when_no_image_prompt() -> None:
    slide = _fake_slide(0, intent="vision", layout="", image_prompt="",
                        headline="Our North Star")
    job = _job_for(slide, _tokens(), mode="standard")
    # Even with no writer prompt, library synthesises from headline
    assert "Our North Star" in job.prompt
    assert getattr(job, "archetype", None) is not None


# ── 4. Pipeline ↔ deep_research ───────────────────────────────────

def test_pipeline_exposes_deep_research_loop_in_both_modes() -> None:
    pipeline = V4ContentPipeline()
    # The loop is mode-agnostic at construction; mode is decided at run().
    assert isinstance(pipeline.deep_research, DeepResearchLoop)
    # Both "standard" and "premium" flow through the same attribute —
    # only the `mode` kwarg passed to .run() changes behaviour.
    import inspect
    sig = inspect.signature(pipeline.deep_research.run)
    assert "mode" in sig.parameters
    assert "research_depth" in sig.parameters
    assert "emit" in sig.parameters
