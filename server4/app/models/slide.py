"""Slide models — one document per slide in slides collection."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SlideLayout(str, Enum):
    TITLE_HERO = "title-hero"
    TWO_COLUMN = "two-column"
    BULLETS = "bullets"
    BULLETS_WITH_IMAGE = "bullets-with-image"
    FULL_IMAGE = "full-image"
    CHART = "chart"
    COMPARISON = "comparison"
    TIMELINE = "timeline"
    QUOTE = "quote"
    TEAM_GRID = "team-grid"
    KPI_DASHBOARD = "kpi-dashboard"
    BLANK = "blank"


class SlideContent(BaseModel):
    title: str = ""
    subtitle: Optional[str] = None
    body_text: Optional[str] = None
    bullets: Optional[list[str]] = None
    left_content: Optional[str] = None
    right_content: Optional[str] = None
    left_label: Optional[str] = None
    right_label: Optional[str] = None
    left_items: Optional[list[str]] = None
    right_items: Optional[list[str]] = None
    quote_text: Optional[str] = None
    quote_author: Optional[str] = None
    quote_role: Optional[str] = None
    image_url: Optional[str] = None
    image_prompt: Optional[str] = None
    chart_data: Optional[dict[str, Any]] = None
    chart_type: Optional[str] = None
    events: Optional[list[dict[str, str]]] = None  # For timeline
    members: Optional[list[dict[str, str]]] = None  # For team grid
    metrics: Optional[list[dict[str, Any]]] = None  # For KPI dashboard
    speaker_notes: Optional[str] = None
    background_style: Optional[str] = None
    citation_map: Optional[dict[str, str]] = None  # Citation markers [1], [2] mapped to sources


class SlideInDB(BaseModel):
    id: str = Field(alias="_id")
    presentation_id: str
    index: int
    layout: SlideLayout
    content: SlideContent
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class SlideResponse(BaseModel):
    id: str
    presentation_id: str
    index: int
    layout: SlideLayout
    content: SlideContent
    version: int
    created_at: datetime
    updated_at: datetime


class SlideUpdate(BaseModel):
    """Update slide content (text, notes, image, chart)."""
    content: Optional[SlideContent] = None


class SlideLayoutChange(BaseModel):
    """Change slide layout."""
    layout: SlideLayout


class SlideReorder(BaseModel):
    """Reorder slides."""
    slide_ids: list[str]  # Ordered list of slide IDs in new order


class SlideVersionInDB(BaseModel):
    id: str = Field(alias="_id")
    slide_id: str
    version: int
    layout: SlideLayout
    content: SlideContent
    change_type: str  # edit | layout_change | ai_rewrite | ai_expand | ai_summarize | ai_translate
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class AISlideAction(BaseModel):
    """Request body for AI-assisted slide editing."""
    instruction: Optional[str] = None  # For rewrite
    target_language: Optional[str] = None  # For translate
    writing_style: Optional[str] = None  # For style-rewrite (yc_pitch, narrative, etc.)
