"""
DSL v2 Schema — Comprehensive Pydantic v2 models for the V7 Slide Generation System.

This module defines the complete Domain-Specific Language for describing
presentations in a structured, validated format that all 8 agents consume
and produce. Every field is typed, constrained, and documented.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ═══════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════

class SlideType(str, Enum):
    TITLE_SLIDE = "title-slide"
    PROBLEM_SLIDE = "problem-slide"
    SOLUTION_SLIDE = "solution-slide"
    MARKET_SLIDE = "market-slide"
    TRACTION_SLIDE = "traction-slide"
    BUSINESS_MODEL_SLIDE = "business-model-slide"
    TEAM_SLIDE = "team-slide"
    FINANCIAL_SLIDE = "financial-slide"
    COMPETITION_SLIDE = "competition-slide"
    CLOSING_SLIDE = "closing-slide"
    CUSTOM = "custom"


class LayoutType(str, Enum):
    CENTER_FOCUS = "center-focus"
    SPLIT_SCREEN = "split-screen"
    FULL_BLEED = "full-bleed"
    GRID_2X2 = "grid-2x2"
    GRID_3X1 = "grid-3x1"
    TEXT_LEFT_VISUAL_RIGHT = "text-left-visual-right"
    TEXT_RIGHT_VISUAL_LEFT = "text-right-visual-left"
    TOP_BOTTOM = "top-bottom"
    OVERLAY = "overlay"
    BULLETS = "bullets"
    COMPARISON = "comparison"
    TIMELINE = "timeline"
    KPI_DASHBOARD = "kpi-dashboard"
    QUOTE = "quote"
    TEAM_GRID = "team-grid"
    CHART = "chart"
    BLANK = "blank"


class BackgroundType(str, Enum):
    SOLID = "solid"
    GRADIENT_LINEAR = "gradient-linear"
    GRADIENT_RADIAL = "gradient-radial"
    GRADIENT_MESH = "gradient-mesh"
    GRADIENT_CONIC = "gradient-conic"
    IMAGE = "image"
    IMAGE_OVERLAY = "image-overlay"
    PATTERN = "pattern"
    NOISE = "noise"
    GLASS = "glass"


class PatternType(str, Enum):
    """CSS/SVG background patterns for decorative slide backgrounds."""
    DOTS = "dots"
    GRID = "grid"
    DIAGONAL_LINES = "diagonal-lines"
    CROSS_HATCH = "cross-hatch"
    WAVES = "waves"
    CIRCLES = "circles"
    HEXAGONS = "hexagons"
    TOPOGRAPHY = "topography"
    NONE = "none"


class ElementType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    CHART = "chart"
    SHAPE = "shape"
    ICON = "icon"
    VIDEO = "video"
    CODE = "code"
    DIAGRAM = "diagram"
    QR = "qr"
    DIVIDER = "divider"
    BADGE = "badge"
    AVATAR = "avatar"
    PROGRESS_BAR = "progress-bar"
    CARD = "card"
    DECORATIVE = "decorative"


class AnimationType(str, Enum):
    FADE_IN = "fade-in"
    SLIDE_UP = "slide-up"
    GROW = "grow"
    SHRINK = "shrink"
    STRIKE = "strike"
    HIGHLIGHT = "highlight"


class ThreeSceneType(str, Enum):
    GLOBE = "globe"
    BAR_CHART = "bar-chart"
    PARTICLES = "particles"
    SCATTER = "scatter"
    CUSTOM = "custom"


class ThemeVariant(str, Enum):
    DARK = "dark"
    LIGHT = "light"
    AUTO = "auto"


class TransitionType(str, Enum):
    NONE = "none"
    FADE = "fade"
    SLIDE = "slide"
    CONVEX = "convex"
    CONCAVE = "concave"
    ZOOM = "zoom"


class FontWeight(str, Enum):
    NORMAL = "normal"
    BOLD = "bold"
    LIGHT = "light"
    SEMIBOLD = "semibold"
    EXTRABOLD = "extrabold"


class TextAlign(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


# ═══════════════════════════════════════════════════════════════════
# GEOMETRY & STYLE PRIMITIVES
# ═══════════════════════════════════════════════════════════════════

class SlidePosition(BaseModel):
    """Normalised position (0‑1 range, percentage of slide dimensions)."""
    x: float = Field(default=0.0, ge=0.0, le=1.0, description="Horizontal position (0=left, 1=right)")
    y: float = Field(default=0.0, ge=0.0, le=1.0, description="Vertical position (0=top, 1=bottom)")


class SlideSize(BaseModel):
    """Normalised size (0‑1 range, percentage of slide dimensions)."""
    width: float = Field(default=1.0, gt=0.0, le=1.0, description="Width as fraction of slide width")
    height: float = Field(default=1.0, gt=0.0, le=1.0, description="Height as fraction of slide height")


class BackgroundStyle(BaseModel):
    """Slide background definition supporting solid, gradient, image, pattern,
    noise, glass, mesh gradient, and image-overlay fills."""
    type: BackgroundType = Field(default=BackgroundType.SOLID)
    colors: list[str] = Field(
        default_factory=lambda: ["#1a1a2e"],
        min_length=1,
        max_length=8,
        description="Hex colour values; 1 for solid, 2+ for gradients",
    )
    image_url: Optional[str] = Field(default=None, max_length=2048)
    image_prompt: Optional[str] = Field(
        default=None, max_length=1000,
        description="AI image generation prompt for background (Flux/SDXL)",
    )
    angle: Optional[float] = Field(default=None, ge=0.0, le=360.0, description="Gradient angle in degrees")
    overlay_color: Optional[str] = Field(
        default=None, max_length=30,
        description="Colour overlay on top of image backgrounds (hex with alpha, e.g. #0F172ABB)",
    )
    overlay_opacity: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Opacity of the overlay layer (0=transparent, 1=opaque)",
    )
    blur: Optional[float] = Field(
        default=None, ge=0.0, le=50.0,
        description="Background blur in px (for glass/frosted effects)",
    )
    pattern: Optional[PatternType] = Field(
        default=None,
        description="Decorative pattern overlay type",
    )
    pattern_opacity: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Opacity of pattern overlay (0.03-0.15 recommended)",
    )
    noise_intensity: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Film grain / noise texture intensity (0.02-0.08 recommended)",
    )
    mesh_points: Optional[list[dict[str, Any]]] = Field(
        default=None, max_length=6,
        description="Mesh gradient control points [{x, y, color, spread}]",
    )

    @field_validator("colors")
    @classmethod
    def validate_hex_colors(cls, v: list[str]) -> list[str]:
        import re
        hex_re = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
        for c in v:
            if not hex_re.match(c):
                raise ValueError(f"Invalid hex colour: {c}")
        return v

    @model_validator(mode="after")
    def gradient_needs_multiple_colors(self) -> "BackgroundStyle":
        if self.type in (
            BackgroundType.GRADIENT_LINEAR,
            BackgroundType.GRADIENT_RADIAL,
            BackgroundType.GRADIENT_CONIC,
        ):
            if len(self.colors) < 2:
                raise ValueError("Gradient backgrounds require at least 2 colours")
        return self


class ElementStyle(BaseModel):
    """Visual styling for individual slide elements."""
    fontSize: Optional[int] = Field(default=None, ge=6, le=200, description="Font size in px")
    fontWeight: Optional[FontWeight] = None
    color: Optional[str] = Field(default=None, max_length=20)
    fontFamily: Optional[str] = Field(default=None, max_length=100)
    textAlign: Optional[TextAlign] = None
    backgroundColor: Optional[str] = Field(default=None, max_length=20)
    borderRadius: Optional[int] = Field(default=None, ge=0, le=100)
    opacity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    padding: Optional[str] = Field(default=None, max_length=50)
    margin: Optional[str] = Field(default=None, max_length=50)
    border: Optional[str] = Field(default=None, max_length=100)
    shadow: Optional[str] = Field(default=None, max_length=200)
    lineHeight: Optional[float] = Field(default=None, ge=0.5, le=5.0)
    letterSpacing: Optional[float] = Field(default=None, ge=-5.0, le=20.0)
    textTransform: Optional[str] = Field(default=None, pattern=r"^(none|uppercase|lowercase|capitalize)$")
    zIndex: Optional[int] = Field(default=None, ge=0, le=1000)


# ═══════════════════════════════════════════════════════════════════
# SLIDE ELEMENTS
# ═══════════════════════════════════════════════════════════════════

class SlideElement(BaseModel):
    """A positioned, styled element on a slide (text box, image, chart, shape, etc.)."""
    id: str = Field(..., min_length=1, max_length=100, description="Unique element ID within the slide")
    type: ElementType = Field(...)
    content: str = Field(default="", max_length=50000, description="Text content, URL, chart JSON, or SVG markup")
    position: SlidePosition = Field(default_factory=SlidePosition)
    size: SlideSize = Field(default_factory=SlideSize)
    style: ElementStyle = Field(default_factory=ElementStyle)
    alt_text: Optional[str] = Field(default=None, max_length=500, description="Accessibility alt text for images")
    data: Optional[dict[str, Any]] = Field(default=None, description="Extra data payload (chart series, icon name, etc.)")


# ═══════════════════════════════════════════════════════════════════
# ANIMATION & REVEAL
# ═══════════════════════════════════════════════════════════════════

class FragmentAnimation(BaseModel):
    """Reveal.js fragment animation applied to a slide element."""
    elementId: str = Field(..., min_length=1, max_length=100)
    order: int = Field(..., ge=0, le=100, description="Fragment display order")
    animation: AnimationType = Field(default=AnimationType.FADE_IN)
    delay: Optional[int] = Field(default=None, ge=0, le=5000, description="Delay in ms")


class RevealConfig(BaseModel):
    """Per-slide Reveal.js configuration overrides."""
    transition: TransitionType = Field(default=TransitionType.SLIDE)
    autoAnimate: bool = Field(default=False)
    backgroundTransition: TransitionType = Field(default=TransitionType.FADE)
    verticalSlides: bool = Field(default=False)
    autoSlide: Optional[int] = Field(default=None, ge=0, le=60000, description="Auto-advance in ms")


class ThreeSceneConfig(BaseModel):
    """Three.js 3-D scene configuration for VFX slides."""
    type: ThreeSceneType = Field(default=ThreeSceneType.PARTICLES)
    data: dict[str, Any] = Field(default_factory=dict, description="Scene data (vertices, series, labels)")
    config: dict[str, Any] = Field(default_factory=dict, description="Rendering options (camera, lighting, colours)")


# ═══════════════════════════════════════════════════════════════════
# SLIDE STYLE
# ═══════════════════════════════════════════════════════════════════

class SlideStyle(BaseModel):
    """Top-level visual style for a single slide."""
    background: BackgroundStyle = Field(default_factory=BackgroundStyle)
    accentColor: Optional[str] = Field(default=None, max_length=20)
    animation: Optional[str] = Field(default=None, max_length=50)
    customCSS: Optional[str] = Field(default=None, max_length=5000)
    surfaceStyle: Optional[str] = Field(
        default=None, max_length=50,
        description="Surface effect: glass, frosted, elevated, flat, neumorphic",
    )
    borderGlow: Optional[str] = Field(
        default=None, max_length=100,
        description="CSS glow border (e.g. '0 0 20px rgba(99,102,241,0.3)')",
    )
    iconSet: Optional[str] = Field(
        default=None, max_length=50,
        description="Icon library: lucide, heroicons, phosphor, tabler",
    )


# ═══════════════════════════════════════════════════════════════════
# SLIDE CONTENT V2
# ═══════════════════════════════════════════════════════════════════

class KPIMetric(BaseModel):
    label: str = Field(..., max_length=100)
    value: str = Field(..., max_length=50)
    change: Optional[str] = Field(default=None, max_length=30)
    trend: Optional[str] = Field(default=None, pattern=r"^(up|down|flat)$")


class TeamMember(BaseModel):
    name: str = Field(..., max_length=100)
    role: str = Field(..., max_length=100)
    image_url: Optional[str] = Field(default=None, max_length=2048)
    bio: Optional[str] = Field(default=None, max_length=500)
    linkedin: Optional[str] = Field(default=None, max_length=300)


class TimelineItem(BaseModel):
    date: str = Field(..., max_length=50)
    title: str = Field(..., max_length=200)
    description: Optional[str] = Field(default=None, max_length=500)
    status: Optional[str] = Field(default=None, pattern=r"^(completed|in-progress|planned)$")


class ComparisonItem(BaseModel):
    label: str = Field(..., max_length=100)
    us: Optional[str] = Field(default=None, max_length=200)
    them: Optional[str] = Field(default=None, max_length=200)
    advantage: Optional[bool] = None


class SlideContentV2(BaseModel):
    """Structured semantic content for a slide. Agents populate relevant fields
    based on slide type; unused fields remain None."""

    # Core text
    title: str = Field(default="", max_length=200)
    subtitle: Optional[str] = Field(default=None, max_length=300)
    presenter: Optional[str] = Field(default=None, max_length=100)
    tagline: Optional[str] = Field(default=None, max_length=300)
    body_text: Optional[str] = Field(default=None, max_length=10000)
    bullets: Optional[list[str]] = Field(default=None, max_length=30)

    # Quotation
    quote_text: Optional[str] = Field(default=None, max_length=1000)
    quote_author: Optional[str] = Field(default=None, max_length=100)

    # Data
    chart_data: Optional[dict[str, Any]] = Field(default=None, description="Chart.js compatible data object")

    # Team
    team_members: Optional[list[TeamMember]] = Field(default=None, max_length=20)

    # KPI
    kpi_metrics: Optional[list[KPIMetric]] = Field(default=None, max_length=12)

    # Timeline
    timeline_items: Optional[list[TimelineItem]] = Field(default=None, max_length=20)

    # Comparison / competition
    comparison_items: Optional[list[ComparisonItem]] = Field(default=None, max_length=20)

    # Media
    image_url: Optional[str] = Field(default=None, max_length=2048)
    image_prompt: Optional[str] = Field(default=None, max_length=1000)

    # Split layout content
    left_content: Optional[str] = Field(default=None, max_length=5000)
    right_content: Optional[str] = Field(default=None, max_length=5000)

    @field_validator("title")
    @classmethod
    def title_not_empty_whitespace(cls, v: str) -> str:
        if v and not v.strip():
            return ""
        return v

    @field_validator("bullets")
    @classmethod
    def bullets_max_items(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is not None and len(v) > 30:
            raise ValueError("Maximum 30 bullet points per slide")
        return v


# ═══════════════════════════════════════════════════════════════════
# SINGLE SLIDE DSL
# ═══════════════════════════════════════════════════════════════════

class SlideDSL(BaseModel):
    """Complete DSL representation of a single slide."""

    index: int = Field(..., ge=0, description="0-based slide order")
    id: str = Field(..., min_length=1, max_length=100)
    type: SlideType = Field(default=SlideType.CUSTOM)
    layout: LayoutType = Field(default=LayoutType.CENTER_FOCUS)
    section: Optional[str] = Field(default=None, max_length=100)
    content: SlideContentV2 = Field(default_factory=SlideContentV2)
    style: SlideStyle = Field(default_factory=SlideStyle)
    elements: list[SlideElement] = Field(default_factory=list, max_length=50)
    speakerNotes: Optional[str] = Field(default=None, max_length=5000)
    fragments: list[FragmentAnimation] = Field(default_factory=list, max_length=30)
    threeScene: Optional[ThreeSceneConfig] = None
    revealConfig: RevealConfig = Field(default_factory=RevealConfig)
    customFields: dict[str, Any] = Field(default_factory=dict)

    @field_validator("elements")
    @classmethod
    def unique_element_ids(cls, v: list[SlideElement]) -> list[SlideElement]:
        ids = [e.id for e in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate element IDs within a slide")
        return v

    @model_validator(mode="after")
    def fragment_refs_valid(self) -> "SlideDSL":
        element_ids = {e.id for e in self.elements}
        for frag in self.fragments:
            if frag.elementId not in element_ids:
                raise ValueError(
                    f"Fragment references unknown element '{frag.elementId}'"
                )
        return self


# ═══════════════════════════════════════════════════════════════════
# THEME DSL
# ═══════════════════════════════════════════════════════════════════

class ThemeDSL(BaseModel):
    """Presentation-level theme definition."""
    id: str = Field(default="default", min_length=1, max_length=100)
    variant: ThemeVariant = Field(default=ThemeVariant.DARK)
    preset: Optional[str] = Field(default=None, max_length=100, description="Built-in preset name")
    customOverrides: dict[str, Any] = Field(
        default_factory=dict,
        description="CSS variable overrides (--primary-color, --font-heading, etc.)",
    )


# ═══════════════════════════════════════════════════════════════════
# PRESENTATION-LEVEL METADATA
# ═══════════════════════════════════════════════════════════════════

class PresentationDimensions(BaseModel):
    width: int = Field(default=1920, ge=640, le=7680)
    height: int = Field(default=1080, ge=360, le=4320)


class PresentationMetadata(BaseModel):
    author: Optional[str] = Field(default=None, max_length=200)
    company: Optional[str] = Field(default=None, max_length=200)
    date: Optional[str] = Field(default=None, max_length=30)
    version: int = Field(default=1, ge=1)
    tags: list[str] = Field(default_factory=list, max_length=20)
    language: str = Field(default="en", max_length=10)


class GenerationMetadataV2(BaseModel):
    """Tracks agent work, model usage, and quality metrics for a generation session."""
    skillVersions: dict[str, int] = Field(
        default_factory=dict,
        description="Agent skill versions, e.g. {'ceo': 3, 'designer': 2}",
    )
    qualityScore: int = Field(default=0, ge=0, le=100)
    iterations: int = Field(default=1, ge=1)
    modelUsage: dict[str, str] = Field(
        default_factory=dict,
        description="Model used per agent, e.g. {'ceo': 'kimi-k2', 'designer': 'gpt-4o-mini'}",
    )
    totalCost: str = Field(default="$0.00", max_length=20)
    generationTime: str = Field(default="0s", max_length=20)
    startedAt: Optional[datetime] = None
    completedAt: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════
# PRESENTATION CORE
# ═══════════════════════════════════════════════════════════════════

class PresentationCore(BaseModel):
    """Top-level presentation identity and configuration (not slides)."""
    id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    archetype: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Narrative archetype: problem-solution, hero-journey, before-after, data-story, etc.",
    )
    theme: ThemeDSL = Field(default_factory=ThemeDSL)
    aspectRatio: str = Field(default="16:9", pattern=r"^\d{1,2}:\d{1,2}$")
    dimensions: PresentationDimensions = Field(default_factory=PresentationDimensions)
    renderers: list[str] = Field(
        default_factory=lambda: ["reveal.js"],
        description="Target renderers: reveal.js, react, html, pptx",
    )
    modes: list[str] = Field(
        default_factory=lambda: ["present", "edit"],
        description="Supported modes: present, edit, print, embed",
    )
    metadata: PresentationMetadata = Field(default_factory=PresentationMetadata)


# ═══════════════════════════════════════════════════════════════════
# ROOT PRESENTATION DSL
# ═══════════════════════════════════════════════════════════════════

class PresentationDSL(BaseModel):
    """Root document: the complete, validated DSL for a presentation.

    This is the single source of truth that gets:
    - Generated by the agent pipeline
    - Stored in MongoDB
    - Sent to renderers (Reveal.js / React / PPTX)
    - Returned via the API
    """

    version: str = Field(default="2.0", pattern=r"^\d+\.\d+$")
    presentation: PresentationCore = Field(...)
    slides: list[SlideDSL] = Field(..., min_length=1, max_length=200)
    generationMetadata: GenerationMetadataV2 = Field(default_factory=GenerationMetadataV2)

    @field_validator("slides")
    @classmethod
    def validate_slide_indexes(cls, v: list[SlideDSL]) -> list[SlideDSL]:
        indexes = [s.index for s in v]
        if sorted(indexes) != list(range(len(v))):
            raise ValueError("Slide indexes must be contiguous starting from 0")
        return v

    @field_validator("slides")
    @classmethod
    def unique_slide_ids(cls, v: list[SlideDSL]) -> list[SlideDSL]:
        ids = [s.id for s in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate slide IDs in presentation")
        return v

    def to_mongo_doc(self) -> dict[str, Any]:
        """Serialise to a MongoDB-friendly dict."""
        return self.model_dump(mode="json")

    @classmethod
    def from_mongo_doc(cls, doc: dict[str, Any]) -> "PresentationDSL":
        """Deserialise from a MongoDB document."""
        return cls.model_validate(doc)
