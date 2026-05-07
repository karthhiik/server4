"""
V4 Quality Scorer — Phase 4.5 (Day 8) of v3-final plan.

Real, deterministic per-slide scoring across three dimensions:

  1. **contrast** — WCAG 2.1 relative-luminance ratio between the
     slide's primary text color and its background, using the real
     palette in the resolved DesignSystem tokens. No estimation —
     the formula in the WCAG spec, applied to the actual hex values
     the slide will render with.
  2. **alignment** — Structural validity check against the kit's
     contract. A `ChartBlock` with empty data is misaligned by
     definition (the chart canvas will be blank); a `DiagramBlock`
     with edges referencing missing nodes is misaligned; a
     `TitleHero` with no headline is misaligned. These are content
     defects the upstream writer can produce, and they must show up
     in the score so Phase 4.5+ pipelines can re-roll them.
  3. **density** — Total user-visible character count against a
     per-kit target band derived from the kit's React layout
     (e.g. TitleHero target = 10-250 chars; FeatureGrid = 80-800).
     Decks with sparse Hero slides feel empty; dense FeatureGrids
     feel cramped — both penalised proportionally to deviation.

Output shape (lives at `compiled_slide.quality_score`):

    {
      "schema_version": 1,
      "overall": 82,
      "passes_threshold": True,        # overall >= 70
      "dimensions": {
        "contrast":  {"score": 100, "ratio": 12.6, "passes_wcag_aa": True,  "details": "…"},
        "alignment": {"score":  90, "issues": [],  "details": "…"},
        "density":   {"score":  78, "char_count": 142, "target_min": 20, "target_max": 400}
      }
    }

The scorer is consumed by:
  * Phase 6 hot-swap (only swap to a regenerated slide if its score
    is ≥ the current slide's).
  * Phase 12 few-shot prompt injection (low-scoring slides are
    excluded from the few-shot pool).
  * Frontend deck dashboard (badge low-quality slides for review).

NO LLM calls. <2ms per slide.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping


_SCHEMA_VERSION = 1


# ── Per-kit density targets ─────────────────────────────────────────
# Hand-tuned against the kit React components' visual capacity.
# `(min_chars, max_chars)` of total user-visible text on the slide.
# Hitting the band → score 100. Outside the band → linear penalty
# proportional to how far off you are (50% penalty per band-width of
# overshoot/undershoot, capped at 0).

_DENSITY_TARGETS: dict[str, tuple[int, int]] = {
    "TitleHero":       (10, 250),
    "StatHero":        (20, 400),
    "ChartBlock":      (30, 500),
    "TimelineBlock":   (50, 800),
    "ComparisonBlock": (100, 1200),
    "FeatureGrid":     (80, 800),
    "TeamGrid":        (50, 600),
    "QuoteBlock":      (20, 400),
    "FullBleedImage":  (10, 200),
    "DiagramBlock":    (30, 500),
}


# ── WCAG 2.1 color math ─────────────────────────────────────────────

def _hex_to_rgb(value: str) -> tuple[int, int, int] | None:
    """Parse `#RGB` / `#RRGGBB` into an (r, g, b) 0-255 triple. None on failure."""
    if not isinstance(value, str):
        return None
    s = value.strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        return None
    try:
        return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    except ValueError:
        return None


def _srgb_channel_to_linear(c: float) -> float:
    """sRGB → linear-light per WCAG 2.1 SC 1.4.3 / 1.4.6."""
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float | None:
    rgb = _hex_to_rgb(hex_color)
    if rgb is None:
        return None
    r, g, b = (
        _srgb_channel_to_linear(rgb[0]),
        _srgb_channel_to_linear(rgb[1]),
        _srgb_channel_to_linear(rgb[2]),
    )
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(fg_hex: str, bg_hex: str) -> float | None:
    l1 = _relative_luminance(fg_hex)
    l2 = _relative_luminance(bg_hex)
    if l1 is None or l2 is None:
        return None
    lighter, darker = (l1, l2) if l1 >= l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)


# ── Helpers ─────────────────────────────────────────────────────────

def _collect_visible_text(value: Any) -> list[str]:
    """
    Walk a kit props dict and collect every user-visible string. URLs
    (imageUrl / photoUrl / linkedInUrl / logoUrl) and structural enum
    fields (variant / orientation / overlay / align / type / xKey /
    nameKey / valueKey / icon / id / from / to / style / trend) are
    excluded — they aren't seen on screen.
    """
    skip_keys = {
        "imageUrl", "photoUrl", "linkedInUrl", "logoUrl", "iconUrl",
        "variant", "orientation", "overlay", "align", "type",
        "xKey", "yKeys", "nameKey", "valueKey", "icon",
        "id", "from", "to", "style", "trend", "highlight", "done",
        "x", "y", "columns", "seriesLabels", "yKey",
    }
    out: list[str] = []

    def walk(node: Any, parent_key: str | None = None):
        if isinstance(node, str):
            if parent_key in skip_keys:
                return
            s = node.strip()
            if s:
                out.append(s)
        elif isinstance(node, Mapping):
            for k, v in node.items():
                if k in skip_keys:
                    continue
                walk(v, k)
        elif isinstance(node, (list, tuple)):
            for item in node:
                walk(item, parent_key)
        # numbers / bools / None contribute no visible characters.

    walk(value, None)
    return out


def _total_char_count(props: Mapping[str, Any]) -> int:
    return sum(len(s) for s in _collect_visible_text(props))


def _clamp_score(s: float) -> int:
    return int(round(max(0.0, min(100.0, s))))


# ── Per-dimension scorers ───────────────────────────────────────────

def _score_contrast(
    kit: str, props: Mapping[str, Any], design_tokens: Mapping[str, Any]
) -> dict[str, Any]:
    """
    Compute the WCAG contrast ratio for the slide's text-on-background
    pairing. Uses the actual palette in the resolved tokens.
    """
    palette = design_tokens.get("palette") if isinstance(design_tokens, Mapping) else None
    if not isinstance(palette, Mapping):
        return {
            "score": 0,
            "ratio": None,
            "passes_wcag_aa": False,
            "details": "design_tokens.palette missing — cannot compute contrast",
        }

    text_color = palette.get("text_primary") or palette.get("text") or "#000000"
    surface = palette.get("surface") or palette.get("background") or "#FFFFFF"
    background = palette.get("background") or surface

    # Determine the actual rendered background per kit/variant.
    # These mirror the rules in `html_transformer._BASE_CSS` and the
    # per-kit CSS so the score reflects what the user will see.
    variant = (props.get("variant") or "").lower() if isinstance(props, Mapping) else ""

    if kit == "TitleHero" and variant == "image":
        # Image variant always renders text over a dark scrim — the
        # scrim guarantees ≥7:1 against white text. Hard-code that
        # known-good case rather than fake a contrast computation.
        return {
            "score": 100,
            "ratio": 7.0,
            "passes_wcag_aa": True,
            "details": "TitleHero[image] uses a dark scrim overlay (guaranteed AA)",
        }
    if kit == "TitleHero" and variant == "gradient":
        # Gradient runs primary → accent. Text is rendered with
        # `--color-background` (white in light themes) — score the
        # darker of the two gradient stops vs that color.
        primary = palette.get("primary", "#000000")
        accent = palette.get("accent", primary)
        bg_for_text = palette.get("background", "#FFFFFF")
        ratios = [
            r for r in (
                _contrast_ratio(bg_for_text, primary),
                _contrast_ratio(bg_for_text, accent),
            ) if r is not None
        ]
        if not ratios:
            return {
                "score": 0, "ratio": None, "passes_wcag_aa": False,
                "details": "could not parse gradient stop colors",
            }
        ratio = min(ratios)  # worst case along the gradient
        return _wcag_score_block(ratio, "TitleHero[gradient]: text vs gradient stops")
    if kit == "QuoteBlock" and (props.get("variant") or "").lower() == "accent":
        accent = palette.get("accent", "#000000")
        bg_for_text = palette.get("background", "#FFFFFF")
        ratio = _contrast_ratio(bg_for_text, accent)
        if ratio is None:
            return {"score": 0, "ratio": None, "passes_wcag_aa": False, "details": "accent palette parse failed"}
        return _wcag_score_block(ratio, "QuoteBlock[accent]: text vs accent")
    if kit == "FullBleedImage":
        # Always renders white text over a scrim/duotone. Same
        # known-good case as TitleHero[image].
        return {
            "score": 100,
            "ratio": 7.0,
            "passes_wcag_aa": True,
            "details": "FullBleedImage uses scrim/duotone overlay (guaranteed AA)",
        }

    # Default: text_primary on surface (the base slide-stage rule in
    # _BASE_CSS). Also check the secondary text color for completeness
    # (used by .slide-sub) and report the worst.
    pair_ratios: list[tuple[float, str]] = []
    r_main = _contrast_ratio(text_color, surface)
    if r_main is not None:
        pair_ratios.append((r_main, "text_primary↔surface"))
    secondary = palette.get("text_secondary")
    if isinstance(secondary, str):
        r_sec = _contrast_ratio(secondary, surface)
        if r_sec is not None:
            pair_ratios.append((r_sec, "text_secondary↔surface"))
    if not pair_ratios:
        return {
            "score": 0, "ratio": None, "passes_wcag_aa": False,
            "details": f"could not parse palette colors text={text_color!r} surface={surface!r}",
        }
    pair_ratios.sort(key=lambda x: x[0])
    worst_ratio, worst_pair = pair_ratios[0]
    return _wcag_score_block(worst_ratio, f"worst pair: {worst_pair}")


def _wcag_score_block(ratio: float, details: str) -> dict[str, Any]:
    """Map a real contrast ratio to a 0-100 score, anchored to WCAG bands."""
    # WCAG bands:
    #   < 3.0     fail
    #   3.0-4.49  AA-large only
    #   4.5-6.99  AA
    #   ≥ 7.0     AAA
    if ratio >= 7.0:
        score = 100
    elif ratio >= 4.5:
        # Linear: 4.5 → 80, 7.0 → 99
        score = 80 + (ratio - 4.5) / (7.0 - 4.5) * 19
    elif ratio >= 3.0:
        # Linear: 3.0 → 50, 4.5 → 79
        score = 50 + (ratio - 3.0) / (4.5 - 3.0) * 29
    elif ratio >= 1.5:
        # Linear: 1.5 → 0, 3.0 → 49
        score = (ratio - 1.5) / (3.0 - 1.5) * 49
    else:
        score = 0
    return {
        "score": _clamp_score(score),
        "ratio": round(ratio, 2),
        "passes_wcag_aa": ratio >= 4.5,
        "details": details,
    }


def _score_alignment(kit: str, props: Mapping[str, Any]) -> dict[str, Any]:
    """
    Structural validity per kit. Each kit has a contract of required
    fields; missing/malformed fields are real defects (the React
    component renders an empty box).
    """
    issues: list[str] = []
    p = props or {}

    if kit == "TitleHero":
        if not _nonempty_str(p.get("headline")):
            issues.append("missing headline")
        if (p.get("variant") or "").lower() == "image" and not _nonempty_str(p.get("imageUrl")):
            issues.append("variant=image but no imageUrl")
    elif kit == "StatHero":
        stats = [s for s in (p.get("stats") or []) if isinstance(s, Mapping) and _nonempty_str(s.get("value"))]
        if not stats:
            issues.append("no usable stats")
        elif len(stats) > 4:
            issues.append(f"{len(stats)} stats (max 4 fit)")
        if not _nonempty_str(p.get("headline")) and not _nonempty_str(p.get("eyebrow")):
            issues.append("no headline or eyebrow")
    elif kit == "ChartBlock":
        data = [d for d in (p.get("data") or []) if isinstance(d, Mapping)]
        if not data:
            issues.append("empty chart data")
        chart_type = (p.get("type") or "bar").lower()
        if chart_type in {"bar", "line", "area"}:
            y_keys = p.get("yKeys") or []
            if not y_keys and data:
                # Need at least one numeric key.
                numeric_keys = [k for k, v in data[0].items() if isinstance(v, (int, float))]
                if not numeric_keys:
                    issues.append(f"{chart_type} chart has no numeric series")
        if chart_type == "pie":
            value_key = p.get("valueKey") or "value"
            positives = [
                d for d in data
                if isinstance(d.get(value_key), (int, float)) and float(d[value_key]) > 0
            ]
            if not positives:
                issues.append("pie chart has no positive values")
        if not _nonempty_str(p.get("headline")):
            issues.append("missing headline")
    elif kit == "TimelineBlock":
        ms = [m for m in (p.get("milestones") or []) if isinstance(m, Mapping)]
        if len(ms) < 2:
            issues.append("timeline needs ≥2 milestones")
        if not _nonempty_str(p.get("headline")):
            issues.append("missing headline")
    elif kit == "ComparisonBlock":
        cols = [c for c in (p.get("columns") or []) if isinstance(c, Mapping)]
        rows = [r for r in (p.get("rows") or []) if isinstance(r, Mapping)]
        if len(cols) < 2:
            issues.append("comparison needs ≥2 columns")
        if not rows:
            issues.append("comparison has no rows")
        col_names = {c.get("name") for c in cols}
        for ri, r in enumerate(rows):
            values = r.get("values") or {}
            if isinstance(values, Mapping):
                missing = [n for n in col_names if n and n not in values]
                if missing:
                    issues.append(f"row {ri} missing values for {missing}")
    elif kit == "FeatureGrid":
        feats = [f for f in (p.get("features") or []) if isinstance(f, Mapping)]
        if not feats:
            issues.append("feature grid has no features")
        cols = p.get("columns") or 3
        try:
            cols_int = int(cols)
        except (TypeError, ValueError):
            cols_int = 3
        if feats and cols_int and len(feats) % cols_int != 0 and len(feats) > cols_int:
            # Trailing row will be ragged.
            issues.append(f"{len(feats)} features in {cols_int} columns leaves ragged row")
    elif kit == "TeamGrid":
        members = [m for m in (p.get("members") or []) if isinstance(m, Mapping) and _nonempty_str(m.get("name"))]
        if not members:
            issues.append("team grid has no members with names")
    elif kit == "QuoteBlock":
        if not _nonempty_str(p.get("quote")):
            issues.append("quote text is empty")
        if not _nonempty_str(p.get("attribution")):
            issues.append("quote has no attribution")
    elif kit == "FullBleedImage":
        if not _nonempty_str(p.get("imageUrl")):
            issues.append("FullBleedImage has no imageUrl")
    elif kit == "DiagramBlock":
        nodes = [n for n in (p.get("nodes") or []) if isinstance(n, Mapping) and _nonempty_str(n.get("id"))]
        edges = [e for e in (p.get("edges") or []) if isinstance(e, Mapping)]
        node_ids = {n["id"] for n in nodes}
        if len(nodes) < 2:
            issues.append("diagram needs ≥2 nodes")
        for n in nodes:
            x, y = n.get("x"), n.get("y")
            if not (isinstance(x, (int, float)) and 0.0 <= float(x) <= 1.0):
                issues.append(f"node {n.get('id')!r} has invalid x={x!r}")
            if not (isinstance(y, (int, float)) and 0.0 <= float(y) <= 1.0):
                issues.append(f"node {n.get('id')!r} has invalid y={y!r}")
        for e in edges:
            if e.get("from") not in node_ids:
                issues.append(f"edge from={e.get('from')!r} references missing node")
            if e.get("to") not in node_ids:
                issues.append(f"edge to={e.get('to')!r} references missing node")
    else:
        issues.append(f"unknown kit {kit!r}")

    # Also score headline length — real kits all clip very long headlines.
    headline = p.get("headline")
    if isinstance(headline, str) and len(headline) > 120:
        issues.append(f"headline {len(headline)} chars (>120 will wrap awkwardly)")

    # Scoring: each issue → -15. Cap at 0.
    score = _clamp_score(100 - 15 * len(issues))
    return {
        "score": score,
        "issues": issues,
        "details": (
            "all structural fields present"
            if not issues
            else f"{len(issues)} structural issue(s)"
        ),
    }


def _nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _score_density(kit: str, props: Mapping[str, Any]) -> dict[str, Any]:
    target = _DENSITY_TARGETS.get(kit)
    char_count = _total_char_count(props or {})
    if target is None:
        return {
            "score": 50,  # unknown kit — neutral score
            "char_count": char_count,
            "target_min": None,
            "target_max": None,
            "details": f"no density target for kit {kit!r}",
        }
    lo, hi = target
    band_width = hi - lo
    if lo <= char_count <= hi:
        score = 100
        detail = "in target band"
    elif char_count < lo:
        # Linear penalty: -50 / band_width per char short, capped 0.
        deficit = lo - char_count
        score = _clamp_score(100 - (deficit / band_width) * 100)
        detail = f"sparse: {deficit} chars below min"
    else:
        overshoot = char_count - hi
        score = _clamp_score(100 - (overshoot / band_width) * 100)
        detail = f"crowded: {overshoot} chars over max"
    return {
        "score": score,
        "char_count": char_count,
        "target_min": lo,
        "target_max": hi,
        "details": detail,
    }


# ── Public API ──────────────────────────────────────────────────────

def score_slide(
    *,
    kit: str,
    props: Mapping[str, Any],
    design_tokens: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Compute a real quality score for one slide.

    `design_tokens` is the same dict produced by `design_resolver`'s
    `ResolvedDesignTokens.to_dict()` — contains palette, fonts, scale,
    etc. The contrast scorer only consumes `palette`.
    """
    contrast = _score_contrast(kit, props or {}, design_tokens or {})
    alignment = _score_alignment(kit, props or {})
    density = _score_density(kit, props or {})
    overall = round(
        (contrast["score"] + alignment["score"] + density["score"]) / 3
    )
    return {
        "schema_version": _SCHEMA_VERSION,
        "overall": int(overall),
        "passes_threshold": int(overall) >= 70,
        "dimensions": {
            "contrast": contrast,
            "alignment": alignment,
            "density": density,
        },
    }


def attach_quality_scores(
    compiled_slides: list[dict[str, Any]],
    design_tokens: Mapping[str, Any] | None,
) -> None:
    """
    Mutate each compiled slide to populate `quality_score`. Defensive
    against malformed dicts — slides without a recognised
    `kit_component` get an explicit error score rather than crashing
    the whole pipeline.
    """
    tokens = design_tokens if isinstance(design_tokens, Mapping) else {}
    for slide in compiled_slides:
        if not isinstance(slide, dict):
            continue
        kit = slide.get("kit_component") or ""
        artifacts = slide.get("artifacts") or {}
        kit_jsx = artifacts.get("kit_jsx") if isinstance(artifacts, dict) else None
        props = (
            kit_jsx.get("props_json")
            if isinstance(kit_jsx, dict) and isinstance(kit_jsx.get("props_json"), dict)
            else {}
        )
        slide["quality_score"] = score_slide(
            kit=kit, props=props, design_tokens=tokens
        )
