"""
Design Intelligence Orchestrator -- Phase 5.

Central coordination layer that ties together all Phase 5 subsystems:
- Brand DNA Extraction (brand_dna.py)
- Anti-AI-Slop Processing (anti_slop.py)
- Visual Style Discovery (style_discovery.py)
- PreTeXt Text Measurement (pretext_engine.py)
- Integration with existing DesignerAgent and Theme Engine

Provides a unified pipeline for design decisions during presentation generation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from app.services.slides_new.design.brand_dna import (
    BrandDNA,
    BrandDNAExtractor,
    BrandMood,
    VisualStyle,
)
from app.services.slides_new.design.anti_slop import (
    AntiAISlopProcessor,
    SlopReport,
    SlopSeverity,
)
from app.services.slides_new.design.style_discovery import (
    AITemplateSelector,
    LayoutDecision,
    StyleDiscoveryResult,
    StyleIntelligenceEngine,
    StylePreview,
    TYPOGRAPHY_RULES,
    ANIMATION_RULES,
)
from app.services.slides_new.design.pretext_engine import (
    LayoutFitResult,
    PreTeXtEngine,
    TextMeasurement,
    check_slide_fit,
)
from app.services.slides_new.themes.theme_engine import GenerativeThemeEngine
from app.services.slides_new.themes.theme_models import ThemeDefinition

logger = logging.getLogger(__name__)


# -- Pipeline Models ----------------------------------------------------------


class DesignQuality(str, Enum):
    """Quality tiers for design output."""
    DRAFT = "draft"          # Fast, minimal checks
    STANDARD = "standard"    # Anti-slop + basic text fit
    PREMIUM = "premium"      # Full pipeline with brand DNA + PreTeXt + iteration


@dataclass
class SlideDesignSpec:
    """Design specification for a single slide."""
    slide_index: int
    slide_type: str
    layout: str
    typography_scale: str
    animation_preset: str
    layout_reasoning: str = ""
    text_fits: bool = True
    text_suggestions: list[str] = field(default_factory=list)
    slop_report: Optional[SlopReport] = None
    slop_clean: bool = True
    adjusted_font_sizes: dict[str, float] = field(default_factory=dict)


@dataclass
class PresentationDesignResult:
    """Full design result for an entire presentation."""
    slide_specs: list[SlideDesignSpec]
    theme: Optional[ThemeDefinition] = None
    brand_dna: Optional[BrandDNA] = None
    style_preview: Optional[StylePreview] = None
    global_slop_score: float = 100.0  # 0-100, 100 = perfectly clean
    total_overflow_slides: int = 0
    quality_tier: DesignQuality = DesignQuality.STANDARD
    processing_time_ms: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def is_production_ready(self) -> bool:
        """Check if design meets production quality bar."""
        return (
            self.global_slop_score >= 70
            and self.total_overflow_slides == 0
            and all(s.slop_clean for s in self.slide_specs)
        )


# -- Design Intelligence Engine -----------------------------------------------


class DesignIntelligenceEngine:
    """
    Orchestrates the full design intelligence pipeline.

    Pipeline stages:
    1. Style Discovery: Pick visual style based on topic/purpose
    2. Brand DNA Integration (optional): Extract brand identity from uploads
    3. Theme Generation: Build theme from style + brand DNA
    4. Layout Selection: Per-slide layout optimization
    5. Text Measurement: PreTeXt validation for every text block
    6. Anti-Slop: Quality gate filtering AI-generic aesthetics
    7. Iteration: Auto-fix issues found in steps 5-6

    Thread-safe: each instance maintains no shared mutable state.
    """

    def __init__(self):
        self._style_engine = StyleIntelligenceEngine()
        self._template_selector = AITemplateSelector()
        self._pretext = PreTeXtEngine()
        self._anti_slop = AntiAISlopProcessor()
        self._theme_engine = GenerativeThemeEngine()
        self._brand_extractor = BrandDNAExtractor()

    def run_full_pipeline(
        self,
        slides: list[dict[str, Any]],
        topic: str = "",
        purpose: str = "",
        audience: str = "",
        industry: str = "",
        brand_dna: Optional[BrandDNA] = None,
        quality: DesignQuality = DesignQuality.STANDARD,
        selected_preset: Optional[str] = None,
        max_iterations: int = 2,
    ) -> PresentationDesignResult:
        """
        Run the full design intelligence pipeline.

        Args:
            slides: List of slide content dicts with keys:
                - type: SlideType value
                - title: str
                - subtitle: str (optional)
                - body: str (optional)
                - bullets: list[str] (optional)
                - images: list[dict] (optional)
                - charts: list[dict] (optional)
                - kpis: list[dict] (optional)
            topic: Presentation topic
            purpose: e.g. "investor pitch", "sales deck"
            audience: Target audience
            industry: Industry vertical
            brand_dna: Pre-extracted BrandDNA (optional)
            quality: Quality tier
            selected_preset: Override style preset (skip discovery)
            max_iterations: Max fix iterations for Premium quality

        Returns:
            PresentationDesignResult with complete design specs
        """
        start = time.monotonic()
        warnings: list[str] = []

        # Stage 1: Style Discovery
        style_preview = None
        if selected_preset:
            discovery = self._style_engine.discover_styles(
                topic=topic, purpose=purpose, audience=audience,
                industry=industry, count=1,
            )
            # Find matching preset or use first
            style_preview = next(
                (p for p in discovery.previews if p.preset_id == selected_preset),
                discovery.previews[0] if discovery.previews else None,
            )
        else:
            discovery = self._style_engine.discover_styles(
                topic=topic, purpose=purpose, audience=audience,
                industry=industry, count=3,
            )
            style_preview = (
                discovery.previews[discovery.recommended_index]
                if discovery.previews else None
            )

        # Stage 2: Theme Generation
        theme = None
        if brand_dna and brand_dna.primary_color:
            # Brand DNA takes priority
            theme = self._theme_engine.from_brand_colors(
                primary=brand_dna.primary_color,
                accent=brand_dna.accent_color or brand_dna.secondary_color,
            )
            logger.info(
                "Generated theme from Brand DNA (primary=%s)",
                brand_dna.primary_color,
            )
        elif style_preview and style_preview.theme:
            theme = style_preview.theme
            logger.info(
                "Using style preset theme: %s", style_preview.preset_id
            )

        # Determine fonts
        heading_font = "Inter"
        body_font = "Inter"
        if brand_dna and brand_dna.heading_font:
            heading_font = brand_dna.heading_font
            body_font = brand_dna.body_font or heading_font
        elif theme:
            heading_font = theme.typography.heading_font
            body_font = theme.typography.body_font

        # Stage 3: Per-slide design
        slide_specs: list[SlideDesignSpec] = []
        total_slides = len(slides)
        previous_layout = ""

        for i, slide in enumerate(slides):
            spec = self._design_single_slide(
                slide=slide,
                slide_index=i,
                total_slides=total_slides,
                previous_layout=previous_layout,
                heading_font=heading_font,
                body_font=body_font,
                quality=quality,
            )
            slide_specs.append(spec)
            previous_layout = spec.layout

        # Stage 4: Anti-slop analysis (Standard and Premium)
        if quality in (DesignQuality.STANDARD, DesignQuality.PREMIUM):
            slide_specs = self._run_anti_slop_pass(slide_specs, slides)

        # Stage 5: Iteration (Premium only)
        if quality == DesignQuality.PREMIUM:
            for iteration in range(max_iterations):
                issues = sum(
                    1 for s in slide_specs
                    if not s.text_fits or not s.slop_clean
                )
                if issues == 0:
                    break
                logger.info(
                    "Design iteration %d: fixing %d issues",
                    iteration + 1, issues,
                )
                slide_specs = self._iterate_fixes(
                    slide_specs, slides, heading_font, body_font
                )

        # Compute global scores
        total_overflow = sum(1 for s in slide_specs if not s.text_fits)
        slop_scores = [
            s.slop_report.quality_score
            for s in slide_specs
            if s.slop_report is not None
        ]
        global_slop = (
            sum(slop_scores) / len(slop_scores) if slop_scores else 100.0
        )

        elapsed_ms = (time.monotonic() - start) * 1000

        return PresentationDesignResult(
            slide_specs=slide_specs,
            theme=theme,
            brand_dna=brand_dna,
            style_preview=style_preview,
            global_slop_score=round(global_slop, 1),
            total_overflow_slides=total_overflow,
            quality_tier=quality,
            processing_time_ms=round(elapsed_ms, 1),
            warnings=warnings,
        )

    def discover_styles(
        self,
        topic: str = "",
        purpose: str = "",
        audience: str = "",
        industry: str = "",
        count: int = 3,
    ) -> StyleDiscoveryResult:
        """
        Visual Style Discovery UX endpoint.

        Returns N style previews for user selection.
        """
        return self._style_engine.discover_styles(
            topic=topic, purpose=purpose, audience=audience,
            industry=industry, count=count,
        )

    def extract_brand_dna(
        self,
        pixel_data: Optional[bytes] = None,
        width: int = 0,
        height: int = 0,
        hex_colors: Optional[list[str]] = None,
    ) -> BrandDNA:
        """
        Extract Brand DNA from uploaded materials.

        Args:
            pixel_data: Raw RGBA pixel bytes (from image processing)
            width: Image width in pixels
            height: Image height in pixels
            hex_colors: Pre-extracted hex color list (alternative to pixels)

        Returns:
            BrandDNA with extracted brand identity
        """
        if pixel_data and width > 0 and height > 0:
            return self._brand_extractor.extract_from_pixels(
                pixel_data, width, height
            )
        elif hex_colors:
            return self._brand_extractor.extract_from_colors(hex_colors)
        else:
            return self._brand_extractor.extract_from_colors([])

    def analyze_slide_quality(
        self,
        slide_data: dict[str, Any],
    ) -> SlopReport:
        """
        Run anti-AI-slop analysis on a single slide.

        Args:
            slide_data: Slide properties dict

        Returns:
            SlopReport with violations and suggestions
        """
        return self._anti_slop.analyze_slide(slide_data)

    def measure_text(
        self,
        text: str,
        font_family: str = "Inter",
        font_size_pt: float = 16.0,
        max_width_px: float = 1520.0,
    ) -> TextMeasurement:
        """Measure text dimensions using PreTeXt engine."""
        return self._pretext.measure_text(
            text=text,
            font_family=font_family,
            font_size_pt=font_size_pt,
            max_width_px=max_width_px,
        )

    def check_slide_text_fit(
        self,
        layout: str,
        content: dict[str, str],
        heading_font: str = "Inter",
        body_font: str = "Inter",
    ) -> LayoutFitResult:
        """Check if text content fits within a slide layout."""
        return check_slide_fit(
            layout=layout,
            content=content,
            heading_font=heading_font,
            body_font=body_font,
        )

    # -- Internal pipeline stages -------------------------------------------

    def _design_single_slide(
        self,
        slide: dict[str, Any],
        slide_index: int,
        total_slides: int,
        previous_layout: str,
        heading_font: str,
        body_font: str,
        quality: DesignQuality,
    ) -> SlideDesignSpec:
        """Design a single slide: layout selection + text measurement."""
        slide_type = slide.get("type", "custom")

        # Layout selection
        layout_decision = self._template_selector.select_layout(
            slide_content=slide,
            slide_type=slide_type,
            slide_index=slide_index,
            total_slides=total_slides,
            previous_layout=previous_layout,
        )

        spec = SlideDesignSpec(
            slide_index=slide_index,
            slide_type=slide_type,
            layout=layout_decision.layout,
            typography_scale=layout_decision.typography_scale,
            animation_preset=layout_decision.animation_preset,
            layout_reasoning=layout_decision.reasoning,
        )

        # Text measurement (Standard and Premium)
        if quality != DesignQuality.DRAFT:
            content_map = self._build_content_map(slide, layout_decision.layout)
            fit_result = self._pretext.check_layout_fit(
                layout=layout_decision.layout,
                content=content_map,
                font_family=body_font,
                heading_font_size=self._get_heading_size(
                    layout_decision.typography_scale
                ),
                body_font_size=18.0,
            )
            spec.text_fits = fit_result.fits
            spec.text_suggestions = fit_result.suggestions

            # Store adjusted sizes if shrinking was suggested
            if fit_result.title_measurement and fit_result.title_measurement.suggested_font_size:
                spec.adjusted_font_sizes["heading"] = (
                    fit_result.title_measurement.suggested_font_size
                )
            for i, bm in enumerate(fit_result.body_measurements):
                if bm.suggested_font_size:
                    spec.adjusted_font_sizes[f"body_{i}"] = bm.suggested_font_size

        return spec

    def _run_anti_slop_pass(
        self,
        specs: list[SlideDesignSpec],
        slides: list[dict[str, Any]],
    ) -> list[SlideDesignSpec]:
        """Run anti-slop analysis on all slides."""
        for i, (spec, slide) in enumerate(zip(specs, slides)):
            slide_data = {
                "layout": spec.layout,
                "title": slide.get("title", ""),
                "bullets": slide.get("bullets", []),
                "images": slide.get("images", []),
                "charts": slide.get("charts", []),
                **slide,
            }
            report = self._anti_slop.analyze_slide(slide_data)
            spec.slop_report = report
            spec.slop_clean = report.is_clean

        return specs

    def _iterate_fixes(
        self,
        specs: list[SlideDesignSpec],
        slides: list[dict[str, Any]],
        heading_font: str,
        body_font: str,
    ) -> list[SlideDesignSpec]:
        """
        Attempt to fix overflow and slop issues.

        Fix strategies:
        1. Text overflow: Try alternative layout or reduced font size
        2. Slop violations: Apply auto-fixes from AntiAISlopProcessor
        """
        for i, spec in enumerate(specs):
            slide = slides[i] if i < len(slides) else {}

            # Fix text overflow by trying alternative layouts
            if not spec.text_fits:
                alternatives = self._template_selector._get_alternative_layouts(
                    self._template_selector._extract_features(
                        slide, spec.slide_type
                    )
                )
                for alt_layout in alternatives:
                    if alt_layout == spec.layout:
                        continue
                    content_map = self._build_content_map(slide, alt_layout)
                    fit = self._pretext.check_layout_fit(
                        layout=alt_layout,
                        content=content_map,
                        font_family=body_font,
                    )
                    if fit.fits:
                        spec.layout = alt_layout
                        spec.text_fits = True
                        spec.text_suggestions = []
                        spec.layout_reasoning += (
                            f" [auto-fixed: switched to {alt_layout}]"
                        )
                        break

            # Fix slop violations
            if spec.slop_report and not spec.slop_clean:
                slide_data = {
                    "layout": spec.layout,
                    **slide,
                }
                fixed = self._anti_slop.auto_fix(slide_data)
                # Re-analyze after fix
                report = self._anti_slop.analyze_slide(fixed)
                spec.slop_report = report
                spec.slop_clean = report.is_clean

        return specs

    def _build_content_map(
        self,
        slide: dict[str, Any],
        layout: str,
    ) -> dict[str, str]:
        """Build a content map for PreTeXt measurement."""
        content: dict[str, str] = {}

        title = slide.get("title", "")
        subtitle = slide.get("subtitle", "")
        body = slide.get("body", "")
        bullets = slide.get("bullets", [])

        # Title always maps
        content["title"] = title
        if subtitle:
            content["subtitle"] = subtitle

        # Build body text from all text sources
        body_parts = []
        if body:
            body_parts.append(body)
        if bullets:
            body_parts.append("\n".join(f"- {b}" for b in bullets))

        body_text = "\n\n".join(body_parts)

        # Map body to appropriate box name based on layout
        if layout in ("two-column", "comparison"):
            # Split body roughly in half for two-column layouts
            lines = body_text.split("\n")
            mid = len(lines) // 2
            content["left_body"] = "\n".join(lines[:mid]) if lines else ""
            content["right_body"] = "\n".join(lines[mid:]) if lines else ""
        elif layout == "split-screen":
            content["left_body"] = body_text
        elif layout in ("text-left-visual-right",):
            content["body"] = body_text
        else:
            content["body"] = body_text

        return content

    def _get_heading_size(self, typography_scale: str) -> float:
        """Get heading font size for a typography scale."""
        scale_map = {
            "hero": 48.0,
            "default": 36.0,
            "minimal": 28.0,
        }
        return scale_map.get(typography_scale, 36.0)
