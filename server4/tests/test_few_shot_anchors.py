"""
Phase 12 — Few-shot prompt injection.

Tests for `app.services.v4.few_shot_anchors`:

1. Anchor lookup by intent.
2. Layout tiebreaker selects the layout-matching variant.
3. Unknown intent → None / empty block.
4. Empty / blank intent → None / empty block.
5. Returned block is wrapped in a clear "DO NOT COPY" guard.
6. Returned block is valid JSON-embedding text.
7. All registered intents emit a non-empty anchor block.
8. Block carries the actual reference output JSON.
9. Layout-mismatch falls back to first anchor for the intent.
10. Anchor structure invariants (every anchor has skeleton + output dicts
    with the canonical fields).
"""
from __future__ import annotations

import json

import pytest

from app.services.v4.few_shot_anchors import (
    _ANCHORS,
    _BY_INTENT,
    _select_anchor,
    format_few_shot,
)


def test_select_anchor_by_intent_only():
    a = _select_anchor("problem", layout_hint=None)
    assert a is not None
    assert a["intent"] == "problem"


def test_select_anchor_layout_tiebreaker():
    # The "competition" intent has anchors keyed on comparison/table/two-column.
    a = _select_anchor("competition", layout_hint="comparison")
    assert a is not None
    assert "comparison" in a["layouts"]


def test_select_anchor_unknown_intent_returns_none():
    assert _select_anchor("not_a_real_intent", None) is None
    assert _select_anchor("", None) is None
    assert _select_anchor("   ", None) is None


def test_format_few_shot_unknown_intent_returns_empty():
    assert format_few_shot("not_a_real_intent") == ""
    assert format_few_shot("") == ""


def test_format_few_shot_emits_do_not_copy_guard():
    block = format_few_shot("problem", layout_hint="bullet-points")
    assert block, "expected a non-empty block for a registered intent"
    # Both DO-NOT-COPY guard rails must be present.
    assert "DO NOT copy" in block
    assert "REFERENCE EXAMPLE" in block
    assert "END REFERENCE EXAMPLE" in block


def test_format_few_shot_block_carries_reference_output_json():
    block = format_few_shot("traction", layout_hint="stat-hero")
    assert "reference_output:" in block
    # Extract the JSON payload after "reference_output:" up to the next newline.
    line = next(
        ln for ln in block.splitlines() if ln.startswith("reference_output:")
    )
    payload = line.split("reference_output:", 1)[1].strip()
    parsed = json.loads(payload)
    assert "headline" in parsed
    assert "subheadline" in parsed


@pytest.mark.parametrize(
    "intent",
    [
        "title", "problem", "solution", "how_it_works", "market",
        "traction", "business_model", "competition", "go_to_market",
        "technology", "team", "financials", "ask",
    ],
)
def test_every_registered_intent_has_anchor(intent):
    block = format_few_shot(intent)
    assert block, f"intent {intent!r} should have an anchor"
    assert "REFERENCE EXAMPLE" in block


def test_layout_mismatch_falls_back_to_first_anchor_for_intent():
    # "problem" anchors don't include "stat-hero"; we should still get the
    # default problem anchor rather than None.
    a = _select_anchor("problem", layout_hint="stat-hero")
    assert a is not None
    assert a["intent"] == "problem"


def test_anchor_structure_invariants():
    required_skel_keys = {"intent", "headline_target", "key_points", "layout_hint"}
    for a in _ANCHORS:
        assert isinstance(a["intent"], str) and a["intent"]
        assert isinstance(a["layouts"], tuple) and a["layouts"]
        skel = a["skeleton"]
        out = a["output"]
        assert isinstance(skel, dict)
        assert isinstance(out, dict)
        # Skeleton must mirror the writer's input shape.
        assert required_skel_keys.issubset(skel.keys()), (
            f"anchor {a['intent']!r} missing skeleton keys: "
            f"{required_skel_keys - set(skel.keys())}"
        )
        # Output must always carry headline + speaker_notes.
        assert "headline" in out
        assert "speaker_notes" in out
        assert isinstance(out["headline"], str) and out["headline"]


def test_intent_index_consistency():
    # Every anchor in _ANCHORS must be indexed under _BY_INTENT.
    seen = 0
    for intent, lst in _BY_INTENT.items():
        for a in lst:
            assert a["intent"] == intent
            seen += 1
    assert seen == len(_ANCHORS)


def test_format_few_shot_intent_normalization():
    # Intent matching should be case- and whitespace-insensitive.
    assert format_few_shot("PROBLEM") != ""
    assert format_few_shot("  problem  ") != ""
    assert format_few_shot("Problem") != ""


def test_block_is_compact_enough_for_token_budget():
    # Sanity: a single anchor block should be well under ~2000 chars
    # (~500 tokens) so it doesn't blow the writer prompt budget.
    for intent in _BY_INTENT:
        block = format_few_shot(intent)
        assert len(block) < 4000, (
            f"anchor block for {intent!r} is too long: {len(block)} chars"
        )
