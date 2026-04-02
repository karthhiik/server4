"""Presentation models — root collection documents."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PresentationMode(str, Enum):
    STANDARD = "standard"
    PREMIUM = "premium"


class GenerationState(str, Enum):
    IDLE = "idle"
    RESEARCHING = "researching"
    OUTLINING = "outlining"
    GENERATING_CONTENT = "generating_content"
    FILLING_TEMPLATE = "filling_template"
    DESIGNING = "designing"
    RENDERING_PREVIEW = "rendering_preview"
    READY_FOR_EDITING = "ready_for_editing"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"


class CreatedFrom(str, Enum):
    AI = "ai"
    TEMPLATE = "template"


class PresentationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    mode: PresentationMode = PresentationMode.STANDARD
    created_from: CreatedFrom = CreatedFrom.AI
    template_id: Optional[str] = None
    theme_id: Optional[str] = None


class PresentationUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    theme_id: Optional[str] = None


class PresentationInDB(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    title: str
    description: Optional[str] = None
    mode: PresentationMode
    created_from: CreatedFrom = CreatedFrom.AI
    template_id: Optional[str] = None
    theme_id: Optional[str] = None
    slide_count: int = 0
    thumbnail_url: Optional[str] = None
    generation_state: GenerationState = GenerationState.IDLE
    generation_progress: int = 0
    generation_message: str = ""
    generation_error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class PresentationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str] = None
    mode: PresentationMode
    created_from: CreatedFrom
    template_id: Optional[str] = None
    theme_id: Optional[str] = None
    slide_count: int
    thumbnail_url: Optional[str] = None
    generation_state: GenerationState
    generation_progress: int
    generation_message: str
    created_at: datetime
    updated_at: datetime


class GenerationInput(BaseModel):
    """Input for AI slide generation."""
    topic: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1, max_length=5000)
    audience: str = Field(..., min_length=1, max_length=200)
    purpose: str = Field(default="pitch")  # pitch | sales | educational | report | internal | fundraising | demo_day | investor_update
    slide_count: int = Field(default=10, ge=3, le=50)
    language: str = Field(default="English")
    additional_notes: Optional[str] = Field(default=None, max_length=3000)
    mode: PresentationMode = PresentationMode.STANDARD
    writing_style: str = Field(default="yc_pitch")  # yc_pitch | narrative | descriptive | persuasive | analytical | conversational | executive | technical | academic | minimalist | storytelling | investor_update
    theme_id: Optional[str] = None
    generate_images: bool = False
    generate_notes: bool = False


class TemplateGenerationInput(BaseModel):
    """Input for template-based generation."""
    template_id: str
    mode: PresentationMode = PresentationMode.STANDARD
    user_inputs: dict = Field(default_factory=dict)
    theme_id: Optional[str] = None
