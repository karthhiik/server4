"""
Auto Regenerator - Regenerates slides with same content but different designs
Preserves content while changing layout, colors, typography, and visual elements
"""

from typing import Dict, Any, List
import random


class AutoRegenerator:
    """
    Auto-regenerates slides with same content but different designs
    Preserves factual content while changing visual presentation
    """
    
    def __init__(self):
        self.layout_variants = [
            "minimalist",
            "modern",
            "corporate",
            "creative",
            "data-focused",
            "story-driven"
        ]
        
        self.color_schemes = [
            {"primary": "#3B82F6", "secondary": "#8B5CF6", "accent": "#EC4899"},
            {"primary": "#10B981", "secondary": "#3B82F6", "accent": "#F59E0B"},
            {"primary": "#EF4444", "secondary": "#F59E0B", "accent": "#10B981"},
            {"primary": "#8B5CF6", "secondary": "#EC4899", "accent": "#3B82F6"},
            {"primary": "#F59E0B", "secondary": "#EF4444", "accent": "#8B5CF6"},
        ]
        
        self.typography_variants = [
            {"font_family": "Inter", "headline_size": "text-4xl", "body_size": "text-lg"},
            {"font_family": "Roboto", "headline_size": "text-3xl", "body_size": "text-base"},
            {"font_family": "Montserrat", "headline_size": "text-5xl", "body_size": "text-xl"},
            {"font_family": "Open Sans", "headline_size": "text-4xl", "body_size": "text-lg"},
        ]
    
    async def regenerate_slides(
        self,
        slides: List[Dict[str, Any]],
        num_variants: int = 3
    ) -> List[List[Dict[str, Any]]]:
        """
        Generate multiple design variants for the same slide content
        
        Args:
            slides: Original slides with content
            num_variants: Number of design variants to generate
            
        Returns:
            List of slide variants (each variant is a list of slides)
        """
        variants = []
        
        for i in range(num_variants):
            variant = []
            
            for slide in slides:
                # Preserve content
                content = {
                    "headline": slide.get("headline"),
                    "subheadline": slide.get("subheadline"),
                    "bullets": slide.get("bullets"),
                    "body": slide.get("body"),
                    "data": slide.get("data")
                }
                
                # Generate new design
                design = self._generate_design_variant(i)
                
                # Combine content with new design
                regenerated_slide = {
                    **content,
                    "design": design,
                    "render_decision": self._generate_render_decision(slide, design)
                }
                
                variant.append(regenerated_slide)
            
            variants.append(variant)
        
        return variants
    
    def _generate_design_variant(self, variant_index: int) -> Dict[str, Any]:
        """Generate a design variant"""
        # Use different design for each variant
        layout = self.layout_variants[variant_index % len(self.layout_variants)]
        colors = self.color_schemes[variant_index % len(self.color_schemes)]
        typography = self.typography_variants[variant_index % len(self.typography_variants)]
        
        return {
            "layout": layout,
            "colors": colors,
            "typography": typography,
            "spacing": "medium" if variant_index % 2 == 0 else "generous"
        }
    
    def _generate_render_decision(
        self,
        original_slide: Dict[str, Any],
        design: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate render decision based on content and design"""
        original_decision = original_slide.get("render_decision", {})
        modality = original_decision.get("modality", "text")
        
        # Adjust modality based on layout
        if design["layout"] == "data-focused":
            if original_decision.get("chart_data"):
                modality = "chart"
            elif original_decision.get("table_data"):
                modality = "table"
        
        return {
            "modality": modality,
            "layout": design["layout"],
            "colors": design["colors"],
            "typography": design["typography"],
            "chart_data": original_decision.get("chart_data"),
            "table_data": original_decision.get("table_data"),
            "timeline_data": original_decision.get("timeline_data"),
            "diagram_data": original_decision.get("diagram_data")
        }
    
    async def regenerate_single_slide(
        self,
        slide: Dict[str, Any],
        preserve_layout: bool = False
    ) -> Dict[str, Any]:
        """
        Regenerate a single slide with different design
        
        Args:
            slide: Original slide
            preserve_layout: Whether to preserve the original layout
            
        Returns:
            Regenerated slide
        """
        # Preserve content
        content = {
            "headline": slide.get("headline"),
            "subheadline": slide.get("subheadline"),
            "bullets": slide.get("bullets"),
            "body": slide.get("body"),
            "data": slide.get("data")
        }
        
        # Generate new design
        if preserve_layout:
            original_design = slide.get("design", {})
            design = {
                "layout": original_design.get("layout", "modern"),
                "colors": self._get_alternate_color_scheme(original_design.get("colors")),
                "typography": original_design.get("typography"),
                "spacing": original_design.get("spacing", "medium")
            }
        else:
            design = self._generate_design_variant(random.randint(0, 5))
        
        # Combine content with new design
        regenerated_slide = {
            **content,
            "design": design,
            "render_decision": self._generate_render_decision(slide, design)
        }
        
        return regenerated_slide
    
    def _get_alternate_color_scheme(self, original_colors: Dict[str, str]) -> Dict[str, str]:
        """Get an alternate color scheme"""
        if not original_colors:
            return random.choice(self.color_schemes)
        
        # Find a different color scheme
        for scheme in self.color_schemes:
            if scheme != original_colors:
                return scheme
        
        return original_colors
