"""Admin endpoints — provider health, generation stats."""

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.dependencies import require_admin, require_auth
from app.services.observability import ObservabilityService, counter_snapshot

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/health/providers")
async def provider_health(
    hours: int = 1,
    user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> list[dict]:
    """
    Provider health dashboard.
    Shows success rate, avg latency, failure count per provider/model.
    """
    svc = ObservabilityService(db)
    return await svc.get_provider_health(hours)


@router.get("/stats/generations")
async def generation_stats(
    hours: int = 24,
    user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Overall generation statistics."""
    svc = ObservabilityService(db)
    return await svc.get_generation_stats(hours)


@router.get("/health/v4-quality")
async def v4_quality_health(
    hours: int = 24,
    user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Plan 10 quality-gate metrics for schema/provenance/rollout health."""
    svc = ObservabilityService(db)
    return await svc.get_quality_health(hours)


@router.get("/health/v4-alerts")
async def v4_quality_alerts(
    hours: int = 2,
    user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Plan 10 production alert thresholds for quality gates and providers."""
    svc = ObservabilityService(db)
    return await svc.get_v4_quality_alerts(hours)


@router.get("/settings/v4-gates")
async def v4_gate_settings(
    user: dict = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Runtime V4 gate and rollout settings."""
    svc = ObservabilityService(db)
    return svc.get_v4_gate_settings()


@router.get("/metrics")
async def v4_admin_metrics(
    user: dict = Depends(require_auth),
) -> dict:
    """Redis-backed V4 operational counters. Admins only; 404 for others."""
    role = user.get("role", "")
    set_role = user.get("setuserrole", "")
    if role != "admin" and set_role != "admin":
        raise HTTPException(status_code=404, detail="Not Found")
    return await counter_snapshot()
