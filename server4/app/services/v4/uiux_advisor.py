"""Deterministic UI/UX advisor for V4 slide quality gates.

The catalog is a local snapshot extracted from ui-ux-pro-max-skill. This module
does not call an LLM; it only ranks local rows and detects obvious design
anti-patterns in compiled slide props/tokens.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence


_CATALOG_PATH = Path(__file__).resolve().parent / "assets" / "uiux_design_catalog.json"
_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "]"
)
_PURPLE_PINK_HEXES = {
    "#8b00ff",
    "#9333ea",
    "#a855f7",
    "#c084fc",
    "#d946ef",
    "#e879f9",
    "#ec4899",
    "#ff1493",
    "#ff00ff",
}
_NEON_HEXES = {"#00ff00", "#39ff14", "#00ffff", "#ff00ff", "#ffff00"}
_STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "in",
    "of",
    "on",
    "the",
    "to",
    "with",
}


@dataclass(frozen=True)
class RecommendedDesignSystem:
    style_family: dict[str, Any]
    palette: dict[str, Any]
    font_pairing: dict[str, Any]
    rationale: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AntiPatternIssue:
    code: str
    message: str
    target: str
    rule_id: str
    severity: str = "warn"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    with _CATALOG_PATH.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("uiux_design_catalog.json must contain a JSON object")
    return data


def recommend_design(
    industry: str | None,
    audience: str | None,
    mode: str | None,
    brand_brief: Mapping[str, Any] | str | None = None,
) -> RecommendedDesignSystem:
    """Return a deterministic local recommendation from the catalog."""

    catalog = load_catalog()
    query = " ".join(
        part
        for part in (
            industry or "",
            audience or "",
            mode or "",
            _brand_text(brand_brief),
        )
        if part
    )
    query_terms = _terms(query)
    styles = list(catalog.get("style_families") or [])
    palettes = list(catalog.get("palette_library") or [])
    fonts = list(catalog.get("font_pairings") or [])

    style = _best_row(
        styles,
        query_terms,
        fields=("name", "category", "mood", "best_for"),
        default_index=0,
    )
    palette = _best_row(
        palettes,
        query_terms,
        fields=("product_type", "notes"),
        default_index=0,
    )
    font = _best_row(
        fonts,
        query_terms,
        fields=("name", "mood", "best_for", "category"),
        default_index=0,
    )
    return RecommendedDesignSystem(
        style_family=dict(style),
        palette=dict(palette),
        font_pairing=dict(font),
        rationale=[
            "Matched against local ui-ux catalog terms.",
            f"Input terms: {', '.join(sorted(query_terms)[:8]) or 'default business deck'}",
        ],
    )


def evaluate_anti_patterns(
    compiled_slide: Mapping[str, Any],
    design_tokens: Mapping[str, Any] | None = None,
) -> list[AntiPatternIssue]:
    """Flag deterministic design anti-patterns visible in a compiled slide."""

    tokens = design_tokens or {}
    props = _props(compiled_slide)
    haystack = " ".join(
        [
            _visible_text(props),
            _visible_text(tokens),
            str(compiled_slide.get("background") or ""),
            str(compiled_slide.get("visual_direction") or ""),
        ]
    ).lower()
    colors = [c.lower() for c in _HEX_RE.findall(haystack)]
    palette = tokens.get("palette") if isinstance(tokens.get("palette"), Mapping) else {}
    issues: list[AntiPatternIssue] = []

    if _has_ai_purple_pink_gradient(haystack, colors):
        issues.append(
            AntiPatternIssue(
                code="design_anti_pattern",
                message="The slide uses an AI-purple/pink gradient pattern.",
                target="design_tokens.palette",
                rule_id="avoid.ai_purple_pink_gradients",
            )
        )
    if _has_neon(haystack, colors):
        issues.append(
            AntiPatternIssue(
                code="design_anti_pattern",
                message="The slide uses neon colors that read as generic AI UI.",
                target="design_tokens.palette",
                rule_id="avoid.neon_colors",
            )
        )
    if _EMOJI_RE.search(_visible_text(props)):
        issues.append(
            AntiPatternIssue(
                code="design_anti_pattern",
                message="The slide uses emoji as structural visual language.",
                target="visible_text",
                rule_id="ux.no_emoji_icons",
            )
        )
    if _has_harsh_shadow(tokens):
        issues.append(
            AntiPatternIssue(
                code="design_anti_pattern",
                message="The slide uses heavy shadows that conflict with boardroom export polish.",
                target="design_tokens.shape",
                rule_id="avoid.harsh_shadows",
            )
        )
    contrast = _palette_contrast(palette)
    if contrast is not None and contrast < 4.5:
        issues.append(
            AntiPatternIssue(
                code="design_anti_pattern",
                message=f"Text/background contrast is below WCAG AA ({contrast:.2f}:1).",
                target="design_tokens.palette",
                rule_id="wcag.contrast_aa",
            )
        )
    return _dedupe_issues(issues)


def _brand_text(brand_brief: Mapping[str, Any] | str | None) -> str:
    if isinstance(brand_brief, str):
        return brand_brief
    if isinstance(brand_brief, Mapping):
        return _visible_text(brand_brief)
    return ""


def _terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", (text or "").lower())
        if token not in _STOPWORDS and len(token) > 1
    }


def _best_row(
    rows: Sequence[Mapping[str, Any]],
    query_terms: set[str],
    *,
    fields: Sequence[str],
    default_index: int,
) -> Mapping[str, Any]:
    if not rows:
        return {}

    def score(row: Mapping[str, Any]) -> tuple[int, str]:
        row_text = " ".join(str(row.get(field) or "") for field in fields).lower()
        row_terms = _terms(row_text)
        overlap = len(query_terms & row_terms)
        return overlap, str(row.get("id") or row.get("name") or "")

    best = max(rows, key=score)
    if score(best)[0] == 0:
        return rows[min(default_index, len(rows) - 1)]
    return best


def _props(compiled: Mapping[str, Any]) -> Mapping[str, Any]:
    artifacts = compiled.get("artifacts")
    if isinstance(artifacts, Mapping):
        kit = artifacts.get("kit_jsx")
        if isinstance(kit, Mapping) and isinstance(kit.get("props_json"), Mapping):
            return kit["props_json"]
    render_props = compiled.get("render_props")
    if isinstance(render_props, Mapping):
        return render_props
    return {}


def _visible_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join(_visible_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_visible_text(v) for v in value)
    return ""


def _has_ai_purple_pink_gradient(text: str, colors: Sequence[str]) -> bool:
    has_gradient = "gradient" in text or "linear-gradient" in text or "radial-gradient" in text
    has_purple = "purple" in text or "violet" in text or any(c in _PURPLE_PINK_HEXES for c in colors)
    has_pink = "pink" in text or "magenta" in text or any(c in {"#ec4899", "#ff1493", "#ff00ff"} for c in colors)
    return (has_gradient and has_purple and has_pink) or (has_purple and has_pink and len(colors) >= 2)


def _has_neon(text: str, colors: Sequence[str]) -> bool:
    if "neon" in text:
        return True
    if any(c in _NEON_HEXES for c in colors):
        return True
    return any(_is_neon_hex(c) for c in colors)


def _is_neon_hex(value: str) -> bool:
    rgb = _hex_to_rgb(value)
    if rgb is None:
        return False
    r, g, b = rgb
    high = sum(1 for c in rgb if c >= 235)
    low = sum(1 for c in rgb if c <= 30)
    return high >= 1 and low >= 1 and max(r, g, b) - min(r, g, b) > 210


def _has_harsh_shadow(tokens: Mapping[str, Any]) -> bool:
    shape = tokens.get("shape") if isinstance(tokens.get("shape"), Mapping) else {}
    text = _visible_text(shape).lower()
    if not text:
        return False
    if "rgba(0,0,0,0.4" in text or "rgba(0, 0, 0, 0.4" in text:
        return True
    px_values = [int(v) for v in re.findall(r"\b(\d{2,3})px\b", text)]
    return any(v >= 28 for v in px_values)


def _palette_contrast(palette: Mapping[str, Any]) -> float | None:
    if not isinstance(palette, Mapping):
        return None
    fg = str(
        palette.get("text_primary")
        or palette.get("foreground")
        or palette.get("text")
        or ""
    )
    bg = str(palette.get("background") or "")
    if not fg or not bg:
        return None
    return _contrast_ratio(fg, bg)


def _hex_to_rgb(value: str) -> tuple[int, int, int] | None:
    s = str(value or "").strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) < 6:
        return None
    try:
        return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    except ValueError:
        return None


def _relative_luminance(hex_color: str) -> float | None:
    rgb = _hex_to_rgb(hex_color)
    if rgb is None:
        return None

    def linear(c: int) -> float:
        channel = c / 255.0
        return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(rgb[0]), linear(rgb[1]), linear(rgb[2]))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(fg_hex: str, bg_hex: str) -> float | None:
    fg = _relative_luminance(fg_hex)
    bg = _relative_luminance(bg_hex)
    if fg is None or bg is None:
        return None
    lighter, darker = (fg, bg) if fg >= bg else (bg, fg)
    return (lighter + 0.05) / (darker + 0.05)


def _dedupe_issues(issues: Sequence[AntiPatternIssue]) -> list[AntiPatternIssue]:
    seen: set[str] = set()
    out: list[AntiPatternIssue] = []
    for issue in issues:
        key = issue.rule_id
        if key in seen:
            continue
        seen.add(key)
        out.append(issue)
    return out


__all__ = [
    "AntiPatternIssue",
    "RecommendedDesignSystem",
    "evaluate_anti_patterns",
    "load_catalog",
    "recommend_design",
]
