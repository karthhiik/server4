"""
Context Board — Shared mutable state for inter-agent communication.

Agents (CEO, Researcher, Designer, Layout, Code, QA, Image, VFX) read and write
to named sections on this board. Fast path via Redis hashes; durable path via
background MongoDB sync.

Sections:
    strategy  — CEO agent: archetype, narrative arc, audience persona
    research  — Researcher: data points, citations, market stats
    design    — Designer: theme, colour palette, typography choices
    layout    — Layout agent: per-slide layout decisions, grid specs
    dsl       — Code agent: generated DSL fragments
    quality   — QA agent: scores, feedback, error list
    images    — Image pipeline: generated URLs, prompts
    status    — Orchestrator: current phase, progress percentage
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Optional

import structlog
from redis.asyncio import Redis

from app.config import settings
from app.database import get_db

logger = structlog.get_logger(__name__)

VALID_SECTIONS = frozenset(
    {
        "strategy",
        "research",
        "design",
        "layout",
        "dsl",
        "quality",
        "images",
        "status",
    }
)

_REDIS_KEY_PREFIX = "ctxboard"
_HISTORY_MAX = 50  # max entries per key history


def _redis_hash_key(session_id: str) -> str:
    return f"{_REDIS_KEY_PREFIX}:{session_id}"


def _redis_history_key(session_id: str, key: str) -> str:
    return f"{_REDIS_KEY_PREFIX}:history:{session_id}:{key}"


def _redis_lock_key(session_id: str, key: str) -> str:
    return f"{_REDIS_KEY_PREFIX}:lock:{session_id}:{key}"


class ContextBoard:
    """Shared state board backed by Redis (fast) + MongoDB (durable).

    Usage::

        board = ContextBoard(session_id="gen-abc123")
        await board.connect()
        await board.set("strategy.archetype", "problem-solution", agent="ceo")
        val = await board.get("strategy.archetype")
        history = await board.history("strategy.archetype")
        await board.close()
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._redis: Optional[Redis] = None
        self._sync_task: Optional[asyncio.Task[None]] = None
        self._dirty: bool = False

    # ── lifecycle ──────────────────────────────────────────────

    async def connect(self) -> None:
        try:
            self._redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Test connection
            await self._redis.ping()
            self._sync_task = asyncio.create_task(self._background_sync_loop())
            logger.info("context_board_connected", session_id=self.session_id)
        except Exception as e:
            logger.warning(
                "context_board_redis_unavailable_using_memory",
                session_id=self.session_id,
                error=str(e),
            )
            # Fall back to in-memory only (no Redis, no sync)
            self._redis = None
            self._sync_task = None

    async def close(self) -> None:
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        # final flush
        await self._sync_to_mongo()
        if self._redis:
            await self._redis.aclose()
        logger.info("context_board_closed", session_id=self.session_id)

    # ── core operations ───────────────────────────────────────

    async def set(self, key: str, value: Any, agent: str) -> None:
        """Write a value to the board. ``key`` should be ``section.field``."""
        self._validate_key(key)
        serialized = json.dumps(value) if not isinstance(value, str) else value
        redis = self._get_redis()

        await redis.hset(_redis_hash_key(self.session_id), key, serialized)

        # append history entry
        history_entry = json.dumps(
            {
                "value": value,
                "agent": agent,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        history_key = _redis_history_key(self.session_id, key)
        await redis.lpush(history_key, history_entry)
        await redis.ltrim(history_key, 0, _HISTORY_MAX - 1)
        await redis.expire(history_key, 86400)  # 24h TTL

        self._dirty = True
        logger.debug("context_board_set", session=self.session_id, key=key, agent=agent)

    async def get(self, key: str) -> Optional[Any]:
        """Read a single value (returns deserialised JSON or raw string)."""
        redis = self._get_redis()
        raw = await redis.hget(_redis_hash_key(self.session_id), key)
        if raw is None:
            return None
        return self._maybe_parse_json(raw)

    async def get_section(self, section: str) -> dict[str, Any]:
        """Return all key/value pairs whose key starts with ``section.``."""
        if section not in VALID_SECTIONS:
            raise ValueError(
                f"Unknown section '{section}', must be one of {VALID_SECTIONS}"
            )
        redis = self._get_redis()
        data = await redis.hgetall(_redis_hash_key(self.session_id))
        prefix = f"{section}."
        return {
            k: self._maybe_parse_json(v)
            for k, v in data.items()
            if k.startswith(prefix)
        }

    async def get_all(self) -> dict[str, Any]:
        """Snapshot the entire board."""
        redis = self._get_redis()
        data = await redis.hgetall(_redis_hash_key(self.session_id))
        return {k: self._maybe_parse_json(v) for k, v in data.items()}

    async def history(self, key: str, limit: int = 10) -> list[dict[str, Any]]:
        """Return recent change history for a key (newest first)."""
        redis = self._get_redis()
        entries = await redis.lrange(
            _redis_history_key(self.session_id, key),
            0,
            limit - 1,
        )
        results: list[dict[str, Any]] = []
        for raw in entries:
            try:
                results.append(json.loads(raw))
            except json.JSONDecodeError:
                results.append({"value": raw})
        return results

    async def delete(self, key: str) -> None:
        """Remove a key from the board."""
        redis = self._get_redis()
        await redis.hdel(_redis_hash_key(self.session_id), key)
        self._dirty = True

    # ── locking ───────────────────────────────────────────────

    async def lock(self, key: str, ttl_seconds: int = 10) -> bool:
        """Acquire an advisory lock on a key. Returns True if acquired."""
        redis = self._get_redis()
        lock_key = _redis_lock_key(self.session_id, key)
        acquired = await redis.set(lock_key, "1", nx=True, ex=ttl_seconds)
        return acquired is not None

    async def unlock(self, key: str) -> None:
        """Release an advisory lock."""
        redis = self._get_redis()
        await redis.delete(_redis_lock_key(self.session_id, key))

    # ── persistence (MongoDB) ─────────────────────────────────

    async def save_snapshot(self) -> None:
        """Explicitly persist current board state to MongoDB."""
        await self._sync_to_mongo()

    async def load_from_mongo(self) -> bool:
        """Hydrate Redis from a previously persisted MongoDB snapshot.
        Returns True if a snapshot was found and loaded."""
        try:
            db = get_db()
            doc = await db.context_boards.find_one({"session_id": self.session_id})
            if not doc or "data" not in doc:
                return False
            redis = self._get_redis()
            if doc["data"]:
                mapping = {
                    k: json.dumps(v) if not isinstance(v, str) else v
                    for k, v in doc["data"].items()
                }
                await redis.hset(_redis_hash_key(self.session_id), mapping=mapping)
            logger.info("context_board_loaded_from_mongo", session=self.session_id)
            return True
        except Exception:
            logger.exception("context_board_mongo_load_failed", session=self.session_id)
            return False

    # ── internal ──────────────────────────────────────────────

    def _get_redis(self) -> Redis:
        if self._redis is None:
            raise RuntimeError("ContextBoard not connected — call connect() first")
        return self._redis

    @staticmethod
    def _validate_key(key: str) -> None:
        if "." not in key:
            raise ValueError(f"Key must be 'section.field' format, got '{key}'")
        section = key.split(".", 1)[0]
        if section not in VALID_SECTIONS:
            raise ValueError(
                f"Unknown section '{section}', must be one of {VALID_SECTIONS}"
            )

    @staticmethod
    def _maybe_parse_json(raw: str) -> Any:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def _sync_to_mongo(self) -> None:
        """Persist current Redis state into MongoDB for durability."""
        if not self._dirty:
            return
        try:
            db = get_db()
            data = await self.get_all()
            await db.context_boards.update_one(
                {"session_id": self.session_id},
                {
                    "$set": {
                        "data": data,
                        "updated_at": datetime.utcnow(),
                    },
                    "$setOnInsert": {
                        "session_id": self.session_id,
                        "created_at": datetime.utcnow(),
                    },
                },
                upsert=True,
            )
            self._dirty = False
            logger.debug("context_board_synced_to_mongo", session=self.session_id)
        except Exception:
            logger.exception("context_board_sync_failed", session=self.session_id)

    async def _background_sync_loop(self) -> None:
        """Periodically flush dirty state to MongoDB."""
        while True:
            await asyncio.sleep(5.0)
            await self._sync_to_mongo()
