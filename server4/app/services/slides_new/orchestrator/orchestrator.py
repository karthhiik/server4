"""
Slide Generation Orchestrator
Runs the agent pipeline and manages execution flow.
"""

import time
from typing import Any, Dict, List, Optional

import structlog

from app.services.slides_new.agents.base import (
    AgentContext,
    AgentOutput,
    AgentType,
    AgentFactory,
)
from app.services.slides_new.templates.engine import TemplateEngine

logger = structlog.get_logger()


class SlideGenerationOrchestrator:
    """
    Orchestrates the slide generation agent pipeline.

    Executes agents in sequence:
    CEO -> Researcher -> Designer -> Assembler -> QA

    If QA fails, can trigger regeneration loop.
    """

    def __init__(self, db, context: AgentContext):
        self.db = db
        self.context = context
        self.agent_outputs: Dict[AgentType, AgentOutput] = {}
        self.start_time = None
        self.end_time = None

    async def run(self) -> Dict[str, Any]:
        """Execute the full pipeline"""
        self.start_time = time.monotonic()

        try:
            # Execute agents in sequence
            await self._run_ceo()
            await self._run_researcher()
            await self._run_designer()
            await self._run_assembler()
            await self._run_qa()

            # Get final result
            qa_output = self.agent_outputs.get(AgentType.QA)

            if qa_output and qa_output.success:
                result = {
                    "success": True,
                    "presentation": qa_output.output.get("presentation"),
                    "quality_score": qa_output.output.get("quality_score"),
                    "quality_passed": qa_output.output.get("passed"),
                    "metrics": self._get_metrics(),
                }
            else:
                result = {
                    "success": False,
                    "error": "QA failed",
                    "quality_score": 0,
                    "quality_passed": False,
                }

            return result

        except Exception as e:
            logger.error("pipeline_error", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "quality_score": 0,
                "quality_passed": False,
            }
        finally:
            self.end_time = time.monotonic()

    async def _run_ceo(self):
        """Run CEO Agent"""
        logger.info("running_agent", agent=AgentType.CEO.value)

        agent = AgentFactory.create(AgentType.CEO, self.db, self.context)
        output = await agent.execute()

        self.agent_outputs[AgentType.CEO] = output
        self.context.previous_outputs[AgentType.CEO] = output

    async def _run_researcher(self):
        """Run Researcher Agent"""
        logger.info("running_agent", agent=AgentType.RESEARCHER.value)

        agent = AgentFactory.create(AgentType.RESEARCHER, self.db, self.context)
        output = await agent.execute()

        self.agent_outputs[AgentType.RESEARCHER] = output
        self.context.previous_outputs[AgentType.RESEARCHER] = output

    async def _run_designer(self):
        """Run Designer Agent"""
        logger.info("running_agent", agent=AgentType.DESIGNER.value)

        agent = AgentFactory.create(AgentType.DESIGNER, self.db, self.context)
        output = await agent.execute()

        self.agent_outputs[AgentType.DESIGNER] = output
        self.context.previous_outputs[AgentType.DESIGNER] = output

    async def _run_assembler(self):
        """Run Assembler Agent"""
        logger.info("running_agent", agent=AgentType.ASSEMBLER.value)

        agent = AgentFactory.create(AgentType.ASSEMBLER, self.db, self.context)
        output = await agent.execute()

        self.agent_outputs[AgentType.ASSEMBLER] = output
        self.context.previous_outputs[AgentType.ASSEMBLER] = output

    async def _run_qa(self):
        """Run QA Agent"""
        logger.info("running_agent", agent=AgentType.QA.value)

        agent = AgentFactory.create(AgentType.QA, self.db, self.context)
        output = await agent.execute()

        self.agent_outputs[AgentType.QA] = output

    def _get_metrics(self) -> Dict[str, Any]:
        """Get pipeline execution metrics"""
        total_time = (
            int((self.end_time - self.start_time) * 1000) if self.end_time else 0
        )

        agent_metrics = {}
        for agent_type, output in self.agent_outputs.items():
            agent_metrics[agent_type.value] = {
                "success": output.success,
                "model_used": output.model_used,
                "tokens_used": output.tokens_used,
                "latency_ms": output.latency_ms,
                "errors": output.errors,
            }

        return {
            "total_time_ms": total_time,
            "agents": agent_metrics,
        }
