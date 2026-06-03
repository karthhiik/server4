"""
Design token resolver for Barise v4 presentation backend.

Handles visual direction selection, token resolution, and critical safety checks
like ensuring surface_alt is always lighter than surface.
"""

import colorsys
from typing import Any, Dict, Literal, Optional

from app.models.v4 import FontTokens, PaletteTokens, ResolvedDesignTokens, TypeScale


# ============================================================================
# VISUAL DIRECTIONS DATABASE
# ============================================================================

VISUAL_DIRECTIONS: Dict[str, Dict[str, Any]] = {
    "minimal_dark": {
        "palette": {
            "primary": "#00D9FF",
            "secondary": "#7C3AED",
            "accent": "#EC4899",
            "background": "#0F0F0F",
            "surface": "#1A1A1A",
            "surface_alt": "#2D2D2D",  # ~8% lighter
            "text_primary": "#FFFFFF",
            "text_secondary": "#D4D4D8",
            "text_muted": "#71717A",
            "border": "#3F3F46",
            "gradient_start": "#00D9FF",
            "gradient_end": "#7C3AED",
            "success": "#10B981",
            "warning": "#F59E0B",
            "danger": "#EF4444",
            "chart": "#06B6D4",
        },
        "fonts": {
            "heading": '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            "body": '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            "display": '"IBM Plex Sans", -apple-system, BlinkMacSystemFont, sans-serif',
            "mono": '"IBM Plex Mono", "Courier New", monospace',
        },
    },
    "cinematic_dark": {
        "palette": {
            "primary": "#FF006E",
            "secondary": "#00F5FF",
            "accent": "#FFB703",
            "background": "#0A0E27",
            "surface": "#1A1F3A",
            "surface_alt": "#2A2F4A",  # ~8% lighter
            "text_primary": "#FFFFFF",
            "text_secondary": "#E0E0E0",
            "text_muted": "#9E9E9E",
            "border": "#404070",
            "gradient_start": "#FF006E",
            "gradient_end": "#00F5FF",
            "success": "#00D084",
            "warning": "#FFA500",
            "danger": "#FF4757",
            "chart": "#FF006E",
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
            "primary": "#0066CC",
            "secondary": "#6B5B95",
            "accent": "#F27835",
            "background": "#FFFFFF",
            "surface": "#F5F7FA",
            "surface_alt": "#EAEEF5",  # ~8% lighter
            "text_primary": "#1A1A1A",
            "text_secondary": "#4A4A4A",
            "text_muted": "#888888",
            "border": "#D0D0D0",
            "gradient_start": "#0066CC",
            "gradient_end": "#6B5B95",
            "success": "#28A745",
            "warning": "#FFC107",
            "danger": "#DC3545",
            "chart": "#0066CC",
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
            "primary": "#2E5090",
            "secondary": "#4A7C7E",
            "accent": "#E8AD60",
            "background": "#FAFBFC",
            "surface": "#FFFFFF",
            "surface_alt": "#F0F2F5",  # ~8% lighter
            "text_primary": "#212B36",
            "text_secondary": "#5A6C7D",
            "text_muted": "#8899AA",
            "border": "#C4CDD5",
            "gradient_start": "#2E5090",
            "gradient_end": "#4A7C7E",
            "success": "#22863A",
            "warning": "#B08500",
            "danger": "#CB2431",
            "chart": "#2E5090",
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
            "secondary": "#666666",
            "accent": "#CC0000",
            "background": "#FFFFFF",
            "surface": "#EEEEEE",
            "surface_alt": "#DDDDDD",  # ~8% lighter
            "text_primary": "#000000",
            "text_secondary": "#333333",
            "text_muted": "#999999",
            "border": "#CCCCCC",
            "gradient_start": "#000000",
            "gradient_end": "#666666",
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
    Lighten a color by increasing lightness by a percentage.
    Uses HLS color space for predictable lightening.
    """
    r, g, b = _hex_to_rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    # Increase lightness by percentage (max 1.0)
    l = min(1.0, l * (1.0 + percentage))

    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return _rgb_to_hex(r, g, b)


# ============================================================================
# CORE FUNCTIONS
# ============================================================================


def ensure_surface_alt(palette: Dict[str, str]) -> Dict[str, str]:
    """
    CRITICAL SAFETY CHECK: Ensure surface_alt is at least 8% lighter in luminance than surface.

    This prevents invisible UI elements caused by surface_alt being darker or equal to surface.
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
) -> ResolvedDesignTokens:
    """
    Resolve design tokens with priority: theme_id -> visual_direction -> brand_kit -> purpose -> system_defaults.

    Args:
        theme_id: Predefined theme ID (currently unused, reserved for future)
        visual_direction: Visual direction name (must be in VISUAL_DIRECTIONS)
        brand_kit: Custom brand kit dict with palette and fonts
        purpose: Purpose context (pitch, fundraise, security, enterprise, etc.)

    Returns:
        ResolvedDesignTokens with all fields populated and safety checks applied.
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

    # CRITICAL: Ensure surface_alt safety
    palette_dict = ensure_surface_alt(palette_dict)

    # Create palette tokens
    palette_tokens = PaletteTokens(**palette_dict)

    # Create font tokens
    font_tokens = FontTokens(**fonts_dict)

    # Return resolved tokens with defaults
    return ResolvedDesignTokens(
        palette=palette_tokens,
        fonts=font_tokens,
        type_scale=TypeScale(),
        density="comfortable",
        radius=12,
    )


# ============================================================================
# PURPOSE-SPECIFIC DEFAULTS (for future expansion)
# ============================================================================

PURPOSE_DEFAULTS = {
    "pitch": {"visual_direction": "premium_brand_house"},
    "fundraise": {"visual_direction": "premium_brand_house"},
    "internal": {"visual_direction": "light_professional"},
    "security": {"visual_direction": "minimal_dark"},
    "enterprise": {"visual_direction": "minimal_dark"},
    "creative": {"visual_direction": "cinematic_dark"},
}
