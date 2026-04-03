"""
Designer Agent - Visual Design & Layout Intelligence
Agent 3: Creates visual design system, selects color palettes, defines typography,
determines layouts, and generates design specifications for each slide.
"""

from typing import Any, Dict, List, Optional

from app.services.llm import TaskType
from app.services.slides_new.agents.base import (
    BaseAgent,
    AgentOutput,
    AgentType,
    AgentContext,
)


class DesignerAgent(BaseAgent):
    """
    Agent 3: Visual design and layout intelligence.

    Responsibilities:
    - Create design system (colors, typography, spacing)
    - Define slide layouts for each content type
    - Generate visual specifications for each slide
    - Select appropriate imagery style
    - Define animation/transitions
    - Apply Anti-AI-Slop design principles

    Uses design intelligence to avoid generic AI aesthetics.
    """

    DEFAULT_MODEL = "mistral-medium-2505"
    FALLBACK_MODELS = ["gpt-4o-mini", "deepseek-v3"]

    ANTI_AI_SLOP_PRESETS = {
        "yc_pitch": {
            "name": "YC/Sequoia Anti-AI",
            "description": "Clean, founder-led aesthetic - not startup generic",
            "fonts": {
                "heading": "DM Sans",
                "body": "Inter",
                "accent": "Space Mono",
            },
            "colors": {
                "primary": "#1A1A2E",
                "secondary": "#16213E",
                "accent": "#E94560",
                "background": "#FFFFFF",
                "text": "#1A1A2E",
                "muted": "#6B7280",
            },
            "spacing": {"base": 8, "tight": 4, "loose": 16, "section": 32},
            "border_radius": {"small": 4, "medium": 8, "large": 12},
            "shadows": {
                "subtle": "0 1px 2px rgba(0,0,0,0.05)",
                "card": "0 4px 6px rgba(0,0,0,0.07)",
            },
        },
        "consulting": {
            "name": "Premium Consulting",
            "description": "McKinsey/BCG style - authoritative and clean",
            "fonts": {
                "heading": "Playfair Display",
                "body": "Source Sans Pro",
                "accent": "Lora",
            },
            "colors": {
                "primary": "#0F172A",
                "secondary": "#334155",
                "accent": "#0EA5E9",
                "background": "#F8FAFC",
                "text": "#1E293B",
                "muted": "#64748B",
            },
            "spacing": {"base": 8, "tight": 4, "loose": 24, "section": 48},
            "border_radius": {"small": 2, "medium": 4, "large": 8},
            "shadows": {
                "subtle": "0 1px 3px rgba(0,0,0,0.1)",
                "card": "0 4px 12px rgba(0,0,0,0.08)",
            },
        },
        "investor_update": {
            "name": "Investor Update",
            "description": "Data-first, clean metrics display",
            "fonts": {
                "heading": "Sora",
                "body": "Inter",
                "accent": "JetBrains Mono",
            },
            "colors": {
                "primary": "#18181B",
                "secondary": "#27272A",
                "accent": "#10B981",
                "background": "#FAFAFA",
                "text": "#18181B",
                "muted": "#71717A",
            },
            "spacing": {"base": 8, "tight": 4, "loose": 16, "section": 32},
            "border_radius": {"small": 4, "medium": 6, "large": 8},
            "shadows": {
                "subtle": "0 1px 2px rgba(0,0,0,0.05)",
                "card": "0 2px 8px rgba(0,0,0,0.06)",
            },
        },
        "sales": {
            "name": "Sales Deck",
            "description": "Persuasive, benefit-focused design",
            "fonts": {
                "heading": "Clash Display",
                "body": "Satoshi",
                "accent": "General Sans",
            },
            "colors": {
                "primary": "#0D0D0D",
                "secondary": "#262626",
                "accent": "#FF4D4D",
                "background": "#FFFFFF",
                "text": "#0D0D0D",
                "muted": "#737373",
            },
            "spacing": {"base": 8, "tight": 4, "loose": 20, "section": 40},
            "border_radius": {"small": 4, "medium": 8, "large": 16},
            "shadows": {
                "subtle": "0 2px 4px rgba(0,0,0,0.08)",
                "card": "0 8px 24px rgba(0,0,0,0.12)",
            },
        },
        "marketing": {
            "name": "Product Launch",
            "description": "Bold, premium product aesthetic",
            "fonts": {
                "heading": "Cabinet Grotesk",
                "body": "Satoshi",
                "accent": "Space Grotesk",
            },
            "colors": {
                "primary": "#000000",
                "secondary": "#1A1A1A",
                "accent": "#6366F1",
                "background": "#FFFFFF",
                "text": "#000000",
                "muted": "#525252",
            },
            "spacing": {"base": 8, "tight": 4, "loose": 24, "section": 48},
            "border_radius": {"small": 4, "medium": 8, "large": 24},
            "shadows": {
                "subtle": "0 2px 8px rgba(0,0,0,0.08)",
                "card": "0 12px 32px rgba(0,0,0,0.12)",
            },
        },
    }

    LAYOUT_SPECS = {
        "title-hero": {
            "elements": [
                {"type": "heading", "style": "hero", "size": "64px", "align": "center"},
                {
                    "type": "subtitle",
                    "style": "subtle",
                    "size": "24px",
                    "align": "center",
                },
                {"type": "background", "style": "gradient"},
            ],
            "grid": {"cols": 1, "rows": "auto", "gap": 16},
        },
        "two-column": {
            "elements": [
                {"type": "heading", "style": "section", "size": "36px"},
                {"type": "column", "side": "left", "width": "50%"},
                {"type": "column", "side": "right", "width": "50%"},
            ],
            "grid": {"cols": 2, "rows": "auto", "gap": 24},
        },
        "bullets": {
            "elements": [
                {"type": "heading", "style": "section", "size": "36px"},
                {"type": "bullet_list", "items": 5, "icon": "disc"},
            ],
            "grid": {"cols": 1, "rows": "auto", "gap": 12},
        },
        "bullets-with-image": {
            "elements": [
                {"type": "heading", "style": "section", "size": "36px"},
                {"type": "column", "side": "left", "width": "60%"},
                {"type": "image", "side": "right", "width": "40%"},
            ],
            "grid": {"cols": 2, "rows": "auto", "gap": 24},
        },
        "chart": {
            "elements": [
                {"type": "heading", "style": "section", "size": "36px"},
                {"type": "chart_container", "height": "300px"},
                {"type": "caption", "style": "muted", "size": "14px"},
            ],
            "grid": {"cols": 1, "rows": "auto", "gap": 16},
        },
        "team-grid": {
            "elements": [
                {"type": "heading", "style": "section", "size": "36px"},
                {"type": "grid", "cols": 4, "card": "team_member"},
            ],
            "grid": {"cols": 4, "rows": "auto", "gap": 16},
        },
        "comparison": {
            "elements": [
                {"type": "heading", "style": "section", "size": "36px"},
                {"type": "comparison_table", "cols": 2},
            ],
            "grid": {"cols": 1, "rows": "auto", "gap": 24},
        },
        "kpi-dashboard": {
            "elements": [
                {"type": "heading", "style": "section", "size": "36px"},
                {"type": "kpi_cards", "cols": 4},
            ],
            "grid": {"cols": 4, "rows": "auto", "gap": 16},
        },
        "timeline": {
            "elements": [
                {"type": "heading", "style": "section", "size": "36px"},
                {"type": "timeline", "items": 5},
            ],
            "grid": {"cols": 1, "rows": "auto", "gap": 8},
        },
        "quote": {
            "elements": [
                {"type": "quote_mark", "style": "large"},
                {"type": "quote_text", "size": "28px", "style": "italic"},
                {"type": "attribution", "size": "16px"},
            ],
            "grid": {"cols": 1, "rows": "auto", "gap": 16},
        },
    }

    @property
    def agent_type(self) -> AgentType:
        return AgentType.DESIGNER

    async def execute(self) -> AgentOutput:
        """
        Execute Designer Agent - create design system and specifications.

        Steps:
        1. Get CEO output for structure and writing style
        2. Select appropriate Anti-AI-Slop preset
        3. Generate design system if custom
        4. Create layout specs for each slide
        5. Return design output
        """
        self.log_progress("Starting Designer Agent execution")

        # Get CEO output
        ceo_output = self.context.previous_outputs.get(AgentType.CEO)
        if not ceo_output or not ceo_output.success:
            return AgentOutput(
                success=False,
                agent_type=self.agent_type,
                output={},
                errors=["CEO Agent output not available"],
            )

        structure = ceo_output.output.get("structure", [])
        writing_style = ceo_output.output.get("writing_style", "general")

        # Select design preset
        design_preset = self._select_preset(writing_style)

        # Create design specifications for each slide
        slide_specs = await self._generate_slide_specs(structure, design_preset)

        # Compile design output
        design = {
            "preset": design_preset["name"],
            "preset_description": design_preset["description"],
            "fonts": design_preset["fonts"],
            "colors": design_preset["colors"],
            "spacing": design_preset["spacing"],
            "border_radius": design_preset["border_radius"],
            "shadows": design_preset["shadows"],
            "slide_specs": slide_specs,
            "global_styles": self._generate_global_styles(design_preset),
        }

        self.log_progress(f"Design system created with {len(slide_specs)} slide specs")

        return AgentOutput(
            success=True, agent_type=self.agent_type, output=design, warnings=[]
        )

    def _select_preset(self, writing_style: str) -> Dict:
        """Select appropriate Anti-AI-Slop preset based on writing style"""
        preset_map = {
            "yc_pitch": "yc_pitch",
            "analytical": "consulting",
            "consulting": "consulting",
            "investor_update": "investor_update",
            "sales": "sales",
            "marketing": "marketing",
            "general": "yc_pitch",
        }

        preset_key = preset_map.get(writing_style, "yc_pitch")
        return self.ANTI_AI_SLOP_PRESETS[preset_key]

    async def _generate_slide_specs(
        self, structure: List[Dict], preset: Dict
    ) -> List[Dict]:
        """Generate design specifications for each slide"""
        slide_specs = []

        for slide in structure:
            slide_index = slide.get("index", 0)
            layout = slide.get("layout", "bullets")
            title = slide.get("title", "")

            # Get layout spec
            layout_spec = self.LAYOUT_SPECS.get(layout, self.LAYOUT_SPECS["bullets"])

            # Generate specific spec for this slide
            spec = await self._generate_single_slide_spec(
                slide_index=slide_index,
                title=title,
                layout=layout,
                layout_spec=layout_spec,
                preset=preset,
            )

            slide_specs.append(spec)

        return slide_specs

    async def _generate_single_slide_spec(
        self,
        slide_index: int,
        title: str,
        layout: str,
        layout_spec: Dict,
        preset: Dict,
    ) -> Dict[str, Any]:
        """Generate detailed design spec for a single slide"""
        prompt = f"""Generate visual design specification for slide {slide_index}.

SLIDE: {title}
LAYOUT: {layout}

PRESET: {preset["name"]}
COLORS: {preset["colors"]}
FONTS: {preset["fonts"]}

Provide JSON:
{{
  "slide_index": {slide_index},
  "title": "{title}",
  "layout": "{layout}",
  "background": {{"type": "solid", "color": "{preset["colors"]["background"]}"}},
  "heading": {{"color": "{preset["colors"]["primary"]}", "font": "{preset["fonts"]["heading"]}"}},
  "body": {{"color": "{preset["colors"]["text"]}", "font": "{preset["fonts"]["body"]}"}},
  "accent": {{"color": "{preset["colors"]["accent"]}"}},
  "elements": [
    {{"type": "heading", "spec": "specific styling for {title}"}},
    {{"type": "content", "spec": "content area styling"}}
  ],
  "visual_notes": "specific design notes for this slide"
}}

Respond with ONLY valid JSON."""

        result = await self.call_llm_json(
            task_type=TaskType.STRUCTURED_JSON,
            prompt=prompt,
            temperature=0.3,
            max_tokens=1500,
            system_prompt="You are a presentation design expert. Create specific, non-generic design specifications. Apply Anti-AI-Slop principles: distinctive typography, purposeful color, intentional spacing.",
        )

        if result.success:
            return result.output

        # Return default spec on failure
        return {
            "slide_index": slide_index,
            "title": title,
            "layout": layout,
            "background": {"type": "solid", "color": preset["colors"]["background"]},
            "heading": {
                "color": preset["colors"]["primary"],
                "font": preset["fonts"]["heading"],
            },
            "body": {
                "color": preset["colors"]["text"],
                "font": preset["fonts"]["body"],
            },
            "accent": {"color": preset["colors"]["accent"]},
            "elements": layout_spec.get("elements", []),
            "visual_notes": "Use default preset styling",
        }

    def _generate_global_styles(self, preset: Dict) -> Dict:
        """Generate global CSS/style properties"""
        return {
            "root_variables": {
                "--color-primary": preset["colors"]["primary"],
                "--color-secondary": preset["colors"]["secondary"],
                "--color-accent": preset["colors"]["accent"],
                "--color-background": preset["colors"]["background"],
                "--color-text": preset["colors"]["text"],
                "--color-muted": preset["colors"]["muted"],
                "--font-heading": preset["fonts"]["heading"],
                "--font-body": preset["fonts"]["body"],
                "--font-accent": preset["fonts"]["accent"],
                "--spacing-base": f"{preset['spacing']['base']}px",
                "--spacing-tight": f"{preset['spacing']['tight']}px",
                "--spacing-loose": f"{preset['spacing']['loose']}px",
                "--spacing-section": f"{preset['spacing']['section']}px",
                "--radius-small": f"{preset['border_radius']['small']}px",
                "--radius-medium": f"{preset['border_radius']['medium']}px",
                "--radius-large": f"{preset['border_radius']['large']}px",
            },
            "global_css": f"""
                .slide {{ background: {preset["colors"]["background"]}; }}
                .heading {{ font-family: {preset["fonts"]["heading"]}; color: {preset["colors"]["primary"]}; }}
                .body {{ font-family: {preset["fonts"]["body"]}; color: {preset["colors"]["text"]}; }}
                .accent {{ color: {preset["colors"]["accent"]}; }}
            """,
        }
