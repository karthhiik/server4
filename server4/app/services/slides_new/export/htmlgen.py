"""
HTML Export Builder - Phase 2
Generates HTML presentations from slide data.
"""

import json
from typing import Any, Dict, List, Optional

from app.services.slides_new.design.system import DesignSystem


class HtmlExporter:
    """
    HTML Export Builder - creates HTML presentations from slide data.

    Features:
    - Responsive 16:9 slides
    - CSS animations
    - Keyboard navigation
    - Print-friendly
    - Custom fonts and colors
    """

    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family={fonts}&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: {primary};
            --secondary: {secondary};
            --accent: {accent};
            --background: {background};
            --text: {text};
            --muted: {muted};
            --spacing-base: {spacing_base}px;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        html, body {{
            height: 100%;
            font-family: {font_body}, sans-serif;
            background: #1a1a1a;
            color: var(--text);
        }}
        
        .slides-container {{
            height: 100vh;
            width: 100vw;
            overflow: hidden;
            position: relative;
        }}
        
        .slide {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: var(--background);
            display: flex;
            flex-direction: column;
            padding: {padding}px;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.5s ease;
        }}
        
        .slide.active {{
            opacity: 1;
            transform: translateX(0);
        }}
        
        .slide.prev {{
            transform: translateX(-100%);
        }}
        
        .slide-title {{
            font-family: {font_heading}, sans-serif;
            font-size: {h1_size}px;
            font-weight: {h1_weight};
            color: var(--primary);
            margin-bottom: {spacing_section}px;
        }}
        
        .slide-content {{
            flex: 1;
            display: flex;
            gap: {spacing_loose}px;
        }}
        
        .column {{
            flex: 1;
            padding: {spacing_loose}px;
        }}
        
        .bullet-list {{
            list-style: none;
        }}
        
        .bullet-list li {{
            font-size: {body_size}px;
            line-height: {line_height};
            margin-bottom: {spacing_base}px;
            padding-left: 24px;
            position: relative;
        }}
        
        .bullet-list li::before {{
            content: "•";
            color: var(--accent);
            position: absolute;
            left: 0;
            font-size: 1.2em;
        }}
        
        .quote {{
            font-size: 28px;
            font-style: italic;
            text-align: center;
            padding: 48px;
            color: var(--primary);
        }}
        
        .quote-author {{
            font-size: 18px;
            margin-top: 24px;
            color: var(--muted);
        }}
        
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: {spacing_loose}px;
            margin-top: {spacing_section}px;
        }}
        
        .kpi-card {{
            background: var(--secondary);
            padding: {spacing_loose}px;
            border-radius: {radius}px;
            text-align: center;
        }}
        
        .kpi-value {{
            font-size: 48px;
            font-weight: bold;
            color: var(--accent);
        }}
        
        .kpi-label {{
            font-size: 14px;
            color: var(--muted);
            margin-top: 8px;
        }}
        
        .navigation {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 12px;
            z-index: 100;
        }}
        
        .nav-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--muted);
            cursor: pointer;
            transition: all 0.3s;
        }}
        
        .nav-dot.active {{
            background: var(--accent);
            transform: scale(1.2);
        }}
        
        .progress-bar {{
            position: fixed;
            top: 0;
            left: 0;
            height: 4px;
            background: var(--accent);
            transition: width 0.3s;
            z-index: 100;
        }}
        
        @media print {{
            .slide {{
                position: relative;
                page-break-after: always;
                opacity: 1;
                transform: none;
            }}
            .navigation, .progress-bar {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="progress-bar" id="progress"></div>
    <div class="slides-container" id="slides">
        {slides_html}
    </div>
    <div class="navigation" id="nav">
        {nav_dots}
    </div>
    <script>
        let currentSlide = 0;
        const slides = document.querySelectorAll('.slide');
        const total = slides.length;
        
        function showSlide(index) {{
            if (index < 0) index = 0;
            if (index >= total) index = total - 1;
            
            currentSlide = index;
            
            slides.forEach((slide, i) => {{
                slide.classList.remove('active', 'prev');
                if (i === index) {{
                    slide.classList.add('active');
                }} else if (i < index) {{
                    slide.classList.add('prev');
                }}
            }});
            
            document.getElementById('progress').style.width = ((index + 1) / total * 100) + '%';
            
            const dots = document.querySelectorAll('.nav-dot');
            dots.forEach((dot, i) => {{
                dot.classList.toggle('active', i === index);
            }});
        }}
        
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowRight' || e.key === ' ') {{
                showSlide(currentSlide + 1);
            }} else if (e.key === 'ArrowLeft') {{
                showSlide(currentSlide - 1);
            }}
        }});
        
        document.getElementById('nav').addEventListener('click', (e) => {{
            if (e.target.classList.contains('nav-dot')) {{
                const index = Array.from(e.target.parentElement.children).indexOf(e.target);
                showSlide(index);
            }}
        }});
        
        showSlide(0);
    </script>
</body>
</html>"""

    def __init__(self, design_system: Optional[DesignSystem] = None):
        self.design = design_system or DesignSystem()

    def _generate_slide_html(self, slide_data: Dict[str, Any], index: int) -> str:
        """Generate HTML for a single slide"""
        layout = slide_data.get("layout", "bullets")
        title = slide_data.get("title", "")
        content = slide_data.get("content", {})

        if layout == "title-hero":
            subtitle = content.get("headline", "")
            return f"""
            <div class="slide active">
                <h1 class="slide-title" style="font-size: 64px; text-align: center; margin: auto;">{title}</h1>
                {f'<p style="font-size: 24px; text-align: center; color: var(--muted);">{subtitle}</p>' if subtitle else ""}
            </div>
            """

        elif layout == "quote":
            quote = content.get("quote", {})
            return f"""
            <div class="slide">
                <div class="quote">"{quote.get("text", "")}"</div>
                <div class="quote-author">- {quote.get("author", "")}</div>
            </div>
            """

        elif layout == "kpi-dashboard":
            data = content.get("data", [])
            kpi_html = ""
            for d in data:
                kpi_html += f"""
                <div class="kpi-card">
                    <div class="kpi-value">{d.get("value", "")}</div>
                    <div class="kpi-label">{d.get("label", "")}</div>
                </div>
                """
            return f"""
            <div class="slide">
                <h2 class="slide-title">{title}</h2>
                <div class="kpi-grid">{kpi_html}</div>
            </div>
            """

        elif layout == "two-column":
            bullets = content.get("bullets", [])
            mid = len(bullets) // 2
            left = bullets[:mid]
            right = bullets[mid:]

            left_html = "".join(f"<li>{b}</li>" for b in left)
            right_html = "".join(f"<li>{b}</li>" for b in right)

            return f"""
            <div class="slide">
                <h2 class="slide-title">{title}</h2>
                <div class="slide-content">
                    <div class="column"><ul class="bullet-list">{left_html}</ul></div>
                    <div class="column"><ul class="bullet-list">{right_html}</ul></div>
                </div>
            </div>
            """

        else:
            bullets = content.get("bullets", [])
            bullets_html = "".join(f"<li>{b}</li>" for b in bullets)

            return f"""
            <div class="slide">
                <h2 class="slide-title">{title}</h2>
                <ul class="bullet-list">{bullets_html}</ul>
            </div>
            """

    def export_presentation(
        self, slides_data: List[Dict[str, Any]], metadata: Dict[str, Any] = None
    ) -> str:
        """Export presentation to HTML"""
        design = self.design.to_dict()

        colors = design["colors"]
        typography = design["typography"]
        spacing = design["spacing"]

        fonts = design.get("fonts", {})
        font_family = (
            f"{fonts.get('heading', 'Inter')}|{fonts.get('body', 'Inter')}".replace(
                " ", "+"
            )
        )

        slides_html = "".join(
            self._generate_slide_html(slide, i) for i, slide in enumerate(slides_data)
        )

        nav_dots = "".join(
            f'<div class="nav-dot{" active" if i == 0 else ""}"></div>'
            for i in range(len(slides_data))
        )

        h1 = typography.get("h1", {"size": 44, "weight": 700})

        return self.HTML_TEMPLATE.format(
            title=metadata.get("topic", "Presentation") if metadata else "Presentation",
            primary=colors.get("primary", "#1A1A2E"),
            secondary=colors.get("secondary", "#16213E"),
            accent=colors.get("accent", "#E94560"),
            background=colors.get("background", "#FFFFFF"),
            text=colors.get("text", "#1A1A2E"),
            muted=colors.get("muted", "#6B7280"),
            font_heading=fonts.get("heading", "Inter"),
            font_body=fonts.get("body", "Inter"),
            fonts=font_family,
            padding=spacing.get("loose", 16),
            spacing_base=spacing.get("base", 8),
            spacing_loose=spacing.get("loose", 16),
            spacing_section=spacing.get("section", 32),
            h1_size=h1.get("size", 44),
            h1_weight=h1.get("weight", 700),
            body_size=typography.get("body", {}).get("size", 18),
            line_height=typography.get("body", {}).get("lineHeight", 1.6),
            radius=self.design.border_radius,
            slides_html=slides_html,
            nav_dots=nav_dots,
        )

    def export_to_file(
        self, slides_data: List[Dict], filepath: str, metadata: Dict = None
    ):
        """Export to HTML file"""
        html = self.export_presentation(slides_data, metadata)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)


def export_to_html(presentation: Dict[str, Any], filepath: Optional[str] = None) -> str:
    """
    Convenience function to export presentation to HTML.

    Args:
        presentation: Full presentation dict with slides and metadata
        filepath: Optional filepath to save to

    Returns:
        HTML string
    """
    preset = presentation.get("design_system", {}).get("preset", "yc_pitch")
    design = DesignSystem(preset)

    exporter = HtmlExporter(design)
    slides = presentation.get("slides", [])
    metadata = presentation.get("metadata", {})

    html = exporter.export_presentation(slides, metadata)

    if filepath:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

    return html
