"""Content generation models — used by Brain MCP."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class OutlineSlide(BaseModel):
    index: int
    title: str
    purpose: str
    suggested_layout: str
    content_hints: Optional[str] = None
    needs_research: bool = False
    needs_chart: bool = False
    needs_image: bool = False


class PresentationOutline(BaseModel):
    title: str
    subtitle: Optional[str] = None
    slides: list[OutlineSlide]
    narrative_arc: Optional[str] = None  # Brief description of the story flow


class ResearchResult(BaseModel):
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    data_points: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, str]] = Field(default_factory=list)
    confidence: float = 0.0  # 0-1


class MarketAnalysis(BaseModel):
    tam: Optional[str] = None
    sam: Optional[str] = None
    som: Optional[str] = None
    growth_rate: Optional[str] = None
    key_players: list[str] = Field(default_factory=list)
    trends: list[str] = Field(default_factory=list)
    sources: list[dict[str, str]] = Field(default_factory=list)


class ChartData(BaseModel):
    chart_type: str  # bar | line | pie | donut | funnel | area
    title: str
    subtitle: Optional[str] = None
    labels: list[str]
    datasets: list[dict[str, Any]]
    source_attribution: Optional[str] = None


class RefinedContent(BaseModel):
    content: dict[str, Any]
    changes_summary: str
    before_after: Optional[dict] = None


class SpeakerNotes(BaseModel):
    talking_points: list[str]
    transitions: Optional[str] = None
    timing_cue: Optional[str] = None
    audience_tips: Optional[str] = None
