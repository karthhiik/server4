"""
Chibi Avatar — Python SVG Renderer (Server-Side)

A Python port of the TypeScript Chibi renderer for server-side avatar generation.
This produces static SVGs (no animations) for auto-provisioning and fallback.

The seed-to-options algorithm matches the frontend exactly using cyrb128 + sfc32 PRNG.
"""

from typing import Optional, Dict, Any, List, Literal
import math

# ══════════════════════════════════════════════════════════════════════════════
# PALETTES & STYLE ARRAYS (must match TypeScript exactly)
# ══════════════════════════════════════════════════════════════════════════════

SKIN_TONES = [
    "#ffe5d9", "#fcd5ce", "#f8c8b8", "#f1c27d",
    "#e0ac69", "#c68642", "#8d5524", "#5c3a21"
]

HAIR_COLORS = [
    "#090806", "#2c222b", "#3b302a", "#4e433f", "#6a4e42",
    "#8d5524", "#c68642", "#e5c07b", "#d4a853", "#e88a5e",
    "#ec4899", "#a855f7", "#06b6d4", "#22c55e", "#f43f5e"
]

EYE_COLORS = [
    "#4a3728", "#2d5a27", "#3b82f6", "#6b7280",
    "#8b5cf6", "#ec4899", "#f59e0b", "#1a1a2e"
]

CLOTHING_COLORS = [
    "#1e293b", "#4a4e69", "#7c3aed", "#2563eb",
    "#059669", "#dc2626", "#f59e0b", "#ec4899", "#f5f5f4"
]

BACKGROUND_COLORS = [
    "#fce7f3", "#dbeafe", "#d1fae5", "#fef3c7",
    "#f3e8ff", "#e0e7ff", "#f5f5f4", "#1e1b4b"
]

HAIR_STYLES = [
    "twintails", "bob", "ponytail", "messy", "spiky", "long-straight",
    "long-wavy", "short-crop", "buzz", "bangs", "side-swept", "bun",
    "braids", "afro", "pigtails", "undercut", "mohawk", "hime-cut"
]

EYE_STYLES = [
    "round-sparkle", "cat-eye", "droopy", "determined", "happy-closed",
    "wink", "surprised", "cool", "sleepy", "heart", "star", "default"
]

EYEBROW_STYLES = ["default", "flat", "raised", "angry", "sad", "none"]

NOSE_STYLES = ["dot", "line", "none"]

EXPRESSIONS = [
    "smile", "grin", "cat-mouth", "o-mouth", "pout",
    "tongue-out", "fangs", "neutral", "smirk", "open-smile"
]

CLOTHING_TYPES = [
    "hoodie", "school-uniform", "t-shirt", "dress", "suit", "kimono",
    "overalls", "tank-top", "sweater", "cape", "sailor", "jacket"
]

ACCESSORY_TYPES = [
    "none", "glasses", "sunglasses", "headband", "bow", "cat-ears",
    "horns", "crown", "scarf", "mask", "earrings", "bandaid"
]

BACKGROUND_STYLES = ["solid", "gradient", "dots", "hearts", "stars"]

ChibiVariant = Literal["neutral", "male", "female"]

# ══════════════════════════════════════════════════════════════════════════════
# DETERMINISTIC PRNG (cyrb128 + sfc32) — matches TypeScript exactly
# ══════════════════════════════════════════════════════════════════════════════

def cyrb128(s: str) -> tuple:
    """128-bit hash from string, returns 4 32-bit integers."""
    h1 = 1779033703
    h2 = 3144134277
    h3 = 1013904242
    h4 = 2773480762
    for ch in s:
        k = ord(ch)
        h1 = (h2 ^ (((h1 ^ k) * 597399067) & 0xFFFFFFFF)) & 0xFFFFFFFF
        h2 = (h3 ^ (((h2 ^ k) * 2869860233) & 0xFFFFFFFF)) & 0xFFFFFFFF
        h3 = (h4 ^ (((h3 ^ k) * 951274213) & 0xFFFFFFFF)) & 0xFFFFFFFF
        h4 = (h1 ^ (((h4 ^ k) * 2716044179) & 0xFFFFFFFF)) & 0xFFFFFFFF
    h1 = (((h3 ^ (h1 >> 18)) * 597399067) & 0xFFFFFFFF) ^ 0
    h2 = (((h4 ^ (h2 >> 22)) * 2869860233) & 0xFFFFFFFF) ^ 0
    h3 = (((h1 ^ (h3 >> 17)) * 951274213) & 0xFFFFFFFF) ^ 0
    h4 = (((h2 ^ (h4 >> 19)) * 2716044179) & 0xFFFFFFFF) ^ 0
    return (
        ((h1 ^ h2 ^ h3 ^ h4) & 0xFFFFFFFF),
        ((h2 ^ h1) & 0xFFFFFFFF),
        ((h3 ^ h1) & 0xFFFFFFFF),
        ((h4 ^ h1) & 0xFFFFFFFF)
    )


def sfc32(a: int, b: int, c: int, d: int):
    """Simple Fast Counter PRNG, returns a generator function."""
    state = [a & 0xFFFFFFFF, b & 0xFFFFFFFF, c & 0xFFFFFFFF, d & 0xFFFFFFFF]

    def next_random() -> float:
        e = (state[0] + state[1]) & 0xFFFFFFFF
        state[0] = state[1] ^ (state[1] >> 9)
        state[1] = (state[2] + (state[2] << 3)) & 0xFFFFFFFF
        state[2] = (((state[2] << 21) | (state[2] >> 11)) & 0xFFFFFFFF) ^ e
        state[3] = (state[3] + 1) & 0xFFFFFFFF
        e = (e + state[3]) & 0xFFFFFFFF
        return e / 0x100000000

    return next_random


def create_rng(seed: str):
    """Create a PRNG from a string seed."""
    h = cyrb128(seed)
    return sfc32(h[0], h[1], h[2], h[3])


def pick(rng, arr: list):
    """Pick a random element from an array using the PRNG."""
    return arr[int(rng() * len(arr))]


def pick_index(rng, length: int) -> int:
    """Pick a random index."""
    return int(rng() * length)


# ══════════════════════════════════════════════════════════════════════════════
# COLOR HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def hex_to_rgb(hex_color: str) -> Dict[str, int]:
    """Convert hex color to RGB dict."""
    h = hex_color.lstrip("#")
    return {
        "r": int(h[0:2], 16),
        "g": int(h[2:4], 16),
        "b": int(h[4:6], 16)
    }


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB to hex color."""
    def clamp(v):
        return max(0, min(255, round(v)))
    return f"#{clamp(r):02x}{clamp(g):02x}{clamp(b):02x}"


def lighten(hex_color: str, pct: int) -> str:
    """Lighten a hex color by percentage."""
    rgb = hex_to_rgb(hex_color)
    f = pct / 100
    return rgb_to_hex(
        rgb["r"] + (255 - rgb["r"]) * f,
        rgb["g"] + (255 - rgb["g"]) * f,
        rgb["b"] + (255 - rgb["b"]) * f
    )


def darken(hex_color: str, pct: int) -> str:
    """Darken a hex color by percentage."""
    rgb = hex_to_rgb(hex_color)
    f = 1 - pct / 100
    return rgb_to_hex(rgb["r"] * f, rgb["g"] * f, rgb["b"] * f)


# ══════════════════════════════════════════════════════════════════════════════
# RESOLVE OPTIONS FROM SEED
# ══════════════════════════════════════════════════════════════════════════════

def resolve_options(seed: str, variant: ChibiVariant = "neutral", opts: Optional[Dict] = None) -> Dict:
    """
    Resolve full ChibiOptions from a seed and optional overrides.
    Matches the TypeScript resolveOptions() function exactly.
    """
    opts = opts or {}
    full_seed = f"{variant}:{seed}"
    rng = create_rng(full_seed)

    return {
        "skinTone": opts.get("skinTone") or pick(rng, SKIN_TONES),
        "hairStyle": opts.get("hairStyle") or pick(rng, HAIR_STYLES),
        "hairColor": opts.get("hairColor") or pick(rng, HAIR_COLORS),
        "eyeStyle": opts.get("eyeStyle") or pick(rng, EYE_STYLES),
        "eyeColor": opts.get("eyeColor") or pick(rng, EYE_COLORS),
        "eyebrowStyle": opts.get("eyebrowStyle") or pick(rng, EYEBROW_STYLES),
        "noseStyle": opts.get("noseStyle") or pick(rng, NOSE_STYLES),
        "expression": opts.get("expression") or pick(rng, EXPRESSIONS),
        "clothing": opts.get("clothing") or pick(rng, CLOTHING_TYPES),
        "clothingColor": opts.get("clothingColor") or pick(rng, CLOTHING_COLORS),
        "accessory": opts.get("accessory") or pick(rng, ACCESSORY_TYPES),
        "background": opts.get("background") or pick(rng, BACKGROUND_COLORS),
        "backgroundStyle": opts.get("backgroundStyle") or pick(rng, BACKGROUND_STYLES),
        "blush": opts.get("blush") if opts.get("blush") is not None else (rng() > 0.4),
        "animated": False,  # Server-side always static
    }


# ══════════════════════════════════════════════════════════════════════════════
# SVG PART RENDERERS
# ══════════════════════════════════════════════════════════════════════════════

def render_background(style: str, color: str) -> str:
    """Render background layer."""
    if style == "solid":
        return f'<rect width="128" height="128" fill="{color}"/>'

    elif style == "gradient":
        return f'''
    <defs>
      <linearGradient id="bgGrad" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="{lighten(color, 15)}"/>
        <stop offset="100%" stop-color="{darken(color, 10)}"/>
      </linearGradient>
    </defs>
    <rect width="128" height="128" fill="url(#bgGrad)"/>'''

    elif style == "dots":
        dots = f'<rect width="128" height="128" fill="{color}"/>'
        dot_color = darken(color, 12)
        for y in range(8, 128, 16):
            for x in range(8, 128, 16):
                dots += f'<circle cx="{x}" cy="{y}" r="1.8" fill="{dot_color}" opacity="0.25"/>'
        return dots

    elif style == "hearts":
        heart_color = darken(color, 15)
        svg = f'<rect width="128" height="128" fill="{color}"/>'
        positions = [
            (16, 12, 6), (48, 8, 5), (80, 14, 7), (112, 10, 5),
            (8, 44, 5), (40, 40, 6), (72, 48, 5), (104, 42, 6),
            (20, 76, 6), (56, 72, 5), (88, 80, 7), (116, 74, 5),
            (12, 108, 5), (44, 112, 6), (76, 106, 5), (108, 110, 6),
        ]
        for x, y, s in positions:
            svg += f'<path d="M{x} {y + s * 0.3} C{x} {y - s * 0.3}, {x + s} {y - s * 0.3}, {x + s} {y + s * 0.3} C{x + s} {y + s * 0.8}, {x + s * 0.5} {y + s * 1.2}, {x + s * 0.5} {y + s * 1.2} C{x + s * 0.5} {y + s * 1.2}, {x} {y + s * 0.8}, {x} {y + s * 0.3}Z" fill="{heart_color}" opacity="0.15" transform="translate({-s * 0.5}, {-s * 0.5})"/>'
        return svg

    elif style == "stars":
        star_color = darken(color, 15)
        svg = f'<rect width="128" height="128" fill="{color}"/>'
        positions = [
            (16, 14, 5), (52, 10, 4), (88, 16, 5.5), (118, 8, 3.5),
            (10, 48, 4), (42, 44, 5), (78, 50, 4), (110, 46, 5),
            (22, 80, 5), (58, 78, 4.5), (94, 82, 5), (120, 76, 3.5),
            (14, 114, 4), (50, 110, 5), (86, 116, 4), (114, 112, 5),
        ]
        for cx, cy, r in positions:
            pts = []
            for i in range(5):
                a_outer = ((i * 72 - 90) * math.pi) / 180
                a_inner = (((i * 72 + 36) - 90) * math.pi) / 180
                pts.append(f"{cx + r * math.cos(a_outer)},{cy + r * math.sin(a_outer)}")
                pts.append(f"{cx + r * 0.45 * math.cos(a_inner)},{cy + r * 0.45 * math.sin(a_inner)}")
            svg += f'<polygon points="{" ".join(pts)}" fill="{star_color}" opacity="0.18"/>'
        return svg

    return f'<rect width="128" height="128" fill="{color}"/>'


def render_body(skin_tone: str) -> str:
    """Render chibi body."""
    return f'''<g class="chibi-body">
    <rect x="57" y="74" width="14" height="8" rx="3" fill="{skin_tone}" stroke="{darken(skin_tone, 10)}" stroke-width="0.3"/>
    <path d="M32 96 Q34 82, 48 80 Q56 78, 64 78 Q72 78, 80 80 Q94 82, 96 96 Q98 104, 96 112 L96 128 L32 128 L32 112 Q30 104, 32 96Z"
          fill="{skin_tone}" stroke="{darken(skin_tone, 10)}" stroke-width="0.4"/>
    <path d="M38 92 Q44 84, 54 82 L50 90 Q44 88, 38 92Z" fill="{lighten(skin_tone, 8)}" opacity="0.5"/>
    <path d="M90 92 Q84 84, 74 82 L78 90 Q84 88, 90 92Z" fill="{lighten(skin_tone, 8)}" opacity="0.5"/>
  </g>'''


def render_head(skin_tone: str, blush: bool) -> str:
    """Render head with optional blush."""
    head_grad = f'''
    <defs>
      <radialGradient id="headGrad" cx="0.45" cy="0.38" r="0.55">
        <stop offset="0%" stop-color="{lighten(skin_tone, 12)}" />
        <stop offset="85%" stop-color="{skin_tone}" />
        <stop offset="100%" stop-color="{darken(skin_tone, 8)}" />
      </radialGradient>
    </defs>'''

    head = f'<ellipse cx="64" cy="44" rx="36" ry="34" fill="url(#headGrad)" stroke="{darken(skin_tone, 15)}" stroke-width="0.5"/>'

    ears = f'''
    <ellipse cx="28.5" cy="46" rx="5" ry="6.5" fill="{skin_tone}" stroke="{darken(skin_tone, 15)}" stroke-width="0.5"/>
    <ellipse cx="28.5" cy="46" rx="2.8" ry="4" fill="{darken(skin_tone, 8)}"/>
    <ellipse cx="99.5" cy="46" rx="5" ry="6.5" fill="{skin_tone}" stroke="{darken(skin_tone, 15)}" stroke-width="0.5"/>
    <ellipse cx="99.5" cy="46" rx="2.8" ry="4" fill="{darken(skin_tone, 8)}"/>'''

    blush_svg = ""
    if blush:
        blush_svg = '''
    <ellipse cx="42" cy="54" rx="7" ry="4" fill="#fca5a5" opacity="0.45"/>
    <ellipse cx="86" cy="54" rx="7" ry="4" fill="#fca5a5" opacity="0.45"/>'''

    return f"{head_grad}\n{ears}\n{head}\n{blush_svg}"


# ── HAIR STYLES ──────────────────────────────────────────────────────────────

def _hair_twintails_back(c: str) -> str:
    return f'''
      <path d="M28 38 C20 42, 14 65, 22 90 Q25 96, 20 100 Q15 88, 15 70 Q14 50, 28 38Z" fill="{c}" stroke="{darken(c,18)}" stroke-width="0.5"/>
      <path d="M100 38 C108 42, 114 65, 106 90 Q103 96, 108 100 Q113 88, 113 70 Q114 50, 100 38Z" fill="{c}" stroke="{darken(c,18)}" stroke-width="0.5"/>
      <path d="M30 14 Q64 0, 98 14 Q102 22, 100 36 L64 30 L28 36 Q26 22, 30 14Z" fill="{c}"/>'''

def _hair_twintails_front(c: str) -> str:
    return f'''
      <path d="M30 16 Q46 10, 64 12 Q82 10, 98 16 Q100 24, 98 32 Q82 22, 64 20 Q46 22, 30 32 Q28 24, 30 16Z" fill="{c}" stroke="{darken(c,12)}" stroke-width="0.4"/>
      <path d="M36 32 Q44 26, 52 30 L48 38 Q40 36, 36 32Z" fill="{lighten(c,8)}"/>
      <circle cx="26" cy="38" r="6" fill="{c}" stroke="{darken(c,12)}" stroke-width="0.4"/>
      <circle cx="102" cy="38" r="6" fill="{c}" stroke="{darken(c,12)}" stroke-width="0.4"/>'''

def _hair_bob_back(c: str) -> str:
    return f'''
      <path d="M28 26 Q64 8, 100 26 Q106 44, 102 60 Q98 66, 92 66 L36 66 Q30 66, 26 60 Q22 44, 28 26Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>'''

def _hair_bob_front(c: str) -> str:
    return f'''
      <path d="M30 18 Q48 8, 64 10 Q80 8, 98 18 Q100 28, 96 36 Q80 26, 64 24 Q48 26, 32 36 Q28 28, 30 18Z" fill="{c}" stroke="{darken(c,12)}" stroke-width="0.4"/>
      <path d="M28 36 Q26 50, 28 60 Q30 64, 34 62 L32 40Z" fill="{lighten(c,6)}"/>
      <path d="M100 36 Q102 50, 100 60 Q98 64, 94 62 L96 40Z" fill="{lighten(c,6)}"/>'''

def _hair_ponytail_back(c: str) -> str:
    return f'''
      <path d="M60 16 Q80 12, 96 24 Q102 38, 94 46 Q88 36, 76 28 Q68 24, 60 16Z" fill="{c}"/>
      <path d="M82 20 Q90 18, 96 24 Q104 36, 98 58 Q96 78, 90 94 Q88 98, 86 92 Q90 76, 92 58 Q94 40, 88 28 Q86 24, 82 20Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>
      <path d="M30 14 Q64 2, 98 14 Q102 24, 100 36 L64 30 L28 36 Q26 24, 30 14Z" fill="{c}"/>'''

def _hair_ponytail_front(c: str) -> str:
    return f'''
      <path d="M30 18 Q48 8, 64 10 Q80 8, 98 18 Q100 26, 98 34 Q80 22, 64 20 Q48 22, 30 34 Q28 26, 30 18Z" fill="{c}" stroke="{darken(c,12)}" stroke-width="0.4"/>
      <path d="M48 24 Q56 18, 66 20 L64 30 Q54 28, 48 24Z" fill="{lighten(c,8)}"/>'''

def _hair_messy_back(c: str) -> str:
    return f'''
      <path d="M24 20 Q64 -2, 104 20 Q112 40, 106 58 Q100 68, 92 62 L36 62 Q28 68, 22 58 Q16 40, 24 20Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>'''

def _hair_messy_front(c: str) -> str:
    return f'''
      <path d="M28 22 Q40 10, 54 14 L48 34 Q38 30, 28 22Z" fill="{c}"/>
      <path d="M50 12 Q64 6, 78 12 L72 32 Q60 28, 50 12Z" fill="{lighten(c,6)}"/>
      <path d="M74 14 Q88 10, 100 22 L94 34 Q84 26, 74 14Z" fill="{c}"/>
      <path d="M26 30 L22 20 Q18 28, 20 38Z" fill="{c}"/>
      <path d="M102 30 L106 20 Q110 28, 108 38Z" fill="{c}"/>
      <path d="M56 10 L58 4 Q62 8, 60 14Z" fill="{lighten(c,10)}"/>
      <path d="M72 10 L70 2 Q66 8, 68 14Z" fill="{c}"/>'''

def _hair_spiky_back(c: str) -> str:
    return f'''
      <path d="M24 28 Q64 4, 104 28 Q108 44, 104 56 L24 56 Q20 44, 24 28Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>'''

def _hair_spiky_front(c: str) -> str:
    return f'''
      <path d="M32 30 L28 8 Q36 20, 42 14 L46 28Z" fill="{c}"/>
      <path d="M44 26 L44 4 Q52 16, 56 10 L54 26Z" fill="{lighten(c,8)}"/>
      <path d="M52 24 L56 0 Q62 14, 68 2 L74 24Z" fill="{c}"/>
      <path d="M72 26 L76 8 Q80 18, 84 12 L82 28Z" fill="{lighten(c,6)}"/>
      <path d="M80 30 L86 10 Q92 20, 96 14 L96 30Z" fill="{c}"/>
      <path d="M28 30 Q26 36, 28 42 L30 34Z" fill="{darken(c,8)}"/>
      <path d="M100 30 Q102 36, 100 42 L98 34Z" fill="{darken(c,8)}"/>'''

def _hair_long_straight_back(c: str) -> str:
    return f'''
      <path d="M26 20 Q64 2, 102 20 Q108 40, 106 70 Q104 96, 98 110 Q90 118, 80 116 L48 116 Q38 118, 30 110 Q24 96, 22 70 Q20 40, 26 20Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>'''

def _hair_long_straight_front(c: str) -> str:
    return f'''
      <path d="M30 18 Q48 6, 64 8 Q80 6, 98 18 Q100 28, 98 36 Q80 24, 64 22 Q48 24, 30 36 Q28 28, 30 18Z" fill="{c}" stroke="{darken(c,10)}" stroke-width="0.4"/>
      <path d="M28 36 L26 58 Q28 52, 32 48Z" fill="{lighten(c,6)}"/>
      <path d="M100 36 L102 58 Q100 52, 96 48Z" fill="{lighten(c,6)}"/>'''

def _hair_long_wavy_back(c: str) -> str:
    return f'''
      <path d="M26 20 Q64 2, 102 20 Q110 46, 104 72 Q100 88, 106 100 Q108 108, 102 112 Q92 118, 80 114 Q70 108, 64 112 Q58 108, 48 114 Q36 118, 26 112 Q20 108, 22 100 Q28 88, 24 72 Q18 46, 26 20Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>'''

def _hair_long_wavy_front(c: str) -> str:
    return f'''
      <path d="M30 18 Q48 6, 64 8 Q80 6, 98 18 Q100 28, 98 36 Q80 24, 64 22 Q48 24, 30 36 Q28 28, 30 18Z" fill="{c}" stroke="{darken(c,10)}" stroke-width="0.4"/>
      <path d="M34 36 Q30 46, 28 56 Q32 50, 36 46Z" fill="{lighten(c,8)}"/>
      <path d="M94 36 Q98 46, 100 56 Q96 50, 92 46Z" fill="{lighten(c,8)}"/>'''

def _hair_short_crop_back(c: str) -> str:
    return f'''
      <path d="M30 18 Q64 6, 98 18 Q104 30, 100 42 L28 42 Q24 30, 30 18Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>'''

def _hair_short_crop_front(c: str) -> str:
    return f'''
      <path d="M32 20 Q48 10, 64 12 Q80 10, 96 20 Q98 28, 96 34 Q80 24, 64 22 Q48 24, 32 34 Q30 28, 32 20Z" fill="{c}" stroke="{darken(c,10)}" stroke-width="0.4"/>'''

def _hair_buzz_back(c: str) -> str:
    return f'''
      <path d="M32 20 Q64 8, 96 20 Q100 30, 98 38 L30 38 Q28 30, 32 20Z" fill="{c}" opacity="0.7" stroke="{darken(c,15)}" stroke-width="0.5"/>'''

def _hair_buzz_front(c: str) -> str:
    return f'''
      <path d="M34 22 Q48 14, 64 16 Q80 14, 94 22 Q96 28, 94 34 Q80 24, 64 22 Q48 24, 34 34 Q32 28, 34 22Z" fill="{c}" opacity="0.6"/>'''

def _hair_bangs_back(c: str) -> str:
    return f'''
      <path d="M28 18 Q64 4, 100 18 Q106 36, 102 54 Q98 60, 94 58 L34 58 Q30 60, 26 54 Q22 36, 28 18Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>'''

def _hair_bangs_front(c: str) -> str:
    return f'''
      <path d="M28 18 Q48 6, 64 8 Q80 6, 100 18 Q102 30, 100 44 Q82 34, 64 32 Q46 34, 28 44 Q26 30, 28 18Z" fill="{c}" stroke="{darken(c,10)}" stroke-width="0.4"/>
      <path d="M36 28 Q48 20, 60 24 L58 36 Q46 32, 36 28Z" fill="{lighten(c,6)}"/>
      <path d="M68 24 Q80 20, 92 28 L88 36 Q78 32, 68 24Z" fill="{lighten(c,6)}"/>'''

def _hair_side_swept_back(c: str) -> str:
    return f'''
      <path d="M28 18 Q64 4, 100 18 Q106 36, 102 52 L26 52 Q22 36, 28 18Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>'''

def _hair_side_swept_front(c: str) -> str:
    return f'''
      <path d="M26 20 Q40 8, 58 10 Q76 8, 100 18 Q102 28, 100 38 Q84 26, 66 24 Q48 24, 30 30 Q32 36, 26 48 Q22 36, 26 20Z" fill="{c}" stroke="{darken(c,10)}" stroke-width="0.4"/>
      <path d="M28 28 Q24 40, 24 50 L28 44 Q30 36, 28 28Z" fill="{lighten(c,8)}"/>'''

def _hair_bun_back(c: str) -> str:
    return f'''
      <path d="M30 18 Q64 4, 98 18 Q104 30, 100 42 L28 42 Q24 30, 30 18Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>'''

def _hair_bun_front(c: str) -> str:
    return f'''
      <circle cx="64" cy="10" r="11" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>
      <circle cx="64" cy="8" r="5" fill="{lighten(c,10)}"/>
      <path d="M32 20 Q48 10, 64 12 Q80 10, 96 20 Q98 28, 96 34 Q80 24, 64 22 Q48 24, 32 34 Q30 28, 32 20Z" fill="{c}" stroke="{darken(c,10)}" stroke-width="0.4"/>'''

def _hair_braids_back(c: str) -> str:
    return f'''
      <path d="M30 14 Q64 2, 98 14 Q102 24, 100 36 L28 36 Q26 24, 30 14Z" fill="{c}"/>
      <path d="M30 36 Q26 50, 24 66 Q22 78, 26 88 Q28 92, 30 88 Q28 78, 30 66 Q32 50, 34 40Z" fill="{c}" stroke="{darken(c,12)}" stroke-width="0.5"/>
      <path d="M98 36 Q102 50, 104 66 Q106 78, 102 88 Q100 92, 98 88 Q100 78, 98 66 Q96 50, 94 40Z" fill="{c}" stroke="{darken(c,12)}" stroke-width="0.5"/>
      <circle cx="27" cy="90" r="3.5" fill="{c}" stroke="{darken(c,12)}" stroke-width="0.4"/>
      <circle cx="101" cy="90" r="3.5" fill="{c}" stroke="{darken(c,12)}" stroke-width="0.4"/>'''

def _hair_braids_front(c: str) -> str:
    return f'''
      <path d="M30 16 Q48 6, 64 8 Q80 6, 98 16 Q100 26, 98 34 Q80 22, 64 20 Q48 22, 30 34 Q28 26, 30 16Z" fill="{c}" stroke="{darken(c,10)}" stroke-width="0.4"/>'''

def _hair_afro_back(c: str) -> str:
    return f'''
      <ellipse cx="64" cy="38" rx="46" ry="42" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>
      <ellipse cx="64" cy="36" rx="40" ry="36" fill="{lighten(c,6)}"/>'''

def _hair_afro_front(c: str) -> str:
    return f'''
      <path d="M32 30 Q48 16, 64 18 Q80 16, 96 30 Q98 36, 96 42 Q80 30, 64 28 Q48 30, 32 42 Q30 36, 32 30Z" fill="{c}" stroke="{darken(c,10)}" stroke-width="0.4"/>'''

def _hair_pigtails_back(c: str) -> str:
    return f'''
      <path d="M30 14 Q64 2, 98 14 Q102 24, 100 36 L28 36 Q26 24, 30 14Z" fill="{c}"/>
      <circle cx="24" cy="36" r="8" fill="{c}" stroke="{darken(c,12)}" stroke-width="0.5"/>
      <circle cx="104" cy="36" r="8" fill="{c}" stroke="{darken(c,12)}" stroke-width="0.5"/>
      <path d="M20 44 Q18 56, 20 68 Q22 60, 24 52Z" fill="{c}" stroke="{darken(c,12)}" stroke-width="0.4"/>
      <path d="M108 44 Q110 56, 108 68 Q106 60, 104 52Z" fill="{c}" stroke="{darken(c,12)}" stroke-width="0.4"/>'''

def _hair_pigtails_front(c: str) -> str:
    return f'''
      <path d="M30 16 Q48 6, 64 8 Q80 6, 98 16 Q100 26, 98 34 Q80 22, 64 20 Q48 22, 30 34 Q28 26, 30 16Z" fill="{c}" stroke="{darken(c,10)}" stroke-width="0.4"/>'''

def _hair_undercut_back(c: str) -> str:
    return f'''
      <path d="M30 28 Q64 16, 98 28 Q102 36, 100 44 L28 44 Q26 36, 30 28Z" fill="{darken(c,20)}" opacity="0.5"/>'''

def _hair_undercut_front(c: str) -> str:
    return f'''
      <path d="M34 16 Q52 6, 72 8 Q88 10, 98 22 Q100 30, 96 38 Q80 26, 64 22 Q48 20, 34 26 Q30 22, 34 16Z" fill="{c}" stroke="{darken(c,10)}" stroke-width="0.4"/>
      <path d="M36 26 Q48 18, 62 20 L60 30 Q48 28, 36 26Z" fill="{lighten(c,8)}"/>'''

def _hair_mohawk_back(c: str) -> str:
    return f'''
      <path d="M30 28 Q64 16, 98 28 Q102 36, 100 42 L28 42 Q26 36, 30 28Z" fill="{darken(c,20)}" opacity="0.4"/>'''

def _hair_mohawk_front(c: str) -> str:
    return f'''
      <path d="M50 26 Q56 -4, 64 -2 Q72 -4, 78 26 Q72 18, 64 16 Q56 18, 50 26Z" fill="{c}" stroke="{darken(c,12)}" stroke-width="0.5"/>
      <path d="M54 20 Q60 4, 64 6 Q68 4, 74 20 Q68 14, 64 12 Q60 14, 54 20Z" fill="{lighten(c,12)}"/>'''

def _hair_hime_cut_back(c: str) -> str:
    return f'''
      <path d="M26 18 Q64 2, 102 18 Q108 40, 106 68 Q104 90, 98 104 Q90 112, 80 108 L48 108 Q38 112, 30 104 Q24 90, 22 68 Q20 40, 26 18Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>'''

def _hair_hime_cut_front(c: str) -> str:
    return f'''
      <path d="M28 18 Q48 6, 64 8 Q80 6, 100 18 Q102 30, 100 40 L28 40 Q26 30, 28 18Z" fill="{c}" stroke="{darken(c,10)}" stroke-width="0.4"/>
      <line x1="28" y1="40" x2="28" y2="72" stroke="{c}" stroke-width="8" stroke-linecap="round"/>
      <line x1="100" y1="40" x2="100" y2="72" stroke="{c}" stroke-width="8" stroke-linecap="round"/>
      <path d="M32 40 L28 72 Q30 68, 34 64Z" fill="{lighten(c,8)}"/>
      <path d="M96 40 L100 72 Q98 68, 94 64Z" fill="{lighten(c,8)}"/>'''


HAIR_RENDERERS = {
    "twintails": (_hair_twintails_back, _hair_twintails_front),
    "bob": (_hair_bob_back, _hair_bob_front),
    "ponytail": (_hair_ponytail_back, _hair_ponytail_front),
    "messy": (_hair_messy_back, _hair_messy_front),
    "spiky": (_hair_spiky_back, _hair_spiky_front),
    "long-straight": (_hair_long_straight_back, _hair_long_straight_front),
    "long-wavy": (_hair_long_wavy_back, _hair_long_wavy_front),
    "short-crop": (_hair_short_crop_back, _hair_short_crop_front),
    "buzz": (_hair_buzz_back, _hair_buzz_front),
    "bangs": (_hair_bangs_back, _hair_bangs_front),
    "side-swept": (_hair_side_swept_back, _hair_side_swept_front),
    "bun": (_hair_bun_back, _hair_bun_front),
    "braids": (_hair_braids_back, _hair_braids_front),
    "afro": (_hair_afro_back, _hair_afro_front),
    "pigtails": (_hair_pigtails_back, _hair_pigtails_front),
    "undercut": (_hair_undercut_back, _hair_undercut_front),
    "mohawk": (_hair_mohawk_back, _hair_mohawk_front),
    "hime-cut": (_hair_hime_cut_back, _hair_hime_cut_front),
}


def render_hair_back(style: str, color: str) -> str:
    """Render hair back layer."""
    back_fn, _ = HAIR_RENDERERS.get(style, HAIR_RENDERERS["bob"])
    return f'<g class="chibi-hair-back">{back_fn(color)}</g>'


def render_hair_front(style: str, color: str) -> str:
    """Render hair front layer."""
    _, front_fn = HAIR_RENDERERS.get(style, HAIR_RENDERERS["bob"])
    return f'<g class="chibi-hair-front">{front_fn(color)}</g>'


# ── EYE STYLES ───────────────────────────────────────────────────────────────

def _sparkle_eye(cx: int, cy: int, eye_color: str, rx_outer: float = 8, ry_outer: float = 10) -> str:
    """Render a single sparkle eye."""
    eye_id = "irisR" if cx > 64 else "irisL"
    return f'''
    <ellipse cx="{cx}" cy="{cy}" rx="{rx_outer}" ry="{ry_outer}" fill="#fff" stroke="#2d2d3d" stroke-width="1"/>
    <defs>
      <radialGradient id="{eye_id}" cx="0.45" cy="0.4" r="0.55">
        <stop offset="0%" stop-color="{lighten(eye_color, 25)}"/>
        <stop offset="60%" stop-color="{eye_color}"/>
        <stop offset="100%" stop-color="{darken(eye_color, 30)}"/>
      </radialGradient>
    </defs>
    <ellipse cx="{cx}" cy="{cy + 1}" rx="{rx_outer * 0.7}" ry="{ry_outer * 0.72}" fill="url(#{eye_id})"/>
    <ellipse cx="{cx}" cy="{cy + 2}" rx="{rx_outer * 0.35}" ry="{ry_outer * 0.38}" fill="#1a1a2e"/>
    <ellipse cx="{cx - 2.5}" cy="{cy - 2.5}" rx="2.2" ry="2.6" fill="#fff" opacity="0.92"/>
    <ellipse cx="{cx + 2}" cy="{cy + 1.5}" rx="1.2" ry="1.4" fill="#fff" opacity="0.6"/>
    <path d="M{cx - rx_outer} {cy - ry_outer * 0.4} Q{cx} {cy - ry_outer - 2}, {cx + rx_outer} {cy - ry_outer * 0.4}" stroke="#2d2d3d" stroke-width="1.8" fill="none" stroke-linecap="round"/>'''


def _eye_round_sparkle(ec: str) -> str:
    return _sparkle_eye(48, 46, ec) + _sparkle_eye(80, 46, ec)


def _eye_cat_eye(ec: str) -> str:
    def eye(cx: int, flip: int) -> str:
        return f'''
      <path d="M{cx - 9 * flip} 42 Q{cx} 34, {cx + 9 * flip} 42 Q{cx} 56, {cx - 9 * flip} 42Z" fill="#fff" stroke="#2d2d3d" stroke-width="0.8"/>
      <ellipse cx="{cx + 1 * flip}" cy="44" rx="5" ry="6.5" fill="{ec}"/>
      <ellipse cx="{cx + 1 * flip}" cy="45" rx="2" ry="4.5" fill="#1a1a2e"/>
      <ellipse cx="{cx - 1 * flip}" cy="42" rx="1.8" ry="2" fill="#fff" opacity="0.9"/>
      <path d="M{cx - 8 * flip} 42 Q{cx} 34, {cx + 8 * flip} 42" stroke="#2d2d3d" stroke-width="1.6" fill="none" stroke-linecap="round"/>'''
    return eye(48, 1) + eye(80, -1)


def _eye_droopy(ec: str) -> str:
    def eye(cx: int) -> str:
        return f'''
      <ellipse cx="{cx}" cy="48" rx="7.5" ry="8.5" fill="#fff" stroke="#2d2d3d" stroke-width="0.8"/>
      <ellipse cx="{cx}" cy="49" rx="5.5" ry="6.5" fill="{ec}"/>
      <ellipse cx="{cx}" cy="50" rx="2.8" ry="3.5" fill="#1a1a2e"/>
      <ellipse cx="{cx - 2}" cy="46" rx="2" ry="2.2" fill="#fff" opacity="0.85"/>
      <path d="M{cx - 7} 43 Q{cx} 39, {cx + 7} 45" stroke="#2d2d3d" stroke-width="1.5" fill="none" stroke-linecap="round"/>'''
    return eye(48) + eye(80)


def _eye_determined(ec: str) -> str:
    def eye(cx: int, d: int) -> str:
        return f'''
      <ellipse cx="{cx}" cy="46" rx="7" ry="8" fill="#fff" stroke="#2d2d3d" stroke-width="0.8"/>
      <ellipse cx="{cx}" cy="47" rx="5" ry="6" fill="{ec}"/>
      <ellipse cx="{cx}" cy="48" rx="2.5" ry="3.2" fill="#1a1a2e"/>
      <ellipse cx="{cx - 1.5}" cy="44" rx="1.8" ry="2" fill="#fff" opacity="0.9"/>
      <line x1="{cx - 8}" y1="{42 - d * 2}" x2="{cx + 8}" y2="{42 + d * 2}" stroke="#2d2d3d" stroke-width="2" stroke-linecap="round"/>'''
    return eye(48, 1) + eye(80, -1)


def _eye_happy_closed(ec: str) -> str:
    return '''
    <path d="M40 46 Q48 38, 56 46" stroke="#2d2d3d" stroke-width="2.2" fill="none" stroke-linecap="round"/>
    <path d="M72 46 Q80 38, 88 46" stroke="#2d2d3d" stroke-width="2.2" fill="none" stroke-linecap="round"/>'''


def _eye_wink(ec: str) -> str:
    return _sparkle_eye(48, 46, ec) + '''
    <path d="M72 46 Q80 38, 88 46" stroke="#2d2d3d" stroke-width="2.2" fill="none" stroke-linecap="round"/>'''


def _eye_surprised(ec: str) -> str:
    def eye(cx: int) -> str:
        return f'''
      <ellipse cx="{cx}" cy="45" rx="9" ry="11" fill="#fff" stroke="#2d2d3d" stroke-width="1"/>
      <ellipse cx="{cx}" cy="46" rx="6" ry="7.5" fill="{ec}"/>
      <ellipse cx="{cx}" cy="47" rx="3.5" ry="4.2" fill="#1a1a2e"/>
      <ellipse cx="{cx - 2.5}" cy="43" rx="2.5" ry="3" fill="#fff" opacity="0.9"/>
      <ellipse cx="{cx + 2}" cy="45" rx="1.2" ry="1.5" fill="#fff" opacity="0.6"/>'''
    return eye(48) + eye(80)


def _eye_cool(ec: str) -> str:
    def eye(cx: int) -> str:
        return f'''
      <ellipse cx="{cx}" cy="46" rx="8" ry="9" fill="#fff" stroke="#2d2d3d" stroke-width="0.8"/>
      <ellipse cx="{cx}" cy="48" rx="5.5" ry="6" fill="{ec}"/>
      <ellipse cx="{cx}" cy="49" rx="2.8" ry="3.2" fill="#1a1a2e"/>
      <ellipse cx="{cx - 2}" cy="45" rx="1.8" ry="2" fill="#fff" opacity="0.85"/>
      <path d="M{cx - 9} 42 L{cx + 9} 42 L{cx + 8} 46 Q{cx} 40, {cx - 8} 46Z" fill="{darken(ec, 60)}" opacity="0.18"/>
      <line x1="{cx - 9}" y1="42" x2="{cx + 9}" y2="42" stroke="#2d2d3d" stroke-width="2" stroke-linecap="round"/>'''
    return eye(48) + eye(80)


def _eye_sleepy(ec: str) -> str:
    return '''
    <path d="M40 48 Q48 44, 56 48" stroke="#2d2d3d" stroke-width="2" fill="none" stroke-linecap="round"/>
    <path d="M72 48 Q80 44, 88 48" stroke="#2d2d3d" stroke-width="2" fill="none" stroke-linecap="round"/>
    <line x1="57" y1="44" x2="59" y2="42" stroke="#2d2d3d" stroke-width="1" stroke-linecap="round"/>
    <line x1="89" y1="44" x2="91" y2="42" stroke="#2d2d3d" stroke-width="1" stroke-linecap="round"/>'''


def _eye_heart(ec: str) -> str:
    def heart(cx: int) -> str:
        return f'''
      <path d="M{cx - 7} 44 C{cx - 7} 39, {cx} 38, {cx} 44 C{cx} 38, {cx + 7} 39, {cx + 7} 44 C{cx + 7} 50, {cx} 55, {cx} 55 C{cx} 55, {cx - 7} 50, {cx - 7} 44Z" fill="{ec}" stroke="{darken(ec, 20)}" stroke-width="0.5"/>
      <ellipse cx="{cx - 2.5}" cy="43" rx="1.5" ry="1.8" fill="#fff" opacity="0.7"/>'''
    return heart(48) + heart(80)


def _eye_star(ec: str) -> str:
    def star(cx: int, cy: int) -> str:
        pts = []
        for i in range(5):
            a_outer = ((i * 72 - 90) * math.pi) / 180
            a_inner = (((i * 72 + 36) - 90) * math.pi) / 180
            pts.append(f"{cx + 9 * math.cos(a_outer)},{cy + 9 * math.sin(a_outer)}")
            pts.append(f"{cx + 4.5 * math.cos(a_inner)},{cy + 4.5 * math.sin(a_inner)}")
        return f'''
        <polygon points="{" ".join(pts)}" fill="{ec}" stroke="{darken(ec, 20)}" stroke-width="0.5"/>
        <circle cx="{cx - 2}" cy="{cy - 2}" r="1.5" fill="#fff" opacity="0.7"/>'''
    return star(48, 46) + star(80, 46)


def _eye_default(ec: str) -> str:
    return _sparkle_eye(48, 46, ec, 7.5, 9) + _sparkle_eye(80, 46, ec, 7.5, 9)


EYE_RENDERERS = {
    "round-sparkle": _eye_round_sparkle,
    "cat-eye": _eye_cat_eye,
    "droopy": _eye_droopy,
    "determined": _eye_determined,
    "happy-closed": _eye_happy_closed,
    "wink": _eye_wink,
    "surprised": _eye_surprised,
    "cool": _eye_cool,
    "sleepy": _eye_sleepy,
    "heart": _eye_heart,
    "star": _eye_star,
    "default": _eye_default,
}


def render_eyes(style: str, eye_color: str) -> str:
    """Render eyes."""
    renderer = EYE_RENDERERS.get(style, EYE_RENDERERS["default"])
    return f'<g class="chibi-eyes">{renderer(eye_color)}</g>'


# ── EYEBROWS ─────────────────────────────────────────────────────────────────

EYEBROW_RENDERERS = {
    "default": lambda: '''
    <path d="M40 34 Q48 30, 56 34" stroke="#3d3d50" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    <path d="M72 34 Q80 30, 88 34" stroke="#3d3d50" stroke-width="1.8" fill="none" stroke-linecap="round"/>''',

    "flat": lambda: '''
    <line x1="40" y1="33" x2="56" y2="33" stroke="#3d3d50" stroke-width="1.8" stroke-linecap="round"/>
    <line x1="72" y1="33" x2="88" y2="33" stroke="#3d3d50" stroke-width="1.8" stroke-linecap="round"/>''',

    "raised": lambda: '''
    <path d="M40 32 Q48 26, 56 32" stroke="#3d3d50" stroke-width="1.8" fill="none" stroke-linecap="round"/>
    <path d="M72 32 Q80 26, 88 32" stroke="#3d3d50" stroke-width="1.8" fill="none" stroke-linecap="round"/>''',

    "angry": lambda: '''
    <line x1="40" y1="36" x2="56" y2="32" stroke="#3d3d50" stroke-width="2" stroke-linecap="round"/>
    <line x1="88" y1="36" x2="72" y2="32" stroke="#3d3d50" stroke-width="2" stroke-linecap="round"/>''',

    "sad": lambda: '''
    <path d="M40 32 Q48 36, 56 34" stroke="#3d3d50" stroke-width="1.6" fill="none" stroke-linecap="round"/>
    <path d="M72 34 Q80 36, 88 32" stroke="#3d3d50" stroke-width="1.6" fill="none" stroke-linecap="round"/>''',

    "none": lambda: "",
}


def render_eyebrows(style: str) -> str:
    """Render eyebrows."""
    renderer = EYEBROW_RENDERERS.get(style, EYEBROW_RENDERERS["default"])
    return f'<g class="chibi-eyebrows">{renderer()}</g>'


# ── MOUTH / EXPRESSIONS ──────────────────────────────────────────────────────

MOUTH_RENDERERS = {
    "smile": lambda: '''
    <path d="M56 60 Q64 68, 72 60" stroke="#4a3040" stroke-width="1.6" fill="none" stroke-linecap="round"/>''',

    "grin": lambda: '''
    <path d="M52 58 Q64 70, 76 58" stroke="#4a3040" stroke-width="1.4" fill="#fff" stroke-linecap="round"/>
    <path d="M52 58 Q64 62, 76 58" stroke="none" fill="#4a3040" opacity="0.1"/>''',

    "cat-mouth": lambda: '''
    <path d="M54 60 L64 64 L74 60" stroke="#4a3040" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    <line x1="64" y1="58" x2="64" y2="64" stroke="#4a3040" stroke-width="1.2" stroke-linecap="round"/>''',

    "o-mouth": lambda: '''
    <ellipse cx="64" cy="62" rx="5" ry="5.5" fill="#4a3040" stroke="#3d2838" stroke-width="0.6"/>
    <ellipse cx="64" cy="61" rx="3.5" ry="3.5" fill="#b44060" opacity="0.6"/>''',

    "pout": lambda: '''
    <ellipse cx="64" cy="62" rx="5.5" ry="3.5" fill="#d48a9c" stroke="#4a3040" stroke-width="0.8"/>
    <path d="M59 61 Q64 58, 69 61" stroke="#4a3040" stroke-width="0.6" fill="none"/>''',

    "tongue-out": lambda: '''
    <path d="M54 60 Q64 68, 74 60" stroke="#4a3040" stroke-width="1.4" fill="none" stroke-linecap="round"/>
    <ellipse cx="64" cy="67" rx="4" ry="4.5" fill="#e88098" stroke="#c06070" stroke-width="0.4"/>''',

    "fangs": lambda: '''
    <path d="M52 58 Q64 68, 76 58" stroke="#4a3040" stroke-width="1.4" fill="#fff" stroke-linecap="round"/>
    <path d="M56 58 L57.5 63 L59 58" fill="#fff" stroke="#4a3040" stroke-width="0.5"/>
    <path d="M69 58 L70.5 63 L72 58" fill="#fff" stroke="#4a3040" stroke-width="0.5"/>''',

    "neutral": lambda: '''
    <line x1="58" y1="61" x2="70" y2="61" stroke="#4a3040" stroke-width="1.5" stroke-linecap="round"/>''',

    "smirk": lambda: '''
    <path d="M56 61 Q64 61, 72 57" stroke="#4a3040" stroke-width="1.6" fill="none" stroke-linecap="round"/>''',

    "open-smile": lambda: '''
    <path d="M52 58 Q64 72, 76 58" stroke="#4a3040" stroke-width="1.4" fill="#fff" stroke-linecap="round"/>
    <path d="M56 64 Q64 70, 72 64" fill="#d46080" stroke="none"/>''',
}


def render_mouth(expression: str) -> str:
    """Render mouth."""
    renderer = MOUTH_RENDERERS.get(expression, MOUTH_RENDERERS["smile"])
    return f'<g class="chibi-mouth">{renderer()}</g>'


# ── NOSE ─────────────────────────────────────────────────────────────────────

NOSE_RENDERERS = {
    "dot": lambda: '<circle cx="64" cy="55" r="1.5" fill="#c09888" opacity="0.65"/>',
    "line": lambda: '<line x1="63" y1="53" x2="64.5" y2="56" stroke="#c09888" stroke-width="1.2" stroke-linecap="round" opacity="0.6"/>',
    "none": lambda: "",
}


def render_nose(style: str) -> str:
    """Render nose."""
    renderer = NOSE_RENDERERS.get(style, NOSE_RENDERERS["dot"])
    return renderer()


# ── CLOTHING ─────────────────────────────────────────────────────────────────

def _clothing_hoodie(c: str) -> str:
    return f'''
    <path d="M32 96 Q34 82, 48 80 Q56 78, 64 78 Q72 78, 80 80 Q94 82, 96 96 Q98 104, 96 112 L96 128 L32 128 L32 112 Q30 104, 32 96Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>
    <path d="M52 78 Q58 74, 64 76 Q70 74, 76 78 Q72 82, 64 84 Q56 82, 52 78Z" fill="{darken(c,8)}" stroke="{darken(c,15)}" stroke-width="0.3"/>
    <path d="M54 80 Q64 86, 74 80 L72 88 Q64 94, 56 88Z" fill="{darken(c,5)}"/>
    <line x1="64" y1="88" x2="64" y2="128" stroke="{darken(c,12)}" stroke-width="0.8"/>
    <ellipse cx="64" cy="108" rx="3" ry="2" fill="{darken(c,10)}"/>'''


def _clothing_school_uniform(c: str) -> str:
    return f'''
    <path d="M32 96 Q34 82, 48 80 Q56 78, 64 78 Q72 78, 80 80 Q94 82, 96 96 Q98 104, 96 112 L96 128 L32 128 L32 112 Q30 104, 32 96Z" fill="#fff" stroke="#ccc" stroke-width="0.5"/>
    <path d="M48 80 Q56 78, 64 78 Q72 78, 80 80 Q82 86, 80 92 L48 92 Q46 86, 48 80Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>
    <line x1="64" y1="92" x2="64" y2="128" stroke="#ddd" stroke-width="0.6"/>
    <path d="M58 92 L64 106 L70 92" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.3"/>
    <rect x="61.5" y="105" width="5" height="3" rx="1" fill="{lighten(c,20)}" stroke="{c}" stroke-width="0.3"/>'''


def _clothing_t_shirt(c: str) -> str:
    return f'''
    <path d="M32 96 Q34 82, 48 80 Q56 78, 64 78 Q72 78, 80 80 Q94 82, 96 96 Q98 104, 96 112 L96 128 L32 128 L32 112 Q30 104, 32 96Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>
    <path d="M50 78 Q58 74, 64 76 Q70 74, 78 78 Q74 82, 64 84 Q54 82, 50 78Z" fill="{darken(c,8)}" stroke="{darken(c,12)}" stroke-width="0.3"/>
    <path d="M36 90 Q38 86, 44 84" stroke="{darken(c,10)}" stroke-width="0.6" fill="none"/>
    <path d="M92 90 Q90 86, 84 84" stroke="{darken(c,10)}" stroke-width="0.6" fill="none"/>'''


def _clothing_dress(c: str) -> str:
    return f'''
    <path d="M38 92 Q42 80, 56 78 Q60 76, 64 78 Q68 76, 72 78 Q86 80, 90 92 Q96 108, 100 128 L28 128 Q32 108, 38 92Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>
    <path d="M50 78 Q58 74, 64 76 Q70 74, 78 78 Q74 82, 64 84 Q54 82, 50 78Z" fill="{lighten(c,10)}" stroke="{darken(c,12)}" stroke-width="0.3"/>
    <path d="M44 100 Q64 96, 84 100" stroke="{lighten(c,15)}" stroke-width="0.5" fill="none"/>
    <path d="M40 110 Q64 106, 88 110" stroke="{lighten(c,15)}" stroke-width="0.5" fill="none"/>'''


def _clothing_suit(c: str) -> str:
    return f'''
    <path d="M32 96 Q34 82, 48 80 Q56 78, 64 78 Q72 78, 80 80 Q94 82, 96 96 Q98 104, 96 112 L96 128 L32 128 L32 112 Q30 104, 32 96Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>
    <path d="M64 80 L56 128 L54 128 L62 82Z" fill="{darken(c,8)}"/>
    <path d="M64 80 L72 128 L74 128 L66 82Z" fill="{darken(c,8)}"/>
    <rect x="56" y="80" width="16" height="10" rx="2" fill="#fff" stroke="#ccc" stroke-width="0.3"/>
    <circle cx="64" cy="104" r="1.5" fill="{lighten(c,30)}"/>
    <circle cx="64" cy="112" r="1.5" fill="{lighten(c,30)}"/>'''


def _clothing_kimono(c: str) -> str:
    return f'''
    <path d="M32 96 Q34 82, 48 80 Q56 78, 64 78 Q72 78, 80 80 Q94 82, 96 96 Q98 108, 96 128 L32 128 Q30 108, 32 96Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>
    <path d="M50 80 L64 104 L78 80" fill="{lighten(c,15)}" stroke="{darken(c,10)}" stroke-width="0.3"/>
    <rect x="52" y="102" width="24" height="6" rx="1" fill="{darken(c,10)}" stroke="{darken(c,20)}" stroke-width="0.3"/>
    <path d="M32 96 Q44 92, 50 80" stroke="{darken(c,10)}" stroke-width="0.4" fill="none"/>
    <path d="M96 96 Q84 92, 78 80" stroke="{darken(c,10)}" stroke-width="0.4" fill="none"/>'''


def _clothing_overalls(c: str) -> str:
    return f'''
    <path d="M32 96 Q34 82, 48 80 Q56 78, 64 78 Q72 78, 80 80 Q94 82, 96 96 Q98 104, 96 112 L96 128 L32 128 L32 112 Q30 104, 32 96Z" fill="{lighten(c,40)}" stroke="#ccc" stroke-width="0.5"/>
    <path d="M42 88 L42 128 L86 128 L86 88 Q80 82, 64 82 Q48 82, 42 88Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>
    <line x1="54" y1="88" x2="54" y2="92" stroke="{darken(c,20)}" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="74" y1="88" x2="74" y2="92" stroke="{darken(c,20)}" stroke-width="1.5" stroke-linecap="round"/>
    <rect x="56" y="104" width="16" height="10" rx="2" fill="{darken(c,8)}" stroke="{darken(c,15)}" stroke-width="0.3"/>'''


def _clothing_tank_top(c: str) -> str:
    return f'''
    <path d="M32 96 Q34 82, 48 80 Q56 78, 64 78 Q72 78, 80 80 Q94 82, 96 96 Q98 104, 96 112 L96 128 L32 128 L32 112 Q30 104, 32 96Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>
    <path d="M32 96 Q38 88, 46 84" stroke="{darken(c,10)}" stroke-width="1" fill="none"/>
    <path d="M96 96 Q90 88, 82 84" stroke="{darken(c,10)}" stroke-width="1" fill="none"/>
    <path d="M52 78 Q58 76, 64 78 Q70 76, 76 78 L74 82 Q64 84, 54 82Z" fill="{darken(c,6)}"/>'''


def _clothing_sweater(c: str) -> str:
    return f'''
    <path d="M30 96 Q32 80, 48 78 Q56 76, 64 78 Q72 76, 80 78 Q96 80, 98 96 Q100 106, 98 114 L98 128 L30 128 L30 114 Q28 106, 30 96Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>
    <path d="M50 78 Q58 72, 64 74 Q70 72, 78 78 Q74 82, 64 84 Q54 82, 50 78Z" fill="{c}" stroke="{darken(c,10)}" stroke-width="0.8"/>
    <path d="M34 100 Q64 96, 94 100" stroke="{darken(c,6)}" stroke-width="0.5" fill="none"/>
    <path d="M34 106 Q64 102, 94 106" stroke="{darken(c,6)}" stroke-width="0.5" fill="none"/>
    <path d="M34 112 Q64 108, 94 112" stroke="{darken(c,6)}" stroke-width="0.5" fill="none"/>'''


def _clothing_cape(c: str) -> str:
    return f'''
    <path d="M32 96 Q34 82, 48 80 Q56 78, 64 78 Q72 78, 80 80 Q94 82, 96 96 Q98 104, 96 112 L96 128 L32 128 L32 112 Q30 104, 32 96Z" fill="#334155" stroke="#1e293b" stroke-width="0.5"/>
    <path d="M26 84 Q30 78, 40 80 L36 128 L20 128 Q16 108, 26 84Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>
    <path d="M102 84 Q98 78, 88 80 L92 128 L108 128 Q112 108, 102 84Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>
    <circle cx="48" cy="84" r="2.5" fill="{lighten(c,30)}" stroke="{darken(c,10)}" stroke-width="0.4"/>
    <circle cx="80" cy="84" r="2.5" fill="{lighten(c,30)}" stroke="{darken(c,10)}" stroke-width="0.4"/>'''


def _clothing_sailor(c: str) -> str:
    return f'''
    <path d="M32 96 Q34 82, 48 80 Q56 78, 64 78 Q72 78, 80 80 Q94 82, 96 96 Q98 104, 96 112 L96 128 L32 128 L32 112 Q30 104, 32 96Z" fill="#fff" stroke="#ccc" stroke-width="0.5"/>
    <path d="M36 84 Q40 78, 52 78 L64 100 L76 78 Q88 78, 92 84 L92 98 Q88 94, 80 92 L64 104 L48 92 Q40 94, 36 98Z" fill="{c}" stroke="{darken(c,12)}" stroke-width="0.5"/>
    <path d="M60 98 L64 106 L68 98" fill="{c}"/>
    <line x1="38" y1="92" x2="46" y2="92" stroke="#fff" stroke-width="0.8"/>
    <line x1="82" y1="92" x2="90" y2="92" stroke="#fff" stroke-width="0.8"/>'''


def _clothing_jacket(c: str) -> str:
    return f'''
    <path d="M32 96 Q34 82, 48 80 Q56 78, 64 78 Q72 78, 80 80 Q94 82, 96 96 Q98 104, 96 112 L96 128 L32 128 L32 112 Q30 104, 32 96Z" fill="{c}" stroke="{darken(c,15)}" stroke-width="0.5"/>
    <rect x="60" y="80" width="8" height="48" rx="1" fill="{lighten(c,30)}" stroke="{darken(c,5)}" stroke-width="0.3"/>
    <line x1="64" y1="80" x2="64" y2="128" stroke="{darken(c,12)}" stroke-width="0.8"/>
    <path d="M52 78 Q58 74, 64 76 Q70 74, 76 78 Q74 82, 64 84 Q54 82, 52 78Z" fill="{darken(c,6)}" stroke="{darken(c,12)}" stroke-width="0.3"/>
    <rect x="42" y="100" width="10" height="8" rx="2" fill="{darken(c,8)}" stroke="{darken(c,12)}" stroke-width="0.3"/>
    <rect x="76" y="100" width="10" height="8" rx="2" fill="{darken(c,8)}" stroke="{darken(c,12)}" stroke-width="0.3"/>'''


CLOTHING_RENDERERS = {
    "hoodie": _clothing_hoodie,
    "school-uniform": _clothing_school_uniform,
    "t-shirt": _clothing_t_shirt,
    "dress": _clothing_dress,
    "suit": _clothing_suit,
    "kimono": _clothing_kimono,
    "overalls": _clothing_overalls,
    "tank-top": _clothing_tank_top,
    "sweater": _clothing_sweater,
    "cape": _clothing_cape,
    "sailor": _clothing_sailor,
    "jacket": _clothing_jacket,
}


def render_clothing(style: str, color: str) -> str:
    """Render clothing."""
    renderer = CLOTHING_RENDERERS.get(style, CLOTHING_RENDERERS["t-shirt"])
    return f'<g class="chibi-clothing">{renderer(color)}</g>'


# ── ACCESSORIES ──────────────────────────────────────────────────────────────

ACCESSORY_RENDERERS = {
    "none": lambda: "",

    "glasses": lambda: '''
    <circle cx="48" cy="46" r="10" fill="none" stroke="#334155" stroke-width="1.6"/>
    <circle cx="80" cy="46" r="10" fill="none" stroke="#334155" stroke-width="1.6"/>
    <line x1="58" y1="46" x2="70" y2="46" stroke="#334155" stroke-width="1.2"/>
    <line x1="38" y1="44" x2="30" y2="42" stroke="#334155" stroke-width="1.2" stroke-linecap="round"/>
    <line x1="90" y1="44" x2="98" y2="42" stroke="#334155" stroke-width="1.2" stroke-linecap="round"/>''',

    "sunglasses": lambda: '''
    <rect x="36" y="38" width="24" height="16" rx="4" fill="#1e293b" stroke="#0f172a" stroke-width="1"/>
    <rect x="68" y="38" width="24" height="16" rx="4" fill="#1e293b" stroke="#0f172a" stroke-width="1"/>
    <line x1="60" y1="45" x2="68" y2="45" stroke="#0f172a" stroke-width="1.2"/>
    <line x1="36" y1="43" x2="28" y2="41" stroke="#0f172a" stroke-width="1.2" stroke-linecap="round"/>
    <line x1="92" y1="43" x2="100" y2="41" stroke="#0f172a" stroke-width="1.2" stroke-linecap="round"/>
    <rect x="38" y="40" width="10" height="4" rx="1" fill="#334155" opacity="0.3"/>
    <rect x="70" y="40" width="10" height="4" rx="1" fill="#334155" opacity="0.3"/>''',

    "headband": lambda: '''
    <path d="M28 32 Q48 22, 64 24 Q80 22, 100 32 Q102 34, 100 36 Q80 26, 64 28 Q48 26, 28 36 Q26 34, 28 32Z" fill="#ef4444" stroke="#dc2626" stroke-width="0.4"/>''',

    "bow": lambda: '''
    <g transform="translate(64, 16)">
      <path d="M0 0 C-6 -6, -14 -4, -12 0 C-14 4, -6 6, 0 0Z" fill="#f472b6" stroke="#ec4899" stroke-width="0.5"/>
      <path d="M0 0 C6 -6, 14 -4, 12 0 C14 4, 6 6, 0 0Z" fill="#f472b6" stroke="#ec4899" stroke-width="0.5"/>
      <circle cx="0" cy="0" r="2.5" fill="#ec4899"/>
    </g>''',

    "cat-ears": lambda: '''
    <path d="M30 24 L22 2 Q24 0, 28 2 L42 22Z" fill="#d4a853" stroke="#b8943a" stroke-width="0.5"/>
    <path d="M32 22 L26 6 L38 20Z" fill="#f0b8a8" opacity="0.7"/>
    <path d="M98 24 L106 2 Q104 0, 100 2 L86 22Z" fill="#d4a853" stroke="#b8943a" stroke-width="0.5"/>
    <path d="M96 22 L102 6 L90 20Z" fill="#f0b8a8" opacity="0.7"/>''',

    "horns": lambda: '''
    <path d="M38 22 L30 0 Q34 4, 36 10 L42 20Z" fill="#8b5cf6" stroke="#7c3aed" stroke-width="0.5"/>
    <path d="M90 22 L98 0 Q94 4, 92 10 L86 20Z" fill="#8b5cf6" stroke="#7c3aed" stroke-width="0.5"/>
    <path d="M38 22 L32 4 L36 14Z" fill="#a78bfa" opacity="0.5"/>
    <path d="M90 22 L96 4 L92 14Z" fill="#a78bfa" opacity="0.5"/>''',

    "crown": lambda: '''
    <g transform="translate(64, 10)">
      <path d="M-18 8 L-14 -4 L-6 4 L0 -8 L6 4 L14 -4 L18 8Z" fill="#fbbf24" stroke="#d97706" stroke-width="0.5"/>
      <rect x="-18" y="6" width="36" height="5" rx="1" fill="#f59e0b" stroke="#d97706" stroke-width="0.4"/>
      <circle cx="-8" cy="8" r="1.5" fill="#ef4444"/>
      <circle cx="0" cy="8" r="1.5" fill="#3b82f6"/>
      <circle cx="8" cy="8" r="1.5" fill="#10b981"/>
    </g>''',

    "scarf": lambda: '''
    <path d="M28 68 Q36 64, 48 66 Q58 68, 64 70 Q70 68, 80 66 Q92 64, 100 68 Q102 72, 100 76 Q92 72, 80 74 Q70 76, 64 78 Q58 76, 48 74 Q36 72, 28 76 Q26 72, 28 68Z" fill="#ef4444" stroke="#dc2626" stroke-width="0.4"/>
    <path d="M58 78 Q60 86, 56 96 Q54 98, 52 96 Q54 86, 52 78Z" fill="#ef4444" stroke="#dc2626" stroke-width="0.3"/>''',

    "mask": lambda: '''
    <path d="M40 52 Q52 48, 64 50 Q76 48, 88 52 Q90 58, 88 64 Q76 68, 64 66 Q52 68, 40 64 Q38 58, 40 52Z" fill="#fff" stroke="#d1d5db" stroke-width="0.5"/>
    <line x1="40" y1="56" x2="34" y2="48" stroke="#d1d5db" stroke-width="0.6" stroke-linecap="round"/>
    <line x1="88" y1="56" x2="94" y2="48" stroke="#d1d5db" stroke-width="0.6" stroke-linecap="round"/>
    <path d="M48 56 Q64 52, 80 56" stroke="#e5e7eb" stroke-width="0.4" fill="none"/>''',

    "earrings": lambda: '''
    <circle cx="27" cy="54" r="2.5" fill="#fbbf24" stroke="#d97706" stroke-width="0.4"/>
    <circle cx="27" cy="58" r="1.5" fill="#fbbf24"/>
    <circle cx="101" cy="54" r="2.5" fill="#fbbf24" stroke="#d97706" stroke-width="0.4"/>
    <circle cx="101" cy="58" r="1.5" fill="#fbbf24"/>''',

    "bandaid": lambda: '''
    <g transform="translate(82, 34) rotate(20)">
      <rect x="-8" y="-3" width="16" height="6" rx="2" fill="#fcd34d" stroke="#d97706" stroke-width="0.3"/>
      <rect x="-3" y="-3" width="6" height="6" rx="1" fill="#fbbf24"/>
      <circle cx="0" cy="0" r="0.8" fill="#d97706" opacity="0.5"/>
    </g>''',
}


def render_accessory(acc_type: str) -> str:
    """Render accessory."""
    renderer = ACCESSORY_RENDERERS.get(acc_type, ACCESSORY_RENDERERS["none"])
    return renderer()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN RENDER FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def render_chibi_svg(
    seed: str,
    variant: ChibiVariant = "neutral",
    options: Optional[Dict] = None
) -> str:
    """
    Render a complete Chibi avatar as a raw SVG string.

    Args:
        seed: Any string (username, userId, etc.)
        variant: "neutral" | "male" | "female"
        options: Partial overrides; unspecified values derived from seed

    Returns:
        Complete <svg>...</svg> string
    """
    o = resolve_options(seed, variant, options)

    # Build layers
    bg = render_background(o["backgroundStyle"], o["background"])
    body = render_body(o["skinTone"])
    clothing = render_clothing(o["clothing"], o["clothingColor"])
    hair_back = render_hair_back(o["hairStyle"], o["hairColor"])
    head = render_head(o["skinTone"], o["blush"])
    eyes = render_eyes(o["eyeStyle"], o["eyeColor"])
    eyebrows = render_eyebrows(o["eyebrowStyle"])
    nose = render_nose(o["noseStyle"])
    mouth = render_mouth(o["expression"])
    hair_front = render_hair_front(o["hairStyle"], o["hairColor"])
    accessory = render_accessory(o["accessory"])

    # Compose all layers (no animations in server-side render)
    svg_parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">',
        f'<g class="chibi-bg">{bg}</g>',
        f'<g class="chibi-body-group">{body}{clothing}</g>',
        f'<g class="chibi-head-group">{hair_back}{head}{eyes}{eyebrows}{nose}{mouth}{hair_front}{accessory}</g>',
        '</svg>'
    ]

    return "\n".join(svg_parts)


def render_chibi_data_uri(
    seed: str,
    variant: ChibiVariant = "neutral",
    options: Optional[Dict] = None
) -> str:
    """
    Render as a data:image/svg+xml URI safe for use in <img src>.
    """
    import urllib.parse
    svg = render_chibi_svg(seed, variant, options)
    return f"data:image/svg+xml,{urllib.parse.quote(svg)}"


# ══════════════════════════════════════════════════════════════════════════════
# TEST
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Quick test
    svg = render_chibi_svg("test-user", "female")
    print(f"Generated SVG length: {len(svg)} characters")
    print("First 500 chars:")
    print(svg[:500])
