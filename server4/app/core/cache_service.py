"""Cache Service using Redis for distributed caching.

Provides async cache operations with TTL support.
"""

import json
import logging
from typing import Any, Optional
import redis.asyncio as redis
from app.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Async cache service backed by Redis."""

    def __init__(self):
        """Initialize cache service with Redis connection."""
        self.redis_client: Optional[redis.Redis] = None
        self._initialized = False

    async def initialize(self):
        """Initialize Redis connection."""
        if self._initialized:
            return
        try:
            self.redis_client = await redis.from_url(
                settings.REDIS_URL, decode_responses=True
            )
            await self.redis_client.ping()
            self._initialized = True
            logger.info("Cache service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize cache service: {e}")
            self._initialized = False

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or Redis unavailable
        """
        if not self.redis_client:
            await self.initialize()

        if not self.redis_client:
            return None

        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            await self.initialize()

        if not self.redis_client:
            return False

        try:
            serialized = json.dumps(value)
            await self.redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False

        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")
            return False

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()


# Global cache service instance
cache_service = CacheService()
