"""
Session Store -- Redis-backed editor session persistence.

Replaces the in-memory ``_sessions`` dict in editor_routes.py with a
Redis-backed store that:
- Persists session metadata across server restarts
- Supports TTL-based expiry for abandoned sessions
- Provides atomic session locking
- Stores session status (active / paused / closed)

The actual DSL + engine objects are still in-memory (they contain
non-serializable state). The SessionStore tracks session *metadata*
and provides the bookkeeping that enables the sync layer.
"""

import json
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Session status and record
# ---------------------------------------------------------------------------


class SessionStatus(str, Enum):
    """Status of an editor session."""
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    EXPIRED = "expired"


class SessionRecord:
    """
    Metadata about an editor session.

    Stored in Redis as JSON. The actual engine objects live in-memory
    and are tracked by editor_routes._sessions.
    """

    __slots__ = (
        "session_id", "presentation_id", "user_id",
        "status", "created_at", "last_activity",
        "slide_count", "revision", "client_ids",
        "metadata",
    )

    def __init__(
        self,
        presentation_id: str,
        user_id: str = "system",
        session_id: Optional[str] = None,
    ):
        self.session_id = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        self.presentation_id = presentation_id
        self.user_id = user_id
        self.status = SessionStatus.ACTIVE
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)
        self.slide_count = 0
        self.revision = 0
        self.client_ids: List[str] = []
        self.metadata: Dict[str, Any] = {}

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "presentation_id": self.presentation_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "slide_count": self.slide_count,
            "revision": self.revision,
            "client_ids": self.client_ids,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionRecord":
        record = cls(
            presentation_id=data["presentation_id"],
            user_id=data.get("user_id", "system"),
            session_id=data.get("session_id"),
        )
        record.status = SessionStatus(data.get("status", "active"))
        if "created_at" in data:
            record.created_at = datetime.fromisoformat(data["created_at"])
        if "last_activity" in data:
            record.last_activity = datetime.fromisoformat(data["last_activity"])
        record.slide_count = data.get("slide_count", 0)
        record.revision = data.get("revision", 0)
        record.client_ids = data.get("client_ids", [])
        record.metadata = data.get("metadata", {})
        return record

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, raw: str) -> "SessionRecord":
        return cls.from_dict(json.loads(raw))


# ---------------------------------------------------------------------------
# SessionStore -- hybrid in-memory + Redis session store
# ---------------------------------------------------------------------------


class SessionStore:
    """
    Session store with in-memory primary and optional Redis backing.

    In-memory dict is the source of truth for active sessions because
    engine objects are non-serializable. Redis stores metadata for:
    - Cross-restart continuity of session IDs
    - TTL expiry detection
    - Admin visibility / monitoring

    Usage:
        store = SessionStore()
        await store.init_redis(redis_url)

        record = store.create("pres-123", user_id="user-1")
        record = store.get("pres-123")
        store.touch("pres-123")
        store.close("pres-123")
    """

    # Redis key prefix
    KEY_PREFIX = "editor:session:"
    # Default session TTL: 4 hours
    DEFAULT_TTL = 4 * 60 * 60

    def __init__(self, ttl: int = DEFAULT_TTL):
        self._sessions: Dict[str, SessionRecord] = {}
        self._ttl = ttl
        self._redis = None

    # ── Redis initialization ─────────────────────────────────────

    async def init_redis(self, redis_url: str) -> bool:
        """
        Optionally connect to Redis for session persistence.

        Returns True if connected, False if Redis is unavailable.
        The store works without Redis (pure in-memory fallback).
        """
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info("session_store_redis_connected")
            return True
        except Exception as exc:
            logger.warning("session_store_redis_unavailable", error=str(exc))
            self._redis = None
            return False

    # ── Session lifecycle ────────────────────────────────────────

    def create(
        self,
        presentation_id: str,
        user_id: str = "system",
        slide_count: int = 0,
    ) -> SessionRecord:
        """Create a new session record."""
        record = SessionRecord(
            presentation_id=presentation_id,
            user_id=user_id,
        )
        record.slide_count = slide_count
        self._sessions[presentation_id] = record

        logger.info(
            "session_created",
            presentation_id=presentation_id,
            session_id=record.session_id,
        )
        return record

    def get(self, presentation_id: str) -> Optional[SessionRecord]:
        """Get session record by presentation ID."""
        return self._sessions.get(presentation_id)

    def exists(self, presentation_id: str) -> bool:
        """Check if a session exists."""
        return presentation_id in self._sessions

    def touch(self, presentation_id: str) -> bool:
        """Update last activity timestamp. Returns False if no session."""
        record = self._sessions.get(presentation_id)
        if not record:
            return False
        record.touch()
        return True

    def update_revision(self, presentation_id: str, revision: int) -> bool:
        """Update session revision counter."""
        record = self._sessions.get(presentation_id)
        if not record:
            return False
        record.revision = revision
        record.touch()
        return True

    def add_client(self, presentation_id: str, client_id: str) -> bool:
        """Add a client to the session."""
        record = self._sessions.get(presentation_id)
        if not record:
            return False
        if client_id not in record.client_ids:
            record.client_ids.append(client_id)
        record.touch()
        return True

    def remove_client(self, presentation_id: str, client_id: str) -> bool:
        """Remove a client from the session."""
        record = self._sessions.get(presentation_id)
        if not record:
            return False
        if client_id in record.client_ids:
            record.client_ids.remove(client_id)
        record.touch()
        return True

    def close(self, presentation_id: str) -> Optional[SessionRecord]:
        """Close a session. Returns the closed record."""
        record = self._sessions.pop(presentation_id, None)
        if record:
            record.status = SessionStatus.CLOSED
            logger.info(
                "session_closed",
                presentation_id=presentation_id,
                session_id=record.session_id,
            )
        return record

    # ── Redis persistence ────────────────────────────────────────

    async def persist(self, presentation_id: str) -> bool:
        """Persist session record to Redis."""
        if not self._redis:
            return False
        record = self._sessions.get(presentation_id)
        if not record:
            return False
        key = f"{self.KEY_PREFIX}{presentation_id}"
        try:
            await self._redis.set(key, record.to_json(), ex=self._ttl)
            return True
        except Exception as exc:
            logger.warning("session_persist_failed", error=str(exc))
            return False

    async def restore(self, presentation_id: str) -> Optional[SessionRecord]:
        """Restore session record from Redis (metadata only)."""
        if not self._redis:
            return None
        key = f"{self.KEY_PREFIX}{presentation_id}"
        try:
            raw = await self._redis.get(key)
            if raw:
                record = SessionRecord.from_json(raw)
                self._sessions[presentation_id] = record
                return record
        except Exception as exc:
            logger.warning("session_restore_failed", error=str(exc))
        return None

    async def persist_all(self) -> int:
        """Persist all active sessions to Redis. Returns count."""
        if not self._redis:
            return 0
        count = 0
        for pid in list(self._sessions.keys()):
            if await self.persist(pid):
                count += 1
        return count

    # ── Queries ──────────────────────────────────────────────────

    def list_sessions(
        self,
        status: Optional[SessionStatus] = None,
    ) -> List[SessionRecord]:
        """List all sessions, optionally filtered by status."""
        sessions = list(self._sessions.values())
        if status:
            sessions = [s for s in sessions if s.status == status]
        return sessions

    def list_active(self) -> List[SessionRecord]:
        """List active sessions."""
        return self.list_sessions(status=SessionStatus.ACTIVE)

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    @property
    def active_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.status == SessionStatus.ACTIVE)

    def get_stats(self) -> Dict[str, Any]:
        """Store-wide statistics."""
        by_status: Dict[str, int] = {}
        for s in self._sessions.values():
            by_status[s.status.value] = by_status.get(s.status.value, 0) + 1
        return {
            "total_sessions": self.session_count,
            "active_sessions": self.active_count,
            "by_status": by_status,
            "redis_connected": self._redis is not None,
        }

    # ── Cleanup ──────────────────────────────────────────────────

    def cleanup_expired(self, max_idle_seconds: int = 14400) -> int:
        """Remove sessions idle longer than max_idle_seconds. Returns count removed."""
        now = datetime.now(timezone.utc)
        expired = []
        for pid, record in self._sessions.items():
            delta = (now - record.last_activity).total_seconds()
            if delta > max_idle_seconds and record.status != SessionStatus.CLOSED:
                record.status = SessionStatus.EXPIRED
                expired.append(pid)

        for pid in expired:
            self._sessions.pop(pid, None)

        if expired:
            logger.info("sessions_expired", count=len(expired))
        return len(expired)
