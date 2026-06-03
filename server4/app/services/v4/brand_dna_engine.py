"""
Brand DNA Engine for V4 Pipeline — Logo to Auto-Theme Extraction

Extracts brand identity from uploaded company logo to automatically
generate matching design tokens (colors, fonts, mood, visual style).

Integration with V4:
- Called in content_pipeline when company_icon_url is provided
- Extracts palette, mood, style from logo image
- Generates design tokens that feed into design_resolver
"""

from __future__ import annotations

import hashlib
import io
import structlog
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

logger = structlog.get_logger(__name__)


class BrandMood(str, Enum):
    """Detected brand mood/personality from logo colors."""
    PROFESSIONAL = "professional"
    PLAYFUL = "playful"
    CORPORATE = "corporate"
    CREATIVE = "creative"
    DARK = "dark"
    MINIMAL = "minimal"
    TECH = "tech"
    ENERGETIC = "energetic"


class VisualStyle(str, Enum):
    """Detected visual style from logo characteristics."""
    FLAT = "flat"
    GRADIENT = "gradient"
    BOLD = "bold"
    MINIMAL = "minimal"
    MODERN = "modern"


@dataclass
class BrandDNA:
    """Extracted brand identity from logo."""
    primary_color: str
    secondary_color: Optional[str]
    accent_color: Optional[str]
    palette: List[str]
    mood: BrandMood
    visual_style: VisualStyle
    confidence: float
    source_url: str = ""


class BrandDNAEngine:
    """
    Extracts brand DNA from logo image for auto-theme generation.
    """
    
    def __init__(self):
        self.logger = logger
    
    def extract_from_url(self, logo_url: str, image_bytes: bytes) -> BrandDNA:
        """
        Extract brand DNA from uploaded logo image.
        
        Args:
            logo_url: URL of the uploaded logo
            image_bytes: Raw image bytes
            
        Returns:
            BrandDNA with extracted colors, mood, style
        """
        self.logger.info("brand_dna_extract_start", url=logo_url)
        
        try:
            # Load image
            img = Image.open(io.BytesIO(image_bytes))
            img = img.convert("RGB")
            
            # Extract palette via dominant color extraction
            palette = self._extract_palette(img)
            
            # Determine primary, secondary, accent
            primary = palette[0] if palette else "#1A1A2E"
            secondary = palette[1] if len(palette) > 1 else None
            accent = palette[2] if len(palette) > 2 else None
            
            # Detect mood from colors
            mood = self._detect_mood(palette)
            
            # Detect visual style
            visual_style = self._detect_style(img, palette)
            
            # Compute confidence
            confidence = self._compute_confidence(img, palette)
            
            dna = BrandDNA(
                primary_color=primary,
                secondary_color=secondary,
                accent_color=accent,
                palette=palette,
                mood=mood,
                visual_style=visual_style,
                confidence=confidence,
                source_url=logo_url,
            )
            
            self.logger.info(
                "brand_dna_extract_complete",
                primary=primary,
                mood=mood.value,
                style=visual_style.value,
                confidence=confidence,
            )
            
            return dna
            
        except Exception as e:
            self.logger.error("brand_dna_extract_failed", error=str(e))
            # Return safe defaults
            return BrandDNA(
                primary_color="#1A1A2E",
                secondary_color="#4A4A6E",
                accent_color="#6A6A8E",
                palette=["#1A1A2E", "#4A4A6E", "#6A6A8E"],
                mood=BrandMood.PROFESSIONAL,
                visual_style=VisualStyle.MINIMAL,
                confidence=0.0,
                source_url=logo_url,
            )
    
    def _extract_palette(self, img: Image.Image, n_colors: int = 6) -> List[str]:
        """Extract dominant colors from image using simple quantization."""
        # Resize for performance
        img = img.resize((100, 100))
        
        # Get pixel data
        pixels = list(img.getdata())
        
        # Sample pixels for performance
        if len(pixels) > 1000:
            import random
            pixels = random.sample(pixels, 1000)
        
        # Simple color quantization - find most common colors
        color_counter = Counter(pixels)
        most_common = color_counter.most_common(n_colors * 2)  # Get more, then filter similar
        
        # Filter similar colors
        palette = []
        for color, _ in most_common:
            if not palette:
                palette.append(color)
            else:
                # Check if this color is too similar to existing colors
                is_similar = False
                for existing in palette:
                    if self._colors_similar(color, existing):
                        is_similar = True
                        break
                if not is_similar and len(palette) < n_colors:
                    palette.append(color)
        
        # Convert to hex
        hex_palette = []
        for color in palette:
            hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
            hex_palette.append(hex_color)
        
        return hex_palette
    
    def _colors_similar(self, c1: Tuple[int, int, int], c2: Tuple[int, int, int], threshold: int = 30) -> bool:
        """Check if two colors are similar using Euclidean distance."""
        r_diff = c1[0] - c2[0]
        g_diff = c1[1] - c2[1]
        b_diff = c1[2] - c2[2]
        distance = (r_diff**2 + g_diff**2 + b_diff**2) ** 0.5
        return distance < threshold
    
    def _detect_mood(self, palette: List[str]) -> BrandMood:
        """Detect brand mood from color palette."""
        if not palette:
            return BrandMood.PROFESSIONAL
        
        # Analyze color properties
        primary = self._hex_to_rgb(palette[0])
        
        # Calculate luminance
        luminance = 0.299 * primary[0] + 0.587 * primary[1] + 0.114 * primary[2]
        
        # Calculate saturation
        max_val = max(primary)
        min_val = min(primary)
        saturation = (max_val - min_val) / max_val if max_val > 0 else 0
        
        # Mood detection rules
        if luminance < 80:
            # Dark colors → dark, tech, professional
            if saturation > 0.6:
                return BrandMood.TECH
            return BrandMood.DARK
        elif luminance > 200:
            # Light colors → minimal, professional
            return BrandMood.MINIMAL
        else:
            # Medium luminance
            if saturation > 0.7:
                # High saturation → energetic, playful
                if len(palette) > 3:
                    return BrandMood.PLAYFUL
                return BrandMood.ENERGETIC
            else:
                # Lower saturation → professional, corporate
                if len(palette) > 4:
                    return BrandMood.CORPORATE
                return BrandMood.PROFESSIONAL
    
    def _detect_style(self, img: Image.Image, palette: List[str]) -> VisualStyle:
        """Detect visual style from image characteristics."""
        # Calculate color variance across image
        img = img.resize((50, 50))
        pixels = list(img.getdata())
        
        # Calculate color variance as a simple metric
        if len(pixels) > 1:
            r_values = [p[0] for p in pixels]
            g_values = [p[1] for p in pixels]
            b_values = [p[2] for p in pixels]
            
            r_variance = max(r_values) - min(r_values)
            g_variance = max(g_values) - min(g_values)
            b_variance = max(b_values) - min(b_values)
            
            avg_variance = (r_variance + g_variance + b_variance) / 3
        else:
            avg_variance = 0
        
        # Style detection based on palette and variance
        if avg_variance < 30:
            return VisualStyle.FLAT
        elif avg_variance > 150:
            return VisualStyle.BOLD
        elif len(palette) > 4:
            return VisualStyle.GRADIENT
        else:
            return VisualStyle.MODERN
    
    def _compute_confidence(self, img: Image.Image, palette: List[str]) -> float:
        """Compute confidence score for extraction."""
        # Base confidence on image quality and palette distinctness
        if not palette:
            return 0.0
        
        # Check palette distinctness
        distinct_colors = len(set(palette))
        distinctness_score = min(distinct_colors / 6, 1.0)
        
        # Check image resolution
        width, height = img.size
        resolution_score = min(min(width, height) / 200, 1.0)
        
        # Combined confidence
        confidence = (distinctness_score * 0.6) + (resolution_score * 0.4)
        
        return round(confidence, 2)
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def to_design_tokens(self, dna: BrandDNA) -> Dict[str, Any]:
        """
        Convert BrandDNA to design tokens format for design_resolver.
        
        Args:
            dna: Extracted BrandDNA
            
        Returns:
            Design tokens dict compatible with design_resolver
        """
        return {
            "primary": dna.primary_color,
            "secondary": dna.secondary_color or dna.primary_color,
            "accent": dna.accent_color,
            "background": "#0b0d12" if dna.mood == BrandMood.DARK else "#ffffff",
            "surface": "#151821" if dna.mood == BrandMood.DARK else "#f8fafc",
            "mood": dna.mood.value,
            "visual_style": dna.visual_style.value,
            "palette": dna.palette,
        }


# Import for bytes handling
import io
