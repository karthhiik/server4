"""Title Extractor for Standard Mode.

This module extracts a professional, concise title from the user's prompt
that is appropriate for the selected presentation purpose.
"""

from __future__ import annotations

import re
from typing import Optional

import structlog

from app.services.llm.model_router import ModelRouter

logger = structlog.get_logger(__name__)


class TitleExtractor:
    """Extracts professional titles from user prompts."""

    def __init__(self) -> None:
        """Initialize the title extractor."""
        self.model_router = ModelRouter()

    def _extract_company_name(self, prompt: str) -> Optional[str]:
        """Extract company name from prompt using heuristics."""
        # Look for patterns like "MyCompany" or "my company"
        patterns = [
            r'(?:my|our|the)\s+(?:company|startup|business)\s+is\s+([A-Z][a-zA-Z\s]+)',
            r'(?:my|our|the)\s+([A-Z][a-zA-Z]+)\s+(?:company|startup|business)',
            r'building\s+([A-Z][a-zA-Z]+)',
            r'founded\s+([A-Z][a-zA-Z]+)',
            r'called\s+([A-Z][a-zA-Z]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_explicit_topic(self, prompt: str) -> Optional[str]:
        """Extract a user-provided topic/title without an LLM call.

        Real-time form prompts commonly arrive as:
        "Presentation Topic: ... Description: ... Target Audience: ..."
        This is authoritative user input, so using the LLM here is both
        slower and less accurate.
        """
        if not prompt:
            return None

        label_re = (
            r"(?:presentation\s+topic|topic|title)\s*:\s*"
            r"(.+?)"
            r"(?=(?:\s*[\.\n]\s*)?"
            r"(?:description|target\s+audience|audience|purpose|slide\s+count)\s*:|$)"
        )
        match = re.search(label_re, prompt, re.IGNORECASE | re.DOTALL)
        if not match:
            return None

        title = match.group(1).strip()
        title = re.sub(r"\$([^$]+)\$", r"\1", title)
        title = re.sub(r"\s+", " ", title).strip(" .:-")
        title = title.strip('"').strip("'")
        if not title:
            return None

        if len(title) > 70:
            title = title[:70].rsplit(" ", 1)[0]
        return title or None

    def _extract_key_topic(self, prompt: str, purpose: str) -> str:
        """Extract the main topic/subject from the prompt."""
        # Remove common filler words
        filler_words = {
            "i", "we", "my", "our", "the", "a", "an", "is", "are", "was", "were",
            "building", "creating", "making", "developing", "launching", "starting"
        }

        words = prompt.split()
        content_words = [w for w in words if w.lower() not in filler_words]

        # Take first few meaningful words
        topic_words = content_words[:5]
        topic = " ".join(topic_words)

        # Clean up
        topic = re.sub(r'[^\w\s-]', '', topic)
        topic = " ".join(topic.split())

        return topic[:50]  # Limit to 50 characters

    async def extract_title(
        self,
        prompt: str,
        purpose: str,
    ) -> str:
        """Extract a professional title from the prompt.

        Args:
            prompt: User's input prompt
            purpose: Selected presentation purpose

        Returns:
            Professional title for the presentation
        """
        # Fast path: try heuristic extraction first
        explicit_topic = self._extract_explicit_topic(prompt)
        if explicit_topic:
            logger.info(
                "title_extracted_explicit_topic",
                title=explicit_topic,
                purpose=purpose,
            )
            return explicit_topic

        company_name = self._extract_company_name(prompt)
        if company_name:
            # Build title based on purpose
            purpose_titles = {
                "deep_tech": f"{company_name}: Technical Architecture",
                "vc_pitch": f"{company_name}: Investment Opportunity",
                "executive_brief": f"{company_name}: Executive Summary",
                "trust_compliance": f"{company_name}: Trust & Security",
                "cinematic_keynote": f"{company_name}: Vision",
                "seed_round": f"{company_name}: Seed Round",
                "series_a": f"{company_name}: Series A Growth",
                "partnership": f"{company_name}: Partnership Proposal",
                "customer_case": f"{company_name}: Customer Success",
                "fundraising_roadshow": f"{company_name}: Fundraising Roadshow",
                "growth_deck": f"{company_name}: Growth Strategy",
                "market_analysis": f"{company_name}: Market Analysis",
                "competitive_analysis": f"{company_name}: Competitive Positioning",
                "team_deck": f"{company_name}: Team Overview",
                "financial_projection": f"{company_name}: Financial Projections",
                "product_roadmap": f"{company_name}: Product Roadmap",
                "milestone_deck": f"{company_name}: Milestones",
                "crisis_management": f"{company_name}: Crisis Response",
                "expansion_plan": f"{company_name}: Expansion Strategy",
                "advisory_board": f"{company_name}: Advisory Board",
                "strategic_partnership": f"{company_name}: Strategic Partnership",
                "pre_seed_pitch": f"{company_name}: Pre-Seed Pitch",
            }

            title = purpose_titles.get(purpose, f"{company_name}: Presentation")
            logger.info(
                "title_extracted_heuristic",
                title=title,
                purpose=purpose,
                company_name=company_name,
            )
            return title

        # Fallback: use LLM for semantic title extraction
        return await self._llm_title_extraction(prompt, purpose)

    async def _llm_title_extraction(
        self,
        prompt: str,
        purpose: str,
    ) -> str:
        """Use LLM to extract a professional title.

        This is more accurate but slower than heuristic extraction.
        """
        system_prompt = """You are an expert at creating professional presentation titles.
Extract a concise, professional title (under 50 characters) from the user's prompt.
The title should be appropriate for the presentation purpose.
Return ONLY the title, no explanation or extra text."""

        user_prompt = f"""User Prompt: {prompt}

Presentation Purpose: {purpose}

Create a professional title for this presentation. Return ONLY the title (under 50 characters)."""

        try:
            # Use a fast, capable model for title extraction
            # Use complete() method instead of non-existent generate()
            from app.services.llm.model_router import TaskType
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.model_router.complete(
                task_type=TaskType.TEMPLATE_FILL,
                messages=messages,
                max_tokens=30,
                temperature=0.3,
                phase="v4_title_extraction",
                mode="standard",
            )

            # Clean up response
            title = response.content.strip().strip('"').strip("'")

            # Ensure it's not too long
            if len(title) > 50:
                title = title[:50].rsplit(" ", 1)[0]

            # Fallback if title is empty
            if not title:
                title = self._extract_key_topic(prompt, purpose)

            logger.info(
                "title_extracted_llm",
                title=title,
                purpose=purpose,
            )

            return title

        except Exception as e:
            logger.error(
                "title_extraction_llm_error",
                error=str(e),
                prompt_length=len(prompt),
                purpose=purpose,
            )
            # Ultimate fallback
            return self._extract_key_topic(prompt, purpose)


__all__ = ["TitleExtractor"]
