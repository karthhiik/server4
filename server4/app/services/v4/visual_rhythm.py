"""
V4 Visual Rhythm Engine — Ensures consistent visual flow across slides.

This module implements visual rhythm planning to ensure:
- Consistent spacing and layout patterns across the deck
- Balanced visual weight distribution
- Avoidance of repetitive layouts
- Strategic use of white space
- Visual hierarchy alignment

Design principles:
- Rhythm is planned at deck level, not slide level
- Each slide contributes to the overall visual narrative
- Alternating patterns prevent visual fatigue
- Spacing follows a consistent scale
- Visual density varies intentionally to create emphasis
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

_CATALOG_AVOID_PROMPTS = (
    "avoid AI-purple/pink gradients",
    "avoid neon color accents",
    "avoid harsh shadows",
    "avoid generic emoji icon language",
)


# ── Visual Density Levels ─────────────────────────────────────────────

class VisualDensity(Enum):
    """Visual density levels for slides."""
    SPARSE = "sparse"          # Minimal content, lots of white space
    BALANCED = "balanced"      # Standard density
    DENSE = "dense"            # High information density
    MAXIMAL = "maximal"        # Very dense, data-heavy


# ── Layout Pattern Types ────────────────────────────────────────────

class LayoutPattern(Enum):
    """Layout pattern archetypes for rhythm planning."""
    HERO = "hero"                    # Full-width hero with minimal content
    SPLIT_LEFT = "split_left"        # Content left, visual right
    SPLIT_RIGHT = "split_right"      # Visual left, content right
    CENTERED = "centered"            # Centered content, symmetrical
    GRID = "grid"                    # Grid-based layout
    FULL_BLEED = "full_bleed"        # Full-bleed image with overlay
    TYPOGRAPHY = "typography"        # Text-focused, minimal visuals
    DATA = "data"                    # Chart/data focused


# ── Visual Rhythm State ─────────────────────────────────────────────

@dataclass
class SlideRhythmProfile:
    """Visual rhythm profile for a single slide."""
    index: int
    density: VisualDensity
    pattern: LayoutPattern
    spacing_level: float  # 0.0-1.0, relative to deck average
    visual_weight: float  # 0.0-1.0, visual impact
    has_image: bool
    has_chart: bool
    has_data: bool


@dataclass
class DeckRhythmPlan:
    """Visual rhythm plan for the entire deck."""
    slides: list[SlideRhythmProfile] = field(default_factory=list)
    spacing_scale: list[float] = field(default_factory=list)  # Spacing multipliers
    pattern_sequence: list[LayoutPattern] = field(default_factory=list)
    density_curve: list[VisualDensity] = field(default_factory=list)
    
    def get_slide_profile(self, index: int) -> Optional[SlideRhythmProfile]:
        """Get rhythm profile for a specific slide index."""
        for profile in self.slides:
            if profile.index == index:
                return profile
        return None
    
    def get_recommended_pattern(self, index: int, slide_intent: str) -> LayoutPattern:
        """Get recommended layout pattern based on rhythm plan."""
        # If we have a planned pattern for this index, use it
        if index < len(self.pattern_sequence):
            return self.pattern_sequence[index]
        
        # Otherwise, recommend based on intent
        intent_lower = slide_intent.lower()
        
        if "cover" in intent_lower or "hero" in intent_lower:
            return LayoutPattern.HERO
        elif "chart" in intent_lower or "data" in intent_lower or "metric" in intent_lower:
            return LayoutPattern.DATA
        elif "grid" in intent_lower or "feature" in intent_lower:
            return LayoutPattern.GRID
        elif "split" in intent_lower:
            # Alternate split direction based on index
            return LayoutPattern.SPLIT_LEFT if index % 2 == 0 else LayoutPattern.SPLIT_RIGHT
        elif "image" in intent_lower:
            return LayoutPattern.FULL_BLEED
        else:
            return LayoutPattern.CENTERED


# ── Visual Rhythm Engine ─────────────────────────────────────────────

class VisualRhythmEngine:
    """Plans and enforces visual rhythm across slides."""
    
    def __init__(self) -> None:
        self._spacing_scale = [1.0, 0.8, 1.2, 1.0, 0.9, 1.1, 1.0]  # Default spacing rhythm
        self._pattern_alternation_limit = 2  # Max consecutive same patterns
    
    def plan_deck_rhythm(
        self,
        slide_intents: list[str],
        total_slides: int,
    ) -> DeckRhythmPlan:
        """Plan visual rhythm for the entire deck.
        
        Args:
            slide_intents: List of slide intents (e.g., "cover", "traction", "market")
            total_slides: Total number of slides in the deck
        
        Returns:
            DeckRhythmPlan with rhythm profiles for all slides
        """
        plan = DeckRhythmPlan()
        
        for i, intent in enumerate(slide_intents):
            profile = self._plan_slide_rhythm(
                index=i,
                intent=intent,
                total_slides=total_slides,
                previous_profiles=plan.slides,
            )
            plan.slides.append(profile)
            plan.pattern_sequence.append(profile.pattern)
            plan.density_curve.append(profile.density)
        
        # Calculate spacing scale based on density curve
        plan.spacing_scale = self._calculate_spacing_scale(plan.density_curve)
        
        logger.info(
            "visual_rhythm_planned",
            total_slides=total_slides,
            pattern_sequence=[p.value for p in plan.pattern_sequence[:10]],
        )
        
        return plan
    
    def _plan_slide_rhythm(
        self,
        index: int,
        intent: str,
        total_slides: int,
        previous_profiles: list[SlideRhythmProfile],
    ) -> SlideRhythmProfile:
        """Plan rhythm for a single slide."""
        # Determine density based on intent
        density = self._infer_density_from_intent(intent)
        
        # Determine pattern based on intent and previous patterns
        pattern = self._select_pattern(
            intent=intent,
            index=index,
            total_slides=total_slides,
            previous_profiles=previous_profiles,
        )
        
        # Calculate spacing level (varies to create rhythm)
        spacing_level = self._calculate_spacing_level(index, total_slides, density)
        
        # Calculate visual weight
        visual_weight = self._calculate_visual_weight(density, pattern, intent)
        
        # Determine if slide has visual elements
        has_image = "image" in intent.lower() or index == 0  # Cover usually has image
        has_chart = "chart" in intent.lower() or "data" in intent.lower()
        has_data = has_chart or "metric" in intent.lower() or "number" in intent.lower()
        
        return SlideRhythmProfile(
            index=index,
            density=density,
            pattern=pattern,
            spacing_level=spacing_level,
            visual_weight=visual_weight,
            has_image=has_image,
            has_chart=has_chart,
            has_data=has_data,
        )
    
    def _infer_density_from_intent(self, intent: str) -> VisualDensity:
        """Infer visual density from slide intent."""
        intent_lower = intent.lower()
        
        if "cover" in intent_lower or "hero" in intent_lower:
            return VisualDensity.SPARSE
        elif "chart" in intent_lower or "data" in intent_lower or "table" in intent_lower:
            return VisualDensity.DENSE
        elif "grid" in intent_lower or "feature" in intent_lower:
            return VisualDensity.BALANCED
        elif "market" in intent_lower or "competition" in intent_lower:
            return VisualDensity.BALANCED
        elif "financial" in intent_lower or "projection" in intent_lower:
            return VisualDensity.MAXIMAL
        else:
            return VisualDensity.BALANCED
    
    def _select_pattern(
        self,
        intent: str,
        index: int,
        total_slides: int,
        previous_profiles: list[SlideRhythmProfile],
    ) -> LayoutPattern:
        """Select layout pattern considering rhythm constraints."""
        # Get base pattern from intent
        intent_lower = intent.lower()
        
        if "cover" in intent_lower:
            return LayoutPattern.HERO
        elif "chart" in intent_lower or "data" in intent_lower:
            return LayoutPattern.DATA
        elif "grid" in intent_lower or "feature" in intent_lower:
            return LayoutPattern.GRID
        elif "image" in intent_lower:
            return LayoutPattern.FULL_BLEED
        elif "quote" in intent_lower or "testimonial" in intent_lower:
            return LayoutPattern.CENTERED
        elif "typography" in intent_lower or "mission" in intent_lower:
            return LayoutPattern.TYPOGRAPHY
        else:
            # Default to alternating split patterns for variety
            if index % 2 == 0:
                return LayoutPattern.SPLIT_LEFT
            else:
                return LayoutPattern.SPLIT_RIGHT
        
        # Check for pattern repetition and adjust if needed
        # (Future enhancement: implement pattern alternation logic)
    
    def _calculate_spacing_level(
        self,
        index: int,
        total_slides: int,
        density: VisualDensity,
    ) -> float:
        """Calculate spacing level for a slide."""
        # Base spacing from density
        density_spacing = {
            VisualDensity.SPARSE: 1.2,
            VisualDensity.BALANCED: 1.0,
            VisualDensity.DENSE: 0.8,
            VisualDensity.MAXIMAL: 0.6,
        }
        
        base = density_spacing.get(density, 1.0)
        
        # Apply rhythm variation based on position in deck
        rhythm_index = index % len(self._spacing_scale)
        rhythm_multiplier = self._spacing_scale[rhythm_index]
        
        return base * rhythm_multiplier
    
    def _calculate_visual_weight(
        self,
        density: VisualDensity,
        pattern: LayoutPattern,
        intent: str,
    ) -> float:
        """Calculate visual weight of a slide."""
        # Base weight from density
        density_weight = {
            VisualDensity.SPARSE: 0.3,
            VisualDensity.BALANCED: 0.5,
            VisualDensity.DENSE: 0.7,
            VisualDensity.MAXIMAL: 0.9,
        }
        
        base = density_weight.get(density, 0.5)
        
        # Adjust based on pattern
        pattern_weight = {
            LayoutPattern.HERO: 0.8,
            LayoutPattern.FULL_BLEED: 0.9,
            LayoutPattern.DATA: 0.7,
            LayoutPattern.GRID: 0.6,
            LayoutPattern.SPLIT_LEFT: 0.5,
            LayoutPattern.SPLIT_RIGHT: 0.5,
            LayoutPattern.CENTERED: 0.4,
            LayoutPattern.TYPOGRAPHY: 0.3,
        }
        
        pattern_adjustment = pattern_weight.get(pattern, 0.0)
        
        return min(1.0, base + pattern_adjustment * 0.2)
    
    def _calculate_spacing_scale(self, density_curve: list[VisualDensity]) -> list[float]:
        """Calculate spacing scale based on density curve."""
        scale = []
        
        for i, density in enumerate(density_curve):
            # Higher density = tighter spacing
            if density == VisualDensity.SPARSE:
                scale.append(1.2)
            elif density == VisualDensity.BALANCED:
                scale.append(1.0)
            elif density == VisualDensity.DENSE:
                scale.append(0.8)
            else:  # MAXIMAL
                scale.append(0.6)
        
        return scale
    
    def validate_rhythm(self, plan: DeckRhythmPlan) -> dict[str, Any]:
        """Validate rhythm plan for consistency and issues.
        
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        # Check for pattern repetition
        pattern_counts = {}
        for pattern in plan.pattern_sequence:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        # Warn if any pattern is overused (>50% of slides)
        for pattern, count in pattern_counts.items():
            if count > len(plan.pattern_sequence) * 0.5:
                warnings.append(f"Pattern {pattern.value} used in {count}/{len(plan.pattern_sequence)} slides")
        
        # Check for density monotonicity (should vary, not be flat)
        density_values = [d.value for d in plan.density_curve]
        if len(set(density_values)) == 1:
            warnings.append("All slides have same density - consider varying for visual interest")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "pattern_diversity": len(set(plan.pattern_sequence)) / len(plan.pattern_sequence),
            "density_diversity": len(set(density_values)) / len(density_values),
        }


# ── Convenience Functions ─────────────────────────────────────────────

def plan_deck_visual_rhythm(slide_intents: list[str]) -> DeckRhythmPlan:
    """Convenience function to plan visual rhythm for a deck.
    
    Args:
        slide_intents: List of slide intents
    
    Returns:
        DeckRhythmPlan with rhythm profiles
    """
    engine = VisualRhythmEngine()
    return engine.plan_deck_rhythm(slide_intents, len(slide_intents))


def get_slide_spacing_multiplier(
    slide_index: int,
    rhythm_plan: Optional[DeckRhythmPlan] = None,
) -> float:
    """Get spacing multiplier for a specific slide.
    
    Args:
        slide_index: Index of the slide
        rhythm_plan: Optional rhythm plan (if None, uses default scale)
    
    Returns:
        Spacing multiplier (0.6-1.2)
    """
    if rhythm_plan and slide_index < len(rhythm_plan.spacing_scale):
        return rhythm_plan.spacing_scale[slide_index]
    
    # Default scale
    engine = VisualRhythmEngine()
    return engine._spacing_scale[slide_index % len(engine._spacing_scale)]


def catalog_anti_pattern_prompt_suffix(design_tokens: Optional[dict[str, Any]] = None) -> str:
    """Return image/style prompt guidance grounded in the Slice 7 catalog."""
    tokens = design_tokens if isinstance(design_tokens, dict) else {}
    recommendation = tokens.get("catalog_recommendation")
    style = recommendation.get("style_family") if isinstance(recommendation, dict) else {}
    anti_patterns = style.get("anti_patterns") if isinstance(style, dict) else None
    avoid = list(_CATALOG_AVOID_PROMPTS)
    if isinstance(anti_patterns, list):
        avoid.extend(str(item).strip() for item in anti_patterns if str(item).strip())
    return "; ".join(dict.fromkeys(avoid))
