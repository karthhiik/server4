"""SWOT Analysis data models for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SWOTQuadrant(str, Enum):
    """SWOT quadrants."""

    STRENGTHS = "strengths"
    WEAKNESSES = "weaknesses"
    OPPORTUNITIES = "opportunities"
    THREATS = "threats"


class RecommendationType(str, Enum):
    """Strategic recommendation types."""

    LEVERAGE = "leverage"  # SO: Strengths + Opportunities
    DEFENSIVE = "defensive"  # ST: Strengths + Threats
    GROWTH = "growth"  # WO: Weaknesses + Opportunities
    SURVIVAL = "survival"  # WT: Weaknesses + Threats


class RecommendationPriority(str, Enum):
    """Recommendation priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SWOTItemCreate(BaseModel):
    """Request model for creating a SWOT item."""

    text: str = Field(..., min_length=1, description="Item text")
    description: Optional[str] = Field(None, description="Item description")
    importance: int = Field(default=5, ge=1, le=10, description="Importance score 1-10")


class SWOTItemUpdate(BaseModel):
    """Request model for updating a SWOT item."""

    text: Optional[str] = None
    description: Optional[str] = None
    importance: Optional[int] = Field(None, ge=1, le=10)


class SWOTItem(BaseModel):
    """Response model for a SWOT item."""

    id: str
    quadrant: str
    text: str
    description: Optional[str] = None
    importance: int = Field(ge=1, le=10)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SWOTRecommendationAction(BaseModel):
    """Action item within a recommendation."""

    action: str = Field(..., min_length=1)
    owner: Optional[str] = None
    timeline: Optional[str] = None


class SWOTRecommendation(BaseModel):
    """Response model for a strategic recommendation."""

    id: str
    type: RecommendationType
    title: str
    description: Optional[str] = None
    priority: RecommendationPriority
    actions: List[str] = Field(default_factory=list)
    created_at: datetime


class SWOTScores(BaseModel):
    """SWOT quadrant scores and metrics."""

    strengths_avg: float = Field(ge=0, le=10)
    weaknesses_avg: float = Field(ge=0, le=10)
    opportunities_avg: float = Field(ge=0, le=10)
    threats_avg: float = Field(ge=0, le=10)
    strategy_health: float = Field(ge=0, le=10, description="Overall strategy health 0-10")
    opportunity_threat_ratio: float = Field(description="O/T ratio, ideally > 1.0")
    internal_balance: float = Field(description="S/W balance")


class SWOTAnalysisCreate(BaseModel):
    """Request model for creating a SWOT analysis."""

    business_plan_id: Optional[str] = None
    title: Optional[str] = None


class SWOTAnalysisResponse(BaseModel):
    """Response model for complete SWOT analysis."""

    id: str
    business_plan_id: Optional[str] = None
    title: Optional[str] = None
    strengths: List[SWOTItem] = Field(default_factory=list)
    weaknesses: List[SWOTItem] = Field(default_factory=list)
    opportunities: List[SWOTItem] = Field(default_factory=list)
    threats: List[SWOTItem] = Field(default_factory=list)
    scores: Optional[SWOTScores] = None
    recommendations: List[SWOTRecommendation] = Field(default_factory=list)
    generated_at: datetime
    updated_at: datetime


class ExportFormat(str, Enum):
    """Export format options."""

    JSON = "json"
    MARKDOWN = "markdown"
    PDF = "pdf"
    PNG = "png"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
