"""
Color engine — utilities for color manipulation and palette generation.
"""

import colorsys
from typing import Optional

from app.mcp.design_mcp.engines.theme_engine import hex_to_hsl, hsl_to_hex


class ColorEngine:
    """Color manipulation utilities for theme and chart styling."""

    @staticmethod
    def lighten(hex_color: str, amount: float = 10) -> str:
        """Lighten a color by amount (0-100)."""
        h, s, l = hex_to_hsl(hex_color)
        return hsl_to_hex(h, s, min(l + amount, 100))

    @staticmethod
    def darken(hex_color: str, amount: float = 10) -> str:
        """Darken a color by amount (0-100)."""
        h, s, l = hex_to_hsl(hex_color)
        return hsl_to_hex(h, s, max(l - amount, 0))

    @staticmethod
    def saturate(hex_color: str, amount: float = 10) -> str:
        """Increase saturation by amount (0-100)."""
        h, s, l = hex_to_hsl(hex_color)
        return hsl_to_hex(h, min(s + amount, 100), l)

    @staticmethod
    def desaturate(hex_color: str, amount: float = 10) -> str:
        """Decrease saturation by amount (0-100)."""
        h, s, l = hex_to_hsl(hex_color)
        return hsl_to_hex(h, max(s - amount, 0), l)

    @staticmethod
    def opacity_hex(hex_color: str, opacity: float) -> str:
        """Return hex color with alpha channel (8-digit hex)."""
        hex_color = hex_color.lstrip("#")
        alpha = int(opacity * 255)
        return f"#{hex_color}{alpha:02x}"

    @staticmethod
    def generate_gradient_stops(start: str, end: str, steps: int = 5) -> list[str]:
        """Generate intermediate colors for a gradient."""
        sh, ss, sl = hex_to_hsl(start)
        eh, es, el = hex_to_hsl(end)

        colors = []
        for i in range(steps):
            t = i / (steps - 1) if steps > 1 else 0
            h = sh + (eh - sh) * t
            s = ss + (es - ss) * t
            l = sl + (el - sl) * t
            colors.append(hsl_to_hex(h % 360, s, l))
        return colors

    @staticmethod
    def generate_monochromatic(base: str, count: int = 5) -> list[str]:
        """Generate monochromatic palette from a base color."""
        h, s, l = hex_to_hsl(base)
        colors = []
        step = 60 / max(count - 1, 1)
        start_l = max(l - 30, 15)
        for i in range(count):
            colors.append(hsl_to_hex(h, s, start_l + step * i))
        return colors

    @staticmethod
    def generate_analogous(base: str, count: int = 5, spread: float = 30) -> list[str]:
        """Generate analogous color palette."""
        h, s, l = hex_to_hsl(base)
        colors = []
        step = (spread * 2) / max(count - 1, 1)
        start_h = h - spread
        for i in range(count):
            colors.append(hsl_to_hex((start_h + step * i) % 360, s, l))
        return colors

    @staticmethod
    def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        """Convert hex to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """Convert RGB tuple to hex."""
        return f"#{r:02x}{g:02x}{b:02x}"
