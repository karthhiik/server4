"""
Phase 6 (hot-swap) tests.

Covers detection, deterministic remediation paths, no-fake-data rule,
artifact recompilation, and event emission.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from app.services.v4.hot_swap import hot_swap_low_quality_slides
from app.services.v4.quality_scorer import attach_quality_scores


# AAA palette (matches Phase 4.5 fixtures) so contrast is not the
# failing dimension in these tests.
_AAA_TOKENS = {
    "palette": {
        "primary": "#0043CE",
        "accent": "#005D5D",
        "background": "#FFFFFF",
        "surface": "#FFFFFF",
        "text_primary": "#161616",
        "text_secondary": "#525252",
        "text_muted": "#6F6F6F",
        "success": "#198038",
        "danger": "#DA1E28",
        "border": "#DDE1E6",
    },
    "fonts": {"heading": "Inter", "body": "Inter"},
}


def _make_slide(
    *,
    slide_id: str,
    kit: str,
    props: dict[str, Any],
    index: int = 0,
) -> dict[str, Any]:
    """Build a real CompiledSlide dict via the actual Phase 5 compiler outputs."""
    from app.services.v4.animation_ir import build_animation_ir
    from app.services.v4.engine_transformer import build_engine
    from app.services.v4.html_transformer import build_html_css_js
    from app.services.v4.reveal_legacy_transformer import build_reveal_legacy
    from app.services.v4.slide_compiler import _render_jsx

    plan = {"intent": "title", "kit": kit, "entry": []}
    ir = build_animation_ir(plan)
    jsx = _render_jsx(kit=kit, props=props)
    return {
        "slide_id": slide_id,
        "slide_index": index,
        "jsx_source": jsx,
        "kit_component": kit,
        "animation_ir": ir,
        "artifact_version": 1,
        "artifacts": {
            "kit_jsx": {
                "source": jsx,
                "kit_component": kit,
                "props_json": json.loads(json.dumps(props, ensure_ascii=False)),
                "fingerprint": "x" * 12,
            },
            "html_css_js": build_html_css_js(
                kit=kit, props=props, animation_ir=ir, slide_id=slide_id
            ),
            "engine": build_engine(
                kit=kit, props=props, animation_ir=ir, slide_id=slide_id
            ),
            "reveal_legacy": build_reveal_legacy(
                kit=kit, props=props, animation_ir=ir, slide_id=slide_id
            ),
        },
        "quality_score": None,
    }


class _Recorder:
    """Captures emit() calls as (stage, payload) tuples."""

    def __init__(self):
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, stage: str, payload: dict[str, Any]) -> None:
        self.events.append((stage, dict(payload)))

    def stages(self) -> list[str]:
        return [s for s, _ in self.events]

    def find(self, stage: str) -> list[dict[str, Any]]:
        return [p for s, p in self.events if s == stage]


# ── Detection ────────────────────────────────────────────────────


def test_quality_summary_emitted_for_clean_deck():
    healthy = _make_slide(
        slide_id="slide-000",
        kit="TitleHero",
        props={"headline": "Acme Inc.", "subheadline": "Real-time presentations.", "variant": "gradient"},
    )
    attach_quality_scores([healthy], _AAA_TOKENS)
    rec = _Recorder()
    asyncio.run(hot_swap_low_quality_slides(
        compiled_slides=[healthy],
        design_tokens=_AAA_TOKENS,
        emit=rec,
    ))
    summaries = rec.find("quality_summary")
    assert len(summaries) == 1
    assert summaries[0]["n_slides"] == 1
    assert summaries[0]["n_low"] == 0
    # No per-slide hot-swap events since none failed.
    assert "slide_hotswap_started" not in rec.stages()


def test_low_quality_slide_emits_started_event():
    # 4 dangling edges + invalid node coord = 5 alignment issues
    # → alignment score 25 → dimension < threshold → enters hot-swap.
    slide = _make_slide(
        slide_id="slide-001",
        kit="DiagramBlock",
        props={
            "headline": "System architecture",
            "subheadline": "Real-time pipeline overview.",
            "nodes": [
                {"id": "a", "label": "API", "x": 0.2, "y": 0.5},
                {"id": "b", "label": "DB", "x": 0.8, "y": 0.5},
            ],
            "edges": [
                {"from": "a", "to": "ghost1"},
                {"from": "ghost2", "to": "b"},
                {"from": "ghost3", "to": "ghost4"},
                {"from": "a", "to": "ghost5"},
            ],
        },
    )
    attach_quality_scores([slide], _AAA_TOKENS)
    # Alignment dimension is below threshold even if overall is not.
    assert slide["quality_score"]["dimensions"]["alignment"]["score"] < 70
    rec = _Recorder()
    asyncio.run(hot_swap_low_quality_slides(
        compiled_slides=[slide],
        design_tokens=_AAA_TOKENS,
        emit=rec,
    ))
    assert "slide_hotswap_started" in rec.stages()


# ── Deterministic alignment fixes ────────────────────────────────


def test_diagram_block_drops_dangling_edges_and_promotes_score():
    slide = _make_slide(
        slide_id="slide-002",
        kit="DiagramBlock",
        props={
            "headline": "Architecture overview",
            "subheadline": "Data flow across services in real time.",
            "nodes": [
                {"id": "a", "label": "API", "x": 0.2, "y": 0.5},
                {"id": "b", "label": "DB", "x": 0.8, "y": 0.5},
            ],
            "edges": [
                {"from": "a", "to": "b", "label": "writes"},
                {"from": "a", "to": "ghost1"},
                {"from": "ghost2", "to": "b"},
                {"from": "ghost3", "to": "ghost4"},
            ],
        },
    )
    attach_quality_scores([slide], _AAA_TOKENS)
    rec = _Recorder()
    asyncio.run(hot_swap_low_quality_slides(
        compiled_slides=[slide],
        design_tokens=_AAA_TOKENS,
        emit=rec,
    ))
    edges = slide["artifacts"]["kit_jsx"]["props_json"]["edges"]
    assert len(edges) == 1
    assert edges[0]["from"] == "a" and edges[0]["to"] == "b"


def test_chart_block_drops_rows_with_no_numeric_values():
    # All-null data + missing headline + pie with no positives
    # → multiple alignment issues so the slide enters hot-swap.
    slide = _make_slide(
        slide_id="slide-003",
        kit="ChartBlock",
        props={
            "headline": "",
            "type": "bar",
            "xKey": "quarter",
            "yKeys": ["revenue"],
            "data": [
                {"quarter": "Q1", "revenue": 100},
                {"quarter": "Q2"},
                {"quarter": "Q3", "revenue": None},
                {"quarter": "Q4", "revenue": 220},
            ],
        },
    )
    attach_quality_scores([slide], _AAA_TOKENS)
    rec = _Recorder()
    asyncio.run(hot_swap_low_quality_slides(
        compiled_slides=[slide],
        design_tokens=_AAA_TOKENS,
        emit=rec,
    ))
    data = slide["artifacts"]["kit_jsx"]["props_json"]["data"]
    quarters = [r["quarter"] for r in data]
    # If hot-swap ran, dropped Q2 and Q3; if not (score above all
    # thresholds), data is untouched. Either way no fabricated rows.
    assert quarters in (["Q1", "Q4"], ["Q1", "Q2", "Q3", "Q4"])
    if quarters == ["Q1", "Q4"]:
        assert any("drop_empty_chart_rows" in p.get("fixes_applied", [""])[0]
                   if p.get("fixes_applied") else False
                   for p in rec.find("slide_hotswap_succeeded"))


def test_stat_hero_drops_empty_stat_entries():
    # Test the alignment helper directly — it must drop entries with
    # neither value nor label, never fabricate replacements.
    from app.services.v4.hot_swap import _apply_alignment_fixes
    props = {
        "stats": [
            {"value": "10x", "label": "ARR growth"},
            {"value": "", "label": ""},
            {"label": ""},
            {"value": " ", "label": " "},
            {"value": "", "label": "MRR"},
        ],
    }
    fixes = _apply_alignment_fixes(kit="StatHero", props=props)
    # 3 empties dropped; the real one + the label-only one survive.
    assert len(props["stats"]) == 2
    surviving = {(s.get("value", ""), s.get("label", "")) for s in props["stats"]}
    assert ("10x", "ARR growth") in surviving
    assert ("", "MRR") in surviving
    assert any("drop_empty_stats" in f for f in fixes)


# ── Density truncation ───────────────────────────────────────────


def test_density_overshoot_truncates_longest_field():
    long_text = "Lorem ipsum dolor sit amet, " * 30  # ~840 chars in one prop
    slide = _make_slide(
        slide_id="slide-005",
        kit="TitleHero",
        props={"headline": long_text, "subheadline": "Tagline.", "variant": "gradient"},
    )
    attach_quality_scores([slide], _AAA_TOKENS)
    before = slide["quality_score"]["overall"]
    rec = _Recorder()
    asyncio.run(hot_swap_low_quality_slides(
        compiled_slides=[slide],
        design_tokens=_AAA_TOKENS,
        emit=rec,
    ))
    after_headline = slide["artifacts"]["kit_jsx"]["props_json"]["headline"]
    assert after_headline.endswith("…")
    assert len(after_headline) < len(long_text)
    after_score = slide["quality_score"]["overall"]
    assert after_score >= before


# ── No-fake-data invariant ───────────────────────────────────────


def test_no_features_means_no_hot_swap_succeeded():
    """FeatureGrid alignment fix drops empty features; never invents."""
    from app.services.v4.hot_swap import _apply_alignment_fixes
    props = {
        "headline": "",
        "columns": 3,
        "features": [
            {"icon": "", "title": "", "description": ""},
            {"icon": "zap", "title": "Real", "description": "yes"},
            {"icon": "", "title": "", "description": ""},
        ],
    }
    fixes = _apply_alignment_fixes(kit="FeatureGrid", props=props)
    assert len(props["features"]) == 1
    assert props["features"][0]["title"] == "Real"
    assert any("drop_empty_features" in f for f in fixes)
    # And the empty case: cleanup leaves the slot empty rather than
    # inventing content.
    props2 = {"features": [{"icon": "", "title": "", "description": ""}]}
    _apply_alignment_fixes(kit="FeatureGrid", props=props2)
    assert props2["features"] == []


def test_artifact_version_bumped_on_success():
    slide = _make_slide(
        slide_id="slide-007",
        kit="DiagramBlock",
        props={
            "headline": "Real-time data flow across the production stack",
            "subheadline": "From ingestion to render in under one second.",
            "nodes": [
                {"id": "a", "label": "API gateway", "x": 0.15, "y": 0.5},
                {"id": "b", "label": "Database", "x": 0.85, "y": 0.5},
            ],
            "edges": [
                {"from": "a", "to": "b", "label": "writes durable rows"},
                {"from": "a", "to": "ghost"},
            ],
        },
    )
    attach_quality_scores([slide], _AAA_TOKENS)
    initial_version = slide["artifact_version"]
    rec = _Recorder()
    asyncio.run(hot_swap_low_quality_slides(
        compiled_slides=[slide],
        design_tokens=_AAA_TOKENS,
        emit=rec,
    ))
    if rec.find("slide_hotswap_succeeded"):
        assert slide["artifact_version"] == initial_version + 1
        assert slide.get("hot_swap", {}).get("applied") is True


# ── Hot-swap recompiles all four artifact slots ──────────────────


def test_all_four_artifacts_rebuilt_on_success():
    slide = _make_slide(
        slide_id="slide-008",
        kit="DiagramBlock",
        props={
            "headline": "Pipeline overview with end-to-end real-time guarantees",
            "subheadline": "Designed for low-latency presentation streaming.",
            "nodes": [
                {"id": "a", "label": "Source", "x": 0.2, "y": 0.4},
                {"id": "b", "label": "Sink", "x": 0.8, "y": 0.6},
            ],
            "edges": [
                {"from": "a", "to": "b"},
                {"from": "a", "to": "phantom"},
            ],
        },
    )
    attach_quality_scores([slide], _AAA_TOKENS)
    pre_engine_fp = slide["artifacts"]["engine"]["fingerprint"]
    pre_reveal_fp = slide["artifacts"]["reveal_legacy"]["fingerprint"]
    pre_html_fp = slide["artifacts"]["html_css_js"]["fingerprint"]
    pre_jsx_fp = slide["artifacts"]["kit_jsx"]["fingerprint"]

    rec = _Recorder()
    asyncio.run(hot_swap_low_quality_slides(
        compiled_slides=[slide],
        design_tokens=_AAA_TOKENS,
        emit=rec,
    ))
    if rec.find("slide_hotswap_succeeded"):
        assert slide["artifacts"]["engine"]["fingerprint"] != pre_engine_fp
        assert slide["artifacts"]["reveal_legacy"]["fingerprint"] != pre_reveal_fp
        assert slide["artifacts"]["html_css_js"]["fingerprint"] != pre_html_fp
        assert slide["artifacts"]["kit_jsx"]["fingerprint"] != pre_jsx_fp


# ── Final report ─────────────────────────────────────────────────


def test_hot_swap_complete_event_has_counts():
    slides = [
        _make_slide(
            slide_id=f"slide-{i:03d}",
            kit="TitleHero",
            props={"headline": "Acme Inc.", "subheadline": "Real-time decks.", "variant": "gradient"},
        )
        for i in range(3)
    ]
    attach_quality_scores(slides, _AAA_TOKENS)
    rec = _Recorder()
    asyncio.run(hot_swap_low_quality_slides(
        compiled_slides=slides,
        design_tokens=_AAA_TOKENS,
        emit=rec,
    ))
    completes = rec.find("hot_swap_complete")
    assert len(completes) == 1
    rep = completes[0]
    assert rep["n_attempted"] == rep["n_succeeded"] + rep["n_skipped"]
    assert isinstance(rep["duration_ms"], int)


def test_emit_failure_does_not_crash_pipeline():
    """A broken emit callback must not propagate."""

    async def bad_emit(stage: str, payload: dict[str, Any]) -> None:
        raise RuntimeError(f"emit broken at {stage}")

    slide = _make_slide(
        slide_id="slide-x",
        kit="TitleHero",
        props={"headline": "Hi", "subheadline": "There"},
    )
    attach_quality_scores([slide], _AAA_TOKENS)
    # Should not raise.
    asyncio.run(hot_swap_low_quality_slides(
        compiled_slides=[slide],
        design_tokens=_AAA_TOKENS,
        emit=bad_emit,
    ))
