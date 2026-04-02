"""
Observability — tracks LLM/API call metrics for monitoring.
Feeds into generation_logs collection.
"""

from datetime import datetime, timedelta
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

import structlog

logger = structlog.get_logger()


class ObservabilityService:
    """Query generation_logs for provider health and performance metrics."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def get_provider_health(self, hours: int = 1) -> list[dict]:
        """Get success rate and avg latency per provider in the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        pipeline = [
            {"$match": {"created_at": {"$gte": cutoff}}},
            {"$group": {
                "_id": {"provider": "$provider", "model": "$model"},
                "total": {"$sum": 1},
                "successes": {"$sum": {"$cond": [{"$eq": ["$success", True]}, 1, 0]}},
                "failures": {"$sum": {"$cond": [{"$eq": ["$success", False]}, 1, 0]}},
                "avg_latency": {"$avg": "$latency_ms"},
                "avg_tokens": {"$avg": "$tokens_used"},
            }},
            {"$sort": {"total": -1}},
        ]
        results = await self.db.generation_logs.aggregate(pipeline).to_list(100)

        return [
            {
                "provider": r["_id"]["provider"],
                "model": r["_id"]["model"],
                "total_calls": r["total"],
                "success_rate": round(r["successes"] / max(r["total"], 1) * 100, 1),
                "failure_count": r["failures"],
                "avg_latency_ms": round(r["avg_latency"] or 0),
                "avg_tokens": round(r["avg_tokens"] or 0),
            }
            for r in results
        ]

    async def get_generation_stats(self, hours: int = 24) -> dict:
        """Overall generation statistics."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        total = await self.db.presentations.count_documents({"created_at": {"$gte": cutoff}})
        completed = await self.db.presentations.count_documents({
            "created_at": {"$gte": cutoff},
            "generation_state": "completed",
        })
        failed = await self.db.presentations.count_documents({
            "created_at": {"$gte": cutoff},
            "generation_state": "failed",
        })

        return {
            "period_hours": hours,
            "total_generations": total,
            "completed": completed,
            "failed": failed,
            "success_rate": round(completed / max(total, 1) * 100, 1),
        }
