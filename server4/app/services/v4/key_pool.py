"""
V4 Key Pool — round-robin API key rotation with per-key 429 cooldown.

Used for providers where we hold multiple keys (Exa, Jina, You.com, Serper).
Each pool tracks per-key health: a key that returns 429 / 5xx is parked in a
cooldown bucket and skipped until its window expires. acquire() returns the
next healthy key under an asyncio.Lock so concurrent fan-out doesn't hammer
the same key.

Design goals:
  - Zero external dependency (pure asyncio + dataclasses)
  - Thread/coroutine safe
  - Honest telemetry — telemetry() returns counts callers can log
  - Graceful degradation — if every key is cooling, returns the
    least-recently-failed key (better to retry one than to fail the request)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class _KeyState:
    key: str
    requests: int = 0
    successes: int = 0
    failures: int = 0
    last_failure_at: float = 0.0
    cooldown_until: float = 0.0  # monotonic seconds


class KeyPool:
    """Round-robin pool with cooldown on failure.

    Args:
        name: Human label for logs (e.g. "exa", "jina", "you_com").
        keys: Raw API key strings. Empty/None values are filtered.
        cooldown_seconds_429: Cooldown after a 429.
        cooldown_seconds_5xx: Cooldown after a 5xx (or other server error).
    """

    def __init__(
        self,
        name: str,
        keys: list[str],
        cooldown_seconds_429: float = 60.0,
        cooldown_seconds_5xx: float = 30.0,
    ) -> None:
        self.name = name
        self._states: list[_KeyState] = [
            _KeyState(key=k.strip()) for k in keys if k and k.strip()
        ]
        self._cursor = 0
        self._lock = asyncio.Lock()
        self._cooldown_429 = cooldown_seconds_429
        self._cooldown_5xx = cooldown_seconds_5xx

    @property
    def empty(self) -> bool:
        return not self._states

    @property
    def size(self) -> int:
        return len(self._states)

    async def acquire(self) -> Optional[str]:
        """Return the next healthy key (or the least-recently-failed key
        if every key is cooling down). Returns None only if the pool is empty.
        """
        if not self._states:
            return None

        async with self._lock:
            now = time.monotonic()
            n = len(self._states)
            # First pass: find a healthy key starting at cursor
            for i in range(n):
                idx = (self._cursor + i) % n
                state = self._states[idx]
                if state.cooldown_until <= now:
                    self._cursor = (idx + 1) % n
                    state.requests += 1
                    return state.key
            # All cooling: pick the one with the oldest failure (least recent)
            idx = min(range(n), key=lambda i: self._states[i].last_failure_at)
            state = self._states[idx]
            state.requests += 1
            logger.warning(
                "keypool.all_cooling",
                pool=self.name,
                fallback_key_index=idx,
                cooldown_remaining=state.cooldown_until - now,
            )
            return state.key

    async def report_success(self, key: str) -> None:
        async with self._lock:
            for state in self._states:
                if state.key == key:
                    state.successes += 1
                    return

    async def report_failure(self, key: str, status_code: int = 0) -> None:
        async with self._lock:
            now = time.monotonic()
            for state in self._states:
                if state.key == key:
                    state.failures += 1
                    state.last_failure_at = now
                    if status_code == 429:
                        state.cooldown_until = now + self._cooldown_429
                    elif status_code >= 500:
                        state.cooldown_until = now + self._cooldown_5xx
                    elif status_code in (401, 403):
                        # Auth failures: long cooldown — key is likely bad
                        state.cooldown_until = now + 3600.0
                        logger.warning(
                            "keypool.auth_failure",
                            pool=self.name,
                            status=status_code,
                        )
                    return

    def telemetry(self) -> dict:
        return {
            "pool": self.name,
            "size": len(self._states),
            "keys": [
                {
                    "requests": s.requests,
                    "successes": s.successes,
                    "failures": s.failures,
                    "cooling": s.cooldown_until > time.monotonic(),
                }
                for s in self._states
            ],
        }


# ── Module-level singleton pools (lazy-initialized) ────────────────

_pools: dict[str, KeyPool] = {}


def get_pool(name: str, keys: list[str]) -> KeyPool:
    """Return a singleton pool for `name`, creating on first call."""
    pool = _pools.get(name)
    if pool is None:
        pool = KeyPool(name=name, keys=keys)
        _pools[name] = pool
    return pool


def all_telemetry() -> list[dict]:
    return [p.telemetry() for p in _pools.values()]
