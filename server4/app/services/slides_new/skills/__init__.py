"""
Slide Skills System — Phase 3 (yoyo-evolve pattern)

Self-evolving skill storage, versioning, and few-shot retrieval
for the Code Agent's learnable slide generation pipeline.
"""

from app.services.slides_new.skills.models import (
    SlideSkill,
    SkillVersion,
    SkillFailurePattern,
    SkillGenerationMode,
)
from app.services.slides_new.skills.skill_store import SkillStore
from app.services.slides_new.skills.skill_registry import (
    SkillRegistry,
    DEFAULT_SKILL_PROMPTS,
)

__all__ = [
    "SlideSkill",
    "SkillVersion",
    "SkillFailurePattern",
    "SkillGenerationMode",
    "SkillStore",
    "SkillRegistry",
    "DEFAULT_SKILL_PROMPTS",
]
