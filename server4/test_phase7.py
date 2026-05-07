"""
Phase 7 Verification Test -- PPTX & HTML Renderers + Render Router.

Tests:
 1. PptxCompiler: module imports
 2. PptxCompiler: class instantiation
 3. PptxCompiler: get_renderer_type == PPTX
 4. PptxCompiler: render_presentation minimal DSL
 5. PptxCompiler: render_presentation output structure
 6. PptxCompiler: pptx_base64 decodes to valid bytes
 7. PptxCompiler: file_name in assets
 8. PptxCompiler: slide_count matches DSL
 9. PptxCompiler: render_slide single
10. PptxCompiler: render_slide contains metadata
11. PptxCompiler: center_focus layout
12. PptxCompiler: split_screen layout
13. PptxCompiler: full_bleed layout
14. PptxCompiler: grid_2x2 layout
15. PptxCompiler: grid_3x1 layout
16. PptxCompiler: text_left_visual_right layout
17. PptxCompiler: text_right_visual_left layout
18. PptxCompiler: top_bottom layout
19. PptxCompiler: overlay layout
20. PptxCompiler: bullets layout
21. PptxCompiler: comparison layout
22. PptxCompiler: timeline layout
23. PptxCompiler: kpi_dashboard layout
24. PptxCompiler: quote layout
25. PptxCompiler: team_grid layout
26. PptxCompiler: chart layout (native Excel)
27. PptxCompiler: blank layout
28. PptxCompiler: speaker notes embedding
29. PptxCompiler: 3D fallback placeholder
30. PptxCompiler: theme colors extraction
31. PptxCompiler: multi-slide compilation
32. PptxCompiler: error handling returns success=False
33. HtmlCompiler: module imports
34. HtmlCompiler: class instantiation
35. HtmlCompiler: get_renderer_type == HTML
36. HtmlCompiler: render_presentation minimal
37. HtmlCompiler: render_presentation has <!DOCTYPE html>
38. HtmlCompiler: CSS custom properties in output
39. HtmlCompiler: navigation JS in output
40. HtmlCompiler: render_slide single
41. HtmlCompiler: center_focus layout
42. HtmlCompiler: split_screen layout
43. HtmlCompiler: full_bleed layout
44. HtmlCompiler: grid_2x2 layout
45. HtmlCompiler: grid_3x1 layout
46. HtmlCompiler: text_left_visual_right layout
47. HtmlCompiler: text_right_visual_left layout
48. HtmlCompiler: top_bottom layout
49. HtmlCompiler: overlay layout
50. HtmlCompiler: bullets layout
51. HtmlCompiler: comparison layout
52. HtmlCompiler: timeline layout
53. HtmlCompiler: kpi_dashboard layout
54. HtmlCompiler: quote layout
55. HtmlCompiler: team_grid layout
56. HtmlCompiler: chart layout (Chart.js canvas)
57. HtmlCompiler: blank layout
58. HtmlCompiler: speaker notes hidden div
59. HtmlCompiler: 3D fallback notice
60. HtmlCompiler: chart CDN script tag
61. HtmlCompiler: offline mode no CDN
62. HtmlCompiler: slide_count correct
63. HtmlCompiler: theme CSS vars generation
64. HtmlCompiler: error handling
65. RenderRouter: module imports
66. RenderRouter: instantiation
67. RenderRouter: register_renderer
68. RenderRouter: get_available_formats
69. RenderRouter: render PPTX format
70. RenderRouter: render HTML format
71. RenderRouter: render unavailable format
72. RenderRouter: render_all multi-format
73. RenderRouter: recommend_format standard
74. RenderRouter: recommend_format with charts
75. RenderRouter: recommend_formats complementary
76. RenderRouter: ContentCapabilities analysis
77. RenderRouter: create_export_job
78. RenderRouter: ExportJobStatus lifecycle
79. RenderRouter: get_stats
80. ExportRoutes: module imports
81. ExportRoutes: router prefix
82. ExportRoutes: FormatInfo schema
83. ExportRoutes: ExportRequest schema
84. ExportRoutes: ExportResponse schema
85. ExportRoutes: MultiExportRequest schema
86. ExportRoutes: RecommendResponse schema
87. Integration: renderers __init__ Phase 7 exports
88. Integration: database Phase 7 index code
89. Integration: main.py export_routes registration
90. Integration: ExportFormat enum values
91. Integration: ExportJobStatus enum values
92. RendererType PPTX in enum
93. RendererType HTML in enum
94. BaseRenderer ABC compliance (PptxCompiler)
95. BaseRenderer ABC compliance (HtmlCompiler)
96. Edge: empty presentation
97. Edge: slide with no layout defaults
98. Edge: all 17 layouts compile (PPTX)
99. Edge: all 17 layouts compile (HTML)
100. Edge: large presentation (20 slides)

Run: python test_phase7.py
"""

import sys
import os
import base64
import json
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
        print(f"Phase 7 Tests: {self.passed}/{total} passed")
        if self.errors:
            print("\nFailures:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0


results = TestResult()


# ═══════════════════════════════════════════════════════════════
# DSL BUILDERS
# ═══════════════════════════════════════════════════════════════


def _make_dsl(slides_data=None, title="Test Deck"):
    """Build a minimal PresentationDSL for testing."""
    from app.models.dsl_v2 import (
        PresentationDSL, PresentationCore, SlideDSL,
        SlideContentV2, SlideStyle, BackgroundStyle,
        ThemeDSL, LayoutType, SlideType,
    )

    if slides_data is None:
        slides_data = [
            {
                "index": 0,
                "type": SlideType.TITLE_SLIDE,
                "layout": LayoutType.CENTER_FOCUS,
                "title": "Hello World",
                "subtitle": "Test presentation",
            }
        ]

    slides = []
    for sd in slides_data:
        content = SlideContentV2(
            title=sd.get("title", "Slide"),
            subtitle=sd.get("subtitle"),
            body_text=sd.get("body_text"),
            bullets=sd.get("bullets"),
            quote_text=sd.get("quote_text"),
            quote_author=sd.get("quote_author"),
            chart_data=sd.get("chart_data"),
            team_members=sd.get("team_members"),
            kpi_metrics=sd.get("kpi_metrics"),
            timeline_items=sd.get("timeline_items"),
            comparison_items=sd.get("comparison_items"),
            image_url=sd.get("image_url"),
            image_prompt=sd.get("image_prompt"),
            left_content=sd.get("left_content"),
            right_content=sd.get("right_content"),
            tagline=sd.get("tagline"),
            presenter=sd.get("presenter"),
        )
        bg_color = sd.get("bg_color")
        style = SlideStyle(
            background=BackgroundStyle(
                colors=[bg_color] if bg_color else ["#1a1a2e"],
            ),
        )
        slide = SlideDSL(
            index=sd.get("index", 0),
            id=sd.get("id", f"slide-{sd.get('index', 0)}"),
            type=sd.get("type", SlideType.CUSTOM),
            layout=sd.get("layout", LayoutType.CENTER_FOCUS),
            content=content,
            style=style,
            speakerNotes=sd.get("speaker_notes"),
        )

        # Add 3D scene if requested
        if sd.get("three_scene"):
            from app.models.dsl_v2 import ThreeSceneConfig, ThreeSceneType
            slide.threeScene = ThreeSceneConfig(
                type=ThreeSceneType.PARTICLES,
            )

        slides.append(slide)

    return PresentationDSL(
        version="2.0",
        presentation=PresentationCore(
            id="test-001",
            title=title,
            theme=ThemeDSL(
                id="midnight-blue",
                preset="midnight-blue",
                customOverrides={
                    "--primary-color": "#2563EB",
                    "--secondary-color": "#7C3AED",
                    "--background-color": "#FFFFFF",
                    "--text-color": "#111827",
                    "--text-muted": "#6B7280",
                    "--surface-color": "#F9FAFB",
                    "--accent-color": "#F59E0B",
                },
            ),
        ),
        slides=slides,
    )


def _make_slide_dsl(layout, **extra):
    """Build a single SlideDSL for layout-specific tests."""
    from app.models.dsl_v2 import (
        SlideDSL, SlideContentV2, SlideStyle, BackgroundStyle,
        LayoutType, SlideType,
    )
    content = SlideContentV2(
        title=extra.get("title", "Test Slide"),
        subtitle=extra.get("subtitle"),
        body_text=extra.get("body_text"),
        bullets=extra.get("bullets"),
        quote_text=extra.get("quote_text"),
        quote_author=extra.get("quote_author"),
        chart_data=extra.get("chart_data"),
        team_members=extra.get("team_members"),
        kpi_metrics=extra.get("kpi_metrics"),
        timeline_items=extra.get("timeline_items"),
        comparison_items=extra.get("comparison_items"),
        image_url=extra.get("image_url"),
        image_prompt=extra.get("image_prompt"),
        left_content=extra.get("left_content"),
        right_content=extra.get("right_content"),
        tagline=extra.get("tagline"),
        presenter=extra.get("presenter"),
    )
    return SlideDSL(
        index=extra.get("index", 0),
        type=extra.get("type", SlideType.CUSTOM),
        layout=layout,
        content=content,
        id=extra.get("id", f"slide-{extra.get('index', 0)}"),
        style=SlideStyle(background=BackgroundStyle()),
        speakerNotes=extra.get("speaker_notes"),
    )


# Helper data factories
def _team_members():
    from app.models.dsl_v2 import TeamMember
    return [
        TeamMember(name="Alice Smith", role="CEO", bio="Serial entrepreneur"),
        TeamMember(name="Bob Jones", role="CTO", bio="Ex-Google"),
        TeamMember(name="Carol Lee", role="CFO"),
    ]


def _kpi_metrics():
    from app.models.dsl_v2 import KPIMetric
    return [
        KPIMetric(label="Revenue", value="$1.2M", change="+45%"),
        KPIMetric(label="Users", value="50K", change="+120%"),
        KPIMetric(label="Churn", value="3.2%", change="-0.5%"),
    ]


def _timeline_items():
    from app.models.dsl_v2 import TimelineItem
    return [
        TimelineItem(date="Q1 2024", title="Launch", description="Beta release"),
        TimelineItem(date="Q2 2024", title="Growth", description="10K users"),
        TimelineItem(date="Q3 2024", title="Expand", description="Series A"),
    ]


def _comparison_items():
    from app.models.dsl_v2 import ComparisonItem
    return [
        ComparisonItem(label="Speed", us="10x faster", them="Baseline"),
        ComparisonItem(label="Price", us="$99/mo", them="$499/mo"),
        ComparisonItem(label="Support", us="24/7", them="Email only"),
    ]


def _chart_data():
    return {
        "type": "bar",
        "labels": ["Q1", "Q2", "Q3", "Q4"],
        "datasets": [
            {"label": "Revenue", "values": [100, 200, 350, 500]},
        ],
    }


# ═══════════════════════════════════════════════════════════════
# PPTX COMPILER TESTS (1-32)
# ═══════════════════════════════════════════════════════════════

print("\n-- PptxCompiler Tests --")

# 1. Module imports
try:
    from app.services.slides_new.renderers.pptx_compiler import (
        PptxCompiler, _hex_to_rgb, _strip_html,
        CHART_TYPE_MAP, SLIDE_WIDTH_EMU, SLIDE_HEIGHT_EMU,
    )
    results.ok("PptxCompiler: module imports")
except Exception as e:
    results.fail("PptxCompiler: module imports", str(e))

# 2. Class instantiation
try:
    pc = PptxCompiler()
    assert pc is not None
    results.ok("PptxCompiler: class instantiation")
except Exception as e:
    results.fail("PptxCompiler: class instantiation", str(e))

# 3. get_renderer_type
try:
    from app.services.slides_new.renderers.base_renderer import RendererType
    pc = PptxCompiler()
    assert pc.get_renderer_type() == RendererType.PPTX
    results.ok("PptxCompiler: get_renderer_type == PPTX")
except Exception as e:
    results.fail("PptxCompiler: get_renderer_type == PPTX", str(e))

# 4. render_presentation minimal
try:
    pc = PptxCompiler()
    dsl = _make_dsl()
    output = pc.render_presentation(dsl)
    assert output.success == True, f"Expected success, got error: {output.error}"
    results.ok("PptxCompiler: render_presentation minimal DSL")
except Exception as e:
    results.fail("PptxCompiler: render_presentation minimal DSL", str(e))

# 5. render_presentation output structure
try:
    pc = PptxCompiler()
    dsl = _make_dsl()
    output = pc.render_presentation(dsl)
    assert output.renderer == RendererType.PPTX
    assert output.html == ""
    assert output.css == ""
    assert output.js == ""
    assert isinstance(output.assets, dict)
    assert isinstance(output.metadata, dict)
    assert output.success == True
    results.ok("PptxCompiler: render_presentation output structure")
except Exception as e:
    results.fail("PptxCompiler: render_presentation output structure", str(e))

# 6. pptx_base64 decodes to valid bytes
try:
    pc = PptxCompiler()
    dsl = _make_dsl()
    output = pc.render_presentation(dsl)
    b64 = output.assets["pptx_base64"]
    pptx_bytes = base64.b64decode(b64)
    assert len(pptx_bytes) > 1000, f"PPTX too small: {len(pptx_bytes)} bytes"
    # PPTX is a ZIP file - starts with PK
    assert pptx_bytes[:2] == b"PK", "PPTX should be a ZIP (PK signature)"
    results.ok("PptxCompiler: pptx_base64 decodes to valid bytes")
except Exception as e:
    results.fail("PptxCompiler: pptx_base64 decodes to valid bytes", str(e))

# 7. file_name in assets
try:
    pc = PptxCompiler()
    dsl = _make_dsl(title="My Great Pitch")
    output = pc.render_presentation(dsl)
    fname = output.assets["file_name"]
    assert fname.endswith(".pptx"), f"Expected .pptx, got {fname}"
    assert "My" in fname or "my" in fname.lower(), f"Title not in filename: {fname}"
    results.ok("PptxCompiler: file_name in assets")
except Exception as e:
    results.fail("PptxCompiler: file_name in assets", str(e))

# 8. slide_count matches DSL
try:
    pc = PptxCompiler()
    slides = [
        {"index": i, "title": f"Slide {i}"}
        for i in range(5)
    ]
    dsl = _make_dsl(slides_data=slides)
    output = pc.render_presentation(dsl)
    assert output.slide_count == 5, f"Expected 5, got {output.slide_count}"
    results.ok("PptxCompiler: slide_count matches DSL")
except Exception as e:
    results.fail("PptxCompiler: slide_count matches DSL", str(e))

# 9. render_slide single
try:
    pc = PptxCompiler()
    from app.models.dsl_v2 import LayoutType
    slide = _make_slide_dsl(LayoutType.BULLETS, title="Test", bullets=["A", "B"])
    result = pc.render_slide(slide)
    assert isinstance(result, str)
    assert "PPTX Slide" in result
    assert "Test" in result
    results.ok("PptxCompiler: render_slide single")
except Exception as e:
    results.fail("PptxCompiler: render_slide single", str(e))

# 10. render_slide contains metadata
try:
    pc = PptxCompiler()
    from app.models.dsl_v2 import LayoutType
    slide = _make_slide_dsl(LayoutType.CHART, title="Revenue",
                            chart_data=_chart_data())
    result = pc.render_slide(slide)
    assert "Chart" in result or "chart" in result
    assert "native" in result.lower() or "excel" in result.lower()
    results.ok("PptxCompiler: render_slide contains metadata")
except Exception as e:
    results.fail("PptxCompiler: render_slide contains metadata", str(e))


# 11-27: Layout-specific tests
from app.models.dsl_v2 import LayoutType, SlideType

layout_tests = [
    (11, "center_focus", LayoutType.CENTER_FOCUS, {
        "title": "Hero", "subtitle": "Sub", "tagline": "Tag",
    }),
    (12, "split_screen", LayoutType.SPLIT_SCREEN, {
        "title": "Split", "left_content": "Left", "right_content": "Right",
    }),
    (13, "full_bleed", LayoutType.FULL_BLEED, {
        "title": "Full Bleed", "subtitle": "Background",
    }),
    (14, "grid_2x2", LayoutType.GRID_2X2, {
        "title": "Grid", "kpi_metrics": _kpi_metrics(),
    }),
    (15, "grid_3x1", LayoutType.GRID_3X1, {
        "title": "Three Col", "bullets": ["A", "B", "C"],
    }),
    (16, "text_left_visual_right", LayoutType.TEXT_LEFT_VISUAL_RIGHT, {
        "title": "TLVR", "bullets": ["Feature 1", "Feature 2"],
        "image_prompt": "product screenshot",
    }),
    (17, "text_right_visual_left", LayoutType.TEXT_RIGHT_VISUAL_LEFT, {
        "title": "TRVL", "bullets": ["Benefit 1", "Benefit 2"],
    }),
    (18, "top_bottom", LayoutType.TOP_BOTTOM, {
        "title": "Top", "body_text": "Bottom content here",
    }),
    (19, "overlay", LayoutType.OVERLAY, {
        "title": "Overlay", "body_text": "Dark background text",
    }),
    (20, "bullets", LayoutType.BULLETS, {
        "title": "Key Points", "bullets": ["Point 1", "Point 2", "Point 3"],
    }),
    (21, "comparison", LayoutType.COMPARISON, {
        "title": "Us vs Them", "comparison_items": _comparison_items(),
    }),
    (22, "timeline", LayoutType.TIMELINE, {
        "title": "Roadmap", "timeline_items": _timeline_items(),
    }),
    (23, "kpi_dashboard", LayoutType.KPI_DASHBOARD, {
        "title": "Metrics", "kpi_metrics": _kpi_metrics(),
    }),
    (24, "quote", LayoutType.QUOTE, {
        "title": "Quote", "quote_text": "Move fast.", "quote_author": "Zuck",
    }),
    (25, "team_grid", LayoutType.TEAM_GRID, {
        "title": "Our Team", "team_members": _team_members(),
    }),
    (26, "chart", LayoutType.CHART, {
        "title": "Revenue Growth", "chart_data": _chart_data(),
    }),
    (27, "blank", LayoutType.BLANK, {
        "title": "Thank You",
    }),
]

for num, layout_name, layout_type, extra in layout_tests:
    try:
        pc = PptxCompiler()
        dsl = _make_dsl([{"index": 0, "layout": layout_type, **extra}])
        output = pc.render_presentation(dsl)
        assert output.success, f"Failed: {output.error}"
        assert output.slide_count == 1
        # Verify it's a valid PPTX
        pptx_bytes = base64.b64decode(output.assets["pptx_base64"])
        assert pptx_bytes[:2] == b"PK", "Not a valid ZIP/PPTX"
        results.ok(f"PptxCompiler: {layout_name} layout")
    except Exception as e:
        results.fail(f"PptxCompiler: {layout_name} layout", str(e))


# 28. Speaker notes
try:
    pc = PptxCompiler()
    dsl = _make_dsl([{
        "index": 0, "title": "Noted",
        "speaker_notes": "Remember to emphasize ROI",
    }])
    output = pc.render_presentation(dsl)
    assert output.success
    notes = output.assets.get("slide_notes", [])
    assert len(notes) == 1
    assert "ROI" in notes[0]["notes"]
    results.ok("PptxCompiler: speaker notes embedding")
except Exception as e:
    results.fail("PptxCompiler: speaker notes embedding", str(e))

# 29. 3D fallback placeholder
try:
    pc = PptxCompiler()
    dsl = _make_dsl([{
        "index": 0, "title": "3D Slide", "three_scene": True,
    }])
    output = pc.render_presentation(dsl)
    assert output.success
    fallbacks = output.assets.get("3d_fallback_slides", [])
    assert len(fallbacks) == 1
    assert fallbacks[0] == 0
    results.ok("PptxCompiler: 3D fallback placeholder")
except Exception as e:
    results.fail("PptxCompiler: 3D fallback placeholder", str(e))

# 30. Theme colors extraction
try:
    from app.services.slides_new.renderers.pptx_compiler import (
        _extract_theme_colors, _extract_theme_fonts,
    )
    dsl = _make_dsl()
    colors = _extract_theme_colors(dsl)
    assert colors["primary"] == "#2563EB"
    assert "background" in colors
    assert "text_primary" in colors
    fonts = _extract_theme_fonts(dsl)
    assert fonts["heading"] == "Calibri"
    assert fonts["body"] == "Calibri"
    results.ok("PptxCompiler: theme colors extraction")
except Exception as e:
    results.fail("PptxCompiler: theme colors extraction", str(e))

# 31. Multi-slide compilation
try:
    pc = PptxCompiler()
    slides = [
        {"index": 0, "layout": LayoutType.CENTER_FOCUS,
         "title": "Title", "type": SlideType.TITLE_SLIDE},
        {"index": 1, "layout": LayoutType.BULLETS,
         "title": "Problem", "bullets": ["Pain 1", "Pain 2"]},
        {"index": 2, "layout": LayoutType.CHART,
         "title": "Traction", "chart_data": _chart_data()},
        {"index": 3, "layout": LayoutType.TEAM_GRID,
         "title": "Team", "team_members": _team_members()},
    ]
    dsl = _make_dsl(slides)
    output = pc.render_presentation(dsl)
    assert output.success
    assert output.slide_count == 4
    pptx_bytes = base64.b64decode(output.assets["pptx_base64"])
    assert len(pptx_bytes) > 5000
    results.ok("PptxCompiler: multi-slide compilation")
except Exception as e:
    results.fail("PptxCompiler: multi-slide compilation", str(e))

# 32. Error handling
try:
    pc = PptxCompiler()
    # Create invalid DSL that will trigger error in compilation
    dsl = _make_dsl()
    # Monkey-patch to force error
    original = pc._compile_slide_content
    def _raise(*a, **kw):
        raise ValueError("Simulated error")
    pc._compile_slide_content = _raise
    output = pc.render_presentation(dsl)
    assert output.success == False
    assert output.error is not None
    assert "Simulated error" in output.error
    pc._compile_slide_content = original
    results.ok("PptxCompiler: error handling returns success=False")
except Exception as e:
    results.fail("PptxCompiler: error handling returns success=False", str(e))


# ═══════════════════════════════════════════════════════════════
# HTML COMPILER TESTS (33-64)
# ═══════════════════════════════════════════════════════════════

print("\n-- HtmlCompiler Tests --")

# 33. Module imports
try:
    from app.services.slides_new.renderers.html_compiler import (
        HtmlCompiler, _esc, _theme_css_vars, _BASE_CSS, _NAV_JS, _CHART_JS,
    )
    results.ok("HtmlCompiler: module imports")
except Exception as e:
    results.fail("HtmlCompiler: module imports", str(e))

# 34. Class instantiation
try:
    hc = HtmlCompiler()
    assert hc is not None
    hc2 = HtmlCompiler(offline=True)
    assert hc2 is not None
    results.ok("HtmlCompiler: class instantiation")
except Exception as e:
    results.fail("HtmlCompiler: class instantiation", str(e))

# 35. get_renderer_type
try:
    hc = HtmlCompiler()
    assert hc.get_renderer_type() == RendererType.HTML
    results.ok("HtmlCompiler: get_renderer_type == HTML")
except Exception as e:
    results.fail("HtmlCompiler: get_renderer_type == HTML", str(e))

# 36. render_presentation minimal
try:
    hc = HtmlCompiler()
    dsl = _make_dsl()
    output = hc.render_presentation(dsl)
    assert output.success == True, f"Error: {output.error}"
    assert output.html != ""
    results.ok("HtmlCompiler: render_presentation minimal")
except Exception as e:
    results.fail("HtmlCompiler: render_presentation minimal", str(e))

# 37. has <!DOCTYPE html>
try:
    hc = HtmlCompiler()
    output = hc.render_presentation(_make_dsl())
    assert "<!DOCTYPE html>" in output.html
    assert "<html" in output.html
    assert "</html>" in output.html
    results.ok("HtmlCompiler: render_presentation has <!DOCTYPE html>")
except Exception as e:
    results.fail("HtmlCompiler: render_presentation has <!DOCTYPE html>", str(e))

# 38. CSS custom properties
try:
    hc = HtmlCompiler()
    output = hc.render_presentation(_make_dsl())
    assert "--primary" in output.html or "--primary" in output.css
    assert "--bg" in output.html or "--bg" in output.css
    assert "--font-heading" in output.html or "--font-heading" in output.css
    results.ok("HtmlCompiler: CSS custom properties in output")
except Exception as e:
    results.fail("HtmlCompiler: CSS custom properties in output", str(e))

# 39. Navigation JS
try:
    hc = HtmlCompiler()
    output = hc.render_presentation(_make_dsl())
    assert "ArrowRight" in output.html
    assert "PresentationNav" in output.html
    results.ok("HtmlCompiler: navigation JS in output")
except Exception as e:
    results.fail("HtmlCompiler: navigation JS in output", str(e))

# 40. render_slide single
try:
    hc = HtmlCompiler()
    slide = _make_slide_dsl(LayoutType.BULLETS, title="Points",
                            bullets=["One", "Two"])
    result = hc.render_slide(slide)
    assert isinstance(result, str)
    assert "Points" in result
    assert "One" in result
    assert "slide" in result.lower()
    results.ok("HtmlCompiler: render_slide single")
except Exception as e:
    results.fail("HtmlCompiler: render_slide single", str(e))


# 41-57: Layout HTML tests
html_layout_tests = [
    (41, "center_focus", LayoutType.CENTER_FOCUS, {
        "title": "Hero", "subtitle": "Sub",
    }),
    (42, "split_screen", LayoutType.SPLIT_SCREEN, {
        "title": "Split", "left_content": "L", "right_content": "R",
    }),
    (43, "full_bleed", LayoutType.FULL_BLEED, {
        "title": "Full Bleed",
    }),
    (44, "grid_2x2", LayoutType.GRID_2X2, {
        "title": "Grid", "bullets": ["A", "B", "C", "D"],
    }),
    (45, "grid_3x1", LayoutType.GRID_3X1, {
        "title": "Three", "kpi_metrics": _kpi_metrics(),
    }),
    (46, "text_left_visual_right", LayoutType.TEXT_LEFT_VISUAL_RIGHT, {
        "title": "TLVR", "bullets": ["B1"],
    }),
    (47, "text_right_visual_left", LayoutType.TEXT_RIGHT_VISUAL_LEFT, {
        "title": "TRVL", "bullets": ["B1"],
    }),
    (48, "top_bottom", LayoutType.TOP_BOTTOM, {
        "title": "Top", "body_text": "Bottom",
    }),
    (49, "overlay", LayoutType.OVERLAY, {
        "title": "Overlay", "body_text": "Text",
    }),
    (50, "bullets", LayoutType.BULLETS, {
        "title": "Bullets", "bullets": ["X", "Y"],
    }),
    (51, "comparison", LayoutType.COMPARISON, {
        "title": "Compare", "comparison_items": _comparison_items(),
    }),
    (52, "timeline", LayoutType.TIMELINE, {
        "title": "Road", "timeline_items": _timeline_items(),
    }),
    (53, "kpi_dashboard", LayoutType.KPI_DASHBOARD, {
        "title": "KPIs", "kpi_metrics": _kpi_metrics(),
    }),
    (54, "quote", LayoutType.QUOTE, {
        "title": "Quote", "quote_text": "Innovate.", "quote_author": "Jobs",
    }),
    (55, "team_grid", LayoutType.TEAM_GRID, {
        "title": "Team", "team_members": _team_members(),
    }),
    (56, "chart", LayoutType.CHART, {
        "title": "Chart", "chart_data": _chart_data(),
    }),
    (57, "blank", LayoutType.BLANK, {
        "title": "End",
    }),
]

for num, layout_name, layout_type, extra in html_layout_tests:
    try:
        hc = HtmlCompiler()
        dsl = _make_dsl([{"index": 0, "layout": layout_type, **extra}])
        output = hc.render_presentation(dsl)
        assert output.success, f"Failed: {output.error}"
        assert output.slide_count == 1
        assert "<!DOCTYPE html>" in output.html
        assert extra["title"] in output.html
        results.ok(f"HtmlCompiler: {layout_name} layout")
    except Exception as e:
        results.fail(f"HtmlCompiler: {layout_name} layout", str(e))


# 58. Speaker notes hidden div
try:
    hc = HtmlCompiler()
    dsl = _make_dsl([{
        "index": 0, "title": "Noted",
        "speaker_notes": "Key message: growth",
    }])
    output = hc.render_presentation(dsl)
    assert output.success
    assert "slide-notes" in output.html
    assert "Key message: growth" in output.html
    results.ok("HtmlCompiler: speaker notes hidden div")
except Exception as e:
    results.fail("HtmlCompiler: speaker notes hidden div", str(e))

# 59. 3D fallback notice
try:
    hc = HtmlCompiler()
    dsl = _make_dsl([{"index": 0, "title": "3D", "three_scene": True}])
    output = hc.render_presentation(dsl)
    assert output.success
    assert "three-d-notice" in output.html or "3D" in output.html
    results.ok("HtmlCompiler: 3D fallback notice")
except Exception as e:
    results.fail("HtmlCompiler: 3D fallback notice", str(e))

# 60. Chart CDN script tag
try:
    hc = HtmlCompiler()
    dsl = _make_dsl([{
        "index": 0, "layout": LayoutType.CHART,
        "title": "Chart", "chart_data": _chart_data(),
    }])
    output = hc.render_presentation(dsl)
    assert output.success
    assert "chart.js" in output.html.lower() or "chart.umd" in output.html
    results.ok("HtmlCompiler: chart CDN script tag")
except Exception as e:
    results.fail("HtmlCompiler: chart CDN script tag", str(e))

# 61. Offline mode no CDN
try:
    hc = HtmlCompiler(offline=True)
    dsl = _make_dsl([{
        "index": 0, "layout": LayoutType.CHART,
        "title": "Chart", "chart_data": _chart_data(),
    }])
    output = hc.render_presentation(dsl)
    assert output.success
    assert "cdn.jsdelivr" not in output.html
    results.ok("HtmlCompiler: offline mode no CDN")
except Exception as e:
    results.fail("HtmlCompiler: offline mode no CDN", str(e))

# 62. slide_count correct
try:
    hc = HtmlCompiler()
    slides = [{"index": i, "title": f"S{i}"} for i in range(7)]
    dsl = _make_dsl(slides)
    output = hc.render_presentation(dsl)
    assert output.slide_count == 7
    results.ok("HtmlCompiler: slide_count correct")
except Exception as e:
    results.fail("HtmlCompiler: slide_count correct", str(e))

# 63. Theme CSS vars generation
try:
    from app.services.slides_new.renderers.html_compiler import _theme_css_vars
    dsl = _make_dsl()
    css = _theme_css_vars(dsl)
    assert ":root{" in css
    assert "--primary:#2563EB" in css
    assert "--bg:#FFFFFF" in css
    results.ok("HtmlCompiler: theme CSS vars generation")
except Exception as e:
    results.fail("HtmlCompiler: theme CSS vars generation", str(e))

# 64. Error handling
try:
    hc = HtmlCompiler()
    dsl = _make_dsl()
    original = hc._compile_slide
    def _raise_err(*a, **kw):
        raise RuntimeError("HTML error")
    hc._compile_slide = _raise_err
    output = hc.render_presentation(dsl)
    assert output.success == False
    assert "HTML error" in output.error
    hc._compile_slide = original
    results.ok("HtmlCompiler: error handling")
except Exception as e:
    results.fail("HtmlCompiler: error handling", str(e))


# ═══════════════════════════════════════════════════════════════
# RENDER ROUTER TESTS (65-79)
# ═══════════════════════════════════════════════════════════════

print("\n-- RenderRouter Tests --")

# 65. Module imports
try:
    from app.services.slides_new.renderers.render_router import (
        RenderRouter, ExportFormat, ExportJobStatus, ExportJob,
        ContentCapabilities,
    )
    results.ok("RenderRouter: module imports")
except Exception as e:
    results.fail("RenderRouter: module imports", str(e))

# 66. Instantiation
try:
    rr = RenderRouter()
    assert rr is not None
    results.ok("RenderRouter: instantiation")
except Exception as e:
    results.fail("RenderRouter: instantiation", str(e))

# 67. register_renderer
try:
    rr = RenderRouter()
    rr.register_renderer(PptxCompiler())
    rr.register_renderer(HtmlCompiler())
    fmts = rr.get_available_formats()
    assert "pptx" in fmts
    assert "html" in fmts
    results.ok("RenderRouter: register_renderer")
except Exception as e:
    results.fail("RenderRouter: register_renderer", str(e))

# 68. get_available_formats
try:
    rr = RenderRouter()
    rr.register_renderer(PptxCompiler())
    fmts = rr.get_available_formats()
    assert isinstance(fmts, list)
    assert "pptx" in fmts
    results.ok("RenderRouter: get_available_formats")
except Exception as e:
    results.fail("RenderRouter: get_available_formats", str(e))

# 69. render PPTX
try:
    rr = RenderRouter()
    rr.register_renderer(PptxCompiler())
    dsl = _make_dsl()
    output = rr.render(dsl, ExportFormat.PPTX)
    assert output.success, f"Error: {output.error}"
    assert output.renderer == RendererType.PPTX
    results.ok("RenderRouter: render PPTX format")
except Exception as e:
    results.fail("RenderRouter: render PPTX format", str(e))

# 70. render HTML
try:
    rr = RenderRouter()
    rr.register_renderer(HtmlCompiler())
    dsl = _make_dsl()
    output = rr.render(dsl, ExportFormat.HTML)
    assert output.success, f"Error: {output.error}"
    assert output.renderer == RendererType.HTML
    assert "<!DOCTYPE html>" in output.html
    results.ok("RenderRouter: render HTML format")
except Exception as e:
    results.fail("RenderRouter: render HTML format", str(e))

# 71. render unavailable format
try:
    rr = RenderRouter()
    dsl = _make_dsl()
    output = rr.render(dsl, ExportFormat.PPTX)
    assert output.success == False
    assert "not available" in output.error.lower()
    results.ok("RenderRouter: render unavailable format")
except Exception as e:
    results.fail("RenderRouter: render unavailable format", str(e))

# 72. render_all
try:
    rr = RenderRouter()
    rr.register_renderer(PptxCompiler())
    rr.register_renderer(HtmlCompiler())
    dsl = _make_dsl()
    outputs = rr.render_all(dsl, [ExportFormat.PPTX, ExportFormat.HTML])
    assert "pptx" in outputs
    assert "html" in outputs
    assert outputs["pptx"].success
    assert outputs["html"].success
    results.ok("RenderRouter: render_all multi-format")
except Exception as e:
    results.fail("RenderRouter: render_all multi-format", str(e))

# 73. recommend_format standard
try:
    rr = RenderRouter()
    rr.register_renderer(PptxCompiler())
    rr.register_renderer(HtmlCompiler())
    dsl = _make_dsl()
    fmt = rr.recommend_format(dsl)
    assert isinstance(fmt, ExportFormat)
    # Standard content → PPTX (most portable)
    assert fmt == ExportFormat.PPTX
    results.ok("RenderRouter: recommend_format standard")
except Exception as e:
    results.fail("RenderRouter: recommend_format standard", str(e))

# 74. recommend_format with charts
try:
    rr = RenderRouter()
    rr.register_renderer(PptxCompiler())
    rr.register_renderer(HtmlCompiler())
    dsl = _make_dsl([{
        "index": 0, "layout": LayoutType.CHART,
        "title": "Chart", "chart_data": _chart_data(),
    }])
    fmt = rr.recommend_format(dsl)
    assert fmt == ExportFormat.HTML, f"Charts should recommend HTML, got {fmt}"
    results.ok("RenderRouter: recommend_format with charts")
except Exception as e:
    results.fail("RenderRouter: recommend_format with charts", str(e))

# 75. recommend_formats complementary
try:
    rr = RenderRouter()
    rr.register_renderer(PptxCompiler())
    rr.register_renderer(HtmlCompiler())
    dsl = _make_dsl()
    fmts = rr.recommend_formats(dsl)
    assert len(fmts) >= 1
    assert isinstance(fmts[0], ExportFormat)
    results.ok("RenderRouter: recommend_formats complementary")
except Exception as e:
    results.fail("RenderRouter: recommend_formats complementary", str(e))

# 76. ContentCapabilities
try:
    rr = RenderRouter()
    dsl = _make_dsl([
        {"index": 0, "title": "Chart", "chart_data": _chart_data(),
         "layout": LayoutType.CHART},
        {"index": 1, "title": "Team", "team_members": _team_members(),
         "layout": LayoutType.TEAM_GRID},
    ])
    caps = rr.analyze_content(dsl)
    assert caps.has_charts == True
    assert caps.has_complex_layouts == True
    assert caps.slide_count == 2
    d = caps.to_dict()
    assert "has_charts" in d
    assert "slide_count" in d
    results.ok("RenderRouter: ContentCapabilities analysis")
except Exception as e:
    results.fail("RenderRouter: ContentCapabilities analysis", str(e))

# 77. create_export_job
try:
    rr = RenderRouter()
    rr.register_renderer(PptxCompiler())
    rr.register_renderer(HtmlCompiler())
    dsl = _make_dsl()
    job = rr.create_export_job(dsl, [ExportFormat.PPTX, ExportFormat.HTML])
    assert job.status == ExportJobStatus.COMPLETED
    assert "pptx" in job.results
    assert "html" in job.results
    assert job.duration_ms > 0
    d = job.to_dict()
    assert "job_id" in d
    assert d["status"] == "completed"
    results.ok("RenderRouter: create_export_job")
except Exception as e:
    results.fail("RenderRouter: create_export_job", str(e))

# 78. ExportJobStatus lifecycle
try:
    from app.services.slides_new.renderers.render_router import ExportJobStatus
    assert ExportJobStatus.PENDING.value == "pending"
    assert ExportJobStatus.RENDERING.value == "rendering"
    assert ExportJobStatus.COMPLETED.value == "completed"
    assert ExportJobStatus.FAILED.value == "failed"
    results.ok("RenderRouter: ExportJobStatus lifecycle")
except Exception as e:
    results.fail("RenderRouter: ExportJobStatus lifecycle", str(e))

# 79. get_stats
try:
    rr = RenderRouter()
    rr.register_renderer(PptxCompiler())
    stats = rr.get_stats()
    assert "renderers" in stats
    assert "available_formats" in stats
    assert "pptx" in stats["renderers"]
    assert stats["renderers"]["pptx"]["total_renders"] == 0
    results.ok("RenderRouter: get_stats")
except Exception as e:
    results.fail("RenderRouter: get_stats", str(e))


# ═══════════════════════════════════════════════════════════════
# EXPORT ROUTES TESTS (80-86)
# ═══════════════════════════════════════════════════════════════

print("\n-- Export Routes Tests --")

# 80. Module imports
try:
    from app.api.routes.export_routes import (
        router as export_router,
        ExportRequest, ExportResponse, MultiExportRequest,
        MultiExportResponse, FormatInfo, RecommendResponse,
    )
    results.ok("ExportRoutes: module imports")
except Exception as e:
    results.fail("ExportRoutes: module imports", str(e))

# 81. Router prefix
try:
    from app.api.routes.export_routes import router as export_router
    assert export_router.prefix == "/api/v2/export"
    results.ok("ExportRoutes: router prefix")
except Exception as e:
    results.fail("ExportRoutes: router prefix", str(e))

# 82. FormatInfo schema
try:
    from app.api.routes.export_routes import FormatInfo
    fi = FormatInfo(
        name="pptx",
        description="PowerPoint",
        supports_charts=True,
        editable=True,
    )
    assert fi.name == "pptx"
    assert fi.editable == True
    results.ok("ExportRoutes: FormatInfo schema")
except Exception as e:
    results.fail("ExportRoutes: FormatInfo schema", str(e))

# 83. ExportRequest schema
try:
    from app.api.routes.export_routes import ExportRequest
    fields = ExportRequest.model_fields
    assert "presentation" in fields
    assert "theme_css" in fields
    assert "template_path" in fields
    results.ok("ExportRoutes: ExportRequest schema")
except Exception as e:
    results.fail("ExportRoutes: ExportRequest schema", str(e))

# 84. ExportResponse schema
try:
    from app.api.routes.export_routes import ExportResponse
    fields = ExportResponse.model_fields
    assert "success" in fields
    assert "format" in fields
    assert "pptx_base64" in fields
    assert "html" in fields
    assert "file_name" in fields
    results.ok("ExportRoutes: ExportResponse schema")
except Exception as e:
    results.fail("ExportRoutes: ExportResponse schema", str(e))

# 85. MultiExportRequest schema
try:
    from app.api.routes.export_routes import MultiExportRequest
    fields = MultiExportRequest.model_fields
    assert "presentation" in fields
    assert "formats" in fields
    results.ok("ExportRoutes: MultiExportRequest schema")
except Exception as e:
    results.fail("ExportRoutes: MultiExportRequest schema", str(e))

# 86. RecommendResponse schema
try:
    from app.api.routes.export_routes import RecommendResponse
    fields = RecommendResponse.model_fields
    assert "recommended" in fields
    assert "alternatives" in fields
    assert "capabilities" in fields
    assert "reasoning" in fields
    results.ok("ExportRoutes: RecommendResponse schema")
except Exception as e:
    results.fail("ExportRoutes: RecommendResponse schema", str(e))


# ═══════════════════════════════════════════════════════════════
# INTEGRATION TESTS (87-95)
# ═══════════════════════════════════════════════════════════════

print("\n-- Integration Tests --")

# 87. renderers __init__ Phase 7 exports
try:
    from app.services.slides_new.renderers import (
        PptxCompiler, HtmlCompiler, RenderRouter,
        ExportFormat, ExportJob, ExportJobStatus,
        ContentCapabilities,
    )
    results.ok("Integration: renderers __init__ Phase 7 exports")
except Exception as e:
    results.fail("Integration: renderers __init__ Phase 7 exports", str(e))

# 88. database Phase 7 index code
try:
    with open("app/database.py", "r") as f:
        db_code = f.read()
    assert "pptx_builds" in db_code
    assert "html_builds" in db_code
    assert "export_jobs" in db_code
    assert "phase7=True" in db_code
    results.ok("Integration: database Phase 7 index code")
except Exception as e:
    results.fail("Integration: database Phase 7 index code", str(e))

# 89. main.py export_routes registration
try:
    with open("main.py", "r") as f:
        main_code = f.read()
    assert "export_routes" in main_code
    assert "export_v2" in main_code
    results.ok("Integration: main.py export_routes registration")
except Exception as e:
    results.fail("Integration: main.py export_routes registration", str(e))

# 90. ExportFormat enum values
try:
    from app.services.slides_new.renderers.render_router import ExportFormat
    expected = {"pptx", "html", "reveal.js", "react", "all"}
    actual = {f.value for f in ExportFormat}
    assert actual == expected, f"Expected {expected}, got {actual}"
    results.ok("Integration: ExportFormat enum values")
except Exception as e:
    results.fail("Integration: ExportFormat enum values", str(e))

# 91. ExportJobStatus enum values
try:
    from app.services.slides_new.renderers.render_router import ExportJobStatus
    expected = {"pending", "rendering", "completed", "failed"}
    actual = {s.value for s in ExportJobStatus}
    assert actual == expected, f"Expected {expected}, got {actual}"
    results.ok("Integration: ExportJobStatus enum values")
except Exception as e:
    results.fail("Integration: ExportJobStatus enum values", str(e))

# 92. RendererType PPTX in enum
try:
    from app.services.slides_new.renderers.base_renderer import RendererType
    assert RendererType.PPTX.value == "pptx"
    results.ok("RendererType PPTX in enum")
except Exception as e:
    results.fail("RendererType PPTX in enum", str(e))

# 93. RendererType HTML in enum
try:
    assert RendererType.HTML.value == "html"
    results.ok("RendererType HTML in enum")
except Exception as e:
    results.fail("RendererType HTML in enum", str(e))

# 94. BaseRenderer ABC compliance (PptxCompiler)
try:
    from app.services.slides_new.renderers.base_renderer import BaseRenderer
    assert issubclass(PptxCompiler, BaseRenderer)
    pc = PptxCompiler()
    assert hasattr(pc, "get_renderer_type")
    assert hasattr(pc, "render_presentation")
    assert hasattr(pc, "render_slide")
    results.ok("BaseRenderer ABC compliance (PptxCompiler)")
except Exception as e:
    results.fail("BaseRenderer ABC compliance (PptxCompiler)", str(e))

# 95. BaseRenderer ABC compliance (HtmlCompiler)
try:
    assert issubclass(HtmlCompiler, BaseRenderer)
    hc = HtmlCompiler()
    assert hasattr(hc, "get_renderer_type")
    assert hasattr(hc, "render_presentation")
    assert hasattr(hc, "render_slide")
    results.ok("BaseRenderer ABC compliance (HtmlCompiler)")
except Exception as e:
    results.fail("BaseRenderer ABC compliance (HtmlCompiler)", str(e))


# ═══════════════════════════════════════════════════════════════
# EDGE CASE TESTS (96-100)
# ═══════════════════════════════════════════════════════════════

print("\n-- Edge Case Tests --")

# 96. Empty presentation (1 slide minimum enforced by Pydantic)
try:
    pc = PptxCompiler()
    dsl = _make_dsl([{"index": 0, "title": ""}])
    output = pc.render_presentation(dsl)
    assert output.success
    assert output.slide_count == 1
    results.ok("Edge: empty presentation")
except Exception as e:
    results.fail("Edge: empty presentation", str(e))

# 97. Slide with no layout defaults
try:
    pc = PptxCompiler()
    dsl = _make_dsl([{"index": 0, "title": "Default Layout"}])
    output = pc.render_presentation(dsl)
    assert output.success
    results.ok("Edge: slide with no layout defaults")
except Exception as e:
    results.fail("Edge: slide with no layout defaults", str(e))

# 98. All 17 layouts compile (PPTX)
try:
    pc = PptxCompiler()
    all_layouts = list(LayoutType)
    slides = []
    for i, lt in enumerate(all_layouts):
        sd = {"index": i, "layout": lt, "title": f"Layout {lt.value}"}
        if lt == LayoutType.CHART:
            sd["chart_data"] = _chart_data()
        elif lt == LayoutType.TEAM_GRID:
            sd["team_members"] = _team_members()
        elif lt == LayoutType.KPI_DASHBOARD:
            sd["kpi_metrics"] = _kpi_metrics()
        elif lt == LayoutType.TIMELINE:
            sd["timeline_items"] = _timeline_items()
        elif lt == LayoutType.COMPARISON:
            sd["comparison_items"] = _comparison_items()
        elif lt == LayoutType.QUOTE:
            sd["quote_text"] = "Test"
            sd["quote_author"] = "Author"
        elif lt == LayoutType.BULLETS:
            sd["bullets"] = ["A", "B"]
        slides.append(sd)

    dsl = _make_dsl(slides, title="All Layouts PPTX")
    output = pc.render_presentation(dsl)
    assert output.success, f"Failed: {output.error}"
    assert output.slide_count == len(all_layouts)
    results.ok("Edge: all 17 layouts compile (PPTX)")
except Exception as e:
    results.fail("Edge: all 17 layouts compile (PPTX)", str(e))

# 99. All 17 layouts compile (HTML)
try:
    hc = HtmlCompiler()
    all_layouts = list(LayoutType)
    slides = []
    for i, lt in enumerate(all_layouts):
        sd = {"index": i, "layout": lt, "title": f"Layout {lt.value}"}
        if lt == LayoutType.CHART:
            sd["chart_data"] = _chart_data()
        elif lt == LayoutType.TEAM_GRID:
            sd["team_members"] = _team_members()
        elif lt == LayoutType.KPI_DASHBOARD:
            sd["kpi_metrics"] = _kpi_metrics()
        elif lt == LayoutType.TIMELINE:
            sd["timeline_items"] = _timeline_items()
        elif lt == LayoutType.COMPARISON:
            sd["comparison_items"] = _comparison_items()
        elif lt == LayoutType.QUOTE:
            sd["quote_text"] = "Test"
            sd["quote_author"] = "Author"
        elif lt == LayoutType.BULLETS:
            sd["bullets"] = ["A", "B"]
        slides.append(sd)

    dsl = _make_dsl(slides, title="All Layouts HTML")
    output = hc.render_presentation(dsl)
    assert output.success, f"Failed: {output.error}"
    assert output.slide_count == len(all_layouts)
    results.ok("Edge: all 17 layouts compile (HTML)")
except Exception as e:
    results.fail("Edge: all 17 layouts compile (HTML)", str(e))

# 100. Large presentation (20 slides)
try:
    pc = PptxCompiler()
    slides = []
    for i in range(20):
        layout = list(LayoutType)[i % len(list(LayoutType))]
        sd = {"index": i, "layout": layout, "title": f"Slide {i+1}"}
        if layout == LayoutType.CHART:
            sd["chart_data"] = _chart_data()
        elif layout == LayoutType.TEAM_GRID:
            sd["team_members"] = _team_members()
        elif layout == LayoutType.KPI_DASHBOARD:
            sd["kpi_metrics"] = _kpi_metrics()
        elif layout == LayoutType.TIMELINE:
            sd["timeline_items"] = _timeline_items()
        elif layout == LayoutType.COMPARISON:
            sd["comparison_items"] = _comparison_items()
        elif layout == LayoutType.QUOTE:
            sd["quote_text"] = "Test"
        elif layout == LayoutType.BULLETS:
            sd["bullets"] = ["Point"]
        slides.append(sd)

    dsl = _make_dsl(slides, title="Large Deck")
    output = pc.render_presentation(dsl)
    assert output.success, f"Failed: {output.error}"
    assert output.slide_count == 20
    pptx_bytes = base64.b64decode(output.assets["pptx_base64"])
    assert len(pptx_bytes) > 10000
    results.ok("Edge: large presentation (20 slides)")
except Exception as e:
    results.fail("Edge: large presentation (20 slides)", str(e))


# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════

all_passed = results.summary()
sys.exit(0 if all_passed else 1)
