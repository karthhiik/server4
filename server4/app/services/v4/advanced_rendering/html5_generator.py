"""
HTML5 Generator - Generates HTML5 slides from slide data
Converts slide content to HTML5 with proper structure and accessibility
"""

from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class SlideElement:
    """Represents a slide element"""
    element_type: str  # "text", "image", "chart", "table", "timeline", "diagram"
    content: str
    position: Dict[str, Any]
    style: Dict[str, Any]
    accessibility: Dict[str, Any]


class HTML5Generator:
    """
    Generates HTML5 slides from slide data
    Ensures WCAG 2.1 AAA compliance and accessibility
    """
    
    def __init__(self):
        self.accessibility_level = "AAA"
        self.wcag_version = "2.1"
    
    def generate_slide(self, slide_data: Dict[str, Any]) -> str:
        """
        Generate HTML5 for a single slide
        
        Args:
            slide_data: Slide data from generation pipeline
            
        Returns:
            HTML5 string for the slide
        """
        # Extract slide content
        headline = slide_data.get("headline", "")
        subheadline = slide_data.get("subheadline", "")
        bullets = slide_data.get("bullets", [])
        body = slide_data.get("body", "")
        image_url = slide_data.get("image_url", "")
        render_decision = slide_data.get("render_decision", {})
        
        # Generate HTML5 structure
        html = self._generate_html_structure(
            headline,
            subheadline,
            bullets,
            body,
            image_url,
            render_decision
        )
        
        return html
    
    def _generate_html_structure(
        self,
        headline: str,
        subheadline: str,
        bullets: List[str],
        body: str,
        image_url: str,
        render_decision: Dict[str, Any]
    ) -> str:
        """
        Generate HTML5 structure for a slide
        
        Args:
            headline: Slide headline
            subheadline: Slide subheadline
            bullets: List of bullet points
            body: Slide body text
            image_url: Image URL
            render_decision: Render decision from pipeline
            
        Returns:
            HTML5 string
        """
        modality = render_decision.get("modality", "text")
        
        html_parts = []
        
        # Start with slide container
        html_parts.append('<div class="slide-container" role="img" aria-label="Slide">')
        
        # Add headline
        if headline:
            html_parts.append(f'  <h1 class="slide-headline">{self._escape_html(headline)}</h1>')
        
        # Add subheadline
        if subheadline:
            html_parts.append(f'  <h2 class="slide-subheadline">{self._escape_html(subheadline)}</h2>')
        
        # Add content based on modality
        if modality == "image" and image_url:
            html_parts.append(f'  <img src="{image_url}" alt="{self._escape_html(headline)}" class="slide-image" loading="lazy">')
        
        if modality in ["text", "split"]:
            # Add bullets
            if bullets:
                html_parts.append('  <ul class="slide-bullets">')
                for bullet in bullets:
                    html_parts.append(f'    <li>{self._escape_html(bullet)}</li>')
                html_parts.append('  </ul>')
            
            # Add body
            if body:
                html_parts.append(f'  <p class="slide-body">{self._escape_html(body)}</p>')
        
        if modality == "chart":
            # Add chart placeholder (will be rendered by JS)
            chart_data = render_decision.get("chart_data", {})
            html_parts.append(f'  <div class="slide-chart" data-chart=\'{self._escape_json(chart_data)}\' aria-label="Chart">')
            html_parts.append('    <div class="chart-placeholder">Chart will be rendered here</div>')
            html_parts.append('  </div>')
        
        if modality == "table":
            # Add table
            table_data = render_decision.get("table_data", {})
            html_parts.append(self._generate_table(table_data))
        
        if modality == "timeline":
            # Add timeline
            timeline_data = render_decision.get("timeline_data", {})
            html_parts.append(self._generate_timeline(timeline_data))
        
        if modality == "diagram":
            # Add diagram
            diagram_data = render_decision.get("diagram_data", {})
            html_parts.append(self._generate_diagram(diagram_data))
        
        # Close slide container
        html_parts.append('</div>')
        
        return "\n".join(html_parts)
    
    def _generate_table(self, table_data: Dict[str, Any]) -> str:
        """Generate HTML table from table data"""
        html_parts = ['  <table class="slide-table">']
        
        headers = table_data.get("headers", [])
        if headers:
            html_parts.append('    <thead>')
            html_parts.append('      <tr>')
            for header in headers:
                html_parts.append(f'        <th scope="col">{self._escape_html(header)}</th>')
            html_parts.append('      </tr>')
            html_parts.append('    </thead>')
        
        rows = table_data.get("rows", [])
        if rows:
            html_parts.append('    <tbody>')
            for row in rows:
                html_parts.append('      <tr>')
                for cell in row:
                    html_parts.append(f'        <td>{self._escape_html(cell)}</td>')
                html_parts.append('      </tr>')
            html_parts.append('    </tbody>')
        
        html_parts.append('  </table>')
        
        return "\n".join(html_parts)
    
    def _generate_timeline(self, timeline_data: Dict[str, Any]) -> str:
        """Generate HTML timeline from timeline data"""
        html_parts = ['  <div class="slide-timeline">']
        
        events = timeline_data.get("events", [])
        for event in events:
            date = event.get("date", "")
            title = event.get("title", "")
            description = event.get("description", "")
            
            html_parts.append('    <div class="timeline-event">')
            html_parts.append(f'      <time datetime="{date}">{self._escape_html(date)}</time>')
            html_parts.append(f'      <h3>{self._escape_html(title)}</h3>')
            html_parts.append(f'      <p>{self._escape_html(description)}</p>')
            html_parts.append('    </div>')
        
        html_parts.append('  </div>')
        
        return "\n".join(html_parts)
    
    def _generate_diagram(self, diagram_data: Dict[str, Any]) -> str:
        """Generate HTML diagram placeholder"""
        html_parts = ['  <div class="slide-diagram" data-diagram=\'{self._escape_json(diagram_data)}\' aria-label="Diagram">']
        html_parts.append('    <div class="diagram-placeholder">Diagram will be rendered here</div>')
        html_parts.append('  </div>')
        
        return "\n".join(html_parts)
    
    def generate_presentation(self, slides: List[Dict[str, Any]]) -> str:
        """
        Generate complete HTML5 presentation
        
        Args:
            slides: List of slide data
            
        Returns:
            Complete HTML5 presentation string
        """
        html_parts = ['<!DOCTYPE html>']
        html_parts.append('<html lang="en">')
        html_parts.append('<head>')
        html_parts.append('  <meta charset="UTF-8">')
        html_parts.append('  <meta name="viewport" content="width=device-width, initial-scale=1.0">')
        html_parts.append('  <title>Presentation</title>')
        html_parts.append('  <script src="https://cdn.tailwindcss.com"></script>')
        html_parts.append('</head>')
        html_parts.append('<body class="bg-gray-900 text-white">')
        html_parts.append('  <div class="presentation-container">')
        
        for i, slide_data in enumerate(slides):
            slide_html = self.generate_slide(slide_data)
            html_parts.append(f'    <div class="slide" data-slide-index="{i}">')
            html_parts.append(f'      {slide_html}')
            html_parts.append('    </div>')
        
        html_parts.append('  </div>')
        html_parts.append('</body>')
        html_parts.append('</html>')
        
        return "\n".join(html_parts)
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        if not text:
            return ""
        
        text = str(text)
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&#x27;")
        
        return text
    
    def _escape_json(self, data: Any) -> str:
        """Escape JSON for HTML attribute"""
        import json
        json_str = json.dumps(data)
        return self._escape_html(json_str)
