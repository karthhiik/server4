#!/usr/bin/env python3
"""
Phase 12 Tests -- Self-Learning System (Teacher Agent + Design Memory + Learning Engine).

100 tests covering all learning system modules + integration:
    Tests  1-20:  Learning Models (DesignLesson, DesignPattern, TeacherFeedback, etc.)
    Tests 21-40:  Design Memory (store, retrieve, evolve lessons + patterns)
    Tests 41-60:  Teacher Agent (evaluation, lesson extraction, prompt building)
    Tests 61-80:  Learning Engine (full cycle, pattern detection, snapshots)
    Tests 81-100: Integration (V7 orchestrator, Designer/Code agent wiring, AgentType/Factory)

Run:
    cd server4
    python test_phase12.py
"""

import sys
import os
import json
import time
import asyncio
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name: str):
        self.passed += 1
        print(f"  [PASS] {name}")

    def fail(self, name: str, reason: str):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  [FAIL] {name}: {reason}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Phase 12 Tests: {self.passed}/{total} passed")
        if self.errors:
            print("\nFailures:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0


results = TestResult()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: Learning Models (Tests 1-20)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 1: Learning Models ===")

# Test 1: Import learning models
try:
    from app.services.slides_new.learning.models import (
        DesignLesson,
        DesignPattern,
        GenerationRecord,
        LearningSnapshot,
        LessonCategory,
        LessonSentiment,
        PatternStrength,
        TeacherDimension,
        TeacherFeedback,
    )
    results.ok("T1: Import learning models")
except Exception as e:
    results.fail("T1: Import learning models", str(e))

# Test 2: LessonCategory enum values
try:
    assert len(LessonCategory) >= 16, f"Expected >= 16 categories, got {len(LessonCategory)}"
    assert LessonCategory.COLOR_PALETTE == "color_palette"
    assert LessonCategory.TYPOGRAPHY == "typography"
    assert LessonCategory.BACKGROUND == "background"
    assert LessonCategory.EMOTIONAL_IMPACT == "emotional_impact"
    results.ok("T2: LessonCategory enum values")
except Exception as e:
    results.fail("T2: LessonCategory enum values", str(e))

# Test 3: LessonSentiment enum
try:
    assert LessonSentiment.POSITIVE == "positive"
    assert LessonSentiment.NEGATIVE == "negative"
    assert LessonSentiment.NEUTRAL == "neutral"
    results.ok("T3: LessonSentiment enum values")
except Exception as e:
    results.fail("T3: LessonSentiment enum values", str(e))

# Test 4: PatternStrength enum
try:
    assert PatternStrength.EMERGING == "emerging"
    assert PatternStrength.ESTABLISHED == "established"
    assert PatternStrength.PROVEN == "proven"
    assert PatternStrength.DECLINING == "declining"
    results.ok("T4: PatternStrength enum values")
except Exception as e:
    results.fail("T4: PatternStrength enum values", str(e))

# Test 5: Create DesignLesson
try:
    lesson = DesignLesson(
        category=LessonCategory.COLOR_PALETTE,
        sentiment=LessonSentiment.POSITIVE,
        summary="Dark gradients with glass cards scored higher for fintech pitches",
        slide_type="title-hero",
        quality_delta=12.5,
        confidence=0.8,
    )
    assert lesson.id.startswith("lesson_")
    assert lesson.category == LessonCategory.COLOR_PALETTE
    assert lesson.sentiment == LessonSentiment.POSITIVE
    assert lesson.quality_delta == 12.5
    results.ok("T5: Create DesignLesson")
except Exception as e:
    results.fail("T5: Create DesignLesson", str(e))

# Test 6: DesignLesson to_prompt_line
try:
    lesson = DesignLesson(
        category=LessonCategory.LAYOUT,
        sentiment=LessonSentiment.NEGATIVE,
        summary="3-column layouts with team photos need minimum 1200px width",
        slide_type="team",
        confidence=0.9,
    )
    line = lesson.to_prompt_line()
    assert "AVOID" in line
    assert "[team]" in line
    assert "3-column" in line
    assert "90%" in line
    results.ok("T6: DesignLesson to_prompt_line")
except Exception as e:
    results.fail("T6: DesignLesson to_prompt_line", str(e))

# Test 7: DesignLesson effectiveness_rate
try:
    lesson = DesignLesson(
        category=LessonCategory.SPACING,
        sentiment=LessonSentiment.POSITIVE,
        summary="More whitespace improves readability",
        times_applied=10,
        times_validated=7,
    )
    assert lesson.effectiveness_rate == 0.7
    lesson_zero = DesignLesson(
        category=LessonCategory.SPACING,
        sentiment=LessonSentiment.POSITIVE,
        summary="Unused lesson",
        times_applied=0,
    )
    assert lesson_zero.effectiveness_rate == 0.0
    results.ok("T7: DesignLesson effectiveness_rate")
except Exception as e:
    results.fail("T7: DesignLesson effectiveness_rate", str(e))

# Test 8: Create DesignPattern
try:
    pattern = DesignPattern(
        name="dark_gradient_glass_card",
        description="Dark gradient background with glass-morphism cards",
        categories=[LessonCategory.BACKGROUND, LessonCategory.LAYOUT],
        applicable_slide_types=["title-hero", "ask"],
        occurrence_count=5,
        avg_quality_score=88.5,
    )
    assert pattern.id.startswith("pattern_")
    assert pattern.strength == PatternStrength.EMERGING
    assert len(pattern.categories) == 2
    results.ok("T8: Create DesignPattern")
except Exception as e:
    results.fail("T8: Create DesignPattern", str(e))

# Test 9: DesignPattern record_usage
try:
    pattern = DesignPattern(
        name="test_pattern",
        description="Test",
        occurrence_count=3,
        quality_scores=[80, 85, 90],
    )
    pattern.record_usage(92)
    assert pattern.occurrence_count == 4
    assert len(pattern.quality_scores) == 4
    assert pattern.avg_quality_score > 0
    assert pattern.strength == PatternStrength.ESTABLISHED
    results.ok("T9: DesignPattern record_usage and strength update")
except Exception as e:
    results.fail("T9: DesignPattern record_usage and strength update", str(e))

# Test 10: DesignPattern strength evolution to PROVEN
try:
    pattern = DesignPattern(
        name="proven_pattern",
        description="Test proven",
        occurrence_count=9,
        quality_scores=[80, 82, 85, 88, 90, 87, 85, 88, 92],
    )
    pattern.record_usage(91)
    assert pattern.occurrence_count == 10
    assert pattern.strength == PatternStrength.PROVEN
    results.ok("T10: DesignPattern strength evolution to PROVEN")
except Exception as e:
    results.fail("T10: DesignPattern strength evolution to PROVEN", str(e))

# Test 11: DesignPattern strength DECLINING detection
try:
    pattern = DesignPattern(
        name="declining_pattern",
        description="Once good now bad",
        occurrence_count=7,
        quality_scores=[80, 85, 88, 65, 60, 55, 50],
    )
    pattern.record_usage(45)
    # Last 5 scores: [60, 55, 50, 45] — last 3 of those are all < 70
    assert pattern.strength == PatternStrength.DECLINING
    results.ok("T11: DesignPattern DECLINING detection")
except Exception as e:
    results.fail("T11: DesignPattern DECLINING detection", str(e))

# Test 12: DesignPattern quality_scores cap at 50
try:
    pattern = DesignPattern(
        name="capped_pattern",
        description="Test cap",
        quality_scores=list(range(55)),
    )
    pattern.record_usage(99)
    assert len(pattern.quality_scores) <= 51  # 50 + 1 new, then trimmed to 50
    results.ok("T12: DesignPattern quality_scores capped")
except Exception as e:
    results.fail("T12: DesignPattern quality_scores capped", str(e))

# Test 13: TeacherDimension creation
try:
    dim = TeacherDimension(
        name="Visual Cohesion",
        score=85.5,
        grade="A",
        observations=["Consistent color palette across all slides"],
        recommendations=["Add more gradient variation on data slides"],
    )
    assert dim.name == "Visual Cohesion"
    assert dim.score == 85.5
    results.ok("T13: TeacherDimension creation")
except Exception as e:
    results.fail("T13: TeacherDimension creation", str(e))

# Test 14: TeacherFeedback creation
try:
    fb = TeacherFeedback(
        presentation_id="test_pres_123",
        overall_score=82.0,
        overall_grade="B",
        cohesion_score=88.0,
        narrative_flow_score=79.0,
        brand_consistency_score=85.0,
        style_directives=["Use gradient backgrounds on all slides"],
        anti_patterns=["Avoid flat white backgrounds"],
    )
    assert fb.id.startswith("teach_")
    assert fb.presentation_id == "test_pres_123"
    assert len(fb.style_directives) == 1
    results.ok("T14: TeacherFeedback creation")
except Exception as e:
    results.fail("T14: TeacherFeedback creation", str(e))

# Test 15: TeacherFeedback to_prompt_context
try:
    fb = TeacherFeedback(
        presentation_id="test_pres",
        overall_score=85.0,
        overall_grade="A",
        cohesion_score=90.0,
        narrative_flow_score=80.0,
        style_directives=["Use dark themes for VC pitches"],
        anti_patterns=["Avoid generic stock images"],
    )
    prompt = fb.to_prompt_context()
    assert "Teacher Feedback" in prompt
    assert "A (85/100)" in prompt
    assert "dark themes" in prompt
    assert "stock images" in prompt
    results.ok("T15: TeacherFeedback to_prompt_context")
except Exception as e:
    results.fail("T15: TeacherFeedback to_prompt_context", str(e))

# Test 16: LearningSnapshot creation
try:
    snap = LearningSnapshot(
        total_presentations_analyzed=50,
        total_lessons=120,
        total_patterns=15,
        avg_quality_all_time=78.5,
        avg_quality_recent=82.0,
        quality_trend="improving",
    )
    assert snap.id.startswith("snap_")
    assert snap.quality_trend == "improving"
    results.ok("T16: LearningSnapshot creation")
except Exception as e:
    results.fail("T16: LearningSnapshot creation", str(e))

# Test 17: GenerationRecord creation
try:
    record = GenerationRecord(
        presentation_id="gen_test_1",
        user_id="user_1",
        topic="AI Startup Pitch",
        purpose="fundraising",
        audience="VCs",
        slide_count=10,
        quality_score=87.5,
        quality_passed=True,
        slide_types_used=["title-hero", "problem", "solution"],
    )
    assert record.presentation_id == "gen_test_1"
    assert record.quality_score == 87.5
    assert len(record.slide_types_used) == 3
    results.ok("T17: GenerationRecord creation")
except Exception as e:
    results.fail("T17: GenerationRecord creation", str(e))

# Test 18: DesignLesson model_dump (serialization)
try:
    lesson = DesignLesson(
        category=LessonCategory.IMAGERY,
        sentiment=LessonSentiment.POSITIVE,
        summary="Abstract geometric images work better than stock photos",
    )
    dumped = lesson.model_dump(mode="json")
    assert isinstance(dumped, dict)
    assert dumped["category"] == "imagery"
    assert dumped["sentiment"] == "positive"
    assert "summary" in dumped
    results.ok("T18: DesignLesson model_dump serialization")
except Exception as e:
    results.fail("T18: DesignLesson model_dump serialization", str(e))

# Test 19: DesignPattern model_dump (serialization)
try:
    pattern = DesignPattern(
        name="test_serialize",
        description="Test serialization",
        categories=[LessonCategory.BACKGROUND],
        strength=PatternStrength.ESTABLISHED,
    )
    dumped = pattern.model_dump(mode="json")
    assert dumped["name"] == "test_serialize"
    assert dumped["strength"] == "established"
    results.ok("T19: DesignPattern model_dump serialization")
except Exception as e:
    results.fail("T19: DesignPattern model_dump serialization", str(e))

# Test 20: DesignLesson positive prompt line
try:
    lesson = DesignLesson(
        category=LessonCategory.CONTRAST,
        sentiment=LessonSentiment.POSITIVE,
        summary="High contrast text on dark backgrounds improves readability",
        confidence=0.75,
    )
    line = lesson.to_prompt_line()
    assert "DO:" in line
    assert "75%" in line
    results.ok("T20: DesignLesson positive to_prompt_line")
except Exception as e:
    results.fail("T20: DesignLesson positive to_prompt_line", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: Design Memory (Tests 21-40)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 2: Design Memory ===")

# Test 21: Import DesignMemory
try:
    from app.services.slides_new.learning.design_memory import (
        DesignMemory,
        LESSONS_COLLECTION,
        PATTERNS_COLLECTION,
        SNAPSHOTS_COLLECTION,
        GENERATION_RECORDS_COLLECTION,
        TEACHER_FEEDBACK_COLLECTION,
        MAX_LESSONS_PER_QUERY,
        SNAPSHOT_INTERVAL,
    )
    results.ok("T21: Import DesignMemory")
except Exception as e:
    results.fail("T21: Import DesignMemory", str(e))

# Test 22: Collection names are strings
try:
    assert isinstance(LESSONS_COLLECTION, str)
    assert isinstance(PATTERNS_COLLECTION, str)
    assert isinstance(SNAPSHOTS_COLLECTION, str)
    assert LESSONS_COLLECTION == "design_lessons"
    assert PATTERNS_COLLECTION == "design_patterns"
    results.ok("T22: Collection names correct")
except Exception as e:
    results.fail("T22: Collection names correct", str(e))

# Test 23: Constants are reasonable
try:
    assert MAX_LESSONS_PER_QUERY == 15
    assert SNAPSHOT_INTERVAL == 20
    results.ok("T23: Constants correct values")
except Exception as e:
    results.fail("T23: Constants correct values", str(e))

# Test 24: DesignMemory construction
try:
    from unittest.mock import MagicMock, AsyncMock
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=MagicMock())
    memory = DesignMemory(mock_db)
    assert memory.db is mock_db
    assert memory._initialized is False
    assert memory.generation_count == 0
    results.ok("T24: DesignMemory construction")
except Exception as e:
    results.fail("T24: DesignMemory construction", str(e))

# Test 25: DesignMemory should_snapshot property
try:
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=MagicMock())
    memory = DesignMemory(mock_db)
    memory._generation_count = 0
    assert memory.should_snapshot is False
    memory._generation_count = 20
    assert memory.should_snapshot is True
    memory._generation_count = 19
    assert memory.should_snapshot is False
    memory._generation_count = 40
    assert memory.should_snapshot is True
    results.ok("T25: DesignMemory should_snapshot logic")
except Exception as e:
    results.fail("T25: DesignMemory should_snapshot logic", str(e))

# Test 26: DesignMemory generation_count property
try:
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=MagicMock())
    memory = DesignMemory(mock_db)
    memory._generation_count = 42
    assert memory.generation_count == 42
    results.ok("T26: DesignMemory generation_count property")
except Exception as e:
    results.fail("T26: DesignMemory generation_count property", str(e))

# Test 27: DesignMemory with chroma service
try:
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=MagicMock())
    mock_chroma = MagicMock()
    memory = DesignMemory(mock_db, chroma_service=mock_chroma)
    assert memory._chroma is mock_chroma
    results.ok("T27: DesignMemory with ChromaDB service")
except Exception as e:
    results.fail("T27: DesignMemory with ChromaDB service", str(e))

# Test 28: DesignMemory store_lesson (async mock)
try:
    async def test_store_lesson():
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        memory = DesignMemory(mock_db)

        lesson = DesignLesson(
            category=LessonCategory.COLOR_PALETTE,
            sentiment=LessonSentiment.POSITIVE,
            summary="Blue gradients work well for tech companies",
        )
        await memory.store_lesson(lesson)
        mock_collection.update_one.assert_called_once()

    asyncio.get_event_loop().run_until_complete(test_store_lesson())
    results.ok("T28: DesignMemory store_lesson")
except Exception as e:
    results.fail("T28: DesignMemory store_lesson", str(e))

# Test 29: DesignMemory store_lessons batch
try:
    async def test_store_lessons_batch():
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        memory = DesignMemory(mock_db)

        lessons = [
            DesignLesson(
                category=LessonCategory.LAYOUT,
                sentiment=LessonSentiment.POSITIVE,
                summary=f"Test lesson {i}",
            )
            for i in range(5)
        ]
        count = await memory.store_lessons(lessons)
        assert count == 5

    asyncio.get_event_loop().run_until_complete(test_store_lessons_batch())
    results.ok("T29: DesignMemory store_lessons batch")
except Exception as e:
    results.fail("T29: DesignMemory store_lessons batch", str(e))

# Test 30: DesignMemory store_pattern
try:
    async def test_store_pattern():
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        memory = DesignMemory(mock_db)

        pattern = DesignPattern(
            name="glass_card_dark",
            description="Glass morphism cards on dark background",
        )
        await memory.store_pattern(pattern)
        mock_collection.update_one.assert_called_once()

    asyncio.get_event_loop().run_until_complete(test_store_pattern())
    results.ok("T30: DesignMemory store_pattern")
except Exception as e:
    results.fail("T30: DesignMemory store_pattern", str(e))

# Test 31: DesignMemory store_generation_record
try:
    async def test_store_record():
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        memory = DesignMemory(mock_db)

        record = GenerationRecord(
            presentation_id="test_gen_1",
            user_id="user_1",
            topic="Test Topic",
            purpose="testing",
            audience="testers",
            slide_count=10,
            quality_score=85.0,
            quality_passed=True,
        )
        await memory.store_generation_record(record)
        assert memory.generation_count == 1

    asyncio.get_event_loop().run_until_complete(test_store_record())
    results.ok("T31: DesignMemory store_generation_record")
except Exception as e:
    results.fail("T31: DesignMemory store_generation_record", str(e))

# Test 32: DesignMemory store_teacher_feedback
try:
    async def test_store_feedback():
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        memory = DesignMemory(mock_db)

        fb = TeacherFeedback(
            presentation_id="test_pres",
            overall_score=88.0,
            overall_grade="A",
        )
        await memory.store_teacher_feedback(fb)
        mock_collection.update_one.assert_called_once()

    asyncio.get_event_loop().run_until_complete(test_store_feedback())
    results.ok("T32: DesignMemory store_teacher_feedback")
except Exception as e:
    results.fail("T32: DesignMemory store_teacher_feedback", str(e))

# Test 33: DesignMemory record_lesson_application
try:
    async def test_record_application():
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        memory = DesignMemory(mock_db)

        await memory.record_lesson_application("lesson_abc", quality_improved=True)
        mock_collection.update_one.assert_called_once()

    asyncio.get_event_loop().run_until_complete(test_record_application())
    results.ok("T33: DesignMemory record_lesson_application")
except Exception as e:
    results.fail("T33: DesignMemory record_lesson_application", str(e))

# Test 34: DesignMemory decay_stale_lessons
try:
    async def test_decay():
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_result = MagicMock()
        mock_result.modified_count = 3
        mock_collection.update_many = AsyncMock(return_value=mock_result)
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        memory = DesignMemory(mock_db)

        count = await memory.decay_stale_lessons()
        assert count == 3

    asyncio.get_event_loop().run_until_complete(test_decay())
    results.ok("T34: DesignMemory decay_stale_lessons")
except Exception as e:
    results.fail("T34: DesignMemory decay_stale_lessons", str(e))

# Test 35: DesignMemory get_lessons_for_prompt returns empty when no lessons
try:
    async def test_empty_lessons():
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        # Mock cursor that returns empty
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.__aiter__ = lambda self: self
        mock_cursor.__anext__ = AsyncMock(side_effect=StopAsyncIteration)
        mock_collection.find = MagicMock(return_value=mock_cursor)
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        memory = DesignMemory(mock_db)

        text = await memory.get_lessons_for_prompt()
        assert text == ""

    asyncio.get_event_loop().run_until_complete(test_empty_lessons())
    results.ok("T35: DesignMemory empty lessons prompt")
except Exception as e:
    results.fail("T35: DesignMemory empty lessons prompt", str(e))

# Test 36: DesignMemory get_patterns_for_prompt returns empty
try:
    async def test_empty_patterns():
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.__aiter__ = lambda self: self
        mock_cursor.__anext__ = AsyncMock(side_effect=StopAsyncIteration)
        mock_collection.find = MagicMock(return_value=mock_cursor)
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        memory = DesignMemory(mock_db)

        text = await memory.get_patterns_for_prompt()
        assert text == ""

    asyncio.get_event_loop().run_until_complete(test_empty_patterns())
    results.ok("T36: DesignMemory empty patterns prompt")
except Exception as e:
    results.fail("T36: DesignMemory empty patterns prompt", str(e))

# Test 37: DesignMemory get_quality_trend with insufficient data
try:
    async def test_trend_insufficient():
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.__aiter__ = lambda self: self
        mock_cursor.__anext__ = AsyncMock(side_effect=StopAsyncIteration)
        mock_collection.find = MagicMock(return_value=mock_cursor)
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        memory = DesignMemory(mock_db)

        trend = await memory.get_quality_trend()
        assert trend == "insufficient_data"

    asyncio.get_event_loop().run_until_complete(test_trend_insufficient())
    results.ok("T37: DesignMemory quality trend insufficient data")
except Exception as e:
    results.fail("T37: DesignMemory quality trend insufficient data", str(e))

# Test 38: DesignMemory store_lessons with empty list
try:
    async def test_store_empty():
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=MagicMock())
        memory = DesignMemory(mock_db)
        count = await memory.store_lessons([])
        assert count == 0

    asyncio.get_event_loop().run_until_complete(test_store_empty())
    results.ok("T38: DesignMemory store empty lessons list")
except Exception as e:
    results.fail("T38: DesignMemory store empty lessons list", str(e))

# Test 39: Collection constant TEACHER_FEEDBACK_COLLECTION
try:
    assert TEACHER_FEEDBACK_COLLECTION == "teacher_feedback"
    assert GENERATION_RECORDS_COLLECTION == "generation_records"
    results.ok("T39: Additional collection constants")
except Exception as e:
    results.fail("T39: Additional collection constants", str(e))

# Test 40: SNAPSHOT_INTERVAL modular arithmetic
try:
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=MagicMock())
    memory = DesignMemory(mock_db)
    memory._generation_count = 60
    assert memory.should_snapshot is True
    memory._generation_count = 61
    assert memory.should_snapshot is False
    results.ok("T40: Snapshot interval modular arithmetic")
except Exception as e:
    results.fail("T40: Snapshot interval modular arithmetic", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: Teacher Agent (Tests 41-60)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 3: Teacher Agent ===")

# Test 41: Import Teacher Agent
try:
    from app.services.slides_new.learning.teacher_agent import (
        TeacherAgent,
        TEACHER_SYSTEM_PROMPT,
        TEACHER_EVALUATION_PROMPT,
    )
    results.ok("T41: Import TeacherAgent")
except Exception as e:
    results.fail("T41: Import TeacherAgent", str(e))

# Test 42: TEACHER_SYSTEM_PROMPT contains required sections
try:
    assert "Principal Design Critic" in TEACHER_SYSTEM_PROMPT
    assert "VISUAL COHESION" in TEACHER_SYSTEM_PROMPT
    assert "NARRATIVE FLOW" in TEACHER_SYSTEM_PROMPT
    assert "ORIGINALITY" in TEACHER_SYSTEM_PROMPT
    assert "AUDIENCE FIT" in TEACHER_SYSTEM_PROMPT
    results.ok("T42: TEACHER_SYSTEM_PROMPT contains evaluation dimensions")
except Exception as e:
    results.fail("T42: TEACHER_SYSTEM_PROMPT contains evaluation dimensions", str(e))

# Test 43: TEACHER_EVALUATION_PROMPT has format placeholders
try:
    assert "{topic}" in TEACHER_EVALUATION_PROMPT
    assert "{purpose}" in TEACHER_EVALUATION_PROMPT
    assert "{audience}" in TEACHER_EVALUATION_PROMPT
    assert "{qa_score}" in TEACHER_EVALUATION_PROMPT
    assert "{strategy_summary}" in TEACHER_EVALUATION_PROMPT
    assert "{design_summary}" in TEACHER_EVALUATION_PROMPT
    assert "{historical_context}" in TEACHER_EVALUATION_PROMPT
    results.ok("T43: TEACHER_EVALUATION_PROMPT format placeholders")
except Exception as e:
    results.fail("T43: TEACHER_EVALUATION_PROMPT format placeholders", str(e))

# Test 44: TeacherAgent is a BaseAgent
try:
    from app.services.slides_new.agents.base import BaseAgent, AgentType
    assert issubclass(TeacherAgent, BaseAgent)
    results.ok("T44: TeacherAgent inherits BaseAgent")
except Exception as e:
    results.fail("T44: TeacherAgent inherits BaseAgent", str(e))

# Test 45: TeacherAgent agent_type is TEACHER
try:
    from dataclasses import fields
    from app.services.slides_new.agents.base import AgentContext, AgentOutput

    ctx = AgentContext(
        task_id="test", user_id="u1", topic="Test",
        description="", purpose="testing", audience="testers",
        slide_count=5, mode="standard",
    )
    mock_db = MagicMock()
    agent = TeacherAgent(mock_db, ctx)
    assert agent.agent_type == AgentType.TEACHER
    results.ok("T45: TeacherAgent.agent_type == TEACHER")
except Exception as e:
    results.fail("T45: TeacherAgent.agent_type == TEACHER", str(e))

# Test 46: TeacherAgent._gather_generation_data
try:
    ctx = AgentContext(
        task_id="test_task", user_id="u1", topic="AI Pitch",
        description="Test desc", purpose="fundraising", audience="VCs",
        slide_count=10, mode="standard", company_name="TestCo",
    )
    agent = TeacherAgent(MagicMock(), ctx)
    data = agent._gather_generation_data()
    assert data["topic"] == "AI Pitch"
    assert data["audience"] == "VCs"
    assert data["company_name"] == "TestCo"
    assert data["slide_count"] == 10
    results.ok("T46: TeacherAgent._gather_generation_data")
except Exception as e:
    results.fail("T46: TeacherAgent._gather_generation_data", str(e))

# Test 47: TeacherAgent._gather_generation_data with previous outputs
try:
    from app.services.slides_new.agents.base import AgentOutput

    ctx = AgentContext(
        task_id="test", user_id="u1", topic="Test",
        description="", purpose="testing", audience="testers",
        slide_count=5, mode="standard",
    )
    ceo_out = AgentOutput(
        success=True,
        agent_type=AgentType.CEO,
        output={"archetype": "yc_seed", "narrative_arc": "problem-solution"},
    )
    ctx.previous_outputs[AgentType.CEO] = ceo_out

    agent = TeacherAgent(MagicMock(), ctx)
    data = agent._gather_generation_data()
    assert data["strategy"].get("archetype") == "yc_seed"
    results.ok("T47: TeacherAgent gathers CEO output")
except Exception as e:
    results.fail("T47: TeacherAgent gathers CEO output", str(e))

# Test 48: TeacherAgent._parse_evaluation valid JSON
try:
    ctx = AgentContext(
        task_id="t1", user_id="u1", topic="T",
        description="D", purpose="P", audience="A",
        slide_count=5, mode="standard",
    )
    agent = TeacherAgent(MagicMock(), ctx)

    valid_json = json.dumps({
        "overall_score": 85.0,
        "overall_grade": "A",
        "dimensions": [
            {
                "name": "Visual Cohesion",
                "score": 82.0,
                "grade": "B",
                "observations": ["Consistent palette"],
                "recommendations": ["More gradient variety"],
            }
        ],
        "cohesion_score": 88.0,
        "narrative_flow_score": 80.0,
        "brand_consistency_score": 85.0,
        "lessons": [
            {
                "category": "color_palette",
                "sentiment": "positive",
                "summary": "Blue tones work well for tech pitches",
                "details": "Extended detail here",
                "slide_type": "title-hero",
                "quality_delta": 8.5,
            }
        ],
        "style_directives": ["Use dark gradients"],
        "anti_patterns": ["Avoid flat white"],
    })

    feedback = agent._parse_evaluation(valid_json)
    assert feedback is not None
    assert feedback.overall_score == 85.0
    assert feedback.overall_grade == "A"
    assert len(feedback.dimensions) == 1
    assert len(feedback.lessons_learned) == 1
    assert feedback.lessons_learned[0].category == LessonCategory.COLOR_PALETTE
    assert feedback.cohesion_score == 88.0
    results.ok("T48: TeacherAgent._parse_evaluation valid JSON")
except Exception as e:
    results.fail("T48: TeacherAgent._parse_evaluation valid JSON", str(e))

# Test 49: TeacherAgent._parse_evaluation invalid JSON
try:
    agent = TeacherAgent(MagicMock(), ctx)
    result = agent._parse_evaluation("not valid json {{{")
    assert result is None
    results.ok("T49: TeacherAgent._parse_evaluation invalid JSON returns None")
except Exception as e:
    results.fail("T49: TeacherAgent._parse_evaluation invalid JSON returns None", str(e))

# Test 50: TeacherAgent._parse_evaluation with invalid category
try:
    agent = TeacherAgent(MagicMock(), ctx)
    data = json.dumps({
        "overall_score": 70.0,
        "overall_grade": "B",
        "dimensions": [],
        "cohesion_score": 70.0,
        "narrative_flow_score": 70.0,
        "brand_consistency_score": 70.0,
        "lessons": [
            {
                "category": "nonexistent_category",
                "sentiment": "positive",
                "summary": "Fallback to layout category",
                "quality_delta": 5.0,
            }
        ],
        "style_directives": [],
        "anti_patterns": [],
    })
    feedback = agent._parse_evaluation(data)
    assert feedback is not None
    assert feedback.lessons_learned[0].category == LessonCategory.LAYOUT
    results.ok("T50: TeacherAgent handles invalid category gracefully")
except Exception as e:
    results.fail("T50: TeacherAgent handles invalid category gracefully", str(e))

# Test 51: TeacherAgent._build_evaluation_prompt
try:
    agent = TeacherAgent(MagicMock(), ctx)
    data = {
        "topic": "AI Platform",
        "purpose": "fundraising",
        "audience": "VCs",
        "slide_count": 10,
        "company_name": "Barise",
        "strategy": {"archetype": "yc_seed"},
        "design": {"theme": "dark"},
        "qa": {"quality_score": 85, "issues": ["Minor spacing"]},
        "code": {"slide_types": ["title-hero", "problem"]},
    }
    prompt = agent._build_evaluation_prompt(data, "No history")
    assert "AI Platform" in prompt
    assert "fundraising" in prompt
    assert "VCs" in prompt
    results.ok("T51: TeacherAgent._build_evaluation_prompt")
except Exception as e:
    results.fail("T51: TeacherAgent._build_evaluation_prompt", str(e))

# Test 52: TeacherAgent._format_historical with dict
try:
    agent = TeacherAgent(MagicMock(), ctx)
    history = {"avg_score": 82.5, "trend": "improving", "top_issues": ["spacing", "contrast"]}
    formatted = agent._format_historical(history)
    assert "82" in formatted
    assert "improving" in formatted
    assert "spacing" in formatted
    results.ok("T52: TeacherAgent._format_historical dict")
except Exception as e:
    results.fail("T52: TeacherAgent._format_historical dict", str(e))

# Test 53: TeacherAgent._format_historical with string
try:
    agent = TeacherAgent(MagicMock(), ctx)
    result = agent._format_historical("Just a string")
    assert "Just a string" in result
    results.ok("T53: TeacherAgent._format_historical string")
except Exception as e:
    results.fail("T53: TeacherAgent._format_historical string", str(e))

# Test 54: TeacherAgent DEFAULT_MODEL and FALLBACK_MODELS
try:
    assert TeacherAgent.DEFAULT_MODEL == "deepseek-v3"
    assert len(TeacherAgent.FALLBACK_MODELS) >= 3
    assert "gpt-4o-mini" in TeacherAgent.FALLBACK_MODELS
    results.ok("T54: TeacherAgent model configuration")
except Exception as e:
    results.fail("T54: TeacherAgent model configuration", str(e))

# Test 55: TeacherAgent._parse_evaluation handles empty lessons
try:
    agent = TeacherAgent(MagicMock(), ctx)
    data = json.dumps({
        "overall_score": 60.0,
        "overall_grade": "C",
        "dimensions": [],
        "cohesion_score": 55.0,
        "narrative_flow_score": 60.0,
        "brand_consistency_score": 65.0,
        "lessons": [],
        "style_directives": [],
        "anti_patterns": [],
    })
    feedback = agent._parse_evaluation(data)
    assert feedback is not None
    assert len(feedback.lessons_learned) == 0
    assert feedback.overall_score == 60.0
    results.ok("T55: TeacherAgent handles empty lessons")
except Exception as e:
    results.fail("T55: TeacherAgent handles empty lessons", str(e))

# Test 56: TeacherAgent parses multiple dimensions
try:
    agent = TeacherAgent(MagicMock(), ctx)
    data = json.dumps({
        "overall_score": 90.0,
        "overall_grade": "A",
        "dimensions": [
            {"name": "Visual Cohesion", "score": 92, "grade": "A", "observations": [], "recommendations": []},
            {"name": "Narrative Flow", "score": 88, "grade": "A", "observations": [], "recommendations": []},
            {"name": "Originality", "score": 85, "grade": "B", "observations": [], "recommendations": []},
        ],
        "cohesion_score": 90.0,
        "narrative_flow_score": 88.0,
        "brand_consistency_score": 92.0,
        "lessons": [],
        "style_directives": ["Use cinematic transitions"],
        "anti_patterns": ["No generic stock art"],
    })
    feedback = agent._parse_evaluation(data)
    assert len(feedback.dimensions) == 3
    assert feedback.dimensions[0].name == "Visual Cohesion"
    assert len(feedback.style_directives) == 1
    assert len(feedback.anti_patterns) == 1
    results.ok("T56: TeacherAgent parses multiple dimensions")
except Exception as e:
    results.fail("T56: TeacherAgent parses multiple dimensions", str(e))

# Test 57: TeacherAgent lesson confidence defaults to 0.6
try:
    agent = TeacherAgent(MagicMock(), ctx)
    data = json.dumps({
        "overall_score": 80.0,
        "overall_grade": "B",
        "dimensions": [],
        "cohesion_score": 80.0,
        "narrative_flow_score": 80.0,
        "brand_consistency_score": 80.0,
        "lessons": [
            {
                "category": "typography",
                "sentiment": "positive",
                "summary": "Monospace fonts work for tech data slides",
                "quality_delta": 3.0,
            }
        ],
        "style_directives": [],
        "anti_patterns": [],
    })
    feedback = agent._parse_evaluation(data)
    assert feedback.lessons_learned[0].confidence == 0.6
    results.ok("T57: Lesson default confidence 0.6")
except Exception as e:
    results.fail("T57: Lesson default confidence 0.6", str(e))

# Test 58: TeacherAgent lesson gets source_presentation_id
try:
    agent = TeacherAgent(MagicMock(), ctx)
    data = json.dumps({
        "overall_score": 85.0,
        "overall_grade": "A",
        "dimensions": [],
        "cohesion_score": 85.0,
        "narrative_flow_score": 85.0,
        "brand_consistency_score": 85.0,
        "lessons": [
            {
                "category": "background",
                "sentiment": "positive",
                "summary": "Mesh gradients create depth for hero slides",
                "quality_delta": 10.0,
            }
        ],
        "style_directives": [],
        "anti_patterns": [],
    })
    feedback = agent._parse_evaluation(data)
    assert feedback.lessons_learned[0].source_presentation_id == ctx.task_id
    assert feedback.lessons_learned[0].source_quality_score == 85.0
    results.ok("T58: Lesson source tracking")
except Exception as e:
    results.fail("T58: Lesson source tracking", str(e))

# Test 59: TeacherAgent with no previous outputs
try:
    empty_ctx = AgentContext(
        task_id="empty", user_id="u1", topic="Test",
        description="", purpose="testing", audience="testers",
        slide_count=5, mode="standard",
    )
    agent = TeacherAgent(MagicMock(), empty_ctx)
    data = agent._gather_generation_data()
    assert data["strategy"] == {}
    assert data["design"] == {}
    assert data["qa"] == {}
    results.ok("T59: TeacherAgent handles no previous outputs")
except Exception as e:
    results.fail("T59: TeacherAgent handles no previous outputs", str(e))

# Test 60: TeacherAgent evaluation prompt handles missing data
try:
    agent = TeacherAgent(MagicMock(), ctx)
    data = {
        "topic": "Unknown",
        "purpose": "Unknown",
        "audience": "Unknown",
        "slide_count": 0,
        "company_name": "Unknown",
        "strategy": {},
        "design": {},
        "qa": {},
        "code": {},
    }
    prompt = agent._build_evaluation_prompt(data, "No history")
    assert "Unknown" in prompt
    results.ok("T60: TeacherAgent handles missing data in prompt")
except Exception as e:
    results.fail("T60: TeacherAgent handles missing data in prompt", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4: Learning Engine (Tests 61-80)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 4: Learning Engine ===")

# Test 61: Import Learning Engine
try:
    from app.services.slides_new.learning.learning_engine import (
        LearningEngine,
        DEEP_ANALYSIS_INTERVAL,
        MIN_QUALITY_FOR_POSITIVE,
        MAX_LESSONS_PER_GENERATION,
    )
    results.ok("T61: Import LearningEngine")
except Exception as e:
    results.fail("T61: Import LearningEngine", str(e))

# Test 62: Constants are correct
try:
    assert DEEP_ANALYSIS_INTERVAL == 10
    assert MIN_QUALITY_FOR_POSITIVE == 70.0
    assert MAX_LESSONS_PER_GENERATION == 12
    results.ok("T62: LearningEngine constants")
except Exception as e:
    results.fail("T62: LearningEngine constants", str(e))

# Test 63: LearningEngine construction
try:
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=MagicMock())
    engine = LearningEngine(mock_db)
    assert engine._initialized is False
    assert engine._memory is not None
    results.ok("T63: LearningEngine construction")
except Exception as e:
    results.fail("T63: LearningEngine construction", str(e))

# Test 64: LearningEngine.memory property
try:
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=MagicMock())
    engine = LearningEngine(mock_db)
    assert isinstance(engine.memory, DesignMemory)
    results.ok("T64: LearningEngine.memory property")
except Exception as e:
    results.fail("T64: LearningEngine.memory property", str(e))

# Test 65: LearningEngine with ChromaDB service
try:
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=MagicMock())
    mock_chroma = MagicMock()
    engine = LearningEngine(mock_db, chroma_service=mock_chroma)
    assert engine._memory._chroma is mock_chroma
    results.ok("T65: LearningEngine with ChromaDB")
except Exception as e:
    results.fail("T65: LearningEngine with ChromaDB", str(e))

# Test 66: LearningEngine._build_generation_record
try:
    ctx = AgentContext(
        task_id="rec_test", user_id="u1", topic="Test Topic",
        description="Desc", purpose="fundraising", audience="VCs",
        slide_count=10, mode="standard",
    )
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=MagicMock())
    engine = LearningEngine(mock_db)

    result_data = {
        "quality_score": 88.0,
        "quality_passed": True,
        "total_latency_ms": 5000,
        "agent_metrics": {"ceo": {"success": True}},
    }

    record = engine._build_generation_record(ctx, result_data)
    assert record.presentation_id == "rec_test"
    assert record.quality_score == 88.0
    assert record.quality_passed is True
    assert record.topic == "Test Topic"
    results.ok("T66: LearningEngine._build_generation_record")
except Exception as e:
    results.fail("T66: LearningEngine._build_generation_record", str(e))

# Test 67: LearningEngine._derive_pattern_name
try:
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=MagicMock())
    engine = LearningEngine(mock_db)

    lesson = DesignLesson(
        category=LessonCategory.BACKGROUND,
        sentiment=LessonSentiment.POSITIVE,
        summary="Mesh gradients create depth for hero slides",
        slide_type="title-hero",
    )
    name = engine._derive_pattern_name(lesson)
    assert "background" in name
    assert "title-hero" in name
    assert len(name) <= 80
    results.ok("T67: LearningEngine._derive_pattern_name")
except Exception as e:
    results.fail("T67: LearningEngine._derive_pattern_name", str(e))

# Test 68: LearningEngine._derive_pattern_name without slide_type
try:
    lesson = DesignLesson(
        category=LessonCategory.COLOR_PALETTE,
        sentiment=LessonSentiment.POSITIVE,
        summary="Blue tones for tech",
    )
    name = engine._derive_pattern_name(lesson)
    assert "color_palette" in name
    assert "title-hero" not in name
    results.ok("T68: Pattern name without slide_type")
except Exception as e:
    results.fail("T68: Pattern name without slide_type", str(e))

# Test 69: LearningEngine._build_generation_record with QA feedback
try:
    ctx = AgentContext(
        task_id="qa_test", user_id="u1", topic="QA Test",
        description="", purpose="testing", audience="testers",
        slide_count=5, mode="standard",
    )
    qa_out = AgentOutput(
        success=True,
        agent_type=AgentType.QA,
        output={"issues": ["spacing", "contrast"], "recommendations": ["fix spacing"]},
    )
    ctx.previous_outputs[AgentType.QA] = qa_out

    record = engine._build_generation_record(ctx, {"quality_score": 70, "quality_passed": False})
    assert len(record.qa_issues) == 2
    assert len(record.qa_recommendations) == 1
    results.ok("T69: Generation record with QA feedback")
except Exception as e:
    results.fail("T69: Generation record with QA feedback", str(e))

# Test 70: LearningEngine._build_generation_record with designer output
try:
    ctx = AgentContext(
        task_id="des_test", user_id="u1", topic="Design Test",
        description="", purpose="testing", audience="testers",
        slide_count=5, mode="standard",
    )
    des_out = AgentOutput(
        success=True,
        agent_type=AgentType.DESIGNER,
        output={"theme": "dark", "preset": "yc_pitch"},
    )
    ctx.previous_outputs[AgentType.DESIGNER] = des_out

    record = engine._build_generation_record(ctx, {"quality_score": 80, "quality_passed": True})
    assert record.design_choices.get("theme") == "dark"
    results.ok("T70: Generation record with designer output")
except Exception as e:
    results.fail("T70: Generation record with designer output", str(e))

# Test 71: LearningEngine get_lessons_for_context (async, empty)
try:
    async def test_lessons_context():
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.__aiter__ = lambda self: self
        mock_cursor.__anext__ = AsyncMock(side_effect=StopAsyncIteration)
        mock_collection.find = MagicMock(return_value=mock_cursor)
        mock_collection.create_index = AsyncMock()
        mock_collection.count_documents = AsyncMock(return_value=0)
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        engine = LearningEngine(mock_db)
        text = await engine.get_lessons_for_context(
            slide_types=["title-hero"],
            audience="VCs",
        )
        assert isinstance(text, str)

    asyncio.get_event_loop().run_until_complete(test_lessons_context())
    results.ok("T71: LearningEngine.get_lessons_for_context")
except Exception as e:
    results.fail("T71: LearningEngine.get_lessons_for_context", str(e))

# Test 72: LearningEngine detects patterns from lessons
try:
    async def test_pattern_detection():
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_collection.find_one = AsyncMock(return_value=None)  # No existing pattern
        mock_collection.update_one = AsyncMock()
        mock_collection.create_index = AsyncMock()
        mock_collection.count_documents = AsyncMock(return_value=0)
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        engine = LearningEngine(mock_db)

        lessons = [
            DesignLesson(
                category=LessonCategory.BACKGROUND,
                sentiment=LessonSentiment.POSITIVE,
                summary="Gradient mesh backgrounds are excellent",
                slide_type="title-hero",
            )
        ]
        count = await engine._detect_and_evolve_patterns(lessons, 85.0)
        assert count >= 1

    asyncio.get_event_loop().run_until_complete(test_pattern_detection())
    results.ok("T72: LearningEngine pattern detection")
except Exception as e:
    results.fail("T72: LearningEngine pattern detection", str(e))

# Test 73: LearningEngine skips negative lessons for patterns
try:
    async def test_skip_negative():
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_collection.create_index = AsyncMock()
        mock_collection.count_documents = AsyncMock(return_value=0)
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        engine = LearningEngine(mock_db)

        negative_lessons = [
            DesignLesson(
                category=LessonCategory.BACKGROUND,
                sentiment=LessonSentiment.NEGATIVE,
                summary="Flat white backgrounds are boring",
            )
        ]
        count = await engine._detect_and_evolve_patterns(negative_lessons, 85.0)
        assert count == 0

    asyncio.get_event_loop().run_until_complete(test_skip_negative())
    results.ok("T73: LearningEngine skips negative lessons for patterns")
except Exception as e:
    results.fail("T73: LearningEngine skips negative lessons for patterns", str(e))

# Test 74: LearningEngine evolves existing pattern
try:
    async def test_evolve_existing():
        mock_db = MagicMock()
        mock_collection = AsyncMock()

        existing_pattern = DesignPattern(
            name="background_title-hero_gradient_mesh_backgrounds_are",
            description="Existing pattern",
            occurrence_count=3,
            quality_scores=[80, 82, 85],
            contributing_lessons=["l1", "l2"],
        )
        mock_collection.find_one = AsyncMock(
            return_value=existing_pattern.model_dump(mode="json")
        )
        mock_collection.update_one = AsyncMock()
        mock_collection.create_index = AsyncMock()
        mock_collection.count_documents = AsyncMock(return_value=0)
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        engine = LearningEngine(mock_db)

        lessons = [
            DesignLesson(
                category=LessonCategory.BACKGROUND,
                sentiment=LessonSentiment.POSITIVE,
                summary="Gradient mesh backgrounds are excellent for titles",
                slide_type="title-hero",
            )
        ]
        count = await engine._detect_and_evolve_patterns(lessons, 90.0)
        assert count >= 1

    asyncio.get_event_loop().run_until_complete(test_evolve_existing())
    results.ok("T74: LearningEngine evolves existing pattern")
except Exception as e:
    results.fail("T74: LearningEngine evolves existing pattern", str(e))

# Test 75: LearningEngine._derive_pattern_name max length
try:
    lesson = DesignLesson(
        category=LessonCategory.VISUAL_HIERARCHY,
        sentiment=LessonSentiment.POSITIVE,
        summary="A very long lesson summary that should be truncated when deriving the pattern name to stay within 80 chars",
        slide_type="kpi-dashboard",
    )
    name = engine._derive_pattern_name(lesson)
    assert len(name) <= 80
    results.ok("T75: Pattern name max length enforcement")
except Exception as e:
    results.fail("T75: Pattern name max length enforcement", str(e))

# Test 76: LearningEngine empty lessons list for pattern detection
try:
    async def test_empty_pattern():
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_collection.create_index = AsyncMock()
        mock_collection.count_documents = AsyncMock(return_value=0)
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        engine = LearningEngine(mock_db)
        count = await engine._detect_and_evolve_patterns([], 80.0)
        assert count == 0

    asyncio.get_event_loop().run_until_complete(test_empty_pattern())
    results.ok("T76: Empty lessons returns 0 patterns")
except Exception as e:
    results.fail("T76: Empty lessons returns 0 patterns", str(e))

# Test 77: LearningEngine multiple categories in lessons
try:
    async def test_multi_category():
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_collection.find_one = AsyncMock(return_value=None)
        mock_collection.update_one = AsyncMock()
        mock_collection.create_index = AsyncMock()
        mock_collection.count_documents = AsyncMock(return_value=0)
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        engine = LearningEngine(mock_db)

        lessons = [
            DesignLesson(
                category=LessonCategory.COLOR_PALETTE,
                sentiment=LessonSentiment.POSITIVE,
                summary="Blue gradients for tech",
            ),
            DesignLesson(
                category=LessonCategory.TYPOGRAPHY,
                sentiment=LessonSentiment.POSITIVE,
                summary="DM Sans for headings",
            ),
        ]
        count = await engine._detect_and_evolve_patterns(lessons, 82.0)
        assert count == 2

    asyncio.get_event_loop().run_until_complete(test_multi_category())
    results.ok("T77: Multiple lesson categories create multiple patterns")
except Exception as e:
    results.fail("T77: Multiple lesson categories create multiple patterns", str(e))

# Test 78: LearningEngine._build_generation_record with code agent output
try:
    ctx = AgentContext(
        task_id="code_test", user_id="u1", topic="Code Test",
        description="", purpose="testing", audience="testers",
        slide_count=5, mode="standard",
    )
    code_out = AgentOutput(
        success=True,
        agent_type=AgentType.CODE_AGENT,
        output={"slide_types": ["title-hero", "problem", "solution"]},
    )
    ctx.previous_outputs[AgentType.CODE_AGENT] = code_out

    record = engine._build_generation_record(ctx, {"quality_score": 85})
    assert len(record.slide_types_used) == 3
    results.ok("T78: Generation record with code agent output")
except Exception as e:
    results.fail("T78: Generation record with code agent output", str(e))

# Test 79: LearningEngine double initialize is idempotent
try:
    async def test_double_init():
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_collection.create_index = AsyncMock()
        mock_collection.count_documents = AsyncMock(return_value=0)
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        engine = LearningEngine(mock_db)
        await engine.initialize()
        assert engine._initialized is True
        # Second call should be no-op
        await engine.initialize()
        assert engine._initialized is True

    asyncio.get_event_loop().run_until_complete(test_double_init())
    results.ok("T79: Double initialize is idempotent")
except Exception as e:
    results.fail("T79: Double initialize is idempotent", str(e))

# Test 80: LearningEngine pattern name deterministic
try:
    lesson = DesignLesson(
        category=LessonCategory.SPACING,
        sentiment=LessonSentiment.POSITIVE,
        summary="More whitespace between sections",
        slide_type="bullets",
    )
    name1 = engine._derive_pattern_name(lesson)
    name2 = engine._derive_pattern_name(lesson)
    assert name1 == name2
    results.ok("T80: Pattern name is deterministic")
except Exception as e:
    results.fail("T80: Pattern name is deterministic", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5: Integration (Tests 81-100)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 5: Integration ===")

# Test 81: AgentType.TEACHER exists
try:
    from app.services.slides_new.agents.base import AgentType
    assert hasattr(AgentType, "TEACHER")
    assert AgentType.TEACHER == "teacher"
    results.ok("T81: AgentType.TEACHER exists")
except Exception as e:
    results.fail("T81: AgentType.TEACHER exists", str(e))

# Test 82: AgentType has 9 members (original 8 + TEACHER)
try:
    assert len(AgentType) == 9, f"Expected 9 AgentTypes, got {len(AgentType)}"
    results.ok("T82: AgentType has 9 members")
except Exception as e:
    results.fail("T82: AgentType has 9 members", str(e))

# Test 83: AgentFactory._agents includes TEACHER
try:
    from app.services.slides_new.agents.base import AgentFactory
    assert AgentType.TEACHER in AgentFactory._agents
    assert AgentFactory._agents[AgentType.TEACHER] == "TeacherAgent"
    results.ok("T83: AgentFactory includes TEACHER")
except Exception as e:
    results.fail("T83: AgentFactory includes TEACHER", str(e))

# Test 84: AgentFactory.create(TEACHER) works
try:
    ctx = AgentContext(
        task_id="factory_test", user_id="u1", topic="Test",
        description="", purpose="testing", audience="testers",
        slide_count=5, mode="standard",
    )
    agent = AgentFactory.create(AgentType.TEACHER, MagicMock(), ctx)
    assert isinstance(agent, TeacherAgent)
    assert agent.agent_type == AgentType.TEACHER
    results.ok("T84: AgentFactory.create(TEACHER)")
except Exception as e:
    results.fail("T84: AgentFactory.create(TEACHER)", str(e))

# Test 85: ExecutionPhase.LEARNING exists
try:
    from app.services.slides_new.agents.protocols import ExecutionPhase
    assert hasattr(ExecutionPhase, "LEARNING")
    assert ExecutionPhase.LEARNING == "learning"
    results.ok("T85: ExecutionPhase.LEARNING exists")
except Exception as e:
    results.fail("T85: ExecutionPhase.LEARNING exists", str(e))

# Test 86: V7GenerationConfig has enable_learning
try:
    from app.services.slides_new.orchestrator.v7_orchestrator import V7GenerationConfig
    config = V7GenerationConfig()
    assert config.enable_learning is True
    config_off = V7GenerationConfig(enable_learning=False)
    assert config_off.enable_learning is False
    results.ok("T86: V7GenerationConfig.enable_learning")
except Exception as e:
    results.fail("T86: V7GenerationConfig.enable_learning", str(e))

# Test 87: V7GenerationResult has teacher_feedback and lessons_learned
try:
    from app.services.slides_new.orchestrator.v7_orchestrator import V7GenerationResult
    result = V7GenerationResult(success=True)
    assert result.teacher_feedback is None
    assert result.lessons_learned == 0
    result2 = V7GenerationResult(
        success=True,
        teacher_feedback={"overall_score": 85},
        lessons_learned=5,
    )
    assert result2.lessons_learned == 5
    results.ok("T87: V7GenerationResult learning fields")
except Exception as e:
    results.fail("T87: V7GenerationResult learning fields", str(e))

# Test 88: V7Orchestrator has _learning_engine attribute
try:
    from app.services.slides_new.orchestrator.v7_orchestrator import V7Orchestrator
    orch = V7Orchestrator(MagicMock())
    assert hasattr(orch, "_learning_engine")
    assert orch._learning_engine is None
    results.ok("T88: V7Orchestrator._learning_engine attribute")
except Exception as e:
    results.fail("T88: V7Orchestrator._learning_engine attribute", str(e))

# Test 89: V7Orchestrator has _run_learning_phase method
try:
    assert hasattr(V7Orchestrator, "_run_learning_phase")
    assert asyncio.iscoroutinefunction(V7Orchestrator._run_learning_phase)
    results.ok("T89: V7Orchestrator._run_learning_phase method")
except Exception as e:
    results.fail("T89: V7Orchestrator._run_learning_phase method", str(e))

# Test 90: Learning module __init__ exports
try:
    from app.services.slides_new.learning import (
        LearningEngine,
        DesignMemory,
        TeacherAgent,
        DesignLesson,
        DesignPattern,
        TeacherFeedback,
        LessonCategory,
        LessonSentiment,
        PatternStrength,
    )
    results.ok("T90: Learning module __init__ exports")
except Exception as e:
    results.fail("T90: Learning module __init__ exports", str(e))

# Test 91: Agents __init__ exports TeacherAgent
try:
    from app.services.slides_new.agents import TeacherAgent as TA
    assert TA is TeacherAgent
    results.ok("T91: Agents __init__ exports TeacherAgent")
except Exception as e:
    results.fail("T91: Agents __init__ exports TeacherAgent", str(e))

# Test 92: DesignerAgent has _get_learned_design_context method
try:
    from app.services.slides_new.agents.designer_agent import DesignerAgent
    assert hasattr(DesignerAgent, "_get_learned_design_context")
    assert asyncio.iscoroutinefunction(DesignerAgent._get_learned_design_context)
    results.ok("T92: DesignerAgent._get_learned_design_context method")
except Exception as e:
    results.fail("T92: DesignerAgent._get_learned_design_context method", str(e))

# Test 93: CodeAgent _build_generation_context includes learned_context
try:
    from app.services.slides_new.agents.code_agent import CodeAgent
    ctx = AgentContext(
        task_id="code_test", user_id="u1", topic="Test",
        description="", purpose="testing", audience="testers",
        slide_count=5, mode="standard",
    )
    agent = CodeAgent(MagicMock(), ctx)
    gen_ctx = agent._build_generation_context({
        "colors": {"primary": "#000"},
        "fonts": {"heading": "Inter", "body": "Inter"},
        "learned_context": "## Test Lessons\n- DO: Use dark themes",
    })
    assert gen_ctx.get("_learned_design_lessons") is not None
    assert "dark themes" in gen_ctx["_learned_design_lessons"]
    results.ok("T93: CodeAgent passes learned_context to generation")
except Exception as e:
    results.fail("T93: CodeAgent passes learned_context to generation", str(e))

# Test 94: CodeAgent _build_generation_context without learned_context
try:
    gen_ctx = agent._build_generation_context({
        "colors": {"primary": "#000"},
        "fonts": {"heading": "Inter", "body": "Inter"},
    })
    assert "_learned_design_lessons" not in gen_ctx
    results.ok("T94: CodeAgent without learned_context is clean")
except Exception as e:
    results.fail("T94: CodeAgent without learned_context is clean", str(e))

# Test 95: DesignerAgent design output includes learned_context key
try:
    # Verify that the execute method's output dict has learned_context
    import inspect
    source = inspect.getsource(DesignerAgent.execute)
    assert "learned_context" in source
    results.ok("T95: DesignerAgent output includes learned_context")
except Exception as e:
    results.fail("T95: DesignerAgent output includes learned_context", str(e))

# Test 96: LearningEngine import from v7_orchestrator
try:
    import inspect
    source = inspect.getsource(V7Orchestrator)
    assert "LearningEngine" in source or "_learning_engine" in source
    results.ok("T96: V7Orchestrator references LearningEngine")
except Exception as e:
    results.fail("T96: V7Orchestrator references LearningEngine", str(e))

# Test 97: TeacherFeedback round-trip serialization
try:
    fb = TeacherFeedback(
        presentation_id="rt_test",
        overall_score=87.5,
        overall_grade="A",
        dimensions=[
            TeacherDimension(name="Cohesion", score=90, grade="A"),
        ],
        lessons_learned=[
            DesignLesson(
                category=LessonCategory.BACKGROUND,
                sentiment=LessonSentiment.POSITIVE,
                summary="Mesh gradients are excellent",
            ),
        ],
        cohesion_score=90.0,
        narrative_flow_score=85.0,
        brand_consistency_score=88.0,
    )
    dumped = fb.model_dump(mode="json")
    restored = TeacherFeedback.model_validate(dumped)
    assert restored.overall_score == 87.5
    assert len(restored.dimensions) == 1
    assert len(restored.lessons_learned) == 1
    results.ok("T97: TeacherFeedback round-trip serialization")
except Exception as e:
    results.fail("T97: TeacherFeedback round-trip serialization", str(e))

# Test 98: GenerationRecord round-trip
try:
    rec = GenerationRecord(
        presentation_id="rt_gen",
        user_id="u1",
        topic="RT Test",
        purpose="testing",
        audience="devs",
        slide_count=8,
        quality_score=92.0,
        quality_passed=True,
        slide_types_used=["title-hero", "solution"],
        qa_issues=["Minor spacing"],
    )
    dumped = rec.model_dump(mode="json")
    restored = GenerationRecord.model_validate(dumped)
    assert restored.quality_score == 92.0
    assert len(restored.slide_types_used) == 2
    results.ok("T98: GenerationRecord round-trip serialization")
except Exception as e:
    results.fail("T98: GenerationRecord round-trip serialization", str(e))

# Test 99: V7Orchestrator backward compat alias
try:
    from app.services.slides_new.orchestrator.v7_orchestrator import SlideGenerationOrchestratorV7
    assert SlideGenerationOrchestratorV7 is V7Orchestrator
    results.ok("T99: Backward compat alias preserved")
except Exception as e:
    results.fail("T99: Backward compat alias preserved", str(e))

# Test 100: Full model ecosystem consistency check
try:
    # Verify all enum values are lowercase strings
    for cat in LessonCategory:
        assert cat.value == cat.value.lower(), f"Category {cat} not lowercase"
    for sent in LessonSentiment:
        assert sent.value == sent.value.lower(), f"Sentiment {sent} not lowercase"
    for strength in PatternStrength:
        assert strength.value == strength.value.lower(), f"Strength {strength} not lowercase"
    for phase in ExecutionPhase:
        assert phase.value == phase.value.lower(), f"Phase {phase} not lowercase"
    results.ok("T100: All enums use lowercase values")
except Exception as e:
    results.fail("T100: All enums use lowercase values", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

all_passed = results.summary()
sys.exit(0 if all_passed else 1)
