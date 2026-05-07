"""
Design Memory — Persistent design knowledge store (MongoDB-backed).

Inspired by Hermes Agent's MemoryManager + MEMORY.md/USER.md pattern.
Instead of flat files, uses MongoDB for structured storage and retrieval.

Responsibilities:
- Store and retrieve DesignLessons from generation experiences
- Detect and manage DesignPatterns across generations
- Provide relevant lessons for injection into agent prompts
- Track learning evolution over time via LearningSnapshots
- Semantic search via ChromaDB for contextual lesson retrieval
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.slides_new.learning.models import (
    DesignLesson,
    DesignPattern,
    GenerationRecord,
    LearningSnapshot,
    LessonCategory,
    LessonSentiment,
    PatternStrength,
    TeacherFeedback,
)

logger = structlog.get_logger()

# MongoDB collection names
LESSONS_COLLECTION = "design_lessons"
PATTERNS_COLLECTION = "design_patterns"
SNAPSHOTS_COLLECTION = "learning_snapshots"
GENERATION_RECORDS_COLLECTION = "generation_records"
TEACHER_FEEDBACK_COLLECTION = "teacher_feedback"

# Limits
MAX_LESSONS_PER_QUERY = 15
MAX_PATTERNS_PER_QUERY = 10
SNAPSHOT_INTERVAL = 20  # Take snapshot every N generations


class DesignMemory:
    """
    Persistent design knowledge store.

    Like Hermes' MemoryStore manages MEMORY.md + USER.md,
    DesignMemory manages lessons + patterns in MongoDB with
    optional ChromaDB for semantic retrieval.

    Usage:
        memory = DesignMemory(db)
        await memory.initialize()

        # After generation — store lessons
        await memory.store_lessons(teacher_feedback.lessons_learned)

        # Before generation — retrieve relevant lessons
        lessons = await memory.get_relevant_lessons(
            slide_type="title-hero",
            audience="VCs",
            purpose="fundraising",
        )
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        chroma_service: Optional[Any] = None,
    ) -> None:
        self.db = db
        self._chroma = chroma_service

        # Collections
        self._lessons = db[LESSONS_COLLECTION]
        self._patterns = db[PATTERNS_COLLECTION]
        self._snapshots = db[SNAPSHOTS_COLLECTION]
        self._records = db[GENERATION_RECORDS_COLLECTION]
        self._teacher_fb = db[TEACHER_FEEDBACK_COLLECTION]

        # In-memory cache (like Hermes prefetch)
        self._generation_count: int = 0
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize indexes and load generation count.
        Call once at startup (like Hermes initialize_all()).
        """
        if self._initialized:
            return

        # Create indexes for efficient queries
        await self._lessons.create_index("category")
        await self._lessons.create_index("slide_type")
        await self._lessons.create_index("audience_type")
        await self._lessons.create_index("purpose")
        await self._lessons.create_index("confidence", pymongo_kwargs={"sparse": True})
        await self._lessons.create_index(
            [("slide_type", 1), ("category", 1), ("confidence", -1)]
        )

        await self._patterns.create_index("name", unique=True)
        await self._patterns.create_index("applicable_slide_types")
        await self._patterns.create_index("strength")

        await self._records.create_index("presentation_id", unique=True)
        await self._records.create_index("created_at")

        # Load generation count
        self._generation_count = await self._records.count_documents({})
        self._initialized = True

        logger.info(
            "design_memory_initialized",
            generation_count=self._generation_count,
            lessons=await self._lessons.count_documents({}),
            patterns=await self._patterns.count_documents({}),
        )

    # ── LESSON STORAGE ────────────────────────────────────────

    async def store_lesson(self, lesson: DesignLesson) -> None:
        """Store a single design lesson."""
        doc = lesson.model_dump(mode="json")
        doc["_id"] = lesson.id
        await self._lessons.update_one(
            {"_id": lesson.id},
            {"$set": doc},
            upsert=True,
        )
        logger.debug(
            "lesson_stored",
            id=lesson.id,
            category=lesson.category.value,
            sentiment=lesson.sentiment.value,
        )

    async def store_lessons(self, lessons: List[DesignLesson]) -> int:
        """Store multiple lessons. Returns count stored."""
        if not lessons:
            return 0
        stored = 0
        for lesson in lessons:
            try:
                await self.store_lesson(lesson)
                stored += 1
            except Exception as e:
                logger.warning("lesson_store_failed", id=lesson.id, error=str(e))
        return stored

    async def get_lesson(self, lesson_id: str) -> Optional[DesignLesson]:
        """Retrieve a lesson by ID."""
        doc = await self._lessons.find_one({"_id": lesson_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return DesignLesson.model_validate(doc)

    # ── LESSON RETRIEVAL ──────────────────────────────────────

    async def get_relevant_lessons(
        self,
        slide_type: Optional[str] = None,
        audience: Optional[str] = None,
        purpose: Optional[str] = None,
        categories: Optional[List[LessonCategory]] = None,
        sentiment: Optional[LessonSentiment] = None,
        min_confidence: float = 0.3,
        limit: int = MAX_LESSONS_PER_QUERY,
    ) -> List[DesignLesson]:
        """
        Retrieve lessons relevant to the current generation context.

        Prioritizes:
        1. Exact slide_type match
        2. Audience/purpose match
        3. Global lessons (no slide_type)
        4. Higher confidence
        """
        query: Dict[str, Any] = {"confidence": {"$gte": min_confidence}}

        if categories:
            query["category"] = {"$in": [c.value for c in categories]}
        if sentiment:
            query["sentiment"] = sentiment.value

        # Build an OR query: exact match || global
        or_conditions = []
        if slide_type:
            or_conditions.append({"slide_type": slide_type})
        or_conditions.append({"slide_type": None})

        if audience:
            or_conditions.append({"audience_type": audience})
        if purpose:
            or_conditions.append({"purpose": purpose})

        if or_conditions:
            query["$or"] = or_conditions

        cursor = (
            self._lessons
            .find(query)
            .sort([("confidence", -1), ("quality_delta", -1)])
            .limit(limit)
        )

        lessons = []
        async for doc in cursor:
            doc.pop("_id", None)
            try:
                lessons.append(DesignLesson.model_validate(doc))
            except Exception:
                continue
        return lessons

    async def get_lessons_for_prompt(
        self,
        slide_type: Optional[str] = None,
        audience: Optional[str] = None,
        purpose: Optional[str] = None,
        max_lines: int = 15,
    ) -> str:
        """
        Get lessons formatted for injection into agent prompts.
        Returns a concise text block.
        """
        lessons = await self.get_relevant_lessons(
            slide_type=slide_type,
            audience=audience,
            purpose=purpose,
            min_confidence=0.4,
            limit=max_lines,
        )
        if not lessons:
            return ""

        lines = ["## Design Lessons (Learned from Past Generations)"]
        positive = [l for l in lessons if l.sentiment == LessonSentiment.POSITIVE]
        negative = [l for l in lessons if l.sentiment == LessonSentiment.NEGATIVE]

        if positive:
            lines.append("### Best Practices")
            for lesson in positive[:8]:
                lines.append(lesson.to_prompt_line())

        if negative:
            lines.append("### Avoid These")
            for lesson in negative[:7]:
                lines.append(lesson.to_prompt_line())

        return "\n".join(lines)

    # ── LESSON EVOLUTION ──────────────────────────────────────

    async def record_lesson_application(
        self,
        lesson_id: str,
        quality_improved: bool,
    ) -> None:
        """
        Record that a lesson was applied in a generation.
        Track whether it actually helped (like Hermes skill self-improvement).
        """
        update: Dict[str, Any] = {
            "$inc": {"times_applied": 1},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
        }
        if quality_improved:
            update["$inc"]["times_validated"] = 1

        await self._lessons.update_one({"_id": lesson_id}, update)

    async def decay_stale_lessons(self, max_age_days: int = 90) -> int:
        """
        Reduce confidence of old, unvalidated lessons.
        Like Hermes memory pruning — prevent stale knowledge from dominating.
        """
        cutoff = datetime.now(timezone.utc)
        # Reduce confidence by 10% for lessons not validated recently
        result = await self._lessons.update_many(
            {
                "times_validated": 0,
                "times_applied": {"$gte": 3},
                "confidence": {"$gt": 0.2},
            },
            {"$mul": {"confidence": 0.9}},
        )
        return result.modified_count

    # ── PATTERN MANAGEMENT ────────────────────────────────────

    async def store_pattern(self, pattern: DesignPattern) -> None:
        """Store or update a design pattern."""
        doc = pattern.model_dump(mode="json")
        doc["_id"] = pattern.id
        await self._patterns.update_one(
            {"name": pattern.name},
            {"$set": doc},
            upsert=True,
        )
        logger.debug(
            "pattern_stored",
            name=pattern.name,
            strength=pattern.strength.value,
            occurrences=pattern.occurrence_count,
        )

    async def get_pattern(self, name: str) -> Optional[DesignPattern]:
        """Retrieve a pattern by name."""
        doc = await self._patterns.find_one({"name": name})
        if doc is None:
            return None
        doc.pop("_id", None)
        return DesignPattern.model_validate(doc)

    async def get_relevant_patterns(
        self,
        slide_types: Optional[List[str]] = None,
        audience: Optional[str] = None,
        purpose: Optional[str] = None,
        min_strength: PatternStrength = PatternStrength.EMERGING,
        limit: int = MAX_PATTERNS_PER_QUERY,
    ) -> List[DesignPattern]:
        """Retrieve patterns relevant to the current generation."""
        strength_order = {
            PatternStrength.EMERGING: 0,
            PatternStrength.ESTABLISHED: 1,
            PatternStrength.PROVEN: 2,
            PatternStrength.DECLINING: 3,
        }
        min_order = strength_order.get(min_strength, 0)
        valid_strengths = [
            s.value for s, o in strength_order.items()
            if o >= min_order and s != PatternStrength.DECLINING
        ]

        query: Dict[str, Any] = {"strength": {"$in": valid_strengths}}

        if slide_types:
            query["applicable_slide_types"] = {"$in": slide_types}

        cursor = (
            self._patterns
            .find(query)
            .sort("avg_quality_score", -1)
            .limit(limit)
        )

        patterns = []
        async for doc in cursor:
            doc.pop("_id", None)
            try:
                patterns.append(DesignPattern.model_validate(doc))
            except Exception:
                continue
        return patterns

    async def get_patterns_for_prompt(
        self,
        slide_types: Optional[List[str]] = None,
        audience: Optional[str] = None,
        purpose: Optional[str] = None,
    ) -> str:
        """Get patterns formatted for prompt injection."""
        patterns = await self.get_relevant_patterns(
            slide_types=slide_types,
            audience=audience,
            purpose=purpose,
            min_strength=PatternStrength.ESTABLISHED,
            limit=5,
        )
        if not patterns:
            return ""

        lines = ["## Proven Design Patterns (Learned)"]
        for p in patterns:
            scope = ", ".join(p.applicable_slide_types[:3]) if p.applicable_slide_types else "all"
            lines.append(
                f"- **{p.name}** ({p.strength.value}, avg {p.avg_quality_score:.0f}/100): "
                f"{p.description} [for: {scope}]"
            )
        return "\n".join(lines)

    # ── GENERATION RECORDS ────────────────────────────────────

    async def store_generation_record(self, record: GenerationRecord) -> None:
        """Store a generation record for future analysis."""
        doc = record.model_dump(mode="json")
        doc["_id"] = record.presentation_id
        await self._records.update_one(
            {"_id": record.presentation_id},
            {"$set": doc},
            upsert=True,
        )
        self._generation_count += 1

    async def get_recent_records(
        self,
        limit: int = 20,
    ) -> List[GenerationRecord]:
        """Get recent generation records for trend analysis."""
        cursor = (
            self._records
            .find()
            .sort("created_at", -1)
            .limit(limit)
        )
        records = []
        async for doc in cursor:
            doc.pop("_id", None)
            try:
                records.append(GenerationRecord.model_validate(doc))
            except Exception:
                continue
        return records

    async def get_quality_trend(self, window: int = 20) -> str:
        """Determine if quality is improving, stable, or declining."""
        records = await self.get_recent_records(limit=window)
        if len(records) < 4:
            return "insufficient_data"

        scores = [r.quality_score for r in records]
        first_half = scores[len(scores) // 2:]  # Older (records are newest-first)
        second_half = scores[:len(scores) // 2]  # Newer

        avg_old = sum(first_half) / len(first_half) if first_half else 0
        avg_new = sum(second_half) / len(second_half) if second_half else 0

        delta = avg_new - avg_old
        if delta > 3.0:
            return "improving"
        elif delta < -3.0:
            return "declining"
        return "stable"

    # ── TEACHER FEEDBACK ──────────────────────────────────────

    async def store_teacher_feedback(self, feedback: TeacherFeedback) -> None:
        """Store Teacher Agent feedback."""
        doc = feedback.model_dump(mode="json")
        doc["_id"] = feedback.id
        await self._teacher_fb.update_one(
            {"_id": feedback.id},
            {"$set": doc},
            upsert=True,
        )

    async def get_latest_teacher_feedback(
        self,
        limit: int = 5,
    ) -> List[TeacherFeedback]:
        """Get most recent Teacher feedback for trend analysis."""
        cursor = (
            self._teacher_fb
            .find()
            .sort("created_at", -1)
            .limit(limit)
        )
        feedbacks = []
        async for doc in cursor:
            doc.pop("_id", None)
            try:
                feedbacks.append(TeacherFeedback.model_validate(doc))
            except Exception:
                continue
        return feedbacks

    # ── SNAPSHOTS ─────────────────────────────────────────────

    async def take_snapshot(self) -> LearningSnapshot:
        """
        Take a point-in-time snapshot of learning state.
        Like Hermes flush_memories() — persist current knowledge state.
        """
        total_lessons = await self._lessons.count_documents({})
        total_patterns = await self._patterns.count_documents({})
        total_records = await self._records.count_documents({})

        # Calculate averages
        pipeline = [
            {"$group": {"_id": None, "avg": {"$avg": "$quality_score"}}}
        ]
        cursor = self._records.aggregate(pipeline)
        avg_all = 0.0
        async for doc in cursor:
            avg_all = doc.get("avg", 0.0)

        recent = await self.get_recent_records(limit=20)
        avg_recent = (
            sum(r.quality_score for r in recent) / len(recent)
            if recent
            else 0.0
        )

        trend = await self.get_quality_trend()

        # Top patterns
        top_pattern_docs = (
            self._patterns
            .find({"strength": {"$in": ["proven", "established"]}})
            .sort("avg_quality_score", -1)
            .limit(5)
        )
        top_patterns = []
        async for doc in top_pattern_docs:
            top_patterns.append(doc.get("name", "unknown"))

        # Most impactful lessons
        impact_cursor = (
            self._lessons
            .find({"confidence": {"$gte": 0.7}})
            .sort([("quality_delta", -1)])
            .limit(5)
        )
        impactful = []
        async for doc in impact_cursor:
            impactful.append(doc.get("summary", ""))

        snapshot = LearningSnapshot(
            total_presentations_analyzed=total_records,
            total_lessons=total_lessons,
            total_patterns=total_patterns,
            avg_quality_all_time=avg_all,
            avg_quality_recent=avg_recent,
            quality_trend=trend,
            top_patterns=top_patterns,
            most_impactful_lessons=impactful,
        )

        # Store snapshot
        doc = snapshot.model_dump(mode="json")
        doc["_id"] = snapshot.id
        await self._snapshots.insert_one(doc)

        logger.info(
            "learning_snapshot_taken",
            total_lessons=total_lessons,
            total_patterns=total_patterns,
            avg_quality=round(avg_recent, 1),
            trend=trend,
        )

        return snapshot

    @property
    def generation_count(self) -> int:
        """How many generations have been analyzed."""
        return self._generation_count

    @property
    def should_snapshot(self) -> bool:
        """Whether it's time to take a learning snapshot (like Hermes nudge)."""
        return self._generation_count > 0 and (
            self._generation_count % SNAPSHOT_INTERVAL == 0
        )
