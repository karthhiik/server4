"""Advanced Typography Engine

Font pairing database with harmony scores, dynamic type scale generation,
and optical sizing recommendations. No LLM calls — fully deterministic.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class FontPair:
    heading: str
    body: str
    harmony_score: float  # 0-1
    personality: str  # e.g. "modern", "classic", "playful"
    best_for: list[str]  # direction IDs where this pair excels


# Curated font pairings with harmony scores
_FONT_PAIRS: list[FontPair] = [
    FontPair("Space Grotesk", "Inter", 0.92, "modern", ["minimal_dark", "obsidian_tech", "neon_futurism"]),
    FontPair("Playfair Display", "Source Serif 4", 0.88, "classic", ["luxury_gold", "warm_narrative", "midnight_navy"]),
    FontPair("Manrope", "Inter", 0.90, "clean", ["light_professional", "swiss_editorial", "sage_calm"]),
    FontPair("Archivo", "Karla", 0.85, "playful", ["pastel_soft", "coral_energy", "berry_creative"]),
    FontPair("Syne", "Space Grotesk", 0.87, "futuristic", ["neon_futurism", "cinematic_dark", "bold_contrast"]),
    FontPair("DM Serif Display", "DM Sans", 0.89, "editorial", ["swiss_editorial", "luxury_gold", "earth_organic"]),
    FontPair("Clash Display", "Inter", 0.84, "youthful", ["coral_energy", "berry_creative", "pastel_soft"]),
    FontPair("Cinzel", "Lora", 0.86, "luxury", ["luxury_gold", "midnight_navy", "cinematic_dark"]),
    FontPair("Satoshi", "Inter", 0.91, "geometric", ["minimal_dark", "light_professional", "obsidian_tech"]),
    FontPair("Boska", "Plus Jakarta Sans", 0.83, "warm", ["warm_narrative", "earth_organic", "sage_calm"]),
]


@dataclass
class TypeScale:
    display: int
    h1: int
    h2: int
    h3: int
    body: int
    caption: int
    line_height: float
    letter_spacing: float


def recommend_font_pair(visual_direction: str, user_heading: Optional[str] = None, user_body: Optional[str] = None) -> dict[str, str]:
    """Recommend a font pair based on visual direction."""
    if user_heading and user_body:
        return {"heading": user_heading, "body": user_body}

    # Find best pair for direction
    best = None
    best_score = -1.0
    for pair in _FONT_PAIRS:
        if visual_direction in pair.best_for:
            if pair.harmony_score > best_score:
                best = pair
                best_score = pair.harmony_score

    if best:
        return {"heading": best.heading, "body": best.body}

    # Fallback
    return {"heading": "Inter", "body": "Inter"}


def generate_type_scale(
    *,
    content_density: str = "balanced",
    visual_direction: str = "minimal_dark",
    base_body: int = 14,
) -> TypeScale:
    """Generate an appropriate type scale based on content density and direction."""
    # Direction multipliers
    display_mult = {
        "cinematic_dark": 5.2, "luxury_gold": 4.8, "neon_futurism": 5.0,
        "bold_contrast": 4.5, "minimal_dark": 4.0, "swiss_editorial": 3.8,
        "light_professional": 3.6, "warm_narrative": 4.2, "pastel_soft": 3.5,
        "earth_organic": 4.0, "midnight_navy": 4.5, "coral_energy": 4.2,
        "sage_calm": 3.6, "berry_creative": 4.0, "obsidian_tech": 4.5,
    }.get(visual_direction, 4.0)

    # Density adjustments
    if content_density == "sparse":
        display_mult *= 1.15
        body = max(15, base_body + 1)
        line_height = 1.6
        letter_spacing = -0.01
    elif content_density == "dense":
        display_mult *= 0.85
        body = max(12, base_body - 1)
        line_height = 1.4
        letter_spacing = 0.0
    else:
        body = base_body
        line_height = 1.5
        letter_spacing = -0.005

    display = int(body * display_mult)
    h1 = int(display * 0.72)
    h2 = int(h1 * 0.78)
    h3 = int(h2 * 0.82)
    caption = max(10, int(body * 0.78))

    return TypeScale(
        display=display, h1=h1, h2=h2, h3=h3,
        body=body, caption=caption,
        line_height=line_height, letter_spacing=letter_spacing,
    )


def heading_weight_for_personality(visual_direction: str) -> int:
    """Recommend heading font weight based on direction personality."""
    bold_directions = {"bold_contrast", "cinematic_dark", "neon_futurism", "coral_energy"}
    if visual_direction in bold_directions:
        return 800
    medium_directions = {"luxury_gold", "midnight_navy", "obsidian_tech"}
    if visual_direction in medium_directions:
        return 700
    return 600
