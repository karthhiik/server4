"""
Tailwind Integrator - Integrates Tailwind CSS styling into HTML5 slides
Applies design tokens and responsive design principles
"""

from typing import Dict, Any, List, Optional


class TailwindIntegrator:
    """
    Integrates Tailwind CSS styling into HTML5 slides
    Applies design tokens for consistent, professional styling
    """
    
    def __init__(self):
        self.design_tokens = {
            "colors": {
                "primary": "text-blue-400",
                "secondary": "text-purple-400",
                "accent": "text-pink-400",
                "background": "bg-gray-900",
                "surface": "bg-gray-800",
                "text": "text-white",
                "text-muted": "text-gray-400"
            },
            "spacing": {
                "xs": "p-2",
                "sm": "p-4",
                "md": "p-6",
                "lg": "p-8",
                "xl": "p-12"
            },
            "typography": {
                "headline": "text-4xl font-bold",
                "subheadline": "text-2xl font-semibold",
                "body": "text-lg",
                "caption": "text-sm"
            },
            "layout": {
                "container": "max-w-6xl mx-auto",
                "grid": "grid grid-cols-2 gap-6",
                "flex": "flex items-center justify-between"
            }
        }
    
    def apply_styling(self, html: str, slide_data: Dict[str, Any]) -> str:
        """
        Apply Tailwind CSS styling to HTML
        
        Args:
            html: HTML string to style
            slide_data: Slide data for context
            
        Returns:
            Styled HTML string
        """
        # Apply design tokens based on slide data
        styled_html = html
        
        # Add Tailwind classes to slide container
        styled_html = styled_html.replace(
            'class="slide-container"',
            f'class="slide-container {self.design_tokens["layout"]["container"]} {self.design_tokens["spacing"]["lg"]}"'
        )
        
        # Style headline
        styled_html = styled_html.replace(
            'class="slide-headline"',
            f'class="slide-headline {self.design_tokens["typography"]["headline"]} {self.design_tokens["colors"]["primary"]} mb-4"'
        )
        
        # Style subheadline
        styled_html = styled_html.replace(
            'class="slide-subheadline"',
            f'class="slide-subheadline {self.design_tokens["typography"]["subheadline"]} {self.design_tokens["colors"]["text-muted"]} mb-6"'
        )
        
        # Style bullets
        styled_html = styled_html.replace(
            'class="slide-bullets"',
            f'class="slide-bullets {self.design_tokens["typography"]["body"]} {self.design_tokens["colors"]["text"]} space-y-2 ml-6"'
        )
        
        # Style body
        styled_html = styled_html.replace(
            'class="slide-body"',
            f'class="slide-body {self.design_tokens["typography"]["body"]} {self.design_tokens["colors"]["text"]} mt-4"'
        )
        
        # Style image
        styled_html = styled_html.replace(
            'class="slide-image"',
            f'class="slide-image w-full h-auto rounded-lg shadow-lg"'
        )
        
        # Style table
        styled_html = styled_html.replace(
            'class="slide-table"',
            f'class="slide-table w-full border-collapse {self.design_tokens["colors"]["text"]}"'
        )
        
        return styled_html
    
    def generate_tailwind_config(self, custom_colors: Optional[Dict[str, str]] = None) -> str:
        """
        Generate Tailwind CSS config with custom design tokens
        
        Args:
            custom_colors: Optional custom color palette
            
        Returns:
            Tailwind config JavaScript string
        """
        config = {
            "theme": {
                "extend": {
                    "colors": {
                        "primary": custom_colors or {
                            "50": "#eff6ff",
                            "100": "#dbeafe",
                            "200": "#bfdbfe",
                            "300": "#93c5fd",
                            "400": "#60a5fa",
                            "500": "#3b82f6",
                            "600": "#2563eb",
                            "700": "#1d4ed8",
                            "800": "#1e40af",
                            "900": "#1e3a8a"
                        }
                    },
                    "spacing": {
                        "128": "32rem",
                        "144": "36rem"
                    },
                    "typography": {
                        "fontFamily": {
                            "sans": ["Inter", "system-ui", "sans-serif"],
                            "display": ["Cal Sans", "Inter", "sans-serif"]
                        }
                    }
                }
            }
        }
        
        import json
        return f"tailwind.config = {json.dumps(config, indent=2)};"
    
    def apply_responsive_design(self, html: str) -> str:
        """
        Apply responsive design classes
        
        Args:
            html: HTML string to make responsive
            
        Returns:
            Responsive HTML string
        """
        # Add responsive classes for different screen sizes
        responsive_html = html
        
        # Make container responsive
        responsive_html = responsive_html.replace(
            'max-w-6xl mx-auto',
            'max-w-6xl mx-auto px-4 sm:px-6 lg:px-8'
        )
        
        # Make typography responsive
        responsive_html = responsive_html.replace(
            'text-4xl font-bold',
            'text-3xl sm:text-4xl lg:text-5xl font-bold'
        )
        
        responsive_html = responsive_html.replace(
            'text-2xl font-semibold',
            'text-xl sm:text-2xl lg:text-3xl font-semibold'
        )
        
        responsive_html = responsive_html.replace(
            'text-lg',
            'text-base sm:text-lg lg:text-xl'
        )
        
        return responsive_html
    
    def apply_accessibility_classes(self, html: str) -> str:
        """
        Apply accessibility-focused classes
        
        Args:
            html: HTML string to enhance for accessibility
            
        Returns:
            Accessibility-enhanced HTML string
        """
        accessible_html = html
        
        # Add focus indicators
        accessible_html = accessible_html.replace(
            '<a href=',
            '<a class="focus:outline-none focus:ring-2 focus:ring-blue-500" href='
        )
        
        # Add reduced motion support
        accessible_html = accessible_html.replace(
            '<div class="slide-container"',
            '<div class="slide-container motion-reduce:transition-none"'
        )
        
        return accessible_html
    
    def generate_custom_css(self, design_system: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate custom CSS for advanced styling
        
        Args:
            design_system: Optional design system configuration
            
        Returns:
            Custom CSS string
        """
        css = """
<style>
  /* Custom slide animations */
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }
  
  .slide-container {
    animation: fadeIn 0.5s ease-out;
  }
  
  /* Custom scrollbar */
  ::-webkit-scrollbar {
    width: 8px;
  }
  
  ::-webkit-scrollbar-track {
    background: #1f2937;
  }
  
  ::-webkit-scrollbar-thumb {
    background: #4b5563;
    border-radius: 4px;
  }
  
  ::-webkit-scrollbar-thumb:hover {
    background: #6b7280;
  }
  
  /* Print styles */
  @media print {
    .slide-container {
      page-break-after: always;
    }
  }
</style>
"""
        return css
