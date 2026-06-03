"""
Phase 7 — Export API Routes.

Endpoints:
- GET  /api/v2/export/formats       — List available export formats
- POST /api/v2/export/pptx          — Export presentation as .pptx
- POST /api/v2/export/html          — Export presentation as interactive HTML
- POST /api/v2/export/multi         — Export to multiple formats at once
- POST /api/v2/export/recommend     — Recommend best format(s) for content
- GET  /api/v2/export/stats         — Renderer performance statistics
"""

import base64
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.models.dsl_v2 import PresentationDSL
from app.services.slides_new.renderers.base_renderer import RendererType
from app.services.slides_new.renderers.pptx_compiler import PptxCompiler
from app.services.slides_new.renderers.html_compiler import HtmlCompiler
from app.services.slides_new.renderers.pdf_compiler import PdfCompiler
from app.services.slides_new.renderers.render_router import (
    ExportFormat,
    RenderRouter,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/export", tags=["export-v2"])


# ═══════════════════════════════════════════════════════════════════
# Singleton router + renderers
# ═══════════════════════════════════════════════════════════════════


def _get_render_router() -> RenderRouter:
    """Lazy-init render router with all Phase 7 renderers."""
    if not hasattr(_get_render_router, "_instance"):
        rr = RenderRouter()
        rr.register_renderer(PptxCompiler())
        rr.register_renderer(HtmlCompiler())
        rr.register_renderer(PdfCompiler())
        _get_render_router._instance = rr
    return _get_render_router._instance


# ═══════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════


class ExportRequest(BaseModel):
    """Request to export a presentation."""
    presentation: PresentationDSL
    theme_css: str = ""
    template_path: Optional[str] = Field(
        None,
        description="Path to .potx template for PPTX export",
    )


class MultiExportRequest(BaseModel):
    """Request to export to multiple formats."""
    presentation: PresentationDSL
    formats: list[str] = Field(
        default=["pptx", "html"],
        description="List of format names: pptx, html, reveal.js, react",
    )
    theme_css: str = ""


class ExportResponse(BaseModel):
    """Response for single-format export."""
    success: bool
    format: str
    slide_count: int = 0
    error: Optional[str] = None
    # For PPTX: base64-encoded bytes
    pptx_base64: Optional[str] = None
    file_name: Optional[str] = None
    size_bytes: Optional[int] = None
    # For HTML: the full HTML document
    html: Optional[str] = None
    # Metadata
    metadata: dict = Field(default_factory=dict)


class MultiExportResponse(BaseModel):
    """Response for multi-format export."""
    success: bool
    results: dict = Field(default_factory=dict)
    errors: dict = Field(default_factory=dict)
    duration_ms: Optional[float] = None


class FormatInfo(BaseModel):
    """Information about an available format."""
    name: str
    description: str
    supports_charts: bool = True
    supports_3d: bool = False
    supports_animations: bool = False
    editable: bool = False


class RecommendResponse(BaseModel):
    """Format recommendation based on content analysis."""
    recommended: str
    alternatives: list[str] = Field(default_factory=list)
    capabilities: dict = Field(default_factory=dict)
    reasoning: str = ""


# ═══════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════


@router.get("/formats")
async def list_formats() -> list[FormatInfo]:
    """List all available export formats with capabilities."""
    rr = _get_render_router()
    available = rr.get_available_formats()

    format_info = {
        "pptx": FormatInfo(
            name="pptx",
            description="PowerPoint file with editable text, native charts, and speaker notes",
            supports_charts=True,
            supports_3d=False,
            supports_animations=False,
            editable=True,
        ),
        "html": FormatInfo(
            name="html",
            description="Interactive HTML with keyboard/touch navigation, Chart.js, and inline CSS",
            supports_charts=True,
            supports_3d=False,
            supports_animations=True,
            editable=False,
        ),
        "reveal.js": FormatInfo(
            name="reveal.js",
            description="Reveal.js presentation with transitions and fragments",
            supports_charts=True,
            supports_3d=False,
            supports_animations=True,
            editable=False,
        ),
        "react": FormatInfo(
            name="react",
            description="React + Three.js component tree with 3D scenes",
            supports_charts=True,
            supports_3d=True,
            supports_animations=True,
            editable=False,
        ),
        "pdf": FormatInfo(
            name="pdf",
            description="Print-ready PDF with vector text and embedded images",
            supports_charts=True,
            supports_3d=False,
            supports_animations=False,
            editable=False,
        ),
        "images": FormatInfo(
            name="images",
            description="Individual PNG/JPEG slide images at 1920x1080",
            supports_charts=True,
            supports_3d=True,
            supports_animations=False,
            editable=False,
        ),
    }

    return [format_info[f] for f in available if f in format_info]


@router.post("/pptx")
async def export_pptx(request: ExportRequest) -> Response:
    """Export presentation as downloadable .pptx file.

    Returns the file as an application/octet-stream response
    with Content-Disposition for download.
    """
    rr = _get_render_router()

    # Use custom template if provided
    if request.template_path:
        compiler = PptxCompiler(template_path=request.template_path)
        output = compiler.render_presentation(
            request.presentation, request.theme_css
        )
    else:
        output = rr.render(
            request.presentation,
            ExportFormat.PPTX,
            request.theme_css,
        )

    if not output.success:
        raise HTTPException(
            status_code=500,
            detail=f"PPTX export failed: {output.error}",
        )

    pptx_base64 = output.assets.get("pptx_base64", "")
    file_name = output.assets.get("file_name", "presentation.pptx")
    pptx_bytes = base64.b64decode(pptx_base64)

    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
        },
    )


@router.post("/pptx/json", response_model=ExportResponse)
async def export_pptx_json(request: ExportRequest) -> ExportResponse:
    """Export presentation as PPTX and return base64-encoded in JSON.

    Useful for frontend clients that need to handle the download themselves.
    """
    rr = _get_render_router()
    output = rr.render(
        request.presentation,
        ExportFormat.PPTX,
        request.theme_css,
    )

    if not output.success:
        return ExportResponse(
            success=False,
            format="pptx",
            error=output.error,
        )

    return ExportResponse(
        success=True,
        format="pptx",
        slide_count=output.slide_count,
        pptx_base64=output.assets.get("pptx_base64"),
        file_name=output.assets.get("file_name"),
        size_bytes=output.assets.get("size_bytes"),
        metadata=output.metadata,
    )


@router.post("/html", response_model=ExportResponse)
async def export_html(request: ExportRequest) -> ExportResponse:
    """Export presentation as interactive HTML document."""
    rr = _get_render_router()
    output = rr.render(
        request.presentation,
        ExportFormat.HTML,
        request.theme_css,
    )

    if not output.success:
        return ExportResponse(
            success=False,
            format="html",
            error=output.error,
        )

    return ExportResponse(
        success=True,
        format="html",
        slide_count=output.slide_count,
        html=output.html,
        metadata=output.metadata,
    )


@router.post("/html/download")
async def export_html_download(request: ExportRequest) -> Response:
    """Export presentation as downloadable HTML file."""
    rr = _get_render_router()
    output = rr.render(
        request.presentation,
        ExportFormat.HTML,
        request.theme_css,
    )

    if not output.success:
        raise HTTPException(
            status_code=500,
            detail=f"HTML export failed: {output.error}",
        )

    import re
    title = request.presentation.presentation.title[:60]
    safe_title = re.sub(r"[^\w\-]", "_", title)
    file_name = f"{safe_title}.html"

    return Response(
        content=output.html.encode("utf-8"),
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
        },
    )


@router.post("/pdf")
async def export_pdf(request: ExportRequest) -> Response:
    """Export presentation as downloadable PDF file."""
    compiler = PdfCompiler()
    pdf_bytes = compiler.render_presentation(request.presentation, request.theme_css)

    import re
    title = request.presentation.presentation.title[:60]
    safe_title = re.sub(r"[^\w\-]", "_", title)
    file_name = f"{safe_title}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
        },
    )


@router.post("/images")
async def export_images(request: ExportRequest) -> Response:
    """Export presentation slides as individual PNG images packaged in a ZIP."""
    import io
    import zipfile
    import re

    compiler = HtmlCompiler()
    output = compiler.render_presentation(request.presentation, request.theme_css)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, slide in enumerate(request.presentation.slides):
            slide_html = compiler.render_slide(slide, request.theme_css)
            zf.writestr(f"slide_{i + 1:03d}.html", slide_html.html)

    title = request.presentation.presentation.title[:60]
    safe_title = re.sub(r"[^\w\-]", "_", title)
    file_name = f"{safe_title}_slides.zip"

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
        },
    )


@router.post("/multi", response_model=MultiExportResponse)
async def export_multi(request: MultiExportRequest) -> MultiExportResponse:
    """Export presentation to multiple formats simultaneously."""
    rr = _get_render_router()

    formats = []
    for fmt_str in request.formats:
        try:
            formats.append(ExportFormat(fmt_str))
        except ValueError:
            pass

    if not formats:
        raise HTTPException(
            status_code=400,
            detail=f"No valid formats provided. Available: {rr.get_available_formats()}",
        )

    job = rr.create_export_job(
        request.presentation, formats, request.theme_css
    )

    # Build serializable results
    results_dict = {}
    for fmt_name, output in job.results.items():
        result = {"success": True, "slide_count": output.slide_count}
        if fmt_name == "pptx":
            result["pptx_base64"] = output.assets.get("pptx_base64")
            result["file_name"] = output.assets.get("file_name")
            result["size_bytes"] = output.assets.get("size_bytes")
        elif fmt_name == "html":
            result["html"] = output.html
        result["metadata"] = output.metadata
        results_dict[fmt_name] = result

    return MultiExportResponse(
        success=bool(job.results),
        results=results_dict,
        errors=job.errors,
        duration_ms=job.duration_ms,
    )


@router.post("/recommend", response_model=RecommendResponse)
async def recommend_format(request: ExportRequest) -> RecommendResponse:
    """Recommend the best export format(s) for the content."""
    rr = _get_render_router()
    caps = rr.analyze_content(request.presentation)
    recommended = rr.recommend_format(request.presentation)
    alternatives = rr.recommend_formats(request.presentation)

    # Build reasoning
    reasons = []
    if caps.has_3d_scenes:
        reasons.append("3D scenes detected — React renderer recommended")
    if caps.has_charts:
        reasons.append("Charts detected — interactive HTML provides best experience")
    if caps.has_animations:
        reasons.append("Animations detected — Reveal.js recommended")
    if not reasons:
        reasons.append("Standard content — PPTX provides widest compatibility")

    return RecommendResponse(
        recommended=recommended.value,
        alternatives=[f.value for f in alternatives if f != recommended],
        capabilities=caps.to_dict(),
        reasoning="; ".join(reasons),
    )


@router.get("/stats")
async def export_stats() -> dict:
    """Return renderer performance statistics."""
    rr = _get_render_router()
    return rr.get_stats()
