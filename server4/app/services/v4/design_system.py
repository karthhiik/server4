"""
V4 Design System Builder — Phase 2 (Day 2) of v3-final plan.

Given the deterministic `ResolvedDesignTokens` produced by `design_resolver`,
build the deck-level **DesignSystem snapshot**:

    {
      "version":       "<sha1[:12]>",       # cache-bust key + slide FK
      "tokens":        { … same shape as design_tokens_dict … },
      "css":           ":root { --color-primary: …; … }",
      "font_imports":  ["https://fonts.googleapis.com/css2?family=…"],
      "generated_at":  "<iso-8601 utc>",
    }

Design principles:
  - **Deterministic.** Same input tokens → same `version`. No LLM, no
    randomness. Sorted serialization so dict-key ordering can't drift
    the hash.
  - **No fake data.** All values come from the resolved tokens; nothing
    is invented. If the upstream tokens are wrong, that's a bug in
    `design_resolver`, not here.
  - **Wire-compatible.** The CSS variable names match the Kit components'
    CSS-var consumption (see lliveupdatedstreaming/src/sandbox/kit.css).
  - **Frontend-ready.** `font_imports` lists the Google Fonts URLs the
    sandbox / preview must inject. Inter is always included (kit fallback).

Phase 2 owns: producing the snapshot. Phase 6 (hot-swap WS) owns:
broadcasting the new `version` so the frontend invalidates its cache.
Phase 7 (useCompiledDeck) owns: keying the deck cache by `version`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus


_SCHEMA_VERSION = 1
"""
Bumped only when the *shape* of the snapshot dict changes (e.g. new
top-level keys). The `version` field below is a content hash — a
different concept used for cache busting.
"""


# ── PT → CSS px conversion ────────────────────────────────────────
# Backend type scale lives in points (PPTX-native). Frontend slide
# rendering uses pixels at the canonical 16:9 viewport (1280x720 px =
# the same physical 13.33in × 7.5in deck if you do the math at 96dpi).
# 1 pt at 96dpi = 1.333… px.
_PT_TO_PX = 96.0 / 72.0
# Likewise inches → px at 96dpi for spacing tokens.
_IN_TO_PX = 96.0


def _px(pt_value: float) -> str:
    return f"{round(pt_value * _PT_TO_PX, 2)}px"


def _px_in(in_value: float) -> str:
    return f"{round(in_value * _IN_TO_PX, 2)}px"


# ── Google Fonts URL builder ──────────────────────────────────────
# We always ship Inter as a fallback (the Kit components reference it
# in their default font stacks). User-selected fonts get appended.
_BASE_GOOGLE_FONT = "Inter:wght@400;500;600;700"

# Weights pulled per-font: most decks need 400/500/700; a handful of
# display fonts also need 600 for headings.
_FONT_WEIGHT_PROFILE = "wght@400;500;600;700"

# Local-system fonts that must NOT be requested from Google.
_SYSTEM_FONTS = {
    "ui-monospace",
    "SFMono-Regular",
    "Menlo",
    "monospace",
    "system-ui",
    "-apple-system",
    "BlinkMacSystemFont",
    "Segoe UI",
    "sans-serif",
    "serif",
}


def _is_system_font(family: str) -> bool:
    return family.strip() in _SYSTEM_FONTS


def _google_fonts_url(families: list[str]) -> str | None:
    """
    Build a single Google Fonts URL for all webfont families.
    Returns None if every requested font is a system font (no network call needed).
    """
    web_families: list[str] = []
    seen: set[str] = set()
    for fam in families:
        fam = (fam or "").strip()
        if not fam or fam in seen or _is_system_font(fam):
            continue
        seen.add(fam)
        # Google Fonts expects family name with `+` for spaces.
        web_families.append(f"{quote_plus(fam)}:{_FONT_WEIGHT_PROFILE}")
    if not web_families:
        return None
    return "https://fonts.googleapis.com/css2?" + "&".join(
        f"family={f}" for f in web_families
    ) + "&display=swap"


# ── CSS artifact builder ──────────────────────────────────────────

def _stringify_font_stack(family: str, fallback: str) -> str:
    """Quote multi-word families and append a fallback group."""
    fam = (family or "").strip() or "Inter"
    quoted = f'"{fam}"' if " " in fam and not fam.startswith('"') else fam
    return f"{quoted}, {fallback}"


def _build_css(tokens: dict[str, Any]) -> str:
    """
    Generate a CSS string with `:root { --token: value; }` declarations
    spanning every role a Kit component might consume.

    Shape of `tokens` matches `ResolvedDesignTokens.to_dict()`:
      palette, fonts, scale, spacing, weights, density, line_height,
      letter_spacing_em, provided_by.
    """
    palette = tokens.get("palette") or {}
    fonts = tokens.get("fonts") or {}
    scale = tokens.get("scale") or {}
    spacing = tokens.get("spacing") or {}
    weights = tokens.get("weights") or {}

    chart_palette: list[str] = list(palette.get("chart") or [])

    heading_stack = _stringify_font_stack(
        fonts.get("heading", "Inter"),
        "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
    )
    body_stack = _stringify_font_stack(
        fonts.get("body", "Inter"),
        "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
    )
    mono_stack = fonts.get("mono") or "ui-monospace, SFMono-Regular, Menlo, monospace"

    lines: list[str] = [":root {"]

    # ── Color tokens ─────────────────────────────────────────────
    color_roles = (
        "primary", "secondary", "accent",
        "background", "surface",
        "text_primary", "text_secondary", "text_muted",
        "success", "warning", "danger",
    )
    for role in color_roles:
        val = palette.get(role)
        if not val:
            continue
        css_role = role.replace("_", "-")
        lines.append(f"  --color-{css_role}: {val};")

    # Chart color slots (1-indexed, matching the sandbox chart kit).
    for i, hex_str in enumerate(chart_palette, start=1):
        if hex_str:
            lines.append(f"  --color-chart-{i}: {hex_str};")
    if chart_palette:
        lines.append(f"  --color-chart-count: {len(chart_palette)};")

    # ── Font families ────────────────────────────────────────────
    lines.append(f"  --font-heading: {heading_stack};")
    lines.append(f"  --font-body: {body_stack};")
    lines.append(f"  --font-mono: {mono_stack};")

    # ── Type scale (points → CSS px) ─────────────────────────────
    for role in ("display", "h1", "h2", "h3", "body", "caption"):
        pt = scale.get(role)
        if pt is None:
            continue
        try:
            lines.append(f"  --type-{role}: {_px(float(pt))};")
        except (TypeError, ValueError):
            continue

    # ── Weights ──────────────────────────────────────────────────
    for role in ("heading", "body"):
        w = weights.get(role)
        if w is None:
            continue
        try:
            lines.append(f"  --weight-{role}: {int(w)};")
        except (TypeError, ValueError):
            continue

    # ── Spacing (inches → CSS px) ────────────────────────────────
    space_map = {
        "slide_margin_in": "margin",
        "gap_in": "gap",
        "section_gap_in": "section-gap",
    }
    for src, css_name in space_map.items():
        v = spacing.get(src)
        if v is None:
            continue
        try:
            lines.append(f"  --space-{css_name}: {_px_in(float(v))};")
        except (TypeError, ValueError):
            continue

    # ── Rhythm tokens ────────────────────────────────────────────
    line_height = tokens.get("line_height")
    if isinstance(line_height, (int, float)):
        lines.append(f"  --line-height: {round(float(line_height), 3)};")

    letter_spacing = tokens.get("letter_spacing_em")
    if isinstance(letter_spacing, (int, float)):
        lines.append(f"  --letter-spacing: {round(float(letter_spacing), 4)}em;")

    # ── Density token (informational; some kits branch on it) ────
    density = tokens.get("density")
    if isinstance(density, str) and density.strip():
        lines.append(f'  --density: "{density}";')

    # ── Shape tokens ───────────────────────────────────────────────
    shape = tokens.get("shape") or {}
    shape_map = {
        "radius_sm": "radius-sm", "radius_md": "radius-md",
        "radius_lg": "radius-lg", "radius_xl": "radius-xl",
        "shadow_sm": "shadow-sm", "shadow_md": "shadow-md",
        "shadow_lg": "shadow-lg", "shadow_glow": "shadow-glow",
        "border_width": "border-width", "border_subtle": "border-subtle",
        "glass_blur": "glass-blur",
    }
    for src, css_name in shape_map.items():
        v = shape.get(src)
        if v is not None:
            lines.append(f'  --shape-{css_name}: {v};')

    # ── Animation tokens ───────────────────────────────────────────
    animation = tokens.get("animation") or {}
    anim_map = {
        "entry_duration_ms": "entry-duration", "stagger_ms": "stagger",
        "hover_scale": "hover-scale", "hover_duration_ms": "hover-duration",
        "easing": "easing", "page_transition_ms": "page-transition",
        "micro_duration_ms": "micro-duration",
    }
    for src, css_name in anim_map.items():
        v = animation.get(src)
        if v is not None:
            lines.append(f'  --anim-{css_name}: {v};')

    # ── Grid tokens ──────────────────────────────────────────────
    grid = tokens.get("grid") or {}
    grid_map = {
        "columns": "columns", "gutter_px": "gutter",
        "baseline_px": "baseline", "max_content_width": "max-content-width",
        "slide_margin_px": "slide-margin", "safe_area_inset": "safe-area",
    }
    for src, css_name in grid_map.items():
        v = grid.get(src)
        if v is not None:
            lines.append(f'  --grid-{css_name}: {v};')

    lines.append("}")
    return "\n".join(lines) + "\n"


# ── Public API ────────────────────────────────────────────────────

def build_design_system(
    tokens: dict[str, Any],
    *,
    deck_title: str | None = None,
) -> dict[str, Any]:
    """
    Produce a deterministic, content-addressable DesignSystem snapshot
    from the resolved design tokens.

    Args:
        tokens: Output of `ResolvedDesignTokens.to_dict()` (palette, fonts,
                scale, spacing, weights, density, line_height,
                letter_spacing_em, provided_by).
        deck_title: Used only as a comment header in the generated CSS so
                    a human inspecting the artifact can trace which deck
                    produced it. Does NOT affect the version hash.

    Returns:
        A snapshot dict suitable for persistence on
        `presentations.design_system` and for `result.design_system`.

    Raises:
        ValueError: If `tokens` is missing the required `palette` or
                    `fonts` sub-objects (defensive — design_resolver
                    always supplies these in practice).
    """
    if not isinstance(tokens, dict):
        raise ValueError("design_system: tokens must be a dict")
    if not tokens.get("palette"):
        raise ValueError("design_system: tokens.palette is required")
    if not tokens.get("fonts"):
        raise ValueError("design_system: tokens.fonts is required")

    css_body = _build_css(tokens)

    # Hash is computed BEFORE we prepend the deck-title comment so that
    # two decks with identical tokens but different titles share the
    # same version (correct: same artifact, just different deck name).
    fingerprint_input = css_body + "|" + json.dumps(
        tokens, sort_keys=True, ensure_ascii=False
    )
    version = hashlib.sha1(fingerprint_input.encode("utf-8")).hexdigest()[:12]

    header = (
        f"/* DesignSystem v{_SCHEMA_VERSION} — version={version}"
        f" — deck={deck_title!r}"
        f" — generated_by=v4.design_system.build_design_system */\n"
    ) if deck_title else (
        f"/* DesignSystem v{_SCHEMA_VERSION} — version={version} */\n"
    )
    css = header + css_body

    fonts = tokens.get("fonts") or {}
    families = [
        fonts.get("heading", ""),
        fonts.get("body", ""),
    ]
    fonts_url = _google_fonts_url(families)
    font_imports = [fonts_url] if fonts_url else []

    return {
        "schema_version": _SCHEMA_VERSION,
        "version": version,
        "tokens": tokens,
        "css": css,
        "font_imports": font_imports,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def attach_version_to_compiled_slides(
    compiled_slides: list[dict[str, Any]],
    version: str,
) -> None:
    """
    Stamp every compiled-slide dict with the deck-level design_system
    version. Mutates the list in place — no copy, since the dicts are
    already fresh from `compile_slides()`.

    Idempotent: re-stamping with the same version is a no-op write.
    """
    for slide in compiled_slides:
        slide["design_system_version"] = version


def attach_design_system_to_html_artifact(
    compiled_slides: list[dict[str, Any]],
    design_system: dict[str, Any],
) -> None:
    """
    Inline the deck-level DesignSystem CSS + font_imports into each
    slide's `artifacts.html_css_js.css` so the artifact is fully
    self-contained (PPTX export / screenshot / standalone HTML).

    The DS CSS is prepended to the slide's existing `css` so the
    `:root { --color-* }` declarations resolve before any kit / IR
    rules consume them.

    Idempotent: detects the DS version comment and skips if already
    inlined (so re-running the post-compile pass on a hot-swapped
    deck is a no-op rather than building up duplicate token blocks).

    Mutates the list in place.
    """
    if not isinstance(design_system, dict):
        return
    ds_css = design_system.get("css")
    if not isinstance(ds_css, str) or not ds_css.strip():
        return
    version = design_system.get("version")
    sentinel = f"version={version}" if version else None
    font_imports = design_system.get("font_imports") or []

    for slide in compiled_slides:
        artifacts = slide.get("artifacts")
        if not isinstance(artifacts, dict):
            continue
        html_artifact = artifacts.get("html_css_js")
        if not isinstance(html_artifact, dict):
            continue
        existing = html_artifact.get("css") or ""
        # Idempotency: detect the DS sentinel comment in the existing CSS.
        if sentinel and sentinel in existing:
            continue
        html_artifact["css"] = ds_css.rstrip("\n") + "\n" + existing
        # Re-thread font_imports into head_meta for standalone export.
        head_meta = html_artifact.get("head_meta")
        if isinstance(head_meta, dict) and font_imports:
            head_meta["fonts"] = json.dumps(font_imports, ensure_ascii=False)
        # Re-fingerprint so cache invalidation matches the new CSS body.
        fp_input = (
            (html_artifact.get("html") or "")
            + "\n" + (html_artifact.get("css") or "")
            + "\n" + (html_artifact.get("js") or "")
        ).encode("utf-8")
        html_artifact["fingerprint"] = hashlib.sha1(fp_input).hexdigest()[:12]
