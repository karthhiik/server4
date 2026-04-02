"""
Chart data generator — creates structured chart data from research/context.
Now powered by PromptEngine for investor-grade data presentation.
"""

import json
from typing import Optional

import structlog

from app.services.llm.model_router import ModelRouter, TaskType
from app.mcp.brain_mcp.prompts.chart_system import CHART_STYLE_RECOMMENDATIONS
from app.mcp.brain_mcp.prompts.prompt_engine import PromptEngine
from app.models.content import ChartData

logger = structlog.get_logger()


class ChartGenerator:
    """Generates structured chart data suitable for native PPTX charts."""

    def __init__(self):
        self.router = ModelRouter.get_instance()
        self.prompt_engine = PromptEngine()

    async def generate_chart_data(
        self,
        topic: str,
        chart_type: Optional[str] = None,
        research_context: str = "",
        data_hints: str = "",
        slide_purpose: str = "",
        writing_style: str = "yc_pitch",
        presentation_purpose: str = "pitch",
        presentation_id: Optional[str] = None,
    ) -> ChartData:
        """Generate chart data from context. Returns structured ChartData."""
        # Compose system prompt with domain layers for data presentation
        system_prompt = self.prompt_engine.compose_chart_prompt(
            style=writing_style,
            purpose=presentation_purpose,
            slide_purpose=slide_purpose,
        )

        user_prompt = f"""Generate chart data for: {topic}

{"Preferred chart type: " + chart_type if chart_type else "Choose the best chart type for this data."}
{"Data context: " + research_context[:2000] if research_context else ""}
{"Specific data hints: " + data_hints if data_hints else ""}
{"Slide purpose: " + slide_purpose if slide_purpose else ""}

Return JSON:
{{
  "chart_type": "bar|line|pie|donut|area",
  "title": "Chart title",
  "labels": ["Label1", "Label2", ...],
  "datasets": [
    {{"label": "Series Name", "values": [10, 20, 30]}}
  ],
  "source_attribution": "Data source if known",
  "units": "$ / % / count / etc"
}}

Use realistic, plausible data. If research context provides real numbers, use those.
Every number over $1M must have a source attribution."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await self.router.complete(
            task_type=TaskType.STRUCTURED_JSON,
            messages=messages,
            temperature=0.4,
            max_tokens=1024,
            presentation_id=presentation_id,
            phase="chart_data",
        )

        return self._parse_chart_data(response.content, topic)

    def _parse_chart_data(self, raw: str, fallback_topic: str) -> ChartData:
        """Parse LLM response into ChartData."""
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
            else:
                return ChartData(
                    chart_type="bar",
                    title=fallback_topic,
                    labels=["Category A", "Category B", "Category C"],
                    datasets=[{"label": "Values", "values": [30, 50, 70]}],
                )

        return ChartData(
            chart_type=data.get("chart_type", "bar"),
            title=data.get("title", fallback_topic),
            labels=data.get("labels", []),
            datasets=data.get("datasets", []),
            source_attribution=data.get("source_attribution"),
            units=data.get("units"),
        )

    def get_style_recommendation(self, chart_type: str) -> dict:
        """Get style recommendations for a chart type."""
        return CHART_STYLE_RECOMMENDATIONS.get(chart_type, CHART_STYLE_RECOMMENDATIONS.get("bar", {}))
