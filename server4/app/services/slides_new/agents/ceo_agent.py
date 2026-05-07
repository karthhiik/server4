"""
CEO Agent — V7 Phase 2
Agent 1: Strategic planning for presentations.

Creates presentation strategy, determines archetype, creates structured outline.
Uses Kimi-K2-Thinking for deep reasoning about narrative structure.

Writes to Context Board: strategy section
"""

import json
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import structlog

from app.services.llm import TaskType
from app.services.slides_new.agents.base import (
    BaseAgent,
    AgentOutput,
    AgentType,
    AgentContext,
)
from app.services.slides_new.agents.protocols import (
    StrategyData,
    ArchetypeType,
    WritingStyle,
    SlideStructure,
)

if TYPE_CHECKING:
    from app.services.context_board import ContextBoard

logger = structlog.get_logger()


class CEOAgent(BaseAgent):
    """
    Agent 1: Strategic planning for presentations - V7 Phase 2.

    Responsibilities:
    - Determine presentation archetype (YC seed, Series A, consulting, etc.)
    - Create structured slide outline with layouts
    - Define narrative arc and writing style
    - Set purpose and audience context
    - Write strategy to Context Board
    - Support HITL checkpoint for narrative approval

    Uses Kimi-K2-Thinking for deep reasoning about narrative structure.
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
        3. Generate detailed outline with AI (using Kimi-K2-Thinking)
        4. Generate narrative arc and key message
        5. Determine writing style
        6. Build strategy and write to Context Board
        7. Prepare HITL checkpoint data (if not in fast mode)
        """
        self.log_progress("Starting CEO Agent execution")
        self._board_writes = []

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
        target_count = self.context.slide_count or 10
        outline = await self._generate_detailed_outline(
            archetype=archetype, template=template, target_count=target_count
        )

        # If outline generation failed, use template structure
        if not outline:
            outline = template["slides"]

        # Step 3b: Adapt outline to exact user-requested count
        outline = self._adapt_outline_to_count(outline, target_count)

        # Step 4: Generate narrative arc and key message
        narrative_result = await self._generate_narrative_arc(archetype, outline)
        narrative_arc = narrative_result.get("narrative_arc", "Standard presentation flow")
        key_message = narrative_result.get("key_message", self.context.topic)

        # Step 5: Determine writing style
        writing_style_str = self.WRITING_STYLES.get(archetype, "general")
        try:
            writing_style = WritingStyle(writing_style_str)
        except ValueError:
            writing_style = WritingStyle.GENERAL

        # Step 6: Build strategy data
        try:
            archetype_enum = ArchetypeType(archetype)
        except ValueError:
            archetype_enum = ArchetypeType.SALES

        strategy_data = StrategyData(
            archetype=archetype_enum,
            archetype_name=template["name"],
            narrative_arc=narrative_arc,
            target_audience=self.context.audience,
            writing_style=writing_style,
            slide_count=target_count,
            structure=outline,
            key_message=key_message,
            success_criteria=self._get_success_criteria(archetype),
        )

        # Step 7: Write to Context Board
        if self.protocol:
            await self.protocol.write_strategy(strategy_data, agent="ceo")
            self._board_writes.extend([
                "strategy.archetype",
                "strategy.archetype_name",
                "strategy.narrative_arc",
                "strategy.target_audience",
                "strategy.writing_style",
                "strategy.slide_count",
                "strategy.structure",
                "strategy.key_message",
            ])

        # Step 8: Prepare HITL checkpoint (if not fast mode)
        hitl_checkpoint = None
        if not self.context.fast_mode:
            hitl_checkpoint = {
                "gate": "narrative_approval",
                "data": {
                    "archetype": archetype,
                    "archetype_name": template["name"],
                    "slide_count": target_count,
                    "outline_preview": outline[:5],  # First 5 slides for preview
                    "narrative_arc": narrative_arc,
                    "key_message": key_message,
                },
                "awaiting_approval": True,
            }

        # Build output dict for backwards compatibility
        strategy_dict = {
            "archetype": archetype,
            "archetype_name": template["name"],
            "slide_count": target_count,
            "structure": outline,
            "writing_style": writing_style_str,
            "purpose": self.context.purpose,
            "audience": self.context.audience,
            "topic": self.context.topic,
            "narrative_arc": narrative_arc,
            "key_message": key_message,
        }

        self.log_progress(f"Strategy created with {len(outline)} slides")

        return AgentOutput(
            success=True,
            agent_type=self.agent_type,
            output=strategy_dict,
            context_board_writes=self._board_writes,
            hitl_checkpoint=hitl_checkpoint,
        )

    async def _generate_narrative_arc(
        self, archetype: str, outline: List[Dict]
    ) -> Dict[str, str]:
        """
        Generate the narrative arc and key message using AI.
        Uses deep reasoning for compelling storytelling.
        """
        slide_titles = [s.get("title", s.get("purpose", "")) for s in outline]

        prompt = f"""Analyze this presentation structure and create a compelling narrative arc.

PRESENTATION TYPE: {archetype}
TOPIC: {self.context.topic}
DESCRIPTION: {self.context.description}
AUDIENCE: {self.context.audience}
PURPOSE: {self.context.purpose}

SLIDE TITLES/PURPOSES:
{json.dumps(slide_titles, indent=2)}

## THINK STEP BY STEP:
1. Identify the single transformative insight this presentation must convey.
2. Define the emotional journey: curiosity → tension → relief → conviction → action.
3. Map each slide to one stage of that journey.
4. Verify the "bar test": could you explain the key message in one sentence at a noisy bar?
5. Check the "so what?" test: after every claim, ask "so what?" — the arc must answer it.

## NARRATIVE FRAMEWORKS (pick the best fit):
- **Problem-Solution-Proof**: Pain → Fix → Evidence → Ask (best for YC/seed)
- **Situation-Complication-Resolution**: Status quo → Disruption → Our answer (best for consulting)
- **Before-After-Bridge**: World without us → World with us → How we bridge it (best for sales)
- **Hero's Journey**: Challenge → Discovery → Transformation → Return with proof (best for product launch)

Create a JSON response with:
{{
  "narrative_arc": "A 2-3 sentence description of the story flow. Start with [hook], build through [problem/opportunity], [solution], [evidence], and end with [call to action].",
  "key_message": "The single most important takeaway in one sentence. This is what the audience should remember.",
  "emotional_journey": ["curiosity", "tension", "relief", "conviction", "action"],
  "framework_used": "problem-solution-proof|situation-complication-resolution|before-after-bridge|heros-journey"
}}

Make it compelling and specific to the topic, not generic.
If you cannot determine a compelling arc from the slides, state why and propose a reordering.
Respond with ONLY valid JSON."""

        result = await self.call_llm_json(
            task_type=TaskType.OUTLINE_PLANNING,
            prompt=prompt,
            temperature=0.5,
            max_tokens=800,
            system_prompt="You are a master storyteller and pitch strategist who has coached 500+ YC founders and designed decks that raised $2B+ collectively. You think in narrative arcs, not bullet points. Every presentation is a story — your job is to find the emotional spine. Apply the 'Pixar pitch' structure: Once upon a time → Every day → One day → Because of that → Until finally.",
        )

        if result.success and isinstance(result.output, dict):
            return result.output

        return {
            "narrative_arc": f"Introduction → Problem → Solution → Evidence → Call to Action",
            "key_message": self.context.topic,
        }

    def _get_success_criteria(self, archetype: str) -> List[str]:
        """Get success criteria based on archetype"""
        criteria_map = {
            "yc_seed": [
                "Clear one-liner value proposition",
                "Quantified problem with market size",
                "Unique insight or solution differentiation",
                "Early traction or validation signals",
                "Credible team-market fit",
            ],
            "series_a": [
                "Strong product-market fit evidence",
                "Clear unit economics",
                "Scalable go-to-market strategy",
                "Competitive moat articulation",
                "Experienced team with execution track record",
            ],
            "consulting": [
                "Clear problem definition",
                "Data-driven insights",
                "Actionable recommendations",
                "Implementation roadmap",
                "Risk mitigation plan",
            ],
            "sales": [
                "Pain point resonance",
                "Clear ROI articulation",
                "Social proof/testimonials",
                "Easy next steps",
            ],
        }
        return criteria_map.get(archetype, ["Clear message", "Compelling visuals", "Strong call to action"])

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

    # ---- Supplementary slide topics for extending outlines beyond template size ----
    SUPPLEMENTARY_SLIDE_POOL = [
        {"layout": "bullets", "purpose": "Why Now - Market Timing"},
        {"layout": "chart", "purpose": "Case Study / Success Story"},
        {"layout": "two-column", "purpose": "Go-to-Market Strategy"},
        {"layout": "kpi-dashboard", "purpose": "Key Performance Metrics"},
        {"layout": "bullets", "purpose": "Product Demo / Features Deep Dive"},
        {"layout": "comparison", "purpose": "Competitive Landscape"},
        {"layout": "timeline", "purpose": "Product Roadmap"},
        {"layout": "chart", "purpose": "Financial Projections"},
        {"layout": "bullets", "purpose": "Partnerships & Ecosystem"},
        {"layout": "quote", "purpose": "Customer Testimonial"},
        {"layout": "bullets", "purpose": "Risk Analysis & Mitigation"},
        {"layout": "chart", "purpose": "Unit Economics"},
        {"layout": "two-column", "purpose": "Market Expansion Plans"},
        {"layout": "bullets", "purpose": "Technology Architecture"},
        {"layout": "kpi-dashboard", "purpose": "Operational Metrics"},
        {"layout": "bullets-with-image", "purpose": "User Journey"},
        {"layout": "bullets", "purpose": "Appendix"},
    ]

    def _adapt_outline_to_count(
        self, outline: List[Dict], target_count: int
    ) -> List[Dict]:
        """
        Adapt an outline to the exact number requested by the user.

        - If outline is longer: keep title (first) and ask/close (last), trim middle.
        - If outline is shorter: extend with supplementary slides.
        - Always re-index afterwards.
        """
        if len(outline) == target_count:
            return outline

        if len(outline) > target_count:
            # Keep first slide (title) and last slide (ask/close),
            # pick the strongest middle slides to fill the gap.
            if target_count <= 1:
                outline = outline[:target_count]
            elif target_count == 2:
                outline = [outline[0], outline[-1]]
            else:
                middle_budget = target_count - 2
                outline = [outline[0]] + outline[1:-1][:middle_budget] + [outline[-1]]
        else:
            # Need more slides — pull from supplementary pool
            used_purposes = {s.get("purpose", "").lower() for s in outline}
            pool = [
                s
                for s in self.SUPPLEMENTARY_SLIDE_POOL
                if s["purpose"].lower() not in used_purposes
            ]
            # Insert supplementary slides before the last slide (ask/close)
            insert_pos = max(len(outline) - 1, 0)
            needed = target_count - len(outline)
            for i in range(needed):
                slide = pool[i % len(pool)] if pool else {
                    "layout": "bullets",
                    "purpose": f"Additional Content {i + 1}",
                }
                outline.insert(insert_pos + i, dict(slide))

        # Re-index all slides
        for idx, slide in enumerate(outline):
            slide["index"] = idx

        return outline

    async def _generate_detailed_outline(
        self, archetype: str, template: Dict, target_count: int = 10
    ) -> List[Dict]:
        """
        Generate detailed slide outline using AI.

        Creates specific, non-generic slide titles and purposes
        based on the topic and presentation type.
        Instructs the LLM to produce exactly `target_count` slides.
        """
        prompt = f"""Create a detailed outline for a {self.ARCHETYPE_TEMPLATES[archetype]["name"]} presentation.

TOPIC: {self.context.topic}
DESCRIPTION: {self.context.description}
AUDIENCE: {self.context.audience}
PURPOSE: {self.context.purpose}
SLIDE COUNT: Generate EXACTLY {target_count} slides. Not more, not fewer.

## THINK STEP BY STEP:
1. What is the ONE thing the audience must believe after this presentation?
2. What evidence would make a skeptic believe it?
3. What is the logical order to build that belief?
4. Which slides are "foundation" (must come first) vs "payoff" (earn the ask)?
5. Where does the audience's attention peak? Place your strongest content there.

## YC/SEQUOIA PITCH DECK PRINCIPLES:
- Slide 1 must pass the "5-second test": can someone understand your company in 5 seconds?
- Problem slide: quantify the pain ($X lost, Y hours wasted, Z% failure rate)
- Solution slide: show, don't tell — product screenshots > descriptions
- Market slide: bottom-up TAM only (# customers × price point), never top-down handwaving
- Traction slide: show velocity (MoM growth), not just totals
- Team slide: why THIS team for THIS problem — domain expertise > pedigree
- Ask slide: specific amount, specific use of funds, specific milestone it unlocks

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
            system_prompt="You are an expert pitch deck strategist who has reviewed 10,000+ decks for YC, Sequoia, and a16z. You know that the best decks have: (1) specific titles with numbers, not generic labels, (2) a clear 'aha moment' by slide 3, (3) data that makes the market feel inevitable, and (4) an ask that feels like a privilege, not a request. Create titles that a founder would be proud to present. Avoid corporate jargon. Write like a human, not a committee.",
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
