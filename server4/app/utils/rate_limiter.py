"""Per-user rate limiting using Redis."""

import time
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.close()
        _redis = None


async def check_rate_limit(user_id: str, is_premium: bool = False) -> bool:
    """
    Returns True if request is allowed, False if rate limited.
    Uses sliding window counter in Redis.
    """
    r = await get_redis()
    limit = settings.RATE_LIMIT_PREMIUM if is_premium else settings.RATE_LIMIT_STANDARD
    window = 3600  # 1 hour

    key = f"ratelimit:presentations:{user_id}"
    now = time.time()
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, now - window)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, window)
    results = await pipe.execute()

    count = results[2]
    return count <= limit


async def get_rate_limit_remaining(user_id: str, is_premium: bool = False) -> int:
    r = await get_redis()
    limit = settings.RATE_LIMIT_PREMIUM if is_premium else settings.RATE_LIMIT_STANDARD
    window = 3600

    key = f"ratelimit:presentations:{user_id}"
    now = time.time()
    await r.zremrangebyscore(key, 0, now - window)
    count = await r.zcard(key)
    return max(0, limit - count)
