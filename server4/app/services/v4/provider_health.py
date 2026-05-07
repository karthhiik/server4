"""
V4 Provider Health Tracker — auto-mute providers that are chronically failing.

A provider is considered unhealthy when its rolling failure rate over the last
N calls exceeds a threshold. Unhealthy providers are skipped for a cooldown
window. This protects the pipeline from spending budget on broken endpoints
(e.g. NewsAPI returning 426, GitHub 401 on bad token scope).

Usage:
    if not provider_health.is_healthy("newsapi"):
        return []  # skip
    try:
        result = await call_newsapi(...)
        provider_health.record("newsapi", success=True)
    except Exception:
        provider_health.record("newsapi", success=False)
        raise
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class _ProviderState:
    name: str
    history: Deque[bool] = field(default_factory=lambda: deque(maxlen=100))
    muted_until: float = 0.0


class ProviderHealth:
    """Singleton-style tracker. Use module-level helpers below."""

    def __init__(
        self,
        failure_rate_threshold: float = 0.80,
        min_samples: int = 10,
        mute_seconds: float = 3600.0,  # 1 hour
    ) -> None:
        self._states: dict[str, _ProviderState] = {}
        self._threshold = failure_rate_threshold
        self._min_samples = min_samples
        self._mute_seconds = mute_seconds

    def _get(self, name: str) -> _ProviderState:
        state = self._states.get(name)
        if state is None:
            state = _ProviderState(name=name)
            self._states[name] = state
        return state

    def is_healthy(self, name: str) -> bool:
        state = self._get(name)
        return time.monotonic() >= state.muted_until

    def record(self, name: str, success: bool) -> None:
        state = self._get(name)
        state.history.append(success)
        if len(state.history) >= self._min_samples:
            failures = sum(1 for x in state.history if not x)
            failure_rate = failures / len(state.history)
            if failure_rate >= self._threshold and time.monotonic() >= state.muted_until:
                state.muted_until = time.monotonic() + self._mute_seconds
                logger.warning(
                    "provider_health.muted",
                    provider=name,
                    failure_rate=round(failure_rate, 3),
                    samples=len(state.history),
                    mute_for_seconds=self._mute_seconds,
                )

    def mute(
        self,
        name: str,
        *,
        reason: str,
        mute_seconds: float | None = None,
    ) -> None:
        state = self._get(name)
        duration = mute_seconds if mute_seconds is not None else self._mute_seconds
        muted_until = time.monotonic() + duration
        if muted_until <= state.muted_until:
            return
        state.muted_until = muted_until
        logger.info(
            "provider_health.force_muted",
            provider=name,
            reason=reason,
            mute_for_seconds=duration,
        )

    def force_unmute(self, name: str) -> None:
        state = self._get(name)
        state.muted_until = 0.0
        state.history.clear()

    def telemetry(self) -> list[dict]:
        now = time.monotonic()
        out = []
        for state in self._states.values():
            samples = len(state.history)
            failures = sum(1 for x in state.history if not x) if samples else 0
            out.append({
                "provider": state.name,
                "samples": samples,
                "failure_rate": round(failures / samples, 3) if samples else 0.0,
                "healthy": now >= state.muted_until,
                "mute_remaining_seconds": max(0.0, state.muted_until - now),
            })
        return out


# Module-level singleton
_health = ProviderHealth()


def is_healthy(name: str) -> bool:
    return _health.is_healthy(name)


def record(name: str, success: bool) -> None:
    _health.record(name, success)


def mute(name: str, *, reason: str, mute_seconds: float | None = None) -> None:
    _health.mute(name, reason=reason, mute_seconds=mute_seconds)


def force_unmute(name: str) -> None:
    _health.force_unmute(name)


def telemetry() -> list[dict]:
    return _health.telemetry()
