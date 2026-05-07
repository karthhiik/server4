"""
V4 Reveal-legacy Transformer — Phase 5 (Day 9-10) of v3-final plan.

Emits a reveal.js-friendly ``<section>`` artifact for the legacy export
path (downloadable HTML deck, marketing-team handoff, blog embeds).

    {
      "schema_version": 1,
      "section": "<section class='reveal-slide' …>…</section>",
      "css": ".reveal-slide { … }\\n@keyframes …",
      "fragments": [{"id": "headline", "index": 0}, …],
      "fingerprint": "sha1[:12] of section+css",
    }

Why this artifact exists
------------------------
Reveal.js is a 14-year-old presentation framework with very stable
markup conventions: each slide is a ``<section>``, animatable elements
get ``class="fragment"``. We emit that format so users who already
publish reveal decks (engineering blogs, conference talks) can drop our
slides into their existing pipeline.

Design rules
------------
* **Real data only.** Same rule as html_transformer / engine_transformer:
  every node is sourced from real props. Missing prop → omitted node.
  Unknown kit → a ``<section>`` with ``data-error="unknown_kit"``.
* **Reveal-native structure.** Use the conventional reveal classes
  (``.r-stack``, ``.r-stretch``, ``.r-fit-text``, ``.fragment``) so the
  output renders correctly with stock reveal.js styling.
* **Token-driven CSS.** Same ``--color-*``, ``--type-*``, ``--space-*``
  variables as the html_css_js artifact, so a single design system
  snapshot styles every artifact.
* **HTML-escaped.** Every user-supplied string is escaped to prevent
  XSS in the published deck.
* **Pure deterministic.** No LLM, no I/O. <2 ms per slide.
"""

from __future__ import annotations

import hashlib
import html as _stdhtml
import json
from typing import Any, Iterable, Mapping


_SCHEMA_VERSION = 1


# ── Helpers ──────────────────────────────────────────────────────────


def _esc(text: Any) -> str:
    if text is None:
        return ""
    return _stdhtml.escape(str(text), quote=True)


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _list_of_mappings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, Iterable):
        return [str(x) for x in value if x is not None and str(x).strip()]
    return []


class _FragmentTracker:
    """Allocates ``data-fragment-index`` values matching the IR order."""

    def __init__(self, animation_ir: Mapping[str, Any] | None):
        self._index_for: dict[str, int] = {}
        self._next = 0
        if isinstance(animation_ir, Mapping):
            entries = animation_ir.get("entries") or []
            sorted_entries = sorted(
                (e for e in entries if isinstance(e, Mapping)),
                key=lambda e: (e.get("delay_ms", 0), e.get("stagger_index", 0)),
            )
            for e in sorted_entries:
                target = e.get("target")
                if isinstance(target, str) and target not in self._index_for:
                    self._index_for[target] = self._next
                    self._next += 1
        self.fragments: list[dict[str, Any]] = []

    def fragment_attrs(self, target: str) -> str:
        """Return the ``class`` and ``data-fragment-index`` attrs for a target."""
        if target not in self._index_for:
            # Allocate on demand for targets not in the IR (still animated
            # in the deck via a sane default order).
            self._index_for[target] = self._next
            self._next += 1
        idx = self._index_for[target]
        self.fragments.append({"id": target, "index": idx})
        return f' class="fragment" data-fragment-index="{idx}"'


# ── Per-kit translators ──────────────────────────────────────────────


def _reveal_title_hero(props: Mapping[str, Any], frag: _FragmentTracker) -> str:
    headline = _str_or_none(props.get("headline"))
    subheadline = _str_or_none(props.get("subheadline"))
    eyebrow = _str_or_none(props.get("eyebrow"))
    footer = _str_or_none(props.get("footer"))
    logo_url = _str_or_none(props.get("logoUrl"))
    image_url = _str_or_none(props.get("imageUrl"))
    variant = str(props.get("variant") or "gradient")
    has_image = variant == "image" and bool(image_url)

    parts: list[str] = []
    if has_image:
        parts.append(
            f'<div class="rs-bleed" style="background-image:url(&quot;{_esc(image_url)}&quot;)"></div>'
            f'<div class="rs-scrim"></div>'
        )
    if logo_url:
        parts.append(f'<img class="rs-logo" src="{_esc(logo_url)}" alt="" />')

    parts.append('<div class="rs-stack">')
    if eyebrow:
        parts.append(
            f'<span{frag.fragment_attrs("eyebrow")}><span class="rs-chip">{_esc(eyebrow)}</span></span>'
        )
    if headline:
        parts.append(f'<h1{frag.fragment_attrs("headline")} class="rs-display">{_esc(headline)}</h1>')
    if subheadline:
        parts.append(f'<p{frag.fragment_attrs("subheadline")} class="rs-sub">{_esc(subheadline)}</p>')
    parts.append('</div>')
    if footer:
        parts.append(f'<div class="rs-footer"{frag.fragment_attrs("footer")}>{_esc(footer)}</div>')

    return "".join(parts)


def _reveal_stat_hero(props: Mapping[str, Any], frag: _FragmentTracker) -> str:
    headline = _str_or_none(props.get("headline"))
    subheadline = _str_or_none(props.get("subheadline"))
    eyebrow = _str_or_none(props.get("eyebrow"))
    stats = _list_of_mappings(props.get("stats"))[:4]
    align = _str_or_none(props.get("align")) or "left"

    parts: list[str] = []
    parts.append(f'<div class="rs-stat-head" data-align="{_esc(align)}">')
    if eyebrow:
        parts.append(f'<div class="rs-caption">{_esc(eyebrow)}</div>')
    if headline:
        parts.append(f'<h1{frag.fragment_attrs("headline")} class="rs-h1">{_esc(headline)}</h1>')
    if subheadline:
        parts.append(f'<p{frag.fragment_attrs("subheadline")} class="rs-sub">{_esc(subheadline)}</p>')
    parts.append('</div>')

    if stats:
        parts.append(f'<div class="rs-stats" data-count="{len(stats)}">')
        for i, st in enumerate(stats):
            value = _str_or_none(st.get("value"))
            label = _str_or_none(st.get("label"))
            sublabel = _str_or_none(st.get("sublabel"))
            parts.append(f'<div{frag.fragment_attrs(f"stats.{i}")} class="rs-stat">')
            if value:
                parts.append(f'<div class="rs-stat-value">{_esc(value)}</div>')
            if label:
                parts.append(f'<div class="rs-stat-label">{_esc(label)}</div>')
            if sublabel:
                parts.append(f'<div class="rs-stat-sub">{_esc(sublabel)}</div>')
            parts.append('</div>')
        parts.append('</div>')

    return "".join(parts)


def _reveal_chart_block(props: Mapping[str, Any], frag: _FragmentTracker) -> str:
    headline = _str_or_none(props.get("headline"))
    subheadline = _str_or_none(props.get("subheadline"))
    chart_kind = _str_or_none(props.get("type")) or "bar"
    data = _list_of_mappings(props.get("data"))
    x_key = _str_or_none(props.get("xKey")) or "x"
    y_keys = _coerce_str_list(props.get("yKeys"))
    source = _str_or_none(props.get("source"))

    parts: list[str] = []
    if headline:
        parts.append(f'<h1{frag.fragment_attrs("headline")} class="rs-h1">{_esc(headline)}</h1>')
    if subheadline:
        parts.append(f'<p{frag.fragment_attrs("subheadline")} class="rs-sub">{_esc(subheadline)}</p>')

    # Render chart data as a reveal-friendly HTML table inside a wrapper
    # that reveal.js will treat as a single chart "fragment". Reveal-legacy
    # consumers commonly post-process the table with a chart helper, but
    # the table itself is real data — never fabricated.
    parts.append(
        f'<figure{frag.fragment_attrs("chart")} class="rs-chart" '
        f'data-chart-kind="{_esc(chart_kind)}" data-x-key="{_esc(x_key)}" '
        f'data-y-keys="{_esc(",".join(y_keys))}">'
    )
    if data:
        parts.append('<table class="rs-chart-data"><thead><tr>')
        parts.append(f'<th>{_esc(x_key)}</th>')
        for k in y_keys:
            parts.append(f'<th>{_esc(k)}</th>')
        parts.append('</tr></thead><tbody>')
        for row in data:
            parts.append('<tr>')
            parts.append(f'<td>{_esc(row.get(x_key, ""))}</td>')
            for k in y_keys:
                parts.append(f'<td>{_esc(row.get(k, ""))}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table>')
    else:
        parts.append('<div class="rs-empty" data-error="empty_chart_data">No chart data.</div>')
    if source:
        parts.append(f'<figcaption class="rs-source">Source: {_esc(source)}</figcaption>')
    parts.append('</figure>')
    return "".join(parts)


def _reveal_timeline_block(props: Mapping[str, Any], frag: _FragmentTracker) -> str:
    headline = _str_or_none(props.get("headline"))
    subheadline = _str_or_none(props.get("subheadline"))
    milestones = _list_of_mappings(props.get("milestones"))
    orientation = str(props.get("orientation") or "horizontal")

    parts: list[str] = []
    if headline:
        parts.append(f'<h1{frag.fragment_attrs("headline")} class="rs-h1">{_esc(headline)}</h1>')
    if subheadline:
        parts.append(f'<p class="rs-sub">{_esc(subheadline)}</p>')
    if milestones:
        parts.append(f'<ol class="rs-timeline" data-orientation="{_esc(orientation)}">')
        for i, m in enumerate(milestones):
            label = _str_or_none(m.get("label"))
            date = _str_or_none(m.get("date"))
            description = _str_or_none(m.get("description"))
            parts.append(f'<li{frag.fragment_attrs(f"milestones.{i}")} class="rs-milestone">')
            if date:
                parts.append(f'<div class="rs-milestone-date">{_esc(date)}</div>')
            if label:
                parts.append(f'<div class="rs-milestone-label">{_esc(label)}</div>')
            if description:
                parts.append(f'<div class="rs-milestone-desc">{_esc(description)}</div>')
            parts.append('</li>')
        parts.append('</ol>')
    return "".join(parts)


def _reveal_comparison_block(props: Mapping[str, Any], frag: _FragmentTracker) -> str:
    headline = _str_or_none(props.get("headline"))
    columns = _list_of_mappings(props.get("columns"))
    rows = _list_of_mappings(props.get("rows"))

    parts: list[str] = []
    if headline:
        parts.append(f'<h1{frag.fragment_attrs("headline")} class="rs-h1">{_esc(headline)}</h1>')

    if columns and rows:
        parts.append('<table class="rs-compare"><thead><tr><th></th>')
        for j, col in enumerate(columns):
            label = _str_or_none(col.get("label")) or ""
            highlight = "rs-col-highlight" if col.get("highlight") else ""
            parts.append(f'<th{frag.fragment_attrs(f"columns.{j}")} class="{highlight}">{_esc(label)}</th>')
        parts.append('</tr></thead><tbody>')
        for i, row in enumerate(rows):
            row_label = _str_or_none(row.get("label")) or ""
            parts.append(f'<tr{frag.fragment_attrs(f"rows.{i}")}>')
            parts.append(f'<th scope="row">{_esc(row_label)}</th>')
            values = row.get("values") or []
            n_cols = len(columns)
            if isinstance(values, list):
                for j in range(n_cols):
                    val = values[j] if j < len(values) else None
                    if val is True:
                        cell = '<span class="rs-yes" aria-label="yes">✓</span>'
                    elif val is False:
                        cell = '<span class="rs-no" aria-label="no">✕</span>'
                    elif val is None:
                        cell = '<span class="rs-na" aria-label="not applicable">—</span>'
                    else:
                        cell = _esc(val)
                    parts.append(f'<td>{cell}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table>')
    return "".join(parts)


def _reveal_feature_grid(props: Mapping[str, Any], frag: _FragmentTracker) -> str:
    headline = _str_or_none(props.get("headline"))
    subheadline = _str_or_none(props.get("subheadline"))
    features = _list_of_mappings(props.get("features"))
    columns_in = props.get("columns")
    cols = int(columns_in) if isinstance(columns_in, (int, float)) and 1 <= int(columns_in) <= 4 else 3

    parts: list[str] = []
    if headline:
        parts.append(f'<h1{frag.fragment_attrs("headline")} class="rs-h1">{_esc(headline)}</h1>')
    if subheadline:
        parts.append(f'<p class="rs-sub">{_esc(subheadline)}</p>')
    if features:
        parts.append(f'<div class="rs-features" data-cols="{cols}">')
        for i, feat in enumerate(features):
            icon = _str_or_none(feat.get("icon"))
            title = _str_or_none(feat.get("title"))
            description = _str_or_none(feat.get("description"))
            parts.append(f'<div{frag.fragment_attrs(f"features.{i}")} class="rs-feature">')
            if icon:
                parts.append(f'<div class="rs-feature-icon" data-icon="{_esc(icon)}"></div>')
            if title:
                parts.append(f'<h3 class="rs-feature-title">{_esc(title)}</h3>')
            if description:
                parts.append(f'<p class="rs-feature-desc">{_esc(description)}</p>')
            parts.append('</div>')
        parts.append('</div>')
    return "".join(parts)


def _reveal_team_grid(props: Mapping[str, Any], frag: _FragmentTracker) -> str:
    headline = _str_or_none(props.get("headline"))
    subheadline = _str_or_none(props.get("subheadline"))
    members = _list_of_mappings(props.get("members"))

    parts: list[str] = []
    if headline:
        parts.append(f'<h1{frag.fragment_attrs("headline")} class="rs-h1">{_esc(headline)}</h1>')
    if subheadline:
        parts.append(f'<p class="rs-sub">{_esc(subheadline)}</p>')
    if members:
        n = len(members)
        cols = min(n, 4)
        parts.append(f'<div class="rs-team" data-cols="{cols}">')
        for i, mem in enumerate(members):
            name = _str_or_none(mem.get("name"))
            role = _str_or_none(mem.get("role"))
            avatar = _str_or_none(mem.get("avatarUrl"))
            bio = _str_or_none(mem.get("bio"))
            linkedin = _str_or_none(mem.get("linkedinUrl"))
            parts.append(f'<div{frag.fragment_attrs(f"members.{i}")} class="rs-member">')
            if avatar:
                parts.append(f'<img class="rs-avatar" src="{_esc(avatar)}" alt="" />')
            if name:
                parts.append(f'<div class="rs-member-name">{_esc(name)}</div>')
            if role:
                parts.append(f'<div class="rs-member-role">{_esc(role)}</div>')
            if bio:
                parts.append(f'<p class="rs-member-bio">{_esc(bio)}</p>')
            if linkedin:
                parts.append(
                    f'<a class="rs-member-link" href="{_esc(linkedin)}" '
                    f'rel="noopener noreferrer" target="_blank">LinkedIn</a>'
                )
            parts.append('</div>')
        parts.append('</div>')
    return "".join(parts)


def _reveal_quote_block(props: Mapping[str, Any], frag: _FragmentTracker) -> str:
    quote = _str_or_none(props.get("quote"))
    attribution = _str_or_none(props.get("attribution"))
    role = _str_or_none(props.get("role"))
    avatar = _str_or_none(props.get("avatarUrl"))
    variant = _str_or_none(props.get("variant")) or "default"

    parts: list[str] = []
    parts.append(f'<blockquote class="rs-quote" data-variant="{_esc(variant)}">')
    if quote:
        parts.append(f'<p{frag.fragment_attrs("quote")} class="rs-quote-text">{_esc(quote)}</p>')
    if attribution or role or avatar:
        parts.append('<footer class="rs-quote-foot">')
        if avatar:
            parts.append(f'<img class="rs-avatar" src="{_esc(avatar)}" alt="" />')
        parts.append('<div class="rs-quote-meta">')
        if attribution:
            parts.append(
                f'<cite{frag.fragment_attrs("attribution")} class="rs-attr">{_esc(attribution)}</cite>'
            )
        if role:
            parts.append(f'<div class="rs-attr-role">{_esc(role)}</div>')
        parts.append('</div></footer>')
    parts.append('</blockquote>')
    return "".join(parts)


def _reveal_full_bleed_image(props: Mapping[str, Any], frag: _FragmentTracker) -> str:
    image_url = _str_or_none(props.get("imageUrl"))
    headline = _str_or_none(props.get("headline"))
    subheadline = _str_or_none(props.get("subheadline"))
    caption = _str_or_none(props.get("caption"))
    align = _str_or_none(props.get("align")) or "bottom-left"

    parts: list[str] = []
    if image_url:
        parts.append(
            f'<div class="rs-bleed" style="background-image:url(&quot;{_esc(image_url)}&quot;)"></div>'
            f'<div class="rs-bleed-scrim"></div>'
        )
    parts.append(f'<div class="rs-bleed-stack" data-align="{_esc(align)}">')
    if headline:
        parts.append(f'<h1{frag.fragment_attrs("headline")} class="rs-h1 rs-on-image">{_esc(headline)}</h1>')
    if subheadline:
        parts.append(
            f'<p{frag.fragment_attrs("subheadline")} class="rs-sub rs-on-image">{_esc(subheadline)}</p>'
        )
    parts.append('</div>')
    if caption:
        parts.append(f'<div class="rs-caption rs-on-image">{_esc(caption)}</div>')
    return "".join(parts)


def _reveal_diagram_block(props: Mapping[str, Any], frag: _FragmentTracker) -> str:
    headline = _str_or_none(props.get("headline"))
    subheadline = _str_or_none(props.get("subheadline"))
    nodes = _list_of_mappings(props.get("nodes"))
    edges = _list_of_mappings(props.get("edges"))

    parts: list[str] = []
    if headline:
        parts.append(f'<h1{frag.fragment_attrs("headline")} class="rs-h1">{_esc(headline)}</h1>')
    if subheadline:
        parts.append(f'<p class="rs-sub">{_esc(subheadline)}</p>')

    # Reveal-legacy renders the diagram as an SVG within a 1280×500 viewBox.
    if nodes:
        node_index: dict[str, dict[str, float]] = {}
        for node in nodes:
            nid = _str_or_none(node.get("id"))
            if not nid:
                continue
            try:
                nx = float(node.get("x", 0.5))
                ny = float(node.get("y", 0.5))
            except (TypeError, ValueError):
                continue
            node_index[nid] = {
                "x": max(0.0, min(1.0, nx)) * 1280,
                "y": max(0.0, min(1.0, ny)) * 500,
            }

        parts.append(
            '<svg class="rs-diagram" viewBox="0 0 1280 500" '
            'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="diagram">'
        )
        # Edges first (so nodes paint over them).
        for j, edge in enumerate(edges):
            a = node_index.get(_str_or_none(edge.get("from")) or "")
            b = node_index.get(_str_or_none(edge.get("to")) or "")
            if not a or not b:
                continue
            parts.append(
                f'<line x1="{a["x"]:.1f}" y1="{a["y"]:.1f}" '
                f'x2="{b["x"]:.1f}" y2="{b["y"]:.1f}" '
                f'class="rs-diagram-edge" />'
            )
            edge_label = _str_or_none(edge.get("label"))
            if edge_label:
                mx = (a["x"] + b["x"]) / 2
                my = (a["y"] + b["y"]) / 2
                parts.append(
                    f'<text x="{mx:.1f}" y="{my:.1f}" '
                    f'class="rs-diagram-edge-label" text-anchor="middle">{_esc(edge_label)}</text>'
                )
        # Nodes.
        node_w, node_h = 200, 70
        for i, node in enumerate(nodes):
            nid = _str_or_none(node.get("id"))
            if not nid or nid not in node_index:
                continue
            coords = node_index[nid]
            x0 = coords["x"] - node_w / 2
            y0 = coords["y"] - node_h / 2
            attrs = frag.fragment_attrs(f"nodes.{i}")
            parts.append(
                f'<g{attrs}>'
                f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{node_w}" height="{node_h}" '
                f'rx="14" ry="14" class="rs-diagram-node" />'
            )
            label = _str_or_none(node.get("label"))
            if label:
                parts.append(
                    f'<text x="{coords["x"]:.1f}" y="{coords["y"]:.1f}" '
                    f'class="rs-diagram-node-label" text-anchor="middle" '
                    f'dominant-baseline="middle">{_esc(label)}</text>'
                )
            parts.append('</g>')
        parts.append('</svg>')
    return "".join(parts)


# ── Static reveal-legacy CSS ────────────────────────────────────────
# Scoped under .reveal-slide so it never bleeds into the consumer's
# reveal.js theme. All colors / fonts read design-system variables.

_REVEAL_CSS = """
.reveal-slide {
  position: relative; width: 100%; height: 100%; overflow: hidden;
  display: flex; flex-direction: column; justify-content: center;
  padding: var(--space-margin, 64px); box-sizing: border-box;
  background: var(--color-surface, #fff); color: var(--color-text-primary, #111);
  font-family: var(--font-body, system-ui), sans-serif;
}
.reveal-slide[data-variant="gradient"] {
  background: linear-gradient(135deg, var(--color-primary, #0f62fe), var(--color-accent, #08bdba));
  color: var(--color-background, #fff);
}
.reveal-slide[data-variant="image"] { background: var(--color-background, #000); }
.reveal-slide .rs-bleed {
  position: absolute; inset: 0; z-index: 0;
  background-size: cover; background-position: center;
}
.reveal-slide .rs-scrim,
.reveal-slide .rs-bleed-scrim {
  position: absolute; inset: 0; z-index: 0;
  background: linear-gradient(120deg, rgba(0,0,0,.65), rgba(0,0,0,.15));
}
.reveal-slide .rs-stack,
.reveal-slide .rs-stat-head,
.reveal-slide .rs-bleed-stack,
.reveal-slide .rs-features,
.reveal-slide .rs-team,
.reveal-slide .rs-stats,
.reveal-slide .rs-timeline,
.reveal-slide .rs-quote,
.reveal-slide .rs-chart,
.reveal-slide .rs-compare,
.reveal-slide .rs-diagram { position: relative; z-index: 1; }
.reveal-slide .rs-display {
  font-family: var(--font-heading, inherit);
  font-size: var(--type-display, clamp(40px, 6vw, 88px));
  font-weight: var(--weight-heading, 700);
  line-height: 1.05; letter-spacing: -0.02em; margin: 0;
}
.reveal-slide .rs-h1 {
  font-family: var(--font-heading, inherit);
  font-size: var(--type-h1, clamp(32px, 4.5vw, 64px));
  font-weight: var(--weight-heading, 700);
  line-height: 1.1; margin: 0 0 0.5em;
}
.reveal-slide .rs-sub {
  font-size: var(--type-h3, 22px);
  color: var(--color-text-secondary, #555);
  line-height: 1.35; max-width: 80ch; margin: 0;
}
.reveal-slide .rs-on-image, .reveal-slide[data-variant="image"] * { color: var(--color-background, #fff); }
.reveal-slide .rs-chip {
  display: inline-block; padding: 4px 10px;
  background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.18);
  border-radius: 999px; font-size: var(--type-caption, 12px); letter-spacing: 0.06em;
}
.reveal-slide .rs-stats {
  display: grid; grid-template-columns: repeat(var(--rs-stat-cols, 1), minmax(0, 1fr));
  gap: var(--space-gap, 24px); margin-top: var(--space-gap, 24px);
}
.reveal-slide .rs-stats[data-count="2"] { --rs-stat-cols: 2; }
.reveal-slide .rs-stats[data-count="3"] { --rs-stat-cols: 3; }
.reveal-slide .rs-stats[data-count="4"] { --rs-stat-cols: 4; }
.reveal-slide .rs-stat-value {
  font-family: var(--font-heading, inherit);
  font-size: var(--type-display, 64px); color: var(--color-primary, #0f62fe);
  font-weight: var(--weight-heading, 700); line-height: 1;
}
.reveal-slide .rs-stat-label { font-weight: 600; margin-top: 8px; }
.reveal-slide .rs-stat-sub { color: var(--color-text-secondary, #555); margin-top: 4px; }
.reveal-slide .rs-features {
  display: grid; grid-template-columns: repeat(var(--rs-feat-cols, 3), minmax(0, 1fr));
  gap: var(--space-gap, 24px);
}
.reveal-slide .rs-features[data-cols="1"] { --rs-feat-cols: 1; }
.reveal-slide .rs-features[data-cols="2"] { --rs-feat-cols: 2; }
.reveal-slide .rs-features[data-cols="4"] { --rs-feat-cols: 4; }
.reveal-slide .rs-feature {
  background: rgba(0,0,0,0.02); padding: 20px; border-radius: 12px;
}
.reveal-slide .rs-feature-icon {
  width: 32px; height: 32px; background: var(--color-primary, #0f62fe); border-radius: 8px;
}
.reveal-slide .rs-feature-title { margin: 12px 0 8px; font-size: var(--type-h3, 20px); }
.reveal-slide .rs-feature-desc { color: var(--color-text-secondary, #555); margin: 0; }
.reveal-slide .rs-team {
  display: grid; grid-template-columns: repeat(var(--rs-team-cols, 4), minmax(0, 1fr));
  gap: var(--space-gap, 24px);
}
.reveal-slide .rs-team[data-cols="1"] { --rs-team-cols: 1; }
.reveal-slide .rs-team[data-cols="2"] { --rs-team-cols: 2; }
.reveal-slide .rs-team[data-cols="3"] { --rs-team-cols: 3; }
.reveal-slide .rs-member { text-align: center; }
.reveal-slide .rs-avatar {
  width: 96px; height: 96px; border-radius: 50%; object-fit: cover;
}
.reveal-slide .rs-member-name { font-weight: 700; margin-top: 8px; }
.reveal-slide .rs-member-role { color: var(--color-primary, #0f62fe); font-size: var(--type-caption, 12px); }
.reveal-slide .rs-member-bio { color: var(--color-text-secondary, #555); margin-top: 6px; }
.reveal-slide .rs-quote { border: 0; padding: 0; margin: 0; }
.reveal-slide .rs-quote[data-variant="accent"] {
  background: var(--color-accent, #08bdba); color: var(--color-background, #fff);
  padding: 32px; border-radius: 16px;
}
.reveal-slide .rs-quote-text {
  font-family: var(--font-heading, inherit);
  font-size: var(--type-h1, 44px); line-height: 1.25; margin: 0;
}
.reveal-slide .rs-quote-foot { display: flex; gap: 16px; align-items: center; margin-top: 24px; }
.reveal-slide .rs-attr { font-style: normal; font-weight: 700; }
.reveal-slide .rs-attr-role { color: var(--color-text-secondary, #555); font-size: var(--type-caption, 12px); }
.reveal-slide .rs-timeline {
  list-style: none; padding: 0; margin: 0;
  display: grid; gap: var(--space-gap, 24px);
}
.reveal-slide .rs-timeline[data-orientation="horizontal"] {
  grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
  grid-auto-flow: column;
}
.reveal-slide .rs-milestone-date { color: var(--color-primary, #0f62fe); font-weight: 700; }
.reveal-slide .rs-milestone-label { font-weight: 700; margin-top: 4px; }
.reveal-slide .rs-milestone-desc { color: var(--color-text-secondary, #555); margin-top: 4px; }
.reveal-slide .rs-compare { width: 100%; border-collapse: collapse; }
.reveal-slide .rs-compare th, .reveal-slide .rs-compare td {
  padding: 12px 16px; text-align: left;
  border-bottom: 1px solid var(--color-border, #e0e0e0);
}
.reveal-slide .rs-col-highlight {
  background: var(--color-primary, #0f62fe); color: var(--color-background, #fff);
}
.reveal-slide .rs-yes { color: var(--color-success, #24a148); font-weight: 700; }
.reveal-slide .rs-no  { color: var(--color-danger, #da1e28); font-weight: 700; }
.reveal-slide .rs-na  { color: var(--color-text-muted, #8d8d8d); }
.reveal-slide .rs-chart-data { width: 100%; border-collapse: collapse; }
.reveal-slide .rs-chart-data th, .reveal-slide .rs-chart-data td {
  padding: 8px 12px; border-bottom: 1px solid var(--color-border, #e0e0e0);
}
.reveal-slide .rs-source { color: var(--color-text-muted, #8d8d8d); font-size: var(--type-caption, 12px); margin-top: 8px; }
.reveal-slide .rs-empty { color: var(--color-danger, #da1e28); padding: 20px; }
.reveal-slide .rs-diagram { width: 100%; height: auto; max-height: 60vh; }
.reveal-slide .rs-diagram-edge {
  stroke: var(--color-border, #e0e0e0); stroke-width: 2; fill: none;
}
.reveal-slide .rs-diagram-edge-label {
  fill: var(--color-text-secondary, #555); font-size: 14px;
}
.reveal-slide .rs-diagram-node {
  fill: var(--color-primary, #0f62fe); stroke: none;
}
.reveal-slide .rs-diagram-node-label {
  fill: var(--color-background, #fff); font-weight: 700; font-size: 18px;
}
.reveal-slide .rs-error {
  color: var(--color-danger, #da1e28); padding: 24px;
  border: 1px dashed var(--color-danger, #da1e28); border-radius: 12px;
}
@media (prefers-reduced-motion: reduce) {
  .reveal-slide .fragment { transition: none !important; animation: none !important; }
}
"""


# ── Public API ───────────────────────────────────────────────────────


_KIT_TRANSLATORS = {
    "TitleHero":       _reveal_title_hero,
    "StatHero":        _reveal_stat_hero,
    "ChartBlock":      _reveal_chart_block,
    "TimelineBlock":   _reveal_timeline_block,
    "ComparisonBlock": _reveal_comparison_block,
    "FeatureGrid":     _reveal_feature_grid,
    "TeamGrid":        _reveal_team_grid,
    "QuoteBlock":      _reveal_quote_block,
    "FullBleedImage":  _reveal_full_bleed_image,
    "DiagramBlock":    _reveal_diagram_block,
}


def build_reveal_legacy(
    *,
    kit: str,
    props: Mapping[str, Any],
    animation_ir: Mapping[str, Any] | None = None,
    design_system: Mapping[str, Any] | None = None,  # noqa: ARG001 (CSS pulls vars at runtime)
    slide_id: str | None = None,
) -> dict[str, Any]:
    """Build the reveal-legacy artifact.

    Returns ``{schema_version, section, css, fragments, fingerprint}``.
    Unknown kits emit a section with ``data-error="unknown_kit"``; never a
    fabricated kit.
    """
    kit_name = (kit or "").strip()
    frag = _FragmentTracker(animation_ir)
    translator = _KIT_TRANSLATORS.get(kit_name)
    section_id_attr = f' id="{_esc(slide_id)}"' if slide_id else ""
    variant = ""
    if kit_name == "TitleHero":
        variant = str((props or {}).get("variant") or "gradient")
    variant_attr = f' data-variant="{_esc(variant)}"' if variant else ""

    if translator is None:
        body = (
            f'<div class="rs-error" role="alert" data-error="unknown_kit">'
            f'Unknown kit component: {_esc(kit_name) or "(empty)"}'
            f'</div>'
        )
        section = (
            f'<section class="reveal-slide" data-kit="{_esc(kit_name)}"'
            f' data-error="unknown_kit"{section_id_attr}>{body}</section>'
        )
    else:
        body = translator(props or {}, frag)
        section = (
            f'<section class="reveal-slide" data-kit="{_esc(kit_name)}"'
            f'{variant_attr}{section_id_attr}>{body}</section>'
        )

    fingerprint = hashlib.sha1((section + "\n" + _REVEAL_CSS).encode("utf-8")).hexdigest()[:12]
    return {
        "schema_version": _SCHEMA_VERSION,
        "section": section,
        "css": _REVEAL_CSS.strip(),
        "fragments": list(frag.fragments),
        "fingerprint": fingerprint,
    }


def render_standalone_reveal_deck(
    artifacts: list[Mapping[str, Any]],
    *,
    deck_title: str = "Deck",
    design_system_css: str | None = None,
) -> str:
    """Wrap a list of reveal-legacy artifacts into a complete reveal.js HTML
    document. Used by the legacy export endpoint."""
    if not isinstance(artifacts, list):
        raise TypeError("artifacts must be a list")
    sections = "\n".join(a.get("section", "") for a in artifacts if isinstance(a, Mapping))
    ds = design_system_css or ""
    head = (
        '<head>'
        '<meta charset="utf-8" />'
        '<meta name="viewport" content="width=1280, initial-scale=1" />'
        f'<title>{_esc(deck_title)}</title>'
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.css" />'
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/theme/white.css" />'
        f'<style>{ds}</style>'
        f'<style>{_REVEAL_CSS}</style>'
        '</head>'
    )
    body = (
        '<body>'
        '<div class="reveal"><div class="slides">'
        f'{sections}'
        '</div></div>'
        '<script src="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.js"></script>'
        '<script>Reveal.initialize({hash:true});</script>'
        '</body>'
    )
    return f'<!DOCTYPE html><html lang="en">{head}{body}</html>'
