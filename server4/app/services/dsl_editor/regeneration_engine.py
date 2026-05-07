"""
Regeneration Engine -- Per-slide, per-section, and full-deck re-generation.

Three levels (from V7 Plan Section 21):
    Level 1: Per-Slide   -- regenerate a single slide preserving context
    Level 2: Per-Section -- regenerate all slides in a logical section
    Level 3: Full Deck   -- fresh generation with optional preservation

Context preservation: the re-generation agent receives the current deck
state + user feedback so the output is coherent with surrounding slides.
"""

import copy
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

from app.models.dsl_v2 import (
    LayoutType,
    PresentationDSL,
    SlideDSL,
    SlideContentV2,
    SlideStyle,
    SlideType,
)

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Enums and models
# ---------------------------------------------------------------------------

class RegenerationLevel(str, Enum):
    """Scope of regeneration."""
    SLIDE = "slide"         # Single slide
    SECTION = "section"     # All slides in a section
    DECK = "deck"           # Entire presentation


class RegenerationRequest:
    """
    A request to regenerate part of a presentation.

    Carry enough context for the regenerating agent to produce
    coherent output that fits the surrounding slides.
    """

    def __init__(
        self,
        presentation_id: str,
        level: RegenerationLevel,
        target_slide_id: Optional[str] = None,
        target_section: Optional[str] = None,
        user_feedback: str = "",
        preserve_theme: bool = True,
        preserve_layout: bool = True,
        preserve_images: bool = False,
    ):
        self.id = f"regen_{uuid.uuid4().hex[:12]}"
        self.presentation_id = presentation_id
        self.level = level
        self.target_slide_id = target_slide_id
        self.target_section = target_section
        self.user_feedback = user_feedback
        self.preserve_theme = preserve_theme
        self.preserve_layout = preserve_layout
        self.preserve_images = preserve_images
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "presentation_id": self.presentation_id,
            "level": self.level.value,
            "target_slide_id": self.target_slide_id,
            "target_section": self.target_section,
            "user_feedback": self.user_feedback,
            "preserve_theme": self.preserve_theme,
            "preserve_layout": self.preserve_layout,
            "preserve_images": self.preserve_images,
            "created_at": self.created_at.isoformat(),
        }


class RegenerationResult:
    """Result of a regeneration operation."""

    __slots__ = (
        "success", "request_id", "level", "slides_affected",
        "error", "dsl", "generation_time_ms",
    )

    def __init__(
        self,
        success: bool,
        request_id: str = "",
        level: RegenerationLevel = RegenerationLevel.SLIDE,
        slides_affected: int = 0,
        error: Optional[str] = None,
        dsl: Optional[PresentationDSL] = None,
        generation_time_ms: int = 0,
    ):
        self.success = success
        self.request_id = request_id
        self.level = level
        self.slides_affected = slides_affected
        self.error = error
        self.dsl = dsl
        self.generation_time_ms = generation_time_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "request_id": self.request_id,
            "level": self.level.value,
            "slides_affected": self.slides_affected,
            "error": self.error,
            "generation_time_ms": self.generation_time_ms,
        }


# ---------------------------------------------------------------------------
# Regeneration Engine
# ---------------------------------------------------------------------------

class RegenerationEngine:
    """
    Coordinates slide/section/deck regeneration.

    The engine does NOT call LLMs directly. Instead, it:
    1. Builds a context window from surrounding slides
    2. Creates a regeneration brief (what to regenerate + constraints)
    3. Applies the new content to the DSL
    4. Returns the mutated DSL

    The actual LLM-based generation is delegated to the caller
    (orchestrator or agent pipeline).
    """

    # Maximum surrounding slides to include as context
    CONTEXT_WINDOW = 2

    def __init__(self, dsl: PresentationDSL):
        self._dsl = dsl

    @property
    def dsl(self) -> PresentationDSL:
        return self._dsl

    # ── Level 1: Per-slide regeneration ───────────────────────────

    def build_slide_context(
        self, slide_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Build context for regenerating a single slide.

        Includes:
        - The slide's current data
        - Surrounding slides (before/after) for narrative coherence
        - Presentation-level metadata (topic, archetype, theme)
        - Section siblings
        """
        idx = self._find_index(slide_id)
        if idx is None:
            return None

        slide = self._dsl.slides[idx]

        # Surrounding slides
        before = []
        for i in range(max(0, idx - self.CONTEXT_WINDOW), idx):
            s = self._dsl.slides[i]
            before.append({
                "index": s.index,
                "type": s.type.value,
                "title": s.content.title,
                "layout": s.layout.value,
            })

        after = []
        for i in range(idx + 1, min(len(self._dsl.slides), idx + 1 + self.CONTEXT_WINDOW)):
            s = self._dsl.slides[i]
            after.append({
                "index": s.index,
                "type": s.type.value,
                "title": s.content.title,
                "layout": s.layout.value,
            })

        # Section siblings
        section_siblings = []
        if slide.section:
            for s in self._dsl.slides:
                if s.section == slide.section and s.id != slide_id:
                    section_siblings.append({
                        "index": s.index,
                        "type": s.type.value,
                        "title": s.content.title,
                    })

        return {
            "target_slide": slide.model_dump(mode="json"),
            "slides_before": before,
            "slides_after": after,
            "section_siblings": section_siblings,
            "presentation": {
                "title": self._dsl.presentation.title,
                "archetype": self._dsl.presentation.archetype,
                "theme_id": self._dsl.presentation.theme.id,
                "total_slides": len(self._dsl.slides),
            },
        }

    def apply_slide_regeneration(
        self,
        slide_id: str,
        new_content: Dict[str, Any],
        request: RegenerationRequest,
    ) -> RegenerationResult:
        """
        Apply regenerated content to a single slide.

        Respects preservation flags (layout, theme, images).
        """
        idx = self._find_index(slide_id)
        if idx is None:
            return RegenerationResult(
                success=False,
                request_id=request.id,
                error=f"Slide '{slide_id}' not found",
            )

        slide = self._dsl.slides[idx]

        # Preserve layout if requested
        original_layout = slide.layout
        original_style = slide.style.model_dump()
        original_image_url = slide.content.image_url

        # Apply new content
        try:
            merged = slide.content.model_dump()
            merged.update(new_content)
            slide.content = SlideContentV2.model_validate(merged)
        except Exception as e:
            return RegenerationResult(
                success=False,
                request_id=request.id,
                error=f"Content validation failed: {e}",
            )

        # Restore preserved fields
        if request.preserve_layout:
            slide.layout = original_layout
        if request.preserve_theme:
            slide.style = SlideStyle.model_validate(original_style)
        if request.preserve_images and original_image_url:
            slide.content.image_url = original_image_url

        logger.info(
            "slide_regenerated",
            slide_id=slide_id,
            request_id=request.id,
        )

        return RegenerationResult(
            success=True,
            request_id=request.id,
            level=RegenerationLevel.SLIDE,
            slides_affected=1,
            dsl=self._dsl,
        )

    # ── Level 2: Per-section regeneration ─────────────────────────

    def build_section_context(
        self, section: str
    ) -> Optional[Dict[str, Any]]:
        """Build context for regenerating all slides in a section."""
        section_slides = [s for s in self._dsl.slides if s.section == section]
        if not section_slides:
            return None

        # Non-section slides for context
        other_sections = {}
        for s in self._dsl.slides:
            if s.section and s.section != section:
                if s.section not in other_sections:
                    other_sections[s.section] = []
                other_sections[s.section].append({
                    "index": s.index,
                    "type": s.type.value,
                    "title": s.content.title,
                })

        return {
            "target_section": section,
            "section_slides": [
                s.model_dump(mode="json") for s in section_slides
            ],
            "section_slide_count": len(section_slides),
            "other_sections": other_sections,
            "presentation": {
                "title": self._dsl.presentation.title,
                "archetype": self._dsl.presentation.archetype,
                "theme_id": self._dsl.presentation.theme.id,
                "total_slides": len(self._dsl.slides),
            },
        }

    def apply_section_regeneration(
        self,
        section: str,
        new_slides_data: List[Dict[str, Any]],
        request: RegenerationRequest,
    ) -> RegenerationResult:
        """
        Replace all slides in a section with regenerated versions.

        Preserves the section's position in the deck but allows
        the number of slides to change.
        """
        # Find section boundaries
        section_indices = [
            i for i, s in enumerate(self._dsl.slides)
            if s.section == section
        ]
        if not section_indices:
            return RegenerationResult(
                success=False,
                request_id=request.id,
                error=f"Section '{section}' not found",
            )

        first_idx = section_indices[0]

        # Remove old section slides (in reverse to preserve indices)
        for idx in reversed(section_indices):
            self._dsl.slides.pop(idx)

        # Build new slides
        new_slides = []
        for i, slide_data in enumerate(new_slides_data):
            slide_data.setdefault("id", f"slide_{uuid.uuid4().hex[:12]}")
            slide_data.setdefault("index", 0)
            slide_data.setdefault("section", section)
            slide_data.setdefault("type", "custom")
            slide_data.setdefault("layout", "center-focus")
            if "content" not in slide_data:
                slide_data["content"] = {}

            try:
                new_slide = SlideDSL.model_validate(slide_data)
                new_slides.append(new_slide)
            except Exception as e:
                logger.warning("section_regen_slide_invalid", error=str(e))
                continue

        # Insert at original position
        for i, ns in enumerate(new_slides):
            self._dsl.slides.insert(first_idx + i, ns)

        # Reindex
        self._reindex()

        return RegenerationResult(
            success=True,
            request_id=request.id,
            level=RegenerationLevel.SECTION,
            slides_affected=len(new_slides),
            dsl=self._dsl,
        )

    # ── Level 3: Full deck regeneration ───────────────────────────

    def build_deck_context(self) -> Dict[str, Any]:
        """Build context for full deck regeneration."""
        return {
            "current_deck": self._dsl.model_dump(mode="json"),
            "slide_count": len(self._dsl.slides),
            "sections": self._get_section_summary(),
            "presentation": {
                "title": self._dsl.presentation.title,
                "archetype": self._dsl.presentation.archetype,
                "theme_id": self._dsl.presentation.theme.id,
            },
        }

    def apply_deck_regeneration(
        self,
        new_dsl_data: Dict[str, Any],
        request: RegenerationRequest,
    ) -> RegenerationResult:
        """
        Replace the entire deck with a regenerated version.

        Can optionally preserve theme from the original.
        """
        try:
            new_dsl = PresentationDSL.model_validate(new_dsl_data)
        except Exception as e:
            return RegenerationResult(
                success=False,
                request_id=request.id,
                error=f"DSL validation failed: {e}",
            )

        # Preserve theme if requested
        if request.preserve_theme:
            new_dsl.presentation.theme = copy.deepcopy(self._dsl.presentation.theme)

        # Keep presentation ID consistent
        new_dsl.presentation.id = self._dsl.presentation.id

        # Increment version
        old_version = self._dsl.presentation.metadata.version
        new_dsl.presentation.metadata.version = old_version + 1

        self._dsl = new_dsl

        return RegenerationResult(
            success=True,
            request_id=request.id,
            level=RegenerationLevel.DECK,
            slides_affected=len(new_dsl.slides),
            dsl=self._dsl,
        )

    # ── Feedback integration ──────────────────────────────────────

    def build_feedback_prompt(
        self,
        request: RegenerationRequest,
        context: Dict[str, Any],
    ) -> str:
        """
        Build a structured prompt incorporating user feedback
        for the regeneration agent.
        """
        parts = []

        if request.level == RegenerationLevel.SLIDE:
            parts.append("Regenerate this single slide.")
            target = context.get("target_slide", {})
            parts.append(f"Current type: {target.get('type', 'unknown')}")
            parts.append(f"Current title: {target.get('content', {}).get('title', '')}")

        elif request.level == RegenerationLevel.SECTION:
            parts.append(f"Regenerate all slides in section: {request.target_section}")
            parts.append(f"Current slide count in section: {context.get('section_slide_count', 0)}")

        elif request.level == RegenerationLevel.DECK:
            parts.append("Regenerate the entire presentation.")
            parts.append(f"Current slide count: {context.get('slide_count', 0)}")

        if request.user_feedback:
            parts.append(f"\nUser feedback: {request.user_feedback}")

        if request.preserve_layout:
            parts.append("CONSTRAINT: Preserve existing layout types.")
        if request.preserve_theme:
            parts.append("CONSTRAINT: Preserve existing theme and visual style.")

        pres = context.get("presentation", {})
        parts.append(f"\nPresentation: {pres.get('title', 'Untitled')}")
        parts.append(f"Archetype: {pres.get('archetype', 'general')}")

        return "\n".join(parts)

    # ── Dry-run ───────────────────────────────────────────────────

    def preview_regeneration(
        self, request: RegenerationRequest
    ) -> Dict[str, Any]:
        """
        Preview what will be regenerated without executing.
        Useful for showing the user which slides will change.
        """
        if request.level == RegenerationLevel.SLIDE:
            idx = self._find_index(request.target_slide_id or "")
            if idx is None:
                return {"error": "Slide not found", "slides_affected": 0}
            slide = self._dsl.slides[idx]
            return {
                "level": "slide",
                "slides_affected": 1,
                "affected_slides": [{
                    "id": slide.id,
                    "index": slide.index,
                    "type": slide.type.value,
                    "title": slide.content.title,
                }],
            }

        elif request.level == RegenerationLevel.SECTION:
            section = request.target_section or ""
            section_slides = [
                s for s in self._dsl.slides if s.section == section
            ]
            return {
                "level": "section",
                "section": section,
                "slides_affected": len(section_slides),
                "affected_slides": [{
                    "id": s.id,
                    "index": s.index,
                    "type": s.type.value,
                    "title": s.content.title,
                } for s in section_slides],
            }

        else:
            return {
                "level": "deck",
                "slides_affected": len(self._dsl.slides),
                "affected_slides": [{
                    "id": s.id,
                    "index": s.index,
                    "type": s.type.value,
                    "title": s.content.title,
                } for s in self._dsl.slides],
            }

    # ── Internal helpers ──────────────────────────────────────────

    def _find_index(self, slide_id: str) -> Optional[int]:
        for i, s in enumerate(self._dsl.slides):
            if s.id == slide_id:
                return i
        return None

    def _reindex(self) -> None:
        for i, s in enumerate(self._dsl.slides):
            s.index = i

    def _get_section_summary(self) -> Dict[str, int]:
        """Count slides per section."""
        counts: Dict[str, int] = {}
        for s in self._dsl.slides:
            sec = s.section or "no_section"
            counts[sec] = counts.get(sec, 0) + 1
        return counts
