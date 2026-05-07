"""
Phase 5 (Day 9-10) tests — reveal_legacy_transformer.

Verifies reveal-native markup, fragment indexing tied to AnimationIR
order, XSS escaping, deterministic fingerprint, unknown-kit error,
standalone deck wrapping, and per-kit content correctness.
"""

from __future__ import annotations

import re

import pytest

from app.services.v4.animation_ir import build_animation_ir
from app.services.v4.reveal_legacy_transformer import (
    build_reveal_legacy,
    render_standalone_reveal_deck,
)


def _ir_for(intent: str, kit: str):
    plan = {
        "intent": intent,
        "kit": kit,
        "entry": [
            {"target": "headline", "effect": "fade-up", "delay_ms": 100, "duration_ms": 400, "easing": "ease-out"},
            {"target": "subheadline", "effect": "fade-up", "delay_ms": 200, "duration_ms": 400, "easing": "ease-out"},
            {"target": "stats", "effect": "fade-up", "delay_ms": 300, "duration_ms": 400, "stagger_ms": 60, "easing": "ease-out"},
        ],
    }
    return build_animation_ir(plan)


# ── Public contract ──────────────────────────────────────────────


def test_artifact_has_expected_top_level_keys():
    art = build_reveal_legacy(kit="TitleHero", props={"headline": "Hi"}, animation_ir=None)
    for k in ("schema_version", "section", "css", "fragments", "fingerprint"):
        assert k in art
    assert art["schema_version"] == 1
    assert len(art["fingerprint"]) == 12


def test_unknown_kit_emits_data_error_section():
    art = build_reveal_legacy(kit="MysteryKit", props={"headline": "x"}, animation_ir=None)
    assert 'data-error="unknown_kit"' in art["section"]
    assert 'role="alert"' in art["section"]
    assert "Unknown kit component: MysteryKit" in art["section"]


def test_section_starts_with_section_tag_and_kit_attr():
    art = build_reveal_legacy(kit="StatHero", props={"headline": "H"}, animation_ir=None)
    assert art["section"].startswith('<section class="reveal-slide" data-kit="StatHero"')
    assert art["section"].endswith("</section>")


def test_fingerprint_is_deterministic():
    args = dict(
        kit="StatHero",
        props={"headline": "H", "stats": [{"value": "10x", "label": "ARR"}]},
        animation_ir=None,
    )
    a = build_reveal_legacy(**args)
    b = build_reveal_legacy(**args)
    assert a["fingerprint"] == b["fingerprint"]


# ── XSS escaping ─────────────────────────────────────────────────


def test_xss_in_headline_is_escaped():
    art = build_reveal_legacy(
        kit="TitleHero",
        props={"headline": "<script>alert(1)</script>"},
        animation_ir=None,
    )
    assert "<script>" not in art["section"]
    assert "&lt;script&gt;" in art["section"]


def test_xss_in_image_url_is_escaped():
    art = build_reveal_legacy(
        kit="TitleHero",
        props={"headline": "x", "imageUrl": '"><script>x</script>', "variant": "image"},
        animation_ir=None,
    )
    assert "<script>" not in art["section"]


# ── Fragment indexing ────────────────────────────────────────────


def test_fragments_indexed_in_ir_order():
    ir = _ir_for("stat", "StatHero")
    art = build_reveal_legacy(
        kit="StatHero",
        props={
            "headline": "H",
            "subheadline": "S",
            "stats": [
                {"value": "10x", "label": "a"},
                {"value": "$1M", "label": "b"},
            ],
        },
        animation_ir=ir,
    )
    by_id = {f["id"]: f["index"] for f in art["fragments"]}
    # IR has headline (delay=100) before subheadline (delay=200) — order honored.
    assert by_id["headline"] < by_id["subheadline"]
    # Per-stat targets allocated after IR-known targets.
    assert by_id["stats.0"] > by_id["subheadline"]
    assert by_id["stats.1"] > by_id["stats.0"]
    # Section markup carries the indices.
    assert 'data-fragment-index="0"' in art["section"]
    assert f'data-fragment-index="{by_id["stats.1"]}"' in art["section"]


def test_fragments_present_even_without_ir():
    art = build_reveal_legacy(
        kit="StatHero",
        props={"headline": "H", "stats": [{"value": "1", "label": "a"}]},
        animation_ir=None,
    )
    # Without IR, fragments still allocated in encounter order.
    ids = [f["id"] for f in art["fragments"]]
    assert "headline" in ids
    assert "stats.0" in ids


def test_reduced_motion_media_query_present_in_css():
    art = build_reveal_legacy(kit="TitleHero", props={"headline": "x"}, animation_ir=None)
    assert "@media (prefers-reduced-motion: reduce)" in art["css"]


# ── TitleHero ────────────────────────────────────────────────────


def test_title_hero_gradient_variant_attribute():
    art = build_reveal_legacy(
        kit="TitleHero",
        props={"headline": "Acme", "variant": "gradient"},
        animation_ir=None,
    )
    assert 'data-variant="gradient"' in art["section"]


def test_title_hero_image_variant_includes_bleed_div():
    art = build_reveal_legacy(
        kit="TitleHero",
        props={"headline": "x", "imageUrl": "https://x/y.jpg", "variant": "image"},
        animation_ir=None,
    )
    assert 'class="rs-bleed"' in art["section"]
    assert "https://x/y.jpg" in art["section"]


def test_title_hero_omits_missing_props():
    art = build_reveal_legacy(
        kit="TitleHero", props={"headline": "Only headline"}, animation_ir=None
    )
    assert "Only headline" in art["section"]
    assert "rs-sub" not in art["section"]
    # No empty paragraph fabricated.
    assert "<p" not in art["section"] or "rs-sub" in art["section"]


# ── ChartBlock ───────────────────────────────────────────────────


def test_chart_block_emits_real_data_table():
    data = [{"month": "Jan", "rev": 10}, {"month": "Feb", "rev": 22}]
    art = build_reveal_legacy(
        kit="ChartBlock",
        props={
            "headline": "Revenue",
            "type": "bar",
            "data": data,
            "xKey": "month",
            "yKeys": ["rev"],
        },
        animation_ir=None,
    )
    assert "Jan" in art["section"]
    assert "Feb" in art["section"]
    assert "<table" in art["section"]
    assert 'data-chart-kind="bar"' in art["section"]


def test_chart_block_with_empty_data_shows_real_error():
    """No data → real error marker, never fabricated rows."""
    art = build_reveal_legacy(
        kit="ChartBlock",
        props={"headline": "X", "type": "line", "data": [], "xKey": "x", "yKeys": ["y"]},
        animation_ir=None,
    )
    assert 'data-error="empty_chart_data"' in art["section"]
    assert "<table" not in art["section"]


# ── ComparisonBlock ──────────────────────────────────────────────


def test_comparison_block_renders_yes_no_glyphs():
    art = build_reveal_legacy(
        kit="ComparisonBlock",
        props={
            "headline": "vs.",
            "columns": [{"label": "Us"}, {"label": "Them"}],
            "rows": [{"label": "Free", "values": [True, False]}],
        },
        animation_ir=None,
    )
    assert "rs-yes" in art["section"]
    assert "rs-no" in art["section"]


def test_comparison_block_renders_na_for_none():
    art = build_reveal_legacy(
        kit="ComparisonBlock",
        props={
            "headline": "vs.",
            "columns": [{"label": "A"}],
            "rows": [{"label": "x", "values": [None]}],
        },
        animation_ir=None,
    )
    assert "rs-na" in art["section"]


# ── DiagramBlock ─────────────────────────────────────────────────


def test_diagram_block_emits_svg_and_drops_dangling_edges():
    art = build_reveal_legacy(
        kit="DiagramBlock",
        props={
            "headline": "Graph",
            "nodes": [
                {"id": "a", "label": "A", "x": 0.2, "y": 0.5},
                {"id": "b", "label": "B", "x": 0.8, "y": 0.5},
            ],
            "edges": [
                {"from": "a", "to": "b", "label": "edge1"},
                {"from": "a", "to": "missing"},
            ],
        },
        animation_ir=None,
    )
    assert '<svg class="rs-diagram"' in art["section"]
    # Only 1 valid line element.
    line_count = len(re.findall(r"<line ", art["section"]))
    assert line_count == 1
    assert "edge1" in art["section"]


# ── TeamGrid ─────────────────────────────────────────────────────


def test_team_grid_external_links_have_rel_noopener():
    art = build_reveal_legacy(
        kit="TeamGrid",
        props={
            "headline": "Team",
            "members": [
                {"name": "Ada", "role": "CTO", "linkedinUrl": "https://linkedin.com/in/ada"},
            ],
        },
        animation_ir=None,
    )
    assert 'rel="noopener noreferrer"' in art["section"]
    assert 'target="_blank"' in art["section"]


# ── Standalone deck ──────────────────────────────────────────────


def test_render_standalone_reveal_deck_wraps_sections():
    a1 = build_reveal_legacy(kit="TitleHero", props={"headline": "Slide 1"}, animation_ir=None)
    a2 = build_reveal_legacy(kit="StatHero", props={"headline": "Slide 2"}, animation_ir=None)
    html = render_standalone_reveal_deck([a1, a2], deck_title="My Deck")
    assert html.startswith("<!DOCTYPE html>")
    assert "My Deck" in html
    assert "Slide 1" in html
    assert "Slide 2" in html
    assert 'class="reveal"' in html
    assert "Reveal.initialize" in html


def test_render_standalone_reveal_deck_inlines_design_system_css():
    a1 = build_reveal_legacy(kit="TitleHero", props={"headline": "x"}, animation_ir=None)
    css = ":root { --color-primary: #ff0000; }"
    html = render_standalone_reveal_deck([a1], design_system_css=css)
    assert css in html


def test_render_standalone_reveal_deck_rejects_non_list():
    with pytest.raises(TypeError):
        render_standalone_reveal_deck("not a list")  # type: ignore[arg-type]
