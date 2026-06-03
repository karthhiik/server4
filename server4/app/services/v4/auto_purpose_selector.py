"""Auto Purpose Selector for Standard Mode.

This module uses AI to automatically detect the most appropriate purpose
from a user's prompt, with confidence scoring for reliability.
"""

from __future__ import annotations

from typing import Optional, Tuple

import structlog

from app.services.llm.model_router import ModelRouter
from app.services.v4.purpose_configs import PURPOSE_CONFIGS

logger = structlog.get_logger(__name__)


class AutoPurposeSelector:
    """Automatically selects the best purpose from a user prompt."""

    def __init__(self) -> None:
        """Initialize the auto purpose selector."""
        self.model_router = ModelRouter()
        self._purpose_keywords = self._build_keyword_mapping()

    def _build_keyword_mapping(self) -> dict[str, list[str]]:
        """Build a keyword-to-purpose mapping for fast initial filtering."""
        return {
            "deep_tech": [
                "api", "infrastructure", "architecture", "technical", "developer",
                "engine", "platform", "sdk", "gateway", "low-latency",
                "latency", "idempotent", "circuit breaker", "circuit breakers",
                "zero-trust", "zero knowledge", "edge computing",
            ],
            "vc_pitch": ["raise", "fundraising", "investment", "venture", "series", "investor", "round"],
            "executive_brief": ["executive", "board", "summary", "report", "strategic", "management"],
            "trust_compliance": ["security", "compliance", "gdpr", "hipaa", "certification", "audit", "trust"],
            "cinematic_keynote": ["keynote", "vision", "inspire", "story", "emotional", "future"],
            "seed_round": ["seed", "angel", "pre-seed", "early stage", "idea", "founder"],
            "series_a": ["series a", "growth", "traction", "scale", "metrics", "unit economics"],
            "partnership": ["partnership", "integration", "collaborate", "joint venture", "alliance"],
            "customer_case": ["case study", "testimonial", "customer success", "client", "result"],
            "fundraising_roadshow": ["roadshow", "fundraising tour", "investor meetings", "pitch tour"],
            "growth_deck": ["growth", "optimization", "funnel", "retention", "acquisition", "experiment"],
            "market_analysis": ["market research", "analysis", "trends", "landscape", "market size"],
            "competitive_analysis": ["competitive", "positioning", "differentiation", "vs", "comparison"],
            "team_deck": ["team", "founders", "leadership", "advisors", "talent", "hiring"],
            "financial_projection": ["financial", "projection", "revenue", "expenses", "forecast", "budget"],
            "product_roadmap": ["roadmap", "product plan", "timeline", "features", "milestones"],
            "milestone_deck": ["milestone", "achievement", "launched", "shipped", "completed"],
            "crisis_management": ["crisis", "response", "incident", "issue", "transparency", "remediation"],
            "expansion_plan": ["expansion", "international", "geographic", "new market", "global"],
            "advisory_board": ["advisory", "advisor", "board", "guidance", "strategic"],
            "strategic_partnership": ["strategic partnership", "enterprise", "alliance", "integration"],
            "pre_seed_pitch": ["pre-seed", "idea", "concept", "validation", "prototype"],
        }

    def _keyword_match(self, prompt: str, available_purposes: list[str]) -> list[Tuple[str, float]]:
        """Fast keyword-based matching as initial filter."""
        prompt_lower = prompt.lower()
        matches = []

        for purpose, keywords in self._purpose_keywords.items():
            if purpose not in available_purposes:
                continue

            match_count = sum(1 for keyword in keywords if keyword in prompt_lower)
            if match_count > 0:
                # Normalize score based on number of keywords matched
                score = min(match_count / len(keywords), 1.0)
                matches.append((purpose, score))

        return sorted(matches, key=lambda x: x[1], reverse=True)

    async def select_purpose(
        self,
        prompt: str,
        available_purposes: list[str],
    ) -> Tuple[str, float]:
        """Select the best purpose for the given prompt.

        Args:
            prompt: User's input prompt
            available_purposes: List of purpose IDs to choose from

        Returns:
            Tuple of (purpose_id, confidence_score) where confidence is 0.0-1.0
        """
        # Step 1: Fast keyword matching
        keyword_matches = self._keyword_match(prompt, available_purposes)

        # Step 2: If we have a useful keyword match, use it. This keeps
        # standard mode fast and avoids routing obvious technical prompts
        # through an LLM classifier.
        if keyword_matches and keyword_matches[0][1] >= 0.2:
            purpose, confidence = keyword_matches[0]
            logger.info(
                "auto_purpose_keyword_match",
                purpose=purpose,
                confidence=confidence,
                prompt_length=len(prompt),
            )
            return purpose, confidence

        # Step 3: Otherwise, use LLM for semantic understanding
        return await self._llm_purpose_selection(prompt, available_purposes)

    async def _llm_purpose_selection(
        self,
        prompt: str,
        available_purposes: list[str],
    ) -> Tuple[str, float]:
        """Use LLM for semantic purpose selection.

        This is more accurate but slower than keyword matching.
        """
        # Build purpose descriptions for the LLM
        purpose_descriptions = []
        for purpose_id in available_purposes:
            config = PURPOSE_CONFIGS.get(purpose_id)
            if config:
                desc = f"{config.website_label}: {config.content_tone}, {config.focus_area}"
                purpose_descriptions.append(f"{purpose_id}: {desc}")
            else:
                purpose_descriptions.append(purpose_id)

        purpose_list = "\n".join(purpose_descriptions)

        system_prompt = """You are an expert at understanding presentation purposes. 
Analyze the user's prompt and select the most appropriate presentation purpose from the list.
Respond with the purpose ID and a confidence score (0.0-1.0) in the format: PURPOSE_ID|CONFIDENCE"""

        user_prompt = f"""User Prompt: {prompt}

Available Purposes:
{purpose_list}

Select the best purpose and return in format: PURPOSE_ID|CONFIDENCE"""

        try:
            from app.services.llm.model_router import TaskType
            from app.services.v4.llm_safe import safe_complete

            # Use INTENT_CLASSIFICATION task type for purpose selection
            llm_response = await safe_complete(
                router=self.model_router,
                primary_task=TaskType.INTENT_CLASSIFICATION,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                timeout_s=15.0,
                phase="v4_auto_purpose_selection",
                mode="standard",
            )

            # Extract content from LLMResponse
            response = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)

            # Parse response
            if "|" in response:
                purpose, confidence_str = response.strip().split("|", 1)
                try:
                    confidence = float(confidence_str.strip())
                    confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
                except ValueError:
                    confidence = 0.5  # Default confidence if parsing fails
            else:
                # Fallback: extract first purpose ID from response
                for purpose_id in available_purposes:
                    if purpose_id in response.lower():
                        purpose = purpose_id
                        confidence = 0.7
                        break
                else:
                    # Ultimate fallback: use first available purpose
                    purpose = available_purposes[0] if available_purposes else "vc_pitch"
                    confidence = 0.3

            logger.info(
                "auto_purpose_llm_match",
                purpose=purpose,
                confidence=confidence,
                prompt_length=len(prompt),
            )

            return purpose, confidence

        except Exception as e:
            logger.error(
                "auto_purpose_llm_error",
                error=str(e),
                prompt_length=len(prompt),
            )
            # Fallback to keyword matches or default
            if keyword_matches := self._keyword_match(prompt, available_purposes):
                return keyword_matches[0]
            # Ultimate fallback
            return available_purposes[0] if available_purposes else "vc_pitch", 0.2


__all__ = ["AutoPurposeSelector"]
