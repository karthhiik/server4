"""
Image Prompt Generator for Azure Flux.

Generates descriptive, style-aware prompts for Azure Flux image generation.
Each prompt is tailored to the slide kind, topic, and visual style preferences.
"""

import logging
from typing import Optional

from app.mcp.brain_mcp.research.models import SlideKind, StyleProfile

logger = logging.getLogger(__name__)

# Visual style mappings for different visual preferences
_VISUAL_STYLE_PROMPTS = {
    "chart_heavy": "clean data visualization with modern flat design, professional color palette",
    "image_accent": "subtle professional photograph as background with overlay space for text",
    "product_screenshot": "modern software UI screenshot mockup with clean interface design",
    "hero_image": "bold dramatic hero image, cinematic wide angle, professional photography",
    "minimal": "minimal abstract geometric shapes, clean white space, subtle gradients",
    "diagram": "clean technical diagram with connected nodes, flowchart style, modern flat design",
    "kpi_dashboard": "modern KPI dashboard mockup with metric cards," " clean data visualization",
    "comparison_diagram": "side-by-side comparison layout, split design, contrasting elements",
    "impact_visual": "impactful environmental or social impact imagery, documentary style",
    "community_collage": "diverse group of people collaborating, modern workspace, authentic",
    "product_detail": "close-up product detail shot, craft quality, precise engineering",
    "timeline": "horizontal timeline infographic design, milestone markers, clean layout",
    "architecture_diagram": "technical architecture diagram, system components, cloud infrastructure",
    "table": "clean structured data table with headers, professional spreadsheet aesthetic",
    "comparison_table": "two-column comparison layout, pros and cons format, structured design",
    "checklist_table": "verification checklist with status indicators, organized grid layout",
    "waterfall_chart": "financial waterfall chart visualization, accounting format, step progression",
    "market_map": "market landscape map with quadrants, company logos, positioning grid",
    "scenario_table": "three-scenario comparison (base/bear/bull), probability weighted layout",
    "comparison_matrix": "competitive matrix with feature comparison, structured grid",
    "process_flow": "business process flowchart, sequential steps, professional diagram",
    "funnel_chart": "marketing funnel visualization, conversion stages, gradient colors",
    "social_proof_grid": "grid of customer logos and testimonials, trust building layout",
    "supply_demand_chart": "supply and demand curve intersection, economics chart style",
    "compliance_checklist": "regulatory compliance checklist, approval badges, certification marks",
    "clinical_data_chart": "clinical trial results visualization, medical data presentation",
    "impact_infographic": "environmental impact infographic, carbon footprint visualization",
    "code_snippet": "code editor screenshot with syntax highlighting, developer tool aesthetic",
    "data_table": "structured research data table, academic formatting, clear headers",
    "figure_with_caption": "scientific figure with numbered caption, publication quality",
    "detailed_table": "comprehensive reference table, multi-column data, appendix format",
    "annotated_timeline": "annotated timeline with evidence markers, chronological flow",
    "sparkline_kpi": "compact KPI cards with sparkline trends, dashboard widget style",
    "annotated_chart": "chart with expert annotations, callout boxes, insight markers",
    "evidence_board": "detective-style evidence board, connected notes and photos, investigation",
    "full_bleed_image": "edge-to-edge dramatic photograph, no margins, cinematic composition",
    "cinematic_image": "widescreen cinematic shot, dramatic lighting, film grain, 16:9 aspect",
    "editorial_layout": "magazine editorial layout, typography-focused, pull quotes",
    "multi_chart_dashboard": "multi-panel dashboard with 4-6 charts, dense data visualization",
    "icon_grid": "modern icon grid layout, flat design icons, labeled categories",
    "premium_photography": "luxury product photography, muted tones, elegant composition",
    "text_only_bold": "bold typography only, large monospace text, brutalist design",
    "saas_metrics_dashboard": "SaaS metrics dashboard, ARR/MRR charts, cohort analysis",
    "architecture_and_benchmark": "system architecture with performance benchmarks overlay",
    "pipeline_diagram": "biotech pipeline stages diagram, phase progression, clinical pathway",
    "capability_matrix": "defense capability matrix, feature grid, certification badges",
    "retail_metrics_grid": "retail KPI grid, store performance metrics, inventory visualization",
    "before_after_comparison": "before and after comparison layout, transformation showcase",
    "map_overlay": "geographic map with data overlay, route visualization, logistics network",
    "property_comparison_table": "real estate comparison table, property metrics, deal structure",
    "minimal_with_photo": "minimal slide with small authentic photo, clean white space",
}

# Slide kind descriptions for context
_SLIDE_KIND_CONTEXT = {
    SlideKind.title: "opening title slide, bold and memorable first impression",
    SlideKind.problem: "problem statement, showing pain point or challenge",
    SlideKind.solution: "solution showcase, demonstrating how the product solves the problem",
    SlideKind.market: "market opportunity, showing scale and potential",
    SlideKind.competition: "competitive landscape, positioning against alternatives",
    SlideKind.gtm: "go-to-market strategy, showing distribution and growth channels",
    SlideKind.traction: "growth and traction metrics, showing momentum",
    SlideKind.financial: "financial projections and metrics",
    SlideKind.team: "team showcase, highlighting expertise and experience",
    SlideKind.ask: "funding ask, investment opportunity",
    SlideKind.why_now: "market timing, showing why now is the right moment",
    SlideKind.product_demo: "product demonstration, showing the product in action",
    SlideKind.appendix: "supplementary information, detailed reference data",
}


class ImagePromptGenerator:
    """Generates descriptive prompts for Azure Flux image generation."""

    def generate(
        self,
        slide_kind: SlideKind,
        title: str,
        topic: str,
        style: StyleProfile,
    ) -> str:
        """Create an image generation prompt for Azure Flux.

        Args:
            slide_kind: Type of slide to generate image for.
            title: The slide headline for thematic context.
            topic: The overall presentation topic.
            style: The style profile controlling visual preferences.

        Returns:
            A descriptive image generation prompt string.
        """
        # Get visual style description
        visual_pref = style.visual_preference
        visual_desc = _VISUAL_STYLE_PROMPTS.get(
            visual_pref,
            "modern professional presentation slide background, clean design",
        )

        # Get slide context
        slide_context = _SLIDE_KIND_CONTEXT.get(
            slide_kind,
            "professional presentation slide",
        )

        # Build the prompt
        parts = [
            f"Professional presentation slide image for a {slide_context}.",
            f"Topic: {topic}.",
            f"Slide headline context: {title}.",
            f"Visual style: {visual_desc}.",
            "Requirements: 16:9 aspect ratio, high contrast text readability areas,",
            "professional color palette, no text rendered in image,",
            "suitable as slide background or accent image.",
        ]

        # Add tone modifiers based on style
        tone_modifiers = self._get_tone_modifiers(style.tone)
        if tone_modifiers:
            parts.append(f"Mood: {tone_modifiers}.")

        # Add technical specs
        parts.append("Technical: high resolution, 1920x1080, PNG quality, no watermarks.")

        prompt = " ".join(parts)

        # Safety: ensure prompt doesn't contain harmful content
        prompt = self._sanitize_prompt(prompt)

        logger.debug(
            "Generated image prompt for %s slide: %s chars",
            slide_kind.value,
            len(prompt),
        )
        return prompt

    def _get_tone_modifiers(self, tone: str) -> str:
        """Map style tone to visual mood descriptors."""
        tone_map = {
            "cold_data": "clinical, precise, blue-grey tones",
            "authoritative_storytelling": "confident, warm earth tones, sophisticated",
            "product_obsessed": "clean, minimal, product-focused, white space",
            "thesis_driven": "intellectual, deep navy and gold accents",
            "growth_velocity": "dynamic, energetic, green accents, upward motion",
            "authentic_founder": "warm, authentic, natural tones, personal",
            "saas_analytical": "professional, blue enterprise tones, structured",
            "growth_trajectory": "momentum, gradient from dark to light, ascending",
            "visionary_bold": "futuristic, gradient, bold colors, expansive",
            "hustle_authentic": "raw, honest, minimal decoration, focused",
            "contrarian_intellectual": "provocative, dark background, sharp contrast",
            "purposeful_urgent": "mission-driven, warm tones, human-centered",
            "technical_authority": "precise, technical, dark mode, code-inspired",
            "community_voice": "diverse, colorful, collaborative, connected",
            "perfectionist_precise": "crafted, detailed, premium finish, precise",
            "candid_operational": "honest, straightforward, neutral professional tones",
            "executive_formal": "boardroom, dark suit, formal, structured",
            "analytical_neutral": "objective, cool tones, data-driven",
            "investment_committee": "serious, institutional, traditional finance",
            "due_diligence_formal": "thorough, structured, verification-focused",
            "financial_rigor": "numbers-focused, spreadsheet-inspired, precise",
            "landscape_analytical": "bird's eye view, mapping, landscape perspective",
            "risk_aware_measured": "cautious, balanced, muted warning tones",
            "portfolio_strategic": "strategic, chess-like, calculated positioning",
            "enterprise_professional": "corporate, reliable, scalable, mature",
            "product_growth": "growth hacking, metrics, funnel visualization",
            "consumer_energetic": "vibrant, social, user-generated, playful",
            "marketplace_analytical": "network effects, two-sided, connected",
            "regulatory_trustworthy": "trustworthy, secure, shield imagery, blue",
            "clinical_evidence_based": "medical, clean, evidence-based, white coat",
            "impact_urgent": "environmental, green, sustainability, urgency",
            "developer_pragmatic": "developer, terminal, code, dark theme",
            "keynote_dramatic": "dramatic, theatrical, spotlight, stage",
            "cinematic_suspense": "cinematic, moody, dramatic lighting, tension",
            "editorial_polished": "editorial, magazine quality, typography-focused",
            "data_maximalist": "dense, dashboard, multiple data points, information-rich",
            "modern_corporate": "modern, clean corporate, icon-driven, structured",
            "premium_refined": "luxury, refined, understated, elegant",
            "brutalist_raw": "brutalist, raw, monochrome, stark contrast",
            "demo_walkthrough": "interactive, step-by-step, UI focused, guided",
        }
        return tone_map.get(tone, "professional, clean, modern")

    @staticmethod
    def _sanitize_prompt(prompt: str) -> str:
        """Remove potentially harmful content from image prompts."""
        # Basic sanitization: remove control characters
        sanitized = "".join(c for c in prompt if c.isprintable() or c in ("\n", "\t"))
        # Limit length to prevent prompt injection
        if len(sanitized) > 2000:
            sanitized = sanitized[:2000]
        return sanitized
