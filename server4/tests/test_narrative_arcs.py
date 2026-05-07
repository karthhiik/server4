"""Tests for purpose-aware narrative arcs (plan 03)."""

from __future__ import annotations

import pytest

from app.models.generation_input_v4 import PresentationPurpose
from app.services.v4.narrative_arcs import (
    FORBIDDEN_INTENTS_BY_PURPOSE,
    NARRATIVE_ARCS,
    VOICE_PROFILES,
    NarrativeSlot,
    arc_to_planner_payload,
    get_arc_for_purpose,
    get_forbidden_intents,
    get_voice_profile,
    scale_arc,
)


# Every PresentationPurpose enum value must have a hand-crafted arc.
@pytest.mark.parametrize("purpose", [p.value for p in PresentationPurpose])
def test_every_purpose_has_arc(purpose: str) -> None:
    assert purpose in NARRATIVE_ARCS, f"missing arc for {purpose!r}"
    arc = NARRATIVE_ARCS[purpose]
    assert len(arc) >= 5, f"arc for {purpose!r} too short ({len(arc)})"
    assert all(isinstance(s, NarrativeSlot) for s in arc)
    # First and last slots should be unique anchors.
    intents = [s.intent for s in arc]
    assert intents[0] != intents[-1]
    # Must contain at least one ``must`` slot.
    assert any(s.priority == "must" for s in arc)


@pytest.mark.parametrize("purpose", [p.value for p in PresentationPurpose])
def test_every_purpose_has_voice_profile(purpose: str) -> None:
    assert purpose in VOICE_PROFILES
    vp = VOICE_PROFILES[purpose]
    for axis_name, axis in vp.as_dict().items():
        assert 0.0 <= axis <= 1.0, f"{purpose}.{axis_name}={axis} out of range"


@pytest.mark.parametrize("purpose", [p.value for p in PresentationPurpose])
def test_every_purpose_has_forbidden_set(purpose: str) -> None:
    assert purpose in FORBIDDEN_INTENTS_BY_PURPOSE


@pytest.mark.parametrize(
    "purpose,n",
    [
        (p.value, n)
        for p in PresentationPurpose
        for n in (1, 3, 5, 7, 10, 15, 25, 50)
    ],
)
def test_scale_arc_returns_exact_count(purpose: str, n: int) -> None:
    arc = get_arc_for_purpose(purpose)
    out = scale_arc(arc, n)
    assert len(out) == n


def test_scale_arc_clamps_to_one() -> None:
    arc = get_arc_for_purpose("pitch_deck")
    assert len(scale_arc(arc, 0)) == 1
    assert len(scale_arc(arc, -5)) == 1


def test_scale_arc_clamps_to_fifty() -> None:
    arc = get_arc_for_purpose("pitch_deck")
    assert len(scale_arc(arc, 100)) == 50


def test_scale_arc_preserves_must_slots_when_possible() -> None:
    arc = get_arc_for_purpose("pitch_deck")
    must_count = sum(1 for s in arc if s.priority == "must")
    out = scale_arc(arc, must_count)
    assert len(out) == must_count
    # Every kept slot should be a must-slot.
    out_intents = {s.intent for s in out}
    must_intents = {s.intent for s in arc if s.priority == "must"}
    assert out_intents == must_intents


def test_scale_arc_expand_does_not_duplicate_first_or_last() -> None:
    arc = get_arc_for_purpose("conference_talk")
    target = len(arc) + 5
    out = scale_arc(arc, target)
    assert len(out) == target
    # First slot intent must equal the original first slot.
    assert out[0].intent == arc[0].intent
    # Last slot intent must equal the original last slot.
    assert out[-1].intent == arc[-1].intent
    # No duplicate intents.
    intents = [s.intent for s in out]
    assert len(set(intents)) == len(intents)


def test_get_arc_for_purpose_unknown_falls_back_to_custom() -> None:
    out = get_arc_for_purpose("not_a_real_purpose_xyz")
    assert out == get_arc_for_purpose("custom")


def test_get_arc_for_purpose_none_falls_back_to_custom() -> None:
    out = get_arc_for_purpose(None)
    assert out == get_arc_for_purpose("custom")


def test_get_arc_for_purpose_returns_copy() -> None:
    a = get_arc_for_purpose("pitch_deck")
    a.clear()
    b = get_arc_for_purpose("pitch_deck")
    assert len(b) > 0


def test_forbidden_intents_educational_blocks_pitch_intents() -> None:
    forbidden = get_forbidden_intents("educational")
    assert "competition" in forbidden
    assert "ask" in forbidden
    assert "fundraising" in forbidden


def test_forbidden_intents_pitch_deck_is_empty() -> None:
    assert get_forbidden_intents("pitch_deck") == frozenset()


def test_voice_profile_sales_more_persuasive_than_educational() -> None:
    sales = get_voice_profile("sales_deck")
    edu = get_voice_profile("educational")
    assert sales.persuasiveness > edu.persuasiveness


def test_voice_profile_demo_day_more_urgent_than_quarterly_review() -> None:
    demo = get_voice_profile("demo_day")
    qbr = get_voice_profile("quarterly_review")
    assert demo.urgency > qbr.urgency


def test_voice_profile_board_meeting_more_formal_than_conference_talk() -> None:
    board = get_voice_profile("board_meeting")
    talk = get_voice_profile("conference_talk")
    assert board.formality > talk.formality


def test_arc_to_planner_payload_shape() -> None:
    arc = scale_arc(get_arc_for_purpose("pitch_deck"), 5)
    payload = arc_to_planner_payload(arc)
    assert len(payload) == 5
    for entry in payload:
        assert set(entry.keys()) == {"intent", "suggested_layout", "brief", "voice"}
        assert all(isinstance(v, str) for v in entry.values())


def test_arc_to_planner_payload_omits_priority() -> None:
    arc = scale_arc(get_arc_for_purpose("internal_memo"), 4)
    payload = arc_to_planner_payload(arc)
    for entry in payload:
        assert "priority" not in entry


def test_internal_memo_starts_with_executive_summary() -> None:
    arc = get_arc_for_purpose("internal_memo")
    # Pyramid principle: the answer (decision/exec summary) appears
    # in the first two slots.
    leading = [s.intent for s in arc[:2]]
    assert any("executive" in i or "title" in i for i in leading)


def test_demo_day_arc_is_short_and_pitch_shaped() -> None:
    arc = get_arc_for_purpose("demo_day")
    intents = {s.intent for s in arc}
    # YC-style demo day must include the core pitch intents.
    assert {"problem", "solution", "traction", "ask"}.issubset(intents)
    # And must remain short \u2014 demo day is a sub-3-minute pitch.
    assert len(arc) <= 8


def test_educational_arc_avoids_pitch_intents() -> None:
    arc = get_arc_for_purpose("educational")
    intents = {s.intent for s in arc}
    forbidden = get_forbidden_intents("educational")
    assert intents.isdisjoint(forbidden)


def test_scale_arc_smaller_than_must_count_keeps_must_prefix() -> None:
    arc = get_arc_for_purpose("pitch_deck")
    must_count = sum(1 for s in arc if s.priority == "must")
    n = max(1, must_count - 2)
    out = scale_arc(arc, n)
    assert len(out) == n
    # All output slots should still be ``must`` slots from the original.
    must_intents_in_order = [s.intent for s in arc if s.priority == "must"]
    assert [s.intent for s in out] == must_intents_in_order[:n]
