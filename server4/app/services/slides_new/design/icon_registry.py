"""
Icon Reference Registry — Phase 13 Integration.

Based on microsoft/fluentui-system-icons (10.5k stars):
- Maps slide content types to appropriate professional icon names
- Provides icon categories, variants (regular/filled/light), and sizing
- Used by Code Agent and Assembler Agent when generating HTML/React slides

The registry references Fluent UI naming conventions without bundling the icons
themselves — at render time, icons are referenced via CDN or SVG lookup.

This gives our slides professional Microsoft-grade iconography instead of
generic emoji or no icons at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════════
# ICON VARIANTS — Following Fluent UI conventions
# ═══════════════════════════════════════════════════════════════════════════════


class IconVariant(str, Enum):
    """Fluent UI icon variants."""
    REGULAR = "regular"
    FILLED = "filled"
    LIGHT = "light"
    COLOR = "color"


class IconSize(int, Enum):
    """Standard Fluent UI icon sizes."""
    SIZE_16 = 16
    SIZE_20 = 20
    SIZE_24 = 24
    SIZE_28 = 28
    SIZE_32 = 32
    SIZE_48 = 48


@dataclass
class IconRef:
    """Reference to a Fluent UI system icon."""
    name: str
    variant: IconVariant = IconVariant.REGULAR
    size: IconSize = IconSize.SIZE_24
    category: str = ""
    description: str = ""

    @property
    def fluent_name(self) -> str:
        """Full Fluent UI icon name."""
        return f"{self.name}_{self.size.value}_{self.variant.value}"

    @property
    def svg_path(self) -> str:
        """Path in the Fluent UI assets directory."""
        return f"assets/{self.name}/SVG/{self.fluent_name}.svg"

    @property
    def cdn_url(self) -> str:
        """CDN URL for the icon SVG (unpkg)."""
        return (
            f"https://unpkg.com/@fluentui/svg-icons/icons/"
            f"{self.fluent_name}.svg"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE-TYPE → ICON MAPPINGS
# Maps slide content types to recommended icons for professional presentations
# ═══════════════════════════════════════════════════════════════════════════════


# Icons for common pitch deck slide types
SLIDE_TYPE_ICONS: dict[str, list[IconRef]] = {
    "title-hero": [
        IconRef("rocket", description="Launch/startup energy"),
        IconRef("star", description="Excellence/featured"),
        IconRef("sparkle", description="Innovation/new"),
    ],
    "problem": [
        IconRef("warning", description="Alert/issue"),
        IconRef("flash", description="Pain point urgency"),
        IconRef("question_circle", description="Unknown/question"),
        IconRef("error_circle", description="Problem/error state"),
    ],
    "solution": [
        IconRef("lightbulb", description="Idea/insight"),
        IconRef("checkmark_circle", description="Solution/resolved"),
        IconRef("puzzle_piece", description="Fits together"),
        IconRef("wand", description="Magic/transformation"),
    ],
    "market": [
        IconRef("globe", description="Global market"),
        IconRef("people_community", description="Market segments"),
        IconRef("arrow_trending_lines", description="Market growth"),
        IconRef("chart_multiple", description="Market data"),
    ],
    "traction": [
        IconRef("arrow_trending_lines", description="Growth trajectory"),
        IconRef("trophy", description="Achievements"),
        IconRef("pulse", description="Activity/momentum"),
        IconRef("star_emphasis", description="Key metrics"),
    ],
    "team": [
        IconRef("people_team", description="Team overview"),
        IconRef("person", description="Individual member"),
        IconRef("person_board", description="Leadership"),
        IconRef("hat_graduation", description="Expertise"),
    ],
    "competition": [
        IconRef("grid", description="Comparison matrix"),
        IconRef("target_arrow", description="Competitive positioning"),
        IconRef("shield_checkmark", description="Advantage/moat"),
        IconRef("scales", description="Comparison"),
    ],
    "business-model": [
        IconRef("money", description="Revenue"),
        IconRef("building_bank", description="Business/finance"),
        IconRef("arrow_repeat_all", description="Recurring model"),
        IconRef("layer", description="Multi-tier pricing"),
    ],
    "financials": [
        IconRef("data_bar_vertical", description="Revenue chart"),
        IconRef("calculator", description="Financial calculation"),
        IconRef("wallet", description="Budget/costs"),
        IconRef("arrow_trending_lines", description="Projections"),
    ],
    "ask": [
        IconRef("handshake", description="Partnership/deal"),
        IconRef("money", description="Funding amount"),
        IconRef("calendar", description="Timeline"),
        IconRef("target", description="Goals"),
    ],
    "closing": [
        IconRef("mail", description="Contact"),
        IconRef("link", description="Website/links"),
        IconRef("call", description="Phone"),
        IconRef("heart", description="Thank you"),
    ],
}


# Icons for content element types (used inside slides)
CONTENT_ELEMENT_ICONS: dict[str, list[IconRef]] = {
    "feature": [
        IconRef("checkmark", description="Feature checkmark"),
        IconRef("star", description="Feature highlight"),
    ],
    "benefit": [
        IconRef("thumb_like", description="Positive benefit"),
        IconRef("arrow_up", description="Improvement"),
    ],
    "step": [
        IconRef("number_symbol", description="Step number"),
        IconRef("arrow_right", description="Next step"),
    ],
    "quote": [
        IconRef("text_quote", description="Quote/testimonial"),
        IconRef("chat", description="Customer voice"),
    ],
    "stat": [
        IconRef("data_usage", description="Statistic"),
        IconRef("pulse", description="Metric"),
    ],
    "timeline": [
        IconRef("timeline", description="Timeline track"),
        IconRef("calendar_clock", description="Schedule"),
    ],
    "comparison": [
        IconRef("arrow_swap", description="Compare items"),
        IconRef("scales", description="Weigh options"),
    ],
    "list": [
        IconRef("list", description="List items"),
        IconRef("checkbox_checked", description="Checklist"),
    ],
    "technology": [
        IconRef("code", description="Code/programming"),
        IconRef("server", description="Infrastructure"),
        IconRef("cloud", description="Cloud services"),
        IconRef("database", description="Data storage"),
    ],
    "security": [
        IconRef("shield_checkmark", description="Security verified"),
        IconRef("lock_closed", description="Encrypted/secure"),
        IconRef("key", description="Authentication"),
    ],
    "growth": [
        IconRef("arrow_trending_lines", description="Growth chart"),
        IconRef("rocket", description="Rapid growth"),
        IconRef("leaf", description="Organic growth"),
    ],
    "communication": [
        IconRef("mail", description="Email"),
        IconRef("chat", description="Messaging"),
        IconRef("megaphone", description="Announcements"),
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# INDUSTRY-SPECIFIC ICON SETS
# ═══════════════════════════════════════════════════════════════════════════════


INDUSTRY_ICONS: dict[str, list[IconRef]] = {
    "fintech": [
        IconRef("building_bank", description="Banking"),
        IconRef("money", description="Finance"),
        IconRef("credit_card_person", description="Payments"),
        IconRef("lock_closed", description="Security"),
    ],
    "healthtech": [
        IconRef("heart_pulse", description="Health monitoring"),
        IconRef("stethoscope", description="Medical"),
        IconRef("pill", description="Medication"),
        IconRef("person_heart", description="Patient care"),
    ],
    "edtech": [
        IconRef("hat_graduation", description="Education"),
        IconRef("book_open", description="Learning"),
        IconRef("board", description="Teaching"),
        IconRef("certificate", description="Certification"),
    ],
    "saas": [
        IconRef("cloud", description="Cloud service"),
        IconRef("apps", description="Application"),
        IconRef("server", description="Infrastructure"),
        IconRef("people_team", description="Collaboration"),
    ],
    "ecommerce": [
        IconRef("cart", description="Shopping"),
        IconRef("box", description="Delivery/product"),
        IconRef("tag", description="Pricing/offers"),
        IconRef("store", description="Storefront"),
    ],
    "ai_ml": [
        IconRef("brain_circuit", description="AI/Neural networks"),
        IconRef("bot", description="Chatbot/agent"),
        IconRef("data_scatter", description="Data analysis"),
        IconRef("sparkle", description="AI magic"),
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# ICON SELECTION API
# ═══════════════════════════════════════════════════════════════════════════════


def get_icons_for_slide(
    slide_type: str,
    variant: IconVariant = IconVariant.REGULAR,
    size: IconSize = IconSize.SIZE_24,
    max_icons: int = 3,
) -> list[IconRef]:
    """Get recommended icons for a slide type."""
    icons = SLIDE_TYPE_ICONS.get(slide_type, [])
    result = []
    for icon in icons[:max_icons]:
        result.append(IconRef(
            name=icon.name,
            variant=variant,
            size=size,
            category=slide_type,
            description=icon.description,
        ))
    return result


def get_icons_for_content(
    element_type: str,
    variant: IconVariant = IconVariant.REGULAR,
    size: IconSize = IconSize.SIZE_20,
    max_icons: int = 2,
) -> list[IconRef]:
    """Get recommended icons for a content element type."""
    icons = CONTENT_ELEMENT_ICONS.get(element_type, [])
    result = []
    for icon in icons[:max_icons]:
        result.append(IconRef(
            name=icon.name,
            variant=variant,
            size=size,
            category=element_type,
            description=icon.description,
        ))
    return result


def get_icons_for_industry(
    industry: str,
    variant: IconVariant = IconVariant.REGULAR,
    size: IconSize = IconSize.SIZE_24,
) -> list[IconRef]:
    """Get industry-specific icons."""
    # Normalize industry name
    normalized = industry.lower().replace(" ", "_").replace("-", "_")

    # Try direct match first, then fuzzy
    icons = INDUSTRY_ICONS.get(normalized, [])
    if not icons:
        for key in INDUSTRY_ICONS:
            if key in normalized or normalized in key:
                icons = INDUSTRY_ICONS[key]
                break

    return [
        IconRef(
            name=icon.name,
            variant=variant,
            size=size,
            category=f"industry:{normalized}",
            description=icon.description,
        )
        for icon in icons
    ]


def suggest_icon_variant(formality_level: float) -> IconVariant:
    """
    Suggest icon variant based on formality level.
    From style_transfer module integration.
    """
    if formality_level >= 0.8:
        return IconVariant.LIGHT      # Elegant, understated for formal
    elif formality_level >= 0.5:
        return IconVariant.REGULAR    # Balanced for standard
    return IconVariant.FILLED         # Bold, casual for informal


def get_all_icon_names() -> list[str]:
    """Get all unique icon names in the registry."""
    names: set[str] = set()
    for icons in SLIDE_TYPE_ICONS.values():
        for icon in icons:
            names.add(icon.name)
    for icons in CONTENT_ELEMENT_ICONS.values():
        for icon in icons:
            names.add(icon.name)
    for icons in INDUSTRY_ICONS.values():
        for icon in icons:
            names.add(icon.name)
    return sorted(names)
