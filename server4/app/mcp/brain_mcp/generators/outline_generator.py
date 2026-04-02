"""
Outline generator — creates structured presentation outlines using LLM.
Uses Kimi-K2-Thinking (T0) for planning, falls back through routing chain.
Now powered by PromptEngine for style-aware, investor-grade outlines.
"""

import json
from typing import Optional

import structlog

from app.services.llm.model_router import ModelRouter, TaskType
from app.mcp.brain_mcp.prompts.outline_system import OUTLINE_USER_TEMPLATE
from app.mcp.brain_mcp.prompts.prompt_engine import PromptEngine
from app.mcp.brain_mcp.security.prompt_sanitizer import PromptSanitizer
from app.models.content import PresentationOutline, OutlineSlide

logger = structlog.get_logger()

sanitizer = PromptSanitizer()


class OutlineGenerator:
    """Generates presentation outlines from topic + research context."""

    def __init__(self):
        self.router = ModelRouter.get_instance()
        self.prompt_engine = PromptEngine()

    async def generate_outline(
        self,
        topic: str,
        audience: str = "general",
        purpose: str = "pitch",
        slide_count: int = 10,
        language: str = "English",
        research_context: str = "",
        additional_notes: str = "",
        writing_style: str = "yc_pitch",
        presentation_id: Optional[str] = None,
    ) -> PresentationOutline:
        """Generate a structured outline with narrative arc."""
        safe_topic = sanitizer.sanitize(topic)
        safe_notes = sanitizer.sanitize(additional_notes) if additional_notes else ""

        # Compose system prompt with style + domain layers
        system_prompt = self.prompt_engine.compose_outline_prompt(
            style=writing_style,
            purpose=purpose,
        )

        user_prompt = OUTLINE_USER_TEMPLATE.format(
            slide_count=slide_count,
            topic=safe_topic,
            audience=audience,
            purpose=purpose,
            language=language,
            research_context=research_context[:3000],
            additional_notes=safe_notes,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await self.router.complete(
            task_type=TaskType.OUTLINE_PLANNING,
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
            presentation_id=presentation_id,
            phase="outline",
        )

        outline = self._parse_outline(response.content, slide_count)
        logger.info("outline_generated", slides=len(outline.slides), model=response.model, style=writing_style)
        return outline

    def _parse_outline(self, raw: str, expected_count: int) -> PresentationOutline:
        """Parse LLM response into structured outline."""
        # Strip markdown fences if present
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
            else:
                raise ValueError("Could not parse outline JSON from LLM response")

        slides_data = data.get("slides", [])
        slides = []
        for s in slides_data[:expected_count]:
            slides.append(OutlineSlide(
                title=s.get("title", "Untitled"),
                purpose=s.get("purpose", ""),
                suggested_layout=s.get("suggested_layout", "bullets"),
                content_hints=s.get("content_hints", ""),
                needs_research=s.get("needs_research", False),
                needs_chart=s.get("needs_chart", False),
                needs_image=s.get("needs_image", False),
            ))

        return PresentationOutline(slides=slides)
