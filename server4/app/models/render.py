"""Render / export models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ExportFormat(str, Enum):
    PPTX = "pptx"
    PDF = "pdf"
    HTML = "html"
    PNG = "png"


class ExportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportRequest(BaseModel):
    format: ExportFormat
    include_notes: bool = False
    quality: str = "standard"  # standard | print (PDF only)
    # Slice 1 (Trust Honesty): premium owners may force an export when the
    # production quality gate has flagged blocker issues. The export router
    # is responsible for verifying premium + ownership and audit-logging
    # the override; this flag merely records the user's explicit intent.
    force: bool = False
    # Optional, audit-only — UI can pass a short reason string. Truncated
    # server-side. Standard users are forbidden from setting force=true.
    force_reason: Optional[str] = None


class ExportJobInDB(BaseModel):
    id: str = Field(alias="_id")
    presentation_id: str
    user_id: str
    format: ExportFormat
    status: ExportStatus = ExportStatus.PENDING
    download_url: Optional[str] = None
    file_size: Optional[int] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Config:
        populate_by_name = True


class ExportJobResponse(BaseModel):
    id: str
    presentation_id: str
    format: ExportFormat
    status: ExportStatus
    download_url: Optional[str] = None
    file_size: Optional[int] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class RenderedFile(BaseModel):
    url: str
    format: str
    file_size: int
    filename: str
