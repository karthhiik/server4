"""Pitch Deck Canvas data models for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SlideType(str, Enum):
    """Slide type enumeration."""

    EXECUTIVE_SUMMARY = "executive_summary"
    PRODUCT_DEMO = "product_demo"
    MARKET = "market"
    BUSINESS_MODEL = "business_model"
    FINANCIALS = "financials"
    TEAM = "team"
    TRACTION = "traction"
    ASK = "ask"


class DeckStatus(str, Enum):
    """Pitch deck status enumeration."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ExecutiveSummaryContent(BaseModel):
    """Content for executive summary slide."""

    company_name: str
    tagline: str
    description: str
    vision: Optional[str] = None
    problem: Optional[str] = None
    solution: Optional[str] = None


class ProductDemoContent(BaseModel):
    """Content for product demo slide."""

    product_name: str
    description: str
    features: Optional[list[str]] = None
    unique_value: Optional[str] = None
    differentiators: Optional[list[str]] = None
    image_url: Optional[str] = None


class MarketContent(BaseModel):
    """Content for market opportunity slide."""

    tam: Optional[float] = None  # Total Addressable Market
    sam: Optional[float] = None  # Serviceable Addressable Market
    som: Optional[float] = None  # Serviceable Obtainable Market
    competitors: Optional[list[str]] = None
    positioning: Optional[str] = None
    target_segment: Optional[str] = None


class UnitEconomics(BaseModel):
    """Unit economics data."""

    ltv: Optional[float] = None  # Lifetime Value
    cac: Optional[float] = None  # Customer Acquisition Cost
    payback_period_months: Optional[int] = None


class BusinessModelContent(BaseModel):
    """Content for business model slide."""

    revenue_streams: Optional[list[str]] = None
    pricing_model: Optional[str] = None
    unit_economics: Optional[UnitEconomics] = None
    revenue_breakdown: Optional[dict[str, float]] = None


class FinancialsContent(BaseModel):
    """Content for financials slide."""

    revenue_2024: Optional[float] = None
    revenue_2025: Optional[float] = None
    revenue_2026: Optional[float] = None
    growth_rate: Optional[float] = None
    mrr: Optional[float] = None  # Monthly Recurring Revenue
    arr: Optional[float] = None  # Annual Recurring Revenue
    valuation: Optional[float] = None


class TeamMember(BaseModel):
    """Team member information."""

    name: str
    title: str
    bio: Optional[str] = None
    image_url: Optional[str] = None


class TeamContent(BaseModel):
    """Content for team slide."""

    team_members: Optional[list[TeamMember]] = None
    advisors: Optional[list[str]] = None


class Metric(BaseModel):
    """Metric data point."""

    label: str
    value: Any


class Milestone(BaseModel):
    """Milestone data point."""

    date: str
    milestone: str


class TractionContent(BaseModel):
    """Content for traction slide."""

    metrics: Optional[list[Metric]] = None
    timeline: Optional[list[Milestone]] = None


class AskContent(BaseModel):
    """Content for ask/funding slide."""

    funding_amount: Optional[float] = None
    use_of_funds: Optional[dict[str, float]] = None
    timeline: Optional[str] = None


class SlideContent(BaseModel):
    """Flexible slide content model that accepts any slide type content."""

    pass


class Slide(BaseModel):
    """Pitch deck slide model."""

    id: str
    order: int
    type: SlideType
    title: str
    content: dict[str, Any]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    speaker_notes: Optional[str] = None


class PitchDeckMetrics(BaseModel):
    """Analytics metrics for pitch deck."""

    total_views: int = 0
    unique_viewers: int = 0
    average_session_time: int = 0  # in seconds
    last_viewed: Optional[datetime] = None
    shares_count: int = 0


class PitchDeck(BaseModel):
    """Complete pitch deck model."""

    id: str
    business_plan_id: str
    title: str
    subtitle: Optional[str] = None
    status: DeckStatus = DeckStatus.DRAFT
    theme: Optional[str] = "modern_blue"
    slides: list[Slide] = []
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    metrics: Optional[PitchDeckMetrics] = None
    user_id: Optional[str] = None


class PitchDeckCreate(BaseModel):
    """Request model for creating a new pitch deck."""

    business_plan_id: str = Field(..., description="Associated business plan ID")
    title: str = Field(..., description="Pitch deck title")
    subtitle: Optional[str] = None


class PitchDeckUpdate(BaseModel):
    """Request model for updating a pitch deck."""

    title: Optional[str] = None
    subtitle: Optional[str] = None
    status: Optional[DeckStatus] = None
    theme: Optional[str] = None


class SlideCreate(BaseModel):
    """Request model for creating a slide."""

    order: int
    type: SlideType
    title: str
    content: dict[str, Any]
    speaker_notes: Optional[str] = None


class SlideUpdate(BaseModel):
    """Request model for updating a slide."""

    order: Optional[int] = None
    title: Optional[str] = None
    content: Optional[dict[str, Any]] = None
    speaker_notes: Optional[str] = None


class DeckShare(BaseModel):
    """Share configuration for pitch deck."""

    deck_id: str
    recipients: list[str]


class ExportRequest(BaseModel):
    """Export configuration request."""

    format: str = Field(..., description="Export format (pdf or pptx)")
    include_speaker_notes: bool = False
    include_animations: bool = False


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = "ok"
    service: str = "pitch-deck-service"
    version: str = "1.0.0"
