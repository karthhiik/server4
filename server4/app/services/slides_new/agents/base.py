"""
Base Agent Class - V7 Phase 2
All slide generation agents inherit from this base class.
Provides LLM calling, error handling, logging, Context Board integration, and common utilities.

Updated for Phase 2:
- Context Board integration for inter-agent communication
- New Layout and VFX agent types
- Enhanced execution tracking
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.llm import ModelRouter, TaskType

if TYPE_CHECKING:
    from app.services.context_board import ContextBoard
    from app.services.slides_new.agents.protocols import ContextBoardProtocol

logger = structlog.get_logger()


class AgentType(str, Enum):
    """Agent types in the slide generation pipeline - V7"""

    CEO = "ceo"
    RESEARCHER = "researcher"
    DESIGNER = "designer"
    LAYOUT = "layout"  # NEW in Phase 2
    CODE_AGENT = "code_agent"
    VFX = "vfx"  # NEW - 3D/VFX Agent
    ASSEMBLER = "assembler"
    QA = "qa"
    TEACHER = "teacher"  # Self-learning: evaluates and teaches


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
    context_board_writes: List[str] = field(default_factory=list)  # V7: Track writes
    hitl_checkpoint: Optional[Dict[str, Any]] = None  # V7: HITL gate data


@dataclass
class AgentContext:
    """Shared context passed between agents - V7 Enhanced"""

    task_id: str
    user_id: str
    topic: str
    description: str
    purpose: str
    audience: str
    slide_count: int
    mode: str  # "fast" | "standard" | "deep"
    writing_style: str = "general"
    selected_style_preset: Optional[str] = None
    company_name: Optional[str] = None
    custom_theme: Optional[Dict] = None
    previous_outputs: Dict[str, AgentOutput] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # V7 additions
    fast_mode: bool = False  # Skip HITL gates
    research_depth: str = "standard"  # "quick" | "standard" | "deep"
    enable_3d: bool = False  # Whether to use 3D/VFX agent
    target_renderers: List[str] = field(default_factory=lambda: ["revealjs"])


class BaseAgent(ABC):
    """
    Base class for all slide generation agents - V7 Phase 2.
    Provides:
    - LLM calling with proper error handling and fallback chains
    - Context Board integration for inter-agent communication
    - Logging and observability
    - Database access
    - Common utilities
    """

    # Default model for this agent type - override in subclasses
    DEFAULT_MODEL = "deepseek-v3"
    FALLBACK_MODELS = ["gpt-4o-mini", "mistral-medium", "cf-qwen"]

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        context: AgentContext,
        context_board: Optional["ContextBoard"] = None,
    ):
        """
        Initialize agent with database connection, context, and optional Context Board.

        Args:
            db: MongoDB database instance
            context: Shared context for this generation task
            context_board: Optional Context Board for inter-agent communication
        """
        self.db = db
        self.context = context
        self.router = ModelRouter.get_instance()
        self._context_board = context_board
        self._protocol: Optional["ContextBoardProtocol"] = None
        self._board_writes: List[str] = []
        self._start_time: Optional[float] = None

    @property
    def context_board(self) -> Optional["ContextBoard"]:
        """Get the Context Board instance"""
        return self._context_board

    @property
    def protocol(self) -> Optional["ContextBoardProtocol"]:
        """Get the Context Board Protocol helper for typed access"""
        if self._protocol is None and self._context_board is not None:
            from app.services.slides_new.agents.protocols import ContextBoardProtocol
            self._protocol = ContextBoardProtocol(self._context_board)
        return self._protocol

    async def write_to_board(self, key: str, value: Any) -> None:
        """Write a value to the Context Board with tracking"""
        if self._context_board is not None:
            await self._context_board.set(key, value, self.agent_type.value)
            self._board_writes.append(key)
            logger.debug(
                "agent_board_write",
                agent=self.agent_type.value,
                key=key,
                task_id=self.context.task_id,
            )

    async def read_from_board(self, key: str) -> Optional[Any]:
        """Read a value from the Context Board"""
        if self._context_board is not None:
            return await self._context_board.get(key)
        return None

    async def get_board_section(self, section: str) -> Dict[str, Any]:
        """Get all values from a Context Board section"""
        if self._context_board is not None:
            return await self._context_board.get_section(section)
        return {}

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
    """Factory for creating agents - V7 Phase 2"""

    _agents = {
        AgentType.CEO: "CEOAgent",
        AgentType.RESEARCHER: "ResearcherAgent",
        AgentType.DESIGNER: "DesignerAgent",
        AgentType.LAYOUT: "LayoutAgent",  # NEW in Phase 2
        AgentType.ASSEMBLER: "AssemblerAgent",
        AgentType.CODE_AGENT: "CodeAgent",
        AgentType.VFX: "VFXAgent",  # NEW in Phase 2
        AgentType.QA: "QAAgent",
        AgentType.TEACHER: "TeacherAgent",  # Self-learning
    }

    @classmethod
    def create(
        cls,
        agent_type: AgentType,
        db: AsyncIOMotorDatabase,
        context: AgentContext,
        context_board: Optional["ContextBoard"] = None,
    ) -> BaseAgent:
        """Create an agent instance with optional Context Board integration"""
        from app.services.slides_new.agents.ceo_agent import CEOAgent
        from app.services.slides_new.agents.researcher_agent import ResearcherAgent
        from app.services.slides_new.agents.designer_agent import DesignerAgent
        from app.services.slides_new.agents.layout_agent import LayoutAgent
        from app.services.slides_new.agents.assembler_agent import AssemblerAgent
        from app.services.slides_new.agents.code_agent import CodeAgent
        from app.services.slides_new.agents.qa_agent import QAAgent
        from app.services.slides_new.learning.teacher_agent import TeacherAgent

        agent_map = {
            AgentType.CEO: CEOAgent,
            AgentType.RESEARCHER: ResearcherAgent,
            AgentType.DESIGNER: DesignerAgent,
            AgentType.LAYOUT: LayoutAgent,
            AgentType.ASSEMBLER: AssemblerAgent,
            AgentType.CODE_AGENT: CodeAgent,
            AgentType.QA: QAAgent,
            AgentType.TEACHER: TeacherAgent,
        }

        agent_class = agent_map.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")

        return agent_class(db, context, context_board)
