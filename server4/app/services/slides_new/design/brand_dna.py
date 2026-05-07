"""
Brand DNA Extraction Engine — Phase 5.

Extracts brand identity from uploaded company materials (PDF, PPTX, PNG, brand
guidelines URL). Uses VLM-powered analysis to detect exact brand colors,
typography preferences, whitespace ratios, logo placement, and visual style.

Pipeline:
1. Ingest uploaded file (PDF pages → images, PPTX slides → images, PNG direct)
2. Dominant-color extraction via k-means clustering on pixel data
3. VLM analysis (Phi-4-reasoning-vision or fallback to text analysis)
4. Brand DNA object compilation
5. Feed into GenerativeThemeEngine for theme generation
"""

from __future__ import annotations

import colorsys
import hashlib
import io
import math
import re
import struct
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Brand DNA Models ──────────────────────────────────────────


class VisualStyle(str, Enum):
    """Detected visual style from brand materials."""
    FLAT = "flat"
    GRADIENT = "gradient"
    GLASSMORPHISM = "glassmorphism"
    MINIMAL = "minimal"
    BOLD = "bold"
    EDITORIAL = "editorial"
    CORPORATE = "corporate"
    PLAYFUL = "playful"
    MODERN = "modern"


class LogoPosition(str, Enum):
    """Detected logo placement pattern."""
    TOP_LEFT = "top-left"
    TOP_CENTER = "top-center"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_CENTER = "bottom-center"
    BOTTOM_RIGHT = "bottom-right"
    CENTER = "center"


class BrandMood(str, Enum):
    """Detected brand mood/personality."""
    PROFESSIONAL = "professional"
    PLAYFUL = "playful"
    CORPORATE = "corporate"
    CREATIVE = "creative"
    DARK = "dark"
    MINIMAL = "minimal"
    TECH = "tech"
    EDITORIAL = "editorial"
    LUXURY = "luxury"
    ENERGETIC = "energetic"


class BrandDNA(BaseModel):
    """
    Complete brand identity extracted from uploaded materials.

    Fields mirror the V7 plan specification for BrandDNA.
    """
    id: str = Field(description="Unique brand DNA identifier")
    primary_color: str = Field(description="Primary brand color (hex)")
    secondary_color: Optional[str] = Field(None, description="Secondary color")
    accent_color: Optional[str] = Field(None, description="Accent color")
    palette: list[str] = Field(default_factory=list, description="Full extracted palette")
    heading_font: str = Field(default="Inter", description="Detected heading font")
    body_font: str = Field(default="Inter", description="Detected body font")
    mono_font: str = Field(default="JetBrains Mono", description="Monospace font")
    whitespace_ratio: float = Field(
        default=0.30, ge=0.0, le=1.0,
        description="Whitespace fraction (0-1)"
    )
    logo_position: LogoPosition = Field(default=LogoPosition.TOP_LEFT)
    detected_mood: BrandMood = Field(default=BrandMood.PROFESSIONAL)
    visual_style: VisualStyle = Field(default=VisualStyle.FLAT)
    source_file: str = Field(default="", description="Original uploaded filename")
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Extraction confidence score"
    )
    raw_analysis: dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            VisualStyle: lambda v: v.value,
            LogoPosition: lambda v: v.value,
            BrandMood: lambda v: v.value,
        }


# ── Color Extraction Algorithms ──────────────────────────────


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) < 6:
        hex_color = hex_color.ljust(6, "0")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return r, g, b


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB to hex string."""
    return f"#{max(0, min(255, r)):02X}{max(0, min(255, g)):02X}{max(0, min(255, b)):02X}"


def _color_distance(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    """Euclidean distance in RGB space (weighted for perceptual accuracy)."""
    # Redmean weighting for perceptual color distance
    rmean = (c1[0] + c2[0]) / 2
    dr = c1[0] - c2[0]
    dg = c1[1] - c2[1]
    db = c1[2] - c2[2]
    return math.sqrt(
        (2 + rmean / 256) * dr * dr
        + 4 * dg * dg
        + (2 + (255 - rmean) / 256) * db * db
    )


def _rgb_to_hsl(r: int, g: int, b: int) -> tuple[float, float, float]:
    """RGB to HSL. Returns (h: 0-360, s: 0-100, l: 0-100)."""
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    return h * 360, s * 100, l * 100


def _is_chromatic(r: int, g: int, b: int, threshold: int = 25) -> bool:
    """Check if a color has enough saturation to be considered chromatic."""
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    return (max_c - min_c) > threshold


def _is_neutral(r: int, g: int, b: int) -> bool:
    """True if color is near-black, near-white, or neutral gray."""
    _, s, l = _rgb_to_hsl(r, g, b)
    return s < 10 or l < 8 or l > 92


class KMeansColor:
    """
    Simplified K-Means color clustering for palette extraction.

    Operates on a list of RGB tuples — no NumPy required.
    Designed for robustness: handles degenerate cases (all same color,
    fewer unique colors than k, etc.)
    """

    def __init__(self, k: int = 6, max_iterations: int = 20):
        self.k = k
        self.max_iterations = max_iterations

    def fit(self, pixels: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
        """
        Run K-Means on pixel data and return k centroids.

        Uses K-Means++ initialization for better convergence.
        """
        if not pixels:
            return [(0, 0, 0)]

        unique = list(set(pixels))
        if len(unique) <= self.k:
            return unique

        # K-Means++ initialization
        centroids = [unique[0]]
        for _ in range(1, self.k):
            distances = []
            for pixel in unique:
                min_dist = min(_color_distance(pixel, c) for c in centroids)
                distances.append(min_dist)
            total = sum(distances)
            if total == 0:
                break
            # Pick pixel proportional to distance
            threshold = (hash(str(distances[:5])) % 1000) / 1000 * total
            cumulative = 0.0
            for i, d in enumerate(distances):
                cumulative += d
                if cumulative >= threshold:
                    centroids.append(unique[i])
                    break

        # Iterate K-Means
        for _ in range(self.max_iterations):
            # Assign each pixel to nearest centroid
            clusters: dict[int, list[tuple[int, int, int]]] = {
                i: [] for i in range(len(centroids))
            }
            for pixel in pixels:
                min_idx = 0
                min_dist = float("inf")
                for ci, centroid in enumerate(centroids):
                    d = _color_distance(pixel, centroid)
                    if d < min_dist:
                        min_dist = d
                        min_idx = ci
                clusters[min_idx].append(pixel)

            # Recompute centroids
            new_centroids = []
            for ci in range(len(centroids)):
                group = clusters[ci]
                if group:
                    avg_r = sum(p[0] for p in group) // len(group)
                    avg_g = sum(p[1] for p in group) // len(group)
                    avg_b = sum(p[2] for p in group) // len(group)
                    new_centroids.append((avg_r, avg_g, avg_b))
                else:
                    new_centroids.append(centroids[ci])

            if new_centroids == centroids:
                break
            centroids = new_centroids

        return centroids

    def extract_palette(
        self,
        pixels: list[tuple[int, int, int]],
        min_saturation: float = 15.0,
    ) -> list[str]:
        """
        Extract a clean palette from pixel data.

        Steps:
        1. K-Means clustering
        2. Sort by frequency (cluster size)
        3. Filter neutrals
        4. Return hex palette
        """
        if not pixels:
            return ["#000000"]

        centroids = self.fit(pixels)

        # Count each centroid's cluster size
        centroid_counts: list[tuple[tuple[int, int, int], int]] = []
        for centroid in centroids:
            count = 0
            for p in pixels:
                # Assign pixel to nearest centroid
                nearest = min(centroids, key=lambda ct: _color_distance(p, ct))
                if nearest == centroid:
                    count += 1
            centroid_counts.append((centroid, max(count, 1)))

        # Sort by frequency (most common first)
        centroid_counts.sort(key=lambda x: x[1], reverse=True)

        # Build palette — chromatic first, then neutrals
        chromatic = []
        neutrals = []
        for (r, g, b), _ in centroid_counts:
            hex_c = _rgb_to_hex(r, g, b)
            if _is_chromatic(r, g, b) and not _is_neutral(r, g, b):
                chromatic.append(hex_c)
            else:
                neutrals.append(hex_c)

        return (chromatic + neutrals)[:self.k]


# ── Whitespace Analysis ──────────────────────────────────────


def estimate_whitespace_ratio(
    pixels: list,
    width: int = 0,
    height: int = 0,
    bg_color: tuple[int, int, int] = (255, 255, 255),
    tolerance: float = 30.0,
) -> float:
    """
    Estimate the fraction of an image that is whitespace (close to bg_color).

    Accepts either:
    - A flat list of RGB tuples (with optional width/height)
    - A 2D list of RGB tuples (list of rows)

    Args:
        pixels: Flat or 2D list of RGB tuples
        width: Image width (used for flat list interpretation)
        height: Image height (unused, kept for compatibility)
        bg_color: Expected background color
        tolerance: Max color distance to consider "whitespace"

    Returns:
        Ratio 0.0-1.0 of whitespace pixels
    """
    if not pixels:
        return 0.3  # default fallback

    # Detect if 2D (list of lists) or flat (list of tuples)
    flat_pixels: list[tuple[int, int, int]] = []
    if pixels and isinstance(pixels[0], (list, tuple)):
        first = pixels[0]
        if isinstance(first, (list, tuple)) and len(first) > 0 and isinstance(first[0], (list, tuple)):
            # 2D grid: list of rows of tuples
            for row in pixels:
                for pixel in row:
                    flat_pixels.append(pixel)
        else:
            # Already flat: list of tuples
            flat_pixels = pixels
    else:
        return 0.3

    if not flat_pixels:
        return 0.3

    total = len(flat_pixels)
    ws_count = sum(1 for p in flat_pixels if _color_distance(p, bg_color) < tolerance)

    return ws_count / total if total > 0 else 0.3


# ── Mood Detection ───────────────────────────────────────────


def detect_mood_from_palette(palette: list[str]) -> BrandMood:
    """
    Infer brand mood from color palette characteristics.

    Algorithm:
    - Average saturation → playful (high), corporate (low)
    - Average lightness → dark, minimal
    - Hue distribution → creative (wide spread), tech (blue-ish)
    - Chromatic ratio → editorial (low), energetic (high)
    """
    if not palette:
        return BrandMood.PROFESSIONAL

    hsls = []
    for hex_c in palette:
        try:
            r, g, b = _hex_to_rgb(hex_c)
            hsls.append(_rgb_to_hsl(r, g, b))
        except Exception:
            continue

    if not hsls:
        return BrandMood.PROFESSIONAL

    avg_s = sum(s for _, s, _ in hsls) / len(hsls)
    avg_l = sum(l for _, _, l in hsls) / len(hsls)
    hues = [h for h, _, _ in hsls]
    hue_range = max(hues) - min(hues) if len(hues) > 1 else 0

    # Mostly dark colors
    if avg_l < 25:
        return BrandMood.DARK

    # Very muted / low saturation
    if avg_s < 15:
        return BrandMood.MINIMAL

    # Very bright and saturated → energetic
    if avg_s > 70 and avg_l > 40:
        return BrandMood.ENERGETIC

    # Wide hue distribution → creative
    if hue_range > 150:
        return BrandMood.CREATIVE

    # Blue-dominant hues (180-260)
    blue_count = sum(1 for h in hues if 180 <= h <= 260)
    if blue_count > len(hues) / 2:
        return BrandMood.TECH

    # Gold / warm dominant (30-60)
    warm_count = sum(1 for h in hues if 20 <= h <= 60)
    if warm_count > len(hues) / 2:
        return BrandMood.LUXURY

    # Low saturation + light→ editorial
    if avg_s < 30 and avg_l > 50:
        return BrandMood.EDITORIAL

    # Low saturation + moderate → corporate
    if avg_s < 40:
        return BrandMood.CORPORATE

    # High saturation → playful
    if avg_s > 55:
        return BrandMood.PLAYFUL

    return BrandMood.PROFESSIONAL


# ── Font Detection (Heuristic) ───────────────────────────────


# Common presentation fonts mapped to detected patterns
PROFESSIONAL_FONTS = {"Inter", "Helvetica Neue", "Arial", "Open Sans", "Roboto"}
CREATIVE_FONTS = {"Fraunces", "Playfair Display", "Abril Fatface"}
TECH_FONTS = {"Outfit", "Space Grotesk", "JetBrains Mono", "Fira Code"}
EDITORIAL_FONTS = {"Playfair Display", "Source Serif Pro", "Merriweather", "EB Garamond"}

MOOD_TO_FONT_PAIR: dict[BrandMood, tuple[str, str]] = {
    BrandMood.PROFESSIONAL: ("Inter", "Inter"),
    BrandMood.PLAYFUL: ("DM Sans", "Nunito"),
    BrandMood.CORPORATE: ("Sora", "Inter"),
    BrandMood.CREATIVE: ("Fraunces", "Karla"),
    BrandMood.DARK: ("Outfit", "DM Sans"),
    BrandMood.MINIMAL: ("Inter", "Inter"),
    BrandMood.TECH: ("Outfit", "DM Sans"),
    BrandMood.EDITORIAL: ("Playfair Display", "Source Serif Pro"),
    BrandMood.LUXURY: ("Cormorant Garamond", "Proza Libre"),
    BrandMood.ENERGETIC: ("Cabinet Grotesk", "Satoshi"),
}


def infer_fonts_from_mood(mood: BrandMood) -> tuple[str, str, str]:
    """Return (heading_font, body_font, mono_font) based on detected mood."""
    heading, body = MOOD_TO_FONT_PAIR.get(mood, ("Inter", "Inter"))
    mono = "JetBrains Mono"
    if mood == BrandMood.TECH:
        mono = "Fira Code"
    return heading, body, mono


# ── Visual Style Detection ───────────────────────────────────


def detect_visual_style(
    palette: list[str],
    whitespace_ratio: float,
    color_count: int,
) -> VisualStyle:
    """
    Infer visual style from extracted brand signals.

    Heuristics:
    - High whitespace + low color count → minimal
    - Many gradient-adjacent colors → gradient
    - Very bold primary + high contrast → bold
    - Muted palette + serif → editorial
    """
    if whitespace_ratio > 0.55 and color_count <= 3:
        return VisualStyle.MINIMAL
    if whitespace_ratio < 0.15:
        return VisualStyle.BOLD

    # Check for gradient-like palette (adjacent colors with smooth transitions)
    if len(palette) >= 3:
        hsls = []
        for hex_c in palette:
            r, g, b = _hex_to_rgb(hex_c)
            hsls.append(_rgb_to_hsl(r, g, b))
        if len(hsls) >= 3:
            l_range = max(l for _, _, l in hsls) - min(l for _, _, l in hsls)
            s_avg = sum(s for _, s, _ in hsls) / len(hsls)
            if l_range > 50 and s_avg > 40:
                return VisualStyle.GRADIENT

    if color_count <= 2:
        return VisualStyle.FLAT

    return VisualStyle.CORPORATE


# ── Brand DNA Extractor ──────────────────────────────────────


class BrandDNAExtractor:
    """
    Extract brand identity from uploaded company materials.

    Supports analysis of:
    - Raw pixel data (from pre-processed images)
    - Color lists (from document parsing)
    - Text content (from OCR/text extraction)

    The extraction pipeline is modular — callers provide pre-processed
    data (pixel lists, text content) and this class handles the
    intelligence layer (clustering, mood detection, style inference).
    """

    def __init__(self, k_clusters: int = 6):
        self._kmeans = KMeansColor(k=k_clusters)

    def extract_from_pixels(
        self,
        pixels: list[tuple[int, int, int]] | bytes,
        pixel_grid_or_width: list[list[tuple[int, int, int]]] | int | None = None,
        source_file_or_height: str | int = "",
        company_name: str = "",
    ) -> BrandDNA:
        """
        Extract brand DNA from raw pixel data.

        Supports two call conventions:
        1. extract_from_pixels(rgb_tuples, pixel_grid?, source_file?, company_name?)
        2. extract_from_pixels(rgba_bytes, width, height)

        Args:
            pixels: Flat list of RGB tuples OR raw RGBA bytes
            pixel_grid_or_width: 2D grid for whitespace, or image width (bytes mode)
            source_file_or_height: Source filename, or image height (bytes mode)
            company_name: Company name for theme naming

        Returns:
            Complete BrandDNA object
        """
        # Handle raw bytes input: extract_from_pixels(bytes, width, height)
        if isinstance(pixels, (bytes, bytearray)):
            width = int(pixel_grid_or_width) if pixel_grid_or_width else 1
            height = int(source_file_or_height) if source_file_or_height else 1
            rgb_pixels: list[tuple[int, int, int]] = []
            stride = 4  # RGBA
            for i in range(0, len(pixels), stride):
                r, g, b = pixels[i], pixels[i + 1], pixels[i + 2]
                rgb_pixels.append((r, g, b))
            # Build 2D grid for whitespace analysis
            pixel_grid: list[list[tuple[int, int, int]]] | None = None
            if width > 0 and height > 0:
                pixel_grid = []
                for row in range(height):
                    row_pixels = []
                    for col in range(width):
                        idx = row * width + col
                        if idx < len(rgb_pixels):
                            row_pixels.append(rgb_pixels[idx])
                    pixel_grid.append(row_pixels)
            pixels = rgb_pixels
            pixel_grid_or_width = pixel_grid
            source_file_or_height = ""

        # Normalize parameters for tuple input path
        pixel_grid = pixel_grid_or_width if isinstance(pixel_grid_or_width, list) else None
        source_file = source_file_or_height if isinstance(source_file_or_height, str) else ""
        # 1. Extract palette via K-Means
        palette = self._kmeans.extract_palette(pixels)

        # 2. Identify primary, secondary, accent
        primary = palette[0] if palette else "#1A1A2E"
        secondary = palette[1] if len(palette) > 1 else None
        accent = palette[2] if len(palette) > 2 else None

        # 3. Whitespace ratio
        if pixel_grid:
            # Detect background color (most common in corners)
            corners = []
            if pixel_grid and pixel_grid[0]:
                h, w = len(pixel_grid), len(pixel_grid[0])
                for row_idx in [0, min(1, h - 1), max(0, h - 2), h - 1]:
                    for col_idx in [0, min(1, w - 1), max(0, w - 2), w - 1]:
                        if row_idx < h and col_idx < w:
                            corners.append(pixel_grid[row_idx][col_idx])
            bg_color = _most_common_color(corners) if corners else (255, 255, 255)
            ws_ratio = estimate_whitespace_ratio(pixel_grid, bg_color)
        else:
            ws_ratio = 0.30  # sensible default

        # 4. Mood detection
        mood = detect_mood_from_palette(palette)

        # 5. Visual style
        style = detect_visual_style(palette, ws_ratio, len(palette))

        # 6. Font inference
        heading_font, body_font, mono_font = infer_fonts_from_mood(mood)

        # 7. Logo position (default heuristic — top-left is most common)
        logo_pos = LogoPosition.TOP_LEFT

        # 8. Confidence score
        confidence = self._compute_confidence(pixels, palette, pixel_grid)

        # 9. Build ID
        dna_id = hashlib.md5(
            f"{primary}{secondary}{source_file}".encode()
        ).hexdigest()[:12]

        return BrandDNA(
            id=f"brand-{dna_id}",
            primary_color=primary,
            secondary_color=secondary,
            accent_color=accent,
            palette=palette,
            heading_font=heading_font,
            body_font=body_font,
            mono_font=mono_font,
            whitespace_ratio=round(ws_ratio, 3),
            logo_position=logo_pos,
            detected_mood=mood,
            visual_style=style,
            source_file=source_file,
            confidence=round(confidence, 3),
            raw_analysis={
                "cluster_count": len(palette),
                "pixel_sample_size": len(pixels),
                "whitespace_ratio": ws_ratio,
            },
        )

    def extract_from_colors(
        self,
        hex_colors: list[str],
        source_file: str = "",
        company_name: str = "",
    ) -> BrandDNA:
        """
        Extract brand DNA from a pre-existing list of hex colors.
        Useful when colors are already known (e.g., parsed from CSS/PDF).
        """
        # Convert hex colors to pixel-like tuples for palette extraction
        pixels = [_hex_to_rgb(c) for c in hex_colors if len(c) >= 4]
        # Repeat to give clustering enough data
        expanded_pixels = pixels * max(1, 50 // len(pixels)) if pixels else []
        return self.extract_from_pixels(
            expanded_pixels,
            None,
            source_file,
            company_name,
        )

    def extract_from_text_analysis(
        self,
        color_mentions: list[str],
        font_mentions: list[str],
        style_keywords: list[str],
        source_file: str = "",
    ) -> BrandDNA:
        """
        Extract brand DNA from text analysis of brand guidelines.

        Useful when processing OCR output or text content from brand docs.
        """
        # Parse color mentions (hex values)
        hex_pattern = re.compile(r"#[0-9A-Fa-f]{3,8}")
        parsed_colors = []
        for mention in color_mentions:
            matches = hex_pattern.findall(mention)
            parsed_colors.extend(matches)

        if parsed_colors:
            dna = self.extract_from_colors(
                parsed_colors, source_file=source_file
            )
        else:
            # Fallback with defaults
            dna = BrandDNA(
                id=f"brand-text-{hashlib.md5(source_file.encode()).hexdigest()[:8]}",
                primary_color="#1A1A2E",
                source_file=source_file,
                confidence=0.2,
            )

        # Override fonts if mentioned
        if font_mentions:
            dna.heading_font = font_mentions[0]
            if len(font_mentions) > 1:
                dna.body_font = font_mentions[1]

        # Override mood from keywords
        keyword_mood_map = {
            "modern": BrandMood.MINIMAL,
            "bold": BrandMood.ENERGETIC,
            "elegant": BrandMood.LUXURY,
            "playful": BrandMood.PLAYFUL,
            "corporate": BrandMood.CORPORATE,
            "tech": BrandMood.TECH,
            "creative": BrandMood.CREATIVE,
            "professional": BrandMood.PROFESSIONAL,
            "dark": BrandMood.DARK,
            "editorial": BrandMood.EDITORIAL,
        }
        for kw in style_keywords:
            kw_lower = kw.lower()
            if kw_lower in keyword_mood_map:
                dna.detected_mood = keyword_mood_map[kw_lower].value
                break

        return dna

    def _compute_confidence(
        self,
        pixels: list[tuple[int, int, int]],
        palette: list[str],
        pixel_grid: list[list[tuple[int, int, int]]] | None,
    ) -> float:
        """
        Compute extraction confidence score (0-1).

        Factors:
        - Pixel sample size (more = higher confidence)
        - Palette diversity (not all same color)
        - Have spatial data (grid) for whitespace
        """
        score = 0.0

        # Sample size factor (0-0.4)
        if len(pixels) >= 1000:
            score += 0.4
        elif len(pixels) >= 100:
            score += 0.3
        elif len(pixels) >= 10:
            score += 0.15

        # Palette factor (0-0.3)
        unique_colors = set(palette)
        if len(unique_colors) >= 3:
            score += 0.3
        elif len(unique_colors) >= 2:
            score += 0.2
        elif len(unique_colors) >= 1:
            score += 0.1

        # Spatial data factor (0-0.3)
        if pixel_grid and len(pixel_grid) > 1:
            score += 0.3
        else:
            score += 0.1  # still some confidence from flat pixels

        return min(1.0, score)


# ── VLM Analysis Prompt Builder ──────────────────────────────


class VLMBrandAnalysisPrompt:
    """
    Constructs structured prompts for VLM-based brand analysis.

    Used when a VLM (Phi-4-reasoning-vision-15B) is available to
    analyze screenshots of brand materials for richer extraction.
    """

    SYSTEM_PROMPT = (
        "You are a brand identity analyst. Analyze the uploaded brand material "
        "and extract the exact visual identity: colors (hex), typography families, "
        "whitespace patterns, logo placement, and overall visual mood. "
        "Be precise with hex color values — sample actual pixel colors, "
        "don't guess. Return structured JSON only."
    )

    ANALYSIS_PROMPT = """Analyze this brand material and extract the brand identity.

Return ONLY valid JSON:
{{
  "primary_color": "#XXXXXX",
  "secondary_color": "#XXXXXX",
  "accent_color": "#XXXXXX",
  "heading_font": "Font Name",
  "body_font": "Font Name",
  "whitespace_ratio": 0.35,
  "logo_position": "top-left",
  "detected_mood": "professional",
  "visual_style": "flat",
  "confidence": 0.8,
  "notes": "Brief description of the brand aesthetic"
}}

Mood options: professional, playful, corporate, creative, dark, minimal, tech, editorial, luxury, energetic
Style options: flat, gradient, glassmorphism, minimal, bold, editorial, corporate, playful
Position options: top-left, top-center, top-right, bottom-left, bottom-center, bottom-right, center"""

    @classmethod
    def build_messages(cls, context: str = "") -> list[dict[str, str]]:
        """Build message list for VLM analysis."""
        user_content = cls.ANALYSIS_PROMPT
        if context:
            user_content += f"\n\nAdditional context: {context}"
        return [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    @classmethod
    def parse_vlm_response(cls, response_text: str) -> dict[str, Any]:
        """
        Parse VLM JSON response with fallback for malformed output.
        """
        import json

        # Try direct JSON parse
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding first { to last }
        start = response_text.find("{")
        end = response_text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(response_text[start : end + 1])
            except json.JSONDecodeError:
                pass

        return {}


# ── Helper ───────────────────────────────────────────────────


def _most_common_color(
    colors: list[tuple[int, int, int]],
) -> tuple[int, int, int]:
    """Return the most common color from a list. Quantizes to reduce noise."""
    quantized = [(r // 16 * 16, g // 16 * 16, b // 16 * 16) for r, g, b in colors]
    counter = Counter(quantized)
    return counter.most_common(1)[0][0] if counter else (255, 255, 255)
