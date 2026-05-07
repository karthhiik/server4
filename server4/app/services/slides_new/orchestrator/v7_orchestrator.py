"""
V7 Orchestrator — Phase 2 Enhanced Orchestrator
Main orchestration layer for V7 slide generation pipeline.

Features:
- Context Board integration for inter-agent communication
- Parallel execution of Researcher + Designer
- HITL (Human-in-the-Loop) checkpoint support
- Full observability and progress tracking
- Error recovery and partial results
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import structlog

from app.services.context_board import ContextBoard
from app.services.slides_new.agents.base import (
    AgentContext,
    AgentOutput,
    AgentType,
    AgentFactory,
)
from app.services.slides_new.agents.protocols import (
    ExecutionPhase,
    StatusData,
    ContextBoardProtocol,
)
from app.services.slides_new.orchestrator.parallel_runner import (
    ParallelExecutor,
    PipelineOrchestrator,
    ExecutionPlan,
    AgentTask,
    ExecutionMode,
)
from app.services.slides_new.learning.learning_engine import LearningEngine
from app.services.slides_new.orchestrator.evidence_bridge import EvidenceBridge

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = structlog.get_logger()


@dataclass
class V7GenerationConfig:
    """Configuration for V7 slide generation"""

    fast_mode: bool = False  # Skip HITL gates
    research_depth: str = "standard"  # "quick", "standard", "deep"
    enable_3d: bool = False  # Use 3D/VFX agent
    target_renderers: List[str] = field(default_factory=lambda: ["revealjs"])
    max_qa_iterations: int = 3
    timeout_per_agent: int = 120  # seconds
    parallel_research_design: bool = True
    enable_learning: bool = True  # Self-learning after generation


@dataclass
class V7GenerationResult:
    """Result from V7 slide generation"""

    success: bool
    presentation_id: Optional[str] = None
    slides: List[Dict[str, Any]] = field(default_factory=list)
    strategy: Optional[Dict[str, Any]] = None
    research: Optional[Dict[str, Any]] = None
    design: Optional[Dict[str, Any]] = None
    layout: Optional[Dict[str, Any]] = None
    quality_score: float = 0.0
    quality_passed: bool = False
    total_latency_ms: int = 0
    agent_metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    hitl_checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    # Learning system outputs
    teacher_feedback: Optional[Dict[str, Any]] = None
    lessons_learned: int = 0
    # Evidence bridge outputs (premium mode only)
    evidence_report: Optional[Dict[str, Any]] = None


class V7Orchestrator:
    """
    V7 Slide Generation Orchestrator — Phase 2.

    Orchestrates the full slide generation pipeline with:
    - Context Board for inter-agent communication
    - Parallel execution of independent agents
    - HITL checkpoints for user approval gates
    - Quality assurance with reflective loop

    Usage:
        orchestrator = V7Orchestrator(db)
        result = await orchestrator.generate(
            user_id="user123",
            topic="AI Startup Pitch",
            description="Series A pitch for AI infrastructure company",
            purpose="fundraising",
            audience="VCs",
            config=V7GenerationConfig(fast_mode=False)
        )
    """

    def __init__(self, db: "AsyncIOMotorDatabase"):
        self.db = db
        self._context_board: Optional[ContextBoard] = None
        self._protocol: Optional[ContextBoardProtocol] = None
        self._learning_engine: Optional[LearningEngine] = None

    async def generate(
        self,
        user_id: str,
        topic: str,
        description: str,
        purpose: str,
        audience: str,
        slide_count: int = 10,
        company_name: Optional[str] = None,
        custom_theme: Optional[Dict[str, Any]] = None,
        config: Optional[V7GenerationConfig] = None,
        evidence_contracts: Optional[List[Any]] = None,
    ) -> V7GenerationResult:
        """
        Generate a presentation using the V7 pipeline.

        Args:
            user_id: User ID for attribution
            topic: Main topic/title of the presentation
            description: Detailed description of what to present
            purpose: Purpose (fundraising, sales, etc.)
            audience: Target audience
            slide_count: Number of slides (default 10)
            company_name: Optional company name for branding
            custom_theme: Optional custom theme settings
            config: Generation configuration
            evidence_contracts: Optional pre-researched SlideContentContracts
                from the Brain MCP pipeline. When provided, the ResearcherAgent
                is SKIPPED and evidence is injected via EvidenceBridge.

        Returns:
            V7GenerationResult with presentation data
        """
        config = config or V7GenerationConfig()
        start_time = time.monotonic()

        # Generate unique task ID
        import uuid

        task_id = str(uuid.uuid4())

        logger.info(
            "v7_generation_started",
            task_id=task_id,
            user_id=user_id,
            topic=topic,
            fast_mode=config.fast_mode,
        )

        # Initialize Context Board - with fallback for Redis issues
        try:
            self._context_board = ContextBoard(session_id=task_id)
            await self._context_board.connect()
            self._protocol = ContextBoardProtocol(self._context_board)
        except Exception as e:
            logger.warning(
                "context_board_init_failed_using_in_memory",
                task_id=task_id,
                error=str(e),
            )
            # Create a simple in-memory context board substitute
            from app.services.slides_new.agents.protocols import ContextBoardProtocol

            class InMemoryBoard:
                def __init__(self):
                    self._data = {}

                async def set(self, key, value, agent=None):
                    self._data[key] = value

                async def get(self, key):
                    return self._data.get(key)

                async def get_section(self, section):
                    return {
                        k: v
                        for k, v in self._data.items()
                        if k.startswith(section + ".")
                    }

                async def close(self):
                    pass

            self._context_board = InMemoryBoard()
            self._protocol = ContextBoardProtocol(self._context_board)

        try:
            # Build agent context
            context = AgentContext(
                task_id=task_id,
                user_id=user_id,
                topic=topic,
                description=description,
                purpose=purpose,
                audience=audience,
                slide_count=slide_count,
                mode=config.research_depth,
                company_name=company_name,
                custom_theme=custom_theme,
                fast_mode=config.fast_mode,
                research_depth=config.research_depth,
                enable_3d=config.enable_3d,
                target_renderers=config.target_renderers,
            )

            # Initialize status
            await self._update_status(ExecutionPhase.INITIALIZING, 0.0)

            # Phase 1: CEO Agent (Strategy)
            # If premium evidence available, inject summary into context for richer strategy
            if evidence_contracts:
                bridge = EvidenceBridge(self._context_board)
                evidence_summary = bridge.extract_research_summary(evidence_contracts)
                await self._context_board.set(
                    "research.premium_summary",
                    evidence_summary,
                    agent="evidence_bridge",
                )
                logger.info(
                    "evidence_injected_for_ceo",
                    task_id=task_id,
                    total_contracts=len(evidence_contracts),
                )

            ceo_result = await self._run_ceo_agent(context)
            if not ceo_result.success:
                return self._build_error_result(
                    "CEO Agent failed",
                    ceo_result.errors,
                    start_time,
                )

            # Check HITL checkpoint for narrative approval
            hitl_checkpoints = []
            if ceo_result.hitl_checkpoint and not config.fast_mode:
                hitl_checkpoints.append(ceo_result.hitl_checkpoint)
                # In real implementation, would pause for approval here

            # Phase 2: Researcher + Designer (Parallel)
            if evidence_contracts:
                # SKIP ResearcherAgent — use EvidenceBridge to inject pre-researched data
                bridge = EvidenceBridge(self._context_board)
                await bridge.bridge_to_context(evidence_contracts)

                # Create a synthetic researcher output for downstream agents
                researcher_result = AgentOutput(
                    success=True,
                    agent_type=AgentType.RESEARCHER,
                    output=bridge.extract_research_summary(evidence_contracts),
                )
                context.previous_outputs[AgentType.RESEARCHER] = researcher_result

                # Designer still runs (independent of evidence)
                await self._update_status(
                    ExecutionPhase.RESEARCH_DESIGN, 25.0, "designer"
                )
                designer = AgentFactory.create(
                    AgentType.DESIGNER,
                    self.db,
                    context,
                    self._context_board,
                )
                designer_result = await designer.execute()
                context.previous_outputs[AgentType.DESIGNER] = designer_result

                phase2_results = {
                    AgentType.RESEARCHER: researcher_result,
                    AgentType.DESIGNER: designer_result,
                }

                logger.info(
                    "evidence_bridge_skipped_researcher",
                    task_id=task_id,
                    evidence_slides=len(evidence_contracts),
                )
            elif config.parallel_research_design:
                phase2_results = await self._run_research_design_parallel(context)
            else:
                phase2_results = await self._run_research_design_sequential(context)

            researcher_result = phase2_results.get(AgentType.RESEARCHER)
            designer_result = phase2_results.get(AgentType.DESIGNER)

            if not researcher_result or not researcher_result.success:
                return self._build_error_result(
                    "Researcher Agent failed",
                    researcher_result.errors
                    if researcher_result
                    else ["Unknown error"],
                    start_time,
                )

            # Phase 3: Layout Agent
            layout_result = await self._run_layout_agent(context)

            # Phase 4: Code Agent (existing implementation)
            code_result = await self._run_code_agent(context)

            # Phase 5: Assembler Agent
            assembler_result = await self._run_assembler_agent(context)

            # Phase 6: QA Agent with reflective loop
            qa_result = await self._run_qa_with_loop(context, config.max_qa_iterations)

            # Phase 7: Self-Learning (Teacher Agent + Lesson Extraction)
            teacher_feedback = None
            lessons_learned = 0
            if config.enable_learning:
                teacher_feedback, lessons_learned = await self._run_learning_phase(
                    context, qa_result, config
                )

            # Calculate total latency
            total_latency = int((time.monotonic() - start_time) * 1000)

            # Collect errors from all agents
            all_errors = []
            for agent_name, agent_output in {
                "ceo": ceo_result,
                "researcher": researcher_result,
                "designer": designer_result,
                "layout": layout_result,
                "code": code_result,
                "assembler": assembler_result,
                "qa": qa_result,
            }.items():
                if agent_output and not agent_output.success:
                    all_errors.append(f"{agent_name}: {agent_output.errors}")

            # Build result
            result = V7GenerationResult(
                success=qa_result.success
                if qa_result
                else (assembler_result.success if assembler_result else True),
                presentation_id=task_id,
                slides=assembler_result.output.get("slides", [])
                if assembler_result
                else [],
                strategy=ceo_result.output,
                research=researcher_result.output if researcher_result else None,
                design=designer_result.output if designer_result else None,
                layout=layout_result.output if layout_result else None,
                quality_score=qa_result.output.get("quality_score", 0.0)
                if qa_result
                else 0.0,
                quality_passed=qa_result.output.get("passed", False)
                if qa_result
                else False,
                total_latency_ms=total_latency,
                agent_metrics=self._collect_agent_metrics(
                    {
                        "ceo": ceo_result,
                        "researcher": researcher_result,
                        "designer": designer_result,
                        "layout": layout_result,
                        "code": code_result,
                        "assembler": assembler_result,
                        "qa": qa_result,
                    }
                ),
                hitl_checkpoints=hitl_checkpoints,
                teacher_feedback=teacher_feedback,
                lessons_learned=lessons_learned,
                evidence_report=(
                    EvidenceBridge.extract_evidence_metrics(evidence_contracts)
                    if evidence_contracts
                    else None
                ),
                errors=all_errors,
            )

            await self._update_status(ExecutionPhase.COMPLETE, 100.0)

            logger.info(
                "v7_generation_completed",
                task_id=task_id,
                success=result.success,
                latency_ms=total_latency,
                quality_score=result.quality_score,
            )

            return result

        except Exception as e:
            logger.exception("v7_generation_error", task_id=task_id, error=str(e))
            return self._build_error_result(str(e), [str(e)], start_time)

        finally:
            # Clean up Context Board
            if self._context_board:
                await self._context_board.close()

    async def _run_ceo_agent(self, context: AgentContext) -> AgentOutput:
        """Run CEO Agent for strategy"""
        await self._update_status(ExecutionPhase.STRATEGY, 10.0, "ceo")

        agent = AgentFactory.create(
            AgentType.CEO,
            self.db,
            context,
            self._context_board,
        )
        output = await agent.execute()
        context.previous_outputs[AgentType.CEO] = output

        return output

    async def _run_research_design_parallel(
        self, context: AgentContext
    ) -> Dict[AgentType, AgentOutput]:
        """Run Researcher and Designer agents in parallel"""
        await self._update_status(
            ExecutionPhase.RESEARCH_DESIGN, 25.0, "researcher+designer"
        )

        # Create agents
        researcher = AgentFactory.create(
            AgentType.RESEARCHER,
            self.db,
            context,
            self._context_board,
        )
        designer = AgentFactory.create(
            AgentType.DESIGNER,
            self.db,
            context,
            self._context_board,
        )

        # Execute in parallel
        results = await asyncio.gather(
            researcher.execute(),
            designer.execute(),
            return_exceptions=True,
        )

        outputs: Dict[AgentType, AgentOutput] = {}

        # Process results
        for i, result in enumerate(results):
            agent_type = AgentType.RESEARCHER if i == 0 else AgentType.DESIGNER
            if isinstance(result, Exception):
                logger.error(
                    "parallel_agent_error",
                    agent=agent_type.value,
                    error=str(result),
                )
                outputs[agent_type] = AgentOutput(
                    success=False,
                    agent_type=agent_type,
                    errors=[str(result)],
                )
            else:
                outputs[agent_type] = result
                context.previous_outputs[agent_type] = result

        return outputs

    async def _run_research_design_sequential(
        self, context: AgentContext
    ) -> Dict[AgentType, AgentOutput]:
        """Run Researcher and Designer agents sequentially (fallback)"""
        outputs: Dict[AgentType, AgentOutput] = {}

        # Researcher first
        await self._update_status(ExecutionPhase.RESEARCH_DESIGN, 25.0, "researcher")
        researcher = AgentFactory.create(
            AgentType.RESEARCHER,
            self.db,
            context,
            self._context_board,
        )
        researcher_output = await researcher.execute()
        outputs[AgentType.RESEARCHER] = researcher_output
        context.previous_outputs[AgentType.RESEARCHER] = researcher_output

        # Then Designer
        await self._update_status(ExecutionPhase.RESEARCH_DESIGN, 40.0, "designer")
        designer = AgentFactory.create(
            AgentType.DESIGNER,
            self.db,
            context,
            self._context_board,
        )
        designer_output = await designer.execute()
        outputs[AgentType.DESIGNER] = designer_output
        context.previous_outputs[AgentType.DESIGNER] = designer_output

        return outputs

    async def _run_layout_agent(self, context: AgentContext) -> Optional[AgentOutput]:
        """Run Layout Agent"""
        await self._update_status(ExecutionPhase.LAYOUT, 50.0, "layout")

        agent = AgentFactory.create(
            AgentType.LAYOUT,
            self.db,
            context,
            self._context_board,
        )
        output = await agent.execute()
        context.previous_outputs[AgentType.LAYOUT] = output

        return output

    async def _run_code_agent(self, context: AgentContext) -> Optional[AgentOutput]:
        """Run Code Agent for DSL generation"""
        await self._update_status(ExecutionPhase.CODE_GENERATION, 60.0, "code_agent")

        agent = AgentFactory.create(
            AgentType.CODE_AGENT,
            self.db,
            context,
            self._context_board,
        )
        output = await agent.execute()
        context.previous_outputs[AgentType.CODE_AGENT] = output

        return output

    async def _run_assembler_agent(
        self, context: AgentContext
    ) -> Optional[AgentOutput]:
        """Run Assembler Agent"""
        await self._update_status(ExecutionPhase.ASSEMBLY, 75.0, "assembler")

        agent = AgentFactory.create(
            AgentType.ASSEMBLER,
            self.db,
            context,
            self._context_board,
        )
        output = await agent.execute()
        context.previous_outputs[AgentType.ASSEMBLER] = output

        return output

    async def _run_qa_with_loop(
        self, context: AgentContext, max_iterations: int = 3
    ) -> Optional[AgentOutput]:
        """Run QA Agent with reflective loop"""
        await self._update_status(ExecutionPhase.QA, 85.0, "qa")

        for iteration in range(max_iterations):
            agent = AgentFactory.create(
                AgentType.QA,
                self.db,
                context,
                self._context_board,
            )
            output = await agent.execute()

            if output.success and output.output.get("passed", False):
                return output

            # If not passed and not last iteration, trigger regeneration
            if iteration < max_iterations - 1:
                logger.info(
                    "qa_retry",
                    iteration=iteration + 1,
                    score=output.output.get("quality_score", 0),
                )
                # In full implementation, would regenerate problematic slides here

        return output

    async def _run_learning_phase(
        self,
        context: AgentContext,
        qa_result: Optional[AgentOutput],
        config: V7GenerationConfig,
    ) -> tuple:
        """
        Run Phase 7: Self-Learning (Teacher evaluation + lesson extraction).

        Inspired by Hermes Agent's _spawn_background_review():
        - Evaluates the ENTIRE presentation holistically
        - Extracts design lessons for future generations
        - Detects and evolves design patterns
        - Stores everything in Design Memory

        Returns:
            Tuple of (teacher_feedback_dict, lessons_learned_count)
        """
        await self._update_status(ExecutionPhase.LEARNING, 92.0, "teacher")

        try:
            # Initialize learning engine
            if self._learning_engine is None:
                self._learning_engine = LearningEngine(self.db)
                await self._learning_engine.initialize()

            # Build result dict for learning engine
            result_data = {
                "quality_score": qa_result.output.get("quality_score", 0)
                if qa_result
                else 0,
                "quality_passed": qa_result.output.get("passed", False)
                if qa_result
                else False,
                "total_latency_ms": 0,
                "agent_metrics": {},
            }

            # Run the full learning cycle
            feedback = await self._learning_engine.run_post_generation_learning(
                context=context,
                result=result_data,
                context_board=self._context_board,
            )

            teacher_feedback = None
            lessons_count = 0

            if feedback:
                teacher_feedback = {
                    "overall_score": feedback.overall_score,
                    "overall_grade": feedback.overall_grade,
                    "cohesion_score": feedback.cohesion_score,
                    "narrative_flow_score": feedback.narrative_flow_score,
                    "brand_consistency_score": feedback.brand_consistency_score,
                    "style_directives": feedback.style_directives,
                    "anti_patterns": feedback.anti_patterns,
                }
                lessons_count = len(feedback.lessons_learned)

            logger.info(
                "learning_phase_complete",
                task_id=context.task_id,
                lessons=lessons_count,
                teacher_score=feedback.overall_score if feedback else 0,
            )

            return teacher_feedback, lessons_count

        except Exception as e:
            logger.warning(
                "learning_phase_error",
                task_id=context.task_id,
                error=str(e),
            )
            # Learning failures should NOT fail the generation
            return None, 0

    async def _update_status(
        self,
        phase: ExecutionPhase,
        progress: float,
        current_agent: Optional[str] = None,
    ) -> None:
        """Update execution status on Context Board"""
        if self._protocol:
            status = StatusData(
                phase=phase,
                progress_percent=progress,
                current_agent=current_agent,
            )
            await self._protocol.write_status(status, agent="orchestrator")

    def _collect_agent_metrics(
        self, outputs: Dict[str, Optional[AgentOutput]]
    ) -> Dict[str, Any]:
        """Collect metrics from all agent outputs"""
        metrics = {}
        for name, output in outputs.items():
            if output:
                metrics[name] = {
                    "success": output.success,
                    "model_used": output.model_used,
                    "tokens_used": output.tokens_used,
                    "latency_ms": output.latency_ms,
                    "errors": output.errors,
                    "context_board_writes": output.context_board_writes,
                }
        return metrics

    def _build_error_result(
        self,
        message: str,
        errors: List[str],
        start_time: float,
    ) -> V7GenerationResult:
        """Build error result"""
        return V7GenerationResult(
            success=False,
            errors=[message] + errors,
            total_latency_ms=int((time.monotonic() - start_time) * 1000),
        )


# Backwards compatibility alias
SlideGenerationOrchestratorV7 = V7Orchestrator
