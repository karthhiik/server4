"""
Phase 9 -- Unified DSL Editor API Routes.

REST endpoints for all editor operations:
    - Slide CRUD (add / remove / move / duplicate / update)
    - Element CRUD (add / remove / update / move / resize)
    - HITL checkpoint gates (create / approve / reject / status)
    - Version history (snapshot / diff / rollback / list)
    - Regeneration (per-slide / per-section / full-deck)
    - Layout management (change / suggest / available)
    - Validation (full / per-slide)
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.dsl_v2 import (
    ElementType,
    LayoutType,
    PresentationDSL,
    SlideContentV2,
    SlideElement,
    SlideStyle,
    SlideType,
)
from app.services.dsl_editor.editor_engine import (
    DSLEditorEngine,
    LineageSource,
)
from app.services.dsl_editor.hitl_manager import (
    HITLManager,
    HITLGate,
    HITLDecision,
)
from app.services.dsl_editor.version_manager import VersionManager
from app.services.dsl_editor.regeneration_engine import (
    RegenerationEngine,
    RegenerationLevel,
    RegenerationRequest,
)
from app.services.dsl_editor.layout_manager import LayoutManager
from app.services.dsl_editor.dsl_validator import DSLValidator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/editor", tags=["dsl-editor-v2"])


# ═══════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════


# -- Slide operations -----------------------------------------------

class AddSlideRequest(BaseModel):
    slide_type: str = Field(default="custom", description="SlideType value")
    layout: str = Field(default="center-focus", description="LayoutType value")
    title: str = Field(default="New Slide", max_length=200)
    position: Optional[int] = Field(default=None, description="Insert at index (None=end)")
    section: Optional[str] = Field(default=None, max_length=100)


class MoveSlideRequest(BaseModel):
    slide_id: str
    to_index: int = Field(ge=0)


class DuplicateSlideRequest(BaseModel):
    slide_id: str


class UpdateSlideContentRequest(BaseModel):
    slide_id: str
    content: Dict[str, Any] = Field(description="Partial SlideContentV2 fields to update")


class UpdateSlideStyleRequest(BaseModel):
    slide_id: str
    style: Dict[str, Any] = Field(description="Partial SlideStyle fields to update")


class UpdateSlideTypeRequest(BaseModel):
    slide_id: str
    slide_type: str


class ReorderSlidesRequest(BaseModel):
    slide_ids: List[str] = Field(description="New ordering of slide IDs")


# -- Element operations ---------------------------------------------

class AddElementRequest(BaseModel):
    slide_id: str
    element_type: str
    content: str = ""
    x: float = Field(default=0.1, ge=0.0, le=1.0)
    y: float = Field(default=0.1, ge=0.0, le=1.0)
    width: float = Field(default=0.3, gt=0.0, le=1.0)
    height: float = Field(default=0.2, gt=0.0, le=1.0)


class UpdateElementRequest(BaseModel):
    slide_id: str
    element_id: str
    updates: Dict[str, Any] = Field(description="Fields to update on the element")


class MoveElementRequest(BaseModel):
    slide_id: str
    element_id: str
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)


class ResizeElementRequest(BaseModel):
    slide_id: str
    element_id: str
    width: float = Field(gt=0.0, le=1.0)
    height: float = Field(gt=0.0, le=1.0)


# -- HITL operations ------------------------------------------------

class CreateCheckpointRequest(BaseModel):
    presentation_id: str
    gate: str = Field(description="HITLGate value: narrative | research_design | full_render")
    agent_output: Dict[str, Any] = Field(description="Agent output to review")
    fast_mode: bool = False


class CheckpointDecisionRequest(BaseModel):
    presentation_id: str
    gate: str
    decision: str = Field(description="approve | reject | edit")
    feedback: Optional[str] = None
    edits: Optional[Dict[str, Any]] = None


# -- Version operations ---------------------------------------------

class CreateSnapshotRequest(BaseModel):
    label: str = Field(default="manual", max_length=200)


class RollbackRequest(BaseModel):
    version: int = Field(ge=0)


class DiffRequest(BaseModel):
    from_version: int = Field(ge=0)
    to_version: int = Field(ge=0)


# -- Regeneration operations ----------------------------------------

class RegenerateRequest(BaseModel):
    level: str = Field(description="slide | section | deck")
    slide_id: Optional[str] = None
    section_name: Optional[str] = None
    feedback: str = Field(default="", description="User feedback for regeneration")
    preserve_theme: bool = True
    preserve_layout: bool = True
    preserve_images: bool = False


# -- Layout operations ----------------------------------------------

class ChangeLayoutRequest(BaseModel):
    slide_id: str
    layout: str = Field(description="LayoutType value")
    reflow: bool = True


class DeckLayoutRequest(BaseModel):
    layout: str
    exclude_types: Optional[List[str]] = None


# -- Validation operations ------------------------------------------

class ValidateSlideRequest(BaseModel):
    slide_id: str


# -- Generic responses ----------------------------------------------

class OperationResponse(BaseModel):
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None


class EditorStateResponse(BaseModel):
    success: bool
    dsl: Dict[str, Any]
    version: Optional[int] = None


# ═══════════════════════════════════════════════════════════════════
# In-memory session store (per-presentation editor state)
# ═══════════════════════════════════════════════════════════════════

# In a production deployment this would be backed by Redis/MongoDB.
# For Phase 9, we keep an in-memory dict keyed by presentation ID.

class _EditorSession:
    """Bundles all Phase 9 components for a single presentation."""

    __slots__ = ("engine", "hitl", "versions", "regen", "layout", "validator")

    def __init__(self, dsl: PresentationDSL):
        self.engine = DSLEditorEngine(dsl)
        self.hitl = HITLManager()
        self.versions = VersionManager()
        self.regen = RegenerationEngine(dsl)
        self.layout = LayoutManager(dsl)
        self.validator = DSLValidator(dsl)

    @property
    def dsl(self) -> PresentationDSL:
        return self.engine.dsl


_sessions: Dict[str, _EditorSession] = {}


def _get_session(presentation_id: str) -> _EditorSession:
    if presentation_id not in _sessions:
        raise HTTPException(status_code=404, detail=f"No editor session for '{presentation_id}'")
    return _sessions[presentation_id]


# ═══════════════════════════════════════════════════════════════════
# SESSION LIFECYCLE
# ═══════════════════════════════════════════════════════════════════


@router.post("/sessions/open", response_model=EditorStateResponse)
async def open_editor_session(dsl: PresentationDSL):
    """Open an editor session for a presentation DSL."""
    pid = dsl.presentation.id
    session = _EditorSession(dsl)
    session.versions.create_snapshot(dsl, description="session_opened")
    _sessions[pid] = session

    logger.info("Editor session opened: %s (%d slides)", pid, len(dsl.slides))
    return EditorStateResponse(
        success=True,
        dsl=dsl.model_dump(mode="json"),
        version=0,
    )


@router.get("/sessions/{presentation_id}", response_model=EditorStateResponse)
async def get_editor_state(presentation_id: str):
    """Get current editor state."""
    s = _get_session(presentation_id)
    return EditorStateResponse(
        success=True,
        dsl=s.dsl.model_dump(mode="json"),
        version=len(s.versions.list_snapshots()) - 1,
    )


@router.delete("/sessions/{presentation_id}", response_model=OperationResponse)
async def close_editor_session(presentation_id: str):
    """Close and clean up an editor session."""
    if presentation_id in _sessions:
        del _sessions[presentation_id]
    return OperationResponse(success=True, message="Session closed")


# ═══════════════════════════════════════════════════════════════════
# SLIDE CRUD
# ═══════════════════════════════════════════════════════════════════


@router.post("/sessions/{pid}/slides", response_model=OperationResponse)
async def add_slide(pid: str, req: AddSlideRequest):
    """Add a new slide to the presentation."""
    s = _get_session(pid)
    try:
        slide_type = SlideType(req.slide_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid slide type: {req.slide_type}")
    try:
        layout_type = LayoutType(req.layout)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid layout: {req.layout}")

    result = s.engine.add_slide(
        slide_type=slide_type,
        layout=layout_type,
        title=req.title,
        position=req.position,
        section=req.section,
    )
    s.versions.create_snapshot(s.dsl, description=f"add_slide:{result.slide_id}")
    return OperationResponse(
        success=result.success,
        message=result.message,
        data={"slide_id": result.slide_id, "index": result.index},
    )


@router.delete("/sessions/{pid}/slides/{slide_id}", response_model=OperationResponse)
async def remove_slide(pid: str, slide_id: str):
    """Remove a slide."""
    s = _get_session(pid)
    result = s.engine.remove_slide(slide_id)
    if result.success:
        s.versions.create_snapshot(s.dsl, description=f"remove_slide:{slide_id}")
    return OperationResponse(success=result.success, message=result.message)


@router.put("/sessions/{pid}/slides/move", response_model=OperationResponse)
async def move_slide(pid: str, req: MoveSlideRequest):
    """Move a slide to a new position."""
    s = _get_session(pid)
    result = s.engine.move_slide(req.slide_id, req.to_index)
    if result.success:
        s.versions.create_snapshot(s.dsl, description=f"move_slide:{req.slide_id}")
    return OperationResponse(success=result.success, message=result.message)


@router.post("/sessions/{pid}/slides/duplicate", response_model=OperationResponse)
async def duplicate_slide(pid: str, req: DuplicateSlideRequest):
    """Duplicate a slide."""
    s = _get_session(pid)
    result = s.engine.duplicate_slide(req.slide_id)
    if result.success:
        s.versions.create_snapshot(s.dsl, description=f"duplicate_slide:{req.slide_id}")
    return OperationResponse(
        success=result.success,
        message=result.message,
        data={"new_slide_id": result.slide_id} if result.success else None,
    )


@router.put("/sessions/{pid}/slides/content", response_model=OperationResponse)
async def update_slide_content(pid: str, req: UpdateSlideContentRequest):
    """Update slide content fields."""
    s = _get_session(pid)
    result = s.engine.update_slide_content(req.slide_id, req.content)
    if result.success:
        s.versions.create_snapshot(s.dsl, description=f"update_content:{req.slide_id}")
    return OperationResponse(success=result.success, message=result.message)


@router.put("/sessions/{pid}/slides/style", response_model=OperationResponse)
async def update_slide_style(pid: str, req: UpdateSlideStyleRequest):
    """Update slide style fields."""
    s = _get_session(pid)
    result = s.engine.update_slide_style(req.slide_id, req.style)
    if result.success:
        s.versions.create_snapshot(s.dsl, description=f"update_style:{req.slide_id}")
    return OperationResponse(success=result.success, message=result.message)


@router.put("/sessions/{pid}/slides/type", response_model=OperationResponse)
async def update_slide_type(pid: str, req: UpdateSlideTypeRequest):
    """Change a slide's type."""
    s = _get_session(pid)
    try:
        slide_type = SlideType(req.slide_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid slide type: {req.slide_type}")
    result = s.engine.update_slide_type(req.slide_id, slide_type)
    if result.success:
        s.versions.create_snapshot(s.dsl, description=f"update_type:{req.slide_id}")
    return OperationResponse(success=result.success, message=result.message)


@router.put("/sessions/{pid}/slides/reorder", response_model=OperationResponse)
async def reorder_slides(pid: str, req: ReorderSlidesRequest):
    """Reorder all slides."""
    s = _get_session(pid)
    result = s.engine.reorder_slides(req.slide_ids)
    if result.success:
        s.versions.create_snapshot(s.dsl, description="reorder_slides")
    return OperationResponse(success=result.success, message=result.message)


# ═══════════════════════════════════════════════════════════════════
# ELEMENT CRUD
# ═══════════════════════════════════════════════════════════════════


@router.post("/sessions/{pid}/elements", response_model=OperationResponse)
async def add_element(pid: str, req: AddElementRequest):
    """Add an element to a slide."""
    s = _get_session(pid)
    try:
        elem_type = ElementType(req.element_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid element type: {req.element_type}")

    result = s.engine.add_element(
        slide_id=req.slide_id,
        element_type=elem_type,
        content=req.content,
        x=req.x, y=req.y,
        width=req.width, height=req.height,
    )
    if result.success:
        s.versions.create_snapshot(s.dsl, description=f"add_element:{req.slide_id}")
    return OperationResponse(
        success=result.success,
        message=result.message,
        data={"element_id": result.element_id} if result.success else None,
    )


@router.delete("/sessions/{pid}/elements/{slide_id}/{element_id}", response_model=OperationResponse)
async def remove_element(pid: str, slide_id: str, element_id: str):
    """Remove an element from a slide."""
    s = _get_session(pid)
    result = s.engine.remove_element(slide_id, element_id)
    if result.success:
        s.versions.create_snapshot(s.dsl, description=f"remove_element:{slide_id}:{element_id}")
    return OperationResponse(success=result.success, message=result.message)


@router.put("/sessions/{pid}/elements/update", response_model=OperationResponse)
async def update_element(pid: str, req: UpdateElementRequest):
    """Update element fields."""
    s = _get_session(pid)
    result = s.engine.update_element(req.slide_id, req.element_id, req.updates)
    if result.success:
        s.versions.create_snapshot(s.dsl, description=f"update_element:{req.slide_id}:{req.element_id}")
    return OperationResponse(success=result.success, message=result.message)


@router.put("/sessions/{pid}/elements/move", response_model=OperationResponse)
async def move_element(pid: str, req: MoveElementRequest):
    """Move an element to new coordinates."""
    s = _get_session(pid)
    result = s.engine.move_element(req.slide_id, req.element_id, req.x, req.y)
    if result.success:
        s.versions.create_snapshot(s.dsl, description=f"move_element:{req.slide_id}:{req.element_id}")
    return OperationResponse(success=result.success, message=result.message)


@router.put("/sessions/{pid}/elements/resize", response_model=OperationResponse)
async def resize_element(pid: str, req: ResizeElementRequest):
    """Resize an element."""
    s = _get_session(pid)
    result = s.engine.resize_element(req.slide_id, req.element_id, req.width, req.height)
    if result.success:
        s.versions.create_snapshot(s.dsl, description=f"resize_element:{req.slide_id}:{req.element_id}")
    return OperationResponse(success=result.success, message=result.message)


# ═══════════════════════════════════════════════════════════════════
# HITL CHECKPOINTS
# ═══════════════════════════════════════════════════════════════════


@router.post("/sessions/{pid}/hitl/checkpoint", response_model=OperationResponse)
async def create_hitl_checkpoint(pid: str, req: CreateCheckpointRequest):
    """Create a HITL checkpoint for agent output review."""
    s = _get_session(pid)
    try:
        gate = HITLGate(req.gate)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid gate: {req.gate}")

    checkpoint = s.hitl.create_checkpoint(
        presentation_id=req.presentation_id,
        gate=gate,
        agent_output=req.agent_output,
        fast_mode=req.fast_mode,
    )
    return OperationResponse(
        success=True,
        message=f"Checkpoint created: {gate.value}",
        data=checkpoint.to_dict(),
    )


@router.put("/sessions/{pid}/hitl/decision", response_model=OperationResponse)
async def submit_hitl_decision(pid: str, req: CheckpointDecisionRequest):
    """Submit a user decision on a HITL checkpoint."""
    s = _get_session(pid)
    try:
        gate = HITLGate(req.gate)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid gate: {req.gate}")

    if req.decision == "approve":
        result = s.hitl.approve(req.presentation_id, gate, user_edits=req.edits)
    elif req.decision == "reject":
        result = s.hitl.reject(req.presentation_id, gate, feedback=req.feedback or "")
    elif req.decision == "edit":
        if not req.edits:
            raise HTTPException(status_code=400, detail="Edit decision requires 'edits' field")
        result = s.hitl.approve(req.presentation_id, gate, user_edits=req.edits)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid decision: {req.decision}")

    return OperationResponse(
        success=result,
        message=f"{req.decision} applied to {gate.value}",
    )


@router.get("/sessions/{pid}/hitl/status", response_model=OperationResponse)
async def get_hitl_status(pid: str):
    """Get gate status for all HITL checkpoints."""
    s = _get_session(pid)
    status = s.hitl.get_pipeline_status(pid)
    pending = s.hitl.get_pending_checkpoints(pid)
    return OperationResponse(
        success=True,
        message="HITL status retrieved",
        data={
            "gates": status,
            "pending": [cp.to_dict() for cp in pending],
        },
    )


# ═══════════════════════════════════════════════════════════════════
# VERSION HISTORY
# ═══════════════════════════════════════════════════════════════════


@router.post("/sessions/{pid}/versions/snapshot", response_model=OperationResponse)
async def create_snapshot(pid: str, req: CreateSnapshotRequest):
    """Create a named snapshot of the current state."""
    s = _get_session(pid)
    snap = s.versions.create_snapshot(s.dsl, description=req.label)
    return OperationResponse(
        success=True,
        message=f"Snapshot v{snap.version} created",
        data={"version": snap.version, "label": snap.label, "checksum": snap.checksum},
    )


@router.get("/sessions/{pid}/versions", response_model=OperationResponse)
async def list_versions(pid: str, limit: int = 20, offset: int = 0):
    """List version history."""
    s = _get_session(pid)
    snapshots = s.versions.list_snapshots(limit=limit, offset=offset)
    return OperationResponse(
        success=True,
        message=f"{len(snapshots)} snapshots",
        data={
            "snapshots": [
                {
                    "version": sn.version,
                    "label": sn.label,
                    "timestamp": sn.timestamp.isoformat(),
                    "checksum": sn.checksum,
                    "slide_count": sn.slide_count,
                }
                for sn in snapshots
            ]
        },
    )


@router.post("/sessions/{pid}/versions/rollback", response_model=EditorStateResponse)
async def rollback_version(pid: str, req: RollbackRequest):
    """Rollback to a previous version."""
    s = _get_session(pid)
    restored = s.versions.rollback(req.version)
    if restored is None:
        raise HTTPException(status_code=404, detail=f"Version {req.version} not found")

    # Replace the DSL in all components
    s.engine._dsl = restored
    s.regen._dsl = restored
    s.layout._dsl = restored
    s.validator._dsl = restored

    return EditorStateResponse(
        success=True,
        dsl=restored.model_dump(mode="json"),
        version=req.version,
    )


@router.post("/sessions/{pid}/versions/diff", response_model=OperationResponse)
async def diff_versions(pid: str, req: DiffRequest):
    """Diff two versions."""
    s = _get_session(pid)
    diff = s.versions.diff(req.from_version, req.to_version)
    if diff is None:
        raise HTTPException(status_code=404, detail="One or both versions not found")
    return OperationResponse(
        success=True,
        message=f"Diff v{req.from_version} → v{req.to_version}",
        data=diff.to_dict(),
    )


# ═══════════════════════════════════════════════════════════════════
# REGENERATION
# ═══════════════════════════════════════════════════════════════════


@router.post("/sessions/{pid}/regenerate/preview", response_model=OperationResponse)
async def preview_regeneration(pid: str, req: RegenerateRequest):
    """Preview what a regeneration would affect (dry run)."""
    s = _get_session(pid)
    try:
        level = RegenerationLevel(req.level)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid level: {req.level}")

    regen_req = RegenerationRequest(
        level=level,
        slide_id=req.slide_id,
        section_name=req.section_name,
        feedback=req.feedback,
        preserve_theme=req.preserve_theme,
        preserve_layout=req.preserve_layout,
        preserve_images=req.preserve_images,
    )
    preview = s.regen.preview_regeneration(regen_req)
    return OperationResponse(
        success=True,
        message="Regeneration preview",
        data=preview,
    )


@router.post("/sessions/{pid}/regenerate/context", response_model=OperationResponse)
async def get_regeneration_context(pid: str, req: RegenerateRequest):
    """Get the context that would be sent to the regeneration agent."""
    s = _get_session(pid)
    try:
        level = RegenerationLevel(req.level)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid level: {req.level}")

    if level == RegenerationLevel.SLIDE and req.slide_id:
        context = s.regen.build_slide_context(req.slide_id)
    elif level == RegenerationLevel.SECTION and req.section_name:
        context = s.regen.build_section_context(req.section_name)
    elif level == RegenerationLevel.DECK:
        context = s.regen.build_deck_context()
    else:
        raise HTTPException(status_code=400, detail="Missing slide_id or section_name for selected level")

    return OperationResponse(
        success=True,
        message=f"Context for {level.value} regeneration",
        data=context,
    )


# ═══════════════════════════════════════════════════════════════════
# LAYOUT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════


@router.put("/sessions/{pid}/layout/change", response_model=OperationResponse)
async def change_slide_layout(pid: str, req: ChangeLayoutRequest):
    """Change a slide's layout with content reflow."""
    s = _get_session(pid)
    try:
        layout = LayoutType(req.layout)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid layout: {req.layout}")

    result = s.layout.change_slide_layout(req.slide_id, layout, reflow=req.reflow)
    if result.success:
        s.versions.create_snapshot(s.dsl, description=f"layout_change:{req.slide_id}")
    return OperationResponse(
        success=result.success,
        message=f"Layout changed to {req.layout}" if result.success else (result.error or "Failed"),
        data=result.to_dict(),
    )


@router.put("/sessions/{pid}/layout/deck", response_model=OperationResponse)
async def apply_deck_layout(pid: str, req: DeckLayoutRequest):
    """Apply a consistent layout across all content slides."""
    s = _get_session(pid)
    try:
        layout = LayoutType(req.layout)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid layout: {req.layout}")

    exclude = None
    if req.exclude_types:
        try:
            exclude = [SlideType(t) for t in req.exclude_types]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid exclude type: {e}")

    result = s.layout.apply_deck_layout(layout, exclude_types=exclude)
    s.versions.create_snapshot(s.dsl, description="deck_layout_applied")
    return OperationResponse(
        success=True,
        message=f"Applied {req.layout} to deck",
        data=result,
    )


@router.get("/sessions/{pid}/layout/suggest/{slide_id}", response_model=OperationResponse)
async def suggest_layout(pid: str, slide_id: str):
    """Get smart layout suggestions for a slide."""
    s = _get_session(pid)
    suggestions = s.layout.suggest_layout(slide_id)
    return OperationResponse(
        success=True,
        message=f"{len(suggestions)} layout suggestions",
        data={"suggestions": [sg.to_dict() for sg in suggestions]},
    )


@router.get("/sessions/{pid}/layout/suggest-deck", response_model=OperationResponse)
async def suggest_deck_layouts(pid: str):
    """Get layout suggestions for every slide."""
    s = _get_session(pid)
    suggestions = s.layout.suggest_layouts_for_deck()
    return OperationResponse(
        success=True,
        message="Deck layout suggestions",
        data={
            sid: [sg.to_dict() for sg in sgs]
            for sid, sgs in suggestions.items()
        },
    )


@router.get("/layout/available", response_model=OperationResponse)
async def list_available_layouts():
    """List all available layout types."""
    from app.services.dsl_editor.layout_manager import LayoutManager, LAYOUT_GEOMETRY
    from app.models.dsl_v2 import LayoutType as LT

    layouts = []
    for lt in LT:
        geo = LAYOUT_GEOMETRY.get(lt.value, {})
        layouts.append({
            "id": lt.value,
            "name": lt.value.replace("-", " ").replace("_", " ").title(),
            "regions": list(geo.keys()),
            "region_count": len(geo),
        })
    return OperationResponse(success=True, message="Available layouts", data={"layouts": layouts})


# ═══════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════


@router.get("/sessions/{pid}/validate", response_model=OperationResponse)
async def validate_presentation(pid: str):
    """Run full validation on the presentation."""
    s = _get_session(pid)
    report = s.validator.validate()
    return OperationResponse(
        success=report.passed,
        message=f"Score: {report.score}/100, {report.error_count} errors, {report.warning_count} warnings",
        data=report.to_dict(),
    )


@router.post("/sessions/{pid}/validate/slide", response_model=OperationResponse)
async def validate_slide(pid: str, req: ValidateSlideRequest):
    """Validate a single slide."""
    s = _get_session(pid)
    report = s.validator.validate_slide(req.slide_id)
    return OperationResponse(
        success=report.passed,
        message=f"Slide validation: {report.error_count} errors, {report.warning_count} warnings",
        data=report.to_dict(),
    )
