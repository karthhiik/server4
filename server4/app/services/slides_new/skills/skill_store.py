"""
Skill Store — MongoDB + ChromaDB persistence for the Code Agent's skill system.

Handles:
- CRUD for SlideSkill objects in MongoDB
- Indexing best examples in ChromaDB for semantic few-shot retrieval
- Version management and quality tracking
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.slides_new.skills.models import (
    BestExample,
    QAFeedback,
    SkillFailurePattern,
    SlideSkill,
)

logger = structlog.get_logger()

# MongoDB collection name
SKILLS_COLLECTION = "slide_skills"


class SkillStore:
    """
    Persistent storage for the Code Agent's self-evolving skill system.

    MongoDB stores the full SlideSkill documents (versions, failures, metadata).
    ChromaDB stores best_examples for semantic similarity retrieval.
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        chroma_service: Optional[Any] = None,
    ) -> None:
        self.db = db
        self.collection = db[SKILLS_COLLECTION]
        self._chroma = chroma_service

    # ── CRUD ──────────────────────────────────────────────────

    async def get_skill(self, skill_name: str) -> Optional[SlideSkill]:
        """Load a skill by name from MongoDB."""
        doc = await self.collection.find_one({"name": skill_name})
        if doc is None:
            return None
        return SlideSkill.from_mongo_doc(doc)

    async def save_skill(self, skill: SlideSkill) -> None:
        """Upsert a skill to MongoDB."""
        skill.updated_at = datetime.now(timezone.utc)
        doc = skill.to_mongo_doc()
        await self.collection.update_one(
            {"name": skill.name},
            {"$set": doc},
            upsert=True,
        )
        logger.debug(
            "skill_saved",
            name=skill.name,
            version=skill.version,
            avg_quality=round(skill.avg_quality, 1),
        )

    async def list_skills(self) -> List[SlideSkill]:
        """Return all skills ordered by name."""
        cursor = self.collection.find().sort("name", 1)
        skills = []
        async for doc in cursor:
            skills.append(SlideSkill.from_mongo_doc(doc))
        return skills

    async def delete_skill(self, skill_name: str) -> bool:
        """Delete a skill by name."""
        result = await self.collection.delete_one({"name": skill_name})
        return result.deleted_count > 0

    # ── SKILL EVOLUTION ───────────────────────────────────────

    async def record_quality(
        self,
        skill_name: str,
        score: float,
        dsl_output: str,
        qa_feedback: QAFeedback,
        slide_type: str = "",
        layout: str = "",
        topic_hint: str = "",
    ) -> SlideSkill:
        """
        Record a generation quality score and evolve the skill.

        If score >= threshold:
          - Add to best_examples
          - Index in ChromaDB for few-shot
          - Possibly upgrade version
        If score < threshold:
          - Record failure patterns from QA feedback
        """
        skill = await self.get_skill(skill_name)
        if skill is None:
            logger.warning("skill_not_found_for_quality", name=skill_name)
            raise ValueError(f"Skill '{skill_name}' not found")

        # Record the generation attempt
        skill.record_generation(score)

        if score >= skill.quality_threshold:
            # Success path — learn from good output
            example = BestExample(
                dsl_json=dsl_output,
                quality_score=score,
                slide_type=slide_type or skill_name,
                layout=layout,
                topic_hint=topic_hint,
            )
            skill.add_best_example(example)

            # Index in ChromaDB for semantic retrieval
            if self._chroma is not None:
                try:
                    await self._chroma.add_skill_example(
                        skill_name=skill_name,
                        version=skill.version,
                        example_dsl=dsl_output,
                        quality_score=int(score),
                        metadata={
                            "slide_type": slide_type,
                            "layout": layout,
                            "topic_hint": topic_hint,
                        },
                    )
                except Exception as e:
                    logger.warning(
                        "chromadb_skill_index_failed",
                        skill=skill_name,
                        error=str(e),
                    )

            # Check if we should upgrade the version
            # Upgrade if: last 3 scores all above threshold
            recent = skill.quality_history[-3:]
            if (
                len(recent) >= 3
                and all(s >= skill.quality_threshold for s in recent)
                and score > skill.avg_quality
            ):
                improvements = [
                    f"Average quality improved to {skill.avg_quality:.1f}",
                    f"Last 3 scores: {[round(s, 1) for s in recent]}",
                ]
                if qa_feedback.recommendations:
                    improvements.extend(
                        qa_feedback.recommendations[:2]
                    )
                skill.upgrade_version(improvements, score)
                logger.info(
                    "skill_version_upgraded",
                    name=skill_name,
                    new_version=skill.version,
                    score=round(score, 1),
                )
        else:
            # Failure path — learn from bad output
            for issue in qa_feedback.issues[:5]:
                pattern = SkillFailurePattern(
                    description=issue,
                    qa_feedback="; ".join(qa_feedback.structured_failures[0].values())
                    if qa_feedback.structured_failures
                    else issue,
                    severity="high" if score < 50 else "medium",
                )
                skill.add_failure_pattern(pattern)

            # Record structured failures
            for sf in qa_feedback.structured_failures[:3]:
                pattern = SkillFailurePattern(
                    description=sf.get("reason", "Unknown failure"),
                    qa_feedback=sf.get("suggestion", ""),
                    severity="high" if sf.get("gate") in (
                        "content_completeness",
                        "factual_accuracy",
                    ) else "medium",
                    mitigation=sf.get("suggestion"),
                )
                skill.add_failure_pattern(pattern)

            logger.info(
                "skill_failure_recorded",
                name=skill_name,
                score=round(score, 1),
                failures_count=len(qa_feedback.issues),
            )

        # Persist updated skill
        await self.save_skill(skill)
        return skill

    # ── FEW-SHOT RETRIEVAL ────────────────────────────────────

    async def get_few_shot_examples(
        self,
        skill_name: str,
        query: str,
        n: int = 3,
        min_quality: int = 80,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the best examples for few-shot prompting.

        Strategy:
        1. Try ChromaDB semantic search (matches by topic/content similarity)
        2. Fall back to skill's best_examples sorted by quality
        """
        # Try ChromaDB first for semantic matching
        if self._chroma is not None:
            try:
                results = await self._chroma.search_skill_examples(
                    query=query,
                    skill_name=skill_name,
                    min_quality=min_quality,
                    n_results=n,
                )
                if results:
                    return results
            except Exception as e:
                logger.warning(
                    "chromadb_few_shot_failed",
                    skill=skill_name,
                    error=str(e),
                )

        # Fall back to MongoDB best_examples
        skill = await self.get_skill(skill_name)
        if skill is None:
            return []

        top = skill.get_top_examples(n)
        return [
            {
                "id": ex.id,
                "document": ex.dsl_json,
                "metadata": {
                    "skill_name": skill_name,
                    "quality_score": ex.quality_score,
                    "slide_type": ex.slide_type,
                    "layout": ex.layout,
                },
            }
            for ex in top
            if ex.quality_score >= min_quality
        ]

    async def get_failure_patterns(
        self, skill_name: str, n: int = 5
    ) -> List[SkillFailurePattern]:
        """Get the most common failure patterns for a skill."""
        skill = await self.get_skill(skill_name)
        if skill is None:
            return []
        return skill.get_recent_failures(n)

    # ── BULK OPERATIONS ───────────────────────────────────────

    async def initialize_defaults(
        self, default_prompts: Dict[str, Dict[str, Any]]
    ) -> int:
        """
        Initialize default skills from the skill registry.
        Only creates skills that don't already exist.
        Returns: number of skills created.
        """
        created = 0
        for skill_name, config in default_prompts.items():
            existing = await self.get_skill(skill_name)
            if existing is not None:
                continue

            skill = SlideSkill(
                name=skill_name,
                prompt_template=config["prompt_template"],
                generation_mode=config.get("mode", "instant"),
                quality_threshold=config.get("threshold", 85.0),
            )
            await self.save_skill(skill)
            created += 1
            logger.info("skill_initialized", name=skill_name)

        return created

    async def get_skill_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics across all skills."""
        skills = await self.list_skills()
        if not skills:
            return {"total": 0}

        return {
            "total": len(skills),
            "total_generations": sum(s.total_generations for s in skills),
            "total_improvements": sum(s.total_improvements for s in skills),
            "avg_quality_overall": round(
                sum(s.avg_quality for s in skills) / len(skills), 1
            )
            if skills
            else 0.0,
            "best_performing": max(skills, key=lambda s: s.avg_quality).name
            if skills
            else None,
            "most_generated": max(skills, key=lambda s: s.total_generations).name
            if skills
            else None,
            "skills": [
                {
                    "name": s.name,
                    "version": s.version,
                    "avg_quality": round(s.avg_quality, 1),
                    "generations": s.total_generations,
                    "examples": len(s.best_examples),
                    "failures": len(s.common_failures),
                }
                for s in skills
            ],
        }
