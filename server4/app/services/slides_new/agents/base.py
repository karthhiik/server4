"""
Base Agent Class - Phase 1 Foundation
All slide generation agents inherit from this base class.
Provides LLM calling, error handling, logging, and common utilities.
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.llm import ModelRouter, TaskType

logger = structlog.get_logger()


class AgentType(str, Enum):
    """Agent types in the slide generation pipeline"""

    CEO = "ceo"
    RESEARCHER = "researcher"
    DESIGNER = "designer"
    ASSEMBLER = "assembler"
    CODE_AGENT = "code_agent"
    QA = "qa"


@dataclass
class AgentOutput:
    """Standard output format for all agents"""

    success: bool
    agent_type: AgentType
    output: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    model_used: Optional[str] = None
    tokens_used: int = 0
    latency_ms: int = 0
    warnings: List[str] = field(default_factory=list)


@dataclass
class AgentContext:
    """Shared context passed between agents"""

    task_id: str
    user_id: str
    topic: str
    description: str
    purpose: str
    audience: str
    slide_count: int
    mode: str
    writing_style: str = "general"
    selected_style_preset: Optional[str] = None
    company_name: Optional[str] = None
    custom_theme: Optional[Dict] = None
    previous_outputs: Dict[str, AgentOutput] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Base class for all slide generation agents.
    Provides:
    - LLM calling with proper error handling
    - Logging and observability
    - Database access
    - Common utilities
    """

    # Default model for this agent type - override in subclasses
    DEFAULT_MODEL = "deepseek-v3"
    FALLBACK_MODELS = ["mistral-medium", "groq", "cf-qwen"]

    def __init__(self, db: AsyncIOMotorDatabase, context: AgentContext):
        """
        Initialize agent with database connection and context.

        Args:
            db: MongoDB database instance
            context: Shared context for this generation task
        """
        self.db = db
        self.context = context
        self.router = ModelRouter.get_instance()

    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """Return the type of this agent - must be implemented by subclasses"""
        pass

    @abstractmethod
    async def execute(self) -> AgentOutput:
        """
        Execute the agent's main logic.
        Must be implemented by each agent.

        Returns:
            AgentOutput with results or errors
        """
        pass

    async def call_llm(
        self,
        task_type: TaskType,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        system_prompt: Optional[str] = None,
    ) -> AgentOutput:
        """
        Make LLM call with proper error handling, retries, and logging.

        Args:
            task_type: Type of task for routing
            prompt: User prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            response_format: If JSON, pass schema
            system_prompt: Optional system prompt

        Returns:
            AgentOutput with response or error
        """
        start_time = time.monotonic()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Try default model first
        for model_attempt, model_name in enumerate(
            [self.DEFAULT_MODEL] + self.FALLBACK_MODELS
        ):
            try:
                response = await self.router.complete(
                    task_type=task_type,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    presentation_id=self.context.task_id,
                    phase=self.agent_type.value,
                )

                latency = int((time.monotonic() - start_time) * 1000)

                # Validate response
                if not response.content or not response.content.strip():
                    logger.warning(
                        "agent_empty_response",
                        agent=self.agent_type.value,
                        model=model_name,
                        task_type=task_type.value,
                    )
                    continue  # Try next model

                logger.info(
                    "agent_llm_success",
                    agent=self.agent_type.value,
                    model=model_name,
                    provider=response.provider
                    if hasattr(response, "provider")
                    else "unknown",
                    latency_ms=latency,
                    tokens=response.tokens_used
                    if hasattr(response, "tokens_used")
                    else 0,
                )

                return AgentOutput(
                    success=True,
                    agent_type=self.agent_type,
                    output={"content": response.content, "raw_response": response},
                    model_used=model_name,
                    tokens_used=response.tokens_used
                    if hasattr(response, "tokens_used")
                    else 0,
                    latency_ms=latency,
                )

            except Exception as e:
                latency = int((time.monotonic() - start_time) * 1000)
                logger.warning(
                    "agent_llm_error",
                    agent=self.agent_type.value,
                    model=model_name,
                    error=str(e),
                    latency_ms=latency,
                    attempt=model_attempt + 1,
                )

                # If it's a hard error (not just rate limit), try next model
                error_str = str(e).lower()
                if (
                    "rate_limit" not in error_str
                    and "429" not in error_str
                    and "timeout" not in error_str
                ):
                    continue

                # Small delay before retry
                if model_attempt < len(self.FALLBACK_MODELS):
                    await asyncio.sleep(0.5)
                    continue

                # All models failed
                return AgentOutput(
                    success=False,
                    agent_type=self.agent_type,
                    output={},
                    errors=[f"All models failed: {str(e)}"],
                    latency_ms=latency,
                )

        # Should not reach here, but handle case
        return AgentOutput(
            success=False,
            agent_type=self.agent_type,
            output={},
            errors=["No models available"],
            latency_ms=int((time.monotonic() - start_time) * 1000),
        )

    async def call_llm_json(
        self,
        task_type: TaskType,
        prompt: str,
        temperature: float = 0.5,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
    ) -> AgentOutput:
        """
        Convenience method for JSON responses.
        Parses JSON and returns structured output.
        """
        result = await self.call_llm(
            task_type=task_type,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            system_prompt=system_prompt,
        )

        if not result.success:
            return result

        # Parse JSON from response
        try:
            parsed = json.loads(result.output.get("content", "{}"))
            result.output = parsed
            return result
        except json.JSONDecodeError as e:
            logger.error(
                "agent_json_parse_error", agent=self.agent_type.value, error=str(e)
            )
            return AgentOutput(
                success=False,
                agent_type=self.agent_type,
                output={},
                errors=[f"Failed to parse JSON: {str(e)}"],
                model_used=result.model_used,
                tokens_used=result.tokens_used,
                latency_ms=result.latency_ms,
            )

    def log_progress(self, message: str, level: str = "info"):
        """Log progress with context"""
        log = getattr(logger, level, logger.info)
        log(
            "agent_progress",
            agent=self.agent_type.value,
            task_id=self.context.task_id,
            message=message,
        )

    async def validate_input(self, required_fields: List[str]) -> Optional[AgentOutput]:
        """
        Validate that required fields exist in context.
        Returns error output if validation fails, None if passes.
        """
        context_dict = (
            self.context.__dict__ if hasattr(self.context, "__dict__") else {}
        )

        missing = []
        for field in required_fields:
            if field not in context_dict or context_dict[field] is None:
                missing.append(field)

        if missing:
            return AgentOutput(
                success=False,
                agent_type=self.agent_type,
                output={},
                errors=[f"Missing required fields: {', '.join(missing)}"],
            )

        return None  # Validation passed

    def get_style_preset_system_prompt(self) -> str:
        """System prompt for style-related tasks"""
        return """You are an expert presentation designer. 
Create visually stunning, professional slide designs.
Avoid generic AI aesthetics - use specific, distinctive styling.
Consider contrast, typography, spacing, and visual hierarchy.
Output clean, structured content that fits each slide layout perfectly."""


class AgentFactory:
    """Factory for creating agents"""

    _agents = {
        AgentType.CEO: "CEOAgent",
        AgentType.RESEARCHER: "ResearcherAgent",
        AgentType.DESIGNER: "DesignerAgent",
        AgentType.ASSEMBLER: "AssemblerAgent",
        AgentType.QA: "QAAgent",
    }

    @classmethod
    def create(
        cls, agent_type: AgentType, db: AsyncIOMotorDatabase, context: AgentContext
    ) -> BaseAgent:
        """Create an agent instance"""
        from app.services.slides_new.agents.ceo_agent import CEOAgent
        from app.services.slides_new.agents.researcher_agent import ResearcherAgent
        from app.services.slides_new.agents.designer_agent import DesignerAgent
        from app.services.slides_new.agents.assembler_agent import AssemblerAgent
        from app.services.slides_new.agents.qa_agent import QAAgent

        agent_map = {
            AgentType.CEO: CEOAgent,
            AgentType.RESEARCHER: ResearcherAgent,
            AgentType.DESIGNER: DesignerAgent,
            AgentType.ASSEMBLER: AssemblerAgent,
            AgentType.QA: QAAgent,
        }

        agent_class = agent_map.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")

        return agent_class(db, context)
