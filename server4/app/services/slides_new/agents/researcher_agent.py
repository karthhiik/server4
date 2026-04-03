"""
Researcher Agent - Content Research & Fact-Finding
Agent 2: Gathers relevant data, statistics, case studies, and references for the presentation.
"""

from typing import Any, Dict, List

from app.services.llm import TaskType
from app.services.slides_new.agents.base import (
    BaseAgent,
    AgentOutput,
    AgentType,
    AgentContext,
)


class ResearcherAgent(BaseAgent):
    """
    Agent 2: Content research and fact-finding.

    Responsibilities:
    - Research topic, gather relevant data and statistics
    - Find case studies and examples
    - Collect references and sources
    - Identify knowledge gaps that need addressing
    - Provide fact-checkable content for slides

    Uses web search for current data and trends.
    """

    DEFAULT_MODEL = "gemma-3-12b-it"
    FALLBACK_MODELS = ["qwen2.5-coder-32b-instruct", "glm-4.7-flash"]

    @property
    def agent_type(self) -> AgentType:
        return AgentType.RESEARCHER

    async def execute(self) -> AgentOutput:
        """
        Execute Researcher Agent - gather research for presentation.

        Steps:
        1. Get structure from CEO agent output
        2. Research each slide's topic area
        3. Gather statistics, examples, case studies
        4. Compile research into structured format
        5. Return research output
        """
        self.log_progress("Starting Researcher Agent execution")

        # Get CEO output for structure
        ceo_output = self.context.previous_outputs.get(AgentType.CEO)
        if not ceo_output or not ceo_output.success:
            return AgentOutput(
                success=False,
                agent_type=self.agent_type,
                output={},
                errors=["CEO Agent output not available"],
            )

        structure = ceo_output.output.get("structure", [])
        topic = self.context.topic
        description = self.context.description

        # Research each slide
        research_data = await self._research_slides(structure, topic, description)

        # Compile research output
        research = {
            "topic": topic,
            "slide_count": len(structure),
            "research_items": research_data,
            "key_findings": self._extract_key_findings(research_data),
            "sources": self._extract_sources(research_data),
        }

        self.log_progress(f"Research completed for {len(structure)} slides")

        return AgentOutput(
            success=True, agent_type=self.agent_type, output=research, warnings=[]
        )

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

    def _extract_key_findings(self, research_items: List[Dict]) -> List[str]:
        """Extract key findings from research items"""
        findings = []
        for item in research_items:
            key_takeaways = item.get("key_takeaways", [])
            findings.extend(key_takeaways[:2])  # Limit to 2 per slide
        return findings[:10]  # Top 10 findings

    def _extract_sources(self, research_items: List[Dict]) -> List[Dict]:
        """Extract all unique sources from research"""
        sources_map = {}
        for item in research_items:
            for stat in item.get("statistics", []):
                source = stat.get("source", "")
                if source and source not in sources_map:
                    sources_map[source] = {"name": source, "used_in": []}
                if source:
                    sources_map[source]["used_in"].append(item.get("title", ""))

            for dp in item.get("data_points", []):
                source = dp.get("source", "")
                if source and source not in sources_map:
                    sources_map[source] = {"name": source, "used_in": []}
                if source:
                    sources_map[source]["used_in"].append(item.get("title", ""))

        return list(sources_map.values())
