"""
LLM Token Bucket — Redis-backed pre-call skip for exhausted models.

Purpose:
    Before each LLM call, the router asks `can_call(model)`. If the model has
    been marked rate-limited, quota-exhausted, or permanently dead in this
    process, we skip it without wasting a round-trip.

This is NOT cost tracking or per-user throttling. It is a minimal shared-state
circuit breaker that prevents every worker in a Celery pool from independently
hammering a 429-returning provider.

All keys are namespaced under `llm:` and have hard TTLs. If Redis is down, the
module degrades to an in-memory dict so the hot path never blocks on I/O.

Public API:
    await can_call(model) -> bool
    await mark_rate_limited(model, cooldown_s)
    await mark_quota_exhausted(model, reset_at_utc=None)
    mark_dead_local(model)           # process-local permanent (AUTH class)
    is_dead_local(model) -> bool
    await mark_healthy(model)        # clear rate-limit state
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


# ── Process-local state ────────────────────────────────────────────
# AUTH failures mean the key is wrong / revoked. That cannot be fixed at
# runtime, so we mark the model dead for the lifetime of the process.
_DEAD_LOCAL: set[str] = set()

# In-memory fallback when Redis is unreachable. Maps model → unix-epoch
# seconds when the skip expires. Scanned by `can_call`.
_LOCAL_SKIP: dict[str, float] = {}
_LOCAL_LOCK = asyncio.Lock()

# Module-level Redis handle (lazily initialised).
_REDIS = None
_REDIS_FAILED_ONCE = False


# ── Redis helpers ──────────────────────────────────────────────────

async def _get_redis():
    """Return an async-redis client or None if Redis is misconfigured/down.

    Uses `app.services.storage.redis_client` when present; otherwise builds
    from `settings.REDIS_URL`.
    """
    global _REDIS, _REDIS_FAILED_ONCE
    if _REDIS is not None:
        return _REDIS
    if _REDIS_FAILED_ONCE:
        return None
    try:
        # Prefer the already-configured project client if available.
        try:
            from app.services.storage.redis_client import get_redis  # type: ignore
            client = await get_redis()
            if client is not None:
                _REDIS = client
                return client
        except Exception:  # noqa: BLE001
            pass

        import redis.asyncio as aioredis  # type: ignore
        from app.config import settings

        url = settings.REDIS_URL
        client = aioredis.from_url(url, decode_responses=True, socket_timeout=2.0)
        # Light probe — avoid long hangs when Redis is down.
        await asyncio.wait_for(client.ping(), timeout=2.0)
        _REDIS = client
        return client
    except Exception as e:  # noqa: BLE001
        _REDIS_FAILED_ONCE = True
        logger.warning("token_bucket_redis_unavailable",
                       error=str(e)[:200], fallback="in_memory")
        return None


def _seconds_until_utc_midnight() -> int:
    """Cooldown TTL until next UTC midnight for daily-quota errors."""
    now = datetime.now(timezone.utc)
    next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # bump to tomorrow
    next_midnight = next_midnight.replace(day=now.day) if False else next_midnight
    from datetime import timedelta
    next_midnight = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return max(60, int((next_midnight - now).total_seconds()))


# ── Public API ─────────────────────────────────────────────────────

def mark_dead_local(model: str) -> None:
    """Mark a model permanently dead for this process (used on AUTH errors)."""
    _DEAD_LOCAL.add(model)
    logger.warning("token_bucket_marked_dead_local", model=model)


def is_dead_local(model: str) -> bool:
    return model in _DEAD_LOCAL


async def can_call(model: str) -> bool:
    """Return False iff we know the model is currently exhausted / dead."""
    if is_dead_local(model):
        return False

    # Check in-memory skip cache first — avoids Redis on the hot path.
    now = time.time()
    async with _LOCAL_LOCK:
        skip_until = _LOCAL_SKIP.get(model)
        if skip_until is not None and skip_until > now:
            return False
        if skip_until is not None and skip_until <= now:
            _LOCAL_SKIP.pop(model, None)

    client = await _get_redis()
    if client is None:
        return True

    try:
        # SETEX'd keys are cleared by TTL; existence == still exhausted.
        pipe = client.pipeline()
        pipe.get(f"llm:skip:{model}")
        pipe.get(f"llm:quota_exhausted:{model}")
        skip, quota = await pipe.execute()
        if skip or quota:
            # Populate local cache so the next call within TTL is free.
            # Use remaining TTL as cache duration (cap 60s).
            try:
                ttl = await client.ttl(f"llm:skip:{model}" if skip else f"llm:quota_exhausted:{model}")
                if ttl and ttl > 0:
                    async with _LOCAL_LOCK:
                        _LOCAL_SKIP[model] = time.time() + min(ttl, 60)
            except Exception:  # noqa: BLE001
                pass
            return False
        return True
    except Exception as e:  # noqa: BLE001
        logger.debug("token_bucket_get_failed", model=model, error=str(e)[:120])
        return True


async def mark_rate_limited(model: str, cooldown_s: float) -> None:
    """Skip this model for `cooldown_s` seconds (RATE_LIMIT class)."""
    cooldown_s = max(5.0, min(float(cooldown_s or 30.0), 600.0))
    expire_at = time.time() + cooldown_s
    async with _LOCAL_LOCK:
        _LOCAL_SKIP[model] = expire_at
    client = await _get_redis()
    if client is not None:
        try:
            await client.setex(f"llm:skip:{model}", int(cooldown_s), "1")
        except Exception as e:  # noqa: BLE001
            logger.debug("token_bucket_setex_failed", model=model, error=str(e)[:120])
    logger.info("token_bucket_rate_limited", model=model, cooldown_s=cooldown_s)


async def mark_quota_exhausted(model: str, reset_at_utc: Optional[datetime] = None) -> None:
    """Skip this model until next UTC midnight (or explicit reset)."""
    if reset_at_utc is not None:
        ttl = max(60, int((reset_at_utc - datetime.now(timezone.utc)).total_seconds()))
    else:
        ttl = _seconds_until_utc_midnight()
    expire_at = time.time() + ttl
    async with _LOCAL_LOCK:
        _LOCAL_SKIP[model] = expire_at
    client = await _get_redis()
    if client is not None:
        try:
            await client.setex(f"llm:quota_exhausted:{model}", ttl, "1")
        except Exception as e:  # noqa: BLE001
            logger.debug("token_bucket_quota_setex_failed", model=model, error=str(e)[:120])
    logger.warning("token_bucket_quota_exhausted", model=model, ttl_s=ttl)


async def mark_healthy(model: str) -> None:
    """Clear any skip marker — called on successful complete()."""
    async with _LOCAL_LOCK:
        _LOCAL_SKIP.pop(model, None)
    client = await _get_redis()
    if client is None:
        return
    try:
        await client.delete(f"llm:skip:{model}", f"llm:quota_exhausted:{model}")
    except Exception as e:  # noqa: BLE001
        logger.debug("token_bucket_healthy_failed", model=model, error=str(e)[:120])


async def status_snapshot() -> dict[str, dict[str, object]]:
    """Diagnostic: dump current skip state for observability endpoints."""
    out: dict[str, dict[str, object]] = {}
    now = time.time()
    async with _LOCAL_LOCK:
        for m, exp in _LOCAL_SKIP.items():
            out[m] = {"skip_until_ts": exp, "remaining_s": max(0, int(exp - now))}
    for m in _DEAD_LOCAL:
        out.setdefault(m, {})["dead_local"] = True
    return out


__all__ = [
    "can_call",
    "mark_rate_limited",
    "mark_quota_exhausted",
    "mark_dead_local",
    "is_dead_local",
    "mark_healthy",
    "status_snapshot",
]
