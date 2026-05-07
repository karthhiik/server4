"""
Learning Engine — Core orchestrator for the self-learning presentation system.

Inspired by Hermes Agent's closed learning loop:
- MemoryManager → LearningEngine (orchestrates the learning lifecycle)
- _spawn_background_review() → run_post_generation_learning()
- memory_nudge_interval → snapshot_interval (periodic knowledge captures)
- flush_memories() → flush_lessons() (persist before cleanup)
- skill self-improvement → pattern evolution

The Learning Engine ties together:
- Teacher Agent (evaluation + lesson extraction)
- Design Memory (persistent storage + retrieval)
- Pattern Detection (cross-generation trends)
- Snapshot System (periodic knowledge captures)

It is called by the V7 Orchestrator after QA completes (Phase 7).
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import structlog

from app.services.slides_new.agents.base import (
    AgentContext,
    AgentOutput,
    AgentType,
)
from app.services.slides_new.learning.design_memory import DesignMemory
from app.services.slides_new.learning.models import (
    DesignLesson,
    DesignPattern,
    GenerationRecord,
    LessonCategory,
    LessonSentiment,
    PatternStrength,
    TeacherFeedback,
)
from app.services.slides_new.learning.teacher_agent import TeacherAgent

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase
    from app.services.context_board import ContextBoard

logger = structlog.get_logger()

# Nudge interval — after this many generations, trigger deep analysis
DEEP_ANALYSIS_INTERVAL = 10
# Minimum quality score to extract positive lessons
MIN_QUALITY_FOR_POSITIVE = 70.0
# Maximum lessons to extract per generation
MAX_LESSONS_PER_GENERATION = 12


class LearningEngine:
    """
    Core orchestrator for the self-learning presentation system.

    Lifecycle (per generation):
    1. Pre-generation: Provide relevant lessons to agents
    2. Post-generation: Run Teacher → extract lessons → detect patterns
    3. Periodic: Take snapshots, decay stale lessons, evolve patterns

    Usage:
        engine = LearningEngine(db)
        await engine.initialize()

        # Before generation — get lessons for agents
        lessons_text = await engine.get_lessons_for_context(
            slide_types=["title-hero", "problem"],
            audience="VCs",
            purpose="fundraising",
        )

        # After generation — run the learning cycle
        feedback = await engine.run_post_generation_learning(
            context=agent_context,
            result=generation_result,
            context_board=context_board,
        )
    """

    def __init__(
        self,
        db: "AsyncIOMotorDatabase",
        chroma_service: Optional[Any] = None,
    ) -> None:
        self.db = db
        self._memory = DesignMemory(db, chroma_service)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the learning system. Call once at startup."""
        if self._initialized:
            return
        await self._memory.initialize()
        self._initialized = True
        logger.info("learning_engine_initialized")

    # ── PRE-GENERATION: PROVIDE LESSONS ───────────────────────

    async def get_lessons_for_context(
        self,
        slide_types: Optional[List[str]] = None,
        audience: Optional[str] = None,
        purpose: Optional[str] = None,
    ) -> str:
        """
        Get formatted lessons for injection into agent prompts.
        Called BEFORE generation to inform Designer/Code agents.
        """
        if not self._initialized:
            await self.initialize()

        lessons_text = await self._memory.get_lessons_for_prompt(
            slide_type=slide_types[0] if slide_types else None,
            audience=audience,
            purpose=purpose,
        )
        patterns_text = await self._memory.get_patterns_for_prompt(
            slide_types=slide_types,
            audience=audience,
            purpose=purpose,
        )

        parts = []
        if lessons_text:
            parts.append(lessons_text)
        if patterns_text:
            parts.append(patterns_text)

        return "\n\n".join(parts)

    # ── POST-GENERATION: LEARNING CYCLE ───────────────────────

    async def run_post_generation_learning(
        self,
        context: AgentContext,
        result: Dict[str, Any],
        context_board: Optional["ContextBoard"] = None,
    ) -> Optional[TeacherFeedback]:
        """
        Run the full post-generation learning cycle.
        Analogous to Hermes _spawn_background_review().

        Steps:
        1. Run Teacher Agent evaluation
        2. Store lessons in Design Memory
        3. Store generation record
        4. Detect and evolve patterns
        5. Take snapshot if interval reached
        6. Write historical context for next generation

        Args:
            context: The AgentContext from the generation
            result: The V7GenerationResult data
            context_board: Optional Context Board for writing learning data

        Returns:
            TeacherFeedback if successful, None on failure
        """
        if not self._initialized:
            await self.initialize()

        start_time = time.monotonic()

        logger.info(
            "learning_cycle_started",
            task_id=context.task_id,
            quality_score=result.get("quality_score", 0),
        )

        try:
            # 1. Run Teacher Agent
            teacher = TeacherAgent(self.db, context, context_board)
            teacher_output = await teacher.execute()

            feedback: Optional[TeacherFeedback] = None

            if teacher_output.success and teacher_output.output:
                feedback_data = teacher_output.output.get("feedback")
                if feedback_data:
                    try:
                        feedback = TeacherFeedback.model_validate(feedback_data)
                    except Exception as e:
                        logger.warning(
                            "teacher_feedback_parse_failed",
                            error=str(e),
                        )

            # 2. Store lessons
            lessons_stored = 0
            if feedback and feedback.lessons_learned:
                lessons_stored = await self._memory.store_lessons(
                    feedback.lessons_learned
                )

            # 3. Store Teacher feedback
            if feedback:
                await self._memory.store_teacher_feedback(feedback)

            # 4. Store generation record
            record = self._build_generation_record(context, result)
            await self._memory.store_generation_record(record)

            # 5. Detect and evolve patterns
            patterns_updated = 0
            if feedback and feedback.lessons_learned:
                patterns_updated = await self._detect_and_evolve_patterns(
                    feedback.lessons_learned,
                    result.get("quality_score", 0),
                )

            # 6. Periodic snapshot (like Hermes memory nudge)
            snapshot_taken = False
            if self._memory.should_snapshot:
                await self._memory.take_snapshot()
                snapshot_taken = True

            # 7. Decay stale lessons periodically
            if self._memory.generation_count % 50 == 0:
                decayed = await self._memory.decay_stale_lessons()
                if decayed > 0:
                    logger.info("stale_lessons_decayed", count=decayed)

            # 8. Write historical context for next generation
            if context_board is not None:
                await self._write_historical_context(context_board)

            latency = int((time.monotonic() - start_time) * 1000)

            logger.info(
                "learning_cycle_complete",
                task_id=context.task_id,
                lessons_stored=lessons_stored,
                patterns_updated=patterns_updated,
                snapshot_taken=snapshot_taken,
                latency_ms=latency,
            )

            return feedback

        except Exception as e:
            logger.exception(
                "learning_cycle_error",
                task_id=context.task_id,
                error=str(e),
            )
            return None

    # ── PATTERN DETECTION ─────────────────────────────────────

    async def _detect_and_evolve_patterns(
        self,
        new_lessons: List[DesignLesson],
        quality_score: float,
    ) -> int:
        """
        Detect recurring patterns across lessons.
        Like Hermes skill creation — when patterns repeat, formalize them.
        """
        patterns_updated = 0

        # Group lessons by category
        by_category: Dict[LessonCategory, List[DesignLesson]] = {}
        for lesson in new_lessons:
            by_category.setdefault(lesson.category, []).append(lesson)

        for category, lessons in by_category.items():
            positive_lessons = [
                l for l in lessons if l.sentiment == LessonSentiment.POSITIVE
            ]
            if not positive_lessons:
                continue

            for lesson in positive_lessons:
                # Check if a pattern already exists for this category + slide_type
                pattern_name = self._derive_pattern_name(lesson)
                existing = await self._memory.get_pattern(pattern_name)

                if existing:
                    # Evolve existing pattern
                    existing.record_usage(quality_score)
                    existing.contributing_lessons.append(lesson.id)
                    # Keep last 20 contributing lessons
                    if len(existing.contributing_lessons) > 20:
                        existing.contributing_lessons = existing.contributing_lessons[-20:]
                    await self._memory.store_pattern(existing)
                    patterns_updated += 1
                else:
                    # Create new emerging pattern
                    pattern = DesignPattern(
                        name=pattern_name,
                        description=lesson.summary,
                        categories=[category],
                        strength=PatternStrength.EMERGING,
                        applicable_slide_types=[lesson.slide_type] if lesson.slide_type else [],
                        applicable_audiences=[lesson.audience_type] if lesson.audience_type else [],
                        applicable_purposes=[lesson.purpose] if lesson.purpose else [],
                        occurrence_count=1,
                        avg_quality_score=quality_score,
                        quality_scores=[quality_score],
                        contributing_lessons=[lesson.id],
                    )
                    await self._memory.store_pattern(pattern)
                    patterns_updated += 1

        return patterns_updated

    def _derive_pattern_name(self, lesson: DesignLesson) -> str:
        """Derive a pattern name from a lesson."""
        parts = [lesson.category.value]
        if lesson.slide_type:
            parts.append(lesson.slide_type)
        # Create a stable short name
        summary_words = lesson.summary.lower().split()[:4]
        parts.extend(summary_words)
        return "_".join(parts)[:80]

    # ── GENERATION RECORD ─────────────────────────────────────

    def _build_generation_record(
        self,
        context: AgentContext,
        result: Dict[str, Any],
    ) -> GenerationRecord:
        """Build a generation record from context + result."""
        prev = context.previous_outputs

        # Extract QA feedback
        qa_output = prev.get(AgentType.QA) or prev.get("qa")
        qa_issues: List[str] = []
        qa_recommendations: List[str] = []
        if qa_output and isinstance(qa_output, AgentOutput):
            qa_issues = qa_output.output.get("issues", [])
            qa_recommendations = qa_output.output.get("recommendations", [])

        # Extract design choices
        designer_output = prev.get(AgentType.DESIGNER) or prev.get("designer")
        design_choices = {}
        if designer_output and isinstance(designer_output, AgentOutput):
            design_choices = designer_output.output or {}

        # Extract slide types
        code_output = prev.get(AgentType.CODE_AGENT) or prev.get("code_agent")
        slide_types: List[str] = []
        if code_output and isinstance(code_output, AgentOutput):
            slide_types = code_output.output.get("slide_types", [])

        return GenerationRecord(
            presentation_id=context.task_id,
            user_id=context.user_id,
            topic=context.topic,
            purpose=context.purpose,
            audience=context.audience,
            slide_count=context.slide_count,
            quality_score=result.get("quality_score", 0),
            quality_passed=result.get("quality_passed", False),
            design_choices=design_choices,
            slide_types_used=slide_types,
            total_latency_ms=result.get("total_latency_ms", 0),
            qa_issues=qa_issues,
            qa_recommendations=qa_recommendations,
            agent_metrics=result.get("agent_metrics", {}),
        )

    # ── HISTORICAL CONTEXT ────────────────────────────────────

    async def _write_historical_context(
        self,
        context_board: "ContextBoard",
    ) -> None:
        """
        Write historical learning context to the Context Board
        so the next generation's agents can access it.
        Like Hermes build_system_prompt() enriching future prompts.
        """
        try:
            recent = await self._memory.get_recent_records(limit=10)
            if not recent:
                return

            avg_score = sum(r.quality_score for r in recent) / len(recent)
            trend = await self._memory.get_quality_trend()

            # Collect common issues across recent generations
            all_issues: List[str] = []
            for r in recent[:5]:
                all_issues.extend(r.qa_issues[:3])

            # Deduplicate
            seen = set()
            unique_issues = []
            for issue in all_issues:
                key = issue.lower().strip()
                if key not in seen:
                    seen.add(key)
                    unique_issues.append(issue)

            historical = {
                "avg_score": round(avg_score, 1),
                "trend": trend,
                "total_generations": self._memory.generation_count,
                "top_issues": unique_issues[:10],
            }

            await context_board.set(
                "learning:recent_feedback",
                historical,
                "learning_engine",
            )
        except Exception as e:
            logger.warning("historical_context_write_failed", error=str(e))

    # ── UTILITY ───────────────────────────────────────────────

    @property
    def memory(self) -> DesignMemory:
        """Access the underlying Design Memory store."""
        return self._memory
