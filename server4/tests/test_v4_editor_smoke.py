"""V4 editor smoke tests.

These are intentionally narrow: they exercise the parts of the V4 editor stack
that have unit-testable behavior without requiring a live Mongo, Redis, or LLM.

Covered:
  * URL sanitization in `parallel_writer._sanitize_url` against the exact
    `"httpshttps://..."` corruption observed in
    `tests/v4_forced_gpt_oss_120b.json` (slide 0).
  * V4 editor router is registered on the FastAPI app with the expected
    paths and methods.
  * Writer system prompts contain the planner-directive guardrail so a future
    refactor doesn't silently drop it.

Run:
    cd server4
    pytest tests/test_v4_editor_smoke.py -v
"""

from __future__ import annotations

import pytest

from app.services.v4.parallel_writer import (
    _PREMIUM_WRITER_SYSTEM,
    _STANDARD_WRITER_SYSTEM,
    _sanitize_url,
)
from app.routers.v4_editor import (
    _reindex_compiled_slides,
    _reindex_skeleton,
    _validated_reorder,
)


# ── URL sanitizer ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        # The exact bug captured in tests/v4_forced_gpt_oss_120b.json (slide 0).
        (
            "httpshttps://www.rillion.com/blog/best-invoice-automation-software/",
            "https://www.rillion.com/blog/best-invoice-automation-software/",
        ),
        (
            "httphttp://example.com/x",
            "http://example.com/x",
        ),
        (
            "https://https://example.com/y",
            "https://example.com/y",
        ),
        (
            "  https://example.com/clean  ",
            "https://example.com/clean",
        ),
        (
            '"https://example.com/quoted"',
            "https://example.com/quoted",
        ),
        # Already correct — should pass through unchanged.
        ("https://example.com/", "https://example.com/"),
    ],
)
def test_sanitize_url_fixes_known_corruptions(raw: str, expected: str) -> None:
    assert _sanitize_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        None,
        "javascript:alert(1)",
        "ftp://example.com/file",
        "not-a-url",
        "//cdn.example.com/x.js",
    ],
)
def test_sanitize_url_rejects_unusable(raw) -> None:
    assert _sanitize_url(raw) == ""


def test_sanitize_url_caps_length() -> None:
    long_path = "a" * 2000
    out = _sanitize_url(f"https://example.com/{long_path}")
    assert out.startswith("https://example.com/")
    assert len(out) <= 1024


# ── Writer prompt guardrails ───────────────────────────────────────


def test_premium_writer_warns_against_echoing_planner_directive() -> None:
    assert "planner_directive" in _PREMIUM_WRITER_SYSTEM
    # Must explicitly forbid echoing the directive verbatim.
    assert "echo" in _PREMIUM_WRITER_SYSTEM.lower()


def test_standard_writer_keeps_descriptive_subheadline_constraint() -> None:
    # The standard writer is the fallback for premium failures (template_fill);
    # it must still require a descriptive subheadline so we don't ship empty
    # subheadlines like the slide_drafted writer_2_fallback failure case.
    assert "subheadline" in _STANDARD_WRITER_SYSTEM
    assert "REQUIRED" in _STANDARD_WRITER_SYSTEM


# ── V4 editor router registration ──────────────────────────────────


def test_v4_editor_routes_are_mounted() -> None:
    """Import the FastAPI app and assert the V4 editor surface is wired.

    This catches accidental removal of `app.include_router(v4_editor_router)`
    in `server4/main.py`.
    """
    from main import app  # noqa: WPS433 — intentional late import

    paths = {(getattr(r, "path", None), tuple(sorted(getattr(r, "methods", []) or []))) for r in app.routes}

    expected = [
        ("/api/v4/projects/{project_id}/slides", ("GET",)),
        ("/api/v4/projects/{project_id}/slides/reorder", ("PATCH",)),
        ("/api/v4/projects/{project_id}/slides/{slide_no}", ("PATCH",)),
        ("/api/v4/projects/{project_id}/slides/{slide_no}/regenerate", ("POST",)),
        ("/api/v4/projects/{project_id}/slides/{slide_no}/recompile", ("POST",)),
        ("/api/v4/projects/{project_id}/slides/{slide_no}/repair", ("POST",)),
        ("/api/v4/projects/{project_id}/slides/regenerate-batch", ("POST",)),
        ("/api/v4/projects/{project_id}/regenerate-deck", ("POST",)),
        ("/api/v4/projects/{project_id}/slides/{slide_no}/team-member", ("POST",)),
        (
            "/api/v4/projects/{project_id}/slides/{slide_no}/team-member/{member_idx}",
            ("DELETE",),
        ),
    ]
    for path, methods in expected:
        assert any(
            p == path and set(methods).issubset(set(m))
            for (p, m) in paths
            if p is not None
        ), f"Missing V4 editor route: {methods} {path}"


def test_plan10_admin_alert_route_is_mounted() -> None:
    from main import app  # noqa: WPS433 — intentional late import

    paths = {(getattr(r, "path", None), tuple(sorted(getattr(r, "methods", []) or []))) for r in app.routes}

    assert any(
        p == "/api/admin/health/v4-alerts" and "GET" in set(m)
        for (p, m) in paths
        if p is not None
    )


def test_reorder_helpers_validate_and_reindex_compiled_artifacts() -> None:
    assert _validated_reorder([2, 0, 1], [0, 1, 2]) == [2, 0, 1]
    with pytest.raises(ValueError, match="duplicate"):
        _validated_reorder([0, 0, 1], [0, 1, 2])
    with pytest.raises(ValueError, match="missing"):
        _validated_reorder([0, 1, 5], [0, 1, 2])

    compiled = [
        {"slide_id": "slide-000", "slide_index": 0, "jsx_source": "a"},
        {"slide_id": "slide-001", "slide_index": 1, "jsx_source": "b"},
        {"slide_id": "slide-002", "slide_index": 2, "jsx_source": "c"},
    ]
    reordered = _reindex_compiled_slides(compiled, [2, 0, 1])
    assert [s["slide_id"] for s in reordered] == ["slide-002", "slide-000", "slide-001"]
    assert [s["slide_index"] for s in reordered] == [0, 1, 2]
    assert compiled[2]["slide_index"] == 2


def test_reorder_helper_reindexes_skeleton_when_shape_matches() -> None:
    skeleton = {
        "title": "Deck",
        "slides": [
            {"index": 0, "intent": "problem"},
            {"index": 1, "intent": "solution"},
            {"index": 2, "intent": "traction"},
        ],
    }
    reordered = _reindex_skeleton(skeleton, [1, 2, 0])
    assert [s["intent"] for s in reordered["slides"]] == ["solution", "traction", "problem"]
    assert [s["index"] for s in reordered["slides"]] == [0, 1, 2]
    assert [s["index"] for s in skeleton["slides"]] == [0, 1, 2]
