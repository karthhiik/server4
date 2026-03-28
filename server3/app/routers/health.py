import os
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.db.mongo import db as mongo_db
from app.db.redis import redis_client

settings = get_settings()
router = APIRouter()


@router.get("/healthz")
async def healthz():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/readyz")
async def readyz():
    mongo_ok = False
    redis_ok = False

    try:
        if mongo_db.client is not None:
            await mongo_db.client.admin.command("ping")
            mongo_ok = True
    except Exception:
        mongo_ok = False

    try:
        if redis_client.client is not None:
            await redis_client.client.ping()
            redis_ok = True
    except Exception:
        redis_ok = False

    report = {
        "status": "ok" if mongo_ok and redis_ok else "degraded",
        "mongodb": "connected" if mongo_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected",
        "timestamp": datetime.utcnow().isoformat(),
    }

    if not (mongo_ok and redis_ok):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=report)

    return report


@router.get("/diagnostics")
async def diagnostics():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "port": int(os.environ.get("PORT", "8000")),
        "services": {
            "mongodb_connected": mongo_db.client is not None,
            "redis_connected": redis_client.client is not None,
        },
    }
