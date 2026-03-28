from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections import defaultdict
from typing import Dict, List

from redis import exceptions as redis_exceptions
from fastapi import WebSocket

from app.core.config import get_settings
from app.db.redis import get_redis, redis_client
from app.services.presence_service import presence_service

logger = logging.getLogger(__name__)
settings = get_settings()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = defaultdict(list)
        self.instance_id = settings.CHAT_SERVER_INSTANCE_ID
        self._pubsub_task: asyncio.Task | None = None
        self._pubsub = None
        self._pubsub_client = None
        self._stopping_pubsub = False

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id].append(websocket)
        if len(self.active_connections[user_id]) == 1:
            await presence_service.mark_online(user_id)
        else:
            await presence_service.refresh_online(user_id)

    async def disconnect(self, websocket: WebSocket, user_id: str):
        connections = self.active_connections.get(user_id, [])
        if websocket in connections:
            connections.remove(websocket)

        if not connections and user_id in self.active_connections:
            del self.active_connections[user_id]
            await presence_service.mark_offline(user_id)
        elif connections:
            await presence_service.refresh_online(user_id)

    async def heartbeat(self, user_id: str):
        if user_id in self.active_connections:
            await presence_service.refresh_online(user_id)

    async def get_presence(self, user_id: str):
        return await presence_service.get_presence(user_id)

    async def is_user_online(self, user_id: str) -> bool:
        if user_id in self.active_connections and self.active_connections[user_id]:
            return True
        return await presence_service.is_online(user_id)

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id not in self.active_connections:
            return

        stale_connections: list[WebSocket] = []
        for connection in list(self.active_connections[user_id]):
            try:
                await connection.send_json(message)
            except Exception:
                stale_connections.append(connection)

        for connection in stale_connections:
            try:
                self.active_connections[user_id].remove(connection)
            except ValueError:
                continue

        if user_id in self.active_connections and not self.active_connections[user_id]:
            del self.active_connections[user_id]
            await presence_service.mark_offline(user_id)

    async def broadcast(self, message: dict):
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)

    async def emit_to_users(self, message: dict, user_ids: list[str], *, publish: bool = True):
        target_ids = [user_id for user_id in dict.fromkeys(user_ids) if user_id]
        if not target_ids:
            return

        for user_id in target_ids:
            await self.send_personal_message(message, user_id)

        if publish:
            await self.publish_event(
                {
                    "type": "user_event",
                    "target_user_ids": target_ids,
                    "payload": message,
                }
            )

    async def publish_event(self, event: dict):
        redis = await get_redis()
        if redis is None:
            return

        payload = {
            **event,
            "origin_instance": self.instance_id,
        }
        await redis.publish(settings.CHAT_REDIS_EVENT_CHANNEL, json.dumps(payload))

    async def setup_redis_pubsub(self):
        redis = await get_redis()
        if redis is None:
            logger.warning("Redis not available; cross-instance chat fan-out disabled")
            return

        try:
            pubsub_client = await redis_client.create_pubsub_client()
        except Exception as exc:
            logger.warning("Redis pubsub client unavailable; cross-instance chat fan-out disabled: %s", exc)
            return

        pubsub = pubsub_client.pubsub(ignore_subscribe_messages=True)
        self._pubsub_client = pubsub_client
        self._pubsub = pubsub

        try:
            await pubsub.subscribe(settings.CHAT_REDIS_EVENT_CHANNEL)
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                try:
                    data = json.loads(message["data"])
                except Exception:
                    continue

                if data.get("origin_instance") == self.instance_id:
                    continue

                if data.get("type") != "user_event":
                    continue

                payload = data.get("payload")
                target_user_ids = data.get("target_user_ids") or []
                if not isinstance(payload, dict) or not isinstance(target_user_ids, list):
                    continue

                for user_id in target_user_ids:
                    await self.send_personal_message(payload, user_id)
        except asyncio.CancelledError:
            if not self._stopping_pubsub:
                raise
        except (
            asyncio.TimeoutError,
            redis_exceptions.ConnectionError,
            redis_exceptions.TimeoutError,
        ) as exc:
            if self._stopping_pubsub:
                logger.debug("Redis pubsub stopped during shutdown: %s", exc)
            else:
                logger.warning("Redis pubsub listener stopped unexpectedly: %s", exc)
        finally:
            with contextlib.suppress(Exception):
                await pubsub.unsubscribe(settings.CHAT_REDIS_EVENT_CHANNEL)
            with contextlib.suppress(Exception):
                await pubsub.close()
            with contextlib.suppress(Exception):
                await pubsub_client.close()
            self._pubsub = None
            self._pubsub_client = None

    async def start_pubsub(self):
        if self._pubsub_task and not self._pubsub_task.done():
            return
        self._stopping_pubsub = False
        self._pubsub_task = asyncio.create_task(self.setup_redis_pubsub())

    async def stop_pubsub(self):
        if not self._pubsub_task:
            return
        self._stopping_pubsub = True
        if self._pubsub is not None:
            with contextlib.suppress(Exception):
                await self._pubsub.close()
        if self._pubsub_client is not None:
            with contextlib.suppress(Exception):
                await self._pubsub_client.close()
        self._pubsub_task.cancel()
        try:
            await asyncio.wait_for(self._pubsub_task, timeout=1.5)
        except (
            asyncio.CancelledError,
            asyncio.TimeoutError,
            redis_exceptions.ConnectionError,
            redis_exceptions.TimeoutError,
            Exception,
        ):
            pass
        self._pubsub_task = None
        self._pubsub = None
        self._pubsub_client = None
        self._stopping_pubsub = False


manager = ConnectionManager()
