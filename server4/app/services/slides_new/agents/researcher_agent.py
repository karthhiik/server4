"""
Researcher Agent — V7 Phase 2
Agent 2: Content research and fact-finding.

Gathers relevant data, statistics, case studies, and references for the presentation.
Uses DeepSeek-V3.2 for fast extraction with FREE fallbacks.

Writes to Context Board: research section
"""

import asyncio
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
    ResearchData,
    SlideResearch,
    ResearchDataPoint,
    ResearchStatistic,
    ResearchExample,
    ResearchQuote,
)

if TYPE_CHECKING:
    from app.services.context_board import ContextBoard

logger = structlog.get_logger()


class ResearcherAgent(BaseAgent):
    """
    Agent 2: Content research and fact-finding - V7 Phase 2.

    Responsibilities:
    - Research topic, gather relevant data and statistics
    - Find case studies and examples
    - Collect references and sources
    - Identify knowledge gaps that need addressing
    - Provide fact-checkable content for slides
    - Write research data to Context Board
    - Support parallel execution with Designer Agent

    Uses DeepSeek-V3.2 for fast extraction with FREE fallbacks.
    """

    DEFAULT_MODEL = "gpt-4o-mini"
    FALLBACK_MODELS = ["deepseek-v3", "cf-qwen"]

    @property
    def agent_type(self) -> AgentType:
        return AgentType.RESEARCHER

    async def execute(self) -> AgentOutput:
        """
        Execute Researcher Agent - gather research for presentation.

        Steps:
        1. Get structure from Context Board or CEO agent output
        2. Research slides in parallel batches for efficiency
        3. Gather statistics, examples, case studies
        4. Compile research into structured format
        5. Write research data to Context Board
        """
        self.log_progress("Starting Researcher Agent execution")
        self._board_writes = []

        # Step 1: Get structure from Context Board first, then fallback
        structure = await self._get_slide_structure()
        if not structure:
            return AgentOutput(
                success=False,
                agent_type=self.agent_type,
                output={},
                errors=["No slide structure available - CEO Agent output required"],
            )

        topic = self.context.topic
        description = self.context.description

        # Step 2: Research slides with parallel processing for efficiency
        research_depth = getattr(self.context, "research_depth", "standard")
        research_items = await self._research_slides_parallel(
            structure, topic, description, depth=research_depth
        )

        # Step 3: Compile research output
        key_findings = self._extract_key_findings(research_items)
        sources = self._extract_sources(research_items)
        total_data_points = sum(
            len(item.data_points) + len(item.statistics)
            for item in research_items
        )

        # Step 4: Build typed research data
        research_data = ResearchData(
            topic=topic,
            slide_count=len(structure),
            research_items=research_items,
            key_findings=key_findings,
            sources=sources,
            total_data_points=total_data_points,
            research_depth=research_depth,
        )

        # Step 5: Write to Context Board
        if self.protocol:
            await self.protocol.write_research(research_data, agent="researcher")
            self._board_writes.extend([
                "research.topic",
                "research.slide_count",
                "research.items",
                "research.key_findings",
                "research.sources",
                "research.total_data_points",
            ])

        # Build output dict for backwards compatibility
        research_dict = {
            "topic": topic,
            "slide_count": len(structure),
            "research_items": [item.dict() for item in research_items],
            "key_findings": key_findings,
            "sources": sources,
            "total_data_points": total_data_points,
            "research_depth": research_depth,
        }

        self.log_progress(
            f"Research completed: {len(research_items)} slides, {total_data_points} data points"
        )

        return AgentOutput(
            success=True,
            agent_type=self.agent_type,
            output=research_dict,
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

    async def _research_slides_parallel(
        self,
        structure: List[Dict],
        topic: str,
        description: str,
        depth: str = "standard",
    ) -> List[SlideResearch]:
        """
        Research slides with parallel processing for efficiency.
        Groups slides into batches to avoid rate limits.
        """
        # Batch size based on depth
        batch_size = {"quick": 5, "standard": 3, "deep": 2}.get(depth, 3)

        research_items: List[SlideResearch] = []

        # Process in batches
        for i in range(0, len(structure), batch_size):
            batch = structure[i : i + batch_size]

            # Create tasks for parallel execution
            tasks = [
                self._research_single_slide_v2(
                    slide_index=slide.get("index", idx),
                    slide_title=slide.get("title", ""),
                    slide_purpose=slide.get("purpose", ""),
                    layout=slide.get("layout", ""),
                    topic=topic,
                    description=description,
                    depth=depth,
                )
                for idx, slide in enumerate(batch, start=i)
            ]

            # Execute batch in parallel
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, SlideResearch):
                    research_items.append(result)
                elif isinstance(result, Exception):
                    logger.warning("research_slide_error", error=str(result))

        return research_items

    async def _research_single_slide_v2(
        self,
        slide_index: int,
        slide_title: str,
        slide_purpose: str,
        layout: str,
        topic: str,
        description: str,
        depth: str = "standard",
    ) -> SlideResearch:
        """
        Research a single slide's content area with typed output.
        """
        # Adjust detail level based on depth
        detail_instructions = {
            "quick": "Provide 2-3 key data points. Be concise.",
            "standard": "Provide 3-5 data points with sources. Include 1-2 examples.",
            "deep": "Provide comprehensive research with 5+ data points, multiple examples, and expert quotes.",
        }

        prompt = f"""Research content for a slide in a presentation about: {topic}

SLIDE DETAILS:
- Index: {slide_index}
- Title: {slide_title}
- Purpose: {slide_purpose}
- Layout Type: {layout}

DESCRIPTION: {description}

{detail_instructions.get(depth, detail_instructions["standard"])}

## RESEARCH QUALITY RULES:
1. Every data point MUST have a specific, named source (e.g., "Gartner 2024 Magic Quadrant", not just "industry report")
2. If you cannot find a credible source for a statistic, set confidence to 0.0 and add research_notes: "Needs verification — no confirmed source"
3. Do NOT fabricate statistics. Use "estimated" prefix for calculated values (e.g., "estimated $2.1B based on 15M users × $140 ARPU")
4. Prefer recent sources (2023-2025). Flag older data with confidence penalty
5. Cross-reference: if a stat appears in only one source, confidence ≤ 0.7
6. For market size: always use bottom-up calculation, show the math
7. For growth rates: specify the timeframe (YoY, MoM, QoQ)

## ANTI-HALLUCINATION CHECKS:
- Before outputting any number, ask: "Would this survive a due diligence check?"
- If a company example seems fabricated, use well-known public companies instead
- Prefer conservative estimates over impressive-sounding fabrications
- Mark any data point you're less than 70% confident about with "⚠️ verify" in research_notes

Provide research data as JSON:
{{
  "slide_index": {slide_index},
  "title": "{slide_title}",
  "data_points": [
    {{"value": "23%", "label": "Market Growth", "source": "Gartner 2024", "confidence": 0.9}}
  ],
  "statistics": [
    {{"stat": "73%", "context": "of enterprises", "source": "McKinsey 2024"}}
  ],
  "examples": [
    {{"company": "Company X", "metric": "10x growth", "context": "in 18 months"}}
  ],
  "quotes": [
    {{"quote": "...", "author": "Industry Expert", "source": "Forbes", "relevance_score": 0.8}}
  ],
  "key_takeaways": ["takeaway1", "takeaway2"],
  "research_notes": "additional context for presenter, including any caveats or verification needs"
}}

Respond with ONLY valid JSON, no explanation."""

        result = await self.call_llm_json(
            task_type=TaskType.FACT_SYNTHESIS_JSON,
            prompt=prompt,
            temperature=0.3,
            max_tokens=2000,
            system_prompt="You are a senior research analyst at a top-tier consulting firm (McKinsey/BCG caliber). You never fabricate data. When you don't know something, you say so — your credibility depends on accuracy, not volume. Every statistic you cite must pass the 'investor due diligence' test. Provide specific, fact-checkable data points with named sources and publication dates. If a data point is an estimate, label it clearly as such. Your confidence scores must be calibrated: 0.9+ means you are certain the source exists, 0.5-0.8 means probable but unverified, below 0.5 means speculative.",
        )

        if result.success and isinstance(result.output, dict):
            try:
                # Parse into typed models
                data_points = [
                    ResearchDataPoint(**dp)
                    for dp in result.output.get("data_points", [])
                    if isinstance(dp, dict)
                ]
                statistics = [
                    ResearchStatistic(**stat)
                    for stat in result.output.get("statistics", [])
                    if isinstance(stat, dict)
                ]
                examples = [
                    ResearchExample(**ex)
                    for ex in result.output.get("examples", [])
                    if isinstance(ex, dict)
                ]
                quotes = [
                    ResearchQuote(**q)
                    for q in result.output.get("quotes", [])
                    if isinstance(q, dict)
                ]

                return SlideResearch(
                    slide_index=slide_index,
                    title=slide_title,
                    data_points=data_points,
                    statistics=statistics,
                    examples=examples,
                    quotes=quotes,
                    key_takeaways=result.output.get("key_takeaways", []),
                    research_notes=result.output.get("research_notes"),
                )
            except Exception as e:
                logger.warning(
                    "research_parse_error",
                    slide_index=slide_index,
                    error=str(e),
                )

        # Return empty research on failure
        return SlideResearch(
            slide_index=slide_index,
            title=slide_title,
            data_points=[],
            statistics=[],
            examples=[],
            quotes=[],
            key_takeaways=[],
            research_notes="Research pending - use CEO outline",
        )

    # Keep legacy methods for backwards compatibility
    async def _research_slides(
        self, structure: List[Dict], topic: str, description: str
    ) -> List[Dict]:
        """
        Research each slide in the structure.

        Creates detailed research for each slide's content area.
        """
        research_items = []

        for slide in structure:
            slide_index = slide.get("index", 0)
            slide_title = slide.get("title", "")
            slide_purpose = slide.get("purpose", "")
            layout = slide.get("layout", "")

            # Generate research for this slide
            research_item = await self._research_single_slide(
                slide_index=slide_index,
                slide_title=slide_title,
                slide_purpose=slide_purpose,
                layout=layout,
                topic=topic,
                description=description,
            )

            if research_item:
                research_items.append(research_item)

        return research_items

    async def _research_single_slide(
        self,
        slide_index: int,
        slide_title: str,
        slide_purpose: str,
        layout: str,
        topic: str,
        description: str,
    ) -> Dict[str, Any]:
        """
        Research a single slide's content area.
        """
        prompt = f"""Research content for a slide in a presentation about: {topic}

SLIDE DETAILS:
- Index: {slide_index}
- Title: {slide_title}
- Purpose: {slide_purpose}
- Layout Type: {layout}

DESCRIPTION: {description}

Provide research data as JSON:
{{
  "slide_index": {slide_index},
  "title": "{slide_title}",
  "data_points": [
    {{"value": "23%", "label": "Market Growth", "source": "Gartner 2024"}},
    {{"value": "$50B", "label": "TAM", "source": "Forrester"}}
  ],
  "key_takeaways": ["takeaway1", "takeaway2"],
  "examples": [
    {{"company": "Company X", "metric": "10x growth", "context": "in 18 months"}}
  ],
  "statistics": [
    {{"stat": "73%", "context": "of enterprises", "source": "McKinsey 2024"}}
  ],
  "quotes": [
    {{"quote": "...", "author": "Industry Expert", "source": " Forbes"}}
  ],
  "research_notes": "additional context for presenter"
}}

Respond with ONLY valid JSON, no explanation."""

        result = await self.call_llm_json(
            task_type=TaskType.STRUCTURED_JSON,
            prompt=prompt,
            temperature=0.3,
            max_tokens=2000,
            system_prompt="You are a research analyst. Provide specific, fact-checkable data points, statistics, and examples. Always include sources. Make content specific to the topic, not generic.",
        )

        if result.success:
            return result.output

        # Return minimal structure on failure
        return {
            "slide_index": slide_index,
            "title": slide_title,
            "data_points": [],
            "key_takeaways": [],
            "examples": [],
            "statistics": [],
            "quotes": [],
            "research_notes": "Research pending - use CEO outline",
        }

    def _extract_key_findings(
        self, research_items: List[SlideResearch]
    ) -> List[str]:
        """Extract key findings from research items"""
        findings = []
        for item in research_items:
            findings.extend(item.key_takeaways[:2])  # Limit to 2 per slide
        return findings[:10]  # Top 10 findings

    def _extract_sources(
        self, research_items: List[SlideResearch]
    ) -> List[Dict[str, Any]]:
        """Extract all unique sources from research"""
        sources_map: Dict[str, Dict[str, Any]] = {}

        for item in research_items:
            # From statistics
            for stat in item.statistics:
                source = stat.source
                if source and source not in sources_map:
                    sources_map[source] = {"name": source, "used_in": []}
                if source:
                    sources_map[source]["used_in"].append(item.title)

            # From data points
            for dp in item.data_points:
                source = dp.source
                if source and source not in sources_map:
                    sources_map[source] = {"name": source, "used_in": []}
                if source:
                    sources_map[source]["used_in"].append(item.title)

        return list(sources_map.values())
