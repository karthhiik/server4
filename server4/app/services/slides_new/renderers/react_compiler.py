"""
React + Three.js Compiler — Phase 6.

Compiles PresentationDSL / SlideDSL into a React component tree
(JSX/TSX source) with Three.js 3D scenes, Framer Motion animations,
and Tailwind CSS styling.

Architecture:
    PresentationDSL --> ReactCompiler --> RenderOutput (component bundle)
    SlideDSL        --> ReactCompiler --> str (single component JSX)

Output includes:
    - html  → Complete React app entry point (App.tsx source)
    - css   → Tailwind + theme CSS variables
    - js    → Vite config and shared utilities
    - assets → Import manifest, lazy-load directives, scene configs

Features supported:
    - All 17 LayoutType variants → React component mapping
    - 6 Three.js scene types (globe, bar-chart, particles, scatter,
      floating-cards, data-flow) via @react-three/fiber
    - Framer Motion animations (10 presets)
    - Adaptive quality downgrade (high → medium → low → 2D)
    - Lazy-loading of Three.js with skeleton placeholders
    - Responsive 16:9 aspect ratio
    - Tailwind CSS utility classes + CSS custom properties
    - Chart rendering via Recharts
    - Keyboard navigation (← → Esc)
    - Speaker notes panel
"""

import hashlib
import html as html_mod
import json
import re
from typing import Any, Optional

from app.models.dsl_v2 import (
    AnimationType,
    BackgroundType,
    ElementType,
    LayoutType,
    PresentationDSL,
    SlideDSL,
    SlideContentV2,
    SlideElement,
    SlideStyle,
    SlideType,
    ThreeSceneConfig,
    ThreeSceneType,
)
from app.services.slides_new.renderers.base_renderer import (
    BaseRenderer,
    RenderOutput,
    RendererType,
)
from app.services.slides_new.renderers.react_templates import (
    COMPONENT_TEMPLATES,
    SCENE_TEMPLATES,
    MOTION_VARIANTS,
    UTILITY_COMPONENTS,
    SLIDE_WRAPPER_TEMPLATE,
    ComponentTemplate,
    SceneTemplate,
    MotionPreset,
    get_component_template,
    get_scene_template,
    get_imports_for_layout,
    get_motion_variant,
)
from app.services.slides_new.renderers.performance_guardrails import (
    PerformanceGuardrails,
    QualityLevel,
    SceneBudgetReport,
    LazyLoadDirective,
)


# ═══════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════

# Animation type to MotionPreset mapping
ANIMATION_PRESET_MAP: dict[AnimationType, str] = {
    AnimationType.FADE_IN: "fadeIn",
    AnimationType.SLIDE_UP: "slideUp",
    AnimationType.GROW: "scaleUp",
    AnimationType.SHRINK: "scaleUp",
    AnimationType.STRIKE: "slideLeft",
    AnimationType.HIGHLIGHT: "pulse",
}

# SlideType → suggested default animation if none specified
SLIDE_TYPE_ANIMATION: dict[SlideType, str] = {
    SlideType.TITLE_SLIDE: "scaleUp",
    SlideType.PROBLEM_SLIDE: "slideUp",
    SlideType.SOLUTION_SLIDE: "slideLeft",
    SlideType.MARKET_SLIDE: "fadeIn",
    SlideType.TRACTION_SLIDE: "staggerChildren",
    SlideType.BUSINESS_MODEL_SLIDE: "slideUp",
    SlideType.TEAM_SLIDE: "staggerChildren",
    SlideType.FINANCIAL_SLIDE: "fadeIn",
    SlideType.COMPETITION_SLIDE: "slideLeft",
    SlideType.CLOSING_SLIDE: "scaleUp",
    SlideType.CUSTOM: "fadeIn",
}

# Layout classes for containers
LAYOUT_TAILWIND: dict[str, str] = {
    "center-focus": "flex flex-col items-center justify-center h-full text-center px-16",
    "split-screen": "grid grid-cols-2 h-full gap-0",
    "full-bleed": "relative h-full w-full overflow-hidden",
    "grid-2x2": "grid grid-cols-2 grid-rows-2 gap-6 h-full p-8",
    "grid-3x1": "grid grid-cols-3 gap-6 h-full p-8",
    "text-left-visual-right": "grid grid-cols-[1.2fr_1fr] h-full gap-0",
    "text-right-visual-left": "grid grid-cols-[1fr_1.2fr] h-full gap-0",
    "top-bottom": "flex flex-col h-full",
    "overlay": "relative h-full w-full",
    "bullets": "flex flex-col justify-center h-full px-16 py-12",
    "comparison": "flex flex-col h-full px-12 py-8",
    "timeline": "flex flex-col h-full px-12 py-8",
    "kpi-dashboard": "flex flex-col h-full px-12 py-8",
    "quote": "flex flex-col items-center justify-center h-full px-20 text-center",
    "team-grid": "flex flex-col h-full px-12 py-8",
    "chart": "flex flex-col h-full px-12 py-8",
    "blank": "relative h-full w-full",
}


def _esc(text: str) -> str:
    """Escape text for safe JSX embedding (prevent XSS in generated source)."""
    if not text:
        return ""
    # Escape JSX-sensitive characters
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace("{", "&#123;")
    text = text.replace("}", "&#125;")
    text = text.replace('"', "&quot;")
    return text


def _jsx_string(text: str) -> str:
    """Format a string for use as a JSX attribute value."""
    if not text:
        return '""'
    # Escape special chars for JSX string literal
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _stable_id(prefix: str, index: int) -> str:
    """Generate a stable component key."""
    return f"{prefix}-{index}"


# ═══════════════════════════════════════════════════════════════════
# REACT COMPILER
# ═══════════════════════════════════════════════════════════════════


class ReactCompiler(BaseRenderer):
    """
    Compiles Slide DSL v2 into React + Three.js component source code.

    Generates a complete React application bundle:
    - App.tsx: Slide deck with navigation and animation
    - Per-slide components with proper layout and 3D integration
    - Theme CSS variables from PresentationDSL theme
    - Vite configuration for dev server with HMR
    - Performance-aware lazy loading for Three.js scenes

    Usage:
        compiler = ReactCompiler()
        output = compiler.render_presentation(presentation_dsl, theme_css)
        # output.html = App.tsx source
        # output.css = Theme CSS
        # output.js = Vite config
        # output.assets = {import_manifest, scene_configs, lazy_load_plan}
    """

    def __init__(self, quality: QualityLevel = QualityLevel.HIGH):
        self._guardrails = PerformanceGuardrails()
        self._quality = quality

    def get_renderer_type(self) -> RendererType:
        return RendererType.REACT_3D

    # ═══════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════

    def render_presentation(
        self,
        presentation_dsl: PresentationDSL,
        theme_css: str = "",
    ) -> RenderOutput:
        """
        Compile a full PresentationDSL into a React application bundle.

        Returns:
            RenderOutput where:
            - html = App.tsx component source
            - css = Theme CSS with custom properties
            - js = Vite config source
            - assets = import manifest, scene configs, lazy-load plan
        """
        try:
            slides = presentation_dsl.slides
            dims = presentation_dsl.presentation.dimensions
            title = presentation_dsl.presentation.title
            theme = presentation_dsl.presentation.theme

            # 1. Analyze 3D scenes for performance budgeting
            scene_analysis = self._analyze_3d_scenes(slides)

            # 2. Generate per-slide component source
            slide_components: list[str] = []
            slide_imports: list[str] = []
            for i, slide in enumerate(slides):
                comp_name = f"Slide{i}"
                comp_source = self._compile_slide_component(slide, comp_name, scene_analysis)
                slide_components.append(comp_source)
                slide_imports.append(comp_name)

            # 3. Build App.tsx with navigation and slide mounting
            app_source = self._build_app_tsx(
                title=title,
                slide_components=slide_components,
                slide_imports=slide_imports,
                slide_count=len(slides),
                dims=dims,
            )

            # 4. Build theme CSS
            theme_css_output = self._build_theme_css(theme, theme_css)

            # 5. Build Vite config
            vite_config = self._build_vite_config()

            # 6. Build import manifest (for bundler)
            import_manifest = self._build_import_manifest(slides, scene_analysis)

            # 7. Build lazy-load plan
            lazy_plan = self._build_lazy_load_plan(slides, scene_analysis)

            return RenderOutput(
                renderer=RendererType.REACT_3D,
                html=app_source,
                css=theme_css_output,
                js=vite_config,
                assets={
                    "import_manifest": import_manifest,
                    "scene_configs": {
                        i: s for i, s in scene_analysis.items()
                    },
                    "lazy_load_plan": lazy_plan,
                    "slide_count": len(slides),
                    "has_3d": any(
                        s.get("scene_type") is not None
                        for s in scene_analysis.values()
                    ),
                    "quality_level": self._quality.value,
                },
                metadata={
                    "renderer": "react-threejs",
                    "slide_count": len(slides),
                    "title": title,
                    "has_3d_scenes": any(
                        s.get("scene_type") is not None
                        for s in scene_analysis.values()
                    ),
                    "quality": self._quality.value,
                    "framework": "react-18",
                    "bundler": "vite",
                    "styling": "tailwind-css",
                },
                success=True,
                slide_count=len(slides),
            )
        except Exception as exc:
            return RenderOutput(
                renderer=RendererType.REACT_3D,
                success=False,
                error=str(exc),
            )

    def render_slide(self, slide_dsl: SlideDSL, theme_css: str = "") -> str:
        """Compile a single SlideDSL into a React component JSX string."""
        scene_analysis = self._analyze_3d_scenes([slide_dsl])
        return self._compile_slide_component(slide_dsl, "SlidePreview", scene_analysis)

    # ═══════════════════════════════════════════════════════════════
    # APP.TSX BUILDER
    # ═══════════════════════════════════════════════════════════════

    def _build_app_tsx(
        self,
        title: str,
        slide_components: list[str],
        slide_imports: list[str],
        slide_count: int,
        dims: Any,
    ) -> str:
        """Build the root App.tsx with slide navigation and rendering."""
        safe_title = _esc(title)

        # Build inline slide component definitions
        components_block = "\n\n".join(slide_components)

        # Build slides array
        slides_array = ",\n    ".join(
            f"{{ component: {name}, key: '{name}' }}" for name in slide_imports
        )

        return f'''// Auto-generated by Barise ReactCompiler — Phase 6
// Title: {safe_title}
import React, {{ useState, useCallback, useEffect, memo, Suspense, lazy }} from "react";
import {{ motion, AnimatePresence }} from "framer-motion";
import "./theme.css";

// ── Slide Components ────────────────────────────────────────

{components_block}

// ── Slide Registry ──────────────────────────────────────────

const SLIDES = [
    {slides_array}
];

// ── Navigation Hook ─────────────────────────────────────────

function useSlideNavigation(total: number) {{
  const [current, setCurrent] = useState(0);

  const next = useCallback(() => {{
    setCurrent((c) => Math.min(c + 1, total - 1));
  }}, [total]);

  const prev = useCallback(() => {{
    setCurrent((c) => Math.max(c - 1, 0));
  }}, []);

  const goTo = useCallback((idx: number) => {{
    setCurrent(Math.max(0, Math.min(idx, total - 1)));
  }}, [total]);

  useEffect(() => {{
    const handler = (e: KeyboardEvent) => {{
      if (e.key === "ArrowRight" || e.key === " ") next();
      else if (e.key === "ArrowLeft") prev();
      else if (e.key === "Escape") goTo(0);
    }};
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }}, [next, prev, goTo]);

  return {{ current, next, prev, goTo, total }};
}}

// ── Slide Wrapper ───────────────────────────────────────────

const SlideWrapper = memo(function SlideWrapper({{
  children,
  isActive,
  index,
}}: {{
  children: React.ReactNode;
  isActive: boolean;
  index: number;
}}) {{
  return (
    <motion.div
      className="slide-wrapper absolute inset-0 w-full h-full"
      initial={{ opacity: 0 }}
      animate={{ opacity: isActive ? 1 : 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5, ease: "easeInOut" }}
      style={{ display: isActive ? "block" : "none" }}
      data-slide-index={{index}}
    >
      {{children}}
    </motion.div>
  );
}});

// ── App ─────────────────────────────────────────────────────

export default function App() {{
  const nav = useSlideNavigation(SLIDES.length);

  return (
    <div
      className="presentation-container relative overflow-hidden bg-[var(--bg-primary)]"
      style={{{{
        width: "{dims.width}px",
        height: "{dims.height}px",
        aspectRatio: "{dims.width}/{dims.height}",
        maxWidth: "100vw",
        maxHeight: "100vh",
      }}}}
    >
      <AnimatePresence mode="wait">
        {{SLIDES.map((slide, i) => (
          <SlideWrapper key={{slide.key}} isActive={{i === nav.current}} index={{i}}>
            <slide.component />
          </SlideWrapper>
        ))}}
      </AnimatePresence>

      {{/* Navigation Controls */}}
      <div className="fixed bottom-4 right-4 flex gap-2 z-50">
        <button
          onClick={{nav.prev}}
          className="px-3 py-1.5 rounded bg-white/10 hover:bg-white/20
                     text-white text-sm backdrop-blur-sm transition"
          disabled={{nav.current === 0}}
        >
          &larr;
        </button>
        <span className="px-3 py-1.5 text-white/60 text-sm">
          {{nav.current + 1}} / {{nav.total}}
        </span>
        <button
          onClick={{nav.next}}
          className="px-3 py-1.5 rounded bg-white/10 hover:bg-white/20
                     text-white text-sm backdrop-blur-sm transition"
          disabled={{nav.current === nav.total - 1}}
        >
          &rarr;
        </button>
      </div>
    </div>
  );
}}
'''

    # ═══════════════════════════════════════════════════════════════
    # SLIDE COMPONENT COMPILER
    # ═══════════════════════════════════════════════════════════════

    def _compile_slide_component(
        self,
        slide: SlideDSL,
        comp_name: str,
        scene_analysis: dict[int, dict[str, Any]],
    ) -> str:
        """Compile a single SlideDSL into a named React component function."""
        layout = slide.layout.value
        template = get_component_template(layout)
        layout_class = LAYOUT_TAILWIND.get(layout, LAYOUT_TAILWIND["blank"])

        # Determine animation
        animation = self._resolve_animation(slide)
        motion_variant = get_motion_variant(animation)

        # Build background style
        bg_style = self._compile_background(slide.style)

        # Build inner content
        inner_jsx = self._compile_content_by_layout(slide, template, scene_analysis)

        # Build speaker notes (as data attribute for presenter mode)
        notes_attr = ""
        if slide.speakerNotes:
            safe_notes = _jsx_string(slide.speakerNotes)
            notes_attr = f"\n      data-speaker-notes={{{safe_notes}}}"

        # Wrap in motion.div with animation
        initial = json.dumps(motion_variant.get("initial", {}))
        animate = json.dumps(motion_variant.get("animate", {}))
        transition_cfg = motion_variant.get("transition", {"duration": 0.6})
        transition = json.dumps(transition_cfg)

        return f'''const {comp_name} = memo(function {comp_name}() {{
  return (
    <motion.div
      className="{layout_class}"
      style={{{{{bg_style}}}}}
      initial={{{initial}}}
      animate={{{animate}}}
      transition={{{transition}}}{notes_attr}
    >
      {inner_jsx}
    </motion.div>
  );
}});'''

    # ═══════════════════════════════════════════════════════════════
    # LAYOUT-SPECIFIC CONTENT COMPILATION
    # ═══════════════════════════════════════════════════════════════

    def _compile_content_by_layout(
        self,
        slide: SlideDSL,
        template: Optional[ComponentTemplate],
        scene_analysis: dict[int, dict[str, Any]],
    ) -> str:
        """Compile slide content into JSX based on layout type."""
        c = slide.content
        layout = slide.layout.value
        scene_info = scene_analysis.get(slide.index, {})
        has_3d = scene_info.get("scene_type") is not None

        # Dispatch to layout-specific compiler
        compiler_map = {
            "center-focus": self._compile_center_focus,
            "split-screen": self._compile_split_screen,
            "full-bleed": self._compile_full_bleed,
            "grid-2x2": self._compile_grid_2x2,
            "grid-3x1": self._compile_grid_3x1,
            "text-left-visual-right": self._compile_text_visual,
            "text-right-visual-left": self._compile_visual_text,
            "top-bottom": self._compile_top_bottom,
            "overlay": self._compile_overlay,
            "bullets": self._compile_bullets,
            "comparison": self._compile_comparison,
            "timeline": self._compile_timeline,
            "kpi-dashboard": self._compile_kpi_dashboard,
            "quote": self._compile_quote,
            "team-grid": self._compile_team_grid,
            "chart": self._compile_chart,
            "blank": self._compile_blank,
        }

        compiler_fn = compiler_map.get(layout, self._compile_generic)
        return compiler_fn(c, slide, scene_info)

    # ── Layout compilers ──────────────────────────────────────

    def _compile_center_focus(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """Center-focus layout: large centered title with optional 3D background."""
        parts: list[str] = []

        # 3D background
        if scene.get("scene_type"):
            parts.append(self._compile_3d_background(scene))

        # Title
        if c.title:
            parts.append(
                f'<motion.h1 className="text-6xl font-bold tracking-tight '
                f'text-[var(--text-primary)]" '
                f'initial={{{{ opacity: 0, y: 20 }}}} '
                f'animate={{{{ opacity: 1, y: 0 }}}} '
                f'transition={{{{ delay: 0.2 }}}}>'
                f'{_esc(c.title)}</motion.h1>'
            )

        # Subtitle
        if c.subtitle:
            parts.append(
                f'<motion.p className="text-2xl text-[var(--text-secondary)] mt-4" '
                f'initial={{{{ opacity: 0 }}}} animate={{{{ opacity: 1 }}}} '
                f'transition={{{{ delay: 0.5 }}}}>'
                f'{_esc(c.subtitle)}</motion.p>'
            )

        # Tagline
        if c.tagline:
            parts.append(
                f'<motion.p className="text-lg text-[var(--text-muted)] mt-6 '
                f'font-light tracking-wide" '
                f'initial={{{{ opacity: 0 }}}} animate={{{{ opacity: 1 }}}} '
                f'transition={{{{ delay: 0.8 }}}}>'
                f'{_esc(c.tagline)}</motion.p>'
            )

        return "\n      ".join(parts) if parts else '<div className="empty-slide" />'

    def _compile_split_screen(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """Split-screen layout: text on one side, visual on the other."""
        left_parts: list[str] = []
        right_parts: list[str] = []

        # Text side (left by default)
        text_items: list[str] = []
        if c.title:
            text_items.append(
                f'<h2 className="text-4xl font-bold text-[var(--text-primary)]">'
                f'{_esc(c.title)}</h2>'
            )
        if c.body_text:
            text_items.append(
                f'<p className="text-lg text-[var(--text-secondary)] mt-4 leading-relaxed">'
                f'{_esc(c.body_text)}</p>'
            )
        if c.bullets:
            bullet_items = "\n            ".join(
                f'<li className="text-[var(--text-secondary)]">{_esc(b)}</li>'
                for b in c.bullets
            )
            text_items.append(
                f'<ul className="space-y-3 mt-4 list-disc list-inside">\n'
                f'            {bullet_items}\n'
                f'          </ul>'
            )

        left_parts.append(
            f'<div className="flex flex-col justify-center px-12 py-8">\n'
            f'        {"".join(text_items)}\n'
            f'      </div>'
        )

        # Visual side (right)
        if scene.get("scene_type"):
            right_parts.append(self._compile_3d_panel(scene))
        elif c.image_url:
            right_parts.append(
                f'<div className="flex items-center justify-center h-full bg-[var(--bg-secondary)]">'
                f'<img src="{_esc(c.image_url)}" alt="{_esc(c.title or "")}" '
                f'className="max-w-full max-h-full object-contain" /></div>'
            )
        else:
            right_parts.append(
                '<div className="h-full bg-[var(--bg-secondary)]" />'
            )

        left_block = "\n      ".join(left_parts)
        right_block = "\n      ".join(right_parts)
        return f"{left_block}\n      {right_block}"

    def _compile_full_bleed(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """Full-bleed layout: edge-to-edge visual with overlaid content."""
        parts: list[str] = []

        # Background layer
        if scene.get("scene_type"):
            parts.append(
                f'<div className="absolute inset-0 z-0">\n'
                f'        {self._compile_3d_inline(scene)}\n'
                f'      </div>'
            )
        elif c.image_url:
            parts.append(
                f'<div className="absolute inset-0 z-0">'
                f'<img src="{_esc(c.image_url)}" className="w-full h-full object-cover" '
                f'alt="" /></div>'
            )

        # Content overlay
        overlay_items: list[str] = []
        if c.title:
            overlay_items.append(
                f'<h1 className="text-5xl font-bold text-white">{_esc(c.title)}</h1>'
            )
        if c.subtitle:
            overlay_items.append(
                f'<p className="text-xl text-white/80 mt-3">{_esc(c.subtitle)}</p>'
            )

        if overlay_items:
            parts.append(
                f'<div className="relative z-10 flex flex-col justify-end p-12 h-full '
                f'bg-gradient-to-t from-black/60 to-transparent">\n'
                f'        {"".join(overlay_items)}\n'
                f'      </div>'
            )

        return "\n      ".join(parts) if parts else '<div className="empty-slide" />'

    def _compile_grid_2x2(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """2x2 grid layout: four cells with optional title bar."""
        parts: list[str] = []

        # Title spans full width if present
        if c.title:
            parts.append(
                f'<div className="col-span-2 flex items-end">'
                f'<h2 className="text-3xl font-bold text-[var(--text-primary)]">'
                f'{_esc(c.title)}</h2></div>'
            )

        # Populate grid cells from bullets or elements
        items = c.bullets or []
        for i in range(4):
            cell_content = _esc(items[i]) if i < len(items) else ""
            parts.append(
                f'<motion.div className="rounded-xl bg-[var(--bg-secondary)] p-6 '
                f'flex items-center justify-center" '
                f'initial={{{{ opacity: 0, scale: 0.9 }}}} '
                f'animate={{{{ opacity: 1, scale: 1 }}}} '
                f'transition={{{{ delay: {0.1 * (i + 1)} }}}}>'
                f'<p className="text-[var(--text-secondary)] text-center">'
                f'{cell_content}</p></motion.div>'
            )

        return "\n      ".join(parts)

    def _compile_grid_3x1(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """3-column grid: three pillars/features/steps."""
        parts: list[str] = []

        if c.title:
            parts.append(
                f'<div className="col-span-3 flex items-end pb-4">'
                f'<h2 className="text-3xl font-bold text-[var(--text-primary)]">'
                f'{_esc(c.title)}</h2></div>'
            )

        items = c.bullets or []
        for i in range(3):
            cell_content = _esc(items[i]) if i < len(items) else ""
            parts.append(
                f'<motion.div className="rounded-xl bg-[var(--bg-secondary)] p-8 '
                f'flex flex-col items-center justify-center text-center" '
                f'initial={{{{ opacity: 0, y: 20 }}}} '
                f'animate={{{{ opacity: 1, y: 0 }}}} '
                f'transition={{{{ delay: {0.15 * (i + 1)} }}}}>'
                f'<p className="text-[var(--text-secondary)]">{cell_content}</p>'
                f'</motion.div>'
            )

        return "\n      ".join(parts)

    def _compile_text_visual(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """Text-left, visual-right layout."""
        return self._compile_split_screen(c, slide, scene)

    def _compile_visual_text(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """Visual-left, text-right layout (reversed split)."""
        # Same as split but swap order
        left_parts: list[str] = []
        right_parts: list[str] = []

        # Visual side (left)
        if scene.get("scene_type"):
            left_parts.append(self._compile_3d_panel(scene))
        elif c.image_url:
            left_parts.append(
                f'<div className="flex items-center justify-center h-full bg-[var(--bg-secondary)]">'
                f'<img src="{_esc(c.image_url)}" alt="" '
                f'className="max-w-full max-h-full object-contain" /></div>'
            )
        else:
            left_parts.append(
                '<div className="h-full bg-[var(--bg-secondary)]" />'
            )

        # Text side (right)
        text_items: list[str] = []
        if c.title:
            text_items.append(
                f'<h2 className="text-4xl font-bold text-[var(--text-primary)]">'
                f'{_esc(c.title)}</h2>'
            )
        if c.body_text:
            text_items.append(
                f'<p className="text-lg text-[var(--text-secondary)] mt-4 leading-relaxed">'
                f'{_esc(c.body_text)}</p>'
            )

        right_parts.append(
            f'<div className="flex flex-col justify-center px-12 py-8">\n'
            f'        {"".join(text_items)}\n'
            f'      </div>'
        )

        left_block = "\n      ".join(left_parts)
        right_block = "\n      ".join(right_parts)
        return f"{left_block}\n      {right_block}"

    def _compile_top_bottom(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """Top-bottom stacked layout."""
        parts: list[str] = []

        # Header zone
        if c.title:
            parts.append(
                f'<div className="px-12 pt-10 pb-4">'
                f'<h2 className="text-4xl font-bold text-[var(--text-primary)]">'
                f'{_esc(c.title)}</h2></div>'
            )

        # Content zone
        content_items: list[str] = []
        if c.body_text:
            content_items.append(
                f'<p className="text-lg text-[var(--text-secondary)] leading-relaxed">'
                f'{_esc(c.body_text)}</p>'
            )
        if c.bullets:
            li_items = "\n            ".join(
                f'<li>{_esc(b)}</li>' for b in c.bullets
            )
            content_items.append(f'<ul className="space-y-2 mt-4">\n            {li_items}\n          </ul>')

        parts.append(
            f'<div className="flex-1 px-12 py-4">\n'
            f'        {"".join(content_items)}\n'
            f'      </div>'
        )

        return "\n      ".join(parts)

    def _compile_overlay(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """Overlay layout: glassmorphism card over background."""
        parts: list[str] = []

        # Background
        if scene.get("scene_type"):
            parts.append(
                f'<div className="absolute inset-0 z-0">'
                f'{self._compile_3d_inline(scene)}</div>'
            )

        # Glassmorphism card
        card_items: list[str] = []
        if c.title:
            card_items.append(
                f'<h2 className="text-3xl font-bold text-white">{_esc(c.title)}</h2>'
            )
        if c.body_text:
            card_items.append(
                f'<p className="text-white/80 mt-3">{_esc(c.body_text)}</p>'
            )

        parts.append(
            f'<div className="relative z-10 flex items-center justify-center h-full p-12">'
            f'<div className="bg-white/10 backdrop-blur-xl rounded-2xl p-10 '
            f'max-w-2xl border border-white/20 shadow-2xl">\n'
            f'        {"".join(card_items)}\n'
            f'      </div></div>'
        )

        return "\n      ".join(parts)

    def _compile_bullets(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """Bullet list with staggered animation."""
        parts: list[str] = []

        if c.title:
            parts.append(
                f'<motion.h2 className="text-4xl font-bold text-[var(--text-primary)] mb-8" '
                f'initial={{{{ opacity: 0, y: 20 }}}} animate={{{{ opacity: 1, y: 0 }}}}>'
                f'{_esc(c.title)}</motion.h2>'
            )

        if c.bullets:
            li_items = "\n        ".join(
                f'<motion.li className="text-xl text-[var(--text-secondary)] py-2" '
                f'initial={{{{ opacity: 0, x: -20 }}}} '
                f'animate={{{{ opacity: 1, x: 0 }}}} '
                f'transition={{{{ delay: {0.15 * (i + 1)} }}}}>'
                f'{_esc(b)}</motion.li>'
                for i, b in enumerate(c.bullets)
            )
            parts.append(
                f'<ul className="space-y-2">\n        {li_items}\n      </ul>'
            )

        return "\n      ".join(parts) if parts else '<div />'

    def _compile_comparison(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """Comparison table layout."""
        parts: list[str] = []

        if c.title:
            parts.append(
                f'<h2 className="text-3xl font-bold text-[var(--text-primary)] mb-6">'
                f'{_esc(c.title)}</h2>'
            )

        if c.comparison_items:
            rows: list[str] = []
            for i, item in enumerate(c.comparison_items):
                advantage_class = "text-green-400" if item.advantage else "text-[var(--text-secondary)]"
                rows.append(
                    f'<motion.tr className="border-b border-white/10" '
                    f'initial={{{{ opacity: 0 }}}} animate={{{{ opacity: 1 }}}} '
                    f'transition={{{{ delay: {0.1 * (i + 1)} }}}}>'
                    f'<td className="py-3 px-4 text-[var(--text-primary)] font-medium">'
                    f'{_esc(item.label)}</td>'
                    f'<td className="py-3 px-4 {advantage_class}">'
                    f'{_esc(item.us or "")}</td>'
                    f'<td className="py-3 px-4 text-[var(--text-muted)]">'
                    f'{_esc(item.them or "")}</td>'
                    f'</motion.tr>'
                )
            rows_html = "\n          ".join(rows)
            parts.append(
                f'<table className="w-full">'
                f'<thead><tr className="text-left text-sm text-[var(--text-muted)] uppercase">'
                f'<th className="py-2 px-4">Feature</th>'
                f'<th className="py-2 px-4">Us</th>'
                f'<th className="py-2 px-4">Them</th>'
                f'</tr></thead>'
                f'<tbody>\n          {rows_html}\n        </tbody></table>'
            )

        return "\n      ".join(parts) if parts else '<div />'

    def _compile_timeline(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """Timeline layout with milestone nodes."""
        parts: list[str] = []

        if c.title:
            parts.append(
                f'<h2 className="text-3xl font-bold text-[var(--text-primary)] mb-8">'
                f'{_esc(c.title)}</h2>'
            )

        if c.timeline_items:
            items: list[str] = []
            for i, item in enumerate(c.timeline_items):
                status_color = {
                    "completed": "bg-green-500",
                    "in-progress": "bg-blue-500",
                    "planned": "bg-gray-500",
                }.get(item.status or "planned", "bg-gray-500")

                items.append(
                    f'<motion.div className="flex items-start gap-4" '
                    f'initial={{{{ opacity: 0, x: -20 }}}} '
                    f'animate={{{{ opacity: 1, x: 0 }}}} '
                    f'transition={{{{ delay: {0.15 * (i + 1)} }}}}>'
                    f'<div className="flex flex-col items-center">'
                    f'<div className="w-3 h-3 rounded-full {status_color}" />'
                    f'<div className="w-0.5 h-full bg-white/20 mt-1" /></div>'
                    f'<div className="pb-8">'
                    f'<span className="text-sm text-[var(--accent-color)] font-mono">'
                    f'{_esc(item.date)}</span>'
                    f'<h3 className="text-lg font-semibold text-[var(--text-primary)] mt-1">'
                    f'{_esc(item.title)}</h3>'
                    f'{"<p class=text-[var(--text-secondary)] text-sm mt-1>" + _esc(item.description or "") + "</p>" if item.description else ""}'
                    f'</div></motion.div>'
                )
            items_html = "\n        ".join(items)
            parts.append(
                f'<div className="flex flex-col">\n        {items_html}\n      </div>'
            )

        return "\n      ".join(parts) if parts else '<div />'

    def _compile_kpi_dashboard(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """KPI dashboard with metric cards."""
        parts: list[str] = []

        if c.title:
            parts.append(
                f'<h2 className="text-3xl font-bold text-[var(--text-primary)] mb-6">'
                f'{_esc(c.title)}</h2>'
            )

        if c.kpi_metrics:
            cols = min(len(c.kpi_metrics), 4)
            grid_class = f"grid grid-cols-{cols} gap-6"
            cards: list[str] = []
            for i, metric in enumerate(c.kpi_metrics):
                trend_icon = {"up": "↑", "down": "↓", "flat": "→"}.get(
                    metric.trend or "flat", "→"
                )
                trend_color = {"up": "text-green-400", "down": "text-red-400", "flat": "text-gray-400"}.get(
                    metric.trend or "flat", "text-gray-400"
                )
                cards.append(
                    f'<motion.div className="bg-[var(--bg-secondary)] rounded-xl p-6" '
                    f'initial={{{{ opacity: 0, y: 20 }}}} '
                    f'animate={{{{ opacity: 1, y: 0 }}}} '
                    f'transition={{{{ delay: {0.1 * (i + 1)} }}}}>'
                    f'<p className="text-sm text-[var(--text-muted)] uppercase tracking-wider">'
                    f'{_esc(metric.label)}</p>'
                    f'<p className="text-4xl font-bold text-[var(--text-primary)] mt-2">'
                    f'{_esc(metric.value)}</p>'
                    f'{"<p class=" + trend_color + " text-sm mt-1>" + trend_icon + " " + _esc(metric.change or "") + "</p>" if metric.change else ""}'
                    f'</motion.div>'
                )
            cards_html = "\n        ".join(cards)
            parts.append(f'<div className="{grid_class}">\n        {cards_html}\n      </div>')

        return "\n      ".join(parts) if parts else '<div />'

    def _compile_quote(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """Quote layout with decorative quotation marks."""
        parts: list[str] = []

        quote_text = c.quote_text or c.body_text or ""
        if quote_text:
            parts.append(
                f'<div className="relative">'
                f'<span className="absolute -top-8 -left-6 text-8xl text-[var(--accent-color)] '
                f'opacity-20 font-serif">&ldquo;</span>'
                f'<motion.blockquote className="text-3xl text-[var(--text-primary)] '
                f'leading-relaxed italic font-light max-w-3xl" '
                f'initial={{{{ opacity: 0 }}}} animate={{{{ opacity: 1 }}}} '
                f'transition={{{{ duration: 0.8 }}}}>'
                f'{_esc(quote_text)}</motion.blockquote></div>'
            )

        author = c.quote_author or c.presenter or ""
        if author:
            parts.append(
                f'<motion.p className="text-lg text-[var(--text-muted)] mt-6" '
                f'initial={{{{ opacity: 0 }}}} animate={{{{ opacity: 1 }}}} '
                f'transition={{{{ delay: 0.5 }}}}>'
                f'— {_esc(author)}</motion.p>'
            )

        return "\n      ".join(parts) if parts else '<div />'

    def _compile_team_grid(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """Team member grid with photos and info."""
        parts: list[str] = []

        if c.title:
            parts.append(
                f'<h2 className="text-3xl font-bold text-[var(--text-primary)] mb-8">'
                f'{_esc(c.title)}</h2>'
            )

        if c.team_members:
            cols = min(len(c.team_members), 4)
            grid_class = f"grid grid-cols-{cols} gap-6 flex-1"
            cards: list[str] = []
            for i, member in enumerate(c.team_members):
                avatar = (
                    f'<img src="{_esc(member.image_url)}" alt="{_esc(member.name)}" '
                    f'className="w-20 h-20 rounded-full object-cover mx-auto" />'
                    if member.image_url
                    else f'<div className="w-20 h-20 rounded-full bg-[var(--accent-color)]/20 '
                         f'flex items-center justify-center mx-auto">'
                         f'<span className="text-2xl text-[var(--accent-color)]">'
                         f'{_esc(member.name[0].upper() if member.name else "?")}</span></div>'
                )
                cards.append(
                    f'<motion.div className="text-center" '
                    f'initial={{{{ opacity: 0, y: 20 }}}} '
                    f'animate={{{{ opacity: 1, y: 0 }}}} '
                    f'transition={{{{ delay: {0.1 * (i + 1)} }}}}>'
                    f'{avatar}'
                    f'<h3 className="text-lg font-semibold text-[var(--text-primary)] mt-3">'
                    f'{_esc(member.name)}</h3>'
                    f'<p className="text-sm text-[var(--text-muted)]">{_esc(member.role)}</p>'
                    f'{"<p class=text-xs text-[var(--text-secondary)] mt-2>" + _esc(member.bio or "") + "</p>" if member.bio else ""}'
                    f'</motion.div>'
                )
            cards_html = "\n        ".join(cards)
            parts.append(f'<div className="{grid_class}">\n        {cards_html}\n      </div>')

        return "\n      ".join(parts) if parts else '<div />'

    def _compile_chart(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """Chart-focus layout with Recharts or 3D chart."""
        parts: list[str] = []

        if c.title:
            parts.append(
                f'<h2 className="text-3xl font-bold text-[var(--text-primary)] mb-4">'
                f'{_esc(c.title)}</h2>'
            )

        # If 3D scene is a bar-chart or scatter, use 3D rendering
        if scene.get("scene_type") in ("bar-chart", "scatter"):
            parts.append(
                f'<div className="flex-1 rounded-xl overflow-hidden">'
                f'{self._compile_3d_inline(scene)}</div>'
            )
        elif c.chart_data:
            # Generate Recharts placeholder (actual data binding happens at runtime)
            chart_json = json.dumps(c.chart_data, default=str)
            parts.append(
                f'<div className="flex-1">'
                f'<div className="w-full h-full bg-[var(--bg-secondary)] rounded-xl p-4" '
                f'data-chart-config={{{_jsx_string(chart_json)}}}>'
                f'<p className="text-[var(--text-muted)] text-center pt-20">'
                f'Chart: data bound at runtime</p>'
                f'</div></div>'
            )
        else:
            parts.append(
                '<div className="flex-1 bg-[var(--bg-secondary)] rounded-xl '
                'flex items-center justify-center">'
                '<p className="text-[var(--text-muted)]">Chart placeholder</p></div>'
            )

        return "\n      ".join(parts) if parts else '<div />'

    def _compile_blank(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """Blank canvas with positioned elements."""
        parts: list[str] = []

        if scene.get("scene_type"):
            parts.append(self._compile_3d_background(scene))

        for elem in slide.elements:
            parts.append(self._compile_element(elem))

        return "\n      ".join(parts) if parts else '<div className="empty-slide" />'

    def _compile_generic(
        self, c: SlideContentV2, slide: SlideDSL, scene: dict
    ) -> str:
        """Fallback generic compiler for unknown layouts."""
        return self._compile_center_focus(c, slide, scene)

    # ═══════════════════════════════════════════════════════════════
    # ELEMENT COMPILER
    # ═══════════════════════════════════════════════════════════════

    def _compile_element(self, elem: SlideElement) -> str:
        """Compile a positioned SlideElement into absolute-positioned JSX."""
        pos = elem.position
        size = elem.size
        style_parts: list[str] = [
            f"left: '{pos.x * 100:.1f}%'",
            f"top: '{pos.y * 100:.1f}%'",
            f"width: '{size.width * 100:.1f}%'",
            f"height: '{size.height * 100:.1f}%'",
        ]

        if elem.style.fontSize:
            style_parts.append(f"fontSize: '{elem.style.fontSize}px'")
        if elem.style.color:
            style_parts.append(f"color: '{_esc(elem.style.color)}'")
        if elem.style.fontWeight:
            style_parts.append(f"fontWeight: '{elem.style.fontWeight.value}'")
        if elem.style.textAlign:
            style_parts.append(f"textAlign: '{elem.style.textAlign.value}'")
        if elem.style.opacity is not None:
            style_parts.append(f"opacity: {elem.style.opacity}")

        style_str = ", ".join(style_parts)

        if elem.type == ElementType.TEXT:
            return (
                f'<div className="absolute" style={{{{ {style_str} }}}}>'
                f'{_esc(elem.content)}</div>'
            )
        elif elem.type == ElementType.IMAGE:
            return (
                f'<img className="absolute object-contain" '
                f'style={{{{ {style_str} }}}} '
                f'src="{_esc(elem.content)}" alt="{_esc(elem.alt_text or "")}" />'
            )
        elif elem.type == ElementType.CODE:
            return (
                f'<pre className="absolute bg-[var(--bg-secondary)] rounded-lg p-4 '
                f'overflow-auto font-mono text-sm" style={{{{ {style_str} }}}}>'
                f'<code>{_esc(elem.content)}</code></pre>'
            )
        else:
            return (
                f'<div className="absolute" style={{{{ {style_str} }}}}>'
                f'{_esc(elem.content)}</div>'
            )

    # ═══════════════════════════════════════════════════════════════
    # THREE.JS SCENE COMPILATION
    # ═══════════════════════════════════════════════════════════════

    def _compile_3d_background(self, scene_info: dict[str, Any]) -> str:
        """Compile a 3D scene as a full-slide background layer."""
        scene_type = scene_info.get("scene_type", "particles")
        template = get_scene_template(scene_type)
        if template is None:
            return '<div className="absolute inset-0 bg-[var(--bg-primary)]" />'

        config = scene_info.get("config", template.default_config)
        config_json = json.dumps(config, default=str)
        quality = scene_info.get("quality", self._quality.value)

        return (
            f'<div className="absolute inset-0 z-0">\n'
            f'        <Suspense fallback={{<div className="w-full h-full animate-pulse '
            f'bg-[var(--bg-secondary)]" />}}>\n'
            f'          <ThreeSceneContainer\n'
            f'            sceneType="{scene_type}"\n'
            f'            config={{{config_json}}}\n'
            f'            quality="{quality}"\n'
            f'          />\n'
            f'        </Suspense>\n'
            f'      </div>'
        )

    def _compile_3d_panel(self, scene_info: dict[str, Any]) -> str:
        """Compile a 3D scene as a panel (for split layouts)."""
        scene_type = scene_info.get("scene_type", "particles")
        template = get_scene_template(scene_type)
        if template is None:
            return '<div className="h-full bg-[var(--bg-secondary)]" />'

        config = scene_info.get("config", template.default_config)
        config_json = json.dumps(config, default=str)

        return (
            f'<div className="h-full">\n'
            f'        <Suspense fallback={{<div className="w-full h-full animate-pulse '
            f'bg-[var(--bg-secondary)]" />}}>\n'
            f'          <ThreeSceneContainer\n'
            f'            sceneType="{scene_type}"\n'
            f'            config={{{config_json}}}\n'
            f'          />\n'
            f'        </Suspense>\n'
            f'      </div>'
        )

    def _compile_3d_inline(self, scene_info: dict[str, Any]) -> str:
        """Compile a 3D scene as an inline component (no wrapper)."""
        scene_type = scene_info.get("scene_type", "particles")
        config = scene_info.get("config", {})
        config_json = json.dumps(config, default=str)

        return (
            f'<Suspense fallback={{<div className="w-full h-full animate-pulse '
            f'bg-[var(--bg-secondary)]" />}}>\n'
            f'          <ThreeSceneContainer\n'
            f'            sceneType="{scene_type}"\n'
            f'            config={{{config_json}}}\n'
            f'          />\n'
            f'        </Suspense>'
        )

    # ═══════════════════════════════════════════════════════════════
    # BACKGROUND & THEME
    # ═══════════════════════════════════════════════════════════════

    def _compile_background(self, style: SlideStyle) -> str:
        """Compile SlideStyle into inline CSS style object properties."""
        bg = style.background
        parts: list[str] = []

        if bg.type == BackgroundType.SOLID:
            color = bg.colors[0] if bg.colors else "#1a1a2e"
            parts.append(f"backgroundColor: '{color}'")

        elif bg.type in (BackgroundType.GRADIENT_LINEAR, BackgroundType.GRADIENT_RADIAL):
            if len(bg.colors) >= 2:
                angle = bg.angle or 135
                if bg.type == BackgroundType.GRADIENT_LINEAR:
                    stops = ", ".join(bg.colors)
                    parts.append(f"background: 'linear-gradient({angle}deg, {stops})'")
                else:
                    stops = ", ".join(bg.colors)
                    parts.append(f"background: 'radial-gradient(circle, {stops})'")

        elif bg.type == BackgroundType.IMAGE and bg.image_url:
            parts.append(f"backgroundImage: 'url({_esc(bg.image_url)})'")
            parts.append("backgroundSize: 'cover'")
            parts.append("backgroundPosition: 'center'")

        # Accent color
        if style.accentColor:
            parts.append(f"'--accent-color': '{_esc(style.accentColor)}'")

        return ", ".join(parts) if parts else "backgroundColor: 'var(--bg-primary)'"

    def _build_theme_css(self, theme: Any, extra_css: str = "") -> str:
        """Build CSS custom properties from the PresentationDSL theme."""
        overrides = theme.customOverrides if hasattr(theme, "customOverrides") else {}
        variant = theme.variant.value if hasattr(theme, "variant") else "dark"

        # Default dark theme
        defaults_dark = {
            "--bg-primary": "#0f0f1a",
            "--bg-secondary": "#1a1a2e",
            "--text-primary": "#ffffff",
            "--text-secondary": "#a0aec0",
            "--text-muted": "#6b7280",
            "--accent-color": "#38bdf8",
            "--accent-secondary": "#7b2ff7",
            "--border-color": "rgba(255,255,255,0.1)",
            "--font-heading": "'Inter', sans-serif",
            "--font-body": "'Inter', sans-serif",
            "--font-mono": "'JetBrains Mono', monospace",
        }

        defaults_light = {
            "--bg-primary": "#ffffff",
            "--bg-secondary": "#f8fafc",
            "--text-primary": "#0f172a",
            "--text-secondary": "#475569",
            "--text-muted": "#94a3b8",
            "--accent-color": "#2563eb",
            "--accent-secondary": "#7c3aed",
            "--border-color": "rgba(0,0,0,0.1)",
            "--font-heading": "'Inter', sans-serif",
            "--font-body": "'Inter', sans-serif",
            "--font-mono": "'JetBrains Mono', monospace",
        }

        defaults = defaults_light if variant == "light" else defaults_dark

        # Apply overrides
        merged = {**defaults, **overrides}

        vars_css = "\n  ".join(f"{k}: {v};" for k, v in merged.items())

        return f""":root {{
  {vars_css}
}}

.presentation-container {{
  font-family: var(--font-body);
  color: var(--text-primary);
  background-color: var(--bg-primary);
}}

.slide-wrapper {{
  font-family: var(--font-body);
}}

h1, h2, h3, h4, h5, h6 {{
  font-family: var(--font-heading);
}}

code, pre {{
  font-family: var(--font-mono);
}}

{extra_css}
"""

    # ═══════════════════════════════════════════════════════════════
    # VITE CONFIG
    # ═══════════════════════════════════════════════════════════════

    def _build_vite_config(self) -> str:
        """Generate Vite configuration for the React presentation app."""
        return '''// Auto-generated Vite config for Barise Presentation
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3100,
    hmr: true,
    open: false,
  },
  build: {
    target: "esnext",
    minify: "esbuild",
    rollupOptions: {
      output: {
        manualChunks: {
          "three-core": ["three"],
          "r3f": ["@react-three/fiber", "@react-three/drei"],
          "framer": ["framer-motion"],
          "recharts": ["recharts"],
        },
      },
    },
  },
  optimizeDeps: {
    include: ["react", "react-dom", "framer-motion"],
    exclude: ["three", "@react-three/fiber"],
  },
});
'''

    # ═══════════════════════════════════════════════════════════════
    # ANALYSIS & MANIFEST
    # ═══════════════════════════════════════════════════════════════

    def _analyze_3d_scenes(
        self, slides: list[SlideDSL]
    ) -> dict[int, dict[str, Any]]:
        """
        Analyze all slides for 3D scene requirements.
        Returns a dict of slide_index → scene_info.
        """
        analysis: dict[int, dict[str, Any]] = {}

        for slide in slides:
            scene_info: dict[str, Any] = {"scene_type": None, "config": {}, "quality": self._quality.value}

            if slide.threeScene is not None:
                st = slide.threeScene.type.value
                scene_info["scene_type"] = st
                scene_info["config"] = {
                    **slide.threeScene.data,
                    **slide.threeScene.config,
                }

                # Run performance check
                budget_report = self._guardrails.analyze_scene(st, self._quality)
                scene_info["quality"] = budget_report.quality_level.value
                scene_info["fallback_2d"] = budget_report.fallback_2d
                scene_info["budget_report"] = {
                    "passed": budget_report.passed,
                    "violations": budget_report.violation_count,
                    "polygons": budget_report.polygons,
                    "particles": budget_report.particles,
                }

            analysis[slide.index] = scene_info

        return analysis

    def _build_import_manifest(
        self,
        slides: list[SlideDSL],
        scene_analysis: dict[int, dict[str, Any]],
    ) -> dict[str, Any]:
        """Build an import manifest listing all required packages."""
        packages = {
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "framer-motion": "^11.0.0",
        }

        has_3d = any(
            s.get("scene_type") is not None for s in scene_analysis.values()
        )
        has_chart = any(
            s.content.chart_data is not None for s in slides
        )

        if has_3d:
            packages.update({
                "three": "^0.170.0",
                "@react-three/fiber": "^8.17.0",
                "@react-three/drei": "^9.114.0",
            })

        if has_chart:
            packages["recharts"] = "^2.12.0"

        return {
            "dependencies": packages,
            "devDependencies": {
                "@vitejs/plugin-react": "^4.3.0",
                "vite": "^6.0.0",
                "tailwindcss": "^3.4.0",
                "typescript": "^5.6.0",
            },
        }

    def _build_lazy_load_plan(
        self,
        slides: list[SlideDSL],
        scene_analysis: dict[int, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build lazy-loading directives for 3D slides."""
        scenes_for_plan: list[dict[str, Any]] = []
        for idx, info in scene_analysis.items():
            if info.get("scene_type"):
                scenes_for_plan.append({
                    "slide_index": idx,
                    "scene_type": info["scene_type"],
                })

        if not scenes_for_plan:
            return []

        directives = self._guardrails.generate_lazy_load_plan(
            scenes_for_plan,
            current_slide=0,
            total_slides=len(slides),
        )

        return [
            {
                "slide_index": d.slide_index,
                "scene_type": d.scene_type,
                "preload": d.preload,
                "placeholder": d.placeholder,
                "estimated_load_ms": d.estimated_load_ms,
                "priority": d.priority,
            }
            for d in directives
        ]

    # ═══════════════════════════════════════════════════════════════
    # ANIMATION RESOLUTION
    # ═══════════════════════════════════════════════════════════════

    def _resolve_animation(self, slide: SlideDSL) -> str:
        """Determine the animation preset for a slide."""
        # 1. Check slide style animation override
        if slide.style.animation:
            if slide.style.animation in MOTION_VARIANTS:
                return slide.style.animation

        # 2. Check fragments for dominant animation
        if slide.fragments:
            first_anim = slide.fragments[0].animation
            preset = ANIMATION_PRESET_MAP.get(first_anim, "fadeIn")
            return preset

        # 3. Fall back to slide-type default
        return SLIDE_TYPE_ANIMATION.get(slide.type, "fadeIn")
