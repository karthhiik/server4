"""
Slide content generator — generates content for individual slides per layout.
Uses structured JSON task routing with working models only.
Now powered by PromptEngine for style-aware, investor-grade slide content.

Updated 2026-04-02:
- Removed GPT-4o-mini dependency (uses Groq/DeepSeek/Qwen)
- Added retry mechanism for JSON parsing failures
- Improved prompt structure with explicit JSON schema
- Better fallback content generation
"""

import json
from typing import Optional

import structlog

from app.services.llm.model_router import ModelRouter, TaskType
from app.mcp.brain_mcp.prompts.prompt_engine import (
    PromptEngine,
    INVESTOR_PURPOSES,
)
from app.mcp.brain_mcp.prompts.quality_guards import run_quality_guards
from app.models.slide import SlideContent

logger = structlog.get_logger()

# JSON schema for slide content response
SLIDE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Slide title (3-8 words)"},
        "bullets": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Bullet points (3-6 items, each 5-15 words with source)",
        },
        "subtitle": {"type": "string"},
        "body_text": {"type": "string"},
        "left_content": {"type": "string"},
        "right_content": {"type": "string"},
        "left_label": {"type": "string"},
        "right_label": {"type": "string"},
        "left_items": {"type": "array", "items": {"type": "string"}},
        "right_items": {"type": "array", "items": {"type": "string"}},
        "image_prompt": {"type": "string"},
        "image_url": {"type": "string"},
        "chart_type": {"type": "string", "enum": ["bar", "line", "pie", "donut"]},
        "chart_data": {
            "type": "object",
            "properties": {
                "labels": {"type": "array", "items": {"type": "string"}},
                "datasets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "values": {"type": "array", "items": {"type": "number"}},
                        },
                    },
                },
            },
        },
        "source_attribution": {"type": "string"},
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "description": {"type": "string"},
                },
            },
        },
        "quote_text": {"type": "string"},
        "quote_author": {"type": "string"},
        "quote_role": {"type": "string"},
        "members": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "role": {"type": "string"},
                    "bio": {"type": "string"},
                },
            },
        },
        "metrics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "value": {"type": "string"},
                    "change": {"type": "string"},
                },
            },
        },
    },
    "required": ["title"],
}


class SlideGenerator:
    """Generates content for a single slide based on layout and context."""

    def __init__(self):
        self.router = ModelRouter.get_instance()
        self.prompt_engine = PromptEngine()

    async def generate_slide_content(
        self,
        layout: str,
        title: str,
        purpose: str,
        content_hints: str,
        research_context: str = "",
        presentation_context: str = "",
        writing_style: str = "yc_pitch",
        presentation_purpose: str = "pitch",
        presentation_id: Optional[str] = None,
    ) -> SlideContent:
        """Generate content for one slide with retry on failure."""
        # Compose system prompt with style + domain + layout layers
        system_prompt = self.prompt_engine.compose_slide_prompt(
            layout=layout,
            style=writing_style,
            purpose=presentation_purpose,
            slide_purpose=purpose,
        )

        user_prompt = self._build_user_prompt(
            layout=layout,
            title=title,
            purpose=purpose,
            content_hints=content_hints,
            research_context=research_context,
            presentation_context=presentation_context,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Try up to 2 times (first attempt + 1 retry with error feedback)
        last_error = None
        for attempt in range(2):
            try:
                response = await self.router.complete(
                    task_type=TaskType.STRUCTURED_JSON,
                    messages=messages,
                    temperature=0.6,
                    max_tokens=2048,
                    response_format={"type": "json_object"},
                    presentation_id=presentation_id,
                    phase="content",
                )

                content = self._parse_slide_content(response.content, layout, title)

                # Run quality guards
                guard_result = run_quality_guards(
                    content=content.model_dump(exclude_none=True),
                    layout=layout,
                    purpose=purpose,
                    is_investor_deck=presentation_purpose in INVESTOR_PURPOSES,
                )
                if guard_result.fluff_found:
                    logger.info(
                        "quality_guard_fluff",
                        slide=title[:30],
                        fluff=guard_result.fluff_found,
                    )
                if guard_result.unsourced_claims:
                    logger.info(
                        "quality_guard_unsourced",
                        slide=title[:30],
                        claims=guard_result.unsourced_claims,
                    )

                return content

            except (json.JSONDecodeError, KeyError) as e:
                last_error = str(e)
                logger.warning(
                    "slide_generation_retry",
                    attempt=attempt + 1,
                    slide=title[:30],
                    error=last_error,
                )
                # Add error feedback to messages for retry
                messages.append(
                    {
                        "role": "assistant",
                        "content": f"Error: {last_error}. Please return valid JSON only.",
                    }
                )
                messages.append(
                    {
                        "role": "user",
                        "content": "Return ONLY valid JSON matching the schema. No explanation, no markdown.",
                    }
                )

        # Final fallback: create minimal valid content
        logger.error(
            "slide_generation_failed_all_attempts",
            slide=title[:30],
            layout=layout,
        )
        return self._create_fallback_content(layout, title)

    def _build_user_prompt(
        self,
        layout: str,
        title: str,
        purpose: str,
        content_hints: str,
        research_context: str,
        presentation_context: str,
    ) -> str:
        """Build structured user prompt with explicit JSON schema."""
        prompt_parts = [
            f"Generate content for a '{layout}' layout slide:",
            f"",
            f"Title: {title}",
            f"Purpose: {purpose}",
            f"Content guidance: {content_hints}",
            f"",
        ]

        if research_context:
            prompt_parts.extend(
                [
                    f"Research data (use these facts and sources):",
                    research_context[:2000],
                    f"",
                ]
            )

        if presentation_context:
            prompt_parts.extend(
                [
                    f"Presentation context:",
                    presentation_context[:500],
                    f"",
                ]
            )

        # Add layout-specific JSON structure guidance
        layout_fields = {
            "bullets": "Required: title, bullets (array of 3-6 strings with sources)",
            "title-hero": "Required: title, subtitle",
            "two-column": "Required: title, left_content, right_content",
            "bullets-with-image": "Required: title, bullets (array), image_prompt",
            "chart": "Required: title, chart_type, chart_data (with labels and datasets), source_attribution",
            "comparison": "Required: title, left_label, right_label, left_items (array), right_items (array)",
            "timeline": "Required: title, events (array of {date, description})",
            "quote": "Required: title, quote_text, quote_author, quote_role",
            "team-grid": "Required: title, members (array of {name, role, bio})",
            "kpi-dashboard": "Required: title, metrics (array of {label, value, change})",
            "full-image": "Required: title, subtitle, image_prompt",
            "blank": "Required: title, body_text",
        }

        prompt_parts.extend(
            [
                f"Return ONLY valid JSON with these fields for '{layout}' layout:",
                layout_fields.get(layout, "Required: title, bullets"),
                f"",
                f"CRITICAL RULES:",
                f"- Return ONLY JSON, no markdown, no explanation",
                f"- Every number must have a source (e.g., '$180B by 2028 — Source: McKinsey 2025')",
                f"- Bullets: 3-6 items, each 5-15 words",
                f"- Title: 3-8 words",
                f"- Use research data provided above",
            ]
        )

        return "\n".join(prompt_parts)

    def _parse_slide_content(
        self, raw: str, layout: str, fallback_title: str
    ) -> SlideContent:
        """Parse LLM response into SlideContent with robust error handling."""
        text = raw.strip()

        # Strip markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:]) if len(lines) > 1 else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Strip json language marker
        if text.lower().startswith("json"):
            text = text[4:].strip()

        # Find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start < 0 or end <= start:
            raise json.JSONDecodeError("No JSON found", text, 0)

        json_str = text[start:end]
        data = json.loads(json_str)

        # Validate required fields
        if "title" not in data:
            data["title"] = fallback_title

        # Build SlideContent with only valid fields
        valid_fields = {
            "title",
            "subtitle",
            "body_text",
            "bullets",
            "left_content",
            "right_content",
            "left_label",
            "right_label",
            "left_items",
            "right_items",
            "image_prompt",
            "image_url",
            "chart_type",
            "chart_data",
            "events",
            "quote_text",
            "quote_author",
            "quote_role",
            "members",
            "metrics",
            "background_style",
            "speaker_notes",
        }

        clean_data = {k: v for k, v in data.items() if k in valid_fields and v}

        return SlideContent(**clean_data)

    def _create_fallback_content(self, layout: str, title: str) -> SlideContent:
        """Create minimal valid content when generation fails."""
        fallbacks = {
            "bullets": SlideContent(
                title=title,
                bullets=[
                    "Key insight 1 — Source: Industry research",
                    "Key insight 2 — Source: Market analysis",
                    "Key insight 3 — Source: Data review",
                ],
            ),
            "title-hero": SlideContent(
                title=title, subtitle="Details to be added during editing"
            ),
            "two-column": SlideContent(
                title=title,
                left_content="Left column content to be added",
                right_content="Right column content to be added",
            ),
            "chart": SlideContent(
                title=title,
                chart_type="bar",
                chart_data={
                    "labels": ["Q1", "Q2", "Q3", "Q4"],
                    "datasets": [{"label": "Data", "values": [0, 0, 0, 0]}],
                },
                body_text="Data to be added",
            ),
            "quote": SlideContent(
                title=title,
                quote_text="Quote to be added",
                quote_author="Author",
                quote_role="Role",
            ),
        }

        return fallbacks.get(
            layout,
            SlideContent(
                title=title,
                bullets=[
                    "Content generation in progress — edit this slide",
                ],
            ),
        )
