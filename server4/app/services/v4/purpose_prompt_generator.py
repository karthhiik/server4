"""Purpose Prompt Generator for Standard Mode.

This module generates purpose-specific prompts for the LLM to ensure
content generation aligns with the selected presentation purpose.
"""

from __future__ import annotations

from typing import Optional

import structlog

from app.services.v4.purpose_configs import PURPOSE_CONFIGS

logger = structlog.get_logger(__name__)


class PurposePromptGenerator:
    """Generates purpose-specific prompts for content generation."""

    def __init__(self) -> None:
        """Initialize the purpose prompt generator."""

    def generate_system_prompt(
        self,
        purpose: str,
        user_prompt: str,
    ) -> str:
        """Generate a purpose-specific system prompt.

        Args:
            purpose: Selected presentation purpose
            user_prompt: User's input prompt

        Returns:
            System prompt tailored to the purpose
        """
        config = PURPOSE_CONFIGS.get(purpose)
        if not config:
            return self._get_default_system_prompt()

        # Build purpose-specific system prompt
        system_prompt = f"""You are an expert presentation writer specializing in {config.website_label}.

CONTENT TONE: {config.content_tone}
NARRATIVE STYLE: {config.narrative_style}
FOCUS AREA: {config.focus_area}
TECHNICAL DEPTH: {config.technical_depth}

VOCABULARY GUIDELINES:
Use these key terms: {', '.join(config.vocabulary_guidelines[:5])}

FORBIDDEN WORDS:
Avoid these words: {', '.join(config.forbidden_words[:3])}

SENTENCE STRUCTURE: {config.sentence_structure}

WORD COUNT LIMIT: {config.word_count_limit if config.word_count_limit else 'No limit'}

REQUIRED ELEMENTS:
{', '.join(config.required_elements)}

Generate content that is {config.content_tone} and focuses on {config.focus_area}.
"""

        logger.info(
            "purpose_system_prompt_generated",
            purpose=purpose,
            tone=config.content_tone,
            focus_area=config.focus_area,
        )

        return system_prompt

    def generate_user_prompt(
        self,
        purpose: str,
        user_prompt: str,
        research_context: Optional[str] = None,
    ) -> str:
        """Generate a purpose-specific user prompt.

        Args:
            purpose: Selected presentation purpose
            user_prompt: User's input prompt
            research_context: Optional research context from research collector

        Returns:
            User prompt with purpose-specific instructions
        """
        config = PURPOSE_CONFIGS.get(purpose)
        if not config:
            return self._get_default_user_prompt(user_prompt, research_context)

        # Build purpose-specific user prompt
        user_instruction = f"""Create a {config.website_label} presentation based on the following:

USER REQUEST: {user_prompt}

PRESENTATION PURPOSE: {purpose}
FOCUS: {config.focus_area}
TONE: {config.content_tone}

"""

        if research_context:
            user_instruction += f"""
RESEARCH CONTEXT:
{research_context}

"""

        user_instruction += f"""
REQUIREMENTS:
- Use {config.vocabulary_guidelines[0]} language
- Focus on {config.focus_area}
- Maintain a {config.content_tone} tone
- Include required elements: {', '.join(config.required_elements)}
- Structure sentences in a {config.sentence_structure} style
"""

        logger.info(
            "purpose_user_prompt_generated",
            purpose=purpose,
            has_research_context=bool(research_context),
        )

        return user_instruction

    def generate_slide_level_prompt(
        self,
        purpose: str,
        slide_type: str,
        slide_number: int,
        total_slides: int,
        research_context: Optional[str] = None,
    ) -> str:
        """Generate a prompt for a specific slide.

        Args:
            purpose: Selected presentation purpose
            slide_type: Type of slide (e.g., "traction", "market_size")
            slide_number: Current slide number
            total_slides: Total number of slides
            research_context: Optional research context

        Returns:
            Slide-specific prompt
        """
        config = PURPOSE_CONFIGS.get(purpose)
        if not config:
            return self._get_default_slide_prompt(slide_type, slide_number, total_slides)

        # Build slide-specific prompt
        slide_instruction = f"""Create slide {slide_number} of {total_slides} for a {config.website_label} presentation.

SLIDE TYPE: {slide_type}
PURPOSE: {purpose}
TONE: {config.content_tone}
FOCUS: {config.focus_area}

"""

        if research_context:
            slide_instruction += f"""
RESEARCH CONTEXT FOR THIS SLIDE:
{research_context}

"""

        slide_instruction += f"""
CONTENT GUIDANCE:
- Use {config.vocabulary_guidelines[0]} language
- Focus on {config.focus_area}
- Maintain a {config.content_tone} tone
- Structure sentences in a {config.sentence_structure} style
"""

        logger.info(
            "purpose_slide_prompt_generated",
            purpose=purpose,
            slide_type=slide_type,
            slide_number=slide_number,
            total_slides=total_slides,
        )

        return slide_instruction

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt when purpose config is not found."""
        return """You are an expert presentation writer.

Create professional, clear, and compelling presentation content.
Focus on the user's specific needs and the presentation purpose.
Use appropriate vocabulary and maintain a professional tone."""

    def _get_default_user_prompt(
        self,
        user_prompt: str,
        research_context: Optional[str] = None,
    ) -> str:
        """Get default user prompt when purpose config is not found."""
        user_instruction = f"""Create a professional presentation based on the following:

USER REQUEST: {user_prompt}

"""

        if research_context:
            user_instruction += f"""
RESEARCH CONTEXT:
{research_context}

"""

        user_instruction += """
Generate clear, professional content that addresses the user's needs.
"""

        return user_instruction

    def _get_default_slide_prompt(
        self,
        slide_type: str,
        slide_number: int,
        total_slides: int,
    ) -> str:
        """Get default slide prompt when purpose config is not found."""
        return f"""Create slide {slide_number} of {total_slides} for the presentation.

SLIDE TYPE: {slide_type}

Generate professional, clear content for this slide.
"""


__all__ = ["PurposePromptGenerator"]
