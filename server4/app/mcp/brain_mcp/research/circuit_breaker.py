"""
Redis-backed circuit breaker for external API providers.

Tracks consecutive failures, latency EMA, and opens the circuit when a
provider exceeds the failure threshold.  Falls back to an in-memory dict
when Redis is unavailable so the system never hard-crashes.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from app.mcp.brain_mcp.research.models import ProviderHealth, ProviderStatus

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Redis-backed circuit breaker with graceful in-memory fallback.

    Redis key layout:
        cb:{provider}:failures   — int   (consecutive failure count)
        cb:{provider}:status     — str   (healthy|degraded|open_circuit)
        cb:{provider}:latency    — float (EMA latency_ms)
        cb:{provider}:last_ok    — str   (ISO timestamp)
        cb:{provider}:last_fail  — str   (ISO timestamp)
        cb:{provider}:calls_day  — int   (calls counter, TTL 86400)
        cb:{provider}:calls_mon  — int   (calls counter, TTL 2678400)
        cb:{provider}:open_until — str   (ISO timestamp when circuit can re-close)
    """

    DEGRADED_THRESHOLD: int = 3
    OPEN_THRESHOLD: int = 5
    COOLDOWN_SECONDS: int = 300
    LATENCY_EMA_ALPHA: float = 0.3

    # Redis key TTLs
    _FAILURE_TTL: int = 3600       # 1 hour
    _STATUS_TTL: int = 86400       # 1 day
    _COUNTER_DAY_TTL: int = 86400
    _COUNTER_MONTH_TTL: int = 2678400  # 31 days

    def __init__(self, redis_client: Any = None) -> None:
        self._redis = redis_client
        self._memory: dict[str, dict[str, Any]] = {}

    # ── Helpers ─────────────────────────────────────────────────

    def _key(self, provider: str, suffix: str) -> str:
        return f"cb:{provider}:{suffix}"

    async def _redis_get(self, key: str) -> Optional[str]:
        if self._redis is None:
            return self._memory.get(key, {}).get("v")
        try:
            val = await self._redis.get(key)
            if isinstance(val, bytes):
                return val.decode()
            return val
        except Exception as exc:
            logger.warning("Redis GET %s failed: %s", key, exc)
            return self._memory.get(key, {}).get("v")

    async def _redis_set(
        self, key: str, value: str, ttl: int | None = None
    ) -> None:
        self._memory[key] = {"v": value}
        if self._redis is None:
            return
        try:
            if ttl:
                await self._redis.set(key, value, ex=ttl)
            else:
                await self._redis.set(key, value)
        except Exception as exc:
            logger.warning("Redis SET %s failed: %s", key, exc)

    async def _redis_incr(self, key: str, ttl: int | None = None) -> int:
        current = self._memory.get(key, {}).get("v", "0")
        new_val = int(current) + 1
        self._memory[key] = {"v": str(new_val)}
        if self._redis is None:
            return new_val
        try:
            result = await self._redis.incr(key)
            if ttl:
                # Only set TTL if key was just created (value == 1)
                if result == 1:
                    await self._redis.expire(key, ttl)
            return int(result)
        except Exception as exc:
            logger.warning("Redis INCR %s failed: %s", key, exc)
            return new_val

    async def _redis_delete(self, key: str) -> None:
        self._memory.pop(key, None)
        if self._redis is None:
            return
        try:
            await self._redis.delete(key)
        except Exception as exc:
            logger.warning("Redis DELETE %s failed: %s", key, exc)

    # ── Public API ──────────────────────────────────────────────

    async def check_health(self, provider: str) -> ProviderHealth:
        """Return the current health snapshot for a provider."""
        status_str = await self._redis_get(self._key(provider, "status"))
        failures_str = await self._redis_get(self._key(provider, "failures"))
        latency_str = await self._redis_get(self._key(provider, "latency"))
        last_ok = await self._redis_get(self._key(provider, "last_ok"))
        last_fail = await self._redis_get(self._key(provider, "last_fail"))
        calls_day_str = await self._redis_get(self._key(provider, "calls_day"))
        calls_mon_str = await self._redis_get(self._key(provider, "calls_mon"))
        open_until = await self._redis_get(self._key(provider, "open_until"))

        try:
            status = ProviderStatus(status_str) if status_str else ProviderStatus.healthy
        except ValueError:
            status = ProviderStatus.healthy

        return ProviderHealth(
            provider=provider,
            status=status,
            consecutive_failures=int(failures_str or 0),
            last_success=last_ok,
            last_failure=last_fail,
            avg_latency_ms=float(latency_str or 0.0),
            total_calls_today=int(calls_day_str or 0),
            total_calls_month=int(calls_mon_str or 0),
            circuit_open_until=open_until,
        )

    async def record_success(self, provider: str, latency_ms: float) -> None:
        """Record a successful call — resets failure count, updates latency EMA."""
        now_iso = datetime.now(timezone.utc).isoformat()

        # Reset failures
        await self._redis_set(
            self._key(provider, "failures"), "0", ttl=self._FAILURE_TTL
        )
        await self._redis_set(
            self._key(provider, "status"),
            ProviderStatus.healthy.value,
            ttl=self._STATUS_TTL,
        )
        await self._redis_set(self._key(provider, "last_ok"), now_iso)

        # Clear circuit open
        await self._redis_delete(self._key(provider, "open_until"))

        # Update latency EMA
        prev_str = await self._redis_get(self._key(provider, "latency"))
        prev = float(prev_str) if prev_str else latency_ms
        ema = self.LATENCY_EMA_ALPHA * latency_ms + (1 - self.LATENCY_EMA_ALPHA) * prev
        await self._redis_set(
            self._key(provider, "latency"), f"{ema:.2f}"
        )

        # Increment counters
        await self._redis_incr(
            self._key(provider, "calls_day"), ttl=self._COUNTER_DAY_TTL
        )
        await self._redis_incr(
            self._key(provider, "calls_mon"), ttl=self._COUNTER_MONTH_TTL
        )

    async def record_failure(self, provider: str, error_type: str) -> None:
        """Record a failed call — increments failure count, may open circuit."""
        now_iso = datetime.now(timezone.utc).isoformat()

        failures = await self._redis_incr(
            self._key(provider, "failures"), ttl=self._FAILURE_TTL
        )
        await self._redis_set(self._key(provider, "last_fail"), now_iso)

        # Increment call counters even for failures
        await self._redis_incr(
            self._key(provider, "calls_day"), ttl=self._COUNTER_DAY_TTL
        )
        await self._redis_incr(
            self._key(provider, "calls_mon"), ttl=self._COUNTER_MONTH_TTL
        )

        if failures >= self.OPEN_THRESHOLD:
            cooldown_until = datetime.fromtimestamp(
                time.time() + self.COOLDOWN_SECONDS, tz=timezone.utc
            ).isoformat()
            await self._redis_set(
                self._key(provider, "status"),
                ProviderStatus.open_circuit.value,
                ttl=self._STATUS_TTL,
            )
            await self._redis_set(
                self._key(provider, "open_until"),
                cooldown_until,
            )
            logger.warning(
                "Circuit OPEN for %s after %d failures (%s). "
                "Cooldown until %s",
                provider,
                failures,
                error_type,
                cooldown_until,
            )
        elif failures >= self.DEGRADED_THRESHOLD:
            await self._redis_set(
                self._key(provider, "status"),
                ProviderStatus.degraded.value,
                ttl=self._STATUS_TTL,
            )
            logger.info(
                "Provider %s DEGRADED after %d failures (%s)",
                provider,
                failures,
                error_type,
            )

    async def is_open(self, provider: str) -> bool:
        """
        True if the circuit is open (provider should NOT be called).

        If the cooldown has elapsed, auto-resets to degraded (half-open).
        """
        status_str = await self._redis_get(self._key(provider, "status"))
        if status_str != ProviderStatus.open_circuit.value:
            return False

        open_until = await self._redis_get(self._key(provider, "open_until"))
        if not open_until:
            return True

        try:
            deadline = datetime.fromisoformat(open_until)
            if datetime.now(timezone.utc) >= deadline:
                # Cooldown elapsed → half-open (degraded)
                await self._redis_set(
                    self._key(provider, "status"),
                    ProviderStatus.degraded.value,
                    ttl=self._STATUS_TTL,
                )
                await self._redis_delete(self._key(provider, "open_until"))
                logger.info(
                    "Circuit for %s cooldown elapsed → DEGRADED (half-open)",
                    provider,
                )
                return False
        except (ValueError, TypeError):
            pass

        return True

    async def get_all_health(self) -> dict[str, ProviderHealth]:
        """Return health for every provider that has any tracked state."""
        # Collect unique provider names from keys
        provider_names: set[str] = set()

        if self._redis is not None:
            try:
                keys: list[bytes | str] = await self._redis.keys("cb:*:status")
                for k in keys:
                    key_str = k.decode() if isinstance(k, bytes) else k
                    parts = key_str.split(":")
                    if len(parts) >= 3:
                        provider_names.add(parts[1])
            except Exception as exc:
                logger.warning("Redis KEYS scan failed: %s", exc)

        # Also include in-memory providers
        for k in self._memory:
            parts = k.split(":")
            if len(parts) >= 3 and parts[0] == "cb":
                provider_names.add(parts[1])

        result: dict[str, ProviderHealth] = {}
        for name in provider_names:
            result[name] = await self.check_health(name)

        return result

    async def reset(self, provider: str) -> None:
        """Fully reset a provider's circuit breaker state."""
        suffixes = [
            "failures", "status", "latency", "last_ok",
            "last_fail", "calls_day", "calls_mon", "open_until",
        ]
        for suffix in suffixes:
            await self._redis_delete(self._key(provider, suffix))
        logger.info("Circuit breaker reset for %s", provider)
