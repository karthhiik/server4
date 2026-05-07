"""
Phase 4.5 (Day 8) tests — quality_scorer real-data validation.

All tests use real WCAG-spec contrast math, real palette hex values,
real kit prop shapes. No fakes.
"""

from __future__ import annotations

import pytest

from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.quality_scorer import (
    _contrast_ratio,
    _hex_to_rgb,
    _relative_luminance,
    _total_char_count,
    attach_quality_scores,
    score_slide,
)
from app.services.v4.slide_compiler import compile_slides


# ── WCAG primitives ───────────────────────────────────────────────

def test_hex_to_rgb_handles_all_forms():
    assert _hex_to_rgb("#000000") == (0, 0, 0)
    assert _hex_to_rgb("#FFFFFF") == (255, 255, 255)
    assert _hex_to_rgb("#fff") == (255, 255, 255)  # 3-digit shorthand
    assert _hex_to_rgb("FFFFFF") == (255, 255, 255)  # no leading #
    assert _hex_to_rgb("0F62FE") == (15, 98, 254)
    assert _hex_to_rgb("not a color") is None
    assert _hex_to_rgb(None) is None  # type: ignore[arg-type]


def test_relative_luminance_matches_wcag_anchors():
    """Per WCAG 2.1: white = 1.0, black = 0.0."""
    assert _relative_luminance("#FFFFFF") == pytest.approx(1.0, abs=1e-6)
    assert _relative_luminance("#000000") == pytest.approx(0.0, abs=1e-6)
    # Pure red sRGB → 0.2126 (the R coefficient).
    assert _relative_luminance("#FF0000") == pytest.approx(0.2126, abs=1e-4)


def test_contrast_ratio_white_on_black_is_21():
    """WCAG: max contrast ratio is 21:1."""
    r = _contrast_ratio("#FFFFFF", "#000000")
    assert r == pytest.approx(21.0, abs=0.01)


def test_contrast_ratio_known_pair():
    """#0F62FE (IBM Blue 60) on white ≈ 4.94:1 — passes AA."""
    r = _contrast_ratio("#0F62FE", "#FFFFFF")
    assert r is not None
    assert 4.5 <= r < 5.5


# ── Per-dimension scoring ─────────────────────────────────────────

_GOOD_TOKENS = {
    "palette": {
        "primary": "#0043CE",          # IBM Blue 70 → ~7.4:1 on white (AAA)
        "accent": "#005D5D",           # IBM Teal 80 → ~9.3:1 on white (AAA)
        "background": "#FFFFFF",
        "surface": "#FFFFFF",
        "text_primary": "#161616",     # near-black on white  → ~16:1
        "text_secondary": "#525252",   # mid-grey on white    → ~7:1
        "success": "#24A148",
        "warning": "#F1C21B",
        "danger": "#DA1E28",
    },
}

_BAD_TOKENS = {
    "palette": {
        "primary": "#cccccc",
        "background": "#ffffff",
        "surface": "#f5f5f5",
        "text_primary": "#bbbbbb",     # light grey on light grey → ~1.4:1
        "text_secondary": "#cccccc",
    },
}


def test_contrast_high_ratio_scores_perfect():
    s = score_slide(
        kit="StatHero",
        props={"headline": "Hello", "stats": [{"value": "10x", "label": "Growth"}]},
        design_tokens=_GOOD_TOKENS,
    )
    c = s["dimensions"]["contrast"]
    assert c["passes_wcag_aa"] is True
    assert c["score"] >= 80
    assert c["ratio"] >= 4.5


def test_contrast_failing_palette_scores_low():
    s = score_slide(
        kit="StatHero",
        props={"headline": "Hello", "stats": [{"value": "10x"}]},
        design_tokens=_BAD_TOKENS,
    )
    c = s["dimensions"]["contrast"]
    assert c["passes_wcag_aa"] is False
    assert c["score"] < 50


def test_titlehero_image_variant_is_guaranteed_aa():
    """Image variant uses scrim; contrast hard-coded as guaranteed AA."""
    s = score_slide(
        kit="TitleHero",
        props={"headline": "H", "imageUrl": "https://x/y.jpg", "variant": "image"},
        design_tokens=_BAD_TOKENS,  # palette doesn't matter for image
    )
    assert s["dimensions"]["contrast"]["passes_wcag_aa"] is True
    assert s["dimensions"]["contrast"]["score"] == 100


def test_alignment_flags_chartblock_with_empty_data():
    s = score_slide(
        kit="ChartBlock",
        props={"headline": "Empty chart", "type": "bar", "data": [], "xKey": "x", "yKeys": ["y"]},
        design_tokens=_GOOD_TOKENS,
    )
    issues = s["dimensions"]["alignment"]["issues"]
    assert any("empty chart data" in i for i in issues)
    assert s["dimensions"]["alignment"]["score"] < 100


def test_alignment_flags_diagram_with_dangling_edge():
    s = score_slide(
        kit="DiagramBlock",
        props={
            "headline": "Bad diagram",
            "nodes": [
                {"id": "a", "label": "A", "x": 0.2, "y": 0.5},
                {"id": "b", "label": "B", "x": 0.8, "y": 0.5},
            ],
            "edges": [{"from": "a", "to": "missing"}],
        },
        design_tokens=_GOOD_TOKENS,
    )
    issues = s["dimensions"]["alignment"]["issues"]
    assert any("missing" in i for i in issues)


def test_alignment_flags_invalid_diagram_coords():
    s = score_slide(
        kit="DiagramBlock",
        props={
            "headline": "H",
            "nodes": [
                {"id": "a", "label": "A", "x": 1.5, "y": 0.5},  # x out of range
                {"id": "b", "label": "B", "x": 0.5, "y": 0.5},
            ],
            "edges": [],
        },
        design_tokens=_GOOD_TOKENS,
    )
    assert any("invalid x" in i for i in s["dimensions"]["alignment"]["issues"])


def test_alignment_clean_titlehero_has_no_issues():
    s = score_slide(
        kit="TitleHero",
        props={"headline": "Real Co.", "subheadline": "We build presentations.", "variant": "gradient"},
        design_tokens=_GOOD_TOKENS,
    )
    assert s["dimensions"]["alignment"]["issues"] == []
    assert s["dimensions"]["alignment"]["score"] == 100


def test_density_in_band_scores_perfect():
    # FeatureGrid target band = (80, 800)
    feats = [{"title": "Feature " + str(i), "description": "Some descriptive copy here."} for i in range(3)]
    s = score_slide(
        kit="FeatureGrid",
        props={"headline": "Capabilities", "features": feats, "columns": 3},
        design_tokens=_GOOD_TOKENS,
    )
    d = s["dimensions"]["density"]
    assert 80 <= d["char_count"] <= 800
    assert d["score"] == 100


def test_density_sparse_titlehero_penalised():
    # TitleHero target = (10, 250). Only 2 chars total.
    s = score_slide(
        kit="TitleHero",
        props={"headline": "Hi"},
        design_tokens=_GOOD_TOKENS,
    )
    d = s["dimensions"]["density"]
    assert d["char_count"] == 2
    assert d["score"] < 100
    assert "sparse" in d["details"]


def test_density_crowded_titlehero_penalised():
    huge_headline = "x " * 200  # 400 chars
    s = score_slide(
        kit="TitleHero",
        props={"headline": huge_headline},
        design_tokens=_GOOD_TOKENS,
    )
    d = s["dimensions"]["density"]
    assert d["char_count"] > 250
    assert d["score"] < 100
    assert "crowded" in d["details"]


def test_total_char_count_skips_urls_and_enums():
    chars = _total_char_count({
        "headline": "abc",          # 3
        "subheadline": "defg",      # 4
        "imageUrl": "https://very/long/url/should/not/count.jpg",
        "variant": "gradient",
        "type": "bar",
    })
    assert chars == 3 + 4


# ── Public API + integration ──────────────────────────────────────

def test_score_slide_returns_complete_shape():
    s = score_slide(
        kit="TitleHero",
        props={"headline": "Acme", "subheadline": "We make widgets.", "variant": "gradient"},
        design_tokens=_GOOD_TOKENS,
    )
    assert s["schema_version"] == 1
    assert isinstance(s["overall"], int)
    assert 0 <= s["overall"] <= 100
    assert s["passes_threshold"] == (s["overall"] >= 70)
    for dim in ("contrast", "alignment", "density"):
        assert dim in s["dimensions"]
        assert "score" in s["dimensions"][dim]


def test_attach_quality_scores_via_real_pipeline():
    slide = GeneratedSlide(
        index=1, intent="title", layout="title-hero",
        headline="Real Founders Co.",
        subheadline="From query to deck in 30 seconds.",
    )
    compiled = compile_slides(slides=[slide], image_urls={}, deck_title="Real Co.")
    attach_quality_scores(compiled, _GOOD_TOKENS)

    qs = compiled[0]["quality_score"]
    assert qs is not None
    assert qs["schema_version"] == 1
    assert 0 <= qs["overall"] <= 100
    assert qs["dimensions"]["contrast"]["passes_wcag_aa"] is True


def test_attach_quality_scores_handles_missing_tokens():
    slide = GeneratedSlide(
        index=1, intent="title", layout="title-hero",
        headline="Hi", subheadline="World",
    )
    compiled = compile_slides(slides=[slide], image_urls={}, deck_title="X")
    # Should not crash with empty tokens.
    attach_quality_scores(compiled, {})
    qs = compiled[0]["quality_score"]
    assert qs is not None
    assert qs["dimensions"]["contrast"]["passes_wcag_aa"] is False


def test_unknown_kit_emits_alignment_issue_not_crash():
    s = score_slide(kit="MysteryKit", props={"headline": "X"}, design_tokens=_GOOD_TOKENS)
    assert any("unknown kit" in i for i in s["dimensions"]["alignment"]["issues"])
    # Density falls back to neutral 50 for unknown kits.
    assert s["dimensions"]["density"]["score"] == 50


def test_score_is_deterministic():
    args = {
        "kit": "StatHero",
        "props": {"headline": "H", "stats": [{"value": "10x", "label": "Growth"}]},
        "design_tokens": _GOOD_TOKENS,
    }
    a = score_slide(**args)
    b = score_slide(**args)
    assert a == b


def test_passes_threshold_is_overall_gte_70():
    # Build a high-quality slide.
    s = score_slide(
        kit="StatHero",
        props={
            "headline": "Strong traction across all metrics",
            "subheadline": "Q4 2025 results show consistent growth",
            "stats": [
                {"value": "10x", "label": "ARR growth"},
                {"value": "142%", "label": "Net retention"},
                {"value": "$4.2M", "label": "Q4 ARR"},
            ],
        },
        design_tokens=_GOOD_TOKENS,
    )
    assert s["overall"] >= 70
    assert s["passes_threshold"] is True
