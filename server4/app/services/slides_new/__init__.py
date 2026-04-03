"""
New Slide Generation Services - Phase 1 Foundation
Complete implementation with orchestrator and base agent class.
"""

from app.services.slides_new.orchestrator import (
    SlideGenerationOrchestrator,
    PipelineOrchestrator,
)
from app.services.slides_new.agents.base import (
    BaseAgent,
    AgentType,
    AgentContext,
    AgentOutput,
    AgentFactory,
)
from app.services.slides_new.agents.ceo_agent import CEOAgent
from app.services.slides_new.agents.researcher_agent import ResearcherAgent
from app.services.slides_new.agents.designer_agent import DesignerAgent
from app.services.slides_new.agents.assembler_agent import AssemblerAgent
from app.services.slides_new.agents.qa_agent import QAAgent
from app.services.slides_new.templates.engine import TemplateEngine

__all__ = [
    "SlideGenerationOrchestrator",
    "PipelineOrchestrator",
    "BaseAgent",
    "AgentType",
    "AgentContext",
    "AgentOutput",
    "AgentFactory",
    "CEOAgent",
    "ResearcherAgent",
    "DesignerAgent",
    "AssemblerAgent",
    "QAAgent",
    "TemplateEngine",
]
