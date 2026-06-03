"""
Layout Remix Engine — Phase 4-2

Enables users to transform slides by applying different layout variants.
Provides 30+ layout transform options from the existing layout library.

Flow:
1. Analyze current slide content (features, intent, visual elements)
2. Find compatible layout variants from LAYOUT_LIBRARY
3. Apply selected variant by recompiling with new kit_id:variant
4. Return transformed compiled slide
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.services.v4.layout.library import LAYOUT_LIBRARY, LayoutSpec
from app.services.v4.layout.intent_engine import extract_features, LayoutFeatures

logger = structlog.get_logger(__name__)


class TransformCategory(str, Enum):
    """Categories of layout transforms for UI organization."""
    TITLE = "title"
    HERO = "hero"
    CONTENT = "content"
    DATA = "data"
    FEATURE = "feature"
    TEAM = "team"
    QUOTE = "quote"
    DIAGRAM = "diagram"
    COMPARISON = "comparison"
    EDITORIAL = "editorial"
    PREMIUM = "premium"


@dataclass
class LayoutTransform:
    """A layout transform option."""
    id: str
    name: str
    description: str
    kit_id: str
    variant: str
    category: TransformCategory
    requires: Tuple[str, ...] = ()
    icon: str = "layout"


class LayoutRemixEngine:
    """
    Engine for applying layout transforms to slides.
    
    Analyzes slide content and provides compatible layout variants
    for remixing the slide design.
    """
    
    def __init__(self):
        self.logger = logger
        # Build transform catalog from LAYOUT_LIBRARY
        self._transforms = self._build_transform_catalog()
    
    def _build_transform_catalog(self) -> Dict[str, LayoutTransform]:
        """Build transform catalog from layout library."""
        transforms = {}
        for spec in LAYOUT_LIBRARY:
            category = self._categorize_layout(spec)
            transform = LayoutTransform(
                id=spec.key,
                name=self._format_name(spec.kit_id, spec.variant),
                description=self._format_description(spec),
                kit_id=spec.kit_id,
                variant=spec.variant,
                category=category,
                requires=spec.requires,
                icon=self._get_icon(spec.kit_id),
            )
            transforms[transform.id] = transform
        return transforms
    
    def _categorize_layout(self, spec: LayoutSpec) -> TransformCategory:
        """Categorize layout by kit_id."""
        kit_lower = spec.kit_id.lower()
        if "title" in kit_lower or "cover" in kit_lower:
            return TransformCategory.TITLE
        elif "hero" in kit_lower or "stat" in kit_lower or "duotone" in kit_lower or "cinematic" in kit_lower:
            return TransformCategory.HERO
        elif "content" in spec.intents or "overview" in spec.intents:
            return TransformCategory.CONTENT
        elif "chart" in kit_lower or "stat" in kit_lower or "financial" in spec.intents:
            return TransformCategory.DATA
        elif "feature" in kit_lower or "glass" in kit_lower:
            return TransformCategory.FEATURE
        elif "team" in kit_lower:
            return TransformCategory.TEAM
        elif "quote" in kit_lower:
            return TransformCategory.QUOTE
        elif "diagram" in kit_lower or "flywheel" in kit_lower:
            return TransformCategory.DIAGRAM
        elif "comparison" in kit_lower:
            return TransformCategory.COMPARISON
        elif "editorial" in kit_lower or "split" in kit_lower:
            return TransformCategory.EDITORIAL
        else:
            return TransformCategory.PREMIUM
    
    def _format_name(self, kit_id: str, variant: str) -> str:
        """Format human-readable name."""
        # Convert camelCase to Title Case
        kit_name = "".join(f" {c}" if c.isupper() else c for c in kit_id).strip()
        variant_name = variant.replace("-", " ").title()
        return f"{kit_name} - {variant_name}"
    
    def _format_description(self, spec: LayoutSpec) -> str:
        """Format description from layout keywords."""
        if spec.layout_keywords:
            keywords = ", ".join(spec.layout_keywords[:3])
            return f"Layout: {keywords}"
        return f"Layout variant for {', '.join(spec.intents[:2])}"
    
    def _get_icon(self, kit_id: str) -> str:
        """Get icon name for kit."""
        kit_lower = kit_id.lower()
        if "title" in kit_lower:
            return "type"
        elif "image" in kit_lower or "editorial" in kit_lower or "bleed" in kit_lower:
            return "image"
        elif "stat" in kit_lower or "chart" in kit_lower or "financial" in kit_lower:
            return "bar-chart-2"
        elif "feature" in kit_lower or "glass" in kit_lower:
            return "grid"
        elif "team" in kit_lower:
            return "users"
        elif "quote" in kit_lower:
            return "quote"
        elif "diagram" in kit_lower or "timeline" in kit_lower:
            return "git-branch"
        elif "comparison" in kit_lower:
            return "columns"
        else:
            return "layout"
    
    def get_available_transforms(
        self,
        slide_content: Dict[str, Any],
        current_layout: Optional[str] = None,
    ) -> List[LayoutTransform]:
        """
        Get compatible layout transforms for a slide.
        
        Args:
            slide_content: Compiled slide content
            current_layout: Current layout key (to exclude from options)
            
        Returns:
            List of compatible layout transforms
        """
        # Create a simple slide-like object from compiled content
        from types import SimpleNamespace
        slide_obj = SimpleNamespace(
            headline=slide_content.get("headline", ""),
            subheadline=slide_content.get("subheadline", ""),
            body=slide_content.get("body", ""),
            bullets=slide_content.get("bullets", []),
            layout=slide_content.get("layout_hint", ""),
            intent=slide_content.get("intent", ""),
            purpose=slide_content.get("purpose", ""),
            chart=slide_content.get("chart"),
            timeline=slide_content.get("timeline"),
            comparison=slide_content.get("comparison"),
            diagram=slide_content.get("diagram"),
            quote=slide_content.get("quote"),
            team_members=slide_content.get("team_members"),
            stat_blocks=slide_content.get("stat_blocks"),
            image_url=slide_content.get("image_url"),
            image_prompt=slide_content.get("image_prompt"),
            render_decision=slide_content.get("render_decision", {}),
        )
        
        # Extract features from slide
        features = extract_features(
            slide_obj,
            deck_purpose=slide_content.get("purpose", ""),
            deck_index=slide_content.get("slide_index", 0),
            deck_total=slide_content.get("total_slides", 1),
        )
        
        # Find compatible transforms
        compatible = []
        for transform in self._transforms.values():
            # Skip current layout
            if current_layout and transform.id == current_layout:
                continue
            
            # Check requirements
            if self._meets_requirements(transform, features, slide_content):
                compatible.append(transform)
        
        # Sort by category then name
        compatible.sort(key=lambda t: (t.category.value, t.name))
        
        return compatible
    
    def _meets_requirements(
        self,
        transform: LayoutTransform,
        features: LayoutFeatures,
        slide_content: Dict[str, Any],
    ) -> bool:
        """Check if slide meets transform requirements."""
        # Check required features
        for req in transform.requires:
            if req == "image" and not features.has_image:
                return False
            elif req == "chart" and not features.has_chart:
                return False
            elif req == "timeline" and not features.has_timeline:
                return False
            elif req == "comparison" and not features.has_comparison:
                return False
            elif req == "diagram" and not features.has_diagram:
                return False
            elif req == "features" and not features.has_features:
                return False
            elif req == "team" and not features.has_team:
                return False
            elif req == "stats" and not features.has_stats:
                return False
            elif req == "quote" and not features.has_quote:
                return False
        
        # Check word count constraints
        word_count = features.word_count
        spec = self._get_spec(transform.kit_id, transform.variant)
        if spec:
            if word_count < spec.min_words or word_count > spec.max_words:
                return False
            if features.bullet_count < spec.min_bullets or features.bullet_count > spec.max_bullets:
                return False
        
        return True
    
    def _get_spec(self, kit_id: str, variant: str) -> Optional[LayoutSpec]:
        """Get LayoutSpec by kit_id and variant."""
        for spec in LAYOUT_LIBRARY:
            if spec.kit_id == kit_id and spec.variant == variant:
                return spec
        return None
    
    def apply_transform(
        self,
        slide_content: Dict[str, Any],
        transform_id: str,
    ) -> Dict[str, Any]:
        """
        Apply a layout transform to a slide.
        
        Args:
            slide_content: Current compiled slide content
            transform_id: Layout transform ID to apply
            
        Returns:
            Updated slide content with new layout
        """
        transform = self._transforms.get(transform_id)
        if not transform:
            raise ValueError(f"Transform not found: {transform_id}")
        
        # Create a simple slide-like object from compiled content
        from types import SimpleNamespace
        slide_obj = SimpleNamespace(
            headline=slide_content.get("headline", ""),
            subheadline=slide_content.get("subheadline", ""),
            body=slide_content.get("body", ""),
            bullets=slide_content.get("bullets", []),
            layout=slide_content.get("layout_hint", ""),
            intent=slide_content.get("intent", ""),
            purpose=slide_content.get("purpose", ""),
            chart=slide_content.get("chart"),
            timeline=slide_content.get("timeline"),
            comparison=slide_content.get("comparison"),
            diagram=slide_content.get("diagram"),
            quote=slide_content.get("quote"),
            team_members=slide_content.get("team_members"),
            stat_blocks=slide_content.get("stat_blocks"),
            image_url=slide_content.get("image_url"),
            image_prompt=slide_content.get("image_prompt"),
            render_decision=slide_content.get("render_decision", {}),
        )
        
        # Verify compatibility
        features = extract_features(
            slide_obj,
            deck_purpose=slide_content.get("purpose", ""),
            deck_index=slide_content.get("slide_index", 0),
            deck_total=slide_content.get("total_slides", 1),
        )
        
        if not self._meets_requirements(transform, features, slide_content):
            raise ValueError(f"Slide does not meet requirements for transform: {transform_id}")
        
        # Update slide with new layout
        updated = slide_content.copy()
        updated["kit_id"] = transform.kit_id
        updated["layout_variant"] = transform.variant
        updated["layout_key"] = transform.id
        
        self.logger.info(
            "layout_transform_applied",
            transform_id=transform_id,
            kit_id=transform.kit_id,
            variant=transform.variant,
        )
        
        return updated
    
    def get_transforms_by_category(self) -> Dict[TransformCategory, List[LayoutTransform]]:
        """Get all transforms grouped by category."""
        grouped = {}
        for transform in self._transforms.values():
            if transform.category not in grouped:
                grouped[transform.category] = []
            grouped[transform.category].append(transform)
        
        # Sort within each category
        for category in grouped:
            grouped[category].sort(key=lambda t: t.name)
        
        return grouped
    
    def get_transform(self, transform_id: str) -> Optional[LayoutTransform]:
        """Get a specific transform by ID."""
        return self._transforms.get(transform_id)
