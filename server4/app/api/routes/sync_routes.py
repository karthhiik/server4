"""
Phase 10 -- State Synchronization API Routes.

REST + WebSocket endpoints:
    - WebSocket sync endpoint for real-time collaborative editing
    - Session store management (list / get / close / stats)
    - Undo / redo via HTTP
    - Presence queries
    - Sync state and conflict log
    - Operation bus stats and log
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.services.state_sync.operation_bus import (
    OperationBus,
    OperationType,
    DSLOperation,
)
from app.services.state_sync.crdt_document import (
    CRDTDocument,
    DocumentState,
    MergeResult,
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
    CursorPosition,
    PresenceEvent,
    UserPresence,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/sync", tags=["state-sync-v2"])


# ═══════════════════════════════════════════════════════════════════
# SINGLETONS -- shared state for the sync layer
# ═══════════════════════════════════════════════════════════════════

_operation_bus = OperationBus()
_sync_hub = SyncHub()
_session_store = SessionStore()
_presence_manager = PresenceManager()
_crdt_documents: Dict[str, CRDTDocument] = {}


def get_operation_bus() -> OperationBus:
    return _operation_bus


def get_sync_hub() -> SyncHub:
    return _sync_hub


def get_session_store() -> SessionStore:
    return _session_store


def get_presence_manager() -> PresenceManager:
    return _presence_manager


def get_crdt_document(presentation_id: str) -> Optional[CRDTDocument]:
    return _crdt_documents.get(presentation_id)


def register_crdt_document(presentation_id: str, doc: CRDTDocument) -> None:
    _crdt_documents[presentation_id] = doc


def unregister_crdt_document(presentation_id: str) -> None:
    _crdt_documents.pop(presentation_id, None)


# ═══════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════


class SyncResponse(BaseModel):
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None


class MergeRequest(BaseModel):
    client_id: str
    update: Dict[str, Any] = Field(description="Dot-notation field updates")
    client_clock: Optional[Dict[str, int]] = None


class UndoRedoResponse(BaseModel):
    success: bool
    operation_id: Optional[str] = None
    operation_type: Optional[str] = None
    state: Optional[Dict[str, Any]] = None
    can_undo: bool = False
    can_redo: bool = False


class CursorUpdateRequest(BaseModel):
    client_id: str
    slide_id: str = ""
    element_id: Optional[str] = None
    x: float = 0.0
    y: float = 0.0
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None


# ═══════════════════════════════════════════════════════════════════
# WEBSOCKET SYNC ENDPOINT
# ═══════════════════════════════════════════════════════════════════


@router.websocket("/ws/{presentation_id}")
async def sync_websocket(
    websocket: WebSocket,
    presentation_id: str,
    client_id: str = Query(default=""),
    user_id: str = Query(default="anonymous"),
    token: Optional[str] = Query(default=None),
):
    """
    WebSocket endpoint for real-time editor synchronization.

    Protocol:
        1. Client connects with client_id and user_id
        2. Server sends sync_init with current peers
        3. Client sends operations, presence updates, ping
        4. Server broadcasts to other clients in the room
    """
    if not client_id:
        client_id = f"client_{id(websocket)}"

    # Register with sync hub
    client = await _sync_hub.connect(
        websocket=websocket,
        presentation_id=presentation_id,
        client_id=client_id,
        user_id=user_id,
    )

    # Register presence
    _presence_manager.join(
        presentation_id=presentation_id,
        user_id=user_id,
        client_id=client_id,
    )

    # Track in session store
    _session_store.add_client(presentation_id, client_id)

    try:
        # Set up message handlers
        _sync_hub.on_message(SyncMessageType.OPERATION, _handle_operation)
        _sync_hub.on_message(SyncMessageType.PRESENCE, _handle_presence)
        _sync_hub.on_message(SyncMessageType.UNDO, _handle_undo)
        _sync_hub.on_message(SyncMessageType.REDO, _handle_redo)
        _sync_hub.on_message(SyncMessageType.STATE_REQUEST, _handle_state_request)

        # Run the client loop (blocks until disconnect)
        await _sync_hub.handle_client(client)

    except WebSocketDisconnect:
        logger.info("Sync client disconnected: %s", client_id)
    finally:
        # Cleanup presence
        _presence_manager.leave(presentation_id, client_id)
        _session_store.remove_client(presentation_id, client_id)


# ── WebSocket message handlers ───────────────────────────────────


async def _handle_operation(client: SyncClient, message: SyncMessage) -> None:
    """Handle an incoming DSL operation from a client."""
    data = message.data
    op_type_str = data.get("operation_type", "")
    target_id = data.get("target_id")
    path = data.get("path")
    before_state = data.get("before_state")
    after_state = data.get("after_state")

    try:
        op_type = OperationType(op_type_str)
    except ValueError:
        await client.send(SyncMessage(
            msg_type=SyncMessageType.ERROR,
            data={"error": f"Unknown operation type: {op_type_str}"},
        ))
        return

    # Record in operation bus
    op = _operation_bus.record(
        op_type=op_type,
        presentation_id=client.presentation_id,
        target_id=target_id,
        path=path,
        before_state=before_state,
        after_state=after_state,
        client_id=client.client_id,
        user_id=client.user_id,
    )

    # Merge into CRDT document if available
    crdt_doc = _crdt_documents.get(client.presentation_id)
    if crdt_doc and after_state and path:
        crdt_doc.merge_update(
            client_id=client.client_id,
            update={path: after_state},
        )

    # Broadcast to other clients
    await _sync_hub.broadcast(
        client.presentation_id,
        SyncMessage(
            msg_type=SyncMessageType.OPERATION_BROADCAST,
            client_id=client.client_id,
            data={
                "operation": op.to_dict(),
                "revision": crdt_doc.revision if crdt_doc else 0,
            },
        ),
        exclude={client.client_id},
    )


async def _handle_presence(client: SyncClient, message: SyncMessage) -> None:
    """Handle a presence/cursor update."""
    data = message.data
    cursor = CursorPosition(
        slide_id=data.get("slide_id", ""),
        element_id=data.get("element_id"),
        x=data.get("x", 0.0),
        y=data.get("y", 0.0),
        selection_start=data.get("selection_start"),
        selection_end=data.get("selection_end"),
    )
    _presence_manager.update_cursor(
        client.presentation_id, client.client_id, cursor
    )

    # Broadcast to peers
    presence = _presence_manager.get_presence(
        client.presentation_id, client.client_id
    )
    if presence:
        await _sync_hub.broadcast(
            client.presentation_id,
            SyncMessage(
                msg_type=SyncMessageType.PRESENCE,
                client_id=client.client_id,
                data=presence.to_dict(),
            ),
            exclude={client.client_id},
        )


async def _handle_undo(client: SyncClient, message: SyncMessage) -> None:
    """Handle undo request."""
    op = _operation_bus.undo(client.presentation_id)
    if op:
        await client.send(SyncMessage(
            msg_type=SyncMessageType.UNDO_RESULT,
            data={
                "success": True,
                "operation": op.to_dict(),
                "can_undo": _operation_bus.can_undo(client.presentation_id),
                "can_redo": _operation_bus.can_redo(client.presentation_id),
            },
        ))
        # Broadcast undo to peers
        await _sync_hub.broadcast(
            client.presentation_id,
            SyncMessage(
                msg_type=SyncMessageType.UNDO_RESULT,
                client_id=client.client_id,
                data={"operation": op.to_dict()},
            ),
            exclude={client.client_id},
        )
    else:
        await client.send(SyncMessage(
            msg_type=SyncMessageType.UNDO_RESULT,
            data={"success": False, "error": "Nothing to undo"},
        ))


async def _handle_redo(client: SyncClient, message: SyncMessage) -> None:
    """Handle redo request."""
    op = _operation_bus.redo(client.presentation_id)
    if op:
        await client.send(SyncMessage(
            msg_type=SyncMessageType.REDO_RESULT,
            data={
                "success": True,
                "operation": op.to_dict(),
                "can_undo": _operation_bus.can_undo(client.presentation_id),
                "can_redo": _operation_bus.can_redo(client.presentation_id),
            },
        ))
        await _sync_hub.broadcast(
            client.presentation_id,
            SyncMessage(
                msg_type=SyncMessageType.REDO_RESULT,
                client_id=client.client_id,
                data={"operation": op.to_dict()},
            ),
            exclude={client.client_id},
        )
    else:
        await client.send(SyncMessage(
            msg_type=SyncMessageType.REDO_RESULT,
            data={"success": False, "error": "Nothing to redo"},
        ))


async def _handle_state_request(client: SyncClient, message: SyncMessage) -> None:
    """Handle a full-state sync request from a client."""
    crdt_doc = _crdt_documents.get(client.presentation_id)
    if crdt_doc:
        await client.send(SyncMessage(
            msg_type=SyncMessageType.STATE_RESPONSE,
            data=crdt_doc.get_state(),
        ))
    else:
        await client.send(SyncMessage(
            msg_type=SyncMessageType.STATE_RESPONSE,
            data={"error": "No CRDT document for this presentation"},
        ))


# ═══════════════════════════════════════════════════════════════════
# REST ENDPOINTS -- Sync State
# ═══════════════════════════════════════════════════════════════════


@router.get("/{presentation_id}/state", response_model=SyncResponse)
async def get_sync_state(presentation_id: str):
    """Get current sync state for a presentation."""
    crdt_doc = _crdt_documents.get(presentation_id)
    if not crdt_doc:
        return SyncResponse(
            success=True,
            message="No CRDT document active",
            data={"revision": 0, "state": "none"},
        )
    return SyncResponse(
        success=True,
        message="Sync state retrieved",
        data={
            "revision": crdt_doc.revision,
            "checksum": crdt_doc.checksum,
            "state": crdt_doc.state.value,
            "vector_clock": crdt_doc.vector_clock,
            "slide_count": len(crdt_doc.dsl.slides),
        },
    )


@router.post("/{presentation_id}/merge", response_model=SyncResponse)
async def merge_update(presentation_id: str, req: MergeRequest):
    """Apply a field-level update via CRDT merge."""
    crdt_doc = _crdt_documents.get(presentation_id)
    if not crdt_doc:
        raise HTTPException(status_code=404, detail="No CRDT document for this presentation")

    result = crdt_doc.merge_update(
        client_id=req.client_id,
        update=req.update,
        client_clock=req.client_clock,
    )
    return SyncResponse(
        success=result.success,
        message=f"Merged {result.fields_merged} fields, {result.conflict_count} conflicts",
        data=result.to_dict(),
    )


@router.get("/{presentation_id}/conflicts", response_model=SyncResponse)
async def get_conflicts(presentation_id: str, limit: int = 50):
    """Get conflict log for a presentation."""
    crdt_doc = _crdt_documents.get(presentation_id)
    if not crdt_doc:
        return SyncResponse(success=True, data={"conflicts": []})
    return SyncResponse(
        success=True,
        message=f"{crdt_doc.conflict_count} total conflicts",
        data={"conflicts": crdt_doc.get_conflict_log(limit)},
    )


# ═══════════════════════════════════════════════════════════════════
# REST ENDPOINTS -- Undo / Redo
# ═══════════════════════════════════════════════════════════════════


@router.post("/{presentation_id}/undo", response_model=UndoRedoResponse)
async def undo_operation(presentation_id: str):
    """Undo the last operation."""
    op = _operation_bus.undo(presentation_id)
    if not op:
        return UndoRedoResponse(
            success=False,
            can_undo=False,
            can_redo=_operation_bus.can_redo(presentation_id),
        )
    return UndoRedoResponse(
        success=True,
        operation_id=op.id,
        operation_type=op.type.value,
        state=op.before_state if isinstance(op.before_state, dict) else None,
        can_undo=_operation_bus.can_undo(presentation_id),
        can_redo=_operation_bus.can_redo(presentation_id),
    )


@router.post("/{presentation_id}/redo", response_model=UndoRedoResponse)
async def redo_operation(presentation_id: str):
    """Redo the last undone operation."""
    op = _operation_bus.redo(presentation_id)
    if not op:
        return UndoRedoResponse(
            success=False,
            can_undo=_operation_bus.can_undo(presentation_id),
            can_redo=False,
        )
    return UndoRedoResponse(
        success=True,
        operation_id=op.id,
        operation_type=op.type.value,
        state=op.after_state if isinstance(op.after_state, dict) else None,
        can_undo=_operation_bus.can_undo(presentation_id),
        can_redo=_operation_bus.can_redo(presentation_id),
    )


@router.get("/{presentation_id}/undo-history", response_model=SyncResponse)
async def get_undo_history(presentation_id: str):
    """Get undo stack summary for UI display."""
    history = _operation_bus.get_undo_history(presentation_id)
    return SyncResponse(
        success=True,
        message=f"{len(history)} operations in undo stack",
        data={
            "history": history,
            "can_undo": _operation_bus.can_undo(presentation_id),
            "can_redo": _operation_bus.can_redo(presentation_id),
        },
    )


# ═══════════════════════════════════════════════════════════════════
# REST ENDPOINTS -- Presence
# ═══════════════════════════════════════════════════════════════════


@router.get("/{presentation_id}/presence", response_model=SyncResponse)
async def get_presence(presentation_id: str):
    """Get all present users for a presentation."""
    peers = _presence_manager.get_peer_dicts(presentation_id)
    return SyncResponse(
        success=True,
        message=f"{len(peers)} users present",
        data={"users": peers},
    )


@router.post("/{presentation_id}/presence/cursor", response_model=SyncResponse)
async def update_cursor(presentation_id: str, req: CursorUpdateRequest):
    """Update cursor position via REST (alternative to WebSocket)."""
    cursor = CursorPosition(
        slide_id=req.slide_id,
        element_id=req.element_id,
        x=req.x,
        y=req.y,
        selection_start=req.selection_start,
        selection_end=req.selection_end,
    )
    ok = _presence_manager.update_cursor(presentation_id, req.client_id, cursor)
    if not ok:
        raise HTTPException(status_code=404, detail="Client not found in presence")
    return SyncResponse(success=True, message="Cursor updated")


# ═══════════════════════════════════════════════════════════════════
# REST ENDPOINTS -- Session Store
# ═══════════════════════════════════════════════════════════════════


@router.get("/sessions/list", response_model=SyncResponse)
async def list_sessions(status: Optional[str] = None):
    """List all editor sessions."""
    filter_status = None
    if status:
        try:
            filter_status = SessionStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    sessions = _session_store.list_sessions(status=filter_status)
    return SyncResponse(
        success=True,
        message=f"{len(sessions)} sessions",
        data={"sessions": [s.to_dict() for s in sessions]},
    )


@router.get("/sessions/{presentation_id}/info", response_model=SyncResponse)
async def get_session_info(presentation_id: str):
    """Get session info."""
    record = _session_store.get(presentation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Session not found")
    return SyncResponse(
        success=True,
        message="Session info",
        data=record.to_dict(),
    )


# ═══════════════════════════════════════════════════════════════════
# REST ENDPOINTS -- Operation Log & Bus Stats
# ═══════════════════════════════════════════════════════════════════


@router.get("/{presentation_id}/operations", response_model=SyncResponse)
async def get_operations(presentation_id: str, limit: int = 50):
    """Get recent operations for a presentation."""
    ops = _operation_bus.get_operations(presentation_id=presentation_id, limit=limit)
    return SyncResponse(
        success=True,
        message=f"{len(ops)} operations",
        data={"operations": [op.to_dict() for op in ops]},
    )


@router.get("/stats/bus", response_model=SyncResponse)
async def get_bus_stats():
    """Get operation bus statistics."""
    return SyncResponse(
        success=True,
        message="Bus stats",
        data=_operation_bus.get_stats(),
    )


@router.get("/stats/hub", response_model=SyncResponse)
async def get_hub_stats():
    """Get sync hub statistics."""
    return SyncResponse(
        success=True,
        message="Hub stats",
        data=_sync_hub.get_stats(),
    )


@router.get("/stats/presence", response_model=SyncResponse)
async def get_presence_stats():
    """Get presence manager statistics."""
    return SyncResponse(
        success=True,
        message="Presence stats",
        data=_presence_manager.get_stats(),
    )


@router.get("/stats/sessions", response_model=SyncResponse)
async def get_session_stats():
    """Get session store statistics."""
    return SyncResponse(
        success=True,
        message="Session stats",
        data=_session_store.get_stats(),
    )
