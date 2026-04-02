"""
Narrative checker — validates presentation flow and coherence.
"""

import json
from typing import Optional

import structlog

from app.services.llm.model_router import ModelRouter, TaskType

logger = structlog.get_logger()


class NarrativeChecker:
    """Checks narrative coherence across all slides in a presentation."""

    def __init__(self):
        self.router = ModelRouter.get_instance()

    async def check_narrative(
        self,
        slides: list[dict],
        topic: str,
        audience: str = "general",
        presentation_id: Optional[str] = None,
    ) -> dict:
        """Analyze narrative flow and suggest improvements."""
        slides_summary = "\n".join(
            f"Slide {i+1} [{s.get('layout', '?')}]: {s.get('title', 'Untitled')}"
            for i, s in enumerate(slides)
        )

        user_prompt = f"""Analyze the narrative flow of this {len(slides)}-slide presentation:

Topic: {topic}
Audience: {audience}

Slides:
{slides_summary}

Evaluate:
1. Does it follow a clear narrative arc (Hook → Problem → Solution → Evidence → Ask)?
2. Are there redundant slides?
3. Are any key sections missing?
4. Is the ordering logical?
5. Does the ending have a clear call-to-action?

Return JSON:
{{
  "score": 1-10,
  "has_clear_arc": true/false,
  "missing_sections": ["section name", ...],
  "redundant_slides": [slide_numbers],
  "reorder_suggestions": [
    {{"from": slide_num, "to": suggested_position, "reason": "..."}}
  ],
  "overall_feedback": "1-2 sentence summary"
}}"""

        messages = [
            {"role": "system", "content": "You are a presentation narrative expert. Analyze slide flow and suggest improvements. Return valid JSON only."},
            {"role": "user", "content": user_prompt},
        ]

        response = await self.router.complete(
            task_type=TaskType.OUTLINE_PLANNING,
            messages=messages,
            temperature=0.4,
            max_tokens=1024,
            presentation_id=presentation_id,
            phase="narrative_check",
        )

        return self._parse_feedback(response.content)

    def _parse_feedback(self, raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
        return {"score": 5, "overall_feedback": "Could not analyze narrative.", "has_clear_arc": False}
