"""
Presentation Modes Engine — Phase 11.

Manages Reading mode vs. Presentation mode for slide output.
Each mode provides a distinct experience with different navigation,
layout, and feature sets. Integrates with existing dual-mode content
from the V2 slide generator.

Modes:
  - Reading: Scrollable document with TOC, inline notes, expanded details
  - Presentation: Fullscreen slideshow with keyboard nav, timer, transitions
  - Overview: Grid thumbnail view for navigation
  - Speaker: Dual-view with notes and timer
  - Print: Optimized for paper/PDF output

Per-renderer adaptation:
  - reveal.js → Presentation/Overview natively; Reading via linearized HTML
  - React+3D → Presentation best; Reading degrades gracefully
  - HTML → Reading natively; Presentation via minimal slide container
  - PPTX → Presentation mode; Reading via notes export
"""

from __future__ import annotations

import html
import re
import time
from typing import Any, Optional

import structlog

from app.services.slides_new.quality.models import (
    ModeConfig,
    ModeFeature,
    NavigationType,
    PresentationMode,
    SlideReadingContent,
)
from app.services.slides_new.renderers.base_renderer import RendererType

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════════
# DEFAULT MODE CONFIGURATIONS
# ═══════════════════════════════════════════════════════════════════


def _build_reading_config() -> ModeConfig:
    """Build default Reading mode configuration."""
    return ModeConfig(
        mode=PresentationMode.READING,
        navigation=NavigationType.SCROLL,
        features=[
            ModeFeature(name="toc_sidebar", enabled=True, description="Table of contents sidebar"),
            ModeFeature(name="inline_notes", enabled=True, description="Show speaker notes inline"),
            ModeFeature(name="expanded_details", enabled=True, description="Expand chart/data details"),
            ModeFeature(name="dark_mode_toggle", enabled=True, description="Dark/light mode switch"),
            ModeFeature(name="font_resize", enabled=True, description="User-adjustable font size"),
            ModeFeature(name="search", enabled=True, description="Full-text search across slides"),
            ModeFeature(name="annotations", enabled=True, description="Inline annotations and footnotes"),
            ModeFeature(name="print_friendly", enabled=True, description="Print-optimized CSS"),
        ],
        css_class="mode-reading",
        layout="scroll",
        show_speaker_notes=True,
        show_slide_numbers=False,
        show_progress_bar=False,
        show_toc_sidebar=True,
        enable_transitions=False,
        enable_fragments=False,
        enable_timer=False,
        aspect_ratio="auto",
    )


def _build_presentation_config() -> ModeConfig:
    """Build default Presentation mode configuration."""
    return ModeConfig(
        mode=PresentationMode.PRESENTATION,
        navigation=NavigationType.KEYBOARD,
        features=[
            ModeFeature(name="fullscreen", enabled=True, description="Fullscreen display"),
            ModeFeature(name="transitions", enabled=True, description="Slide transitions"),
            ModeFeature(name="fragments", enabled=True, description="Incremental reveal"),
            ModeFeature(name="laser_pointer", enabled=True, description="Virtual laser pointer"),
            ModeFeature(name="presenter_timer", enabled=True, description="Built-in presentation timer"),
            ModeFeature(name="slide_overview", enabled=True, description="Quick overview grid (Esc key)"),
            ModeFeature(name="keyboard_shortcuts", enabled=True, description="Arrow/space navigation"),
            ModeFeature(name="auto_advance", enabled=False, description="Timed auto-advance"),
        ],
        css_class="mode-presentation",
        layout="slideshow",
        show_speaker_notes=False,
        show_slide_numbers=True,
        show_progress_bar=True,
        show_toc_sidebar=False,
        enable_transitions=True,
        enable_fragments=True,
        enable_timer=True,
        aspect_ratio="16:9",
    )


def _build_overview_config() -> ModeConfig:
    """Build default Overview mode configuration."""
    return ModeConfig(
        mode=PresentationMode.OVERVIEW,
        navigation=NavigationType.CLICK,
        features=[
            ModeFeature(name="grid_view", enabled=True, description="Thumbnail grid"),
            ModeFeature(name="zoom_preview", enabled=True, description="Hover zoom preview"),
            ModeFeature(name="drag_reorder", enabled=True, description="Drag to reorder slides"),
            ModeFeature(name="quick_jump", enabled=True, description="Click to jump to slide"),
        ],
        css_class="mode-overview",
        layout="grid",
        show_speaker_notes=False,
        show_slide_numbers=True,
        show_progress_bar=False,
        enable_transitions=False,
        enable_fragments=False,
    )


def _build_speaker_config() -> ModeConfig:
    """Build default Speaker mode configuration."""
    return ModeConfig(
        mode=PresentationMode.SPEAKER,
        navigation=NavigationType.KEYBOARD,
        features=[
            ModeFeature(name="notes_panel", enabled=True, description="Large speaker notes panel"),
            ModeFeature(name="preview_next", enabled=True, description="Preview next slide"),
            ModeFeature(name="elapsed_timer", enabled=True, description="Elapsed time display"),
            ModeFeature(name="clock", enabled=True, description="Current time display"),
            ModeFeature(name="slide_count", enabled=True, description="Current/total slide indicator"),
        ],
        css_class="mode-speaker",
        layout="dual-panel",
        show_speaker_notes=True,
        show_slide_numbers=True,
        show_progress_bar=True,
        enable_transitions=True,
        enable_fragments=True,
        enable_timer=True,
    )


def _build_print_config() -> ModeConfig:
    """Build default Print mode configuration."""
    return ModeConfig(
        mode=PresentationMode.PRINT,
        navigation=NavigationType.SCROLL,
        features=[
            ModeFeature(name="page_breaks", enabled=True, description="Page breaks between slides"),
            ModeFeature(name="print_notes", enabled=True, description="Include speaker notes"),
            ModeFeature(name="high_contrast", enabled=True, description="High contrast for printing"),
            ModeFeature(name="no_animations", enabled=True, description="Strip all animations"),
        ],
        css_class="mode-print",
        layout="scroll",
        show_speaker_notes=True,
        show_slide_numbers=True,
        show_progress_bar=False,
        enable_transitions=False,
        enable_fragments=False,
        dark_mode=False,
    )


# Mode config lookup
_MODE_DEFAULTS: dict[PresentationMode, ModeConfig] = {}


def get_mode_config(mode: PresentationMode) -> ModeConfig:
    """Get the default configuration for a mode."""
    if not _MODE_DEFAULTS:
        _MODE_DEFAULTS[PresentationMode.READING] = _build_reading_config()
        _MODE_DEFAULTS[PresentationMode.PRESENTATION] = _build_presentation_config()
        _MODE_DEFAULTS[PresentationMode.OVERVIEW] = _build_overview_config()
        _MODE_DEFAULTS[PresentationMode.SPEAKER] = _build_speaker_config()
        _MODE_DEFAULTS[PresentationMode.PRINT] = _build_print_config()
    return _MODE_DEFAULTS[mode]


def get_all_modes() -> list[ModeConfig]:
    """Get all mode configurations."""
    return [get_mode_config(m) for m in PresentationMode]


# ═══════════════════════════════════════════════════════════════════
# RENDERER-MODE COMPATIBILITY
# ═══════════════════════════════════════════════════════════════════


# Compatibility matrix: which renderers support which modes natively
_RENDERER_MODE_SUPPORT: dict[RendererType, dict[PresentationMode, str]] = {
    RendererType.REVEAL_JS: {
        PresentationMode.PRESENTATION: "native",
        PresentationMode.OVERVIEW: "native",      # reveal.js Esc overview
        PresentationMode.SPEAKER: "native",        # reveal.js speaker view
        PresentationMode.READING: "adapted",       # linearized HTML
        PresentationMode.PRINT: "adapted",         # reveal.js print-pdf
    },
    RendererType.REACT_3D: {
        PresentationMode.PRESENTATION: "native",
        PresentationMode.OVERVIEW: "adapted",
        PresentationMode.READING: "degraded",      # loses 3D
        PresentationMode.SPEAKER: "adapted",
        PresentationMode.PRINT: "degraded",
    },
    RendererType.HTML: {
        PresentationMode.READING: "native",
        PresentationMode.PRESENTATION: "adapted",
        PresentationMode.OVERVIEW: "adapted",
        PresentationMode.SPEAKER: "adapted",
        PresentationMode.PRINT: "native",
    },
    RendererType.PPTX: {
        PresentationMode.PRESENTATION: "native",
        PresentationMode.READING: "degraded",
        PresentationMode.OVERVIEW: "degraded",
        PresentationMode.SPEAKER: "adapted",
        PresentationMode.PRINT: "native",
    },
}


def check_mode_compatibility(
    renderer: RendererType, mode: PresentationMode
) -> str:
    """
    Check how well a renderer supports a given mode.

    Returns: "native", "adapted", "degraded", or "unsupported"
    """
    return _RENDERER_MODE_SUPPORT.get(renderer, {}).get(mode, "unsupported")


def get_supported_modes(renderer: RendererType) -> list[dict[str, str]]:
    """Get all modes with their support level for a renderer."""
    support = _RENDERER_MODE_SUPPORT.get(renderer, {})
    return [
        {"mode": mode.value, "support": support.get(mode, "unsupported")}
        for mode in PresentationMode
    ]


# ═══════════════════════════════════════════════════════════════════
# READING MODE TRANSFORMER
# ═══════════════════════════════════════════════════════════════════


class ReadingModeTransformer:
    """
    Transforms presentation DSL into a reading-optimized document.

    Converts the slide-based format into a continuous scrollable document
    with table of contents, inline speaker notes, expanded data details,
    and accessible text alternatives for visual content.
    """

    def __init__(self, include_notes: bool = True, include_details: bool = True):
        self.include_notes = include_notes
        self.include_details = include_details
        self._transforms_run = 0

    def transform(
        self, presentation_dsl: dict[str, Any]
    ) -> list[SlideReadingContent]:
        """
        Transform all slides into reading content.

        Args:
            presentation_dsl: Full DSL dict

        Returns:
            List of SlideReadingContent entries
        """
        self._transforms_run += 1
        slides = presentation_dsl.get("slides", [])
        result: list[SlideReadingContent] = []
        current_section = ""

        for i, slide in enumerate(slides):
            content = slide.get("content", {})
            title = content.get("title", f"Slide {i + 1}")

            # Detect section changes
            section = content.get("section", "")
            if section:
                current_section = section

            # Build body HTML from content fields
            body_parts: list[str] = []
            subtitle = content.get("subtitle", "")
            if subtitle:
                body_parts.append(f"<p class='subtitle'>{html.escape(subtitle)}</p>")

            body_text = content.get("body", "")
            if body_text:
                body_parts.append(f"<div class='body'>{html.escape(body_text)}</div>")

            # Bullet points
            bullets = content.get("bullets", []) or content.get("points", [])
            if bullets:
                items = "".join(
                    f"<li>{html.escape(str(b))}</li>" for b in bullets
                )
                body_parts.append(f"<ul class='reading-bullets'>{items}</ul>")

            # Data/chart description
            data_desc = content.get("data_description", "")
            if data_desc:
                body_parts.append(
                    f"<div class='data-detail'>{html.escape(data_desc)}</div>"
                )

            body_html = "\n".join(body_parts)

            # Speaker notes
            notes = slide.get("speakerNotes", "") if self.include_notes else ""

            # Expanded details from elements
            details_parts: list[str] = []
            if self.include_details:
                for elem in slide.get("elements", []):
                    if elem.get("type") in ("chart", "diagram", "table"):
                        desc = elem.get("description", "") or elem.get("alt_text", "")
                        if desc:
                            details_parts.append(desc)

            expanded = "\n".join(details_parts)

            # Word count
            text = f"{title} {subtitle} {body_text} {notes} {expanded}"
            word_count = len(text.split())

            # TOC entry
            toc_entry = title if len(title) <= 60 else title[:57] + "..."

            result.append(SlideReadingContent(
                slide_id=slide.get("id", f"slide_{i}"),
                title=title,
                body_html=body_html,
                speaker_notes=notes,
                expanded_details=expanded,
                toc_entry=toc_entry,
                section=current_section,
                word_count=word_count,
            ))

        return result

    def generate_toc(
        self, reading_content: list[SlideReadingContent]
    ) -> list[dict[str, Any]]:
        """Generate table of contents from reading content."""
        toc: list[dict[str, Any]] = []
        current_section = ""
        for item in reading_content:
            if item.section and item.section != current_section:
                current_section = item.section
                toc.append({
                    "type": "section",
                    "title": current_section,
                    "slide_id": item.slide_id,
                })
            toc.append({
                "type": "slide",
                "title": item.toc_entry,
                "slide_id": item.slide_id,
                "word_count": item.word_count,
            })
        return toc

    @property
    def transforms_run(self) -> int:
        return self._transforms_run


# ═══════════════════════════════════════════════════════════════════
# PRESENTATION MODE ADAPTER
# ═══════════════════════════════════════════════════════════════════


class PresentationModeAdapter:
    """
    Adapts rendered output for a specific display mode.

    Takes render output and a target mode, then applies CSS classes,
    navigation wrappers, and feature toggles to produce the final
    mode-specific output.
    """

    def __init__(self):
        self._adaptations_run = 0

    def adapt(
        self,
        rendered_html: str,
        rendered_css: str,
        mode: PresentationMode,
        renderer: RendererType,
        config: Optional[ModeConfig] = None,
    ) -> dict[str, Any]:
        """
        Adapt rendered output for a specific mode.

        Returns dict with:
            html, css, js, config, mode, support_level
        """
        self._adaptations_run += 1
        cfg = config or get_mode_config(mode)
        support = check_mode_compatibility(renderer, mode)

        result: dict[str, Any] = {
            "mode": mode.value,
            "renderer": renderer.value,
            "support_level": support,
            "config": cfg.to_dict(),
            "html": rendered_html,
            "css": rendered_css,
            "js": "",
        }

        if mode == PresentationMode.READING:
            result = self._adapt_reading(result, cfg, renderer)
        elif mode == PresentationMode.PRESENTATION:
            result = self._adapt_presentation(result, cfg, renderer)
        elif mode == PresentationMode.OVERVIEW:
            result = self._adapt_overview(result, cfg, renderer)
        elif mode == PresentationMode.SPEAKER:
            result = self._adapt_speaker(result, cfg, renderer)
        elif mode == PresentationMode.PRINT:
            result = self._adapt_print(result, cfg, renderer)

        return result

    def _adapt_reading(
        self, result: dict[str, Any], cfg: ModeConfig, renderer: RendererType
    ) -> dict[str, Any]:
        """Adapt for reading mode — continuous scroll."""
        reading_css = """
.mode-reading { max-width: 900px; margin: 0 auto; padding: 2rem; }
.mode-reading .slide { margin-bottom: 3rem; border-bottom: 1px solid #e5e7eb; padding-bottom: 2rem; }
.mode-reading .slide-title { font-size: 1.875rem; font-weight: 700; margin-bottom: 1rem; }
.mode-reading .speaker-notes { background: #f9fafb; border-left: 4px solid #6366f1; padding: 1rem; margin: 1rem 0; font-style: italic; }
.mode-reading .data-detail { background: #eff6ff; border-radius: 0.5rem; padding: 1rem; margin: 1rem 0; }
.toc-sidebar { position: fixed; left: 0; top: 0; width: 260px; height: 100vh; overflow-y: auto; padding: 1rem; background: #f8fafc; border-right: 1px solid #e2e8f0; }
@media (prefers-color-scheme: dark) { .mode-reading { background: #1a1a2e; color: #e2e8f0; } }
@media print { .toc-sidebar { display: none; } .mode-reading { max-width: 100%; } }
"""
        result["css"] += "\n" + reading_css

        # Wrap HTML for scroll layout
        if renderer == RendererType.REVEAL_JS:
            # Linearize reveal.js sections into scroll divs
            result["html"] = re.sub(
                r"<section([^>]*)>",
                r"<div class='slide'\1>",
                result["html"],
            )
            result["html"] = result["html"].replace("</section>", "</div>")

        result["html"] = f"<div class='mode-reading'>\n{result['html']}\n</div>"
        return result

    def _adapt_presentation(
        self, result: dict[str, Any], cfg: ModeConfig, renderer: RendererType
    ) -> dict[str, Any]:
        """Adapt for presentation mode — fullscreen slideshow."""
        pres_css = """
.mode-presentation { width: 100vw; height: 100vh; overflow: hidden; }
.mode-presentation .slide { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
.progress-bar { position: fixed; bottom: 0; left: 0; height: 4px; background: #6366f1; transition: width 0.3s; }
.slide-number { position: fixed; bottom: 12px; right: 16px; font-size: 0.75rem; color: #9ca3af; }
.presentation-timer { position: fixed; top: 12px; right: 16px; font-family: monospace; color: #9ca3af; }
"""
        pres_js = """
document.addEventListener('keydown', function(e) {
  if (e.key === 'ArrowRight' || e.key === ' ') { window.nextSlide && window.nextSlide(); }
  if (e.key === 'ArrowLeft') { window.prevSlide && window.prevSlide(); }
  if (e.key === 'Escape') { window.toggleOverview && window.toggleOverview(); }
  if (e.key === 'f') { document.documentElement.requestFullscreen && document.documentElement.requestFullscreen(); }
});
"""
        result["css"] += "\n" + pres_css
        result["js"] += "\n" + pres_js

        result["html"] = f"<div class='mode-presentation'>\n{result['html']}\n</div>"

        if cfg.show_progress_bar:
            result["html"] += "\n<div class='progress-bar' id='progress'></div>"
        if cfg.show_slide_numbers:
            result["html"] += "\n<div class='slide-number' id='slideNumber'></div>"
        if cfg.enable_timer:
            result["html"] += "\n<div class='presentation-timer' id='timer'></div>"

        return result

    def _adapt_overview(
        self, result: dict[str, Any], cfg: ModeConfig, renderer: RendererType
    ) -> dict[str, Any]:
        """Adapt for overview mode — thumbnail grid."""
        overview_css = """
.mode-overview { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.5rem; padding: 2rem; }
.mode-overview .slide-thumb { border: 2px solid #e5e7eb; border-radius: 0.75rem; overflow: hidden; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; aspect-ratio: 16/9; }
.mode-overview .slide-thumb:hover { transform: scale(1.05); box-shadow: 0 10px 25px rgba(0,0,0,0.15); }
.mode-overview .slide-number { text-align: center; padding: 0.5rem; font-size: 0.75rem; color: #6b7280; }
"""
        result["css"] += "\n" + overview_css
        result["html"] = f"<div class='mode-overview'>\n{result['html']}\n</div>"
        return result

    def _adapt_speaker(
        self, result: dict[str, Any], cfg: ModeConfig, renderer: RendererType
    ) -> dict[str, Any]:
        """Adapt for speaker mode — dual panel with notes."""
        speaker_css = """
.mode-speaker { display: grid; grid-template-columns: 2fr 1fr; height: 100vh; }
.speaker-slide-panel { display: flex; align-items: center; justify-content: center; background: #000; }
.speaker-notes-panel { padding: 1.5rem; overflow-y: auto; background: #1a1a2e; color: #e2e8f0; }
.speaker-notes-panel .notes-text { font-size: 1.25rem; line-height: 1.8; }
.speaker-notes-panel .timer { font-family: monospace; font-size: 2rem; margin-bottom: 1rem; color: #6366f1; }
.speaker-notes-panel .next-preview { margin-top: 1rem; border: 1px solid #374151; border-radius: 0.5rem; overflow: hidden; aspect-ratio: 16/9; }
"""
        result["css"] += "\n" + speaker_css

        result["html"] = f"""<div class='mode-speaker'>
  <div class='speaker-slide-panel'>{result['html']}</div>
  <div class='speaker-notes-panel'>
    <div class='timer' id='speakerTimer'>00:00</div>
    <div class='notes-text' id='speakerNotes'></div>
    <div class='next-preview' id='nextSlide'></div>
  </div>
</div>"""
        return result

    def _adapt_print(
        self, result: dict[str, Any], cfg: ModeConfig, renderer: RendererType
    ) -> dict[str, Any]:
        """Adapt for print mode — page-break optimized."""
        print_css = """
@media print {
  .mode-print .slide { page-break-after: always; min-height: 100vh; }
  .mode-print .speaker-notes { page-break-inside: avoid; }
  .mode-print { background: white !important; color: black !important; }
  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
.mode-print { background: white; color: #111827; }
.mode-print .slide { padding: 2rem; border-bottom: 1px solid #d1d5db; }
"""
        result["css"] += "\n" + print_css
        result["html"] = f"<div class='mode-print'>\n{result['html']}\n</div>"
        return result

    @property
    def adaptations_run(self) -> int:
        return self._adaptations_run


# ═══════════════════════════════════════════════════════════════════
# MODE MANAGER (Unified Access)
# ═══════════════════════════════════════════════════════════════════


class PresentationModeManager:
    """
    Unified manager for all presentation mode operations.

    Provides a single entry point for:
    - Getting/configuring modes
    - Checking renderer compatibility
    - Transforming content for reading mode
    - Adapting rendered output for any mode
    """

    def __init__(self):
        self._reading_transformer = ReadingModeTransformer()
        self._adapter = PresentationModeAdapter()

    def get_mode_config(self, mode: PresentationMode) -> ModeConfig:
        return get_mode_config(mode)

    def get_all_modes(self) -> list[dict[str, Any]]:
        return [cfg.to_dict() for cfg in get_all_modes()]

    def check_compatibility(
        self, renderer: RendererType, mode: PresentationMode
    ) -> str:
        return check_mode_compatibility(renderer, mode)

    def get_renderer_modes(self, renderer: RendererType) -> list[dict[str, str]]:
        return get_supported_modes(renderer)

    def transform_for_reading(
        self, presentation_dsl: dict[str, Any]
    ) -> dict[str, Any]:
        """Transform a presentation DSL into reading mode content."""
        content = self._reading_transformer.transform(presentation_dsl)
        toc = self._reading_transformer.generate_toc(content)
        return {
            "mode": PresentationMode.READING.value,
            "slides": [s.to_dict() for s in content],
            "toc": toc,
            "total_words": sum(s.word_count for s in content),
            "reading_time_min": round(sum(s.word_count for s in content) / 200, 1),
        }

    def adapt_output(
        self,
        rendered_html: str,
        rendered_css: str,
        mode: PresentationMode,
        renderer: RendererType,
        config: Optional[ModeConfig] = None,
    ) -> dict[str, Any]:
        """Adapt rendered output for a specific mode."""
        return self._adapter.adapt(rendered_html, rendered_css, mode, renderer, config)

    def get_stats(self) -> dict[str, Any]:
        return {
            "reading_transforms": self._reading_transformer.transforms_run,
            "mode_adaptations": self._adapter.adaptations_run,
            "supported_modes": len(PresentationMode),
            "supported_renderers": len(RendererType),
        }
