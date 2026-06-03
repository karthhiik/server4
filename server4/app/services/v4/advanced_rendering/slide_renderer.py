"""
Slide Renderer - Main renderer for slide generation
Orchestrates HTML5 generation and Tailwind CSS integration
"""

from typing import Dict, Any, List, Optional
from app.services.v4.advanced_rendering.html5_generator import HTML5Generator
from app.services.v4.advanced_rendering.tailwind_integrator import TailwindIntegrator


class SlideRenderer:
    """
    Main renderer for slide generation
    Orchestrates HTML5 generation and Tailwind CSS integration
    """
    
    def __init__(self):
        self.html5_generator = HTML5Generator()
        self.tailwind_integrator = TailwindIntegrator()
    
    def render_slides(
        self,
        slides_data: List[Dict[str, Any]],
        design_system: Optional[Dict[str, Any]] = None,
        responsive: bool = True,
        accessible: bool = True
    ) -> Dict[str, Any]:
        """
        Render slides to HTML5 with Tailwind CSS
        
        Args:
            slides_data: List of slide data
            design_system: Optional design system configuration
            responsive: Whether to apply responsive design
            accessible: Whether to apply accessibility features
            
        Returns:
            Dictionary with rendered slides and metadata
        """
        # Generate HTML5 for each slide
        slides_html = []
        for slide_data in slides_data:
            slide_html = self.html5_generator.generate_slide(slide_data)
            
            # Apply Tailwind styling
            styled_html = self.tailwind_integrator.apply_styling(slide_html, slide_data)
            
            # Apply responsive design if requested
            if responsive:
                styled_html = self.tailwind_integrator.apply_responsive_design(styled_html)
            
            # Apply accessibility if requested
            if accessible:
                styled_html = self.tailwind_integrator.apply_accessibility_classes(styled_html)
            
            slides_html.append(styled_html)
        
        # Generate complete presentation
        presentation_html = self.html5_generator.generate_presentation(slides_data)
        
        # Generate Tailwind config
        tailwind_config = self.tailwind_integrator.generate_tailwind_config(
            design_system.get("colors") if design_system else None
        )
        
        # Generate custom CSS
        custom_css = self.tailwind_integrator.generate_custom_css(design_system)
        
        return {
            "slides_html": slides_html,
            "presentation_html": presentation_html,
            "tailwind_config": tailwind_config,
            "custom_css": custom_css,
            "metadata": {
                "slide_count": len(slides_data),
                "responsive": responsive,
                "accessible": accessible,
                "wcag_level": "2.1 AAA" if accessible else None
            }
        }
    
    def render_single_slide(
        self,
        slide_data: Dict[str, Any],
        design_system: Optional[Dict[str, Any]] = None,
        responsive: bool = True,
        accessible: bool = True
    ) -> str:
        """
        Render a single slide
        
        Args:
            slide_data: Slide data
            design_system: Optional design system configuration
            responsive: Whether to apply responsive design
            accessible: Whether to apply accessibility features
            
        Returns:
            Rendered HTML string
        """
        # Generate HTML5
        slide_html = self.html5_generator.generate_slide(slide_data)
        
        # Apply Tailwind styling
        styled_html = self.tailwind_integrator.apply_styling(slide_html, slide_data)
        
        # Apply responsive design if requested
        if responsive:
            styled_html = self.tailwind_integrator.apply_responsive_design(styled_html)
        
        # Apply accessibility if requested
        if accessible:
            styled_html = self.tailwind_integrator.apply_accessibility_classes(styled_html)
        
        return styled_html
    
    def validate_rendering(self, html: str) -> Dict[str, Any]:
        """
        Validate rendered HTML
        
        Args:
            html: HTML string to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_errors = []
        validation_warnings = []
        
        # Check for required elements
        if "<!DOCTYPE html>" not in html:
            validation_errors.append("Missing DOCTYPE declaration")
        
        if "<html" not in html:
            validation_errors.append("Missing html tag")
        
        if "<head>" not in html:
            validation_errors.append("Missing head tag")
        
        if "<body>" not in html:
            validation_errors.append("Missing body tag")
        
        # Check for accessibility
        if 'role="img"' not in html:
            validation_warnings.append("Missing ARIA roles for slides")
        
        if 'aria-label=' not in html:
            validation_warnings.append("Missing ARIA labels")
        
        # Check for Tailwind CDN
        if "tailwindcss.com" not in html:
            validation_warnings.append("Tailwind CDN not included")
        
        return {
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "warnings": validation_warnings
        }
