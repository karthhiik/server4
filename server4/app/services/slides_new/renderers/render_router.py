"""
Render Router — Phase 7.

Intelligent multi-format rendering router that selects and orchestrates
renderers based on DSL content, user preferences, and slide capabilities.

Features:
    - Format selection based on user preference + DSL content analysis
    - Multi-format parallel rendering (PPTX + HTML + Reveal.js)
    - Capability detection (charts, 3D scenes, animations)
    - Renderer health tracking
    - Export job management with status tracking
"""

import time
import uuid
from enum import Enum
from typing import Optional

import structlog

from app.models.dsl_v2 import PresentationDSL, LayoutType
from app.services.slides_new.renderers.base_renderer import (
    BaseRenderer,
    RenderOutput,
    RendererType,
)

logger = structlog.get_logger()


class ExportFormat(str, Enum):
    """Supported export formats."""
    PPTX = "pptx"
    HTML = "html"
    REVEAL_JS = "reveal.js"
    REACT_3D = "react"
    ALL = "all"


class ExportJobStatus(str, Enum):
    """Export job lifecycle states."""
    PENDING = "pending"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportJob:
    """Tracks the lifecycle of an export rendering job."""

    def __init__(self, job_id: str, formats: list[ExportFormat]):
        self.job_id = job_id
        self.formats = formats
        self.status = ExportJobStatus.PENDING
        self.results: dict[str, RenderOutput] = {}
        self.errors: dict[str, str] = {}
        self.created_at = time.time()
        self.completed_at: Optional[float] = None
        self.duration_ms: Optional[float] = None

    def to_dict(self) -> dict:
        """Serialize job state for API responses."""
        return {
            "job_id": self.job_id,
            "formats": [f.value for f in self.formats],
            "status": self.status.value,
            "completed_formats": list(self.results.keys()),
            "failed_formats": self.errors,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
        }


class ContentCapabilities:
    """Analyzes PresentationDSL to determine content capabilities."""

    def __init__(self, dsl: PresentationDSL):
        self.has_charts = any(s.content.chart_data for s in dsl.slides)
        self.has_3d_scenes = any(s.threeScene for s in dsl.slides)
        self.has_animations = any(
            s.revealConfig and s.revealConfig.transition
            and s.revealConfig.transition.value != "none"
            for s in dsl.slides
        )
        self.has_speaker_notes = any(s.speakerNotes for s in dsl.slides)
        self.has_rich_media = any(
            s.content.image_url or s.content.image_prompt
            for s in dsl.slides
        )
        self.slide_count = len(dsl.slides)

        # Layout complexity
        complex_layouts = {
            LayoutType.CHART, LayoutType.KPI_DASHBOARD,
            LayoutType.COMPARISON, LayoutType.TIMELINE,
            LayoutType.TEAM_GRID,
        }
        self.has_complex_layouts = any(
            s.layout in complex_layouts for s in dsl.slides
        )

    def to_dict(self) -> dict:
        return {
            "has_charts": self.has_charts,
            "has_3d_scenes": self.has_3d_scenes,
            "has_animations": self.has_animations,
            "has_speaker_notes": self.has_speaker_notes,
            "has_rich_media": self.has_rich_media,
            "has_complex_layouts": self.has_complex_layouts,
            "slide_count": self.slide_count,
        }


class RenderRouter:
    """Routes rendering requests to appropriate renderer(s).

    Manages renderer instances and selects the best renderer(s) based
    on DSL content analysis and user preferences.

    Usage::

        router = RenderRouter()
        router.register_renderer(PptxCompiler())
        router.register_renderer(HtmlCompiler())

        # Single format
        output = router.render(dsl, ExportFormat.PPTX)

        # Multi-format
        outputs = router.render_all(dsl, [ExportFormat.PPTX, ExportFormat.HTML])

        # Auto-select best format
        fmt = router.recommend_format(dsl)
    """

    def __init__(self):
        self._renderers: dict[RendererType, BaseRenderer] = {}
        self._render_stats: dict[str, dict] = {}

    def register_renderer(self, renderer: BaseRenderer) -> None:
        """Register a renderer instance."""
        rtype = renderer.get_renderer_type()
        self._renderers[rtype] = renderer
        self._render_stats[rtype.value] = {
            "total_renders": 0,
            "total_failures": 0,
            "avg_duration_ms": 0,
        }
        logger.info("renderer_registered", type=rtype.value)

    def get_available_formats(self) -> list[str]:
        """Return list of available export format names."""
        return [rt.value for rt in self._renderers]

    def get_renderer(self, renderer_type: RendererType) -> Optional[BaseRenderer]:
        """Get a registered renderer by type."""
        return self._renderers.get(renderer_type)

    def analyze_content(self, dsl: PresentationDSL) -> ContentCapabilities:
        """Analyze DSL content to determine capabilities."""
        return ContentCapabilities(dsl)

    def recommend_format(self, dsl: PresentationDSL) -> ExportFormat:
        """Recommend the best export format based on content.

        Heuristics:
        - 3D scenes → react (or HTML fallback)
        - Charts + complex layouts → HTML (interactive)
        - Standard content → PPTX (most portable)
        - Animations → Reveal.js
        """
        caps = self.analyze_content(dsl)

        if caps.has_3d_scenes and RendererType.REACT_3D in self._renderers:
            return ExportFormat.REACT_3D
        if caps.has_animations and RendererType.REVEAL_JS in self._renderers:
            return ExportFormat.REVEAL_JS
        if caps.has_charts and RendererType.HTML in self._renderers:
            return ExportFormat.HTML
        if RendererType.PPTX in self._renderers:
            return ExportFormat.PPTX
        if RendererType.HTML in self._renderers:
            return ExportFormat.HTML

        available = list(self._renderers.keys())
        if available:
            return ExportFormat(available[0].value)
        return ExportFormat.HTML

    def recommend_formats(self, dsl: PresentationDSL) -> list[ExportFormat]:
        """Recommend multiple complementary export formats.

        Returns formats ordered by priority. Typically returns 2 formats:
        a primary (most feature-rich) and a portable fallback.
        """
        caps = self.analyze_content(dsl)
        formats: list[ExportFormat] = []

        # Primary format
        primary = self.recommend_format(dsl)
        formats.append(primary)

        # Add complementary format
        if primary != ExportFormat.PPTX and RendererType.PPTX in self._renderers:
            formats.append(ExportFormat.PPTX)
        elif primary != ExportFormat.HTML and RendererType.HTML in self._renderers:
            formats.append(ExportFormat.HTML)

        return formats

    def _format_to_renderer_type(self, fmt: ExportFormat) -> Optional[RendererType]:
        """Map export format to renderer type."""
        mapping = {
            ExportFormat.PPTX: RendererType.PPTX,
            ExportFormat.HTML: RendererType.HTML,
            ExportFormat.REVEAL_JS: RendererType.REVEAL_JS,
            ExportFormat.REACT_3D: RendererType.REACT_3D,
        }
        return mapping.get(fmt)

    def render(
        self,
        dsl: PresentationDSL,
        fmt: ExportFormat,
        theme_css: str = "",
    ) -> RenderOutput:
        """Render presentation to a single format.

        Args:
            dsl: The presentation DSL to render.
            fmt: Desired export format.
            theme_css: Optional additional CSS.

        Returns:
            RenderOutput with rendering result.
        """
        renderer_type = self._format_to_renderer_type(fmt)
        if renderer_type is None or renderer_type not in self._renderers:
            return RenderOutput(
                renderer=renderer_type or RendererType.HTML,
                success=False,
                error=f"Renderer '{fmt.value}' not available. "
                       f"Available: {self.get_available_formats()}",
            )

        renderer = self._renderers[renderer_type]
        start = time.monotonic()

        try:
            output = renderer.render_presentation(dsl, theme_css)

            # Update stats
            duration = (time.monotonic() - start) * 1000
            stats = self._render_stats[renderer_type.value]
            stats["total_renders"] += 1
            if not output.success:
                stats["total_failures"] += 1
            prev_avg = stats["avg_duration_ms"]
            n = stats["total_renders"]
            stats["avg_duration_ms"] = prev_avg + (duration - prev_avg) / n

            logger.info(
                "render_complete",
                format=fmt.value,
                success=output.success,
                duration_ms=round(duration, 1),
            )

            return output

        except Exception as exc:
            self._render_stats[renderer_type.value]["total_failures"] += 1
            logger.exception("render_failed", format=fmt.value, error=str(exc))
            return RenderOutput(
                renderer=renderer_type,
                success=False,
                error=str(exc),
            )

    def render_all(
        self,
        dsl: PresentationDSL,
        formats: Optional[list[ExportFormat]] = None,
        theme_css: str = "",
    ) -> dict[str, RenderOutput]:
        """Render presentation to multiple formats.

        Args:
            dsl: The presentation DSL to render.
            formats: List of formats. If None, renders all registered.
            theme_css: Optional additional CSS.

        Returns:
            Dict mapping format name → RenderOutput.
        """
        if formats is None:
            formats = [ExportFormat(rt.value) for rt in self._renderers]

        results: dict[str, RenderOutput] = {}
        for fmt in formats:
            if fmt == ExportFormat.ALL:
                for rt in self._renderers:
                    results[rt.value] = self.render(
                        dsl, ExportFormat(rt.value), theme_css
                    )
            else:
                results[fmt.value] = self.render(dsl, fmt, theme_css)

        return results

    def create_export_job(
        self,
        dsl: PresentationDSL,
        formats: list[ExportFormat],
        theme_css: str = "",
    ) -> ExportJob:
        """Create and execute an export job (synchronous).

        For background processing, wrap this in a Celery task.
        """
        job_id = str(uuid.uuid4())
        job = ExportJob(job_id, formats)
        job.status = ExportJobStatus.RENDERING

        start = time.monotonic()

        for fmt in formats:
            if fmt == ExportFormat.ALL:
                for rt in self._renderers:
                    output = self.render(dsl, ExportFormat(rt.value), theme_css)
                    if output.success:
                        job.results[rt.value] = output
                    else:
                        job.errors[rt.value] = output.error or "Unknown error"
            else:
                output = self.render(dsl, fmt, theme_css)
                if output.success:
                    job.results[fmt.value] = output
                else:
                    job.errors[fmt.value] = output.error or "Unknown error"

        duration = (time.monotonic() - start) * 1000
        job.duration_ms = round(duration, 1)
        job.completed_at = time.time()

        if job.errors and not job.results:
            job.status = ExportJobStatus.FAILED
        else:
            job.status = ExportJobStatus.COMPLETED

        logger.info(
            "export_job_complete",
            job_id=job_id,
            formats=[f.value for f in formats],
            completed=list(job.results.keys()),
            failed=list(job.errors.keys()),
            duration_ms=job.duration_ms,
        )

        return job

    def get_stats(self) -> dict:
        """Return renderer statistics."""
        return {
            "renderers": self._render_stats,
            "available_formats": self.get_available_formats(),
        }
