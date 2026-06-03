"""
Pydantic v2 models for Barise server4 presentation backend.

All models are fully typed, production-ready, and follow Pydantic v2 syntax.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator
import uuid


# ============================================================================
# Design System Models
# ============================================================================


class PaletteTokens(BaseModel):
    """16-color palette for design system."""

    primary: str = Field(..., description="Primary brand color (usually vibrant)")
    secondary: str = Field(..., description="Secondary brand color")
    accent: str = Field(..., description="Accent color for highlights")
    background: str = Field(..., description="Page background color")
    surface: str = Field(..., description="Card/component surface color")
    surface_alt: str = Field(
        ..., description="Alternative surface (must be 8% lighter than surface)"
    )
    text_primary: str = Field(..., description="Primary text color")
    text_secondary: str = Field(..., description="Secondary text color")
    text_muted: str = Field(..., description="Muted/disabled text color")
    border: str = Field(..., description="Border color")
    gradient_start: str = Field(..., description="Gradient start color")
    gradient_end: str = Field(..., description="Gradient end color")
    success: str = Field(..., description="Success state color")
    warning: str = Field(..., description="Warning state color")
    danger: str = Field(..., description="Danger/error state color")
    chart: str = Field(..., description="Chart/data visualization color")

    @field_validator("primary", "secondary", "accent", "background", "surface",
                      "surface_alt", "text_primary", "text_secondary", "text_muted",
                      "border", "gradient_start", "gradient_end", "success",
                      "warning", "danger", "chart")
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        """Validate that color is valid hex format."""
        if not isinstance(v, str):
            raise ValueError("Color must be a string")
        if not (v.startswith("#") and len(v) in (7, 9)):
            raise ValueError(f"Invalid hex color: {v}")
        return v


class FontTokens(BaseModel):
    """Font families for typography system."""

    heading: str = Field(..., description="Font family for headings")
    body: str = Field(..., description="Font family for body text")
    display: str = Field(..., description="Font family for display text")
    mono: str = Field(..., description="Font family for monospace/code")


class TypeScale(BaseModel):
    """Type scale sizes in pixels."""

    display: int = Field(default=72, description="Display size (72px)")
    h1: int = Field(default=56, description="H1 size (56px)")
    h2: int = Field(default=48, description="H2 size (48px)")
    h3: int = Field(default=36, description="H3 size (36px)")
    body: int = Field(default=18, description="Body size (18px)")
    caption: int = Field(default=14, description="Caption size (14px)")


class ResolvedDesignTokens(BaseModel):
    """Resolved design tokens ready for rendering."""

    palette: PaletteTokens
    fonts: FontTokens
    type_scale: TypeScale = Field(default_factory=TypeScale)
    density: Literal["compact", "comfortable", "spacious"] = "comfortable"
    radius: int = Field(default=12, description="Border radius in pixels")


# ============================================================================
# Content Block Models (BodyBlock Union)
# ============================================================================


class MetricBlock(BaseModel):
    """Single metric display block."""

    type: Literal["metric"] = "metric"
    value: str = Field(..., description="Metric value")
    label: str = Field(..., description="Metric label")
    delta: Optional[str] = Field(default=None, description="Change amount")
    delta_direction: Optional[Literal["up", "down", "neutral"]] = Field(
        default=None, description="Direction of change"
    )


class TextBlock(BaseModel):
    """Text content block."""

    type: Literal["text"] = "text"
    headline: Optional[str] = Field(default=None, description="Optional headline")
    text: str = Field(..., description="Body text content")


class QuoteBlock(BaseModel):
    """Quote/testimonial block."""

    type: Literal["quote"] = "quote"
    quote: str = Field(..., description="Quote text")
    attribution: str = Field(..., description="Who said the quote")
    role: Optional[str] = Field(default=None, description="Role/title of person")


class ChartBlock(BaseModel):
    """Chart/data visualization block."""

    type: Literal["chart"] = "chart"
    chart_type: Literal["bar", "line", "pie", "area", "scatter"] = Field(
        ..., description="Type of chart"
    )
    data: List[Dict[str, Any]] = Field(..., description="Chart data points")
    x_key: str = Field(..., description="Key for x-axis values")
    y_key: str = Field(..., description="Key for y-axis values")


class MediaBlock(BaseModel):
    """Media (image/video) block."""

    type: Literal["media"] = "media"
    url: str = Field(..., description="URL to media asset")
    alt: str = Field(..., description="Alt text for accessibility")
    caption: Optional[str] = Field(default=None, description="Optional caption")


# Union type for any body block
BodyBlock = Union[MetricBlock, TextBlock, QuoteBlock, ChartBlock, MediaBlock]


# ============================================================================
# Flow/Process Models
# ============================================================================


class FlowNode(BaseModel):
    """Node in a process flow diagram."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str = Field(..., description="Node label")
    description: Optional[str] = Field(default=None, description="Detailed description")
    status: Literal["input", "process", "output", "decision"] = Field(
        default="process", description="Node type/status"
    )


# ============================================================================
# Slide Models
# ============================================================================


class SlideContent(BaseModel):
    """Content structure for a slide."""

    headline: Optional[str] = Field(default=None, description="Main headline")
    subhead: Optional[str] = Field(default=None, description="Subheading")
    body_blocks: Optional[List[BodyBlock]] = Field(
        default=None, description="Content blocks"
    )
    nodes: Optional[List[FlowNode]] = Field(
        default=None, description="Flow nodes (for process_flow layout)"
    )
    meta: Optional[Dict[str, Any]] = Field(
        default=None, description="Arbitrary metadata"
    )

    class Config:
        use_enum_values = False


class CompiledSlide(BaseModel):
    """A compiled, ready-to-render slide."""

    slide_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    slide_no: int = Field(..., description="Slide number in deck")
    layout_type: Literal[
        "hero",
        "stat_hero",
        "split",
        "bento",
        "feature_grid",
        "process_flow",
        "timeline",
        "comparison",
        "quote",
        "metrics",
        "chart",
        "media_first",
    ] = Field(..., description="Layout template type (NOT kit_jsx)")
    intent: str = Field(..., description="Slide intent (e.g., 'cover', 'problem')")
    content: SlideContent = Field(..., description="Slide content")
    design_tokens: Optional[ResolvedDesignTokens] = Field(
        default=None, description="Design tokens for this slide (optional override)"
    )
    version: int = Field(default=1, description="Schema version")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Presentation Models
# ============================================================================


class Presentation(BaseModel):
    """A complete presentation/deck."""

    deck_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., description="Deck title")
    user_id: str = Field(..., description="Owner user ID")
    design_tokens: ResolvedDesignTokens = Field(..., description="Deck-wide design tokens")
    slides: List[CompiledSlide] = Field(
        default_factory=list, description="Compiled slides"
    )
    status: Literal["draft", "published", "archived"] = Field(
        default="draft", description="Deck status"
    )
    mode: Literal["edit", "present", "view"] = Field(
        default="edit", description="Current mode"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# API Request/Response Models
# ============================================================================


class CreateDeckRequest(BaseModel):
    """Request to create a new deck."""

    title: str = Field(..., description="Deck title")
    user_id: str = Field(..., description="Owner user ID")
    brief: Optional[str] = Field(default=None, description="Creative brief")
    mode: Literal["edit", "present", "view"] = Field(default="edit")
    slide_count: Optional[int] = Field(default=5, description="Initial slide count")
    theme_id: Optional[str] = Field(default=None, description="Theme template ID")
    visual_direction: Optional[str] = Field(
        default=None, description="Visual direction name"
    )
    brand_kit: Optional[Dict[str, Any]] = Field(default=None, description="Brand guidelines")


class DeckResponse(BaseModel):
    """Response after deck creation."""

    success: bool
    deck_id: str
    message: str
    slides: Optional[List[CompiledSlide]] = None


class SlidePatchRequest(BaseModel):
    """Request to update a slide."""

    content: Optional[SlideContent] = None
    layout_type: Optional[str] = None
    design_tokens: Optional[ResolvedDesignTokens] = None


class ExportRequest(BaseModel):
    """Request to export a deck."""

    deck_id: str
    format: Literal["pdf", "pptx", "html"] = "pdf"
    include_watermark: bool = Field(default=True)


# ============================================================================
# Investor Intelligence Models
# ============================================================================


class InvestorProfile(BaseModel):
    """Investor profile for matching."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Investor name")
    firm: str = Field(..., description="Firm name")
    stage_focus: List[str] = Field(
        default_factory=list, description="Stages (seed, series-a, etc)"
    )
    sector_focus: List[str] = Field(
        default_factory=list, description="Sectors of interest"
    )
    check_size_min: Optional[float] = Field(default=None, description="Minimum check size")
    check_size_max: Optional[float] = Field(default=None, description="Maximum check size")
    recent_investments: List[Dict[str, Any]] = Field(
        default_factory=list, description="Recent investments"
    )
    warm_intro_paths: List[Dict[str, Any]] = Field(
        default_factory=list, description="People who can introduce"
    )
    thesis_keywords: List[str] = Field(
        default_factory=list, description="Keywords describing thesis"
    )


class LiveMetric(BaseModel):
    """Live metric reference in a deck."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: Literal[
        "stripe_mrr",
        "stripe_arr",
        "user_count",
        "engagement_rate",
        "churn_rate",
        "nps",
        "custom",
    ] = Field(..., description="Metric source")
    value: Union[str, int, float] = Field(..., description="Current metric value")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    deck_id: str = Field(..., description="Associated deck ID")


# ============================================================================
# Validation and Export Models
# ============================================================================


class ValidationResult(BaseModel):
    """Result of content validation."""

    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ExportMetadata(BaseModel):
    """Metadata for exported files."""

    format: str
    deck_id: str
    deck_title: str
    created_at: datetime
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    total_slides: int
    includes_watermark: bool
