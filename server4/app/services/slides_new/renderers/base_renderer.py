"""
Base Renderer - Phase 4.

Abstract base class for all renderers. Each renderer compiles
PresentationDSL into a specific output format.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class RendererType(str, Enum):
    REVEAL_JS = "reveal.js"
    REACT_3D = "react"
    HTML = "html"
    PPTX = "pptx"


@dataclass
class RenderOutput:
    """Result of a render operation."""

    renderer: RendererType
    html: str = ""
    css: str = ""
    js: str = ""
    assets: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None
    slide_count: int = 0


class BaseRenderer(ABC):
    """Abstract base for all renderers."""

    @abstractmethod
    def get_renderer_type(self) -> RendererType:
        ...

    @abstractmethod
    def render_presentation(self, presentation_dsl: Any, theme_css: str = "") -> RenderOutput:
        """Compile a full PresentationDSL into renderable output."""
        ...

    @abstractmethod
    def render_slide(self, slide_dsl: Any, theme_css: str = "") -> str:
        """Compile a single SlideDSL into an HTML fragment."""
        ...
