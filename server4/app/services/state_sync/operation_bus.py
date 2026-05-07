"""
Operation Bus -- Typed DSL mutation events with undo/redo and broadcast.

Every mutation to the PresentationDSL flows through the OperationBus.
Operations are:
    1. Captured as typed DSLOperation objects with full before/after state
    2. Pushed onto a per-presentation undo stack
    3. Published to Redis pub/sub for connected WebSocket clients
    4. Logged for audit trail

The bus is the single choke-point between the editor engine and the
outside world, enabling real-time sync, undo/redo, and conflict detection.
"""

import copy
import json
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Operation types
# ---------------------------------------------------------------------------


class OperationType(str, Enum):
    """All possible DSL mutation types."""

    # Slide operations
    SLIDE_ADD = "slide_add"
    SLIDE_REMOVE = "slide_remove"
    SLIDE_MOVE = "slide_move"
    SLIDE_DUPLICATE = "slide_duplicate"
    SLIDE_UPDATE_CONTENT = "slide_update_content"
    SLIDE_UPDATE_STYLE = "slide_update_style"
    SLIDE_UPDATE_TYPE = "slide_update_type"
    SLIDE_UPDATE_NOTES = "slide_update_notes"
    SLIDE_UPDATE_REVEAL = "slide_update_reveal"
    SLIDE_UPDATE_CUSTOM = "slide_update_custom"
    SLIDE_SET_SECTION = "slide_set_section"
    SLIDE_REORDER = "slide_reorder"

    # Element operations
    ELEMENT_ADD = "element_add"
    ELEMENT_REMOVE = "element_remove"
    ELEMENT_UPDATE = "element_update"
    ELEMENT_MOVE = "element_move"
    ELEMENT_RESIZE = "element_resize"

    # Fragment operations
    FRAGMENT_ADD = "fragment_add"
    FRAGMENT_REMOVE = "fragment_remove"

    # Presentation-level operations
    PRESENTATION_UPDATE = "presentation_update"
    THEME_UPDATE = "theme_update"
    RENDERERS_SET = "renderers_set"

    # Batch / compound operations
    BATCH = "batch"

    # Layout operations
    LAYOUT_CHANGE = "layout_change"
    LAYOUT_DECK = "layout_deck"

    # Regeneration operations
    REGENERATE_SLIDE = "regenerate_slide"
    REGENERATE_SECTION = "regenerate_section"
    REGENERATE_DECK = "regenerate_deck"

    # Version operations (not undoable, but tracked)
    SNAPSHOT_CREATE = "snapshot_create"
    ROLLBACK = "rollback"


# ---------------------------------------------------------------------------
# DSLOperation -- immutable record of a single mutation
# ---------------------------------------------------------------------------


class DSLOperation:
    """
    Immutable record of a single DSL mutation.

    Stores enough information for undo (before_state) and redo (after_state),
    plus metadata for conflict detection (vector clock, client_id, timestamp).
    """

    __slots__ = (
        "id",
        "type",
        "presentation_id",
        "client_id",
        "user_id",
        "timestamp",
        "target_id",
        "path",
        "before_state",
        "after_state",
        "metadata",
        "vector_clock",
        "undone",
    )

    def __init__(
        self,
        op_type: OperationType,
        presentation_id: str,
        client_id: str = "server",
        user_id: str = "system",
        target_id: Optional[str] = None,
        path: Optional[str] = None,
        before_state: Optional[Any] = None,
        after_state: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        vector_clock: Optional[Dict[str, int]] = None,
    ):
        self.id = f"op_{uuid.uuid4().hex[:12]}"
        self.type = op_type
        self.presentation_id = presentation_id
        self.client_id = client_id
        self.user_id = user_id
        self.timestamp = datetime.now(timezone.utc)
        self.target_id = target_id
        self.path = path or ""
        self.before_state = before_state
        self.after_state = after_state
        self.metadata = metadata or {}
        self.vector_clock = vector_clock or {}
        self.undone = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "id": self.id,
            "type": self.type.value,
            "presentation_id": self.presentation_id,
            "client_id": self.client_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "target_id": self.target_id,
            "path": self.path,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "metadata": self.metadata,
            "vector_clock": self.vector_clock,
            "undone": self.undone,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DSLOperation":
        """Deserialize from dict."""
        op = cls(
            op_type=OperationType(data["type"]),
            presentation_id=data["presentation_id"],
            client_id=data.get("client_id", "server"),
            user_id=data.get("user_id", "system"),
            target_id=data.get("target_id"),
            path=data.get("path"),
            before_state=data.get("before_state"),
            after_state=data.get("after_state"),
            metadata=data.get("metadata", {}),
            vector_clock=data.get("vector_clock", {}),
        )
        op.id = data.get("id", op.id)
        op.undone = data.get("undone", False)
        if "timestamp" in data:
            op.timestamp = datetime.fromisoformat(data["timestamp"])
        return op

    @property
    def is_undoable(self) -> bool:
        """Whether this operation can be undone."""
        non_undoable = {
            OperationType.SNAPSHOT_CREATE,
            OperationType.ROLLBACK,
        }
        return self.type not in non_undoable and self.before_state is not None


# ---------------------------------------------------------------------------
# OperationBatch -- group of operations applied atomically
# ---------------------------------------------------------------------------


class OperationBatch:
    """
    A group of operations that should be applied/undone together.

    Used for compound edits like:
    - Reorder slides (multiple moves)
    - Section regeneration (remove old + add new)
    - Layout change with content reflow
    """

    __slots__ = ("id", "operations", "description", "timestamp")

    def __init__(
        self,
        operations: Optional[List[DSLOperation]] = None,
        description: str = "",
    ):
        self.id = f"batch_{uuid.uuid4().hex[:12]}"
        self.operations = operations or []
        self.description = description
        self.timestamp = datetime.now(timezone.utc)

    def add(self, op: DSLOperation) -> None:
        """Add operation to batch."""
        self.operations.append(op)

    @property
    def size(self) -> int:
        return len(self.operations)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "operations": [op.to_dict() for op in self.operations],
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# UndoRedoStack -- per-presentation undo/redo with operation limit
# ---------------------------------------------------------------------------


class UndoRedoStack:
    """
    Per-presentation undo/redo stack.

    Max depth prevents unbounded memory. Undo pops from undo_stack
    and pushes the inverse onto redo_stack. Any new operation clears
    the redo stack (no branching history in this model).
    """

    MAX_DEPTH = 200

    def __init__(self):
        self._undo: List[DSLOperation] = []
        self._redo: List[DSLOperation] = []

    def push(self, op: DSLOperation) -> None:
        """Push a new operation. Clears redo stack."""
        if op.is_undoable:
            self._undo.append(op)
            if len(self._undo) > self.MAX_DEPTH:
                self._undo.pop(0)
            self._redo.clear()

    def can_undo(self) -> bool:
        return len(self._undo) > 0

    def can_redo(self) -> bool:
        return len(self._redo) > 0

    def undo(self) -> Optional[DSLOperation]:
        """Pop last operation for undo. Returns the operation to reverse."""
        if not self._undo:
            return None
        op = self._undo.pop()
        op.undone = True
        self._redo.append(op)
        return op

    def redo(self) -> Optional[DSLOperation]:
        """Pop last undone operation for redo."""
        if not self._redo:
            return None
        op = self._redo.pop()
        op.undone = False
        self._undo.append(op)
        return op

    @property
    def undo_count(self) -> int:
        return len(self._undo)

    @property
    def redo_count(self) -> int:
        return len(self._redo)

    @property
    def history(self) -> List[Dict[str, Any]]:
        """Return summary of undo stack (most recent first)."""
        return [
            {
                "id": op.id,
                "type": op.type.value,
                "target_id": op.target_id,
                "timestamp": op.timestamp.isoformat(),
                "user_id": op.user_id,
            }
            for op in reversed(self._undo)
        ]

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()


# ---------------------------------------------------------------------------
# OperationBus -- central event bus for all DSL mutations
# ---------------------------------------------------------------------------


class OperationBus:
    """
    Central event bus for DSL mutations.

    Responsibilities:
    1. Record every mutation as a DSLOperation
    2. Maintain per-presentation undo/redo stacks
    3. Track vector clocks for causal ordering
    4. Publish operations to subscribers (WebSocket sync, Redis pub/sub)
    5. Provide operation log for audit trail

    Usage:
        bus = OperationBus()
        op = bus.record(
            OperationType.SLIDE_ADD,
            "pres-123",
            target_id="slide_abc",
            after_state={"type": "custom", "index": 3},
            client_id="client_1",
            user_id="user_42",
        )
        # All subscribers notified immediately
        # Undo stack updated
    """

    def __init__(self, max_log_size: int = 1000):
        self._stacks: Dict[str, UndoRedoStack] = defaultdict(UndoRedoStack)
        self._vector_clocks: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self._subscribers: List[Callable[[DSLOperation], None]] = []
        self._async_subscribers: List[Callable] = []
        self._operation_log: List[DSLOperation] = []
        self._max_log_size = max_log_size

    # ── Recording operations ──────────────────────────────────────

    def record(
        self,
        op_type: OperationType,
        presentation_id: str,
        target_id: Optional[str] = None,
        path: Optional[str] = None,
        before_state: Optional[Any] = None,
        after_state: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        client_id: str = "server",
        user_id: str = "system",
    ) -> DSLOperation:
        """
        Record a new DSL mutation.

        Increments vector clock, creates operation, pushes to undo stack,
        notifies all subscribers.
        """
        # Increment vector clock for this client
        vc = self._vector_clocks[presentation_id]
        vc[client_id] = vc.get(client_id, 0) + 1
        clock_snapshot = dict(vc)

        op = DSLOperation(
            op_type=op_type,
            presentation_id=presentation_id,
            client_id=client_id,
            user_id=user_id,
            target_id=target_id,
            path=path,
            before_state=before_state,
            after_state=after_state,
            metadata=metadata,
            vector_clock=clock_snapshot,
        )

        # Push to undo stack
        self._stacks[presentation_id].push(op)

        # Append to operation log
        self._operation_log.append(op)
        if len(self._operation_log) > self._max_log_size:
            self._operation_log.pop(0)

        # Notify sync subscribers
        for cb in self._subscribers:
            try:
                cb(op)
            except Exception as exc:
                logger.error("subscriber_error", error=str(exc), op_id=op.id)

        logger.debug(
            "operation_recorded",
            op_type=op.type.value,
            presentation_id=presentation_id,
            target_id=target_id,
            client_id=client_id,
        )
        return op

    def record_batch(
        self,
        ops: List[DSLOperation],
        description: str = "",
    ) -> OperationBatch:
        """Record a batch of operations (applied atomically)."""
        batch = OperationBatch(operations=ops, description=description)
        for op in ops:
            self._stacks[op.presentation_id].push(op)
            self._operation_log.append(op)
        # Trim log
        while len(self._operation_log) > self._max_log_size:
            self._operation_log.pop(0)
        # Notify for last op only (batch summary)
        if ops:
            for cb in self._subscribers:
                try:
                    cb(ops[-1])
                except Exception as exc:
                    logger.error("batch_subscriber_error", error=str(exc))
        return batch

    # ── Undo / Redo ──────────────────────────────────────────────

    def undo(self, presentation_id: str) -> Optional[DSLOperation]:
        """
        Undo the last operation for a presentation.

        Returns the operation that was undone (caller applies before_state).
        """
        op = self._stacks[presentation_id].undo()
        if op:
            logger.info("operation_undone", op_id=op.id, op_type=op.type.value)
        return op

    def redo(self, presentation_id: str) -> Optional[DSLOperation]:
        """
        Redo the last undone operation.

        Returns the operation to re-apply (caller applies after_state).
        """
        op = self._stacks[presentation_id].redo()
        if op:
            logger.info("operation_redone", op_id=op.id, op_type=op.type.value)
        return op

    def can_undo(self, presentation_id: str) -> bool:
        return self._stacks[presentation_id].can_undo()

    def can_redo(self, presentation_id: str) -> bool:
        return self._stacks[presentation_id].can_redo()

    def get_undo_history(self, presentation_id: str) -> List[Dict[str, Any]]:
        """Get undo stack summary for UI display."""
        return self._stacks[presentation_id].history

    # ── Vector clocks ────────────────────────────────────────────

    def get_vector_clock(self, presentation_id: str) -> Dict[str, int]:
        """Get current vector clock for a presentation."""
        return dict(self._vector_clocks.get(presentation_id, {}))

    def is_causally_ready(
        self, presentation_id: str, incoming_clock: Dict[str, int]
    ) -> bool:
        """
        Check if an incoming operation is causally ready to be applied.

        An operation is causally ready when our local clock is >= the
        incoming clock for all entries except the sender.
        """
        local = self._vector_clocks.get(presentation_id, {})
        for client_id, remote_val in incoming_clock.items():
            local_val = local.get(client_id, 0)
            if local_val < remote_val:
                return False
        return True

    # ── Subscribers ──────────────────────────────────────────────

    def subscribe(self, callback: Callable[[DSLOperation], None]) -> None:
        """Register a synchronous subscriber for operation events."""
        self._subscribers.append(callback)

    def subscribe_async(self, callback: Callable) -> None:
        """Register an async subscriber (for WebSocket broadcast)."""
        self._async_subscribers.append(callback)

    def unsubscribe(self, callback: Callable) -> None:
        """Remove a subscriber."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
        if callback in self._async_subscribers:
            self._async_subscribers.remove(callback)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers) + len(self._async_subscribers)

    # ── Operation log ────────────────────────────────────────────

    def get_operations(
        self,
        presentation_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[DSLOperation]:
        """
        Get recent operations, optionally filtered by presentation and time.
        """
        ops = self._operation_log
        if presentation_id:
            ops = [o for o in ops if o.presentation_id == presentation_id]
        if since:
            ops = [o for o in ops if o.timestamp >= since]
        return ops[-limit:]

    @property
    def total_operations(self) -> int:
        return len(self._operation_log)

    # ── Cleanup ──────────────────────────────────────────────────

    def clear_presentation(self, presentation_id: str) -> int:
        """Remove all state for a presentation. Returns ops removed."""
        count = 0
        if presentation_id in self._stacks:
            count += self._stacks[presentation_id].undo_count
            count += self._stacks[presentation_id].redo_count
            del self._stacks[presentation_id]
        if presentation_id in self._vector_clocks:
            del self._vector_clocks[presentation_id]
        self._operation_log = [
            o for o in self._operation_log if o.presentation_id != presentation_id
        ]
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Bus-wide statistics."""
        return {
            "total_operations": self.total_operations,
            "presentations_tracked": len(self._stacks),
            "subscriber_count": self.subscriber_count,
            "stacks": {
                pid: {
                    "undo": stack.undo_count,
                    "redo": stack.redo_count,
                }
                for pid, stack in self._stacks.items()
            },
        }
