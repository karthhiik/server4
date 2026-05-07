"""
DSL Editor Engine -- Core CRUD operations on PresentationDSL.

The single source of truth: all edits flow through here.
Every mutation is validated, lineage-tracked, and snapshot-ready.

Principles (from V7 Plan Section 10):
- Edits ALWAYS flow through the DSL, NEVER directly to a renderer
- User drags a text box -> DSL position updates -> all renderers re-compile
- Every node tracks whether it was created by Agent, User, or Template
"""

import copy
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import structlog

from app.models.dsl_v2 import (
    BackgroundStyle,
    BackgroundType,
    ElementStyle,
    ElementType,
    FragmentAnimation,
    LayoutType,
    PresentationCore,
    PresentationDSL,
    RevealConfig,
    SlideDSL,
    SlideContentV2,
    SlideElement,
    SlidePosition,
    SlideSize,
    SlideStyle,
    SlideType,
    ThemeDSL,
)

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Lineage tracking
# ---------------------------------------------------------------------------

class LineageSource(str, Enum):
    """Who created or last modified a DSL node."""
    AGENT = "agent"
    USER = "user"
    TEMPLATE = "template"
    SYSTEM = "system"


class EditLineage:
    """Tracks origin and modification history of a DSL node."""

    __slots__ = ("node_id", "source", "agent_name", "created_at", "modified_at", "edit_count")

    def __init__(
        self,
        node_id: str,
        source: LineageSource = LineageSource.USER,
        agent_name: Optional[str] = None,
    ):
        self.node_id = node_id
        self.source = source
        self.agent_name = agent_name
        self.created_at = datetime.now(timezone.utc)
        self.modified_at = self.created_at
        self.edit_count = 0

    def record_edit(self, source: LineageSource, agent_name: Optional[str] = None) -> None:
        self.source = source
        self.agent_name = agent_name
        self.modified_at = datetime.now(timezone.utc)
        self.edit_count += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "source": self.source.value,
            "agent_name": self.agent_name,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "edit_count": self.edit_count,
        }


# ---------------------------------------------------------------------------
# Operation results
# ---------------------------------------------------------------------------

class SlideOperationResult:
    """Result of a slide-level CRUD operation."""

    __slots__ = ("success", "slide_id", "slide_index", "error", "dsl")

    def __init__(
        self,
        success: bool,
        slide_id: Optional[str] = None,
        slide_index: Optional[int] = None,
        error: Optional[str] = None,
        dsl: Optional[PresentationDSL] = None,
    ):
        self.success = success
        self.slide_id = slide_id
        self.slide_index = slide_index
        self.error = error
        self.dsl = dsl


class ElementOperationResult:
    """Result of an element-level CRUD operation."""

    __slots__ = ("success", "element_id", "slide_id", "error")

    def __init__(
        self,
        success: bool,
        element_id: Optional[str] = None,
        slide_id: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.element_id = element_id
        self.slide_id = slide_id
        self.error = error


# ---------------------------------------------------------------------------
# Editor Engine
# ---------------------------------------------------------------------------

class DSLEditorEngine:
    """
    Unified DSL Editor Engine -- single source of truth for all mutations.

    Every operation:
    1. Validates input
    2. Applies mutation to the PresentationDSL
    3. Re-indexes slides (contiguous 0..N)
    4. Records lineage
    5. Returns result with updated DSL

    Thread-safe note: This engine operates on an in-memory PresentationDSL
    object. For concurrent access, wrap calls in an asyncio.Lock or use
    the VersionManager for optimistic concurrency control.
    """

    def __init__(self, dsl: PresentationDSL):
        self._dsl = dsl
        self._lineage: Dict[str, EditLineage] = {}
        self._operation_log: List[Dict[str, Any]] = []

        # Initialise lineage for existing nodes
        for slide in self._dsl.slides:
            self._lineage[slide.id] = EditLineage(
                slide.id, LineageSource.SYSTEM, agent_name="initializer"
            )
            for elem in slide.elements:
                self._lineage[elem.id] = EditLineage(
                    elem.id, LineageSource.SYSTEM, agent_name="initializer"
                )

    # ── Properties ────────────────────────────────────────────────

    @property
    def dsl(self) -> PresentationDSL:
        return self._dsl

    @property
    def slide_count(self) -> int:
        return len(self._dsl.slides)

    @property
    def lineage(self) -> Dict[str, EditLineage]:
        return dict(self._lineage)

    @property
    def operation_log(self) -> List[Dict[str, Any]]:
        return list(self._operation_log)

    # ── Slide CRUD ────────────────────────────────────────────────

    def get_slide(self, slide_id: str) -> Optional[SlideDSL]:
        """Get a slide by ID."""
        for s in self._dsl.slides:
            if s.id == slide_id:
                return s
        return None

    def get_slide_by_index(self, index: int) -> Optional[SlideDSL]:
        """Get a slide by its 0-based index."""
        if 0 <= index < len(self._dsl.slides):
            return self._dsl.slides[index]
        return None

    def add_slide(
        self,
        slide_type: SlideType = SlideType.CUSTOM,
        layout: LayoutType = LayoutType.CENTER_FOCUS,
        content: Optional[Dict[str, Any]] = None,
        insert_at: Optional[int] = None,
        source: LineageSource = LineageSource.USER,
        agent_name: Optional[str] = None,
    ) -> SlideOperationResult:
        """Add a new slide to the presentation."""
        slide_id = f"slide_{uuid.uuid4().hex[:12]}"

        # Build content
        content_obj = SlideContentV2(**(content or {}))

        new_slide = SlideDSL(
            index=0,  # will be fixed by _reindex
            id=slide_id,
            type=slide_type,
            layout=layout,
            content=content_obj,
            style=SlideStyle(),
            elements=[],
            revealConfig=RevealConfig(),
        )

        # Insert position
        if insert_at is not None and 0 <= insert_at <= len(self._dsl.slides):
            self._dsl.slides.insert(insert_at, new_slide)
        else:
            self._dsl.slides.append(new_slide)

        self._reindex_slides()
        self._record_lineage(slide_id, source, agent_name)
        self._log_operation("add_slide", slide_id=slide_id, slide_type=slide_type.value)

        logger.info("slide_added", slide_id=slide_id, type=slide_type.value)
        return SlideOperationResult(
            success=True,
            slide_id=slide_id,
            slide_index=new_slide.index,
            dsl=self._dsl,
        )

    def remove_slide(self, slide_id: str) -> SlideOperationResult:
        """Remove a slide by ID. Presentation must keep at least 1 slide."""
        if len(self._dsl.slides) <= 1:
            return SlideOperationResult(
                success=False,
                error="Cannot remove the last slide in a presentation",
            )

        idx = self._find_slide_index(slide_id)
        if idx is None:
            return SlideOperationResult(
                success=False, error=f"Slide '{slide_id}' not found"
            )

        removed = self._dsl.slides.pop(idx)
        self._reindex_slides()

        # Clean up lineage
        self._lineage.pop(slide_id, None)
        for elem in removed.elements:
            self._lineage.pop(elem.id, None)

        self._log_operation("remove_slide", slide_id=slide_id)
        logger.info("slide_removed", slide_id=slide_id)

        return SlideOperationResult(
            success=True, slide_id=slide_id, slide_index=idx, dsl=self._dsl
        )

    def move_slide(self, slide_id: str, new_index: int) -> SlideOperationResult:
        """Move a slide to a new position in the deck."""
        old_idx = self._find_slide_index(slide_id)
        if old_idx is None:
            return SlideOperationResult(
                success=False, error=f"Slide '{slide_id}' not found"
            )

        max_idx = len(self._dsl.slides) - 1
        new_index = max(0, min(new_index, max_idx))

        if old_idx == new_index:
            return SlideOperationResult(
                success=True, slide_id=slide_id, slide_index=new_index, dsl=self._dsl
            )

        slide = self._dsl.slides.pop(old_idx)
        self._dsl.slides.insert(new_index, slide)
        self._reindex_slides()

        self._log_operation("move_slide", slide_id=slide_id, from_idx=old_idx, to_idx=new_index)
        logger.info("slide_moved", slide_id=slide_id, from_idx=old_idx, to_idx=new_index)

        return SlideOperationResult(
            success=True, slide_id=slide_id, slide_index=new_index, dsl=self._dsl
        )

    def duplicate_slide(
        self,
        slide_id: str,
        source: LineageSource = LineageSource.USER,
    ) -> SlideOperationResult:
        """Deep-copy a slide and insert it right after the original."""
        idx = self._find_slide_index(slide_id)
        if idx is None:
            return SlideOperationResult(
                success=False, error=f"Slide '{slide_id}' not found"
            )

        original = self._dsl.slides[idx]
        clone_data = original.model_dump()
        new_id = f"slide_{uuid.uuid4().hex[:12]}"
        clone_data["id"] = new_id

        # Re-ID all elements
        id_map: Dict[str, str] = {}
        for elem in clone_data.get("elements", []):
            old_eid = elem["id"]
            new_eid = f"elem_{uuid.uuid4().hex[:8]}"
            id_map[old_eid] = new_eid
            elem["id"] = new_eid

        # Update fragment references
        for frag in clone_data.get("fragments", []):
            old_ref = frag.get("elementId", "")
            if old_ref in id_map:
                frag["elementId"] = id_map[old_ref]

        clone = SlideDSL.model_validate(clone_data)
        self._dsl.slides.insert(idx + 1, clone)
        self._reindex_slides()

        self._record_lineage(new_id, source)
        for new_eid in id_map.values():
            self._record_lineage(new_eid, source)

        self._log_operation("duplicate_slide", slide_id=slide_id, new_slide_id=new_id)
        logger.info("slide_duplicated", original=slide_id, clone=new_id)

        return SlideOperationResult(
            success=True, slide_id=new_id, slide_index=idx + 1, dsl=self._dsl
        )

    def update_slide_content(
        self,
        slide_id: str,
        updates: Dict[str, Any],
        source: LineageSource = LineageSource.USER,
        agent_name: Optional[str] = None,
    ) -> SlideOperationResult:
        """Patch slide content fields (title, subtitle, bullets, etc.)."""
        slide = self.get_slide(slide_id)
        if slide is None:
            return SlideOperationResult(
                success=False, error=f"Slide '{slide_id}' not found"
            )

        # Merge updates into existing content
        current = slide.content.model_dump()
        for key, value in updates.items():
            if hasattr(slide.content, key):
                current[key] = value

        try:
            slide.content = SlideContentV2.model_validate(current)
        except Exception as e:
            return SlideOperationResult(
                success=False, error=f"Validation failed: {e}"
            )

        self._update_lineage(slide_id, source, agent_name)
        self._log_operation("update_slide_content", slide_id=slide_id, fields=list(updates.keys()))

        return SlideOperationResult(
            success=True, slide_id=slide_id, slide_index=slide.index, dsl=self._dsl
        )

    def update_slide_style(
        self,
        slide_id: str,
        style_updates: Dict[str, Any],
        source: LineageSource = LineageSource.USER,
    ) -> SlideOperationResult:
        """Update slide-level visual style (background, accent, animation)."""
        slide = self.get_slide(slide_id)
        if slide is None:
            return SlideOperationResult(
                success=False, error=f"Slide '{slide_id}' not found"
            )

        current = slide.style.model_dump()
        current.update(style_updates)

        try:
            slide.style = SlideStyle.model_validate(current)
        except Exception as e:
            return SlideOperationResult(
                success=False, error=f"Style validation failed: {e}"
            )

        self._update_lineage(slide_id, source)
        self._log_operation("update_slide_style", slide_id=slide_id)

        return SlideOperationResult(
            success=True, slide_id=slide_id, slide_index=slide.index, dsl=self._dsl
        )

    def update_slide_type(
        self,
        slide_id: str,
        new_type: SlideType,
        source: LineageSource = LineageSource.USER,
    ) -> SlideOperationResult:
        """Change a slide's semantic type."""
        slide = self.get_slide(slide_id)
        if slide is None:
            return SlideOperationResult(
                success=False, error=f"Slide '{slide_id}' not found"
            )

        slide.type = new_type
        self._update_lineage(slide_id, source)
        self._log_operation("update_slide_type", slide_id=slide_id, new_type=new_type.value)

        return SlideOperationResult(
            success=True, slide_id=slide_id, slide_index=slide.index, dsl=self._dsl
        )

    def update_speaker_notes(
        self,
        slide_id: str,
        notes: str,
        source: LineageSource = LineageSource.USER,
    ) -> SlideOperationResult:
        """Set or update speaker notes for a slide."""
        slide = self.get_slide(slide_id)
        if slide is None:
            return SlideOperationResult(
                success=False, error=f"Slide '{slide_id}' not found"
            )

        if len(notes) > 5000:
            return SlideOperationResult(
                success=False, error="Speaker notes exceed 5000 character limit"
            )

        slide.speakerNotes = notes
        self._update_lineage(slide_id, source)
        self._log_operation("update_speaker_notes", slide_id=slide_id)

        return SlideOperationResult(
            success=True, slide_id=slide_id, slide_index=slide.index, dsl=self._dsl
        )

    def update_reveal_config(
        self,
        slide_id: str,
        config_updates: Dict[str, Any],
    ) -> SlideOperationResult:
        """Update per-slide reveal.js configuration."""
        slide = self.get_slide(slide_id)
        if slide is None:
            return SlideOperationResult(
                success=False, error=f"Slide '{slide_id}' not found"
            )

        current = slide.revealConfig.model_dump()
        current.update(config_updates)

        try:
            slide.revealConfig = RevealConfig.model_validate(current)
        except Exception as e:
            return SlideOperationResult(
                success=False, error=f"RevealConfig validation failed: {e}"
            )

        self._log_operation("update_reveal_config", slide_id=slide_id)
        return SlideOperationResult(
            success=True, slide_id=slide_id, slide_index=slide.index, dsl=self._dsl
        )

    def update_custom_fields(
        self,
        slide_id: str,
        fields: Dict[str, Any],
        merge: bool = True,
    ) -> SlideOperationResult:
        """Set or merge custom fields on a slide."""
        slide = self.get_slide(slide_id)
        if slide is None:
            return SlideOperationResult(
                success=False, error=f"Slide '{slide_id}' not found"
            )

        if merge:
            slide.customFields.update(fields)
        else:
            slide.customFields = fields

        self._log_operation("update_custom_fields", slide_id=slide_id)
        return SlideOperationResult(
            success=True, slide_id=slide_id, slide_index=slide.index, dsl=self._dsl
        )

    def set_section(
        self,
        slide_id: str,
        section: Optional[str],
    ) -> SlideOperationResult:
        """Assign a slide to a logical section (opening, problem, solution, etc.)."""
        slide = self.get_slide(slide_id)
        if slide is None:
            return SlideOperationResult(
                success=False, error=f"Slide '{slide_id}' not found"
            )

        slide.section = section
        self._log_operation("set_section", slide_id=slide_id, section=section)

        return SlideOperationResult(
            success=True, slide_id=slide_id, slide_index=slide.index, dsl=self._dsl
        )

    # ── Element CRUD ──────────────────────────────────────────────

    def add_element(
        self,
        slide_id: str,
        element_type: ElementType,
        content: str = "",
        position: Optional[Dict[str, float]] = None,
        size: Optional[Dict[str, float]] = None,
        style: Optional[Dict[str, Any]] = None,
        source: LineageSource = LineageSource.USER,
    ) -> ElementOperationResult:
        """Add a new element to a slide."""
        slide = self.get_slide(slide_id)
        if slide is None:
            return ElementOperationResult(
                success=False, error=f"Slide '{slide_id}' not found"
            )

        if len(slide.elements) >= 50:
            return ElementOperationResult(
                success=False, error="Maximum 50 elements per slide"
            )

        elem_id = f"elem_{uuid.uuid4().hex[:8]}"

        elem = SlideElement(
            id=elem_id,
            type=element_type,
            content=content,
            position=SlidePosition(**(position or {})),
            size=SlideSize(**(size or {})),
            style=ElementStyle(**(style or {})),
        )
        slide.elements.append(elem)

        self._record_lineage(elem_id, source)
        self._log_operation("add_element", slide_id=slide_id, element_id=elem_id)

        return ElementOperationResult(
            success=True, element_id=elem_id, slide_id=slide_id
        )

    def remove_element(
        self, slide_id: str, element_id: str
    ) -> ElementOperationResult:
        """Remove an element from a slide, cleaning up fragment references."""
        slide = self.get_slide(slide_id)
        if slide is None:
            return ElementOperationResult(
                success=False, error=f"Slide '{slide_id}' not found"
            )

        idx = None
        for i, e in enumerate(slide.elements):
            if e.id == element_id:
                idx = i
                break

        if idx is None:
            return ElementOperationResult(
                success=False,
                error=f"Element '{element_id}' not found in slide '{slide_id}'",
            )

        slide.elements.pop(idx)

        # Clean up any fragment animations referencing this element
        slide.fragments = [
            f for f in slide.fragments if f.elementId != element_id
        ]

        self._lineage.pop(element_id, None)
        self._log_operation("remove_element", slide_id=slide_id, element_id=element_id)

        return ElementOperationResult(
            success=True, element_id=element_id, slide_id=slide_id
        )

    def update_element(
        self,
        slide_id: str,
        element_id: str,
        updates: Dict[str, Any],
        source: LineageSource = LineageSource.USER,
    ) -> ElementOperationResult:
        """Patch element properties (content, position, size, style)."""
        slide = self.get_slide(slide_id)
        if slide is None:
            return ElementOperationResult(
                success=False, error=f"Slide '{slide_id}' not found"
            )

        elem = None
        for e in slide.elements:
            if e.id == element_id:
                elem = e
                break

        if elem is None:
            return ElementOperationResult(
                success=False,
                error=f"Element '{element_id}' not found in slide '{slide_id}'",
            )

        # Apply updates to appropriate sub-fields
        if "content" in updates:
            elem.content = updates["content"]
        if "position" in updates:
            elem.position = SlidePosition.model_validate(updates["position"])
        if "size" in updates:
            elem.size = SlideSize.model_validate(updates["size"])
        if "style" in updates:
            current_style = elem.style.model_dump()
            current_style.update(updates["style"])
            elem.style = ElementStyle.model_validate(current_style)
        if "alt_text" in updates:
            elem.alt_text = updates["alt_text"]
        if "data" in updates:
            elem.data = updates["data"]

        self._update_lineage(element_id, source)
        self._log_operation("update_element", slide_id=slide_id, element_id=element_id)

        return ElementOperationResult(
            success=True, element_id=element_id, slide_id=slide_id
        )

    def move_element(
        self,
        slide_id: str,
        element_id: str,
        x: float,
        y: float,
    ) -> ElementOperationResult:
        """Move an element to a new normalised position."""
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            return ElementOperationResult(
                success=False, error="Position must be in [0.0, 1.0] range"
            )

        return self.update_element(
            slide_id, element_id, {"position": {"x": x, "y": y}}
        )

    def resize_element(
        self,
        slide_id: str,
        element_id: str,
        width: float,
        height: float,
    ) -> ElementOperationResult:
        """Resize an element (normalised 0-1)."""
        if not (0.0 < width <= 1.0 and 0.0 < height <= 1.0):
            return ElementOperationResult(
                success=False, error="Size must be in (0.0, 1.0] range"
            )

        return self.update_element(
            slide_id, element_id, {"size": {"width": width, "height": height}}
        )

    # ── Fragment (animation) operations ───────────────────────────

    def add_fragment(
        self,
        slide_id: str,
        element_id: str,
        order: int,
        animation: str = "fade-in",
    ) -> SlideOperationResult:
        """Add a fragment animation to a slide element."""
        slide = self.get_slide(slide_id)
        if slide is None:
            return SlideOperationResult(
                success=False, error=f"Slide '{slide_id}' not found"
            )

        # Verify element exists
        if not any(e.id == element_id for e in slide.elements):
            return SlideOperationResult(
                success=False,
                error=f"Element '{element_id}' not found in slide",
            )

        # Check for duplicate
        for f in slide.fragments:
            if f.elementId == element_id:
                return SlideOperationResult(
                    success=False,
                    error=f"Fragment already exists for element '{element_id}'",
                )

        from app.models.dsl_v2 import AnimationType
        try:
            anim = AnimationType(animation)
        except ValueError:
            anim = AnimationType.FADE_IN

        frag = FragmentAnimation(
            elementId=element_id,
            order=order,
            animation=anim,
        )
        slide.fragments.append(frag)

        self._log_operation("add_fragment", slide_id=slide_id, element_id=element_id)
        return SlideOperationResult(
            success=True, slide_id=slide_id, slide_index=slide.index, dsl=self._dsl
        )

    def remove_fragment(
        self, slide_id: str, element_id: str
    ) -> SlideOperationResult:
        """Remove a fragment animation from a slide."""
        slide = self.get_slide(slide_id)
        if slide is None:
            return SlideOperationResult(
                success=False, error=f"Slide '{slide_id}' not found"
            )

        before = len(slide.fragments)
        slide.fragments = [
            f for f in slide.fragments if f.elementId != element_id
        ]

        if len(slide.fragments) == before:
            return SlideOperationResult(
                success=False,
                error=f"No fragment found for element '{element_id}'",
            )

        self._log_operation("remove_fragment", slide_id=slide_id, element_id=element_id)
        return SlideOperationResult(
            success=True, slide_id=slide_id, slide_index=slide.index, dsl=self._dsl
        )

    # ── Presentation-level operations ─────────────────────────────

    def update_presentation(
        self, updates: Dict[str, Any]
    ) -> SlideOperationResult:
        """Update top-level presentation properties (title, archetype, etc.)."""
        current = self._dsl.presentation.model_dump()
        current.update(updates)

        try:
            self._dsl.presentation = PresentationCore.model_validate(current)
        except Exception as e:
            return SlideOperationResult(
                success=False, error=f"Presentation update failed: {e}"
            )

        self._log_operation("update_presentation", fields=list(updates.keys()))
        return SlideOperationResult(success=True, dsl=self._dsl)

    def update_theme(self, theme_updates: Dict[str, Any]) -> SlideOperationResult:
        """Update the presentation theme."""
        current = self._dsl.presentation.theme.model_dump()
        current.update(theme_updates)

        try:
            self._dsl.presentation.theme = ThemeDSL.model_validate(current)
        except Exception as e:
            return SlideOperationResult(
                success=False, error=f"Theme update failed: {e}"
            )

        self._log_operation("update_theme", fields=list(theme_updates.keys()))
        return SlideOperationResult(success=True, dsl=self._dsl)

    def set_renderers(self, renderers: List[str]) -> SlideOperationResult:
        """Set target renderers for the presentation."""
        valid = {"reveal.js", "react", "html", "pptx"}
        for r in renderers:
            if r not in valid:
                return SlideOperationResult(
                    success=False,
                    error=f"Invalid renderer '{r}'. Valid: {sorted(valid)}",
                )

        self._dsl.presentation.renderers = renderers
        self._log_operation("set_renderers", renderers=renderers)
        return SlideOperationResult(success=True, dsl=self._dsl)

    # ── Batch operations ──────────────────────────────────────────

    def reorder_slides(self, slide_ids: List[str]) -> SlideOperationResult:
        """Reorder all slides to match the given ID sequence."""
        if len(slide_ids) != len(self._dsl.slides):
            return SlideOperationResult(
                success=False,
                error=f"Expected {len(self._dsl.slides)} slide IDs, got {len(slide_ids)}",
            )

        existing_ids = {s.id for s in self._dsl.slides}
        provided_ids = set(slide_ids)
        if existing_ids != provided_ids:
            return SlideOperationResult(
                success=False,
                error="Provided slide IDs don't match existing slides",
            )

        id_to_slide = {s.id: s for s in self._dsl.slides}
        self._dsl.slides = [id_to_slide[sid] for sid in slide_ids]
        self._reindex_slides()

        self._log_operation("reorder_slides", order=slide_ids)
        return SlideOperationResult(success=True, dsl=self._dsl)

    def bulk_update_slides(
        self,
        updates: List[Dict[str, Any]],
        source: LineageSource = LineageSource.AGENT,
        agent_name: Optional[str] = None,
    ) -> List[SlideOperationResult]:
        """Apply multiple slide content updates in one call."""
        results = []
        for u in updates:
            sid = u.get("slide_id")
            if not sid:
                results.append(SlideOperationResult(success=False, error="Missing slide_id"))
                continue
            content_updates = u.get("content", {})
            result = self.update_slide_content(sid, content_updates, source, agent_name)
            results.append(result)
        return results

    # ── Query helpers ─────────────────────────────────────────────

    def get_slides_by_section(self, section: str) -> List[SlideDSL]:
        """Get all slides in a given section."""
        return [s for s in self._dsl.slides if s.section == section]

    def get_slides_by_type(self, slide_type: SlideType) -> List[SlideDSL]:
        """Get all slides of a given type."""
        return [s for s in self._dsl.slides if s.type == slide_type]

    def get_all_sections(self) -> List[str]:
        """Get unique ordered section names."""
        seen = set()
        sections = []
        for s in self._dsl.slides:
            if s.section and s.section not in seen:
                seen.add(s.section)
                sections.append(s.section)
        return sections

    def get_element(self, slide_id: str, element_id: str) -> Optional[SlideElement]:
        """Get a specific element from a slide."""
        slide = self.get_slide(slide_id)
        if slide is None:
            return None
        for e in slide.elements:
            if e.id == element_id:
                return e
        return None

    def find_slides_with_element_type(self, elem_type: ElementType) -> List[SlideDSL]:
        """Get all slides that contain at least one element of the given type."""
        return [
            s for s in self._dsl.slides
            if any(e.type == elem_type for e in s.elements)
        ]

    def get_three_js_slides(self) -> List[SlideDSL]:
        """Get all slides that contain Three.js 3D scenes."""
        return [s for s in self._dsl.slides if s.threeScene is not None]

    # ── Serialization ─────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the full editor state (DSL + lineage) to a dict."""
        return {
            "dsl": self._dsl.model_dump(mode="json"),
            "lineage": {k: v.to_dict() for k, v in self._lineage.items()},
            "operation_count": len(self._operation_log),
        }

    # ── Internal helpers ──────────────────────────────────────────

    def _find_slide_index(self, slide_id: str) -> Optional[int]:
        for i, s in enumerate(self._dsl.slides):
            if s.id == slide_id:
                return i
        return None

    def _reindex_slides(self) -> None:
        """Ensure slide indexes are contiguous 0..N-1."""
        for i, s in enumerate(self._dsl.slides):
            s.index = i

    def _record_lineage(
        self,
        node_id: str,
        source: LineageSource,
        agent_name: Optional[str] = None,
    ) -> None:
        self._lineage[node_id] = EditLineage(node_id, source, agent_name)

    def _update_lineage(
        self,
        node_id: str,
        source: LineageSource,
        agent_name: Optional[str] = None,
    ) -> None:
        if node_id in self._lineage:
            self._lineage[node_id].record_edit(source, agent_name)
        else:
            self._record_lineage(node_id, source, agent_name)

    def _log_operation(self, operation: str, **kwargs: Any) -> None:
        self._operation_log.append({
            "operation": operation,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        })
