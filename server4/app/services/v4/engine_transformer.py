"""
V4 Custom Engine Transformer — Phase 5 (Day 9-10) of v3-final plan.

Given the same `(kit, props, animation_ir, design_system)` tuple that
the html_css_js transformer consumes, this module emits a small,
JSON-only **engine artifact** the parent shell can paint in <200 ms
for the T1 progressive-render tier (no JSX compile, no headless HTML
parse — just primitive draw ops).

    {
      "schema_version": 1,
      "kit": "StatHero",
      "viewport": {"w": 1280, "h": 720, "margin": 64},
      "background": {"kind": "solid", "color_token": "background"},
      "layers": [
         {"type": "text", "id": "headline", "text": "…", "role": "h1", ...},
         {"type": "stat", "id": "stat-0", "value": "10x", "label": "ARR", ...},
         …
      ],
      "fingerprint": "sha1[:12]",
    }

Why this artifact exists
------------------------
* T1 (<200 ms) preview — the parent shell can render every layer to
  an SVG/canvas without booting esbuild-wasm or a headless iframe.
* Skeleton fallback — when JSX fails to compile and the html_css_js
  artifact is too heavy to inline (large image kits), we paint the
  engine artifact while the heavier artifacts hydrate.
* Edit substrate — Phase 8 thin-slice edit ops mutate this primitive
  layer list (it's the smallest representation of the slide).

Design rules
------------
* **Real data only.** Every layer is sourced from the actual props.
  Missing prop → missing layer (matches the React kit's behavior).
  Unknown kit → single ``error`` layer with code+message; never a
  fabricated stand-in.
* **Pure deterministic transformation.** No LLMs, no I/O, <2 ms per
  slide. Fingerprint stable across runs.
* **Token references, not raw values.** Colors are emitted as design
  token names (``text_primary``, ``surface``, …) so the parent shell
  can theme at paint time.
* **Normalized coordinates.** All x/y/w/h are floats in ``[0, 1]`` of
  the slide viewport. The parent shell scales to its actual canvas.
* **Stable IR linkage.** Each animatable layer carries the matching
  ``anim_id`` (``ir-anim-<id>``) from the AnimationIR so the parent
  shell can apply per-layer enter/exit transitions consistently
  with the html_css_js artifact.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping


_SCHEMA_VERSION = 1

# Default 16:9 working canvas — matches the html_transformer & PPTX export.
_VIEWPORT = {"w": 1280, "h": 720, "margin": 64}


# ── Helpers ──────────────────────────────────────────────────────────


def _str_or_none(value: Any) -> str | None:
    """Strip + return value as str. None / empty → None (so layers omit)."""
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


def _ir_anim_id_for(animation_ir: Mapping[str, Any], target: str) -> str | None:
    """Return the ``ir-anim-<id>`` class for a given target, or None."""
    if not isinstance(animation_ir, Mapping):
        return None
    for entry in animation_ir.get("entries") or []:
        if not isinstance(entry, Mapping):
            continue
        if entry.get("target") == target:
            entry_id = entry.get("id")
            if entry_id:
                return f"ir-anim-{entry_id}"
    return None


def _ir_anim_id_for_indexed(
    animation_ir: Mapping[str, Any], target_prefix: str, index: int
) -> str | None:
    """Lookup ``cards.3`` style stagger entry, falling back to the parent."""
    cls = _ir_anim_id_for(animation_ir, f"{target_prefix}.{index}")
    return cls or _ir_anim_id_for(animation_ir, target_prefix)


def _text_layer(
    *,
    layer_id: str,
    text: str | None,
    role: str,
    color_token: str = "text_primary",
    x: float = 0.05,
    y: float = 0.5,
    w: float = 0.9,
    h: float = 0.1,
    align: str = "left",
    weight: str | None = None,
    anim_id: str | None = None,
) -> dict[str, Any] | None:
    if text is None:
        return None
    layer: dict[str, Any] = {
        "type": "text",
        "id": layer_id,
        "text": text,
        "role": role,
        "color_token": color_token,
        "x": round(float(x), 4),
        "y": round(float(y), 4),
        "w": round(float(w), 4),
        "h": round(float(h), 4),
        "align": align,
    }
    if weight:
        layer["weight"] = weight
    if anim_id:
        layer["anim_id"] = anim_id
    return layer


# ── Per-kit translators ──────────────────────────────────────────────
# Each translator returns (background, layers). background is a dict;
# layers is a list[dict] in z-order (first painted first).


def _engine_title_hero(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    variant = str(props.get("variant") or "gradient")
    image_url = _str_or_none(props.get("imageUrl"))
    headline = _str_or_none(props.get("headline"))
    subheadline = _str_or_none(props.get("subheadline"))
    eyebrow = _str_or_none(props.get("eyebrow"))
    footer = _str_or_none(props.get("footer"))
    logo_url = _str_or_none(props.get("logoUrl"))

    if variant == "image" and image_url:
        background: dict[str, Any] = {
            "kind": "scrim_image",
            "url": image_url,
            "scrim": {"angle": 120, "stops": [
                {"color": "rgba(0,0,0,0.68)", "pos": 0.0},
                {"color": "rgba(0,0,0,0.35)", "pos": 0.45},
                {"color": "rgba(0,0,0,0.15)", "pos": 1.0},
            ]},
        }
        text_color = "background"  # white-on-scrim
    elif variant == "image":  # image variant requested but no url
        background = {"kind": "solid", "color_token": "background"}
        text_color = "text_primary"
    else:
        background = {
            "kind": "gradient",
            "angle": 135,
            "stops": [
                {"color_token": "primary", "pos": 0.0},
                {"color_token": "accent", "pos": 1.0},
            ],
        }
        text_color = "background"

    layers: list[dict[str, Any]] = []
    if logo_url:
        layers.append({
            "type": "image",
            "id": "logo",
            "url": logo_url,
            "x": 0.04, "y": 0.06, "w": 0.10, "h": 0.06,
            "fit": "contain",
        })
    if eyebrow:
        layers.append(_text_layer(
            layer_id="eyebrow", text=eyebrow, role="eyebrow",
            color_token=text_color,
            x=0.05, y=0.32, w=0.6, h=0.05,
            anim_id=_ir_anim_id_for(ir, "eyebrow"),
        ))  # type: ignore[arg-type]
    if headline:
        layers.append(_text_layer(
            layer_id="headline", text=headline, role="display",
            color_token=text_color,
            x=0.05, y=0.40, w=0.7, h=0.20,
            weight="heading",
            anim_id=_ir_anim_id_for(ir, "headline"),
        ))  # type: ignore[arg-type]
    if subheadline:
        layers.append(_text_layer(
            layer_id="subheadline", text=subheadline, role="h3",
            color_token=("background" if text_color == "background" else "text_secondary"),
            x=0.05, y=0.62, w=0.7, h=0.12,
            anim_id=_ir_anim_id_for(ir, "subheadline"),
        ))  # type: ignore[arg-type]
    if footer:
        layers.append(_text_layer(
            layer_id="footer", text=footer, role="caption",
            color_token=("background" if text_color == "background" else "text_muted"),
            x=0.05, y=0.92, w=0.9, h=0.05,
            anim_id=_ir_anim_id_for(ir, "footer"),
        ))  # type: ignore[arg-type]
    layers = [layer for layer in layers if layer is not None]
    return background, layers


def _engine_stat_hero(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    headline = _str_or_none(props.get("headline"))
    subheadline = _str_or_none(props.get("subheadline"))
    eyebrow = _str_or_none(props.get("eyebrow"))
    stats = _list_of_mappings(props.get("stats"))[:4]

    background = {"kind": "solid", "color_token": "surface"}
    layers: list[dict[str, Any]] = []
    if eyebrow:
        layers.append(_text_layer(
            layer_id="eyebrow", text=eyebrow, role="caption",
            color_token="text_muted",
            x=0.05, y=0.10, w=0.9, h=0.05,
        ))  # type: ignore[arg-type]
    if headline:
        layers.append(_text_layer(
            layer_id="headline", text=headline, role="h1",
            x=0.05, y=0.16, w=0.9, h=0.12, weight="heading",
            anim_id=_ir_anim_id_for(ir, "headline"),
        ))  # type: ignore[arg-type]
    if subheadline:
        layers.append(_text_layer(
            layer_id="subheadline", text=subheadline, role="body",
            color_token="text_secondary",
            x=0.05, y=0.30, w=0.9, h=0.08,
            anim_id=_ir_anim_id_for(ir, "subheadline"),
        ))  # type: ignore[arg-type]

    n = len(stats)
    if n:
        # Distribute n stat blocks horizontally across 0.05..0.95 with
        # equal gutters. y ~ 0.45..0.85.
        avail = 0.90
        gutter = 0.02
        block_w = (avail - gutter * (n - 1)) / n
        for i, st in enumerate(stats):
            value = _str_or_none(st.get("value"))
            label = _str_or_none(st.get("label"))
            sublabel = _str_or_none(st.get("sublabel"))
            x = 0.05 + i * (block_w + gutter)
            anim = _ir_anim_id_for_indexed(ir, "stats", i)
            if value:
                layers.append(_text_layer(
                    layer_id=f"stat-{i}-value", text=value, role="display",
                    color_token="primary",
                    x=x, y=0.46, w=block_w, h=0.20, weight="heading",
                    anim_id=anim,
                ))  # type: ignore[arg-type]
            if label:
                layers.append(_text_layer(
                    layer_id=f"stat-{i}-label", text=label, role="body",
                    x=x, y=0.68, w=block_w, h=0.06, weight="heading",
                    anim_id=anim,
                ))  # type: ignore[arg-type]
            if sublabel:
                layers.append(_text_layer(
                    layer_id=f"stat-{i}-sub", text=sublabel, role="caption",
                    color_token="text_secondary",
                    x=x, y=0.75, w=block_w, h=0.06,
                    anim_id=anim,
                ))  # type: ignore[arg-type]

    layers = [layer for layer in layers if layer is not None]
    return background, layers


def _engine_chart_block(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    headline = _str_or_none(props.get("headline"))
    subheadline = _str_or_none(props.get("subheadline"))
    chart_kind = str(props.get("type") or "bar")
    data = _list_of_mappings(props.get("data"))
    x_key = _str_or_none(props.get("xKey")) or "x"
    y_keys = _coerce_str_list(props.get("yKeys"))
    source = _str_or_none(props.get("source"))

    background = {"kind": "solid", "color_token": "surface"}
    layers: list[dict[str, Any]] = []
    if headline:
        layers.append(_text_layer(
            layer_id="headline", text=headline, role="h1",
            x=0.05, y=0.08, w=0.9, h=0.10, weight="heading",
            anim_id=_ir_anim_id_for(ir, "headline"),
        ))  # type: ignore[arg-type]
    if subheadline:
        layers.append(_text_layer(
            layer_id="subheadline", text=subheadline, role="body",
            color_token="text_secondary",
            x=0.05, y=0.20, w=0.9, h=0.06,
            anim_id=_ir_anim_id_for(ir, "subheadline"),
        ))  # type: ignore[arg-type]
    layers.append({
        "type": "chart",
        "id": "chart",
        "kind": chart_kind,
        "data": data,
        "x_key": x_key,
        "y_keys": y_keys,
        "x": 0.05, "y": 0.28, "w": 0.9, "h": 0.58,
        **({"anim_id": _ir_anim_id_for(ir, "chart")}
           if _ir_anim_id_for(ir, "chart") else {}),
    })
    if source:
        layers.append(_text_layer(
            layer_id="source", text=f"Source: {source}", role="caption",
            color_token="text_muted",
            x=0.05, y=0.92, w=0.9, h=0.05,
        ))  # type: ignore[arg-type]
    layers = [layer for layer in layers if layer is not None]
    return background, layers


def _engine_timeline_block(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    headline = _str_or_none(props.get("headline"))
    subheadline = _str_or_none(props.get("subheadline"))
    milestones = _list_of_mappings(props.get("milestones"))
    orientation = str(props.get("orientation") or "horizontal")

    background = {"kind": "solid", "color_token": "surface"}
    layers: list[dict[str, Any]] = []
    if headline:
        layers.append(_text_layer(
            layer_id="headline", text=headline, role="h1",
            x=0.05, y=0.08, w=0.9, h=0.10, weight="heading",
            anim_id=_ir_anim_id_for(ir, "headline"),
        ))  # type: ignore[arg-type]
    if subheadline:
        layers.append(_text_layer(
            layer_id="subheadline", text=subheadline, role="body",
            color_token="text_secondary",
            x=0.05, y=0.20, w=0.9, h=0.06,
        ))  # type: ignore[arg-type]

    n = len(milestones)
    if n and orientation != "vertical":
        avail = 0.90
        block_w = avail / n
        layers.append({
            "type": "shape",
            "id": "timeline-axis",
            "kind": "rect",
            "x": 0.05, "y": 0.50, "w": 0.90, "h": 0.004,
            "fill_token": "border",
        })
        for i, m in enumerate(milestones):
            x = 0.05 + i * block_w + block_w / 2
            label = _str_or_none(m.get("label"))
            date = _str_or_none(m.get("date"))
            description = _str_or_none(m.get("description"))
            anim = _ir_anim_id_for_indexed(ir, "milestones", i)
            layers.append({
                "type": "shape",
                "id": f"timeline-dot-{i}",
                "kind": "circle",
                "x": x - 0.012, "y": 0.486, "w": 0.024, "h": 0.024,
                "fill_token": "primary",
                **({"anim_id": anim} if anim else {}),
            })
            if date:
                layers.append(_text_layer(
                    layer_id=f"milestone-{i}-date", text=date, role="caption",
                    color_token="primary",
                    x=x - block_w / 2, y=0.36, w=block_w, h=0.05,
                    align="center", anim_id=anim,
                ))  # type: ignore[arg-type]
            if label:
                layers.append(_text_layer(
                    layer_id=f"milestone-{i}-label", text=label, role="body",
                    x=x - block_w / 2, y=0.55, w=block_w, h=0.06,
                    align="center", weight="heading", anim_id=anim,
                ))  # type: ignore[arg-type]
            if description:
                layers.append(_text_layer(
                    layer_id=f"milestone-{i}-desc", text=description, role="caption",
                    color_token="text_secondary",
                    x=x - block_w / 2, y=0.62, w=block_w, h=0.18,
                    align="center", anim_id=anim,
                ))  # type: ignore[arg-type]
    elif n:  # vertical
        block_h = 0.70 / n
        for i, m in enumerate(milestones):
            y = 0.20 + i * block_h
            label = _str_or_none(m.get("label"))
            date = _str_or_none(m.get("date"))
            description = _str_or_none(m.get("description"))
            anim = _ir_anim_id_for_indexed(ir, "milestones", i)
            if date:
                layers.append(_text_layer(
                    layer_id=f"milestone-{i}-date", text=date, role="caption",
                    color_token="primary",
                    x=0.05, y=y, w=0.18, h=block_h, anim_id=anim,
                ))  # type: ignore[arg-type]
            if label:
                layers.append(_text_layer(
                    layer_id=f"milestone-{i}-label", text=label, role="body",
                    x=0.25, y=y, w=0.7, h=block_h * 0.45,
                    weight="heading", anim_id=anim,
                ))  # type: ignore[arg-type]
            if description:
                layers.append(_text_layer(
                    layer_id=f"milestone-{i}-desc", text=description, role="caption",
                    color_token="text_secondary",
                    x=0.25, y=y + block_h * 0.45, w=0.7, h=block_h * 0.55,
                    anim_id=anim,
                ))  # type: ignore[arg-type]

    layers = [layer for layer in layers if layer is not None]
    return background, layers


def _engine_comparison_block(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    headline = _str_or_none(props.get("headline"))
    columns = _list_of_mappings(props.get("columns"))
    rows = _list_of_mappings(props.get("rows"))

    background = {"kind": "solid", "color_token": "surface"}
    layers: list[dict[str, Any]] = []
    if headline:
        layers.append(_text_layer(
            layer_id="headline", text=headline, role="h1",
            x=0.05, y=0.08, w=0.9, h=0.10, weight="heading",
            anim_id=_ir_anim_id_for(ir, "headline"),
        ))  # type: ignore[arg-type]

    n_cols = len(columns)
    if n_cols and rows:
        # column 0 is the row-label column; the dataset columns share the rest
        total_cols = n_cols + 1
        col_w = 0.90 / total_cols
        # column headers
        for j, col in enumerate(columns):
            label = _str_or_none(col.get("label"))
            if label:
                layers.append(_text_layer(
                    layer_id=f"col-header-{j}", text=label, role="body",
                    x=0.05 + (j + 1) * col_w, y=0.22, w=col_w, h=0.06,
                    align="center", weight="heading",
                    anim_id=_ir_anim_id_for_indexed(ir, "columns", j),
                ))  # type: ignore[arg-type]
        # rows
        n_rows = len(rows)
        avail_h = 0.65
        row_h = avail_h / n_rows
        for i, row in enumerate(rows):
            row_label = _str_or_none(row.get("label"))
            anim = _ir_anim_id_for_indexed(ir, "rows", i)
            y = 0.30 + i * row_h
            if row_label:
                layers.append(_text_layer(
                    layer_id=f"row-label-{i}", text=row_label, role="body",
                    x=0.05, y=y, w=col_w, h=row_h,
                    weight="heading", anim_id=anim,
                ))  # type: ignore[arg-type]
            values = row.get("values") or []
            if isinstance(values, list):
                for j in range(n_cols):
                    val = values[j] if j < len(values) else None
                    if val is True:
                        cell_text, color = "✓", "success"
                    elif val is False:
                        cell_text, color = "✕", "danger"
                    elif val is None:
                        cell_text, color = "—", "text_muted"
                    else:
                        cell_text, color = str(val), "text_primary"
                    layers.append(_text_layer(
                        layer_id=f"cell-{i}-{j}", text=cell_text, role="body",
                        color_token=color,
                        x=0.05 + (j + 1) * col_w, y=y, w=col_w, h=row_h,
                        align="center", anim_id=anim,
                    ))  # type: ignore[arg-type]

    layers = [layer for layer in layers if layer is not None]
    return background, layers


def _engine_feature_grid(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    headline = _str_or_none(props.get("headline"))
    subheadline = _str_or_none(props.get("subheadline"))
    features = (
        _list_of_mappings(props.get("features"))
        or _list_of_mappings(props.get("items"))
        or _list_of_mappings(props.get("cards"))
    )
    columns_in = props.get("columns")
    cols = int(columns_in) if isinstance(columns_in, (int, float)) and 1 <= int(columns_in) <= 4 else 3
    if not features:
        cols = 1

    background = {"kind": "solid", "color_token": "surface"}
    layers: list[dict[str, Any]] = []
    if headline:
        layers.append(_text_layer(
            layer_id="headline", text=headline, role="h1",
            x=0.05, y=0.08, w=0.9, h=0.10, weight="heading",
            anim_id=_ir_anim_id_for(ir, "headline"),
        ))  # type: ignore[arg-type]
    if subheadline:
        layers.append(_text_layer(
            layer_id="subheadline", text=subheadline, role="body",
            color_token="text_secondary",
            x=0.05, y=0.20, w=0.9, h=0.06,
        ))  # type: ignore[arg-type]

    if features:
        n = len(features)
        rows = (n + cols - 1) // cols
        avail_w = 0.90
        gutter = 0.02
        cell_w = (avail_w - gutter * (cols - 1)) / cols
        avail_h = 0.65
        row_gutter = 0.03
        cell_h = (avail_h - row_gutter * (rows - 1)) / rows
        for idx, feat in enumerate(features):
            r = idx // cols
            c = idx % cols
            x = 0.05 + c * (cell_w + gutter)
            y = 0.28 + r * (cell_h + row_gutter)
            anim = _ir_anim_id_for_indexed(ir, "features", idx)
            icon = _str_or_none(feat.get("icon"))
            title = _str_or_none(feat.get("title"))
            description = _str_or_none(feat.get("description"))
            if icon:
                layers.append({
                    "type": "icon",
                    "id": f"feat-{idx}-icon",
                    "name": icon,
                    "color_token": "primary",
                    "x": x, "y": y, "w": 0.04, "h": 0.04,
                    **({"anim_id": anim} if anim else {}),
                })
            if title:
                layers.append(_text_layer(
                    layer_id=f"feat-{idx}-title", text=title, role="h3",
                    x=x, y=y + 0.06, w=cell_w, h=0.06,
                    weight="heading", anim_id=anim,
                ))  # type: ignore[arg-type]
            if description:
                layers.append(_text_layer(
                    layer_id=f"feat-{idx}-desc", text=description, role="body",
                    color_token="text_secondary",
                    x=x, y=y + 0.13, w=cell_w, h=cell_h - 0.13,
                    anim_id=anim,
                ))  # type: ignore[arg-type]

    layers = [layer for layer in layers if layer is not None]
    return background, layers


def _engine_team_grid(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    headline = _str_or_none(props.get("headline"))
    subheadline = _str_or_none(props.get("subheadline"))
    members = _list_of_mappings(props.get("members"))

    background = {"kind": "solid", "color_token": "surface"}
    layers: list[dict[str, Any]] = []
    if headline:
        layers.append(_text_layer(
            layer_id="headline", text=headline, role="h1",
            x=0.05, y=0.08, w=0.9, h=0.10, weight="heading",
            anim_id=_ir_anim_id_for(ir, "headline"),
        ))  # type: ignore[arg-type]
    if subheadline:
        layers.append(_text_layer(
            layer_id="subheadline", text=subheadline, role="body",
            color_token="text_secondary",
            x=0.05, y=0.20, w=0.9, h=0.06,
        ))  # type: ignore[arg-type]

    n = len(members)
    if n:
        cols = min(n, 4)
        rows = (n + cols - 1) // cols
        avail_w = 0.90
        gutter = 0.02
        cell_w = (avail_w - gutter * (cols - 1)) / cols
        avail_h = 0.65
        row_gutter = 0.03
        cell_h = (avail_h - row_gutter * (rows - 1)) / rows
        for idx, mem in enumerate(members):
            r = idx // cols
            c = idx % cols
            x = 0.05 + c * (cell_w + gutter)
            y = 0.28 + r * (cell_h + row_gutter)
            anim = _ir_anim_id_for_indexed(ir, "members", idx)
            avatar = _str_or_none(mem.get("avatarUrl"))
            name = _str_or_none(mem.get("name"))
            role = _str_or_none(mem.get("role"))
            bio = _str_or_none(mem.get("bio"))
            avatar_h = min(0.18, cell_h * 0.45)
            if avatar:
                layers.append({
                    "type": "image",
                    "id": f"member-{idx}-avatar",
                    "url": avatar,
                    "x": x + cell_w / 2 - avatar_h / 2,
                    "y": y, "w": avatar_h, "h": avatar_h,
                    "fit": "cover",
                    "shape": "circle",
                    **({"anim_id": anim} if anim else {}),
                })
            if name:
                layers.append(_text_layer(
                    layer_id=f"member-{idx}-name", text=name, role="body",
                    x=x, y=y + avatar_h + 0.01, w=cell_w, h=0.05,
                    align="center", weight="heading", anim_id=anim,
                ))  # type: ignore[arg-type]
            if role:
                layers.append(_text_layer(
                    layer_id=f"member-{idx}-role", text=role, role="caption",
                    color_token="primary",
                    x=x, y=y + avatar_h + 0.06, w=cell_w, h=0.04,
                    align="center", anim_id=anim,
                ))  # type: ignore[arg-type]
            if bio:
                layers.append(_text_layer(
                    layer_id=f"member-{idx}-bio", text=bio, role="caption",
                    color_token="text_secondary",
                    x=x, y=y + avatar_h + 0.10,
                    w=cell_w, h=cell_h - avatar_h - 0.10,
                    align="center", anim_id=anim,
                ))  # type: ignore[arg-type]

    layers = [layer for layer in layers if layer is not None]
    return background, layers


def _engine_quote_block(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    quote = _str_or_none(props.get("quote"))
    attribution = _str_or_none(props.get("attribution"))
    role = _str_or_none(props.get("role"))
    avatar = _str_or_none(props.get("avatarUrl"))
    variant = str(props.get("variant") or "default")

    background = (
        {"kind": "solid", "color_token": "accent"}
        if variant == "accent"
        else {"kind": "solid", "color_token": "surface"}
    )
    text_color = "background" if variant == "accent" else "text_primary"
    sec_color = "background" if variant == "accent" else "text_secondary"

    layers: list[dict[str, Any]] = []
    layers.append({
        "type": "icon",
        "id": "quote-mark",
        "name": "quote",
        "color_token": ("background" if variant == "accent" else "primary"),
        "x": 0.06, "y": 0.18, "w": 0.06, "h": 0.06,
    })
    if quote:
        layers.append(_text_layer(
            layer_id="quote", text=quote, role="h2",
            color_token=text_color,
            x=0.10, y=0.30, w=0.80, h=0.30,
            weight="heading",
            anim_id=_ir_anim_id_for(ir, "quote"),
        ))  # type: ignore[arg-type]
    if avatar:
        layers.append({
            "type": "image",
            "id": "quote-avatar",
            "url": avatar,
            "x": 0.10, "y": 0.66, "w": 0.06, "h": 0.06,
            "fit": "cover", "shape": "circle",
        })
    if attribution:
        x = 0.18 if avatar else 0.10
        layers.append(_text_layer(
            layer_id="attribution", text=attribution, role="body",
            color_token=text_color,
            x=x, y=0.66, w=0.7, h=0.05,
            weight="heading",
            anim_id=_ir_anim_id_for(ir, "attribution"),
        ))  # type: ignore[arg-type]
    if role:
        x = 0.18 if avatar else 0.10
        layers.append(_text_layer(
            layer_id="attribution-role", text=role, role="caption",
            color_token=sec_color,
            x=x, y=0.71, w=0.7, h=0.04,
        ))  # type: ignore[arg-type]
    layers = [layer for layer in layers if layer is not None]
    return background, layers


def _engine_full_bleed_image(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    image_url = _str_or_none(props.get("imageUrl"))
    headline = _str_or_none(props.get("headline"))
    subheadline = _str_or_none(props.get("subheadline"))
    caption = _str_or_none(props.get("caption"))
    align = str(props.get("align") or "bottom-left")

    if image_url:
        background = {
            "kind": "scrim_image",
            "url": image_url,
            "scrim": {"angle": 180, "stops": [
                {"color": "rgba(0,0,0,0.0)", "pos": 0.0},
                {"color": "rgba(0,0,0,0.55)", "pos": 1.0},
            ]},
        }
    else:
        background = {"kind": "solid", "color_token": "background"}

    layers: list[dict[str, Any]] = []
    # Anchor box per align value.
    if align.startswith("top"):
        y0 = 0.08
    elif align.startswith("center") or align == "middle":
        y0 = 0.40
    else:
        y0 = 0.62
    if align.endswith("right"):
        x0, w0, text_align = 0.40, 0.55, "right"
    elif align.endswith("center"):
        x0, w0, text_align = 0.10, 0.80, "center"
    else:
        x0, w0, text_align = 0.05, 0.55, "left"

    if headline:
        layers.append(_text_layer(
            layer_id="headline", text=headline, role="h1",
            color_token="background",
            x=x0, y=y0, w=w0, h=0.12,
            align=text_align, weight="heading",
            anim_id=_ir_anim_id_for(ir, "headline"),
        ))  # type: ignore[arg-type]
    if subheadline:
        layers.append(_text_layer(
            layer_id="subheadline", text=subheadline, role="body",
            color_token="background",
            x=x0, y=y0 + 0.14, w=w0, h=0.10,
            align=text_align,
            anim_id=_ir_anim_id_for(ir, "subheadline"),
        ))  # type: ignore[arg-type]
    if caption:
        layers.append(_text_layer(
            layer_id="caption", text=caption, role="caption",
            color_token="background",
            x=0.05, y=0.94, w=0.9, h=0.04,
        ))  # type: ignore[arg-type]
    layers = [layer for layer in layers if layer is not None]
    return background, layers


def _engine_diagram_block(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    headline = _str_or_none(props.get("headline"))
    subheadline = _str_or_none(props.get("subheadline"))
    nodes = _list_of_mappings(props.get("nodes"))
    edges = _list_of_mappings(props.get("edges"))

    background = {"kind": "solid", "color_token": "surface"}
    layers: list[dict[str, Any]] = []
    if headline:
        layers.append(_text_layer(
            layer_id="headline", text=headline, role="h1",
            x=0.05, y=0.08, w=0.9, h=0.10, weight="heading",
            anim_id=_ir_anim_id_for(ir, "headline"),
        ))  # type: ignore[arg-type]
    if subheadline:
        layers.append(_text_layer(
            layer_id="subheadline", text=subheadline, role="body",
            color_token="text_secondary",
            x=0.05, y=0.20, w=0.9, h=0.06,
        ))  # type: ignore[arg-type]

    # Diagram canvas region (where graph nodes/edges live).
    canvas_x, canvas_y, canvas_w, canvas_h = 0.05, 0.30, 0.90, 0.60
    node_w, node_h = 0.16, 0.09

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
        nx = max(0.0, min(1.0, nx))
        ny = max(0.0, min(1.0, ny))
        cx = canvas_x + nx * canvas_w
        cy = canvas_y + ny * canvas_h
        node_index[nid] = {"cx": cx, "cy": cy}

    # Edges first (under nodes).
    for j, edge in enumerate(edges):
        a = node_index.get(_str_or_none(edge.get("from")) or "")
        b = node_index.get(_str_or_none(edge.get("to")) or "")
        if not a or not b:
            continue
        layers.append({
            "type": "edge",
            "id": f"edge-{j}",
            "x1": a["cx"], "y1": a["cy"],
            "x2": b["cx"], "y2": b["cy"],
            "color_token": "border",
            "label": _str_or_none(edge.get("label")),
        })

    # Then nodes.
    for i, node in enumerate(nodes):
        nid = _str_or_none(node.get("id"))
        if not nid or nid not in node_index:
            continue
        coords = node_index[nid]
        anim = _ir_anim_id_for_indexed(ir, "nodes", i)
        layers.append({
            "type": "shape",
            "id": f"node-{nid}-bg",
            "kind": "rect",
            "x": coords["cx"] - node_w / 2,
            "y": coords["cy"] - node_h / 2,
            "w": node_w, "h": node_h,
            "radius": 0.012,
            "fill_token": "primary",
            **({"anim_id": anim} if anim else {}),
        })
        label = _str_or_none(node.get("label"))
        if label:
            layers.append(_text_layer(
                layer_id=f"node-{nid}-label", text=label, role="body",
                color_token="background",
                x=coords["cx"] - node_w / 2,
                y=coords["cy"] - node_h / 2,
                w=node_w, h=node_h,
                align="center", weight="heading", anim_id=anim,
            ))  # type: ignore[arg-type]

    layers = [layer for layer in layers if layer is not None]
    return background, layers


# ── Public API ───────────────────────────────────────────────────────


def _engine_data_table(
    props: Mapping[str, Any], ir: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    headline = _str_or_none(props.get("headline"))
    subheadline = _str_or_none(props.get("subheadline"))
    headers = _coerce_str_list(props.get("headers"))
    rows_raw = props.get("rows") or []
    rows: list[list[str]] = []
    if isinstance(rows_raw, Iterable) and not isinstance(rows_raw, (str, bytes)):
        for row in rows_raw:
            if isinstance(row, Iterable) and not isinstance(row, (str, bytes, Mapping)):
                cells = [str(cell) for cell in row if cell is not None]
                if cells:
                    rows.append(cells)

    background = {"kind": "solid", "color_token": "surface"}
    layers: list[dict[str, Any]] = []
    if headline:
        layers.append(_text_layer(
            layer_id="headline", text=headline, role="h1",
            x=0.05, y=0.08, w=0.9, h=0.10, weight="heading",
            anim_id=_ir_anim_id_for(ir, "headline"),
        ))  # type: ignore[arg-type]
    if subheadline:
        layers.append(_text_layer(
            layer_id="subheadline", text=subheadline, role="body",
            color_token="text_secondary", x=0.05, y=0.20, w=0.9, h=0.06,
        ))  # type: ignore[arg-type]

    col_count = max(len(headers), max((len(row) for row in rows), default=0), 1)
    col_w = 0.90 / col_count
    start_y = 0.31
    row_h = 0.07
    for ci in range(col_count):
        header = headers[ci] if ci < len(headers) else ""
        if header:
            layers.append(_text_layer(
                layer_id=f"table-header-{ci}", text=header, role="caption",
                color_token="primary", x=0.05 + ci * col_w, y=start_y,
                w=col_w - 0.01, h=row_h, weight="heading",
                anim_id=_ir_anim_id_for_indexed(ir, "headers", ci),
            ))  # type: ignore[arg-type]
    for ri, row in enumerate(rows[:6]):
        y = start_y + row_h * (ri + 1)
        for ci in range(col_count):
            cell = row[ci] if ci < len(row) else ""
            if not cell:
                continue
            layers.append(_text_layer(
                layer_id=f"table-cell-{ri}-{ci}", text=cell, role="body",
                color_token="text_primary" if ci == 0 else "text_secondary",
                x=0.05 + ci * col_w, y=y, w=col_w - 0.01, h=row_h,
                weight="heading" if ci == 0 else None,
                anim_id=_ir_anim_id_for_indexed(ir, "rows", ri),
            ))  # type: ignore[arg-type]

    layers = [layer for layer in layers if layer is not None]
    return background, layers


_KIT_TRANSLATORS = {
    "TitleHero":       _engine_title_hero,
    "StatHero":        _engine_stat_hero,
    "ChartBlock":      _engine_chart_block,
    "TimelineBlock":   _engine_timeline_block,
    "ComparisonBlock": _engine_comparison_block,
    "FeatureGrid":     _engine_feature_grid,
    "GlassCard":       _engine_feature_grid,
    "BentoGrid":       _engine_feature_grid,
    "ValuePropGrid":   _engine_feature_grid,
    "ProblemSolution": _engine_feature_grid,
    "TeamGrid":        _engine_team_grid,
    "QuoteBlock":      _engine_quote_block,
    "FullBleedImage":  _engine_full_bleed_image,
    "DiagramBlock":    _engine_diagram_block,
    "DataTable":       _engine_data_table,
    "ProcessFlow":     _engine_timeline_block,
    "Roadmap":         _engine_timeline_block,
}


def build_engine(
    *,
    kit: str,
    props: Mapping[str, Any],
    animation_ir: Mapping[str, Any] | None = None,
    design_system: Mapping[str, Any] | None = None,  # noqa: ARG001 (reserved for future theming hints)
    slide_id: str | None = None,
) -> dict[str, Any]:
    """
    Build the engine artifact from the same tuple all transformers consume.

    Returns a dict with: ``schema_version``, ``kit``, ``slide_id``,
    ``viewport``, ``background``, ``layers``, ``fingerprint``.

    Unknown kits emit a single ``error`` layer; never a fabricated kit.
    """
    kit_name = (kit or "").strip()
    ir = animation_ir if isinstance(animation_ir, Mapping) else {}
    translator = _KIT_TRANSLATORS.get(kit_name)
    if translator is None:
        background = {"kind": "solid", "color_token": "background"}
        layers: list[dict[str, Any]] = [{
            "type": "error",
            "id": "engine-unknown-kit",
            "code": "unknown_kit",
            "message": f"Unknown kit component: {kit_name or '(empty)'}",
            "x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0,
        }]
    else:
        background, layers = translator(props or {}, ir)

    artifact: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "kit": kit_name,
        "slide_id": slide_id or None,
        "viewport": dict(_VIEWPORT),
        "background": background,
        "layers": layers,
    }
    # Stable, deterministic fingerprint over the canonical JSON form.
    serialized = json.dumps(artifact, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    artifact["fingerprint"] = hashlib.sha1(serialized.encode("utf-8")).hexdigest()[:12]
    return artifact
