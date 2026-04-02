"""
Theme engine — generates themes from brand colors using HSL color math.
No LLM needed for most theme generation (pure algorithmic).
Also suggests best built-in theme based on topic, purpose, and audience.
"""

import colorsys
import hashlib
from typing import Optional

import structlog

logger = structlog.get_logger()

# Topic keyword → theme mapping (V1: rule-based, zero LLM cost)
_TOPIC_THEME_MAP = {
    "tech-neon": [
        "ai",
        "ml",
        "machine learning",
        "tech",
        "software",
        "saas",
        "platform",
        "cloud",
        "api",
        "data",
        "automation",
        "cyber",
        "blockchain",
        "web3",
        "iot",
        "digital",
        "compute",
    ],
    "startup-gradient": [
        "sales",
        "pitch",
        "startup",
        "fundraising",
        "investor",
        "venture",
        "seed",
        "series",
        "growth",
        "unicorn",
        "disrupt",
        "launch",
    ],
    "minimal-mono": [
        "internal",
        "meeting",
        "workshop",
        "review",
        "standup",
        "retrospective",
        "sync",
        "update",
        "team meeting",
    ],
    "corporate-blue": [
        "quarterly",
        "board",
        "financial",
        "report",
        "revenue",
        "earnings",
        "annual",
        "fiscal",
        "compliance",
        "governance",
    ],
    "nature-earth": [
        "health",
        "green",
        "nature",
        "sustainability",
        "esg",
        "environment",
        "climate",
        "organic",
        "eco",
        "wellness",
        "agriculture",
        "farming",
        "renewable",
        "solar",
        "wind",
    ],
    "medical-clean": [
        "medical",
        "healthcare",
        "pharma",
        "biotech",
        "clinical",
        "hospital",
        "patient",
        "drug",
        "therapy",
        "diagnostic",
    ],
    "academic-serif": [
        "education",
        "training",
        "learning",
        "academic",
        "research",
        "university",
        "course",
        "curriculum",
        "pedagogy",
        "thesis",
    ],
    "creative-bold": [
        "creative",
        "design",
        "brand",
        "marketing",
        "campaign",
        "media",
        "content",
        "storytelling",
        "art",
        "fashion",
    ],
}

# Safe fallback for mixed/conflicting topics
_SAFE_FALLBACK_THEME = "minimal-mono"
_SAFE_FALLBACK_REASON = (
    "Topic spans multiple categories. Selected neutral professional theme."
)


def hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
    """Convert hex color to HSL (0-360, 0-100, 0-100)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s * 100, l * 100


def hsl_to_hex(h: float, s: float, l: float) -> str:
    """Convert HSL (0-360, 0-100, 0-100) to hex color."""
    r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


class ThemeEngine:
    """Generates complete themes from brand colors using color theory."""

    def suggest_theme(self, topic: str, purpose: str = "", audience: str = "") -> dict:
        """Suggest best built-in theme based on topic, purpose, and audience.

        Uses keyword matching with tie-breaker logic for mixed topics.
        Zero LLM cost — pure rule-based matching.
        """
        topic_lower = topic.lower()
        scores = {}
        for theme_id, keywords in _TOPIC_THEME_MAP.items():
            score = sum(1 for kw in keywords if kw in topic_lower)
            scores[theme_id] = score

        max_score = max(scores.values()) if scores else 0

        # No keywords matched — default to corporate-blue
        if max_score == 0:
            return {
                "theme_id": "corporate-blue",
                "confidence": 0.0,
                "reason": "No specific topic match. Defaulted to professional theme.",
            }

        # Check for ties — mixed topic dilemma
        tied_themes = [k for k, v in scores.items() if v == max_score and v > 0]

        if len(tied_themes) > 1:
            # Conflict detected — use safe fallback
            best_theme = _SAFE_FALLBACK_THEME
            reason = _SAFE_FALLBACK_REASON
            confidence = max_score / 3.0
        else:
            best_theme = tied_themes[0]
            confidence = min(max_score / 3.0, 1.0)
            reason = f"Topic matches '{best_theme}' theme ({max_score} keyword hits)."

        # Purpose overrides
        if purpose in ("investor", "fundraising") and best_theme == "minimal-mono":
            best_theme = "startup-gradient"
            reason = f"Overrode '{best_theme}' → 'startup-gradient' for investor/fundraising purpose."
        elif purpose == "internal" and best_theme == "startup-gradient":
            best_theme = "minimal-mono"
            reason = (
                "Overrode 'startup-gradient' → 'minimal-mono' for internal purpose."
            )
        elif purpose in ("quarterly", "board") and best_theme not in (
            "corporate-blue",
            "minimal-mono",
        ):
            best_theme = "corporate-blue"
            reason = f"Overrode to 'corporate-blue' for {purpose} purpose."

        logger.info(
            "theme_suggested",
            topic=topic[:50],
            purpose=purpose,
            theme_id=best_theme,
            confidence=round(confidence, 2),
        )
        return {
            "theme_id": best_theme,
            "confidence": round(confidence, 2),
            "reason": reason,
        }

    def generate_from_brand_colors(
        self,
        brand_colors: list[str],
        brand_vibe: str = "professional",
        font_preference: str = "modern",
    ) -> dict:
        """Generate a complete theme from 1-3 brand colors."""
        primary = brand_colors[0] if brand_colors else "#2563eb"
        secondary = (
            brand_colors[1]
            if len(brand_colors) > 1
            else self._generate_complement(primary)
        )
        accent = (
            brand_colors[2] if len(brand_colors) > 2 else self._generate_accent(primary)
        )

        ph, ps, pl = hex_to_hsl(primary)

        # Generate background/surface based on vibe
        if brand_vibe in ("dark", "bold", "tech", "neon"):
            background = hsl_to_hex(ph, max(ps * 0.15, 5), 10)
            surface = hsl_to_hex(ph, max(ps * 0.1, 3), 15)
            text_primary = "#ffffff"
            text_secondary = "#b0b0b0"
        elif brand_vibe in ("minimal", "clean", "light"):
            background = "#ffffff"
            surface = hsl_to_hex(ph, max(ps * 0.05, 2), 97)
            text_primary = "#1a1a1a"
            text_secondary = "#6b7280"
        else:  # professional, corporate, warm, nature
            background = "#ffffff"
            surface = hsl_to_hex(ph, max(ps * 0.08, 3), 96)
            text_primary = "#111827"
            text_secondary = "#4b5563"

        # Generate chart palette (6 distinct colors)
        chart_colors = self._generate_chart_palette(primary, secondary, accent)

        # Font selection
        fonts = self._select_fonts(font_preference)

        theme = {
            "colors": {
                "primary": primary,
                "secondary": secondary,
                "accent": accent,
                "background": background,
                "surface": surface,
                "text_primary": text_primary,
                "text_secondary": text_secondary,
                "chart_colors": chart_colors,
            },
            "fonts": fonts,
            "generated_from": {
                "brand_colors": brand_colors,
                "brand_vibe": brand_vibe,
                "font_preference": font_preference,
            },
        }

        logger.info("theme_generated", primary=primary, vibe=brand_vibe)
        return theme

    def _generate_complement(self, hex_color: str) -> str:
        """Generate complementary color."""
        h, s, l = hex_to_hsl(hex_color)
        return hsl_to_hex((h + 180) % 360, s, l)

    def _generate_accent(self, hex_color: str) -> str:
        """Generate accent color (triadic)."""
        h, s, l = hex_to_hsl(hex_color)
        return hsl_to_hex((h + 120) % 360, min(s * 1.2, 100), min(l * 1.1, 85))

    def _generate_chart_palette(
        self, primary: str, secondary: str, accent: str
    ) -> list[str]:
        """Generate 6 distinct chart colors from base palette."""
        ph, ps, pl = hex_to_hsl(primary)
        colors = [primary, secondary, accent]

        # Add 3 more by rotating hue
        for offset in [60, 210, 300]:
            h = (ph + offset) % 360
            colors.append(hsl_to_hex(h, min(ps * 0.9, 80), min(pl * 1.05, 70)))

        return colors[:6]

    def _select_fonts(self, preference: str) -> dict:
        """Select font stack based on preference."""
        font_stacks = {
            "modern": {
                "heading": "Inter",
                "body": "Inter",
                "mono": "JetBrains Mono",
            },
            "classic": {
                "heading": "Georgia",
                "body": "Helvetica Neue",
                "mono": "Courier New",
            },
            "playful": {
                "heading": "Poppins",
                "body": "Nunito",
                "mono": "Fira Code",
            },
            "corporate": {
                "heading": "Montserrat",
                "body": "Open Sans",
                "mono": "Source Code Pro",
            },
            "elegant": {
                "heading": "Playfair Display",
                "body": "Lato",
                "mono": "IBM Plex Mono",
            },
            "technical": {
                "heading": "Roboto",
                "body": "Roboto",
                "mono": "Roboto Mono",
            },
        }
        return font_stacks.get(preference, font_stacks["modern"])

    def adjust_for_contrast(
        self, fg_hex: str, bg_hex: str, min_ratio: float = 4.5
    ) -> str:
        """Adjust foreground color to meet WCAG contrast ratio against background."""
        ratio = self._contrast_ratio(fg_hex, bg_hex)
        if ratio >= min_ratio:
            return fg_hex

        fh, fs, fl = hex_to_hsl(fg_hex)
        _, _, bl = hex_to_hsl(bg_hex)

        # If bg is light, darken fg; if bg is dark, lighten fg
        if bl > 50:
            while (
                fl > 5
                and self._contrast_ratio(hsl_to_hex(fh, fs, fl), bg_hex) < min_ratio
            ):
                fl -= 5
        else:
            while (
                fl < 95
                and self._contrast_ratio(hsl_to_hex(fh, fs, fl), bg_hex) < min_ratio
            ):
                fl += 5

        return hsl_to_hex(fh, fs, fl)

    def _contrast_ratio(self, hex1: str, hex2: str) -> float:
        """Calculate WCAG contrast ratio between two colors."""
        l1 = self._relative_luminance(hex1)
        l2 = self._relative_luminance(hex2)
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)

    def _relative_luminance(self, hex_color: str) -> float:
        """Calculate relative luminance per WCAG 2.0."""
        hex_color = hex_color.lstrip("#")
        r, g, b = (int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

        def linearize(c):
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)
