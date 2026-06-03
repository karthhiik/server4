"""Emotional style families for V4 design resolution."""

from __future__ import annotations

from typing import Any


STYLE_FAMILIES: dict[str, dict[str, Any]] = {
    "minimal_saas": {
        "use_case": "B2B decks",
        "palette": "cool_neutrals_with_blue_accent",
        "fonts": ("Inter", "Inter"),
        "density": "comfortable",
        "motion": "subtle",
    },
    "bold_startup": {
        "use_case": "fundraising",
        "palette": "high_contrast_black_white_accent",
        "fonts": ("Space Grotesk", "Inter"),
        "density": "spacious",
        "motion": "dramatic",
    },
    "enterprise_consulting": {
        "use_case": "sales / strategy",
        "palette": "deep_navy_with_gold",
        "fonts": ("Source Serif 4", "Inter"),
        "density": "compact",
        "motion": "minimal",
    },
    "luxury_minimal": {
        "use_case": "premium brands",
        "palette": "warm_neutral_with_black",
        "fonts": ("Playfair Display", "Source Sans 3"),
        "density": "spacious",
        "motion": "elegant",
    },
    "ai_futuristic": {
        "use_case": "AI products",
        "palette": "dark_high_contrast_with_cyan",
        "fonts": ("Plus Jakarta Sans", "IBM Plex Sans"),
        "density": "comfortable",
        "motion": "kinetic",
    },
    "playful_product": {
        "use_case": "consumer apps",
        "palette": "bright_multicolor",
        "fonts": ("DM Sans", "DM Sans"),
        "density": "comfortable",
        "motion": "bouncy",
    },
    "data_heavy": {
        "use_case": "market reports",
        "palette": "cool_grayscale_with_teal",
        "fonts": ("IBM Plex Sans", "IBM Plex Mono"),
        "density": "compact",
        "motion": "minimal",
    },
    "founder_story": {
        "use_case": "early-stage pitch",
        "palette": "warm_earth_tones",
        "fonts": ("Lora", "Inter"),
        "density": "spacious",
        "motion": "narrative",
    },
}


def select_style_family(*, purpose: str, industry: str | None = None, requested: str | None = None) -> dict[str, Any]:
    if requested and requested in STYLE_FAMILIES:
        return {"id": requested, **STYLE_FAMILIES[requested]}
    key = (purpose or "").lower()
    industry_key = (industry or "").lower()
    if "sales" in key or "enterprise" in key:
        family = "enterprise_consulting"
    elif "report" in key or "market" in key or "financial" in key:
        family = "data_heavy"
    elif "consumer" in industry_key or "education" in industry_key:
        family = "playful_product"
    elif "ai" in industry_key or "tech" in industry_key:
        family = "ai_futuristic"
    elif "story" in key:
        family = "founder_story"
    else:
        family = "bold_startup" if "pitch" in key or "investor" in key else "minimal_saas"
    return {"id": family, **STYLE_FAMILIES[family]}
