"""
CEO Agent - Strategy & Presentation Structure
Agent 1: Creates presentation strategy, determines archetype, creates structured outline.
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


class CEOAgent(BaseAgent):
    """
    Agent 1: Strategic planning for presentations.

    Responsibilities:
    - Determine presentation archetype (YC seed, Series A, consulting, etc.)
    - Create structured slide outline with layouts
    - Define narrative arc and writing style
    - Set purpose and audience context

    Uses YC/Sequoia pitch deck best practices for investor presentations.
    """

    DEFAULT_MODEL = "kimi-k2-thinking"
    FALLBACK_MODELS = ["phi-4-reasoning", "deepseek-v3"]

    # YC/Sequoia proven pitch deck structures
    ARCHETYPE_TEMPLATES = {
        "yc_seed": {
            "name": "YC Seed Pitch",
            "description": "10-slide YC format for seed rounds",
            "slides": [
                {
                    "index": 0,
                    "layout": "title-hero",
                    "purpose": "One-liner introduction",
                },
                {
                    "index": 1,
                    "layout": "two-column",
                    "purpose": "Problem - quantified pain",
                },
                {
                    "index": 2,
                    "layout": "bullets",
                    "purpose": "Solution - what you built",
                },
                {"index": 3, "layout": "bullets", "purpose": "Why Now - market timing"},
                {"index": 4, "layout": "chart", "purpose": "Market - TAM/SAM/SOM"},
                {"index": 5, "layout": "bullets", "purpose": "Product - how it works"},
                {
                    "index": 6,
                    "layout": "bullets",
                    "purpose": "Business Model - revenue",
                },
                {"index": 7, "layout": "chart", "purpose": "Traction - growth"},
                {"index": 8, "layout": "team-grid", "purpose": "Team - why you"},
                {"index": 9, "layout": "two-column", "purpose": "Ask - funding ask"},
            ],
        },
        "series_a": {
            "name": "Series A Pitch",
            "description": "12-slide Sequoia format for Series A",
            "slides": [
                {"index": 0, "layout": "title-hero", "purpose": "Company Purpose"},
                {
                    "index": 1,
                    "layout": "two-column",
                    "purpose": "Problem - market pain",
                },
                {"index": 2, "layout": "bullets", "purpose": "Solution"},
                {"index": 3, "layout": "bullets", "purpose": "Why Now"},
                {"index": 4, "layout": "chart", "purpose": "Market Size"},
                {
                    "index": 5,
                    "layout": "bullets-with-image",
                    "purpose": "Product Deep Dive",
                },
                {"index": 6, "layout": "bullets", "purpose": "Business Model"},
                {"index": 7, "layout": "chart", "purpose": "Traction"},
                {"index": 8, "layout": "comparison", "purpose": "Competition"},
                {"index": 9, "layout": "team-grid", "purpose": "Team"},
                {"index": 10, "layout": "kpi-dashboard", "purpose": "Financials"},
                {"index": 11, "layout": "two-column", "purpose": "The Ask"},
            ],
        },
        "consulting": {
            "name": "Consulting Deck",
            "description": "15-slide consulting/strategy format",
            "slides": [
                {"index": 0, "layout": "title-hero", "purpose": "Title Slide"},
                {"index": 1, "layout": "bullets", "purpose": "Executive Summary"},
                {
                    "index": 2,
                    "layout": "two-column",
                    "purpose": "Current State Assessment",
                },
                {"index": 3, "layout": "chart", "purpose": "Data Analysis"},
                {
                    "index": 4,
                    "layout": "bullets",
                    "purpose": "Opportunity Identification",
                },
                {"index": 5, "layout": "two-column", "purpose": "Recommendations"},
                {"index": 6, "layout": "timeline", "purpose": "Implementation Roadmap"},
                {"index": 7, "layout": "chart", "purpose": "Impact Projections"},
                {
                    "index": 8,
                    "layout": "comparison",
                    "purpose": "Alternative Approaches",
                },
                {"index": 9, "layout": "kpi-dashboard", "purpose": "Key Metrics"},
                {"index": 10, "layout": "bullets", "purpose": "Risk Mitigation"},
                {"index": 11, "layout": "team-grid", "purpose": "Team & Capabilities"},
                {"index": 12, "layout": "chart", "purpose": "Investment Required"},
                {"index": 13, "layout": "bullets", "purpose": "Next Steps"},
                {"index": 14, "layout": "title-hero", "purpose": "Closing"},
            ],
        },
        "quarterly_report": {
            "name": "Quarterly Report",
            "description": "10-slide quarterly business review",
            "slides": [
                {"index": 0, "layout": "title-hero", "purpose": "Cover - Period ID"},
                {"index": 1, "layout": "kpi-dashboard", "purpose": "Key Highlights"},
                {"index": 2, "layout": "chart", "purpose": "Revenue Performance"},
                {"index": 3, "layout": "chart", "purpose": "Growth Metrics"},
                {"index": 4, "layout": "bullets", "purpose": "Key Wins"},
                {"index": 5, "layout": "bullets", "purpose": "Challenges"},
                {"index": 6, "layout": "chart", "purpose": "Burn & Runway"},
                {"index": 7, "layout": "bullets", "purpose": "Product Updates"},
                {"index": 8, "layout": "bullets", "purpose": "Team Updates"},
                {"index": 9, "layout": "bullets", "purpose": "How Investors Can Help"},
            ],
        },
        "sales": {
            "name": "Sales Deck",
            "description": "8-slide sales/presentation deck",
            "slides": [
                {"index": 0, "layout": "title-hero", "purpose": "Company Intro"},
                {
                    "index": 1,
                    "layout": "two-column",
                    "purpose": "Challenge/Pain Points",
                },
                {"index": 2, "layout": "bullets", "purpose": "Solution Overview"},
                {"index": 3, "layout": "comparison", "purpose": "Before/After"},
                {"index": 4, "layout": "kpi-dashboard", "purpose": "Results/Metrics"},
                {"index": 5, "layout": "quote", "purpose": "Testimonial"},
                {"index": 6, "layout": "bullets", "purpose": "Pricing/Tiers"},
                {"index": 7, "layout": "title-hero", "purpose": "Call to Action"},
            ],
        },
        "product_launch": {
            "name": "Product Launch",
            "description": "10-slide product announcement",
            "slides": [
                {"index": 0, "layout": "title-hero", "purpose": "Announce Product"},
                {"index": 1, "layout": "two-column", "purpose": "Problem Gap"},
                {
                    "index": 2,
                    "layout": "bullets-with-image",
                    "purpose": "Product Reveal",
                },
                {"index": 3, "layout": "bullets", "purpose": "Key Features"},
                {"index": 4, "layout": "comparison", "purpose": "Differentiation"},
                {"index": 5, "layout": "kpi-dashboard", "purpose": "Beta Results"},
                {"index": 6, "layout": "quote", "purpose": "Early Feedback"},
                {"index": 7, "layout": "bullets", "purpose": "Pricing"},
                {"index": 8, "layout": "timeline", "purpose": "Roadmap"},
                {"index": 9, "layout": "title-hero", "purpose": "CTA"},
            ],
        },
    }

    WRITING_STYLES = {
        "yc_seed": "yc_pitch",
        "series_a": "analytical",
        "consulting": "consulting",
        "quarterly_report": "investor_update",
        "sales": "sales",
        "product_launch": "marketing",
    }

    LAYOUT_TYPES = [
        "title-hero",
        "two-column",
        "bullets",
        "bullets-with-image",
        "chart",
        "team-grid",
        "comparison",
        "kpi-dashboard",
        "timeline",
        "quote",
    ]

    @property
    def agent_type(self) -> AgentType:
        return AgentType.CEO

    async def execute(self) -> AgentOutput:
        """
        Execute CEO Agent - create presentation strategy.

        Steps:
        1. Determine archetype based on purpose/audience
        2. Get template structure
        3. Generate detailed outline with AI
        4. Determine writing style
        5. Return strategy output
        """
        self.log_progress("Starting CEO Agent execution")

        # Step 1: Determine archetype
        archetype = self._determine_archetype(
            purpose=self.context.purpose, audience=self.context.audience
        )

        self.log_progress(f"Determined archetype: {archetype}")

        # Step 2: Get template structure
        template = self.ARCHETYPE_TEMPLATES.get(
            archetype, self.ARCHETYPE_TEMPLATES["sales"]
        )

        # Step 3: Generate detailed outline with AI
        outline = await self._generate_detailed_outline(
            archetype=archetype, template=template
        )

        # If outline generation failed, use template structure
        if not outline:
            outline = template["slides"]

        # Step 4: Determine writing style
        writing_style = self.WRITING_STYLES.get(archetype, "general")

        # Step 5: Build strategy output
        strategy = {
            "archetype": archetype,
            "archetype_name": template["name"],
            "slide_count": len(outline),
            "structure": outline,
            "writing_style": writing_style,
            "purpose": self.context.purpose,
            "audience": self.context.audience,
            "topic": self.context.topic,
        }

        self.log_progress(f"Strategy created with {len(outline)} slides")

        return AgentOutput(
            success=True, agent_type=self.agent_type, output=strategy, warnings=[]
        )

    def _determine_archetype(self, purpose: str, audience: str) -> str:
        """
        Determine presentation archetype based on purpose and audience.

        Args:
            purpose: The purpose of the presentation (fundraising, sales, etc.)
            audience: The target audience (investors, clients, etc.)

        Returns:
            Archetype string (yc_seed, series_a, etc.)
        """
        purpose_lower = purpose.lower() if purpose else ""
        audience_lower = audience.lower() if audience else ""

        # Fundraising/Pitch scenarios
        if any(
            word in purpose_lower
            for word in ["fundrais", "pitch", "investor", "seed", "series"]
        ):
            if any(
                word in audience_lower
                for word in ["seed", "angel", "pre-seed", "early"]
            ):
                return "yc_seed"
            return "series_a"

        # Consulting/Strategy
        if any(
            word in purpose_lower
            for word in ["consulting", "strategy", "advisory", "assessment"]
        ):
            return "consulting"

        # Reporting
        if any(
            word in purpose_lower
            for word in ["report", "quarterly", "monthly", "update", "review"]
        ):
            return "quarterly_report"

        # Sales/Demo
        if any(
            word in purpose_lower
            for word in ["sales", "demo", "proposal", "prospect", "client"]
        ):
            return "sales"

        # Product launch
        if any(
            word in purpose_lower
            for word in ["launch", "announce", "release", "reveal"]
        ):
            return "product_launch"

        # Default to sales deck
        return "sales"

    async def _generate_detailed_outline(
        self, archetype: str, template: Dict
    ) -> List[Dict]:
        """
        Generate detailed slide outline using AI.

        Creates specific, non-generic slide titles and purposes
        based on the topic and presentation type.
        """
        prompt = f"""Create a detailed outline for a {self.ARCHETYPE_TEMPLATES[archetype]["name"]} presentation.

TOPIC: {self.context.topic}
DESCRIPTION: {self.context.description}
AUDIENCE: {self.context.audience}
PURPOSE: {self.context.purpose}

For each slide provide (as JSON array):
- index: slide number (0-based)
- title: SPECIFIC title (not generic like "The Problem")
- layout: one of: {", ".join(self.LAYOUT_TYPES)}
- purpose: what this slide achieves (specific, not generic)
- content_hints: what content should go here

Example output format:
[
  {{"index": 0, "title": "NeuralScale - AI Infrastructure for Next Billion Params", "layout": "title-hero", "purpose": "One-liner value prop", "content_hints": "Company name, tagline, founder"}},
  {{"index": 1, "title": "The $50B Infrastructure Crisis", "layout": "two-column", "purpose": "Quantify market pain", "content_hints": "GPU shortage stats, cost overruns"}}
]

Make titles SPECIFIC to the topic - not generic.
Respond with ONLY valid JSON array, no explanation."""

        result = await self.call_llm_json(
            task_type=TaskType.STRUCTURED_JSON,
            prompt=prompt,
            temperature=0.4,
            max_tokens=2500,
            system_prompt="You are an expert pitch deck strategist. Create specific, compelling slide titles that grab investor attention. Avoid generic titles. Use numbers, specific claims, and clear value propositions.",
        )

        if result.success:
            output_data = result.output
            # Ensure it's a list
            if isinstance(output_data, list):
                return output_data
            elif isinstance(output_data, dict) and "slides" in output_data:
                return output_data["slides"]
            else:
                self.log_progress(
                    f"Unexpected output format: {type(output_data)}", "warning"
                )
                return []

        # Fallback to template structure
        self.log_progress(
            f"Outline generation failed, using template structure", "warning"
        )
        return template.get("slides", [])


class CEOAgentWithTemplates(CEOAgent):
    """
    Extended CEO Agent with additional template types.
    For users who need more template options.
    """

    # Extended templates beyond core set
    EXTENDED_TEMPLATES = {
        "enterprise_sales": {
            "name": "Enterprise Sales",
            "slides": [
                {"index": 0, "layout": "title-hero", "purpose": "Intro"},
                {"index": 1, "layout": "bullets", "purpose": "Agenda"},
                {
                    "index": 2,
                    "layout": "two-column",
                    "purpose": "Understanding Your Challenges",
                },
                {"index": 3, "layout": "bullets", "purpose": "Our Solution"},
                {"index": 4, "layout": "bullets-with-image", "purpose": "Product Demo"},
                {"index": 5, "layout": "chart", "purpose": "Case Study"},
                {"index": 6, "layout": "comparison", "purpose": "Why Us"},
                {"index": 7, "layout": "bullets", "purpose": "Pricing"},
                {"index": 8, "layout": "bullets", "purpose": "Next Steps"},
                {"index": 9, "layout": "title-hero", "purpose": "Close"},
            ],
        },
        "investor_update": {
            "name": "Monthly Investor Update",
            "slides": [
                {"index": 0, "layout": "title-hero", "purpose": "Period Cover"},
                {"index": 1, "layout": "kpi-dashboard", "purpose": "Traffic Light"},
                {"index": 2, "layout": "chart", "purpose": "Revenue"},
                {"index": 3, "layout": "chart", "purpose": "Growth"},
                {"index": 4, "layout": "bullets", "purpose": "Wins"},
                {"index": 5, "layout": "bullets", "purpose": "Challenges"},
                {"index": 6, "layout": "chart", "purpose": "Runway"},
                {"index": 7, "layout": "bullets", "purpose": "Product"},
                {"index": 8, "layout": "bullets", "purpose": "Team"},
                {"index": 9, "layout": "bullets", "purpose": "Asks"},
            ],
        },
        "board_deck": {
            "name": "Board Presentation",
            "slides": [
                {"index": 0, "layout": "title-hero", "purpose": "Company Update"},
                {"index": 1, "layout": "kpi-dashboard", "purpose": "Executive Summary"},
                {"index": 2, "layout": "chart", "purpose": "Financials"},
                {"index": 3, "layout": "chart", "purpose": "Metrics"},
                {"index": 4, "layout": "bullets", "purpose": "Strategy"},
                {"index": 5, "layout": "bullets", "purpose": "Operations"},
                {"index": 6, "layout": "team-grid", "purpose": "Team"},
                {"index": 7, "layout": "bullets", "purpose": "Risks"},
                {"index": 8, "layout": "timeline", "purpose": "Forward Looking"},
                {"index": 9, "layout": "bullets", "purpose": "Decisions Needed"},
                {"index": 10, "layout": "title-hero", "purpose": "Close"},
            ],
        },
        "academic_defense": {
            "name": "PhD/Academic Defense",
            "slides": [
                {"index": 0, "layout": "title-hero", "purpose": "Title"},
                {"index": 1, "layout": "bullets", "purpose": "Introduction"},
                {"index": 2, "layout": "bullets", "purpose": "Literature Review"},
                {"index": 3, "layout": "bullets", "purpose": "Methodology"},
                {"index": 4, "layout": "chart", "purpose": "Results"},
                {"index": 5, "layout": "bullets", "purpose": "Analysis"},
                {"index": 6, "layout": "bullets", "purpose": "Discussion"},
                {"index": 7, "layout": "bullets", "purpose": "Conclusions"},
                {"index": 8, "layout": "bullets", "purpose": "Future Work"},
                {"index": 9, "layout": "title-hero", "purpose": "Q&A"},
            ],
        },
        "mvp_pitch": {
            "name": "MVP Pitch",
            "slides": [
                {"index": 0, "layout": "title-hero", "purpose": "One-liner"},
                {"index": 1, "layout": "two-column", "purpose": "Problem"},
                {"index": 2, "layout": "bullets", "purpose": "Solution Demo"},
                {"index": 3, "layout": "chart", "purpose": "Early Traction"},
                {"index": 4, "layout": "bullets", "purpose": "Ask"},
            ],
        },
    }

    async def execute(self) -> AgentOutput:
        """Extended execute with more template options"""
        # Check for extended templates first
        purpose_lower = self.context.purpose.lower() if self.context.purpose else ""

        if "enterprise" in purpose_lower or "b2b" in purpose_lower:
            self.ARCHETYPE_TEMPLATES.update(self.EXTENDED_TEMPLATES)

        return await super().execute()
