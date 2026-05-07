"""
Layout Agent — V7 Phase 2
Agent 8: Per-slide layout optimization using spatial reasoning.

Uses GPT-4o or Phi-4-reasoning-vision for:
- Analyzing content and selecting optimal layout rules
- Grid-based positioning of elements
- Content measurement and truncation decisions
- Responsive design considerations

Writes to Context Board: layout section
"""

import json
from typing import Any, Dict, List, Optional

import structlog

from app.services.llm import TaskType
from app.services.slides_new.agents.base import (
    BaseAgent,
    AgentOutput,
    AgentType,
    AgentContext,
)
from app.services.slides_new.agents.protocols import (
    LayoutData,
    SlideLayout,
    GridSpec,
    ContentMeasurement,
    LayoutRuleName,
)

logger = structlog.get_logger()


# Layout rule definitions with grid specifications
LAYOUT_RULES: Dict[str, Dict[str, Any]] = {
    "single_column_center": {
        "description": "Single centered column for simple content",
        "grid": {"columns": 1, "alignment": "center"},
        "best_for": ["title", "quote", "single-focus"],
        "max_elements": 3,
    },
    "two_column_equal": {
        "description": "Two equal columns for comparison or balanced content",
        "grid": {"columns": 2, "ratio": "50:50"},
        "best_for": ["comparison", "before-after", "dual-content"],
        "max_elements": 6,
    },
    "two_column_60_40": {
        "description": "Asymmetric two columns - main content left, supporting right",
        "grid": {"columns": 2, "ratio": "60:40"},
        "best_for": ["content-with-image", "text-heavy"],
        "max_elements": 5,
    },
    "three_column": {
        "description": "Three equal columns for triple comparison or features",
        "grid": {"columns": 3, "ratio": "33:33:33"},
        "best_for": ["features", "triple-comparison", "team-3"],
        "max_elements": 9,
    },
    "hero_with_subtitle": {
        "description": "Large title with subtitle below - for title slides",
        "grid": {"columns": 1, "title_size": "xl", "subtitle_size": "md"},
        "best_for": ["title-slide", "section-divider"],
        "max_elements": 2,
    },
    "content_with_image_right": {
        "description": "Text on left, image on right",
        "grid": {"columns": 2, "ratio": "55:45", "image_position": "right"},
        "best_for": ["product-showcase", "feature-highlight"],
        "max_elements": 4,
    },
    "content_with_image_left": {
        "description": "Image on left, text on right",
        "grid": {"columns": 2, "ratio": "45:55", "image_position": "left"},
        "best_for": ["visual-first", "case-study"],
        "max_elements": 4,
    },
    "grid_2x2": {
        "description": "2x2 grid for four equal items",
        "grid": {"columns": 2, "rows": 2},
        "best_for": ["four-features", "matrix", "quad-comparison"],
        "max_elements": 4,
    },
    "grid_3x2": {
        "description": "3x2 grid for six items",
        "grid": {"columns": 3, "rows": 2},
        "best_for": ["six-features", "team-6", "process-6-steps"],
        "max_elements": 6,
    },
    "grid_2x3": {
        "description": "2x3 grid for six items (taller)",
        "grid": {"columns": 2, "rows": 3},
        "best_for": ["six-features-vertical", "timeline-6"],
        "max_elements": 6,
    },
    "timeline_horizontal": {
        "description": "Horizontal timeline for process or milestones",
        "grid": {"columns": "auto", "direction": "horizontal"},
        "best_for": ["process", "roadmap", "milestones"],
        "max_elements": 7,
    },
    "timeline_vertical": {
        "description": "Vertical timeline for detailed process",
        "grid": {"columns": 1, "direction": "vertical"},
        "best_for": ["detailed-timeline", "history"],
        "max_elements": 5,
    },
    "kpi_dashboard": {
        "description": "Dashboard layout with key metrics",
        "grid": {"columns": "auto", "item_type": "metric"},
        "best_for": ["metrics", "kpis", "numbers-highlight"],
        "max_elements": 6,
    },
    "team_grid": {
        "description": "Grid for team member profiles",
        "grid": {"columns": "auto", "item_type": "person"},
        "best_for": ["team", "advisors", "investors"],
        "max_elements": 8,
    },
    "comparison_side_by_side": {
        "description": "Side-by-side comparison with vs divider",
        "grid": {"columns": 2, "ratio": "50:50", "divider": True},
        "best_for": ["vs-comparison", "old-vs-new", "competitor"],
        "max_elements": 8,
    },
    "quote_centered": {
        "description": "Centered quote with attribution",
        "grid": {"columns": 1, "alignment": "center", "item_type": "quote"},
        "best_for": ["testimonial", "quote", "callout"],
        "max_elements": 2,
    },
    "full_bleed_image": {
        "description": "Full-screen image with overlay text",
        "grid": {"columns": 1, "image": "background"},
        "best_for": ["hero-image", "emotional-impact", "visual-break"],
        "max_elements": 2,
    },
}

# Map from slide layout type to best layout rules
LAYOUT_TYPE_TO_RULES: Dict[str, List[str]] = {
    "title-hero": ["hero_with_subtitle", "full_bleed_image"],
    "two-column": ["two_column_equal", "two_column_60_40"],
    "bullets": ["single_column_center", "two_column_60_40"],
    "bullets-with-image": ["content_with_image_right", "content_with_image_left"],
    "chart": ["two_column_60_40", "single_column_center"],
    "team-grid": ["team_grid", "grid_3x2", "grid_2x2"],
    "comparison": ["comparison_side_by_side", "two_column_equal"],
    "kpi-dashboard": ["kpi_dashboard", "grid_2x2"],
    "timeline": ["timeline_horizontal", "timeline_vertical"],
    "quote": ["quote_centered", "single_column_center"],
}


class LayoutAgent(BaseAgent):
    """
    Agent 8: Per-slide layout optimization.

    Responsibilities:
    - Analyze content for each slide and select optimal layout rule
    - Calculate grid specifications and element positions
    - Measure content and determine truncation needs
    - Ensure visual consistency across slides
    - Write layout decisions to Context Board

    Uses GPT-4o or Phi-4-reasoning for spatial reasoning.
    """

    DEFAULT_MODEL = "gpt-4o-mini"  # Fast and good at structured output
    FALLBACK_MODELS = ["phi-4-reasoning", "deepseek-v3", "cf-qwen"]

    @property
    def agent_type(self) -> AgentType:
        return AgentType.LAYOUT

    async def execute(self) -> AgentOutput:
        """
        Execute Layout Agent - create per-slide layout specifications.

        Steps:
        1. Read strategy and research from Context Board
        2. Analyze each slide's content requirements
        3. Select optimal layout rule for each slide
        4. Calculate grid specs and element positions
        5. Measure content and flag truncation needs
        6. Write layout data to Context Board
        """
        self.log_progress("Starting Layout Agent execution")
        self._board_writes = []

        # Step 1: Get structure from CEO output (via Context Board or previous_outputs)
        structure = await self._get_slide_structure()
        if not structure:
            return AgentOutput(
                success=False,
                agent_type=self.agent_type,
                output={},
                errors=["No slide structure available from CEO Agent"],
            )

        # Step 2: Get research data for content hints
        research_data = await self._get_research_data()

        # Step 3: Generate layouts for each slide
        slide_layouts = await self._generate_slide_layouts(structure, research_data)

        # Step 4: Check layout consistency
        consistency_score = self._calculate_consistency_score(slide_layouts)

        # Step 5: Build layout data
        layout_data = LayoutData(
            slide_layouts=slide_layouts,
            global_grid=GridSpec(columns=12, rows=8, gutter=16, margin=40),
            layout_consistency_score=consistency_score,
        )

        # Step 6: Write to Context Board
        if self.protocol:
            await self.protocol.write_layout(layout_data, agent="layout")
            self._board_writes.extend([
                "layout.slide_layouts",
                "layout.global_grid",
                "layout.consistency_score",
            ])

        self.log_progress(f"Layout generated for {len(slide_layouts)} slides, consistency={consistency_score:.2f}")

        return AgentOutput(
            success=True,
            agent_type=self.agent_type,
            output={
                "slide_layouts": [sl.dict() for sl in slide_layouts],
                "layout_consistency_score": consistency_score,
            },
            context_board_writes=self._board_writes,
        )

    async def _get_slide_structure(self) -> List[Dict[str, Any]]:
        """Get slide structure from Context Board or previous outputs"""
        # Try Context Board first
        if self.protocol:
            strategy = await self.protocol.read_strategy()
            if strategy and strategy.structure:
                return strategy.structure

        # Fallback to previous outputs
        ceo_output = self.context.previous_outputs.get(AgentType.CEO)
        if ceo_output and ceo_output.success:
            return ceo_output.output.get("structure", [])

        return []

    async def _get_research_data(self) -> Dict[str, Any]:
        """Get research data from Context Board or previous outputs"""
        if self.protocol:
            research = await self.protocol.read_research()
            if research:
                return {
                    "items": [item.dict() for item in research.research_items],
                    "key_findings": research.key_findings,
                }

        researcher_output = self.context.previous_outputs.get(AgentType.RESEARCHER)
        if researcher_output and researcher_output.success:
            return researcher_output.output

        return {}

    async def _generate_slide_layouts(
        self, structure: List[Dict], research_data: Dict
    ) -> List[SlideLayout]:
        """Generate layout for each slide using AI reasoning"""
        slide_layouts = []

        # Batch process for efficiency
        batch_prompt = self._build_batch_layout_prompt(structure, research_data)
        result = await self.call_llm_json(
            task_type=TaskType.DESIGNER_LAYOUT,
            prompt=batch_prompt,
            temperature=0.3,
            max_tokens=4000,
            system_prompt=self._get_layout_system_prompt(),
        )

        if result.success and isinstance(result.output, dict):
            layouts_raw = result.output.get("layouts", [])
            for layout_data in layouts_raw:
                try:
                    slide_layout = self._parse_layout_response(layout_data)
                    if slide_layout:
                        slide_layouts.append(slide_layout)
                except Exception as e:
                    logger.warning(
                        "layout_parse_error",
                        slide_index=layout_data.get("slide_index"),
                        error=str(e),
                    )

        # Fill in missing layouts with defaults
        existing_indexes = {sl.slide_index for sl in slide_layouts}
        for slide in structure:
            idx = slide.get("index", 0)
            if idx not in existing_indexes:
                default_layout = self._get_default_layout(slide)
                slide_layouts.append(default_layout)

        # Sort by index
        slide_layouts.sort(key=lambda x: x.slide_index)
        return slide_layouts

    def _build_batch_layout_prompt(
        self, structure: List[Dict], research_data: Dict
    ) -> str:
        """Build prompt for batch layout generation"""
        slides_info = []
        for slide in structure:
            slide_info = {
                "index": slide.get("index", 0),
                "title": slide.get("title", ""),
                "layout_type": slide.get("layout", "bullets"),
                "purpose": slide.get("purpose", ""),
                "content_hints": slide.get("content_hints", ""),
            }
            # Add research data if available
            research_items = research_data.get("items", [])
            for item in research_items:
                if item.get("slide_index") == slide_info["index"]:
                    slide_info["data_points_count"] = len(item.get("data_points", []))
                    slide_info["has_statistics"] = len(item.get("statistics", [])) > 0
                    break
            slides_info.append(slide_info)

        available_rules = list(LAYOUT_RULES.keys())

        return f"""Analyze these slides and select the optimal layout rule for each one.

SLIDES:
{json.dumps(slides_info, indent=2)}

AVAILABLE LAYOUT RULES:
{json.dumps(available_rules, indent=2)}

LAYOUT RULE DETAILS:
{json.dumps({k: {"description": v["description"], "best_for": v["best_for"]} for k, v in LAYOUT_RULES.items()}, indent=2)}

For each slide, respond with JSON:
{{
  "layouts": [
    {{
      "slide_index": 0,
      "layout_rule": "hero_with_subtitle",
      "reasoning": "Title slide needs large centered text",
      "element_hints": {{
        "title": {{"position": "center", "size": "xl"}},
        "subtitle": {{"position": "below_title", "size": "md"}}
      }},
      "estimated_content_density": "low"
    }},
    ...
  ]
}}

Consider:
1. Match layout to content type (bullets, charts, images, etc.)
2. Ensure visual variety - don't use the same layout for every slide
3. Use simpler layouts for important messages
4. Consider content density when choosing grids

Respond with ONLY valid JSON."""

    def _get_layout_system_prompt(self) -> str:
        """System prompt for layout reasoning"""
        return """You are an expert presentation layout designer with deep knowledge of visual hierarchy, grid systems, and information architecture.

Your task is to select the optimal layout rule for each slide based on:
1. Content type (text, images, charts, metrics, team members)
2. Information density (how much content needs to fit)
3. Visual importance (hero slides vs supporting slides)
4. Narrative flow (maintaining visual rhythm across slides)

Rules:
- Title slides should use hero_with_subtitle or full_bleed_image
- Data-heavy slides benefit from two_column layouts
- Team/feature slides work best with grid layouts
- Keep visual consistency while avoiding monotony
- Consider the audience's viewing experience"""

    def _parse_layout_response(self, layout_data: Dict) -> Optional[SlideLayout]:
        """Parse AI response into SlideLayout object"""
        try:
            slide_index = layout_data.get("slide_index", 0)
            rule_name = layout_data.get("layout_rule", "single_column_center")

            # Validate and convert to enum
            try:
                layout_rule = LayoutRuleName(rule_name)
            except ValueError:
                layout_rule = LayoutRuleName.SINGLE_COLUMN_CENTER

            # Get grid spec from rule definition
            rule_def = LAYOUT_RULES.get(rule_name, LAYOUT_RULES["single_column_center"])
            grid_info = rule_def.get("grid", {})

            grid_spec = GridSpec(
                columns=grid_info.get("columns", 12) if isinstance(grid_info.get("columns"), int) else 12,
                rows=grid_info.get("rows", 8) if isinstance(grid_info.get("rows"), int) else 8,
                gutter=16,
                margin=40,
            )

            # Element positions from AI hints
            element_positions = layout_data.get("element_hints", {})

            return SlideLayout(
                slide_index=slide_index,
                layout_rule=layout_rule,
                grid_spec=grid_spec,
                element_positions=element_positions,
                content_measurements=[],
                responsive_breakpoints={},
                layout_reasoning=layout_data.get("reasoning", ""),
            )
        except Exception as e:
            logger.warning("layout_parse_error", error=str(e))
            return None

    def _get_default_layout(self, slide: Dict) -> SlideLayout:
        """Get default layout for a slide based on its type"""
        layout_type = slide.get("layout", "bullets")
        idx = slide.get("index", 0)

        # Map layout type to best rule
        candidate_rules = LAYOUT_TYPE_TO_RULES.get(layout_type, ["single_column_center"])
        rule_name = candidate_rules[0]

        try:
            layout_rule = LayoutRuleName(rule_name)
        except ValueError:
            layout_rule = LayoutRuleName.SINGLE_COLUMN_CENTER

        return SlideLayout(
            slide_index=idx,
            layout_rule=layout_rule,
            grid_spec=GridSpec(),
            element_positions={},
            content_measurements=[],
            responsive_breakpoints={},
            layout_reasoning=f"Default layout for {layout_type} slide type",
        )

    def _calculate_consistency_score(self, layouts: List[SlideLayout]) -> float:
        """Calculate visual consistency score across slides"""
        if len(layouts) < 2:
            return 1.0

        # Check for variety (not too much repetition)
        rule_counts: Dict[str, int] = {}
        for layout in layouts:
            rule = layout.layout_rule.value
            rule_counts[rule] = rule_counts.get(rule, 0) + 1

        max_count = max(rule_counts.values())
        total = len(layouts)

        # Penalize if one rule is used too much (>60% of slides)
        repetition_penalty = max(0, (max_count / total - 0.6) * 0.5)

        # Check for logical transitions (title → content → supporting)
        transition_score = self._check_layout_transitions(layouts)

        # Combine scores
        consistency = 0.7 + (transition_score * 0.3) - repetition_penalty
        return max(0.0, min(1.0, consistency))

    def _check_layout_transitions(self, layouts: List[SlideLayout]) -> float:
        """Check if layouts have logical transitions"""
        if len(layouts) < 2:
            return 1.0

        score = 1.0

        # First slide should be hero/title
        if layouts[0].layout_rule not in [
            LayoutRuleName.HERO_WITH_SUBTITLE,
            LayoutRuleName.FULL_BLEED_IMAGE,
        ]:
            score -= 0.1

        # Last slide should be simple (call to action)
        if layouts[-1].layout_rule in [LayoutRuleName.GRID_3X2, LayoutRuleName.GRID_2X3]:
            score -= 0.1

        return max(0.0, score)


class LayoutAgentWithPreText(LayoutAgent):
    """
    Extended Layout Agent with PreTeXt text measurement.
    Uses canvas.measureText() equivalent for precise text fitting.
    """

    async def measure_content(
        self,
        text: str,
        font_family: str = "Inter",
        font_size: int = 16,
        max_width: int = 800,
    ) -> ContentMeasurement:
        """
        Measure text content for layout fitting.
        Uses character-based estimation (server-side approximation).
        """
        # Approximate character width based on font
        char_width = font_size * 0.5  # Average for proportional fonts
        line_height = font_size * 1.5

        word_count = len(text.split())
        estimated_width = min(len(text) * char_width, max_width)

        # Calculate lines needed
        line_count = max(1, int((len(text) * char_width) / max_width) + 1)
        estimated_height = line_count * line_height

        # Check if truncation needed
        needs_truncation = word_count > 100 or line_count > 8

        return ContentMeasurement(
            element_id="text_block",
            estimated_width=estimated_width,
            estimated_height=estimated_height,
            line_count=line_count,
            word_count=word_count,
            needs_truncation=needs_truncation,
            suggested_font_size=font_size if not needs_truncation else max(12, font_size - 2),
        )
