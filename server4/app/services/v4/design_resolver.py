"""
V4 Design Resolver — turns the user's optional `design_profile` into a concrete,
fully-populated `ResolvedDesignTokens` set that every downstream stage
consumes (writer palette context, code agent JSX, sandbox preview, PPTX export).

Design principles (from .github/skills/design-system-intelligence/SKILL.md
and server4/Premium_plan_10.2V.md Part VII):

  - OKLCH color math (perceptually uniform). Radix-style 12-step logic,
    collapsed here to the 8 semantic roles a slide actually consumes.
  - Deterministic: same input → same output. No LLM call. No randomness.
  - Optional-first: every field the user did NOT provide is auto-filled
    based on purpose / industry / audience.
  - Serialized as DTCG v2025.10-compatible JSON in the presentation doc
    so the frontend and PPTX export read the same snapshot.

This module has zero external deps beyond stdlib — `colorsys` + a small
OKLCH↔hex helper (≈80 LOC) keeps the bundle light and avoids the
`colour-science` / `culori` dependencies.
"""

from __future__ import annotations

import colorsys
import hashlib
import math
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════
# TOKEN SHAPE (mirrors frontend DesignTokens in sandboxProtocol.ts)
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Palette:
    primary: str
    secondary: str
    accent: str
    background: str
    surface: str
    text_primary: str
    text_secondary: str
    text_muted: str
    success: str
    warning: str
    danger: str
    chart: list[str] = field(default_factory=list)


@dataclass
class Fonts:
    heading: str
    body: str
    mono: str = "ui-monospace, SFMono-Regular, Menlo, monospace"


@dataclass
class TypeScale:
    display: float
    h1: float
    h2: float
    h3: float
    body: float
    caption: float


@dataclass
class Spacing:
    slide_margin_in: float
    gap_in: float
    section_gap_in: float


@dataclass
class Weights:
    heading: int
    body: int


@dataclass
class ResolvedDesignTokens:
    palette: Palette
    fonts: Fonts
    scale: TypeScale
    spacing: Spacing
    weights: Weights
    density: str                 # compact | comfortable | spacious
    line_height: float
    letter_spacing_em: float
    provided_by: str             # user | auto | hybrid

    def to_dict(self) -> dict[str, Any]:
        return {
            "palette": asdict(self.palette),
            "fonts": asdict(self.fonts),
            "scale": asdict(self.scale),
            "spacing": asdict(self.spacing),
            "weights": asdict(self.weights),
            "density": self.density,
            "line_height": self.line_height,
            "letter_spacing_em": self.letter_spacing_em,
            "provided_by": self.provided_by,
        }


# ═══════════════════════════════════════════════════════════════════
# OKLCH ↔ HEX (minimal, no deps)
# ═══════════════════════════════════════════════════════════════════
# Reference: https://bottosson.github.io/posts/oklab/
# OKLCH = (L, C, H) where L ∈ [0,1], C ≥ 0, H ∈ [0, 360)

def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def hex_to_oklch(hex_str: str) -> tuple[float, float, float]:
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r = _srgb_to_linear(int(h[0:2], 16) / 255)
    g = _srgb_to_linear(int(h[2:4], 16) / 255)
    b = _srgb_to_linear(int(h[4:6], 16) / 255)
    # Linear sRGB → Oklab (Björn Ottosson matrix)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b_ = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    C = math.hypot(a, b_)
    H = (math.degrees(math.atan2(b_, a)) + 360) % 360
    return L, C, H


def oklch_to_hex(L: float, C: float, H: float) -> str:
    a = C * math.cos(math.radians(H))
    b = C * math.sin(math.radians(H))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    rgb = [_linear_to_srgb(max(0.0, min(1.0, c))) for c in (r, g, bl)]
    return "#" + "".join(f"{int(round(max(0, min(1, c)) * 255)):02x}" for c in rgb)


def _adjust(hex_str: str, *, dL: float = 0.0, dC: float = 0.0, dH: float = 0.0) -> str:
    L, C, H = hex_to_oklch(hex_str)
    return oklch_to_hex(
        max(0.0, min(1.0, L + dL)),
        max(0.0, C + dC),
        (H + dH) % 360,
    )


def _contrast_text(bg_hex: str) -> str:
    """Return a near-black or near-white text color for the given bg."""
    L, _, _ = hex_to_oklch(bg_hex)
    return "#0b0d12" if L > 0.60 else "#f8fafc"


# ═══════════════════════════════════════════════════════════════════
# PURPOSE / INDUSTRY → PALETTE & FONT DEFAULTS
# ═══════════════════════════════════════════════════════════════════
# When the user provides nothing, we pick a tasteful default informed by
# the deck purpose and the industry. These are deliberate starting points,
# NOT the final tokens — the resolver still derives scales/text colors.

_INDUSTRY_PALETTES: dict[str, dict[str, str]] = {
    "fintech":     {"primary": "#0b5cff", "accent": "#22c55e"},
    "healthcare":  {"primary": "#0ea5e9", "accent": "#14b8a6"},
    "ai":          {"primary": "#7c3aed", "accent": "#22d3ee"},
    "saas":        {"primary": "#2563eb", "accent": "#f97316"},
    "ecommerce":   {"primary": "#ef4444", "accent": "#fbbf24"},
    "edtech":      {"primary": "#0891b2", "accent": "#f59e0b"},
    "climate":     {"primary": "#059669", "accent": "#84cc16"},
    "security":    {"primary": "#1e293b", "accent": "#38bdf8"},
    "media":       {"primary": "#db2777", "accent": "#facc15"},
    "biotech":     {"primary": "#0d9488", "accent": "#a855f7"},
    "logistics":   {"primary": "#334155", "accent": "#f97316"},
    "default":     {"primary": "#2563eb", "accent": "#7c3aed"},
}

_PURPOSE_FONT_PAIRS: dict[str, dict[str, str]] = {
    # (heading, body) pairings vetted for on-screen readability at 16:9.
    "pitch_deck":       {"heading": "Inter", "body": "Inter"},
    "investor_update":  {"heading": "Inter", "body": "Inter"},
    "sales_deck":       {"heading": "Inter", "body": "Inter"},
    "conference_talk":  {"heading": "Manrope", "body": "Inter"},
    "product_launch":   {"heading": "Space Grotesk", "body": "Inter"},
    "academic":         {"heading": "Lora", "body": "Source Serif 4"},
    "educational":      {"heading": "Manrope", "body": "Inter"},
    "default":          {"heading": "Inter", "body": "Inter"},
}

# Font-pair override table: if user set EITHER heading or body but not both,
# these are the matching siblings we'll pair.
_FONT_SIBLINGS: dict[str, str] = {
    "Inter": "Inter",
    "Manrope": "Inter",
    "Space Grotesk": "Inter",
    "Lora": "Source Serif 4",
    "Source Serif 4": "Lora",
    "Playfair Display": "Source Sans 3",
    "DM Sans": "DM Sans",
    "Plus Jakarta Sans": "Plus Jakarta Sans",
    "IBM Plex Sans": "IBM Plex Sans",
    "Work Sans": "Work Sans",
}

# Type scales keyed by density. Units: points (PPTX-native).
_TYPE_SCALES: dict[str, TypeScale] = {
    "compact":      TypeScale(display=48, h1=36, h2=26, h3=20, body=14, caption=11),
    "comfortable":  TypeScale(display=57, h1=43, h2=32, h3=24, body=18, caption=13),
    "spacious":     TypeScale(display=68, h1=51, h2=38, h3=28, body=22, caption=15),
}

_DENSITY_SPACING: dict[str, Spacing] = {
    "compact":     Spacing(slide_margin_in=0.45, gap_in=0.15, section_gap_in=0.35),
    "comfortable": Spacing(slide_margin_in=0.55, gap_in=0.22, section_gap_in=0.50),
    "spacious":    Spacing(slide_margin_in=0.70, gap_in=0.30, section_gap_in=0.70),
}


# ═══════════════════════════════════════════════════════════════════
# CORE RESOLVER
# ═══════════════════════════════════════════════════════════════════

def _pick_industry_bucket(industry: Optional[str]) -> str:
    if not industry:
        return "default"
    s = industry.lower()
    for key in _INDUSTRY_PALETTES:
        if key != "default" and key in s:
            return key
    return "default"


def _derive_palette(primary: str, accent: Optional[str], background: Optional[str]) -> Palette:
    """Derive all 12 palette roles from a primary + optional accent + optional bg."""
    if accent is None:
        # Complementary-adjacent hue shift (~+140°) with slightly lifted chroma
        accent = _adjust(primary, dH=140.0, dC=0.02)

    # Background: near-black by default (dark theme). If user set a light bg
    # we'll detect it by luminance and flip the text roles accordingly.
    if background is None:
        background = "#0b0d12"

    bg_L, _, _ = hex_to_oklch(background)
    is_dark_theme = bg_L < 0.50

    # Surface: slightly lifted from background
    surface = _adjust(background, dL=0.04 if is_dark_theme else -0.04)

    # Text roles: high contrast to background
    text_primary = "#f8fafc" if is_dark_theme else "#0b0d12"
    text_secondary = _adjust(text_primary, dL=-0.15 if is_dark_theme else 0.20)
    text_muted = _adjust(text_primary, dL=-0.28 if is_dark_theme else 0.40)

    # Secondary brand: primary shifted 30° for UI accents
    secondary = _adjust(primary, dH=30.0, dL=-0.05)

    # Chart palette: primary + accent + 4 harmonized hues stepping around the
    # color wheel, each kept at a similar L/C to match visual weight.
    L_p, C_p, H_p = hex_to_oklch(primary)
    base_L = max(0.55, min(0.72, L_p))
    base_C = max(0.12, min(0.22, C_p))
    chart = [
        primary,
        accent,
        oklch_to_hex(base_L, base_C, (H_p + 60) % 360),
        oklch_to_hex(base_L, base_C, (H_p + 200) % 360),
        oklch_to_hex(base_L, base_C, (H_p + 280) % 360),
        oklch_to_hex(max(0.40, base_L - 0.18), base_C, (H_p + 20) % 360),
        oklch_to_hex(min(0.85, base_L + 0.15), max(0.08, base_C - 0.05), (H_p + 120) % 360),
    ]

    return Palette(
        primary=primary,
        secondary=secondary,
        accent=accent,
        background=background,
        surface=surface,
        text_primary=text_primary,
        text_secondary=text_secondary,
        text_muted=text_muted,
        success="#10b981",
        warning="#f59e0b",
        danger="#ef4444",
        chart=chart,
    )


def _validate_hex(s: Optional[str]) -> Optional[str]:
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if not s.startswith("#"):
        s = "#" + s
    try:
        hex_to_oklch(s)
        return s
    except Exception:
        return None


def resolve_design_tokens(
    *,
    design_profile: Optional[dict[str, Any]] = None,
    purpose: Optional[str] = None,
    industry: Optional[str] = None,
    variation_seed: Optional[str] = None,
) -> ResolvedDesignTokens:
    """
    Produce a complete token set from an optional `design_profile` dict.

    `design_profile` shape (all fields optional — must handle partial input):
        {
            "user_provided": bool,
            "theme_id": str | None,
            "brand": {
                "primary_color": "#...",
                "secondary_color": "#...",
                "accent_color": "#...",
                "background_color": "#...",
                "font_heading": "Inter",
                "font_body": "Inter",
                "font_size_scale": "compact|comfortable|spacious",
                "heading_weight": 700,
                "body_weight": 400,
                "line_height_scale": 1.4,
                "letter_spacing_em": 0.0,
                "logo_url": "...",
                "brand_guidelines_text": "...",
            }
        }
    """
    dp = design_profile or {}
    user_provided = bool(dp.get("user_provided"))
    brand = dp.get("brand") or {}

    # ── Palette ────────────────────────────────────────────────────
    user_primary = _validate_hex(brand.get("primary_color"))
    user_accent = _validate_hex(brand.get("accent_color"))
    user_bg = _validate_hex(brand.get("background_color"))

    if user_primary is None:
        bucket = _pick_industry_bucket(industry)
        user_primary = _INDUSTRY_PALETTES[bucket]["primary"]
        # Accent tracks bucket only if user didn't provide either primary or accent
        if user_accent is None:
            user_accent = _INDUSTRY_PALETTES[bucket]["accent"]

    if not user_provided and variation_seed:
        hue_shift, light_shift = _variation_offsets(variation_seed)
        user_primary = _adjust(user_primary, dH=hue_shift, dL=light_shift)
        if user_accent is not None:
            user_accent = _adjust(user_accent, dH=-hue_shift / 2.0, dL=-light_shift / 2.0)

    palette = _derive_palette(primary=user_primary, accent=user_accent, background=user_bg)

    # If the user provided a secondary explicitly, override the derived one.
    user_secondary = _validate_hex(brand.get("secondary_color"))
    if user_secondary:
        palette.secondary = user_secondary

    # ── Fonts ──────────────────────────────────────────────────────
    purpose_key = (purpose or "default").lower()
    defaults = _PURPOSE_FONT_PAIRS.get(purpose_key, _PURPOSE_FONT_PAIRS["default"])
    user_heading = (brand.get("font_heading") or "").strip() or None
    user_body = (brand.get("font_body") or "").strip() or None

    if user_heading and not user_body:
        user_body = _FONT_SIBLINGS.get(user_heading, user_heading)
    if user_body and not user_heading:
        user_heading = _FONT_SIBLINGS.get(user_body, user_body)

    fonts = Fonts(
        heading=user_heading or defaults["heading"],
        body=user_body or defaults["body"],
    )

    # ── Density & scale ────────────────────────────────────────────
    density = (brand.get("font_size_scale") or "comfortable").lower()
    if density not in _TYPE_SCALES:
        density = "comfortable"
    scale = _TYPE_SCALES[density]
    spacing = _DENSITY_SPACING[density]

    # ── Weights ────────────────────────────────────────────────────
    def _clamp_weight(v: Any, default: int, lo: int = 100, hi: int = 900) -> int:
        try:
            n = int(v)
            return max(lo, min(hi, n))
        except (TypeError, ValueError):
            return default

    weights = Weights(
        heading=_clamp_weight(brand.get("heading_weight"), 700),
        body=_clamp_weight(brand.get("body_weight"), 400),
    )

    # ── Line height & letter spacing ───────────────────────────────
    try:
        lh = float(brand.get("line_height_scale", 1.4))
        lh = max(1.0, min(2.5, lh))
    except (TypeError, ValueError):
        lh = 1.4
    try:
        ls = float(brand.get("letter_spacing_em", 0.0))
        ls = max(-0.1, min(0.3, ls))
    except (TypeError, ValueError):
        ls = 0.0

    # ── Provenance tag ─────────────────────────────────────────────
    if not user_provided:
        provided_by = "auto"
    else:
        # Count how many fields the user actually set
        user_fields = [
            user_primary if brand.get("primary_color") else None,
            user_accent if brand.get("accent_color") else None,
            user_bg,
            user_heading if brand.get("font_heading") else None,
            user_body if brand.get("font_body") else None,
            brand.get("font_size_scale"),
            brand.get("heading_weight"),
            brand.get("body_weight"),
            brand.get("line_height_scale"),
            brand.get("letter_spacing_em"),
        ]
        filled = sum(1 for f in user_fields if f is not None)
        provided_by = "user" if filled >= 7 else "hybrid"

    tokens = ResolvedDesignTokens(
        palette=palette,
        fonts=fonts,
        scale=scale,
        spacing=spacing,
        weights=weights,
        density=density,
        line_height=lh,
        letter_spacing_em=ls,
        provided_by=provided_by,
    )

    logger.info(
        "design_tokens_resolved",
        provided_by=provided_by,
        density=density,
        primary=palette.primary,
        accent=palette.accent,
        heading_font=fonts.heading,
        body_font=fonts.body,
    )
    return tokens


def _variation_offsets(seed: str) -> tuple[float, float]:
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    hue_bucket = int(digest[:2], 16) / 255.0
    light_bucket = int(digest[2:4], 16) / 255.0
    hue_shift = (hue_bucket - 0.5) * 28.0
    light_shift = (light_bucket - 0.5) * 0.05
    return hue_shift, light_shift
