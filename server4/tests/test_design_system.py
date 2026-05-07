"""
Unit tests for v4.design_system.build_design_system.

Validates:
  - Determinism (same input → same version)
  - Sensitivity (any token change → different version)
  - CSS contains every expected variable
  - Font imports filter out system fonts
  - Defensive errors on missing required sub-objects
"""

from __future__ import annotations

import pytest

from app.services.v4.design_resolver import resolve_design_tokens
from app.services.v4.design_system import (
    build_design_system,
    attach_version_to_compiled_slides,
)


def _tokens() -> dict:
    """Real tokens from the actual resolver — no hand-crafted fakes."""
    return resolve_design_tokens(
        design_profile=None,
        purpose="pitch_deck",
        industry="ai",
    ).to_dict()


def test_design_system_deterministic():
    t = _tokens()
    a = build_design_system(t, deck_title="Same Title")
    b = build_design_system(t, deck_title="Different Title")
    # version is content-addressed over (css + sorted tokens), NOT title.
    assert a["version"] == b["version"]
    assert len(a["version"]) == 12
    # Header comments differ (deck_title differs), but the CSS body must
    # contain every token-derived line.
    assert "--color-primary" in a["css"]
    assert "--color-primary" in b["css"]


def test_design_system_changes_with_tokens():
    t1 = _tokens()
    t2 = resolve_design_tokens(
        design_profile=None,
        purpose="pitch_deck",
        industry="fintech",  # different industry → different palette
    ).to_dict()
    a = build_design_system(t1)
    b = build_design_system(t2)
    assert a["version"] != b["version"]


def test_css_contains_required_tokens():
    t = _tokens()
    ds = build_design_system(t)
    css = ds["css"]
    for var in (
        "--color-primary",
        "--color-secondary",
        "--color-accent",
        "--color-background",
        "--color-text-primary",
        "--font-heading",
        "--font-body",
        "--type-h1",
        "--type-body",
        "--space-margin",
        "--line-height",
    ):
        assert var in css, f"missing CSS var {var}"


def test_chart_palette_mapped():
    t = _tokens()
    chart = t["palette"]["chart"]
    assert len(chart) >= 3
    ds = build_design_system(t)
    for i in range(1, len(chart) + 1):
        assert f"--color-chart-{i}" in ds["css"]
    assert f"--color-chart-count: {len(chart)}" in ds["css"]


def test_font_imports_built():
    t = _tokens()
    ds = build_design_system(t)
    # AI/pitch_deck default → Inter (heading + body). Inter is a Google Font.
    assert isinstance(ds["font_imports"], list)
    assert all(url.startswith("https://fonts.googleapis.com/") for url in ds["font_imports"])
    if ds["font_imports"]:
        assert "family=Inter" in ds["font_imports"][0]


def test_font_imports_skip_system_fonts():
    t = _tokens()
    # Force fonts to system-only — should produce no imports.
    t["fonts"]["heading"] = "system-ui"
    t["fonts"]["body"] = "monospace"
    ds = build_design_system(t)
    assert ds["font_imports"] == []


def test_defensive_errors():
    with pytest.raises(ValueError):
        build_design_system({})  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        build_design_system({"palette": {"primary": "#000"}})  # missing fonts


def test_attach_version_to_compiled_slides():
    slides = [
        {"slide_id": "slide-001", "design_system_version": None},
        {"slide_id": "slide-002", "design_system_version": None},
    ]
    attach_version_to_compiled_slides(slides, "abc123def456")
    assert all(s["design_system_version"] == "abc123def456" for s in slides)
    # Idempotent
    attach_version_to_compiled_slides(slides, "abc123def456")
    assert all(s["design_system_version"] == "abc123def456" for s in slides)


def test_snapshot_shape():
    t = _tokens()
    ds = build_design_system(t, deck_title="Test Deck")
    assert set(ds.keys()) == {
        "schema_version", "version", "tokens", "css",
        "font_imports", "generated_at",
    }
    assert ds["schema_version"] == 1
    assert ds["tokens"] == t
    assert ds["css"].startswith("/* DesignSystem")
    # generated_at is ISO-8601-with-tz
    assert ds["generated_at"].endswith("+00:00")
