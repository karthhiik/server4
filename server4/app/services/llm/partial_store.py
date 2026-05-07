"""
Partial-Draft Store — Redis stash of interrupted LLM outputs for resume.

Purpose:
    When a model times out or 429s mid-generation, the next model in the
    chain picks up the partial draft instead of starting from scratch. This
    is the LangChain `RunnableWithFallbacks(exception_key=...)` pattern,
    hand-rolled on our existing Redis.

Keys:
    llm:partial:{project_id}:{phase}:{slot}  →  partial text   (TTL 1h)

If Redis is unreachable, the module degrades to an in-memory dict scoped
to the process (best-effort — the pipeline still works, just without
cross-worker resume).
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


_LOCAL: dict[str, tuple[str, float]] = {}   # key → (value, expire_ts)
_LOCAL_LOCK = asyncio.Lock()
_TTL_S = 3600


def _key(project_id: str, phase: str, slot: str) -> str:
    pid = (project_id or "_").replace(":", "_")
    ph = (phase or "_").replace(":", "_")
    sl = (slot or "_").replace(":", "_")
    return f"llm:partial:{pid}:{ph}:{sl}"


async def _get_redis():
    # Reuse the token_bucket singleton so we don't double-open connections.
    try:
        import app.services.llm.token_bucket as _tb
        return await _tb._get_redis()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return None


async def save_partial(project_id: str, phase: str, slot: str, text: str) -> None:
    if not text or not text.strip():
        return
    # Trim to 4000 chars — we only need the tail so the next model can
    # continue. Models don't need the entire prior output re-echoed.
    trimmed = text.strip()[-4000:]
    k = _key(project_id, phase, slot)
    async with _LOCAL_LOCK:
        _LOCAL[k] = (trimmed, time.time() + _TTL_S)

    client = await _get_redis()
    if client is None:
        return
    try:
        await client.setex(k, _TTL_S, trimmed)
    except Exception as e:  # noqa: BLE001
        logger.debug("partial_store_setex_failed", key=k, error=str(e)[:120])


async def load_partial(project_id: str, phase: str, slot: str) -> Optional[str]:
    k = _key(project_id, phase, slot)
    now = time.time()
    async with _LOCAL_LOCK:
        entry = _LOCAL.get(k)
        if entry is not None:
            val, exp = entry
            if exp > now:
                return val
            _LOCAL.pop(k, None)

    client = await _get_redis()
    if client is None:
        return None
    try:
        val = await client.get(k)
        if val:
            async with _LOCAL_LOCK:
                _LOCAL[k] = (val, now + 60)  # short local cache
        return val
    except Exception as e:  # noqa: BLE001
        logger.debug("partial_store_get_failed", key=k, error=str(e)[:120])
        return None


async def clear_partial(project_id: str, phase: str, slot: str) -> None:
    k = _key(project_id, phase, slot)
    async with _LOCAL_LOCK:
        _LOCAL.pop(k, None)
    client = await _get_redis()
    if client is None:
        return
    try:
        await client.delete(k)
    except Exception:  # noqa: BLE001
        pass


__all__ = ["save_partial", "load_partial", "clear_partial"]
