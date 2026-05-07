"""
Presence Manager -- User presence, cursor tracking, and awareness.

Implements the awareness protocol for collaborative editing:
- Track which users are connected to which presentations
- Track cursor positions (slide + element + coordinates)
- Broadcast presence/cursor updates to peers
- Auto-expire stale presence after inactivity

This is a lightweight in-memory presence system. For persistent
presence across server instances, the data can be mirrored to Redis.
"""

import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import structlog

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class CursorPosition:
    """
    A user's cursor position within the presentation editor.

    Tracks which slide they're viewing, which element they're editing,
    and their approximate viewport coordinates (for ghost cursor display).
    """

    __slots__ = (
        "slide_id", "element_id",
        "x", "y",
        "selection_start", "selection_end",
        "timestamp",
    )

    def __init__(
        self,
        slide_id: str = "",
        element_id: Optional[str] = None,
        x: float = 0.0,
        y: float = 0.0,
        selection_start: Optional[int] = None,
        selection_end: Optional[int] = None,
    ):
        self.slide_id = slide_id
        self.element_id = element_id
        self.x = x
        self.y = y
        self.selection_start = selection_start
        self.selection_end = selection_end
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slide_id": self.slide_id,
            "element_id": self.element_id,
            "x": self.x,
            "y": self.y,
            "selection_start": self.selection_start,
            "selection_end": self.selection_end,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CursorPosition":
        pos = cls(
            slide_id=data.get("slide_id", ""),
            element_id=data.get("element_id"),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            selection_start=data.get("selection_start"),
            selection_end=data.get("selection_end"),
        )
        return pos


class PresenceEvent(str, Enum):
    """Types of presence events."""
    JOINED = "joined"
    LEFT = "left"
    CURSOR_MOVED = "cursor_moved"
    SLIDE_CHANGED = "slide_changed"
    EDITING_STARTED = "editing_started"
    EDITING_STOPPED = "editing_stopped"
    IDLE = "idle"
    ACTIVE = "active"


class UserPresence:
    """
    Tracks a single user's presence state.

    Includes connection info, cursor position, activity status,
    and a display color for ghost cursors.
    """

    # Default colors for collaborative cursors (up to 8 users)
    CURSOR_COLORS = [
        "#3B82F6",  # blue
        "#10B981",  # green
        "#F59E0B",  # amber
        "#EF4444",  # red
        "#8B5CF6",  # violet
        "#EC4899",  # pink
        "#06B6D4",  # cyan
        "#F97316",  # orange
    ]

    __slots__ = (
        "user_id", "client_id", "presentation_id",
        "display_name", "color",
        "cursor", "is_editing", "active_slide_id",
        "connected_at", "last_activity",
        "is_idle",
    )

    def __init__(
        self,
        user_id: str,
        client_id: str,
        presentation_id: str,
        display_name: str = "",
        color_index: int = 0,
    ):
        self.user_id = user_id
        self.client_id = client_id
        self.presentation_id = presentation_id
        self.display_name = display_name or f"User {user_id[:6]}"
        self.color = self.CURSOR_COLORS[color_index % len(self.CURSOR_COLORS)]
        self.cursor = CursorPosition()
        self.is_editing = False
        self.active_slide_id = ""
        self.connected_at = datetime.now(timezone.utc)
        self.last_activity = time.monotonic()
        self.is_idle = False

    def update_cursor(self, cursor: CursorPosition) -> None:
        """Update cursor position."""
        self.cursor = cursor
        self.last_activity = time.monotonic()
        self.is_idle = False
        if cursor.slide_id:
            self.active_slide_id = cursor.slide_id

    def mark_editing(self, editing: bool) -> None:
        self.is_editing = editing
        self.last_activity = time.monotonic()
        self.is_idle = False

    def mark_idle(self) -> None:
        self.is_idle = True

    def mark_active(self) -> None:
        self.is_idle = False
        self.last_activity = time.monotonic()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "client_id": self.client_id,
            "presentation_id": self.presentation_id,
            "display_name": self.display_name,
            "color": self.color,
            "cursor": self.cursor.to_dict(),
            "is_editing": self.is_editing,
            "active_slide_id": self.active_slide_id,
            "is_idle": self.is_idle,
            "connected_at": self.connected_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# PresenceManager -- per-presentation presence tracking
# ---------------------------------------------------------------------------


class PresenceManager:
    """
    Manages user presence for collaborative editing sessions.

    Tracks connected users per presentation, their cursor positions,
    editing state, and idle detection.

    Usage:
        pm = PresenceManager()
        presence = pm.join("pres-123", "user-1", "client-abc")
        pm.update_cursor("pres-123", "client-abc", CursorPosition(slide_id="slide_0"))
        peers = pm.get_peers("pres-123", exclude_client="client-abc")
        pm.leave("pres-123", "client-abc")
    """

    IDLE_TIMEOUT = 120.0  # seconds before marking user idle

    def __init__(self, idle_timeout: float = IDLE_TIMEOUT):
        # {presentation_id: {client_id: UserPresence}}
        self._presence: Dict[str, Dict[str, UserPresence]] = {}
        self._idle_timeout = idle_timeout
        # Track color assignment per room
        self._color_counters: Dict[str, int] = {}

    # ── Join / Leave ─────────────────────────────────────────────

    def join(
        self,
        presentation_id: str,
        user_id: str,
        client_id: str,
        display_name: str = "",
    ) -> UserPresence:
        """Register a user as present in a presentation."""
        if presentation_id not in self._presence:
            self._presence[presentation_id] = {}
            self._color_counters[presentation_id] = 0

        color_idx = self._color_counters[presentation_id]
        self._color_counters[presentation_id] = color_idx + 1

        presence = UserPresence(
            user_id=user_id,
            client_id=client_id,
            presentation_id=presentation_id,
            display_name=display_name,
            color_index=color_idx,
        )
        self._presence[presentation_id][client_id] = presence

        logger.info(
            "presence_joined",
            presentation_id=presentation_id,
            user_id=user_id,
            client_id=client_id,
        )
        return presence

    def leave(self, presentation_id: str, client_id: str) -> Optional[UserPresence]:
        """Remove a user's presence. Returns the removed presence."""
        room = self._presence.get(presentation_id, {})
        presence = room.pop(client_id, None)

        # Clean up empty rooms
        if not room:
            self._presence.pop(presentation_id, None)
            self._color_counters.pop(presentation_id, None)

        if presence:
            logger.info(
                "presence_left",
                presentation_id=presentation_id,
                client_id=client_id,
            )
        return presence

    # ── Cursor updates ───────────────────────────────────────────

    def update_cursor(
        self,
        presentation_id: str,
        client_id: str,
        cursor: CursorPosition,
    ) -> bool:
        """Update a user's cursor position. Returns False if not present."""
        room = self._presence.get(presentation_id, {})
        presence = room.get(client_id)
        if not presence:
            return False
        presence.update_cursor(cursor)
        return True

    def set_editing(
        self,
        presentation_id: str,
        client_id: str,
        editing: bool,
    ) -> bool:
        """Set whether a user is actively editing."""
        room = self._presence.get(presentation_id, {})
        presence = room.get(client_id)
        if not presence:
            return False
        presence.mark_editing(editing)
        return True

    # ── Queries ──────────────────────────────────────────────────

    def get_presence(
        self, presentation_id: str, client_id: str
    ) -> Optional[UserPresence]:
        """Get a specific user's presence."""
        room = self._presence.get(presentation_id, {})
        return room.get(client_id)

    def get_peers(
        self,
        presentation_id: str,
        exclude_client: Optional[str] = None,
    ) -> List[UserPresence]:
        """Get all peers in a presentation room."""
        room = self._presence.get(presentation_id, {})
        return [
            p for cid, p in room.items()
            if cid != exclude_client
        ]

    def get_peer_dicts(
        self,
        presentation_id: str,
        exclude_client: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get serialized peer list."""
        return [p.to_dict() for p in self.get_peers(presentation_id, exclude_client)]

    def get_users_on_slide(
        self, presentation_id: str, slide_id: str
    ) -> List[UserPresence]:
        """Get all users currently viewing a specific slide."""
        room = self._presence.get(presentation_id, {})
        return [
            p for p in room.values()
            if p.active_slide_id == slide_id
        ]

    def get_user_count(self, presentation_id: str) -> int:
        """Get count of present users."""
        return len(self._presence.get(presentation_id, {}))

    # ── Idle detection ───────────────────────────────────────────

    def check_idle(self, presentation_id: str) -> List[str]:
        """
        Check for idle users and mark them. Returns list of newly idle client_ids.
        """
        now = time.monotonic()
        room = self._presence.get(presentation_id, {})
        newly_idle = []

        for cid, presence in room.items():
            elapsed = now - presence.last_activity
            if elapsed > self._idle_timeout and not presence.is_idle:
                presence.mark_idle()
                newly_idle.append(cid)

        return newly_idle

    def check_all_idle(self) -> Dict[str, List[str]]:
        """Check all rooms for idle users. Returns {presentation_id: [client_ids]}."""
        result = {}
        for pid in list(self._presence.keys()):
            idle = self.check_idle(pid)
            if idle:
                result[pid] = idle
        return result

    # ── Cleanup ──────────────────────────────────────────────────

    def cleanup_room(self, presentation_id: str) -> int:
        """Remove all presence data for a presentation. Returns count removed."""
        room = self._presence.pop(presentation_id, {})
        self._color_counters.pop(presentation_id, None)
        return len(room)

    @property
    def total_users(self) -> int:
        return sum(len(room) for room in self._presence.values())

    @property
    def total_rooms(self) -> int:
        return len(self._presence)

    def get_stats(self) -> Dict[str, Any]:
        """Manager-wide statistics."""
        return {
            "total_users": self.total_users,
            "total_rooms": self.total_rooms,
            "rooms": {
                pid: {
                    "user_count": len(room),
                    "editing_count": sum(1 for p in room.values() if p.is_editing),
                    "idle_count": sum(1 for p in room.values() if p.is_idle),
                }
                for pid, room in self._presence.items()
            },
        }
