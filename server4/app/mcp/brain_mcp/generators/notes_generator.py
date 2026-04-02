"""
Speaker notes generator — creates presenter notes for slides.
Now powered by PromptEngine for style-aware notes.
"""

import json
from typing import Optional

import structlog

from app.services.llm.model_router import ModelRouter, TaskType
from app.mcp.brain_mcp.prompts.prompt_engine import PromptEngine

logger = structlog.get_logger()


class NotesGenerator:
    """Generates speaker notes for individual or batch slides."""

    def __init__(self):
        self.router = ModelRouter.get_instance()
        self.prompt_engine = PromptEngine()

    async def generate_notes(
        self,
        slide_title: str,
        slide_content: dict,
        slide_layout: str,
        audience: str = "general",
        writing_style: str = "yc_pitch",
        presentation_purpose: str = "pitch",
        presentation_id: Optional[str] = None,
    ) -> str:
        """Generate speaker notes for a single slide."""
        # Compose system prompt with style + investor psychology layers
        system_prompt = self.prompt_engine.compose_notes_prompt(
            style=writing_style,
            purpose=presentation_purpose,
        )

        user_prompt = f"""Generate speaker notes for this slide:

Title: {slide_title}
Layout: {slide_layout}
Audience: {audience}
Content: {json.dumps(slide_content, default=str)[:1500]}

Write 3-5 sentences of natural speaking notes. Include:
- What to say when this slide appears
- Key points to emphasize
- Transition hint to the next slide"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await self.router.complete(
            task_type=TaskType.TRANSLATION_QUICK_EDIT,
            messages=messages,
            temperature=0.6,
            max_tokens=512,
            presentation_id=presentation_id,
            phase="notes",
        )

        return response.content.strip()

    async def generate_batch_notes(
        self,
        slides: list[dict],
        audience: str = "general",
        presentation_id: Optional[str] = None,
    ) -> list[str]:
        """Generate notes for all slides in one LLM call for efficiency."""
        slides_desc = "\n\n".join(
            f"--- Slide {i+1} ---\nTitle: {s.get('title', 'Untitled')}\n"
            f"Layout: {s.get('layout', 'bullets')}\n"
            f"Content: {json.dumps(s.get('content', {}), default=str)[:500]}"
            for i, s in enumerate(slides)
        )

        user_prompt = f"""Generate speaker notes for ALL {len(slides)} slides below.
Audience: {audience}

{slides_desc}

Return a JSON array of strings, one per slide:
["Notes for slide 1...", "Notes for slide 2...", ...]"""

        messages = [
            {"role": "system", "content": SPEAKER_NOTES_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

        response = await self.router.complete(
            task_type=TaskType.STRUCTURED_JSON,
            messages=messages,
            temperature=0.6,
            max_tokens=4096,
            presentation_id=presentation_id,
            phase="batch_notes",
        )

        return self._parse_batch_notes(response.content, len(slides))

    def _parse_batch_notes(self, raw: str, expected_count: int) -> list[str]:
        """Parse batch notes response."""
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        try:
            notes = json.loads(text)
            if isinstance(notes, list):
                # Pad or trim to expected count
                while len(notes) < expected_count:
                    notes.append("")
                return notes[:expected_count]
        except json.JSONDecodeError:
            pass

        return [""] * expected_count
