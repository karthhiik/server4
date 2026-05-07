"""Regression tests for the slide-count contract (Plan 02 v2).

Guards against the original "target_slide_count or len(LLM_output)" bug
ever creeping back into the planner / pipeline.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]  # server4/
PLANNER_PATH = REPO_ROOT / "app" / "services" / "v4" / "skeleton_planner.py"
ROUTER_FILE = REPO_ROOT / "app" / "services" / "llm" / "model_router.py"
GEN_V4_FILE = REPO_ROOT / "app" / "routers" / "generation_v4.py"


def test_planner_has_no_fragile_or_fallback_for_target_count() -> None:
    """Plan 02 v2: ``target = target_slide_count or len(...)`` is forbidden.

    The pattern silently treats ``None`` as "use whatever len(scaffold) /
    len(slides) is" \u2014 which was the root cause of the slide-count drift
    bug. All sites must now go through ``_resolve_target_count``.
    """
    src = PLANNER_PATH.read_text(encoding="utf-8")
    pattern = re.compile(r"target\s*=\s*target_slide_count\s+or\s+len\(")
    matches = pattern.findall(src)
    assert not matches, (
        f"Found {len(matches)} occurrences of the fragile "
        "`target = target_slide_count or len(...)` pattern in "
        f"{PLANNER_PATH}. Use _resolve_target_count() instead."
    )


def test_planner_does_not_special_case_count_one_in_prompt() -> None:
    """The standard-mode prompt must not include the
    'If the requested count is 1, return a single slide' instruction.

    A deterministic short-circuit at the top of ``_plan_standard``
    already handles ``target == 1`` by routing to ``_fallback_skeleton``.
    Keeping the prompt sentence around encouraged some models to
    *guess* at "what fits the purpose" and produce 1-slide decks even
    when the user requested 8.
    """
    src = PLANNER_PATH.read_text(encoding="utf-8")
    assert "If the requested count is 1" not in src, (
        "skeleton_planner._STANDARD_SYSTEM still contains the "
        "count==1 special-case sentence that biased planners toward "
        "single-slide outputs. Remove it; the deterministic short-"
        "circuit in _plan_standard already covers this case."
    )


def test_router_outline_chain_has_gpt4o_mini_safety_tail() -> None:
    """Plan 02 v2: OUTLINE_PLANNING and PREMIUM_THESIS_PLANNING must
    end with the gpt-4o-mini final safety tail, after openrouter."""
    src = ROUTER_FILE.read_text(encoding="utf-8")
    assert "_with_safety_tail" in src, "_with_safety_tail helper missing"
    assert "is_final_safety_tail" in src, "is_final_safety_tail helper missing"
    assert "TaskType.OUTLINE_PLANNING:       _with_safety_tail" in src, (
        "OUTLINE_PLANNING must use _with_safety_tail (not _with_openrouter_tail)"
    )


def test_router_uses_resolver_before_pipeline() -> None:
    """The V4 generation router must call ``resolve_requested_count``
    BEFORE handing off to the background pipeline so the pipeline never
    sees a ``None`` slide count."""
    src = GEN_V4_FILE.read_text(encoding="utf-8")
    assert "resolve_requested_count" in src, (
        "generation_v4.py must import and call resolve_requested_count"
    )
    # Resolver must be called before the background_tasks.add_task line
    resolver_pos = src.find("resolve_requested_count(")
    bg_pos = src.find("background_tasks.add_task")
    assert resolver_pos != -1 and bg_pos != -1
    assert resolver_pos < bg_pos, (
        "resolve_requested_count must run BEFORE background_tasks.add_task"
    )


def test_resolver_helper_is_module_private_in_planner() -> None:
    """``_resolve_target_count`` defense-in-depth helper must exist in
    skeleton_planner.py (module level, underscore-prefixed)."""
    src = PLANNER_PATH.read_text(encoding="utf-8")
    assert re.search(
        r"^def _resolve_target_count\(",
        src,
        re.MULTILINE,
    ), "_resolve_target_count() helper missing in skeleton_planner.py"


@pytest.mark.parametrize("count", [1, 2, 5, 10, 25, 50])
def test_resolver_returns_exact_user_count(count: int) -> None:
    """User-supplied count must round-trip through the resolver
    unchanged (within [1, 50])."""
    from app.services.v4.slide_count_resolver import resolve_requested_count

    assert (
        resolve_requested_count(
            user_supplied=count,
            analyzer_suggested=10,
            purpose="pitch_deck",
            mode="standard",
        )
        == count
    )
