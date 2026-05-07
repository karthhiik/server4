"""Phase 8 — thin-slice edit ops unit tests.

Cover:
* Path parsing (dotted, numeric segments, rejection of empties)
* Resolve-existing path walks
* Type compatibility check (string↔string ok; string↔int rejected)
* Size caps
* End-to-end `apply_slice_ops` — replace headline, replace nested
  stat value, fingerprint changes, artifact_version bumps, quality
  re-scored, no-op detection, error rollback (no partial mutations)
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.services.v4 import slice_editor as se


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


def _make_compiled_slide(*, kit: str, props: dict[str, Any], index: int = 0):
    """Mirror the test_hot_swap helper but importable here."""
    from app.services.v4.animation_ir import build_animation_ir
    from app.services.v4.engine_transformer import build_engine
    from app.services.v4.html_transformer import build_html_css_js
    from app.services.v4.reveal_legacy_transformer import build_reveal_legacy
    from app.services.v4.slide_compiler import _render_jsx

    plan = {"intent": "title", "kit": kit, "entry": []}
    ir = build_animation_ir(plan)
    jsx = _render_jsx(kit=kit, props=props)
    return {
        "slide_id": f"slide-{index:03d}",
        "slide_index": index,
        "jsx_source": jsx,
        "kit_component": kit,
        "animation_ir": ir,
        "artifact_version": 1,
        "artifacts": {
            "kit_jsx": {
                "source": jsx,
                "kit_component": kit,
                "props_json": json.loads(json.dumps(props)),
                "fingerprint": "originalfp00",
            },
            "html_css_js": build_html_css_js(
                kit=kit, props=props, animation_ir=ir, slide_id=f"slide-{index:03d}"
            ),
            "engine": build_engine(
                kit=kit, props=props, animation_ir=ir, slide_id=f"slide-{index:03d}"
            ),
            "reveal_legacy": build_reveal_legacy(
                kit=kit, props=props, animation_ir=ir, slide_id=f"slide-{index:03d}"
            ),
        },
        "quality_score": {"overall": 80, "passes_threshold": True, "dimensions": {}},
    }


# ── Path parsing ─────────────────────────────────────────────────


def test_parse_path_simple_and_nested():
    assert se._parse_path("headline") == ["headline"]
    assert se._parse_path("stats.0.value") == ["stats", 0, "value"]
    assert se._parse_path("a.b.c") == ["a", "b", "c"]


def test_parse_path_rejects_empty_and_empty_segment():
    with pytest.raises(se.SliceEditError):
        se._parse_path("")
    with pytest.raises(se.SliceEditError):
        se._parse_path("a..b")


def test_resolve_existing_walks_lists_and_dicts():
    root = {"stats": [{"value": "$2B"}, {"value": "$3B"}]}
    assert se._resolve_existing(root, ["stats", 1, "value"]) == "$3B"


def test_resolve_existing_rejects_unknown_key():
    with pytest.raises(se.SliceEditError) as ei:
        se._resolve_existing({"a": 1}, ["b"])
    assert ei.value.code == "unknown_key"


def test_resolve_existing_rejects_out_of_range():
    with pytest.raises(se.SliceEditError) as ei:
        se._resolve_existing({"xs": [1, 2]}, ["xs", 5])
    assert ei.value.code == "index_out_of_range"


# ── Type compat ──────────────────────────────────────────────────


def test_type_compat_same_type_ok():
    se._check_value_compat("old", "new", "headline")
    se._check_value_compat(1, 2, "n")
    se._check_value_compat([1, 2], [3], "xs")


def test_type_compat_string_to_int_rejected():
    with pytest.raises(se.SliceEditError) as ei:
        se._check_value_compat("hi", 5, "headline")
    assert ei.value.code == "type_mismatch"


def test_type_compat_string_to_null_allowed():
    # "Clear field" UX
    se._check_value_compat("hello", None, "subheadline")


# ── Size caps ────────────────────────────────────────────────────


def test_size_cap_string():
    with pytest.raises(se.SliceEditError):
        se._check_size_cap("x" * (se._MAX_STRING_LEN + 1), "body")


def test_size_cap_list():
    with pytest.raises(se.SliceEditError):
        se._check_size_cap(list(range(se._MAX_LIST_LEN + 1)), "bullets")


# ── End-to-end ───────────────────────────────────────────────────


def test_replace_headline_bumps_version_and_fingerprint():
    slide = _make_compiled_slide(
        kit="TitleHero",
        props={"headline": "Old", "subheadline": "Sub", "variant": "gradient"},
    )
    fp_before = slide["artifacts"]["kit_jsx"]["fingerprint"]
    src_before = slide["artifacts"]["kit_jsx"]["source"]
    res = se.apply_slice_ops(
        slide=slide,
        ops=[{"path": "headline", "value": "New title"}],
        design_tokens=_AAA_TOKENS,
    )
    assert res["fields_changed"] == ["headline"]
    assert slide["artifacts"]["kit_jsx"]["props_json"]["headline"] == "New title"
    # Fingerprint and JSX source must change.
    assert slide["artifacts"]["kit_jsx"]["fingerprint"] != fp_before
    assert slide["artifacts"]["kit_jsx"]["source"] != src_before
    # jsx_source legacy mirror also updated.
    assert slide["jsx_source"] == slide["artifacts"]["kit_jsx"]["source"]
    # Artifact version bumps.
    assert slide["artifact_version"] == 2
    # Quality scored fresh.
    assert isinstance(res["quality_score"], dict)
    assert "overall" in res["quality_score"]
    assert res["noop"] is False


def test_replace_nested_stat_value():
    slide = _make_compiled_slide(
        kit="StatHero",
        props={
            "headline": "Market",
            "stats": [
                {"value": "$2B", "label": "TAM"},
                {"value": "20%", "label": "CAGR"},
            ],
            "variant": "split",
        },
    )
    res = se.apply_slice_ops(
        slide=slide,
        ops=[{"path": "stats.0.value", "value": "$2.4B"}],
        design_tokens=_AAA_TOKENS,
    )
    assert res["fields_changed"] == ["stats.0.value"]
    assert slide["artifacts"]["kit_jsx"]["props_json"]["stats"][0]["value"] == "$2.4B"
    # Other stat untouched.
    assert slide["artifacts"]["kit_jsx"]["props_json"]["stats"][1]["value"] == "20%"


def test_insert_stat_item_rebuilds_artifact():
    slide = _make_compiled_slide(
        kit="StatHero",
        props={
            "headline": "Market",
            "stats": [{"value": "$2B", "label": "TAM"}],
        },
    )
    res = se.apply_slice_ops(
        slide=slide,
        ops=[{"op": "insert", "path": "stats.1", "value": {"value": "20%", "label": "CAGR"}}],
        design_tokens=_AAA_TOKENS,
    )
    props = slide["artifacts"]["kit_jsx"]["props_json"]
    assert res["fields_changed"] == ["stats"]
    assert props["stats"][1] == {"value": "20%", "label": "CAGR"}
    assert slide["artifact_version"] == 2


def test_remove_list_item_and_optional_leaf_are_honest_deletions():
    slide = _make_compiled_slide(
        kit="StatHero",
        props={
            "headline": "Market",
            "subheadline": "Original sub",
            "stats": [
                {"value": "$2B", "label": "TAM"},
                {"value": "20%", "label": "CAGR"},
            ],
        },
    )
    se.apply_slice_ops(
        slide=slide,
        ops=[
            {"op": "remove", "path": "stats.0"},
            {"op": "remove", "path": "subheadline"},
        ],
        design_tokens=_AAA_TOKENS,
    )
    props = slide["artifacts"]["kit_jsx"]["props_json"]
    assert props["stats"] == [{"value": "20%", "label": "CAGR"}]
    assert props["subheadline"] is None


def test_move_list_item_reorders_siblings_only():
    slide = _make_compiled_slide(
        kit="TimelineBlock",
        props={
            "headline": "Roadmap",
            "milestones": [
                {"date": "Q1", "title": "Alpha"},
                {"date": "Q2", "title": "Beta"},
                {"date": "Q3", "title": "Launch"},
            ],
        },
    )
    se.apply_slice_ops(
        slide=slide,
        ops=[{"op": "move", "from_path": "milestones.0", "path": "milestones.2"}],
        design_tokens=_AAA_TOKENS,
    )
    assert [m["title"] for m in slide["artifacts"]["kit_jsx"]["props_json"]["milestones"]] == ["Beta", "Launch", "Alpha"]


def test_swap_image_accepts_stored_assets_and_rejects_external_urls():
    slide = _make_compiled_slide(
        kit="TitleHero",
        props={"headline": "Hero", "variant": "image", "imageUrl": "/api/v4/images/p/old.png"},
    )
    se.apply_slice_ops(
        slide=slide,
        ops=[{"op": "swap-image", "path": "imageUrl", "value": "http://127.0.0.1:8003/api/v4/images/p/new.png"}],
        design_tokens=_AAA_TOKENS,
    )
    assert slide["artifacts"]["kit_jsx"]["props_json"]["imageUrl"].endswith("/api/v4/images/p/new.png")

    with pytest.raises(se.SliceEditError) as ei:
        se.apply_slice_ops(
            slide=slide,
            ops=[{"op": "swap-image", "path": "imageUrl", "value": "https://example.com/stock.png"}],
            design_tokens=_AAA_TOKENS,
        )
    assert ei.value.code == "unapproved_image_url"

    with pytest.raises(se.SliceEditError) as external_host:
        se.apply_slice_ops(
            slide=slide,
            ops=[{"op": "swap-image", "path": "imageUrl", "value": "https://assets.invalid/api/v4/images/p/not-local.png"}],
            design_tokens=_AAA_TOKENS,
        )
    assert external_host.value.code == "unapproved_image_url"


def test_set_crop_and_layout_variant_are_allowlisted():
    slide = _make_compiled_slide(
        kit="FullBleedImage",
        props={"imageUrl": "/api/v4/images/p/hero.png", "overlay": "scrim-bottom", "align": "bottom-left"},
    )
    se.apply_slice_ops(
        slide=slide,
        ops=[
            {"op": "set-crop", "path": "imageCrop", "value": {"focalX": 0.4, "focalY": 0.6, "zoom": 1.25}},
            {"op": "set-layout-variant", "path": "overlay", "value": "scrim-full"},
        ],
        design_tokens=_AAA_TOKENS,
    )
    props = slide["artifacts"]["kit_jsx"]["props_json"]
    assert props["imageCrop"] == {"focalX": 0.4, "focalY": 0.6, "zoom": 1.25}
    assert props["overlay"] == "scrim-full"


def test_expanded_ops_still_rollback_on_later_failure():
    slide = _make_compiled_slide(
        kit="StatHero",
        props={"headline": "Market", "stats": [{"value": "$2B", "label": "TAM"}]},
    )
    with pytest.raises(se.SliceEditError):
        se.apply_slice_ops(
            slide=slide,
            ops=[
                {"op": "insert", "path": "stats.1", "value": {"value": "20%", "label": "CAGR"}},
                {"op": "swap-image", "path": "imageUrl", "value": "https://example.com/not-approved.png"},
            ],
            design_tokens=_AAA_TOKENS,
        )
    props = slide["artifacts"]["kit_jsx"]["props_json"]
    assert props["stats"] == [{"value": "$2B", "label": "TAM"}]
    assert slide["artifact_version"] == 1


def test_noop_when_value_unchanged():
    slide = _make_compiled_slide(
        kit="TitleHero",
        props={"headline": "Same", "subheadline": "Sub", "variant": "gradient"},
    )
    fp_before = slide["artifacts"]["kit_jsx"]["fingerprint"]
    res = se.apply_slice_ops(
        slide=slide,
        ops=[{"path": "headline", "value": "Same"}],
        design_tokens=_AAA_TOKENS,
    )
    assert res["noop"] is True
    assert res["fields_changed"] == []
    # No version bump, no fingerprint change.
    assert slide["artifact_version"] == 1
    assert slide["artifacts"]["kit_jsx"]["fingerprint"] == fp_before


def test_unknown_top_level_key_rejected():
    slide = _make_compiled_slide(
        kit="TitleHero",
        props={"headline": "Hi", "variant": "gradient"},
    )
    with pytest.raises(se.SliceEditError) as ei:
        se.apply_slice_ops(
            slide=slide,
            ops=[{"path": "made_up_key", "value": "x"}],
            design_tokens=_AAA_TOKENS,
        )
    assert ei.value.code == "unknown_top_level"
    # Slide must remain unchanged.
    assert slide["artifact_version"] == 1
    assert "made_up_key" not in slide["artifacts"]["kit_jsx"]["props_json"]


def test_partial_failure_does_not_mutate_slide():
    slide = _make_compiled_slide(
        kit="TitleHero",
        props={"headline": "Old", "subheadline": "Sub", "variant": "gradient"},
    )
    fp_before = slide["artifacts"]["kit_jsx"]["fingerprint"]
    with pytest.raises(se.SliceEditError):
        se.apply_slice_ops(
            slide=slide,
            # First op valid; second op invalid → whole batch rolls back.
            ops=[
                {"path": "headline", "value": "Will not stick"},
                {"path": "does_not_exist", "value": "boom"},
            ],
            design_tokens=_AAA_TOKENS,
        )
    # Headline must still be the original; nothing committed.
    assert slide["artifacts"]["kit_jsx"]["props_json"]["headline"] == "Old"
    assert slide["artifacts"]["kit_jsx"]["fingerprint"] == fp_before
    assert slide["artifact_version"] == 1


def test_type_mismatch_rejected_before_commit():
    slide = _make_compiled_slide(
        kit="TitleHero",
        props={"headline": "Hi", "variant": "gradient"},
    )
    with pytest.raises(se.SliceEditError) as ei:
        se.apply_slice_ops(
            slide=slide,
            ops=[{"path": "headline", "value": 123}],
            design_tokens=_AAA_TOKENS,
        )
    assert ei.value.code == "type_mismatch"
    assert slide["artifact_version"] == 1


def test_clearing_string_to_null_allowed():
    slide = _make_compiled_slide(
        kit="TitleHero",
        props={"headline": "Hi", "subheadline": "Sub", "variant": "gradient"},
    )
    res = se.apply_slice_ops(
        slide=slide,
        ops=[{"path": "subheadline", "value": None}],
        design_tokens=_AAA_TOKENS,
    )
    assert res["fields_changed"] == ["subheadline"]
    assert slide["artifacts"]["kit_jsx"]["props_json"]["subheadline"] is None


def test_unsupported_op_kind_rejected():
    slide = _make_compiled_slide(
        kit="TitleHero",
        props={"headline": "Hi", "variant": "gradient"},
    )
    with pytest.raises(se.SliceEditError) as ei:
        se.apply_slice_ops(
            slide=slide,
            ops=[{"path": "headline", "value": "x", "op": "delete"}],
            design_tokens=_AAA_TOKENS,
        )
    assert ei.value.code == "unsupported_op"


def test_too_many_ops_rejected():
    slide = _make_compiled_slide(
        kit="TitleHero",
        props={"headline": "Hi", "variant": "gradient"},
    )
    with pytest.raises(se.SliceEditError) as ei:
        se.apply_slice_ops(
            slide=slide,
            ops=[{"path": "headline", "value": str(i)} for i in range(50)],
            design_tokens=_AAA_TOKENS,
        )
    assert ei.value.code == "too_many_ops"


def test_all_four_artifacts_rebuilt():
    slide = _make_compiled_slide(
        kit="TitleHero",
        props={"headline": "Old", "subheadline": "Sub", "variant": "gradient"},
    )
    html_before = slide["artifacts"]["html_css_js"]
    engine_before = slide["artifacts"]["engine"]
    legacy_before = slide["artifacts"]["reveal_legacy"]
    se.apply_slice_ops(
        slide=slide,
        ops=[{"path": "headline", "value": "Different"}],
        design_tokens=_AAA_TOKENS,
    )
    # Each transformer is deterministic on (kit, props, animation_ir),
    # so a real prop change must produce different artifacts.
    assert slide["artifacts"]["html_css_js"] != html_before
    assert slide["artifacts"]["engine"] != engine_before
    assert slide["artifacts"]["reveal_legacy"] != legacy_before
