"""
Assembler Agent - Content Assembly & Slide Generation
Agent 4: Combines research data, design specs, and content to create final slide structures.
Assembles all outputs into a coherent presentation ready for export.
"""

import json
from typing import Any, Dict, List

from app.services.llm import TaskType
from app.services.slides_new.agents.base import (
    BaseAgent,
    AgentOutput,
    AgentType,
    AgentContext,
)


class AssemblerAgent(BaseAgent):
    """
    Agent 4: Content assembly and slide generation.

    Responsibilities:
    - Combine CEO strategy, researcher data, and designer specs
    - Generate final slide content (titles, bullets, data)
    - Create slide objects with all required properties
    - Prepare for export (PPTX, HTML, PDF)
    - Handle layout-specific content formatting

    This is the "glue" that combines all agent outputs.
    """

    DEFAULT_MODEL = "deepseek-v3"
    FALLBACK_MODELS = ["mistral-medium-2505", "gpt-4o-mini"]

    @property
    def agent_type(self) -> AgentType:
        return AgentType.ASSEMBLER

    async def execute(self) -> AgentOutput:
        """
        Execute Assembler Agent - combine all outputs into final slides.

        Steps:
        1. Validate all previous outputs (CEO, Researcher, Designer)
        2. For each slide position, combine outputs
        3. Generate final slide content
        4. Create slide objects with all properties
        5. Return assembled presentation
        """
        self.log_progress("Starting Assembler Agent execution")

        # Validate all previous outputs
        validation = await self._validate_inputs()
        if not validation["valid"]:
            return AgentOutput(
                success=False,
                agent_type=self.agent_type,
                output={},
                errors=validation["errors"],
            )

        # Get all outputs
        ceo_output = self.context.previous_outputs.get(AgentType.CEO)
        researcher_output = self.context.previous_outputs.get(AgentType.RESEARCHER)
        designer_output = self.context.previous_outputs.get(AgentType.DESIGNER)

        structure = ceo_output.output.get("structure", [])
        research = researcher_output.output.get("research_items", [])
        design = designer_output.output.get("slide_specs", [])

        # Assemble slides
        assembled_slides = await self._assemble_slides(structure, research, design)

        # Create final presentation object
        presentation = {
            "metadata": {
                "topic": self.context.topic,
                "purpose": self.context.purpose,
                "audience": self.context.audience,
                "slide_count": len(assembled_slides),
                "generated_by": "AssemblerAgent",
            },
            "design_system": designer_output.output,
            "slides": assembled_slides,
            "export_options": self._get_export_options(),
        }

        self.log_progress(f"Assembled {len(assembled_slides)} slides")

        return AgentOutput(
            success=True, agent_type=self.agent_type, output=presentation, warnings=[]
        )

    async def _validate_inputs(self) -> Dict[str, Any]:
        """Validate all required inputs are present"""
        errors = []

        required_agents = [AgentType.CEO, AgentType.RESEARCHER, AgentType.DESIGNER]
        for agent_type in required_agents:
            output = self.context.previous_outputs.get(agent_type)
            if not output or not output.success:
                errors.append(f"{agent_type.value} Agent output missing or failed")

        return {"valid": len(errors) == 0, "errors": errors}

    async def _assemble_slides(
        self, structure: List[Dict], research: List[Dict], design: List[Dict]
    ) -> List[Dict]:
        """Assemble final slide content for each slide"""
        assembled = []

        for i, slide_template in enumerate(structure):
            slide_index = slide_template.get("index", i)
            title = slide_template.get("title", "")
            layout = slide_template.get("layout", "bullets")
            purpose = slide_template.get("purpose", "")

            # Get corresponding research and design
            slide_research = self._get_slide_research(slide_index, research)
            slide_design = self._get_slide_design(slide_index, design)

            # Generate final slide content
            slide = await self._generate_slide_content(
                slide_index=slide_index,
                title=title,
                layout=layout,
                purpose=purpose,
                research=slide_research,
                design=slide_design,
            )

            assembled.append(slide)

        return assembled

    def _get_slide_research(self, slide_index: int, research: List[Dict]) -> Dict:
        """Get research for specific slide"""
        for item in research:
            if item.get("slide_index") == slide_index:
                return item
        return {}

    def _get_slide_design(self, slide_index: int, design: List[Dict]) -> Dict:
        """Get design spec for specific slide"""
        for spec in design:
            if spec.get("slide_index") == slide_index:
                return spec
        return {}

    async def _generate_slide_content(
        self,
        slide_index: int,
        title: str,
        layout: str,
        purpose: str,
        research: Dict,
        design: Dict,
    ) -> Dict[str, Any]:
        """Generate final content for a single slide"""
        prompt = f"""Generate final slide content for slide {slide_index}.

SLIDE DETAILS:
- Title: {title}
- Layout: {layout}
- Purpose: {purpose}

RESEARCH DATA:
{json.dumps(research, indent=2)}

DESIGN SPEC:
{json.dumps(design, indent=2)}

TOPIC: {self.context.topic}
DESCRIPTION: {self.context.description}

Provide final slide JSON:
{{
  "index": {slide_index},
  "title": "{title}",
  "layout": "{layout}",
  "purpose": "{purpose}",
  "content": {{
    "headline": "compelling headline if needed",
    "bullets": ["point 1", "point 2", "point 3"],
    "data": {research.get("data_points", [])},
    "chart": {{"type": "bar", "data": []}},
    "quote": {{"text": "", "author": ""}}
  }},
  "design": {{
    "background": {design.get("background", {{}})},
    "heading": {design.get("heading", {{}})},
    "body": {design.get("body", {{}})},
    "accent": {design.get("accent", {{}})}
  }},
  "animation": {{"type": "fade", "duration": 0.5}},
  "notes": "speaker notes for this slide"
}}

Respond with ONLY valid JSON."""

        result = await self.call_llm_json(
            task_type=TaskType.STRUCTURED_JSON,
            prompt=prompt,
            temperature=0.4,
            max_tokens=2500,
            system_prompt="You are a presentation content specialist. Generate polished, presentation-ready content. Make bullets concise, data specific, and content compelling. Match the design system provided.",
        )

        if result.success:
            return result.output

        # Return minimal slide on failure
        return {
            "index": slide_index,
            "title": title,
            "layout": layout,
            "purpose": purpose,
            "content": {
                "headline": "",
                "bullets": [],
                "data": [],
                "chart": None,
                "quote": None,
            },
            "design": {
                "background": design.get("background", {}),
                "heading": design.get("heading", {}),
                "body": design.get("body", {}),
                "accent": design.get("accent", {}),
            },
            "animation": {"type": "fade", "duration": 0.5},
            "notes": "",
        }

    def _get_export_options(self) -> Dict[str, Any]:
        """Get export configuration options"""
        return {
            "pptx": {
                "enabled": True,
                "options": {
                    "slide_width": 13.333,  # 16:9 ratio
                    "slide_height": 7.5,
                    "margin": 0.5,
                    "title_font": "Arial",
                    "body_font": "Arial",
                },
            },
            "html": {
                "enabled": True,
                "options": {
                    "responsive": True,
                    "aspect_ratio": "16:9",
                    "include_animations": True,
                    "theme": "custom",
                },
            },
            "pdf": {
                "enabled": True,
                "options": {
                    "quality": "high",
                    "include_notes": False,
                },
            },
        }
