"""
Agent Module Exports
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
from app.services.slides_new.agents.assembler_agent import AssemblerAgent
from app.services.slides_new.agents.qa_agent import QAAgent

__all__ = [
    "BaseAgent",
    "AgentType",
    "AgentContext",
    "AgentOutput",
    "AgentFactory",
    "CEOAgent",
    "CEOAgentWithTemplates",
    "ResearcherAgent",
    "DesignerAgent",
    "AssemblerAgent",
    "QAAgent",
]
