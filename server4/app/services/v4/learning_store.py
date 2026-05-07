"""
V4 Learning Store — Self-improvement via exemplar retrieval.

Per `llm-content-orchestration` skill: NO recursive fine-tuning (model collapse risk).
Instead, every successful generation is recorded; future generations retrieve
the top-K exemplars by (purpose, industry) and inject them as few-shot examples.

Collections:
  v4_generations:
    _id: generation_id
    project_id, user_id, mode, purpose, industry
    input_summary: condensed input snapshot
    skeleton: the deck skeleton produced
    slides: final slide content
    scores: critic scores per slide + overall
    success_signal: 0..1 (overall score / 10, optionally adjusted by user actions)
    created_at
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class GenerationOutcome:
    project_id: str
    user_id: Optional[str]
    mode: str                    # "premium" | "standard"
    purpose: str                 # e.g. "investor_pitch"
    industry: Optional[str]
    input_summary: dict[str, Any]
    skeleton: dict[str, Any]
    slides: list[dict[str, Any]]
    scores: dict[str, Any]
    success_signal: float        # 0..1, derived from critic + user feedback
    visibility_scope: str = "project"  # project | user | tenant | global
    tenant_id: Optional[str] = None
    generation_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class LearningStore:
    """
    Persists generation outcomes and retrieves high-quality exemplars
    to inject as few-shot examples in future generations.
    """

    COLLECTION = "v4_generations"
    EXEMPLAR_MIN_SCORE = 0.85         # success_signal threshold
    EXEMPLAR_DEFAULT_K = 3

    async def record_outcome(self, outcome: GenerationOutcome) -> str:
        try:
            from app.database import get_db, is_db_initialized
            if not is_db_initialized():
                return outcome.generation_id
            db = get_db()
            doc = {
                "_id": outcome.generation_id,
                "project_id": outcome.project_id,
                "user_id": outcome.user_id,
                "tenant_id": outcome.tenant_id,
                "visibility_scope": outcome.visibility_scope,
                "mode": outcome.mode,
                "purpose": outcome.purpose,
                "industry": (outcome.industry or "").lower(),
                "input_summary": outcome.input_summary,
                "skeleton": outcome.skeleton,
                "slides": outcome.slides,
                "scores": outcome.scores,
                "success_signal": float(outcome.success_signal),
                "created_at": outcome.created_at,
            }
            await db[self.COLLECTION].update_one(
                {"_id": outcome.generation_id}, {"$set": doc}, upsert=True
            )
            logger.info("v4_outcome_recorded",
                generation_id=outcome.generation_id,
                purpose=outcome.purpose,
                signal=outcome.success_signal)
            return outcome.generation_id
        except Exception as e:
            logger.warning("v4_outcome_record_failed", error=str(e))
            return outcome.generation_id

    async def get_exemplars(
        self,
        purpose: str,
        industry: Optional[str] = None,
        limit: int = EXEMPLAR_DEFAULT_K,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve top-K most successful past generations matching purpose
        (and industry when provided). Returns compact exemplars suitable
        for few-shot injection into LLM prompts.
        """
        try:
            from app.database import get_db, is_db_initialized
            if not is_db_initialized():
                return []
            db = get_db()
            q: dict[str, Any] = {
                "purpose": purpose,
                "success_signal": {"$gte": self.EXEMPLAR_MIN_SCORE},
                "$or": _visibility_filters(
                    user_id=user_id,
                    project_id=project_id,
                    tenant_id=tenant_id,
                ),
            }
            if industry:
                q["industry"] = industry.lower()

            cursor = db[self.COLLECTION].find(q).sort("success_signal", -1).limit(limit)
            exemplars: list[dict[str, Any]] = []
            async for doc in cursor:
                exemplars.append({
                    "purpose": doc.get("purpose"),
                    "industry": doc.get("industry"),
                    "visibility_scope": doc.get("visibility_scope", "project"),
                    "skeleton_summary": [
                        {
                            "intent": s.get("intent"),
                            "purpose": s.get("purpose"),
                            "key_points": s.get("key_points", [])[:3],
                        }
                        for s in (doc.get("skeleton", {}).get("slides", []) or [])
                    ],
                    "score": doc.get("success_signal"),
                })
            return exemplars
        except Exception as e:
            logger.warning("v4_exemplar_fetch_failed", error=str(e))
            return []

    async def update_user_feedback(self, generation_id: str, signal_delta: float) -> None:
        """Adjust success_signal based on downstream user behavior (edit ratio, exports, etc.)."""
        try:
            from app.database import get_db, is_db_initialized
            if not is_db_initialized():
                return
            db = get_db()
            await db[self.COLLECTION].update_one(
                {"_id": generation_id},
                {"$inc": {"success_signal": float(signal_delta)},
                 "$set": {"updated_at": datetime.now(timezone.utc)}},
            )
        except Exception as e:
            logger.warning("v4_feedback_update_failed", error=str(e))


def _visibility_filters(
    *,
    user_id: Optional[str],
    project_id: Optional[str],
    tenant_id: Optional[str],
) -> list[dict[str, Any]]:
    filters: list[dict[str, Any]] = [{"visibility_scope": "global"}]
    if project_id:
        filters.append({"visibility_scope": "project", "project_id": project_id})
    if user_id:
        filters.append({"visibility_scope": "user", "user_id": user_id})
    if tenant_id:
        filters.append({"visibility_scope": "tenant", "tenant_id": tenant_id})
    return filters

