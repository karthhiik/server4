"""
Generative Theme Engine - Phase 4.

Creates new themes from minimal input (brand colors, mood keywords).
Supports theme mutations (warmer, cooler, higher-contrast, etc.) and
produces validated ThemeDefinition objects.

Algorithm:
1. Extract HSL from primary color
2. Generate complementary/analogous colors
3. Create full 9-shade palette
4. Select typography pair based on mood
5. Compute spacing scale
6. Validate WCAG AA contrast
7. Return complete ThemeDefinition
"""

import colorsys
import hashlib
from typing import Optional

from app.services.slides_new.themes.theme_models import (
    BuiltInThemes,
    ThemeColors,
    ThemeDefinition,
    ThemeMutation,
    ThemeSpacing,
    ThemeTier,
    ThemeTypography,
)
from app.services.slides_new.themes.css_compiler import (
    CSSCompiler,
    _hex_to_rgb,
    _rgb_to_hex,
    contrast_ratio,
)


# Font pairing recommendations by mood
MOOD_FONTS: dict[str, ThemeTypography] = {
    "professional": ThemeTypography(
        heading_font="Inter",
        body_font="Inter",
        heading_weight=700,
    ),
    "playful": ThemeTypography(
        heading_font="DM Sans",
        body_font="Nunito",
        heading_weight=700,
        heading_letter_spacing="0",
    ),
    "dark": ThemeTypography(
        heading_font="Outfit",
        body_font="DM Sans",
        heading_weight=800,
        heading_letter_spacing="-0.03em",
    ),
    "minimal": ThemeTypography(
        heading_font="Inter",
        body_font="Inter",
        heading_weight=500,
        heading_letter_spacing="-0.01em",
        base_size=38,
    ),
    "corporate": ThemeTypography(
        heading_font="Sora",
        body_font="Inter",
        heading_weight=600,
    ),
    "creative": ThemeTypography(
        heading_font="Fraunces",
        body_font="Karla",
        heading_weight=700,
    ),
    "tech": ThemeTypography(
        heading_font="Outfit",
        body_font="DM Sans",
        mono_font="Fira Code",
        heading_weight=700,
    ),
    "editorial": ThemeTypography(
        heading_font="Playfair Display",
        body_font="Source Serif Pro",
        heading_weight=700,
        heading_letter_spacing="0",
        heading_line_height=1.2,
    ),
}


def _hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
    """Convert hex color to HSL (h: 0-360, s: 0-100, l: 0-100)."""
    r, g, b = _hex_to_rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    return h * 360, s * 100, l * 100


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    """Convert HSL to hex (h: 0-360, s: 0-100, l: 0-100)."""
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)
    return _rgb_to_hex(int(r * 255), int(g * 255), int(b * 255))


def _adjust_lightness(hex_color: str, delta: float) -> str:
    """Adjust lightness of a color by delta (-100..+100)."""
    h, s, l = _hex_to_hsl(hex_color)
    l = max(0, min(100, l + delta))
    return _hsl_to_hex(h, s, l)


def _adjust_saturation(hex_color: str, delta: float) -> str:
    """Adjust saturation by delta (-100..+100)."""
    h, s, l = _hex_to_hsl(hex_color)
    s = max(0, min(100, s + delta))
    return _hsl_to_hex(h, s, l)


def _shift_hue(hex_color: str, degrees: float) -> str:
    """Shift hue by degrees."""
    h, s, l = _hex_to_hsl(hex_color)
    h = (h + degrees) % 360
    return _hsl_to_hex(h, s, l)


def _complementary(hex_color: str) -> str:
    """Generate complementary color (opposite on wheel)."""
    return _shift_hue(hex_color, 180)


def _analogous(hex_color: str, angle: float = 30) -> tuple[str, str]:
    """Generate two analogous colors."""
    return _shift_hue(hex_color, angle), _shift_hue(hex_color, -angle)


def _is_dark_color(hex_color: str) -> bool:
    """Determine if a color is perceptually dark."""
    _, _, l = _hex_to_hsl(hex_color)
    return l < 50


class GenerativeThemeEngine:
    """
    Generate complete themes from minimal input.

    Usage:
        engine = GenerativeThemeEngine()
        theme = engine.from_brand_colors("#FF6B35", mood="professional")
        theme = engine.mutate(existing_theme, ThemeMutation.WARMER)
    """

    def __init__(self):
        self._css_compiler = CSSCompiler()

    def from_brand_colors(
        self,
        primary: str,
        secondary: Optional[str] = None,
        accent: Optional[str] = None,
        mood: str = "professional",
        name: Optional[str] = None,
    ) -> ThemeDefinition:
        """
        Generate a complete theme from 1-3 brand colors.

        Algorithm:
        1. Derive secondary/accent from primary if not provided
        2. Determine dark vs light variant based on primary
        3. Generate background, surface, text colors
        4. Select typography based on mood
        5. Build complete ThemeDefinition
        """
        primary = primary.strip()
        is_dark = _is_dark_color(primary)

        # Derive missing colors
        if secondary is None:
            secondary = _complementary(primary)
        if accent is None:
            accent = primary

        # Generate background/surface/text based on variant
        if is_dark:
            variant = "dark"
            background = _adjust_lightness(primary, -30)
            surface = _adjust_lightness(primary, -20)
            text = "#E2E8F0"
            text_muted = "#94A3B8"
            heading = "#F8FAFC"
            link = accent
            code_bg = _adjust_lightness(background, -5)
        else:
            variant = "light"
            background = _adjust_lightness(primary, 45)
            surface = _adjust_lightness(primary, 35)
            # Ensure readable text on light backgrounds
            text = "#1E293B"
            text_muted = "#64748B"
            heading = "#0F172A"
            link = _adjust_lightness(primary, -15) if not _is_dark_color(primary) else primary
            code_bg = _adjust_lightness(background, -5)

        # Ensure minimum contrast
        bg_ratio = contrast_ratio(text, background)
        if bg_ratio < 4.5:
            if is_dark:
                text = "#FFFFFF"
            else:
                text = "#000000"

        # Typography
        typography = MOOD_FONTS.get(mood, MOOD_FONTS["professional"])

        # Generate ID
        theme_id = name or f"gen-{hashlib.md5(primary.encode()).hexdigest()[:8]}"
        theme_name = name or f"Generated ({primary})"

        return ThemeDefinition(
            id=theme_id,
            name=theme_name,
            variant=variant,
            tier=ThemeTier.GENERATED,
            colors=ThemeColors(
                background=background,
                surface=surface,
                primary=primary,
                secondary=secondary,
                accent=accent,
                text=text,
                text_muted=text_muted,
                heading=heading,
                link=link,
                code_bg=code_bg,
            ),
            typography=typography,
            character=f"Generated from {primary} ({mood})",
            shadows={
                "subtle": f"0 2px 8px {primary}1a",
                "card": f"0 8px 24px {primary}26",
            },
        )

    def mutate(self, theme: ThemeDefinition, mutation: ThemeMutation) -> ThemeDefinition:
        """
        Create a variant of an existing theme.

        Mutations:
          WARMER: shift hues +15, increase saturation
          COOLER: shift hues -15, decrease saturation
          HIGHER_CONTRAST: darken darks, lighten lights
          MORE_SATURATED: +20% saturation
          DESATURATED: -30% saturation
        """
        c = theme.colors
        new_colors = ThemeColors(
            background=c.background,
            surface=c.surface,
            primary=c.primary,
            secondary=c.secondary,
            accent=c.accent,
            text=c.text,
            text_muted=c.text_muted,
            heading=c.heading,
            link=c.link,
            code_bg=c.code_bg,
            success=c.success,
            warning=c.warning,
            error=c.error,
        )

        if mutation == ThemeMutation.WARMER:
            new_colors.primary = _shift_hue(c.primary, 15)
            new_colors.secondary = _shift_hue(c.secondary, 15)
            new_colors.accent = _shift_hue(c.accent, 15)
            new_colors.link = _shift_hue(c.link, 15)
            new_colors.primary = _adjust_saturation(new_colors.primary, 10)

        elif mutation == ThemeMutation.COOLER:
            new_colors.primary = _shift_hue(c.primary, -15)
            new_colors.secondary = _shift_hue(c.secondary, -15)
            new_colors.accent = _shift_hue(c.accent, -15)
            new_colors.link = _shift_hue(c.link, -15)
            new_colors.primary = _adjust_saturation(new_colors.primary, -10)

        elif mutation == ThemeMutation.HIGHER_CONTRAST:
            new_colors.background = _adjust_lightness(c.background, -10)
            new_colors.surface = _adjust_lightness(c.surface, -8)
            new_colors.text = _adjust_lightness(c.text, 15)
            new_colors.heading = _adjust_lightness(c.heading, 10)
            new_colors.text_muted = _adjust_lightness(c.text_muted, 10)

        elif mutation == ThemeMutation.MORE_SATURATED:
            new_colors.primary = _adjust_saturation(c.primary, 20)
            new_colors.secondary = _adjust_saturation(c.secondary, 20)
            new_colors.accent = _adjust_saturation(c.accent, 20)
            new_colors.link = _adjust_saturation(c.link, 20)

        elif mutation == ThemeMutation.DESATURATED:
            new_colors.primary = _adjust_saturation(c.primary, -30)
            new_colors.secondary = _adjust_saturation(c.secondary, -30)
            new_colors.accent = _adjust_saturation(c.accent, -30)
            new_colors.link = _adjust_saturation(c.link, -30)

        new_id = f"{theme.id}-{mutation.value}"
        new_name = f"{theme.name} ({mutation.value})"

        return ThemeDefinition(
            id=new_id,
            name=new_name,
            variant=theme.variant,
            tier=ThemeTier.MUTATION,
            colors=new_colors,
            typography=theme.typography,
            spacing=theme.spacing,
            preset=theme.preset,
            character=f"{theme.character} + {mutation.value}",
            shadows=theme.shadows,
            extras=theme.extras,
        )

    def generate_palette(self, primary: str, count: int = 9) -> list[str]:
        """Generate a shade palette (50-900) from a single color."""
        shades: list[str] = []
        # From lightest to darkest
        steps = list(range(count))
        mid = count // 2
        for i in steps:
            delta = (mid - i) * (80 / count)
            shades.append(_adjust_lightness(primary, delta))
        return shades

    def compile_css(self, theme: ThemeDefinition) -> str:
        """Shortcut to compile theme to CSS."""
        return self._css_compiler.compile(theme)

    def compile_with_validation(self, theme: ThemeDefinition) -> tuple[str, list[str]]:
        """Compile theme to CSS and return contrast warnings."""
        return self._css_compiler.compile_with_validation(theme)
