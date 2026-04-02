"""
Prompt Composition Engine — assembles system prompts from modular layers.

Instead of monolithic 2000-word system prompts, the engine composes only
the relevant layers for each LLM call:

    Style Layer    → writing voice (yc_pitch, narrative, etc.)
    Domain Layer   → pitch deck rules, investor psychology
    Layout Layer   → JSON output format per slide type
    Context Layer  → research data, user input
    Quality Layer  → guards and checks
    Output Layer   → JSON schema enforcement

Usage:
    engine = PromptEngine()
    prompt = engine.compose(
        task="slide_content",
        layout="chart",
        style="yc_pitch",
        purpose="pitch",
        include_domain=True,
    )
"""

from typing import Optional

from app.mcp.brain_mcp.prompts.style_system import ContentStyle, get_style_prompt
from app.mcp.brain_mcp.prompts.domain_layers import (
    PITCH_DECK_RULES,
    YC_PRINCIPLES,
    INVESTOR_PSYCHOLOGY,
    DATA_PRESENTATION_RULES,
    COMMON_MISTAKES,
)
from app.mcp.brain_mcp.prompts.investor_system import (
    YC_PITCH_SYSTEM,
    SEQUOIA_SYSTEM,
    INVESTOR_UPDATE_SYSTEM,
    TRACTION_SLIDE_SYSTEM,
    MARKET_SIZING_SYSTEM,
    UNIT_ECONOMICS_SYSTEM,
)
from app.mcp.brain_mcp.prompts.slide_system import LAYOUT_PROMPTS, BASE_SLIDE_SYSTEM
from app.mcp.brain_mcp.prompts.outline_system import OUTLINE_SYSTEM_PROMPT


# Purposes that trigger investor-grade domain layers
INVESTOR_PURPOSES = {"pitch", "fundraising", "investor", "investor_update", "series_a", "seed", "demo_day"}

# Purposes that trigger YC-specific layers
YC_PURPOSES = {"pitch", "demo_day", "yc"}

# Layout → investor-specific prompt override (when purpose is investor-grade)
INVESTOR_LAYOUT_OVERRIDES = {
    "chart": {
        "traction": TRACTION_SLIDE_SYSTEM,
        "market": MARKET_SIZING_SYSTEM,
        "market_opportunity": MARKET_SIZING_SYSTEM,
    },
    "kpi-dashboard": {
        "traction": TRACTION_SLIDE_SYSTEM,
        "unit_economics": UNIT_ECONOMICS_SYSTEM,
        "financials": UNIT_ECONOMICS_SYSTEM,
    },
}


class PromptEngine:
    """Composes system prompts from modular layers based on task context."""

    def compose_outline_prompt(
        self,
        style: str = "yc_pitch",
        purpose: str = "pitch",
    ) -> str:
        """Compose system prompt for outline generation."""
        layers = [OUTLINE_SYSTEM_PROMPT]

        # Style layer
        layers.append(get_style_prompt(style))

        # Domain layer for pitch/investor purposes
        if purpose in INVESTOR_PURPOSES:
            layers.append(PITCH_DECK_RULES)
            if purpose in YC_PURPOSES:
                layers.append(YC_PRINCIPLES)

        # Quality layer
        layers.append(COMMON_MISTAKES)

        return "\n\n---\n\n".join(layers)

    def compose_slide_prompt(
        self,
        layout: str,
        style: str = "yc_pitch",
        purpose: str = "pitch",
        slide_purpose: str = "",
    ) -> str:
        """Compose system prompt for individual slide content generation."""
        layers = [BASE_SLIDE_SYSTEM]

        # Layout-specific format instructions
        layout_prompt = LAYOUT_PROMPTS.get(layout, LAYOUT_PROMPTS.get("bullets", ""))
        layers.append(layout_prompt)

        # Style layer
        layers.append(get_style_prompt(style))

        # Domain layers for investor-grade content
        if purpose in INVESTOR_PURPOSES:
            # Check for layout+purpose specific overrides
            overrides = INVESTOR_LAYOUT_OVERRIDES.get(layout, {})
            slide_purpose_lower = slide_purpose.lower()

            override_found = False
            for keyword, override_prompt in overrides.items():
                if keyword in slide_purpose_lower:
                    layers.append(override_prompt)
                    override_found = True
                    break

            if not override_found:
                layers.append(DATA_PRESENTATION_RULES)

            if purpose in YC_PURPOSES:
                layers.append(YC_PRINCIPLES)

        # Quality guard reminders
        layers.append(COMMON_MISTAKES)

        return "\n\n---\n\n".join(layers)

    def compose_chart_prompt(
        self,
        style: str = "yc_pitch",
        purpose: str = "pitch",
        slide_purpose: str = "",
    ) -> str:
        """Compose system prompt for chart data generation."""
        from app.mcp.brain_mcp.prompts.chart_system import CHART_DATA_SYSTEM

        layers = [CHART_DATA_SYSTEM]

        # Data presentation rules always included for charts
        layers.append(DATA_PRESENTATION_RULES)

        # Investor-specific chart guidance
        if purpose in INVESTOR_PURPOSES:
            slide_purpose_lower = slide_purpose.lower()
            if "traction" in slide_purpose_lower:
                layers.append(TRACTION_SLIDE_SYSTEM)
            elif "market" in slide_purpose_lower:
                layers.append(MARKET_SIZING_SYSTEM)
            elif "unit" in slide_purpose_lower or "economics" in slide_purpose_lower:
                layers.append(UNIT_ECONOMICS_SYSTEM)

        return "\n\n---\n\n".join(layers)

    def compose_notes_prompt(
        self,
        style: str = "yc_pitch",
        purpose: str = "pitch",
    ) -> str:
        """Compose system prompt for speaker notes generation."""
        from app.mcp.brain_mcp.prompts.notes_system import SPEAKER_NOTES_SYSTEM

        layers = [SPEAKER_NOTES_SYSTEM]
        layers.append(get_style_prompt(style))

        if purpose in INVESTOR_PURPOSES:
            layers.append(INVESTOR_PSYCHOLOGY)

        return "\n\n---\n\n".join(layers)

    def compose_refine_prompt(
        self,
        action: str,
        style: Optional[str] = None,
    ) -> str:
        """Compose system prompt for content refinement actions."""
        from app.mcp.brain_mcp.prompts.refine_system import (
            REFINE_SYSTEM, EXPAND_SYSTEM, SUMMARIZE_SYSTEM, TRANSLATE_SYSTEM,
        )

        action_prompts = {
            "rewrite": REFINE_SYSTEM,
            "expand": EXPAND_SYSTEM,
            "summarize": SUMMARIZE_SYSTEM,
            "translate": TRANSLATE_SYSTEM,
        }

        base = action_prompts.get(action, REFINE_SYSTEM)
        layers = [base]

        if style:
            layers.append(get_style_prompt(style))

        return "\n\n---\n\n".join(layers)

    def compose_template_prompt(
        self,
        template_category: str = "general",
        style: str = "yc_pitch",
    ) -> str:
        """Compose system prompt for template filling."""
        from app.mcp.brain_mcp.prompts.template_system import TEMPLATE_FILL_SYSTEM

        layers = [TEMPLATE_FILL_SYSTEM]
        layers.append(get_style_prompt(style))

        # Category-specific domain knowledge
        if template_category in ("fundraising", "investor"):
            layers.append(PITCH_DECK_RULES)
            layers.append(YC_PRINCIPLES)
        elif template_category == "sales":
            layers.append(INVESTOR_PSYCHOLOGY)  # Persuasion principles apply to sales too
        elif template_category == "internal":
            layers.append(DATA_PRESENTATION_RULES)

        return "\n\n---\n\n".join(layers)
