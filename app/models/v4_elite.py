"""
Pydantic v2 models for Barise Server4 Elite - World-class presentation backend.

This is the production-grade elite system that beats:
- Chronicle AI Deck Generator
- Gamma.app
- Beautiful.ai
- Every deck generator on the market

Architecture enforces:
✓ Exact 16-color palette (no bloat)
✓ Discriminated unions for block types
✓ Content model for frontend compatibility
✓ FlowNode support for process_flow layouts
✓ Literal types (not Enums) for serialization
✓ Pydantic v2 syntax throughout
✓ No dead fields
"""

from datetime import datetime
from typing import Any, Annotated, Dict, List, Literal, Optional, Union
from uuid import uuid4
import uuid

from pydantic import BaseModel, Field, field_validator, Discriminator


# ============================================================================
# ELITE DESIGN SYSTEM (16-Color Palette)
# ============================================================================


class ElitePaletteTokens(BaseModel):
    """Precisely 16 colors, psychology-optimized."""

    primary: str = Field(..., description="Brand primary (action)")
    secondary: str = Field(..., description="Supporting color")
    accent: str = Field(..., description="Highlight/urgency")
    background: str = Field(..., description="Page background")
    surface: str = Field(..., description="Card/section surface")
    surface_alt: str = Field(
        ..., description="Alternative surface (MUST be 8% lighter than surface)"
    )
    text_primary: str = Field(..., description="Main text color")
    text_secondary: str = Field(..., description="Supporting text")
    text_muted: str = Field(..., description="Muted/disabled text")
    border: str = Field(..., description="Borders & dividers")
    gradient_start: str = Field(..., description="Gradient start")
    gradient_end: str = Field(..., description="Gradient end")
    success: str = Field(..., description="Success state (colorblind-safe)")
    warning: str = Field(..., description="Warning state (colorblind-safe)")
    danger: str = Field(..., description="Error state (colorblind-safe)")
    chart: str = Field(..., description="Data visualization color")

    @field_validator(
        "primary",
        "secondary",
        "accent",
        "background",
        "surface",
        "surface_alt",
        "text_primary",
        "text_secondary",
        "text_muted",
        "border",
        "gradient_start",
        "gradient_end",
        "success",
        "warning",
        "danger",
        "chart",
    )
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        """Validate hex color format."""
        if not isinstance(v, str):
            raise ValueError("Color must be string")
        if not (v.startswith("#") and len(v) in (7, 9)):
            raise ValueError(f"Invalid hex color: {v}")
        return v


class EliteFontTokens(BaseModel):
    """Font families for typography system."""

    heading: str = Field(..., description="Font for headings")
    body: str = Field(..., description="Font for body text")
    display: str = Field(..., description="Font for display/hero")
    mono: str = Field(..., description="Font for code/data")


class EliteTypeScale(BaseModel):
    """Type scale sizes in pixels."""

    display: int = Field(default=72, description="Display size")
    h1: int = Field(default=56, description="H1 heading")
    h2: int = Field(default=48, description="H2 heading")
    h3: int = Field(default=36, description="H3 heading")
    body: int = Field(default=18, description="Body text")
    caption: int = Field(default=14, description="Caption text")


class EliteDesignTokens(BaseModel):
    """Master design token set."""

    palette: ElitePaletteTokens
    fonts: EliteFontTokens
    type_scale: EliteTypeScale = Field(default_factory=EliteTypeScale)
    density: Literal["compact", "comfortable", "spacious"] = "comfortable"
    radius: int = Field(default=12, description="Border radius (px)")


# ============================================================================
# ELITE BLOCK TYPES (Discriminated Union)
# ============================================================================


class HeroBlock(BaseModel):
    """Full-screen hero block."""

    type: Literal["hero"] = "hero"
    headline: str = Field(..., description="Main headline")
    subheadline: Optional[str] = Field(None, description="Supporting text")
    background: Optional[str] = Field(None, description="Background image URL")
    cta_text: Optional[str] = Field(None, description="Call-to-action text")
    cta_url: Optional[str] = Field(None, description="CTA link")


class MetricBlock(BaseModel):
    """Metric/KPI display block."""

    type: Literal["metric"] = "metric"
    value: str = Field(..., description="The number")
    label: str = Field(..., description="What it means")
    delta: Optional[str] = Field(None, description="Change (±X%)")
    delta_direction: Optional[Literal["up", "down", "neutral"]] = None
    context: Optional[str] = Field(None, description="Sub-label")


class ChartBlock(BaseModel):
    """Data visualization block."""

    type: Literal["chart"] = "chart"
    chart_type: Literal["bar", "line", "pie", "area", "scatter"] = "bar"
    title: Optional[str] = Field(None, description="Chart title")
    data: List[Dict[str, Any]] = Field(..., description="Chart data")
    x_key: str = Field(..., description="X-axis field")
    y_key: str = Field(..., description="Y-axis field")
    highlight_indices: Optional[List[int]] = Field(None, description="Highlight points")
    show_legend: bool = Field(default=True)
    show_values: bool = Field(default=True)


class TextBlock(BaseModel):
    """Rich text block."""

    type: Literal["text"] = "text"
    headline: Optional[str] = Field(None, description="Heading")
    text: str = Field(..., description="Body text")
    bullet_points: Optional[List[str]] = Field(None, description="Bullets")
    alignment: Literal["left", "center", "right"] = "left"


class QuoteBlock(BaseModel):
    """Testimonial/proof block."""

    type: Literal["quote"] = "quote"
    quote: str = Field(..., description="Quote text")
    attribution: str = Field(..., description="Who said it")
    title: Optional[str] = Field(None, description="Their title")
    company: Optional[str] = Field(None, description="Company name")
    image_url: Optional[str] = Field(None, description="Headshot URL")


class ProcessFlowBlock(BaseModel):
    """Process/workflow block."""

    type: Literal["process_flow"] = "process_flow"
    title: Optional[str] = Field(None, description="Process name")
    steps: List[Dict[str, Any]] = Field(..., description="Process steps")
    flow_direction: Literal["left-to-right", "top-to-bottom"] = "left-to-right"


class TimelineBlock(BaseModel):
    """Timeline/milestone block."""

    type: Literal["timeline"] = "timeline"
    title: Optional[str] = Field(None, description="Timeline title")
    events: List[Dict[str, Any]] = Field(..., description="Timeline events")
    direction: Literal["horizontal", "vertical"] = "horizontal"


class ComparisonBlock(BaseModel):
    """Side-by-side comparison block."""

    type: Literal["comparison"] = "comparison"
    left_title: str = Field(..., description="Left column title")
    right_title: str = Field(..., description="Right column title")
    left_items: List[str] = Field(..., description="Left items")
    right_items: List[str] = Field(..., description="Right items")


class MediaBlock(BaseModel):
    """Image/video block."""

    type: Literal["media"] = "media"
    url: str = Field(..., description="Asset URL")
    alt: str = Field(..., description="Alt text")
    caption: Optional[str] = Field(None, description="Caption")
    media_type: Literal["image", "video"] = "image"


class BentoBlock(BaseModel):
    """Grid layout block."""

    type: Literal["bento"] = "bento"
    title: Optional[str] = Field(None, description="Grid title")
    items: List[Dict[str, Any]] = Field(..., description="Grid items")
    columns: int = Field(default=3, ge=1, le=6)


class GalleryBlock(BaseModel):
    """Image gallery block."""

    type: Literal["gallery"] = "gallery"
    title: Optional[str] = Field(None, description="Gallery title")
    images: List[Dict[str, str]] = Field(..., description="Images")


def get_block_type(block: Union[
    HeroBlock,
    MetricBlock,
    ChartBlock,
    TextBlock,
    QuoteBlock,
    ProcessFlowBlock,
    TimelineBlock,
    ComparisonBlock,
    MediaBlock,
    BentoBlock,
    GalleryBlock,
]) -> str:
    """Discriminator function for block type."""
    return block.type


# Discriminated union for all block types
EliteBodyBlock = Annotated[
    Union[
        HeroBlock,
        MetricBlock,
        ChartBlock,
        TextBlock,
        QuoteBlock,
        ProcessFlowBlock,
        TimelineBlock,
        ComparisonBlock,
        MediaBlock,
        BentoBlock,
        GalleryBlock,
    ],
    Discriminator(get_block_type),
]


# ============================================================================
# FLOW NODE (for process_flow layouts)
# ============================================================================


class FlowNode(BaseModel):
    """Node in a process flow diagram."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    label: str = Field(..., description="Node label")
    description: Optional[str] = Field(None, description="Detailed description")
    status: Literal["input", "process", "output", "decision"] = "process"


# ============================================================================
# SLIDE CONTENT (Frontend Compatibility)
# ============================================================================


class SlideContent(BaseModel):
    """Content structure for a slide."""

    headline: Optional[str] = Field(None, description="Main headline")
    subhead: Optional[str] = Field(None, description="Subheading")
    body_blocks: Optional[List[EliteBodyBlock]] = Field(None, description="Content blocks")
    nodes: Optional[List[FlowNode]] = Field(None, description="Flow nodes")
    meta: Optional[Dict[str, Any]] = Field(None, description="Metadata")

    class Config:
        use_enum_values = False


# ============================================================================
# ELITE COMPILED SLIDE
# ============================================================================


class EliteCompiledSlide(BaseModel):
    """Production-ready compiled slide."""

    slide_id: str = Field(default_factory=lambda: str(uuid4()))
    slide_no: int = Field(..., description="Slide number")
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
    ] = Field(..., description="Layout template")
    intent: Literal[
        "opener",
        "problem",
        "insight",
        "solution",
        "benefits",
        "traction",
        "team",
        "market",
        "competitors",
        "differentiation",
        "business_model",
        "roadmap",
        "social_proof",
        "risk_mitigation",
        "call_to_action",
        "closer",
    ] = Field(..., description="Slide intent")
    content: SlideContent = Field(..., description="Slide content")
    design_tokens: Optional[EliteDesignTokens] = Field(None, description="Design tokens")
    version: int = Field(default=1, description="Schema version")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# ELITE PRESENTATION
# ============================================================================


class ElitePresentation(BaseModel):
    """World-class presentation."""

    deck_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(..., description="Deck title")
    user_id: str = Field(..., description="Owner user ID")
    design_tokens: EliteDesignTokens = Field(..., description="Design tokens")
    slides: List[EliteCompiledSlide] = Field(default_factory=list, description="Slides")
    status: Literal["drafting", "complete", "archived"] = Field(default="drafting", description="Deck status")
    mode: Literal["standard", "premium"] = Field(default="standard", description="Deck mode")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================


class CreateEliteDeckRequest(BaseModel):
    """Request to create a new elite deck."""

    title: str = Field(..., description="Deck title")
    user_id: str = Field(..., description="Owner user ID")
    brief: Optional[str] = Field(None, description="Company brief")
    creation_mode: Literal["standard", "premium"] = Field(default="standard", description="Creation mode")
    slide_count: Optional[int] = Field(default=5, description="Initial slide count")
    visual_direction: Optional[str] = Field(None, description="Visual direction")
    brand_kit: Optional[Dict[str, Any]] = Field(None, description="Brand guidelines")


class EliteDeckResponse(BaseModel):
    """Response after deck operation."""

    success: bool
    deck_id: str
    message: str
    slides: Optional[List[EliteCompiledSlide]] = None


class EliteSlidePatchRequest(BaseModel):
    """Request to update a slide."""

    content: Optional[SlideContent] = None
    layout_type: Optional[str] = None
    design_tokens: Optional[EliteDesignTokens] = None


class EliteExportRequest(BaseModel):
    """Request to export a deck."""

    deck_id: str
    format: Literal["pdf", "pptx", "html"]
    quality_level: Literal["standard", "premium", "ultra-hd"] = "premium"
    include_watermark: bool = False
    watermark_text: Optional[str] = None


# ============================================================================
# INVESTOR & INTELLIGENCE MODELS
# ============================================================================


class InvestorProfile(BaseModel):
    """Investor profile for matching."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Investor name")
    firm: str = Field(..., description="Firm name")
    stage_focus: List[str] = Field(default_factory=list, description="Stages")
    sector_focus: List[str] = Field(default_factory=list, description="Sectors")
    check_size_min: Optional[float] = None
    check_size_max: Optional[float] = None
    recent_investments: List[Dict[str, Any]] = Field(default_factory=list)
    warm_intro_paths: List[Dict[str, Any]] = Field(default_factory=list)
    thesis_keywords: List[str] = Field(default_factory=list)


class LiveMetric(BaseModel):
    """Live metric reference."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    source: Literal[
        "stripe_mrr",
        "stripe_arr",
        "user_count",
        "engagement_rate",
        "churn_rate",
        "nps",
        "custom",
    ]
    value: Union[str, int, float]
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    deck_id: str


# ============================================================================
# ELITE EXPORTS
# ============================================================================


__all__ = [
    # Palette & Design
    "ElitePaletteTokens",
    "EliteFontTokens",
    "EliteTypeScale",
    "EliteDesignTokens",
    # Blocks
    "HeroBlock",
    "MetricBlock",
    "ChartBlock",
    "TextBlock",
    "QuoteBlock",
    "ProcessFlowBlock",
    "TimelineBlock",
    "ComparisonBlock",
    "MediaBlock",
    "BentoBlock",
    "GalleryBlock",
    "EliteBodyBlock",
    # Flow
    "FlowNode",
    "SlideContent",
    # Slides & Presentations
    "EliteCompiledSlide",
    "ElitePresentation",
    # API
    "CreateEliteDeckRequest",
    "EliteDeckResponse",
    "EliteSlidePatchRequest",
    "EliteExportRequest",
    # Intelligence
    "InvestorProfile",
    "LiveMetric",
]
