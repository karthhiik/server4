"""
Phase 5 (Day 9-10) tests — engine_transformer.

Real props matching the React kit shapes; real AnimationIR built by
the Phase 3 builder; verifies layer composition, token references,
fingerprint determinism, unknown-kit safety, and IR linkage.
"""

from __future__ import annotations

import pytest

from app.services.v4.animation_ir import build_animation_ir
from app.services.v4.engine_transformer import build_engine


# Real-shape AnimationIR (matches the Phase 3 schema).
def _ir_for(intent: str, kit: str):
    plan = {
        "intent": intent,
        "kit": kit,
        "entry": [
            {"target": "headline", "effect": "fade-up", "delay_ms": 100, "duration_ms": 400, "easing": "ease-out"},
            {"target": "subheadline", "effect": "fade-up", "delay_ms": 200, "duration_ms": 400, "easing": "ease-out"},
        ],
    }
    return build_animation_ir(plan)


# ── Smoke / public contract ──────────────────────────────────────


def test_unknown_kit_emits_error_layer_not_fabricated():
    art = build_engine(kit="MysteryKit", props={"headline": "x"}, animation_ir=None)
    assert art["kit"] == "MysteryKit"
    layers = art["layers"]
    assert len(layers) == 1
    assert layers[0]["type"] == "error"
    assert layers[0]["code"] == "unknown_kit"


def test_artifact_has_expected_top_level_keys():
    art = build_engine(kit="TitleHero", props={"headline": "Hi"}, animation_ir=None)
    for k in ("schema_version", "kit", "viewport", "background", "layers", "fingerprint"):
        assert k in art
    assert art["schema_version"] == 1
    assert art["viewport"] == {"w": 1280, "h": 720, "margin": 64}
    assert len(art["fingerprint"]) == 12


def test_fingerprint_is_deterministic():
    args = dict(
        kit="StatHero",
        props={"headline": "Growth", "stats": [{"value": "10x", "label": "ARR"}]},
        animation_ir=None,
    )
    a = build_engine(**args)
    b = build_engine(**args)
    assert a["fingerprint"] == b["fingerprint"]


def test_fingerprint_changes_with_content():
    a = build_engine(kit="TitleHero", props={"headline": "A"}, animation_ir=None)
    b = build_engine(kit="TitleHero", props={"headline": "B"}, animation_ir=None)
    assert a["fingerprint"] != b["fingerprint"]


def test_normalized_coords_in_unit_range():
    """All layer coords must be normalized to [0, 1]."""
    art = build_engine(
        kit="StatHero",
        props={
            "headline": "H",
            "stats": [{"value": "1", "label": "a"}, {"value": "2", "label": "b"}, {"value": "3", "label": "c"}],
        },
        animation_ir=None,
    )
    for layer in art["layers"]:
        for axis in ("x", "y", "w", "h"):
            if axis in layer:
                v = layer[axis]
                assert 0.0 <= v <= 1.0, f"{axis}={v} out of [0,1] in {layer.get('id')}"


# ── TitleHero ────────────────────────────────────────────────────


def test_title_hero_gradient_uses_token_stops():
    art = build_engine(
        kit="TitleHero",
        props={"headline": "Acme", "subheadline": "x", "variant": "gradient"},
        animation_ir=None,
    )
    bg = art["background"]
    assert bg["kind"] == "gradient"
    tokens = [s.get("color_token") for s in bg["stops"]]
    assert tokens == ["primary", "accent"]


def test_title_hero_image_variant_emits_scrim():
    art = build_engine(
        kit="TitleHero",
        props={"headline": "Hi", "imageUrl": "https://x/y.jpg", "variant": "image"},
        animation_ir=None,
    )
    bg = art["background"]
    assert bg["kind"] == "scrim_image"
    assert bg["url"] == "https://x/y.jpg"


def test_title_hero_omits_missing_props():
    """Missing prop → missing layer (no default invented)."""
    art = build_engine(kit="TitleHero", props={"headline": "Only headline"}, animation_ir=None)
    layer_ids = {layer["id"] for layer in art["layers"]}
    assert "headline" in layer_ids
    assert "subheadline" not in layer_ids
    assert "eyebrow" not in layer_ids


def test_title_hero_attaches_anim_id_from_ir():
    ir = _ir_for("title", "TitleHero")
    art = build_engine(
        kit="TitleHero",
        props={"headline": "H", "subheadline": "S", "variant": "gradient"},
        animation_ir=ir,
    )
    headline_layer = next(layer for layer in art["layers"] if layer["id"] == "headline")
    assert headline_layer["anim_id"].startswith("ir-anim-")


# ── StatHero ─────────────────────────────────────────────────────


def test_stat_hero_emits_one_block_per_stat():
    stats = [
        {"value": "10x", "label": "ARR growth"},
        {"value": "$4.2M", "label": "Q4 ARR", "sublabel": "+85% YoY"},
        {"value": "142%", "label": "NRR"},
    ]
    art = build_engine(
        kit="StatHero",
        props={"headline": "Traction", "stats": stats},
        animation_ir=None,
    )
    ids = [layer["id"] for layer in art["layers"]]
    for i in range(3):
        assert f"stat-{i}-value" in ids
        assert f"stat-{i}-label" in ids
    assert "stat-1-sub" in ids  # only the second has sublabel
    assert "stat-2-sub" not in ids


def test_stat_hero_caps_at_4_stats():
    stats = [{"value": str(i), "label": f"L{i}"} for i in range(7)]
    art = build_engine(kit="StatHero", props={"stats": stats}, animation_ir=None)
    ids = [layer["id"] for layer in art["layers"]]
    assert "stat-3-value" in ids
    assert "stat-4-value" not in ids


# ── ChartBlock ───────────────────────────────────────────────────


def test_chart_block_carries_data_and_keys():
    data = [{"month": "Jan", "rev": 10}, {"month": "Feb", "rev": 22}]
    art = build_engine(
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
    chart = next(layer for layer in art["layers"] if layer["type"] == "chart")
    assert chart["kind"] == "bar"
    assert chart["data"] == data
    assert chart["x_key"] == "month"
    assert chart["y_keys"] == ["rev"]


def test_chart_block_with_empty_data_still_emits_chart_layer():
    """Empty data is real (the source had none) — emit the layer anyway."""
    art = build_engine(
        kit="ChartBlock",
        props={"headline": "X", "type": "line", "data": [], "xKey": "x", "yKeys": ["y"]},
        animation_ir=None,
    )
    chart = next(layer for layer in art["layers"] if layer["type"] == "chart")
    assert chart["data"] == []


# ── ComparisonBlock ──────────────────────────────────────────────


def test_comparison_block_renders_cells_with_token_colors():
    art = build_engine(
        kit="ComparisonBlock",
        props={
            "headline": "vs.",
            "columns": [{"label": "Us"}, {"label": "Them"}],
            "rows": [
                {"label": "Free tier", "values": [True, False]},
                {"label": "Speed", "values": ["Fast", "Slow"]},
                {"label": "Notes", "values": [None, "n/a"]},
            ],
        },
        animation_ir=None,
    )
    by_id = {layer["id"]: layer for layer in art["layers"] if layer.get("type") == "text"}
    assert by_id["cell-0-0"]["text"] == "✓"
    assert by_id["cell-0-0"]["color_token"] == "success"
    assert by_id["cell-0-1"]["text"] == "✕"
    assert by_id["cell-0-1"]["color_token"] == "danger"
    assert by_id["cell-2-0"]["text"] == "—"
    assert by_id["cell-2-0"]["color_token"] == "text_muted"
    assert by_id["cell-1-0"]["text"] == "Fast"


# ── DiagramBlock ─────────────────────────────────────────────────


def test_diagram_block_drops_dangling_edges():
    art = build_engine(
        kit="DiagramBlock",
        props={
            "headline": "Graph",
            "nodes": [
                {"id": "a", "label": "A", "x": 0.2, "y": 0.5},
                {"id": "b", "label": "B", "x": 0.8, "y": 0.5},
            ],
            "edges": [
                {"from": "a", "to": "b", "label": "ok"},
                {"from": "a", "to": "missing"},
            ],
        },
        animation_ir=None,
    )
    edges = [layer for layer in art["layers"] if layer["type"] == "edge"]
    assert len(edges) == 1
    assert edges[0]["label"] == "ok"


def test_diagram_block_clamps_invalid_node_coords():
    art = build_engine(
        kit="DiagramBlock",
        props={
            "headline": "X",
            "nodes": [
                {"id": "a", "label": "A", "x": 1.5, "y": 0.5},
                {"id": "b", "label": "B", "x": 0.5, "y": -0.2},
            ],
            "edges": [],
        },
        animation_ir=None,
    )
    # Node shapes' x/y/w/h are still in [0,1] post-clamp.
    for layer in art["layers"]:
        if layer.get("type") == "shape":
            assert 0.0 <= layer["x"] <= 1.0
            assert 0.0 <= layer["y"] <= 1.0


# ── FullBleedImage ───────────────────────────────────────────────


def test_full_bleed_image_uses_image_background_when_url_present():
    art = build_engine(
        kit="FullBleedImage",
        props={"imageUrl": "https://x/y.jpg", "headline": "H", "align": "bottom-left"},
        animation_ir=None,
    )
    assert art["background"]["kind"] == "scrim_image"


def test_full_bleed_image_falls_back_to_solid_when_url_missing():
    art = build_engine(
        kit="FullBleedImage", props={"headline": "H"}, animation_ir=None,
    )
    assert art["background"]["kind"] == "solid"


# ── QuoteBlock ───────────────────────────────────────────────────


def test_quote_block_accent_variant_uses_accent_background():
    art = build_engine(
        kit="QuoteBlock",
        props={"quote": "Great.", "attribution": "Jane", "variant": "accent"},
        animation_ir=None,
    )
    assert art["background"] == {"kind": "solid", "color_token": "accent"}


# ── FeatureGrid / TeamGrid ───────────────────────────────────────


def test_feature_grid_handles_default_columns():
    art = build_engine(
        kit="FeatureGrid",
        props={
            "headline": "Why",
            "features": [
                {"icon": "zap", "title": "Fast", "description": "Sub-second."},
                {"icon": "shield", "title": "Safe", "description": "Audited."},
                {"icon": "rocket", "title": "Real", "description": "No fakes."},
            ],
        },
        animation_ir=None,
    )
    icons = [layer for layer in art["layers"] if layer.get("type") == "icon"]
    assert len(icons) == 3
    assert {layer["name"] for layer in icons} == {"zap", "shield", "rocket"}


def test_team_grid_emits_avatar_when_url_present():
    art = build_engine(
        kit="TeamGrid",
        props={
            "headline": "Team",
            "members": [
                {"name": "Ada", "role": "CTO", "avatarUrl": "https://x/a.jpg"},
                {"name": "Linus", "role": "Eng"},
            ],
        },
        animation_ir=None,
    )
    images = [layer for layer in art["layers"] if layer.get("type") == "image"]
    assert len(images) == 1
    assert images[0]["url"] == "https://x/a.jpg"


# ── TimelineBlock ────────────────────────────────────────────────


def test_timeline_block_horizontal_emits_axis_and_dots():
    art = build_engine(
        kit="TimelineBlock",
        props={
            "headline": "Roadmap",
            "milestones": [
                {"date": "2024", "label": "Seed"},
                {"date": "2025", "label": "Series A"},
                {"date": "2026", "label": "Profit"},
            ],
        },
        animation_ir=None,
    )
    has_axis = any(layer.get("id") == "timeline-axis" for layer in art["layers"])
    dots = [layer for layer in art["layers"] if layer.get("kind") == "circle"]
    assert has_axis
    assert len(dots) == 3
