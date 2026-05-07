"""
Phase 9 Verification Test -- Unified DSL Editor.

Tests:
  1. EditorEngine: module imports
  2. EditorEngine: class instantiation
  3. EditorEngine: slide_count property
  4. EditorEngine: get_slide by ID
  5. EditorEngine: get_slide_by_index
  6. EditorEngine: add_slide default
  7. EditorEngine: add_slide at position
  8. EditorEngine: add_slide reindexes
  9. EditorEngine: remove_slide success
 10. EditorEngine: remove_slide last slide fails
 11. EditorEngine: remove_slide not found
 12. EditorEngine: move_slide forward
 13. EditorEngine: move_slide backward
 14. EditorEngine: duplicate_slide
 15. EditorEngine: duplicate_slide re-IDs elements
 16. EditorEngine: update_slide_content
 17. EditorEngine: update_slide_style
 18. EditorEngine: update_slide_type
 19. EditorEngine: update_speaker_notes
 20. EditorEngine: update_reveal_config
 21. EditorEngine: update_custom_fields merge
 22. EditorEngine: set_section
 23. EditorEngine: add_element
 24. EditorEngine: add_element max 50
 25. EditorEngine: remove_element
 26. EditorEngine: remove_element cleans fragments
 27. EditorEngine: update_element content
 28. EditorEngine: move_element
 29. EditorEngine: resize_element
 30. EditorEngine: add_fragment
 31. EditorEngine: remove_fragment
 32. EditorEngine: reorder_slides
 33. EditorEngine: lineage tracking
 34. EditorEngine: operation_log grows
 35. HITLManager: module imports
 36. HITLManager: instantiation
 37. HITLManager: create_checkpoint pending
 38. HITLManager: approve checkpoint
 39. HITLManager: reject checkpoint
 40. HITLManager: revise resets to pending
 41. HITLManager: fast_mode auto-approves
 42. HITLManager: Gate 3 auto-approves
 43. HITLManager: is_gate_cleared
 44. HITLManager: get_pipeline_status
 45. HITLManager: get_pending_checkpoints
 46. HITLManager: expire_stale
 47. HITLManager: clear_presentation
 48. VersionManager: module imports
 49. VersionManager: instantiation
 50. VersionManager: create_snapshot
 51. VersionManager: create_snapshot dedup
 52. VersionManager: rollback
 53. VersionManager: diff additions
 54. VersionManager: diff removals
 55. VersionManager: diff content changes
 56. VersionManager: list_snapshots pagination
 57. VersionManager: DeckSnapshot checksum
 58. VersionManager: max snapshots rolling
 59. RegenerationEngine: module imports
 60. RegenerationEngine: instantiation
 61. RegenerationEngine: build_slide_context
 62. RegenerationEngine: build_section_context
 63. RegenerationEngine: build_deck_context
 64. RegenerationEngine: build_feedback_prompt
 65. RegenerationEngine: preview_regeneration slide
 66. RegenerationEngine: preview_regeneration section
 67. RegenerationEngine: preview_regeneration deck
 68. RegenerationEngine: apply_slide_regeneration
 69. RegenerationEngine: apply_section_regeneration
 70. RegenerationEngine: apply_deck_regeneration
 71. LayoutManager: module imports
 72. LayoutManager: instantiation
 73. LayoutManager: change_slide_layout
 74. LayoutManager: change_slide_layout reflow
 75. LayoutManager: change_slide_layout not found
 76. LayoutManager: apply_deck_layout
 77. LayoutManager: suggest_layout returns ranked
 78. LayoutManager: suggest_layout timeline data
 79. LayoutManager: suggest_layout team data
 80. LayoutManager: get_layout_geometry
 81. LayoutManager: get_available_layouts
 82. DSLValidator: module imports
 83. DSLValidator: instantiation
 84. DSLValidator: validate returns report
 85. DSLValidator: too few slides
 86. DSLValidator: title word limit
 87. DSLValidator: bullet count limit
 88. DSLValidator: body text limit
 89. DSLValidator: missing title slide
 90. DSLValidator: empty slide detected
 91. DSLValidator: no competition anti-pitfall
 92. DSLValidator: layout coherence timeline
 93. DSLValidator: layout coherence quote
 94. DSLValidator: accessibility alt text
 95. DSLValidator: validate_slide single
 96. EditorRoutes: module imports
 97. EditorRoutes: router prefix
 98. EditorRoutes: OperationResponse schema
 99. EditorRoutes: EditorStateResponse schema
100. Integration: main.py includes editor_v2

Run: python test_phase9.py
"""

import sys
import os
import time
import traceback

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
        print(f"Phase 9 Tests: {self.passed}/{total} passed")
        if self.errors:
            print("\nFailures:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0


results = TestResult()


# ===================================================================
# Helper: build a minimal valid PresentationDSL for testing
# ===================================================================

def _make_dsl(num_slides=3, include_elements=False):
    """Build a minimal valid PresentationDSL for testing."""
    from app.models.dsl_v2 import (
        PresentationDSL, PresentationCore, SlideDSL,
        SlideContentV2, SlideStyle, RevealConfig,
        SlideType, LayoutType, SlideElement, ElementType,
        SlidePosition, SlideSize, ElementStyle,
    )

    slides = []
    types = [SlideType.TITLE_SLIDE, SlideType.PROBLEM_SLIDE, SlideType.SOLUTION_SLIDE,
             SlideType.MARKET_SLIDE, SlideType.TEAM_SLIDE, SlideType.FINANCIAL_SLIDE,
             SlideType.CLOSING_SLIDE, SlideType.CUSTOM]

    for i in range(num_slides):
        elements = []
        if include_elements:
            elements.append(SlideElement(
                id=f"elem_{i}_0",
                type=ElementType.TEXT,
                content=f"Element text {i}",
                position=SlidePosition(x=0.1, y=0.1),
                size=SlideSize(width=0.5, height=0.3),
                style=ElementStyle(),
            ))

        slide = SlideDSL(
            index=i,
            id=f"slide_{i}",
            type=types[i % len(types)],
            layout=LayoutType.CENTER_FOCUS,
            section=f"section_{i // 2}",
            content=SlideContentV2(
                title=f"Slide {i} Title",
                bullets=[f"Bullet {j}" for j in range(3)],
            ),
            style=SlideStyle(),
            elements=elements,
            revealConfig=RevealConfig(),
        )
        slides.append(slide)

    return PresentationDSL(
        version="2.0",
        presentation=PresentationCore(
            id="test-pres-001",
            title="Test Presentation",
            renderers=["reveal.js"],
        ),
        slides=slides,
    )


# ===================================================================
# 1-34: EditorEngine
# ===================================================================

print("\n--- EditorEngine ---")

# 1
try:
    from app.services.dsl_editor.editor_engine import (
        DSLEditorEngine, SlideOperationResult, ElementOperationResult,
        EditLineage, LineageSource,
    )
    results.ok("1. EditorEngine: module imports")
except Exception as e:
    results.fail("1. EditorEngine: module imports", str(e))

# 2
try:
    dsl = _make_dsl(3, include_elements=True)
    engine = DSLEditorEngine(dsl)
    assert engine.dsl is dsl
    results.ok("2. EditorEngine: class instantiation")
except Exception as e:
    results.fail("2. EditorEngine: class instantiation", str(e))

# 3
try:
    dsl = _make_dsl(5)
    engine = DSLEditorEngine(dsl)
    assert engine.slide_count == 5
    results.ok("3. EditorEngine: slide_count property")
except Exception as e:
    results.fail("3. EditorEngine: slide_count property", str(e))

# 4
try:
    dsl = _make_dsl(3)
    engine = DSLEditorEngine(dsl)
    s = engine.get_slide("slide_1")
    assert s is not None
    assert s.id == "slide_1"
    assert engine.get_slide("nonexistent") is None
    results.ok("4. EditorEngine: get_slide by ID")
except Exception as e:
    results.fail("4. EditorEngine: get_slide by ID", str(e))

# 5
try:
    dsl = _make_dsl(3)
    engine = DSLEditorEngine(dsl)
    s = engine.get_slide_by_index(0)
    assert s is not None
    assert s.index == 0
    assert engine.get_slide_by_index(99) is None
    results.ok("5. EditorEngine: get_slide_by_index")
except Exception as e:
    results.fail("5. EditorEngine: get_slide_by_index", str(e))

# 6
try:
    from app.models.dsl_v2 import SlideType, LayoutType
    dsl = _make_dsl(3)
    engine = DSLEditorEngine(dsl)
    r = engine.add_slide(slide_type=SlideType.CUSTOM, layout=LayoutType.BULLETS)
    assert r.success
    assert r.slide_id is not None
    assert engine.slide_count == 4
    results.ok("6. EditorEngine: add_slide default")
except Exception as e:
    results.fail("6. EditorEngine: add_slide default", str(e))

# 7
try:
    dsl = _make_dsl(3)
    engine = DSLEditorEngine(dsl)
    r = engine.add_slide(slide_type=SlideType.CUSTOM, insert_at=1)
    assert r.success
    assert engine.dsl.slides[1].id == r.slide_id
    results.ok("7. EditorEngine: add_slide at position")
except Exception as e:
    results.fail("7. EditorEngine: add_slide at position", str(e))

# 8
try:
    dsl = _make_dsl(3)
    engine = DSLEditorEngine(dsl)
    engine.add_slide()
    indexes = [s.index for s in engine.dsl.slides]
    assert indexes == [0, 1, 2, 3], f"Expected [0,1,2,3], got {indexes}"
    results.ok("8. EditorEngine: add_slide reindexes")
except Exception as e:
    results.fail("8. EditorEngine: add_slide reindexes", str(e))

# 9
try:
    dsl = _make_dsl(3)
    engine = DSLEditorEngine(dsl)
    r = engine.remove_slide("slide_1")
    assert r.success
    assert engine.slide_count == 2
    indexes = [s.index for s in engine.dsl.slides]
    assert indexes == [0, 1]
    results.ok("9. EditorEngine: remove_slide success")
except Exception as e:
    results.fail("9. EditorEngine: remove_slide success", str(e))

# 10
try:
    dsl = _make_dsl(1)
    engine = DSLEditorEngine(dsl)
    r = engine.remove_slide("slide_0")
    assert not r.success
    assert "last slide" in r.error.lower()
    results.ok("10. EditorEngine: remove_slide last slide fails")
except Exception as e:
    results.fail("10. EditorEngine: remove_slide last slide fails", str(e))

# 11
try:
    dsl = _make_dsl(3)
    engine = DSLEditorEngine(dsl)
    r = engine.remove_slide("nonexistent")
    assert not r.success
    results.ok("11. EditorEngine: remove_slide not found")
except Exception as e:
    results.fail("11. EditorEngine: remove_slide not found", str(e))

# 12
try:
    dsl = _make_dsl(4)
    engine = DSLEditorEngine(dsl)
    r = engine.move_slide("slide_0", 2)
    assert r.success
    assert engine.dsl.slides[2].id == "slide_0"
    indexes = [s.index for s in engine.dsl.slides]
    assert indexes == [0, 1, 2, 3]
    results.ok("12. EditorEngine: move_slide forward")
except Exception as e:
    results.fail("12. EditorEngine: move_slide forward", str(e))

# 13
try:
    dsl = _make_dsl(4)
    engine = DSLEditorEngine(dsl)
    r = engine.move_slide("slide_3", 0)
    assert r.success
    assert engine.dsl.slides[0].id == "slide_3"
    results.ok("13. EditorEngine: move_slide backward")
except Exception as e:
    results.fail("13. EditorEngine: move_slide backward", str(e))

# 14
try:
    dsl = _make_dsl(3)
    engine = DSLEditorEngine(dsl)
    r = engine.duplicate_slide("slide_1")
    assert r.success
    assert engine.slide_count == 4
    assert r.slide_id != "slide_1"
    orig_idx = next(i for i, s in enumerate(engine.dsl.slides) if s.id == "slide_1")
    clone_idx = next(i for i, s in enumerate(engine.dsl.slides) if s.id == r.slide_id)
    assert clone_idx == orig_idx + 1
    results.ok("14. EditorEngine: duplicate_slide")
except Exception as e:
    results.fail("14. EditorEngine: duplicate_slide", str(e))

# 15
try:
    dsl = _make_dsl(3, include_elements=True)
    engine = DSLEditorEngine(dsl)
    orig = engine.get_slide("slide_1")
    orig_elem_ids = {e.id for e in orig.elements}
    r = engine.duplicate_slide("slide_1")
    clone = engine.get_slide(r.slide_id)
    clone_elem_ids = {e.id for e in clone.elements}
    assert orig_elem_ids.isdisjoint(clone_elem_ids), "Element IDs should be re-generated"
    results.ok("15. EditorEngine: duplicate_slide re-IDs elements")
except Exception as e:
    results.fail("15. EditorEngine: duplicate_slide re-IDs elements", str(e))

# 16
try:
    dsl = _make_dsl(3)
    engine = DSLEditorEngine(dsl)
    r = engine.update_slide_content("slide_0", {"title": "Updated Title", "bullets": ["a", "b"]})
    assert r.success
    s = engine.get_slide("slide_0")
    assert s.content.title == "Updated Title"
    assert s.content.bullets == ["a", "b"]
    results.ok("16. EditorEngine: update_slide_content")
except Exception as e:
    results.fail("16. EditorEngine: update_slide_content", str(e))

# 17
try:
    dsl = _make_dsl(3)
    engine = DSLEditorEngine(dsl)
    r = engine.update_slide_style("slide_0", {"accentColor": "#ff0000"})
    assert r.success
    s = engine.get_slide("slide_0")
    assert s.style.accentColor == "#ff0000"
    results.ok("17. EditorEngine: update_slide_style")
except Exception as e:
    results.fail("17. EditorEngine: update_slide_style", str(e))

# 18
try:
    dsl = _make_dsl(3)
    engine = DSLEditorEngine(dsl)
    r = engine.update_slide_type("slide_0", SlideType.MARKET_SLIDE)
    assert r.success
    assert engine.get_slide("slide_0").type == SlideType.MARKET_SLIDE
    results.ok("18. EditorEngine: update_slide_type")
except Exception as e:
    results.fail("18. EditorEngine: update_slide_type", str(e))

# 19
try:
    dsl = _make_dsl(3)
    engine = DSLEditorEngine(dsl)
    r = engine.update_speaker_notes("slide_0", "Talk about this slide")
    assert r.success
    assert engine.get_slide("slide_0").speakerNotes == "Talk about this slide"
    results.ok("19. EditorEngine: update_speaker_notes")
except Exception as e:
    results.fail("19. EditorEngine: update_speaker_notes", str(e))

# 20
try:
    dsl = _make_dsl(3)
    engine = DSLEditorEngine(dsl)
    r = engine.update_reveal_config("slide_0", {"autoAnimate": True})
    assert r.success
    assert engine.get_slide("slide_0").revealConfig.autoAnimate is True
    results.ok("20. EditorEngine: update_reveal_config")
except Exception as e:
    results.fail("20. EditorEngine: update_reveal_config", str(e))

# 21
try:
    dsl = _make_dsl(3)
    engine = DSLEditorEngine(dsl)
    r = engine.update_custom_fields("slide_0", {"key1": "val1"})
    assert r.success
    assert engine.get_slide("slide_0").customFields["key1"] == "val1"
    r2 = engine.update_custom_fields("slide_0", {"key2": "val2"})
    assert "key1" in engine.get_slide("slide_0").customFields
    results.ok("21. EditorEngine: update_custom_fields merge")
except Exception as e:
    results.fail("21. EditorEngine: update_custom_fields merge", str(e))

# 22
try:
    dsl = _make_dsl(3)
    engine = DSLEditorEngine(dsl)
    r = engine.set_section("slide_0", "opening")
    assert r.success
    assert engine.get_slide("slide_0").section == "opening"
    results.ok("22. EditorEngine: set_section")
except Exception as e:
    results.fail("22. EditorEngine: set_section", str(e))

# 23
try:
    from app.models.dsl_v2 import ElementType
    dsl = _make_dsl(3)
    engine = DSLEditorEngine(dsl)
    r = engine.add_element("slide_0", ElementType.TEXT, content="Hello")
    assert r.success
    assert r.element_id is not None
    s = engine.get_slide("slide_0")
    assert any(e.id == r.element_id for e in s.elements)
    results.ok("23. EditorEngine: add_element")
except Exception as e:
    results.fail("23. EditorEngine: add_element", str(e))

# 24
try:
    dsl = _make_dsl(3, include_elements=True)
    engine = DSLEditorEngine(dsl)
    for i in range(49):
        engine.add_element("slide_0", ElementType.TEXT, content=f"e{i}")
    r = engine.add_element("slide_0", ElementType.TEXT, content="overflow")
    assert not r.success
    assert "50" in r.error
    results.ok("24. EditorEngine: add_element max 50")
except Exception as e:
    results.fail("24. EditorEngine: add_element max 50", str(e))

# 25
try:
    dsl = _make_dsl(3, include_elements=True)
    engine = DSLEditorEngine(dsl)
    r = engine.remove_element("slide_0", "elem_0_0")
    assert r.success
    s = engine.get_slide("slide_0")
    assert not any(e.id == "elem_0_0" for e in s.elements)
    results.ok("25. EditorEngine: remove_element")
except Exception as e:
    results.fail("25. EditorEngine: remove_element", str(e))

# 26
try:
    dsl = _make_dsl(3, include_elements=True)
    engine = DSLEditorEngine(dsl)
    engine.add_fragment("slide_0", "elem_0_0", order=0)
    assert len(engine.get_slide("slide_0").fragments) == 1
    engine.remove_element("slide_0", "elem_0_0")
    assert len(engine.get_slide("slide_0").fragments) == 0
    results.ok("26. EditorEngine: remove_element cleans fragments")
except Exception as e:
    results.fail("26. EditorEngine: remove_element cleans fragments", str(e))

# 27
try:
    dsl = _make_dsl(3, include_elements=True)
    engine = DSLEditorEngine(dsl)
    r = engine.update_element("slide_0", "elem_0_0", {"content": "Updated!"})
    assert r.success
    s = engine.get_slide("slide_0")
    elem = next(e for e in s.elements if e.id == "elem_0_0")
    assert elem.content == "Updated!"
    results.ok("27. EditorEngine: update_element content")
except Exception as e:
    results.fail("27. EditorEngine: update_element content", str(e))

# 28
try:
    dsl = _make_dsl(3, include_elements=True)
    engine = DSLEditorEngine(dsl)
    r = engine.move_element("slide_0", "elem_0_0", 0.5, 0.5)
    assert r.success
    elem = next(e for e in engine.get_slide("slide_0").elements if e.id == "elem_0_0")
    assert elem.position.x == 0.5
    assert elem.position.y == 0.5
    results.ok("28. EditorEngine: move_element")
except Exception as e:
    results.fail("28. EditorEngine: move_element", str(e))

# 29
try:
    dsl = _make_dsl(3, include_elements=True)
    engine = DSLEditorEngine(dsl)
    r = engine.resize_element("slide_0", "elem_0_0", 0.8, 0.6)
    assert r.success
    elem = next(e for e in engine.get_slide("slide_0").elements if e.id == "elem_0_0")
    assert elem.size.width == 0.8
    assert elem.size.height == 0.6
    results.ok("29. EditorEngine: resize_element")
except Exception as e:
    results.fail("29. EditorEngine: resize_element", str(e))

# 30
try:
    dsl = _make_dsl(3, include_elements=True)
    engine = DSLEditorEngine(dsl)
    r = engine.add_fragment("slide_0", "elem_0_0", order=1, animation="slide-up")
    assert r.success
    frags = engine.get_slide("slide_0").fragments
    assert len(frags) == 1
    assert frags[0].elementId == "elem_0_0"
    results.ok("30. EditorEngine: add_fragment")
except Exception as e:
    results.fail("30. EditorEngine: add_fragment", str(e))

# 31
try:
    dsl = _make_dsl(3, include_elements=True)
    engine = DSLEditorEngine(dsl)
    engine.add_fragment("slide_0", "elem_0_0", order=0)
    r = engine.remove_fragment("slide_0", "elem_0_0")
    assert r.success
    assert len(engine.get_slide("slide_0").fragments) == 0
    results.ok("31. EditorEngine: remove_fragment")
except Exception as e:
    results.fail("31. EditorEngine: remove_fragment", str(e))

# 32
try:
    dsl = _make_dsl(4)
    engine = DSLEditorEngine(dsl)
    r = engine.reorder_slides(["slide_3", "slide_2", "slide_1", "slide_0"])
    assert r.success
    ids = [s.id for s in engine.dsl.slides]
    assert ids == ["slide_3", "slide_2", "slide_1", "slide_0"]
    indexes = [s.index for s in engine.dsl.slides]
    assert indexes == [0, 1, 2, 3]
    results.ok("32. EditorEngine: reorder_slides")
except Exception as e:
    results.fail("32. EditorEngine: reorder_slides", str(e))

# 33
try:
    dsl = _make_dsl(3, include_elements=True)
    engine = DSLEditorEngine(dsl)
    lineage = engine.lineage
    assert "slide_0" in lineage
    assert "elem_0_0" in lineage
    assert lineage["slide_0"].source == LineageSource.SYSTEM
    results.ok("33. EditorEngine: lineage tracking")
except Exception as e:
    results.fail("33. EditorEngine: lineage tracking", str(e))

# 34
try:
    dsl = _make_dsl(3)
    engine = DSLEditorEngine(dsl)
    before = len(engine.operation_log)
    engine.add_slide()
    after = len(engine.operation_log)
    assert after > before
    results.ok("34. EditorEngine: operation_log grows")
except Exception as e:
    results.fail("34. EditorEngine: operation_log grows", str(e))


# ===================================================================
# 35-47: HITLManager
# ===================================================================

print("\n--- HITLManager ---")

# 35
try:
    from app.services.dsl_editor.hitl_manager import (
        HITLManager, HITLGate, HITLCheckpoint, HITLDecision, CheckpointStatus,
    )
    results.ok("35. HITLManager: module imports")
except Exception as e:
    results.fail("35. HITLManager: module imports", str(e))

# 36
try:
    hm = HITLManager()
    assert hm is not None
    assert hm.fast_mode is False
    results.ok("36. HITLManager: instantiation")
except Exception as e:
    results.fail("36. HITLManager: instantiation", str(e))

# 37: create_checkpoint(gate, presentation_id, agent_output) -> PENDING
try:
    hm = HITLManager()
    cp = hm.create_checkpoint(
        gate=HITLGate.NARRATIVE,
        presentation_id="pres1",
        agent_output={"summary": "test"},
    )
    assert cp.status == CheckpointStatus.PENDING
    assert cp.gate == HITLGate.NARRATIVE
    assert cp.presentation_id == "pres1"
    results.ok("37. HITLManager: create_checkpoint pending")
except Exception as e:
    results.fail("37. HITLManager: create_checkpoint pending", str(e))

# 38: approve uses checkpoint_id
try:
    hm = HITLManager()
    cp = hm.create_checkpoint(
        gate=HITLGate.NARRATIVE,
        presentation_id="pres1",
        agent_output={"data": "test"},
    )
    ok = hm.approve(cp.id)
    assert ok
    assert hm.is_gate_cleared(HITLGate.NARRATIVE, "pres1")
    results.ok("38. HITLManager: approve checkpoint")
except Exception as e:
    results.fail("38. HITLManager: approve checkpoint", str(e))

# 39: reject uses checkpoint_id
try:
    hm = HITLManager()
    cp = hm.create_checkpoint(
        gate=HITLGate.NARRATIVE,
        presentation_id="pres1",
        agent_output={"data": "test"},
    )
    ok = hm.reject(cp.id, feedback="Needs more detail")
    assert ok
    assert not hm.is_gate_cleared(HITLGate.NARRATIVE, "pres1")
    results.ok("39. HITLManager: reject checkpoint")
except Exception as e:
    results.fail("39. HITLManager: reject checkpoint", str(e))

# 40: revise resets to PENDING
try:
    hm = HITLManager()
    cp = hm.create_checkpoint(
        gate=HITLGate.NARRATIVE,
        presentation_id="pres1",
        agent_output={"data": "test"},
    )
    hm.reject(cp.id, feedback="Fix it")
    ok = hm.revise(cp.id, {"data": "revised"})
    assert ok
    cp_updated = hm.get_checkpoint(cp.id)
    assert cp_updated.status == CheckpointStatus.PENDING
    assert cp_updated.revision_count == 1
    results.ok("40. HITLManager: revise resets to pending")
except Exception as e:
    results.fail("40. HITLManager: revise resets to pending", str(e))

# 41: fast_mode at constructor level auto-skips all gates
try:
    hm = HITLManager(fast_mode=True)
    cp = hm.create_checkpoint(
        gate=HITLGate.NARRATIVE,
        presentation_id="pres1",
        agent_output={"data": "test"},
    )
    assert cp.status == CheckpointStatus.SKIPPED
    assert hm.is_gate_cleared(HITLGate.NARRATIVE, "pres1")
    results.ok("41. HITLManager: fast_mode auto-approves")
except Exception as e:
    results.fail("41. HITLManager: fast_mode auto-approves", str(e))

# 42: Gate 3 (FULL_RENDER) auto-skips regardless of fast_mode
try:
    hm = HITLManager()
    cp = hm.create_checkpoint(
        gate=HITLGate.FULL_RENDER,
        presentation_id="pres1",
        agent_output={"data": "test"},
    )
    assert cp.status == CheckpointStatus.SKIPPED
    assert cp.is_resolved
    results.ok("42. HITLManager: Gate 3 auto-approves")
except Exception as e:
    results.fail("42. HITLManager: Gate 3 auto-approves", str(e))

# 43: is_gate_cleared lifecycle: not_started -> pending -> approved
try:
    hm = HITLManager()
    assert not hm.is_gate_cleared(HITLGate.NARRATIVE, "pres1")
    cp = hm.create_checkpoint(
        gate=HITLGate.NARRATIVE,
        presentation_id="pres1",
        agent_output={"data": "test"},
    )
    assert not hm.is_gate_cleared(HITLGate.NARRATIVE, "pres1")
    hm.approve(cp.id)
    assert hm.is_gate_cleared(HITLGate.NARRATIVE, "pres1")
    results.ok("43. HITLManager: is_gate_cleared")
except Exception as e:
    results.fail("43. HITLManager: is_gate_cleared", str(e))

# 44: get_pipeline_status returns gates dict
try:
    hm = HITLManager()
    hm.create_checkpoint(
        gate=HITLGate.NARRATIVE,
        presentation_id="pres1",
        agent_output={"n": 1},
    )
    hm.create_checkpoint(
        gate=HITLGate.RESEARCH_DESIGN,
        presentation_id="pres1",
        agent_output={"n": 2},
    )
    status = hm.get_pipeline_status("pres1")
    assert "gates" in status
    assert HITLGate.NARRATIVE.value in status["gates"]
    assert HITLGate.RESEARCH_DESIGN.value in status["gates"]
    results.ok("44. HITLManager: get_pipeline_status")
except Exception as e:
    results.fail("44. HITLManager: get_pipeline_status", str(e))

# 45: get_pending_checkpoints
try:
    hm = HITLManager()
    hm.create_checkpoint(
        gate=HITLGate.NARRATIVE,
        presentation_id="pres1",
        agent_output={"n": 1},
    )
    hm.create_checkpoint(
        gate=HITLGate.RESEARCH_DESIGN,
        presentation_id="pres1",
        agent_output={"n": 2},
    )
    pending = hm.get_pending_checkpoints("pres1")
    assert len(pending) == 2
    results.ok("45. HITLManager: get_pending_checkpoints")
except Exception as e:
    results.fail("45. HITLManager: get_pending_checkpoints", str(e))

# 46: expire_stale
try:
    hm = HITLManager()
    cp = hm.create_checkpoint(
        gate=HITLGate.NARRATIVE,
        presentation_id="pres1",
        agent_output={"n": 1},
    )
    from datetime import datetime, timezone, timedelta
    cp.created_at = datetime.now(timezone.utc) - timedelta(seconds=9999)
    expired = hm.expire_stale()
    assert expired >= 1
    assert cp.status == CheckpointStatus.EXPIRED
    results.ok("46. HITLManager: expire_stale")
except Exception as e:
    results.fail("46. HITLManager: expire_stale", str(e))

# 47: clear_presentation removes all checkpoints
try:
    hm = HITLManager()
    hm.create_checkpoint(
        gate=HITLGate.NARRATIVE,
        presentation_id="pres1",
        agent_output={"n": 1},
    )
    removed = hm.clear_presentation("pres1")
    assert removed >= 1
    assert len(hm.get_pending_checkpoints("pres1")) == 0
    results.ok("47. HITLManager: clear_presentation")
except Exception as e:
    results.fail("47. HITLManager: clear_presentation", str(e))


# ===================================================================
# 48-58: VersionManager
# ===================================================================

print("\n--- VersionManager ---")

# 48
try:
    from app.services.dsl_editor.version_manager import (
        VersionManager, DeckSnapshot, VersionDiff, DiffEntry, DiffAction,
    )
    results.ok("48. VersionManager: module imports")
except Exception as e:
    results.fail("48. VersionManager: module imports", str(e))

# 49: Constructor takes max_snapshots, no dsl
try:
    vm = VersionManager()
    assert vm is not None
    assert vm.current_version == 0
    assert vm.snapshot_count == 0
    results.ok("49. VersionManager: instantiation")
except Exception as e:
    results.fail("49. VersionManager: instantiation", str(e))

# 50: create_snapshot(dsl, description) returns DeckSnapshot
try:
    dsl = _make_dsl(3)
    vm = VersionManager()
    snap = vm.create_snapshot(dsl, description="initial")
    assert snap.version == 1
    assert snap.description == "initial"
    assert snap.checksum is not None
    assert len(snap.checksum) == 16
    results.ok("50. VersionManager: create_snapshot")
except Exception as e:
    results.fail("50. VersionManager: create_snapshot", str(e))

# 51: Dedup -- identical DSL skips snapshot
try:
    dsl = _make_dsl(3)
    vm = VersionManager()
    s1 = vm.create_snapshot(dsl, description="v1")
    s2 = vm.create_snapshot(dsl, description="v2")
    assert s1.checksum == s2.checksum
    assert vm.snapshot_count == 1
    results.ok("51. VersionManager: create_snapshot dedup")
except Exception as e:
    results.fail("51. VersionManager: create_snapshot dedup", str(e))

# 52: Rollback restores DSL from version
try:
    dsl = _make_dsl(3)
    vm = VersionManager()
    vm.create_snapshot(dsl, description="v1")
    dsl.slides[0].content.title = "Modified Title"
    vm.create_snapshot(dsl, description="v2")
    restored = vm.rollback(1)
    assert restored is not None
    assert restored.slides[0].content.title == "Slide 0 Title"
    results.ok("52. VersionManager: rollback")
except Exception as e:
    results.fail("52. VersionManager: rollback", str(e))

# 53: Diff detects slide additions
try:
    dsl = _make_dsl(3)
    vm = VersionManager()
    vm.create_snapshot(dsl, description="v1")
    eng = DSLEditorEngine(dsl)
    eng.add_slide(content={"title": "New Slide"})
    vm.create_snapshot(dsl, description="v2")
    diff = vm.diff(1, 2)
    assert diff is not None
    assert diff.change_count > 0
    results.ok("53. VersionManager: diff additions")
except Exception as e:
    results.fail("53. VersionManager: diff additions", str(e))

# 54: Diff detects slide removals
try:
    dsl = _make_dsl(4)
    vm = VersionManager()
    vm.create_snapshot(dsl, description="v1")
    eng = DSLEditorEngine(dsl)
    eng.remove_slide("slide_2")
    vm.create_snapshot(dsl, description="v2")
    diff = vm.diff(1, 2)
    assert diff is not None
    has_removal = any(e.action == DiffAction.REMOVED for e in diff.entries)
    assert has_removal
    results.ok("54. VersionManager: diff removals")
except Exception as e:
    results.fail("54. VersionManager: diff removals", str(e))

# 55: Diff detects content modifications
try:
    dsl = _make_dsl(3)
    vm = VersionManager()
    vm.create_snapshot(dsl, description="v1")
    dsl.slides[0].content.title = "Changed!"
    vm.create_snapshot(dsl, description="v2")
    diff = vm.diff(1, 2)
    assert diff is not None
    has_mod = any(e.action == DiffAction.MODIFIED for e in diff.entries)
    assert has_mod
    results.ok("55. VersionManager: diff content changes")
except Exception as e:
    results.fail("55. VersionManager: diff content changes", str(e))

# 56: list_snapshots with limit
try:
    dsl = _make_dsl(3)
    vm = VersionManager()
    for i in range(10):
        dsl.slides[0].content.title = f"Rev {i}"
        vm.create_snapshot(dsl, description=f"v{i}")
    all_snaps = vm.list_snapshots(limit=5)
    assert len(all_snaps) <= 5
    results.ok("56. VersionManager: list_snapshots pagination")
except Exception as e:
    results.fail("56. VersionManager: list_snapshots pagination", str(e))

# 57: Different DSLs produce different checksums
try:
    dsl = _make_dsl(3)
    vm = VersionManager()
    snap = vm.create_snapshot(dsl, description="test")
    dsl2 = _make_dsl(5)
    vm2 = VersionManager()
    snap2 = vm2.create_snapshot(dsl2, description="test")
    assert snap.checksum != snap2.checksum
    results.ok("57. VersionManager: DeckSnapshot checksum")
except Exception as e:
    results.fail("57. VersionManager: DeckSnapshot checksum", str(e))

# 58: Rolling window evicts old snapshots
try:
    dsl = _make_dsl(3)
    vm = VersionManager(max_snapshots=5)
    for i in range(10):
        dsl.slides[0].content.title = f"Iteration {i}"
        vm.create_snapshot(dsl, description=f"snap_{i}")
    assert vm.snapshot_count <= 5
    results.ok("58. VersionManager: max snapshots rolling")
except Exception as e:
    results.fail("58. VersionManager: max snapshots rolling", str(e))


# ===================================================================
# 59-70: RegenerationEngine
# ===================================================================

print("\n--- RegenerationEngine ---")

# 59
try:
    from app.services.dsl_editor.regeneration_engine import (
        RegenerationEngine, RegenerationLevel, RegenerationRequest, RegenerationResult,
    )
    results.ok("59. RegenerationEngine: module imports")
except Exception as e:
    results.fail("59. RegenerationEngine: module imports", str(e))

# 60
try:
    dsl = _make_dsl(5)
    regen = RegenerationEngine(dsl)
    assert regen.dsl is dsl
    results.ok("60. RegenerationEngine: instantiation")
except Exception as e:
    results.fail("60. RegenerationEngine: instantiation", str(e))

# 61: build_slide_context returns target_slide, slides_before, slides_after, presentation
try:
    dsl = _make_dsl(5)
    regen = RegenerationEngine(dsl)
    ctx = regen.build_slide_context("slide_2")
    assert ctx is not None
    assert "target_slide" in ctx
    assert "slides_before" in ctx
    assert "slides_after" in ctx
    assert "presentation" in ctx
    results.ok("61. RegenerationEngine: build_slide_context")
except Exception as e:
    results.fail("61. RegenerationEngine: build_slide_context", str(e))

# 62: build_section_context returns target_section, section_slides
try:
    dsl = _make_dsl(6)
    regen = RegenerationEngine(dsl)
    ctx = regen.build_section_context("section_0")
    assert ctx is not None
    assert "target_section" in ctx
    assert "section_slides" in ctx
    assert ctx["target_section"] == "section_0"
    results.ok("62. RegenerationEngine: build_section_context")
except Exception as e:
    results.fail("62. RegenerationEngine: build_section_context", str(e))

# 63: build_deck_context returns current_deck, slide_count, presentation
try:
    dsl = _make_dsl(5)
    regen = RegenerationEngine(dsl)
    ctx = regen.build_deck_context()
    assert "current_deck" in ctx
    assert "slide_count" in ctx
    assert "presentation" in ctx
    assert ctx["slide_count"] == 5
    results.ok("63. RegenerationEngine: build_deck_context")
except Exception as e:
    results.fail("63. RegenerationEngine: build_deck_context", str(e))

# 64: build_feedback_prompt(request, context) -> str
try:
    dsl = _make_dsl(5)
    regen = RegenerationEngine(dsl)
    req = RegenerationRequest(
        presentation_id="test-pres",
        level=RegenerationLevel.SLIDE,
        target_slide_id="slide_2",
        user_feedback="Make it more compelling",
    )
    ctx = regen.build_slide_context("slide_2")
    prompt = regen.build_feedback_prompt(req, ctx)
    assert "compelling" in prompt.lower()
    results.ok("64. RegenerationEngine: build_feedback_prompt")
except Exception as e:
    results.fail("64. RegenerationEngine: build_feedback_prompt", str(e))

# 65: preview_regeneration for single slide
try:
    dsl = _make_dsl(5)
    regen = RegenerationEngine(dsl)
    req = RegenerationRequest(
        presentation_id="test-pres",
        level=RegenerationLevel.SLIDE,
        target_slide_id="slide_2",
        user_feedback="More data",
    )
    preview = regen.preview_regeneration(req)
    assert "affected_slides" in preview
    assert preview["slides_affected"] == 1
    results.ok("65. RegenerationEngine: preview_regeneration slide")
except Exception as e:
    results.fail("65. RegenerationEngine: preview_regeneration slide", str(e))

# 66: preview_regeneration for section
try:
    dsl = _make_dsl(6)
    regen = RegenerationEngine(dsl)
    req = RegenerationRequest(
        presentation_id="test-pres",
        level=RegenerationLevel.SECTION,
        target_section="section_0",
        user_feedback="Refresh",
    )
    preview = regen.preview_regeneration(req)
    assert "affected_slides" in preview
    assert len(preview["affected_slides"]) > 0
    results.ok("66. RegenerationEngine: preview_regeneration section")
except Exception as e:
    results.fail("66. RegenerationEngine: preview_regeneration section", str(e))

# 67: preview_regeneration for full deck
try:
    dsl = _make_dsl(5)
    regen = RegenerationEngine(dsl)
    req = RegenerationRequest(
        presentation_id="test-pres",
        level=RegenerationLevel.DECK,
        user_feedback="Complete overhaul",
    )
    preview = regen.preview_regeneration(req)
    assert "affected_slides" in preview
    assert len(preview["affected_slides"]) == 5
    results.ok("67. RegenerationEngine: preview_regeneration deck")
except Exception as e:
    results.fail("67. RegenerationEngine: preview_regeneration deck", str(e))

# 68: apply_slide_regeneration(slide_id, new_content_dict, request)
try:
    dsl = _make_dsl(5)
    regen = RegenerationEngine(dsl)
    req = RegenerationRequest(
        presentation_id="test-pres",
        level=RegenerationLevel.SLIDE,
        target_slide_id="slide_2",
        preserve_layout=True,
    )
    result = regen.apply_slide_regeneration(
        "slide_2",
        {"title": "Regenerated Slide", "bullets": ["New point 1"]},
        req,
    )
    assert result.success
    assert result.slides_affected >= 1
    assert regen.dsl.slides[2].content.title == "Regenerated Slide"
    results.ok("68. RegenerationEngine: apply_slide_regeneration")
except Exception as e:
    results.fail("68. RegenerationEngine: apply_slide_regeneration", str(e))

# 69: apply_section_regeneration(section, new_slides_data_list, request)
try:
    dsl = _make_dsl(6)
    regen = RegenerationEngine(dsl)
    req = RegenerationRequest(
        presentation_id="test-pres",
        level=RegenerationLevel.SECTION,
        target_section="section_0",
    )
    new_slides_data = [
        {"content": {"title": "Section Regen 1"}, "type": "custom", "layout": "center-focus"},
        {"content": {"title": "Section Regen 2"}, "type": "custom", "layout": "center-focus"},
    ]
    result = regen.apply_section_regeneration("section_0", new_slides_data, req)
    assert result.success
    assert result.slides_affected >= 1
    results.ok("69. RegenerationEngine: apply_section_regeneration")
except Exception as e:
    results.fail("69. RegenerationEngine: apply_section_regeneration", str(e))

# 70: apply_deck_regeneration(new_dsl_data_dict, request)
try:
    dsl = _make_dsl(5)
    regen = RegenerationEngine(dsl)
    new_dsl = _make_dsl(3)
    req = RegenerationRequest(
        presentation_id="test-pres",
        level=RegenerationLevel.DECK,
        preserve_theme=True,
    )
    result = regen.apply_deck_regeneration(
        new_dsl.model_dump(mode="json"),
        req,
    )
    assert result.success
    assert result.slides_affected >= 1
    results.ok("70. RegenerationEngine: apply_deck_regeneration")
except Exception as e:
    results.fail("70. RegenerationEngine: apply_deck_regeneration", str(e))


# ===================================================================
# 71-81: LayoutManager
# ===================================================================

print("\n--- LayoutManager ---")

# 71
try:
    from app.services.dsl_editor.layout_manager import (
        LayoutManager, LayoutSuggestion, ContentReflowResult, LAYOUT_GEOMETRY,
    )
    results.ok("71. LayoutManager: module imports")
except Exception as e:
    results.fail("71. LayoutManager: module imports", str(e))

# 72
try:
    dsl = _make_dsl(3)
    lm = LayoutManager(dsl)
    assert lm.dsl is dsl
    results.ok("72. LayoutManager: instantiation")
except Exception as e:
    results.fail("72. LayoutManager: instantiation", str(e))

# 73
try:
    dsl = _make_dsl(3)
    lm = LayoutManager(dsl)
    r = lm.change_slide_layout("slide_0", LayoutType.SPLIT_SCREEN, reflow=False)
    assert r.success
    assert dsl.slides[0].layout == LayoutType.SPLIT_SCREEN
    results.ok("73. LayoutManager: change_slide_layout")
except Exception as e:
    results.fail("73. LayoutManager: change_slide_layout", str(e))

# 74
try:
    dsl = _make_dsl(3, include_elements=True)
    lm = LayoutManager(dsl)
    r = lm.change_slide_layout("slide_0", LayoutType.SPLIT_SCREEN, reflow=True)
    assert r.success
    assert r.elements_repositioned >= 0
    results.ok("74. LayoutManager: change_slide_layout reflow")
except Exception as e:
    results.fail("74. LayoutManager: change_slide_layout reflow", str(e))

# 75
try:
    dsl = _make_dsl(3)
    lm = LayoutManager(dsl)
    r = lm.change_slide_layout("nonexistent", LayoutType.BULLETS)
    assert not r.success
    assert r.error is not None
    results.ok("75. LayoutManager: change_slide_layout not found")
except Exception as e:
    results.fail("75. LayoutManager: change_slide_layout not found", str(e))

# 76
try:
    dsl = _make_dsl(5)
    lm = LayoutManager(dsl)
    result = lm.apply_deck_layout(LayoutType.BULLETS)
    assert result["slides_affected"] > 0
    for s in dsl.slides:
        if s.type not in (SlideType.TITLE_SLIDE, SlideType.CLOSING_SLIDE):
            assert s.layout == LayoutType.BULLETS
    results.ok("76. LayoutManager: apply_deck_layout")
except Exception as e:
    results.fail("76. LayoutManager: apply_deck_layout", str(e))

# 77
try:
    dsl = _make_dsl(3)
    lm = LayoutManager(dsl)
    suggestions = lm.suggest_layout("slide_0")
    assert len(suggestions) > 0
    assert all(isinstance(s, LayoutSuggestion) for s in suggestions)
    for i in range(len(suggestions) - 1):
        assert suggestions[i].confidence >= suggestions[i + 1].confidence
    results.ok("77. LayoutManager: suggest_layout returns ranked")
except Exception as e:
    results.fail("77. LayoutManager: suggest_layout returns ranked", str(e))

# 78
try:
    from app.models.dsl_v2 import TimelineItem
    dsl = _make_dsl(3)
    dsl.slides[1].content.timeline_items = [
        TimelineItem(date="2024-Q1", title="Launch"),
        TimelineItem(date="2024-Q2", title="Growth"),
    ]
    lm = LayoutManager(dsl)
    sug = lm.suggest_layout("slide_1")
    timeline_sug = [s for s in sug if s.layout == LayoutType.TIMELINE]
    assert len(timeline_sug) > 0
    assert timeline_sug[0].confidence >= 0.9
    results.ok("78. LayoutManager: suggest_layout timeline data")
except Exception as e:
    results.fail("78. LayoutManager: suggest_layout timeline data", str(e))

# 79
try:
    from app.models.dsl_v2 import TeamMember
    dsl = _make_dsl(3)
    dsl.slides[1].content.team_members = [
        TeamMember(name="Alice", role="CEO"),
        TeamMember(name="Bob", role="CTO"),
    ]
    lm = LayoutManager(dsl)
    sug = lm.suggest_layout("slide_1")
    team_sug = [s for s in sug if s.layout == LayoutType.TEAM_GRID]
    assert len(team_sug) > 0
    assert team_sug[0].confidence >= 0.9
    results.ok("79. LayoutManager: suggest_layout team data")
except Exception as e:
    results.fail("79. LayoutManager: suggest_layout team data", str(e))

# 80
try:
    dsl = _make_dsl(3)
    lm = LayoutManager(dsl)
    geo = lm.get_layout_geometry(LayoutType.SPLIT_SCREEN)
    assert "title" in geo
    assert "body" in geo
    assert "visual" in geo
    results.ok("80. LayoutManager: get_layout_geometry")
except Exception as e:
    results.fail("80. LayoutManager: get_layout_geometry", str(e))

# 81
try:
    dsl = _make_dsl(3)
    lm = LayoutManager(dsl)
    layouts = lm.get_available_layouts()
    assert len(layouts) >= 10
    assert all("id" in l and "regions" in l for l in layouts)
    results.ok("81. LayoutManager: get_available_layouts")
except Exception as e:
    results.fail("81. LayoutManager: get_available_layouts", str(e))


# ===================================================================
# 82-95: DSLValidator
# ===================================================================

print("\n--- DSLValidator ---")

# 82
try:
    from app.services.dsl_editor.dsl_validator import (
        DSLValidator, ValidationReport, ValidationIssue, IssueSeverity,
    )
    results.ok("82. DSLValidator: module imports")
except Exception as e:
    results.fail("82. DSLValidator: module imports", str(e))

# 83
try:
    dsl = _make_dsl(8)
    v = DSLValidator(dsl)
    assert v.dsl is dsl
    results.ok("83. DSLValidator: instantiation")
except Exception as e:
    results.fail("83. DSLValidator: instantiation", str(e))

# 84
try:
    dsl = _make_dsl(8)
    v = DSLValidator(dsl)
    report = v.validate()
    assert isinstance(report, ValidationReport)
    assert hasattr(report, "passed")
    assert hasattr(report, "score")
    assert hasattr(report, "issues")
    results.ok("84. DSLValidator: validate returns report")
except Exception as e:
    results.fail("84. DSLValidator: validate returns report", str(e))

# 85
try:
    dsl = _make_dsl(3)
    v = DSLValidator(dsl)
    report = v.validate()
    has_few = any("too few" in i.message.lower() for i in report.issues)
    assert has_few, "Should detect too few slides"
    results.ok("85. DSLValidator: too few slides")
except Exception as e:
    results.fail("85. DSLValidator: too few slides", str(e))

# 86
try:
    dsl = _make_dsl(8)
    dsl.slides[1].content.title = "This is a very long title that exceeds the maximum word limit easily"
    v = DSLValidator(dsl)
    report = v.validate()
    has_title_issue = any("title" in i.message.lower() and "words" in i.message.lower() for i in report.issues)
    assert has_title_issue
    results.ok("86. DSLValidator: title word limit")
except Exception as e:
    results.fail("86. DSLValidator: title word limit", str(e))

# 87
try:
    dsl = _make_dsl(8)
    dsl.slides[1].content.bullets = [f"Bullet {i}" for i in range(8)]
    v = DSLValidator(dsl)
    report = v.validate()
    has_bullet_issue = any("bullets" in i.message.lower() for i in report.issues)
    assert has_bullet_issue
    results.ok("87. DSLValidator: bullet count limit")
except Exception as e:
    results.fail("87. DSLValidator: bullet count limit", str(e))

# 88
try:
    dsl = _make_dsl(8)
    dsl.slides[1].content.body_text = " ".join(["word"] * 80)
    v = DSLValidator(dsl)
    report = v.validate()
    has_body_issue = any("body text" in i.message.lower() for i in report.issues)
    assert has_body_issue
    results.ok("88. DSLValidator: body text limit")
except Exception as e:
    results.fail("88. DSLValidator: body text limit", str(e))

# 89
try:
    from app.models.dsl_v2 import SlideContentV2
    dsl = _make_dsl(8)
    for s in dsl.slides:
        if s.type == SlideType.TITLE_SLIDE:
            s.type = SlideType.CUSTOM
    v = DSLValidator(dsl)
    report = v.validate()
    has_title_issue = any("title slide" in i.message.lower() for i in report.issues)
    assert has_title_issue
    results.ok("89. DSLValidator: missing title slide")
except Exception as e:
    results.fail("89. DSLValidator: missing title slide", str(e))

# 90
try:
    from app.models.dsl_v2 import SlideContentV2
    dsl = _make_dsl(8)
    dsl.slides[3].content = SlideContentV2()
    v = DSLValidator(dsl)
    report = v.validate()
    has_empty = any("no content" in i.message.lower() for i in report.issues)
    assert has_empty
    results.ok("90. DSLValidator: empty slide detected")
except Exception as e:
    results.fail("90. DSLValidator: empty slide detected", str(e))

# 91
try:
    dsl = _make_dsl(8)
    comp_slide = None
    for s in dsl.slides:
        if s.type == SlideType.COMPETITION_SLIDE:
            comp_slide = s
            break
    if comp_slide is None:
        dsl.slides[4].type = SlideType.COMPETITION_SLIDE
        comp_slide = dsl.slides[4]
    comp_slide.content.body_text = "We have no competition in this space"
    v = DSLValidator(dsl)
    report = v.validate()
    has_pitfall = any("no competition" in i.message.lower() for i in report.issues)
    assert has_pitfall
    results.ok("91. DSLValidator: no competition anti-pitfall")
except Exception as e:
    results.fail("91. DSLValidator: no competition anti-pitfall", str(e))

# 92
try:
    dsl = _make_dsl(8)
    dsl.slides[2].layout = LayoutType.TIMELINE
    dsl.slides[2].content.timeline_items = None
    v = DSLValidator(dsl)
    report = v.validate()
    has_layout = any("timeline" in i.message.lower() and "layout" in i.message.lower() for i in report.issues)
    assert has_layout
    results.ok("92. DSLValidator: layout coherence timeline")
except Exception as e:
    results.fail("92. DSLValidator: layout coherence timeline", str(e))

# 93
try:
    dsl = _make_dsl(8)
    dsl.slides[2].layout = LayoutType.QUOTE
    dsl.slides[2].content.quote_text = None
    v = DSLValidator(dsl)
    report = v.validate()
    has_layout = any("quote" in i.message.lower() and "layout" in i.message.lower() for i in report.issues)
    assert has_layout
    results.ok("93. DSLValidator: layout coherence quote")
except Exception as e:
    results.fail("93. DSLValidator: layout coherence quote", str(e))

# 94
try:
    from app.models.dsl_v2 import SlideElement, ElementType, SlidePosition, SlideSize, ElementStyle
    dsl = _make_dsl(8)
    dsl.slides[1].elements.append(SlideElement(
        id="img_1",
        type=ElementType.IMAGE,
        content="https://example.com/img.png",
        position=SlidePosition(x=0.1, y=0.1),
        size=SlideSize(width=0.5, height=0.5),
        style=ElementStyle(),
        alt_text=None,
    ))
    v = DSLValidator(dsl)
    report = v.validate()
    has_alt = any("alt text" in i.message.lower() for i in report.issues)
    assert has_alt
    results.ok("94. DSLValidator: accessibility alt text")
except Exception as e:
    results.fail("94. DSLValidator: accessibility alt text", str(e))

# 95
try:
    dsl = _make_dsl(8)
    v = DSLValidator(dsl)
    report = v.validate_slide("slide_1")
    assert isinstance(report, ValidationReport)
    results.ok("95. DSLValidator: validate_slide single")
except Exception as e:
    results.fail("95. DSLValidator: validate_slide single", str(e))


# ===================================================================
# 96-99: EditorRoutes
# ===================================================================

print("\n--- EditorRoutes ---")

# 96
try:
    from app.api.routes.editor_routes import (
        router,
        OperationResponse,
        EditorStateResponse,
        AddSlideRequest,
        MoveSlideRequest,
    )
    results.ok("96. EditorRoutes: module imports")
except Exception as e:
    results.fail("96. EditorRoutes: module imports", str(e))

# 97
try:
    assert router.prefix == "/api/v2/editor"
    results.ok("97. EditorRoutes: router prefix")
except Exception as e:
    results.fail("97. EditorRoutes: router prefix", str(e))

# 98
try:
    resp = OperationResponse(success=True, message="ok", data={"key": "val"})
    assert resp.success is True
    assert resp.data == {"key": "val"}
    results.ok("98. EditorRoutes: OperationResponse schema")
except Exception as e:
    results.fail("98. EditorRoutes: OperationResponse schema", str(e))

# 99
try:
    dsl = _make_dsl(3)
    resp = EditorStateResponse(success=True, dsl=dsl.model_dump(mode="json"))
    assert resp.success
    assert "slides" in resp.dsl
    results.ok("99. EditorRoutes: EditorStateResponse schema")
except Exception as e:
    results.fail("99. EditorRoutes: EditorStateResponse schema", str(e))


# ===================================================================
# 100: Integration
# ===================================================================

print("\n--- Integration ---")

# 100
try:
    with open(os.path.join(os.path.dirname(__file__), "main.py"), "r") as f:
        main_content = f.read()
    assert "editor_routes" in main_content
    assert "editor_v2" in main_content
    results.ok("100. Integration: main.py includes editor_v2")
except Exception as e:
    results.fail("100. Integration: main.py includes editor_v2", str(e))


# ===================================================================
# SUMMARY
# ===================================================================

all_passed = results.summary()
sys.exit(0 if all_passed else 1)
