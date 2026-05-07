"""
Theme Models - Phase 4.

24 built-in themes (8 dark + 8 light + 8 specialty), theme mutations,
and the generative theme data structures. Each theme defines colors,
typography, spacing, and reveal.js CSS variable overrides.

Based on the V7 plan Section 11 (Theme Engine 100+ Themes) and the
frontend-slides anti-AI-slop design philosophy.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ThemeTier(str, Enum):
    BUILT_IN = "built-in"
    GENERATED = "generated"
    MUTATION = "mutation"
    COMMUNITY = "community"


class ThemeMutation(str, Enum):
    WARMER = "warmer"
    COOLER = "cooler"
    HIGHER_CONTRAST = "higher-contrast"
    MORE_SATURATED = "more-saturated"
    DESATURATED = "desaturated"


@dataclass
class ThemeColors:
    """Color palette for a theme."""
    background: str
    surface: str
    primary: str
    secondary: str
    accent: str
    text: str
    text_muted: str
    heading: str
    link: str
    code_bg: str
    success: str = "#10B981"
    warning: str = "#F59E0B"
    error: str = "#EF4444"


@dataclass
class ThemeTypography:
    """Typography configuration."""
    heading_font: str
    body_font: str
    mono_font: str = "JetBrains Mono"
    heading_weight: int = 700
    body_weight: int = 400
    base_size: int = 42
    heading_letter_spacing: str = "-0.02em"
    heading_line_height: float = 1.1
    body_line_height: float = 1.6


@dataclass
class ThemeSpacing:
    """Spacing scale."""
    slide_padding: str = "2rem 3rem"
    section_gap: str = "2rem"
    element_gap: str = "1rem"
    card_padding: str = "1.5rem"
    card_radius: str = "8px"


@dataclass
class ThemeDefinition:
    """Complete theme definition for a presentation."""
    id: str
    name: str
    variant: str  # dark, light, specialty
    tier: ThemeTier = ThemeTier.BUILT_IN
    colors: ThemeColors = field(default_factory=lambda: ThemeColors(
        background="#0F172A", surface="#1E293B", primary="#F8FAFC",
        secondary="#E2E8F0", accent="#38BDF8", text="#E2E8F0",
        text_muted="#94A3B8", heading="#F8FAFC", link="#38BDF8",
        code_bg="#0D1117",
    ))
    typography: ThemeTypography = field(default_factory=lambda: ThemeTypography(
        heading_font="Inter", body_font="Inter",
    ))
    spacing: ThemeSpacing = field(default_factory=ThemeSpacing)
    preset: str = ""
    character: str = ""
    shadows: dict[str, str] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "variant": self.variant,
            "tier": self.tier.value,
            "colors": self.colors.__dict__,
            "typography": self.typography.__dict__,
            "spacing": self.spacing.__dict__,
            "preset": self.preset,
            "character": self.character,
            "shadows": self.shadows,
            "extras": self.extras,
        }


class BuiltInThemes:
    """
    Repository of 24 hand-crafted themes.

    Organization:
    - 8 Dark themes: high-energy, tech, developer, etc.
    - 8 Light themes: minimal, corporate, pastel, etc.
    - 8 Specialty themes: terminal, editorial, blueprint, etc.

    Each theme is anti-AI-slop certified: no generic gradients,
    intentional typography, purposeful spacing.
    """

    # ================================================================ #
    #  DARK THEMES (1-8)                                               #
    # ================================================================ #

    BOLD_SIGNAL = ThemeDefinition(
        id="bold-signal",
        name="Bold Signal",
        variant="dark",
        preset="bold-signal",
        character="High contrast, dynamic, startup energy",
        colors=ThemeColors(
            background="#0F0A1A",
            surface="#1A1128",
            primary="#FF6B35",
            secondary="#004E98",
            accent="#FF6B35",
            text="#F0E6FF",
            text_muted="#9B8CB8",
            heading="#FFFFFF",
            link="#FF6B35",
            code_bg="#0D0816",
        ),
        typography=ThemeTypography(
            heading_font="DM Sans",
            body_font="Inter",
            heading_weight=800,
            heading_letter_spacing="-0.03em",
        ),
        shadows={
            "subtle": "0 2px 8px rgba(255,107,53,0.15)",
            "card": "0 8px 24px rgba(255,107,53,0.2)",
        },
    )

    ELECTRIC_STUDIO = ThemeDefinition(
        id="electric-studio",
        name="Electric Studio",
        variant="dark",
        preset="electric-studio",
        character="Futuristic, neon accents, tech",
        colors=ThemeColors(
            background="#0A0A1B",
            surface="#12122B",
            primary="#7B2FF7",
            secondary="#00F5FF",
            accent="#00F5FF",
            text="#E0E0FF",
            text_muted="#8888BB",
            heading="#FFFFFF",
            link="#00F5FF",
            code_bg="#080818",
        ),
        typography=ThemeTypography(
            heading_font="Outfit",
            body_font="DM Sans",
            heading_weight=700,
        ),
        shadows={
            "subtle": "0 2px 12px rgba(0,245,255,0.1)",
            "card": "0 8px 32px rgba(123,47,247,0.2)",
        },
    )

    DARK_DEVELOPER = ThemeDefinition(
        id="dark-developer",
        name="Dark Developer",
        variant="dark",
        preset="dark-developer",
        character="Developer tools, code-first",
        colors=ThemeColors(
            background="#0F172A",
            surface="#1E293B",
            primary="#38BDF8",
            secondary="#FBBF24",
            accent="#38BDF8",
            text="#E2E8F0",
            text_muted="#94A3B8",
            heading="#F8FAFC",
            link="#38BDF8",
            code_bg="#0D1117",
        ),
        typography=ThemeTypography(
            heading_font="Inter",
            body_font="Inter",
            mono_font="Fira Code",
        ),
        shadows={
            "subtle": "0 1px 4px rgba(0,0,0,0.3)",
            "card": "0 4px 16px rgba(0,0,0,0.4)",
        },
    )

    DARK_BOTANICAL = ThemeDefinition(
        id="dark-botanical",
        name="Dark Botanical",
        variant="dark",
        preset="dark-botanical",
        character="Organic shapes, natural",
        colors=ThemeColors(
            background="#041C14",
            surface="#0A2E20",
            primary="#34D399",
            secondary="#064E3B",
            accent="#34D399",
            text="#D1FAE5",
            text_muted="#6EE7B7",
            heading="#ECFDF5",
            link="#34D399",
            code_bg="#021A10",
        ),
        typography=ThemeTypography(
            heading_font="Sora",
            body_font="Inter",
        ),
        shadows={
            "subtle": "0 2px 8px rgba(52,211,153,0.1)",
            "card": "0 8px 24px rgba(6,78,59,0.3)",
        },
    )

    NEON_CYBER = ThemeDefinition(
        id="neon-cyber",
        name="Neon Cyber",
        variant="dark",
        preset="neon-cyber",
        character="Cyberpunk, gaming, high energy",
        colors=ThemeColors(
            background="#0A0A0A",
            surface="#1A1A2E",
            primary="#FF00FF",
            secondary="#00FFFF",
            accent="#FF00FF",
            text="#E0E0E0",
            text_muted="#888888",
            heading="#FFFFFF",
            link="#00FFFF",
            code_bg="#0D0D1A",
        ),
        typography=ThemeTypography(
            heading_font="Orbitron",
            body_font="Rajdhani",
            heading_weight=900,
            heading_letter_spacing="0.05em",
        ),
        shadows={
            "subtle": "0 0 12px rgba(255,0,255,0.3)",
            "card": "0 0 24px rgba(0,255,255,0.2)",
        },
    )

    CREATIVE_VOLTAGE = ThemeDefinition(
        id="creative-voltage",
        name="Creative Voltage",
        variant="dark",
        preset="creative-voltage",
        character="Creative, energetic, bold",
        colors=ThemeColors(
            background="#1A0A1E",
            surface="#2A1A2E",
            primary="#F59E0B",
            secondary="#8B5CF6",
            accent="#F59E0B",
            text="#F0E6FF",
            text_muted="#A78BFA",
            heading="#FFFFFF",
            link="#F59E0B",
            code_bg="#120818",
        ),
        typography=ThemeTypography(
            heading_font="Cabinet Grotesk",
            body_font="Satoshi",
            heading_weight=800,
        ),
        shadows={
            "subtle": "0 2px 8px rgba(245,158,11,0.15)",
            "card": "0 8px 24px rgba(139,92,246,0.2)",
        },
    )

    MIDNIGHT_OCEAN = ThemeDefinition(
        id="midnight-ocean",
        name="Midnight Ocean",
        variant="dark",
        preset="midnight-ocean",
        character="Deep, calm, professional",
        colors=ThemeColors(
            background="#0C1929",
            surface="#132740",
            primary="#06B6D4",
            secondary="#0C4A6E",
            accent="#06B6D4",
            text="#CBD5E1",
            text_muted="#64748B",
            heading="#E2E8F0",
            link="#06B6D4",
            code_bg="#091420",
        ),
        typography=ThemeTypography(
            heading_font="Sora",
            body_font="Source Sans Pro",
        ),
        shadows={
            "subtle": "0 2px 8px rgba(6,182,212,0.1)",
            "card": "0 8px 24px rgba(12,74,110,0.3)",
        },
    )

    CARBON_FIBER = ThemeDefinition(
        id="carbon-fiber",
        name="Carbon Fiber",
        variant="dark",
        preset="carbon-fiber",
        character="Industrial, sleek, aggressive",
        colors=ThemeColors(
            background="#0A0A0A",
            surface="#18181B",
            primary="#EF4444",
            secondary="#27272A",
            accent="#EF4444",
            text="#D4D4D8",
            text_muted="#71717A",
            heading="#FAFAFA",
            link="#EF4444",
            code_bg="#09090B",
        ),
        typography=ThemeTypography(
            heading_font="Clash Display",
            body_font="Inter",
            heading_weight=800,
            heading_letter_spacing="-0.03em",
        ),
        shadows={
            "subtle": "0 1px 4px rgba(0,0,0,0.5)",
            "card": "0 4px 16px rgba(239,68,68,0.15)",
        },
    )

    # ================================================================ #
    #  LIGHT THEMES (9-16)                                             #
    # ================================================================ #

    SWISS_MODERN = ThemeDefinition(
        id="swiss-modern",
        name="Swiss Modern",
        variant="light",
        preset="swiss-modern",
        character="Minimal, grid, Helvetica",
        colors=ThemeColors(
            background="#FFFFFF",
            surface="#F5F5F5",
            primary="#1A1A1A",
            secondary="#FF0000",
            accent="#FF0000",
            text="#1A1A1A",
            text_muted="#6B6B6B",
            heading="#000000",
            link="#FF0000",
            code_bg="#F0F0F0",
        ),
        typography=ThemeTypography(
            heading_font="Helvetica Neue",
            body_font="Helvetica Neue",
            heading_weight=700,
            heading_letter_spacing="0",
        ),
        spacing=ThemeSpacing(card_radius="0"),
        shadows={"subtle": "none", "card": "none"},
    )

    NOTEBOOK_TABS = ThemeDefinition(
        id="notebook-tabs",
        name="Notebook Tabs",
        variant="light",
        preset="notebook-tabs",
        character="Organized, tabbed, clean",
        colors=ThemeColors(
            background="#FAFAF5",
            surface="#F5F5DC",
            primary="#2563EB",
            secondary="#1E40AF",
            accent="#2563EB",
            text="#1E293B",
            text_muted="#64748B",
            heading="#0F172A",
            link="#2563EB",
            code_bg="#F1F5F9",
        ),
        typography=ThemeTypography(
            heading_font="Sora",
            body_font="Inter",
        ),
        shadows={
            "subtle": "0 1px 3px rgba(0,0,0,0.08)",
            "card": "0 4px 12px rgba(0,0,0,0.1)",
        },
    )

    PASTEL_GEOMETRY = ThemeDefinition(
        id="pastel-geometry",
        name="Pastel Geometry",
        variant="light",
        preset="pastel-geometry",
        character="Soft, approachable, shapes",
        colors=ThemeColors(
            background="#FFF5F5",
            surface="#FDE8E8",
            primary="#7C3AED",
            secondary="#DB2777",
            accent="#7C3AED",
            text="#374151",
            text_muted="#6B7280",
            heading="#1F2937",
            link="#7C3AED",
            code_bg="#F5F3FF",
        ),
        typography=ThemeTypography(
            heading_font="DM Sans",
            body_font="Inter",
            heading_weight=700,
        ),
        spacing=ThemeSpacing(card_radius="16px"),
        shadows={
            "subtle": "0 2px 8px rgba(124,58,237,0.1)",
            "card": "0 8px 24px rgba(124,58,237,0.12)",
        },
    )

    SPLIT_PASTEL = ThemeDefinition(
        id="split-pastel",
        name="Split Pastel",
        variant="light",
        preset="split-pastel",
        character="Dual-tone, modern, fresh",
        colors=ThemeColors(
            background="#F0F4FF",
            surface="#DBEAFE",
            primary="#6366F1",
            secondary="#F0ABFC",
            accent="#F0ABFC",
            text="#334155",
            text_muted="#64748B",
            heading="#1E293B",
            link="#6366F1",
            code_bg="#EEF2FF",
        ),
        typography=ThemeTypography(
            heading_font="Outfit",
            body_font="DM Sans",
        ),
        spacing=ThemeSpacing(card_radius="12px"),
        shadows={
            "subtle": "0 2px 8px rgba(99,102,241,0.08)",
            "card": "0 8px 24px rgba(99,102,241,0.12)",
        },
    )

    VINTAGE_EDITORIAL = ThemeDefinition(
        id="vintage-editorial",
        name="Vintage Editorial",
        variant="light",
        preset="vintage-editorial",
        character="Classic, editorial, serif",
        colors=ThemeColors(
            background="#FFF8E7",
            surface="#FEF3C7",
            primary="#B45309",
            secondary="#92400E",
            accent="#B45309",
            text="#292524",
            text_muted="#78716C",
            heading="#1C1917",
            link="#B45309",
            code_bg="#FFFBEB",
        ),
        typography=ThemeTypography(
            heading_font="Playfair Display",
            body_font="Source Serif Pro",
            heading_weight=700,
            heading_letter_spacing="0",
            heading_line_height=1.2,
        ),
        shadows={
            "subtle": "0 1px 3px rgba(180,83,9,0.1)",
            "card": "0 4px 12px rgba(180,83,9,0.12)",
        },
    )

    CLEAN_CORPORATE = ThemeDefinition(
        id="clean-corporate",
        name="Clean Corporate",
        variant="light",
        preset="clean-corporate",
        character="Enterprise, trustworthy",
        colors=ThemeColors(
            background="#F8FAFC",
            surface="#F1F5F9",
            primary="#0078D4",
            secondary="#1E40AF",
            accent="#0078D4",
            text="#1E293B",
            text_muted="#64748B",
            heading="#0F172A",
            link="#0078D4",
            code_bg="#F1F5F9",
        ),
        typography=ThemeTypography(
            heading_font="Inter",
            body_font="Inter",
            heading_weight=700,
        ),
        spacing=ThemeSpacing(card_radius="4px"),
        shadows={
            "subtle": "0 1px 3px rgba(0,0,0,0.1)",
            "card": "0 4px 12px rgba(0,0,0,0.08)",
        },
    )

    WARM_PAPER = ThemeDefinition(
        id="warm-paper",
        name="Warm Paper",
        variant="light",
        preset="warm-paper",
        character="Warm, inviting, paper texture",
        colors=ThemeColors(
            background="#FFFBEB",
            surface="#FEF3C7",
            primary="#D97706",
            secondary="#92400E",
            accent="#D97706",
            text="#292524",
            text_muted="#78716C",
            heading="#1C1917",
            link="#D97706",
            code_bg="#FFF7ED",
        ),
        typography=ThemeTypography(
            heading_font="Cormorant Garamond",
            body_font="Proza Libre",
        ),
        shadows={
            "subtle": "0 1px 4px rgba(217,119,6,0.1)",
            "card": "0 4px 16px rgba(217,119,6,0.12)",
        },
    )

    FRESH_GREEN = ThemeDefinition(
        id="fresh-green",
        name="Fresh Green",
        variant="light",
        preset="fresh-green",
        character="Growth, sustainability",
        colors=ThemeColors(
            background="#F0FDF4",
            surface="#DCFCE7",
            primary="#16A34A",
            secondary="#166534",
            accent="#16A34A",
            text="#1E293B",
            text_muted="#64748B",
            heading="#14532D",
            link="#16A34A",
            code_bg="#F0FDF4",
        ),
        typography=ThemeTypography(
            heading_font="DM Sans",
            body_font="Inter",
        ),
        shadows={
            "subtle": "0 1px 3px rgba(22,163,74,0.1)",
            "card": "0 4px 12px rgba(22,163,74,0.12)",
        },
    )

    # ================================================================ #
    #  SPECIALTY THEMES (17-24)                                        #
    # ================================================================ #

    TERMINAL_GREEN = ThemeDefinition(
        id="terminal-green",
        name="Terminal Green",
        variant="specialty",
        preset="terminal-green",
        character="Hacker, monospace, phosphor",
        colors=ThemeColors(
            background="#0D1117",
            surface="#161B22",
            primary="#00FF00",
            secondary="#006600",
            accent="#00FF00",
            text="#00CC00",
            text_muted="#338833",
            heading="#00FF00",
            link="#00FF00",
            code_bg="#0D1117",
        ),
        typography=ThemeTypography(
            heading_font="JetBrains Mono",
            body_font="JetBrains Mono",
            mono_font="JetBrains Mono",
            heading_weight=700,
            heading_letter_spacing="0.02em",
        ),
        shadows={
            "subtle": "0 0 8px rgba(0,255,0,0.15)",
            "card": "0 0 20px rgba(0,255,0,0.1)",
        },
        extras={"scanlines": True, "cursor_blink": True},
    )

    PAPER_AND_INK = ThemeDefinition(
        id="paper-and-ink",
        name="Paper & Ink",
        variant="specialty",
        preset="paper-and-ink",
        character="Editorial, print, ink texture",
        colors=ThemeColors(
            background="#FAF9F6",
            surface="#F0EDE8",
            primary="#1A1A1A",
            secondary="#333333",
            accent="#1A1A1A",
            text="#1A1A1A",
            text_muted="#666666",
            heading="#000000",
            link="#1A1A1A",
            code_bg="#EEECE7",
        ),
        typography=ThemeTypography(
            heading_font="Fraunces",
            body_font="Literata",
            heading_weight=700,
            heading_line_height=1.15,
        ),
        shadows={"subtle": "none", "card": "0 1px 3px rgba(0,0,0,0.1)"},
    )

    BLUEPRINT = ThemeDefinition(
        id="blueprint",
        name="Blueprint",
        variant="specialty",
        preset="blueprint",
        character="Technical, engineering, grid",
        colors=ThemeColors(
            background="#1E3A5F",
            surface="#253F66",
            primary="#FFFFFF",
            secondary="#87CEEB",
            accent="#FFFFFF",
            text="#D0E0F0",
            text_muted="#8AAFC8",
            heading="#FFFFFF",
            link="#87CEEB",
            code_bg="#162D4D",
        ),
        typography=ThemeTypography(
            heading_font="Source Code Pro",
            body_font="Inter",
            heading_weight=600,
        ),
        shadows={
            "subtle": "0 1px 4px rgba(0,0,0,0.3)",
            "card": "0 4px 16px rgba(0,0,0,0.2)",
        },
        extras={"grid_overlay": True},
    )

    RETRO_PIXEL = ThemeDefinition(
        id="retro-pixel",
        name="Retro Pixel",
        variant="specialty",
        preset="retro-pixel",
        character="Retro, pixelated, gaming",
        colors=ThemeColors(
            background="#2B2D42",
            surface="#3D3F5C",
            primary="#EF476F",
            secondary="#FFD166",
            accent="#EF476F",
            text="#EDF2F4",
            text_muted="#8D99AE",
            heading="#FFFFFF",
            link="#06D6A0",
            code_bg="#1E1F33",
        ),
        typography=ThemeTypography(
            heading_font="Press Start 2P",
            body_font="VT323",
            heading_weight=400,
            base_size=36,
            heading_letter_spacing="0.05em",
        ),
        shadows={
            "subtle": "4px 4px 0px rgba(0,0,0,0.3)",
            "card": "6px 6px 0px rgba(0,0,0,0.4)",
        },
    )

    GLASSMORPHISM = ThemeDefinition(
        id="glassmorphism",
        name="Glassmorphism",
        variant="specialty",
        preset="glassmorphism",
        character="Frosted glass, depth, blur",
        colors=ThemeColors(
            background="#0F172A",
            surface="rgba(255,255,255,0.08)",
            primary="#818CF8",
            secondary="#C084FC",
            accent="#818CF8",
            text="#E2E8F0",
            text_muted="#94A3B8",
            heading="#FFFFFF",
            link="#818CF8",
            code_bg="rgba(0,0,0,0.3)",
        ),
        typography=ThemeTypography(
            heading_font="Inter",
            body_font="Inter",
        ),
        spacing=ThemeSpacing(card_radius="16px"),
        shadows={
            "subtle": "0 2px 16px rgba(0,0,0,0.2)",
            "card": "0 8px 32px rgba(0,0,0,0.3)",
        },
        extras={"backdrop_blur": "12px", "border_glass": "1px solid rgba(255,255,255,0.1)"},
    )

    GRADIENT_MESH = ThemeDefinition(
        id="gradient-mesh",
        name="Gradient Mesh",
        variant="specialty",
        preset="gradient-mesh",
        character="Flowing gradients, organic",
        colors=ThemeColors(
            background="#1A1035",
            surface="#251A45",
            primary="#667EEA",
            secondary="#764BA2",
            accent="#667EEA",
            text="#E0D6FF",
            text_muted="#9B8FBF",
            heading="#FFFFFF",
            link="#667EEA",
            code_bg="#140D2A",
        ),
        typography=ThemeTypography(
            heading_font="Outfit",
            body_font="DM Sans",
        ),
        shadows={
            "subtle": "0 4px 16px rgba(102,126,234,0.15)",
            "card": "0 8px 32px rgba(118,75,162,0.2)",
        },
        extras={"mesh_gradient": True},
    )

    MONOCHROME = ThemeDefinition(
        id="monochrome",
        name="Monochrome",
        variant="specialty",
        preset="monochrome",
        character="B&W, photography, stark",
        colors=ThemeColors(
            background="#FFFFFF",
            surface="#F5F5F5",
            primary="#000000",
            secondary="#333333",
            accent="#000000",
            text="#1A1A1A",
            text_muted="#666666",
            heading="#000000",
            link="#000000",
            code_bg="#F0F0F0",
        ),
        typography=ThemeTypography(
            heading_font="DM Sans",
            body_font="DM Sans",
            heading_weight=800,
        ),
        shadows={"subtle": "none", "card": "0 2px 8px rgba(0,0,0,0.1)"},
    )

    WARM_GRADIENT = ThemeDefinition(
        id="warm-gradient",
        name="Warm Gradient",
        variant="specialty",
        preset="warm-gradient",
        character="Warm, sunset, energy",
        colors=ThemeColors(
            background="#1A0A0F",
            surface="#2A1520",
            primary="#FF512F",
            secondary="#DD2476",
            accent="#FDE68A",
            text="#FFE4E6",
            text_muted="#FB7185",
            heading="#FFFFFF",
            link="#FDE68A",
            code_bg="#150810",
        ),
        typography=ThemeTypography(
            heading_font="Cabinet Grotesk",
            body_font="Inter",
            heading_weight=800,
        ),
        shadows={
            "subtle": "0 4px 16px rgba(255,81,47,0.15)",
            "card": "0 8px 32px rgba(221,36,118,0.2)",
        },
        extras={"warm_gradient_bg": "linear-gradient(135deg, #FF512F 0%, #DD2476 100%)"},
    )

    # ================================================================ #
    #  THEME REGISTRY                                                  #
    # ================================================================ #

    _ALL_THEMES: dict[str, ThemeDefinition] | None = None

    @classmethod
    def _build_registry(cls) -> dict[str, ThemeDefinition]:
        """Lazily build the theme registry from class attributes."""
        if cls._ALL_THEMES is not None:
            return cls._ALL_THEMES
        registry: dict[str, ThemeDefinition] = {}
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if isinstance(attr, ThemeDefinition):
                registry[attr.id] = attr
        cls._ALL_THEMES = registry
        return registry

    @classmethod
    def get(cls, theme_id: str) -> Optional[ThemeDefinition]:
        """Get a theme by ID, returns None if not found."""
        return cls._build_registry().get(theme_id)

    @classmethod
    def get_or_default(cls, theme_id: str) -> ThemeDefinition:
        """Get a theme by ID, falling back to dark-developer."""
        return cls._build_registry().get(theme_id, cls.DARK_DEVELOPER)

    @classmethod
    def list_all(cls) -> list[ThemeDefinition]:
        """Return all 24 built-in themes."""
        return list(cls._build_registry().values())

    @classmethod
    def list_by_variant(cls, variant: str) -> list[ThemeDefinition]:
        """Return themes filtered by variant (dark/light/specialty)."""
        return [t for t in cls.list_all() if t.variant == variant]

    @classmethod
    def list_ids(cls) -> list[str]:
        """Return all theme IDs."""
        return list(cls._build_registry().keys())

    @classmethod
    def count(cls) -> int:
        return len(cls._build_registry())

    @classmethod
    def get_fonts(cls) -> set[str]:
        """Collect all unique fonts across all themes for preloading."""
        fonts: set[str] = set()
        for theme in cls.list_all():
            fonts.add(theme.typography.heading_font)
            fonts.add(theme.typography.body_font)
            fonts.add(theme.typography.mono_font)
        return fonts
