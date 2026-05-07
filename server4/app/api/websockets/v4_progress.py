"""
WebSocket handler for V4 Skeleton-of-Thought pipeline progress.

Replaces the 1.5 s polling loop in `useV4Generation` with push-based streaming.

Channel: ``v4:progress:{project_id}``      (Redis pub/sub, set up by content_pipeline)
Log:     ``v4:progress_log:{project_id}``  (Redis list, capped at 100, TTL 1h)

Event shape on the wire (forwarded verbatim from the pipeline emitter):
    {"stage": "<stage_name>", "payload": {...}, "ts": "<iso8601>"}

Plus, on terminal state, we send an envelope:
    {"type": "status", "status": "completed"|"failed",
     "progress": 100, "message": "...", "overall_score": float|null,
    "duration_ms": int|null, "slide_count": int,
    "llm_trace_summary": list, "llm_trace_count": int}
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["WebSocket-V4"])

# How long to wait for new pub/sub messages before checking MongoDB for terminal state.
_IDLE_CHECK_INTERVAL_S = 2.0
# How long the socket stays open after the pipeline reports terminal state.
_GRACE_PERIOD_S = 1.0
# Hard ceiling on total connection lifetime (server-side guard).
_MAX_CONN_SECONDS = 60 * 30  # 30 minutes


@router.websocket("/ws/v4/progress/{project_id}")
async def v4_progress_ws(
    websocket: WebSocket,
    project_id: str,
    token: Optional[str] = Query(None),
) -> None:
    """Push V4 pipeline progress events to the connected client in real time."""
    await websocket.accept()

    redis_client = None
    pubsub = None

    channel = f"v4:progress:{project_id}"
    log_key = f"v4:progress_log:{project_id}"

    # ── Try Redis pub/sub first ─────────────────────────────────────
    try:
        from app.utils.rate_limiter import get_redis

        redis_client = await get_redis()
        if redis_client is None:
            raise RuntimeError("redis unavailable")
        await redis_client.ping()

        # Replay any events that landed before the client connected.
        try:
            replay = await redis_client.lrange(log_key, 0, -1)
            for event_json in replay:
                await websocket.send_text(event_json)
        except Exception as replay_err:
            logger.warning(
                "v4_ws_replay_failed",
                project_id=project_id,
                error=str(replay_err),
            )

        # If the pipeline already terminated before we connected, send the
        # terminal envelope from MongoDB and exit cleanly.
        terminal = await _read_terminal_state(project_id)
        if terminal is not None:
            await websocket.send_text(json.dumps({"type": "status", **terminal}))
            await _safe_close(websocket)
            return

        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)
    except WebSocketDisconnect:
        logger.info("v4_ws_disconnect_during_redis_setup", project_id=project_id)
        return
    except Exception as e:
        logger.warning(
            "v4_ws_redis_unavailable_fallback_poll",
            project_id=project_id,
            error=str(e),
        )
        try:
            await _stream_mongo_fallback(websocket, project_id)
        except WebSocketDisconnect:
            pass
        return

    # ── Stream live events ──────────────────────────────────────────
    try:
        await _stream_redis(websocket, pubsub, project_id)
    except WebSocketDisconnect:
        logger.info("v4_ws_disconnect", project_id=project_id)
    except Exception as e:
        logger.error("v4_ws_stream_error", project_id=project_id, error=str(e))
        try:
            await websocket.close(code=1011, reason=str(e)[:120])
        except Exception:
            pass
    finally:
        if pubsub is not None:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            except Exception:
                pass


# ── Streaming loops ────────────────────────────────────────────────


async def _stream_redis(
    websocket: WebSocket,
    pubsub,
    project_id: str,
) -> None:
    """Forward Redis pub/sub events to the websocket; poll Mongo for terminal state."""
    elapsed = 0.0
    sent_terminal = False

    while elapsed < _MAX_CONN_SECONDS:
        # Poll Redis for the next event without blocking the event loop.
        message = None
        try:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=_IDLE_CHECK_INTERVAL_S,
            )
        except Exception as e:
            logger.warning(
                "v4_ws_pubsub_get_failed",
                project_id=project_id,
                error=str(e),
            )

        if message and message.get("type") == "message":
            data = message.get("data", "")
            if isinstance(data, bytes):
                data = data.decode("utf-8", errors="ignore")
            try:
                await websocket.send_text(data)
            except Exception:
                return

            # Only `persisted` / `pipeline_complete` / `pipeline_failed` /
            # `failed` are true terminal events. The `complete` stage is
            # emitted by `content_pipeline` BEFORE the router writes the
            # final MongoDB document (slides, generation_state=completed,
            # compiled_slides, design_tokens). If we closed the socket on
            # `complete`, `_read_terminal_state` would return None because
            # Mongo still shows `generating_content`, and the frontend
            # would never receive the `{type:"status", status:"completed"}`
            # envelope — hanging the UI at 100% on the Generation step.
            # Wait for `persisted` (emitted AFTER the router finalizes
            # MongoDB in `generation_v4._run_v4_pipeline`) to close.
            try:
                parsed = json.loads(data)
                stage = (parsed.get("stage") or "").lower()
                if stage in {"pipeline_complete", "pipeline_failed", "persisted", "failed", "error"}:
                    terminal = await _read_terminal_state(project_id)
                    if terminal is not None:
                        await websocket.send_text(
                            json.dumps({"type": "status", **terminal})
                        )
                        sent_terminal = True
                        await asyncio.sleep(_GRACE_PERIOD_S)
                        return
                    # Race: terminal stage arrived before the Mongo write
                    # propagated. Do NOT close the socket — continue the
                    # loop so the next tick (idle poll) can read Mongo
                    # once the router commits, and emit the envelope.
            except json.JSONDecodeError:
                pass
        else:
            # Idle tick — verify the pipeline is still running.
            elapsed += _IDLE_CHECK_INTERVAL_S
            terminal = await _read_terminal_state(project_id)
            if terminal is not None and not sent_terminal:
                await websocket.send_text(
                    json.dumps({"type": "status", **terminal})
                )
                return

        # Drain any client-side ping without blocking the producer side.
        await _drain_client_pings(websocket)


async def _stream_mongo_fallback(
    websocket: WebSocket,
    project_id: str,
) -> None:
    """If Redis is down, poll MongoDB and emit synthetic progress events."""
    last_progress = -1
    elapsed = 0.0
    poll_s = 1.5

    while elapsed < _MAX_CONN_SECONDS:
        terminal = await _read_terminal_state(project_id)
        if terminal is not None:
            await websocket.send_text(json.dumps({"type": "status", **terminal}))
            return

        snapshot = await _read_running_snapshot(project_id)
        if snapshot is not None and snapshot.get("progress", 0) != last_progress:
            await websocket.send_text(
                json.dumps(
                    {
                        "stage": snapshot.get("state") or "running",
                        "payload": {
                            "progress": snapshot.get("progress", 0),
                            "message": snapshot.get("message", ""),
                        },
                        "ts": snapshot.get("updated_at"),
                    },
                    default=str,
                )
            )
            last_progress = snapshot.get("progress", 0)

        await _drain_client_pings(websocket)
        await asyncio.sleep(poll_s)
        elapsed += poll_s


# ── MongoDB helpers ────────────────────────────────────────────────


async def _read_terminal_state(project_id: str) -> Optional[dict]:
    """Return a status envelope dict if the presentation is in a terminal state, else None."""
    try:
        from app.database import get_db

        db = get_db()
        doc = await db.presentations.find_one(
            {"_id": project_id},
            {
                "_id": 0,
                "generation_state": 1,
                "generation_progress": 1,
                "generation_message": 1,
                "generation_error": 1,
                "slide_count": 1,
                "overall_score": 1,
                "duration_ms": 1,
                "llm_trace_summary": 1,
                "llm_trace_count": 1,
            },
        )
    except Exception:
        return None

    if not doc:
        return None

    state = (doc.get("generation_state") or "").lower()
    if state not in {"completed", "failed", "ready", "ready_for_editing"}:
        return None

    is_failed = state == "failed"
    return {
        "status": "failed" if is_failed else "completed",
        "progress": doc.get("generation_progress", 0 if is_failed else 100),
        "message": doc.get("generation_message", "")
        or (doc.get("generation_error") or "")
        or ("Generation failed" if is_failed else "Generation complete"),
        "error": doc.get("generation_error"),
        "slide_count": doc.get("slide_count", 0),
        "overall_score": doc.get("overall_score"),
        "duration_ms": doc.get("duration_ms"),
        "llm_trace_summary": doc.get("llm_trace_summary") or [],
        "llm_trace_count": doc.get("llm_trace_count", 0),
    }


async def _read_running_snapshot(project_id: str) -> Optional[dict]:
    try:
        from app.database import get_db

        db = get_db()
        doc = await db.presentations.find_one(
            {"_id": project_id},
            {
                "_id": 0,
                "generation_state": 1,
                "generation_progress": 1,
                "generation_message": 1,
                "updated_at": 1,
            },
        )
    except Exception:
        return None

    if not doc:
        return None
    return {
        "state": doc.get("generation_state"),
        "progress": doc.get("generation_progress", 0),
        "message": doc.get("generation_message", ""),
        "updated_at": doc.get("updated_at"),
    }


# ── Client message helper ──────────────────────────────────────────


async def _drain_client_pings(websocket: WebSocket) -> None:
    """Non-blocking read of any client message. Responds to 'ping' with 'pong'."""
    try:
        msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.05)
    except (asyncio.TimeoutError, Exception):
        return
    if msg == "ping":
        try:
            await websocket.send_text(json.dumps({"type": "pong"}))
        except Exception:
            pass


async def _safe_close(websocket: WebSocket) -> None:
    try:
        await websocket.close()
    except Exception:
        pass
