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
from app.services.v4.uiux_advisor import recommend_design

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
    surface_alt: str
    text_primary: str
    text_secondary: str
    text_muted: str
    border: str
    gradient_start: str
    gradient_end: str
    success: str
    warning: str
    danger: str
    chart: list[str] = field(default_factory=list)


@dataclass
class Fonts:
    heading: str
    body: str
    display: str = ""
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
class ShapeTokens:
    """Shape / surface tokens for premium visual effects."""
    radius_sm: str = "2px"
    radius_md: str = "6px"
    radius_lg: str = "12px"
    radius_xl: str = "24px"
    shadow_sm: str = "0 1px 2px rgba(0,0,0,0.06)"
    shadow_md: str = "0 4px 12px rgba(0,0,0,0.08)"
    shadow_lg: str = "0 12px 40px rgba(0,0,0,0.12)"
    shadow_glow: str = "0 0 40px rgba(0,0,0,0.15)"
    border_width: str = "1px"
    border_subtle: str = "color-mix(in oklab, var(--st-on-surface) 8%, transparent)"
    glass_blur: str = "blur(20px) saturate(180%)"


@dataclass
class AnimationTokens:
    """Motion / transition tokens for kinetic design."""
    entry_duration_ms: int = 600
    stagger_ms: int = 80
    hover_scale: float = 1.02
    hover_duration_ms: int = 300
    easing: str = "cubic-bezier(0.22, 1, 0.36, 1)"
    page_transition_ms: int = 400
    micro_duration_ms: int = 150

    # Phase 4: Named transition archetypes consumed by PresentMode.tsx
    ARCHETYPES: dict[str, dict[str, Any]] = field(default_factory=lambda: {
        "fade-cross": {
            "duration_ms": 300,
            "easing": "ease-in-out",
            "stagger_ms": 0,
            "description": "Quick cross-fade for data-heavy slides",
        },
        "editorial-reveal": {
            "duration_ms": 800,
            "easing": "cubic-bezier(0.22, 1, 0.36, 1)",
            "stagger_ms": 120,
            "description": "Dramatic staggered reveal for narrative slides",
        },
        "kinetic-stagger": {
            "duration_ms": 500,
            "easing": "cubic-bezier(0.34, 1.56, 0.64, 1)",
            "stagger_ms": 60,
            "description": "Playful spring-stagger for product/feature slides",
        },
        "count-up": {
            "duration_ms": 1200,
            "easing": "cubic-bezier(0.22, 1, 0.36, 1)",
            "stagger_ms": 0,
            "description": "Slow emphasis for stat/number slides",
        },
    })

    def resolve_archetype(self, name: str) -> dict[str, Any]:
        """Return animation config for a named archetype, or default."""
        return self.ARCHETYPES.get(name, self.ARCHETYPES["fade-cross"])


@dataclass
class GridTokens:
    """Layout grid tokens for composition intelligence."""
    columns: int = 12
    gutter_px: int = 24
    baseline_px: int = 8
    max_content_width: str = "1200px"
    slide_margin_px: int = 64
    safe_area_inset: int = 48


@dataclass
class ResolvedDesignTokens:
    palette: Palette
    fonts: Fonts
    scale: TypeScale
    spacing: Spacing
    weights: Weights
    shape: ShapeTokens = field(default_factory=ShapeTokens)
    animation: AnimationTokens = field(default_factory=AnimationTokens)
    grid: GridTokens = field(default_factory=GridTokens)
    density: str = "comfortable"                 # compact | comfortable | spacious
    line_height: float = 1.4
    letter_spacing_em: float = 0.0
    provided_by: str = "auto"                    # user | auto | hybrid
    visual_direction: str = ""                   # selected motion/layout system
    catalog_recommendation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "palette": asdict(self.palette),
            "fonts": asdict(self.fonts),
            "scale": asdict(self.scale),
            "spacing": asdict(self.spacing),
            "weights": asdict(self.weights),
            "shape": asdict(self.shape),
            "animation": asdict(self.animation),
            "grid": asdict(self.grid),
            "density": self.density,
            "line_height": self.line_height,
            "letter_spacing_em": self.letter_spacing_em,
            "provided_by": self.provided_by,
            "visual_direction": self.visual_direction,
            "catalog_recommendation": self.catalog_recommendation,
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
# VISUAL DIRECTIONS (inspired by Open Design / huashu-design)
# ═══════════════════════════════════════════════════════════════════
# 5 deterministic visual directions the user can pick from.
# Each is a fully-specified design spec: palette in OKLCH-derived hex,
# font stack, layout posture cues. One click → complete visual system.
# No improvisation, no AI-slop.

@dataclass
class VisualDirection:
    id: str
    name: str
    description: str
    primary: str
    accent: str
    background: str
    heading_font: str
    body_font: str
    density: str
    motion_style: str       # minimal | editorial | kinetic
    layout_posture: str     # structured | editorial | swiss | expressive
    anti_patterns: list[str] = field(default_factory=list)


VISUAL_DIRECTIONS: dict[str, VisualDirection] = {
    "minimal_dark": VisualDirection(
        id="minimal_dark",
        name="Minimal Dark",
        description="Clean dark surface, muted palette, maximum whitespace. "
                    "Lets content breathe. Best for: investor decks, product launches.",
        primary="#3b82f6",
        accent="#a78bfa",
        background="#09090b",
        heading_font="Inter",
        body_font="Inter",
        density="comfortable",
        motion_style="minimal",
        layout_posture="structured",
        anti_patterns=["gradients on text", "rounded cards with shadows",
                       "more than 2 colors per slide", "decorative illustrations"],
    ),
    "swiss_editorial": VisualDirection(
        id="swiss_editorial",
        name="Swiss Editorial",
        description="Grid-locked, hairline rules, strong type hierarchy. "
                    "Massimo Vignelli school. Best for: keynotes, conference talks.",
        primary="#0f172a",
        accent="#dc2626",
        background="#ffffff",
        heading_font="Space Grotesk",
        body_font="Inter",
        density="spacious",
        motion_style="editorial",
        layout_posture="swiss",
        anti_patterns=["shadows", "rounded corners > 4px", "gradients",
                       "more than 3 font weights", "centered body text"],
    ),
    "warm_narrative": VisualDirection(
        id="warm_narrative",
        name="Warm Narrative",
        description="Earthy tones, serif headings, generous margins. "
                    "Story-forward. Best for: impact reports, brand stories.",
        primary="#92400e",
        accent="#065f46",
        background="#fffbeb",
        heading_font="Lora",
        body_font="Source Serif 4",
        density="spacious",
        motion_style="editorial",
        layout_posture="editorial",
        anti_patterns=["neon colors", "tech gradients", "monospace body text",
                       "more than 4 bullets per slide"],
    ),
    "bold_contrast": VisualDirection(
        id="bold_contrast",
        name="Bold Contrast",
        description="High-contrast dark with vivid accent punches. "
                    "Demands attention. Best for: demo day, startup pitches.",
        primary="#7c3aed",
        accent="#22d3ee",
        background="#020617",
        heading_font="Manrope",
        body_font="Inter",
        density="compact",
        motion_style="kinetic",
        layout_posture="expressive",
        anti_patterns=["pastel colors", "thin font weights < 400",
                       "small type < 14pt", "busy backgrounds behind text"],
    ),
    "light_professional": VisualDirection(
        id="light_professional",
        name="Light Professional",
        description="Clean white surface, navy primary, restrained accents. "
                    "Corporate-ready. Best for: board decks, sales presentations.",
        primary="#1e3a5f",
        accent="#0ea5e9",
        background="#ffffff",
        heading_font="Plus Jakarta Sans",
        body_font="Inter",
        density="comfortable",
        motion_style="minimal",
        layout_posture="structured",
        anti_patterns=["dark backgrounds", "playful illustrations",
                       "emoji in headings", "decorative borders"],
    ),
    "cinematic_dark": VisualDirection(
        id="cinematic_dark",
        name="Cinematic Dark",
        description="Deep obsidian with warm amber accent. Film-grade contrast. "
                    "Best for: creative pitches, storytelling, cinematic reveals.",
        primary="#0a0a0f",
        accent="#ff6b35",
        background="#050508",
        heading_font="Cinzel",
        body_font="Inter",
        density="spacious",
        motion_style="editorial",
        layout_posture="expressive",
        anti_patterns=["bright backgrounds", "pastel tones", "thin fonts",
                       "cluttered layouts", "generic stock photos"],
    ),
    "luxury_gold": VisualDirection(
        id="luxury_gold",
        name="Luxury Gold",
        description="Rich dark surface with antique gold accent. Premium heritage feel. "
                    "Best for: luxury brands, hospitality, high-end consulting.",
        primary="#1a1a1a",
        accent="#c9a227",
        background="#0f0f0f",
        heading_font="Playfair Display",
        body_font="Source Sans 3",
        density="spacious",
        motion_style="editorial",
        layout_posture="editorial",
        anti_patterns=["neon colors", "comic sans", "gradients on text",
                       "emoji", "crowded layouts"],
    ),
    "neon_futurism": VisualDirection(
        id="neon_futurism",
        name="Neon Futurism",
        description="Cyber-dark with electric cyan and magenta accents. High-tech edge. "
                    "Best for: AI/ML demos, gaming, devtools, sci-fi concepts.",
        primary="#050505",
        accent="#00f0ff",
        background="#020202",
        heading_font="Orbitron",
        body_font="JetBrains Mono",
        density="compact",
        motion_style="kinetic",
        layout_posture="expressive",
        anti_patterns=["earth tones", "serif fonts", "rounded cards",
                       "pastel colors", "organic shapes"],
    ),
    "pastel_soft": VisualDirection(
        id="pastel_soft",
        name="Pastel Soft",
        description="Warm cream with dusty rose accent. Gentle, approachable, feminine. "
                    "Best for: wellness, lifestyle, education, community.",
        primary="#faf8f5",
        accent="#e8b4b8",
        background="#faf8f5",
        heading_font="DM Sans",
        body_font="DM Sans",
        density="comfortable",
        motion_style="minimal",
        layout_posture="structured",
        anti_patterns=["dark backgrounds", "neon colors", "sharp corners",
                       "aggressive fonts", "high contrast"],
    ),
    "earth_organic": VisualDirection(
        id="earth_organic",
        name="Earth Organic",
        description="Natural parchment with forest green accent. Grounded and authentic. "
                    "Best for: sustainability, agriculture, wellness, non-profits.",
        primary="#f5f0e8",
        accent="#6b8e5a",
        background="#f5f0e8",
        heading_font="Lora",
        body_font="Source Serif 4",
        density="spacious",
        motion_style="editorial",
        layout_posture="editorial",
        anti_patterns=["neon colors", "tech gradients", "monospace body",
                       "plastic-looking icons", "artificial colors"],
    ),
    "midnight_navy": VisualDirection(
        id="midnight_navy",
        name="Midnight Navy",
        description="Deep navy with ice-blue accent. Authoritative yet modern. "
                    "Best for: finance, legal, enterprise, government, consulting.",
        primary="#0f172a",
        accent="#38bdf8",
        background="#0b1120",
        heading_font="Space Grotesk",
        body_font="Inter",
        density="comfortable",
        motion_style="minimal",
        layout_posture="structured",
        anti_patterns=["bright backgrounds", "warm colors", "playful fonts",
                       "emoji", "gradients"],
    ),
    "secure_edge": VisualDirection(
        id="secure_edge",
        name="Secure Edge",
        description="Obsidian security-console surface with cyan signal and amber diligence accents. "
                    "Best for: cybersecurity, edge infrastructure, technical investor pitches.",
        primary="#06b6d4",
        accent="#f59e0b",
        background="#05070d",
        heading_font="Space Grotesk",
        body_font="Inter",
        density="compact",
        motion_style="minimal",
        layout_posture="structured",
        anti_patterns=["purple gradients", "stock cyber imagery", "low-contrast slate palettes",
                       "decorative bokeh", "unbounded neon"],
    ),
    "coral_energy": VisualDirection(
        id="coral_energy",
        name="Coral Energy",
        description="Warm cream with vibrant coral punch. Youthful and energetic. "
                    "Best for: startups, consumer apps, fitness, social platforms.",
        primary="#fff5f0",
        accent="#ff6b6b",
        background="#fff5f0",
        heading_font="Manrope",
        body_font="Inter",
        density="comfortable",
        motion_style="kinetic",
        layout_posture="expressive",
        anti_patterns=["dark backgrounds", "muted tones", "serif headings",
                       "slow animations", "boring layouts"],
    ),
    "sage_calm": VisualDirection(
        id="sage_calm",
        name="Sage Calm",
        description="Soft white with muted sage accent. Minimal and tranquil. "
                    "Best for: healthcare, meditation, spa, mental health.",
        primary="#f8faf8",
        accent="#87a878",
        background="#f8faf8",
        heading_font="Plus Jakarta Sans",
        body_font="Inter",
        density="spacious",
        motion_style="minimal",
        layout_posture="structured",
        anti_patterns=["dark backgrounds", "bright neon", "aggressive fonts",
                       "cluttered layouts", "high contrast"],
    ),
    "berry_creative": VisualDirection(
        id="berry_creative",
        name="Berry Creative",
        description="Soft blush with deep berry accent. Artistic and bold. "
                    "Best for: design agencies, portfolios, fashion, creative arts.",
        primary="#faf5f8",
        accent="#c44569",
        background="#faf5f8",
        heading_font="Work Sans",
        body_font="Work Sans",
        density="comfortable",
        motion_style="editorial",
        layout_posture="swiss",
        anti_patterns=["generic stock photos", "boring layouts", "default fonts",
                       "cluttered slides", "low contrast"],
    ),
    "obsidian_tech": VisualDirection(
        id="obsidian_tech",
        name="Obsidian Tech",
        description="Near-black with mint-green accent. Developer-first aesthetic. "
                    "Best for: devtools, infrastructure, API docs, technical deep-dives.",
        primary="#0c0c0c",
        accent="#00d4aa",
        background="#080808",
        heading_font="IBM Plex Sans",
        body_font="IBM Plex Mono",
        density="compact",
        motion_style="minimal",
        layout_posture="structured",
        anti_patterns=["bright backgrounds", "serif fonts", "rounded cards",
                       "gradients", "decorative illustrations"],
    ),
    "premium_brand_house": VisualDirection(
        id="premium_brand_house",
        name="Premium Brand House",
        description="Founder-grade brand system with rich dark canvas, gold accents, and executive spacing. "
                    "Best for: premium fundraising, company story, team credibility, and brand-led investor decks.",
        primary="#111827",
        accent="#d8b456",
        background="#07070a",
        heading_font="Playfair Display",
        body_font="DM Sans",
        density="spacious",
        motion_style="editorial",
        layout_posture="editorial",
        anti_patterns=["flat black templates", "generic logo placement", "crowded cards",
                       "unsupported decorative widgets", "unbranded image choices"],
    ),
    "premium_data_room": VisualDirection(
        id="premium_data_room",
        name="Premium Data Room",
        description="Dense but readable diligence system for charts, tables, claim traceability, risks, and proof. "
                    "Best for: technical investors, underwriters, enterprise buying committees.",
        primary="#1d4ed8",
        accent="#22d3ee",
        background="#06111f",
        heading_font="IBM Plex Sans",
        body_font="Inter",
        density="compact",
        motion_style="minimal",
        layout_posture="structured",
        anti_patterns=["empty benchmark slides", "unsourced market claims", "decorative charts",
                       "low-contrast table text", "placeholder metrics"],
    ),
    "premium_cinematic_fundraise": VisualDirection(
        id="premium_cinematic_fundraise",
        name="Premium Cinematic Fundraise",
        description="Image-led executive storytelling with dramatic reveals, restrained type, and branded chapter moments. "
                    "Best for: premium keynote pitches, product vision, and category creation narratives.",
        primary="#f8fafc",
        accent="#ff7a3d",
        background="#08090d",
        heading_font="Cinzel",
        body_font="Inter",
        density="spacious",
        motion_style="kinetic",
        layout_posture="expressive",
        anti_patterns=["random stock imagery", "busy photo overlays", "tiny text over images",
                       "uncontrolled gradients", "generic AI hero frames"],
    ),
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


def _calculate_contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """Calculate WCAG contrast ratio between foreground and background colors.
    
    Returns contrast ratio from 1:1 to 21:1.
    """
    # Convert hex to relative luminance
    def _relative_luminance(hex_color: str) -> float:
        r, g, b = _hex_to_rgb(hex_color)
        
        # Normalize to 0-1 range
        r, g, b = r / 255, g / 255, b / 255
        
        # Apply sRGB gamma correction
        def _channel(c: float) -> float:
            if c <= 0.03928:
                return c / 12.92
            else:
                return ((c + 0.055) / 1.055) ** 2.4
        
        r, g, b = _channel(r), _channel(g), _channel(b)
        
        # Calculate luminance
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    L1 = _relative_luminance(fg_hex)
    L2 = _relative_luminance(bg_hex)
    
    # Ensure L1 is the lighter color
    if L1 < L2:
        L1, L2 = L2, L1
    
    # WCAG contrast ratio formula
    return (L1 + 0.05) / (L2 + 0.05)


def _adjust_for_wcaa_contrast(fg_hex: str, bg_hex: str, target_ratio: float = 4.5) -> str:
    """Adjust foreground color to meet WCAG AA contrast ratio.
    
    Returns adjusted hex color that meets or exceeds target_ratio.
    """
    current_ratio = _calculate_contrast_ratio(fg_hex, bg_hex)
    
    if current_ratio >= target_ratio:
        return fg_hex  # Already compliant
    
    fg_L, fg_C, fg_H = hex_to_oklch(fg_hex)
    bg_L, _, _ = hex_to_oklch(bg_hex)

    # Walk luminance toward the accessible side while preserving hue/chroma.
    # A single adjustment is not enough for near-white-on-white surface cards.
    direction = 1 if fg_L > bg_L else -1
    best = fg_hex
    for step in range(1, 16):
        next_L = max(0.02, min(0.98, fg_L + direction * step * 0.055))
        candidate = oklch_to_hex(next_L, fg_C, fg_H)
        if _calculate_contrast_ratio(candidate, bg_hex) >= target_ratio:
            return candidate
        best = candidate

    # Absolute fallback: choose the readable neutral. This should be rare,
    # but it prevents invisible text when a palette is extreme.
    black_ratio = _calculate_contrast_ratio("#0b0d12", bg_hex)
    white_ratio = _calculate_contrast_ratio("#f8fafc", bg_hex)
    neutral = "#0b0d12" if black_ratio >= white_ratio else "#f8fafc"
    return neutral if max(black_ratio, white_ratio) >= target_ratio else best


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
    surface_alt = _adjust(background, dL=0.08 if is_dark_theme else -0.08)

    # Text roles: high contrast to background
    text_primary = "#f8fafc" if is_dark_theme else "#0b0d12"
    text_secondary = _adjust(text_primary, dL=-0.15 if is_dark_theme else 0.20)
    text_muted = _adjust(text_primary, dL=-0.28 if is_dark_theme else 0.40)

    # Secondary brand: primary shifted 30° for UI accents
    secondary = _adjust(primary, dH=30.0, dL=-0.05)

    # Border: subtle mix of text and background
    border = _adjust(text_primary, dL=0.55 if is_dark_theme else 0.35)

    # Gradient: brand axis from primary to accent, harmonised
    gradient_start = primary
    gradient_end = _adjust(accent, dH=-15.0, dL=0.05)

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

    # WCAG AA contrast enforcement: ensure text colors meet 4.5:1 on both
    # the slide canvas and raised content surfaces. The second pass prevents
    # light-theme timeline/diagram/table cards from inheriting text that is
    # technically valid on the canvas but invisible inside a surface panel.
    text_primary = _adjust_for_wcaa_contrast(text_primary, background, target_ratio=4.5)
    text_secondary = _adjust_for_wcaa_contrast(text_secondary, background, target_ratio=4.5)
    text_muted = _adjust_for_wcaa_contrast(text_muted, background, target_ratio=4.5)
    text_primary = _adjust_for_wcaa_contrast(text_primary, surface, target_ratio=4.5)
    text_secondary = _adjust_for_wcaa_contrast(text_secondary, surface, target_ratio=4.5)
    text_muted = _adjust_for_wcaa_contrast(text_muted, surface, target_ratio=4.5)
    text_primary = _adjust_for_wcaa_contrast(text_primary, surface_alt, target_ratio=4.5)
    text_secondary = _adjust_for_wcaa_contrast(text_secondary, surface_alt, target_ratio=4.5)
    text_muted = _adjust_for_wcaa_contrast(text_muted, surface_alt, target_ratio=4.5)
    
    # Log contrast ratios for debugging
    logger.info(
        "wcag_contrast_check",
        primary_bg_ratio=_calculate_contrast_ratio(text_primary, background),
        secondary_bg_ratio=_calculate_contrast_ratio(text_secondary, background),
        muted_bg_ratio=_calculate_contrast_ratio(text_muted, background),
        primary_surface_ratio=_calculate_contrast_ratio(text_primary, surface),
        secondary_surface_ratio=_calculate_contrast_ratio(text_secondary, surface),
        muted_surface_ratio=_calculate_contrast_ratio(text_muted, surface),
    )

    return Palette(
        primary=primary,
        secondary=secondary,
        accent=accent,
        background=background,
        surface=surface,
        surface_alt=surface_alt,
        text_primary=text_primary,
        text_secondary=text_secondary,
        text_muted=text_muted,
        border=border,
        gradient_start=gradient_start,
        gradient_end=gradient_end,
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


def _apply_brand_overrides_to_tokens(
    tokens: ResolvedDesignTokens,
    brand: Optional[dict[str, Any]],
) -> ResolvedDesignTokens:
    """Overlay explicit user brand controls on resolved theme tokens.

    Theme/template selection should set the professional baseline, while
    manually chosen colors and typography still need to win when present.
    """
    if not isinstance(brand, dict) or not brand:
        return tokens

    primary = _validate_hex(brand.get("primary_color"))
    accent = _validate_hex(brand.get("accent_color"))
    background = _validate_hex(brand.get("background_color"))
    secondary = _validate_hex(brand.get("secondary_color"))

    if primary or accent or background:
        tokens.palette = _derive_palette(
            primary=primary or tokens.palette.primary,
            accent=accent or tokens.palette.accent,
            background=background or tokens.palette.background,
        )
    if secondary:
        tokens.palette.secondary = secondary

    heading = str(brand.get("font_heading") or "").strip()
    body = str(brand.get("font_body") or "").strip()
    if heading:
        tokens.fonts.heading = heading
        tokens.fonts.display = heading
    if body:
        tokens.fonts.body = body

    density = str(brand.get("font_size_scale") or "").strip().lower()
    if density in _TYPE_SCALES:
        tokens.density = density
        tokens.scale = _TYPE_SCALES[density]
        tokens.spacing = _DENSITY_SPACING[density]

    def _clamp_weight(v: Any, current: int) -> int:
        try:
            return max(100, min(900, int(v)))
        except (TypeError, ValueError):
            return current

    tokens.weights.heading = _clamp_weight(brand.get("heading_weight"), tokens.weights.heading)
    tokens.weights.body = _clamp_weight(brand.get("body_weight"), tokens.weights.body)

    try:
        line_height = float(brand.get("line_height_scale"))
        if 1.0 <= line_height <= 2.0:
            tokens.line_height = line_height
    except (TypeError, ValueError):
        pass

    try:
        letter_spacing = float(brand.get("letter_spacing_em"))
        if -0.05 <= letter_spacing <= 0.12:
            tokens.letter_spacing_em = letter_spacing
    except (TypeError, ValueError):
        pass

    tokens.provided_by = "hybrid" if tokens.provided_by == "auto" else tokens.provided_by
    return tokens


def _apply_visual_direction_to_tokens(
    tokens: ResolvedDesignTokens,
    direction_id: Optional[str],
) -> ResolvedDesignTokens:
    """Apply the selected visual system without discarding theme/brand colors.

    Users select a theme for palette and a visual direction for behavior. Earlier
    theme-first resolution returned before direction tokens could affect motion,
    density, grid, and component posture, which made distinct choices render the
    same. Preserve the palette while adopting the selected system's structure.
    """
    if not direction_id:
        return tokens
    direction_key = str(direction_id).strip()
    if not direction_key:
        return tokens
    if direction_key not in VISUAL_DIRECTIONS:
        logger.warning("unknown_visual_direction_overlay", direction_id=direction_key)
        return tokens

    direction_tokens = resolve_from_direction(direction_key, provided_by="user")
    tokens.fonts = direction_tokens.fonts
    tokens.scale = direction_tokens.scale
    tokens.spacing = direction_tokens.spacing
    tokens.weights = direction_tokens.weights
    tokens.shape = direction_tokens.shape
    tokens.animation = direction_tokens.animation
    tokens.grid = direction_tokens.grid
    tokens.density = direction_tokens.density
    tokens.line_height = direction_tokens.line_height
    tokens.letter_spacing_em = direction_tokens.letter_spacing_em
    tokens.provided_by = "hybrid"
    tokens.visual_direction = direction_tokens.visual_direction
    return tokens


def resolve_design_tokens(
    *,
    design_profile: Optional[dict[str, Any]] = None,
    purpose: Optional[str] = None,
    industry: Optional[str] = None,
    variation_seed: Optional[str] = None,
    mode: Optional[str] = None,
) -> ResolvedDesignTokens:
    """
    Produce a complete token set from an optional `design_profile` dict.

    `design_profile` shape (all fields optional — must handle partial input):
        {
            "user_provided": bool,
            "theme_id": str | None,
            "visual_direction": str | None,  # one of VISUAL_DIRECTIONS keys
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
    brand = dp.get("brand") or {}
    direction_id = dp.get("visual_direction")

    # Fast path 1: explicit theme selection wins for palette, while an
    # explicit visual direction still controls motion/layout/typographic feel.
    theme_id = dp.get("theme_id")
    if theme_id:
        from app.services.v4.theme_engine import resolve_theme
        theme_dict = resolve_theme(theme_id)
        if theme_dict:
            logger.info(
                "design_tokens_from_theme",
                theme_id=theme_id,
                visual_direction=direction_id,
            )
            tokens = _resolve_from_theme_dict(theme_dict)
            tokens = _apply_visual_direction_to_tokens(tokens, direction_id)
            return _apply_brand_overrides_to_tokens(tokens, brand)

    # Fast path 2: a selected template contributes its preferred theme only
    # when no explicit theme was selected. Template IDs are not theme IDs.
    template_id = dp.get("template_id")
    if template_id:
        from app.services.v4.template_engine import TemplateEngine
        from app.services.v4.theme_engine import resolve_theme

        template = TemplateEngine().get(str(template_id))
        if template:
            candidates = [
                template.thumbnail_theme,
                *(template.compatible_themes or []),
            ]
            seen: set[str] = set()
            for candidate_theme_id in candidates:
                if not candidate_theme_id or candidate_theme_id in seen:
                    continue
                seen.add(candidate_theme_id)
                theme_dict = resolve_theme(candidate_theme_id)
                if theme_dict:
                    logger.info(
                        "design_tokens_from_template_theme",
                        template_id=template_id,
                        theme_id=candidate_theme_id,
                        visual_direction=direction_id,
                    )
                    tokens = _resolve_from_theme_dict(theme_dict)
                    tokens = _apply_visual_direction_to_tokens(tokens, direction_id)
                    return _apply_brand_overrides_to_tokens(tokens, brand)

    user_provided = bool(dp.get("user_provided"))
    has_brand_overrides = bool(brand)

    # Slice 9: when the user has not supplied a brand, pick a complete
    # local ui-ux catalog recommendation. This keeps generation deterministic
    # while avoiding a single hardcoded fallback direction for generic briefs.
    if mode and not direction_id and not user_provided and not has_brand_overrides:
        return _resolve_from_catalog_recommendation(
            purpose=purpose,
            industry=industry,
            mode=mode,
            design_profile=dp,
            variation_seed=variation_seed,
        )

    # Fast path 2: if a visual direction is specified, use it directly.
    # Auto-pick a visual direction when nothing explicit is chosen — this
    # guarantees cohesive, modern defaults instead of flat industry palettes.
    if not direction_id and not (user_provided and has_brand_overrides):
        direction_id = _pick_default_direction(purpose, industry)
    if direction_id and direction_id in VISUAL_DIRECTIONS:
        logger.info("design_tokens_from_direction", direction_id=direction_id)
        # When user explicitly chose a visual_direction via frontend picker,
        # provided_by stays default ("user"). When we auto-picked, tag "auto".
        auto_picked = dp.get("visual_direction") is None
        return _apply_brand_overrides_to_tokens(
            resolve_from_direction(direction_id, provided_by="auto" if auto_picked else "user"),
            brand,
        )

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
        display=user_heading or defaults["heading"],
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

    # Build a synthetic VisualDirection for token derivation
    _tmp_vd = VisualDirection(
        id="auto", name="Auto", description="",
        primary=palette.primary, accent=palette.accent,
        background=palette.background,
        heading_font=fonts.heading, body_font=fonts.body,
        density=density, motion_style="minimal", layout_posture="structured",
    )

    tokens = ResolvedDesignTokens(
        palette=palette,
        fonts=fonts,
        scale=scale,
        spacing=spacing,
        weights=weights,
        shape=_shape_tokens_for_direction(_tmp_vd),
        animation=_animation_tokens_for_direction(_tmp_vd),
        grid=_grid_tokens_for_direction(_tmp_vd),
        density=density,
        line_height=lh,
        letter_spacing_em=ls,
        provided_by=provided_by,
        visual_direction=_tmp_vd.id,
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


def _resolve_from_catalog_recommendation(
    *,
    purpose: Optional[str],
    industry: Optional[str],
    mode: Optional[str],
    design_profile: dict[str, Any],
    variation_seed: Optional[str],
) -> ResolvedDesignTokens:
    """Resolve no-brand defaults from the local ui-ux catalog snapshot."""
    brand_brief = {
        "purpose": purpose or "",
        "tone": design_profile.get("tone") or "",
        "brand_brief": design_profile.get("brand_brief") or "",
        "visual_direction": design_profile.get("visual_direction") or "",
    }
    recommendation = recommend_design(
        industry=industry,
        audience=purpose,
        mode=mode,
        brand_brief=brand_brief,
    )
    rec = recommendation.to_dict()
    direction_id = _direction_from_catalog_style(
        recommendation.style_family,
        purpose=purpose,
        industry=industry,
    )
    tokens = resolve_from_direction(direction_id, provided_by="auto")
    palette = recommendation.palette
    primary = _validate_hex(palette.get("primary"))
    accent = _validate_hex(palette.get("accent"))
    background = _validate_hex(palette.get("background"))
    secondary = _validate_hex(palette.get("secondary"))
    text = _validate_hex(palette.get("text"))
    if variation_seed and primary:
        hue_shift, light_shift = _variation_offsets(variation_seed)
        primary = _adjust(primary, dH=hue_shift, dL=light_shift)
        if accent:
            accent = _adjust(accent, dH=-hue_shift / 2.0, dL=-light_shift / 2.0)
    if primary:
        tokens.palette = _derive_palette(primary=primary, accent=accent, background=background)
    if secondary:
        tokens.palette.secondary = secondary
    if text:
        tokens.palette.text_primary = text
        tokens.palette.text_secondary = _ensure_secondary_text(text, tokens.palette.background)
        tokens.palette.text_muted = _ensure_secondary_text(text, tokens.palette.surface)
    font = recommendation.font_pairing
    heading = str(font.get("heading") or "").strip()
    body = str(font.get("body") or "").strip()
    if heading and body:
        tokens.fonts = Fonts(heading=heading, body=body, display=heading)
    elif heading:
        tokens.fonts = Fonts(heading=heading, body=_FONT_SIBLINGS.get(heading, heading), display=heading)
    tokens.catalog_recommendation = {
        "style_family": {
            "id": recommendation.style_family.get("id"),
            "name": recommendation.style_family.get("name"),
            "mood": recommendation.style_family.get("mood"),
            "best_for": recommendation.style_family.get("best_for"),
        },
        "palette": {
            "id": recommendation.palette.get("id"),
            "product_type": recommendation.palette.get("product_type"),
            "primary": tokens.palette.primary,
            "secondary": tokens.palette.secondary,
            "accent": tokens.palette.accent,
            "background": tokens.palette.background,
            "text": tokens.palette.text_primary,
            "accessibility_class": recommendation.palette.get("accessibility_class"),
        },
        "font_pairing": {
            "id": recommendation.font_pairing.get("id"),
            "name": recommendation.font_pairing.get("name"),
            "heading": tokens.fonts.heading,
            "body": tokens.fonts.body,
            "mood": recommendation.font_pairing.get("mood"),
        },
        "rationale": rec.get("rationale") or [],
    }
    logger.info(
        "design_tokens_from_uiux_catalog",
        style_id=tokens.catalog_recommendation["style_family"].get("id"),
        palette_id=tokens.catalog_recommendation["palette"].get("id"),
        font_id=tokens.catalog_recommendation["font_pairing"].get("id"),
        visual_direction=tokens.visual_direction,
    )
    return tokens


def _direction_from_catalog_style(
    style_family: dict[str, Any],
    *,
    purpose: Optional[str],
    industry: Optional[str],
) -> str:
    style_text = " ".join(
        str(style_family.get(key) or "")
        for key in ("id", "name", "category", "mood", "best_for")
    ).lower()
    if any(term in style_text for term in ("swiss", "minimal", "grid", "documentation")):
        return "swiss_editorial"
    if any(term in style_text for term in ("editorial", "magazine", "serif")):
        return "warm_narrative"
    if any(term in style_text for term in ("glass", "corporate", "dashboard", "financial")):
        return "midnight_navy"
    if any(term in style_text for term in ("brutal", "block", "vibrant", "bold")):
        return "bold_contrast"
    if any(term in style_text for term in ("luxury", "premium", "gold")):
        return "luxury_gold"
    if any(term in style_text for term in ("organic", "wellness", "calm")):
        return "sage_calm"
    return _pick_default_direction(purpose, industry)


def _ensure_secondary_text(text: str, background: str) -> str:
    try:
        bg_l, _, _ = hex_to_oklch(background)
        text_l, _, _ = hex_to_oklch(text)
    except Exception:
        return text
    if abs(bg_l - text_l) < 0.45:
        return "#d6dbe8" if bg_l < 0.5 else "#3b414c"
    return text


def _pick_default_direction(purpose: Optional[str], industry: Optional[str]) -> str:
    """Choose a visual direction when the user didn't specify one.

    Maps purpose → direction first, then industry as fallback. When the
    purpose is the generic "pitch_deck" but industry is clearly bucketed,
    we let the industry refine the direction so different industries
    produce visually distinct decks instead of all collapsing into
    bold_contrast.
    """
    p = (purpose or "").lower()
    ind = (industry or "").lower()

    # Purpose-driven selection (strongest signal)
    if p == "pitch_deck" and any(token in ind for token in ("cyber", "security", "edge", "infrastructure")):
        return "secure_edge"
    # Pitch-deck refinements: ai-first decks lean dark+technical, fintech
    # leans midnight_navy (financial trust), healthcare leans warm narrative.
    # This keeps "pitch_deck + ai" visually distinct from "pitch_deck +
    # fintech" instead of stamping bold_contrast on both.
    if p == "pitch_deck" and ind in {"ai", "ml", "data", "saas", "devtool"}:
        return "minimal_dark"
    if p == "pitch_deck" and ind in {"fintech", "finance", "banking"}:
        return "midnight_navy"
    if p == "pitch_deck" and ind in {"healthcare", "biotech", "wellness"}:
        return "warm_narrative"
    if p == "pitch_deck" and ind in {"consumer", "retail", "media", "gaming"}:
        return "coral_energy"
    if p == "pitch_deck" and ind in {"creative", "design", "fashion", "arts"}:
        return "berry_creative"
    if p == "pitch_deck" and ind in {"luxury", "hospitality", "high_end"}:
        return "luxury_gold"
    if p == "pitch_deck":
        return "bold_contrast"
    if p in {"investor_pitch", "demo_day", "startup_pitch", "fundraising", "seed_round", "series_a"}:
        return "bold_contrast"
    if p in {"keynote", "conference", "talk", "workshop", "ted_talk"}:
        return "swiss_editorial"
    if p in {"report", "board_deck", "sales", "proposal", "quarterly", "annual_report"}:
        return "light_professional"
    if p in {"brand_story", "impact_report", "narrative", "storytelling", "case_study"}:
        return "warm_narrative"
    if p in {"product_launch", "demo", "reveal"}:
        return "cinematic_dark"
    if p in {"creative_pitch", "portfolio", "design_review"}:
        return "berry_creative"
    if p in {"technical_deep_dive", "api_docs", "developer_conference"}:
        return "obsidian_tech"
    if p in {"wellness", "meditation", "mental_health", "spa"}:
        return "sage_calm"

    # Industry-driven fallback
    if any(token in ind for token in ("cyber", "security", "edge")):
        return "secure_edge"
    if ind in {"fintech", "saas", "devtool", "ai", "ml", "data"}:
        return "minimal_dark"
    if ind in {"healthcare", "nonprofit", "education", "social", "wellness"}:
        return "warm_narrative"
    if ind in {"consulting", "enterprise", "b2b", "real_estate", "legal", "government"}:
        return "midnight_navy"
    if ind in {"consumer", "ecommerce", "retail", "media", "gaming", "fitness"}:
        return "coral_energy"
    if ind in {"luxury", "hospitality", "high_end", "heritage"}:
        return "luxury_gold"
    if ind in {"sustainability", "agriculture", "organic", "environment"}:
        return "earth_organic"
    if ind in {"creative", "design", "fashion", "arts", "agency"}:
        return "berry_creative"
    if ind in {"devtool", "infrastructure", "api", "developer"}:
        return "obsidian_tech"

    # Safe default
    return "light_professional"


# ═══════════════════════════════════════════════════════════════════
# VISUAL DIRECTION RESOLVER
# ═══════════════════════════════════════════════════════════════════

def _shape_tokens_for_direction(vd: VisualDirection) -> ShapeTokens:
    """Generate shape tokens based on visual direction posture."""
    posture = vd.layout_posture
    is_dark = vd.background and hex_to_oklch(vd.background)[0] < 0.45
    if posture == "swiss":
        return ShapeTokens(
            radius_sm="0px", radius_md="2px", radius_lg="4px", radius_xl="8px",
            shadow_sm="none", shadow_md="none", shadow_lg="none", shadow_glow="none",
            border_width="1px", border_subtle="rgba(0,0,0,0.12)" if not is_dark else "rgba(255,255,255,0.10)",
            glass_blur="none",
        )
    if posture == "expressive":
        return ShapeTokens(
            radius_sm="4px", radius_md="12px", radius_lg="24px", radius_xl="48px",
            shadow_sm="0 2px 8px rgba(0,0,0,0.10)", shadow_md="0 8px 24px rgba(0,0,0,0.14)",
            shadow_lg="0 24px 64px rgba(0,0,0,0.18)", shadow_glow=f"0 0 60px {vd.accent}33",
            border_width="1px", border_subtle=f"color-mix(in oklab, {vd.accent} 12%, transparent)",
            glass_blur="blur(24px) saturate(200%)",
        )
    if posture == "editorial":
        return ShapeTokens(
            radius_sm="2px", radius_md="6px", radius_lg="16px", radius_xl="32px",
            shadow_sm="0 1px 3px rgba(0,0,0,0.06)", shadow_md="0 4px 16px rgba(0,0,0,0.08)",
            shadow_lg="0 16px 48px rgba(0,0,0,0.10)", shadow_glow="none",
            border_width="1px", border_subtle="rgba(0,0,0,0.08)" if not is_dark else "rgba(255,255,255,0.08)",
            glass_blur="blur(16px) saturate(160%)",
        )
    # structured default
    return ShapeTokens(
        radius_sm="2px", radius_md="6px", radius_lg="12px", radius_xl="24px",
        shadow_sm="0 1px 2px rgba(0,0,0,0.06)", shadow_md="0 4px 12px rgba(0,0,0,0.08)",
        shadow_lg="0 12px 40px rgba(0,0,0,0.12)", shadow_glow=f"0 0 40px {vd.accent}22",
        border_width="1px", border_subtle="rgba(0,0,0,0.06)" if not is_dark else "rgba(255,255,255,0.06)",
        glass_blur="blur(20px) saturate(180%)",
    )


def _animation_tokens_for_direction(vd: VisualDirection) -> AnimationTokens:
    """Generate animation tokens based on motion style."""
    ms = vd.motion_style
    if ms == "kinetic":
        return AnimationTokens(
            entry_duration_ms=500, stagger_ms=60, hover_scale=1.03,
            hover_duration_ms=250, easing="cubic-bezier(0.34, 1.56, 0.64, 1)",
            page_transition_ms=350, micro_duration_ms=120,
        )
    if ms == "editorial":
        return AnimationTokens(
            entry_duration_ms=800, stagger_ms=120, hover_scale=1.01,
            hover_duration_ms=400, easing="cubic-bezier(0.22, 1, 0.36, 1)",
            page_transition_ms=500, micro_duration_ms=200,
        )
    # minimal default
    return AnimationTokens(
        entry_duration_ms=400, stagger_ms=80, hover_scale=1.01,
        hover_duration_ms=300, easing="cubic-bezier(0.22, 1, 0.36, 1)",
        page_transition_ms=300, micro_duration_ms=150,
    )


def _grid_tokens_for_direction(vd: VisualDirection) -> GridTokens:
    """Generate grid tokens based on density and posture."""
    density = vd.density
    posture = vd.layout_posture
    margin = 72 if density == "spacious" else 56 if density == "comfortable" else 40
    gutter = 32 if density == "spacious" else 24 if density == "comfortable" else 16
    safe = 56 if posture in ("swiss", "editorial") else 48
    return GridTokens(
        columns=12, gutter_px=gutter, baseline_px=8,
        max_content_width="1160px" if density == "compact" else "1240px",
        slide_margin_px=margin, safe_area_inset=safe,
    )


def resolve_from_direction(direction_id: str, provided_by: str = "user") -> ResolvedDesignTokens:
    """Resolve tokens from a named visual direction. One-click complete system."""
    vd = VISUAL_DIRECTIONS.get(direction_id)
    if vd is None:
        logger.warning("unknown_visual_direction", direction_id=direction_id)
        vd = VISUAL_DIRECTIONS["minimal_dark"]

    palette = _derive_palette(primary=vd.primary, accent=vd.accent, background=vd.background)
    density = vd.density
    scale = _TYPE_SCALES[density]
    spacing = _DENSITY_SPACING[density]

    return ResolvedDesignTokens(
        palette=palette,
        fonts=Fonts(heading=vd.heading_font, body=vd.body_font, display=vd.heading_font),
        scale=scale,
        spacing=spacing,
        weights=Weights(heading=700, body=400),
        shape=_shape_tokens_for_direction(vd),
        animation=_animation_tokens_for_direction(vd),
        grid=_grid_tokens_for_direction(vd),
        density=density,
        line_height=1.4,
        letter_spacing_em=0.0,
        provided_by=provided_by,
        visual_direction=vd.id,
    )


def _resolve_from_theme_dict(theme_dict: dict[str, Any]) -> ResolvedDesignTokens:
    """Resolve tokens from a ThemeEngine theme dict."""
    palette = _derive_palette(
        primary=theme_dict["primary"],
        accent=theme_dict["accent"],
        background=theme_dict["background"],
    )
    density = theme_dict.get("density", "comfortable")
    if density not in _TYPE_SCALES:
        density = "comfortable"
    scale = _TYPE_SCALES[density]
    spacing = _DENSITY_SPACING[density]
    posture = theme_dict.get("layout_posture", "structured")
    motion = theme_dict.get("motion_style", "minimal")
    vd = VisualDirection(
        id=str(theme_dict.get("id") or "theme"), name=theme_dict.get("name", "Theme"), description="",
        primary=theme_dict["primary"], accent=theme_dict["accent"],
        background=theme_dict["background"],
        heading_font=theme_dict["heading_font"], body_font=theme_dict["body_font"],
        density=density, motion_style=motion, layout_posture=posture,
    )

    return ResolvedDesignTokens(
        palette=palette,
        fonts=Fonts(heading=theme_dict["heading_font"], body=theme_dict["body_font"], display=theme_dict["heading_font"]),
        scale=scale,
        spacing=spacing,
        weights=Weights(heading=700, body=400),
        shape=_shape_tokens_for_direction(vd),
        animation=_animation_tokens_for_direction(vd),
        grid=_grid_tokens_for_direction(vd),
        density=density,
        line_height=1.4,
        letter_spacing_em=0.0,
        provided_by="user",
        visual_direction=vd.id,
    )


def get_visual_directions_list() -> list[dict[str, Any]]:
    """Return serializable list of all visual directions for frontend picker."""
    return [
        {
            "id": vd.id,
            "name": vd.name,
            "description": vd.description,
            "primary": vd.primary,
            "accent": vd.accent,
            "background": vd.background,
            "heading_font": vd.heading_font,
            "body_font": vd.body_font,
            "density": vd.density,
            "motion_style": vd.motion_style,
            "layout_posture": vd.layout_posture,
            "anti_patterns": vd.anti_patterns,
        }
        for vd in VISUAL_DIRECTIONS.values()
    ]
