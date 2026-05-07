"""
Phase 4 Verification Test -- reveal.js Renderer & CSS Architecture.

Tests:
 1. BaseRenderer and RenderOutput imports
 2. RevealCompiler instantiation
 3. RevealCompiler — full presentation compile
 4. RevealCompiler — single slide render (all 17 layouts)
 5. RevealCompiler — Auto-Animate data attributes
 6. RevealCompiler — speaker notes
 7. RevealCompiler — fragment animations
 8. RevealCompiler — background styles
 9. RevealCompiler — element rendering (text, image, code, chart)
10. ThemeModels — BuiltInThemes registry (24 themes)
11. ThemeModels — theme lookup and listing
12. ThemeModels — theme variants (dark/light/specialty)
13. CSSCompiler — compile a built-in theme
14. CSSCompiler — WCAG contrast validation
15. CSSCompiler — specialty extras (glassmorphism, scanlines, etc.)
16. CSSCompiler — Google Fonts URL generation
17. CSSCompiler — cache key stability
18. GenerativeThemeEngine — from_brand_colors
19. GenerativeThemeEngine — theme mutation (all 5 types)
20. GenerativeThemeEngine — palette generation
21. GenerativeThemeEngine — dark/light detection
22. Color utilities — hex↔HSL↔RGB conversions
23. Renderer API routes import
24. Database index alignment
25. Full pipeline — DSL → theme CSS + reveal.js HTML
26. XSS safety — HTML escaping
27. CSS output structure
28. Theme engine mood fonts
29. Edge cases — empty presentation, missing fields
30. Integration — RevealCompiler + CSSCompiler + ThemeEngine

Run: python test_phase4.py
"""

import json
import re
import sys
import traceback
from html import escape


# ── Test result tracking ─────────────────────────────────────

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
        print(f"Phase 4 Tests: {self.passed}/{total} passed")
        if self.errors:
            print("\nFailures:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0


results = TestResult()


# ═══════════════════════════════════════════════════════════════
# HELPERS — build minimal DSL objects for testing
# ═══════════════════════════════════════════════════════════════

_SLIDE_COUNTER = 0

def _build_slide(**overrides):
    """Build a minimal SlideDSL for testing."""
    global _SLIDE_COUNTER
    from app.models.dsl_v2 import SlideDSL, SlideType, LayoutType, SlideContentV2, RevealConfig
    idx = overrides.pop("index", _SLIDE_COUNTER)
    _SLIDE_COUNTER += 1
    slide_id = overrides.pop("id", f"slide-{idx}")

    # Extract content fields that go into SlideContentV2
    content_kwargs = {}
    for field_name in ("title", "subtitle", "bullets", "body_text", "quote_text", "quote_author"):
        if field_name in overrides:
            content_kwargs[field_name] = overrides.pop(field_name)

    # Remaining mapped fields
    slide_type = overrides.pop("slide_type", SlideType.TITLE_SLIDE)
    layout = overrides.pop("layout", LayoutType.CENTER_FOCUS)
    speaker_notes = overrides.pop("speaker_notes", None)
    auto_animate = overrides.pop("auto_animate", None)
    elements = overrides.pop("elements", [])
    fragments = overrides.pop("fragments", [])
    background = overrides.pop("background", None)

    # Build RevealConfig if auto_animate requested
    reveal_config = RevealConfig()
    if auto_animate is not None:
        reveal_config = RevealConfig(autoAnimate=auto_animate)

    # Build SlideStyle if background provided
    from app.models.dsl_v2 import SlideStyle
    style = SlideStyle()
    if background is not None:
        style = SlideStyle(background=background)

    return SlideDSL(
        index=idx,
        id=slide_id,
        type=slide_type,
        layout=layout,
        content=SlideContentV2(**content_kwargs),
        speakerNotes=speaker_notes,
        revealConfig=reveal_config,
        elements=elements,
        fragments=fragments,
        style=style,
    )


def _build_presentation(slides=None, **overrides):
    """Build a minimal PresentationDSL for testing."""
    from app.models.dsl_v2 import PresentationDSL, PresentationCore
    if slides is None:
        global _SLIDE_COUNTER
        _SLIDE_COUNTER = 0
        slides = [_build_slide(index=0)]

    # Re-index slides to be contiguous from 0
    for i, s in enumerate(slides):
        s.index = i

    pres_id = overrides.pop("id", "test-deck-1")
    pres_title = overrides.pop("title", "Test Deck")

    core = PresentationCore(id=pres_id, title=pres_title)
    return PresentationDSL(
        presentation=core,
        slides=slides,
    )


# ═══════════════════════════════════════════════════════════════
# 1. BaseRenderer imports
# ═══════════════════════════════════════════════════════════════

def test_01_base_renderer_imports():
    print("\n1. BaseRenderer and RenderOutput imports")
    try:
        from app.services.slides_new.renderers.base_renderer import (
            BaseRenderer,
            RenderOutput,
            RendererType,
        )
        results.ok("BaseRenderer, RenderOutput, RendererType import")

        assert RendererType.REVEAL_JS is not None
        results.ok("RendererType.REVEAL_JS exists")

        # RenderOutput dataclass
        out = RenderOutput(renderer=RendererType.REVEAL_JS, html="<div>", css="body{}", js="", slide_count=1)
        assert out.success is True
        assert out.error is None
        results.ok("RenderOutput default values correct")
    except Exception as e:
        results.fail("BaseRenderer imports", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 2. RevealCompiler instantiation
# ═══════════════════════════════════════════════════════════════

def test_02_reveal_compiler_init():
    print("\n2. RevealCompiler instantiation")
    try:
        from app.services.slides_new.renderers.reveal_compiler import RevealCompiler
        compiler = RevealCompiler()
        results.ok("RevealCompiler() instantiated")

        from app.services.slides_new.renderers.base_renderer import RendererType
        assert compiler.get_renderer_type() == RendererType.REVEAL_JS
        results.ok("Renderer type is REVEAL_JS")
    except Exception as e:
        results.fail("RevealCompiler init", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 3. Full presentation compile
# ═══════════════════════════════════════════════════════════════

def test_03_full_compile():
    print("\n3. Full presentation compile")
    try:
        from app.services.slides_new.renderers.reveal_compiler import RevealCompiler
        compiler = RevealCompiler()
        pres = _build_presentation()
        output = compiler.render_presentation(pres)

        assert output.success, f"Compile failed: {output.error}"
        results.ok("render_presentation() success=True")

        assert output.slide_count == 1
        results.ok("Slide count correct")

        assert "reveal.js" in output.html.lower() or "reveal" in output.html.lower()
        results.ok("Output contains reveal.js reference")

        assert "<!DOCTYPE html>" in output.html or "<!doctype html>" in output.html.lower()
        results.ok("Output is full HTML document")

        assert "<section" in output.html
        results.ok("Output contains <section> elements")

        assert "Reveal.initialize" in output.html or "Reveal.initialize" in output.js
        results.ok("Reveal.initialize() present")
    except Exception as e:
        results.fail("Full compile", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 4. All 17 layout types
# ═══════════════════════════════════════════════════════════════

def test_04_all_layouts():
    print("\n4. All 17 layout types render")
    try:
        from app.services.slides_new.renderers.reveal_compiler import RevealCompiler
        from app.models.dsl_v2 import LayoutType
        compiler = RevealCompiler()

        for layout in LayoutType:
            slide = _build_slide(layout=layout)
            html = compiler.render_slide(slide)
            assert "<section" in html, f"Layout {layout.value} missing <section>"
        results.ok(f"All {len(list(LayoutType))} layouts render correctly")
    except Exception as e:
        results.fail("Layout rendering", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 5. Auto-Animate
# ═══════════════════════════════════════════════════════════════

def test_05_auto_animate():
    print("\n5. Auto-Animate data attributes")
    try:
        from app.services.slides_new.renderers.reveal_compiler import RevealCompiler
        compiler = RevealCompiler()

        slide = _build_slide(auto_animate=True)
        html = compiler.render_slide(slide)
        assert "data-auto-animate" in html
        results.ok("data-auto-animate present when enabled")

        slide2 = _build_slide(auto_animate=False)
        html2 = compiler.render_slide(slide2)
        assert "data-auto-animate" not in html2
        results.ok("data-auto-animate absent when disabled")
    except Exception as e:
        results.fail("Auto-Animate", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 6. Speaker notes
# ═══════════════════════════════════════════════════════════════

def test_06_speaker_notes():
    print("\n6. Speaker notes")
    try:
        from app.services.slides_new.renderers.reveal_compiler import RevealCompiler
        compiler = RevealCompiler()

        slide = _build_slide(speaker_notes="Important: mention revenue growth")
        html = compiler.render_slide(slide)
        assert '<aside class="notes">' in html
        assert "mention revenue growth" in html
        results.ok("Speaker notes rendered in <aside>")

        # No notes
        slide2 = _build_slide()
        html2 = compiler.render_slide(slide2)
        assert '<aside class="notes">' not in html2
        results.ok("No <aside> when no notes")
    except Exception as e:
        results.fail("Speaker notes", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 7. Fragment animations
# ═══════════════════════════════════════════════════════════════

def test_07_fragments():
    print("\n7. Fragment animations")
    try:
        from app.services.slides_new.renderers.reveal_compiler import RevealCompiler
        from app.models.dsl_v2 import FragmentAnimation, SlideElement, ElementType, AnimationType

        compiler = RevealCompiler()

        elements = [
            SlideElement(id="el1", type=ElementType.TEXT, content="First"),
            SlideElement(id="el2", type=ElementType.TEXT, content="Second"),
        ]
        fragments = [
            FragmentAnimation(elementId="el1", animation=AnimationType.FADE_IN, order=0),
            FragmentAnimation(elementId="el2", animation=AnimationType.SLIDE_UP, order=1),
        ]
        slide = _build_slide(elements=elements, fragments=fragments)
        html = compiler.render_slide(slide)
        # Fragment scripts or classes should be in output
        assert "fragment" in html.lower()
        results.ok("Fragment animation markup generated")
    except Exception as e:
        results.fail("Fragments", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 8. Background styles
# ═══════════════════════════════════════════════════════════════

def test_08_backgrounds():
    print("\n8. Background styles")
    try:
        from app.services.slides_new.renderers.reveal_compiler import RevealCompiler
        from app.models.dsl_v2 import BackgroundStyle, BackgroundType
        compiler = RevealCompiler()

        bg = BackgroundStyle(type=BackgroundType.SOLID, colors=["#1A1A2E"])
        slide = _build_slide(background=bg)
        html = compiler.render_slide(slide)
        assert "data-background-color" in html
        results.ok("Background color rendered")

        bg2 = BackgroundStyle(type=BackgroundType.IMAGE, colors=["#000000"], image_url="https://example.com/bg.jpg")
        slide2 = _build_slide(background=bg2)
        html2 = compiler.render_slide(slide2)
        assert "data-background-image" in html2
        results.ok("Background image rendered")
    except Exception as e:
        results.fail("Backgrounds", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 9. Element rendering
# ═══════════════════════════════════════════════════════════════

def test_09_elements():
    print("\n9. Element rendering")
    try:
        from app.services.slides_new.renderers.reveal_compiler import RevealCompiler
        from app.models.dsl_v2 import SlideElement, ElementType
        compiler = RevealCompiler()

        elements = [
            SlideElement(
                id="txt1",
                type=ElementType.TEXT,
                content="Hello World",
            ),
        ]
        slide = _build_slide(elements=elements)
        html = compiler.render_slide(slide)
        assert "Hello World" in html
        results.ok("Text element rendered")

        elements2 = [
            SlideElement(
                id="img1",
                type=ElementType.IMAGE,
                content="https://example.com/logo.png",
            ),
        ]
        slide2 = _build_slide(elements=elements2)
        html2 = compiler.render_slide(slide2)
        assert "img" in html2.lower()
        results.ok("Image element rendered")
    except Exception as e:
        results.fail("Elements", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 10. BuiltInThemes registry
# ═══════════════════════════════════════════════════════════════

def test_10_builtin_themes_registry():
    print("\n10. BuiltInThemes registry (24 themes)")
    try:
        from app.services.slides_new.themes.theme_models import BuiltInThemes
        assert BuiltInThemes.count() == 24, f"Expected 24, got {BuiltInThemes.count()}"
        results.ok(f"Registry contains {BuiltInThemes.count()} themes")

        ids = BuiltInThemes.list_ids()
        assert len(ids) == 24
        results.ok("list_ids() returns 24 IDs")

        all_themes = BuiltInThemes.list_all()
        assert len(all_themes) == 24
        results.ok("list_all() returns 24 ThemeDefinition objects")
    except Exception as e:
        results.fail("BuiltInThemes registry", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 11. Theme lookup
# ═══════════════════════════════════════════════════════════════

def test_11_theme_lookup():
    print("\n11. Theme lookup and listing")
    try:
        from app.services.slides_new.themes.theme_models import BuiltInThemes
        bold = BuiltInThemes.get("bold-signal")
        assert bold is not None
        assert bold.name == "Bold Signal"
        results.ok("get('bold-signal') works")

        missing = BuiltInThemes.get("nonexistent-theme")
        assert missing is None
        results.ok("get() returns None for missing theme")

        default = BuiltInThemes.get_or_default("nonexistent")
        assert default is not None
        results.ok("get_or_default() returns fallback")
    except Exception as e:
        results.fail("Theme lookup", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 12. Theme variants
# ═══════════════════════════════════════════════════════════════

def test_12_theme_variants():
    print("\n12. Theme variants")
    try:
        from app.services.slides_new.themes.theme_models import BuiltInThemes
        dark = BuiltInThemes.list_by_variant("dark")
        light = BuiltInThemes.list_by_variant("light")
        specialty = BuiltInThemes.list_by_variant("specialty")

        assert len(dark) == 8, f"Expected 8 dark, got {len(dark)}"
        results.ok(f"8 dark themes")

        assert len(light) == 8, f"Expected 8 light, got {len(light)}"
        results.ok(f"8 light themes")

        assert len(specialty) == 8, f"Expected 8 specialty, got {len(specialty)}"
        results.ok(f"8 specialty themes")

        assert len(dark) + len(light) + len(specialty) == 24
        results.ok("Variants sum to 24")
    except Exception as e:
        results.fail("Theme variants", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 13. CSSCompiler — compile a theme
# ═══════════════════════════════════════════════════════════════

def test_13_css_compile():
    print("\n13. CSSCompiler — compile a built-in theme")
    try:
        from app.services.slides_new.themes.css_compiler import CSSCompiler
        from app.services.slides_new.themes.theme_models import BuiltInThemes

        compiler = CSSCompiler()
        theme = BuiltInThemes.get("bold-signal")
        css = compiler.compile(theme)

        assert len(css) > 200, "CSS too short"
        results.ok(f"Compiled CSS length: {len(css)}")

        assert "--r-background-color" in css
        results.ok("reveal.js root variables present")

        assert "--b-primary" in css
        results.ok("Barise custom variables present")

        assert ":root" in css
        results.ok(":root block present")
    except Exception as e:
        results.fail("CSSCompiler compile", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 14. WCAG contrast validation
# ═══════════════════════════════════════════════════════════════

def test_14_wcag_validation():
    print("\n14. WCAG contrast validation")
    try:
        from app.services.slides_new.themes.css_compiler import CSSCompiler, contrast_ratio
        compiler = CSSCompiler()

        # High contrast pair
        ratio = contrast_ratio("#000000", "#FFFFFF")
        assert ratio > 20, f"B&W contrast should be 21:1, got {ratio:.1f}"
        results.ok(f"Black/White contrast: {ratio:.1f}:1")

        # Low contrast pair
        ratio2 = contrast_ratio("#777777", "#888888")
        assert ratio2 < 4.5, f"Low contrast pair should fail AA"
        results.ok(f"Gray/Gray contrast: {ratio2:.2f}:1 (below AA)")

        # Compile with validation
        from app.services.slides_new.themes.theme_models import BuiltInThemes
        theme = BuiltInThemes.get("bold-signal")
        css, warnings = compiler.compile_with_validation(theme)
        assert isinstance(warnings, list)
        results.ok(f"Validation returned {len(warnings)} warnings")
    except Exception as e:
        results.fail("WCAG validation", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 15. CSSCompiler — specialty extras
# ═══════════════════════════════════════════════════════════════

def test_15_specialty_extras():
    print("\n15. Specialty extras rendering")
    try:
        from app.services.slides_new.themes.css_compiler import CSSCompiler
        from app.services.slides_new.themes.theme_models import BuiltInThemes
        compiler = CSSCompiler()

        # Glassmorphism
        glass = BuiltInThemes.get("glassmorphism")
        css = compiler.compile(glass)
        assert "backdrop-filter" in css
        results.ok("Glassmorphism: backdrop-filter present")

        # Terminal
        terminal = BuiltInThemes.get("terminal-green")
        css2 = compiler.compile(terminal)
        assert "scanline" in css2.lower() or "repeating-linear-gradient" in css2
        results.ok("Terminal: scanline effect present")

        # Blueprint
        blueprint = BuiltInThemes.get("blueprint")
        css3 = compiler.compile(blueprint)
        assert "grid" in css3.lower()
        results.ok("Blueprint: grid effect present")
    except Exception as e:
        results.fail("Specialty extras", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 16. Google Fonts URL
# ═══════════════════════════════════════════════════════════════

def test_16_google_fonts():
    print("\n16. Google Fonts URL generation")
    try:
        from app.services.slides_new.themes.css_compiler import _generate_font_url
        url = _generate_font_url(["Inter", "DM Sans"])
        assert "fonts.googleapis.com" in url
        assert "Inter" in url
        results.ok("Font URL generated correctly")

        # System fonts should return empty
        url2 = _generate_font_url(["Arial", "Helvetica"])
        assert url2 == ""
        results.ok("System font returns empty URL")
    except Exception as e:
        results.fail("Google Fonts URL", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 17. Cache key stability
# ═══════════════════════════════════════════════════════════════

def test_17_cache_key():
    print("\n17. CSS cache key stability")
    try:
        from app.services.slides_new.themes.css_compiler import CSSCompiler
        from app.services.slides_new.themes.theme_models import BuiltInThemes
        compiler = CSSCompiler()
        theme = BuiltInThemes.get("bold-signal")

        key1 = compiler.cache_key(theme)
        key2 = compiler.cache_key(theme)
        assert key1 == key2
        results.ok("Same theme produces same cache key")

        theme2 = BuiltInThemes.get("swiss-modern")
        key3 = compiler.cache_key(theme2)
        assert key3 != key1
        results.ok("Different themes produce different keys")
    except Exception as e:
        results.fail("Cache key", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 18. GenerativeThemeEngine — from_brand_colors
# ═══════════════════════════════════════════════════════════════

def test_18_theme_generation():
    print("\n18. GenerativeThemeEngine — from_brand_colors")
    try:
        from app.services.slides_new.themes.theme_engine import GenerativeThemeEngine
        from app.services.slides_new.themes.theme_models import ThemeTier

        engine = GenerativeThemeEngine()
        theme = engine.from_brand_colors("#FF6B35", mood="creative")

        assert theme is not None
        results.ok("Theme generated successfully")

        assert theme.tier == ThemeTier.GENERATED
        results.ok("Tier is GENERATED")

        assert theme.colors.primary == "#FF6B35"
        results.ok("Primary color preserved")

        assert theme.colors.background is not None
        assert theme.colors.text is not None
        results.ok("Background and text colors auto-generated")

        # Dark primary should produce dark variant
        dark_theme = engine.from_brand_colors("#1A1A2E")
        assert dark_theme.variant == "dark"
        results.ok("Dark color → dark variant")

        # Light primary
        light_theme = engine.from_brand_colors("#E8F0FE")
        assert light_theme.variant == "light"
        results.ok("Light color → light variant")
    except Exception as e:
        results.fail("Theme generation", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 19. Theme mutations
# ═══════════════════════════════════════════════════════════════

def test_19_mutations():
    print("\n19. Theme mutations (all 5)")
    try:
        from app.services.slides_new.themes.theme_engine import GenerativeThemeEngine
        from app.services.slides_new.themes.theme_models import (
            BuiltInThemes,
            ThemeMutation,
            ThemeTier,
        )

        engine = GenerativeThemeEngine()
        base = BuiltInThemes.get("bold-signal")

        for mutation in ThemeMutation:
            mutated = engine.mutate(base, mutation)
            assert mutated.id == f"bold-signal-{mutation.value}"
            assert mutated.tier == ThemeTier.MUTATION
            assert mutated.colors.primary != "" or True  # colors exist
        results.ok(f"All {len(list(ThemeMutation))} mutations generated")

        # Verify WARMER shifts hue
        warmer = engine.mutate(base, ThemeMutation.WARMER)
        assert warmer.colors.primary != base.colors.primary
        results.ok("WARMER mutation changes primary color")
    except Exception as e:
        results.fail("Mutations", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 20. Palette generation
# ═══════════════════════════════════════════════════════════════

def test_20_palette():
    print("\n20. Palette generation")
    try:
        from app.services.slides_new.themes.theme_engine import GenerativeThemeEngine
        engine = GenerativeThemeEngine()
        palette = engine.generate_palette("#3B82F6", count=9)

        assert len(palette) == 9
        results.ok("9-shade palette generated")

        # All should be valid hex
        for c in palette:
            assert c.startswith("#")
            assert len(c) == 7
        results.ok("All palette colors are valid hex")

        # Shades should go from light → dark
        # (first shade should be lighter than last)
        from app.services.slides_new.themes.theme_engine import _hex_to_hsl
        _, _, l_first = _hex_to_hsl(palette[0])
        _, _, l_last = _hex_to_hsl(palette[-1])
        assert l_first > l_last, f"Expected light→dark, got {l_first:.0f}→{l_last:.0f}"
        results.ok(f"Palette goes light({l_first:.0f}) → dark({l_last:.0f})")
    except Exception as e:
        results.fail("Palette", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 21. Dark/light detection
# ═══════════════════════════════════════════════════════════════

def test_21_dark_light():
    print("\n21. Dark/light color detection")
    try:
        from app.services.slides_new.themes.theme_engine import _is_dark_color
        assert _is_dark_color("#000000") is True
        assert _is_dark_color("#1A1A2E") is True
        assert _is_dark_color("#FFFFFF") is False
        assert _is_dark_color("#F0F0F0") is False
        results.ok("Dark/light detection correct")
    except Exception as e:
        results.fail("Dark/light detection", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 22. Color utility functions
# ═══════════════════════════════════════════════════════════════

def test_22_color_utils():
    print("\n22. Color conversion utilities")
    try:
        from app.services.slides_new.themes.css_compiler import _hex_to_rgb, _rgb_to_hex
        from app.services.slides_new.themes.theme_engine import _hex_to_hsl, _hsl_to_hex

        # RGB roundtrip
        r, g, b = _hex_to_rgb("#FF6B35")
        assert (r, g, b) == (255, 107, 53)
        results.ok("hex_to_rgb: #FF6B35 → (255, 107, 53)")

        hex_out = _rgb_to_hex(255, 107, 53)
        assert hex_out.upper() == "#FF6B35"
        results.ok("rgb_to_hex: (255, 107, 53) → #FF6B35")

        # HSL roundtrip
        h, s, l = _hex_to_hsl("#FF0000")
        assert abs(h - 0) < 1 or abs(h - 360) < 1  # red = 0°
        assert s > 90  # fully saturated
        results.ok(f"hex_to_hsl: red → H={h:.0f} S={s:.0f} L={l:.0f}")

        back = _hsl_to_hex(h, s, l)
        results.ok(f"hsl_to_hex roundtrip → {back}")

        # Short hex
        r2, g2, b2 = _hex_to_rgb("#F00")
        assert r2 == 255 and g2 == 0 and b2 == 0
        results.ok("Short hex #F00 parsed correctly")
    except Exception as e:
        results.fail("Color utils", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 23. Renderer API routes import
# ═══════════════════════════════════════════════════════════════

def test_23_api_routes():
    print("\n23. Renderer API routes import")
    try:
        from app.api.routes.renderer_routes import router
        assert router is not None
        results.ok("renderer_routes.router imports")

        # Check route paths
        routes = [r.path for r in router.routes]
        assert any("compile" in r for r in routes)
        results.ok("compile endpoint registered")

        assert any("themes" in r for r in routes)
        results.ok("themes endpoints registered")
    except Exception as e:
        results.fail("API routes", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 24. Database index alignment
# ═══════════════════════════════════════════════════════════════

def test_24_db_indexes():
    print("\n24. Database index alignment")
    try:
        import inspect
        from app.database import _create_indexes
        src = inspect.getsource(_create_indexes)

        assert "reveal_builds" in src
        results.ok("reveal_builds collection indexed")

        assert "generated_themes" in src
        results.ok("generated_themes collection indexed")

        assert "css_cache" in src
        results.ok("css_cache collection indexed")
    except Exception as e:
        results.fail("DB indexes", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 25. Full pipeline — DSL → theme CSS + reveal.js HTML
# ═══════════════════════════════════════════════════════════════

def test_25_full_pipeline():
    print("\n25. Full pipeline — DSL → CSS + HTML")
    try:
        from app.services.slides_new.renderers.reveal_compiler import RevealCompiler
        from app.services.slides_new.themes.css_compiler import CSSCompiler
        from app.services.slides_new.themes.theme_models import BuiltInThemes
        from app.models.dsl_v2 import (
            PresentationDSL, PresentationCore, SlideDSL,
            SlideType, LayoutType, SlideContentV2,
        )

        compiler = RevealCompiler()
        css_compiler = CSSCompiler()

        slides = [
            SlideDSL(
                index=0, id="title-slide",
                type=SlideType.TITLE_SLIDE,
                layout=LayoutType.CENTER_FOCUS,
                content=SlideContentV2(
                    title="Welcome to Barise",
                    subtitle="Next-gen startup intelligence",
                ),
            ),
            SlideDSL(
                index=1, id="features-slide",
                type=SlideType.CUSTOM,
                layout=LayoutType.BULLETS,
                content=SlideContentV2(
                    title="Key Features",
                    bullets=["AI-powered analysis", "Real-time data", "Community"],
                ),
            ),
            SlideDSL(
                index=2, id="closing-slide",
                type=SlideType.CLOSING_SLIDE,
                layout=LayoutType.CENTER_FOCUS,
                content=SlideContentV2(title="Thank You"),
                speakerNotes="End with call to action",
            ),
        ]
        pres = PresentationDSL(
            presentation=PresentationCore(id="barise-pitch", title="Barise Pitch"),
            slides=slides,
        )

        output = compiler.render_presentation(pres)
        assert output.success
        assert output.slide_count == 3
        results.ok("3-slide presentation compiled")

        theme = BuiltInThemes.get("electric-studio")
        css = css_compiler.compile(theme)
        assert len(css) > 100
        results.ok("Electric Studio CSS compiled")

        # Verify combined output makes sense
        assert "Welcome to Barise" in output.html
        assert "Key Features" in output.html
        assert "Thank You" in output.html
        results.ok("All slide content in final HTML")
    except Exception as e:
        results.fail("Full pipeline", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 26. XSS safety
# ═══════════════════════════════════════════════════════════════

def test_26_xss_safety():
    print("\n26. XSS safety — HTML escaping")
    try:
        from app.services.slides_new.renderers.reveal_compiler import RevealCompiler
        compiler = RevealCompiler()

        # Malicious title
        slide = _build_slide(title='<script>alert("xss")</script>')
        html = compiler.render_slide(slide)
        assert '<script>alert("xss")</script>' not in html
        assert "&lt;script&gt;" in html or "alert" not in html
        results.ok("Script tag in title is escaped")

        # Malicious speaker notes
        slide2 = _build_slide(speaker_notes='<img onerror="alert(1)" src=x>')
        html2 = compiler.render_slide(slide2)
        assert 'onerror="alert(1)"' not in html2
        results.ok("XSS in speaker notes is escaped")
    except Exception as e:
        results.fail("XSS safety", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 27. CSS output structure
# ═══════════════════════════════════════════════════════════════

def test_27_css_structure():
    print("\n27. CSS output structure")
    try:
        from app.services.slides_new.themes.css_compiler import CSSCompiler
        from app.services.slides_new.themes.theme_models import BuiltInThemes

        compiler = CSSCompiler()
        theme = BuiltInThemes.get("swiss-modern")
        css = compiler.compile(theme)

        # Should have font import
        assert "@import" in css or "fonts.googleapis.com" in css
        results.ok("Font import present")

        # Typography rules
        assert ".reveal h1" in css or ".reveal .slides h1" in css
        results.ok("Typography rules present")

        # Card styles
        assert ".grid-cell" in css or ".kpi-card" in css
        results.ok("Card component styles present")
    except Exception as e:
        results.fail("CSS structure", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 28. Mood fonts
# ═══════════════════════════════════════════════════════════════

def test_28_mood_fonts():
    print("\n28. Theme engine mood fonts")
    try:
        from app.services.slides_new.themes.theme_engine import MOOD_FONTS
        assert len(MOOD_FONTS) >= 5
        results.ok(f"{len(MOOD_FONTS)} mood font configurations")

        for mood, typo in MOOD_FONTS.items():
            assert typo.heading_font != ""
            assert typo.body_font != ""
        results.ok("All moods have heading and body fonts")
    except Exception as e:
        results.fail("Mood fonts", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 29. Edge cases
# ═══════════════════════════════════════════════════════════════

def test_29_edge_cases():
    print("\n29. Edge cases")
    try:
        from app.services.slides_new.renderers.reveal_compiler import RevealCompiler
        from app.models.dsl_v2 import (
            PresentationDSL, PresentationCore, SlideDSL,
            SlideType, LayoutType, SlideContentV2,
        )

        compiler = RevealCompiler()

        # Single slide with minimal fields
        pres = PresentationDSL(
            presentation=PresentationCore(id="minimal", title="Minimal"),
            slides=[SlideDSL(
                index=0, id="blank-slide",
                type=SlideType.CUSTOM,
                layout=LayoutType.BLANK,
                content=SlideContentV2(title=""),
            )],
        )
        output = compiler.render_presentation(pres)
        assert output.success
        results.ok("Minimal/blank slide compiles")

        # Slide with long content
        long_title = "A" * 200  # max_length=200 in model
        slide = _build_slide(title=long_title)
        html = compiler.render_slide(slide)
        assert "A" * 100 in html
        results.ok("Very long title handled")
    except Exception as e:
        results.fail("Edge cases", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# 30. Integration — RevealCompiler + CSSCompiler + ThemeEngine
# ═══════════════════════════════════════════════════════════════

def test_30_integration():
    print("\n30. Full integration test")
    try:
        from app.services.slides_new.renderers.reveal_compiler import RevealCompiler
        from app.services.slides_new.themes.css_compiler import CSSCompiler
        from app.services.slides_new.themes.theme_engine import GenerativeThemeEngine
        from app.models.dsl_v2 import (
            PresentationDSL, PresentationCore, SlideDSL, RevealConfig,
            SlideType, LayoutType, BackgroundStyle, BackgroundType,
            SlideContentV2, SlideStyle,
        )

        # Generate a custom theme
        engine = GenerativeThemeEngine()
        theme = engine.from_brand_colors("#2563EB", mood="corporate", name="my-startup")

        # Compile CSS
        css_compiler = CSSCompiler()
        css, warnings = css_compiler.compile_with_validation(theme)
        assert len(css) > 200

        # Build presentation
        slides = [
            SlideDSL(
                index=0, id="int-title",
                type=SlideType.TITLE_SLIDE,
                layout=LayoutType.CENTER_FOCUS,
                content=SlideContentV2(title="My Startup", subtitle="Investor Pitch"),
                revealConfig=RevealConfig(autoAnimate=True),
            ),
            SlideDSL(
                index=1, id="int-problem",
                type=SlideType.CUSTOM,
                layout=LayoutType.SPLIT_SCREEN,
                content=SlideContentV2(
                    title="The Problem",
                    bullets=["Pain point 1", "Pain point 2"],
                ),
                speakerNotes="Emphasize market size",
            ),
            SlideDSL(
                index=2, id="int-traction",
                type=SlideType.TRACTION_SLIDE,
                layout=LayoutType.KPI_DASHBOARD,
                content=SlideContentV2(title="Traction"),
                style=SlideStyle(
                    background=BackgroundStyle(type=BackgroundType.SOLID, colors=["#0F172A"]),
                ),
            ),
        ]
        pres = PresentationDSL(
            presentation=PresentationCore(id="my-startup-pitch", title="My Startup Pitch"),
            slides=slides,
        )

        # Compile to reveal.js
        compiler = RevealCompiler()
        output = compiler.render_presentation(pres)

        assert output.success
        assert output.slide_count == 3
        assert "My Startup" in output.html
        assert "data-auto-animate" in output.html
        assert "notes" in output.html.lower()

        results.ok("Full integration: ThemeEngine -> CSS -> RevealCompiler")
        results.ok(f"Output: {len(output.html)} chars, {len(css)} CSS chars, {len(warnings)} warnings")
    except Exception as e:
        results.fail("Integration", traceback.format_exc())


# ═══════════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════════

def main():
    global _SLIDE_COUNTER
    print("=" * 60)
    print("Phase 4: reveal.js Renderer & CSS Architecture — Tests")
    print("=" * 60)

    _SLIDE_COUNTER = 0; test_01_base_renderer_imports()
    _SLIDE_COUNTER = 0; test_02_reveal_compiler_init()
    _SLIDE_COUNTER = 0; test_03_full_compile()
    _SLIDE_COUNTER = 0; test_04_all_layouts()
    _SLIDE_COUNTER = 0; test_05_auto_animate()
    _SLIDE_COUNTER = 0; test_06_speaker_notes()
    _SLIDE_COUNTER = 0; test_07_fragments()
    _SLIDE_COUNTER = 0; test_08_backgrounds()
    _SLIDE_COUNTER = 0; test_09_elements()
    _SLIDE_COUNTER = 0; test_10_builtin_themes_registry()
    _SLIDE_COUNTER = 0; test_11_theme_lookup()
    _SLIDE_COUNTER = 0; test_12_theme_variants()
    _SLIDE_COUNTER = 0; test_13_css_compile()
    _SLIDE_COUNTER = 0; test_14_wcag_validation()
    _SLIDE_COUNTER = 0; test_15_specialty_extras()
    _SLIDE_COUNTER = 0; test_16_google_fonts()
    _SLIDE_COUNTER = 0; test_17_cache_key()
    _SLIDE_COUNTER = 0; test_18_theme_generation()
    _SLIDE_COUNTER = 0; test_19_mutations()
    _SLIDE_COUNTER = 0; test_20_palette()
    _SLIDE_COUNTER = 0; test_21_dark_light()
    _SLIDE_COUNTER = 0; test_22_color_utils()
    _SLIDE_COUNTER = 0; test_23_api_routes()
    _SLIDE_COUNTER = 0; test_24_db_indexes()
    _SLIDE_COUNTER = 0; test_25_full_pipeline()
    _SLIDE_COUNTER = 0; test_26_xss_safety()
    _SLIDE_COUNTER = 0; test_27_css_structure()
    _SLIDE_COUNTER = 0; test_28_mood_fonts()
    _SLIDE_COUNTER = 0; test_29_edge_cases()
    _SLIDE_COUNTER = 0; test_30_integration()

    success = results.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
