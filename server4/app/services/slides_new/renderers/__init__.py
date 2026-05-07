"""
Renderer package - Phase 4 + Phase 6 + Phase 7.

Compiles Slide DSL v2 into renderable output formats.
Renderers:
- RevealCompiler: reveal.js HTML presentations (Phase 4)
- ReactCompiler: React + Three.js components (Phase 6)
- PptxCompiler: Native PowerPoint .pptx files (Phase 7)
- HtmlCompiler: Zero-dep interactive HTML (Phase 7)
- RenderRouter: Multi-format rendering orchestrator (Phase 7)
"""

from app.services.slides_new.renderers.base_renderer import (
    BaseRenderer,
    RenderOutput,
    RendererType,
)
from app.services.slides_new.renderers.reveal_compiler import RevealCompiler
from app.services.slides_new.renderers.react_compiler import ReactCompiler
from app.services.slides_new.renderers.performance_guardrails import (
    PerformanceGuardrails,
    QualityLevel,
)
from app.services.slides_new.renderers.pptx_compiler import PptxCompiler
from app.services.slides_new.renderers.html_compiler import HtmlCompiler
from app.services.slides_new.renderers.render_router import (
    RenderRouter,
    ExportFormat,
    ExportJob,
    ExportJobStatus,
    ContentCapabilities,
)

__all__ = [
    "BaseRenderer",
    "RenderOutput",
    "RendererType",
    "RevealCompiler",
    "ReactCompiler",
    "PerformanceGuardrails",
    "QualityLevel",
    "PptxCompiler",
    "HtmlCompiler",
    "RenderRouter",
    "ExportFormat",
    "ExportJob",
    "ExportJobStatus",
    "ContentCapabilities",
]
