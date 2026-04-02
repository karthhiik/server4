"""
PDF Builder — generates PDF presentations using WeasyPrint from HTML.
"""

import io
from typing import Optional

import structlog

from app.mcp.render_mcp.builders.html_builder import HtmlBuilder
from app.mcp.render_mcp.config import PDF_PAGE_WIDTH, PDF_PAGE_HEIGHT

logger = structlog.get_logger()


class PdfBuilder:
    """Builds PDF presentations by rendering HTML through WeasyPrint."""

    def __init__(self):
        self.html_builder = HtmlBuilder()

    def build(self, slides: list[dict], theme: dict, metadata: dict = None) -> bytes:
        """Build a PDF from slides. Returns bytes."""
        try:
            from weasyprint import HTML
        except ImportError:
            raise RuntimeError("WeasyPrint not installed. Install with: pip install weasyprint")

        # Generate paginated HTML (not Reveal.js, but print-optimized)
        html_content = self._build_print_html(slides, theme, metadata)

        pdf_bytes = HTML(string=html_content).write_pdf()
        logger.info("pdf_built", slide_count=len(slides), size_kb=len(pdf_bytes) // 1024)
        return pdf_bytes

    def _build_print_html(self, slides: list[dict], theme: dict, metadata: dict = None) -> str:
        """Generate print-optimized HTML for PDF rendering."""
        import html as html_mod

        metadata = metadata or {}
        colors = theme.get("colors", {})
        fonts = theme.get("fonts", {})
        heading_font = fonts.get("heading", "Inter")
        body_font = fonts.get("body", "Inter")

        pages = []
        for slide in slides:
            content = slide.get("content", {})
            layout = slide.get("layout", "bullets")

            title = html_mod.escape(content.get("title", ""))
            body_parts = []

            if content.get("subtitle"):
                body_parts.append(f'<p class="subtitle">{html_mod.escape(content["subtitle"])}</p>')

            if content.get("bullets"):
                items = "\n".join(f"<li>{html_mod.escape(str(b))}</li>" for b in content["bullets"])
                body_parts.append(f"<ul>{items}</ul>")

            if content.get("body_text"):
                body_parts.append(f'<p>{html_mod.escape(content["body_text"])}</p>')

            if content.get("quote_text"):
                author = content.get("quote_author", "")
                body_parts.append(
                    f'<blockquote>"{html_mod.escape(content["quote_text"])}"'
                    f'<cite>— {html_mod.escape(author)}</cite></blockquote>'
                )

            if content.get("metrics"):
                cards = "".join(
                    f'<div class="metric"><span class="val">{html_mod.escape(str(m.get("value","")))}</span>'
                    f'<span class="lbl">{html_mod.escape(str(m.get("label","")))}</span></div>'
                    for m in content["metrics"]
                )
                body_parts.append(f'<div class="metrics-row">{cards}</div>')

            if content.get("events"):
                evts = "".join(
                    f'<div class="evt"><strong>{html_mod.escape(e.get("date",""))}</strong>'
                    f'<p>{html_mod.escape(e.get("description",""))}</p></div>'
                    for e in content["events"]
                )
                body_parts.append(f'<div class="timeline-row">{evts}</div>')

            inner = "\n".join(body_parts)
            is_hero = layout == "title-hero"
            page_class = "page hero" if is_hero else "page"
            pages.append(f'<div class="{page_class}"><h1>{title}</h1>{inner}</div>')

        pages_html = "\n".join(pages)

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{ size: {PDF_PAGE_WIDTH} {PDF_PAGE_HEIGHT}; margin: 1.5cm; }}
body {{ font-family: '{body_font}', sans-serif; color: {colors.get('text_primary','#111827')}; margin: 0; }}
.page {{ page-break-after: always; padding: 2cm; height: calc({PDF_PAGE_HEIGHT} - 3cm); position: relative; }}
.page:last-child {{ page-break-after: auto; }}
h1 {{ font-family: '{heading_font}', sans-serif; font-size: 28pt; margin-bottom: 0.5em; color: {colors.get('text_primary','#111827')}; }}
.hero {{ background: {colors.get('primary','#2563eb')}; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }}
.hero h1 {{ color: #fff; font-size: 36pt; }}
.hero .subtitle {{ color: rgba(255,255,255,0.85); font-size: 18pt; }}
ul {{ padding-left: 1.5em; }}
li {{ font-size: 14pt; margin-bottom: 0.4em; }}
blockquote {{ font-size: 18pt; font-style: italic; border-left: 4px solid {colors.get('primary','#2563eb')}; padding-left: 1em; }}
cite {{ display: block; font-size: 12pt; margin-top: 0.5em; font-style: normal; }}
.metrics-row {{ display: flex; gap: 1em; }}
.metric {{ text-align: center; flex: 1; }}
.val {{ display: block; font-size: 28pt; font-weight: bold; color: {colors.get('primary','#2563eb')}; }}
.lbl {{ display: block; font-size: 10pt; color: {colors.get('text_secondary','#6b7280')}; }}
.timeline-row {{ display: flex; gap: 1em; }}
.evt {{ flex: 1; text-align: center; }}
.evt strong {{ color: {colors.get('primary','#2563eb')}; }}
</style>
</head>
<body>
{pages_html}
</body>
</html>"""
