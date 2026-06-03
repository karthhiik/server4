"""
V4 PDF Export Service — Phase 4-3

Generates PDF exports from V4 compiled slides using Playwright for pixel-perfect rendering.

This service mirrors the V4PptxBuilder pattern, providing a V4-specific PDF export
that works with compiled_slides (same as preview) to ensure export matches exactly
what the user sees in the editor.
"""

from __future__ import annotations

import asyncio
import html
import structlog
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = structlog.get_logger(__name__)


@dataclass
class PDFOptions:
    """PDF export options."""
    format: str = "A4"
    margin_top: str = "0.5in"
    margin_bottom: str = "0.5in"
    margin_left: str = "0.5in"
    margin_right: str = "0.5in"
    print_background: bool = True
    prefer_css_page_size: bool = True


class V4PDFBuilder:
    """
    V4-specific PDF builder that exports compiled slides to PDF.
    
    Uses Playwright to render slides as HTML and convert to PDF for
    pixel-perfect output matching the editor preview.
    """
    
    def __init__(self):
        self.logger = logger
    
    async def build_async(
        self,
        slides: List[Dict[str, Any]],
        design_tokens: Dict[str, Any],
        metadata: Dict[str, Any],
        options: Optional[PDFOptions] = None,
    ) -> bytes:
        """Async variant of ``build`` for callers already inside an event loop.

        Bug C fix: Playwright requires ``asyncio.create_subprocess_exec`` to
        spawn the chromium driver. On Windows under uvicorn, the default
        event loop is ``WindowsSelectorEventLoopPolicy`` whose loop does NOT
        implement subprocess transports — every Playwright call raises
        ``NotImplementedError``. We sidestep this by running the entire
        Playwright invocation in a dedicated worker thread that owns its own
        ``ProactorEventLoop`` (the one Windows policy that supports
        subprocess transports). The host event loop is unaffected.
        """
        options = options or PDFOptions()
        if not slides:
            from app.services.v4.errors import ExportContentEmpty

            raise ExportContentEmpty("V4PDFBuilder.build_async: slides is empty")
        try:
            html_content = self._generate_html(slides, design_tokens, metadata)
            pdf_bytes = await asyncio.to_thread(
                self._html_to_pdf_isolated, html_content, options,
            )
            self.logger.info(
                "v4_pdf_export_success",
                slide_count=len(slides),
                pdf_size=len(pdf_bytes),
            )
            return pdf_bytes
        except Exception as e:  # noqa: BLE001
            self.logger.error(
                "v4_pdf_export_failed",
                error=str(e),
                slide_count=len(slides),
            )
            raise

    def _html_to_pdf_isolated(self, html: str, options: PDFOptions) -> bytes:
        """Run Playwright on its own ProactorEventLoop in this thread.

        Must run in a worker thread (called via ``asyncio.to_thread``).
        Creates a fresh ``ProactorEventLoop`` so chromium can spawn even
        when the host process uses the selector loop. The loop is closed
        when finished so the thread doesn't leak resources.
        """
        import sys as _sys

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            self.logger.warning(
                "playwright_not_available",
                message="Playwright not installed, using fallback PDF generation",
            )
            return self._fallback_pdf(html, options)

        async def _drive() -> bytes:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                try:
                    page = await browser.new_page()
                    await page.set_content(html)
                    pdf_bytes = await page.pdf(
                        format=options.format,
                        margin={
                            "top": options.margin_top,
                            "bottom": options.margin_bottom,
                            "left": options.margin_left,
                            "right": options.margin_right,
                        },
                        print_background=options.print_background,
                        prefer_css_page_size=options.prefer_css_page_size,
                    )
                    return pdf_bytes
                finally:
                    await browser.close()

        # On Windows, force the proactor loop in this worker thread.
        # On Linux/macOS the default loop already supports subprocess.
        if _sys.platform == "win32":
            loop = asyncio.ProactorEventLoop()
        else:
            loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(_drive())
        finally:
            try:
                loop.close()
            except Exception:  # noqa: BLE001
                pass

    async def _html_to_pdf_async(self, html: str, options: PDFOptions) -> bytes:
        """Async HTML-to-PDF rendering on the caller's event loop."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            self.logger.warning(
                "playwright_not_available",
                message="Playwright not installed, using fallback PDF generation",
            )
            return self._fallback_pdf(html, options)

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            try:
                page = await browser.new_page()
                await page.set_content(html)
                pdf_bytes = await page.pdf(
                    format=options.format,
                    margin={
                        "top": options.margin_top,
                        "bottom": options.margin_bottom,
                        "left": options.margin_left,
                        "right": options.margin_right,
                    },
                    print_background=options.print_background,
                    prefer_css_page_size=options.prefer_css_page_size,
                )
                return pdf_bytes
            finally:
                await browser.close()

    def build(
        self,
        slides: List[Dict[str, Any]],
        design_tokens: Dict[str, Any],
        metadata: Dict[str, Any],
        options: Optional[PDFOptions] = None,
    ) -> bytes:
        """
        Build PDF from V4 compiled slides.
        
        Args:
            slides: List of compiled slide dictionaries
            design_tokens: Design token dictionary
            metadata: Presentation metadata (title, company_name, etc.)
            options: PDF export options
            
        Returns:
            PDF file as bytes
        """
        options = options or PDFOptions()
        if not slides:
            # Slice 4 (Export Parity): refuse to emit a corrupt 0-page
            # PDF. Routers translate this into a structured 409 envelope.
            from app.services.v4.errors import ExportContentEmpty

            raise ExportContentEmpty("V4PDFBuilder.build: slides is empty")
        
        try:
            # Generate HTML from compiled slides
            html_content = self._generate_html(slides, design_tokens, metadata)
            
            # Convert HTML to PDF using Playwright
            pdf_bytes = self._html_to_pdf(html_content, options)
            
            self.logger.info(
                "v4_pdf_export_success",
                slide_count=len(slides),
                pdf_size=len(pdf_bytes),
            )
            
            return pdf_bytes
            
        except Exception as e:
            self.logger.error(
                "v4_pdf_export_failed",
                error=str(e),
                slide_count=len(slides),
            )
            raise
    
    def _generate_html(
        self,
        slides: List[Dict[str, Any]],
        design_tokens: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> str:
        """
        Generate HTML from compiled slides for PDF rendering.
        
        Args:
            slides: List of compiled slide dictionaries
            design_tokens: Design token dictionary
            metadata: Presentation metadata
            
        Returns:
            HTML string for PDF generation
        """
        # Extract design tokens. V4 generation stores palette/fonts, while
        # older callers may pass colors/typography. Support both shapes so
        # PDF export matches the deck-level design system.
        colors = design_tokens.get("colors") or design_tokens.get("palette") or {}
        typography = design_tokens.get("typography") or design_tokens.get("fonts") or {}
        spacing = design_tokens.get("spacing", {})
        
        # Build CSS from design tokens
        css = self._build_css(colors, typography, spacing)
        
        # Build slide HTML
        slide_html = ""
        for i, slide in enumerate(slides):
            slide_html += self._build_slide_html(slide, i, design_tokens)
        
        # Combine into full HTML document
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(str(metadata.get('title', 'Presentation')))}</title>
    <style>
        {css}
    </style>
</head>
<body>
    <div class="presentation">
        {slide_html}
    </div>
</body>
</html>
"""
        return html
    
    def _build_css(
        self,
        colors: Dict[str, Any],
        typography: Dict[str, Any],
        spacing: Dict[str, Any],
    ) -> str:
        """Build CSS from design tokens."""
        # Extract color values
        bg_primary = colors.get("background", "#ffffff")
        text_primary = colors.get("text_primary", "#0f172a")
        text_secondary = colors.get("text_secondary", "#475569")
        accent = colors.get("accent", "#3b82f6")
        
        # Extract typography
        font_family = typography.get("font_family") or typography.get("body") or "Inter, system-ui, sans-serif"
        font_size_base = typography.get("font_size_base", "16px")
        
        # Build CSS
        css = f"""
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: {font_family};
    font-size: {font_size_base};
    color: {text_primary};
    background: {bg_primary};
    line-height: 1.5;
}}

.presentation {{
    max-width: 1200px;
    margin: 0 auto;
}}

.slide {{
    width: 100%;
    min-height: 100vh;
    padding: 60px 80px;
    page-break-after: always;
    background: {bg_primary};
    display: flex;
    flex-direction: column;
    justify-content: center;
}}

.slide:last-child {{
    page-break-after: avoid;
}}

.slide-headline {{
    font-size: 48px;
    font-weight: 700;
    margin-bottom: 32px;
    line-height: 1.2;
}}

.slide-body {{
    font-size: 24px;
    color: {text_secondary};
    line-height: 1.6;
}}

.slide-bullets {{
    list-style: none;
    margin-top: 32px;
}}

.slide-bullets li {{
    font-size: 20px;
    color: {text_secondary};
    margin-bottom: 16px;
    padding-left: 32px;
    position: relative;
}}

.slide-bullets li:before {{
    content: "•";
    position: absolute;
    left: 0;
    color: {accent};
    font-weight: bold;
}}

.slide-image {{
    max-width: 100%;
    height: auto;
    margin: 32px 0;
    border-radius: 8px;
}}

.slide-stat {{
    font-size: 72px;
    font-weight: 700;
    color: {accent};
    margin-bottom: 16px;
}}

.slide-stat-label {{
    font-size: 24px;
    color: {text_secondary};
}}
"""
        return css
    
    def _build_slide_html(
        self,
        slide: Dict[str, Any],
        index: int,
        design_tokens: Dict[str, Any],
    ) -> str:
        """Build HTML for a single slide."""
        headline = str(slide.get("headline", "") or "")
        body = str(slide.get("body", "") or "")
        bullets = slide.get("bullets", [])
        image_url = str(slide.get("image_url", "") or "")
        stat_blocks = slide.get("stat_blocks", [])
        
        html_parts = [f'<div class="slide">']
        
        # Headline
        if headline:
            html_parts.append(f'<h1 class="slide-headline">{html.escape(headline)}</h1>')
        
        # Stat blocks (if any)
        if stat_blocks:
            for stat in stat_blocks:
                value = stat.get("value", "")
                label = stat.get("label", "")
                html_parts.append(f'<div class="slide-stat">{html.escape(str(value))}</div>')
                html_parts.append(f'<div class="slide-stat-label">{html.escape(str(label))}</div>')
        
        # Body
        if body:
            html_parts.append(f'<div class="slide-body">{html.escape(body)}</div>')
        
        # Bullets
        if bullets:
            html_parts.append('<ul class="slide-bullets">')
            for bullet in bullets:
                html_parts.append(f'<li>{html.escape(str(bullet))}</li>')
            html_parts.append('</ul>')
        
        # Image
        if image_url:
            safe_url = html.escape(image_url, quote=True)
            html_parts.append(f'<img class="slide-image" src="{safe_url}" alt="Slide image" />')
        
        html_parts.append('</div>')
        
        return "\n".join(html_parts)
    
    def _html_to_pdf(self, html: str, options: PDFOptions) -> bytes:
        """
        Convert HTML to PDF using Playwright.
        
        Args:
            html: HTML content
            options: PDF export options
            
        Returns:
            PDF file as bytes
        """
        try:
            from playwright.async_api import async_playwright
            import asyncio
            
            async def generate_pdf():
                async with async_playwright() as p:
                    browser = await p.chromium.launch()
                    page = await browser.new_page()
                    
                    # Set HTML content
                    await page.set_content(html)
                    
                    # Generate PDF
                    pdf_bytes = await page.pdf(
                        format=options.format,
                        margin={
                            "top": options.margin_top,
                            "bottom": options.margin_bottom,
                            "left": options.margin_left,
                            "right": options.margin_right,
                        },
                        print_background=options.print_background,
                        prefer_css_page_size=options.prefer_css_page_size,
                    )
                    
                    await browser.close()
                    return pdf_bytes
            
            # Run async function in sync context
            return asyncio.run(generate_pdf())
            
        except ImportError:
            # Fallback: Use a simpler PDF generation without Playwright
            # This is a basic fallback that won't be pixel-perfect
            self.logger.warning(
                "playwright_not_available",
                message="Playwright not installed, using fallback PDF generation",
            )
            return self._fallback_pdf(html, options)
    
    def _fallback_pdf(self, html: str, options: PDFOptions) -> bytes:
        """
        Fallback PDF generation without Playwright.
        
        Emit a tiny valid PDF with an honest failure message instead of
        returning text bytes with a PDF content type. We do not call native
        fallback renderers here because missing fontconfig/Cairo libraries can
        terminate the process before Python can catch the exception.
        """
        message = "PDF export renderer unavailable. Retry after service recovery."
        stream = f"BT /F1 14 Tf 72 720 Td ({message}) Tj ET".encode("latin-1")
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]
        chunks = [b"%PDF-1.4\n"]
        offsets = [0]
        for i, obj in enumerate(objects, start=1):
            offsets.append(sum(len(c) for c in chunks))
            chunks.append(f"{i} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
        xref_offset = sum(len(c) for c in chunks)
        chunks.append(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        chunks.append(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            chunks.append(f"{offset:010d} 00000 n \n".encode("ascii"))
        chunks.append(
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
        )
        return b"".join(chunks)
