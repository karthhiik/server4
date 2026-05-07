"""Smoke tests for the V4 → CompiledSlide adapter.

Pure-logic (no LLM, no network). Verifies kit dispatch, prop shaping,
and JSX envelope integrity across the common slide patterns.
"""

from __future__ import annotations

import json
import re

import pytest

from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.slide_compiler import (
    compile_slide,
    compile_slides,
    _KIT_SET,
)


_PROPS_RE = re.compile(r"/\*\s*PROPS\s*([\s\S]*?)\*/")


def _extract_props(jsx: str) -> dict:
    m = _PROPS_RE.search(jsx)
    assert m, f"no PROPS block found in:\n{jsx}"
    return json.loads(m.group(1).strip())


def _slide(**kwargs) -> GeneratedSlide:
    defaults = {
        "index": 0,
        "intent": "content",
        "layout": "title-and-body",
        "headline": "Headline",
    }
    defaults.update(kwargs)
    return GeneratedSlide(**defaults)


def test_envelope_is_valid_jsx_with_parseable_props() -> None:
    slide = _slide(headline="Hello", subheadline="World")
    cs = compile_slide(slide=slide)
    assert cs["slide_id"] == "slide-000"
    assert cs["slide_index"] == 0
    assert cs["kit_component"] in _KIT_SET
    assert cs["imports"] == {"@kit": "1.0.0"}
    jsx = cs["jsx_source"]
    assert "import { " in jsx and ' } from "@kit";' in jsx
    assert "export default function Slide" in jsx
    props = _extract_props(jsx)
    assert props["headline"] == "Hello"
    assert props["subheadline"] == "World"


def test_title_intent_picks_title_hero() -> None:
    slide = _slide(intent="title", headline="Pitchduck", subheadline="Taglines")
    cs = compile_slide(slide=slide, deck_title="Pitchduck Deck")
    assert cs["kit_component"] == "TitleHero"
    props = _extract_props(cs["jsx_source"])
    assert props["variant"] == "gradient"
    assert props["headline"] == "Pitchduck"


def test_image_url_upgrades_title_to_image_variant() -> None:
    slide = _slide(intent="title", headline="X")
    cs = compile_slide(slide=slide, image_url="https://example.com/a.png")
    props = _extract_props(cs["jsx_source"])
    assert props["variant"] == "image"
    assert props["imageUrl"] == "https://example.com/a.png"


def test_stat_blocks_route_to_stat_hero() -> None:
    slide = _slide(
        intent="traction",
        headline="Traction",
        stat_blocks=[
            {"value": "12K", "label": "Users", "delta": "+20%", "trend": "up"},
            {"value": "$48K", "label": "MRR"},
        ],
    )
    cs = compile_slide(slide=slide)
    assert cs["kit_component"] == "StatHero"
    props = _extract_props(cs["jsx_source"])
    assert len(props["stats"]) == 2
    assert props["stats"][0] == {
        "value": "12K",
        "label": "Users",
        "delta": "+20%",
        "trend": "up",
    }
    # Second stat has no delta/trend; only value+label.
    assert "delta" not in props["stats"][1]
    assert "trend" not in props["stats"][1]


def test_chart_slide_shapes_data_correctly() -> None:
    slide = _slide(
        intent="market",
        headline="TAM",
        chart={
            "type": "bar",
            "data": [["2022", 100], ["2023", 140], ["2024", 210]],
            "x_key": "year",
            "y_keys": ["value"],
            "source": "Gartner 2024",
        },
    )
    cs = compile_slide(slide=slide)
    assert cs["kit_component"] == "ChartBlock"
    props = _extract_props(cs["jsx_source"])
    assert props["type"] == "bar"
    assert props["xKey"] == "year"
    assert props["yKeys"] == ["value"]
    assert props["source"] == "Gartner 2024"
    assert props["data"][0] == {"name": "2022", "value": 100.0}


def test_pie_chart_uses_value_name_keys() -> None:
    slide = _slide(
        headline="Segments",
        chart={"type": "pie", "data": [{"name": "A", "value": 1}], "value_key": "value"},
    )
    cs = compile_slide(slide=slide)
    props = _extract_props(cs["jsx_source"])
    assert props["type"] == "pie"
    assert props["valueKey"] == "value"
    assert props["nameKey"] == "name"


def test_timeline_routes_correctly() -> None:
    slide = _slide(
        intent="roadmap",
        headline="Roadmap",
        timeline={
            "orientation": "horizontal",
            "events": [
                {"date": "Q1", "title": "Launch", "done": True},
                {"date": "Q2", "title": "Scale", "description": "Hire"},
            ],
        },
    )
    cs = compile_slide(slide=slide)
    assert cs["kit_component"] == "TimelineBlock"
    props = _extract_props(cs["jsx_source"])
    assert props["orientation"] == "horizontal"
    assert len(props["milestones"]) == 2
    assert props["milestones"][0]["done"] is True
    assert props["milestones"][1]["description"] == "Hire"


def test_comparison_inline_rows_shape() -> None:
    slide = _slide(
        headline="Us vs Them",
        comparison={
            "columns": [
                {
                    "name": "Us",
                    "highlight": True,
                    "rows": [{"feature": "Price", "value": "$9"}, {"feature": "Speed", "value": True}],
                },
                {
                    "name": "Them",
                    "rows": [{"feature": "Price", "value": "$29"}, {"feature": "Speed", "value": False}],
                },
            ]
        },
    )
    cs = compile_slide(slide=slide)
    assert cs["kit_component"] == "ComparisonBlock"
    props = _extract_props(cs["jsx_source"])
    assert len(props["columns"]) == 2
    assert props["columns"][0]["highlight"] is True
    assert len(props["rows"]) == 2
    price_row = next(r for r in props["rows"] if r["feature"] == "Price")
    assert price_row["values"] == ["$9", "$29"]


def test_diagram_auto_layouts_missing_coordinates() -> None:
    slide = _slide(
        headline="How it works",
        diagram={
            "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}, {"id": "c", "label": "C"}],
            "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}, {"from": "a", "to": "missing"}],
        },
    )
    cs = compile_slide(slide=slide)
    assert cs["kit_component"] == "DiagramBlock"
    props = _extract_props(cs["jsx_source"])
    assert len(props["nodes"]) == 3
    # All x positions in 0-1 and distinct.
    xs = [n["x"] for n in props["nodes"]]
    assert all(0 < x < 1 for x in xs)
    assert len(set(xs)) == 3
    # Edge with unknown target is dropped.
    assert len(props["edges"]) == 2


def test_quote_routes_correctly() -> None:
    slide = _slide(
        headline="Endorsement",
        quote={"text": "This is great.", "attribution": "Jane Doe", "role": "CEO"},
    )
    cs = compile_slide(slide=slide)
    assert cs["kit_component"] == "QuoteBlock"
    props = _extract_props(cs["jsx_source"])
    assert props["quote"] == "This is great."
    assert props["attribution"] == "Jane Doe"
    assert props["role"] == "CEO"


def test_team_members_override_intent() -> None:
    slide = _slide(
        intent="team",
        headline="Team",
        team_members=[
            {"name": "A", "role": "CEO", "photo_url": "https://x/a.jpg"},
            {"name": "B", "role": "CTO", "is_default_avatar": True, "photo_url": "fallback"},
            {"name": "C", "role": "COO", "linkedin_url": "https://li/c", "bio": "Ten years..."},
        ],
    )
    cs = compile_slide(slide=slide)
    assert cs["kit_component"] == "TeamGrid"
    props = _extract_props(cs["jsx_source"])
    assert props["columns"] == 3
    assert props["members"][0]["photoUrl"] == "https://x/a.jpg"
    # Default-avatar members should NOT get a photoUrl.
    assert "photoUrl" not in props["members"][1]
    assert props["members"][2]["linkedInUrl"] == "https://li/c"
    assert props["members"][2]["bio"].startswith("Ten years")


def test_short_bullets_become_feature_grid() -> None:
    slide = _slide(
        headline="Why us",
        bullets=["Fast — sub-second response", "Secure: SOC2 compliant", "Global reach"],
    )
    cs = compile_slide(slide=slide)
    assert cs["kit_component"] == "FeatureGrid"
    props = _extract_props(cs["jsx_source"])
    assert len(props["features"]) == 3
    assert props["features"][0]["title"] == "Fast"
    assert props["features"][0]["description"] == "sub-second response"
    assert props["features"][1]["title"] == "Secure"
    # icon guessed based on keyword
    assert props["features"][1]["icon"] == "Shield"


def test_long_bullets_fall_back_to_title_hero() -> None:
    # Bullets averaging >14 words should NOT be rendered as feature cards.
    slide = _slide(
        headline="Detail",
        bullets=[
            "This is an intentionally long bullet with many words meant to exceed the feature-grid heuristic threshold",
            "Another long bullet that reinforces the rule and ensures the average word count stays high enough to reject it",
        ],
    )
    cs = compile_slide(slide=slide)
    assert cs["kit_component"] == "TitleHero"


def test_image_only_content_slide_uses_full_bleed() -> None:
    slide = _slide(intent="cover", headline="Vision")
    cs = compile_slide(slide=slide, image_url="https://example.com/v.png")
    # Intent="cover" wins over full-bleed → title with image variant.
    assert cs["kit_component"] == "TitleHero"

    slide2 = _slide(intent="content", headline="Moment")
    cs2 = compile_slide(slide=slide2, image_url="https://example.com/v.png")
    assert cs2["kit_component"] == "FullBleedImage"
    props2 = _extract_props(cs2["jsx_source"])
    assert props2["imageUrl"].startswith("https://")


def test_compile_slides_bulk_maps_image_urls() -> None:
    slides = [
        _slide(index=0, intent="title", headline="T"),
        _slide(index=1, intent="content", headline="C"),
    ]
    result = compile_slides(
        slides=slides,
        image_urls={1: "https://example.com/slide1.png"},
        deck_title="Deck",
    )
    assert len(result) == 2
    assert result[0]["slide_id"] == "slide-000"
    assert result[1]["slide_id"] == "slide-001"
    assert result[1]["assets"][0]["url"] == "https://example.com/slide1.png"


def test_malicious_headline_is_json_escaped() -> None:
    """Prop strings go through json.dumps — HTML/JS injection impossible."""
    slide = _slide(headline='</script><script>alert(1)</script>')
    cs = compile_slide(slide=slide)
    jsx = cs["jsx_source"]
    # The raw HTML string must NOT appear outside the PROPS JSON block.
    # Inside PROPS it's JSON-escaped so the sandbox `JSON.parse` treats
    # it as literal text.
    props = _extract_props(jsx)
    assert props["headline"] == '</script><script>alert(1)</script>'
    # The PROPS JSON must be parseable (already verified by _extract_props),
    # and the `</script>` sequence must be inside a JSON string — check
    # there's no bare `<script>` tag in the JSX emitted.
    emitted_code = _PROPS_RE.sub("", jsx)
    assert "<script" not in emitted_code.lower()


def test_props_fence_escapes_closing_comment_token() -> None:
    headline = "Market proof */ still literal with slash \\ and rocket \U0001F680"
    subheadline = "Evidence stays visible\nwithout closing the fence"
    slide = _slide(headline=headline, subheadline=subheadline)
    cs = compile_slide(slide=slide)
    props = _extract_props(cs["jsx_source"])
    assert props["headline"] == headline
    assert props["subheadline"] == subheadline
    emitted_code = _PROPS_RE.sub("", cs["jsx_source"])
    assert "still literal" not in emitted_code
    assert cs["artifacts"]["kit_jsx"]["props_json"]["headline"] == headline


def test_all_slides_resolve_to_known_kit() -> None:
    """No slide variant ever returns an unregistered kit name."""
    variants = [
        _slide(intent="title"),
        _slide(intent="team"),
        _slide(intent="thanks"),
        _slide(intent="content"),
        _slide(intent="", bullets=["a", "b", "c"]),
        _slide(intent="data", chart={"type": "bar", "data": [{"name": "x", "value": 1}]}),
    ]
    for v in variants:
        cs = compile_slide(slide=v)
        assert cs["kit_component"] in _KIT_SET, cs["kit_component"]


def test_compiled_slide_carries_layout_intent_metadata() -> None:
    slide = _slide(
        intent="traction",
        headline="Traction is compounding",
        stat_blocks=[
            {"value": "12K", "label": "active teams"},
            {"value": "142%", "label": "net revenue retention"},
        ],
    )
    cs = compile_slide(slide=slide)
    assert cs["kit_component"] == "StatHero"
    layout_intent = cs["layout_intent"]
    assert layout_intent["kit_id"] == "StatHero"
    assert layout_intent["resolved_kit"] == "StatHero"
    assert layout_intent["key"].startswith("StatHero:")
    assert layout_intent["score"] > 0
    assert cs["artifacts"]["kit_jsx"]["layout_intent"]["key"] == layout_intent["key"]


def test_layout_intent_diversifies_repeated_feature_slides() -> None:
    slides = [
        _slide(
            index=i,
            intent="solution",
            headline=f"Capability cluster {i}",
            bullets=[
                "Fast setup — onboard in minutes",
                "Secure workflow — permissions built in",
                "Global reach — deploy across teams",
            ],
        )
        for i in range(4)
    ]
    compiled = compile_slides(slides=slides, deck_title="Capability Deck")
    variants = [c["layout_intent"]["layout_variant"] for c in compiled]
    assert len(set(variants)) >= 2
    for i in range(len(variants) - 2):
        assert len(set(variants[i:i + 3])) > 1


def test_pending_image_content_slide_can_use_full_bleed_placeholder() -> None:
    slide = _slide(
        intent="customer",
        layout="full-bleed image",
        headline="The customer moment",
        render_decision={"modality": "image", "renderer": "hero"},
    )
    cs = compile_slide(slide=slide, image_url=None)
    props = cs["artifacts"]["kit_jsx"]["props_json"]
    assert cs["kit_component"] == "FullBleedImage"
    assert cs["pending_image"] is True
    assert props["pendingImage"] is True
    assert "imageUrl" not in props
