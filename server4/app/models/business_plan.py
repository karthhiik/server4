"""Business Plan data models for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class BusinessPlanStatus(str, Enum):
    """Business plan status enumeration."""

    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ExportFormat(str, Enum):
    """Export format enumeration."""

    PDF = "pdf"
    CSV = "csv"


class SectionUpdate(BaseModel):
    """Request model for updating a plan section."""

    content: str = Field(..., min_length=1, description="Section content")
    metadata: Optional[dict] = Field(None, description="Section metadata")


class BusinessPlanCreate(BaseModel):
    """Request model for creating a new business plan."""

    company_name: str = Field(..., min_length=1, description="Company name")
    industry: str = Field(..., min_length=1, description="Industry")
    business_type: str = Field(..., min_length=1, description="Business type")
    description: str = Field(..., min_length=1, description="Business description")
    target_market: Optional[str] = None
    current_stage: Optional[str] = None
    team_size: Optional[str] = None


class BusinessPlanUpdate(BaseModel):
    """Request model for updating an existing business plan."""

    company_name: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    status: Optional[BusinessPlanStatus] = None


class SectionResponse(BaseModel):
    """Response model for a business plan section."""

    name: str
    content: str
    created_at: datetime
    updated_at: datetime
    metadata: Optional[dict] = None


class VersionResponse(BaseModel):
    """Response model for a business plan version."""

    version_id: str
    version_number: int
    created_at: datetime
    created_by: Optional[str] = None
    status: str
    summary: Optional[str] = None


class CitationResponse(BaseModel):
    """Response model for citations."""

    source: str
    title: str
    url: Optional[str] = None
    date_accessed: Optional[datetime] = None


class BusinessPlanResponse(BaseModel):
    """Response model for a business plan."""

    id: str
    company_name: str
    industry: str
    business_type: str
    description: str
    status: BusinessPlanStatus = BusinessPlanStatus.DRAFT
    created_at: datetime
    updated_at: datetime
    user_id: Optional[str] = None
    sections: Optional[dict] = {}
    versions: Optional[list[VersionResponse]] = []
    citations: Optional[list[CitationResponse]] = []


class BusinessPlanListResponse(BaseModel):
    """Response model for listing business plans."""

    items: list[BusinessPlanResponse]
    total: int
    skip: int
    limit: int


class CitationCreate(BaseModel):
    """Request model for adding citations."""

    source: str = Field(..., min_length=1, description="Citation source")
    title: str = Field(..., min_length=1, description="Citation title")
    url: Optional[str] = None
    date_accessed: Optional[datetime] = None


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = "ok"
    service: str = "business-plan-service"
    version: str = "1.0.0"
