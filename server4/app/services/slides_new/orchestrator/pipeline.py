"""
Orchestrator - Slide Generation Pipeline
Coordinates the multi-agent pipeline for slide generation.
"""

import uuid
from typing import Any, Dict, List, Optional

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.slides_new.agents.base import (
    AgentContext,
    AgentOutput,
    AgentType,
    AgentFactory,
)
from app.services.slides_new.orchestrator import SlideGenerationOrchestrator

logger = structlog.get_logger()


class PipelineOrchestrator:
    """
    Orchestrates the multi-agent slide generation pipeline.

    Pipeline flow:
    1. CEO Agent - Strategy & Structure
    2. Researcher Agent - Content Research
    3. Designer Agent - Visual Design
    4. Assembler Agent - Content Assembly
    5. QA Agent - Quality Assurance
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.agents = {}

    async def generate_presentation(
        self,
        topic: str,
        description: str,
        purpose: str,
        audience: str,
        slide_count: Optional[int] = None,
        writing_style: str = "general",
        company_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a complete presentation through the agent pipeline.

        Args:
            topic: Presentation topic
            description: Detailed description
            purpose: Purpose (fundraising, sales, etc.)
            audience: Target audience
            slide_count: Desired slide count
            writing_style: Writing style preference
            company_name: Company name for branding

        Returns:
            Complete presentation with slides and metadata
        """
        task_id = str(uuid.uuid4())

        logger.info("pipeline_start", task_id=topic, purpose=purpose)

        # Create context
        context = AgentContext(
            task_id=task_id,
            user_id="",  # Will be set from auth
            topic=topic,
            description=description,
            purpose=purpose,
            audience=audience,
            slide_count=slide_count or 10,
            mode="generate",
            writing_style=writing_style,
            company_name=company_name,
        )

        # Run pipeline
        orchestrator = SlideGenerationOrchestrator(self.db, context)
        result = await orchestrator.run()

        return result

    async def generate_with_feedback(
        self,
        topic: str,
        description: str,
        purpose: str,
        audience: str,
        max_retries: int = 2,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate presentation with feedback loop.
        If QA fails, regenerate with feedback.
        """
        for attempt in range(max_retries + 1):
            result = await self.generate_presentation(
                topic=topic,
                description=description,
                purpose=purpose,
                audience=audience,
                **kwargs,
            )

            # Check if quality passed
            if result.get("quality_passed", True):
                return result

            if attempt < max_retries:
                logger.info("regeneration_attempt", attempt=attempt + 1)
                # Add feedback for next iteration
                result["feedback"] = result.get("issues", [])

        return result
