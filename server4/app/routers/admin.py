"""Admin endpoints — provider health, generation stats."""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.dependencies import require_admin
from app.services.observability import ObservabilityService

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
