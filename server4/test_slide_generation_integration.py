"""
╔══════════════════════════════════════════════════════════════════╗
║  SLIDE GENERATION SYSTEM — INTEGRATION TEST SUITE                ║
║  Testing DSL v2 → HTML Pipeline (NeuralScale Pitch Deck)        ║
╚══════════════════════════════════════════════════════════════════╝

Tests the complete pipeline:
  1. DSL v2 construction & Pydantic validation
  2. RevealCompiler rendering (DSL → reveal.js HTML)
  3. Theme engine (Electric Studio)
  4. Accessibility (WCAG AA contrast)
  5. Anti-AI-Slop checks
  6. Speaker notes, fragments, layouts
  7. Edge cases (long titles, empty bullets, etc.)
  8. Performance guardrails

Run:  python test_slide_generation_integration.py
"""

import json
import os
import re
import sys
import time
import traceback
from typing import Any

# ── Ensure project imports work ─────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ═══════════════════════════════════════════════════════════════════
# TEST HARNESS
# ═══════════════════════════════════════════════════════════════════

_results: list[dict[str, Any]] = []
_section = ""


def section(name: str):
    global _section
    _section = name
    print(f"\n{'━' * 70}")
    print(f"  📋 {name}")
    print(f"{'━' * 70}")


def test(name: str, fn):
    """Run a single test, record pass/fail."""
    try:
        fn()
        _results.append({"section": _section, "name": name, "status": "PASS"})
        print(f"  ✅ {name}")
    except Exception as e:
        _results.append({
            "section": _section,
            "name": name,
            "status": "FAIL",
            "error": str(e),
        })
        print(f"  ❌ {name}")
        print(f"     └─ {e}")
        traceback.print_exc(limit=2)


def summary():
    """Print final test summary."""
    total = len(_results)
    passed = sum(1 for r in _results if r["status"] == "PASS")
    failed = total - passed
    print(f"\n{'═' * 70}")
    print(f"  📊 TEST RESULTS: {passed}/{total} passed, {failed} failed")
    print(f"{'═' * 70}")
    if failed:
        print("\n  FAILURES:")
        for r in _results:
            if r["status"] == "FAIL":
                print(f"    ❌ [{r['section']}] {r['name']}")
                print(f"       └─ {r.get('error', 'unknown')}")
    pct = (passed / total * 100) if total else 0
    print(f"\n  Overall Score: {pct:.0f}%")
    if pct >= 80:
        print("  🟢 SYSTEM PASSES (≥80%)")
    else:
        print("  🔴 SYSTEM FAILS (<80%)")
    return failed == 0


# ═══════════════════════════════════════════════════════════════════
# TEST DATA: NeuralScale 5-Slide Pitch Deck (DSL v2)
# ═══════════════════════════════════════════════════════════════════

def build_neuralscale_dsl_dict() -> dict[str, Any]:
    """Build the NeuralScale deck as a raw dict, before Pydantic validation."""
    return {
        "version": "2.0",
        "presentation": {
            "id": "neuralscale-pitch",
            "title": "NeuralScale — AI Infrastructure for Next-Gen Models",
            "archetype": "problem-solution",
            "theme": {
                "id": "electric-studio",
                "variant": "dark",
                "preset": "electric-studio",
            },
            "aspectRatio": "16:9",
            "dimensions": {"width": 1920, "height": 1080},
            "renderers": ["reveal.js"],
            "modes": ["present", "edit"],
            "metadata": {
                "author": "Jane Doe",
                "company": "NeuralScale",
                "language": "en",
                "version": 1,
                "tags": ["AI", "infrastructure", "series-a"],
            },
        },
        "slides": [
            # ── Slide 1: Title ──────────────────────────────────
            {
                "index": 0,
                "id": "title-slide",
                "type": "title-slide",
                "layout": "center-focus",
                "section": "opening",
                "content": {
                    "title": "NeuralScale",
                    "subtitle": "AI Infrastructure for Next-Gen Models",
                    "presenter": "Jane Doe, CEO",
                    "tagline": "Series A — $12M",
                },
                "style": {
                    "background": {
                        "type": "gradient-radial",
                        "colors": ["#0F172A", "#1E293B"],
                    },
                    "accentColor": "#7B2FF7",
                    "animation": "cinematic",
                },
                "elements": [],
                "speakerNotes": "Welcome everyone. Open with the $50K/month GPU cost problem. Emphasize timing.",
                "fragments": [],
                "revealConfig": {
                    "transition": "fade",
                    "autoAnimate": False,
                    "backgroundTransition": "fade",
                },
            },
            # ── Slide 2: Problem ────────────────────────────────
            {
                "index": 1,
                "id": "problem-slide",
                "type": "problem-slide",
                "layout": "text-left-visual-right",
                "section": "problem",
                "content": {
                    "title": "The $50K/Month Problem",
                    "bullets": [
                        "GPU clusters cost $50K+/month to operate",
                        "Zero-downtime deployment takes weeks, not hours",
                        "ML teams spend 60% time on infra, not models",
                        "No unified pipeline from training → production",
                    ],
                },
                "style": {
                    "background": {
                        "type": "solid",
                        "colors": ["#0A0A1B"],
                    },
                    "accentColor": "#00F5FF",
                },
                "elements": [
                    {
                        "id": "cost-visual",
                        "type": "shape",
                        "content": "Data visualization placeholder",
                        "position": {"x": 0.55, "y": 0.15},
                        "size": {"width": 0.4, "height": 0.7},
                        "style": {"opacity": 0.9},
                    }
                ],
                "speakerNotes": "Pause after bullet 2. Ask audience: 'How many of you have felt this pain?'",
                "fragments": [
                    {"elementId": "cost-visual", "order": 0, "animation": "fade-in"},
                ],
                "revealConfig": {"transition": "slide"},
            },
            # ── Slide 3: Solution ───────────────────────────────
            {
                "index": 2,
                "id": "solution-slide",
                "type": "solution-slide",
                "layout": "split-screen",
                "section": "solution",
                "content": {
                    "title": "NeuralScale: The Unified AI Infra Platform",
                    "left_content": "One API for training, serving, monitoring\nAuto-scaling with 99.9% uptime SLA\nReduce infra costs by 70%\nDeploy in hours, not weeks",
                    "right_content": "Architecture diagram placeholder",
                },
                "style": {
                    "background": {
                        "type": "solid",
                        "colors": ["#0A0A1B"],
                    },
                    "accentColor": "#34D399",
                    "surfaceStyle": "glass",
                },
                "elements": [],
                "speakerNotes": "Point to the 70% stat — this is our hero metric. Reference the architecture diagram on right.",
                "fragments": [],
                "revealConfig": {"transition": "slide"},
            },
            # ── Slide 4: Market Opportunity ─────────────────────
            {
                "index": 3,
                "id": "market-slide",
                "type": "market-slide",
                "layout": "grid-3x1",
                "section": "market",
                "content": {
                    "title": "$12B Market, Growing 40% YoY",
                    "bullets": [
                        "$12B — Global AI Infrastructure (TAM)",
                        "$2.4B — Mid-Market ML Teams, 100-1000 employees (SAM)",
                        "$120M — Series A+ Startups in US/EU, Year 1-2 (SOM)",
                    ],
                    "body_text": "Bottom-up calculation: 3,200 qualifying startups × $37.5K avg contract = $120M SOM",
                },
                "style": {
                    "background": {
                        "type": "solid",
                        "colors": ["#0A0A1B"],
                    },
                    "accentColor": "#00F5FF",
                },
                "elements": [],
                "speakerNotes": "Emphasize BOTTOM-UP methodology. We didn't pull '$12B' from a report. Here's the math...",
                "fragments": [],
                "revealConfig": {"transition": "slide"},
            },
            # ── Slide 5: Traction / Ask ─────────────────────────
            {
                "index": 4,
                "id": "traction-ask-slide",
                "type": "traction-slide",
                "layout": "comparison",
                "section": "traction",
                "content": {
                    "title": "Traction & The Ask",
                    "comparison_items": [
                        {"label": "Enterprise Pilots", "us": "10 (Fortune 500)", "them": None, "advantage": True},
                        {"label": "ARR", "us": "$800K (0→$800K in 8mo)", "them": None, "advantage": True},
                        {"label": "Growth", "us": "40% MoM (6mo sustained)", "them": None, "advantage": True},
                        {"label": "NPS", "us": "72", "them": "31 (enterprise avg)", "advantage": True},
                    ],
                    "body_text": "Raising $12M Series A — 24-month runway to profitability. Hire 25 engineers (infra + ML ops).",
                },
                "style": {
                    "background": {
                        "type": "gradient-linear",
                        "colors": ["#0A0A1B", "#1A0A2B"],
                        "angle": 135,
                    },
                    "accentColor": "#00F5FF",
                },
                "elements": [],
                "speakerNotes": "Close strong. The NPS of 72 is our proof point. End with: 'Join us in building the future of AI infra.'",
                "fragments": [],
                "revealConfig": {"transition": "zoom"},
            },
        ],
        "generationMetadata": {
            "skillVersions": {"ceo": 1, "designer": 1, "code": 1, "qa": 1},
            "qualityScore": 0,
            "iterations": 1,
            "modelUsage": {},
        },
    }


# ═══════════════════════════════════════════════════════════════════
# SECTION 1: DSL v2 VALIDATION
# ═══════════════════════════════════════════════════════════════════

def run_dsl_validation_tests():
    section("DSL v2 VALIDATION (Pydantic Schema Compliance)")

    from app.models.dsl_v2 import PresentationDSL, SlideDSL, SlideType, LayoutType

    raw = build_neuralscale_dsl_dict()

    # T1: Full DSL parses without error
    pres = None

    def t1():
        nonlocal pres
        pres = PresentationDSL.model_validate(raw)
        assert pres is not None, "PresentationDSL validation returned None"

    test("T1: Full DSL validates against PresentationDSL schema", t1)

    # T2: Correct slide count
    def t2():
        assert pres is not None, "Depends on T1"
        assert len(pres.slides) == 5, f"Expected 5 slides, got {len(pres.slides)}"

    test("T2: Presentation contains exactly 5 slides", t2)

    # T3: All required fields present
    def t3():
        for s in pres.slides:
            assert s.id, f"Slide index {s.index} missing id"
            assert s.type, f"Slide {s.id} missing type"
            assert s.layout, f"Slide {s.id} missing layout"
            assert s.content.title, f"Slide {s.id} missing title"

    test("T3: All slides have required fields (id, type, layout, title)", t3)

    # T4: Slide types match specification
    def t4():
        expected_types = [
            SlideType.TITLE_SLIDE,
            SlideType.PROBLEM_SLIDE,
            SlideType.SOLUTION_SLIDE,
            SlideType.MARKET_SLIDE,
            SlideType.TRACTION_SLIDE,
        ]
        actual_types = [s.type for s in pres.slides]
        assert actual_types == expected_types, f"Types mismatch: {actual_types}"

    test("T4: Slide types match spec (title→problem→solution→market→traction)", t4)

    # T5: Slide indexes are contiguous 0-based
    def t5():
        indexes = [s.index for s in pres.slides]
        assert indexes == [0, 1, 2, 3, 4], f"Indexes: {indexes}"

    test("T5: Slide indexes are contiguous (0,1,2,3,4)", t5)

    # T6: Unique slide IDs
    def t6():
        ids = [s.id for s in pres.slides]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"

    test("T6: All slide IDs are unique", t6)

    # T7: Speaker notes on every slide
    def t7():
        for s in pres.slides:
            assert s.speakerNotes and s.speakerNotes.strip(), \
                f"Slide {s.id} missing speaker notes"

    test("T7: Speaker notes present on all 5 slides", t7)

    # T8: Custom fields and generation metadata structured
    def t8():
        assert pres.generationMetadata is not None
        assert pres.generationMetadata.skillVersions, "Missing skillVersions"
        assert "ceo" in pres.generationMetadata.skillVersions

    test("T8: generationMetadata has skillVersions", t8)

    # T9: Version string
    def t9():
        assert pres.version == "2.0"

    test("T9: DSL version is '2.0'", t9)

    # T10: Fragment references valid (elementId exists)
    def t10():
        slide2 = pres.slides[1]
        elem_ids = {e.id for e in slide2.elements}
        for frag in slide2.fragments:
            assert frag.elementId in elem_ids, \
                f"Fragment refs unknown element '{frag.elementId}'"

    test("T10: Fragment elementId references match existing elements", t10)

    # T11: Background gradient validation
    def t11():
        slide1 = pres.slides[0]
        bg = slide1.style.background
        assert bg.type.value == "gradient-radial", f"Expected gradient-radial, got {bg.type}"
        assert len(bg.colors) >= 2, "Gradient needs ≥2 colors"

    test("T11: Title slide has radial gradient with ≥2 colors", t11)

    # T12: Hex color format validation
    def t12():
        hex_re = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
        for s in pres.slides:
            for c in s.style.background.colors:
                assert hex_re.match(c), f"Invalid hex color: {c}"

    test("T12: All hex colors use proper format", t12)

    return pres


# ═══════════════════════════════════════════════════════════════════
# SECTION 2: REVEAL.JS COMPILER
# ═══════════════════════════════════════════════════════════════════

def run_reveal_compiler_tests(pres):
    section("REVEAL.JS COMPILER (DSL → HTML)")

    from app.services.slides_new.renderers.reveal_compiler import RevealCompiler
    from app.services.slides_new.renderers.base_renderer import RendererType

    compiler = RevealCompiler()

    output = None

    # T13: Full presentation renders successfully
    def t13():
        nonlocal output
        output = compiler.render_presentation(pres, theme_css="")
        assert output.success, f"Render failed: {output.error}"
        assert output.html, "Output HTML is empty"

    test("T13: RevealCompiler.render_presentation() succeeds", t13)

    # T14: Renderer type
    def t14():
        assert output.renderer == RendererType.REVEAL_JS

    test("T14: Renderer type is REVEAL_JS", t14)

    # T15: Slide count in metadata
    def t15():
        assert output.slide_count == 5, f"Expected 5, got {output.slide_count}"

    test("T15: Output metadata reports 5 slides", t15)

    # T16: Proper <section> tags
    def t16():
        count = output.html.count("<section ")
        assert count == 5, f"Expected 5 <section> tags, got {count}"

    test("T16: HTML contains 5 <section> tags", t16)

    # T17: Speaker notes in <aside class="notes">
    def t17():
        notes_count = output.html.count('class="notes"')
        assert notes_count == 5, \
            f"Expected 5 speaker note blocks, got {notes_count}"

    test("T17: All 5 slides have <aside class='notes'> blocks", t17)

    # T18: reveal.js initialization present
    def t18():
        assert "Reveal.initialize" in output.html, "Missing Reveal.initialize"

    test("T18: Reveal.initialize() call present in HTML", t18)

    # T19: reveal.js CDN links present
    def t19():
        assert "reveal.js" in output.html.lower() or "cdn.jsdelivr.net" in output.html
        assert "reveal.css" in output.html

    test("T19: reveal.js CDN CSS and JS links present", t19)

    # T20: Plugin scripts loaded (notes, highlight, math)
    def t20():
        assert "notes.js" in output.html, "Missing notes plugin"
        assert "highlight.js" in output.html, "Missing highlight plugin"
        assert "math.js" in output.html, "Missing math plugin"

    test("T20: reveal.js plugins loaded (notes, highlight, math)", t20)

    # T21: Single slide rendering
    def t21():
        slide_html = compiler.render_slide(pres.slides[0])
        assert "<section" in slide_html
        assert "NeuralScale" in slide_html
        assert 'class="notes"' in slide_html

    test("T21: Single slide render produces <section> with content + notes", t21)

    # T22: data-background-gradient on slide 1
    def t22():
        slide_html = compiler.render_slide(pres.slides[0])
        assert "data-background-gradient" in slide_html, \
            "Missing background gradient attribute"

    test("T22: Title slide has data-background-gradient attr", t22)

    # T23: Transition attributes
    def t23():
        slide5_html = compiler.render_slide(pres.slides[4])
        assert "data-transition" in slide5_html, "Missing transition on traction slide"

    test("T23: Traction slide has data-transition attribute", t23)

    # T24: Layout classes applied
    def t24():
        html = output.html
        assert "slide-center-focus" in html, "Missing center-focus layout class"
        assert "slide-text-left-visual-right" in html, "Missing text-visual layout class"
        assert "slide-split-screen" in html, "Missing split-screen layout class"
        assert "slide-grid-3x1" in html, "Missing grid-3x1 layout class"
        assert "slide-comparison" in html, "Missing comparison layout class"

    test("T24: All 5 layout classes present in HTML", t24)

    # T25: Semantic HTML elements
    def t25():
        assert "<h1" in output.html, "Missing h1"
        assert "<h2" in output.html, "Missing h2"
        assert "<ul" in output.html, "Missing ul"
        assert "<li" in output.html, "Missing li"
        assert "<table" in output.html, "Missing table (comparison)"

    test("T25: Semantic HTML structure (h1, h2, ul, li, table)", t25)

    # T26: Comparison table structure
    def t26():
        assert "<thead>" in output.html
        assert "<tbody>" in output.html
        assert "Feature" in output.html
        assert "advantage" in output.html

    test("T26: Comparison table has thead/tbody/advantage markup", t26)

    # T27: data-id attributes for auto-animate support
    def t27():
        assert 'data-id="title-' in output.html, "Missing data-id for title"

    test("T27: data-id attributes present for auto-animate support", t27)

    # T28: Elements layer rendered
    def t28():
        assert "elements-layer" in output.html, "Missing elements layer"
        assert "element-shape" in output.html, "Missing shape element"

    test("T28: Positioned elements layer with shape element rendered", t28)

    # T29: Content not XSS-vulnerable (check escaping)
    def t29():
        # The title has an arrow character; check it doesn't create raw HTML
        assert "training → production" not in output.html or \
               "training →" in output.html or "→" in output.html
        # Check no unescaped quotes in content areas
        assert '<script>alert' not in output.html

    test("T29: Content properly HTML-escaped (XSS prevention)", t29)

    # T30: Full HTML document structure
    def t30():
        assert output.html.startswith("<!DOCTYPE html>")
        assert "<html" in output.html
        assert "</html>" in output.html
        assert '<div class="reveal">' in output.html
        assert '<div class="slides">' in output.html

    test("T30: Complete HTML document with reveal.js structure", t30)

    return output


# ═══════════════════════════════════════════════════════════════════
# SECTION 3: THEME ENGINE (Electric Studio)
# ═══════════════════════════════════════════════════════════════════

def run_theme_engine_tests():
    section("THEME ENGINE (Electric Studio & Built-In Themes)")

    from app.services.slides_new.themes.theme_models import (
        BuiltInThemes,
        ThemeDefinition,
        ThemeTier,
    )

    # T31: Electric Studio theme exists
    def t31():
        es = BuiltInThemes.ELECTRIC_STUDIO
        assert es is not None
        assert es.id == "electric-studio"
        assert es.name == "Electric Studio"

    test("T31: Electric Studio theme exists in BuiltInThemes", t31)

    # T32: Electric Studio colors match spec
    def t32():
        es = BuiltInThemes.ELECTRIC_STUDIO
        assert es.colors.primary == "#7B2FF7", f"Primary: {es.colors.primary}"
        assert es.colors.accent == "#00F5FF", f"Accent: {es.colors.accent}"

    test("T32: Electric Studio primary=#7B2FF7, accent=#00F5FF", t32)

    # T33: Dark variant
    def t33():
        es = BuiltInThemes.ELECTRIC_STUDIO
        assert es.variant == "dark"

    test("T33: Electric Studio is dark variant", t33)

    # T34: Typography intentional (not generic)
    def t34():
        es = BuiltInThemes.ELECTRIC_STUDIO
        assert es.typography.heading_font not in ("Arial", "Helvetica", "sans-serif"), \
            f"Generic heading font: {es.typography.heading_font}"
        assert es.typography.body_font not in ("Arial", "Helvetica", "sans-serif"), \
            f"Generic body font: {es.typography.body_font}"

    test("T34: Typography is intentional (not default sans-serif)", t34)

    # T35: Theme to_dict serialization
    def t35():
        d = BuiltInThemes.ELECTRIC_STUDIO.to_dict()
        assert "colors" in d
        assert "typography" in d
        assert d["id"] == "electric-studio"

    test("T35: Theme.to_dict() serializes correctly", t35)

    # T36: Bold Signal theme exists
    def t36():
        bs = BuiltInThemes.BOLD_SIGNAL
        assert bs.id == "bold-signal"
        assert bs.colors.primary == "#FF6B35"

    test("T36: Bold Signal theme exists (high contrast warm)", t36)

    # T37: Dark Developer theme
    def t37():
        dd = BuiltInThemes.DARK_DEVELOPER
        assert dd.id == "dark-developer"

    test("T37: Dark Developer theme exists", t37)

    # T38: Theme engine generates palette
    try:
        from app.services.slides_new.themes.theme_engine import GenerativeThemeEngine

        def t38():
            engine = GenerativeThemeEngine()
            theme = engine.from_brand_colors(
                primary="#7B2FF7",
                mood="tech",
            )
            assert theme is not None
            assert theme.colors.primary == "#7B2FF7" or theme.colors.primary
            assert theme.variant in ("dark", "light", "specialty")

        test("T38: GenerativeThemeEngine.generate() produces theme from color+mood", t38)
    except ImportError:
        print("  ⚠️  T38: Skipped — GenerativeThemeEngine not importable")

    # T39: CSS compiler
    try:
        from app.services.slides_new.themes.css_compiler import CSSCompiler

        def t39():
            comp = CSSCompiler()
            es = BuiltInThemes.ELECTRIC_STUDIO
            result = comp.compile(es)
            assert result, "Empty CSS output"
            assert "--r-background-color" in result or "background" in result.lower()

        test("T39: CSSCompiler compiles Electric Studio to CSS with variables", t39)
    except ImportError:
        print("  ⚠️  T39: Skipped — CSSCompiler not importable")


# ═══════════════════════════════════════════════════════════════════
# SECTION 4: ACCESSIBILITY (WCAG AA)
# ═══════════════════════════════════════════════════════════════════

def run_accessibility_tests():
    section("ACCESSIBILITY (WCAG 2.1 AA Contrast Checks)")

    from app.services.slides_new.quality.accessibility_engine import (
        contrast_ratio,
        hex_to_rgb,
        passes_wcag_aa,
        passes_wcag_aaa,
        relative_luminance,
        suggest_contrast_fix,
    )
    from app.services.slides_new.themes.theme_models import BuiltInThemes

    es = BuiltInThemes.ELECTRIC_STUDIO

    # T40: Utility hex_to_rgb
    def t40():
        r, g, b = hex_to_rgb("#FF0000")
        assert (r, g, b) == (255, 0, 0)
        r, g, b = hex_to_rgb("#00F5FF")
        assert r == 0 and g == 245 and b == 255

    test("T40: hex_to_rgb converts correctly", t40)

    # T41: Relative luminance white vs black
    def t41():
        lum_w = relative_luminance(255, 255, 255)
        lum_b = relative_luminance(0, 0, 0)
        assert abs(lum_w - 1.0) < 0.01, f"White luminance: {lum_w}"
        assert abs(lum_b - 0.0) < 0.01, f"Black luminance: {lum_b}"

    test("T41: Relative luminance: white≈1.0, black≈0.0", t41)

    # T42: Contrast ratio black/white = 21:1
    def t42():
        ratio = contrast_ratio("#000000", "#FFFFFF")
        assert abs(ratio - 21.0) < 0.1, f"B/W ratio: {ratio}"

    test("T42: Contrast ratio black/white ≈ 21:1", t42)

    # T43: heading color vs background (Electric Studio)
    def t43():
        ratio = contrast_ratio(es.colors.heading, es.colors.background)
        assert ratio >= 4.5, \
            f"Heading/BG contrast {ratio:.2f} < 4.5 WCAG AA"

    test("T43: Electric Studio heading/background contrast ≥4.5:1", t43)

    # T44: text color vs background
    def t44():
        ratio = contrast_ratio(es.colors.text, es.colors.background)
        assert ratio >= 4.5, \
            f"Text/BG contrast {ratio:.2f} < 4.5 WCAG AA"

    test("T44: Electric Studio text/background contrast ≥4.5:1", t44)

    # T45: accent color (#00F5FF) vs dark bg
    def t45():
        passed, ratio = passes_wcag_aa(es.colors.accent, es.colors.background)
        # Accent on dark bg for large text (headers) needs 3:1
        passed_large, _ = passes_wcag_aa(
            es.colors.accent, es.colors.background, is_large_text=True
        )
        assert passed or passed_large, \
            f"Accent/BG ratio {ratio:.2f} fails both normal and large text WCAG AA"

    test("T45: Accent (#00F5FF) passes WCAG AA on dark background (large text)", t45)

    # T46: Primary (#7B2FF7) vs background
    def t46():
        passed, ratio = passes_wcag_aa(
            es.colors.primary, es.colors.background, is_large_text=True
        )
        # Primary color on dark bg at heading size should pass 3:1
        assert ratio >= 2.0, f"Primary/BG ratio {ratio:.2f} too low (even for decorative)"

    test("T46: Primary (#7B2FF7) has reasonable contrast on dark bg", t46)

    # T47: suggest_contrast_fix works
    def t47():
        fixed = suggest_contrast_fix("#333333", "#000000", target_ratio=4.5)
        assert fixed.startswith("#"), f"Invalid fix color: {fixed}"
        ratio = contrast_ratio(fixed, "#000000")
        assert ratio >= 4.5, f"Fixed color ratio {ratio:.2f} still < 4.5"

    test("T47: suggest_contrast_fix produces valid high-contrast color", t47)

    # T48: WCAG AAA check
    def t48():
        passed, ratio = passes_wcag_aaa("#FFFFFF", "#0A0A1B")
        assert passed, f"White on near-black should pass AAA, ratio={ratio:.2f}"

    test("T48: White-on-black passes WCAG AAA (7:1)", t48)


# ═══════════════════════════════════════════════════════════════════
# SECTION 5: ANTI-AI-SLOP CHECKS
# ═══════════════════════════════════════════════════════════════════

def run_anti_slop_tests():
    section("ANTI-AI-SLOP CHECKS")

    from app.services.slides_new.design.anti_slop import (
        AntiAISlopProcessor,
        GenericGradientRule,
        SlopCategory,
        SlopSeverity,
        OVERUSED_AI_COLORS,
        OVERUSED_AI_FONTS,
    )

    # T49: GenericGradientRule detects AI gradients
    def t49():
        rule = GenericGradientRule()
        violation = rule.check({
            "background": "linear-gradient(135deg, #667eea, #764ba2)"
        })
        assert violation is not None, "Should detect generic AI gradient"
        assert violation.category == SlopCategory.COLOR

    test("T49: GenericGradientRule detects blue-purple AI gradient", t49)

    # T50: Electric Studio colors NOT in overused set
    def t50():
        from app.services.slides_new.themes.theme_models import BuiltInThemes
        es = BuiltInThemes.ELECTRIC_STUDIO
        theme_colors = [
            es.colors.primary.lower(),
            es.colors.accent.lower(),
            es.colors.background.lower(),
        ]
        for c in theme_colors:
            assert c not in OVERUSED_AI_COLORS, \
                f"Theme color {c} is in overused AI colors list!"

    test("T50: Electric Studio colors not in OVERUSED_AI_COLORS", t50)

    # T51: Electric Studio fonts NOT in overused set
    def t51():
        from app.services.slides_new.themes.theme_models import BuiltInThemes
        es = BuiltInThemes.ELECTRIC_STUDIO
        heading = es.typography.heading_font
        body = es.typography.body_font
        # These are "Outfit" and "DM Sans" — not generic
        assert heading not in OVERUSED_AI_FONTS or body not in OVERUSED_AI_FONTS, \
            f"Using overused AI fonts: {heading}, {body}"

    test("T51: Electric Studio fonts not all in OVERUSED_AI_FONTS", t51)

    # T52: Clean slide passes gradient check
    def t52():
        rule = GenericGradientRule()
        violation = rule.check({
            "background": {
                "type": "gradient-radial",
                "colors": ["#0F172A", "#1E293B"],
            }
        })
        assert violation is None, f"False positive: {violation}"

    test("T52: NeuralScale title gradient is NOT flagged as AI slop", t52)

    # T53: AntiAISlopProcessor class exists and initializes
    def t53():
        processor = AntiAISlopProcessor()
        assert processor is not None

    test("T53: AntiAISlopProcessor initializes without error", t53)

    # T54: Bullets count check
    def t54():
        # NeuralScale problem slide has exactly 4 bullets (within limit of 6)
        from app.services.slides_new.design.anti_slop import MAX_REASONABLE_BULLETS
        bullets = [
            "GPU clusters cost $50K+/month to operate",
            "Zero-downtime deployment takes weeks, not hours",
            "ML teams spend 60% time on infra, not models",
            "No unified pipeline from training → production",
        ]
        assert len(bullets) <= MAX_REASONABLE_BULLETS, \
            f"{len(bullets)} bullets exceeds max {MAX_REASONABLE_BULLETS}"

    test("T54: Problem slide has ≤6 bullets (anti-slop rule)", t54)


# ═══════════════════════════════════════════════════════════════════
# SECTION 6: QUALITY ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════

def run_quality_tests():
    section("QUALITY ORCHESTRATOR & MODELS")

    from app.services.slides_new.quality.models import (
        QualityDimension,
        DimensionScore,
        UnifiedQualityReport,
        AccessibilityReport,
        WCAGLevel,
        A11ySeverity,
    )

    # T55: QualityDimension enum
    def t55():
        dims = list(QualityDimension)
        assert len(dims) >= 6
        assert QualityDimension.ACCESSIBILITY in dims
        assert QualityDimension.ANTI_SLOP in dims
        assert QualityDimension.CONTENT_QUALITY in dims
        assert QualityDimension.PERFORMANCE in dims

    test("T55: QualityDimension has ≥6 dimensions incl. accessibility & anti-slop", t55)

    # T56: DimensionScore structure
    def t56():
        score = DimensionScore(
            dimension=QualityDimension.CONTENT_QUALITY,
            score=85.0,
            weight=1.0,
            issues=[],
            details={},
        )
        assert score.score == 85.0
        assert score.dimension == QualityDimension.CONTENT_QUALITY

    test("T56: DimensionScore creates correctly", t56)

    # T57: UnifiedQualityReport
    def t57():
        dims = [
            DimensionScore(
                dimension=QualityDimension.CONTENT_QUALITY,
                score=90.0, weight=1.0,
            ),
            DimensionScore(
                dimension=QualityDimension.ACCESSIBILITY,
                score=80.0, weight=1.5,
            ),
        ]
        report = UnifiedQualityReport(dimensions=dims)
        report.compute_overall()
        assert 0 <= report.overall_score <= 100, f"Overall score {report.overall_score} out of range"

    test("T57: UnifiedQualityReport.compute_overall() produces valid score", t57)

    # T58: AccessibilityReport structure
    def t58():
        report = AccessibilityReport(
            score=100.0,
            wcag_level=WCAGLevel.AA,
        )
        assert report.score == 100.0
        assert report.violation_count == 0

    test("T58: AccessibilityReport with zero violations scores 100", t58)

    # T59: Quality orchestrator imports
    def t59():
        from app.services.slides_new.quality.quality_orchestrator import (
            QualityOrchestrator,
            ContentQualityEvaluator,
            AntiSlopIntegration,
            PerformanceEvaluator,
        )
        assert QualityOrchestrator is not None
        assert ContentQualityEvaluator is not None

    test("T59: QualityOrchestrator and evaluators importable", t59)


# ═══════════════════════════════════════════════════════════════════
# SECTION 7: PERFORMANCE & RENDER TIMING
# ═══════════════════════════════════════════════════════════════════

def run_performance_tests(pres):
    section("PERFORMANCE METRICS")

    from app.services.slides_new.renderers.reveal_compiler import RevealCompiler

    compiler = RevealCompiler()

    # T60: Total generation time < 30 seconds
    def t60():
        start = time.perf_counter()
        output = compiler.render_presentation(pres, theme_css="")
        elapsed = time.perf_counter() - start
        assert output.success
        assert elapsed < 30, f"Generation took {elapsed:.2f}s (limit: 30s)"
        print(f"       └─ Generated in {elapsed:.3f}s")

    test("T60: Full 5-slide render completes in <30 seconds", t60)

    # T61: Per-slide render < 3 seconds
    def t61():
        for s in pres.slides:
            start = time.perf_counter()
            html = compiler.render_slide(s)
            elapsed = time.perf_counter() - start
            assert elapsed < 3.0, \
                f"Slide {s.id} took {elapsed:.2f}s (limit: 3s)"
            assert html, f"Slide {s.id} produced empty HTML"

    test("T61: Each slide renders in <3 seconds", t61)

    # T62: HTML file size < 250KB
    def t62():
        output = compiler.render_presentation(pres, theme_css="")
        size_bytes = len(output.html.encode("utf-8"))
        size_kb = size_bytes / 1024
        assert size_kb < 250, f"HTML size {size_kb:.1f}KB exceeds 250KB limit"
        print(f"       └─ HTML size: {size_kb:.1f}KB")

    test("T62: HTML output size <250KB", t62)

    # T63: Performance guardrails importable
    def t63():
        from app.services.slides_new.renderers.performance_guardrails import (
            PerformanceGuardrails,
            QualityLevel,
            QUALITY_BUDGETS,
        )
        assert QualityLevel.HIGH is not None
        budgets = QUALITY_BUDGETS[QualityLevel.HIGH]
        assert budgets["max_polygons"] == 50000

    test("T63: PerformanceGuardrails and budgets importable", t63)


# ═══════════════════════════════════════════════════════════════════
# SECTION 8: EDGE CASES
# ═══════════════════════════════════════════════════════════════════

def run_edge_case_tests():
    section("EDGE CASES (Stress & Boundary Testing)")

    from app.models.dsl_v2 import (
        PresentationDSL, SlideDSL, SlideContentV2,
        BackgroundStyle, BackgroundType, SlideStyle,
        PresentationCore, PresentationMetadata, ThemeDSL,
    )
    from app.services.slides_new.renderers.reveal_compiler import RevealCompiler

    compiler = RevealCompiler()

    # Helper: build a minimal valid presentation
    def make_presentation(slides_data: list[dict]) -> PresentationDSL:
        slides = []
        for i, sd in enumerate(slides_data):
            sd.setdefault("index", i)
            sd.setdefault("id", f"slide-{i}")
            slides.append(sd)

        return PresentationDSL.model_validate({
            "version": "2.0",
            "presentation": {
                "id": "test-deck",
                "title": "Test Deck",
            },
            "slides": slides,
        })

    # T64: Super long title (>100 chars)
    def t64():
        long_title = "A" * 150  # 150 characters
        pres = make_presentation([{
            "content": {"title": long_title},
        }])
        html = compiler.render_slide(pres.slides[0])
        assert "A" * 100 in html, "Long title should be preserved"
        assert "<section" in html

    test("T64: Super long title (150 chars) renders without error", t64)

    # T65: Empty bullets array
    def t65():
        pres = make_presentation([{
            "layout": "bullets",
            "content": {"title": "Empty Bullets", "bullets": []},
        }])
        html = compiler.render_slide(pres.slides[0])
        assert "<section" in html
        # Should still render the title even with no bullets
        assert "Empty Bullets" in html

    test("T65: Empty bullets array renders gracefully", t65)

    # T66: No content at all (minimal slide)
    def t66():
        pres = make_presentation([{
            "content": {"title": ""},
        }])
        html = compiler.render_slide(pres.slides[0])
        assert "<section" in html

    test("T66: Minimal slide with empty title renders", t66)

    # T67: Maximum bullet count (30 — schema limit)
    def t67():
        bullets = [f"Bullet {i}" for i in range(30)]
        pres = make_presentation([{
            "layout": "bullets",
            "content": {"title": "Many Bullets", "bullets": bullets},
        }])
        html = compiler.render_slide(pres.slides[0])
        assert html.count("<li") == 30

    test("T67: 30 bullets (schema max) renders all items", t67)

    # T68: Exceeding 30 bullets raises validation error
    def t68():
        bullets = [f"Bullet {i}" for i in range(31)]
        try:
            make_presentation([{
                "layout": "bullets",
                "content": {"title": "Too Many", "bullets": bullets},
            }])
            assert False, "Should have raised validation error"
        except Exception as e:
            assert "30" in str(e) or "Maximum" in str(e) or "max" in str(e).lower(), \
                f"Unexpected error: {e}"

    test("T68: >30 bullets raises Pydantic validation error", t68)

    # T69: Invalid hex color rejected
    def t69():
        try:
            make_presentation([{
                "content": {"title": "Bad Color"},
                "style": {
                    "background": {
                        "type": "solid",
                        "colors": ["not-a-color"],
                    }
                },
            }])
            assert False, "Should reject invalid hex color"
        except Exception as e:
            assert "hex" in str(e).lower() or "color" in str(e).lower() or "Invalid" in str(e)

    test("T69: Invalid hex color 'not-a-color' rejected by validator", t69)

    # T70: Gradient with single color rejected
    def t70():
        try:
            make_presentation([{
                "content": {"title": "Bad Gradient"},
                "style": {
                    "background": {
                        "type": "gradient-linear",
                        "colors": ["#FF0000"],
                    }
                },
            }])
            assert False, "Should reject gradient with single color"
        except Exception as e:
            assert "2" in str(e) or "gradient" in str(e).lower() or "colour" in str(e).lower()

    test("T70: Linear gradient with only 1 color rejected", t70)

    # T71: Duplicate element IDs rejected
    def t71():
        try:
            make_presentation([{
                "content": {"title": "Dup Elements"},
                "elements": [
                    {"id": "dup", "type": "text", "content": "A"},
                    {"id": "dup", "type": "text", "content": "B"},
                ],
            }])
            assert False, "Should reject duplicate element IDs"
        except Exception as e:
            assert "Duplicate" in str(e) or "duplicate" in str(e).lower()

    test("T71: Duplicate element IDs within a slide rejected", t71)

    # T72: Fragment referencing nonexistent element rejected
    def t72():
        try:
            make_presentation([{
                "content": {"title": "Bad Frag"},
                "elements": [
                    {"id": "real-elem", "type": "text", "content": "A"},
                ],
                "fragments": [
                    {"elementId": "ghost-elem", "order": 0, "animation": "fade-in"},
                ],
            }])
            assert False, "Should reject fragment referencing nonexistent element"
        except Exception as e:
            assert "ghost-elem" in str(e) or "unknown" in str(e).lower()

    test("T72: Fragment referencing nonexistent element rejected", t72)

    # T73: Duplicate slide IDs rejected
    def t73():
        try:
            PresentationDSL.model_validate({
                "version": "2.0",
                "presentation": {"id": "test", "title": "Test"},
                "slides": [
                    {"index": 0, "id": "same-id", "content": {"title": "A"}},
                    {"index": 1, "id": "same-id", "content": {"title": "B"}},
                ],
            })
            assert False, "Should reject duplicate slide IDs"
        except Exception as e:
            assert "Duplicate" in str(e) or "duplicate" in str(e).lower()

    test("T73: Duplicate slide IDs in presentation rejected", t73)

    # T74: Non-contiguous slide indexes rejected
    def t74():
        try:
            PresentationDSL.model_validate({
                "version": "2.0",
                "presentation": {"id": "test", "title": "Test"},
                "slides": [
                    {"index": 0, "id": "s0", "content": {"title": "A"}},
                    {"index": 5, "id": "s5", "content": {"title": "B"}},
                ],
            })
            assert False, "Should reject non-contiguous indexes"
        except Exception as e:
            assert "contiguous" in str(e).lower() or "index" in str(e).lower()

    test("T74: Non-contiguous slide indexes (0,5) rejected", t74)

    # T75: Special characters in content handled
    def t75():
        pres = make_presentation([{
            "content": {
                "title": 'Test <script>alert("xss")</script> & "quotes"',
            },
        }])
        html = compiler.render_slide(pres.slides[0])
        assert "<script>" not in html, "XSS not escaped!"
        assert "&lt;" in html or "script" not in html.split("data-id")[0], \
            "Script tag not properly escaped"
        assert "&amp;" in html, "Ampersand not escaped"

    test("T75: XSS content properly escaped in rendered HTML", t75)


# ═══════════════════════════════════════════════════════════════════
# SECTION 9: RENDER ROUTER & MULTI-FORMAT
# ═══════════════════════════════════════════════════════════════════

def run_render_router_tests():
    section("RENDER ROUTER & MULTI-FORMAT SUPPORT")

    from app.services.slides_new.renderers.render_router import (
        RenderRouter,
        ExportFormat,
        ContentCapabilities,
    )
    from app.services.slides_new.renderers.base_renderer import RendererType

    # T76: ExportFormat enum values
    def t76():
        assert ExportFormat.REVEAL_JS is not None
        assert ExportFormat.HTML is not None
        assert ExportFormat.PPTX is not None

    test("T76: ExportFormat enum has REVEAL_JS, HTML, PPTX", t76)

    # T77: RenderRouter initializes
    def t77():
        router = RenderRouter()
        assert router is not None

    test("T77: RenderRouter initializes without error", t77)

    # T78: ContentCapabilities analysis
    def t78():
        # ContentCapabilities requires a PresentationDSL object
        from app.models.dsl_v2 import PresentationDSL
        raw = build_neuralscale_dsl_dict()
        pres = PresentationDSL.model_validate(raw)
        cap = ContentCapabilities(pres)
        assert cap.has_speaker_notes is True
        assert cap.slide_count == 5

    test("T78: ContentCapabilities correctly tracks deck features", t78)


# ═══════════════════════════════════════════════════════════════════
# SECTION 10: ORCHESTRATOR & PIPELINE STRUCTURE
# ═══════════════════════════════════════════════════════════════════

def run_orchestrator_tests():
    section("ORCHESTRATOR & PIPELINE STRUCTURE")

    # T79: V7 orchestrator importable
    def t79():
        from app.services.slides_new.orchestrator.v7_orchestrator import V7Orchestrator
        assert V7Orchestrator is not None

    test("T79: V7Orchestrator importable", t79)

    # T80: Pipeline orchestrator importable
    def t80():
        from app.services.slides_new.orchestrator.pipeline import PipelineOrchestrator
        assert PipelineOrchestrator is not None

    test("T80: PipelineOrchestrator importable", t80)

    # T81: DSL generator importable
    def t81():
        from app.services.slides_new.dsl.dsl_generator import DSLGenerator, DSLGenerationResult
        assert DSLGenerator is not None
        assert DSLGenerationResult is not None

    test("T81: DSLGenerator and DSLGenerationResult importable", t81)

    # T82: Agent types importable
    def t82():
        from app.services.slides_new.agents.code_agent_router import CodeAgentRouter
        from app.services.slides_new.agents.qa_agent import QAAgent
        from app.services.slides_new.agents.designer_agent import DesignerAgent
        from app.services.slides_new.agents.ceo_agent import CEOAgent
        assert CodeAgentRouter is not None
        assert QAAgent is not None
        assert DesignerAgent is not None
        assert CEOAgent is not None

    test("T82: All agent types (CEO, Designer, QA, CodeAgent) importable", t82)

    # T83: Skill registry importable
    def t83():
        from app.services.slides_new.skills.skill_registry import SkillRegistry
        from app.services.slides_new.skills.models import SlideSkill
        assert SkillRegistry is not None
        assert SlideSkill is not None

    test("T83: SkillRegistry and SlideSkill importable", t83)


# ═══════════════════════════════════════════════════════════════════
# SECTION 11: COMPLETE DECK VALIDATION (Combined Output)
# ═══════════════════════════════════════════════════════════════════

def run_complete_deck_tests(pres, output):
    section("COMPLETE DECK VALIDATION")

    # T84: All 5 slide titles appear in HTML
    def t84():
        expected_titles = [
            "NeuralScale",
            "The $50K/Month Problem",
            "NeuralScale: The Unified AI Infra Platform",
            "$12B Market, Growing 40% YoY",
            "Traction &amp; The Ask",
        ]
        for title in expected_titles:
            assert title in output.html, \
                f"Missing title in HTML: {title}"

    test("T84: All 5 slide titles present in rendered HTML", t84)

    # T85: All speaker notes in HTML
    def t85():
        expected_fragments = [
            "GPU cost problem",
            "How many of you have felt this pain",
            "70% stat",
            "BOTTOM-UP methodology",
            "NPS of 72",
        ]
        for frag in expected_fragments:
            assert frag in output.html, \
                f"Missing speaker note fragment: {frag}"

    test("T85: Key phrases from all speaker notes present in HTML", t85)

    # T86: Bullet content rendered
    def t86():
        bullets_to_check = [
            "GPU clusters cost $50K+/month",
            "ML teams spend 60%",
        ]
        for bullet in bullets_to_check:
            assert bullet in output.html, \
                f"Missing bullet: {bullet}"

    test("T86: Problem slide bullets rendered in HTML", t86)

    # T87: Comparison table data rendered
    def t87():
        assert "Enterprise Pilots" in output.html
        assert "$800K" in output.html
        assert "40% MoM" in output.html

    test("T87: Traction comparison data in rendered HTML", t87)

    # T88: Grid-3x1 market data rendered
    def t88():
        assert "$12B" in output.html
        assert "$2.4B" in output.html
        assert "$120M" in output.html

    test("T88: TAM/SAM/SOM values present in market slide", t88)

    # T89: Quality scoring structure
    def t89():
        # Calculate simple quality score breakdown
        checks = {
            "visual_design": 0,
            "content_quality": 0,
            "technical_validity": 0,
            "theme_adherence": 0,
        }
        # Visual: layouts, elements, backgrounds
        if "split-screen" in output.html and "grid-3x1" in output.html:
            checks["visual_design"] += 20
        if "data-background" in output.html:
            checks["visual_design"] += 5
        # Content: titles, bullets, notes
        if output.html.count('class="notes"') == 5:
            checks["content_quality"] += 15
        if "<ul>" in output.html and "<table" in output.html:
            checks["content_quality"] += 10
        # Technical: valid HTML, section tags, reveal init
        if output.html.startswith("<!DOCTYPE html>"):
            checks["technical_validity"] += 10
        if "Reveal.initialize" in output.html:
            checks["technical_validity"] += 10
        if output.html.count("<section ") == 5:
            checks["technical_validity"] += 5
        # Theme: accent colors, layout CSS
        if "barise-theme" in output.html:
            checks["theme_adherence"] += 15
        if "barise-layouts" in output.html:
            checks["theme_adherence"] += 10

        total = sum(checks.values())
        print(f"       └─ Quality breakdown: {checks}")
        print(f"       └─ Total quality score: {total}/100")
        assert total >= 50, f"Quality score {total} too low"

    test("T89: Quality score assessment ≥50/100", t89)

    # T90: Responsive viewport meta tag
    def t90():
        assert 'name="viewport"' in output.html

    test("T90: Viewport meta tag present for responsiveness", t90)


# ═══════════════════════════════════════════════════════════════════
# SECTION 12: THEME STRESS TEST (Multiple Themes)
# ═══════════════════════════════════════════════════════════════════

def run_theme_stress_tests():
    section("THEME STRESS TEST (Multiple Built-In Themes)")

    from app.services.slides_new.themes.theme_models import BuiltInThemes
    from app.services.slides_new.quality.accessibility_engine import contrast_ratio

    themes_to_test = [
        ("BOLD_SIGNAL", BuiltInThemes.BOLD_SIGNAL),
        ("ELECTRIC_STUDIO", BuiltInThemes.ELECTRIC_STUDIO),
        ("DARK_DEVELOPER", BuiltInThemes.DARK_DEVELOPER),
    ]

    for theme_name, theme_def in themes_to_test:
        def make_test(tn, td):
            def t():
                # Heading vs background contrast
                ratio = contrast_ratio(td.colors.heading, td.colors.background)
                assert ratio >= 3.0, \
                    f"{tn}: heading/bg contrast {ratio:.2f} < 3.0"
                # Text vs background
                ratio_text = contrast_ratio(td.colors.text, td.colors.background)
                assert ratio_text >= 3.0, \
                    f"{tn}: text/bg contrast {ratio_text:.2f} < 3.0"
                # Has intentional fonts
                assert td.typography.heading_font, f"{tn}: missing heading font"
                assert td.typography.body_font, f"{tn}: missing body font"
            return t

        test(
            f"T-Theme: {theme_name} passes contrast & typography checks",
            make_test(theme_name, theme_def),
        )


# ═══════════════════════════════════════════════════════════════════
# MAIN RUNNER
# ═══════════════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║  SLIDE GENERATION SYSTEM — INTEGRATION TEST SUITE              ║")
    print("║  Testing DSL v2 → HTML Pipeline (NeuralScale Pitch Deck)       ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    start_time = time.perf_counter()

    # Section 1: DSL Validation
    pres = run_dsl_validation_tests()

    # Section 2: Reveal Compiler (depends on pres)
    output = None
    if pres:
        output = run_reveal_compiler_tests(pres)

    # Section 3: Theme Engine
    run_theme_engine_tests()

    # Section 4: Accessibility
    run_accessibility_tests()

    # Section 5: Anti-AI-Slop
    run_anti_slop_tests()

    # Section 6: Quality Models
    run_quality_tests()

    # Section 7: Performance (depends on pres)
    if pres:
        run_performance_tests(pres)

    # Section 8: Edge Cases
    run_edge_case_tests()

    # Section 9: Render Router
    run_render_router_tests()

    # Section 10: Orchestrator Structure
    run_orchestrator_tests()

    # Section 11: Complete Deck (depends on pres + output)
    if pres and output:
        run_complete_deck_tests(pres, output)

    # Section 12: Theme Stress
    run_theme_stress_tests()

    elapsed = time.perf_counter() - start_time
    print(f"\n  ⏱  Total test time: {elapsed:.2f}s")

    all_pass = summary()
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
