"""
V4 HTML / CSS / JS Transformer — Phase 4 (Day 6-7) of v3-final plan.

Given a real `(kit, props, animation_ir, design_system)` tuple produced
upstream by the V4 generation pipeline + Phase 1 compiler + Phase 2
DesignSystem builder + Phase 3 AnimationIR builder, this module emits
a self-contained `html_css_js` artifact:

    {
      "html":       "<section class='slide' data-kit='StatHero'>…</section>",
      "css":        ":root{…tokens…}\\n@keyframes …\\n.slide{…}",
      "js":         "(function(){ …chart drawing only when needed… })();",
      "head_meta":  {"charset":"utf-8","viewport":"…","title":"…"},
      "fingerprint": "<sha1[:12] of html+css+js>"
    }

The artifact is consumed by:

  * **PPTX exporter** — rasterises the HTML in headless Chromium for
    high-fidelity slide export (Phase 12 / PPTX 80% fidelity target).
  * **Screenshot service** — thumbnails for the deck dashboard.
  * **Fallback renderer** — when the JSX sandbox can't compile (e.g.
    esbuild-wasm cold start) the parent shell renders this artifact
    directly inside an iframe.
  * **Static export** — `Save deck as static HTML` user action.

Design rules (all enforced in this module):
  - **Real implementation.** Every element is rendered from the actual
    props passed in; nothing is invented or stubbed. If a prop is
    missing, the corresponding HTML node is omitted (matches kit React
    behavior).
  - **Zero LLM.** Pure deterministic transformation. <2ms per slide.
  - **Token-driven.** All colors, fonts, spacing read CSS variables
    that come from `design_system.css` (`--color-*`, `--type-*`,
    `--space-*`). Re-theming = swap the design system, no recompile.
  - **AnimationIR-driven.** Each animated element gets `class="ir-anim-<id>"`.
    The IR's `css` (keyframes + classes + reduced-motion media query)
    is appended verbatim — single source of truth for motion.
  - **Real SVG charts.** No external chart lib. Bar / line / area / pie
    rendered server-side with computed geometry from the actual data.
  - **HTML-escaped.** Every user-supplied string is escaped to prevent
    XSS in the standalone export and screenshot pipeline.

Phase 4 owns the transformer. Phase 4.5 (Day 8) consumes the artifact
to compute density / contrast scores. Phase 5 (Day 9-10) adds engine +
reveal_legacy artifacts that share the same animation_ir.

The module is intentionally self-contained: no imports from the kit
React source, no dependence on a browser. Just stdlib + design_system /
animation_ir helpers we already ship.
"""

from __future__ import annotations

import hashlib
import html as _stdhtml
import json
import math
from typing import Any, Iterable, Mapping, Sequence

from app.services.v4.motion_spec import build_seek_runtime_js


_SCHEMA_VERSION = 2
"""
Bumped when the *shape* of the html_css_js artifact changes (e.g. new
top-level keys). Independent from `fingerprint`, which is a content
hash for cache busting.
"""


# ── Lucide icon name → inline SVG path ───────────────────────────────
# We inline a small, hand-picked subset matching the icons the React
# kits actually use (Check, X, Minus, Quote, Linkedin) plus the icons
# referenced by FeatureGrid presets (Target, Zap, Rocket, Shield,
# Sparkles, Globe). Every path is the verbatim path data from the
# Lucide icons project (ISC license). Unknown icons fall through to a
# bullet dot — same fallback the React FeatureGrid uses.
_LUCIDE_PATHS: dict[str, str] = {
    "check": "M20 6 9 17l-5-5",
    "x": "M18 6 6 18 M6 6l12 12",
    "minus": "M5 12h14",
    "quote": (
        "M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 "
        "1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z "
        "M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 "
        "1.25.75 2 2 2 .85 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"
    ),
    "linkedin": (
        "M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-4 0v7h-4v-7a6 6 0 0 1 6-6z "
        "M2 9h4v12H2z M4 4a2 2 0 1 1 0 4 2 2 0 0 1 0-4z"
    ),
    "target": "M12 12m-10 0a10 10 0 1 0 20 0a10 10 0 1 0-20 0 M12 12m-6 0a6 6 0 1 0 12 0a6 6 0 1 0-12 0 M12 12m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0",
    "zap": "M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z",
    "rocket": (
        "M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z "
        "M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z "
        "M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0 M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"
    ),
    "shield": "M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z",
    "sparkles": "M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z",
    "globe": "M12 12m-10 0a10 10 0 1 0 20 0a10 10 0 1 0-20 0 M2 12h20 M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z",
}


# ── Helpers ──────────────────────────────────────────────────────────

def _esc(text: Any) -> str:
    """HTML-escape any value, coercing to str. None becomes empty."""
    if text is None:
        return ""
    return _stdhtml.escape(str(text), quote=True)


def _attr(name: str, value: Any) -> str:
    """Render a single HTML attribute (or empty string when value is falsy/None)."""
    if value is None or value is False or value == "":
        return ""
    if value is True:
        return f" {name}"
    return f' {name}="{_esc(value)}"'


def _classes(*items: Any) -> str:
    """Join a list of class names, dropping empties / falsies."""
    return " ".join(str(x) for x in items if x)


def _ir_class_for_target(animation_ir: Mapping[str, Any], target: str) -> str:
    """
    Look up the IR entry for a target name and return the matching CSS
    class name. Empty string if the target has no animation entry. The
    IR builder emits one class per `entry.id` of form `ir-anim-<id>`.
    """
    if not isinstance(animation_ir, Mapping):
        return ""
    entries = animation_ir.get("entries") or []
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        if entry.get("target") == target:
            entry_id = entry.get("id")
            if entry_id:
                return f"ir-anim-{entry_id}"
    return ""


def _ir_classes_for_target_group(
    animation_ir: Mapping[str, Any],
    target_prefix: str,
    index: int,
) -> str:
    """
    Look up the IR entry for a staggered child like `cards.3`. Returns
    `ir-anim-entry-cards-3` (matching the IR builder's stagger naming).
    """
    target = f"{target_prefix}.{index}"
    cls = _ir_class_for_target(animation_ir, target)
    if cls:
        return cls
    # Fall back to the parent target class (so static layout still matches
    # if a stagger entry is absent).
    return _ir_class_for_target(animation_ir, target_prefix)


def _coerce_str_list(value: Any) -> list[str]:
    """Defensive: accept list[str] / tuple / single str / None."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, Iterable):
        return [str(x) for x in value if x is not None and str(x).strip()]
    return []


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ── Per-kit renderers ────────────────────────────────────────────────
# Each renderer returns (html_body, extra_css, extra_js) where:
#   html_body : str   — the inner HTML inside <section class="slide">
#   extra_css : str   — CSS specific to this kit (appended after base CSS)
#   extra_js  : str   — JS for interactive bits (charts only); "" for most


def _render_title_hero(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[str, str, str]:
    headline = _esc(props.get("headline", ""))
    subheadline = _esc(props.get("subheadline", ""))
    eyebrow = _esc(props.get("eyebrow", ""))
    footer = _esc(props.get("footer", ""))
    logo_url = _esc(props.get("logoUrl", ""))
    image_url = _esc(props.get("imageUrl", ""))
    variant = props.get("variant") or "gradient"
    has_image = variant == "image" and bool(image_url)

    headline_class = _classes("slide-headline", _ir_class_for_target(ir, "headline"))
    sub_class = _classes("slide-subheadline", _ir_class_for_target(ir, "subheadline"))
    eyebrow_class = _classes("slide-eyebrow", _ir_class_for_target(ir, "eyebrow"))

    parts: list[str] = []
    if has_image:
        parts.append(f'<img class="slide-bleed-img" src="{image_url}" alt="" />')
        parts.append('<div class="slide-bleed-scrim"></div>')
    if logo_url:
        parts.append(f'<img class="slide-logo" src="{logo_url}" alt="" />')

    parts.append('<div class="slide-titlehero-stack">')
    if eyebrow:
        parts.append(
            f'<div class="{eyebrow_class}"><span class="chip chip-subtle">{eyebrow}</span></div>'
        )
    if headline:
        parts.append(f'<h1 class="{headline_class} slide-display">{headline}</h1>')
    if subheadline:
        parts.append(f'<p class="{sub_class} slide-sub">{subheadline}</p>')
    parts.append("</div>")

    if footer:
        footer_class = _classes("slide-footer", _ir_class_for_target(ir, "footer"))
        parts.append(f'<div class="{footer_class}"><span>{footer}</span></div>')

    body = "".join(parts)

    # Stage variant class lives at the section level; controlled by the
    # outer wrapper. We emit a small CSS hook here for the image variant.
    extra_css = """
.slide[data-variant="gradient"] {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%);
  color: var(--color-background);
}
.slide[data-variant="image"] { background: var(--color-background); }
.slide-bleed-img {
  position: absolute; inset: 0; width: 100%; height: 100%;
  object-fit: cover; z-index: 0;
}
.slide-bleed-scrim {
  position: absolute; inset: 0; z-index: 0;
  background: linear-gradient(120deg, rgba(0,0,0,.68) 0%, rgba(0,0,0,.35) 45%, rgba(0,0,0,.15) 100%);
}
.slide-logo {
  position: absolute; top: var(--space-margin); left: var(--space-margin);
  height: 36px; width: auto; z-index: 1;
}
.slide-titlehero-stack {
  position: relative; z-index: 1; max-width: 24ch;
  display: flex; flex-direction: column; gap: calc(var(--space-gap) * 1.4);
}
.slide-display {
  font-family: var(--font-heading);
  font-size: var(--type-display);
  font-weight: var(--weight-heading, 700);
  line-height: 1.05; letter-spacing: -0.02em; margin: 0;
}
.slide[data-variant="image"] .slide-display { color: #fff; }
.slide-sub {
  font-family: var(--font-body);
  font-size: var(--type-h3);
  color: var(--color-text-secondary);
  font-weight: 400; line-height: 1.35; max-width: 80ch; margin: 0;
}
.slide[data-variant="image"] .slide-sub { color: rgba(255,255,255,.82); }
.slide-eyebrow { display: block; }
.slide-footer {
  position: absolute; bottom: var(--space-margin);
  left: var(--space-margin); right: var(--space-margin);
  display: flex; justify-content: space-between;
  color: var(--color-text-muted);
  font-size: var(--type-caption); letter-spacing: 0.04em;
  z-index: 1;
}
.slide[data-variant="image"] .slide-footer { color: rgba(255,255,255,.7); }
"""
    return body, extra_css, ""


def _render_stat_hero(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[str, str, str]:
    eyebrow = _esc(props.get("eyebrow", ""))
    headline = _esc(props.get("headline", ""))
    subheadline = _esc(props.get("subheadline", ""))
    align = props.get("align") or "left"
    raw_stats = props.get("stats") or []
    stats = [s for s in raw_stats if isinstance(s, Mapping)]
    columns = max(1, min(len(stats), 4)) if stats else 1
    huge = len(stats) == 1

    parts: list[str] = []
    parts.append(f'<div class="stat-hero-head" data-align="{_esc(align)}">')
    if eyebrow:
        parts.append(f'<div class="caption">{eyebrow}</div>')
    if headline:
        parts.append(
            f'<h1 class="{_classes("slide-h1", _ir_class_for_target(ir, "headline"))}">{headline}</h1>'
        )
    if subheadline:
        parts.append(
            f'<p class="{_classes("slide-sub", _ir_class_for_target(ir, "subheadline"))}">{subheadline}</p>'
        )
    parts.append("</div>")

    if stats:
        parts.append(
            f'<div class="stat-grid" style="grid-template-columns: repeat({columns}, minmax(0, 1fr));">'
        )
        for i, s in enumerate(stats):
            value = _esc(s.get("value", ""))
            label = _esc(s.get("label", ""))
            delta = _esc(s.get("delta", ""))
            trend = (s.get("trend") or "up").lower()
            trend_cls = (
                "trend-down" if trend == "down"
                else "trend-flat" if trend == "flat"
                else "trend-up"
            )
            anim_cls = _ir_classes_for_target_group(ir, "stats", i)
            parts.append(f'<div class="{_classes("stat-cell", anim_cls)}">')
            parts.append(
                f'<div class="stat-value{(" stat-value-huge" if huge else "")}">{value}</div>'
            )
            if label:
                parts.append(f'<div class="stat-label">{label}</div>')
            if delta:
                parts.append(f'<div class="stat-delta {trend_cls}">{delta}</div>')
            parts.append("</div>")
        parts.append("</div>")

    body = "".join(parts)
    extra_css = """
.stat-hero-head[data-align="center"] { text-align: center; max-width: 70ch; margin: 0 auto; }
.stat-hero-head[data-align="left"]   { text-align: left;   max-width: 60ch; }
.slide-h1 {
  font-family: var(--font-heading); font-size: var(--type-h1);
  font-weight: var(--weight-heading, 700); color: var(--color-text-primary);
  line-height: 1.1; letter-spacing: -0.02em; margin: 0;
}
.slide-sub {
  margin: calc(var(--space-gap) * 1.2) 0 0 0;
  font-family: var(--font-body); font-size: var(--type-h3);
  color: var(--color-text-secondary); line-height: 1.35; max-width: 80ch;
}
.caption {
  font-family: var(--font-body); font-size: var(--type-caption);
  color: var(--color-text-muted); text-transform: uppercase;
  letter-spacing: 0.08em; font-weight: 500;
  margin-bottom: var(--space-gap);
}
.stat-grid {
  margin-top: var(--space-section-gap);
  display: grid; gap: calc(var(--space-gap) * 2);
  width: 100%; align-items: flex-start;
}
.stat-cell { display: flex; flex-direction: column; gap: 8px; }
.stat-value {
  font-family: var(--font-heading); font-size: var(--type-h1);
  font-weight: 700; color: var(--color-primary);
  line-height: 1; letter-spacing: -0.03em;
}
.stat-value-huge { font-size: var(--type-display); }
.stat-label {
  font-size: var(--type-body); color: var(--color-text-secondary);
  max-width: 22ch;
}
.stat-delta { font-size: var(--type-caption); font-weight: 600; }
.trend-up   { color: var(--color-success); }
.trend-down { color: var(--color-danger); }
.trend-flat { color: var(--color-text-muted); }
"""
    return body, extra_css, ""


def _render_chart_block(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[str, str, str]:
    headline = _esc(props.get("headline", ""))
    subheadline = _esc(props.get("subheadline", ""))
    source = _esc(props.get("source", ""))
    chart_type = (props.get("type") or "bar").lower()
    data = props.get("data") or []
    x_key = props.get("xKey") or "x"
    y_keys = _coerce_str_list(props.get("yKeys"))
    series_labels = props.get("seriesLabels") or {}
    value_key = props.get("valueKey") or (y_keys[0] if y_keys else "value")
    name_key = props.get("nameKey") or x_key

    chart_svg = _render_chart_svg(
        chart_type=chart_type,
        data=[d for d in data if isinstance(d, Mapping)],
        x_key=x_key,
        y_keys=y_keys,
        series_labels=series_labels if isinstance(series_labels, Mapping) else {},
        value_key=value_key,
        name_key=name_key,
    )

    head_class = _classes("chart-head", _ir_class_for_target(ir, "headline"))
    chart_class = _classes("chart-canvas", _ir_class_for_target(ir, "chart"))

    parts: list[str] = [f'<div class="{head_class}">']
    if headline:
        parts.append(f'<h2 class="slide-h2">{headline}</h2>')
    if subheadline:
        parts.append(f'<p class="slide-sub">{subheadline}</p>')
    parts.append("</div>")
    parts.append(f'<div class="{chart_class}">{chart_svg}</div>')
    if source:
        parts.append(f'<div class="chart-source">{source}</div>')

    body = "".join(parts)
    extra_css = """
.slide-h2 {
  font-family: var(--font-heading); font-size: var(--type-h2);
  font-weight: var(--weight-heading, 700); color: var(--color-text-primary);
  line-height: 1.15; letter-spacing: -0.015em; margin: 0;
}
.chart-head { margin-bottom: var(--space-gap); }
.chart-head .slide-sub { margin-top: calc(var(--space-gap) * 0.6); }
.chart-canvas { flex: 1; min-height: 0; width: 100%; }
.chart-canvas svg { width: 100%; height: 100%; display: block; }
.chart-source {
  margin-top: calc(var(--space-gap) * 0.8);
  font-size: var(--type-caption); color: var(--color-text-muted);
}
.chart-grid line { stroke: color-mix(in oklch, var(--color-text-muted) 25%, transparent); stroke-width: 1; }
.chart-axis text { fill: var(--color-text-muted); font-family: var(--font-body); font-size: 11px; }
.chart-bar       { transition: opacity .2s; }
.chart-bar:hover { opacity: 0.85; }
.chart-line      { fill: none; stroke-width: 2.5; }
.chart-area      { stroke: none; opacity: 0.30; }
.chart-pie-slice { stroke: var(--color-background); stroke-width: 2; }
.chart-legend    {
  display: flex; flex-wrap: wrap; gap: 16px;
  margin-top: 12px; font-size: var(--type-caption);
  color: var(--color-text-secondary);
}
.chart-legend-dot {
  display: inline-block; width: 10px; height: 10px;
  border-radius: 2px; margin-right: 6px; vertical-align: middle;
}
"""
    return body, extra_css, ""


def _render_timeline_block(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[str, str, str]:
    headline = _esc(props.get("headline", ""))
    subheadline = _esc(props.get("subheadline", ""))
    orientation = (props.get("orientation") or "horizontal").lower()
    raw_milestones = props.get("milestones") or []
    milestones = [m for m in raw_milestones if isinstance(m, Mapping)]
    horizontal = orientation == "horizontal"
    n = max(1, len(milestones))

    parts: list[str] = [f'<div class="{_classes("timeline-head", _ir_class_for_target(ir, "headline"))}">']
    if headline:
        parts.append(f'<h2 class="slide-h2">{headline}</h2>')
    if subheadline:
        parts.append(f'<p class="slide-sub">{subheadline}</p>')
    parts.append("</div>")

    grid_style = (
        f"grid-template-columns: repeat({n}, minmax(0, 1fr));" if horizontal else ""
    )
    parts.append(
        f'<div class="timeline" data-orient="{_esc(orientation)}" style="{grid_style}">'
    )
    parts.append('<div class="timeline-track"></div>')
    for i, m in enumerate(milestones):
        date = _esc(m.get("date", ""))
        title = _esc(m.get("title", ""))
        desc = _esc(m.get("description", ""))
        done = bool(m.get("done"))
        dot_cls = "timeline-dot " + ("done" if done else "pending")
        anim_cls = _ir_classes_for_target_group(ir, "milestones", i)
        parts.append(f'<div class="{_classes("timeline-item", anim_cls)}">')
        parts.append(f'<div class="{dot_cls}"></div>')
        parts.append('<div class="timeline-body">')
        if date:
            parts.append(f'<div class="timeline-date">{date}</div>')
        if title:
            parts.append(f'<div class="timeline-title">{title}</div>')
        if desc:
            parts.append(f'<div class="timeline-desc">{desc}</div>')
        parts.append("</div>")  # body
        parts.append("</div>")  # item
    parts.append("</div>")  # timeline

    body = "".join(parts)
    extra_css = """
.timeline-head { margin-bottom: calc(var(--space-section-gap) * 0.6); }
.timeline { position: relative; flex: 1; align-items: flex-start; gap: calc(var(--space-gap) * 1.5); }
.timeline[data-orient="horizontal"] { display: grid; }
.timeline[data-orient="vertical"]   { display: flex; flex-direction: column; }
.timeline-track {
  position: absolute; z-index: 0;
  background: color-mix(in oklch, var(--color-text-muted) 40%, transparent);
}
.timeline[data-orient="horizontal"] .timeline-track { left: 0; right: 0; top: 12px; height: 2px; }
.timeline[data-orient="vertical"]   .timeline-track { left: 11px; top: 0; bottom: 0; width: 2px; }
.timeline-item {
  position: relative; display: flex; gap: 10px; z-index: 1;
}
.timeline[data-orient="horizontal"] .timeline-item { flex-direction: column; align-items: flex-start; }
.timeline[data-orient="vertical"]   .timeline-item { flex-direction: row;    align-items: flex-start; gap: 16px; }
.timeline-dot {
  width: 24px; height: 24px; border-radius: 50%;
  border: 2px solid var(--color-primary); flex-shrink: 0;
}
.timeline-dot.done    { background: var(--color-primary); }
.timeline-dot.pending { background: var(--color-surface); }
.timeline-date {
  font-size: var(--type-caption); color: var(--color-primary);
  font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
}
.timeline-title {
  margin-top: 4px; font-family: var(--font-heading);
  font-size: var(--type-h3); font-weight: 600; color: var(--color-text-primary);
}
.timeline-desc {
  margin-top: 4px; font-size: var(--type-body);
  color: var(--color-text-secondary); max-width: 32ch;
}
"""
    return body, extra_css, ""


def _render_comparison_block(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[str, str, str]:
    headline = _esc(props.get("headline", ""))
    subheadline = _esc(props.get("subheadline", ""))
    raw_columns = props.get("columns") or []
    raw_rows = props.get("rows") or []
    columns = [c for c in raw_columns if isinstance(c, Mapping)]
    rows = [r for r in raw_rows if isinstance(r, Mapping)]
    n_cols = len(columns)

    parts: list[str] = [f'<div class="{_classes("comparison-head", _ir_class_for_target(ir, "headline"))}">']
    if headline:
        parts.append(f'<h2 class="slide-h2">{headline}</h2>')
    if subheadline:
        parts.append(f'<p class="slide-sub">{subheadline}</p>')
    parts.append("</div>")

    parts.append(
        f'<div class="comparison-grid" '
        f'style="grid-template-columns: minmax(160px, 1.4fr) repeat({max(1, n_cols)}, minmax(0, 1fr));">'
    )
    parts.append('<div class="cmp-cell cmp-header"></div>')
    for i, c in enumerate(columns):
        name = _esc(c.get("name", ""))
        tagline = _esc(c.get("tagline", ""))
        highlight = bool(c.get("highlight"))
        cls = "cmp-cell cmp-header" + (" highlight" if highlight else "")
        anim_cls = _ir_classes_for_target_group(ir, "columns", i)
        parts.append(f'<div class="{_classes(cls, anim_cls)}">')
        parts.append(f'<div class="cmp-col-name{(" hl" if highlight else "")}">{name}</div>')
        if tagline:
            parts.append(f'<div class="cmp-col-tag">{tagline}</div>')
        parts.append("</div>")

    for ri, r in enumerate(rows):
        feature = _esc(r.get("feature", ""))
        zebra_cls = " odd" if ri % 2 else ""
        parts.append(f'<div class="cmp-cell cmp-row{zebra_cls} cmp-feat">{feature}</div>')
        raw_values = r.get("values") or {}
        values_by_name = raw_values if isinstance(raw_values, Mapping) else {}
        values_list = raw_values if isinstance(raw_values, list) else []
        for ci, c in enumerate(columns):
            highlight = bool(c.get("highlight"))
            v = values_by_name.get(c.get("name")) if values_by_name else None
            if v is None and ci < len(values_list):
                v = values_list[ci]
            cls = (
                "cmp-cell cmp-row" + zebra_cls
                + (" highlight" if highlight else "")
            )
            parts.append(f'<div class="{cls}">{_render_cmp_value(v)}</div>')
    parts.append("</div>")

    body = "".join(parts)
    extra_css = """
.comparison-head { margin-bottom: calc(var(--space-section-gap) * 0.6); }
.comparison-grid {
  flex: 1; display: grid; gap: 0;
  border: 1px solid color-mix(in oklch, var(--color-text-muted) 25%, transparent);
  border-radius: 12px; overflow: hidden;
}
.cmp-cell { padding: calc(var(--space-gap) * 1.1); font-size: var(--type-body); }
.cmp-header {
  padding: calc(var(--space-gap) * 1.2);
  background: color-mix(in oklch, var(--color-surface) 70%, var(--color-background));
  border-left: 1px solid color-mix(in oklch, var(--color-text-muted) 25%, transparent);
}
.cmp-header.highlight { background: color-mix(in oklch, var(--color-primary) 20%, transparent); }
.cmp-row {
  border-top: 1px solid color-mix(in oklch, var(--color-text-muted) 18%, transparent);
  border-left: 1px solid color-mix(in oklch, var(--color-text-muted) 25%, transparent);
  color: var(--color-text-secondary);
  display: flex; align-items: center; gap: 8px;
}
.cmp-row.highlight { background: color-mix(in oklch, var(--color-primary) 8%, transparent); }
.cmp-row.odd       { background: color-mix(in oklch, var(--color-surface) 35%, transparent); }
.cmp-feat          { font-weight: 600; color: var(--color-text-primary); border-left: 0; }
.cmp-col-name {
  font-family: var(--font-heading); font-weight: 700;
  font-size: var(--type-h3); color: var(--color-text-primary);
}
.cmp-col-name.hl  { color: var(--color-primary); }
.cmp-col-tag      { margin-top: 4px; font-size: var(--type-caption); color: var(--color-text-muted); }
.cmp-icon         { display: inline-flex; }
.cmp-empty        { color: var(--color-text-muted); }
"""
    return body, extra_css, ""


def _render_cmp_value(v: Any) -> str:
    if v is True:
        return f'<span class="cmp-icon" style="color: var(--color-success);">{_svg_icon("check", 18)}</span>'
    if v is False:
        return f'<span class="cmp-icon" style="color: var(--color-danger);">{_svg_icon("x", 18)}</span>'
    if isinstance(v, str) and v.lower() == "partial":
        return f'<span class="cmp-icon" style="color: var(--color-warning);">{_svg_icon("minus", 18)}</span>'
    if v is None or (isinstance(v, str) and not v.strip()):
        return '<span class="cmp-empty">—</span>'
    return f"<span>{_esc(v)}</span>"


def _render_feature_grid(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[str, str, str]:
    headline = _esc(props.get("headline", ""))
    subheadline = _esc(props.get("subheadline", ""))
    raw_features = props.get("features") or []
    features = [f for f in raw_features if isinstance(f, Mapping)]
    columns_raw = props.get("columns")
    try:
        columns = int(columns_raw)
    except (TypeError, ValueError):
        columns = 3
    if columns not in (2, 3, 4):
        columns = 3

    parts: list[str] = [f'<div class="{_classes("fg-head", _ir_class_for_target(ir, "headline"))}">']
    if headline:
        parts.append(f'<h2 class="slide-h2">{headline}</h2>')
    if subheadline:
        parts.append(f'<p class="slide-sub">{subheadline}</p>')
    parts.append("</div>")

    parts.append(
        f'<div class="fg-grid" style="grid-template-columns: repeat({columns}, minmax(0, 1fr));">'
    )
    for i, f in enumerate(features):
        title = _esc(f.get("title", ""))
        desc = _esc(f.get("description", ""))
        icon_name = (f.get("icon") or "").strip()
        icon_svg = _svg_icon(_normalize_icon_name(icon_name), 22)
        anim_cls = _ir_classes_for_target_group(ir, "features", i)
        parts.append(f'<div class="{_classes("fg-card", anim_cls)}">')
        parts.append(f'<div class="fg-icon">{icon_svg}</div>')
        if title:
            parts.append(f'<div class="fg-title">{title}</div>')
        if desc:
            parts.append(f'<div class="fg-desc">{desc}</div>')
        parts.append("</div>")
    parts.append("</div>")

    body = "".join(parts)
    extra_css = """
.fg-head { margin-bottom: calc(var(--space-section-gap) * 0.7); max-width: 60ch; }
.fg-grid { display: grid; gap: calc(var(--space-gap) * 2); flex: 1; align-content: flex-start; }
.fg-card {
  display: flex; flex-direction: column; gap: 12px;
  padding: calc(var(--space-gap) * 1.3);
  background: color-mix(in oklch, var(--color-surface) 70%, var(--color-background));
  border: 1px solid color-mix(in oklch, var(--color-text-muted) 20%, transparent);
  border-radius: 16px;
}
.fg-icon {
  width: 44px; height: 44px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 12px;
  background: color-mix(in oklch, var(--color-primary) 16%, transparent);
  color: var(--color-primary);
}
.fg-title {
  font-family: var(--font-heading); font-weight: 700;
  font-size: var(--type-h3); color: var(--color-text-primary); line-height: 1.2;
}
.fg-desc { font-size: var(--type-body); color: var(--color-text-secondary); line-height: 1.45; }
"""
    return body, extra_css, ""


def _render_team_grid(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[str, str, str]:
    headline = _esc(props.get("headline", ""))
    subheadline = _esc(props.get("subheadline", ""))
    raw_members = props.get("members") or []
    members = [m for m in raw_members if isinstance(m, Mapping)]
    columns_raw = props.get("columns")
    try:
        columns = int(columns_raw)
    except (TypeError, ValueError):
        columns = 3
    if columns not in (2, 3, 4):
        columns = 3

    parts: list[str] = [f'<div class="{_classes("team-head", _ir_class_for_target(ir, "headline"))}">']
    if headline:
        parts.append(f'<h2 class="slide-h2">{headline}</h2>')
    if subheadline:
        parts.append(f'<p class="slide-sub">{subheadline}</p>')
    parts.append("</div>")

    parts.append(
        f'<div class="team-grid" style="grid-template-columns: repeat({columns}, minmax(0, 1fr));">'
    )
    for i, m in enumerate(members):
        name = _esc(m.get("name", ""))
        role = _esc(m.get("role", ""))
        bio = _esc(m.get("bio", ""))
        photo = _esc(m.get("photoUrl", ""))
        linkedin = _esc(m.get("linkedInUrl", ""))
        initials = _initials(m.get("name", ""))
        avatar = (
            f'<img class="team-avatar" src="{photo}" alt="{name}" />'
            if photo
            else f'<div class="team-avatar team-avatar-fallback">{_esc(initials)}</div>'
        )
        anim_cls = _ir_classes_for_target_group(ir, "members", i)
        parts.append(f'<div class="{_classes("team-card", anim_cls)}">')
        parts.append(avatar)
        parts.append('<div class="team-info">')
        if name:
            parts.append(f'<div class="team-name">{name}</div>')
        if role:
            parts.append(f'<div class="team-role">{role}</div>')
        if bio:
            parts.append(f'<div class="team-bio">{bio}</div>')
        if linkedin:
            parts.append(
                f'<a class="team-li" href="{linkedin}" target="_blank" rel="noreferrer noopener">'
                f'{_svg_icon("linkedin", 14)}<span>LinkedIn</span></a>'
            )
        parts.append("</div>")  # info
        parts.append("</div>")  # card
    parts.append("</div>")
    body = "".join(parts)

    extra_css = """
.team-head { margin-bottom: calc(var(--space-section-gap) * 0.7); }
.team-grid { display: grid; gap: calc(var(--space-gap) * 2); flex: 1; align-content: flex-start; }
.team-card { display: flex; flex-direction: column; align-items: flex-start; gap: 12px; }
.team-avatar {
  width: 72px; height: 72px; border-radius: 50%;
  object-fit: cover; flex-shrink: 0; overflow: hidden;
  background: color-mix(in oklch, var(--color-primary) 25%, var(--color-surface));
}
.team-avatar-fallback {
  display: flex; align-items: center; justify-content: center;
  color: var(--color-primary); font-family: var(--font-heading);
  font-weight: 700; font-size: 26px;
}
.team-name {
  font-family: var(--font-heading); font-weight: 700;
  font-size: var(--type-h3); color: var(--color-text-primary); line-height: 1.15;
}
.team-role {
  margin-top: 2px; font-size: var(--type-body);
  color: var(--color-primary); font-weight: 600;
}
.team-bio {
  margin-top: 8px; font-size: var(--type-body);
  color: var(--color-text-secondary); line-height: 1.45; max-width: 32ch;
}
.team-li {
  display: inline-flex; align-items: center; gap: 6px; margin-top: 8px;
  color: var(--color-text-muted); font-size: var(--type-caption);
  text-decoration: none;
}
"""
    return body, extra_css, ""


def _render_quote_block(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[str, str, str]:
    quote = _esc(props.get("quote", ""))
    attribution = _esc(props.get("attribution", ""))
    role = _esc(props.get("role", ""))
    photo = _esc(props.get("photoUrl", ""))
    variant = (props.get("variant") or "default").lower()

    quote_cls = _classes("qb-card", _ir_class_for_target(ir, "quote") or _ir_class_for_target(ir, "headline"))
    parts: list[str] = [f'<div class="qb-wrap" data-variant="{_esc(variant)}">']
    parts.append(f'<div class="{quote_cls}">')
    parts.append(f'<div class="qb-mark">{_svg_icon("quote", 48)}</div>')
    if quote:
        parts.append(f'<div class="qb-text">&ldquo;{quote}&rdquo;</div>')
    parts.append('<div class="qb-attrib-wrap">')
    if photo:
        parts.append(f'<img class="qb-photo" src="{photo}" alt="" />')
    parts.append('<div class="qb-attrib">')
    if attribution:
        parts.append(f'<div class="qb-name">{attribution}</div>')
    if role:
        parts.append(f'<div class="qb-role">{role}</div>')
    parts.append("</div></div></div></div>")
    body = "".join(parts)

    extra_css = """
.qb-wrap {
  display: flex; align-items: center; justify-content: center;
  width: 100%; height: 100%;
}
.qb-wrap[data-variant="accent"] {
  background: var(--color-accent); color: var(--color-background);
}
.qb-card {
  max-width: 64ch; text-align: center;
  display: flex; flex-direction: column; align-items: center;
  gap: calc(var(--space-gap) * 1.6);
}
.qb-mark { color: var(--color-primary); opacity: 0.8; }
.qb-wrap[data-variant="accent"] .qb-mark { color: var(--color-background); }
.qb-text {
  font-family: var(--font-heading); font-size: var(--type-h1);
  font-weight: 500; line-height: 1.22;
  color: var(--color-text-primary); letter-spacing: -0.015em;
}
.qb-wrap[data-variant="accent"] .qb-text { color: var(--color-background); }
.qb-attrib-wrap {
  display: flex; align-items: center; gap: 12px;
  margin-top: calc(var(--space-gap) * 0.6);
}
.qb-photo { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; }
.qb-attrib { text-align: left; }
.qb-name {
  font-family: var(--font-heading); font-weight: 700;
  font-size: var(--type-body); color: var(--color-text-primary);
}
.qb-wrap[data-variant="accent"] .qb-name { color: var(--color-background); }
.qb-role { font-size: var(--type-caption); color: var(--color-text-muted); }
.qb-wrap[data-variant="accent"] .qb-role {
  color: color-mix(in oklch, var(--color-background) 75%, transparent);
}
"""
    return body, extra_css, ""


def _render_data_table(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[str, str, str]:
    headline = _esc(props.get("headline", ""))
    subheadline = _esc(props.get("subheadline", ""))
    headers = [str(h) for h in (props.get("headers") or []) if str(h).strip()]
    raw_rows = props.get("rows") or []
    rows: list[list[str]] = []
    if isinstance(raw_rows, list):
        for row in raw_rows:
            if not isinstance(row, (list, tuple)):
                continue
            cells = [str(cell) for cell in row]
            if any(cell.strip() for cell in cells):
                rows.append(cells)

    head_cls = _classes("dt-head", _ir_class_for_target(ir, "headline"))
    table_cls = _classes("dt-table", _ir_class_for_target(ir, "table"))
    parts: list[str] = ['<div class="dt-wrap">']
    if headline or subheadline:
        parts.append(f'<header class="{head_cls}">')
        if headline:
            parts.append(f'<h1>{headline}</h1>')
        if subheadline:
            parts.append(f'<p>{subheadline}</p>')
        parts.append("</header>")
    if headers and rows:
        parts.append(f'<table class="{table_cls}"><thead><tr>')
        for header in headers:
            parts.append(f"<th>{_esc(header)}</th>")
        parts.append("</tr></thead><tbody>")
        for ri, row in enumerate(rows[:7]):
            anim_cls = _ir_classes_for_target_group(ir, "rows", ri)
            parts.append(f'<tr class="{_esc(anim_cls)}">')
            for ci, _header in enumerate(headers):
                cell = row[ci] if ci < len(row) else ""
                parts.append(f"<td>{_esc(cell)}</td>")
            parts.append("</tr>")
        parts.append("</tbody></table>")
    parts.append("</div>")
    body = "".join(parts)

    extra_css = """
.dt-wrap {
  display: grid; grid-template-rows: auto 1fr; gap: calc(var(--space-gap) * 1.3);
  width: 100%; height: 100%;
}
.dt-head { max-width: 78ch; }
.dt-head h1 {
  margin: 0; font-family: var(--font-heading); font-size: var(--type-h1);
  line-height: 1.08; color: var(--color-text-primary);
}
.dt-head p {
  margin: calc(var(--space-gap) * .55) 0 0; font-size: var(--type-body);
  color: var(--color-text-secondary); line-height: 1.4;
}
.dt-table {
  width: 100%; border-collapse: collapse; align-self: stretch;
  background: color-mix(in oklch, var(--color-surface) 82%, var(--color-primary) 6%);
  border: 1px solid color-mix(in oklch, var(--color-border) 64%, transparent);
}
.dt-table th, .dt-table td {
  padding: clamp(10px, 1.2vw, 18px); text-align: left; vertical-align: top;
  border-bottom: 1px solid color-mix(in oklch, var(--color-border) 50%, transparent);
}
.dt-table th {
  color: var(--color-primary); font-family: var(--font-heading);
  font-size: var(--type-caption); letter-spacing: .08em; text-transform: uppercase;
}
.dt-table td {
  color: var(--color-text-secondary); font-size: clamp(14px, 1.2vw, 20px);
  line-height: 1.38;
}
.dt-table td:first-child {
  color: var(--color-text-primary); font-weight: 700;
}
.dt-table tbody tr:last-child td { border-bottom: 0; }
"""
    return body, extra_css, ""


def _render_full_bleed_image(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[str, str, str]:
    image_url = _esc(props.get("imageUrl", ""))
    headline = _esc(props.get("headline", ""))
    subheadline = _esc(props.get("subheadline", ""))
    caption = _esc(props.get("caption", ""))
    overlay = (props.get("overlay") or "scrim-bottom").lower()
    align = (props.get("align") or "bottom-left").lower()

    img_cls = _classes("fb-img", _ir_class_for_target(ir, "image"))
    text_cls = _classes("fb-text", _ir_class_for_target(ir, "headline"))

    parts: list[str] = ['<div class="fb-wrap">']
    if image_url:
        parts.append(f'<img class="{img_cls}" src="{image_url}" alt="" data-overlay="{_esc(overlay)}" />')
    if overlay != "none":
        parts.append(f'<div class="fb-scrim" data-overlay="{_esc(overlay)}"></div>')
    if headline or subheadline or caption:
        parts.append(f'<div class="{text_cls}" data-align="{_esc(align)}">')
        if headline:
            parts.append(f'<div class="fb-headline">{headline}</div>')
        if subheadline:
            parts.append(f'<div class="fb-sub">{subheadline}</div>')
        if caption:
            parts.append(f'<div class="fb-caption">{caption}</div>')
        parts.append("</div>")
    parts.append("</div>")
    body = "".join(parts)

    extra_css = """
.fb-wrap {
  position: relative; width: 100%; height: 100%;
  overflow: hidden; background: var(--color-background);
}
.fb-img {
  position: absolute; inset: 0; width: 100%; height: 100%;
  object-fit: cover;
}
.fb-img[data-overlay="duotone"] { filter: saturate(0.2) contrast(1.1); }
.fb-scrim { position: absolute; inset: 0; }
.fb-scrim[data-overlay="scrim-bottom"] {
  background: linear-gradient(to top, rgba(0,0,0,.78) 0%, rgba(0,0,0,.25) 55%, rgba(0,0,0,0) 100%);
}
.fb-scrim[data-overlay="scrim-full"] { background: rgba(0,0,0,0.45); }
.fb-scrim[data-overlay="duotone"] {
  background: linear-gradient(135deg,
    color-mix(in oklch, var(--color-primary) 55%, transparent) 0%,
    color-mix(in oklch, var(--color-accent) 55%, transparent) 100%);
}
.fb-text {
  position: absolute; inset: var(--space-margin);
  display: flex; flex-direction: column;
  color: #fff; z-index: 2; max-width: 60ch;
}
.fb-text[data-align="bottom-left"]  { justify-content: flex-end; align-items: flex-start; text-align: left; }
.fb-text[data-align="bottom-right"] { justify-content: flex-end; align-items: flex-end;   text-align: right; }
.fb-text[data-align="left"]   { justify-content: flex-start; align-items: flex-start; text-align: left; }
.fb-text[data-align="right"]  { justify-content: flex-start; align-items: flex-end;   text-align: right; }
.fb-text[data-align="center"] { justify-content: center;     align-items: center;     text-align: center; }
.fb-headline {
  font-family: var(--font-heading); font-size: var(--type-display);
  font-weight: var(--weight-heading, 700); line-height: 1.05;
  letter-spacing: -0.02em; text-shadow: 0 2px 20px rgba(0,0,0,.35);
}
.fb-sub {
  margin-top: calc(var(--space-gap) * 1.1);
  font-size: var(--type-h3); color: rgba(255,255,255,.88);
  line-height: 1.3; max-width: 56ch;
}
.fb-caption {
  margin-top: calc(var(--space-gap) * 2);
  font-size: var(--type-caption); color: rgba(255,255,255,.7);
  letter-spacing: 0.06em; text-transform: uppercase;
}
"""
    return body, extra_css, ""


def _render_diagram_block(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[str, str, str]:
    headline = _esc(props.get("headline", ""))
    subheadline = _esc(props.get("subheadline", ""))
    raw_nodes = props.get("nodes") or []
    raw_edges = props.get("edges") or []
    nodes = [n for n in raw_nodes if isinstance(n, Mapping) and n.get("id")]
    edges = [e for e in raw_edges if isinstance(e, Mapping)]
    by_id = {n["id"]: n for n in nodes}

    # Coordinate space: 1000 x 560 viewBox, with 20px padding inside.
    # Nodes are positioned via fractional (x, y) in [0, 1].
    VBW, VBH, PAD = 1000, 560, 24
    NODE_W, NODE_H = 180, 64

    def _node_pos(n: Mapping[str, Any]) -> tuple[float, float]:
        x = _coerce_float(n.get("x"), 0.5)
        y = _coerce_float(n.get("y"), 0.5)
        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))
        cx = PAD + (VBW - 2 * PAD) * x
        cy = PAD + (VBH - 2 * PAD) * y
        return cx, cy

    edge_svgs: list[str] = []
    for e in edges:
        src = by_id.get(e.get("from"))
        dst = by_id.get(e.get("to"))
        if not src or not dst:
            continue
        x1, y1 = _node_pos(src)
        x2, y2 = _node_pos(dst)
        style = (e.get("style") or "solid").lower()
        dash = "4 6" if style == "dashed" else "0"
        label = _esc(e.get("label") or "")
        # End-cap arrow.
        edge_svgs.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="var(--color-text-muted)" stroke-width="2" stroke-dasharray="{dash}" '
            f'marker-end="url(#diagram-arrow)" />'
        )
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            edge_svgs.append(
                f'<rect x="{mx - 50:.1f}" y="{my - 12:.1f}" width="100" height="24" '
                f'rx="12" fill="var(--color-surface)" stroke="var(--color-text-muted)" stroke-opacity="0.3" />'
                f'<text x="{mx:.1f}" y="{my + 4:.1f}" text-anchor="middle" '
                f'fill="var(--color-text-secondary)" font-size="12">{label}</text>'
            )

    node_svgs: list[str] = []
    for i, n in enumerate(nodes):
        cx, cy = _node_pos(n)
        x = cx - NODE_W / 2
        y = cy - NODE_H / 2
        variant = (n.get("variant") or "secondary").lower()
        fill = {
            "primary": "var(--color-primary)",
            "muted": "color-mix(in oklch, var(--color-text-muted) 18%, transparent)",
        }.get(variant, "var(--color-surface)")
        text_color = "var(--color-background)" if variant == "primary" else "var(--color-text-primary)"
        anim_cls = _ir_classes_for_target_group(ir, "nodes", i)
        node_svgs.append(
            f'<g class="{_classes("diagram-node", anim_cls)}">'
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{NODE_W}" height="{NODE_H}" '
            f'rx="12" fill="{fill}" stroke="var(--color-text-muted)" stroke-opacity="0.25" />'
            f'<text x="{cx:.1f}" y="{cy + 5:.1f}" text-anchor="middle" '
            f'fill="{text_color}" font-family="var(--font-heading)" font-weight="600" font-size="15">'
            f'{_esc(n.get("label", ""))}</text>'
            f'</g>'
        )

    svg = (
        f'<svg viewBox="0 0 {VBW} {VBH}" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">'
        '<defs><marker id="diagram-arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="var(--color-text-muted)"/></marker></defs>'
        + "".join(edge_svgs)
        + "".join(node_svgs)
        + "</svg>"
    )

    parts: list[str] = [f'<div class="{_classes("diagram-head", _ir_class_for_target(ir, "headline"))}">']
    if headline:
        parts.append(f'<h2 class="slide-h2">{headline}</h2>')
    if subheadline:
        parts.append(f'<p class="slide-sub">{subheadline}</p>')
    parts.append("</div>")
    parts.append(f'<div class="diagram-canvas">{svg}</div>')
    body = "".join(parts)

    extra_css = """
.diagram-head { margin-bottom: calc(var(--space-section-gap) * 0.5); }
.diagram-canvas { flex: 1; min-height: 0; width: 100%; }
.diagram-canvas svg { width: 100%; height: 100%; display: block; }
"""
    return body, extra_css, ""


# ── SVG chart renderer ───────────────────────────────────────────────
# Real geometry, no external lib. Reads colors from `--color-chart-N`
# CSS variables so themes auto-apply.

_CHART_W = 1000.0
_CHART_H = 480.0
_CHART_PAD_L = 56.0
_CHART_PAD_R = 24.0
_CHART_PAD_T = 16.0
_CHART_PAD_B = 44.0


def _render_chart_svg(
    *,
    chart_type: str,
    data: list[Mapping[str, Any]],
    x_key: str,
    y_keys: list[str],
    series_labels: Mapping[str, Any],
    value_key: str,
    name_key: str,
) -> str:
    if not data:
        return _empty_chart_svg("No data")

    if chart_type == "pie":
        return _svg_pie(data=data, value_key=value_key, name_key=name_key)
    if chart_type == "radar":
        # Radar is uncommon; render as a labelled polygon for the MVP.
        return _svg_radar(data=data, x_key=x_key, value_key=value_key)
    # bar / line / area share the same axes/scales.
    return _svg_xy(
        chart_type=chart_type, data=data, x_key=x_key, y_keys=y_keys,
        series_labels=series_labels,
    )


def _empty_chart_svg(message: str) -> str:
    return (
        f'<svg viewBox="0 0 {_CHART_W:.0f} {_CHART_H:.0f}" xmlns="http://www.w3.org/2000/svg">'
        f'<text x="{_CHART_W / 2:.0f}" y="{_CHART_H / 2:.0f}" text-anchor="middle" '
        f'fill="var(--color-text-muted)" font-size="14">{_esc(message)}</text></svg>'
    )


def _svg_xy(
    *,
    chart_type: str,
    data: list[Mapping[str, Any]],
    x_key: str,
    y_keys: list[str],
    series_labels: Mapping[str, Any],
) -> str:
    keys = y_keys or [k for k in data[0].keys() if k != x_key and isinstance(data[0][k], (int, float))]
    if not keys:
        return _empty_chart_svg("No numeric series")

    # Compute scales over real data.
    all_vals: list[float] = []
    for d in data:
        for k in keys:
            v = d.get(k)
            if isinstance(v, (int, float)):
                all_vals.append(float(v))
    y_max = max(all_vals) if all_vals else 1.0
    y_min = min(0.0, min(all_vals)) if all_vals else 0.0
    if math.isclose(y_max, y_min):
        y_max = y_min + 1.0
    plot_w = _CHART_W - _CHART_PAD_L - _CHART_PAD_R
    plot_h = _CHART_H - _CHART_PAD_T - _CHART_PAD_B

    def _y(v: float) -> float:
        return _CHART_PAD_T + plot_h - (v - y_min) / (y_max - y_min) * plot_h

    def _x_band(i: int, n: int, k_idx: int = 0, k_n: int = 1) -> float:
        # Centered points / grouped bars.
        band = plot_w / max(1, n)
        if k_n <= 1:
            return _CHART_PAD_L + band * (i + 0.5)
        # Grouped bar mode → split each band evenly across series.
        return _CHART_PAD_L + band * i + (band * 0.1) + (band * 0.8) * (k_idx + 0.5) / k_n

    # Y gridlines + labels (5 ticks).
    grid: list[str] = []
    for t in range(5):
        v = y_min + (y_max - y_min) * t / 4
        y = _y(v)
        grid.append(
            f'<line class="chart-grid-line" x1="{_CHART_PAD_L}" y1="{y:.1f}" '
            f'x2="{_CHART_W - _CHART_PAD_R}" y2="{y:.1f}" />'
        )
        grid.append(
            f'<text x="{_CHART_PAD_L - 10:.0f}" y="{y + 4:.1f}" text-anchor="end">{_format_axis_value(v)}</text>'
        )

    # X labels (cap at 12 to avoid overlap).
    x_step = max(1, len(data) // 12) if len(data) > 12 else 1
    x_labels: list[str] = []
    for i, d in enumerate(data):
        if i % x_step != 0:
            continue
        cx = _x_band(i, len(data))
        label = _esc(d.get(x_key, ""))
        x_labels.append(
            f'<text x="{cx:.1f}" y="{_CHART_H - _CHART_PAD_B + 18:.0f}" text-anchor="middle">{label}</text>'
        )

    # Series.
    series_svgs: list[str] = []
    if chart_type == "bar":
        for ki, k in enumerate(keys):
            color = f"var(--color-chart-{ki + 1}, #2563eb)"
            for i, d in enumerate(data):
                v = d.get(k)
                if not isinstance(v, (int, float)):
                    continue
                cx = _x_band(i, len(data), ki, len(keys))
                bar_w = (plot_w / len(data)) * 0.8 / max(1, len(keys))
                y_top = _y(float(v))
                y_zero = _y(0.0)
                y_bar = min(y_top, y_zero)
                h = abs(y_top - y_zero)
                series_svgs.append(
                    f'<rect class="chart-bar" x="{cx - bar_w / 2:.1f}" y="{y_bar:.1f}" '
                    f'width="{bar_w:.1f}" height="{h:.1f}" rx="2" fill="{color}" />'
                )
    else:
        # line / area
        for ki, k in enumerate(keys):
            color = f"var(--color-chart-{ki + 1}, #2563eb)"
            pts: list[tuple[float, float]] = []
            for i, d in enumerate(data):
                v = d.get(k)
                if not isinstance(v, (int, float)):
                    continue
                pts.append((_x_band(i, len(data)), _y(float(v))))
            if not pts:
                continue
            d_attr = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            if chart_type == "area":
                area_d = (
                    f"{d_attr} L {pts[-1][0]:.1f},{_y(0.0):.1f} L {pts[0][0]:.1f},{_y(0.0):.1f} Z"
                )
                series_svgs.append(
                    f'<path class="chart-area" d="{area_d}" fill="{color}" />'
                )
            series_svgs.append(
                f'<path class="chart-line" d="{d_attr}" stroke="{color}" />'
            )
            for x, y in pts:
                series_svgs.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}" />'
                )

    legend_html = _legend_for_keys(keys, series_labels)

    svg = (
        f'<svg class="chart-svg" viewBox="0 0 {_CHART_W:.0f} {_CHART_H:.0f}" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">'
        f'<g class="chart-grid">{"".join(grid)}</g>'
        f'<g class="chart-axis">{"".join(x_labels)}</g>'
        f'<g class="chart-series">{"".join(series_svgs)}</g>'
        "</svg>" + legend_html
    )
    return svg


def _svg_pie(
    *, data: list[Mapping[str, Any]], value_key: str, name_key: str
) -> str:
    items: list[tuple[str, float]] = []
    for d in data:
        v = d.get(value_key)
        if isinstance(v, (int, float)) and float(v) > 0:
            items.append((str(d.get(name_key, "")), float(v)))
    if not items:
        return _empty_chart_svg("No positive values")

    total = sum(v for _, v in items)
    cx, cy, r = _CHART_W / 2, _CHART_H / 2, min(_CHART_W, _CHART_H) * 0.38
    start = -math.pi / 2  # 12 o'clock
    paths: list[str] = []
    legend_keys: list[str] = []
    for i, (name, value) in enumerate(items):
        sweep = (value / total) * 2 * math.pi
        end = start + sweep
        large = 1 if sweep > math.pi else 0
        x1, y1 = cx + r * math.cos(start), cy + r * math.sin(start)
        x2, y2 = cx + r * math.cos(end), cy + r * math.sin(end)
        d_attr = (
            f"M {cx:.1f},{cy:.1f} L {x1:.1f},{y1:.1f} "
            f"A {r:.1f},{r:.1f} 0 {large} 1 {x2:.1f},{y2:.1f} Z"
        )
        color = f"var(--color-chart-{i + 1}, #2563eb)"
        paths.append(f'<path class="chart-pie-slice" d="{d_attr}" fill="{color}" />')
        legend_keys.append(name)
        start = end

    legend_html = _legend_for_keys(legend_keys, {})
    svg = (
        f'<svg class="chart-svg" viewBox="0 0 {_CHART_W:.0f} {_CHART_H:.0f}" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">'
        f'{"".join(paths)}</svg>{legend_html}'
    )
    return svg


def _svg_radar(
    *, data: list[Mapping[str, Any]], x_key: str, value_key: str
) -> str:
    if len(data) < 3:
        return _empty_chart_svg("Radar requires ≥3 axes")
    cx, cy = _CHART_W / 2, _CHART_H / 2
    r = min(_CHART_W, _CHART_H) * 0.36
    n = len(data)
    raw_vals = [_coerce_float(d.get(value_key)) for d in data]
    v_max = max(raw_vals) if raw_vals else 1.0
    if v_max <= 0:
        v_max = 1.0
    pts: list[tuple[float, float]] = []
    grid: list[str] = []
    labels: list[str] = []
    for i, d in enumerate(data):
        angle = -math.pi / 2 + (2 * math.pi * i) / n
        scale = raw_vals[i] / v_max
        px = cx + r * scale * math.cos(angle)
        py = cy + r * scale * math.sin(angle)
        pts.append((px, py))
        # Axis line + label
        ax = cx + r * math.cos(angle)
        ay = cy + r * math.sin(angle)
        grid.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{ax:.1f}" y2="{ay:.1f}" '
            f'stroke="var(--color-text-muted)" stroke-opacity="0.3" />'
        )
        labels.append(
            f'<text x="{ax:.1f}" y="{ay:.1f}" text-anchor="middle" dy="-6" '
            f'fill="var(--color-text-muted)" font-size="11">{_esc(d.get(x_key, ""))}</text>'
        )
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return (
        f'<svg class="chart-svg" viewBox="0 0 {_CHART_W:.0f} {_CHART_H:.0f}" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">'
        f'{"".join(grid)}'
        f'<polygon points="{poly}" fill="var(--color-chart-1, #2563eb)" fill-opacity="0.3" '
        f'stroke="var(--color-chart-1, #2563eb)" stroke-width="2" />'
        f'{"".join(labels)}</svg>'
    )


def _legend_for_keys(keys: Sequence[str], labels: Mapping[str, Any]) -> str:
    if len(keys) < 2:
        return ""
    items: list[str] = []
    for ki, k in enumerate(keys):
        label = _esc(labels.get(k, k))
        color = f"var(--color-chart-{ki + 1}, #2563eb)"
        items.append(
            f'<span><span class="chart-legend-dot" style="background:{color};"></span>{label}</span>'
        )
    return f'<div class="chart-legend">{"".join(items)}</div>'


def _format_axis_value(v: float) -> str:
    av = abs(v)
    if av >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if av >= 1_000:
        return f"{v / 1_000:.1f}K"
    if av >= 100 or av == 0:
        return f"{v:.0f}"
    if av >= 10:
        return f"{v:.1f}"
    return f"{v:.2f}"


# ── Icon helpers ─────────────────────────────────────────────────────

def _normalize_icon_name(name: str) -> str:
    if not name:
        return ""
    n = name.split(":")[-1].strip().lower()
    return n


def _svg_icon(name: str, size: int = 18) -> str:
    """Return an inline Lucide-stroke SVG, or empty if unknown."""
    path = _LUCIDE_PATHS.get(_normalize_icon_name(name))
    if not path:
        # Bullet dot fallback — same shape FeatureGrid uses in React.
        half = size // 4
        return (
            f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
            'xmlns="http://www.w3.org/2000/svg">'
            f'<circle cx="{size / 2}" cy="{size / 2}" r="{half}" fill="currentColor"/></svg>'
        )
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg">'
        f'<path d="{path}"/></svg>'
    )


def _initials(name: str) -> str:
    if not name:
        return "?"
    parts = [p for p in name.strip().split() if p]
    if not parts:
        return "?"
    return "".join(p[0] for p in parts[:2]).upper()


# ── Base CSS ─────────────────────────────────────────────────────────
# Page-level resets, slide-stage layout, animation utility hooks.
# Per-kit CSS is appended to this string by the renderer dispatch.

_BASE_CSS = """
*, *::before, *::after { box-sizing: border-box; }
html, body { margin: 0; padding: 0; height: 100%; background: var(--color-background); }
.slide {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  padding: var(--space-margin);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-family: var(--font-body);
  font-size: var(--type-body);
  line-height: var(--line-height, 1.4);
  letter-spacing: var(--letter-spacing, 0);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.slide.is-presenting { aspect-ratio: auto; height: 100vh; }
.chip {
  display: inline-flex; align-items: center;
  padding: 4px 12px; border-radius: 999px;
  font-size: var(--type-caption); font-weight: 600;
}
.chip-subtle {
  background: color-mix(in oklch, var(--color-primary) 18%, transparent);
  color: var(--color-primary);
}
.chip-primary { background: var(--color-primary); color: var(--color-background); }
.chip-accent  { background: var(--color-accent);  color: var(--color-background); }
"""


# ── Public API ───────────────────────────────────────────────────────

_KIT_RENDERERS = {
    "TitleHero":       _render_title_hero,
    "StatHero":        _render_stat_hero,
    "ChartBlock":      _render_chart_block,
    "TimelineBlock":   _render_timeline_block,
    "ComparisonBlock": _render_comparison_block,
    "FeatureGrid":     _render_feature_grid,
    "GlassCard":       _render_feature_grid,
    "BentoGrid":       _render_feature_grid,
    "ValuePropGrid":   _render_feature_grid,
    "ProblemSolution": _render_feature_grid,
    "DataTable":       _render_data_table,
    "TeamGrid":        _render_team_grid,
    "QuoteBlock":      _render_quote_block,
    "FullBleedImage":  _render_full_bleed_image,
    "DiagramBlock":    _render_diagram_block,
}


def build_html_css_js(
    *,
    kit: str,
    props: Mapping[str, Any],
    animation_ir: Mapping[str, Any] | None = None,
    design_system: Mapping[str, Any] | None = None,
    slide_id: str | None = None,
    deck_title: str | None = None,
    motion_spec: Mapping[str, Any] | None = None,
    layer_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build the `html_css_js` artifact.

    Parameters
    ----------
    kit : str
        One of the 10 supported kit components (TitleHero, StatHero, …).
    props : Mapping[str, Any]
        The exact props the kit React component would receive — same
        shape that lives in `kit_jsx_artifact.props_json`.
    animation_ir : Mapping[str, Any] | None
        The Phase 3 AnimationIR dict (`{version, fingerprint, entries,
        css, motion_props, …}`). Pass `None` for a static slide.
    design_system : Mapping[str, Any] | None
        The Phase 2 DesignSystem dict (`{version, css, tokens, …}`). When
        supplied, its `css` is inlined so the artifact is fully
        self-contained. When `None`, only the base CSS + kit CSS + IR
        CSS are emitted (the parent must inject design tokens at runtime).
    slide_id : str | None
        Used as the section's `id` attribute. Optional.
    deck_title : str | None
        Threaded into `head_meta.title` for standalone export.
    motion_spec : Mapping[str, Any] | None
        Product-level motion contract: intent preset, deterministic seek
        protocol, poster frame, and QA snapshot plan.
    layer_metadata : Mapping[str, Any] | None
        Deterministic layer metadata derived from the engine artifact. Stored
        on the artifact for screenshot/video/export tooling.

    Returns
    -------
    dict
        `{html, css, js, head_meta, fingerprint, schema_version,
        motion_spec, layer_metadata}`
    """
    kit_name = (kit or "").strip()
    renderer = _KIT_RENDERERS.get(kit_name)
    ir = animation_ir if isinstance(animation_ir, Mapping) else {}
    ds = design_system if isinstance(design_system, Mapping) else {}
    motion = motion_spec if isinstance(motion_spec, Mapping) else {}
    layers = layer_metadata if isinstance(layer_metadata, Mapping) else {}

    if renderer is None:
        # Honest empty render — never invent a different kit. The
        # caller can detect this via the `data-error` attribute and
        # decide whether to retry generation or fall back to JSX-only.
        body_html = (
            f'<div class="slide-error" role="alert" data-kit="{_esc(kit_name)}">'
            f'Unknown kit component: {_esc(kit_name) or "(empty)"}</div>'
        )
        kit_extra_css = ".slide-error { color: var(--color-danger); padding: 24px; }"
        kit_extra_js = ""
    else:
        body_html, kit_extra_css, kit_extra_js = renderer(props or {}, ir)

    # Determine the variant for TitleHero (drives the gradient/image background).
    variant = ""
    if kit_name == "TitleHero":
        variant = str((props or {}).get("variant") or "gradient")

    section_id_attr = _attr("id", slide_id)
    variant_attr = _attr("data-variant", variant)
    poster = motion.get("poster_frame") if isinstance(motion.get("poster_frame"), Mapping) else {}
    motion_attrs = "".join([
        _attr("data-motion-protocol", motion.get("protocol")),
        _attr("data-motion-preset", motion.get("preset")),
        _attr("data-motion-style-preset", motion.get("style_preset")),
        _attr("data-motion-duration-ms", motion.get("duration_ms")),
        _attr("data-poster-frame-ms", poster.get("time_ms")),
        _attr("data-layer-count", layers.get("layer_count")),
        _attr("data-seek-protocol", motion.get("protocol")),
    ])
    section_open = (
        f'<section class="slide" data-kit="{_esc(kit_name)}"{variant_attr}{section_id_attr}{motion_attrs}>'
    )
    html = section_open + body_html + "</section>"

    # Compose CSS: design system tokens (if any) → base → kit-specific →
    # animation IR. IR last so its motion classes win specificity ties.
    ds_css = ds.get("css") if isinstance(ds.get("css"), str) else ""
    ir_css = ir.get("css") if isinstance(ir.get("css"), str) else ""
    css_parts = [ds_css, _BASE_CSS, kit_extra_css, ir_css]
    css = "\n".join(p.strip("\n") for p in css_parts if p)

    # JS: add the deterministic seek bridge when a MotionSpec is present.
    # Screenshot/PDF/video workers call window.__bariseSlide.seek(...) to
    # sample a stable animation time instead of racing the browser paint loop.
    motion_js = build_seek_runtime_js(motion, ir) if motion else ""
    js = "\n".join(part for part in (motion_js, kit_extra_js or "") if part.strip())

    # Title falls back to the kit-rendered headline so PPTX export and
    # screenshot pipeline pick up something meaningful in the page title.
    title_str = (
        deck_title
        or str((props or {}).get("headline") or "")
        or f"{kit_name} slide"
    )
    head_meta = {
        "charset": "utf-8",
        "viewport": "width=1280, initial-scale=1",
        "title": title_str,
        "description": str((props or {}).get("subheadline") or "")[:200],
    }
    # Font preconnects (helps HTML render-only paths).
    font_imports = ds.get("font_imports") if isinstance(ds.get("font_imports"), list) else []
    if font_imports:
        head_meta["fonts"] = json.dumps(font_imports, ensure_ascii=False)

    fingerprint_input = (html + "\n" + css + "\n" + js).encode("utf-8")
    fingerprint = hashlib.sha1(fingerprint_input).hexdigest()[:12]
    motion_payload = (
        json.loads(json.dumps(motion, ensure_ascii=False))
        if motion
        else None
    )
    layer_payload = (
        json.loads(json.dumps(layers, ensure_ascii=False))
        if layers
        else None
    )

    return {
        "html": html,
        "css": css,
        "js": js,
        "head_meta": head_meta,
        "fingerprint": fingerprint,
        "schema_version": _SCHEMA_VERSION,
        "motion_spec": motion_payload,
        "layer_metadata": layer_payload,
    }


def render_standalone_document(artifact: Mapping[str, Any]) -> str:
    """
    Wrap an html_css_js artifact in a complete `<!DOCTYPE html>` document
    suitable for headless screenshots / PPTX export. Used by Phase 12
    PPTX exporter and the screenshot service.
    """
    if not isinstance(artifact, Mapping):
        raise TypeError("artifact must be a mapping")
    head_meta = artifact.get("head_meta") or {}
    title = _esc(head_meta.get("title", "Slide"))
    description = _esc(head_meta.get("description", ""))
    css = artifact.get("css") or ""
    html = artifact.get("html") or ""
    js = artifact.get("js") or ""

    font_links = ""
    raw_fonts = head_meta.get("fonts")
    if isinstance(raw_fonts, str) and raw_fonts.strip():
        try:
            urls = json.loads(raw_fonts)
            if isinstance(urls, list):
                font_links = "\n".join(
                    f'<link rel="stylesheet" href="{_esc(u)}" />'
                    for u in urls
                    if isinstance(u, str) and u.startswith("https://")
                )
        except json.JSONDecodeError:
            font_links = ""

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8" />\n'
        '<meta name="viewport" content="width=1280, initial-scale=1" />\n'
        f"<title>{title}</title>\n"
        + (f'<meta name="description" content="{description}" />\n' if description else "")
        + (font_links + "\n" if font_links else "")
        + f"<style>{css}</style>\n"
        "</head>\n"
        "<body>\n"
        f"{html}\n"
        + (f"<script>{js}</script>\n" if js.strip() else "")
        + "</body>\n</html>\n"
    )
