"""GTM (Go-To-Market) Analysis data models for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MarketSegmentCreate(BaseModel):
    """Request model for creating a market segment."""

    name: str = Field(..., min_length=1, description="Segment name")
    description: Optional[str] = Field(None, description="Segment description")
    tam: float = Field(..., gt=0, description="Total Addressable Market in USD")
    sam: float = Field(..., gt=0, description="Serviceable Addressable Market in USD")
    som: float = Field(..., gt=0, description="Serviceable Obtainable Market in USD")
    market_size_growth: Optional[float] = Field(None, ge=0, description="Annual growth rate")
    customer_count: Optional[int] = Field(None, ge=0, description="Target customer count")


class MarketSegmentUpdate(BaseModel):
    """Request model for updating a market segment."""

    name: Optional[str] = None
    description: Optional[str] = None
    tam: Optional[float] = Field(None, gt=0)
    sam: Optional[float] = Field(None, gt=0)
    som: Optional[float] = Field(None, gt=0)
    market_size_growth: Optional[float] = Field(None, ge=0)
    customer_count: Optional[int] = Field(None, ge=0)


class MarketSegment(BaseModel):
    """Response model for a market segment."""

    id: str
    name: str
    description: Optional[str] = None
    tam: float = Field(gt=0)
    sam: float = Field(gt=0)
    som: float = Field(gt=0)
    market_size_growth: Optional[float] = None
    customer_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class SalesChannelCreate(BaseModel):
    """Request model for creating a sales channel."""

    name: str = Field(..., min_length=1, description="Channel name")
    description: Optional[str] = Field(None, description="Channel description")
    effectiveness_score: int = Field(..., ge=1, le=10, description="Effectiveness 1-10")
    estimated_cost_per_deal: float = Field(..., gt=0, description="Cost per deal in USD")
    estimated_sales_cycle: int = Field(..., gt=0, description="Sales cycle in days")


class SalesChannelUpdate(BaseModel):
    """Request model for updating a sales channel."""

    name: Optional[str] = None
    description: Optional[str] = None
    effectiveness_score: Optional[int] = Field(None, ge=1, le=10)
    estimated_cost_per_deal: Optional[float] = Field(None, gt=0)
    estimated_sales_cycle: Optional[int] = Field(None, gt=0)


class SalesChannel(BaseModel):
    """Response model for a sales channel."""

    id: str
    name: str
    description: Optional[str] = None
    effectiveness_score: int = Field(ge=1, le=10)
    estimated_cost_per_deal: float = Field(gt=0)
    estimated_sales_cycle: int = Field(gt=0)
    revenue_contribution: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class PricingStrategyCreate(BaseModel):
    """Request model for pricing strategy."""

    model: str = Field(..., description="Pricing model (value-based, cost-plus, etc)")
    base_price: float = Field(..., gt=0, description="Base price in USD")
    price_range: Optional[Dict[str, float]] = Field(None, description="Min and max prices")
    discount_strategy: Optional[str] = None


class PricingStrategy(BaseModel):
    """Response model for pricing strategy."""

    id: str
    model: str
    base_price: float = Field(gt=0)
    price_range: Optional[Dict[str, float]] = None
    discount_strategy: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ExecutionMilestone(BaseModel):
    """Execution plan milestone."""

    id: str
    quarter: str = Field(..., description="Quarter (e.g., Q1 2025)")
    milestones: List[str] = Field(default_factory=list, description="Milestone descriptions")
    resources: Optional[Dict[str, int]] = None
    status: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ExecutionPlanCreate(BaseModel):
    """Request model for execution plan."""

    timeline: List[Dict[str, Any]] = Field(default_factory=list)


class UnitEconomics(BaseModel):
    """Unit economics metrics."""

    gross_margin: float = Field(ge=0, le=1)
    payback_period_months: int = Field(gt=0)
    retention_rate: float = Field(ge=0, le=1)
    net_dollar_retention: Optional[float] = None


class GTMMetrics(BaseModel):
    """GTM success metrics."""

    cac: float = Field(..., gt=0, description="Customer Acquisition Cost")
    ltv: float = Field(..., gt=0, description="Lifetime Value")
    conversion_rate: float = Field(..., ge=0, le=1, description="Conversion rate 0-1")
    annual_target_revenue: Optional[float] = Field(None, gt=0)
    unit_economics: Optional[UnitEconomics] = None
    sales_marketing_spend: Optional[float] = None
    new_customers_acquired: Optional[int] = None
    prospects: Optional[int] = None
    qualified_deals: Optional[int] = None
    closed_deals: Optional[int] = None


class GTMAnalysisCreate(BaseModel):
    """Request model for creating GTM analysis."""

    business_plan_id: str = Field(..., description="Business plan ID")
    positioning_statement: Optional[str] = None
    competitive_differentiation: Optional[str] = None


class GTMAnalysisResponse(BaseModel):
    """Response model for complete GTM analysis."""

    id: str
    business_plan_id: str
    target_markets: List[MarketSegment] = Field(default_factory=list)
    sales_channels: List[SalesChannel] = Field(default_factory=list)
    pricing_strategy: Optional[PricingStrategy] = None
    positioning_statement: Optional[str] = None
    competitive_differentiation: Optional[str] = None
    execution_timeline: List[ExecutionMilestone] = Field(default_factory=list)
    success_metrics: Optional[GTMMetrics] = None
    created_at: datetime
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
