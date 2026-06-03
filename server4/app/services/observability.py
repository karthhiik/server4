"""
Observability — tracks LLM/API call metrics for monitoring.
Feeds into generation_logs collection.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

import structlog
from app.config import settings
from app.services.v4.quality_metrics import evaluate_quality_alerts

logger = structlog.get_logger()

COUNTER_HASH_KEY = "v4:metrics:counters"


def _today_suffix(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y%m%d")


def _counter_field(name: str, tags: Optional[dict] = None) -> str:
    clean_tags = tags or {}
    tag_part = ",".join(
        f"{str(k)}={str(clean_tags[k])}"
        for k in sorted(clean_tags)
        if clean_tags[k] is not None
    )
    return f"{_today_suffix()}:{name}" + (f"|{tag_part}" if tag_part else "")


async def counter(name: str, tags: Optional[dict] = None, value: int = 1) -> None:
    """Best-effort Redis counter for operational metrics."""
    try:
        from app.utils.rate_limiter import get_redis

        redis = await get_redis()
        if redis is None:
            return
        await redis.hincrby(COUNTER_HASH_KEY, _counter_field(name, tags), int(value))
    except Exception as exc:  # pragma: no cover - metrics must never break prod flow
        logger.debug("observability_counter_failed", name=name, error=str(exc)[:160])


async def counter_snapshot() -> dict:
    """Return all Redis metric counters as JSON-safe values."""
    try:
        from app.utils.rate_limiter import get_redis

        redis = await get_redis()
        if redis is None:
            return {"ok": False, "counters": {}, "reason": "redis_unavailable"}
        raw = await redis.hgetall(COUNTER_HASH_KEY)
    except Exception as exc:
        return {"ok": False, "counters": {}, "reason": str(exc)[:160]}

    counters: dict[str, int] = {}
    for key, val in dict(raw or {}).items():
        k = key.decode("utf-8", errors="ignore") if isinstance(key, bytes) else str(key)
        v_raw = val.decode("utf-8", errors="ignore") if isinstance(val, bytes) else str(val)
        try:
            counters[k] = int(v_raw)
        except ValueError:
            counters[k] = 0
    return {"ok": True, "hash": COUNTER_HASH_KEY, "counters": counters}


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

    async def get_quality_health(self, hours: int = 24) -> dict:
        """Aggregate Plan 10 quality events by event/gate/severity."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        collection = self.db[settings.QUALITY_METRICS_COLLECTION]
        pipeline = [
            {"$match": {"created_at": {"$gte": cutoff}}},
            {"$group": {
                "_id": {
                    "event": "$event",
                    "gate": "$gate",
                    "severity": "$severity",
                },
                "count": {"$sum": 1},
                "avg_value": {"$avg": "$metric_value"},
            }},
            {"$sort": {"count": -1}},
        ]
        rows = await collection.aggregate(pipeline).to_list(200)
        return {
            "period_hours": hours,
            "collection": settings.QUALITY_METRICS_COLLECTION,
            "events": [
                {
                    "event": r["_id"].get("event"),
                    "gate": r["_id"].get("gate"),
                    "severity": r["_id"].get("severity"),
                    "count": r.get("count", 0),
                    "avg_value": round(r.get("avg_value") or 0, 2),
                }
                for r in rows
            ],
        }

    async def get_v4_quality_alerts(self, hours: int = 2) -> dict:
        """Evaluate Plan 10 production alert thresholds from persisted metrics."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        collection = self.db[settings.QUALITY_METRICS_COLLECTION]
        docs = await collection.find({"created_at": {"$gte": cutoff}}).sort("created_at", -1).to_list(2000)
        alerts = [alert.to_doc() for alert in evaluate_quality_alerts(docs, window_s=float(hours * 3600))]

        provider_alerts: list[dict] = []
        for row in await self.get_provider_health(hours=max(1, hours)):
            total = int(row.get("total_calls") or 0)
            failure_rate = 100.0 - float(row.get("success_rate") or 0.0)
            if total >= 5 and failure_rate > 20.0:
                provider_alerts.append({
                    "code": "primary_model_error_rate_high",
                    "severity": "critical",
                    "provider": row.get("provider"),
                    "model": row.get("model"),
                    "message": "Provider failure rate exceeded 20% in the rolling production window.",
                    "action": "failover_provider",
                    "metric_value": round(failure_rate, 2),
                    "threshold": 20.0,
                })

        return {
            "period_hours": hours,
            "quality_alerts": alerts,
            "provider_alerts": provider_alerts,
            "alert_count": len(alerts) + len(provider_alerts),
        }

    def get_v4_gate_settings(self) -> dict:
        """Current runtime kill-switch and rollout settings."""
        return {
            "schema": settings.ENABLE_SCHEMA_GATE,
            "provenance": settings.ENABLE_PROVENANCE_GATE,
            "style": settings.ENABLE_STYLE_GUARD,
            "layout_rhythm": settings.ENABLE_LAYOUT_RHYTHM_GATE,
            "learning": settings.ENABLE_LEARNING_INFLUENCE,
            "image_prompt": settings.ENABLE_IMAGE_PROMPT_ENRICHMENT,
            "standard_routing_experiment": settings.ENABLE_STANDARD_ROUTING_EXPERIMENT,
            "standard_routing_rollout_percent": settings.STANDARD_ROUTING_EXPERIMENT_ROLLOUT_PERCENT,
            "quality_gate_rollout_percent": settings.QUALITY_GATE_ROLLOUT_PERCENT,
            "allow_pollinations_images": settings.ALLOW_POLLINATIONS_IMAGES,
        }
