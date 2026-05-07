#!/usr/bin/env python3
"""
Phase 11 Tests -- QA + Polish + Delivery.

100 tests covering all 6 modules + quality routes + integration:
    Tests  1-18:  Visual Regression (SSIM engine, diff maps, golden master store)
    Tests 19-36:  Accessibility Engine (contrast, WCAG checks, auditor)
    Tests 37-54:  Presentation Modes (configs, compatibility, transformer, adapter)
    Tests 55-70:  Production Hardening (health checks, load tests, error budget)
    Tests 71-85:  Quality Orchestrator (content, anti-slop, performance, unified)
    Tests 86-100: Quality Routes + Integration (imports, endpoints, module init)

Run:
    cd server4
    python test_phase11.py
"""

import sys
import os
import time
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
        print(f"Phase 11 Tests: {self.passed}/{total} passed")
        if self.errors:
            print("\nFailures:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0


results = TestResult()


# ── Helpers ──────────────────────────────────────────────────────

def _make_dsl(slide_count=3):
    """Create a minimal PresentationDSL dict for testing."""
    slides = []
    for i in range(slide_count):
        slides.append({
            "index": i,
            "id": f"slide_{i}",
            "type": "custom",
            "layout": "center-focus",
            "content": {
                "title": f"Slide {i}",
                "subtitle": f"Subtitle {i}",
                "body": f"Body text for slide {i} with some content.",
                "bullets": ["Point A", "Point B", "Point C"],
            },
            "style": {
                "background": {"colors": ["#1a1a2e"]},
                "titleColor": "#ffffff",
                "textColor": "#e0e0e0",
                "accentColor": "#6366f1",
                "fontSize": "base",
            },
            "elements": [
                {"type": "text", "id": f"txt_{i}", "style": {"color": "#ffffff", "fontSize": "base"}},
            ],
            "speakerNotes": f"Notes for slide {i}",
        })
    return {
        "presentation": {
            "id": "test-pres-p11",
            "title": "Phase 11 Test Presentation",
            "subtitle": "QA Testing",
            "metadata": {"language": "en"},
            "theme": {"colors": {"background": "#1a1a2e", "text": "#ffffff"}},
        },
        "slides": slides,
    }


def _make_image(width=64, height=64, r=128, g=128, b=128):
    """Create a flat RGB pixel list."""
    return [r, g, b] * (width * height)


# ═══════════════════════════════════════════════════════════════════
# TESTS 1-18: VISUAL REGRESSION
# ═══════════════════════════════════════════════════════════════════

print("\n── Visual Regression Tests ──")

# Test 1: SSIMEngine import
try:
    from app.services.slides_new.quality.visual_regression import SSIMEngine
    results.ok("1. SSIMEngine import")
except Exception as e:
    results.fail("1. SSIMEngine import", str(e))

# Test 2: SSIM identical images
try:
    engine = SSIMEngine()
    img_rgb = _make_image(32, 32, 100, 100, 100)
    img = engine.flat_rgb_to_grayscale(img_rgb)
    result = engine.compute(img, img, 32, 32)
    assert result.score >= 0.99, f"Expected ~1.0, got {result.score}"
    assert result.is_similar
    results.ok("2. SSIM identical images = 1.0")
except Exception as e:
    results.fail("2. SSIM identical images = 1.0", str(e))

# Test 3: SSIM different images
try:
    engine = SSIMEngine()
    img_a = engine.flat_rgb_to_grayscale(_make_image(32, 32, 0, 0, 0))
    img_b = engine.flat_rgb_to_grayscale(_make_image(32, 32, 255, 255, 255))
    result = engine.compute(img_a, img_b, 32, 32)
    assert result.score < 0.5, f"Expected low score, got {result.score}"
    results.ok("3. SSIM different images < 0.5")
except Exception as e:
    results.fail("3. SSIM different images < 0.5", str(e))

# Test 4: SSIM components populated
try:
    engine = SSIMEngine()
    img = engine.flat_rgb_to_grayscale(_make_image(32, 32, 50, 100, 150))
    result = engine.compute(img, img, 32, 32)
    assert result.luminance > 0
    assert result.contrast > 0
    assert result.structure > 0
    assert result.computation_time_ms >= 0
    results.ok("4. SSIM components populated")
except Exception as e:
    results.fail("4. SSIM components populated", str(e))

# Test 5: SSIMResult model properties
try:
    from app.services.slides_new.quality.models import SSIMResult
    r = SSIMResult(score=0.92)
    assert r.is_similar
    assert abs(r.dissimilarity - 0.04) < 0.01
    d = r.to_dict()
    assert "score" in d
    assert "is_similar" in d
    results.ok("5. SSIMResult model properties")
except Exception as e:
    results.fail("5. SSIMResult model properties", str(e))

# Test 6: DiffMapGenerator
try:
    from app.services.slides_new.quality.visual_regression import DiffMapGenerator
    gen = DiffMapGenerator(cell_size=16)
    img_a = _make_image(32, 32, 100, 100, 100)
    img_b = _make_image(32, 32, 200, 200, 200)
    entries = gen.generate(img_a, img_b, 32, 32)
    assert isinstance(entries, list)
    results.ok("6. DiffMapGenerator generates entries")
except Exception as e:
    results.fail("6. DiffMapGenerator generates entries", str(e))

# Test 7: DiffMapGenerator identical = no diffs
try:
    gen = DiffMapGenerator(cell_size=16)
    img = _make_image(32, 32, 100, 100, 100)
    entries = gen.generate(img, img, 32, 32)
    assert len(entries) == 0, f"Expected 0, got {len(entries)}"
    results.ok("7. DiffMapGenerator identical = no diffs")
except Exception as e:
    results.fail("7. DiffMapGenerator identical = no diffs", str(e))

# Test 8: GoldenMasterStore
try:
    from app.services.slides_new.quality.visual_regression import GoldenMasterStore
    store = GoldenMasterStore(max_masters=10)
    from app.services.slides_new.quality.models import GoldenMaster
    gm = GoldenMaster(
        presentation_id="p1", slide_id="s1", renderer="reveal.js",
        pixel_data=bytes([255, 0, 0] * 4), resolution=(2, 2),
    )
    store.store(gm)
    assert store.exists("p1", "s1", "reveal.js")
    results.ok("8. GoldenMasterStore store/exists")
except Exception as e:
    results.fail("8. GoldenMasterStore store/exists", str(e))

# Test 9: GoldenMasterStore get
try:
    retrieved = store.get("p1", "s1", "reveal.js")
    assert retrieved is not None
    assert retrieved.resolution == (2, 2)
    results.ok("9. GoldenMasterStore get")
except Exception as e:
    results.fail("9. GoldenMasterStore get", str(e))

# Test 10: GoldenMasterStore LRU eviction
try:
    store2 = GoldenMasterStore(max_masters=3)
    for i in range(5):
        gm = GoldenMaster(
            presentation_id=f"p{i}", slide_id="s0", renderer="reveal.js",
            pixel_data=bytes([i]*12), resolution=(2, 2),
        )
        store2.store(gm)
    stats = store2.get_stats()
    assert stats["total_masters"] <= 3
    results.ok("10. GoldenMasterStore LRU eviction")
except Exception as e:
    results.fail("10. GoldenMasterStore LRU eviction", str(e))

# Test 11: GoldenMasterStore remove
try:
    store3 = GoldenMasterStore()
    gm = GoldenMaster(
        presentation_id="px", slide_id="sx", renderer="html",
        pixel_data=bytes([1]*12), resolution=(2, 2),
    )
    store3.store(gm)
    assert store3.exists("px", "sx", "html")
    store3.remove("px", "sx", "html")
    assert not store3.exists("px", "sx", "html")
    results.ok("11. GoldenMasterStore remove")
except Exception as e:
    results.fail("11. GoldenMasterStore remove", str(e))

# Test 12: GoldenMasterStore clear_presentation
try:
    store4 = GoldenMasterStore()
    for i in range(3):
        gm = GoldenMaster(
            presentation_id="pClear", slide_id=f"s{i}", renderer="reveal.js",
            pixel_data=bytes([i]*12), resolution=(2, 2),
        )
        store4.store(gm)
    assert len(store4.get_for_presentation("pClear")) == 3
    store4.clear_presentation("pClear")
    assert len(store4.get_for_presentation("pClear")) == 0
    results.ok("12. GoldenMasterStore clear_presentation")
except Exception as e:
    results.fail("12. GoldenMasterStore clear_presentation", str(e))

# Test 13: VisualRegressionService new baseline
try:
    from app.services.slides_new.quality.visual_regression import VisualRegressionService
    vr = VisualRegressionService(threshold=0.85)
    img = _make_image(32, 32, 100, 100, 100)
    result = vr.compare_slide("p_new", "s0", "reveal.js", img, 32, 32)
    from app.services.slides_new.quality.models import RegressionStatus
    assert result.status == RegressionStatus.NEW_BASELINE
    results.ok("13. VisualRegressionService new baseline")
except Exception as e:
    results.fail("13. VisualRegressionService new baseline", str(e))

# Test 14: VisualRegressionService pass
try:
    img = _make_image(32, 32, 100, 100, 100)
    result = vr.compare_slide("p_new", "s0", "reveal.js", img, 32, 32)
    assert result.status == RegressionStatus.PASS
    results.ok("14. VisualRegressionService pass on matching image")
except Exception as e:
    results.fail("14. VisualRegressionService pass on matching image", str(e))

# Test 15: VisualRegressionService fail
try:
    img_diff = _make_image(32, 32, 0, 0, 0)  # Grayscale 0 vs baseline 100
    result = vr.compare_slide("p_new", "s0", "reveal.js", img_diff, 32, 32)
    assert result.status == RegressionStatus.FAIL
    results.ok("15. VisualRegressionService fail on different image")
except Exception as e:
    results.fail("15. VisualRegressionService fail on different image", str(e))

# Test 16: VisualRegressionService update_baseline
try:
    img_new = _make_image(32, 32, 50, 50, 50)
    vr.update_baseline("p_new", "s0", "reveal.js", img_new, 32, 32)
    result = vr.compare_slide("p_new", "s0", "reveal.js", img_new, 32, 32)
    assert result.status == RegressionStatus.PASS
    results.ok("16. VisualRegressionService update_baseline")
except Exception as e:
    results.fail("16. VisualRegressionService update_baseline", str(e))

# Test 17: VisualRegressionService batch_compare
try:
    img = _make_image(32, 32, 50, 50, 50)
    batch = [
        {"slide_id": "s0", "pixels": img, "width": 32, "height": 32},
        {"slide_id": "s1", "pixels": img, "width": 32, "height": 32},
    ]
    batch_results = vr.batch_compare("p_new", batch, "reveal.js")
    assert len(batch_results) == 2
    results.ok("17. VisualRegressionService batch_compare")
except Exception as e:
    results.fail("17. VisualRegressionService batch_compare", str(e))

# Test 18: VisualRegressionService statistics
try:
    stats = vr.get_stats()
    assert stats["total_comparisons"] > 0
    assert "pass_count" in stats
    assert "fail_count" in stats
    results.ok("18. VisualRegressionService statistics")
except Exception as e:
    results.fail("18. VisualRegressionService statistics", str(e))


# ═══════════════════════════════════════════════════════════════════
# TESTS 19-36: ACCESSIBILITY ENGINE
# ═══════════════════════════════════════════════════════════════════

print("\n── Accessibility Engine Tests ──")

# Test 19: hex_to_rgb
try:
    from app.services.slides_new.quality.accessibility_engine import hex_to_rgb
    assert hex_to_rgb("#ffffff") == (255, 255, 255)
    assert hex_to_rgb("#000000") == (0, 0, 0)
    assert hex_to_rgb("#fff") == (255, 255, 255)
    results.ok("19. hex_to_rgb")
except Exception as e:
    results.fail("19. hex_to_rgb", str(e))

# Test 20: relative_luminance
try:
    from app.services.slides_new.quality.accessibility_engine import relative_luminance
    lum_white = relative_luminance(255, 255, 255)
    lum_black = relative_luminance(0, 0, 0)
    assert abs(lum_white - 1.0) < 0.001
    assert abs(lum_black - 0.0) < 0.001
    results.ok("20. relative_luminance")
except Exception as e:
    results.fail("20. relative_luminance", str(e))

# Test 21: contrast_ratio
try:
    from app.services.slides_new.quality.accessibility_engine import contrast_ratio
    ratio = contrast_ratio("#ffffff", "#000000")
    assert abs(ratio - 21.0) < 0.1, f"Expected ~21, got {ratio}"
    results.ok("21. contrast_ratio white/black = 21:1")
except Exception as e:
    results.fail("21. contrast_ratio white/black = 21:1", str(e))

# Test 22: contrast_ratio same colors = 1:1
try:
    ratio = contrast_ratio("#888888", "#888888")
    assert abs(ratio - 1.0) < 0.01
    results.ok("22. contrast_ratio same = 1:1")
except Exception as e:
    results.fail("22. contrast_ratio same = 1:1", str(e))

# Test 23: passes_wcag_aa normal text
try:
    from app.services.slides_new.quality.accessibility_engine import passes_wcag_aa
    passed, ratio = passes_wcag_aa("#ffffff", "#000000")
    assert passed
    passed_low, ratio_low = passes_wcag_aa("#777777", "#888888")
    assert not passed_low
    results.ok("23. passes_wcag_aa normal text")
except Exception as e:
    results.fail("23. passes_wcag_aa normal text", str(e))

# Test 24: passes_wcag_aa large text (3:1 threshold)
try:
    passed, ratio = passes_wcag_aa("#ffffff", "#595959", is_large_text=True)
    assert passed, f"Should pass large text with ratio {ratio}"
    results.ok("24. passes_wcag_aa large text")
except Exception as e:
    results.fail("24. passes_wcag_aa large text", str(e))

# Test 25: passes_wcag_aaa
try:
    from app.services.slides_new.quality.accessibility_engine import passes_wcag_aaa
    passed, ratio = passes_wcag_aaa("#ffffff", "#000000")
    assert passed
    passed_fail, _ = passes_wcag_aaa("#999999", "#666666")
    assert not passed_fail
    results.ok("25. passes_wcag_aaa")
except Exception as e:
    results.fail("25. passes_wcag_aaa", str(e))

# Test 26: suggest_contrast_fix
try:
    from app.services.slides_new.quality.accessibility_engine import suggest_contrast_fix
    fix = suggest_contrast_fix("#777777", "#ffffff", 4.5)
    assert fix.startswith("#")
    # The fix should produce passing contrast
    fixed_passed, fixed_ratio = passes_wcag_aa(fix, "#ffffff")
    assert fixed_passed, f"Fix {fix} still fails with ratio {fixed_ratio}"
    results.ok("26. suggest_contrast_fix produces passing color")
except Exception as e:
    results.fail("26. suggest_contrast_fix produces passing color", str(e))

# Test 27: is_large_text
try:
    from app.services.slides_new.quality.accessibility_engine import is_large_text
    assert is_large_text("3xl")  # 30pt >= 24
    assert is_large_text("lg", 700)  # 18pt + bold
    assert not is_large_text("sm")  # 14pt, not bold
    results.ok("27. is_large_text classification")
except Exception as e:
    results.fail("27. is_large_text classification", str(e))

# Test 28: AccessibilityAuditor import
try:
    from app.services.slides_new.quality.accessibility_engine import AccessibilityAuditor
    auditor = AccessibilityAuditor()
    results.ok("28. AccessibilityAuditor import")
except Exception as e:
    results.fail("28. AccessibilityAuditor import", str(e))

# Test 29: audit_presentation basic
try:
    dsl = _make_dsl(3)
    report = auditor.audit_presentation(dsl)
    assert report.slides_audited == 3
    assert report.score >= 0
    assert hasattr(report, "violations")
    assert hasattr(report, "contrast_checks")
    results.ok("29. audit_presentation basic")
except Exception as e:
    results.fail("29. audit_presentation basic", str(e))

# Test 30: audit detects low contrast
try:
    dsl = _make_dsl(1)
    dsl["slides"][0]["style"]["titleColor"] = "#1a1a2e"  # Same as bg
    dsl["slides"][0]["style"]["background"] = {"colors": ["#1a1a2e"]}
    report = auditor.audit_presentation(dsl)
    contrast_fails = [
        v for v in report.violations
        if v.category.value == "color_contrast"
    ]
    assert len(contrast_fails) > 0, "Should detect low contrast"
    results.ok("30. audit detects low contrast")
except Exception as e:
    results.fail("30. audit detects low contrast", str(e))

# Test 31: audit detects missing alt text
try:
    dsl = _make_dsl(1)
    dsl["slides"][0]["elements"] = [
        {"type": "image", "id": "img_1"},  # No alt_text
    ]
    report = auditor.audit_presentation(dsl)
    alt_violations = [v for v in report.violations if v.category.value == "alt_text"]
    assert len(alt_violations) > 0
    results.ok("31. audit detects missing alt text")
except Exception as e:
    results.fail("31. audit detects missing alt text", str(e))

# Test 32: audit detects missing language
try:
    dsl = _make_dsl(1)
    dsl["presentation"]["metadata"] = {}
    report = auditor.audit_presentation(dsl)
    lang_violations = [v for v in report.violations if v.category.value == "language"]
    assert len(lang_violations) > 0
    results.ok("32. audit detects missing language")
except Exception as e:
    results.fail("32. audit detects missing language", str(e))

# Test 33: audit detects rapid animation
try:
    dsl = _make_dsl(1)
    dsl["slides"][0]["style"]["animation"] = "strobe"
    report = auditor.audit_presentation(dsl)
    motion_violations = [v for v in report.violations if v.category.value == "motion_safe"]
    assert len(motion_violations) > 0
    results.ok("33. audit detects rapid animation")
except Exception as e:
    results.fail("33. audit detects rapid animation", str(e))

# Test 34: audit single slide
try:
    auditor2 = AccessibilityAuditor()
    slide = _make_dsl(1)["slides"][0]
    report = auditor2.audit_slide(slide)
    assert report.slides_audited == 1
    results.ok("34. audit single slide")
except Exception as e:
    results.fail("34. audit single slide", str(e))

# Test 35: A11yViolation model
try:
    from app.services.slides_new.quality.models import A11yViolation, A11yCategory, A11ySeverity
    v = A11yViolation(
        category=A11yCategory.COLOR_CONTRAST,
        severity=A11ySeverity.CRITICAL,
        wcag_criterion="1.4.3",
        description="Test violation",
    )
    d = v.to_dict()
    assert d["category"] == "color_contrast"
    assert d["severity"] == "critical"
    results.ok("35. A11yViolation model")
except Exception as e:
    results.fail("35. A11yViolation model", str(e))

# Test 36: ContrastCheck auto-pass
try:
    from app.services.slides_new.quality.models import ContrastCheck
    c = ContrastCheck(foreground="#ffffff", background="#000000", ratio=21.0)
    assert c.passed
    c2 = ContrastCheck(foreground="#888888", background="#888888", ratio=1.0)
    assert not c2.passed
    results.ok("36. ContrastCheck auto-pass")
except Exception as e:
    results.fail("36. ContrastCheck auto-pass", str(e))


# ═══════════════════════════════════════════════════════════════════
# TESTS 37-54: PRESENTATION MODES
# ═══════════════════════════════════════════════════════════════════

print("\n── Presentation Modes Tests ──")

# Test 37: PresentationMode enum
try:
    from app.services.slides_new.quality.models import PresentationMode
    assert PresentationMode.READING.value == "reading"
    assert PresentationMode.PRESENTATION.value == "presentation"
    assert PresentationMode.OVERVIEW.value == "overview"
    assert PresentationMode.SPEAKER.value == "speaker"
    assert PresentationMode.PRINT.value == "print"
    results.ok("37. PresentationMode enum")
except Exception as e:
    results.fail("37. PresentationMode enum", str(e))

# Test 38: get_mode_config
try:
    from app.services.slides_new.quality.presentation_modes import get_mode_config
    cfg = get_mode_config(PresentationMode.READING)
    assert cfg.mode == PresentationMode.READING
    assert cfg.layout == "scroll"
    assert cfg.show_toc_sidebar
    results.ok("38. get_mode_config reading")
except Exception as e:
    results.fail("38. get_mode_config reading", str(e))

# Test 39: presentation mode config
try:
    cfg = get_mode_config(PresentationMode.PRESENTATION)
    assert cfg.navigation.value == "keyboard"
    assert cfg.enable_transitions
    assert cfg.enable_fragments
    results.ok("39. presentation mode config")
except Exception as e:
    results.fail("39. presentation mode config", str(e))

# Test 40: overview mode config
try:
    cfg = get_mode_config(PresentationMode.OVERVIEW)
    assert cfg.layout == "grid"
    results.ok("40. overview mode config")
except Exception as e:
    results.fail("40. overview mode config", str(e))

# Test 41: speaker mode config
try:
    cfg = get_mode_config(PresentationMode.SPEAKER)
    assert cfg.show_speaker_notes
    assert cfg.enable_timer
    results.ok("41. speaker mode config")
except Exception as e:
    results.fail("41. speaker mode config", str(e))

# Test 42: print mode config
try:
    cfg = get_mode_config(PresentationMode.PRINT)
    assert not cfg.enable_transitions
    assert cfg.dark_mode is False
    results.ok("42. print mode config")
except Exception as e:
    results.fail("42. print mode config", str(e))

# Test 43: get_all_modes returns 5
try:
    from app.services.slides_new.quality.presentation_modes import get_all_modes
    modes = get_all_modes()
    assert len(modes) == 5
    results.ok("43. get_all_modes returns 5 modes")
except Exception as e:
    results.fail("43. get_all_modes returns 5 modes", str(e))

# Test 44: ModeConfig to_dict
try:
    cfg = get_mode_config(PresentationMode.READING)
    d = cfg.to_dict()
    assert d["mode"] == "reading"
    assert "features" in d
    assert isinstance(d["features"], list)
    results.ok("44. ModeConfig to_dict")
except Exception as e:
    results.fail("44. ModeConfig to_dict", str(e))

# Test 45: check_mode_compatibility
try:
    from app.services.slides_new.quality.presentation_modes import check_mode_compatibility
    from app.services.slides_new.renderers.base_renderer import RendererType
    assert check_mode_compatibility(RendererType.REVEAL_JS, PresentationMode.PRESENTATION) == "native"
    assert check_mode_compatibility(RendererType.HTML, PresentationMode.READING) == "native"
    assert check_mode_compatibility(RendererType.REACT_3D, PresentationMode.READING) == "degraded"
    results.ok("45. check_mode_compatibility")
except Exception as e:
    results.fail("45. check_mode_compatibility", str(e))

# Test 46: get_supported_modes
try:
    from app.services.slides_new.quality.presentation_modes import get_supported_modes
    modes = get_supported_modes(RendererType.REVEAL_JS)
    assert len(modes) == 5
    assert all("mode" in m and "support" in m for m in modes)
    results.ok("46. get_supported_modes")
except Exception as e:
    results.fail("46. get_supported_modes", str(e))

# Test 47: ReadingModeTransformer
try:
    from app.services.slides_new.quality.presentation_modes import ReadingModeTransformer
    transformer = ReadingModeTransformer()
    dsl = _make_dsl(3)
    content = transformer.transform(dsl)
    assert len(content) == 3
    assert content[0].title == "Slide 0"
    assert content[0].word_count > 0
    results.ok("47. ReadingModeTransformer transform")
except Exception as e:
    results.fail("47. ReadingModeTransformer transform", str(e))

# Test 48: ReadingModeTransformer TOC
try:
    toc = transformer.generate_toc(content)
    assert isinstance(toc, list)
    assert len(toc) >= 3
    results.ok("48. ReadingModeTransformer TOC")
except Exception as e:
    results.fail("48. ReadingModeTransformer TOC", str(e))

# Test 49: PresentationModeAdapter
try:
    from app.services.slides_new.quality.presentation_modes import PresentationModeAdapter
    adapter = PresentationModeAdapter()
    result = adapter.adapt(
        "<div>test</div>", ".test{}", PresentationMode.READING, RendererType.HTML
    )
    assert "html" in result
    assert "css" in result
    assert "mode-reading" in result["html"]
    results.ok("49. PresentationModeAdapter reading")
except Exception as e:
    results.fail("49. PresentationModeAdapter reading", str(e))

# Test 50: PresentationModeAdapter presentation mode
try:
    result = adapter.adapt(
        "<div>slide</div>", "", PresentationMode.PRESENTATION, RendererType.REVEAL_JS
    )
    assert "mode-presentation" in result["html"]
    assert result["js"]  # Should have keyboard JS
    results.ok("50. PresentationModeAdapter presentation")
except Exception as e:
    results.fail("50. PresentationModeAdapter presentation", str(e))

# Test 51: PresentationModeAdapter speaker mode
try:
    result = adapter.adapt(
        "<div>slide</div>", "", PresentationMode.SPEAKER, RendererType.REVEAL_JS
    )
    assert "mode-speaker" in result["html"]
    assert "speakerNotes" in result["html"]
    results.ok("51. PresentationModeAdapter speaker")
except Exception as e:
    results.fail("51. PresentationModeAdapter speaker", str(e))

# Test 52: PresentationModeManager
try:
    from app.services.slides_new.quality.presentation_modes import PresentationModeManager
    mgr = PresentationModeManager()
    all_modes = mgr.get_all_modes()
    assert len(all_modes) == 5
    results.ok("52. PresentationModeManager get_all_modes")
except Exception as e:
    results.fail("52. PresentationModeManager get_all_modes", str(e))

# Test 53: PresentationModeManager transform_for_reading
try:
    dsl = _make_dsl(2)
    reading = mgr.transform_for_reading(dsl)
    assert "slides" in reading
    assert "toc" in reading
    assert reading["total_words"] > 0
    assert reading["reading_time_min"] > 0
    results.ok("53. PresentationModeManager transform_for_reading")
except Exception as e:
    results.fail("53. PresentationModeManager transform_for_reading", str(e))

# Test 54: PresentationModeManager stats
try:
    stats = mgr.get_stats()
    assert "supported_modes" in stats
    assert stats["supported_modes"] == 5
    results.ok("54. PresentationModeManager stats")
except Exception as e:
    results.fail("54. PresentationModeManager stats", str(e))


# ═══════════════════════════════════════════════════════════════════
# TESTS 55-70: PRODUCTION HARDENING
# ═══════════════════════════════════════════════════════════════════

print("\n── Production Hardening Tests ──")

# Test 55: HealthCheckEngine import
try:
    from app.services.slides_new.quality.production_hardening import HealthCheckEngine
    engine = HealthCheckEngine()
    results.ok("55. HealthCheckEngine import")
except Exception as e:
    results.fail("55. HealthCheckEngine import", str(e))

# Test 56: ServiceComponent enum
try:
    from app.services.slides_new.quality.models import ServiceComponent
    assert len(ServiceComponent) == 8
    assert ServiceComponent.LLM_ROUTER.value == "llm_router"
    assert ServiceComponent.STATE_SYNC.value == "state_sync"
    results.ok("56. ServiceComponent enum has 8 components")
except Exception as e:
    results.fail("56. ServiceComponent enum has 8 components", str(e))

# Test 57: HealthCheckEngine check_all
try:
    engine = HealthCheckEngine()
    loop = asyncio.new_event_loop()
    results_dict = loop.run_until_complete(engine.check_all())
    assert len(results_dict) == 8
    loop.close()
    results.ok("57. HealthCheckEngine check_all returns 8 components")
except Exception as e:
    results.fail("57. HealthCheckEngine check_all returns 8 components", str(e))

# Test 58: HealthCheckEngine overall status
try:
    overall = engine.get_overall_status()
    from app.services.slides_new.quality.models import HealthStatus
    assert overall.value in ("healthy", "degraded", "unhealthy", "unknown")
    results.ok("58. HealthCheckEngine overall status")
except Exception as e:
    results.fail("58. HealthCheckEngine overall status", str(e))

# Test 59: HealthCheckEngine summary
try:
    summary = engine.get_summary()
    assert "overall" in summary
    assert "components" in summary
    assert "checks_run" in summary
    results.ok("59. HealthCheckEngine summary")
except Exception as e:
    results.fail("59. HealthCheckEngine summary", str(e))

# Test 60: ComponentHealth model
try:
    from app.services.slides_new.quality.models import ComponentHealth
    ch = ComponentHealth(
        component=ServiceComponent.RENDER_ENGINE,
        status=HealthStatus.HEALTHY,
        latency_ms=42.5,
    )
    d = ch.to_dict()
    assert d["component"] == "render_engine"
    assert d["latency_ms"] == 42.5
    results.ok("60. ComponentHealth model")
except Exception as e:
    results.fail("60. ComponentHealth model", str(e))

# Test 61: LoadTestSimulator import
try:
    from app.services.slides_new.quality.production_hardening import LoadTestSimulator
    tester = LoadTestSimulator()
    results.ok("61. LoadTestSimulator import")
except Exception as e:
    results.fail("61. LoadTestSimulator import", str(e))

# Test 62: LoadTestSimulator run_test
try:
    loop = asyncio.new_event_loop()
    lt_result = loop.run_until_complete(
        tester.run_test(concurrent_users=3, requests_per_user=2)
    )
    assert lt_result.total_requests == 6
    assert lt_result.successful_requests + lt_result.failed_requests == 6
    loop.close()
    results.ok("62. LoadTestSimulator run_test")
except Exception as e:
    results.fail("62. LoadTestSimulator run_test", str(e))

# Test 63: LoadTestResult percentiles
try:
    assert lt_result.avg_latency_ms >= 0
    assert lt_result.p50_latency_ms >= 0
    assert lt_result.p95_latency_ms >= 0
    assert lt_result.requests_per_second > 0
    results.ok("63. LoadTestResult percentiles populated")
except Exception as e:
    results.fail("63. LoadTestResult percentiles populated", str(e))

# Test 64: LoadTestResult to_dict
try:
    d = lt_result.to_dict()
    assert "success_rate" in d
    assert "passed" in d
    assert "avg_latency_ms" in d
    results.ok("64. LoadTestResult to_dict")
except Exception as e:
    results.fail("64. LoadTestResult to_dict", str(e))

# Test 65: ErrorBudgetTracker
try:
    from app.services.slides_new.quality.production_hardening import ErrorBudgetTracker
    tracker = ErrorBudgetTracker(slo_target=99.5, window_seconds=3600)
    for _ in range(100):
        tracker.record_request(True)
    assert tracker.error_budget_remaining == 100.0
    assert tracker.current_success_rate == 100.0
    assert tracker.is_within_budget
    results.ok("65. ErrorBudgetTracker 100% success")
except Exception as e:
    results.fail("65. ErrorBudgetTracker 100% success", str(e))

# Test 66: ErrorBudgetTracker with errors
try:
    tracker2 = ErrorBudgetTracker(slo_target=99.0)
    for _ in range(90):
        tracker2.record_request(True)
    for _ in range(10):
        tracker2.record_request(False)
    assert tracker2.current_success_rate == 90.0
    assert not tracker2.is_within_budget  # 10% errors >> 1% budget
    results.ok("66. ErrorBudgetTracker budget exhausted")
except Exception as e:
    results.fail("66. ErrorBudgetTracker budget exhausted", str(e))

# Test 67: ErrorBudgetTracker summary
try:
    summary = tracker.get_summary()
    assert "slo_target" in summary
    assert "current_success_rate" in summary
    assert "error_budget_remaining" in summary
    results.ok("67. ErrorBudgetTracker summary")
except Exception as e:
    results.fail("67. ErrorBudgetTracker summary", str(e))

# Test 68: ProductionReadinessAssessor import
try:
    from app.services.slides_new.quality.production_hardening import ProductionReadinessAssessor
    assessor = ProductionReadinessAssessor()
    results.ok("68. ProductionReadinessAssessor import")
except Exception as e:
    results.fail("68. ProductionReadinessAssessor import", str(e))

# Test 69: ProductionReadinessAssessor assess
try:
    loop = asyncio.new_event_loop()
    assessment = loop.run_until_complete(assessor.assess())
    assert "production_ready" in assessment
    assert "score" in assessment
    assert "overall_health" in assessment
    loop.close()
    results.ok("69. ProductionReadinessAssessor assess")
except Exception as e:
    results.fail("69. ProductionReadinessAssessor assess", str(e))

# Test 70: LoadTestResult passed property
try:
    from app.services.slides_new.quality.models import LoadTestResult as LTR
    lt = LTR(
        total_requests=100, successful_requests=98, failed_requests=2,
        p95_latency_ms=1500,
    )
    assert lt.passed  # 98% > 95%, p95 < 5000
    lt2 = LTR(
        total_requests=100, successful_requests=80, failed_requests=20,
        p95_latency_ms=1500,
    )
    assert not lt2.passed  # 80% < 95%
    results.ok("70. LoadTestResult passed property")
except Exception as e:
    results.fail("70. LoadTestResult passed property", str(e))


# ═══════════════════════════════════════════════════════════════════
# TESTS 71-85: QUALITY ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════

print("\n── Quality Orchestrator Tests ──")

# Test 71: ContentQualityEvaluator import
try:
    from app.services.slides_new.quality.quality_orchestrator import ContentQualityEvaluator
    evaluator = ContentQualityEvaluator()
    results.ok("71. ContentQualityEvaluator import")
except Exception as e:
    results.fail("71. ContentQualityEvaluator import", str(e))

# Test 72: ContentQualityEvaluator normal presentation
try:
    dsl = _make_dsl(3)
    score = evaluator.evaluate(dsl)
    assert score.score > 70, f"Score {score.score}"
    assert score.passed
    results.ok("72. ContentQualityEvaluator normal = passing")
except Exception as e:
    results.fail("72. ContentQualityEvaluator normal = passing", str(e))

# Test 73: ContentQualityEvaluator empty presentation
try:
    score = evaluator.evaluate({"slides": []})
    assert score.score == 0
    assert not score.passed
    results.ok("73. ContentQualityEvaluator empty = 0")
except Exception as e:
    results.fail("73. ContentQualityEvaluator empty = 0", str(e))

# Test 74: ContentQualityEvaluator too many bullets
try:
    dsl = _make_dsl(1)
    dsl["slides"][0]["content"]["bullets"] = [f"b{i}" for i in range(10)]
    score = evaluator.evaluate(dsl)
    has_bullet_issue = any("Too many bullets" in i for i in score.issues)
    assert has_bullet_issue
    results.ok("74. ContentQualityEvaluator detects too many bullets")
except Exception as e:
    results.fail("74. ContentQualityEvaluator detects too many bullets", str(e))

# Test 75: AntiSlopIntegration
try:
    from app.services.slides_new.quality.quality_orchestrator import AntiSlopIntegration
    slop = AntiSlopIntegration()
    score = slop.evaluate(_make_dsl(2))
    assert score.dimension.value == "anti_slop"
    # Either real engine ran or skipped gracefully
    assert score.score >= 0
    results.ok("75. AntiSlopIntegration evaluate")
except Exception as e:
    results.fail("75. AntiSlopIntegration evaluate", str(e))

# Test 76: PerformanceEvaluator
try:
    from app.services.slides_new.quality.quality_orchestrator import PerformanceEvaluator
    perf = PerformanceEvaluator()
    score = perf.evaluate(_make_dsl(3))
    assert score.dimension.value == "performance"
    assert score.score > 0
    results.ok("76. PerformanceEvaluator normal")
except Exception as e:
    results.fail("76. PerformanceEvaluator normal", str(e))

# Test 77: PerformanceEvaluator heavy slides
try:
    dsl = _make_dsl(1)
    dsl["slides"][0]["elements"] = [
        {"type": "image", "id": f"img_{i}"} for i in range(15)
    ]
    score = perf.evaluate(dsl)
    has_issue = any("elements" in i for i in score.issues)
    assert has_issue
    results.ok("77. PerformanceEvaluator detects heavy slides")
except Exception as e:
    results.fail("77. PerformanceEvaluator detects heavy slides", str(e))

# Test 78: QualityOrchestrator import
try:
    from app.services.slides_new.quality.quality_orchestrator import QualityOrchestrator
    orch = QualityOrchestrator()
    results.ok("78. QualityOrchestrator import")
except Exception as e:
    results.fail("78. QualityOrchestrator import", str(e))

# Test 79: QualityOrchestrator comprehensive audit
try:
    loop = asyncio.new_event_loop()
    report = loop.run_until_complete(
        orch.run_comprehensive_audit(_make_dsl(3), "test-p11")
    )
    assert report.overall_score > 0
    assert report.overall_grade != ""
    assert len(report.dimensions) >= 4
    loop.close()
    results.ok("79. QualityOrchestrator comprehensive audit")
except Exception as e:
    results.fail("79. QualityOrchestrator comprehensive audit", str(e))

# Test 80: UnifiedQualityReport compute_overall
try:
    from app.services.slides_new.quality.models import (
        UnifiedQualityReport, DimensionScore, QualityDimension,
    )
    uqr = UnifiedQualityReport()
    uqr.dimensions = [
        DimensionScore(dimension=QualityDimension.ACCESSIBILITY, score=90, weight=1.5),
        DimensionScore(dimension=QualityDimension.CONTENT_QUALITY, score=80, weight=1.0),
    ]
    uqr.compute_overall()
    expected = (90 * 1.5 + 80 * 1.0) / (1.5 + 1.0)
    assert abs(uqr.overall_score - expected) < 0.1
    assert uqr.overall_grade != ""
    results.ok("80. UnifiedQualityReport compute_overall")
except Exception as e:
    results.fail("80. UnifiedQualityReport compute_overall", str(e))

# Test 81: Grade system
try:
    from app.services.slides_new.quality.models import _score_to_grade
    assert _score_to_grade(98) == "A+"
    assert _score_to_grade(94) == "A"
    assert _score_to_grade(85) == "B"
    assert _score_to_grade(75) == "C"
    assert _score_to_grade(55) == "F"
    results.ok("81. Grade system A+ through F")
except Exception as e:
    results.fail("81. Grade system A+ through F", str(e))

# Test 82: QualityOrchestrator recommendations
try:
    loop = asyncio.new_event_loop()
    report = loop.run_until_complete(
        orch.run_comprehensive_audit(_make_dsl(3))
    )
    assert isinstance(report.recommendations, list)
    assert len(report.recommendations) > 0
    loop.close()
    results.ok("82. QualityOrchestrator recommendations")
except Exception as e:
    results.fail("82. QualityOrchestrator recommendations", str(e))

# Test 83: QualityOrchestrator with visual regression
try:
    loop = asyncio.new_event_loop()
    report = loop.run_until_complete(
        orch.run_comprehensive_audit(_make_dsl(2), run_visual=True)
    )
    has_vr = any(d.dimension == QualityDimension.VISUAL_REGRESSION for d in report.dimensions)
    assert has_vr
    loop.close()
    results.ok("83. QualityOrchestrator with visual regression")
except Exception as e:
    results.fail("83. QualityOrchestrator with visual regression", str(e))

# Test 84: QualityOrchestrator stats
try:
    stats = orch.get_stats()
    assert stats["reports_generated"] > 0
    assert "weights" in stats
    results.ok("84. QualityOrchestrator stats")
except Exception as e:
    results.fail("84. QualityOrchestrator stats", str(e))

# Test 85: DEFAULT_WEIGHTS
try:
    from app.services.slides_new.quality.quality_orchestrator import DEFAULT_WEIGHTS
    assert len(DEFAULT_WEIGHTS) == 6
    assert DEFAULT_WEIGHTS[QualityDimension.ACCESSIBILITY] == 1.5
    results.ok("85. DEFAULT_WEIGHTS has 6 dimensions")
except Exception as e:
    results.fail("85. DEFAULT_WEIGHTS has 6 dimensions", str(e))


# ═══════════════════════════════════════════════════════════════════
# TESTS 86-100: QUALITY ROUTES + INTEGRATION
# ═══════════════════════════════════════════════════════════════════

print("\n── Quality Routes & Integration Tests ──")

# Test 86: quality_routes import
try:
    from app.api.routes import quality_routes
    assert hasattr(quality_routes, "router")
    results.ok("86. quality_routes import")
except Exception as e:
    results.fail("86. quality_routes import", str(e))

# Test 87: router prefix
try:
    from app.api.routes.quality_routes import router
    assert router.prefix == "/api/v2/quality"
    results.ok("87. router prefix /api/v2/quality")
except Exception as e:
    results.fail("87. router prefix /api/v2/quality", str(e))

# Test 88: router has expected routes
try:
    route_paths = [r.path for r in router.routes]
    expected = ["/audit/accessibility", "/audit/visual-regression",
                "/audit/comprehensive", "/health/components", "/stats"]
    for ep in expected:
        found = any(ep in p for p in route_paths)
        assert found, f"Missing route: {ep} in {route_paths}"
    results.ok("88. router has expected routes")
except Exception as e:
    results.fail("88. router has expected routes", str(e))

# Test 89: main.py imports quality_routes
try:
    with open("main.py", "r") as f:
        main_content = f.read()
    assert "quality_routes" in main_content
    assert "quality_v2" in main_content
    results.ok("89. main.py imports quality_routes")
except Exception as e:
    results.fail("89. main.py imports quality_routes", str(e))

# Test 90: quality module __init__ imports
try:
    from app.services.slides_new.quality import (
        SSIMEngine,
        AccessibilityAuditor,
        PresentationModeManager,
        HealthCheckEngine,
        QualityOrchestrator,
    )
    results.ok("90. quality __init__ exports all services")
except Exception as e:
    results.fail("90. quality __init__ exports all services", str(e))

# Test 91: quality module __init__ models
try:
    from app.services.slides_new.quality import (
        SSIMResult,
        AccessibilityReport,
        ModeConfig,
        LoadTestResult as LTR_Init,
        UnifiedQualityReport as UQR_Init,
    )
    results.ok("91. quality __init__ exports all models")
except Exception as e:
    results.fail("91. quality __init__ exports all models", str(e))

# Test 92: quality module helper functions
try:
    from app.services.slides_new.quality import (
        contrast_ratio,
        passes_wcag_aa,
        passes_wcag_aaa,
        relative_luminance,
        suggest_contrast_fix,
        hex_to_rgb,
        get_mode_config,
        check_mode_compatibility,
    )
    results.ok("92. quality __init__ exports helper functions")
except Exception as e:
    results.fail("92. quality __init__ exports helper functions", str(e))

# Test 93: Pydantic request models
try:
    from app.api.routes.quality_routes import (
        AuditRequest, VisualRegressionRequest,
        ComprehensiveAuditRequest, ContrastCheckRequest,
        ModeAdaptRequest, LoadTestRequest,
    )
    req = AuditRequest(presentation_dsl=_make_dsl(1))
    assert req.wcag_level == "AA"
    results.ok("93. Pydantic request models")
except Exception as e:
    results.fail("93. Pydantic request models", str(e))

# Test 94: AuditRequest defaults
try:
    req = AuditRequest(presentation_dsl={})
    assert req.wcag_level == "AA"
    results.ok("94. AuditRequest defaults")
except Exception as e:
    results.fail("94. AuditRequest defaults", str(e))

# Test 95: LoadTestRequest validation
try:
    req = LoadTestRequest(concurrent_users=10, requests_per_user=5)
    assert req.operation == "render"
    results.ok("95. LoadTestRequest validation")
except Exception as e:
    results.fail("95. LoadTestRequest validation", str(e))

# Test 96: VisualRegressionResult model
try:
    from app.services.slides_new.quality.models import VisualRegressionResult, RegressionStatus
    vr_result = VisualRegressionResult(
        status=RegressionStatus.PASS,
        ssim=SSIMResult(score=0.95),
    )
    d = vr_result.to_dict()
    assert d["status"] == "pass"
    assert d["ssim"]["score"] == 0.95
    results.ok("96. VisualRegressionResult model")
except Exception as e:
    results.fail("96. VisualRegressionResult model", str(e))

# Test 97: GoldenMaster model
try:
    from app.services.slides_new.quality.models import GoldenMaster
    gm = GoldenMaster(
        presentation_id="p1", slide_id="s1", renderer="html",
        pixel_data=bytes([1, 2, 3] * 4), resolution=(2, 2),
    )
    assert gm.id  # Auto-generated
    assert gm.pixel_stats  # Auto-generated
    d = gm.to_dict()
    assert "id" in d
    results.ok("97. GoldenMaster model")
except Exception as e:
    results.fail("97. GoldenMaster model", str(e))

# Test 98: DiffMapEntry model
try:
    from app.services.slides_new.quality.models import DiffMapEntry, DiffRegion
    entry = DiffMapEntry(
        region=DiffRegion.COLOR_CHANGE,
        x=0, y=0, width=32, height=32,
        severity=0.5,
        description="Color shift detected",
    )
    d = entry.to_dict()
    assert d["region"] == "color_change"
    results.ok("98. DiffMapEntry model")
except Exception as e:
    results.fail("98. DiffMapEntry model", str(e))

# Test 99: Full module integration — audit + modes + orchestrator
try:
    dsl = _make_dsl(3)
    # 1. Accessibility audit
    auditor = AccessibilityAuditor()
    a11y = auditor.audit_presentation(dsl)
    assert a11y.score >= 0
    # 2. Reading mode transform
    mgr = PresentationModeManager()
    reading = mgr.transform_for_reading(dsl)
    assert reading["total_words"] > 0
    # 3. Orchestrator
    loop = asyncio.new_event_loop()
    report = loop.run_until_complete(
        QualityOrchestrator().run_comprehensive_audit(dsl)
    )
    assert report.overall_score > 0
    loop.close()
    results.ok("99. Full module integration")
except Exception as e:
    results.fail("99. Full module integration", str(e))

# Test 100: ScreenshotCapture import
try:
    from app.services.slides_new.quality.visual_regression import ScreenshotCapture
    cap = ScreenshotCapture()
    assert cap.viewport_width == 1920
    assert cap.viewport_height == 1080
    results.ok("100. ScreenshotCapture import")
except Exception as e:
    results.fail("100. ScreenshotCapture import", str(e))


# ═══════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════

success = results.summary()
sys.exit(0 if success else 1)
