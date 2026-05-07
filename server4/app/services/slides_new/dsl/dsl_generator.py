"""
DSL Generator — Converts slide briefs into validated SlideDSL v2 objects.

Pipeline:
1. Load skill for this slide type (prompt template, mode, few-shot)
2. Build enriched prompt (context, examples, failure avoidance)
3. Call CodeAgentRouter with the correct task + mode
4. Parse + validate output against SlideDSL Pydantic model
5. Return validated DSL or structured error
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

import structlog

from app.models.dsl_v2 import SlideDSL
from app.services.slides_new.agents.code_agent_router import (
    CodeAgentRouter,
    CodeTaskType,
)
from app.services.slides_new.skills.models import (
    SkillGenerationMode,
    SlideSkill,
)
from app.services.slides_new.skills.skill_registry import SkillRegistry
from app.services.slides_new.skills.skill_store import SkillStore

logger = structlog.get_logger()


class DSLGenerationResult:
    """Result of a DSL generation attempt."""

    __slots__ = ("success", "dsl", "raw_json", "error", "model_used", "attempts")

    def __init__(
        self,
        success: bool,
        dsl: Optional[SlideDSL] = None,
        raw_json: Optional[str] = None,
        error: Optional[str] = None,
        model_used: Optional[str] = None,
        attempts: int = 1,
    ):
        self.success = success
        self.dsl = dsl
        self.raw_json = raw_json
        self.error = error
        self.model_used = model_used
        self.attempts = attempts


def _sanitize_template_value(value: str) -> str:
    """
    Sanitize user-provided template variable values to prevent prompt injection.

    Strips known prompt injection patterns:
    - System/assistant role overrides
    - Instruction override phrases
    - Markdown heading injections that mimic prompt sections
    - Encoded payloads (base64 patterns)
    """
    if not isinstance(value, str):
        return str(value)

    sanitized = value

    # Strip role-override attempts
    _INJECTION_PATTERNS = [
        r"(?i)\bsystem\s*:\s*",
        r"(?i)\bassistant\s*:\s*",
        r"(?i)\buser\s*:\s*",
        r"(?i)ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)",
        r"(?i)disregard\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)",
        r"(?i)forget\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)",
        r"(?i)you\s+are\s+now\s+",
        r"(?i)new\s+instructions?\s*:",
        r"(?i)override\s+instructions?\s*:",
        r"(?i)<\|im_start\|>",
        r"(?i)<\|im_end\|>",
        r"(?i)\[INST\]",
        r"(?i)\[/INST\]",
        r"(?i)```\s*system",
    ]

    for pattern in _INJECTION_PATTERNS:
        sanitized = re.sub(pattern, "", sanitized)

    # Collapse multiple newlines to prevent prompt section hijacking
    sanitized = re.sub(r"\n{4,}", "\n\n\n", sanitized)

    # Limit length to prevent context stuffing (generous limit for legit use)
    MAX_SLOT_LEN = 2000
    if len(sanitized) > MAX_SLOT_LEN:
        sanitized = sanitized[:MAX_SLOT_LEN]

    return sanitized.strip()


class DSLGenerator:
    """
    Generates validated SlideDSL v2 from slide briefs using the skill system.

    Flow:
    1. skill = SkillStore.get_skill(slide_type) or use registry default
    2. few_shot = SkillStore.get_few_shot_examples(skill, topic)
    3. failures = SkillStore.get_failure_patterns(skill)
    4. prompt = _build_prompt(skill, brief, few_shot, failures)
    5. response = CodeAgentRouter.generate_dsl(prompt, mode)
    6. dsl = _parse_and_validate(response)
    """

    def __init__(
        self,
        skill_store: SkillStore,
        router: Optional[CodeAgentRouter] = None,
    ) -> None:
        self._store = skill_store
        self._router = router or CodeAgentRouter()

    async def generate(
        self,
        slide_type: str,
        slide_brief: Dict[str, Any],
        context: Dict[str, Any],
        presentation_id: Optional[str] = None,
    ) -> DSLGenerationResult:
        """
        Generate a validated SlideDSL v2 from a slide brief.

        Args:
            slide_type: e.g. "problem", "market", "traction"
            slide_brief: Content brief dict with topic-specific data
            context: Global presentation context (topic, audience, design system)
            presentation_id: For logging/tracing
        """
        # 1. Load skill
        skill = await self._store.get_skill(slide_type)
        if skill is None:
            # Use registry defaults
            prompt_template = SkillRegistry.get_prompt(slide_type)
            mode = SkillRegistry.get_mode(slide_type)
        else:
            prompt_template = skill.prompt_template
            mode = skill.generation_mode

        # 2. Get few-shot examples
        topic_query = context.get("topic", "") + " " + slide_brief.get("title", "")
        few_shot_examples = await self._store.get_few_shot_examples(
            skill_name=slide_type,
            query=topic_query.strip(),
            n=3,
            min_quality=80,
        )

        # 3. Get failure patterns to avoid
        failure_patterns = await self._store.get_failure_patterns(
            skill_name=slide_type, n=5
        )

        # 4. Build enriched prompt
        system_prompt = SkillRegistry.get_dsl_system_prompt()
        user_prompt = self._build_prompt(
            template=prompt_template,
            slide_brief=slide_brief,
            context=context,
            few_shot=few_shot_examples,
            failures=failure_patterns,
        )

        # 5. Call LLM
        try:
            response = await self._router.generate_dsl(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                mode=mode,
                presentation_id=presentation_id,
            )
        except ConnectionError as e:
            logger.error(
                "dsl_generation_all_models_failed",
                slide_type=slide_type,
                error=str(e),
            )
            return DSLGenerationResult(
                success=False,
                error=f"All models failed: {e}",
            )

        # 6. Parse and validate
        raw_content = response.content
        model_used = response.model if hasattr(response, "model") else "unknown"

        return self._parse_and_validate(
            raw_content=raw_content,
            slide_type=slide_type,
            slide_brief=slide_brief,
            model_used=model_used,
        )

    def _build_prompt(
        self,
        template: str,
        slide_brief: Dict[str, Any],
        context: Dict[str, Any],
        few_shot: List[Dict[str, Any]],
        failures: list,
    ) -> str:
        """Build the final prompt by filling template slots."""
        # Fill template variables from context (sanitized to prevent injection)
        filled = template
        slot_values = {
            "topic": context.get("topic", ""),
            "company_name": context.get("company_name", ""),
            "audience": context.get("audience", "investors"),
            "archetype": context.get("archetype", "startup-pitch"),
            "writing_style": context.get("writing_style", "professional"),
            "design_preset": context.get("design_preset", "midnight"),
            "primary_color": context.get("primary_color", "#1A1A2E"),
            "accent_color": context.get("accent_color", "#E94560"),
            "background_color": context.get("background_color", "#FFFFFF"),
            "heading_font": context.get("heading_font", "DM Sans"),
            "body_font": context.get("body_font", "Inter"),
            "slide_brief": json.dumps(slide_brief, indent=2),
        }

        for key, value in slot_values.items():
            sanitized = _sanitize_template_value(str(value))
            filled = filled.replace(f"{{{{{key}}}}}", sanitized)

        # Build few-shot section
        few_shot_section = self._build_few_shot_section(few_shot)
        filled = filled.replace("{few_shot_section}", few_shot_section)

        # Build failure avoidance section
        failure_section = self._build_failure_section(failures)
        filled = filled.replace("{failure_avoidance_section}", failure_section)

        return filled

    def _build_few_shot_section(self, examples: List[Dict[str, Any]]) -> str:
        """Build few-shot examples section for the prompt."""
        if not examples:
            return ""

        parts = ["## Reference Examples (high-scoring outputs for this slide type):"]
        for i, ex in enumerate(examples[:3], 1):
            score = ex.get("metadata", {}).get("quality_score", "?")
            doc = ex.get("document", "")
            # Truncate very long examples
            if len(doc) > 1500:
                doc = doc[:1500] + "\n... (truncated)"
            parts.append(f"\n### Example {i} (score: {score}/100):")
            parts.append(f"```json\n{doc}\n```")

        return "\n".join(parts)

    def _build_failure_section(self, failures: list) -> str:
        """Build failure avoidance section for the prompt."""
        if not failures:
            return ""

        parts = [
            "## AVOID THESE KNOWN FAILURES (past issues — do NOT repeat):"
        ]
        for f in failures[:5]:
            desc = f.description if hasattr(f, "description") else str(f)
            mitigation = (
                f.mitigation
                if hasattr(f, "mitigation") and f.mitigation
                else "Avoid this pattern"
            )
            parts.append(f"- **{desc}** → {mitigation}")

        return "\n".join(parts)

    def _parse_and_validate(
        self,
        raw_content: str,
        slide_type: str,
        slide_brief: Dict[str, Any],
        model_used: str,
    ) -> DSLGenerationResult:
        """Parse raw LLM output into a validated SlideDSL object."""
        # Extract JSON from response (might be wrapped in markdown)
        json_str = self._extract_json(raw_content)
        if json_str is None:
            return DSLGenerationResult(
                success=False,
                raw_json=raw_content,
                error="Could not extract valid JSON from LLM response",
                model_used=model_used,
            )

        # Parse JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return DSLGenerationResult(
                success=False,
                raw_json=json_str,
                error=f"JSON parse error: {e}",
                model_used=model_used,
            )

        # Ensure required fields have defaults
        if "id" not in data:
            data["id"] = f"slide_{slide_type}_{data.get('index', 0)}"
        if "index" not in data:
            data["index"] = 0

        # Validate against SlideDSL Pydantic model
        try:
            dsl = SlideDSL.model_validate(data)
        except Exception as e:
            logger.warning(
                "dsl_validation_error",
                slide_type=slide_type,
                error=str(e),
                model=model_used,
            )
            return DSLGenerationResult(
                success=False,
                raw_json=json_str,
                error=f"DSL validation error: {e}",
                model_used=model_used,
            )

        logger.info(
            "dsl_generated",
            slide_type=slide_type,
            layout=dsl.layout.value,
            model=model_used,
        )

        return DSLGenerationResult(
            success=True,
            dsl=dsl,
            raw_json=json_str,
            model_used=model_used,
        )

    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from text that may be wrapped in markdown code blocks."""
        # Try: direct parse
        text = text.strip()
        if text.startswith("{"):
            return text

        # Try: markdown code block
        pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

        # Try: find first { to last }
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            return text[first_brace : last_brace + 1]

        return None
