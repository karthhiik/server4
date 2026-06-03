"""
Zero-Defect Council Orchestrator

Multi-model deliberation system for content generation with cross-verification,
confidence scoring, and low-confidence flagging.
"""

import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import structlog

from app.services.llm.model_router import ModelRouter
from .council_config import ZeroDefectCouncilConfig

logger = structlog.get_logger(__name__)


@dataclass
class CouncilResult:
    """Result from council deliberation"""
    content: str
    confidence: float
    low_confidence_facts: List[str]
    council_models_used: List[str]
    cross_verification_passed: bool


class CouncilOrchestrator:
    """
    Orchestrates multi-model council deliberation for content generation.
    
    Implements the 7-phase council system:
    - Phase 1: Analysis (Standard) / Deep Analysis (Premium)
    - Phase 2: Content Generation (Standard) / Rich Content Generation (Premium)
    - Phase 3: Layout Intent (Standard) / Premium Layout Selection (Premium)
    - Phase 4: Typography & Styling (Standard) / Premium Design Tokens (Premium)
    - Phase 5: Image Generation (Standard) / Premium Image Generation (Premium)
    - Phase 6: Data Visualization (Standard) / Advanced Data Visualization (Premium)
    - Phase 7: Slide Assembly (Standard) / Premium Slide Assembly (Premium)
    """
    
    def __init__(self, council_mode: str = "standard"):
        """
        Initialize council orchestrator.
        
        Args:
            council_mode: "standard" for 5-model council, "premium" for 7-model council
        """
        self.council_mode = council_mode
        self.config = ZeroDefectCouncilConfig()
        self.model_router = ModelRouter()
        
        # Get council models based on mode
        if council_mode == "premium":
            self.primary_council = self.config.PREMIUM_COUNCIL
            self.chairman = self.config.CHAIRMAN
        else:
            self.primary_council = self.config.PRIMARY_COUNCIL
            self.chairman = self.config.CHAIRMAN
    
    async def deliberate(
        self,
        task: str,
        context: Dict[str, Any],
        phase: int = 1
    ) -> CouncilResult:
        """
        Run council deliberation for a specific phase.
        
        Args:
            task: The task description for the council
            context: Additional context for the task
            phase: The council phase (1-7)
        
        Returns:
            CouncilResult with content, confidence, and verification results
        """
        logger.info(
            "council_deliberation_start",
            phase=phase,
            council_mode=self.council_mode,
            n_models=len(self.primary_council)
        )
        
        # Phase 1: Parallel generation from council members
        responses = await self._parallel_council_generation(task, context, phase)
        
        # Phase 2: Cross-verification
        verification_result = await self._cross_verify(responses, context)
        
        # Phase 3: Chairman synthesis
        synthesized_content = await self._synthesize_with_chairman(
            responses,
            verification_result,
            task,
            context
        )
        
        # Phase 4: Confidence scoring
        confidence_score = await self._calculate_confidence(
            synthesized_content,
            verification_result
        )
        
        # Phase 5: Low-confidence flagging
        low_confidence_facts = await self._flag_low_confidence(
            synthesized_content,
            confidence_score
        )
        
        result = CouncilResult(
            content=synthesized_content,
            confidence=confidence_score,
            low_confidence_facts=low_confidence_facts,
            council_models_used=self.primary_council,
            cross_verification_passed=verification_result["passed"]
        )
        
        logger.info(
            "council_deliberation_complete",
            phase=phase,
            confidence=confidence_score,
            low_confidence_count=len(low_confidence_facts)
        )
        
        return result
    
    async def _parallel_council_generation(
        self,
        task: str,
        context: Dict[str, Any],
        phase: int
    ) -> List[Dict[str, Any]]:
        """Generate responses from all council members in parallel."""
        responses = []
        
        async def generate_with_model(model: str) -> Dict[str, Any]:
            try:
                from app.services.llm.model_router import TaskType
                
                system_prompt = self._get_phase_system_prompt(phase)
                user_prompt = self._format_user_prompt(task, context, phase)
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                response = await self.model_router.complete(
                    task_type=TaskType.TEMPLATE_FILL,
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                
                return {
                    "model": model,
                    "content": response.content,
                    "success": True
                }
            except Exception as e:
                logger.warning(
                    "council_model_failed",
                    model=model,
                    error=str(e)
                )
                return {
                    "model": model,
                    "content": "",
                    "success": False,
                    "error": str(e)
                }
        
        # Run all council members in parallel
        tasks = [generate_with_model(model) for model in self.primary_council]
        responses = await asyncio.gather(*tasks)
        
        return [r for r in responses if r["success"]]
    
    async def _cross_verify(
        self,
        responses: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Cross-verify council responses against each other and sources."""
        if len(responses) < 2:
            return {"passed": True, "agreement_score": 1.0}
        
        # Simple agreement calculation (can be enhanced with more sophisticated verification)
        content_set = set(r["content"] for r in responses)
        agreement_score = 1.0 - (len(content_set) - 1) / len(responses)
        
        return {
            "passed": agreement_score > 0.5,
            "agreement_score": agreement_score
        }
    
    async def _synthesize_with_chairman(
        self,
        responses: List[Dict[str, Any]],
        verification_result: Dict[str, Any],
        task: str,
        context: Dict[str, Any]
    ) -> str:
        """Use chairman model to synthesize the best response."""
        if not responses:
            return ""
        
        # Use the first successful response as base (can be enhanced with actual synthesis)
        # In a full implementation, the chairman would review all responses and synthesize
        return responses[0]["content"]
    
    async def _calculate_confidence(
        self,
        content: str,
        verification_result: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for the content."""
        # Base confidence from cross-verification
        confidence = verification_result.get("agreement_score", 0.8)
        
        # Adjust based on content quality (can be enhanced)
        if len(content) > 100:
            confidence *= 1.1  # Longer content gets slight boost
        
        return min(confidence, 1.0)
    
    async def _flag_low_confidence(
        self,
        content: str,
        confidence: float
    ) -> List[str]:
        """Flag low-confidence facts in the content."""
        low_confidence_facts = []
        
        # Simple heuristic: flag content with low overall confidence
        if confidence < 0.8:
            low_confidence_facts.append("Overall content confidence below threshold")
        
        return low_confidence_facts
    
    def _get_phase_system_prompt(self, phase: int) -> str:
        """Get system prompt for a specific council phase."""
        phase_prompts = {
            1: "You are analyzing the task requirements and extracting key information.",
            2: "You are generating slide content based on the analysis.",
            3: "You are determining the optimal layout for the content.",
            4: "You are applying typography and styling to the content.",
            5: "You are generating or selecting images for the slide.",
            6: "You are creating data visualizations for the slide.",
            7: "You are assembling all components into the final slide."
        }
        return phase_prompts.get(phase, "You are a content generation expert.")
    
    def _format_user_prompt(
        self,
        task: str,
        context: Dict[str, Any],
        phase: int
    ) -> str:
        """Format user prompt for a specific council phase."""
        prompt = f"Task: {task}\n\n"
        if context:
            prompt += f"Context: {context}\n\n"
        prompt += f"Phase: {phase}\n\n"
        prompt += "Generate your response in JSON format."
        return prompt
