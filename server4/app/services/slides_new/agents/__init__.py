"""
Agent Module Exports — V7 Phase 2
"""

from app.services.slides_new.agents.base import (
    BaseAgent,
    AgentType,
    AgentContext,
    AgentOutput,
    AgentFactory,
)
from app.services.slides_new.agents.ceo_agent import CEOAgent, CEOAgentWithTemplates
from app.services.slides_new.agents.researcher_agent import ResearcherAgent
from app.services.slides_new.agents.designer_agent import DesignerAgent
from app.services.slides_new.agents.layout_agent import LayoutAgent, LayoutAgentWithPreText
from app.services.slides_new.agents.assembler_agent import AssemblerAgent
from app.services.slides_new.agents.qa_agent import QAAgent
from app.services.slides_new.agents.vfx_agent import VFXAgent
from app.services.slides_new.learning.teacher_agent import TeacherAgent

# Protocol exports
from app.services.slides_new.agents.protocols import (
    ContextBoardProtocol,
    ExecutionPhase,
    ArchetypeType,
    WritingStyle,
    LayoutRuleName,
    StrategyData,
    ResearchData,
    DesignData,
    LayoutData,
    QualityData,
    StatusData,
    SlideStructure,
    SlideResearch,
    SlideLayout,
    GridSpec,
    ColorPalette,
    Typography,
    AgentResult,
    ParallelExecutionResult,
)

__all__ = [
    # Base classes
    "BaseAgent",
    "AgentType",
    "AgentContext",
    "AgentOutput",
    "AgentFactory",
    # Agents
    "CEOAgent",
    "CEOAgentWithTemplates",
    "ResearcherAgent",
    "DesignerAgent",
    "LayoutAgent",
    "LayoutAgentWithPreText",
    "AssemblerAgent",
    "QAAgent",
    "VFXAgent",
    "TeacherAgent",
    # Protocol
    "ContextBoardProtocol",
    "ExecutionPhase",
    "ArchetypeType",
    "WritingStyle",
    "LayoutRuleName",
    # Data models
    "StrategyData",
    "ResearchData",
    "DesignData",
    "LayoutData",
    "QualityData",
    "StatusData",
    "SlideStructure",
    "SlideResearch",
    "SlideLayout",
    "GridSpec",
    "ColorPalette",
    "Typography",
    "AgentResult",
    "ParallelExecutionResult",
]
