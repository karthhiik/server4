"""
CRDT Document -- Conflict-free replicated data type for PresentationDSL.

Implements an Operational Transform (OT) inspired conflict resolution layer
for concurrent edits. Instead of depending on external CRDT libraries
(pycrdt/yjs at runtime), this module implements a lightweight server-side
conflict resolution protocol:

1. Vector Clock ordering for causal consistency
2. Last-Writer-Wins (LWW) register for scalar fields
3. Add-Wins set semantics for slide/element collections
4. Structural merge for concurrent edits to different fields
5. Conflict detection and resolution with user-friendly reporting

This is the server-side authority. Frontend clients use Yjs for local
conflict-free editing; when they push updates to the server, this module
merges them into the authoritative document.
"""

import copy
import hashlib
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog

from app.models.dsl_v2 import PresentationDSL

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Document state and conflict types
# ---------------------------------------------------------------------------


class ConflictResolution(str, Enum):
    """How a conflict was resolved."""
    LAST_WRITER_WINS = "last_writer_wins"
    ADD_WINS = "add_wins"
    STRUCTURAL_MERGE = "structural_merge"
    SERVER_AUTHORITY = "server_authority"
    CLIENT_PRIORITY = "client_priority"


class ConflictRecord:
    """Record of a detected and resolved conflict."""

    __slots__ = (
        "id", "field_path", "client_a", "client_b",
        "value_a", "value_b", "resolved_value",
        "resolution", "timestamp",
    )

    def __init__(
        self,
        field_path: str,
        client_a: str,
        client_b: str,
        value_a: Any,
        value_b: Any,
        resolved_value: Any,
        resolution: ConflictResolution,
    ):
        self.id = f"conflict_{uuid.uuid4().hex[:8]}"
        self.field_path = field_path
        self.client_a = client_a
        self.client_b = client_b
        self.value_a = value_a
        self.value_b = value_b
        self.resolved_value = resolved_value
        self.resolution = resolution
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "field_path": self.field_path,
            "client_a": self.client_a,
            "client_b": self.client_b,
            "value_a": self.value_a,
            "value_b": self.value_b,
            "resolved_value": self.resolved_value,
            "resolution": self.resolution.value,
            "timestamp": self.timestamp.isoformat(),
        }


class MergeResult:
    """Result of merging a client update into the authoritative document."""

    __slots__ = (
        "success", "conflicts", "fields_merged", "error",
        "new_checksum", "timestamp",
    )

    def __init__(
        self,
        success: bool = True,
        conflicts: Optional[List[ConflictRecord]] = None,
        fields_merged: int = 0,
        error: Optional[str] = None,
    ):
        self.success = success
        self.conflicts = conflicts or []
        self.fields_merged = fields_merged
        self.error = error
        self.new_checksum = ""
        self.timestamp = datetime.now(timezone.utc)

    @property
    def had_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    @property
    def conflict_count(self) -> int:
        return len(self.conflicts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "fields_merged": self.fields_merged,
            "had_conflicts": self.had_conflicts,
            "new_checksum": self.new_checksum,
            "error": self.error,
        }


class DocumentState(str, Enum):
    """State of the CRDT document."""
    CLEAN = "clean"
    DIRTY = "dirty"
    MERGING = "merging"
    LOCKED = "locked"


# ---------------------------------------------------------------------------
# FieldTimestamp -- per-field LWW tracking
# ---------------------------------------------------------------------------


class FieldTimestamp:
    """LWW register: tracks who edited a field and when."""

    __slots__ = ("path", "client_id", "timestamp", "clock_value")

    def __init__(self, path: str, client_id: str, clock_value: int = 0):
        self.path = path
        self.client_id = client_id
        self.timestamp = datetime.now(timezone.utc)
        self.clock_value = clock_value


# ---------------------------------------------------------------------------
# CRDTDocument -- server-side authoritative CRDT wrapper
# ---------------------------------------------------------------------------


class CRDTDocument:
    """
    Server-side CRDT document for a PresentationDSL.

    Provides:
    - Authoritative copy of the DSL
    - Per-field last-writer-wins timestamps
    - Vector clock for causal ordering
    - Structural merge for concurrent edits
    - Conflict detection and resolution log
    - State checksums for sync verification

    Usage:
        doc = CRDTDocument("pres-123", dsl)
        result = doc.merge_update(client_id, partial_update, client_clock)
        if result.had_conflicts:
            # Notify client of resolution
            ...
        current = doc.get_state()
    """

    def __init__(self, presentation_id: str, dsl: PresentationDSL):
        self._presentation_id = presentation_id
        self._dsl = dsl
        self._state = DocumentState.CLEAN
        self._vector_clock: Dict[str, int] = defaultdict(int)
        self._field_timestamps: Dict[str, FieldTimestamp] = {}
        self._conflict_log: List[ConflictRecord] = []
        self._revision = 0
        self._created_at = datetime.now(timezone.utc)
        self._checksum = self._compute_checksum()
        self._active_slide_ids: Set[str] = {s.id for s in dsl.slides}

    # ── Properties ────────────────────────────────────────────────

    @property
    def presentation_id(self) -> str:
        return self._presentation_id

    @property
    def dsl(self) -> PresentationDSL:
        return self._dsl

    @property
    def state(self) -> DocumentState:
        return self._state

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def checksum(self) -> str:
        return self._checksum

    @property
    def vector_clock(self) -> Dict[str, int]:
        return dict(self._vector_clock)

    @property
    def conflict_count(self) -> int:
        return len(self._conflict_log)

    @property
    def active_slide_ids(self) -> Set[str]:
        return set(self._active_slide_ids)

    # ── Core merge operation ─────────────────────────────────────

    def merge_update(
        self,
        client_id: str,
        update: Dict[str, Any],
        client_clock: Optional[Dict[str, int]] = None,
    ) -> MergeResult:
        """
        Merge a client update into the authoritative document.

        The update dict can contain:
        - "slides.<slide_id>.content.title": "New Title"
        - "slides.<slide_id>.style.accentColor": "#FF0000"
        - "presentation.title": "New Deck Title"
        - "slides_add": [{"type": "custom", ...}]
        - "slides_remove": ["slide_3"]

        Returns MergeResult with conflict info.
        """
        if not update:
            return MergeResult(success=True, fields_merged=0)

        self._state = DocumentState.MERGING
        conflicts: List[ConflictRecord] = []
        fields_merged = 0

        # Update vector clock
        if client_clock:
            for cid, val in client_clock.items():
                self._vector_clock[cid] = max(self._vector_clock[cid], val)
        self._vector_clock[client_id] = self._vector_clock.get(client_id, 0) + 1

        try:
            # Process slide collection operations first (add/remove)
            if "slides_add" in update:
                added = self._merge_slide_adds(
                    update["slides_add"], client_id
                )
                fields_merged += added

            if "slides_remove" in update:
                removed = self._merge_slide_removes(
                    update["slides_remove"], client_id, conflicts
                )
                fields_merged += removed

            # Process field-level updates
            for path, value in update.items():
                if path in ("slides_add", "slides_remove"):
                    continue
                merged, conflict = self._merge_field(
                    path, value, client_id
                )
                if merged:
                    fields_merged += 1
                if conflict:
                    conflicts.append(conflict)

            # Update internal state
            self._revision += 1
            self._checksum = self._compute_checksum()
            self._active_slide_ids = {s.id for s in self._dsl.slides}
            self._state = DocumentState.DIRTY if fields_merged > 0 else DocumentState.CLEAN

            # Log conflicts
            self._conflict_log.extend(conflicts)

            result = MergeResult(
                success=True,
                conflicts=conflicts,
                fields_merged=fields_merged,
            )
            result.new_checksum = self._checksum

            logger.info(
                "crdt_merge_complete",
                presentation_id=self._presentation_id,
                client_id=client_id,
                fields_merged=fields_merged,
                conflicts=len(conflicts),
                revision=self._revision,
            )
            return result

        except Exception as exc:
            self._state = DocumentState.CLEAN
            logger.error("crdt_merge_error", error=str(exc))
            return MergeResult(
                success=False,
                error=str(exc),
            )

    # ── Field-level merge ────────────────────────────────────────

    def _merge_field(
        self,
        path: str,
        value: Any,
        client_id: str,
    ) -> Tuple[bool, Optional[ConflictRecord]]:
        """
        Merge a single field update using LWW semantics.

        Returns (merged: bool, conflict: Optional[ConflictRecord]).
        """
        existing = self._field_timestamps.get(path)
        clock_val = self._vector_clock.get(client_id, 0)
        conflict = None

        # Check for concurrent edit (different client, same field)
        if existing and existing.client_id != client_id:
            old_value = self._resolve_path(path)
            if old_value != value:
                # LWW: higher clock wins, ties broken by client_id
                if clock_val > existing.clock_value or (
                    clock_val == existing.clock_value
                    and client_id > existing.client_id
                ):
                    # Incoming wins
                    conflict = ConflictRecord(
                        field_path=path,
                        client_a=existing.client_id,
                        client_b=client_id,
                        value_a=old_value,
                        value_b=value,
                        resolved_value=value,
                        resolution=ConflictResolution.LAST_WRITER_WINS,
                    )
                else:
                    # Existing wins -- skip update
                    conflict = ConflictRecord(
                        field_path=path,
                        client_a=existing.client_id,
                        client_b=client_id,
                        value_a=old_value,
                        value_b=value,
                        resolved_value=old_value,
                        resolution=ConflictResolution.LAST_WRITER_WINS,
                    )
                    return False, conflict

        # Apply the update
        applied = self._apply_path(path, value)
        if applied:
            self._field_timestamps[path] = FieldTimestamp(
                path=path, client_id=client_id, clock_value=clock_val
            )
        return applied, conflict

    # ── Slide collection operations ──────────────────────────────

    def _merge_slide_adds(
        self, slide_data_list: List[Dict[str, Any]], client_id: str
    ) -> int:
        """Add slides (add-wins semantics: concurrent adds both succeed)."""
        from app.models.dsl_v2 import SlideDSL

        added = 0
        for slide_data in slide_data_list:
            try:
                slide = SlideDSL(**slide_data)
                # Ensure unique ID
                if slide.id in self._active_slide_ids:
                    slide.id = f"slide_{uuid.uuid4().hex[:12]}"
                slide.index = len(self._dsl.slides)
                self._dsl.slides.append(slide)
                self._active_slide_ids.add(slide.id)
                added += 1
            except Exception as exc:
                logger.warning("crdt_slide_add_failed", error=str(exc))
        return added

    def _merge_slide_removes(
        self,
        slide_ids: List[str],
        client_id: str,
        conflicts: List[ConflictRecord],
    ) -> int:
        """Remove slides. If slide was concurrently modified, flag conflict."""
        removed = 0
        for sid in slide_ids:
            if sid not in self._active_slide_ids:
                continue
            # Check if another client recently edited this slide
            edited_by_other = False
            for path, ft in self._field_timestamps.items():
                if path.startswith(f"slides.{sid}.") and ft.client_id != client_id:
                    edited_by_other = True
                    break

            if edited_by_other:
                # Flag conflict but still remove (delete-wins in our model)
                conflicts.append(ConflictRecord(
                    field_path=f"slides.{sid}",
                    client_a="other",
                    client_b=client_id,
                    value_a="modified",
                    value_b="removed",
                    resolved_value="removed",
                    resolution=ConflictResolution.SERVER_AUTHORITY,
                ))

            self._dsl.slides = [s for s in self._dsl.slides if s.id != sid]
            self._active_slide_ids.discard(sid)
            # Reindex
            for idx, s in enumerate(self._dsl.slides):
                s.index = idx
            removed += 1
        return removed

    # ── Path resolution (dot-notation to model field) ────────────

    def _resolve_path(self, path: str) -> Any:
        """
        Resolve a dot-notation path to a value in the DSL.

        Paths: "presentation.title", "slides.<id>.content.title", etc.
        """
        parts = path.split(".")
        obj: Any = self._dsl

        for part in parts:
            if isinstance(obj, list):
                # Search by ID in slides list
                found = None
                for item in obj:
                    if hasattr(item, "id") and item.id == part:
                        found = item
                        break
                if found is None:
                    return None
                obj = found
            elif hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict):
                obj = obj.get(part)
            else:
                return None
        return obj

    def _apply_path(self, path: str, value: Any) -> bool:
        """
        Apply a dot-notation update to the DSL.

        Returns True if update was applied successfully.
        """
        parts = path.split(".")
        if len(parts) < 2:
            return False

        # Navigate to parent
        obj: Any = self._dsl
        for part in parts[:-1]:
            if part == "slides":
                obj = self._dsl.slides
                continue
            if isinstance(obj, list):
                found = None
                for item in obj:
                    if hasattr(item, "id") and item.id == part:
                        found = item
                        break
                if found is None:
                    return False
                obj = found
            elif hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict):
                if part not in obj:
                    return False
                obj = obj[part]
            else:
                return False

        # Set final field
        field = parts[-1]
        try:
            if hasattr(obj, field):
                setattr(obj, field, value)
                return True
            elif isinstance(obj, dict):
                obj[field] = value
                return True
        except Exception:
            return False
        return False

    # ── State queries ────────────────────────────────────────────

    def get_state(self) -> Dict[str, Any]:
        """Get full document state for sync."""
        return {
            "presentation_id": self._presentation_id,
            "revision": self._revision,
            "checksum": self._checksum,
            "vector_clock": dict(self._vector_clock),
            "state": self._state.value,
            "slide_count": len(self._dsl.slides),
            "dsl": self._dsl.model_dump(mode="json"),
        }

    def get_delta_since(self, since_revision: int) -> Dict[str, Any]:
        """
        Get changes since a specific revision.

        Returns field updates that happened after since_revision.
        """
        changes = {}
        for path, ft in self._field_timestamps.items():
            if ft.clock_value > since_revision:
                changes[path] = {
                    "value": self._resolve_path(path),
                    "client_id": ft.client_id,
                    "timestamp": ft.timestamp.isoformat(),
                }
        return {
            "from_revision": since_revision,
            "to_revision": self._revision,
            "changes": changes,
            "checksum": self._checksum,
        }

    def get_conflict_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent conflict log."""
        return [c.to_dict() for c in self._conflict_log[-limit:]]

    def mark_clean(self) -> None:
        """Mark document as synced/clean."""
        self._state = DocumentState.CLEAN

    def lock(self) -> bool:
        """Lock document for exclusive operations (e.g., rollback)."""
        if self._state == DocumentState.LOCKED:
            return False
        self._state = DocumentState.LOCKED
        return True

    def unlock(self) -> None:
        """Unlock document."""
        self._state = DocumentState.CLEAN

    def replace_dsl(self, dsl: PresentationDSL) -> None:
        """Replace the entire DSL (used for rollback)."""
        self._dsl = dsl
        self._revision += 1
        self._checksum = self._compute_checksum()
        self._active_slide_ids = {s.id for s in dsl.slides}
        self._field_timestamps.clear()
        self._state = DocumentState.CLEAN

    # ── Internal ─────────────────────────────────────────────────

    def _compute_checksum(self) -> str:
        """SHA-256 first 16 hex chars of serialized DSL."""
        data = json.dumps(
            self._dsl.model_dump(mode="json"), sort_keys=True
        ).encode("utf-8")
        return hashlib.sha256(data).hexdigest()[:16]
