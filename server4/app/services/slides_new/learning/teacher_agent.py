"""
Teacher Agent — Post-generation evaluator and lesson extractor.

Inspired by Hermes Agent's _spawn_background_review() pattern:
- Runs AFTER the main generation pipeline completes
- Reviews the entire presentation holistically (not per-slide like QA)
- Extracts design lessons for future generations
- Detects patterns across presentations
- Grades design cohesion, visual flow, brand consistency
- Writes structured feedback to the learning system

The Teacher is NOT the QA Agent. QA gates individual slides;
the Teacher evaluates the WHOLE presentation and teaches the system.
"""

import json
import time
from typing import Any, Dict, List, Optional

import structlog

from app.services.llm import TaskType
from app.services.slides_new.agents.base import (
    AgentContext,
    AgentOutput,
    AgentType,
    BaseAgent,
)
from app.services.slides_new.learning.models import (
    DesignLesson,
    LessonCategory,
    LessonSentiment,
    TeacherDimension,
    TeacherFeedback,
)

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════════════════════
# TEACHER PROMPTS (inspired by Hermes _COMBINED_REVIEW_PROMPT)
# ═══════════════════════════════════════════════════════════════════════════════

TEACHER_SYSTEM_PROMPT = """You are a Principal Design Critic and Presentation Coach.
Your role is to evaluate completed slide presentations and extract LESSONS that will
make future presentations better. You are NOT fixing this presentation — you are
TEACHING the system to improve.

Think like a senior design director at a top agency reviewing work for patterns
of excellence and areas for growth.

Your evaluation dimensions:
1. VISUAL COHESION — Do slides feel like one deck? Consistent palette, typography, spacing?
2. NARRATIVE FLOW — Does the visual design support the story arc? Building tension, payoff?
3. INFORMATION DESIGN — Are data visuals clear? Is hierarchy obvious? Can audience scan?
4. EMOTIONAL IMPACT — Does the design evoke the right feeling? Professional? Exciting? Trustworthy?
5. ORIGINALITY — Does this avoid generic AI aesthetics? Is there a distinctive design voice?
6. AUDIENCE FIT — Is the visual language appropriate for the target audience?
7. TECHNICAL QUALITY — Clean layouts, readable text, proper contrast, accessible?

For each dimension, provide:
- Score (0-100)
- Grade (A/B/C/D/F)
- 1-3 specific observations
- 1-2 actionable recommendations

Then extract LESSONS — discrete design insights that can be reused:
- What worked well (positive lessons)
- What should be avoided (negative lessons)
- What patterns emerged that could be applied to future decks

CRITICAL: Lessons must be SPECIFIC and ACTIONABLE, not vague platitudes.
BAD: "Use good colors" — too vague
GOOD: "Dark gradient backgrounds with glass-morphism cards scored 15pts higher than flat solid backgrounds for fintech pitch decks targeting VCs"
"""

TEACHER_EVALUATION_PROMPT = """Evaluate this completed presentation and extract design lessons.

## Presentation Context
- Topic: {topic}
- Purpose: {purpose}
- Audience: {audience}
- Slide Count: {slide_count}
- Company: {company_name}
- QA Score: {qa_score}/100

## Strategy (CEO Agent Output)
{strategy_summary}

## Design System (Designer Agent Output)
{design_summary}

## Slide Types Used
{slide_types}

## QA Feedback
{qa_feedback}

## Historical Context
{historical_context}

---

Respond in this EXACT JSON format:
{{
    "overall_score": <float 0-100>,
    "overall_grade": "<A/B/C/D/F>",
    "dimensions": [
        {{
            "name": "<dimension name>",
            "score": <float 0-100>,
            "grade": "<A/B/C/D/F>",
            "observations": ["<specific observation>"],
            "recommendations": ["<actionable recommendation>"]
        }}
    ],
    "cohesion_score": <float 0-100>,
    "narrative_flow_score": <float 0-100>,
    "brand_consistency_score": <float 0-100>,
    "lessons": [
        {{
            "category": "<color_palette|typography|layout|background|animation|visual_hierarchy|content_density|imagery|brand_cohesion|slide_transitions|chart_design|spacing|contrast|readability|emotional_impact|audience_fit>",
            "sentiment": "<positive|negative>",
            "summary": "<specific actionable lesson, 10-200 chars>",
            "details": "<extended explanation>",
            "slide_type": "<specific slide type or null for global>",
            "quality_delta": <float, estimated impact on quality score>
        }}
    ],
    "style_directives": ["<specific style rule for future generations>"],
    "anti_patterns": ["<specific thing to avoid>"]
}}
"""


class TeacherAgent(BaseAgent):
    """
    Teacher Agent — Post-generation design evaluator and lesson extractor.

    Unlike QA which gates individual slides, the Teacher:
    1. Reviews the COMPLETE presentation holistically
    2. Grades design cohesion across all slides
    3. Extracts reusable design lessons
    4. Detects emerging patterns
    5. Compares against historical performance
    6. Generates style directives for future generations

    Runs as Phase 7 after QA completes.
    """

    DEFAULT_MODEL = "deepseek-v3"
    FALLBACK_MODELS = ["gpt-4o-mini", "cf-qwen", "mistral-medium"]

    @property
    def agent_type(self) -> AgentType:
        return AgentType.TEACHER

    async def execute(self) -> AgentOutput:
        """
        Execute the teaching cycle.

        1. Gather all agent outputs from the generation
        2. Build evaluation prompt with full context
        3. Call LLM for structured evaluation
        4. Parse into TeacherFeedback + DesignLessons
        5. Return structured output
        """
        start_time = time.monotonic()

        try:
            # 1. Gather generation data from previous agent outputs
            generation_data = self._gather_generation_data()

            # 2. Build historical context from design memory
            historical_context = await self._build_historical_context()

            # 3. Build the evaluation prompt
            prompt = self._build_evaluation_prompt(
                generation_data, historical_context
            )

            # 4. Call LLM for structured evaluation
            result = await self.call_llm(
                task_type=TaskType.QUALITY_ASSESSMENT,
                prompt=prompt,
                system_prompt=TEACHER_SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )

            if not result.success:
                logger.error(
                    "teacher_llm_failed",
                    errors=result.errors,
                    task_id=self.context.task_id,
                )
                return AgentOutput(
                    success=False,
                    agent_type=AgentType.TEACHER,
                    errors=result.errors,
                    latency_ms=int((time.monotonic() - start_time) * 1000),
                )

            # 5. Parse the evaluation response
            feedback = self._parse_evaluation(result.output.get("content", "{}"))

            if feedback is None:
                return AgentOutput(
                    success=False,
                    agent_type=AgentType.TEACHER,
                    errors=["Failed to parse teacher evaluation"],
                    latency_ms=int((time.monotonic() - start_time) * 1000),
                )

            # 6. Write to Context Board
            if self._context_board is not None:
                await self.write_to_board("learning:teacher_feedback", {
                    "overall_score": feedback.overall_score,
                    "overall_grade": feedback.overall_grade,
                    "cohesion_score": feedback.cohesion_score,
                    "narrative_flow_score": feedback.narrative_flow_score,
                    "brand_consistency_score": feedback.brand_consistency_score,
                    "lessons_count": len(feedback.lessons_learned),
                    "style_directives": feedback.style_directives,
                    "anti_patterns": feedback.anti_patterns,
                })

            latency = int((time.monotonic() - start_time) * 1000)

            logger.info(
                "teacher_evaluation_complete",
                task_id=self.context.task_id,
                overall_score=feedback.overall_score,
                overall_grade=feedback.overall_grade,
                lessons_extracted=len(feedback.lessons_learned),
                latency_ms=latency,
            )

            return AgentOutput(
                success=True,
                agent_type=AgentType.TEACHER,
                output={
                    "feedback": feedback.model_dump(mode="json"),
                    "lessons_count": len(feedback.lessons_learned),
                    "overall_score": feedback.overall_score,
                    "overall_grade": feedback.overall_grade,
                    "cohesion_score": feedback.cohesion_score,
                    "narrative_flow_score": feedback.narrative_flow_score,
                    "brand_consistency_score": feedback.brand_consistency_score,
                    "style_directives": feedback.style_directives,
                    "anti_patterns": feedback.anti_patterns,
                },
                model_used=result.model_used,
                tokens_used=result.tokens_used,
                latency_ms=latency,
            )

        except Exception as e:
            logger.exception(
                "teacher_agent_error",
                task_id=self.context.task_id,
                error=str(e),
            )
            return AgentOutput(
                success=False,
                agent_type=AgentType.TEACHER,
                errors=[str(e)],
                latency_ms=int((time.monotonic() - start_time) * 1000),
            )

    def _gather_generation_data(self) -> Dict[str, Any]:
        """Gather all relevant data from the generation pipeline."""
        data: Dict[str, Any] = {
            "topic": self.context.topic,
            "purpose": self.context.purpose,
            "audience": self.context.audience,
            "slide_count": self.context.slide_count,
            "company_name": self.context.company_name or "Unknown",
        }

        # Extract from previous agent outputs
        prev = self.context.previous_outputs

        # CEO strategy
        ceo_output = prev.get(AgentType.CEO) or prev.get("ceo")
        if ceo_output and isinstance(ceo_output, AgentOutput) and ceo_output.output:
            data["strategy"] = ceo_output.output
        else:
            data["strategy"] = {}

        # Designer output
        designer_output = prev.get(AgentType.DESIGNER) or prev.get("designer")
        if designer_output and isinstance(designer_output, AgentOutput) and designer_output.output:
            data["design"] = designer_output.output
        else:
            data["design"] = {}

        # QA output
        qa_output = prev.get(AgentType.QA) or prev.get("qa")
        if qa_output and isinstance(qa_output, AgentOutput) and qa_output.output:
            data["qa"] = qa_output.output
        else:
            data["qa"] = {}

        # Layout output
        layout_output = prev.get(AgentType.LAYOUT) or prev.get("layout")
        if layout_output and isinstance(layout_output, AgentOutput) and layout_output.output:
            data["layout"] = layout_output.output
        else:
            data["layout"] = {}

        # Code agent output (slide types)
        code_output = prev.get(AgentType.CODE_AGENT) or prev.get("code_agent")
        if code_output and isinstance(code_output, AgentOutput) and code_output.output:
            data["code"] = code_output.output
        else:
            data["code"] = {}

        return data

    async def _build_historical_context(self) -> str:
        """
        Build historical context from past Teacher feedback.
        Like Hermes build_system_prompt() — enrich with memory.
        """
        # Try reading from Context Board (learning section)
        if self._context_board is not None:
            try:
                history = await self.read_from_board("learning:recent_feedback")
                if history:
                    return self._format_historical(history)
            except Exception:
                pass

        return "No historical data available yet. This may be one of the first presentations."

    def _format_historical(self, history: Any) -> str:
        """Format historical data for the prompt."""
        if isinstance(history, dict):
            lines = ["Recent performance:"]
            if "avg_score" in history:
                lines.append(f"- Average quality: {history['avg_score']:.0f}/100")
            if "trend" in history:
                lines.append(f"- Trend: {history['trend']}")
            if "top_issues" in history:
                lines.append("- Common issues:")
                for issue in history.get("top_issues", [])[:5]:
                    lines.append(f"  - {issue}")
            return "\n".join(lines)
        return str(history)[:500]

    def _build_evaluation_prompt(
        self,
        data: Dict[str, Any],
        historical_context: str,
    ) -> str:
        """Build the full evaluation prompt."""
        strategy = data.get("strategy", {})
        design = data.get("design", {})
        qa = data.get("qa", {})

        # Extract strategy summary
        strategy_summary = "Not available"
        if strategy:
            parts = []
            if strategy.get("archetype"):
                parts.append(f"Archetype: {strategy['archetype']}")
            if strategy.get("narrative_arc"):
                parts.append(f"Narrative: {strategy['narrative_arc']}")
            if strategy.get("writing_style"):
                parts.append(f"Style: {strategy['writing_style']}")
            strategy_summary = "\n".join(parts) if parts else json.dumps(strategy, indent=2)[:500]

        # Extract design summary
        design_summary = "Not available"
        if design:
            design_summary = json.dumps(design, indent=2)[:800]

        # Extract slide types
        code_data = data.get("code", {})
        slide_types = "Not available"
        if isinstance(code_data, dict):
            types = code_data.get("slide_types", [])
            if types:
                slide_types = ", ".join(types)
            else:
                slide_types = json.dumps(code_data, indent=2)[:300]

        # QA feedback
        qa_feedback = "Not available"
        if qa:
            qa_parts = []
            if qa.get("quality_score"):
                qa_parts.append(f"Score: {qa['quality_score']}")
            if qa.get("issues"):
                qa_parts.append("Issues: " + "; ".join(qa["issues"][:5]))
            if qa.get("recommendations"):
                qa_parts.append("Recommendations: " + "; ".join(qa["recommendations"][:5]))
            qa_feedback = "\n".join(qa_parts) if qa_parts else json.dumps(qa, indent=2)[:500]

        return TEACHER_EVALUATION_PROMPT.format(
            topic=data.get("topic", "Unknown"),
            purpose=data.get("purpose", "Unknown"),
            audience=data.get("audience", "Unknown"),
            slide_count=data.get("slide_count", 10),
            company_name=data.get("company_name", "Unknown"),
            qa_score=qa.get("quality_score", 0),
            strategy_summary=strategy_summary,
            design_summary=design_summary,
            slide_types=slide_types,
            qa_feedback=qa_feedback,
            historical_context=historical_context,
        )

    def _parse_evaluation(self, raw_content: str) -> Optional[TeacherFeedback]:
        """Parse LLM response into structured TeacherFeedback."""
        try:
            data = json.loads(raw_content) if isinstance(raw_content, str) else raw_content
        except json.JSONDecodeError:
            logger.error("teacher_json_parse_failed", content=raw_content[:200])
            return None

        if not isinstance(data, dict):
            return None

        # Parse dimensions
        dimensions: List[TeacherDimension] = []
        for dim_data in data.get("dimensions", []):
            try:
                dimensions.append(TeacherDimension(
                    name=dim_data.get("name", "unknown"),
                    score=float(dim_data.get("score", 0)),
                    grade=dim_data.get("grade", "C"),
                    observations=dim_data.get("observations", []),
                    recommendations=dim_data.get("recommendations", []),
                ))
            except (ValueError, TypeError):
                continue

        # Parse lessons
        lessons: List[DesignLesson] = []
        for lesson_data in data.get("lessons", []):
            try:
                category_str = lesson_data.get("category", "layout")
                sentiment_str = lesson_data.get("sentiment", "neutral")

                # Validate enums
                try:
                    category = LessonCategory(category_str)
                except ValueError:
                    category = LessonCategory.LAYOUT

                try:
                    sentiment = LessonSentiment(sentiment_str)
                except ValueError:
                    sentiment = LessonSentiment.NEUTRAL

                lesson = DesignLesson(
                    category=category,
                    sentiment=sentiment,
                    summary=str(lesson_data.get("summary", ""))[:500],
                    details=lesson_data.get("details"),
                    slide_type=lesson_data.get("slide_type"),
                    quality_delta=float(lesson_data.get("quality_delta", 0)),
                    confidence=0.6,  # Initial confidence for new lessons
                    source_presentation_id=self.context.task_id,
                    source_quality_score=float(data.get("overall_score", 0)),
                )
                lessons.append(lesson)
            except (ValueError, TypeError) as e:
                logger.debug("teacher_lesson_parse_skip", error=str(e))
                continue

        feedback = TeacherFeedback(
            presentation_id=self.context.task_id,
            overall_score=float(data.get("overall_score", 0)),
            overall_grade=data.get("overall_grade", "C"),
            dimensions=dimensions,
            lessons_learned=lessons,
            cohesion_score=float(data.get("cohesion_score", 0)),
            narrative_flow_score=float(data.get("narrative_flow_score", 0)),
            brand_consistency_score=float(data.get("brand_consistency_score", 0)),
            style_directives=data.get("style_directives", []),
            anti_patterns=data.get("anti_patterns", []),
        )

        return feedback
