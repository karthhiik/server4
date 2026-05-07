"""
Learning Module — Self-evolving presentation intelligence.

Adapts Hermes Agent's closed learning loop for slide generation:
- Teacher Agent: Post-generation evaluator (like Hermes background review)
- Design Memory: Persistent knowledge store (like Hermes MEMORY.md)
- Learning Engine: Orchestrator tying it all together (like Hermes MemoryManager)
- Pattern Detection: Cross-generation trend analysis (like Hermes skill creation)
"""

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
from app.services.slides_new.learning.design_memory import DesignMemory
from app.services.slides_new.learning.teacher_agent import TeacherAgent
from app.services.slides_new.learning.learning_engine import LearningEngine

__all__ = [
    # Engine
    "LearningEngine",
    # Memory
    "DesignMemory",
    # Agent
    "TeacherAgent",
    # Models
    "DesignLesson",
    "DesignPattern",
    "GenerationRecord",
    "LearningSnapshot",
    "LessonCategory",
    "LessonSentiment",
    "PatternStrength",
    "TeacherDimension",
    "TeacherFeedback",
]
