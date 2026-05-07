"""
reveal.js Compiler - Phase 4.

Compiles PresentationDSL / SlideDSL into a complete reveal.js HTML
presentation with Auto-Animate, fragments, speaker notes, and
per-slide backgrounds.

Architecture:
    PresentationDSL --> RevealCompiler --> RenderOutput (full HTML)
    SlideDSL        --> RevealCompiler --> str (single <section>)

reveal.js features supported:
    - Slide transitions (slide, fade, convex, concave, zoom)
    - Progressive fragments (fade-in, slide-up, grow, shrink, strike, highlight)
    - Speaker notes (<aside class="notes">)
    - Auto-Animate (data-auto-animate + matching data-id)
    - Background images / gradients / solid colors
    - Two-column / grid layouts via CSS Grid
    - KPI dashboards, timelines, team grids, comparisons
    - Code blocks with syntax highlighting
    - Math via KaTeX ($...$)
    - Nested vertical slides
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
    RevealConfig,
    SlideDSL,
    SlideElement,
    SlideStyle,
    SlideType,
    ThreeSceneType,
    TransitionType,
)
from app.services.slides_new.renderers.base_renderer import (
    BaseRenderer,
    RenderOutput,
    RendererType,
)

# reveal.js CDN version
REVEAL_JS_VERSION = "5.1.0"
REVEAL_CDN = f"https://cdn.jsdelivr.net/npm/reveal.js@{REVEAL_JS_VERSION}"

# Fragment animation CSS class mapping
FRAGMENT_CLASS_MAP: dict[AnimationType, str] = {
    AnimationType.FADE_IN: "fade-in",
    AnimationType.SLIDE_UP: "fade-up",
    AnimationType.GROW: "grow",
    AnimationType.SHRINK: "shrink",
    AnimationType.STRIKE: "strike",
    AnimationType.HIGHLIGHT: "highlight-current-blue",
}

# Transition type mapping
TRANSITION_MAP: dict[TransitionType, str] = {
    TransitionType.NONE: "none",
    TransitionType.FADE: "fade",
    TransitionType.SLIDE: "slide",
    TransitionType.CONVEX: "convex",
    TransitionType.CONCAVE: "concave",
    TransitionType.ZOOM: "zoom",
}


def _esc(text: str) -> str:
    """HTML-escape user content to prevent XSS."""
    return html_mod.escape(str(text), quote=True)


def _stable_id(prefix: str, index: int) -> str:
    """Generate a stable data-id for Auto-Animate matching."""
    return f"{prefix}-{index}"


class RevealCompiler(BaseRenderer):
    """
    Compiles Slide DSL v2 into reveal.js HTML presentations.

    Usage:
        compiler = RevealCompiler()
        output = compiler.render_presentation(presentation_dsl, theme_css)
        # output.html is a complete, self-contained HTML document
    """

    def get_renderer_type(self) -> RendererType:
        return RendererType.REVEAL_JS

    # ------------------------------------------------------------------ #
    #  PUBLIC API                                                         #
    # ------------------------------------------------------------------ #

    def render_presentation(
        self,
        presentation_dsl: PresentationDSL,
        theme_css: str = "",
    ) -> RenderOutput:
        """Compile a full PresentationDSL into a self-contained reveal.js HTML document."""
        try:
            sections: list[str] = []
            for slide in presentation_dsl.slides:
                sections.append(self.render_slide(slide, theme_css=""))

            slides_html = "\n".join(sections)
            reveal_config = self._build_global_config(presentation_dsl)
            title = _esc(presentation_dsl.presentation.title)
            fonts = self._collect_fonts(presentation_dsl)
            font_imports = self._build_font_imports(fonts)
            dims = presentation_dsl.presentation.dimensions

            full_html = self._build_full_html(
                title=title,
                slides_html=slides_html,
                theme_css=theme_css,
                reveal_config=reveal_config,
                font_imports=font_imports,
                width=dims.width,
                height=dims.height,
            )

            return RenderOutput(
                renderer=RendererType.REVEAL_JS,
                html=full_html,
                css=theme_css,
                metadata={
                    "reveal_version": REVEAL_JS_VERSION,
                    "slide_count": len(presentation_dsl.slides),
                    "title": presentation_dsl.presentation.title,
                    "renderers": presentation_dsl.presentation.renderers,
                },
                success=True,
                slide_count=len(presentation_dsl.slides),
            )
        except Exception as exc:
            return RenderOutput(
                renderer=RendererType.REVEAL_JS,
                success=False,
                error=str(exc),
            )

    def render_slide(self, slide_dsl: SlideDSL, theme_css: str = "") -> str:
        """Compile a single SlideDSL into a reveal.js <section> element."""
        attrs = self._section_attributes(slide_dsl)
        bg_attrs = self._background_attributes(slide_dsl.style)
        inner_html = self._compile_slide_body(slide_dsl)
        notes_html = self._compile_speaker_notes(slide_dsl.speakerNotes)

        all_attrs = {**attrs, **bg_attrs}
        attr_str = " ".join(
            f'{k}="{_esc(str(v))}"' for k, v in all_attrs.items() if v is not None
        )

        return f"<section {attr_str}>\n{inner_html}\n{notes_html}\n</section>"

    # ------------------------------------------------------------------ #
    #  SECTION ATTRIBUTES (transition, auto-animate)                     #
    # ------------------------------------------------------------------ #

    def _section_attributes(self, slide: SlideDSL) -> dict[str, str | None]:
        """Build data-* attributes for the <section> tag."""
        cfg: RevealConfig = slide.revealConfig
        attrs: dict[str, str | None] = {}

        # Slide ID for deep linking
        attrs["id"] = slide.id

        # Transition
        if cfg.transition != TransitionType.SLIDE:
            attrs["data-transition"] = TRANSITION_MAP.get(cfg.transition, "slide")

        # Background transition
        if cfg.backgroundTransition != TransitionType.FADE:
            attrs["data-background-transition"] = TRANSITION_MAP.get(
                cfg.backgroundTransition, "fade"
            )

        # Auto-Animate
        if cfg.autoAnimate:
            attrs["data-auto-animate"] = ""
            attrs["data-auto-animate-easing"] = "ease-out"
            attrs["data-auto-animate-duration"] = "0.8"

        # Auto-slide
        if cfg.autoSlide and cfg.autoSlide > 0:
            attrs["data-autoslide"] = str(cfg.autoSlide)

        # Custom classes based on layout
        attrs["class"] = f"slide-{slide.layout.value}"

        return attrs

    # ------------------------------------------------------------------ #
    #  BACKGROUND                                                        #
    # ------------------------------------------------------------------ #

    def _background_attributes(self, style: SlideStyle) -> dict[str, str]:
        """Convert SlideStyle.background into reveal.js data-background-* attrs."""
        bg = style.background
        attrs: dict[str, str] = {}

        if bg.type == BackgroundType.SOLID:
            attrs["data-background-color"] = bg.colors[0]

        elif bg.type == BackgroundType.GRADIENT_LINEAR:
            angle = bg.angle if bg.angle is not None else 135
            stops = ", ".join(bg.colors)
            attrs["data-background-gradient"] = f"linear-gradient({angle}deg, {stops})"

        elif bg.type == BackgroundType.GRADIENT_RADIAL:
            stops = ", ".join(bg.colors)
            attrs["data-background-gradient"] = f"radial-gradient(circle, {stops})"

        elif bg.type == BackgroundType.GRADIENT_CONIC:
            stops = ", ".join(bg.colors)
            attrs["data-background-gradient"] = (
                f"conic-gradient(from {bg.angle or 0}deg, {stops})"
            )

        elif bg.type == BackgroundType.IMAGE and bg.image_url:
            attrs["data-background-image"] = bg.image_url
            attrs["data-background-size"] = "cover"
            attrs["data-background-position"] = "center"

        # Add custom background class for complex backgrounds (mesh, pattern, glass, noise)
        custom_class = self._get_background_custom_class(bg)
        if custom_class:
            attrs["class"] = (attrs.get("class", "") + " " + custom_class).strip()

        return attrs

    def _get_background_custom_class(self, bg) -> str:
        """Get custom CSS class for complex background types."""
        classes = []

        # Mesh gradient
        if bg.mesh_points and len(bg.mesh_points) >= 2:
            classes.append("bg-mesh")

        # Pattern overlay
        if bg.pattern:
            classes.append(f"pattern-{bg.pattern.value}")

        # Noise texture
        if bg.noise_intensity and bg.noise_intensity > 0:
            classes.append("bg-noise")

        # Glass effect
        if bg.blur and bg.blur > 0:
            classes.append("bg-glass")

        return " ".join(classes) if classes else ""

    # ------------------------------------------------------------------ #
    #  SLIDE BODY (layout-driven HTML)                                   #
    # ------------------------------------------------------------------ #

    def _compile_slide_body(self, slide: SlideDSL) -> str:
        """Compile the inner HTML of a slide based on its layout and content."""
        layout = slide.layout
        content = slide.content

        # Map layouts to compilation methods
        layout_compilers = {
            LayoutType.CENTER_FOCUS: self._layout_center_focus,
            LayoutType.SPLIT_SCREEN: self._layout_split_screen,
            LayoutType.FULL_BLEED: self._layout_full_bleed,
            LayoutType.BULLETS: self._layout_bullets,
            LayoutType.TEXT_LEFT_VISUAL_RIGHT: self._layout_text_visual,
            LayoutType.TEXT_RIGHT_VISUAL_LEFT: self._layout_visual_text,
            LayoutType.GRID_2X2: self._layout_grid_2x2,
            LayoutType.GRID_3X1: self._layout_grid_3x1,
            LayoutType.TOP_BOTTOM: self._layout_top_bottom,
            LayoutType.COMPARISON: self._layout_comparison,
            LayoutType.TIMELINE: self._layout_timeline,
            LayoutType.KPI_DASHBOARD: self._layout_kpi_dashboard,
            LayoutType.QUOTE: self._layout_quote,
            LayoutType.TEAM_GRID: self._layout_team_grid,
            LayoutType.CHART: self._layout_chart,
            LayoutType.OVERLAY: self._layout_overlay,
            LayoutType.BLANK: self._layout_blank,
        }

        compiler_fn = layout_compilers.get(layout, self._layout_center_focus)
        body = compiler_fn(slide)

        # Append positioned elements (absolute-positioned overlays)
        elements_html = self._compile_elements(slide)
        if elements_html:
            body += f'\n<div class="elements-layer">\n{elements_html}\n</div>'

        # Append fragments
        fragments_html = self._compile_fragments(slide)
        if fragments_html:
            body += fragments_html

        return body

    # ------------------------------------------------------------------ #
    #  LAYOUT COMPILERS                                                  #
    # ------------------------------------------------------------------ #

    def _layout_center_focus(self, slide: SlideDSL) -> str:
        c = slide.content
        parts: list[str] = ['<div class="center-focus">']
        if c.tagline:
            parts.append(
                f'  <p class="tagline" data-id="{_stable_id("tagline", slide.index)}">{_esc(c.tagline)}</p>'
            )
        if c.title:
            parts.append(
                f'  <h1 data-id="{_stable_id("title", slide.index)}">{_esc(c.title)}</h1>'
            )
        if c.subtitle:
            parts.append(
                f'  <h3 data-id="{_stable_id("subtitle", slide.index)}">{_esc(c.subtitle)}</h3>'
            )
        if c.presenter:
            parts.append(f'  <p class="presenter">{_esc(c.presenter)}</p>')
        if c.body_text:
            parts.append(f'  <p class="body-text">{_esc(c.body_text)}</p>')
        parts.append("</div>")
        return "\n".join(parts)

    def _layout_split_screen(self, slide: SlideDSL) -> str:
        c = slide.content
        left = c.left_content or c.body_text or ""
        right = c.right_content or ""
        if c.image_url:
            right = f'<img src="{_esc(c.image_url)}" alt="{_esc(c.title)}" class="split-image" />'
        return (
            '<div class="split-screen">\n'
            f'  <div class="split-left">\n'
            f'    <h2 data-id="{_stable_id("title", slide.index)}">{_esc(c.title)}</h2>\n'
            f'    <div class="split-body">{_esc(left)}</div>\n'
            f"  </div>\n"
            f'  <div class="split-right">\n'
            f"    {right}\n"
            f"  </div>\n"
            f"</div>"
        )

    def _layout_full_bleed(self, slide: SlideDSL) -> str:
        c = slide.content
        parts: list[str] = ['<div class="full-bleed">']
        if c.title:
            parts.append(
                f'  <h1 data-id="{_stable_id("title", slide.index)}">{_esc(c.title)}</h1>'
            )
        if c.subtitle:
            parts.append(f"  <h3>{_esc(c.subtitle)}</h3>")
        if c.body_text:
            parts.append(f"  <p>{_esc(c.body_text)}</p>")
        parts.append("</div>")
        return "\n".join(parts)

    def _layout_bullets(self, slide: SlideDSL) -> str:
        c = slide.content
        parts: list[str] = ['<div class="bullets-layout">']
        if c.title:
            parts.append(
                f'  <h2 data-id="{_stable_id("title", slide.index)}">{_esc(c.title)}</h2>'
            )
        if c.subtitle:
            parts.append(f'  <p class="subtitle">{_esc(c.subtitle)}</p>')
        if c.bullets:
            parts.append("  <ul>")
            for i, bullet in enumerate(c.bullets):
                frag_class = (
                    "fragment fade-in" if slide.revealConfig.autoAnimate else ""
                )
                cls = f' class="{frag_class}"' if frag_class else ""
                parts.append(
                    f'    <li{cls} data-id="{_stable_id("bullet", i)}">{_esc(bullet)}</li>'
                )
            parts.append("  </ul>")
        if c.body_text:
            parts.append(f'  <p class="body-text">{_esc(c.body_text)}</p>')
        parts.append("</div>")
        return "\n".join(parts)

    def _layout_text_visual(self, slide: SlideDSL) -> str:
        """Text left, visual right."""
        c = slide.content
        visual = self._make_visual_block(slide)
        text = self._make_text_block(slide)
        return (
            '<div class="text-visual">\n'
            f'  <div class="tv-text">\n{text}\n  </div>\n'
            f'  <div class="tv-visual">\n{visual}\n  </div>\n'
            "</div>"
        )

    def _layout_visual_text(self, slide: SlideDSL) -> str:
        """Visual left, text right."""
        c = slide.content
        visual = self._make_visual_block(slide)
        text = self._make_text_block(slide)
        return (
            '<div class="visual-text">\n'
            f'  <div class="vt-visual">\n{visual}\n  </div>\n'
            f'  <div class="vt-text">\n{text}\n  </div>\n'
            "</div>"
        )

    def _layout_grid_2x2(self, slide: SlideDSL) -> str:
        c = slide.content
        parts: list[str] = ['<div class="grid-2x2">']
        if c.title:
            parts.append(
                f'  <h2 class="grid-title" data-id="{_stable_id("title", slide.index)}">{_esc(c.title)}</h2>'
            )
        parts.append('  <div class="grid-container">')
        items = c.bullets or []
        for i, item in enumerate(items[:4]):
            parts.append(
                f'    <div class="grid-cell" data-id="{_stable_id("cell", i)}">{_esc(item)}</div>'
            )
        parts.append("  </div>")
        parts.append("</div>")
        return "\n".join(parts)

    def _layout_grid_3x1(self, slide: SlideDSL) -> str:
        c = slide.content
        parts: list[str] = ['<div class="grid-3x1">']
        if c.title:
            parts.append(
                f'  <h2 data-id="{_stable_id("title", slide.index)}">{_esc(c.title)}</h2>'
            )
        parts.append('  <div class="grid-container">')
        items = c.bullets or []
        for i, item in enumerate(items[:3]):
            parts.append(
                f'    <div class="grid-cell" data-id="{_stable_id("cell", i)}">{_esc(item)}</div>'
            )
        parts.append("  </div>")
        parts.append("</div>")
        return "\n".join(parts)

    def _layout_top_bottom(self, slide: SlideDSL) -> str:
        c = slide.content
        return (
            '<div class="top-bottom">\n'
            f'  <div class="top-section">\n'
            f'    <h2 data-id="{_stable_id("title", slide.index)}">{_esc(c.title)}</h2>\n'
            f"    {f'<p>{_esc(c.subtitle)}</p>' if c.subtitle else ''}\n"
            f"  </div>\n"
            f'  <div class="bottom-section">\n'
            f"    {f'<p>{_esc(c.body_text)}</p>' if c.body_text else ''}\n"
            f"  </div>\n"
            "</div>"
        )

    def _layout_comparison(self, slide: SlideDSL) -> str:
        c = slide.content
        parts: list[str] = ['<div class="comparison-layout">']
        if c.title:
            parts.append(
                f'  <h2 data-id="{_stable_id("title", slide.index)}">{_esc(c.title)}</h2>'
            )
        if c.comparison_items:
            parts.append('  <table class="comparison-table">')
            parts.append(
                "    <thead><tr><th>Feature</th><th>Us</th><th>Them</th></tr></thead>"
            )
            parts.append("    <tbody>")
            for i, item in enumerate(c.comparison_items):
                adv_cls = ' class="advantage"' if item.advantage else ""
                parts.append(
                    f'    <tr{adv_cls} data-id="{_stable_id("comp", i)}">'
                    f"<td>{_esc(item.label)}</td>"
                    f"<td>{_esc(item.us or '')}</td>"
                    f"<td>{_esc(item.them or '')}</td>"
                    f"</tr>"
                )
            parts.append("    </tbody>")
            parts.append("  </table>")
        parts.append("</div>")
        return "\n".join(parts)

    def _layout_timeline(self, slide: SlideDSL) -> str:
        c = slide.content
        parts: list[str] = ['<div class="timeline-layout">']
        if c.title:
            parts.append(
                f'  <h2 data-id="{_stable_id("title", slide.index)}">{_esc(c.title)}</h2>'
            )
        if c.timeline_items:
            parts.append('  <div class="timeline-track">')
            for i, item in enumerate(c.timeline_items):
                status_cls = f" timeline-{item.status}" if item.status else ""
                parts.append(
                    f'    <div class="timeline-item{status_cls}" data-id="{_stable_id("tl", i)}">\n'
                    f'      <div class="timeline-marker"></div>\n'
                    f'      <div class="timeline-content">\n'
                    f'        <span class="timeline-date">{_esc(item.date)}</span>\n'
                    f"        <h4>{_esc(item.title)}</h4>\n"
                    f"        {f'<p>{_esc(item.description)}</p>' if item.description else ''}\n"
                    f"      </div>\n"
                    f"    </div>"
                )
            parts.append("  </div>")
        parts.append("</div>")
        return "\n".join(parts)

    def _layout_kpi_dashboard(self, slide: SlideDSL) -> str:
        c = slide.content
        parts: list[str] = ['<div class="kpi-dashboard">']
        if c.title:
            parts.append(
                f'  <h2 data-id="{_stable_id("title", slide.index)}">{_esc(c.title)}</h2>'
            )
        if c.kpi_metrics:
            cols = min(len(c.kpi_metrics), 4)
            parts.append(f'  <div class="kpi-grid kpi-cols-{cols}">')
            for i, kpi in enumerate(c.kpi_metrics):
                trend_cls = f" kpi-{kpi.trend}" if kpi.trend else ""
                change_html = (
                    f'<div class="kpi-change">{_esc(kpi.change)}</div>'
                    if kpi.change
                    else ""
                )
                parts.append(
                    f'    <div class="kpi-card{trend_cls}" data-id="{_stable_id("kpi", i)}">\n'
                    f'      <div class="kpi-value">{_esc(kpi.value)}</div>\n'
                    f'      <div class="kpi-label">{_esc(kpi.label)}</div>\n'
                    f"      {change_html}\n"
                    f"    </div>"
                )
            parts.append("  </div>")
        parts.append("</div>")
        return "\n".join(parts)

    def _layout_quote(self, slide: SlideDSL) -> str:
        c = slide.content
        parts: list[str] = ['<div class="quote-layout">']
        text = c.quote_text or c.body_text or ""
        author = c.quote_author or ""
        if text:
            parts.append(f'  <blockquote data-id="{_stable_id("quote", slide.index)}">')
            parts.append(f"    <p>&ldquo;{_esc(text)}&rdquo;</p>")
            if author:
                parts.append(f"    <cite>-- {_esc(author)}</cite>")
            parts.append("  </blockquote>")
        parts.append("</div>")
        return "\n".join(parts)

    def _layout_team_grid(self, slide: SlideDSL) -> str:
        c = slide.content
        parts: list[str] = ['<div class="team-grid-layout">']
        if c.title:
            parts.append(
                f'  <h2 data-id="{_stable_id("title", slide.index)}">{_esc(c.title)}</h2>'
            )
        if c.team_members:
            cols = min(len(c.team_members), 4)
            parts.append(f'  <div class="team-grid team-cols-{cols}">')
            for i, member in enumerate(c.team_members):
                img = ""
                if member.image_url:
                    img = f'<img src="{_esc(member.image_url)}" alt="{_esc(member.name)}" class="team-photo" />'
                else:
                    initials = "".join(w[0].upper() for w in member.name.split()[:2])
                    img = f'<div class="team-avatar">{_esc(initials)}</div>'
                parts.append(
                    f'    <div class="team-member" data-id="{_stable_id("member", i)}">\n'
                    f"      {img}\n"
                    f"      <h4>{_esc(member.name)}</h4>\n"
                    f'      <p class="team-role">{_esc(member.role)}</p>\n'
                    f"      {f"<p class='team-bio'>{_esc(member.bio)}</p>" if member.bio else ''}\n"
                    f"    </div>"
                )
            parts.append("  </div>")
        parts.append("</div>")
        return "\n".join(parts)

    def _layout_chart(self, slide: SlideDSL) -> str:
        c = slide.content
        parts: list[str] = ['<div class="chart-layout">']
        if c.title:
            parts.append(
                f'  <h2 data-id="{_stable_id("title", slide.index)}">{_esc(c.title)}</h2>'
            )
        if c.chart_data:
            chart_json = json.dumps(c.chart_data)
            chart_id = f"chart-{slide.id}"
            parts.append(f'  <div class="chart-container">')
            parts.append(
                f"    <canvas id=\"{_esc(chart_id)}\" data-chart='{chart_json}'></canvas>"
            )
            parts.append("  </div>")
        if c.body_text:
            parts.append(f'  <p class="chart-caption">{_esc(c.body_text)}</p>')
        parts.append("</div>")
        return "\n".join(parts)

    def _layout_overlay(self, slide: SlideDSL) -> str:
        c = slide.content
        parts: list[str] = ['<div class="overlay-layout">']
        if c.title:
            parts.append(
                f'  <h1 data-id="{_stable_id("title", slide.index)}">{_esc(c.title)}</h1>'
            )
        if c.subtitle:
            parts.append(f"  <h3>{_esc(c.subtitle)}</h3>")
        if c.body_text:
            parts.append(f"  <p>{_esc(c.body_text)}</p>")
        parts.append("</div>")
        return "\n".join(parts)

    def _layout_blank(self, slide: SlideDSL) -> str:
        return '<div class="blank-layout"></div>'

    # ------------------------------------------------------------------ #
    #  HELPER: text block / visual block                                  #
    # ------------------------------------------------------------------ #

    def _make_text_block(self, slide: SlideDSL) -> str:
        c = slide.content
        parts: list[str] = []
        if c.title:
            parts.append(
                f'    <h2 data-id="{_stable_id("title", slide.index)}">{_esc(c.title)}</h2>'
            )
        if c.subtitle:
            parts.append(f'    <p class="subtitle">{_esc(c.subtitle)}</p>')
        if c.bullets:
            parts.append("    <ul>")
            for i, b in enumerate(c.bullets):
                parts.append(
                    f'      <li data-id="{_stable_id("bullet", i)}">{_esc(b)}</li>'
                )
            parts.append("    </ul>")
        if c.body_text:
            parts.append(f'    <p class="body-text">{_esc(c.body_text)}</p>')
        return "\n".join(parts)

    def _make_visual_block(self, slide: SlideDSL) -> str:
        c = slide.content
        if c.image_url:
            return f'    <img src="{_esc(c.image_url)}" alt="{_esc(c.title)}" class="visual-image" />'
        if c.chart_data:
            chart_json = json.dumps(c.chart_data)
            return f"    <canvas class=\"visual-chart\" data-chart='{chart_json}'></canvas>"
        return '    <div class="visual-placeholder"></div>'

    # ------------------------------------------------------------------ #
    #  POSITIONED ELEMENTS (absolute overlay layer)                      #
    # ------------------------------------------------------------------ #

    def _compile_elements(self, slide: SlideDSL) -> str:
        """Compile SlideElement list into absolutely-positioned HTML."""
        if not slide.elements:
            return ""
        parts: list[str] = []
        for elem in slide.elements:
            style_parts: list[str] = [
                f"position: absolute",
                f"left: {elem.position.x * 100:.1f}%",
                f"top: {elem.position.y * 100:.1f}%",
                f"width: {elem.size.width * 100:.1f}%",
                f"height: {elem.size.height * 100:.1f}%",
            ]
            if elem.style.opacity is not None:
                style_parts.append(f"opacity: {elem.style.opacity}")
            if elem.style.zIndex is not None:
                style_parts.append(f"z-index: {elem.style.zIndex}")
            if elem.style.fontSize:
                style_parts.append(f"font-size: {elem.style.fontSize}px")
            if elem.style.fontWeight:
                style_parts.append(f"font-weight: {elem.style.fontWeight.value}")
            if elem.style.color:
                style_parts.append(f"color: {_esc(elem.style.color)}")
            if elem.style.fontFamily:
                style_parts.append(f"font-family: {_esc(elem.style.fontFamily)}")
            if elem.style.textAlign:
                style_parts.append(f"text-align: {elem.style.textAlign.value}")
            if elem.style.backgroundColor:
                style_parts.append(
                    f"background-color: {_esc(elem.style.backgroundColor)}"
                )
            if elem.style.borderRadius is not None:
                style_parts.append(f"border-radius: {elem.style.borderRadius}px")
            if elem.style.padding:
                style_parts.append(f"padding: {_esc(elem.style.padding)}")
            if elem.style.shadow:
                style_parts.append(f"box-shadow: {_esc(elem.style.shadow)}")
            if elem.style.lineHeight is not None:
                style_parts.append(f"line-height: {elem.style.lineHeight}")
            if elem.style.letterSpacing is not None:
                style_parts.append(f"letter-spacing: {elem.style.letterSpacing}px")
            if elem.style.textTransform:
                style_parts.append(f"text-transform: {elem.style.textTransform}")

            inline_style = "; ".join(style_parts)
            elem_html = self._render_element_content(elem)
            data_id = (
                f' data-id="{_esc(elem.id)}"' if slide.revealConfig.autoAnimate else ""
            )

            parts.append(
                f'<div class="element element-{elem.type.value}"{data_id} '
                f'style="{inline_style}">\n  {elem_html}\n</div>'
            )
        return "\n".join(parts)

    def _render_element_content(self, elem: SlideElement) -> str:
        """Render content for a single element based on its type."""
        if elem.type == ElementType.TEXT:
            return f"<span>{_esc(elem.content)}</span>"
        elif elem.type == ElementType.IMAGE:
            alt = _esc(elem.alt_text or "")
            return f'<img src="{_esc(elem.content)}" alt="{alt}" loading="lazy" />'
        elif elem.type == ElementType.CODE:
            lang = (elem.data or {}).get("language", "")
            return f'<pre><code data-trim data-line-numbers class="language-{_esc(lang)}">{_esc(elem.content)}</code></pre>'
        elif elem.type == ElementType.CHART:
            return f"<canvas data-chart='{elem.content}'></canvas>"
        elif elem.type == ElementType.SHAPE:
            return f'<div class="shape">{_esc(elem.content)}</div>'
        elif elem.type == ElementType.ICON:
            icon_name = _esc(elem.content)
            return f'<span class="icon icon-{icon_name}"></span>'
        elif elem.type == ElementType.VIDEO:
            return (
                f'<video src="{_esc(elem.content)}" controls preload="metadata">'
                f"Your browser does not support video.</video>"
            )
        elif elem.type == ElementType.DIAGRAM:
            return f'<div class="diagram">{elem.content}</div>'
        elif elem.type == ElementType.QR:
            return f'<div class="qr-code" data-qr="{_esc(elem.content)}"></div>'
        return f"<div>{_esc(elem.content)}</div>"

    # ------------------------------------------------------------------ #
    #  FRAGMENT ANIMATIONS                                               #
    # ------------------------------------------------------------------ #

    def _compile_fragments(self, slide: SlideDSL) -> str:
        """
        Generate a <script> block that applies fragment classes to elements.
        reveal.js fragments are inline classes; we inject them via data-id.
        """
        if not slide.fragments:
            return ""
        # We compile fragments as CSS classes in the element compilation.
        # For elements already rendered with data-id, we emit a small
        # inline script that adds fragment classes post-load.
        script_lines: list[str] = []
        for frag in slide.fragments:
            cls = FRAGMENT_CLASS_MAP.get(frag.animation, "fade-in")
            delay_attr = f'data-fragment-delay="{frag.delay}"' if frag.delay else ""
            script_lines.append(
                f'  applyFragment("{_esc(frag.elementId)}", "{cls}", {frag.order});'
            )
        if not script_lines:
            return ""
        return (
            "\n<script>\n"
            "function applyFragment(eid, cls, order) {\n"
            "  var el = document.querySelector('[data-id=\"' + eid + '\"]');\n"
            '  if (el) { el.classList.add("fragment", cls); el.setAttribute("data-fragment-index", order); }\n'
            "}\n" + "\n".join(script_lines) + "\n</script>"
        )

    # ------------------------------------------------------------------ #
    #  SPEAKER NOTES                                                     #
    # ------------------------------------------------------------------ #

    def _compile_speaker_notes(self, notes: Optional[str]) -> str:
        if not notes or not notes.strip():
            return ""
        return f'<aside class="notes">\n  {_esc(notes)}\n</aside>'

    # ------------------------------------------------------------------ #
    #  GLOBAL CONFIG                                                     #
    # ------------------------------------------------------------------ #

    def _build_global_config(self, pres: PresentationDSL) -> str:
        """Build the Reveal.initialize({...}) config object as JSON."""
        config: dict[str, Any] = {
            "hash": True,
            "respondToHashChanges": True,
            "history": True,
            "center": True,
            "transition": "slide",
            "backgroundTransition": "fade",
            "autoAnimateEasing": "ease-out",
            "autoAnimateDuration": 0.8,
            "autoAnimateUnmatched": True,
            "pdfSeparateFragments": False,
            "width": pres.presentation.dimensions.width,
            "height": pres.presentation.dimensions.height,
            "margin": 0.04,
            "minScale": 0.2,
            "maxScale": 2.0,
            "plugins": [
                "RevealMarkdown",
                "RevealHighlight",
                "RevealMath",
                "RevealNotes",
                "RevealSearch",
                "RevealZoom",
            ],
        }
        return json.dumps(config, indent=2)

    # ------------------------------------------------------------------ #
    #  FONTS                                                             #
    # ------------------------------------------------------------------ #

    def _collect_fonts(self, pres: PresentationDSL) -> set[str]:
        """Collect all font families referenced in the presentation."""
        fonts: set[str] = set()
        for slide in pres.slides:
            for elem in slide.elements:
                if elem.style.fontFamily:
                    fonts.add(elem.style.fontFamily)
        return fonts

    def _build_font_imports(self, fonts: set[str]) -> str:
        """Build Google Fonts import links."""
        if not fonts:
            return ""
        links: list[str] = []
        for font in sorted(fonts):
            family = font.replace(" ", "+")
            links.append(
                f'<link href="https://fonts.googleapis.com/css2?family={family}:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">'
            )
        return "\n".join(links)

    # ------------------------------------------------------------------ #
    #  FULL HTML DOCUMENT                                                #
    # ------------------------------------------------------------------ #

    def _build_full_html(
        self,
        title: str,
        slides_html: str,
        theme_css: str,
        reveal_config: str,
        font_imports: str,
        width: int = 1920,
        height: int = 1080,
    ) -> str:
        """Assemble the complete HTML document."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>

  <!-- reveal.js core CSS -->
  <link rel="stylesheet" href="{REVEAL_CDN}/dist/reveal.css">
  <link rel="stylesheet" href="{REVEAL_CDN}/dist/theme/black.css" id="theme">

  <!-- reveal.js plugins CSS -->
  <link rel="stylesheet" href="{REVEAL_CDN}/plugin/highlight/monokai.css">

  <!-- Google Fonts -->
  {font_imports}

  <!-- Generated theme CSS (overrides reveal.js defaults) -->
  <style id="barise-theme">
{theme_css}
  </style>

  <!-- Layout CSS for slide types -->
  <style id="barise-layouts">
{self._layout_css()}
  </style>
</head>
<body>
  <div class="reveal">
    <div class="slides">
{slides_html}
    </div>
  </div>

  <!-- reveal.js core -->
  <script src="{REVEAL_CDN}/dist/reveal.js"></script>
  <!-- reveal.js plugins -->
  <script src="{REVEAL_CDN}/plugin/markdown/markdown.js"></script>
  <script src="{REVEAL_CDN}/plugin/highlight/highlight.js"></script>
  <script src="{REVEAL_CDN}/plugin/math/math.js"></script>
  <script src="{REVEAL_CDN}/plugin/notes/notes.js"></script>
  <script src="{REVEAL_CDN}/plugin/search/search.js"></script>
  <script src="{REVEAL_CDN}/plugin/zoom/zoom.js"></script>

  <!-- Chart.js for data visualisations -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>

  <script>
    // Initialize reveal.js
    Reveal.initialize({reveal_config});

    // Render Chart.js canvases
    document.querySelectorAll('canvas[data-chart]').forEach(function(canvas) {{
      try {{
        var cfg = JSON.parse(canvas.getAttribute('data-chart'));
        new Chart(canvas.getContext('2d'), cfg);
      }} catch(e) {{ console.warn('Chart render failed:', e); }}
    }});
  </script>
</body>
</html>"""

    # ------------------------------------------------------------------ #
    #  LAYOUT CSS (embedded in every presentation)                       #
    # ------------------------------------------------------------------ #

    def _layout_css(self) -> str:
        """Return CSS rules for all layout types."""
        return """
    /* ====== Global Overrides ====== */
    .reveal .slides section {
      text-align: left;
      padding: 2rem 3rem;
      box-sizing: border-box;
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }
    .reveal .slides section h1 { font-size: 3.2rem; font-weight: 800; line-height: 1.1; margin-bottom: 1rem; }
    .reveal .slides section h2 { font-size: 2.4rem; font-weight: 700; line-height: 1.2; margin-bottom: 0.8rem; }
    .reveal .slides section h3 { font-size: 1.6rem; font-weight: 600; margin-bottom: 0.6rem; }
    .reveal .slides section h4 { font-size: 1.2rem; font-weight: 600; margin-bottom: 0.4rem; }
    .reveal .slides section p  { font-size: 1.1rem; line-height: 1.6; }
    .reveal .slides section ul { list-style: none; padding: 0; }
    .reveal .slides section ul li { font-size: 1.1rem; line-height: 1.6; padding-left: 1.5em; position: relative; margin-bottom: 0.5em; }
    .reveal .slides section ul li::before { content: "\\2022"; color: var(--r-link-color, #38BDF8); position: absolute; left: 0; font-weight: bold; }

    .elements-layer { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }
    .elements-layer .element { pointer-events: auto; }

    /* ====== center-focus ====== */
    .slide-center-focus { text-align: center; align-items: center; }
    .center-focus { text-align: center; width: 100%; }
    .center-focus .tagline { font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.15em; opacity: 0.7; margin-bottom: 1rem; }
    .center-focus .presenter { font-size: 1rem; opacity: 0.7; margin-top: 1.5rem; }

    /* ====== split-screen / text-visual / visual-text ====== */
    .split-screen, .text-visual, .visual-text { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; align-items: center; height: 100%; }
    .split-image, .visual-image { width: 100%; height: auto; max-height: 80vh; object-fit: contain; border-radius: 8px; }

    /* ====== full-bleed ====== */
    .full-bleed { display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; height: 100%; }

    /* ====== bullets ====== */
    .bullets-layout { display: flex; flex-direction: column; justify-content: center; }
    .bullets-layout .subtitle { font-size: 1rem; opacity: 0.7; margin-bottom: 1.5rem; }

    /* ====== grid-2x2 ====== */
    .grid-2x2 .grid-container { display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 1.5rem; flex: 1; }
    .grid-2x2 .grid-cell { background: rgba(255,255,255,0.05); border-radius: 8px; padding: 1.5rem; display: flex; align-items: center; justify-content: center; text-align: center; font-size: 1rem; }

    /* ====== grid-3x1 ====== */
    .grid-3x1 .grid-container { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1.5rem; flex: 1; align-items: start; }
    .grid-3x1 .grid-cell { background: rgba(255,255,255,0.05); border-radius: 8px; padding: 1.5rem; text-align: center; }

    /* ====== top-bottom ====== */
    .top-bottom { display: flex; flex-direction: column; }
    .top-bottom .top-section { flex: 0 0 auto; margin-bottom: 2rem; }
    .top-bottom .bottom-section { flex: 1; }

    /* ====== comparison ====== */
    .comparison-table { width: 100%; border-collapse: collapse; margin-top: 1.5rem; }
    .comparison-table th { text-align: left; padding: 0.8rem 1rem; border-bottom: 2px solid var(--r-link-color, #38BDF8); font-size: 1rem; }
    .comparison-table td { padding: 0.6rem 1rem; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 0.95rem; }
    .comparison-table tr.advantage td:nth-child(2) { color: var(--r-link-color, #38BDF8); font-weight: 600; }

    /* ====== timeline ====== */
    .timeline-track { position: relative; padding-left: 2.5rem; }
    .timeline-track::before { content: ""; position: absolute; left: 0.75rem; top: 0; bottom: 0; width: 2px; background: var(--r-link-color, #38BDF8); }
    .timeline-item { position: relative; margin-bottom: 1.5rem; }
    .timeline-marker { position: absolute; left: -2.15rem; top: 0.3rem; width: 12px; height: 12px; border-radius: 50%; background: var(--r-link-color, #38BDF8); border: 2px solid var(--r-background-color, #0F172A); }
    .timeline-item.timeline-completed .timeline-marker { background: #10B981; }
    .timeline-item.timeline-in-progress .timeline-marker { background: #F59E0B; box-shadow: 0 0 8px rgba(245,158,11,0.5); }
    .timeline-item.timeline-planned .timeline-marker { background: rgba(255,255,255,0.3); }
    .timeline-date { font-size: 0.85rem; opacity: 0.6; }

    /* ====== kpi-dashboard ====== */
    .kpi-grid { display: grid; gap: 1.5rem; margin-top: 1.5rem; }
    .kpi-cols-1 { grid-template-columns: 1fr; }
    .kpi-cols-2 { grid-template-columns: 1fr 1fr; }
    .kpi-cols-3 { grid-template-columns: 1fr 1fr 1fr; }
    .kpi-cols-4 { grid-template-columns: 1fr 1fr 1fr 1fr; }
    .kpi-card { background: rgba(255,255,255,0.05); border-radius: 12px; padding: 1.5rem; text-align: center; }
    .kpi-value { font-size: 2.8rem; font-weight: 800; color: var(--r-link-color, #38BDF8); }
    .kpi-label { font-size: 0.9rem; opacity: 0.7; margin-top: 0.3rem; }
    .kpi-change { font-size: 0.85rem; margin-top: 0.5rem; }
    .kpi-card.kpi-up .kpi-change { color: #10B981; }
    .kpi-card.kpi-up .kpi-change::before { content: "\\2191 "; }
    .kpi-card.kpi-down .kpi-change { color: #EF4444; }
    .kpi-card.kpi-down .kpi-change::before { content: "\\2193 "; }

    /* ====== quote ====== */
    .quote-layout { display: flex; align-items: center; justify-content: center; height: 100%; text-align: center; }
    .quote-layout blockquote { font-size: 1.8rem; font-style: italic; max-width: 80%; border-left: 4px solid var(--r-link-color, #38BDF8); padding-left: 1.5rem; text-align: left; }
    .quote-layout cite { display: block; font-size: 1rem; font-style: normal; opacity: 0.7; margin-top: 1rem; }

    /* ====== team-grid ====== */
    .team-grid { display: grid; gap: 2rem; margin-top: 1.5rem; }
    .team-cols-1 { grid-template-columns: 1fr; }
    .team-cols-2 { grid-template-columns: 1fr 1fr; }
    .team-cols-3 { grid-template-columns: 1fr 1fr 1fr; }
    .team-cols-4 { grid-template-columns: 1fr 1fr 1fr 1fr; }
    .team-member { text-align: center; }
    .team-photo { width: 120px; height: 120px; border-radius: 50%; object-fit: cover; margin: 0 auto 1rem; display: block; }
    .team-avatar { width: 120px; height: 120px; border-radius: 50%; background: var(--r-link-color, #38BDF8); color: var(--r-background-color, #0F172A); display: flex; align-items: center; justify-content: center; font-size: 2rem; font-weight: 700; margin: 0 auto 1rem; }
    .team-role { font-size: 0.9rem; opacity: 0.7; }
    .team-bio { font-size: 0.85rem; opacity: 0.6; margin-top: 0.3rem; }

    /* ====== chart ====== */
    .chart-layout .chart-container { flex: 1; display: flex; align-items: center; justify-content: center; margin-top: 1rem; }
    .chart-layout canvas { max-width: 100%; max-height: 60vh; }
    .chart-caption { font-size: 0.9rem; opacity: 0.7; text-align: center; margin-top: 1rem; }

    /* ====== overlay ====== */
    .overlay-layout { display: flex; flex-direction: column; justify-content: flex-end; padding: 3rem; background: linear-gradient(transparent 30%, rgba(0,0,0,0.7)); height: 100%; }

    /* ====== blank ====== */
    .blank-layout { height: 100%; }

    /* ====== Background Effects ====== */
    /* Mesh gradient background */
    .bg-mesh {
        background-image: 
            radial-gradient(at 0% 0%, var(--mesh-1, rgba(15,23,42,0.8)) 0px, transparent 50%),
            radial-gradient(at 100% 100%, var(--mesh-2, rgba(14,165,233,0.6)) 0px, transparent 50%),
            radial-gradient(at 50% 50%, var(--mesh-3, rgba(51,65,85,0.4)) 0px, transparent 30%);
        background-size: 100% 100%;
    }
    
    /* Pattern overlays */
    .pattern-dots {
        background-image: radial-gradient(rgba(255,255,255,0.08) 1px, transparent 1px);
        background-size: 20px 20px;
    }
    .pattern-grid {
        background-image: 
            linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px);
        background-size: 40px 40px;
    }
    .pattern-diagonal-lines {
        background-image: repeating-linear-gradient(
            45deg,
            transparent,
            transparent 10px,
            rgba(255,255,255,0.03) 10px,
            rgba(255,255,255,0.03) 20px
        );
    }
    .pattern-cross-hatch {
        background-image: 
            repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(255,255,255,0.02) 10px, rgba(255,255,255,0.02) 20px),
            repeating-linear-gradient(-45deg, transparent, transparent 10px, rgba(255,255,255,0.02) 10px, rgba(255,255,255,0.02) 20px);
    }
    .pattern-waves {
        background-image: repeating-linear-gradient(0deg, transparent, transparent 20px, rgba(255,255,255,0.02) 20px, rgba(255,255,255,0.02) 21px);
    }
    .pattern-hexagons {
        background-image: url("data:image/svg+xml,%3Csvg width='28' height='49' viewBox='0 0 28 49' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M14 0L28 8.5V24.5L14 33L0 24.5V8.5L14 0z' fill='none' stroke='rgba(255,255,255,0.03)' stroke-width='1'/%3E%3C/svg%3E");
        background-size: 28px 49px;
    }
    
    /* Noise texture overlay */
    .bg-noise::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
        pointer-events: none;
        z-index: 1;
    }
    .bg-noise section {
        position: relative;
    }
    
    /* Glass effect */
    .bg-glass {
        backdrop-filter: blur(12px);
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
    }
"""
