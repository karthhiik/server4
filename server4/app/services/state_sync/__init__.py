"""
Phase 10 -- State Synchronization.

Modules:
    operation_bus      — Typed operation events, undo/redo stack, Redis pub/sub broadcast
    crdt_document      — CRDT document wrapper: OT-based conflict resolution for DSL mutations
    sync_websocket     — WebSocket hub for real-time multi-client DSL sync
    session_store      — Redis-backed editor session persistence (replaces in-memory dict)
    presence_manager   — User presence, cursor tracking, and awareness protocol
"""

from app.services.state_sync.operation_bus import (
    OperationBus,
    OperationType,
    DSLOperation,
    OperationBatch,
)
from app.services.state_sync.crdt_document import (
    CRDTDocument,
    DocumentState,
    MergeResult,
    ConflictResolution,
)
from app.services.state_sync.sync_websocket import (
    SyncHub,
    SyncClient,
    SyncMessage,
    SyncMessageType,
)
from app.services.state_sync.session_store import (
    SessionStore,
    SessionRecord,
    SessionStatus,
)
from app.services.state_sync.presence_manager import (
    PresenceManager,
    UserPresence,
    CursorPosition,
    PresenceEvent,
)

__all__ = [
    # operation_bus
    "OperationBus",
    "OperationType",
    "DSLOperation",
    "OperationBatch",
    # crdt_document
    "CRDTDocument",
    "DocumentState",
    "MergeResult",
    "ConflictResolution",
    # sync_websocket
    "SyncHub",
    "SyncClient",
    "SyncMessage",
    "SyncMessageType",
    # session_store
    "SessionStore",
    "SessionRecord",
    "SessionStatus",
    # presence_manager
    "PresenceManager",
    "UserPresence",
    "CursorPosition",
    "PresenceEvent",
]
