"""
Design System Module - Phase 2
Color schemes, typography scales, spacing, and Anti-AI-Slop presets.
"""

from typing import Any, Dict, List, Optional


class DesignSystem:
    """
    Production-ready design system for presentations.
    Includes 16 color schemes, 12 style presets, typography scales.
    """

    COLOR_SCHEMES = {
        "default": {
            "primary": "#1A1A2E",
            "secondary": "#16213E",
            "accent": "#E94560",
            "background": "#FFFFFF",
            "text": "#1A1A2E",
            "muted": "#6B7280",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
        },
        "yc_pitch": {
            "primary": "#1A1A2E",
            "secondary": "#16213E",
            "accent": "#E94560",
            "background": "#FFFFFF",
            "text": "#1A1A2E",
            "muted": "#6B7280",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
        },
        "consulting": {
            "primary": "#0F172A",
            "secondary": "#334155",
            "accent": "#0EA5E9",
            "background": "#F8FAFC",
            "text": "#1E293B",
            "muted": "#64748B",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
        },
        "investor_update": {
            "primary": "#18181B",
            "secondary": "#27272A",
            "accent": "#10B981",
            "background": "#FAFAFA",
            "text": "#18181B",
            "muted": "#71717A",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
        },
        "sales": {
            "primary": "#0D0D0D",
            "secondary": "#262626",
            "accent": "#FF4D4D",
            "background": "#FFFFFF",
            "text": "#0D0D0D",
            "muted": "#737373",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
        },
        "marketing": {
            "primary": "#000000",
            "secondary": "#1A1A1A",
            "accent": "#6366F1",
            "background": "#FFFFFF",
            "text": "#000000",
            "muted": "#525252",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
        },
        "dark_mode": {
            "primary": "#F8FAFC",
            "secondary": "#E2E8F0",
            "accent": "#38BDF8",
            "background": "#0F172A",
            "text": "#F8FAFC",
            "muted": "#94A3B8",
            "success": "#34D399",
            "warning": "#FBBF24",
            "error": "#F87171",
        },
        "minimalist": {
            "primary": "#1A1A1A",
            "secondary": "#4A4A4A",
            "accent": "#2563EB",
            "background": "#FAFAFA",
            "text": "#1A1A1A",
            "muted": "#9CA3AF",
            "success": "#059669",
            "warning": "#D97706",
            "error": "#DC2626",
        },
        "premium": {
            "primary": "#1C1917",
            "secondary": "#292524",
            "accent": "#D4AF37",
            "background": "#FFFBEB",
            "text": "#1C1917",
            "muted": "#78716C",
            "success": "#65A30D",
            "warning": "#CA8A04",
            "error": "#BE123C",
        },
        "startup": {
            "primary": "#0F172A",
            "secondary": "#1E293B",
            "accent": "#8B5CF6",
            "background": "#FFFFFF",
            "text": "#0F172A",
            "muted": "#64748B",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
        },
        "corporate": {
            "primary": "#1E3A8A",
            "secondary": "#1E40AF",
            "accent": "#3B82F6",
            "background": "#F0F9FF",
            "text": "#1E3A8A",
            "muted": "#64748B",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
        },
        "tech": {
            "primary": "#09090B",
            "secondary": "#18181B",
            "accent": "#22D3EE",
            "background": "#FFFFFF",
            "text": "#09090B",
            "muted": "#71717A",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
        },
        "creative": {
            "primary": "#2D1B69",
            "secondary": "#4C1D95",
            "accent": "#F472B6",
            "background": "#FAF5FF",
            "text": "#2D1B69",
            "muted": "#7C3AED",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
        },
        "fintech": {
            "primary": "#022C22",
            "secondary": "#064E3B",
            "accent": "#34D399",
            "background": "#ECFDF5",
            "text": "#022C22",
            "muted": "#6EE7B7",
            "success": "#34D399",
            "warning": "#F59E0B",
            "error": "#EF4444",
        },
        "healthcare": {
            "primary": "#0C4A6E",
            "secondary": "#0EA5E9",
            "accent": "#06B6D4",
            "background": "#F0F9FF",
            "text": "#0C4A6E",
            "muted": "#7DD3FC",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
        },
        "education": {
            "primary": "#1E3A8A",
            "secondary": "#3B82F6",
            "accent": "#FCD34D",
            "background": "#FFFBEB",
            "text": "#1E3A8A",
            "muted": "#93C5FD",
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
        },
    }

    TYPOGRAPHY_SCALES = {
        "default": {
            "h1": {"size": 44, "weight": 700, "lineHeight": 1.2},
            "h2": {"size": 36, "weight": 600, "lineHeight": 1.3},
            "h3": {"size": 28, "weight": 600, "lineHeight": 1.4},
            "h4": {"size": 24, "weight": 500, "lineHeight": 1.4},
            "body": {"size": 18, "weight": 400, "lineHeight": 1.6},
            "body_small": {"size": 14, "weight": 400, "lineHeight": 1.5},
            "caption": {"size": 12, "weight": 400, "lineHeight": 1.4},
        },
        "hero": {
            "h1": {"size": 64, "weight": 800, "lineHeight": 1.1},
            "h2": {"size": 48, "weight": 700, "lineHeight": 1.2},
            "h3": {"size": 36, "weight": 600, "lineHeight": 1.3},
            "h4": {"size": 28, "weight": 600, "lineHeight": 1.4},
            "body": {"size": 20, "weight": 400, "lineHeight": 1.6},
            "body_small": {"size": 16, "weight": 400, "lineHeight": 1.5},
            "caption": {"size": 14, "weight": 400, "lineHeight": 1.4},
        },
        "minimal": {
            "h1": {"size": 36, "weight": 500, "lineHeight": 1.3},
            "h2": {"size": 28, "weight": 500, "lineHeight": 1.4},
            "h3": {"size": 22, "weight": 500, "lineHeight": 1.4},
            "h4": {"size": 18, "weight": 500, "lineHeight": 1.5},
            "body": {"size": 16, "weight": 400, "lineHeight": 1.6},
            "body_small": {"size": 13, "weight": 400, "lineHeight": 1.5},
            "caption": {"size": 11, "weight": 400, "lineHeight": 1.4},
        },
    }

    FONT_PAIRS = {
        "default": {"heading": "Inter", "body": "Inter", "accent": "JetBrains Mono"},
        "yc_pitch": {"heading": "DM Sans", "body": "Inter", "accent": "Space Mono"},
        "consulting": {
            "heading": "Playfair Display",
            "body": "Source Sans Pro",
            "accent": "Lora",
        },
        "investor": {"heading": "Sora", "body": "Inter", "accent": "JetBrains Mono"},
        "sales": {
            "heading": "Clash Display",
            "body": "Satoshi",
            "accent": "General Sans",
        },
        "marketing": {
            "heading": "Cabinet Grotesk",
            "body": "Satoshi",
            "accent": "Space Grotesk",
        },
        "premium": {
            "heading": "Cormorant Garamond",
            "body": "Proza Libre",
            "accent": "EB Garamond",
        },
        "tech": {"heading": "Outfit", "body": "DM Sans", "accent": "Fira Code"},
        "creative": {"heading": "Fraunces", "body": "Karla", "accent": "Abril Fatface"},
    }

    SPACING_SCALE = {
        "tight": 4,
        "base": 8,
        "loose": 16,
        "relaxed": 24,
        "section": 32,
        "double": 48,
        "triple": 64,
    }

    BORDER_RADIUS = {
        "none": 0,
        "small": 4,
        "medium": 8,
        "large": 16,
        "xl": 24,
        "full": 9999,
    }

    ANTI_AI_SLOP_PRESETS = {
        "yc_pitch": {
            "name": "YC/Sequoia Anti-AI",
            "description": "Clean, founder-led aesthetic - not startup generic",
            "colors": "default",
            "typography": "default",
            "border_radius": "medium",
            "shadows": {
                "subtle": "0 1px 2px rgba(0,0,0,0.05)",
                "card": "0 4px 6px rgba(0,0,0,0.07)",
            },
        },
        "series_a": {
            "name": "Series A Ready",
            "description": "Professional, data-driven, investor-ready",
            "colors": "consulting",
            "typography": "default",
            "border_radius": "small",
            "shadows": {
                "subtle": "0 1px 3px rgba(0,0,0,0.1)",
                "card": "0 4px 12px rgba(0,0,0,0.08)",
            },
        },
        "consulting": {
            "name": "Premium Consulting",
            "description": "McKinsey/BCG style - authoritative and clean",
            "colors": "consulting",
            "typography": "default",
            "border_radius": "none",
            "shadows": {
                "subtle": "0 1px 3px rgba(0,0,0,0.1)",
                "card": "0 4px 12px rgba(0,0,0,0.08)",
            },
        },
        "investor_update": {
            "name": "Investor Update",
            "description": "Data-first, clean metrics display",
            "colors": "investor_update",
            "typography": "default",
            "border_radius": "small",
            "shadows": {
                "subtle": "0 1px 2px rgba(0,0,0,0.05)",
                "card": "0 2px 8px rgba(0,0,0,0.06)",
            },
        },
        "sales": {
            "name": "Sales Deck",
            "description": "Persuasive, benefit-focused design",
            "colors": "sales",
            "typography": "hero",
            "border_radius": "large",
            "shadows": {
                "subtle": "0 2px 4px rgba(0,0,0,0.08)",
                "card": "0 8px 24px rgba(0,0,0,0.12)",
            },
        },
        "marketing": {
            "name": "Product Launch",
            "description": "Bold, premium product aesthetic",
            "colors": "marketing",
            "typography": "hero",
            "border_radius": "large",
            "shadows": {
                "subtle": "0 2px 8px rgba(0,0,0,0.08)",
                "card": "0 12px 32px rgba(0,0,0,0.12)",
            },
        },
        "dark_mode": {
            "name": "Dark Mode",
            "description": "Modern dark theme for tech presentations",
            "colors": "dark_mode",
            "typography": "default",
            "border_radius": "medium",
            "shadows": {
                "subtle": "0 1px 2px rgba(0,0,0,0.3)",
                "card": "0 4px 12px rgba(0,0,0,0.4)",
            },
        },
        "minimalist": {
            "name": "Minimalist",
            "description": "Less is more - clean and focused",
            "colors": "minimalist",
            "typography": "minimal",
            "border_radius": "none",
            "shadows": {"subtle": "none", "card": "none"},
        },
        "premium": {
            "name": "Premium/Luxury",
            "description": "Elegant, gold accents, sophisticated",
            "colors": "premium",
            "typography": "default",
            "border_radius": "medium",
            "shadows": {
                "subtle": "0 2px 8px rgba(212,175,55,0.1)",
                "card": "0 8px 24px rgba(212,175,55,0.15)",
            },
        },
        "tech_startup": {
            "name": "Tech Startup",
            "description": "Modern tech aesthetic with cyan accents",
            "colors": "tech",
            "typography": "default",
            "border_radius": "medium",
            "shadows": {
                "subtle": "0 1px 3px rgba(0,0,0,0.1)",
                "card": "0 4px 12px rgba(0,0,0,0.1)",
            },
        },
        "fintech": {
            "name": "Fintech",
            "description": "Trustworthy financial aesthetic",
            "colors": "fintech",
            "typography": "default",
            "border_radius": "small",
            "shadows": {
                "subtle": "0 1px 2px rgba(0,0,0,0.05)",
                "card": "0 4px 8px rgba(0,0,0,0.08)",
            },
        },
        "healthcare": {
            "name": "Healthcare",
            "description": "Clean, trustworthy medical aesthetic",
            "colors": "healthcare",
            "typography": "default",
            "border_radius": "medium",
            "shadows": {
                "subtle": "0 1px 3px rgba(0,0,0,0.08)",
                "card": "0 4px 12px rgba(0,0,0,0.1)",
            },
        },
    }

    def __init__(self, preset: str = "yc_pitch"):
        self.preset = preset
        self._load_preset()

    def _load_preset(self):
        preset_data = self.ANTI_AI_SLOP_PRESETS.get(
            self.preset, self.ANTI_AI_SLOP_PRESETS["yc_pitch"]
        )
        self.colors = self.COLOR_SCHEMES.get(
            preset_data["colors"], self.COLOR_SCHEMES["default"]
        )
        self.typography = self.TYPOGRAPHY_SCALES.get(
            preset_data["typography"], self.TYPOGRAPHY_SCALES["default"]
        )
        self.border_radius = preset_data.get("border_radius", "medium")
        self.shadows = preset_data.get("shadows", {})

    def get_color(self, key: str) -> str:
        return self.colors.get(key, "#000000")

    def get_typography(self, level: str) -> Dict[str, Any]:
        return self.typography.get(level, self.typography["body"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preset": self.preset,
            "colors": self.colors,
            "typography": self.typography,
            "border_radius": self.border_radius,
            "shadows": self.shadows,
            "fonts": self.FONT_PAIRS.get(self.preset, self.FONT_PAIRS["default"]),
            "spacing": self.SPACING_SCALE,
        }

    @classmethod
    def list_presets(cls) -> List[str]:
        return list(cls.ANTI_AI_SLOP_PRESETS.keys())

    @classmethod
    def list_color_schemes(cls) -> List[str]:
        return list(cls.COLOR_SCHEMES.keys())


def generate_design_system(preset: str = "yc_pitch") -> Dict[str, Any]:
    ds = DesignSystem(preset)
    return ds.to_dict()
