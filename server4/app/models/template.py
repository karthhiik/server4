"""Template models — presentation templates stored in MongoDB."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TemplatePlaceholder(BaseModel):
    key: str
    label: str
    type: str = "text"  # text | image | data | auto
    default_value: Optional[str] = None
    ai_instructions: Optional[str] = None


class TemplateSlideDefinition(BaseModel):
    index: int
    layout: str
    purpose: str
    placeholders: dict[str, str]
    ai_instructions: Optional[str] = None


class TemplateInDB(BaseModel):
    id: str = Field(alias="_id")
    name: str
    category: str  # fundraising | sales | internal | marketing | education | corporate | business
    description: str
    thumbnail_url: Optional[str] = None
    slide_count: int
    mode_available: list[str] = Field(default=["standard", "premium"])
    slides: list[TemplateSlideDefinition]
    default_theme: str = "corporate-blue"
    usage_count: int = 0
    avg_rating: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class TemplateResponse(BaseModel):
    id: str
    name: str
    category: str
    description: str
    thumbnail_url: Optional[str] = None
    slide_count: int
    mode_available: list[str]
    default_theme: str
    usage_count: int
    avg_rating: Optional[float] = None


class TemplateAnalyticsInDB(BaseModel):
    template_id: str
    total_uses: int = 0
    completion_rate: float = 0.0
    avg_time_to_export: Optional[float] = None
    most_edited_slides: list[int] = Field(default_factory=list)
    layout_changes: dict[str, Any] = Field(default_factory=dict)
    theme_switches: dict[str, int] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
