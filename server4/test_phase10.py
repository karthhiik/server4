#!/usr/bin/env python3
"""
Phase 10 Tests -- State Synchronization.

100 tests covering all 5 modules + sync routes + integration:
    Tests  1-20:  OperationBus (recording, undo/redo, vector clocks, batches, subscribers)
    Tests 21-40:  CRDTDocument (merge, LWW, conflict resolution, slide add/remove, state)
    Tests 41-60:  SyncWebSocket (SyncHub, SyncClient, SyncMessage, rooms, broadcast)
    Tests 61-75:  SessionStore (create, get, close, persist, cleanup, stats)
    Tests 76-90:  PresenceManager (join, leave, cursor, idle, queries)
    Tests 91-100: SyncRoutes + Integration (imports, singletons, schema validation)

Run:
    cd server4
    python test_phase10.py
"""

import sys
import os
import time
import json
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name: str):
        self.passed += 1
        print(f"  [PASS] {name}")

    def fail(self, name: str, reason: str):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  [FAIL] {name}: {reason}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Phase 10 Tests: {self.passed}/{total} passed")
        if self.errors:
            print("\nFailures:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0


results = TestResult()


# ── Helpers ──────────────────────────────────────────────────────

def _make_dsl(slide_count=3):
    """Create a minimal PresentationDSL for testing."""
    from app.models.dsl_v2 import PresentationDSL

    slides = []
    for i in range(slide_count):
        slides.append({
            "index": i,
            "id": f"slide_{i}",
            "type": "custom",
            "layout": "center-focus",
            "content": {"title": f"Slide {i}", "body": f"Body {i}"},
            "style": {},
        })

    dsl_data = {
        "version": "2.0",
        "presentation": {
            "id": "test-pres-001",
            "title": "Test Presentation",
            "subtitle": "Phase 10 Testing",
        },
        "slides": slides,
    }
    return PresentationDSL(**dsl_data)


# ═══════════════════════════════════════════════════════════════════
# 1-20: OperationBus
# ═══════════════════════════════════════════════════════════════════

print("\n--- OperationBus Tests (1-20) ---")

try:
    from app.services.state_sync.operation_bus import (
        OperationBus,
        OperationType,
        DSLOperation,
        OperationBatch,
        UndoRedoStack,
    )
    results.ok("1. OperationBus: module imports")
except Exception as e:
    results.fail("1. OperationBus: module imports", str(e))

try:
    assert issubclass(OperationType, str)
    assert OperationType.SLIDE_ADD == "slide_add"
    assert OperationType.SLIDE_REMOVE == "slide_remove"
    assert OperationType.ELEMENT_ADD == "element_add"
    assert OperationType.ELEMENT_UPDATE == "element_update"
    assert OperationType.THEME_UPDATE == "theme_update"
    assert OperationType.BATCH == "batch"
    assert OperationType.SNAPSHOT_CREATE == "snapshot_create"
    assert OperationType.ROLLBACK == "rollback"
    results.ok("2. OperationType: enum values correct")
except Exception as e:
    results.fail("2. OperationType: enum values correct", str(e))

try:
    op = DSLOperation(
        op_type=OperationType.SLIDE_ADD,
        presentation_id="pres-1",
        client_id="client_a",
        user_id="user_1",
        target_id="slide_5",
        path="slides.5",
        before_state=None,
        after_state={"type": "custom"},
        metadata={"source": "test"},
        vector_clock={"client_a": 1},
    )
    assert op.type == OperationType.SLIDE_ADD
    assert op.presentation_id == "pres-1"
    assert op.client_id == "client_a"
    assert op.target_id == "slide_5"
    assert op.after_state == {"type": "custom"}
    assert op.id.startswith("op_")
    results.ok("3. DSLOperation: constructor and fields")
except Exception as e:
    results.fail("3. DSLOperation: constructor and fields", str(e))

try:
    d = op.to_dict()
    assert d["type"] == "slide_add"
    assert d["presentation_id"] == "pres-1"
    assert d["target_id"] == "slide_5"
    assert "timestamp" in d
    op2 = DSLOperation.from_dict(d)
    assert op2.type == OperationType.SLIDE_ADD
    assert op2.client_id == "client_a"
    results.ok("4. DSLOperation: serialize / deserialize")
except Exception as e:
    results.fail("4. DSLOperation: serialize / deserialize", str(e))

try:
    op_undoable = DSLOperation(
        op_type=OperationType.SLIDE_ADD,
        presentation_id="p1",
        before_state={"old": True},
        after_state={"new": True},
    )
    assert op_undoable.is_undoable is True
    op_snap = DSLOperation(
        op_type=OperationType.SNAPSHOT_CREATE,
        presentation_id="p1",
    )
    assert op_snap.is_undoable is False
    results.ok("5. DSLOperation: is_undoable property")
except Exception as e:
    results.fail("5. DSLOperation: is_undoable property", str(e))

try:
    batch = OperationBatch(description="test batch")
    assert batch.size == 0
    batch.add(op_undoable)
    assert batch.size == 1
    bd = batch.to_dict()
    assert bd["description"] == "test batch"
    assert len(bd["operations"]) == 1
    results.ok("6. OperationBatch: create and add operations")
except Exception as e:
    results.fail("6. OperationBatch: create and add operations", str(e))

try:
    stack = UndoRedoStack()
    assert stack.can_undo() is False
    assert stack.can_redo() is False
    stack.push(op_undoable)
    assert stack.undo_count == 1
    assert stack.can_undo() is True
    results.ok("7. UndoRedoStack: push and can_undo")
except Exception as e:
    results.fail("7. UndoRedoStack: push and can_undo", str(e))

try:
    stack2 = UndoRedoStack()
    stack2.push(op_undoable)
    undone = stack2.undo()
    assert undone is not None
    assert undone.undone is True
    assert stack2.can_undo() is False
    assert stack2.can_redo() is True
    results.ok("8. UndoRedoStack: undo operation")
except Exception as e:
    results.fail("8. UndoRedoStack: undo operation", str(e))

try:
    redone = stack2.redo()
    assert redone is not None
    assert redone.undone is False
    assert stack2.can_undo() is True
    assert stack2.can_redo() is False
    results.ok("9. UndoRedoStack: redo operation")
except Exception as e:
    results.fail("9. UndoRedoStack: redo operation", str(e))

try:
    stack3 = UndoRedoStack()
    for i in range(5):
        o = DSLOperation(
            op_type=OperationType.ELEMENT_UPDATE,
            presentation_id="p1",
            before_state={"v": i},
            after_state={"v": i + 1},
        )
        stack3.push(o)
    assert stack3.undo_count == 5
    hist = stack3.history
    assert len(hist) == 5
    assert hist[0]["type"] == "element_update"
    results.ok("10. UndoRedoStack: history property")
except Exception as e:
    results.fail("10. UndoRedoStack: history property", str(e))

try:
    bus = OperationBus()
    recorded = bus.record(
        op_type=OperationType.SLIDE_ADD,
        presentation_id="pres-bus-1",
        target_id="slide_new",
        after_state={"type": "custom"},
        client_id="c1",
        user_id="u1",
    )
    assert isinstance(recorded, DSLOperation)
    assert recorded.type == OperationType.SLIDE_ADD
    assert recorded.presentation_id == "pres-bus-1"
    results.ok("11. OperationBus: record operation")
except Exception as e:
    results.fail("11. OperationBus: record operation", str(e))

try:
    vc = bus.get_vector_clock("pres-bus-1")
    assert "c1" in vc
    assert vc["c1"] == 1
    results.ok("12. OperationBus: vector clock incremented")
except Exception as e:
    results.fail("12. OperationBus: vector clock incremented", str(e))

try:
    bus2 = OperationBus()
    bus2.record(OperationType.SLIDE_ADD, "p2", before_state={"old": 1}, after_state={"new": 2})
    bus2.record(OperationType.SLIDE_REMOVE, "p2", before_state={"old": 2}, after_state={"new": 3})
    assert bus2.can_undo("p2") is True
    undone_op = bus2.undo("p2")
    assert undone_op is not None
    assert undone_op.type == OperationType.SLIDE_REMOVE
    assert bus2.can_redo("p2") is True
    results.ok("13. OperationBus: undo returns correct operation")
except Exception as e:
    results.fail("13. OperationBus: undo returns correct operation", str(e))

try:
    redone_op = bus2.redo("p2")
    assert redone_op is not None
    assert redone_op.type == OperationType.SLIDE_REMOVE
    results.ok("14. OperationBus: redo returns correct operation")
except Exception as e:
    results.fail("14. OperationBus: redo returns correct operation", str(e))

try:
    received = []
    def _on_op(op):
        received.append(op)
    bus3 = OperationBus()
    bus3.subscribe(_on_op)
    bus3.record(OperationType.ELEMENT_ADD, "p3", target_id="elem_1")
    assert len(received) == 1
    assert received[0].target_id == "elem_1"
    assert bus3.subscriber_count >= 1
    results.ok("15. OperationBus: subscriber notification")
except Exception as e:
    results.fail("15. OperationBus: subscriber notification", str(e))

try:
    bus3.unsubscribe(_on_op)
    bus3.record(OperationType.ELEMENT_REMOVE, "p3", target_id="elem_2")
    assert len(received) == 1  # no new notification
    results.ok("16. OperationBus: unsubscribe")
except Exception as e:
    results.fail("16. OperationBus: unsubscribe", str(e))

try:
    bus4 = OperationBus()
    op_a = DSLOperation(OperationType.SLIDE_ADD, "p4", before_state={}, after_state={"a": 1})
    op_b = DSLOperation(OperationType.SLIDE_ADD, "p4", before_state={}, after_state={"b": 2})
    batch_result = bus4.record_batch([op_a, op_b], description="test batch")
    assert isinstance(batch_result, OperationBatch)
    assert batch_result.size == 2
    results.ok("17. OperationBus: record_batch")
except Exception as e:
    results.fail("17. OperationBus: record_batch", str(e))

try:
    bus5 = OperationBus()
    for i in range(5):
        bus5.record(OperationType.ELEMENT_UPDATE, "p5", target_id=f"e{i}")
    ops = bus5.get_operations(presentation_id="p5", limit=3)
    assert len(ops) == 3
    results.ok("18. OperationBus: get_operations with limit")
except Exception as e:
    results.fail("18. OperationBus: get_operations with limit", str(e))

try:
    bus6 = OperationBus()
    bus6.record(OperationType.SLIDE_ADD, "p6-clear", before_state={"x": 1}, after_state={"x": 2})
    bus6.record(OperationType.SLIDE_REMOVE, "p6-clear", before_state={"x": 2}, after_state={"x": 3})
    removed = bus6.clear_presentation("p6-clear")
    assert removed >= 2
    assert bus6.can_undo("p6-clear") is False
    results.ok("19. OperationBus: clear_presentation")
except Exception as e:
    results.fail("19. OperationBus: clear_presentation", str(e))

try:
    stats = bus5.get_stats()
    assert "total_operations" in stats
    assert "presentations_tracked" in stats
    assert "subscriber_count" in stats
    assert "stacks" in stats
    results.ok("20. OperationBus: get_stats")
except Exception as e:
    results.fail("20. OperationBus: get_stats", str(e))

# ═══════════════════════════════════════════════════════════════════
# 21-40: CRDTDocument
# ═══════════════════════════════════════════════════════════════════

print("\n--- CRDTDocument Tests (21-40) ---")

try:
    from app.services.state_sync.crdt_document import (
        CRDTDocument,
        DocumentState,
        MergeResult,
        ConflictResolution,
        ConflictRecord,
        FieldTimestamp,
    )
    results.ok("21. CRDTDocument: module imports")
except Exception as e:
    results.fail("21. CRDTDocument: module imports", str(e))

try:
    assert DocumentState.CLEAN == "clean"
    assert DocumentState.DIRTY == "dirty"
    assert DocumentState.MERGING == "merging"
    assert DocumentState.LOCKED == "locked"
    results.ok("22. DocumentState: enum values")
except Exception as e:
    results.fail("22. DocumentState: enum values", str(e))

try:
    assert ConflictResolution.LAST_WRITER_WINS == "last_writer_wins"
    assert ConflictResolution.ADD_WINS == "add_wins"
    assert ConflictResolution.STRUCTURAL_MERGE == "structural_merge"
    assert ConflictResolution.SERVER_AUTHORITY == "server_authority"
    results.ok("23. ConflictResolution: enum values")
except Exception as e:
    results.fail("23. ConflictResolution: enum values", str(e))

try:
    dsl = _make_dsl(3)
    doc = CRDTDocument("test-pres-001", dsl)
    assert doc.presentation_id == "test-pres-001"
    assert doc.state == DocumentState.CLEAN
    assert doc.revision == 0
    assert len(doc.checksum) == 16
    assert len(doc.active_slide_ids) == 3
    results.ok("24. CRDTDocument: constructor and properties")
except Exception as e:
    results.fail("24. CRDTDocument: constructor and properties", str(e))

try:
    result = doc.merge_update("client_a", {})
    assert isinstance(result, MergeResult)
    assert result.success is True
    assert result.fields_merged == 0
    results.ok("25. CRDTDocument: merge empty update (no-op)")
except Exception as e:
    results.fail("25. CRDTDocument: merge empty update (no-op)", str(e))

try:
    result = doc.merge_update("client_a", {
        "presentation.title": "Updated Title"
    })
    assert result.success is True
    assert result.fields_merged == 1
    assert doc.revision == 1
    assert len(result.new_checksum) == 16
    results.ok("26. CRDTDocument: merge single field update")
except Exception as e:
    results.fail("26. CRDTDocument: merge single field update", str(e))

try:
    vc = doc.vector_clock
    assert "client_a" in vc
    assert vc["client_a"] >= 1
    results.ok("27. CRDTDocument: vector clock updated after merge")
except Exception as e:
    results.fail("27. CRDTDocument: vector clock updated after merge", str(e))

try:
    state = doc.get_state()
    assert "presentation_id" in state
    assert "revision" in state
    assert "checksum" in state
    assert "vector_clock" in state
    assert "state" in state
    assert "dsl" in state
    results.ok("28. CRDTDocument: get_state returns full state dict")
except Exception as e:
    results.fail("28. CRDTDocument: get_state returns full state dict", str(e))

try:
    r = MergeResult(success=True, fields_merged=5)
    d = r.to_dict()
    assert d["success"] is True
    assert d["fields_merged"] == 5
    assert d["had_conflicts"] is False
    assert d["conflicts"] == []
    results.ok("29. MergeResult: to_dict")
except Exception as e:
    results.fail("29. MergeResult: to_dict", str(e))

try:
    cr = ConflictRecord(
        field_path="slides.slide_0.content.title",
        client_a="c1",
        client_b="c2",
        value_a="Old",
        value_b="New",
        resolved_value="New",
        resolution=ConflictResolution.LAST_WRITER_WINS,
    )
    d = cr.to_dict()
    assert d["field_path"] == "slides.slide_0.content.title"
    assert d["resolution"] == "last_writer_wins"
    assert d["client_a"] == "c1"
    results.ok("30. ConflictRecord: creation and to_dict")
except Exception as e:
    results.fail("30. ConflictRecord: creation and to_dict", str(e))

try:
    ft = FieldTimestamp("slides.x.title", "c1", clock_value=3)
    assert ft.path == "slides.x.title"
    assert ft.client_id == "c1"
    assert ft.clock_value == 3
    results.ok("31. FieldTimestamp: creation")
except Exception as e:
    results.fail("31. FieldTimestamp: creation", str(e))

try:
    doc2 = CRDTDocument("pres-conflict", _make_dsl(2))
    # Client A edits title
    doc2.merge_update("client_a", {"presentation.title": "A's Title"})
    # Client B edits same field concurrently
    r = doc2.merge_update("client_b", {"presentation.title": "B's Title"})
    assert r.success is True
    # Should detect conflict (LWW resolves it)
    assert r.had_conflicts is True
    assert r.conflicts[0].resolution == ConflictResolution.LAST_WRITER_WINS
    results.ok("32. CRDTDocument: LWW conflict detection")
except Exception as e:
    results.fail("32. CRDTDocument: LWW conflict detection", str(e))

try:
    doc3 = CRDTDocument("pres-add", _make_dsl(1))
    r = doc3.merge_update("client_a", {
        "slides_add": [{"index": 1, "id": "slide_new_1", "type": "custom", "layout": "center-focus", "content": {"title": "Added"}, "style": {}}]
    })
    assert r.success is True
    assert r.fields_merged >= 1
    assert "slide_new_1" in doc3.active_slide_ids
    assert len(doc3.dsl.slides) == 2
    results.ok("33. CRDTDocument: slide add (add-wins)")
except Exception as e:
    results.fail("33. CRDTDocument: slide add (add-wins)", str(e))

try:
    doc4 = CRDTDocument("pres-remove", _make_dsl(3))
    r = doc4.merge_update("client_a", {"slides_remove": ["slide_1"]})
    assert r.success is True
    assert "slide_1" not in doc4.active_slide_ids
    assert len(doc4.dsl.slides) == 2
    results.ok("34. CRDTDocument: slide remove")
except Exception as e:
    results.fail("34. CRDTDocument: slide remove", str(e))

try:
    delta = doc.get_delta_since(0)
    assert "from_revision" in delta
    assert "to_revision" in delta
    assert "changes" in delta
    assert "checksum" in delta
    results.ok("35. CRDTDocument: get_delta_since")
except Exception as e:
    results.fail("35. CRDTDocument: get_delta_since", str(e))

try:
    log = doc2.get_conflict_log(limit=10)
    assert isinstance(log, list)
    assert len(log) >= 1
    assert "field_path" in log[0]
    results.ok("36. CRDTDocument: get_conflict_log")
except Exception as e:
    results.fail("36. CRDTDocument: get_conflict_log", str(e))

try:
    doc_lock = CRDTDocument("pres-lock", _make_dsl(1))
    assert doc_lock.lock() is True
    assert doc_lock.state == DocumentState.LOCKED
    assert doc_lock.lock() is False  # already locked
    doc_lock.unlock()
    assert doc_lock.state == DocumentState.CLEAN
    results.ok("37. CRDTDocument: lock / unlock")
except Exception as e:
    results.fail("37. CRDTDocument: lock / unlock", str(e))

try:
    doc_replace = CRDTDocument("pres-replace", _make_dsl(2))
    new_dsl = _make_dsl(5)
    doc_replace.replace_dsl(new_dsl)
    assert len(doc_replace.dsl.slides) == 5
    assert doc_replace.state == DocumentState.CLEAN
    assert doc_replace.revision == 1
    results.ok("38. CRDTDocument: replace_dsl (rollback)")
except Exception as e:
    results.fail("38. CRDTDocument: replace_dsl (rollback)", str(e))

try:
    doc_mark = CRDTDocument("pres-mark", _make_dsl(1))
    doc_mark.merge_update("c1", {"presentation.title": "Dirty"})
    assert doc_mark.state == DocumentState.DIRTY
    doc_mark.mark_clean()
    assert doc_mark.state == DocumentState.CLEAN
    results.ok("39. CRDTDocument: mark_clean")
except Exception as e:
    results.fail("39. CRDTDocument: mark_clean", str(e))

try:
    doc_dup = CRDTDocument("pres-dup-add", _make_dsl(2))
    # Add slide with existing ID → should get new ID
    r = doc_dup.merge_update("c1", {
        "slides_add": [{"index": 10, "id": "slide_0", "type": "custom", "layout": "center-focus", "content": {"title": "Dup"}, "style": {}}]
    })
    assert r.success is True
    assert len(doc_dup.dsl.slides) == 3
    # The added slide should NOT have id "slide_0" (deduped)
    slide_ids = [s.id for s in doc_dup.dsl.slides]
    assert slide_ids.count("slide_0") == 1  # original only
    results.ok("40. CRDTDocument: slide add dedup on existing ID")
except Exception as e:
    results.fail("40. CRDTDocument: slide add dedup on existing ID", str(e))

# ═══════════════════════════════════════════════════════════════════
# 41-60: SyncWebSocket
# ═══════════════════════════════════════════════════════════════════

print("\n--- SyncWebSocket Tests (41-60) ---")

try:
    from app.services.state_sync.sync_websocket import (
        SyncHub,
        SyncClient,
        SyncMessage,
        SyncMessageType,
    )
    results.ok("41. SyncWebSocket: module imports")
except Exception as e:
    results.fail("41. SyncWebSocket: module imports", str(e))

try:
    assert SyncMessageType.SYNC_INIT == "sync_init"
    assert SyncMessageType.OPERATION == "operation"
    assert SyncMessageType.OPERATION_BROADCAST == "operation_broadcast"
    assert SyncMessageType.PRESENCE == "presence"
    assert SyncMessageType.CONFLICT == "conflict"
    assert SyncMessageType.UNDO == "undo"
    assert SyncMessageType.REDO == "redo"
    assert SyncMessageType.PING == "ping"
    assert SyncMessageType.PONG == "pong"
    assert SyncMessageType.ERROR == "error"
    assert SyncMessageType.CLIENT_JOINED == "client_joined"
    assert SyncMessageType.CLIENT_LEFT == "client_left"
    results.ok("42. SyncMessageType: all enum values present")
except Exception as e:
    results.fail("42. SyncMessageType: all enum values present", str(e))

try:
    msg = SyncMessage(
        msg_type=SyncMessageType.OPERATION,
        client_id="c1",
        data={"op": "test"},
    )
    assert msg.type == SyncMessageType.OPERATION
    assert msg.client_id == "c1"
    assert msg.data == {"op": "test"}
    assert msg.message_id.startswith("msg_")
    results.ok("43. SyncMessage: constructor and fields")
except Exception as e:
    results.fail("43. SyncMessage: constructor and fields", str(e))

try:
    j = msg.to_json()
    parsed = json.loads(j)
    assert parsed["type"] == "operation"
    assert parsed["client_id"] == "c1"
    assert parsed["data"] == {"op": "test"}
    results.ok("44. SyncMessage: to_json serialization")
except Exception as e:
    results.fail("44. SyncMessage: to_json serialization", str(e))

try:
    msg2 = SyncMessage.from_json(j)
    assert msg2.type == SyncMessageType.OPERATION
    assert msg2.client_id == "c1"
    assert msg2.data == {"op": "test"}
    results.ok("45. SyncMessage: from_json deserialization")
except Exception as e:
    results.fail("45. SyncMessage: from_json deserialization", str(e))

try:
    hub = SyncHub(heartbeat_interval=30.0)
    assert hub.total_connections == 0
    assert hub.total_rooms == 0
    results.ok("46. SyncHub: constructor (empty state)")
except Exception as e:
    results.fail("46. SyncHub: constructor (empty state)", str(e))

try:
    rooms = hub.get_active_rooms()
    assert isinstance(rooms, dict)
    assert len(rooms) == 0
    results.ok("47. SyncHub: get_active_rooms (empty)")
except Exception as e:
    results.fail("47. SyncHub: get_active_rooms (empty)", str(e))

try:
    clients = hub.get_room_clients("nonexistent")
    assert clients == []
    assert hub.get_room_count("nonexistent") == 0
    results.ok("48. SyncHub: get_room_clients for nonexistent room")
except Exception as e:
    results.fail("48. SyncHub: get_room_clients for nonexistent room", str(e))

try:
    assert hub.is_client_connected("nonexistent", "c1") is False
    results.ok("49. SyncHub: is_client_connected (not connected)")
except Exception as e:
    results.fail("49. SyncHub: is_client_connected (not connected)", str(e))

try:
    stats = hub.get_stats()
    assert "total_connections" in stats
    assert "total_rooms" in stats
    assert "rooms" in stats
    assert "handler_count" in stats
    results.ok("50. SyncHub: get_stats structure")
except Exception as e:
    results.fail("50. SyncHub: get_stats structure", str(e))

try:
    called = []
    async def _handler(client, msg):
        called.append(msg.type)
    hub.on_message(SyncMessageType.OPERATION, _handler)
    assert len(hub._message_handlers) >= 1
    results.ok("51. SyncHub: on_message handler registration")
except Exception as e:
    results.fail("51. SyncHub: on_message handler registration", str(e))

# SyncClient requires a real WebSocket, so test the data model parts
try:
    # Create a mock-like client to test to_dict
    class MockWS:
        async def send_text(self, data): pass
        async def receive_text(self): pass
        async def accept(self): pass
    mock_ws = MockWS()
    client = SyncClient(
        client_id="test-c1",
        user_id="test-u1",
        websocket=mock_ws,
        presentation_id="pres-1",
    )
    assert client.client_id == "test-c1"
    assert client.user_id == "test-u1"
    assert client.is_alive is True
    results.ok("52. SyncClient: constructor and fields")
except Exception as e:
    results.fail("52. SyncClient: constructor and fields", str(e))

try:
    d = client.to_dict()
    assert d["client_id"] == "test-c1"
    assert d["user_id"] == "test-u1"
    assert d["presentation_id"] == "pres-1"
    assert d["is_alive"] is True
    assert "connected_at" in d
    results.ok("53. SyncClient: to_dict")
except Exception as e:
    results.fail("53. SyncClient: to_dict", str(e))

try:
    async def test_send():
        msg = SyncMessage(msg_type=SyncMessageType.PONG)
        result = await client.send(msg)
        return result
    r = asyncio.get_event_loop().run_until_complete(test_send())
    assert r is True
    results.ok("54. SyncClient: send message (mock)")
except Exception as e:
    results.fail("54. SyncClient: send message (mock)", str(e))

try:
    async def test_send_json():
        result = await client.send_json({"test": True})
        return result
    r = asyncio.get_event_loop().run_until_complete(test_send_json())
    assert r is True
    results.ok("55. SyncClient: send_json (mock)")
except Exception as e:
    results.fail("55. SyncClient: send_json (mock)", str(e))

try:
    client.is_alive = False
    async def test_send_dead():
        return await client.send(SyncMessage(msg_type=SyncMessageType.PONG))
    r = asyncio.get_event_loop().run_until_complete(test_send_dead())
    assert r is False
    client.is_alive = True  # restore
    results.ok("56. SyncClient: send returns False when dead")
except Exception as e:
    results.fail("56. SyncClient: send returns False when dead", str(e))

try:
    msg_init = SyncMessage(msg_type=SyncMessageType.SYNC_INIT, data={"peers": []})
    j = msg_init.to_json()
    parsed = json.loads(j)
    assert parsed["type"] == "sync_init"
    assert parsed["data"]["peers"] == []
    results.ok("57. SyncMessage: SYNC_INIT message format")
except Exception as e:
    results.fail("57. SyncMessage: SYNC_INIT message format", str(e))

try:
    msg_err = SyncMessage(msg_type=SyncMessageType.ERROR, data={"error": "bad input"})
    assert msg_err.type == SyncMessageType.ERROR
    assert msg_err.data["error"] == "bad input"
    results.ok("58. SyncMessage: ERROR message construction")
except Exception as e:
    results.fail("58. SyncMessage: ERROR message construction", str(e))

try:
    assert SyncMessageType.STATE_REQUEST == "state_request"
    assert SyncMessageType.STATE_RESPONSE == "state_response"
    assert SyncMessageType.UNDO_RESULT == "undo_result"
    assert SyncMessageType.REDO_RESULT == "redo_result"
    results.ok("59. SyncMessageType: state and undo/redo types")
except Exception as e:
    results.fail("59. SyncMessageType: state and undo/redo types", str(e))

try:
    async def test_broadcast_empty():
        return await hub.broadcast("nonexistent-room", SyncMessage(msg_type=SyncMessageType.PING))
    sent = asyncio.get_event_loop().run_until_complete(test_broadcast_empty())
    assert sent == 0
    results.ok("60. SyncHub: broadcast to empty room returns 0")
except Exception as e:
    results.fail("60. SyncHub: broadcast to empty room returns 0", str(e))


# ═══════════════════════════════════════════════════════════════════
# 61-75: SessionStore
# ═══════════════════════════════════════════════════════════════════

print("\n--- SessionStore Tests (61-75) ---")

try:
    from app.services.state_sync.session_store import (
        SessionStore,
        SessionRecord,
        SessionStatus,
    )
    results.ok("61. SessionStore: module imports")
except Exception as e:
    results.fail("61. SessionStore: module imports", str(e))

try:
    assert SessionStatus.ACTIVE == "active"
    assert SessionStatus.PAUSED == "paused"
    assert SessionStatus.CLOSED == "closed"
    assert SessionStatus.EXPIRED == "expired"
    results.ok("62. SessionStatus: enum values")
except Exception as e:
    results.fail("62. SessionStatus: enum values", str(e))

try:
    rec = SessionRecord(presentation_id="pres-1", user_id="u1")
    assert rec.presentation_id == "pres-1"
    assert rec.user_id == "u1"
    assert rec.status == SessionStatus.ACTIVE
    assert rec.session_id.startswith("sess_")
    assert rec.slide_count == 0
    assert rec.revision == 0
    results.ok("63. SessionRecord: constructor and defaults")
except Exception as e:
    results.fail("63. SessionRecord: constructor and defaults", str(e))

try:
    d = rec.to_dict()
    assert d["presentation_id"] == "pres-1"
    assert d["status"] == "active"
    assert "created_at" in d
    assert "last_activity" in d
    results.ok("64. SessionRecord: to_dict")
except Exception as e:
    results.fail("64. SessionRecord: to_dict", str(e))

try:
    j = rec.to_json()
    rec2 = SessionRecord.from_json(j)
    assert rec2.presentation_id == "pres-1"
    assert rec2.user_id == "u1"
    assert rec2.session_id == rec.session_id
    results.ok("65. SessionRecord: to_json / from_json round-trip")
except Exception as e:
    results.fail("65. SessionRecord: to_json / from_json round-trip", str(e))

try:
    rec.touch()
    # touch just updates last_activity, shouldn't raise
    results.ok("66. SessionRecord: touch updates activity")
except Exception as e:
    results.fail("66. SessionRecord: touch updates activity", str(e))

try:
    store = SessionStore(ttl=3600)
    assert store.session_count == 0
    assert store.active_count == 0
    results.ok("67. SessionStore: constructor (empty)")
except Exception as e:
    results.fail("67. SessionStore: constructor (empty)", str(e))

try:
    created = store.create("pres-store-1", user_id="u1", slide_count=5)
    assert isinstance(created, SessionRecord)
    assert created.presentation_id == "pres-store-1"
    assert created.slide_count == 5
    assert store.session_count == 1
    results.ok("68. SessionStore: create session")
except Exception as e:
    results.fail("68. SessionStore: create session", str(e))

try:
    got = store.get("pres-store-1")
    assert got is not None
    assert got.presentation_id == "pres-store-1"
    assert store.exists("pres-store-1") is True
    assert store.exists("nonexistent") is False
    results.ok("69. SessionStore: get and exists")
except Exception as e:
    results.fail("69. SessionStore: get and exists", str(e))

try:
    assert store.touch("pres-store-1") is True
    assert store.touch("nonexistent") is False
    results.ok("70. SessionStore: touch session")
except Exception as e:
    results.fail("70. SessionStore: touch session", str(e))

try:
    assert store.update_revision("pres-store-1", 5) is True
    assert store.get("pres-store-1").revision == 5
    results.ok("71. SessionStore: update_revision")
except Exception as e:
    results.fail("71. SessionStore: update_revision", str(e))

try:
    store.add_client("pres-store-1", "client_a")
    store.add_client("pres-store-1", "client_b")
    rec = store.get("pres-store-1")
    assert "client_a" in rec.client_ids
    assert "client_b" in rec.client_ids
    store.remove_client("pres-store-1", "client_a")
    assert "client_a" not in store.get("pres-store-1").client_ids
    results.ok("72. SessionStore: add_client / remove_client")
except Exception as e:
    results.fail("72. SessionStore: add_client / remove_client", str(e))

try:
    closed = store.close("pres-store-1")
    assert closed is not None
    assert closed.status == SessionStatus.CLOSED
    assert store.session_count == 0
    results.ok("73. SessionStore: close session")
except Exception as e:
    results.fail("73. SessionStore: close session", str(e))

try:
    store2 = SessionStore()
    store2.create("p1", user_id="u1")
    store2.create("p2", user_id="u2")
    all_sessions = store2.list_sessions()
    assert len(all_sessions) == 2
    active = store2.list_active()
    assert len(active) == 2
    results.ok("74. SessionStore: list_sessions and list_active")
except Exception as e:
    results.fail("74. SessionStore: list_sessions and list_active", str(e))

try:
    stats = store2.get_stats()
    assert "total_sessions" in stats
    assert "active_sessions" in stats
    assert "by_status" in stats
    assert "redis_connected" in stats
    results.ok("75. SessionStore: get_stats")
except Exception as e:
    results.fail("75. SessionStore: get_stats", str(e))


# ═══════════════════════════════════════════════════════════════════
# 76-90: PresenceManager
# ═══════════════════════════════════════════════════════════════════

print("\n--- PresenceManager Tests (76-90) ---")

try:
    from app.services.state_sync.presence_manager import (
        PresenceManager,
        UserPresence,
        CursorPosition,
        PresenceEvent,
    )
    results.ok("76. PresenceManager: module imports")
except Exception as e:
    results.fail("76. PresenceManager: module imports", str(e))

try:
    assert PresenceEvent.JOINED == "joined"
    assert PresenceEvent.LEFT == "left"
    assert PresenceEvent.CURSOR_MOVED == "cursor_moved"
    assert PresenceEvent.IDLE == "idle"
    assert PresenceEvent.EDITING_STARTED == "editing_started"
    assert PresenceEvent.EDITING_STOPPED == "editing_stopped"
    results.ok("77. PresenceEvent: enum values")
except Exception as e:
    results.fail("77. PresenceEvent: enum values", str(e))

try:
    cursor = CursorPosition(
        slide_id="slide_0",
        element_id="elem_1",
        x=0.5,
        y=0.3,
        selection_start=10,
        selection_end=20,
    )
    assert cursor.slide_id == "slide_0"
    assert cursor.x == 0.5
    d = cursor.to_dict()
    assert d["slide_id"] == "slide_0"
    assert d["element_id"] == "elem_1"
    assert d["x"] == 0.5
    results.ok("78. CursorPosition: constructor and to_dict")
except Exception as e:
    results.fail("78. CursorPosition: constructor and to_dict", str(e))

try:
    c2 = CursorPosition.from_dict({"slide_id": "s1", "x": 0.2, "y": 0.4})
    assert c2.slide_id == "s1"
    assert c2.x == 0.2
    results.ok("79. CursorPosition: from_dict")
except Exception as e:
    results.fail("79. CursorPosition: from_dict", str(e))

try:
    up = UserPresence(
        user_id="u1",
        client_id="c1",
        presentation_id="pres-1",
        display_name="Alice",
        color_index=0,
    )
    assert up.user_id == "u1"
    assert up.display_name == "Alice"
    assert up.color == UserPresence.CURSOR_COLORS[0]
    assert up.is_editing is False
    assert up.is_idle is False
    results.ok("80. UserPresence: constructor and defaults")
except Exception as e:
    results.fail("80. UserPresence: constructor and defaults", str(e))

try:
    d = up.to_dict()
    assert d["user_id"] == "u1"
    assert d["client_id"] == "c1"
    assert d["display_name"] == "Alice"
    assert "color" in d
    assert "cursor" in d
    results.ok("81. UserPresence: to_dict")
except Exception as e:
    results.fail("81. UserPresence: to_dict", str(e))

try:
    up.update_cursor(CursorPosition(slide_id="slide_2", x=0.7))
    assert up.active_slide_id == "slide_2"
    assert up.cursor.slide_id == "slide_2"
    assert up.is_idle is False
    results.ok("82. UserPresence: update_cursor")
except Exception as e:
    results.fail("82. UserPresence: update_cursor", str(e))

try:
    up.mark_editing(True)
    assert up.is_editing is True
    up.mark_idle()
    assert up.is_idle is True
    up.mark_active()
    assert up.is_idle is False
    results.ok("83. UserPresence: mark_editing / idle / active")
except Exception as e:
    results.fail("83. UserPresence: mark_editing / idle / active", str(e))

try:
    pm = PresenceManager(idle_timeout=60.0)
    assert pm.total_users == 0
    assert pm.total_rooms == 0
    results.ok("84. PresenceManager: constructor (empty)")
except Exception as e:
    results.fail("84. PresenceManager: constructor (empty)", str(e))

try:
    p1 = pm.join("pres-pm-1", "u1", "c1", display_name="Alice")
    assert isinstance(p1, UserPresence)
    assert p1.display_name == "Alice"
    assert pm.total_users == 1
    assert pm.total_rooms == 1
    results.ok("85. PresenceManager: join")
except Exception as e:
    results.fail("85. PresenceManager: join", str(e))

try:
    pm.join("pres-pm-1", "u2", "c2", display_name="Bob")
    peers = pm.get_peers("pres-pm-1", exclude_client="c1")
    assert len(peers) == 1
    assert peers[0].display_name == "Bob"
    results.ok("86. PresenceManager: get_peers with exclude")
except Exception as e:
    results.fail("86. PresenceManager: get_peers with exclude", str(e))

try:
    ok = pm.update_cursor("pres-pm-1", "c1", CursorPosition(slide_id="slide_3"))
    assert ok is True
    p = pm.get_presence("pres-pm-1", "c1")
    assert p.active_slide_id == "slide_3"
    results.ok("87. PresenceManager: update_cursor")
except Exception as e:
    results.fail("87. PresenceManager: update_cursor", str(e))

try:
    ok = pm.set_editing("pres-pm-1", "c1", True)
    assert ok is True
    p = pm.get_presence("pres-pm-1", "c1")
    assert p.is_editing is True
    results.ok("88. PresenceManager: set_editing")
except Exception as e:
    results.fail("88. PresenceManager: set_editing", str(e))

try:
    on_slide = pm.get_users_on_slide("pres-pm-1", "slide_3")
    assert len(on_slide) == 1
    assert on_slide[0].client_id == "c1"
    results.ok("89. PresenceManager: get_users_on_slide")
except Exception as e:
    results.fail("89. PresenceManager: get_users_on_slide", str(e))

try:
    left = pm.leave("pres-pm-1", "c2")
    assert left is not None
    assert left.display_name == "Bob"
    assert pm.get_user_count("pres-pm-1") == 1
    stats = pm.get_stats()
    assert "total_users" in stats
    assert "total_rooms" in stats
    assert "rooms" in stats
    results.ok("90. PresenceManager: leave and get_stats")
except Exception as e:
    results.fail("90. PresenceManager: leave and get_stats", str(e))


# ═══════════════════════════════════════════════════════════════════
# 91-100: Sync Routes + Integration
# ═══════════════════════════════════════════════════════════════════

print("\n--- SyncRoutes + Integration Tests (91-100) ---")

try:
    from app.api.routes.sync_routes import (
        router as sync_router,
        SyncResponse,
        MergeRequest,
        UndoRedoResponse,
        CursorUpdateRequest,
        get_operation_bus,
        get_sync_hub,
        get_session_store,
        get_presence_manager,
        get_crdt_document,
        register_crdt_document,
        unregister_crdt_document,
    )
    results.ok("91. SyncRoutes: module imports (all exports)")
except Exception as e:
    results.fail("91. SyncRoutes: module imports (all exports)", str(e))

try:
    assert sync_router.prefix == "/api/v2/sync"
    assert "state-sync-v2" in sync_router.tags
    results.ok("92. SyncRoutes: router prefix and tags")
except Exception as e:
    results.fail("92. SyncRoutes: router prefix and tags", str(e))

try:
    bus = get_operation_bus()
    assert isinstance(bus, OperationBus)
    hub = get_sync_hub()
    assert isinstance(hub, SyncHub)
    store = get_session_store()
    assert isinstance(store, SessionStore)
    pm = get_presence_manager()
    assert isinstance(pm, PresenceManager)
    results.ok("93. SyncRoutes: singleton accessors return correct types")
except Exception as e:
    results.fail("93. SyncRoutes: singleton accessors return correct types", str(e))

try:
    # Register a CRDT doc and retrieve it
    dsl = _make_dsl(2)
    doc = CRDTDocument("pres-routes-test", dsl)
    register_crdt_document("pres-routes-test", doc)
    retrieved = get_crdt_document("pres-routes-test")
    assert retrieved is doc
    unregister_crdt_document("pres-routes-test")
    assert get_crdt_document("pres-routes-test") is None
    results.ok("94. SyncRoutes: register / unregister CRDT document")
except Exception as e:
    results.fail("94. SyncRoutes: register / unregister CRDT document", str(e))

try:
    resp = SyncResponse(success=True, message="ok", data={"key": "value"})
    d = resp.model_dump()
    assert d["success"] is True
    assert d["message"] == "ok"
    assert d["data"] == {"key": "value"}
    results.ok("95. SyncResponse: schema validation")
except Exception as e:
    results.fail("95. SyncResponse: schema validation", str(e))

try:
    merge_req = MergeRequest(
        client_id="c1",
        update={"presentation.title": "New"},
        client_clock={"c1": 1},
    )
    assert merge_req.client_id == "c1"
    assert merge_req.update["presentation.title"] == "New"
    results.ok("96. MergeRequest: schema validation")
except Exception as e:
    results.fail("96. MergeRequest: schema validation", str(e))

try:
    undo_resp = UndoRedoResponse(
        success=True,
        operation_id="op_123",
        operation_type="slide_add",
        can_undo=True,
        can_redo=False,
    )
    d = undo_resp.model_dump()
    assert d["success"] is True
    assert d["operation_id"] == "op_123"
    assert d["can_undo"] is True
    results.ok("97. UndoRedoResponse: schema validation")
except Exception as e:
    results.fail("97. UndoRedoResponse: schema validation", str(e))

try:
    cursor_req = CursorUpdateRequest(
        client_id="c1",
        slide_id="slide_0",
        x=0.5,
        y=0.3,
    )
    assert cursor_req.client_id == "c1"
    assert cursor_req.slide_id == "slide_0"
    results.ok("98. CursorUpdateRequest: schema validation")
except Exception as e:
    results.fail("98. CursorUpdateRequest: schema validation", str(e))

# Test the __init__.py re-exports
try:
    from app.services.state_sync import (
        OperationBus as OB,
        OperationType as OT,
        DSLOperation as DO,
        OperationBatch as OBatch,
        CRDTDocument as CD,
        DocumentState as DS,
        MergeResult as MR,
        ConflictResolution as CR,
        SyncHub as SH,
        SyncClient as SC,
        SyncMessage as SM,
        SyncMessageType as SMT,
        SessionStore as SS,
        SessionRecord as SR,
        SessionStatus as SSt,
        PresenceManager as PM,
        UserPresence as UP,
        CursorPosition as CP,
        PresenceEvent as PE,
    )
    assert OB is OperationBus
    assert CD is CRDTDocument
    assert SH is SyncHub
    assert SS is SessionStore
    assert PM is PresenceManager
    results.ok("99. __init__.py: all 19 re-exports accessible")
except Exception as e:
    results.fail("99. __init__.py: all 19 re-exports accessible", str(e))

# Integration: OperationBus + CRDTDocument + PresenceManager working together
try:
    int_bus = OperationBus()
    int_dsl = _make_dsl(3)
    int_doc = CRDTDocument("pres-integration", int_dsl)
    int_pm = PresenceManager()

    # User joins presence
    int_pm.join("pres-integration", "u1", "c1", display_name="Integrator")

    # Record operation
    int_op = int_bus.record(
        OperationType.SLIDE_UPDATE_CONTENT,
        "pres-integration",
        target_id="slide_0",
        path="slides.slide_0.content.title",
        before_state="Slide 0",
        after_state="Updated Slide 0",
        client_id="c1",
        user_id="u1",
    )

    # Merge into CRDT doc
    merge_r = int_doc.merge_update("c1", {
        "slides.slide_0.content.title": "Updated Slide 0"
    })

    # Update cursor
    int_pm.update_cursor("pres-integration", "c1", CursorPosition(slide_id="slide_0"))

    # Verify integration
    assert int_op.type == OperationType.SLIDE_UPDATE_CONTENT
    assert merge_r.success is True
    assert int_doc.revision >= 1
    assert int_pm.get_presence("pres-integration", "c1").active_slide_id == "slide_0"
    assert int_bus.can_undo("pres-integration") is True

    # Undo
    undone = int_bus.undo("pres-integration")
    assert undone.before_state == "Slide 0"

    results.ok("100. Integration: Bus + CRDT + Presence end-to-end")
except Exception as e:
    results.fail("100. Integration: Bus + CRDT + Presence end-to-end", str(e))


# ═══════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════

all_passed = results.summary()
sys.exit(0 if all_passed else 1)
