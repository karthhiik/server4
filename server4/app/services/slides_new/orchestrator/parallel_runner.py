"""
Parallel Execution Framework — V7 Phase 2
Manages concurrent execution of agents with proper dependency handling.

Features:
- Parallel execution of independent agents (Researcher + Designer)
- Dependency-based sequential execution
- Error handling and partial failure recovery
- Progress tracking via Context Board
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

import structlog

from app.services.slides_new.agents.base import (
    AgentType,
    AgentContext,
    AgentOutput,
    AgentFactory,
    BaseAgent,
)
from app.services.slides_new.agents.protocols import (
    ExecutionPhase,
    StatusData,
    ContextBoardProtocol,
    ParallelExecutionResult,
    AgentResult,
)

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase
    from app.services.context_board import ContextBoard

logger = structlog.get_logger()


class ExecutionMode(str, Enum):
    """Agent execution modes"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


@dataclass
class AgentTask:
    """Represents a task to be executed"""
    agent_type: AgentType
    dependencies: Set[AgentType] = field(default_factory=set)
    mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    timeout_seconds: int = 120
    required: bool = True  # If False, failure doesn't stop pipeline


@dataclass
class ExecutionPlan:
    """Defines the execution order for agents"""
    phases: List[List[AgentTask]]  # Each inner list runs in parallel

    @classmethod
    def get_v7_plan(cls) -> "ExecutionPlan":
        """
        V7 execution plan following the architecture:
        Phase 1: CEO (sequential)
        Phase 2: Researcher + Designer (parallel)
        Phase 3: Layout (sequential, depends on Phase 2)
        Phase 4: Code Agent (sequential, depends on Layout)
        Phase 5: Assembly (sequential)
        Phase 6: QA (sequential, iterative)
        """
        return cls(phases=[
            # Phase 1: Strategy
            [AgentTask(AgentType.CEO, required=True)],

            # Phase 2: Research + Design (parallel)
            [
                AgentTask(
                    AgentType.RESEARCHER,
                    dependencies={AgentType.CEO},
                    mode=ExecutionMode.PARALLEL,
                ),
                AgentTask(
                    AgentType.DESIGNER,
                    dependencies={AgentType.CEO},
                    mode=ExecutionMode.PARALLEL,
                ),
            ],

            # Phase 3: Layout
            [
                AgentTask(
                    AgentType.LAYOUT,
                    dependencies={AgentType.CEO, AgentType.RESEARCHER},
                ),
            ],

            # Phase 4: Code Generation
            [
                AgentTask(
                    AgentType.CODE_AGENT,
                    dependencies={AgentType.LAYOUT, AgentType.DESIGNER},
                ),
            ],

            # Phase 5: Assembly
            [
                AgentTask(
                    AgentType.ASSEMBLER,
                    dependencies={AgentType.CODE_AGENT},
                ),
            ],

            # Phase 6: QA
            [
                AgentTask(
                    AgentType.QA,
                    dependencies={AgentType.ASSEMBLER},
                ),
            ],
        ])


class ParallelExecutor:
    """
    Executes agents with support for parallel and sequential modes.

    Usage:
        executor = ParallelExecutor(db, context, context_board)
        results = await executor.run_phase([task1, task2])  # Parallel
    """

    def __init__(
        self,
        db: "AsyncIOMotorDatabase",
        context: AgentContext,
        context_board: Optional["ContextBoard"] = None,
    ):
        self.db = db
        self.context = context
        self.context_board = context_board
        self._protocol: Optional[ContextBoardProtocol] = None
        self._completed_agents: Set[AgentType] = set()
        self._agent_results: Dict[AgentType, AgentOutput] = {}

    @property
    def protocol(self) -> Optional[ContextBoardProtocol]:
        """Get the Context Board Protocol helper"""
        if self._protocol is None and self.context_board is not None:
            self._protocol = ContextBoardProtocol(self.context_board)
        return self._protocol

    async def run_phase(
        self, tasks: List[AgentTask]
    ) -> ParallelExecutionResult:
        """
        Execute a phase of tasks (may be parallel or sequential).

        Args:
            tasks: List of agent tasks to execute

        Returns:
            ParallelExecutionResult with outcomes for all tasks
        """
        start_time = time.monotonic()

        # Check if all tasks have their dependencies met
        for task in tasks:
            unmet = task.dependencies - self._completed_agents
            if unmet:
                logger.error(
                    "unmet_dependencies",
                    agent=task.agent_type.value,
                    missing=[a.value for a in unmet],
                )
                return ParallelExecutionResult(
                    success=False,
                    completed_agents=[],
                    failed_agents=[task.agent_type.value],
                    results={},
                    total_latency_ms=0,
                )

        # Determine execution mode
        if len(tasks) == 1 or all(t.mode == ExecutionMode.SEQUENTIAL for t in tasks):
            # Sequential execution
            results = await self._run_sequential(tasks)
        else:
            # Parallel execution
            results = await self._run_parallel(tasks)

        # Calculate total latency
        total_latency = int((time.monotonic() - start_time) * 1000)

        # Build result
        completed = [
            agent_type.value
            for agent_type, output in results.items()
            if output.success
        ]
        failed = [
            agent_type.value
            for agent_type, output in results.items()
            if not output.success
        ]

        # Convert to AgentResult format
        agent_results = {
            agent_type.value: AgentResult(
                success=output.success,
                agent_name=agent_type.value,
                context_board_writes=output.context_board_writes,
                model_used=output.model_used,
                tokens_used=output.tokens_used,
                latency_ms=output.latency_ms,
                errors=output.errors,
                warnings=output.warnings,
                hitl_checkpoint=output.hitl_checkpoint,
            )
            for agent_type, output in results.items()
        }

        return ParallelExecutionResult(
            success=len(failed) == 0,
            completed_agents=completed,
            failed_agents=failed,
            results=agent_results,
            total_latency_ms=total_latency,
        )

    async def _run_sequential(
        self, tasks: List[AgentTask]
    ) -> Dict[AgentType, AgentOutput]:
        """Run tasks sequentially"""
        results: Dict[AgentType, AgentOutput] = {}

        for task in tasks:
            output = await self._execute_single_task(task)
            results[task.agent_type] = output

            if output.success:
                self._completed_agents.add(task.agent_type)
                self._agent_results[task.agent_type] = output
                # Add to context for next agents
                self.context.previous_outputs[task.agent_type] = output
            elif task.required:
                # Stop on required task failure
                logger.error(
                    "required_agent_failed",
                    agent=task.agent_type.value,
                    errors=output.errors,
                )
                break

        return results

    async def _run_parallel(
        self, tasks: List[AgentTask]
    ) -> Dict[AgentType, AgentOutput]:
        """Run tasks in parallel using asyncio.gather"""
        results: Dict[AgentType, AgentOutput] = {}

        # Create coroutines for all tasks
        async def execute_with_tracking(task: AgentTask) -> Tuple[AgentType, AgentOutput]:
            output = await self._execute_single_task(task)
            return task.agent_type, output

        # Execute all in parallel
        coroutines = [execute_with_tracking(task) for task in tasks]
        parallel_results = await asyncio.gather(*coroutines, return_exceptions=True)

        # Process results
        for result in parallel_results:
            if isinstance(result, Exception):
                logger.error("parallel_execution_error", error=str(result))
                continue

            agent_type, output = result
            results[agent_type] = output

            if output.success:
                self._completed_agents.add(agent_type)
                self._agent_results[agent_type] = output
                self.context.previous_outputs[agent_type] = output

        return results

    async def _execute_single_task(self, task: AgentTask) -> AgentOutput:
        """Execute a single agent task with timeout handling"""
        logger.info(
            "executing_agent",
            agent=task.agent_type.value,
            timeout=task.timeout_seconds,
        )

        try:
            # Create agent instance
            agent = AgentFactory.create(
                task.agent_type,
                self.db,
                self.context,
                self.context_board,
            )

            # Execute with timeout
            try:
                output = await asyncio.wait_for(
                    agent.execute(),
                    timeout=task.timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "agent_timeout",
                    agent=task.agent_type.value,
                    timeout=task.timeout_seconds,
                )
                return AgentOutput(
                    success=False,
                    agent_type=task.agent_type,
                    errors=[f"Agent timed out after {task.timeout_seconds}s"],
                )

            logger.info(
                "agent_completed",
                agent=task.agent_type.value,
                success=output.success,
                latency_ms=output.latency_ms,
            )

            return output

        except Exception as e:
            logger.exception(
                "agent_execution_error",
                agent=task.agent_type.value,
                error=str(e),
            )
            return AgentOutput(
                success=False,
                agent_type=task.agent_type,
                errors=[str(e)],
            )

    async def update_status(
        self,
        phase: ExecutionPhase,
        progress: float,
        current_agent: Optional[str] = None,
    ) -> None:
        """Update execution status on Context Board"""
        if self.protocol:
            status = StatusData(
                phase=phase,
                progress_percent=progress,
                current_agent=current_agent,
                agents_completed=[a.value for a in self._completed_agents],
                agents_failed=[],
            )
            await self.protocol.write_status(status, agent="orchestrator")


class PipelineOrchestrator:
    """
    High-level orchestrator that runs the full V7 pipeline.

    Usage:
        orchestrator = PipelineOrchestrator(db, context, context_board)
        result = await orchestrator.run()
    """

    def __init__(
        self,
        db: "AsyncIOMotorDatabase",
        context: AgentContext,
        context_board: Optional["ContextBoard"] = None,
        execution_plan: Optional[ExecutionPlan] = None,
    ):
        self.db = db
        self.context = context
        self.context_board = context_board
        self.plan = execution_plan or ExecutionPlan.get_v7_plan()
        self.executor = ParallelExecutor(db, context, context_board)
        self._phase_results: List[ParallelExecutionResult] = []

    async def run(self) -> Dict[str, Any]:
        """
        Execute the full pipeline according to the execution plan.

        Returns:
            Dict with pipeline results including all agent outputs
        """
        start_time = time.monotonic()
        total_phases = len(self.plan.phases)

        # Initialize status
        await self.executor.update_status(
            ExecutionPhase.INITIALIZING,
            progress=0.0,
        )

        for phase_idx, phase_tasks in enumerate(self.plan.phases):
            # Determine phase name
            phase_name = self._get_phase_name(phase_idx)

            # Update status
            progress = (phase_idx / total_phases) * 100
            await self.executor.update_status(
                self._get_execution_phase(phase_idx),
                progress=progress,
                current_agent=phase_tasks[0].agent_type.value if phase_tasks else None,
            )

            logger.info(
                "starting_phase",
                phase=phase_idx + 1,
                name=phase_name,
                agents=[t.agent_type.value for t in phase_tasks],
            )

            # Execute phase
            result = await self.executor.run_phase(phase_tasks)
            self._phase_results.append(result)

            # Check for HITL checkpoint
            hitl_checkpoint = self._check_hitl_checkpoint(result)
            if hitl_checkpoint and not self.context.fast_mode:
                # Would pause here for user approval in real implementation
                logger.info(
                    "hitl_checkpoint_reached",
                    gate=hitl_checkpoint.get("gate"),
                    phase=phase_idx + 1,
                )

            # Check for failures
            if not result.success:
                # Check if all failures were optional
                all_optional = all(
                    not task.required
                    for task in phase_tasks
                    if task.agent_type.value in result.failed_agents
                )
                if not all_optional:
                    logger.error(
                        "pipeline_failed",
                        phase=phase_idx + 1,
                        failed_agents=result.failed_agents,
                    )
                    return self._build_failure_result(phase_idx, result)

        # Pipeline completed
        total_latency = int((time.monotonic() - start_time) * 1000)

        await self.executor.update_status(
            ExecutionPhase.COMPLETE,
            progress=100.0,
        )

        return self._build_success_result(total_latency)

    def _get_phase_name(self, phase_idx: int) -> str:
        """Get human-readable phase name"""
        names = [
            "Strategy",
            "Research & Design",
            "Layout",
            "Code Generation",
            "Assembly",
            "Quality Assurance",
        ]
        return names[phase_idx] if phase_idx < len(names) else f"Phase {phase_idx + 1}"

    def _get_execution_phase(self, phase_idx: int) -> ExecutionPhase:
        """Get ExecutionPhase enum for phase index"""
        phases = [
            ExecutionPhase.STRATEGY,
            ExecutionPhase.RESEARCH_DESIGN,
            ExecutionPhase.LAYOUT,
            ExecutionPhase.CODE_GENERATION,
            ExecutionPhase.ASSEMBLY,
            ExecutionPhase.QA,
        ]
        return phases[phase_idx] if phase_idx < len(phases) else ExecutionPhase.COMPLETE

    def _check_hitl_checkpoint(
        self, result: ParallelExecutionResult
    ) -> Optional[Dict[str, Any]]:
        """Check if any agent has an HITL checkpoint"""
        for agent_name, agent_result in result.results.items():
            if agent_result.hitl_checkpoint:
                return agent_result.hitl_checkpoint
        return None

    def _build_success_result(self, total_latency: int) -> Dict[str, Any]:
        """Build success result dictionary"""
        all_results = {}
        for phase_result in self._phase_results:
            all_results.update(phase_result.results)

        return {
            "success": True,
            "total_latency_ms": total_latency,
            "phase_count": len(self._phase_results),
            "agents_completed": [
                agent
                for result in self._phase_results
                for agent in result.completed_agents
            ],
            "agent_results": {
                name: result.to_dict()
                for name, result in all_results.items()
            },
        }

    def _build_failure_result(
        self, failed_phase: int, result: ParallelExecutionResult
    ) -> Dict[str, Any]:
        """Build failure result dictionary"""
        return {
            "success": False,
            "failed_phase": failed_phase + 1,
            "failed_agents": result.failed_agents,
            "completed_agents": [
                agent
                for r in self._phase_results
                for agent in r.completed_agents
            ],
            "error": f"Pipeline failed at phase {failed_phase + 1}",
        }
