"""
Unit tests for v4.animation_ir.build_animation_ir.

Validates:
  - Determinism (same input → same fingerprint)
  - Sensitivity (any plan change → different fingerprint)
  - CSS contains keyframes for every effect referenced + classes per entry
  - Reduced-motion override present
  - Stagger expansion produces N children with monotonic delays
  - Unknown effects fall back to `fade` (no fake fancy effect)
  - Reveal fragments ordered by (delay, stagger_index)
  - Motion props transition timing matches input
  - to_reduced_motion flattens correctly
  - Real plan from `slide_compiler._default_animation_plan` round-trips
"""

from __future__ import annotations

from app.services.v4.animation_ir import (
    build_animation_ir,
    to_reduced_motion,
)
from app.services.v4.slide_compiler import _default_animation_plan


def test_real_plan_roundtrips():
    """Use the actual slide_compiler default — no hand-crafted fakes."""
    plan = _default_animation_plan(intent="traction", layout="", kit="StatHero")
    ir = build_animation_ir(plan)

    assert ir["version"] == 1
    assert len(ir["fingerprint"]) == 12
    assert ir["transition"] == "slide"  # traction → slide
    # StatHero has 3 entry items (headline, subheadline, stats)
    assert len(ir["entries"]) >= 3
    # Each entry has the canonical normalized shape
    for e in ir["entries"]:
        assert {"id", "target", "effect", "delay_ms", "duration_ms", "easing", "phase"} <= set(e.keys())
        assert e["phase"] == "entry"
        assert e["duration_ms"] >= 0
        assert e["delay_ms"] >= 0


def test_deterministic():
    plan = _default_animation_plan(intent="vision", layout="", kit="TitleHero")
    a = build_animation_ir(plan)
    b = build_animation_ir(plan)
    assert a["fingerprint"] == b["fingerprint"]
    assert a["css"] == b["css"]
    assert a["motion_props"] == b["motion_props"]


def test_fingerprint_changes_with_plan():
    a = build_animation_ir(_default_animation_plan(intent="vision", kit="TitleHero"))
    b = build_animation_ir(_default_animation_plan(intent="traction", kit="StatHero"))
    assert a["fingerprint"] != b["fingerprint"]


def test_css_has_keyframes_and_classes():
    plan = _default_animation_plan(intent="vision", kit="TitleHero")
    ir = build_animation_ir(plan)
    css = ir["css"]
    assert "@keyframes ir-fade-up" in css
    assert ".ir-anim-entry-" in css
    # Reduced-motion override must always be present
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_unknown_effect_falls_back_to_fade():
    plan = {
        "entry": [{"target": "x", "effect": "warp-drive", "duration_ms": 200, "delay_ms": 0}],
        "emphasis": [],
        "hover": [],
        "exit": [],
        "transition": "fade",
    }
    ir = build_animation_ir(plan)
    assert ir["entries"][0]["effect"] == "fade"
    assert "@keyframes ir-fade " in ir["css"] or "@keyframes ir-fade {" in ir["css"]


def test_stagger_expansion():
    plan = {
        "entry": [{
            "target": "cards",
            "effect": "fade-up",
            "duration_ms": 400,
            "delay_ms": 100,
            "stagger_ms": 80,
            "stagger_count": 4,
        }],
        "emphasis": [],
        "hover": [],
        "exit": [],
        "transition": "fade",
    }
    ir = build_animation_ir(plan)
    assert len(ir["entries"]) == 4
    delays = [e["delay_ms"] for e in ir["entries"]]
    assert delays == [100, 180, 260, 340]  # monotonic + correct math
    targets = [e["target"] for e in ir["entries"]]
    assert targets == ["cards.0", "cards.1", "cards.2", "cards.3"]


def test_motion_props_timing_in_seconds():
    plan = {
        "entry": [{"target": "h", "effect": "fade-up", "duration_ms": 500, "delay_ms": 200, "easing": "ease-out"}],
        "emphasis": [], "hover": [], "exit": [],
        "transition": "fade",
    }
    ir = build_animation_ir(plan)
    mp = ir["motion_props"]["h"]
    assert mp["transition"]["duration"] == 0.5
    assert mp["transition"]["delay"] == 0.2
    assert mp["initial"]["opacity"] == 0
    assert mp["animate"]["opacity"] == 1


def test_reveal_fragments_ordered_by_delay():
    plan = {
        "entry": [
            {"target": "z", "effect": "fade", "duration_ms": 300, "delay_ms": 400},
            {"target": "a", "effect": "fade", "duration_ms": 300, "delay_ms": 100},
            {"target": "m", "effect": "fade", "duration_ms": 300, "delay_ms": 200},
        ],
        "emphasis": [], "hover": [], "exit": [],
        "transition": "fade",
    }
    ir = build_animation_ir(plan)
    indices = [f["index"] for f in ir["reveal_fragments"]]
    targets = [f["target"] for f in ir["reveal_fragments"]]
    assert indices == [0, 1, 2]
    assert targets == ["a", "m", "z"]


def test_total_entry_ms():
    plan = {
        "entry": [
            {"target": "a", "effect": "fade", "duration_ms": 300, "delay_ms": 100},  # 400
            {"target": "b", "effect": "fade", "duration_ms": 500, "delay_ms": 200},  # 700
            {"target": "c", "effect": "fade", "duration_ms": 200, "delay_ms": 50},   # 250
        ],
        "emphasis": [], "hover": [], "exit": [],
        "transition": "fade",
    }
    ir = build_animation_ir(plan)
    assert ir["total_entry_ms"] == 700


def test_morph_ids_unique_per_group():
    plan = {
        "entry": [{
            "target": "cards", "effect": "fade-up", "duration_ms": 300, "delay_ms": 0,
            "stagger_ms": 60, "stagger_count": 5,
        }],
        "emphasis": [], "hover": [], "exit": [],
        "transition": "fade",
    }
    ir = build_animation_ir(plan)
    # 5 staggered children → 1 morph id (parent group), not 5
    assert ir["morph_ids"] == ["morph-cards"]


def test_to_reduced_motion():
    plan = _default_animation_plan(intent="metrics", kit="StatHero")
    ir = build_animation_ir(plan)
    rm = to_reduced_motion(ir)

    assert rm["transition"] == "none"
    assert rm["total_entry_ms"] == 0
    for e in rm["entries"]:
        assert e["effect"] == "fade"
        assert e["duration_ms"] == 0
        assert e["delay_ms"] == 0
    # Original IR untouched
    assert ir["entries"][0]["duration_ms"] > 0


def test_defensive_against_garbage_input():
    # Non-dict input
    ir = build_animation_ir(None)  # type: ignore[arg-type]
    assert ir["entries"] == []
    assert ir["transition"] == "fade"
    # Missing keys
    ir2 = build_animation_ir({})
    assert ir2["entries"] == []
    # Garbage entry items
    ir3 = build_animation_ir({"entry": [None, "bad", {"target": "x", "effect": "fade", "duration_ms": "bad", "delay_ms": -50}]})
    # Bad numbers coerced to defaults; bad list items skipped
    assert len(ir3["entries"]) == 1
    assert ir3["entries"][0]["duration_ms"] == 400  # default
    assert ir3["entries"][0]["delay_ms"] == 0      # clamped


def test_all_kits_produce_valid_ir():
    """Every kit component produces a valid IR end-to-end."""
    kits = [
        "TitleHero", "StatHero", "ChartBlock", "TimelineBlock",
        "ComparisonBlock", "FeatureGrid", "TeamGrid", "QuoteBlock",
        "FullBleedImage", "DiagramBlock",
    ]
    for kit in kits:
        plan = _default_animation_plan(intent="default", kit=kit)
        ir = build_animation_ir(plan)
        assert ir["fingerprint"]
        assert ir["css"]
        # Every kit emits at least one entry animation in the default plan
        # (verified by reading slide_compiler — they all do).
        assert len(ir["entries"]) >= 1
