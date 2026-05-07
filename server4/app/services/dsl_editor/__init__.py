"""
Phase 9 — Unified DSL Editor.

The single source-of-truth editing engine that replaces per-renderer editors.
All mutations flow through the DSL; renderers are read-only views.

Components:
    - editor_engine: Core CRUD operations on PresentationDSL
    - hitl_manager:  Human-in-the-Loop checkpoint gates
    - version_manager: Snapshot history, diff, rollback
    - regeneration_engine: Per-slide / per-section / full deck re-generation
    - layout_manager: Layout switching, content reflow, smart suggestions
    - dsl_validator: Deep validation, accessibility, anti-pitfall rules
"""

from app.services.dsl_editor.editor_engine import (
    DSLEditorEngine,
    SlideOperationResult,
    ElementOperationResult,
    EditLineage,
    LineageSource,
)
from app.services.dsl_editor.hitl_manager import (
    HITLManager,
    HITLGate,
    HITLCheckpoint,
    HITLDecision,
    CheckpointStatus,
)
from app.services.dsl_editor.version_manager import (
    VersionManager,
    DeckSnapshot,
    VersionDiff,
    DiffEntry,
    DiffAction,
)
from app.services.dsl_editor.regeneration_engine import (
    RegenerationEngine,
    RegenerationLevel,
    RegenerationRequest,
    RegenerationResult,
)
from app.services.dsl_editor.layout_manager import (
    LayoutManager,
    LayoutSuggestion,
    ContentReflowResult,
)
from app.services.dsl_editor.dsl_validator import (
    DSLValidator,
    ValidationReport,
    ValidationIssue,
    IssueSeverity,
)

__all__ = [
    # Editor Engine
    "DSLEditorEngine",
    "SlideOperationResult",
    "ElementOperationResult",
    "EditLineage",
    "LineageSource",
    # HITL
    "HITLManager",
    "HITLGate",
    "HITLCheckpoint",
    "HITLDecision",
    "CheckpointStatus",
    # Versions
    "VersionManager",
    "DeckSnapshot",
    "VersionDiff",
    "DiffEntry",
    "DiffAction",
    # Regeneration
    "RegenerationEngine",
    "RegenerationLevel",
    "RegenerationRequest",
    "RegenerationResult",
    # Layout
    "LayoutManager",
    "LayoutSuggestion",
    "ContentReflowResult",
    # Validation
    "DSLValidator",
    "ValidationReport",
    "ValidationIssue",
    "IssueSeverity",
]
