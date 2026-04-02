"""
Template filler — fills template placeholders with AI-generated + user-provided content.
"""

import json
import re
from typing import Optional

import structlog

from app.services.llm.model_router import ModelRouter, TaskType
from app.mcp.brain_mcp.prompts.template_system import TEMPLATE_FILL_SYSTEM
from app.mcp.brain_mcp.security.prompt_sanitizer import PromptSanitizer
from app.models.slide import SlideContent

logger = structlog.get_logger()

sanitizer = PromptSanitizer()


class TemplateFiller:
    """Fills template slide placeholders using LLM + user data."""

    def __init__(self):
        self.router = ModelRouter.get_instance()

    async def fill_slide(
        self,
        layout: str,
        title: str,
        ai_instructions: str,
        placeholders: list[dict],
        user_data: dict,
        presentation_id: Optional[str] = None,
    ) -> SlideContent:
        """Fill a single template slide's placeholders."""
        # Pre-fill known user data
        filled = {}
        ai_needed = []

        for ph in placeholders:
            key = ph["key"]
            if key in user_data and user_data[key]:
                filled[key] = sanitizer.sanitize(str(user_data[key]))
            elif ph.get("required", False) or ph.get("ai_fallback", True):
                ai_needed.append(ph)

        # Use LLM to fill remaining placeholders
        if ai_needed:
            ai_filled = await self._ai_fill_placeholders(
                layout=layout,
                title=title,
                ai_instructions=ai_instructions,
                placeholders=ai_needed,
                existing_data=filled,
                presentation_id=presentation_id,
            )
            filled.update(ai_filled)

        # Construct SlideContent from filled placeholders
        return self._build_slide_content(layout, title, filled)

    async def _ai_fill_placeholders(
        self,
        layout: str,
        title: str,
        ai_instructions: str,
        placeholders: list[dict],
        existing_data: dict,
        presentation_id: Optional[str] = None,
    ) -> dict:
        """Use LLM to generate content for unfilled placeholders."""
        placeholder_desc = "\n".join(
            f"- {ph['key']}: {ph.get('description', ph['key'])} (type: {ph.get('type', 'text')})"
            for ph in placeholders
        )

        user_prompt = f"""Fill these template placeholders for a "{layout}" slide titled "{title}":

Placeholders to fill:
{placeholder_desc}

Already provided data:
{json.dumps(existing_data, indent=2) if existing_data else "None"}

AI Instructions: {ai_instructions}

Return JSON with keys matching the placeholder keys above."""

        messages = [
            {"role": "system", "content": TEMPLATE_FILL_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

        response = await self.router.complete(
            task_type=TaskType.TEMPLATE_FILL,
            messages=messages,
            temperature=0.5,
            max_tokens=2048,
            presentation_id=presentation_id,
            phase="template_fill",
        )

        return self._parse_filled(response.content)

    def _parse_filled(self, raw: str) -> dict:
        """Parse LLM response into filled placeholder dict."""
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
                return json.loads(text[start:end])
            return {}

    def _build_slide_content(self, layout: str, title: str, data: dict) -> SlideContent:
        """Build SlideContent from filled placeholder data."""
        return SlideContent(
            title=data.get("title", title),
            subtitle=data.get("subtitle"),
            body_text=data.get("body_text"),
            bullets=data.get("bullets"),
            left_content=data.get("left_content"),
            right_content=data.get("right_content"),
            left_label=data.get("left_label"),
            right_label=data.get("right_label"),
            left_items=data.get("left_items"),
            right_items=data.get("right_items"),
            image_prompt=data.get("image_prompt"),
            chart_type=data.get("chart_type"),
            chart_data=data.get("chart_data"),
            source_attribution=data.get("source_attribution"),
            events=data.get("events"),
            quote_text=data.get("quote_text"),
            quote_author=data.get("quote_author"),
            quote_role=data.get("quote_role"),
            members=data.get("members"),
            metrics=data.get("metrics"),
        )
