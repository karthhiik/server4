"""
CSS Compiler - Phase 4.

Compiles ThemeDefinition objects into reveal.js-compatible CSS.
Generates CSS custom properties (--r-* for reveal.js, --b-* for Barise
layout extensions) and layout-aware rules.

Design decisions:
  - Uses CSS custom properties only (no Tailwind/UnoCSS for reveal.js).
    This avoids the Tailwind v4 preflight conflict (GitHub #3782).
  - All colors, fonts, and spacing flow through :root variables.
  - Theme CSS is inlined into the HTML document (no external file).
  - WCAG AA contrast validation is done at compile time.
"""

import colorsys
import hashlib
import re
from typing import Optional

from app.services.slides_new.themes.theme_models import (
    ThemeColors,
    ThemeDefinition,
    ThemeTypography,
)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple. Handles #RGB, #RRGGBB, rgba()."""
    if hex_color.startswith("rgba") or hex_color.startswith("rgb"):
        # Extract from rgba/rgb
        nums = re.findall(r"[\d.]+", hex_color)
        if len(nums) >= 3:
            return int(float(nums[0])), int(float(nums[1])), int(float(nums[2]))
        return 0, 0, 0
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) >= 6:
        return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return 0, 0, 0


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB tuple to hex color."""
    return f"#{r:02x}{g:02x}{b:02x}"


def _relative_luminance(r: int, g: int, b: int) -> float:
    """WCAG 2.1 relative luminance."""

    def linearize(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def contrast_ratio(color1: str, color2: str) -> float:
    """Calculate WCAG contrast ratio between two colors. Returns 1.0..21.0."""
    r1, g1, b1 = _hex_to_rgb(color1)
    r2, g2, b2 = _hex_to_rgb(color2)
    l1 = _relative_luminance(r1, g1, b1)
    l2 = _relative_luminance(r2, g2, b2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _generate_font_url(fonts: list[str]) -> str:
    """Build a Google Fonts import URL for the given font families."""
    if not fonts:
        return ""
    families = []
    for font in fonts:
        if font in ("Helvetica Neue", "Helvetica", "Arial", "serif", "sans-serif", "monospace"):
            continue  # System fonts
        family = font.replace(" ", "+")
        families.append(f"family={family}:wght@300;400;500;600;700;800;900")
    if not families:
        return ""
    return f'@import url("https://fonts.googleapis.com/css2?{"&".join(families)}&display=swap");'


class CSSCompiler:
    """
    Compiles a ThemeDefinition into reveal.js CSS.

    The output CSS uses:
      --r-*  variables (official reveal.js custom properties)
      --b-*  variables (Barise extensions for layouts, cards, KPIs, etc.)

    Usage:
        compiler = CSSCompiler()
        css = compiler.compile(theme)
        # css is a string you embed in <style id="barise-theme">
    """

    def compile(self, theme: ThemeDefinition) -> str:
        """Compile a ThemeDefinition into a complete CSS string."""
        parts: list[str] = []

        # Font imports
        all_fonts = [
            theme.typography.heading_font,
            theme.typography.body_font,
            theme.typography.mono_font,
        ]
        unique_fonts = list(dict.fromkeys(all_fonts))
        font_import = _generate_font_url(unique_fonts)
        if font_import:
            parts.append(font_import)
            parts.append("")

        # Root variables
        parts.append(self._root_variables(theme))

        # Typography rules
        parts.append(self._typography_rules(theme))

        # Card and surface styles
        parts.append(self._card_styles(theme))

        # Specialty extras (glassmorphism, scanlines, etc.)
        extras_css = self._specialty_extras(theme)
        if extras_css:
            parts.append(extras_css)

        return "\n".join(parts)

    def compile_with_validation(self, theme: ThemeDefinition) -> tuple[str, list[str]]:
        """Compile and return (css, warnings). Warnings include contrast issues."""
        css = self.compile(theme)
        warnings = self._validate_contrast(theme)
        return css, warnings

    def cache_key(self, theme: ThemeDefinition) -> str:
        """Generate a stable cache key for a compiled theme."""
        data = f"{theme.id}:{theme.variant}:{theme.colors.__dict__}:{theme.typography.__dict__}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    # ------------------------------------------------------------------ #
    #  ROOT CSS VARIABLES                                                #
    # ------------------------------------------------------------------ #

    def _root_variables(self, theme: ThemeDefinition) -> str:
        c = theme.colors
        t = theme.typography
        s = theme.spacing

        return f"""
    :root {{
      /* reveal.js core variables */
      --r-background-color: {c.background};
      --r-main-font: '{t.body_font}', sans-serif;
      --r-main-font-size: {t.base_size}px;
      --r-main-color: {c.text};
      --r-heading-font: '{t.heading_font}', sans-serif;
      --r-heading-color: {c.heading};
      --r-heading-font-weight: {t.heading_weight};
      --r-heading-text-shadow: none;
      --r-heading-letter-spacing: {t.heading_letter_spacing};
      --r-heading-line-height: {t.heading_line_height};
      --r-link-color: {c.link};
      --r-link-color-hover: {c.accent};
      --r-selection-background-color: {c.accent};
      --r-selection-color: {c.background};
      --r-block-margin: 20px;
      --r-code-font: '{t.mono_font}', monospace;

      /* Barise extensions */
      --b-surface: {c.surface};
      --b-primary: {c.primary};
      --b-secondary: {c.secondary};
      --b-accent: {c.accent};
      --b-text-muted: {c.text_muted};
      --b-code-bg: {c.code_bg};
      --b-success: {c.success};
      --b-warning: {c.warning};
      --b-error: {c.error};
      --b-card-radius: {s.card_radius};
      --b-card-padding: {s.card_padding};
      --b-slide-padding: {s.slide_padding};
      --b-section-gap: {s.section_gap};
      --b-element-gap: {s.element_gap};
      --b-shadow-subtle: {theme.shadows.get("subtle", "none")};
      --b-shadow-card: {theme.shadows.get("card", "none")};
    }}"""

    # ------------------------------------------------------------------ #
    #  TYPOGRAPHY                                                        #
    # ------------------------------------------------------------------ #

    def _typography_rules(self, theme: ThemeDefinition) -> str:
        t = theme.typography
        c = theme.colors
        return f"""
    /* Typography */
    .reveal .slides section {{
      padding: var(--b-slide-padding);
      color: var(--r-main-color);
      font-family: var(--r-main-font);
    }}
    .reveal .slides h1,
    .reveal .slides h2,
    .reveal .slides h3,
    .reveal .slides h4 {{
      font-family: var(--r-heading-font);
      color: var(--r-heading-color);
      font-weight: var(--r-heading-font-weight);
      letter-spacing: var(--r-heading-letter-spacing);
      line-height: var(--r-heading-line-height);
      text-shadow: var(--r-heading-text-shadow);
    }}
    .reveal .slides section a {{
      color: var(--r-link-color);
      text-decoration: none;
    }}
    .reveal .slides section a:hover {{
      color: var(--r-link-color-hover);
      text-decoration: underline;
    }}
    .reveal .slides pre {{
      background: var(--b-code-bg);
      padding: 1rem;
      border-radius: 8px;
      font-family: var(--r-code-font);
      font-size: 0.8em;
    }}
    .reveal .slides code {{
      font-family: var(--r-code-font);
    }}
    .reveal .slides .subtitle,
    .reveal .slides .tagline {{
      color: var(--b-text-muted);
    }}
    .reveal .slides .presenter {{
      color: var(--b-text-muted);
    }}"""

    # ------------------------------------------------------------------ #
    #  CARD / SURFACE STYLES                                             #
    # ------------------------------------------------------------------ #

    def _card_styles(self, theme: ThemeDefinition) -> str:
        return """
    /* Cards and Surfaces */
    .reveal .slides .grid-cell,
    .reveal .slides .kpi-card,
    .reveal .slides .team-member {{
      background: var(--b-surface);
      border-radius: var(--b-card-radius);
      padding: var(--b-card-padding);
      box-shadow: var(--b-shadow-card);
    }}
    .reveal .slides .kpi-value {{
      color: var(--b-accent);
    }}
    .reveal .slides .kpi-label,
    .reveal .slides .team-role,
    .reveal .slides .team-bio {{
      color: var(--b-text-muted);
    }}
    .reveal .slides .timeline-marker {{
      background: var(--b-accent);
      border-color: var(--r-background-color);
    }}
    .reveal .slides .timeline-track::before {{
      background: var(--b-accent);
    }}
    .reveal .slides .comparison-table th {{
      border-bottom-color: var(--b-accent);
    }}
    .reveal .slides .comparison-table td {{
      border-bottom-color: var(--b-surface);
    }}
    .reveal .slides tr.advantage td:nth-child(2) {{
      color: var(--b-accent);
    }}
    .reveal .slides ul li::before {{
      color: var(--b-accent);
    }}
    .reveal .slides blockquote {{
      border-left-color: var(--b-accent);
    }}
    .reveal .slides .team-avatar {{
      background: var(--b-accent);
      color: var(--r-background-color);
    }}"""

    # ------------------------------------------------------------------ #
    #  SPECIALTY EXTRAS                                                  #
    # ------------------------------------------------------------------ #

    def _specialty_extras(self, theme: ThemeDefinition) -> str:
        extras = theme.extras
        if not extras:
            return ""

        parts: list[str] = ["\n    /* Specialty theme extras */"]

        # Glassmorphism
        if extras.get("backdrop_blur"):
            blur = extras["backdrop_blur"]
            border = extras.get("border_glass", "1px solid rgba(255,255,255,0.1)")
            parts.append(f"""
    .reveal .slides .grid-cell,
    .reveal .slides .kpi-card {{
      background: var(--b-surface);
      backdrop-filter: blur({blur});
      -webkit-backdrop-filter: blur({blur});
      border: {border};
    }}""")

        # Terminal scanlines
        if extras.get("scanlines"):
            parts.append("""
    .reveal .slides::after {
      content: "";
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: repeating-linear-gradient(
        0deg,
        rgba(0, 0, 0, 0.05) 0px,
        rgba(0, 0, 0, 0.05) 1px,
        transparent 1px,
        transparent 3px
      );
      pointer-events: none;
      z-index: 9999;
    }""")

        # Blueprint grid
        if extras.get("grid_overlay"):
            parts.append("""
    .reveal .slides section {
      background-image:
        linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px);
      background-size: 40px 40px;
    }""")

        # Warm gradient background
        warm_grad = extras.get("warm_gradient_bg")
        if warm_grad:
            parts.append(f"""
    .reveal {{
      background: {warm_grad};
    }}""")

        # Mesh gradient
        if extras.get("mesh_gradient"):
            parts.append("""
    .reveal {
      background:
        radial-gradient(at 20% 30%, rgba(102,126,234,0.3) 0%, transparent 50%),
        radial-gradient(at 80% 70%, rgba(118,75,162,0.3) 0%, transparent 50%),
        radial-gradient(at 50% 50%, rgba(102,126,234,0.1) 0%, transparent 80%);
    }""")

        return "\n".join(parts)

    # ------------------------------------------------------------------ #
    #  CONTRAST VALIDATION                                               #
    # ------------------------------------------------------------------ #

    def _validate_contrast(self, theme: ThemeDefinition) -> list[str]:
        """Check WCAG AA contrast (4.5:1 for text, 3:1 for large text)."""
        warnings: list[str] = []
        c = theme.colors

        pairs = [
            ("text", c.text, "background", c.background, 4.5),
            ("heading", c.heading, "background", c.background, 3.0),
            ("link", c.link, "background", c.background, 4.5),
            ("text_muted", c.text_muted, "background", c.background, 3.0),
            ("text", c.text, "surface", c.surface, 4.5),
        ]

        for name1, color1, name2, color2, min_ratio in pairs:
            try:
                ratio = contrast_ratio(color1, color2)
                if ratio < min_ratio:
                    warnings.append(
                        f"{name1} ({color1}) on {name2} ({color2}): "
                        f"contrast {ratio:.1f}:1 < {min_ratio}:1 required"
                    )
            except (ValueError, IndexError):
                pass  # Skip invalid color formats like rgba

        return warnings
