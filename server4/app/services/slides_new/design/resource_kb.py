"""
Design Resource Knowledge Base -- Phase 13 Integration.

Curated from:
- bradtraversy/design-resources-for-developers (65.2k stars)
- goabstract/Awesome-Design-Tools (39.5k stars)

Provides categorized design resource URLs that our DesignerAgent and
design intelligence modules can reference when generating color palettes,
selecting fonts, finding icons, and choosing illustration styles.

NOT a runtime dependency -- this is a knowledge base that informs design decisions.
Agents can reference these tools/APIs when they need external design intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DesignResource:
    """A single design resource reference."""
    name: str
    url: str
    category: str
    description: str
    free: bool = True
    api_available: bool = False
    tags: list[str] = field(default_factory=list)


# =========================================================================
# CURATED RESOURCES — Each category has ~5-8 best-in-class tools
# Selected for relevance to AI-generated presentation design
# =========================================================================


COLOR_RESOURCES: list[DesignResource] = [
    DesignResource(
        name="Coolors",
        url="https://coolors.co",
        category="color",
        description="Fast color scheme generator with export options",
        api_available=True,
        tags=["palette", "generator", "export"],
    ),
    DesignResource(
        name="Adobe Color",
        url="https://color.adobe.com",
        category="color",
        description="Create color palettes and extract from images",
        tags=["palette", "extract", "harmony"],
    ),
    DesignResource(
        name="Huemint",
        url="https://huemint.com",
        category="color",
        description="ML-powered color scheme generation for brands and UIs",
        api_available=True,
        tags=["ai", "brand", "generator"],
    ),
    DesignResource(
        name="Colorlab",
        url="https://colorlab.dev",
        category="color",
        description="Create palettes, gradients, color scales, check contrast",
        tags=["palette", "gradient", "contrast", "a11y"],
    ),
    DesignResource(
        name="UI Colors",
        url="https://uicolors.app",
        category="color",
        description="Tailwind CSS color palette generator",
        tags=["tailwind", "palette", "generator"],
    ),
    DesignResource(
        name="Leonardo",
        url="https://leonardocolor.io",
        category="color",
        description="Generate WCAG-accessible color palettes (by Adobe)",
        free=True,
        tags=["a11y", "wcag", "accessible", "palette"],
    ),
]


GRADIENT_RESOURCES: list[DesignResource] = [
    DesignResource(
        name="WebGradients",
        url="https://webgradients.com",
        category="gradient",
        description="180 linear gradients with CSS export",
        tags=["linear", "css", "collection"],
    ),
    DesignResource(
        name="Mesh Gradient",
        url="https://meshgradient.in",
        category="gradient",
        description="Generate mesh gradients for backgrounds",
        tags=["mesh", "background", "generator"],
    ),
    DesignResource(
        name="CoolHue 2.0",
        url="https://webkul.github.io/coolhue",
        category="gradient",
        description="Handpicked gradient palette with CSS/PNG export",
        tags=["curated", "css", "png"],
    ),
    DesignResource(
        name="Gradient Hunt",
        url="https://gradienthunt.com",
        category="gradient",
        description="Thousands of hand-picked color gradients",
        tags=["curated", "community"],
    ),
]


FONT_RESOURCES: list[DesignResource] = [
    DesignResource(
        name="Google Fonts",
        url="https://fonts.google.com",
        category="font",
        description="Open source font library with web embedding",
        api_available=True,
        tags=["free", "web", "api", "embed"],
    ),
    DesignResource(
        name="Fontjoy",
        url="https://fontjoy.com",
        category="font",
        description="AI font pairing generator",
        tags=["ai", "pairing", "generator"],
    ),
    DesignResource(
        name="FontPair",
        url="https://fontpair.co",
        category="font",
        description="Google Fonts pairing suggestions",
        tags=["pairing", "google-fonts"],
    ),
    DesignResource(
        name="Typewolf",
        url="https://www.typewolf.com",
        category="font",
        description="Expert font recommendations and trending typefaces",
        tags=["curated", "trending", "expert"],
    ),
    DesignResource(
        name="Fontsource",
        url="https://fontsource.org",
        category="font",
        description="Self-host open source fonts as NPM packages",
        tags=["npm", "self-host", "open-source"],
    ),
]


ICON_RESOURCES: list[DesignResource] = [
    DesignResource(
        name="Fluent UI System Icons",
        url="https://github.com/microsoft/fluentui-system-icons",
        category="icon",
        description="Microsoft's comprehensive icon library with Regular, Filled, Light, Color variants",
        tags=["microsoft", "svg", "multi-variant", "professional"],
    ),
    DesignResource(
        name="Lucide Icons",
        url="https://lucide.dev",
        category="icon",
        description="Beautiful open-source icons (Feather Icons fork)",
        api_available=True,
        tags=["open-source", "svg", "react", "consistent"],
    ),
    DesignResource(
        name="Phosphor Icons",
        url="https://phosphoricons.com",
        category="icon",
        description="Flexible icon family with 6 weights",
        tags=["weights", "flexible", "react", "vue"],
    ),
    DesignResource(
        name="Heroicons",
        url="https://heroicons.com",
        category="icon",
        description="Beautiful hand-crafted SVG icons by Tailwind creators",
        tags=["tailwind", "svg", "outline", "solid"],
    ),
    DesignResource(
        name="Tabler Icons",
        url="https://tabler.io/icons",
        category="icon",
        description="3500+ highly customizable open source SVG icons",
        tags=["customizable", "svg", "large-set"],
    ),
]


ILLUSTRATION_RESOURCES: list[DesignResource] = [
    DesignResource(
        name="unDraw",
        url="https://undraw.co",
        category="illustration",
        description="Open-source SVG illustrations (customizable colors)",
        tags=["svg", "customizable", "free", "tech"],
    ),
    DesignResource(
        name="Humaaans",
        url="https://humaaans.com",
        category="illustration",
        description="Mix-and-match people illustrations",
        tags=["people", "modular", "team-slides"],
    ),
    DesignResource(
        name="Open Doodles",
        url="https://opendoodles.com",
        category="illustration",
        description="Free sketchy illustrations (CC0 license)",
        tags=["sketch", "hand-drawn", "cc0"],
    ),
    DesignResource(
        name="DrawKit",
        url="https://drawkit.io",
        category="illustration",
        description="Illustrations for startups and designers",
        tags=["startup", "professional", "vector"],
    ),
    DesignResource(
        name="Blush",
        url="https://blush.design",
        category="illustration",
        description="Customizable illustrations by artists worldwide",
        tags=["customizable", "artist", "figma"],
    ),
]


ANIMATION_RESOURCES: list[DesignResource] = [
    DesignResource(
        name="LottieFiles",
        url="https://lottiefiles.com",
        category="animation",
        description="Interactive animations (JSON, GIF, MP4 export)",
        api_available=True,
        tags=["lottie", "json", "web", "interactive"],
    ),
    DesignResource(
        name="GSAP",
        url="https://greensock.com",
        category="animation",
        description="High-performance HTML5 animation library",
        tags=["js", "web", "performant", "timeline"],
    ),
    DesignResource(
        name="Framer Motion",
        url="https://www.framer.com/motion",
        category="animation",
        description="Production-ready React animation library",
        tags=["react", "spring", "layout", "gestures"],
    ),
    DesignResource(
        name="AnimXYZ",
        url="https://animxyz.com",
        category="animation",
        description="Composable CSS animation library (Vue, React, SCSS)",
        tags=["css", "composable", "vue", "react"],
    ),
]


BACKGROUND_RESOURCES: list[DesignResource] = [
    DesignResource(
        name="fffuel",
        url="https://fffuel.co",
        category="background",
        description="SVG generators for gradients, patterns, textures, shapes",
        tags=["svg", "generator", "pattern", "texture"],
    ),
    DesignResource(
        name="Haikei",
        url="https://haikei.app",
        category="background",
        description="Multi-shape SVG background generator (waves, blobs, etc)",
        tags=["svg", "wave", "blob", "layered"],
    ),
    DesignResource(
        name="Hero Patterns",
        url="https://heropatterns.com",
        category="background",
        description="Repeatable SVG background patterns",
        tags=["pattern", "svg", "repeatable", "subtle"],
    ),
    DesignResource(
        name="Cool Backgrounds",
        url="https://coolbackgrounds.io",
        category="background",
        description="Curated background generators (particles, gradients, etc)",
        tags=["curated", "particles", "gradient", "abstract"],
    ),
]


DESIGN_SYSTEM_RESOURCES: list[DesignResource] = [
    DesignResource(
        name="Material Design",
        url="https://material.io",
        category="design_system",
        description="Google's comprehensive design system",
        tags=["google", "components", "guidelines"],
    ),
    DesignResource(
        name="Fluent UI",
        url="https://developer.microsoft.com/en-us/fluentui",
        category="design_system",
        description="Microsoft's cross-platform design system",
        tags=["microsoft", "cross-platform", "react"],
    ),
    DesignResource(
        name="Carbon Design System",
        url="https://carbondesignsystem.com",
        category="design_system",
        description="IBM's open-source design system",
        tags=["ibm", "enterprise", "data-heavy"],
    ),
    DesignResource(
        name="shadcn/ui",
        url="https://ui.shadcn.com",
        category="design_system",
        description="Beautifully designed components (Radix + Tailwind)",
        tags=["react", "tailwind", "radix", "modern"],
    ),
]


# =========================================================================
# RESOURCE LOOKUP API
# =========================================================================


ALL_RESOURCES: list[DesignResource] = (
    COLOR_RESOURCES
    + GRADIENT_RESOURCES
    + FONT_RESOURCES
    + ICON_RESOURCES
    + ILLUSTRATION_RESOURCES
    + ANIMATION_RESOURCES
    + BACKGROUND_RESOURCES
    + DESIGN_SYSTEM_RESOURCES
)


def get_resources_by_category(category: str) -> list[DesignResource]:
    """Get all resources for a specific category."""
    return [r for r in ALL_RESOURCES if r.category == category]


def get_resources_with_api() -> list[DesignResource]:
    """Get resources that have APIs available for programmatic access."""
    return [r for r in ALL_RESOURCES if r.api_available]


def get_resources_by_tag(tag: str) -> list[DesignResource]:
    """Get resources matching a specific tag."""
    tag_lower = tag.lower()
    return [r for r in ALL_RESOURCES if tag_lower in [t.lower() for t in r.tags]]


def get_resource_categories() -> list[str]:
    """Get all available resource categories."""
    return sorted(set(r.category for r in ALL_RESOURCES))


def get_design_toolkit_summary() -> dict[str, int]:
    """Get summary of resources per category."""
    summary: dict[str, int] = {}
    for r in ALL_RESOURCES:
        summary[r.category] = summary.get(r.category, 0) + 1
    return summary
