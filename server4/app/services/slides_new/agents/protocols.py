"""
Agent Communication Protocols — V7 Phase 2
Defines typed contracts for inter-agent data exchange via Context Board.

Each agent writes to specific sections:
- CEO → strategy
- Researcher → research
- Designer → design
- Layout → layout
- Code → dsl
- QA → quality
- Image → images
- Orchestrator → status
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionPhase(str, Enum):
    """Pipeline execution phases"""
    INITIALIZING = "initializing"
    STRATEGY = "strategy"  # CEO running
    RESEARCH_DESIGN = "research_design"  # Researcher + Designer parallel
    LAYOUT = "layout"  # Layout agent
    CODE_GENERATION = "code_generation"  # Code agent
    VFX = "vfx"  # 3D/VFX agent (if needed)
    ASSEMBLY = "assembly"  # Assembler
    QA = "qa"  # Quality assurance
    LEARNING = "learning"  # Self-learning: Teacher evaluation + lesson extraction
    COMPLETE = "complete"
    FAILED = "failed"


class ArchetypeType(str, Enum):
    """Presentation archetypes from CEO Agent"""
    YC_SEED = "yc_seed"
    SERIES_A = "series_a"
    CONSULTING = "consulting"
    QUARTERLY_REPORT = "quarterly_report"
    SALES = "sales"
    PRODUCT_LAUNCH = "product_launch"
    ENTERPRISE_SALES = "enterprise_sales"
    INVESTOR_UPDATE = "investor_update"
    BOARD_DECK = "board_deck"
    ACADEMIC_DEFENSE = "academic_defense"
    MVP_PITCH = "mvp_pitch"


class WritingStyle(str, Enum):
    """Writing styles for content generation"""
    YC_PITCH = "yc_pitch"
    ANALYTICAL = "analytical"
    CONSULTING = "consulting"
    INVESTOR_UPDATE = "investor_update"
    SALES = "sales"
    MARKETING = "marketing"
    GENERAL = "general"


class LayoutRuleName(str, Enum):
    """Named layout rules for Layout Agent"""
    SINGLE_COLUMN_CENTER = "single_column_center"
    TWO_COLUMN_EQUAL = "two_column_equal"
    TWO_COLUMN_60_40 = "two_column_60_40"
    THREE_COLUMN = "three_column"
    HERO_WITH_SUBTITLE = "hero_with_subtitle"
    CONTENT_WITH_IMAGE_RIGHT = "content_with_image_right"
    CONTENT_WITH_IMAGE_LEFT = "content_with_image_left"
    GRID_2X2 = "grid_2x2"
    GRID_3X2 = "grid_3x2"
    GRID_2X3 = "grid_2x3"
    TIMELINE_HORIZONTAL = "timeline_horizontal"
    TIMELINE_VERTICAL = "timeline_vertical"
    KPI_DASHBOARD = "kpi_dashboard"
    TEAM_GRID = "team_grid"
    COMPARISON_SIDE_BY_SIDE = "comparison_side_by_side"
    QUOTE_CENTERED = "quote_centered"
    FULL_BLEED_IMAGE = "full_bleed_image"


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT BOARD SECTION MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class StrategyData(BaseModel):
    """CEO Agent writes this to strategy section"""
    archetype: ArchetypeType
    archetype_name: str
    narrative_arc: str = Field(description="High-level story flow")
    target_audience: str
    audience_persona: Optional[str] = None
    writing_style: WritingStyle
    slide_count: int
    structure: List[Dict[str, Any]] = Field(default_factory=list)
    key_message: str = Field(description="One-liner for the presentation")
    success_criteria: List[str] = Field(default_factory=list)
    hitl_checkpoint_data: Optional[Dict[str, Any]] = None  # For HITL gate
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class SlideStructure(BaseModel):
    """Structure of a single slide from CEO Agent"""
    index: int
    title: str
    layout: str
    purpose: str
    content_hints: Optional[str] = None
    data_needs: Optional[List[str]] = None


class ResearchDataPoint(BaseModel):
    """A single research data point"""
    value: str
    label: str
    source: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    verified: bool = False


class ResearchStatistic(BaseModel):
    """A research statistic with context"""
    stat: str
    context: str
    source: str
    year: Optional[int] = None


class ResearchExample(BaseModel):
    """A case study or example"""
    company: str
    metric: str
    context: str
    source: Optional[str] = None


class ResearchQuote(BaseModel):
    """An industry quote"""
    quote: str
    author: str
    source: str
    relevance_score: float = Field(default=0.7, ge=0.0, le=1.0)


class SlideResearch(BaseModel):
    """Research data for a single slide"""
    slide_index: int
    title: str
    data_points: List[ResearchDataPoint] = Field(default_factory=list)
    statistics: List[ResearchStatistic] = Field(default_factory=list)
    examples: List[ResearchExample] = Field(default_factory=list)
    quotes: List[ResearchQuote] = Field(default_factory=list)
    key_takeaways: List[str] = Field(default_factory=list)
    research_notes: Optional[str] = None


class ResearchData(BaseModel):
    """Researcher Agent writes this to research section"""
    topic: str
    slide_count: int
    research_items: List[SlideResearch] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    web_search_queries: List[str] = Field(default_factory=list)
    total_data_points: int = 0
    research_depth: str = "standard"  # "quick", "standard", "deep"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ColorPalette(BaseModel):
    """Color palette from Designer Agent"""
    primary: str = Field(description="Primary brand color (hex)")
    secondary: str
    accent: str
    background: str
    surface: str
    text_primary: str
    text_secondary: str
    success: Optional[str] = "#22c55e"
    warning: Optional[str] = "#f59e0b"
    error: Optional[str] = "#ef4444"


class Typography(BaseModel):
    """Typography settings"""
    heading_font: str = "Inter"
    body_font: str = "Inter"
    code_font: str = "JetBrains Mono"
    heading_weight: int = 700
    body_weight: int = 400
    base_size: int = 16


class DesignData(BaseModel):
    """Designer Agent writes this to design section"""
    theme_name: str
    theme_variant: str = "dark"
    color_palette: ColorPalette
    typography: Typography
    spacing_scale: str = "comfortable"  # "compact", "comfortable", "spacious"
    border_radius: str = "medium"  # "none", "small", "medium", "large"
    shadow_intensity: str = "subtle"  # "none", "subtle", "medium", "dramatic"
    animation_style: str = "smooth"  # "none", "subtle", "smooth", "dynamic"
    brand_dna: Optional[Dict[str, Any]] = None
    anti_ai_slop_preset: Optional[str] = None
    style_previews: List[str] = Field(default_factory=list)  # URLs for HITL
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GridSpec(BaseModel):
    """Grid specification for layout"""
    columns: int = 12
    rows: int = 8
    gutter: int = 16
    margin: int = 40


class ContentMeasurement(BaseModel):
    """Content measurement result"""
    element_id: str
    estimated_width: float
    estimated_height: float
    line_count: int
    word_count: int
    needs_truncation: bool = False
    suggested_font_size: Optional[int] = None


class SlideLayout(BaseModel):
    """Layout specification for a single slide"""
    slide_index: int
    layout_rule: LayoutRuleName
    grid_spec: GridSpec = Field(default_factory=GridSpec)
    element_positions: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    content_measurements: List[ContentMeasurement] = Field(default_factory=list)
    responsive_breakpoints: Dict[str, Any] = Field(default_factory=dict)
    layout_reasoning: str = Field(description="Why this layout was chosen")


class LayoutData(BaseModel):
    """Layout Agent writes this to layout section"""
    slide_layouts: List[SlideLayout] = Field(default_factory=list)
    global_grid: GridSpec = Field(default_factory=GridSpec)
    layout_consistency_score: float = Field(default=0.0, ge=0.0, le=1.0)
    pretext_measurements: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class QualityIssue(BaseModel):
    """A quality issue found by QA Agent"""
    slide_index: int
    severity: str  # "critical", "major", "minor"
    category: str  # "content", "layout", "contrast", "typography", "accessibility"
    description: str
    suggestion: str


class QualityData(BaseModel):
    """QA Agent writes this to quality section"""
    overall_score: float = Field(ge=0.0, le=100.0)
    passed: bool
    issues: List[QualityIssue] = Field(default_factory=list)
    iteration: int = 1
    max_iterations: int = 3
    contrast_scores: Dict[int, float] = Field(default_factory=dict)
    accessibility_passed: bool = True
    visual_regression_passed: Optional[bool] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StatusData(BaseModel):
    """Orchestrator writes this to status section"""
    phase: ExecutionPhase
    progress_percent: float = Field(ge=0.0, le=100.0)
    current_agent: Optional[str] = None
    agents_completed: List[str] = Field(default_factory=list)
    agents_failed: List[str] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    estimated_completion: Optional[datetime] = None
    last_update: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    hitl_awaiting: Optional[str] = None  # Which HITL gate is awaiting


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT BOARD HELPER PROTOCOL
# ═══════════════════════════════════════════════════════════════════════════════

class ContextBoardProtocol:
    """
    Helper class for agents to read/write to Context Board with type safety.
    
    Usage:
        protocol = ContextBoardProtocol(board)
        await protocol.write_strategy(strategy_data)
        research = await protocol.read_research()
    """
    
    def __init__(self, board: "ContextBoard"):
        self.board = board
    
    # ── Strategy Section ──
    async def write_strategy(self, data: StrategyData, agent: str = "ceo") -> None:
        """Write strategy data from CEO Agent"""
        await self.board.set("strategy.archetype", data.archetype, agent)
        await self.board.set("strategy.archetype_name", data.archetype_name, agent)
        await self.board.set("strategy.narrative_arc", data.narrative_arc, agent)
        await self.board.set("strategy.target_audience", data.target_audience, agent)
        await self.board.set("strategy.writing_style", data.writing_style, agent)
        await self.board.set("strategy.slide_count", data.slide_count, agent)
        await self.board.set("strategy.structure", data.structure, agent)
        await self.board.set("strategy.key_message", data.key_message, agent)
        if data.hitl_checkpoint_data:
            await self.board.set("strategy.hitl_checkpoint", data.hitl_checkpoint_data, agent)
    
    async def read_strategy(self) -> Optional[StrategyData]:
        """Read strategy data"""
        section = await self.board.get_section("strategy")
        if not section:
            return None
        try:
            return StrategyData(
                archetype=section.get("strategy.archetype", ArchetypeType.SALES),
                archetype_name=section.get("strategy.archetype_name", ""),
                narrative_arc=section.get("strategy.narrative_arc", ""),
                target_audience=section.get("strategy.target_audience", ""),
                writing_style=section.get("strategy.writing_style", WritingStyle.GENERAL),
                slide_count=section.get("strategy.slide_count", 10),
                structure=section.get("strategy.structure", []),
                key_message=section.get("strategy.key_message", ""),
            )
        except Exception:
            return None
    
    # ── Research Section ──
    async def write_research(self, data: ResearchData, agent: str = "researcher") -> None:
        """Write research data from Researcher Agent"""
        await self.board.set("research.topic", data.topic, agent)
        await self.board.set("research.slide_count", data.slide_count, agent)
        await self.board.set("research.items", [item.dict() for item in data.research_items], agent)
        await self.board.set("research.key_findings", data.key_findings, agent)
        await self.board.set("research.sources", data.sources, agent)
        await self.board.set("research.total_data_points", data.total_data_points, agent)
    
    async def read_research(self) -> Optional[ResearchData]:
        """Read research data"""
        section = await self.board.get_section("research")
        if not section:
            return None
        try:
            items_raw = section.get("research.items", [])
            items = [SlideResearch(**item) if isinstance(item, dict) else item for item in items_raw]
            return ResearchData(
                topic=section.get("research.topic", ""),
                slide_count=section.get("research.slide_count", 0),
                research_items=items,
                key_findings=section.get("research.key_findings", []),
                sources=section.get("research.sources", []),
                total_data_points=section.get("research.total_data_points", 0),
            )
        except Exception:
            return None
    
    # ── Design Section ──
    async def write_design(self, data: DesignData, agent: str = "designer") -> None:
        """Write design data from Designer Agent"""
        await self.board.set("design.theme_name", data.theme_name, agent)
        await self.board.set("design.theme_variant", data.theme_variant, agent)
        await self.board.set("design.color_palette", data.color_palette.dict(), agent)
        await self.board.set("design.typography", data.typography.dict(), agent)
        await self.board.set("design.spacing_scale", data.spacing_scale, agent)
        await self.board.set("design.animation_style", data.animation_style, agent)
        if data.style_previews:
            await self.board.set("design.style_previews", data.style_previews, agent)
    
    async def read_design(self) -> Optional[DesignData]:
        """Read design data"""
        section = await self.board.get_section("design")
        if not section:
            return None
        try:
            palette_raw = section.get("design.color_palette", {})
            typo_raw = section.get("design.typography", {})
            return DesignData(
                theme_name=section.get("design.theme_name", ""),
                theme_variant=section.get("design.theme_variant", "dark"),
                color_palette=ColorPalette(**palette_raw) if palette_raw else ColorPalette(
                    primary="#3b82f6", secondary="#6366f1", accent="#f59e0b",
                    background="#0f172a", surface="#1e293b", text_primary="#ffffff",
                    text_secondary="#94a3b8"
                ),
                typography=Typography(**typo_raw) if typo_raw else Typography(),
                spacing_scale=section.get("design.spacing_scale", "comfortable"),
                animation_style=section.get("design.animation_style", "smooth"),
                style_previews=section.get("design.style_previews", []),
            )
        except Exception:
            return None
    
    # ── Layout Section ──
    async def write_layout(self, data: LayoutData, agent: str = "layout") -> None:
        """Write layout data from Layout Agent"""
        await self.board.set("layout.slide_layouts", [sl.dict() for sl in data.slide_layouts], agent)
        await self.board.set("layout.global_grid", data.global_grid.dict(), agent)
        await self.board.set("layout.consistency_score", data.layout_consistency_score, agent)
        if data.pretext_measurements:
            await self.board.set("layout.pretext_measurements", data.pretext_measurements, agent)
    
    async def read_layout(self) -> Optional[LayoutData]:
        """Read layout data"""
        section = await self.board.get_section("layout")
        if not section:
            return None
        try:
            layouts_raw = section.get("layout.slide_layouts", [])
            layouts = []
            for sl in layouts_raw:
                if isinstance(sl, dict):
                    # Handle enum conversion
                    if "layout_rule" in sl and isinstance(sl["layout_rule"], str):
                        try:
                            sl["layout_rule"] = LayoutRuleName(sl["layout_rule"])
                        except ValueError:
                            sl["layout_rule"] = LayoutRuleName.SINGLE_COLUMN_CENTER
                    layouts.append(SlideLayout(**sl))
            return LayoutData(
                slide_layouts=layouts,
                global_grid=GridSpec(**section.get("layout.global_grid", {})),
                layout_consistency_score=section.get("layout.consistency_score", 0.0),
                pretext_measurements=section.get("layout.pretext_measurements", {}),
            )
        except Exception:
            return None
    
    # ── Quality Section ──
    async def write_quality(self, data: QualityData, agent: str = "qa") -> None:
        """Write quality data from QA Agent"""
        await self.board.set("quality.overall_score", data.overall_score, agent)
        await self.board.set("quality.passed", data.passed, agent)
        await self.board.set("quality.issues", [issue.dict() for issue in data.issues], agent)
        await self.board.set("quality.iteration", data.iteration, agent)
        await self.board.set("quality.accessibility_passed", data.accessibility_passed, agent)
    
    async def read_quality(self) -> Optional[QualityData]:
        """Read quality data"""
        section = await self.board.get_section("quality")
        if not section:
            return None
        try:
            issues_raw = section.get("quality.issues", [])
            issues = [QualityIssue(**i) if isinstance(i, dict) else i for i in issues_raw]
            return QualityData(
                overall_score=section.get("quality.overall_score", 0.0),
                passed=section.get("quality.passed", False),
                issues=issues,
                iteration=section.get("quality.iteration", 1),
                accessibility_passed=section.get("quality.accessibility_passed", True),
            )
        except Exception:
            return None
    
    # ── Status Section ──
    async def write_status(self, data: StatusData, agent: str = "orchestrator") -> None:
        """Write status data from Orchestrator"""
        await self.board.set("status.phase", data.phase.value, agent)
        await self.board.set("status.progress_percent", data.progress_percent, agent)
        await self.board.set("status.current_agent", data.current_agent, agent)
        await self.board.set("status.agents_completed", data.agents_completed, agent)
        await self.board.set("status.agents_failed", data.agents_failed, agent)
        await self.board.set("status.last_update", data.last_update.isoformat(), agent)
        if data.error_message:
            await self.board.set("status.error_message", data.error_message, agent)
        if data.hitl_awaiting:
            await self.board.set("status.hitl_awaiting", data.hitl_awaiting, agent)
    
    async def read_status(self) -> Optional[StatusData]:
        """Read status data"""
        section = await self.board.get_section("status")
        if not section:
            return None
        try:
            phase_str = section.get("status.phase", "initializing")
            return StatusData(
                phase=ExecutionPhase(phase_str),
                progress_percent=section.get("status.progress_percent", 0.0),
                current_agent=section.get("status.current_agent"),
                agents_completed=section.get("status.agents_completed", []),
                agents_failed=section.get("status.agents_failed", []),
                error_message=section.get("status.error_message"),
                hitl_awaiting=section.get("status.hitl_awaiting"),
            )
        except Exception:
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT OUTPUT CONTRACTS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentResult:
    """Standard result from any agent execution"""
    success: bool
    agent_name: str
    context_board_writes: List[str] = field(default_factory=list)
    model_used: Optional[str] = None
    tokens_used: int = 0
    latency_ms: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    hitl_checkpoint: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ParallelExecutionResult:
    """Result from parallel agent execution"""
    success: bool
    completed_agents: List[str]
    failed_agents: List[str]
    results: Dict[str, AgentResult]
    total_latency_ms: int = 0
    
    def all_succeeded(self) -> bool:
        return len(self.failed_agents) == 0


# Type alias for Context Board import
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.services.context_board import ContextBoard
