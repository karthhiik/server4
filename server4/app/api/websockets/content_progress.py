"""
WebSocket handler for V2 content generation progress.

Subscribes to Redis pub/sub for deck-specific events and
forwards them to the connected frontend client.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket-V2"])


@router.websocket("/ws/v2/deck/{deck_id}/content")
async def content_progress_ws(
    websocket: WebSocket,
    deck_id: str,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for streaming content generation progress.

    Subscribes to Redis pub/sub channel deck:{deck_id}:events.
    Forwards events to the connected frontend.
    Handles:
    - Replay of missed events from Redis log list
    - ping/pong keepalive
    - Graceful shutdown on DECK_CONTENT_COMPLETE
    - MongoDB polling fallback if Redis is unavailable
    """
    await websocket.accept()

    redis_client = None
    pubsub = None
    use_redis = False

    # ── Try connecting to Redis pub/sub ──────────────────────
    try:
        import redis.asyncio as aioredis
        from app.config import settings

        redis_client = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
        # Test connection
        await redis_client.ping()

        # Replay missed events from the log list
        log_key = f"deck:{deck_id}:log"
        missed = await redis_client.lrange(log_key, 0, -1)
        for event_json in missed:
            try:
                await websocket.send_text(event_json)
            except Exception:
                break

        # Subscribe for new events
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"deck:{deck_id}:events")
        use_redis = True
    except Exception as e:
        logger.warning(
            "Redis pub/sub unavailable for deck %s: %s. Falling back to MongoDB polling.",
            deck_id,
            e,
        )

    try:
        if use_redis:
            await _stream_redis(websocket, pubsub, deck_id)
        else:
            await _stream_mongodb_poll(websocket, deck_id)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for deck %s", deck_id)
    except Exception as e:
        logger.error("WebSocket error for deck %s: %s", deck_id, e)
        try:
            await websocket.close(code=1011, reason=str(e)[:120])
        except Exception:
            pass
    finally:
        if pubsub:
            try:
                await pubsub.unsubscribe(f"deck:{deck_id}:events")
                await pubsub.aclose()
            except Exception:
                pass
        if redis_client:
            try:
                await redis_client.aclose()
            except Exception:
                pass


async def _stream_redis(
    websocket: WebSocket, pubsub, deck_id: str
) -> None:
    """Stream events from Redis pub/sub to the WebSocket client."""
    while True:
        # Check for Redis messages (non-blocking with timeout)
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

            # Check for completion event
            try:
                parsed = json.loads(data)
                event_name = parsed.get("event", "")
                if event_name == "deck_content_complete":
                    # Send final ack and close gracefully
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "progress",
                                "state": "ready_for_editing",
                                "progress": 100,
                                "message": "Content generation complete",
                            }
                        )
                    )
                    return
            except (json.JSONDecodeError, KeyError):
                pass

        # Handle incoming messages from client (ping/pong, cancel)
        try:
            client_msg = await asyncio.wait_for(
                websocket.receive_text(), timeout=0.1
            )
            if client_msg == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif client_msg == "cancel":
                logger.info("Client requested cancel for deck %s", deck_id)
                return
        except asyncio.TimeoutError:
            pass


async def _stream_mongodb_poll(
    websocket: WebSocket, deck_id: str
) -> None:
    """Fallback: poll MongoDB for status updates when Redis is unavailable."""
    from app.database import get_db

    last_contracts_count = 0
    poll_interval = 2.0  # seconds

    while True:
        try:
            db = get_db()
        except RuntimeError:
            await asyncio.sleep(poll_interval)
            continue

        run = await db.deck_runs.find_one(
            {"deck_id": deck_id},
            {
                "_id": 0,
                "status": 1,
                "contracts": 1,
                "errors": 1,
                "total_slides": 1,
            },
        )

        if run:
            status = run.get("status", "running")
            contracts = run.get("contracts", [])
            total_slides = run.get("total_slides", 1)
            contracts_count = len(contracts)

            # Send progress update if new contracts appeared
            if contracts_count > last_contracts_count:
                progress = min(
                    int((contracts_count / max(total_slides, 1)) * 100), 99
                )
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "progress",
                            "state": "generating_content",
                            "progress": progress,
                            "message": f"Generated {contracts_count}/{total_slides} slides",
                        }
                    )
                )
                last_contracts_count = contracts_count

            # Terminal states
            if status == "completed":
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "progress",
                            "state": "ready_for_editing",
                            "progress": 100,
                            "message": f"All {contracts_count} slides generated",
                        }
                    )
                )
                return
            elif status == "failed":
                error_msg = run.get("errors", [{}])
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "progress",
                            "state": "failed",
                            "progress": 0,
                            "message": f"Generation failed: {error_msg}",
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
                            "message": f"Generated {contracts_count} slides, {len(errors)} failed",
                        }
                    )
                )
                return

        # Handle client ping/pong during polling
        try:
            client_msg = await asyncio.wait_for(
                websocket.receive_text(), timeout=0.1
            )
            if client_msg == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif client_msg == "cancel":
                return
        except asyncio.TimeoutError:
            pass

        await asyncio.sleep(poll_interval)
