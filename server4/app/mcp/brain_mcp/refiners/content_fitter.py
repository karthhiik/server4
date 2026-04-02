"""
Content fitter — adjusts content to fit layout constraints.
When a slide changes layout, content needs to be reflowed to fit the new format.
"""

import json
from typing import Optional

import structlog

from app.services.llm.model_router import ModelRouter, TaskType
from app.mcp.brain_mcp.prompts.slide_system import get_slide_prompt
from app.mcp.design_mcp.config import LAYOUT_CONSTRAINTS

logger = structlog.get_logger()


class ContentFitter:
    """Reflows slide content when layout changes."""

    def __init__(self):
        self.router = ModelRouter.get_instance()

    async def reflow_for_layout(
        self,
        current_content: dict,
        current_layout: str,
        target_layout: str,
        presentation_id: Optional[str] = None,
    ) -> dict:
        """Reflow content from one layout format to another."""
        constraints = LAYOUT_CONSTRAINTS.get(target_layout, {})
        target_prompt = get_slide_prompt(target_layout)

        user_prompt = f"""Convert this slide content from "{current_layout}" layout to "{target_layout}" layout.

Current content:
{json.dumps(current_content, default=str)}

Target layout constraints:
{json.dumps(constraints)}

Preserve the key message and data. Restructure to fit the new layout format.
Return ONLY valid JSON matching the target layout format."""

        messages = [
            {"role": "system", "content": target_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await self.router.complete(
            task_type=TaskType.CONTENT_FIT_RESIZE,
            messages=messages,
            temperature=0.4,
            max_tokens=2048,
            presentation_id=presentation_id,
            phase="reflow",
        )

        return self._parse_json(response.content, current_content)

    def check_fits_constraints(self, content: dict, layout: str) -> list[str]:
        """Check if content fits layout constraints. Returns list of violations."""
        constraints = LAYOUT_CONSTRAINTS.get(layout, {})
        violations = []

        title = content.get("title", "")
        max_title = constraints.get("max_title_chars")
        if max_title and len(title) > max_title:
            violations.append(f"Title too long: {len(title)}/{max_title} chars")

        bullets = content.get("bullets", [])
        max_bullets = constraints.get("max_bullets")
        if max_bullets and len(bullets) > max_bullets:
            violations.append(f"Too many bullets: {len(bullets)}/{max_bullets}")

        max_bullet_chars = constraints.get("max_bullet_chars")
        if max_bullet_chars and bullets:
            for i, b in enumerate(bullets):
                if len(str(b)) > max_bullet_chars:
                    violations.append(f"Bullet {i+1} too long: {len(str(b))}/{max_bullet_chars} chars")

        events = content.get("events", [])
        max_events = constraints.get("max_events")
        if max_events and len(events) > max_events:
            violations.append(f"Too many events: {len(events)}/{max_events}")

        members = content.get("members", [])
        max_members = constraints.get("max_members")
        if max_members and len(members) > max_members:
            violations.append(f"Too many members: {len(members)}/{max_members}")

        metrics = content.get("metrics", [])
        max_metrics = constraints.get("max_metrics")
        if max_metrics and len(metrics) > max_metrics:
            violations.append(f"Too many metrics: {len(metrics)}/{max_metrics}")

        return violations

    async def auto_fit(
        self,
        content: dict,
        layout: str,
        presentation_id: Optional[str] = None,
    ) -> dict:
        """Auto-trim content to fit constraints using LLM if needed."""
        violations = self.check_fits_constraints(content, layout)
        if not violations:
            return content

        constraints = LAYOUT_CONSTRAINTS.get(layout, {})
        user_prompt = f"""This slide content exceeds its layout constraints. Trim it to fit.

Content:
{json.dumps(content, default=str)}

Layout: {layout}
Constraints: {json.dumps(constraints)}
Violations: {json.dumps(violations)}

Trim the content to fit within constraints while preserving the key message.
Return ONLY valid JSON."""

        messages = [
            {"role": "system", "content": "You are a content editor. Trim slide content to fit layout constraints. Return valid JSON only."},
            {"role": "user", "content": user_prompt},
        ]

        response = await self.router.complete(
            task_type=TaskType.CONTENT_FIT_RESIZE,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
            presentation_id=presentation_id,
            phase="auto_fit",
        )

        return self._parse_json(response.content, content)

    def _parse_json(self, raw: str, fallback: dict) -> dict:
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
        return fallback
