"""
WebSocket handler for V3 unified pipeline progress.

Subscribes to Redis pub/sub for deck-specific V3 events and
forwards them to the connected frontend client.

Channel: deck:{deck_id}:v3:events
Log:     deck:{deck_id}:v3:events:log
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket-V3"])


@router.websocket("/ws/v3/deck/{deck_id}/progress")
async def v3_progress_ws(
    websocket: WebSocket,
    deck_id: str,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for V3 unified pipeline progress streaming.

    Subscribes to Redis channel ``deck:{deck_id}:v3:events``.
    Replays missed events from ``deck:{deck_id}:v3:events:log``.
    Falls back to MongoDB polling (``deck_runs_v3``) if Redis unavailable.
    """
    await websocket.accept()

    redis_client = None
    pubsub = None
    use_redis = False

    channel = f"deck:{deck_id}:v3:events"
    log_key = f"deck:{deck_id}:v3:events:log"

    # ── Try connecting to Redis pub/sub ──────────────────────
    try:
        import redis.asyncio as aioredis
        from app.config import settings

        redis_client = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
        await redis_client.ping()

        # Replay missed events from the log list
        missed = await redis_client.lrange(log_key, 0, -1)
        for event_json in missed:
            try:
                await websocket.send_text(event_json)
            except Exception:
                break

        # Subscribe for new events
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)
        use_redis = True
    except Exception as e:
        logger.warning(
            "Redis pub/sub unavailable for V3 deck %s: %s. Falling back to MongoDB.",
            deck_id,
            e,
        )

    try:
        if use_redis:
            await _stream_redis(websocket, pubsub, channel, deck_id)
        else:
            await _stream_mongodb_poll(websocket, deck_id)
    except WebSocketDisconnect:
        logger.info("V3 WebSocket disconnected for deck %s", deck_id)
    except Exception as e:
        logger.error("V3 WebSocket error for deck %s: %s", deck_id, e)
        try:
            await websocket.close(code=1011, reason=str(e)[:120])
        except Exception:
            pass
    finally:
        if pubsub:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            except Exception:
                pass
        if redis_client:
            try:
                await redis_client.aclose()
            except Exception:
                pass


async def _stream_redis(
    websocket: WebSocket,
    pubsub,
    channel: str,
    deck_id: str,
) -> None:
    """Stream events from V3 Redis pub/sub channel to the WebSocket client."""
    while True:
        # Non-blocking read from Redis pub/sub
        try:
            message = await asyncio.wait_for(
                pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                ),
                timeout=5.0,
            )
        except asyncio.TimeoutError:
            message = None

        if message and message.get("type") == "message":
            data = message.get("data", "")
            await websocket.send_text(data)

            # Check for terminal events
            try:
                parsed = json.loads(data)
                event_name = parsed.get("event", "")
                if event_name in (
                    "deck_content_complete",
                    "pipeline_complete",
                    "pipeline_failed",
                ):
                    # Send final ack
                    state = (
                        "ready_for_editing"
                        if "complete" in event_name
                        else "failed"
                    )
                    progress = 100 if state == "ready_for_editing" else 0
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "progress",
                                "state": state,
                                "progress": progress,
                                "message": parsed.get(
                                    "message", "Generation finished"
                                ),
                            }
                        )
                    )
                    return
            except (json.JSONDecodeError, KeyError):
                pass

        # Handle client messages (ping/pong, cancel)
        try:
            client_msg = await asyncio.wait_for(
                websocket.receive_text(), timeout=0.1
            )
            if client_msg == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif client_msg == "cancel":
                logger.info(
                    "V3 client requested cancel for deck %s", deck_id
                )
                # Set cancel key in Redis
                try:
                    import redis.asyncio as aioredis
                    from app.config import settings

                    cancel_client = aioredis.from_url(
                        settings.REDIS_URL, decode_responses=True
                    )
                    await cancel_client.set(
                        f"deck:{deck_id}:cancel", "1", ex=600
                    )
                    await cancel_client.aclose()
                except Exception:
                    pass
                return
        except asyncio.TimeoutError:
            pass


async def _stream_mongodb_poll(
    websocket: WebSocket, deck_id: str
) -> None:
    """Fallback: poll MongoDB deck_runs_v3 when Redis is unavailable."""
    from app.database import get_db

    last_slide_count = 0
    poll_interval = 2.0

    while True:
        try:
            db = get_db()
        except RuntimeError:
            await asyncio.sleep(poll_interval)
            continue

        run = await db.deck_runs_v3.find_one(
            {"deck_id": deck_id},
            {
                "_id": 0,
                "status": 1,
                "slides": 1,
                "errors": 1,
                "mode": 1,
                "total_time_ms": 1,
                "quality_score": 1,
            },
        )

        if run:
            status = run.get("status", "running")
            slides = run.get("slides", [])
            slide_count = len(slides)
            mode = run.get("mode", "standard")

            # Send progress when new slides appear
            if slide_count > last_slide_count:
                progress = min(
                    int((slide_count / max(slide_count + 1, 1)) * 90), 95
                )
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "progress",
                            "state": "generating_content",
                            "progress": progress,
                            "message": f"[{mode}] Generated {slide_count} slides",
                        }
                    )
                )
                last_slide_count = slide_count

            # Terminal states
            if status == "completed":
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "progress",
                            "state": "ready_for_editing",
                            "progress": 100,
                            "message": f"V3 {mode} generation complete — {slide_count} slides",
                        }
                    )
                )
                return
            elif status == "failed":
                errors = run.get("errors", [])
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "progress",
                            "state": "failed",
                            "progress": 0,
                            "message": f"Generation failed: {errors}",
                        }
                    )
                )
                return
            elif status == "partial":
                errors = run.get("errors", [])
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "progress",
                            "state": "partial",
                            "progress": 100,
                            "message": f"Partial: {slide_count} slides, {len(errors)} failed",
                        }
                    )
                )
                return
            elif status == "cancelled":
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "progress",
                            "state": "cancelled",
                            "progress": 0,
                            "message": "Generation cancelled by user",
                        }
                    )
                )
                return

        # Handle client ping/pong
        try:
            client_msg = await asyncio.wait_for(
                websocket.receive_text(), timeout=0.1
            )
            if client_msg == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
        except asyncio.TimeoutError:
            pass

        await asyncio.sleep(poll_interval)
