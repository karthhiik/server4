"""
WebSocket Sync Hub -- Real-time multi-client DSL synchronization.

Manages WebSocket connections for collaborative editing:
- Client registration and connection tracking
- Operation broadcast (one client edits → all others receive)
- CRDT state synchronization messages
- Presence awareness (who's connected, cursor positions)
- Heartbeat / keep-alive management

Protocol:
    Client connects → /ws/v2/editor/{presentation_id}/sync?token=...&client_id=...
    Server sends: {"type": "sync_init", "revision": N, "clients": [...]}
    Client sends: {"type": "operation", "data": {...}}
    Server broadcasts: {"type": "operation", "client_id": "...", "data": {...}}
    Client sends: {"type": "presence", "cursor": {...}}
    Server broadcasts: {"type": "presence", "client_id": "...", "cursor": {...}}
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

import structlog
from fastapi import WebSocket

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Message types
# ---------------------------------------------------------------------------


class SyncMessageType(str, Enum):
    """Wire-protocol message types for editor sync."""

    # Server → Client: initialization
    SYNC_INIT = "sync_init"

    # Client → Server: DSL operation
    OPERATION = "operation"

    # Server → Client: broadcast of another client's operation
    OPERATION_BROADCAST = "operation_broadcast"

    # Client ↔ Server: presence / cursor updates
    PRESENCE = "presence"

    # Server → Client: conflict notification
    CONFLICT = "conflict"

    # Client ↔ Server: state sync request/response
    STATE_REQUEST = "state_request"
    STATE_RESPONSE = "state_response"

    # Client → Server: undo / redo
    UNDO = "undo"
    REDO = "redo"

    # Server → Client: undo/redo result
    UNDO_RESULT = "undo_result"
    REDO_RESULT = "redo_result"

    # Heartbeat
    PING = "ping"
    PONG = "pong"

    # Server → Client: error
    ERROR = "error"

    # Server → Client: client joined/left
    CLIENT_JOINED = "client_joined"
    CLIENT_LEFT = "client_left"


class SyncMessage:
    """
    A typed message for the sync protocol.

    Serialized as JSON on the wire.
    """

    __slots__ = ("type", "client_id", "data", "timestamp", "message_id")

    def __init__(
        self,
        msg_type: SyncMessageType,
        client_id: str = "server",
        data: Optional[Dict[str, Any]] = None,
    ):
        self.type = msg_type
        self.client_id = client_id
        self.data = data or {}
        self.timestamp = datetime.now(timezone.utc)
        self.message_id = f"msg_{uuid.uuid4().hex[:8]}"

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "client_id": self.client_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "message_id": self.message_id,
        })

    @classmethod
    def from_json(cls, raw: str) -> "SyncMessage":
        parsed = json.loads(raw)
        msg = cls(
            msg_type=SyncMessageType(parsed["type"]),
            client_id=parsed.get("client_id", "unknown"),
            data=parsed.get("data", {}),
        )
        msg.message_id = parsed.get("message_id", msg.message_id)
        return msg


# ---------------------------------------------------------------------------
# SyncClient -- represents one WebSocket connection
# ---------------------------------------------------------------------------


class SyncClient:
    """
    Represents a single connected WebSocket client in a sync room.

    Tracks connection state, last activity, and buffered messages
    for reliable delivery.
    """

    __slots__ = (
        "client_id", "user_id", "websocket", "presentation_id",
        "connected_at", "last_activity", "is_alive",
        "_send_lock",
    )

    def __init__(
        self,
        client_id: str,
        user_id: str,
        websocket: WebSocket,
        presentation_id: str,
    ):
        self.client_id = client_id
        self.user_id = user_id
        self.websocket = websocket
        self.presentation_id = presentation_id
        self.connected_at = datetime.now(timezone.utc)
        self.last_activity = time.monotonic()
        self.is_alive = True
        self._send_lock = asyncio.Lock()

    async def send(self, message: SyncMessage) -> bool:
        """Send a message to this client. Returns False if disconnected."""
        if not self.is_alive:
            return False
        async with self._send_lock:
            try:
                await self.websocket.send_text(message.to_json())
                self.last_activity = time.monotonic()
                return True
            except Exception:
                self.is_alive = False
                return False

    async def send_json(self, data: Dict[str, Any]) -> bool:
        """Send raw JSON data."""
        if not self.is_alive:
            return False
        async with self._send_lock:
            try:
                await self.websocket.send_text(json.dumps(data))
                self.last_activity = time.monotonic()
                return True
            except Exception:
                self.is_alive = False
                return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "user_id": self.user_id,
            "presentation_id": self.presentation_id,
            "connected_at": self.connected_at.isoformat(),
            "is_alive": self.is_alive,
        }


# ---------------------------------------------------------------------------
# SyncHub -- manages all sync rooms (one per presentation)
# ---------------------------------------------------------------------------


class SyncHub:
    """
    Central hub for real-time editor synchronization.

    Manages "rooms" -- one per presentation. Each room holds a set of
    SyncClients connected via WebSocket. Operations from one client
    are broadcast to all others in the same room.

    Integration points:
    - OperationBus: subscribe to operations and broadcast them
    - CRDTDocument: request merge when operations arrive
    - PresenceManager: forward presence updates
    - SessionStore: verify session validity

    Usage:
        hub = SyncHub()
        client = await hub.connect(websocket, presentation_id, client_id, user_id)
        await hub.handle_client(client)  # runs until disconnect
    """

    def __init__(self, heartbeat_interval: float = 30.0):
        # {presentation_id: {client_id: SyncClient}}
        self._rooms: Dict[str, Dict[str, SyncClient]] = {}
        self._heartbeat_interval = heartbeat_interval
        self._message_handlers: Dict[SyncMessageType, Callable] = {}

    # ── Connection lifecycle ─────────────────────────────────────

    async def connect(
        self,
        websocket: WebSocket,
        presentation_id: str,
        client_id: str,
        user_id: str,
    ) -> SyncClient:
        """
        Register a new client connection to a presentation room.

        Accepts the WebSocket and sends sync_init message.
        """
        await websocket.accept()

        client = SyncClient(
            client_id=client_id,
            user_id=user_id,
            websocket=websocket,
            presentation_id=presentation_id,
        )

        # Add to room
        if presentation_id not in self._rooms:
            self._rooms[presentation_id] = {}
        self._rooms[presentation_id][client_id] = client

        # Send init message
        peers = [
            c.to_dict()
            for cid, c in self._rooms[presentation_id].items()
            if cid != client_id and c.is_alive
        ]
        init_msg = SyncMessage(
            msg_type=SyncMessageType.SYNC_INIT,
            data={
                "client_id": client_id,
                "presentation_id": presentation_id,
                "peers": peers,
                "peer_count": len(peers),
            },
        )
        await client.send(init_msg)

        # Notify others
        await self.broadcast(
            presentation_id,
            SyncMessage(
                msg_type=SyncMessageType.CLIENT_JOINED,
                data=client.to_dict(),
            ),
            exclude={client_id},
        )

        logger.info(
            "sync_client_connected",
            presentation_id=presentation_id,
            client_id=client_id,
            user_id=user_id,
            room_size=len(self._rooms[presentation_id]),
        )
        return client

    async def disconnect(self, client: SyncClient) -> None:
        """Remove a client from its room."""
        client.is_alive = False
        pid = client.presentation_id
        cid = client.client_id

        room = self._rooms.get(pid, {})
        room.pop(cid, None)

        # Remove empty rooms
        if not room:
            self._rooms.pop(pid, None)

        # Notify remaining peers
        await self.broadcast(
            pid,
            SyncMessage(
                msg_type=SyncMessageType.CLIENT_LEFT,
                data={"client_id": cid, "user_id": client.user_id},
            ),
        )

        logger.info(
            "sync_client_disconnected",
            presentation_id=pid,
            client_id=cid,
        )

    # ── Message handling ─────────────────────────────────────────

    async def handle_client(self, client: SyncClient) -> None:
        """
        Main receive loop for a connected client.

        Reads messages, dispatches to handlers, and runs until disconnect.
        This should be called inside the WebSocket endpoint.
        """
        try:
            while client.is_alive:
                try:
                    raw = await asyncio.wait_for(
                        client.websocket.receive_text(),
                        timeout=self._heartbeat_interval + 5,
                    )
                except asyncio.TimeoutError:
                    # Send ping
                    ping_ok = await client.send(
                        SyncMessage(msg_type=SyncMessageType.PING)
                    )
                    if not ping_ok:
                        break
                    continue

                client.last_activity = time.monotonic()

                try:
                    message = SyncMessage.from_json(raw)
                except (json.JSONDecodeError, ValueError):
                    await client.send(SyncMessage(
                        msg_type=SyncMessageType.ERROR,
                        data={"error": "Invalid message format"},
                    ))
                    continue

                # Handle ping/pong locally
                if message.type == SyncMessageType.PING:
                    await client.send(
                        SyncMessage(msg_type=SyncMessageType.PONG)
                    )
                    continue

                # Dispatch to registered handler
                handler = self._message_handlers.get(message.type)
                if handler:
                    try:
                        await handler(client, message)
                    except Exception as exc:
                        logger.error(
                            "sync_handler_error",
                            msg_type=message.type.value,
                            error=str(exc),
                        )
                        await client.send(SyncMessage(
                            msg_type=SyncMessageType.ERROR,
                            data={"error": str(exc)},
                        ))
                else:
                    # Default: broadcast to room
                    await self.broadcast(
                        client.presentation_id,
                        SyncMessage(
                            msg_type=message.type,
                            client_id=client.client_id,
                            data=message.data,
                        ),
                        exclude={client.client_id},
                    )

        except Exception as exc:
            logger.error("sync_client_loop_error", error=str(exc))
        finally:
            await self.disconnect(client)

    def on_message(self, msg_type: SyncMessageType, handler: Callable) -> None:
        """Register a handler for a specific message type."""
        self._message_handlers[msg_type] = handler

    # ── Broadcasting ─────────────────────────────────────────────

    async def broadcast(
        self,
        presentation_id: str,
        message: SyncMessage,
        exclude: Optional[Set[str]] = None,
    ) -> int:
        """
        Broadcast a message to all clients in a room.

        Returns count of successful sends.
        """
        room = self._rooms.get(presentation_id, {})
        exclude = exclude or set()
        sent = 0

        dead_clients: List[str] = []
        for cid, client in room.items():
            if cid in exclude:
                continue
            ok = await client.send(message)
            if ok:
                sent += 1
            elif not client.is_alive:
                dead_clients.append(cid)

        # Clean up dead connections
        for cid in dead_clients:
            room.pop(cid, None)

        return sent

    async def send_to_client(
        self,
        presentation_id: str,
        client_id: str,
        message: SyncMessage,
    ) -> bool:
        """Send a message to a specific client."""
        room = self._rooms.get(presentation_id, {})
        client = room.get(client_id)
        if client:
            return await client.send(message)
        return False

    # ── Room queries ─────────────────────────────────────────────

    def get_room_clients(self, presentation_id: str) -> List[Dict[str, Any]]:
        """Get list of connected clients in a room."""
        room = self._rooms.get(presentation_id, {})
        return [c.to_dict() for c in room.values() if c.is_alive]

    def get_room_count(self, presentation_id: str) -> int:
        """Get count of connected clients in a room."""
        room = self._rooms.get(presentation_id, {})
        return sum(1 for c in room.values() if c.is_alive)

    def get_active_rooms(self) -> Dict[str, int]:
        """Get all active rooms and their client counts."""
        return {
            pid: sum(1 for c in room.values() if c.is_alive)
            for pid, room in self._rooms.items()
            if any(c.is_alive for c in room.values())
        }

    def is_client_connected(self, presentation_id: str, client_id: str) -> bool:
        """Check if a specific client is connected."""
        room = self._rooms.get(presentation_id, {})
        client = room.get(client_id)
        return client is not None and client.is_alive

    @property
    def total_connections(self) -> int:
        return sum(
            sum(1 for c in room.values() if c.is_alive)
            for room in self._rooms.values()
        )

    @property
    def total_rooms(self) -> int:
        return len(self._rooms)

    def get_stats(self) -> Dict[str, Any]:
        """Hub-wide statistics."""
        return {
            "total_connections": self.total_connections,
            "total_rooms": self.total_rooms,
            "rooms": self.get_active_rooms(),
            "handler_count": len(self._message_handlers),
        }
