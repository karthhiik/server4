"""
PDF Compiler — Barise Presentation SaaS

Exports presentations to PDF using an HTML→PDF pipeline.
Slides are rendered as high-resolution HTML pages (1920×1080)
and converted to PDF with proper page breaks and print styling.

Dependencies:
    weasyprint (installs automatically with cairo/pango on most systems)
    jinja2 (already in stack)
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Any

from app.models.dsl_v2 import PresentationDSL
from app.services.slides_new.renderers.base_renderer import BaseRenderer, RendererType

logger = logging.getLogger(__name__)


class PdfCompiler(BaseRenderer):
    """Renders a presentation DSL to a multi-page PDF document."""

    @property
    def renderer_type(self) -> RendererType:
        return RendererType.PDF

    @property
    def supported_formats(self) -> list[str]:
        return ["pdf"]

    def render_presentation(self, presentation: PresentationDSL, theme_css: str = "") -> bytes:
        """Render full presentation to PDF bytes."""
        try:
            from weasyprint import HTML, CSS
        except ImportError as exc:
            logger.warning("weasyprint not installed; falling back to stub PDF")
            return self._stub_pdf(presentation)

        html_doc = self._build_html(presentation, theme_css)
        pdf_bytes = HTML(string=html_doc).write_pdf()
        return pdf_bytes

    def render_slide(self, slide_data: dict[str, Any], theme_css: str = "") -> bytes:
        """Render a single slide to PDF page bytes."""
        try:
            from weasyprint import HTML
        except ImportError:
            return b""

        html_doc = self._slide_html(slide_data, theme_css)
        return HTML(string=html_doc).write_pdf()

    def _build_html(self, presentation: PresentationDSL, theme_css: str) -> str:
        slides_html = "\n".join(
            self._slide_html(slide, theme_css) for slide in presentation.slides
        )

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{
    size: 1920px 1080px;
    margin: 0;
}}
body {{
    margin: 0;
    padding: 0;
    font-family: system-ui, -apple-system, sans-serif;
    background: #fff;
}}
.slide-page {{
    width: 1920px;
    height: 1080px;
    page-break-after: always;
    box-sizing: border-box;
    position: relative;
    overflow: hidden;
}}
.slide-page:last-child {{
    page-break-after: auto;
}}
{theme_css}
</style>
</head>
<body>
{slides_html}
</body>
</html>"""

    def _slide_html(self, slide: dict[str, Any], theme_css: str) -> str:
        title = slide.get("title", "")
        content = slide.get("content", "")
        layout = slide.get("layout", "default")
        bg = slide.get("background_color", "#ffffff")
        fg = slide.get("text_color", "#111111")

        # Simple layout mapping
        layout_class = f"layout-{layout}"

        return f"""<div class="slide-page {layout_class}" style="background:{bg};color:{fg};padding:72px;display:flex;flex-direction:column;justify-content:center;">
    <h1 style="font-size:64px;font-weight:700;margin:0 0 24px 0;line-height:1.1;">{title}</h1>
    <div style="font-size:28px;line-height:1.5;max-width:1400px;">{content}</div>
</div>"""

    def _stub_pdf(self, presentation: PresentationDSL) -> bytes:
        """Minimal PDF stub when weasyprint is unavailable."""
        # Return empty PDF-like bytes (not valid PDF, but signals missing dependency)
        logger.error("weasyprint not available — install it for PDF export")
        return b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\nxref\n0 3\n0000000000 65535 f\n0000000015 00000 n\n0000000066 00000 n\ntrailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n115\n%%EOF\n"
