"""
Phase 4 (Day 6-7) tests — html_transformer real-data integration.

These tests exercise the transformer against REAL data shapes:

  * Real GeneratedSlide → real compile_slides() → real artifacts.html_css_js.
  * Real DesignSystem snapshot inlined via attach_design_system_to_html_artifact.
  * Real AnimationIR consumed by per-element class hooks.

No fakes / no stubs. If a test fails, it means either the transformer
or one of the upstream phases regressed.
"""

from __future__ import annotations

import hashlib
import re

import pytest

from app.services.v4.animation_ir import build_animation_ir
from app.services.v4.design_system import (
    attach_design_system_to_html_artifact,
    build_design_system,
)
from app.services.v4.html_transformer import (
    build_html_css_js,
    render_standalone_document,
)
from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.slide_compiler import compile_slides


# ── Fixtures ───────────────────────────────────────────────────────

_REAL_DESIGN_TOKENS = {
    "palette": {
        "primary": "#0F62FE",
        "secondary": "#393939",
        "accent": "#08BDBA",
        "background": "#FFFFFF",
        "surface": "#F4F4F4",
        "text_primary": "#161616",
        "text_secondary": "#525252",
        "text_muted": "#8D8D8D",
        "success": "#24A148",
        "warning": "#F1C21B",
        "danger": "#DA1E28",
        "chart": ["#0F62FE", "#08BDBA", "#FF7EB6", "#33B1FF", "#A56EFF", "#FF6F00", "#42BE65"],
    },
    "fonts": {"heading": "Inter", "body": "Inter", "mono": "ui-monospace"},
    "scale": {"display": 64, "h1": 48, "h2": 36, "h3": 24, "body": 16, "caption": 12},
    "spacing": {"slide_margin_in": 0.6, "gap_in": 0.2, "section_gap_in": 0.5},
    "weights": {"heading": 700, "body": 400},
    "density": "balanced",
    "line_height": 1.5,
    "letter_spacing_em": 0.0,
    "provided_by": "test",
}


def _real_animation_ir():
    plan = {
        "entry": [
            {"target": "headline", "effect": "fade-up", "duration_ms": 500, "delay_ms": 100},
            {"target": "subheadline", "effect": "fade-up", "duration_ms": 500, "delay_ms": 200},
            {
                "target": "stats",
                "effect": "fade-up",
                "duration_ms": 400,
                "delay_ms": 300,
                "stagger_ms": 80,
                "stagger_count": 3,
            },
        ],
        "transition": "slide",
    }
    return build_animation_ir(plan)


# ── Per-kit tests ──────────────────────────────────────────────────

@pytest.mark.parametrize(
    "kit, props",
    [
        (
            "TitleHero",
            {
                "headline": "10x Revenue Growth",
                "subheadline": "From $1M to $10M ARR in 18 months",
                "eyebrow": "Series A",
                "footer": "Q1 2026",
                "variant": "gradient",
            },
        ),
        (
            "StatHero",
            {
                "eyebrow": "Traction",
                "headline": "Massive operational wins",
                "subheadline": "Across all customer segments",
                "stats": [
                    {"value": "87%", "label": "reduction in manual review", "delta": "+12 YoY", "trend": "up"},
                    {"value": "$4.2M", "label": "ARR closed Q4", "trend": "up"},
                    {"value": "3.5x", "label": "faster onboarding"},
                ],
                "align": "left",
            },
        ),
        (
            "ChartBlock",
            {
                "headline": "ARR Growth",
                "subheadline": "Quarterly recurring revenue",
                "type": "bar",
                "data": [
                    {"q": "Q1", "arr": 1.2, "newLogos": 12},
                    {"q": "Q2", "arr": 2.4, "newLogos": 18},
                    {"q": "Q3", "arr": 4.1, "newLogos": 27},
                    {"q": "Q4", "arr": 6.8, "newLogos": 41},
                ],
                "xKey": "q",
                "yKeys": ["arr", "newLogos"],
                "seriesLabels": {"arr": "ARR ($M)", "newLogos": "New Logos"},
                "source": "Source: company filings, 2025",
            },
        ),
        (
            "ChartBlock",
            {
                "headline": "Revenue Mix",
                "type": "pie",
                "data": [
                    {"name": "Enterprise", "value": 65},
                    {"name": "Mid-market", "value": 25},
                    {"name": "SMB", "value": 10},
                ],
                "valueKey": "value",
                "nameKey": "name",
            },
        ),
        (
            "ChartBlock",
            {
                "headline": "Monthly Active Users",
                "type": "line",
                "data": [
                    {"m": "Jan", "users": 1200},
                    {"m": "Feb", "users": 1800},
                    {"m": "Mar", "users": 2900},
                    {"m": "Apr", "users": 4100},
                ],
                "xKey": "m",
                "yKeys": ["users"],
            },
        ),
        (
            "TimelineBlock",
            {
                "headline": "Roadmap",
                "subheadline": "Path to GA",
                "milestones": [
                    {"date": "Q1 2026", "title": "Seed close", "description": "$2M raised", "done": True},
                    {"date": "Q2 2026", "title": "Beta launch"},
                    {"date": "Q3 2026", "title": "Series A"},
                    {"date": "Q4 2026", "title": "GA release", "description": "Public availability"},
                ],
            },
        ),
        (
            "ComparisonBlock",
            {
                "headline": "Why us vs. legacy tools",
                "columns": [
                    {"name": "Us", "highlight": True, "tagline": "AI-native"},
                    {"name": "Tool A"},
                    {"name": "Tool B"},
                ],
                "rows": [
                    {"feature": "Real-time generation", "values": {"Us": True, "Tool A": False, "Tool B": "partial"}},
                    {"feature": "Custom themes", "values": {"Us": True, "Tool A": True, "Tool B": False}},
                    {"feature": "Pricing", "values": {"Us": "$29/mo", "Tool A": "$99/mo", "Tool B": "$149/mo"}},
                ],
            },
        ),
        (
            "FeatureGrid",
            {
                "headline": "Core capabilities",
                "subheadline": "Everything teams need to ship a deck",
                "features": [
                    {"icon": "Zap", "title": "Real-time generation", "description": "Live as you type."},
                    {"icon": "Target", "title": "Pitch-deck native", "description": "YC patterns built in."},
                    {"icon": "Shield", "title": "Brand safe", "description": "Locked design system."},
                ],
                "columns": 3,
            },
        ),
        (
            "TeamGrid",
            {
                "headline": "Founding team",
                "members": [
                    {"name": "Ada Lovelace", "role": "CEO", "bio": "Ex-Stripe."},
                    {"name": "Alan Turing", "role": "CTO", "bio": "Ex-DeepMind.", "linkedInUrl": "https://linkedin.com/in/turing"},
                    {"name": "Grace Hopper", "role": "VP Eng"},
                ],
                "columns": 3,
            },
        ),
        (
            "QuoteBlock",
            {
                "quote": "This is the deck tool we've been waiting for.",
                "attribution": "Sam Altman",
                "role": "OpenAI",
                "variant": "default",
            },
        ),
        (
            "FullBleedImage",
            {
                "imageUrl": "https://example.com/img.jpg",
                "headline": "Built for speed",
                "subheadline": "From query to deck in 30 seconds.",
                "overlay": "scrim-bottom",
                "align": "bottom-left",
            },
        ),
        (
            "DiagramBlock",
            {
                "headline": "How it works",
                "nodes": [
                    {"id": "a", "label": "User query", "x": 0.1, "y": 0.5, "variant": "secondary"},
                    {"id": "b", "label": "AI pipeline", "x": 0.5, "y": 0.5, "variant": "primary"},
                    {"id": "c", "label": "Slide deck", "x": 0.9, "y": 0.5, "variant": "secondary"},
                ],
                "edges": [
                    {"from": "a", "to": "b", "label": "Skeleton"},
                    {"from": "b", "to": "c", "style": "dashed"},
                ],
            },
        ),
    ],
)
def test_every_kit_renders(kit, props):
    ir = _real_animation_ir()
    artifact = build_html_css_js(
        kit=kit, props=props, animation_ir=ir, design_system=None, slide_id="s1", deck_title="Test Deck"
    )

    # Basic shape.
    assert set(artifact.keys()) >= {
        "html", "css", "js", "head_meta", "fingerprint", "schema_version"
    }
    assert artifact["schema_version"] == 1

    html, css = artifact["html"], artifact["css"]
    assert isinstance(html, str) and html.startswith("<section ")
    assert html.endswith("</section>")
    assert f'data-kit="{kit}"' in html

    # CSS includes BASE + kit + IR.
    assert ".slide" in css
    assert "@keyframes" in css  # IR's keyframes for entry animations.

    # Determinism.
    artifact2 = build_html_css_js(
        kit=kit, props=props, animation_ir=ir, design_system=None, slide_id="s1", deck_title="Test Deck"
    )
    assert artifact2["fingerprint"] == artifact["fingerprint"]
    assert artifact2["html"] == artifact["html"]


def test_unknown_kit_emits_honest_error_block():
    artifact = build_html_css_js(
        kit="MysteryKit", props={}, animation_ir={}, design_system=None
    )
    assert 'data-kit="MysteryKit"' in artifact["html"]
    assert 'class="slide-error"' in artifact["html"]
    assert "Unknown kit component" in artifact["html"]
    # Must NOT silently fall back to a different kit.
    assert "TitleHero" not in artifact["html"]
    assert "FeatureGrid" not in artifact["html"]


def test_html_escapes_xss_payload():
    payload = '</style><script>alert("xss")</script>'
    artifact = build_html_css_js(
        kit="TitleHero",
        props={"headline": payload, "subheadline": payload},
        animation_ir={},
    )
    # Raw script tag must NOT appear unescaped in the html.
    assert "<script>alert" not in artifact["html"]
    # But the escaped version must be present.
    assert "&lt;script&gt;" in artifact["html"]


def test_chart_renders_real_svg_geometry():
    props = {
        "headline": "Revenue", "type": "bar",
        "data": [{"q": "Q1", "v": 10}, {"q": "Q2", "v": 20}, {"q": "Q3", "v": 30}],
        "xKey": "q", "yKeys": ["v"],
    }
    artifact = build_html_css_js(kit="ChartBlock", props=props, animation_ir={})
    html = artifact["html"]
    # Must have a real <svg> with rect bars (3 data points → 3 rects).
    assert html.count("<rect") >= 3
    assert "<svg" in html
    # Y-axis labels include formatted values.
    assert ">30<" in html or "30.0" in html or ">30.00<" in html


def test_chart_pie_renders_paths():
    props = {
        "headline": "Mix", "type": "pie",
        "data": [{"k": "A", "v": 40}, {"k": "B", "v": 60}],
        "valueKey": "v", "nameKey": "k",
    }
    artifact = build_html_css_js(kit="ChartBlock", props=props, animation_ir={})
    # Two pie slices → two <path d="M ..."> elements with arcs.
    assert artifact["html"].count("<path") >= 2
    assert " A " in artifact["html"]  # SVG arc command.


def test_chart_empty_data_returns_no_data_message():
    props = {"headline": "Empty", "type": "bar", "data": [], "xKey": "x", "yKeys": ["y"]}
    artifact = build_html_css_js(kit="ChartBlock", props=props, animation_ir={})
    assert "No data" in artifact["html"]


def test_animation_ir_classes_attached_to_targets():
    ir = _real_animation_ir()
    artifact = build_html_css_js(
        kit="StatHero",
        props={
            "headline": "H", "subheadline": "S",
            "stats": [{"value": "1", "label": "L"}, {"value": "2", "label": "L"}, {"value": "3", "label": "L"}],
        },
        animation_ir=ir,
    )
    html, css = artifact["html"], artifact["css"]
    # Every IR entry id must produce both a class hook in the HTML and
    # a matching CSS rule.
    for entry in ir["entries"]:
        cls = f"ir-anim-{entry['id']}"
        assert cls in html, f"missing class hook for {entry['target']}"
        assert f".{cls}" in css, f"missing CSS rule for {entry['target']}"


def test_real_slide_compile_populates_html_artifact():
    """End-to-end: a real GeneratedSlide → compile_slides → html_css_js artifact."""
    slide = GeneratedSlide(
        index=1,
        intent="traction",
        layout="stat-hero",
        headline="10x Revenue Growth",
        subheadline="ARR jumped from $1M to $10M",
        body="Highlight the 10x metric",
        bullets=[],
        stat_blocks=[
            {"value": "10x", "label": "ARR growth"},
            {"value": "142%", "label": "Net retention"},
        ],
    )
    compiled = compile_slides(slides=[slide], image_urls={}, deck_title="Test")
    assert len(compiled) == 1
    artifact = compiled[0]["artifacts"]["html_css_js"]
    assert artifact is not None
    assert "<section" in artifact["html"]
    assert artifact["fingerprint"]
    # Animation IR class hooks present.
    assert "ir-anim-" in artifact["html"]


def test_design_system_inlining_attaches_tokens():
    slide = GeneratedSlide(
        index=1, intent="title", layout="title-hero",
        headline="Hello", subheadline="World",
    )
    compiled = compile_slides(slides=[slide], image_urls={}, deck_title="Hello")
    snapshot = build_design_system(_REAL_DESIGN_TOKENS, deck_title="Hello")
    fp_before = compiled[0]["artifacts"]["html_css_js"]["fingerprint"]

    attach_design_system_to_html_artifact(compiled, snapshot)

    css = compiled[0]["artifacts"]["html_css_js"]["css"]
    # DS sentinel comment present at top.
    assert f"version={snapshot['version']}" in css
    # Real token from the palette must resolve via :root.
    assert "--color-primary: #0F62FE" in css
    assert ":root" in css
    # Fingerprint must change since CSS changed.
    fp_after = compiled[0]["artifacts"]["html_css_js"]["fingerprint"]
    assert fp_before != fp_after


def test_design_system_inlining_is_idempotent():
    slide = GeneratedSlide(
        index=1, intent="title", layout="title-hero", headline="H", subheadline="S"
    )
    compiled = compile_slides(slides=[slide], image_urls={}, deck_title="H")
    snapshot = build_design_system(_REAL_DESIGN_TOKENS, deck_title="H")

    attach_design_system_to_html_artifact(compiled, snapshot)
    css_first = compiled[0]["artifacts"]["html_css_js"]["css"]
    fp_first = compiled[0]["artifacts"]["html_css_js"]["fingerprint"]

    attach_design_system_to_html_artifact(compiled, snapshot)  # second pass
    css_second = compiled[0]["artifacts"]["html_css_js"]["css"]
    fp_second = compiled[0]["artifacts"]["html_css_js"]["fingerprint"]

    assert css_first == css_second
    assert fp_first == fp_second
    # No duplicate :root block.
    assert css_second.count(":root") == 1


def test_render_standalone_document_is_complete_html():
    artifact = build_html_css_js(
        kit="TitleHero",
        props={"headline": "Hi", "subheadline": "World", "variant": "gradient"},
        animation_ir=_real_animation_ir(),
    )
    doc = render_standalone_document(artifact)
    assert doc.startswith("<!DOCTYPE html>")
    assert "<html" in doc and "</html>" in doc
    assert "<title>Hi</title>" in doc
    assert "<style>" in doc
    assert artifact["html"] in doc


def test_fingerprint_changes_with_props():
    a = build_html_css_js(kit="TitleHero", props={"headline": "A"}, animation_ir={})
    b = build_html_css_js(kit="TitleHero", props={"headline": "B"}, animation_ir={})
    assert a["fingerprint"] != b["fingerprint"]


def test_defensive_against_missing_props():
    """No prop should ever raise. Missing optional fields → omitted nodes."""
    artifact = build_html_css_js(kit="TitleHero", props={"headline": "Only headline"}, animation_ir={})
    assert "Only headline" in artifact["html"]
    # No subheadline / footer / eyebrow tags emitted.
    assert "slide-footer" not in artifact["html"]
    assert "chip-subtle" not in artifact["html"]


def test_defensive_against_garbage_props():
    artifact = build_html_css_js(kit="StatHero", props={"stats": [None, "bad", {"value": "1", "label": "ok"}]}, animation_ir={})
    # Only the dict-shaped stat should render.
    assert artifact["html"].count("stat-cell") == 1
    assert ">1<" in artifact["html"]
