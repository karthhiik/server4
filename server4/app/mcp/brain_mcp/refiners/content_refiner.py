"""
Content refiner — rewrites, expands, summarizes, translates, and style-rewrites slide content.
Now powered by PromptEngine for style-aware refinement.
"""

import json
from typing import Optional

import structlog

from app.services.llm.model_router import ModelRouter, TaskType
from app.mcp.brain_mcp.prompts.prompt_engine import PromptEngine
from app.mcp.brain_mcp.prompts.style_system import ContentStyle, get_style_prompt, STYLE_PROMPTS
from app.mcp.brain_mcp.prompts.quality_guards import run_quality_guards
from app.mcp.brain_mcp.security.prompt_sanitizer import PromptSanitizer

logger = structlog.get_logger()

sanitizer = PromptSanitizer()


class ContentRefiner:
    """Refines existing slide content via LLM with style awareness."""

    def __init__(self):
        self.router = ModelRouter.get_instance()
        self.prompt_engine = PromptEngine()

    async def rewrite(
        self,
        content: dict,
        instructions: str,
        presentation_id: Optional[str] = None,
    ) -> dict:
        """Rewrite slide content per user instructions."""
        safe_instructions = sanitizer.sanitize(instructions)
        system_prompt = self.prompt_engine.compose_refine_prompt(action="rewrite")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Current content:\n{json.dumps(content, default=str)}\n\nInstructions: {safe_instructions}\n\nReturn updated JSON."},
        ]

        response = await self.router.complete(
            task_type=TaskType.REFINEMENT,
            messages=messages,
            temperature=0.5,
            max_tokens=2048,
            presentation_id=presentation_id,
            phase="rewrite",
        )
        return self._parse_json(response.content, content)

    async def style_rewrite(
        self,
        content: dict,
        style: str,
        layout: str = "",
        purpose: str = "",
        presentation_id: Optional[str] = None,
    ) -> dict:
        """Rewrite slide content in a specific writing style."""
        # Validate style
        if style not in STYLE_PROMPTS:
            style = ContentStyle.YC_PITCH

        style_prompt = get_style_prompt(style)
        system_prompt = self.prompt_engine.compose_refine_prompt(action="rewrite", style=style)

        user_prompt = f"""Rewrite this slide content in the specified writing style.

Current content:
{json.dumps(content, default=str)}

{"Layout: " + layout if layout else ""}
{"Slide purpose: " + purpose if purpose else ""}

Completely rewrite the content to match the writing style above.
Preserve the JSON field structure. Change the TEXT, not the keys.
Return ONLY valid JSON."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await self.router.complete(
            task_type=TaskType.REFINEMENT,
            messages=messages,
            temperature=0.6,
            max_tokens=2048,
            presentation_id=presentation_id,
            phase="style_rewrite",
        )

        result = self._parse_json(response.content, content)

        # Run quality guards on output
        guard_result = run_quality_guards(
            content=result,
            layout=layout,
            purpose=purpose,
            is_investor_deck=style in (ContentStyle.YC_PITCH, ContentStyle.INVESTOR_UPDATE, ContentStyle.ANALYTICAL),
        )
        if guard_result.fluff_found:
            logger.info("style_rewrite_fluff_detected", style=style, fluff=guard_result.fluff_found)

        return result

    async def expand(
        self,
        content: dict,
        style: Optional[str] = None,
        presentation_id: Optional[str] = None,
    ) -> dict:
        """Expand slide content with more detail."""
        system_prompt = self.prompt_engine.compose_refine_prompt(action="expand", style=style)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Expand this slide content:\n{json.dumps(content, default=str)}\n\nReturn expanded JSON."},
        ]

        response = await self.router.complete(
            task_type=TaskType.REFINEMENT,
            messages=messages,
            temperature=0.6,
            max_tokens=2048,
            presentation_id=presentation_id,
            phase="expand",
        )
        return self._parse_json(response.content, content)

    async def summarize(
        self,
        content: dict,
        style: Optional[str] = None,
        presentation_id: Optional[str] = None,
    ) -> dict:
        """Condense slide content to be more concise."""
        system_prompt = self.prompt_engine.compose_refine_prompt(action="summarize", style=style)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Summarize this slide content:\n{json.dumps(content, default=str)}\n\nReturn condensed JSON."},
        ]

        response = await self.router.complete(
            task_type=TaskType.REFINEMENT,
            messages=messages,
            temperature=0.4,
            max_tokens=1024,
            presentation_id=presentation_id,
            phase="summarize",
        )
        return self._parse_json(response.content, content)

    async def translate(
        self,
        content: dict,
        target_language: str,
        presentation_id: Optional[str] = None,
    ) -> dict:
        """Translate slide content to target language."""
        system_prompt = self.prompt_engine.compose_refine_prompt(action="translate")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Translate to {target_language}:\n{json.dumps(content, default=str)}\n\nReturn translated JSON."},
        ]

        # Use Groq for fast translation
        response = await self.router.complete(
            task_type=TaskType.TRANSLATION_QUICK_EDIT,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
            presentation_id=presentation_id,
            phase="translate",
        )
        return self._parse_json(response.content, content)

    @staticmethod
    def get_available_styles() -> list[dict]:
        """Return list of available writing styles with descriptions."""
        style_descriptions = {
            ContentStyle.YC_PITCH: "YC Demo Day pitch voice. Short, bold, data-backed. Zero fluff.",
            ContentStyle.NARRATIVE: "Story arc structure. Hook → conflict → resolution. Emotional hooks.",
            ContentStyle.DESCRIPTIVE: "Concrete, visual, detail-rich. Makes the audience see it.",
            ContentStyle.PERSUASIVE: "CTA-driven. Social proof, urgency, ROI framing.",
            ContentStyle.ANALYTICAL: "Data-first. Every claim sourced. Charts > words.",
            ContentStyle.CONVERSATIONAL: "Casual, friendly. Like talking to a smart colleague.",
            ContentStyle.EXECUTIVE: "Top-line only. 3 bullets max. Decision-oriented.",
            ContentStyle.TECHNICAL: "Architecture-aware. Precise specs, trade-offs, performance data.",
            ContentStyle.ACADEMIC: "Formal, cited, methodology-driven. Conference-ready.",
            ContentStyle.MINIMALIST: "One idea per slide. 2-5 word titles. Let whitespace breathe.",
            ContentStyle.STORYTELLING: "Customer narratives. Real people, real outcomes, real quotes.",
            ContentStyle.INVESTOR_UPDATE: "Monthly update format. Metrics, wins, challenges, asks. Transparent.",
        }
        return [
            {"id": style.value, "name": style.value.replace("_", " ").title(), "description": desc}
            for style, desc in style_descriptions.items()
        ]

    def _parse_json(self, raw: str, fallback: dict) -> dict:
        """Parse JSON from LLM response with fallback."""
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
        logger.warning("refine_parse_failed")
        return fallback
