"""Theme models — both built-in and generatively created."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ThemeType(str, Enum):
    BUILTIN = "builtin"
    GENERATED = "generated"
    CUSTOM = "custom"


class ThemeColors(BaseModel):
    primary: str = "#2563EB"
    secondary: str = "#1E40AF"
    accent: str = "#3B82F6"
    background: str = "#FFFFFF"
    surface: str = "#F8FAFC"
    text: str = "#0F172A"
    text_secondary: str = "#475569"
    muted: str = "#94A3B8"
    chart_colors: list[str] = Field(default=[
        "#2563EB", "#7C3AED", "#EC4899", "#F97316", "#10B981", "#06B6D4", "#EAB308", "#EF4444",
    ])


class ThemeFonts(BaseModel):
    heading: str = "Inter"
    body: str = "Inter"
    code: Optional[str] = "JetBrains Mono"


class ThemeInDB(BaseModel):
    id: str = Field(alias="_id")
    name: str
    type: ThemeType
    colors: ThemeColors
    fonts: ThemeFonts
    user_id: Optional[str] = None  # For custom themes
    generated_from: Optional[dict] = None  # Brand input that generated this
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class ThemeResponse(BaseModel):
    id: str
    name: str
    type: ThemeType
    colors: ThemeColors
    fonts: ThemeFonts


class ThemeGenerateRequest(BaseModel):
    """Generate a new theme from brand colors."""
    brand_colors: list[str] = Field(..., min_length=1, max_length=5)
    brand_vibe: str = "corporate"  # corporate | playful | minimal | bold | tech
    font_preference: str = "modern"  # modern | classic | playful | technical
