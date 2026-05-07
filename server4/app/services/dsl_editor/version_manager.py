"""
Version Manager -- Snapshot history, diff, and rollback for PresentationDSL.

Every significant edit creates an immutable snapshot. Users can:
- Browse version history
- Diff any two versions (structural + content changes)
- Rollback to any previous version
- Pin a version to prevent auto-upgrade

Storage: in-memory list (persisted to MongoDB by the API layer).
"""

import copy
import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import structlog

from app.models.dsl_v2 import PresentationDSL

logger = structlog.get_logger()


# Maximum snapshots to retain per presentation (rolling window)
MAX_SNAPSHOTS = 100

# ---------------------------------------------------------------------------
# Diff types
# ---------------------------------------------------------------------------

class DiffAction(str, Enum):
    """Type of change between two versions."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    MOVED = "moved"
    UNCHANGED = "unchanged"


class DiffEntry:
    """A single difference between two DSL versions."""

    __slots__ = ("path", "action", "old_value", "new_value", "description")

    def __init__(
        self,
        path: str,
        action: DiffAction,
        old_value: Any = None,
        new_value: Any = None,
        description: str = "",
    ):
        self.path = path
        self.action = action
        self.old_value = old_value
        self.new_value = new_value
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "path": self.path,
            "action": self.action.value,
            "description": self.description,
        }
        if self.action in (DiffAction.REMOVED, DiffAction.MODIFIED):
            result["old_value"] = _truncate(self.old_value)
        if self.action in (DiffAction.ADDED, DiffAction.MODIFIED):
            result["new_value"] = _truncate(self.new_value)
        return result


class VersionDiff:
    """Full diff result between two versions."""

    def __init__(
        self,
        from_version: int,
        to_version: int,
        entries: List[DiffEntry],
    ):
        self.from_version = from_version
        self.to_version = to_version
        self.entries = entries

    @property
    def change_count(self) -> int:
        return len([e for e in self.entries if e.action != DiffAction.UNCHANGED])

    @property
    def has_changes(self) -> bool:
        return self.change_count > 0

    @property
    def summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for e in self.entries:
            key = e.action.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_version": self.from_version,
            "to_version": self.to_version,
            "change_count": self.change_count,
            "summary": self.summary,
            "entries": [e.to_dict() for e in self.entries],
        }


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

class DeckSnapshot:
    """Immutable point-in-time snapshot of a PresentationDSL."""

    def __init__(
        self,
        version: int,
        dsl_data: Dict[str, Any],
        description: str = "",
        author: str = "system",
        trigger: str = "manual",
    ):
        self.id = f"snap_{uuid.uuid4().hex[:12]}"
        self.version = version
        self.dsl_data = dsl_data
        self.description = description
        self.author = author
        self.trigger = trigger
        self.created_at = datetime.now(timezone.utc)
        self.checksum = self._compute_checksum(dsl_data)

    @staticmethod
    def _compute_checksum(data: Dict[str, Any]) -> str:
        raw = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "trigger": self.trigger,
            "created_at": self.created_at.isoformat(),
            "checksum": self.checksum,
            "slide_count": len(self.dsl_data.get("slides", [])),
        }

    def restore_dsl(self) -> PresentationDSL:
        """Reconstruct the PresentationDSL from this snapshot."""
        return PresentationDSL.model_validate(self.dsl_data)


# ---------------------------------------------------------------------------
# Version Manager
# ---------------------------------------------------------------------------

class VersionManager:
    """
    Manages immutable snapshots of PresentationDSL with diff and rollback.

    Usage:
        vm = VersionManager()
        vm.create_snapshot(dsl, description="Initial generation")
        vm.create_snapshot(dsl, description="User edited title")
        diff = vm.diff(1, 2)
        old_dsl = vm.rollback(1)
    """

    def __init__(self, max_snapshots: int = MAX_SNAPSHOTS):
        self._snapshots: List[DeckSnapshot] = []
        self._max = max_snapshots
        self._current_version = 0

    # ── Properties ────────────────────────────────────────────────

    @property
    def current_version(self) -> int:
        return self._current_version

    @property
    def snapshot_count(self) -> int:
        return len(self._snapshots)

    @property
    def latest_snapshot(self) -> Optional[DeckSnapshot]:
        if self._snapshots:
            return self._snapshots[-1]
        return None

    # ── Core operations ───────────────────────────────────────────

    def create_snapshot(
        self,
        dsl: PresentationDSL,
        description: str = "",
        author: str = "system",
        trigger: str = "manual",
    ) -> DeckSnapshot:
        """
        Create a new immutable snapshot. Returns the snapshot.
        If the DSL hasn't changed since the last snapshot, skip.
        """
        dsl_data = dsl.model_dump(mode="json")

        # Dedup: don't snapshot if nothing changed
        if self._snapshots:
            last = self._snapshots[-1]
            new_checksum = DeckSnapshot._compute_checksum(dsl_data)
            if new_checksum == last.checksum:
                logger.debug("snapshot_skipped_no_changes", version=self._current_version)
                return last

        self._current_version += 1

        snap = DeckSnapshot(
            version=self._current_version,
            dsl_data=dsl_data,
            description=description,
            author=author,
            trigger=trigger,
        )
        self._snapshots.append(snap)

        # Enforce rolling window
        if len(self._snapshots) > self._max:
            removed = self._snapshots.pop(0)
            logger.debug("snapshot_evicted", version=removed.version)

        logger.info(
            "snapshot_created",
            version=self._current_version,
            description=description[:60],
            trigger=trigger,
        )

        return snap

    def get_snapshot(self, version: int) -> Optional[DeckSnapshot]:
        """Get a snapshot by version number."""
        for s in self._snapshots:
            if s.version == version:
                return s
        return None

    def get_snapshot_by_id(self, snapshot_id: str) -> Optional[DeckSnapshot]:
        """Get a snapshot by its unique ID."""
        for s in self._snapshots:
            if s.id == snapshot_id:
                return s
        return None

    def list_snapshots(
        self, limit: int = 20, offset: int = 0
    ) -> List[DeckSnapshot]:
        """List snapshots in reverse chronological order."""
        ordered = list(reversed(self._snapshots))
        return ordered[offset:offset + limit]

    def rollback(self, version: int) -> Optional[PresentationDSL]:
        """
        Restore the DSL from a specific version's snapshot.
        Does NOT create a new snapshot -- caller decides whether to snapshot.
        """
        snap = self.get_snapshot(version)
        if snap is None:
            logger.warning("rollback_version_not_found", version=version)
            return None

        logger.info("rollback_executed", target_version=version)
        return snap.restore_dsl()

    def diff(self, from_version: int, to_version: int) -> Optional[VersionDiff]:
        """
        Compute a structural diff between two versions.

        Compares:
        - Presentation-level changes (title, theme, archetype)
        - Slide additions/removals
        - Per-slide content/style modifications
        - Element additions/removals within slides
        """
        snap_a = self.get_snapshot(from_version)
        snap_b = self.get_snapshot(to_version)

        if snap_a is None or snap_b is None:
            return None

        entries = self._compute_diff(snap_a.dsl_data, snap_b.dsl_data)
        return VersionDiff(from_version, to_version, entries)

    def diff_with_current(
        self, current_dsl: PresentationDSL, base_version: Optional[int] = None
    ) -> Optional[VersionDiff]:
        """Diff the current (unsaved) DSL against a snapshot version."""
        if base_version is None:
            snap = self.latest_snapshot
            if snap is None:
                return None
            base_version = snap.version
        else:
            snap = self.get_snapshot(base_version)
            if snap is None:
                return None

        current_data = current_dsl.model_dump(mode="json")
        entries = self._compute_diff(snap.dsl_data, current_data)
        return VersionDiff(base_version, self._current_version + 1, entries)

    # ── Diff algorithm ────────────────────────────────────────────

    def _compute_diff(
        self,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
    ) -> List[DiffEntry]:
        """Compute structural diff between two DSL dicts."""
        entries: List[DiffEntry] = []

        # 1. Presentation-level diff
        old_pres = old_data.get("presentation", {})
        new_pres = new_data.get("presentation", {})
        for key in ("title", "archetype", "aspectRatio"):
            old_val = old_pres.get(key)
            new_val = new_pres.get(key)
            if old_val != new_val:
                entries.append(DiffEntry(
                    path=f"presentation.{key}",
                    action=DiffAction.MODIFIED,
                    old_value=old_val,
                    new_value=new_val,
                    description=f"Changed {key}",
                ))

        # Theme diff
        old_theme = old_pres.get("theme", {})
        new_theme = new_pres.get("theme", {})
        if old_theme != new_theme:
            entries.append(DiffEntry(
                path="presentation.theme",
                action=DiffAction.MODIFIED,
                old_value=old_theme.get("id"),
                new_value=new_theme.get("id"),
                description="Theme changed",
            ))

        # 2. Slide-level diff
        old_slides = {s["id"]: s for s in old_data.get("slides", [])}
        new_slides = {s["id"]: s for s in new_data.get("slides", [])}

        old_ids = set(old_slides.keys())
        new_ids = set(new_slides.keys())

        # Added slides
        for sid in new_ids - old_ids:
            s = new_slides[sid]
            entries.append(DiffEntry(
                path=f"slides[{s.get('index', '?')}]",
                action=DiffAction.ADDED,
                new_value=s.get("content", {}).get("title", "Untitled"),
                description=f"Added slide: {s.get('type', 'custom')}",
            ))

        # Removed slides
        for sid in old_ids - new_ids:
            s = old_slides[sid]
            entries.append(DiffEntry(
                path=f"slides[{s.get('index', '?')}]",
                action=DiffAction.REMOVED,
                old_value=s.get("content", {}).get("title", "Untitled"),
                description=f"Removed slide: {s.get('type', 'custom')}",
            ))

        # Modified slides
        for sid in old_ids & new_ids:
            old_s = old_slides[sid]
            new_s = new_slides[sid]

            # Index change (moved)
            if old_s.get("index") != new_s.get("index"):
                entries.append(DiffEntry(
                    path=f"slides[{sid}].index",
                    action=DiffAction.MOVED,
                    old_value=old_s.get("index"),
                    new_value=new_s.get("index"),
                    description=f"Slide moved from {old_s.get('index')} to {new_s.get('index')}",
                ))

            # Content diff
            old_content = old_s.get("content", {})
            new_content = new_s.get("content", {})
            for field in ("title", "subtitle", "body_text", "bullets", "image_url"):
                old_val = old_content.get(field)
                new_val = new_content.get(field)
                if old_val != new_val:
                    entries.append(DiffEntry(
                        path=f"slides[{sid}].content.{field}",
                        action=DiffAction.MODIFIED,
                        old_value=old_val,
                        new_value=new_val,
                        description=f"Changed {field}",
                    ))

            # Layout/type change
            if old_s.get("layout") != new_s.get("layout"):
                entries.append(DiffEntry(
                    path=f"slides[{sid}].layout",
                    action=DiffAction.MODIFIED,
                    old_value=old_s.get("layout"),
                    new_value=new_s.get("layout"),
                    description="Layout changed",
                ))

            if old_s.get("type") != new_s.get("type"):
                entries.append(DiffEntry(
                    path=f"slides[{sid}].type",
                    action=DiffAction.MODIFIED,
                    old_value=old_s.get("type"),
                    new_value=new_s.get("type"),
                    description="Slide type changed",
                ))

            # Element diff
            old_elems = {e["id"]: e for e in old_s.get("elements", [])}
            new_elems = {e["id"]: e for e in new_s.get("elements", [])}

            for eid in set(new_elems) - set(old_elems):
                entries.append(DiffEntry(
                    path=f"slides[{sid}].elements[{eid}]",
                    action=DiffAction.ADDED,
                    new_value=new_elems[eid].get("type"),
                    description="Element added",
                ))

            for eid in set(old_elems) - set(new_elems):
                entries.append(DiffEntry(
                    path=f"slides[{sid}].elements[{eid}]",
                    action=DiffAction.REMOVED,
                    old_value=old_elems[eid].get("type"),
                    description="Element removed",
                ))

            for eid in set(old_elems) & set(new_elems):
                if old_elems[eid] != new_elems[eid]:
                    entries.append(DiffEntry(
                        path=f"slides[{sid}].elements[{eid}]",
                        action=DiffAction.MODIFIED,
                        description="Element modified",
                    ))

        return entries

    # ── Serialisation ─────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_version": self._current_version,
            "snapshot_count": len(self._snapshots),
            "snapshots": [s.to_dict() for s in self._snapshots],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate(value: Any, max_len: int = 200) -> Any:
    """Truncate large values for display in diffs."""
    if isinstance(value, str) and len(value) > max_len:
        return value[:max_len] + "..."
    if isinstance(value, list) and len(value) > 10:
        return value[:10] + ["..."]
    return value
