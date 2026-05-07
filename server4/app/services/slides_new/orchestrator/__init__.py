"""
Orchestrator Module — V7 Phase 2
"""

from app.services.slides_new.orchestrator.orchestrator import (
    SlideGenerationOrchestrator,
)

# V7 Phase 2 additions
from app.services.slides_new.orchestrator.v7_orchestrator import (
    V7Orchestrator,
    V7GenerationConfig,
    V7GenerationResult,
    SlideGenerationOrchestratorV7,
)
from app.services.slides_new.orchestrator.parallel_runner import (
    ParallelExecutor,
    PipelineOrchestrator,
    ExecutionPlan,
    AgentTask,
    ExecutionMode,
)

__all__ = [
    # Legacy
    "SlideGenerationOrchestrator",
    # V7 Phase 2
    "V7Orchestrator",
    "V7GenerationConfig",
    "V7GenerationResult",
    "SlideGenerationOrchestratorV7",
    "ParallelExecutor",
    "PipelineOrchestrator",
    "ExecutionPlan",
    "AgentTask",
    "ExecutionMode",
]
