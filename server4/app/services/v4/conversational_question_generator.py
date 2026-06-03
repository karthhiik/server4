"""Purpose-aware conversational question generator.

This module generates context-specific clarifying questions for Standard Mode
when the user's input is too sparse (richness_score < 0.7). Questions are
purpose-aware and limited to 8 maximum to ensure real-time responsiveness.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import structlog

from app.services.llm.model_router import ModelRouter, TaskType
from app.services.v4.purpose_configs import PURPOSE_CONFIGS
from app.services.v4.llm_safe import safe_complete

logger = structlog.get_logger(__name__)


@dataclass
class Question:
    """A single clarifying question."""

    id: str
    question: str
    question_type: str  # "company", "market", "traction", "team", "financials", "product"
    required: bool = False
    purpose_specific: bool = True


@dataclass
class QuestionResponse:
    """Response from the question generator."""

    questions: List[Question]
    richness_score: float
    should_ask_questions: bool
    reason: str


class ConversationalQuestionGenerator:
    """Generates purpose-aware clarifying questions for sparse inputs."""

    def __init__(self, model_router: Optional[ModelRouter] = None) -> None:
        """Initialize the question generator.

        Args:
            model_router: Optional model router for LLM-based question generation
        """
        self.model_router = model_router or ModelRouter()
        self._richness_threshold = 0.6  # Lowered from 0.7 to be more lenient
        self._max_questions = 8

    async def generate_questions(
        self,
        user_input: str,
        purpose: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> QuestionResponse:
        """Generate context-specific questions (max 8).

        Args:
            user_input: User's prompt input
            purpose: Selected presentation purpose
            context: Additional context (research, company data, etc.)

        Returns:
            QuestionResponse with questions and metadata
        """
        context = context or {}

        # Calculate input richness score
        richness_score = self._calculate_richness_score(user_input, context)

        # If input is rich enough, no questions needed
        if richness_score >= self._richness_threshold:
            return QuestionResponse(
                questions=[],
                richness_score=richness_score,
                should_ask_questions=False,
                reason="Input richness score meets threshold",
            )

        # Generate purpose-aware questions
        questions = await self._generate_purpose_questions(
            user_input,
            purpose,
            context,
        )

        # Limit to max 8 questions
        questions = questions[:self._max_questions]

        logger.info(
            "questions_generated",
            purpose=purpose,
            richness_score=richness_score,
            question_count=len(questions),
        )

        return QuestionResponse(
            questions=questions,
            richness_score=richness_score,
            should_ask_questions=len(questions) > 0,
            reason=f"Input richness score {richness_score:.2f} below threshold {self._richness_threshold}",
        )

    def _calculate_richness_score(
        self,
        user_input: str,
        context: Dict[str, Any],
    ) -> float:
        """Calculate input richness score (0-1).

        Higher score = more context available, fewer questions needed.

        Args:
            user_input: User's prompt input
            context: Additional context

        Returns:
            Richness score between 0 and 1
        """
        score = 0.0

        # Base score from input length
        input_length = len(user_input.strip())
        if input_length > 500:
            score += 0.3
        elif input_length > 200:
            score += 0.2
        elif input_length > 100:
            score += 0.1

        # Check for company-specific signals
        company_signals = [
            r"\$[0-9]+[MmKk]",  # Financial metrics
            r"\d+%|percent",  # Percentages
            r"ARR|MRR|revenue",  # Revenue terms
            r"users|customers",  # User metrics
            r"funding|round|series",  # Funding terms
        ]
        for pattern in company_signals:
            if re.search(pattern, user_input, re.IGNORECASE):
                score += 0.1
                break

        # Check for structured context
        if context.get("company_name"):
            score += 0.15
        if context.get("industry"):
            score += 0.1
        if context.get("financials"):
            score += 0.15
        if context.get("team"):
            score += 0.1
        if context.get("competitors"):
            score += 0.1

        # Cap at 1.0
        return min(score, 1.0)

    async def _generate_purpose_questions(
        self,
        user_input: str,
        purpose: str,
        context: Dict[str, Any],
    ) -> List[Question]:
        """Generate purpose-specific questions.

        Args:
            user_input: User's prompt input
            purpose: Selected presentation purpose
            context: Additional context

        Returns:
            List of questions
        """
        config = PURPOSE_CONFIGS.get(purpose)

        # Start with heuristic-based questions based on missing context
        questions = self._generate_heuristic_questions(user_input, purpose, context)

        # If config exists and has high technical depth, add LLM-generated questions
        if config and config.technical_depth == "high":
            llm_questions = await self._generate_llm_questions(
                user_input,
                purpose,
                context,
                config,
            )
            questions.extend(llm_questions)

        return questions

    def _generate_heuristic_questions(
        self,
        user_input: str,
        purpose: str,
        context: Dict[str, Any],
    ) -> List[Question]:
        """Generate heuristic questions based on missing context.

        Args:
            user_input: User's prompt input
            purpose: Selected presentation purpose
            context: Additional context

        Returns:
            List of heuristic questions
        """
        questions: List[Question] = []

        # Check for company name
        if not context.get("company_name"):
            questions.append(
                Question(
                    id="company_name",
                    question="What is your company name?",
                    question_type="company",
                    required=True,
                    purpose_specific=False,
                )
            )

        # Check for industry
        if not context.get("industry"):
            questions.append(
                Question(
                    id="industry",
                    question="What industry or sector does your company operate in?",
                    question_type="market",
                    required=True,
                    purpose_specific=False,
                )
            )

        # Purpose-specific questions
        if purpose in ["vc_pitch", "series_a", "seed_round", "fundraising_roadshow"]:
            if not context.get("financials"):
                questions.append(
                    Question(
                        id="financial_metrics",
                        question="What are your key financial metrics (ARR, MRR, growth rate)?",
                        question_type="financials",
                        required=True,
                        purpose_specific=True,
                    )
                )
            if not context.get("fundraising"):
                questions.append(
                    Question(
                        id="fundraising_amount",
                        question="How much are you raising and for what milestones?",
                        question_type="financials",
                        required=True,
                        purpose_specific=True,
                    )
                )

        if purpose in ["team_deck", "executive_brief"]:
            if not context.get("team"):
                questions.append(
                    Question(
                        id="team_size",
                        question="How many team members do you have and what are their key roles?",
                        question_type="team",
                        required=True,
                        purpose_specific=True,
                    )
                )

        if purpose in ["market_analysis", "competitive_analysis", "growth_deck"]:
            if not context.get("competitors"):
                questions.append(
                    Question(
                        id="competitors",
                        question="Who are your main competitors and what differentiates you?",
                        question_type="market",
                        required=True,
                        purpose_specific=True,
                    )
                )

        if purpose in ["deep_tech", "product_launch", "demo_day"]:
            if not context.get("product"):
                questions.append(
                    Question(
                        id="product_details",
                        question="What are the key technical features or capabilities of your product?",
                        question_type="product",
                        required=True,
                        purpose_specific=True,
                    )
                )

        return questions

    async def _generate_llm_questions(
        self,
        user_input: str,
        purpose: str,
        context: Dict[str, Any],
        config: Any,
    ) -> List[Question]:
        """Generate LLM-based questions for complex purposes.

        Args:
            user_input: User's prompt input
            purpose: Selected presentation purpose
            context: Additional context
            config: Purpose configuration

        Returns:
            List of LLM-generated questions
        """
        try:
            system_prompt = f"""You are a helpful assistant that generates clarifying questions for pitch deck creation.

Purpose: {config.website_label}
Focus: {config.focus_area}
Required Elements: {', '.join(config.required_elements)}

Generate 2-3 specific, concise questions to gather missing information for this purpose.
Each question should be:
- Specific and actionable
- Related to the required elements
- Easy for the user to answer in 1-2 sentences

Return only valid JSON in this format:
{{
  "questions": [
    {{"id": "unique_id", "question": "question text", "type": "question_type"}}
  ]
}}
"""

            user_prompt = f"""User Input: {user_input}

Context:
- Company: {context.get('company_name', 'Not provided')}
- Industry: {context.get('industry', 'Not provided')}
- Financials: {context.get('financials', 'Not provided')}
- Team: {context.get('team', 'Not provided')}
- Competitors: {context.get('competitors', 'Not provided')}

Generate clarifying questions."""

            response = await safe_complete(
                router=self.model_router,
                primary_task=TaskType.QUESTION_GENERATION,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                timeout_s=10.0,
            )

            # Parse response
            import json
            from app.services.v4.json_repair import safe_json_loads, JSONRepairFailedError

            try:
                data = safe_json_loads(response)
                questions_data = data.get("questions", [])

                questions: List[Question] = []
                for q_data in questions_data:
                    questions.append(
                        Question(
                            id=q_data.get("id", f"llm_q_{len(questions)}"),
                            question=q_data.get("question", ""),
                            question_type=q_data.get("type", "general"),
                            required=False,
                            purpose_specific=True,
                        )
                    )

                return questions

            except JSONRepairFailedError:
                logger.warning("llm_question_parse_failed", response=response[:200])
                return []

        except Exception as e:
            logger.error(
                "llm_question_generation_failed",
                purpose=purpose,
                error=str(e)[:200],
                exc_info=True,
            )
            return []


__all__ = [
    "Question",
    "QuestionResponse",
    "ConversationalQuestionGenerator",
]
