"""
Design token resolver for Barise Server4 Elite - Fixes invisible nodes with surface_alt.

Guarantees surface_alt is always visibly lighter than surface using WCAG luminance.
"""

import colorsys
from typing import Any, Dict, Literal, Optional

from app.models.v4_elite import EliteDesignTokens, EliteFontTokens, ElitePaletteTokens, EliteTypeScale


# ============================================================================
# VISUAL DIRECTIONS DATABASE
# ============================================================================

VISUAL_DIRECTIONS: Dict[str, Dict[str, Any]] = {
    "minimal_dark": {
        "palette": {
            "primary": "#FFFFFF",
            "secondary": "#E5E5E7",
            "accent": "#00B4D8",
            "background": "#0F0F11",
            "surface": "#18181B",
            "surface_alt": "#27272A",
            "text_primary": "#FAFAFA",
            "text_secondary": "#D1D1D6",
            "text_muted": "#86868B",
            "border": "#424245",
            "gradient_start": "#FFFFFF",
            "gradient_end": "#00B4D8",
            "success": "#34C759",
            "warning": "#FF9500",
            "danger": "#FF3B30",
            "chart": "#00B4D8",
        },
        "fonts": {
            "heading": '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            "body": '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            "display": '"IBM Plex Sans", -apple-system, sans-serif',
            "mono": '"IBM Plex Mono", "Courier New", monospace',
        },
    },
    "cinematic_dark": {
        "palette": {
            "primary": "#D4A853",
            "secondary": "#B8956A",
            "accent": "#F77F00",
            "background": "#0A0A0E",
            "surface": "#12121A",
            "surface_alt": "#1E1E2E",
            "text_primary": "#F5F5F7",
            "text_secondary": "#E0E0E5",
            "text_muted": "#A0A0A8",
            "border": "#3A3A48",
            "gradient_start": "#D4A853",
            "gradient_end": "#F77F00",
            "success": "#06D6A0",
            "warning": "#FFB703",
            "danger": "#FB5607",
            "chart": "#D4A853",
        },
        "fonts": {
            "heading": '"Montserrat", -apple-system, BlinkMacSystemFont, sans-serif',
            "body": '"Open Sans", -apple-system, BlinkMacSystemFont, sans-serif',
            "display": '"Playfair Display", Georgia, serif',
            "mono": '"JetBrains Mono", "Courier New", monospace',
        },
    },
    "premium_brand_house": {
        "palette": {
            "primary": "#C9A96E",
            "secondary": "#8B7355",
            "accent": "#D4A574",
            "background": "#0F0F11",
            "surface": "#161618",
            "surface_alt": "#222224",
            "text_primary": "#F0F0F2",
            "text_secondary": "#D5D5D8",
            "text_muted": "#9E9EA3",
            "border": "#3D3D42",
            "gradient_start": "#C9A96E",
            "gradient_end": "#8B7355",
            "success": "#2ECC71",
            "warning": "#F39C12",
            "danger": "#E74C3C",
            "chart": "#C9A96E",
        },
        "fonts": {
            "heading": '"Poppins", -apple-system, BlinkMacSystemFont, sans-serif',
            "body": '"Lato", -apple-system, BlinkMacSystemFont, sans-serif',
            "display": '"Playfair Display", Georgia, serif',
            "mono": '"IBM Plex Mono", "Courier New", monospace',
        },
    },
    "light_professional": {
        "palette": {
            "primary": "#007AFF",
            "secondary": "#5AC8FA",
            "accent": "#FF2D55",
            "background": "#FFFFFF",
            "surface": "#F5F5F7",
            "surface_alt": "#FFFFFF",
            "text_primary": "#1D1D1F",
            "text_secondary": "#424245",
            "text_muted": "#86868B",
            "border": "#D2D2D7",
            "gradient_start": "#007AFF",
            "gradient_end": "#5AC8FA",
            "success": "#34C759",
            "warning": "#FF9500",
            "danger": "#FF3B30",
            "chart": "#007AFF",
        },
        "fonts": {
            "heading": '"Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif',
            "body": '"Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif',
            "display": '"Georgia", serif',
            "mono": '"Consolas", "Courier New", monospace',
        },
    },
    "swiss_editorial": {
        "palette": {
            "primary": "#000000",
            "secondary": "#333333",
            "accent": "#CC0000",
            "background": "#FFFFFF",
            "surface": "#FFFFFF",
            "surface_alt": "#F5F5F7",
            "text_primary": "#1A1A1A",
            "text_secondary": "#4A4A4A",
            "text_muted": "#999999",
            "border": "#CCCCCC",
            "gradient_start": "#000000",
            "gradient_end": "#333333",
            "success": "#008000",
            "warning": "#FF8C00",
            "danger": "#CC0000",
            "chart": "#000000",
        },
        "fonts": {
            "heading": '"Helvetica Neue", -apple-system, BlinkMacSystemFont, sans-serif',
            "body": '"Helvetica Neue", -apple-system, BlinkMacSystemFont, sans-serif',
            "display": '"Garamond", Georgia, serif',
            "mono": '"Monaco", "Courier New", monospace',
        },
    },
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple (0-1 range)."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def _rgb_to_hex(r: float, g: float, b: float) -> str:
    """Convert RGB (0-1 range) to hex color."""
    return "#{:02x}{:02x}{:02x}".format(
        int(round(r * 255)), int(round(g * 255)), int(round(b * 255))
    )


def _relative_luminance(hex_color: str) -> float:
    """
    Calculate relative luminance using WCAG formula.
    https://www.w3.org/TR/WCAG20/#relativeluminancedef
    """
    r, g, b = _hex_to_rgb(hex_color)

    def adjust(c: float) -> float:
        if c <= 0.03928:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4

    r = adjust(r)
    g = adjust(g)
    b = adjust(b)

    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _lighten_by_percentage(hex_color: str, percentage: float) -> str:
    """
    Lighten a color by increasing lightness by a percentage in HLS space.
    """
    r, g, b = _hex_to_rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    # Increase lightness by percentage (clamped to 1.0)
    l = min(1.0, l * (1.0 + percentage))

    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return _rgb_to_hex(r, g, b)


# ============================================================================
# CORE FUNCTIONS
# ============================================================================


def ensure_surface_alt(palette: Dict[str, str]) -> Dict[str, str]:
    """
    CRITICAL SAFETY CHECK: Ensure surface_alt is visibly lighter than surface.

    Uses WCAG relative luminance calculation. If surface_alt luminance
    is not at least 0.05 units brighter than surface, lightens it by 8%.

    This prevents invisible UI elements caused by surface_alt being
    too close in color to surface.
    """
    surface_lum = _relative_luminance(palette["surface"])
    surface_alt_lum = _relative_luminance(palette["surface_alt"])

    # If surface_alt is not sufficiently lighter, lighten it by 8%
    if surface_alt_lum <= surface_lum + 0.05:
        palette["surface_alt"] = _lighten_by_percentage(palette["surface_alt"], 0.08)

    return palette


def resolve_design_tokens(
    theme_id: Optional[str] = None,
    visual_direction: Optional[str] = None,
    brand_kit: Optional[Dict[str, Any]] = None,
    purpose: Optional[str] = None,
) -> EliteDesignTokens:
    """
    Resolve design tokens with priority system.

    Priority: theme_id -> visual_direction -> brand_kit -> purpose -> defaults

    Args:
        theme_id: Predefined theme ID (reserved for future)
        visual_direction: Visual direction name (must be in VISUAL_DIRECTIONS)
        brand_kit: Custom brand kit dict with palette and fonts
        purpose: Purpose context (pitch, fundraise, security, etc.)

    Returns:
        EliteDesignTokens with all fields populated and safety checks applied.
    """
    # Determine effective visual direction
    effective_direction = visual_direction

    # Purpose-based defaults if no direction specified
    if not effective_direction:
        if purpose in ["pitch", "fundraise"]:
            effective_direction = "premium_brand_house"
        elif purpose in ["security", "enterprise"]:
            effective_direction = "minimal_dark"
        else:
            effective_direction = "light_professional"

    # Validate direction exists
    if effective_direction not in VISUAL_DIRECTIONS:
        effective_direction = "light_professional"

    # Start with direction palette and fonts
    base_direction = VISUAL_DIRECTIONS[effective_direction]
    palette_dict = base_direction["palette"].copy()
    fonts_dict = base_direction["fonts"].copy()

    # Override with brand_kit if provided
    if brand_kit:
        if "palette" in brand_kit:
            palette_dict.update(brand_kit["palette"])
        if "fonts" in brand_kit:
            fonts_dict.update(brand_kit["fonts"])

    # CRITICAL: Ensure surface_alt safety (no invisible nodes)
    palette_dict = ensure_surface_alt(palette_dict)

    # Create palette tokens
    palette_tokens = ElitePaletteTokens(**palette_dict)

    # Create font tokens
    font_tokens = EliteFontTokens(**fonts_dict)

    # Return resolved tokens with defaults
    return EliteDesignTokens(
        palette=palette_tokens,
        fonts=font_tokens,
        type_scale=EliteTypeScale(),
        density="comfortable",
        radius=12,
    )


# ============================================================================
# PURPOSE-SPECIFIC DEFAULTS
# ============================================================================

PURPOSE_DEFAULTS = {
    "pitch": {"visual_direction": "premium_brand_house"},
    "fundraise": {"visual_direction": "premium_brand_house"},
    "internal": {"visual_direction": "light_professional"},
    "security": {"visual_direction": "minimal_dark"},
    "enterprise": {"visual_direction": "minimal_dark"},
    "creative": {"visual_direction": "cinematic_dark"},
}
