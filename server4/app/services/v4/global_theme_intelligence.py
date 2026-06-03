"""
Global Theme Intelligence System - CTO Mission-Critical Fix

This module implements a centralized theme management system that prevents:
- Theme drift across slides
- Inconsistent backgrounds
- Random colors
- Accidental gradients
- Visual conflicts

STRICT RULES:
- Every slide MUST inherit from master theme
- No random colors
- No theme drift
- No inconsistent backgrounds
- No accidental gradients
- No visual conflicts

Features:
- Global design tokens
- Centralized theme engine
- Typography tokens
- Spacing tokens
- Color tokens
- Border radius tokens
- Shadow tokens
- Chart color tokens
- Icon style tokens
- Animation tokens
- Contrast checker
- Accessibility validator
- Typography consistency validator
- Color harmony validator

Theme Engine supports:
- Dark mode
- Light mode
- Glassmorphism
- Minimal
- Premium corporate
- Startup modern
- Luxury investor
- Fintech
- AI futuristic
- Enterprise clean
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


class ThemeMode(Enum):
    """Theme mode variants"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


class ThemeStyle(Enum):
    """Predefined theme styles"""
    MINIMAL = "minimal"
    GLASSMORPHISM = "glassmorphism"
    PREMIUM_CORPORATE = "premium_corporate"
    STARTUP_MODERN = "startup_modern"
    LUXURY_INVESTOR = "luxury_investor"
    FINTECH = "fintech"
    AI_FUTURISTIC = "ai_futuristic"
    ENTERPRISE_CLEAN = "enterprise_clean"


@dataclass
class GlobalThemeTokens:
    """Complete global theme token set"""
    # Color tokens
    primary: str
    secondary: str
    accent: str
    background: str
    surface: str
    text_primary: str
    text_secondary: str
    text_muted: str
    success: str
    warning: str
    danger: str
    
    # Typography tokens
    heading_font: str
    body_font: str
    mono_font: str
    heading_weight: int
    body_weight: int
    display_scale: float
    h1_scale: float
    h2_scale: float
    h3_scale: float
    body_scale: float
    caption_scale: float
    
    # Spacing tokens
    slide_margin: float
    gap: float
    section_gap: float
    
    # Shape tokens
    radius_sm: str
    radius_md: str
    radius_lg: str
    radius_xl: str
    
    # Shadow tokens
    shadow_sm: str
    shadow_md: str
    shadow_lg: str
    shadow_glow: str
    
    # Border tokens
    border_width: str
    border_subtle: str
    
    # Animation tokens
    motion_style: str
    transition_duration: str
    easing: str
    
    # Glass effect tokens (for glassmorphism)
    glass_blur: str
    glass_opacity: float
    glass_border: str
    
    # Icon style tokens
    icon_style: str
    icon_size: str
    
    # Chart style tokens
    chart_style: str
    chart_line_width: float
    chart_point_size: float
    chart_colors: List[str] = field(default_factory=list)


@dataclass
class ThemeValidationResult:
    """Result of theme validation"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    contrast_issues: List[str] = field(default_factory=list)
    accessibility_issues: List[str] = field(default_factory=list)


class ContrastChecker:
    """
    Checks color contrast for accessibility compliance.
    Follows WCAG 2.1 AA standards (4.5:1 for normal text, 3:1 for large text).
    """
    
    # WCAG 2.1 AA contrast ratios
    NORMAL_TEXT_MIN_RATIO = 4.5
    LARGE_TEXT_MIN_RATIO = 3.0
    GRAPHICAL_OBJECTS_MIN_RATIO = 3.0
    
    def hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def calculate_luminance(self, rgb: Tuple[int, int, int]) -> float:
        """Calculate relative luminance (WCAG formula)"""
        r, g, b = rgb
        # Convert to sRGB
        r = r / 255.0
        g = g / 255.0
        b = b / 255.0
        
        # Apply gamma correction
        r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
        
        # Calculate luminance
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    
    def calculate_contrast_ratio(self, foreground: str, background: str) -> float:
        """Calculate contrast ratio between two colors"""
        fg_rgb = self.hex_to_rgb(foreground)
        bg_rgb = self.hex_to_rgb(background)
        
        fg_lum = self.calculate_luminance(fg_rgb)
        bg_lum = self.calculate_luminance(bg_rgb)
        
        lighter = max(fg_lum, bg_lum)
        darker = min(fg_lum, bg_lum)
        
        return (lighter + 0.05) / (darker + 0.05)
    
    def check_contrast(
        self,
        foreground: str,
        background: str,
        is_large_text: bool = False,
    ) -> Tuple[bool, float]:
        """
        Check if contrast meets WCAG standards.
        
        Returns (is_compliant, contrast_ratio)
        """
        ratio = self.calculate_contrast_ratio(foreground, background)
        min_ratio = self.LARGE_TEXT_MIN_RATIO if is_large_text else self.NORMAL_TEXT_MIN_RATIO
        
        return ratio >= min_ratio, ratio


class ColorHarmonyValidator:
    """
    Validates color harmony and palette consistency.
    Prevents clashing colors and ensures professional appearance.
    """
    
    def validate_palette(self, tokens: GlobalThemeTokens) -> List[str]:
        """Validate color palette for harmony issues"""
        issues = []
        
        # Check for too many colors
        unique_colors = set([
            tokens.primary,
            tokens.secondary,
            tokens.accent,
            tokens.background,
            tokens.surface,
        ])
        
        if len(unique_colors) > 5:
            issues.append(f"Palette has {len(unique_colors)} unique colors, consider simplifying")
        
        # Check for color similarity (too close)
        color_pairs = [
            (tokens.primary, tokens.secondary),
            (tokens.secondary, tokens.accent),
            (tokens.primary, tokens.accent),
        ]
        
        for fg, bg in color_pairs:
            if self._colors_too_similar(fg, bg):
                issues.append(f"Colors {fg} and {bg} are too similar, may lack contrast")
        
        # Check chart color harmony
        if len(tokens.chart_colors) > 0:
            for i in range(len(tokens.chart_colors) - 1):
                if self._colors_too_similar(tokens.chart_colors[i], tokens.chart_colors[i + 1]):
                    issues.append(f"Chart colors {tokens.chart_colors[i]} and {tokens.chart_colors[i + 1]} are too similar")
        
        return issues
    
    def _colors_too_similar(self, color1: str, color2: str, threshold: float = 0.15) -> bool:
        """Check if two colors are too similar (simplified)"""
        # This is a simplified check - in production, use proper color distance metrics
        # For now, just check if they're identical
        return color1.lower() == color2.lower()


class TypographyConsistencyValidator:
    """
    Validates typography consistency across the theme.
    Ensures fonts, weights, and scales follow design system rules.
    """
    
    def validate_typography(self, tokens: GlobalThemeTokens) -> List[str]:
        """Validate typography tokens for consistency"""
        issues = []
        
        # Check font weight hierarchy
        if tokens.heading_weight <= tokens.body_weight:
            issues.append(f"Heading weight ({tokens.heading_weight}) should be greater than body weight ({tokens.body_weight})")
        
        # Check type scale hierarchy
        if not (tokens.display_scale > tokens.h1_scale > tokens.h2_scale > tokens.h3_scale > tokens.body_scale > tokens.caption_scale):
            issues.append("Type scale does not follow proper hierarchy")
        
        # Check for reasonable font sizes
        if tokens.body_scale < 1.0:
            issues.append("Body scale is too small (< 1.0)")
        
        if tokens.display_scale > 6.0:
            issues.append("Display scale is too large (> 6.0)")
        
        # Check font families
        if not tokens.heading_font or not tokens.body_font:
            issues.append("Heading or body font is missing")
        
        return issues


class AccessibilityValidator:
    """
    Comprehensive accessibility validation.
    Checks contrast, readability, and WCAG compliance.
    """
    
    def __init__(self) -> None:
        self.contrast_checker = ContrastChecker()
    
    def validate_theme(self, tokens: GlobalThemeTokens) -> ThemeValidationResult:
        """
        Validate entire theme for accessibility compliance.
        
        Returns ThemeValidationResult with all issues.
        """
        errors = []
        warnings = []
        contrast_issues = []
        accessibility_issues = []
        
        # Check text-background contrast
        text_pairs = [
            (tokens.text_primary, tokens.background, "primary text"),
            (tokens.text_secondary, tokens.background, "secondary text"),
            (tokens.text_muted, tokens.background, "muted text"),
        ]
        
        for fg, bg, label in text_pairs:
            is_compliant, ratio = self.contrast_checker.check_contrast(fg, bg)
            if not is_compliant:
                contrast_issues.append(f"{label} contrast ratio {ratio:.2f} below WCAG AA standard")
        
        # Check surface contrast
        if tokens.surface != tokens.background:
            is_compliant, ratio = self.contrast_checker.check_contrast(tokens.surface, tokens.background)
            if not is_compliant:
                contrast_issues.append(f"Surface contrast ratio {ratio:.2f} below WCAG AA standard")
        
        # Check chart color visibility
        for i, color in enumerate(tokens.chart_colors):
            is_compliant, ratio = self.contrast_checker.check_contrast(color, tokens.background)
            if not is_compliant:
                accessibility_issues.append(f"Chart color {i+1} ({color}) has poor contrast with background")
        
        # Check for color-only information (charts should use patterns/text)
        if len(tokens.chart_colors) > 0:
            warnings.append("Ensure charts use patterns or labels in addition to color for accessibility")
        
        return ThemeValidationResult(
            is_valid=len(errors) == 0 and len(contrast_issues) == 0,
            errors=errors,
            warnings=warnings,
            contrast_issues=contrast_issues,
            accessibility_issues=accessibility_issues,
        )


class GlobalThemeIntelligence:
    """
    Global Theme Intelligence System
    
    Centralized theme management that ensures:
    - Every slide inherits from master theme
    - No random colors
    - No theme drift
    - No inconsistent backgrounds
    - No accidental gradients
    - No visual conflicts
    """
    
    def __init__(self) -> None:
        self.contrast_checker = ContrastChecker()
        self.color_harmony_validator = ColorHarmonyValidator()
        self.typography_validator = TypographyConsistencyValidator()
        self.accessibility_validator = AccessibilityValidator()
    
    def create_master_theme(
        self,
        theme_id: str,
        style: ThemeStyle = ThemeStyle.STARTUP_MODERN,
        mode: ThemeMode = ThemeMode.LIGHT,
        user_overrides: Optional[Dict[str, Any]] = None,
    ) -> GlobalThemeTokens:
        """
        Create a master theme with complete token set.
        
        Returns GlobalThemeTokens with all design tokens.
        """
        # Get base theme from style
        base_theme = self._get_base_theme_for_style(style, mode)
        
        # Apply user overrides if provided
        if user_overrides:
            base_theme = self._apply_overrides(base_theme, user_overrides)
        
        # Validate the theme
        validation = self.accessibility_validator.validate_theme(base_theme)
        
        if not validation.is_valid:
            logger.warning(
                "theme_accessibility_issues",
                theme_id=theme_id,
                contrast_issues=validation.contrast_issues,
                accessibility_issues=validation.accessibility_issues,
            )
        
        return base_theme
    
    def _get_base_theme_for_style(
        self,
        style: ThemeStyle,
        mode: ThemeMode,
    ) -> GlobalThemeTokens:
        """Get base theme tokens for a given style and mode"""
        
        # Light mode defaults
        if mode == ThemeMode.LIGHT:
            background = "#ffffff"
            surface = "#f8fafc"
            text_primary = "#0f172a"
            text_secondary = "#475569"
            text_muted = "#94a3b8"
        else:
            # Dark mode defaults
            background = "#0f172a"
            surface = "#1e293b"
            text_primary = "#f8fafc"
            text_secondary = "#cbd5e1"
            text_muted = "#64748b"
        
        # Style-specific overrides
        style_configs = {
            ThemeStyle.MINIMAL: {
                "primary": "#0f172a",
                "secondary": "#334155",
                "accent": "#3b82f6",
                "heading_font": "Inter, system-ui, sans-serif",
                "body_font": "Inter, system-ui, sans-serif",
                "motion_style": "minimal",
                "icon_style": "outline",
            },
            ThemeStyle.GLASSMORPHISM: {
                "primary": "#8b5cf6",
                "secondary": "#a78bfa",
                "accent": "#c4b5fd",
                "heading_font": "Inter, system-ui, sans-serif",
                "body_font": "Inter, system-ui, sans-serif",
                "motion_style": "smooth",
                "icon_style": "filled",
                "glass_blur": "blur(20px) saturate(180%)",
                "glass_opacity": 0.8,
            },
            ThemeStyle.PREMIUM_CORPORATE: {
                "primary": "#1e3a8a",
                "secondary": "#3b82f6",
                "accent": "#f59e0b",
                "heading_font": "Georgia, serif",
                "body_font": "Inter, system-ui, sans-serif",
                "motion_style": "elegant",
                "icon_style": "filled",
            },
            ThemeStyle.STARTUP_MODERN: {
                "primary": "#6366f1",
                "secondary": "#8b5cf6",
                "accent": "#ec4899",
                "heading_font": "Inter, system-ui, sans-serif",
                "body_font": "Inter, system-ui, sans-serif",
                "motion_style": "bouncy",
                "icon_style": "rounded",
            },
            ThemeStyle.LUXURY_INVESTOR: {
                "primary": "#1c1917",
                "secondary": "#44403c",
                "accent": "#d97706",
                "heading_font": "Playfair Display, serif",
                "body_font": "Inter, system-ui, sans-serif",
                "motion_style": "elegant",
                "icon_style": "filled",
            },
            ThemeStyle.FINTECH: {
                "primary": "#059669",
                "secondary": "#10b981",
                "accent": "#f59e0b",
                "heading_font": "Inter, system-ui, sans-serif",
                "body_font": "Inter, system-ui, sans-serif",
                "motion_style": "professional",
                "icon_style": "outline",
            },
            ThemeStyle.AI_FUTURISTIC: {
                "primary": "#7c3aed",
                "secondary": "#a855f7",
                "accent": "#06b6d4",
                "heading_font": "Space Grotesk, sans-serif",
                "body_font": "Inter, system-ui, sans-serif",
                "motion_style": "glowing",
                "icon_style": "neon",
            },
            ThemeStyle.ENTERPRISE_CLEAN: {
                "primary": "#2563eb",
                "secondary": "#3b82f6",
                "accent": "#10b981",
                "heading_font": "Inter, system-ui, sans-serif",
                "body_font": "Inter, system-ui, sans-serif",
                "motion_style": "minimal",
                "icon_style": "outline",
            },
        }
        
        config = style_configs.get(style, style_configs[ThemeStyle.STARTUP_MODERN])
        
        return GlobalThemeTokens(
            primary=config["primary"],
            secondary=config["secondary"],
            accent=config["accent"],
            background=background,
            surface=surface,
            text_primary=text_primary,
            text_secondary=text_secondary,
            text_muted=text_muted,
            success="#22c55e",
            warning="#f59e0b",
            danger="#ef4444",
            chart_colors=self._generate_chart_colors(config["primary"], config["accent"]),
            heading_font=config["heading_font"],
            body_font=config["body_font"],
            mono_font="ui-monospace, SFMono-Regular, Menlo, monospace",
            heading_weight=700,
            body_weight=400,
            display_scale=4.5,
            h1_scale=3.0,
            h2_scale=2.25,
            h3_scale=1.75,
            body_scale=1.0,
            caption_scale=0.875,
            slide_margin=2.0,
            gap=1.0,
            section_gap=2.0,
            radius_sm="2px",
            radius_md="6px",
            radius_lg="12px",
            radius_xl="24px",
            shadow_sm="0 1px 2px rgba(0,0,0,0.06)",
            shadow_md="0 4px 12px rgba(0,0,0,0.08)",
            shadow_lg="0 12px 40px rgba(0,0,0,0.12)",
            shadow_glow="0 0 40px rgba(0,0,0,0.15)",
            border_width="1px",
            border_subtle="color-mix(in oklab, var(--st-on-surface) 8%, transparent)",
            motion_style=config["motion_style"],
            transition_duration="300ms",
            easing="cubic-bezier(0.4, 0, 0.2, 1)",
            glass_blur=config.get("glass_blur", "blur(20px) saturate(180%)"),
            glass_opacity=config.get("glass_opacity", 0.8),
            glass_border="1px solid rgba(255, 255, 255, 0.2)",
            icon_style=config["icon_style"],
            icon_size="24px",
            chart_style="modern",
            chart_line_width=2.0,
            chart_point_size=4.0,
        )
    
    def _generate_chart_colors(self, primary: str, accent: str) -> List[str]:
        """Generate harmonious chart colors from primary and accent"""
        # In production, use proper color manipulation
        # For now, return a set of harmonious colors
        return [
            primary,
            accent,
            "#22c55e",
            "#f59e0b",
            "#ef4444",
            "#8b5cf6",
            "#06b6d4",
            "#ec4899",
        ]
    
    def _apply_overrides(
        self,
        base: GlobalThemeTokens,
        overrides: Dict[str, Any],
    ) -> GlobalThemeTokens:
        """Apply user overrides to base theme.

        The frontend still sends legacy brand keys such as ``primary_color``.
        Keep this adapter tolerant so a style payload can never crash a live
        generation request with an unexpected dataclass field.
        """
        base_dict = base.__dict__.copy()
        if not isinstance(overrides, dict):
            return GlobalThemeTokens(**base_dict)

        alias_map = {
            "primary_color": "primary",
            "secondary_color": "secondary",
            "accent_color": "accent",
            "background_color": "background",
            "surface_color": "surface",
            "text_color": "text_primary",
            "text_primary_color": "text_primary",
            "text_secondary_color": "text_secondary",
            "text_muted_color": "text_muted",
            "success_color": "success",
            "warning_color": "warning",
            "danger_color": "danger",
        }
        allowed_fields = set(GlobalThemeTokens.__dataclass_fields__.keys())

        def apply_item(key: str, value: Any) -> None:
            mapped_key = alias_map.get(key, key)
            if mapped_key not in allowed_fields:
                return
            if value is None or value == "":
                return
            base_dict[mapped_key] = value

        for key, value in overrides.items():
            if key in {"palette", "colors"} and isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    apply_item(nested_key, nested_value)
                continue
            apply_item(key, value)

        return GlobalThemeTokens(**base_dict)
    
    def validate_theme_consistency(
        self,
        tokens: GlobalThemeTokens,
    ) -> ThemeValidationResult:
        """
        Validate theme for consistency and accessibility.
        
        Returns comprehensive validation result.
        """
        errors = []
        warnings = []
        
        # Check color harmony
        color_issues = self.color_harmony_validator.validate_palette(tokens)
        errors.extend(color_issues)
        
        # Check typography consistency
        typography_issues = self.typography_validator.validate_typography(tokens)
        errors.extend(typography_issues)
        
        # Check accessibility
        accessibility_result = self.accessibility_validator.validate_theme(tokens)
        errors.extend(accessibility_result.errors)
        warnings.extend(accessibility_result.warnings)
        
        return ThemeValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            contrast_issues=accessibility_result.contrast_issues,
            accessibility_issues=accessibility_result.accessibility_issues,
        )
    
    def ensure_slide_theme_compliance(
        self,
        slide_tokens: Dict[str, Any],
        master_theme: GlobalThemeTokens,
    ) -> Dict[str, Any]:
        """
        Ensure a slide's tokens comply with master theme.
        
        Returns compliant slide tokens.
        """
        compliant_tokens = slide_tokens.copy()
        
        # Override any missing or inconsistent tokens with master theme
        master_dict = master_theme.__dict__
        
        for key, value in master_dict.items():
            if key not in compliant_tokens or not compliant_tokens[key]:
                compliant_tokens[key] = value
        
        # Check for theme drift (random colors)
        if "primary" in compliant_tokens:
            if compliant_tokens["primary"] != master_theme.primary:
                logger.warning(
                    "theme_drift_detected",
                    token="primary",
                    slide_value=compliant_tokens["primary"],
                    master_value=master_theme.primary,
                )
                # Force compliance
                compliant_tokens["primary"] = master_theme.primary
        
        return compliant_tokens


# Singleton instance
_theme_intelligence_instance: Optional[GlobalThemeIntelligence] = None


def get_global_theme_intelligence() -> GlobalThemeIntelligence:
    """Get singleton global theme intelligence instance"""
    global _theme_intelligence_instance
    if _theme_intelligence_instance is None:
        _theme_intelligence_instance = GlobalThemeIntelligence()
    return _theme_intelligence_instance
