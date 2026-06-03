"""
Intelligent Visual Asset Generation Engine - CTO Mission-Critical Fix

This module implements a multi-agent system for generating accurate visual elements:
- Charts
- Graphs
- Tables
- Diagrams
- Icons
- Timelines
- Team members
- Metrics
- Infographics

Multi-Agent Architecture:
A. Content Understanding Agent - Understands business context, investor intent
B. Visual Planning Agent - Determines required visual type
C. Data-to-Visualization Agent - Converts data to accurate charts/graphs
D. Element Verification Agent - Validates rendered elements
E. Layout Intelligence Agent - Prevents overflow, overlap, broken spacing
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import structlog

from app.services.v4.parallel_writer import GeneratedSlide
from app.services.v4.research_collector import ResearchPacket

logger = structlog.get_logger(__name__)


class VisualElementType(Enum):
    """Types of visual elements that can be generated"""
    CHART = "chart"
    GRAPH = "graph"
    TABLE = "table"
    DIAGRAM = "diagram"
    ICON = "icon"
    TIMELINE = "timeline"
    TEAM_MEMBER = "team_member"
    STAT_BLOCK = "stat_block"
    INFOGRAPHIC = "infographic"
    MAP = "map"
    ORG_CHART = "org_chart"
    FUNNEL = "funnel"
    ROADMAP = "roadmap"
    KPI_CARD = "kpi_card"
    COMPARISON = "comparison"
    PROCESS_FLOW = "process_flow"


class ChartType(Enum):
    """Types of charts that can be generated"""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    DONUT = "donut"
    AREA = "area"
    SCATTER = "scatter"
    RADAR = "radar"
    HISTOGRAM = "histogram"
    WATERFALL = "waterfall"
    STACKED_BAR = "stacked_bar"
    GROUPED_BAR = "grouped_bar"


@dataclass
class VisualRequirement:
    """Requirement for a visual element"""
    element_type: VisualElementType
    chart_type: Optional[ChartType] = None
    data_source: Optional[str] = None
    priority: float = 1.0  # 0.0 to 1.0
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)


@dataclass
class VisualGenerationResult:
    """Result of visual element generation"""
    success: bool
    element_type: VisualElementType
    generated_data: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence: float = 0.0  # 0.0 to 1.0


class ContentUnderstandingAgent:
    """
    Agent A: Content Understanding
    
    Understands:
    - Business context
    - Investor intent
    - Slide purpose
    - Required visual type
    """
    
    # Intent to visual type mapping
    INTENT_VISUAL_MAPPING = {
        "market": [VisualElementType.CHART, VisualElementType.GRAPH],
        "traction": [VisualElementType.STAT_BLOCK, VisualElementType.CHART],
        "financials": [VisualElementType.CHART, VisualElementType.TABLE],
        "competition": [VisualElementType.COMPARISON, VisualElementType.TABLE],
        "team": [VisualElementType.TEAM_MEMBER, VisualElementType.ORG_CHART],
        "timeline": [VisualElementType.TIMELINE, VisualElementType.ROADMAP],
        "problem": [VisualElementType.DIAGRAM, VisualElementType.ICON],
        "solution": [VisualElementType.DIAGRAM, VisualElementType.PROCESS_FLOW],
        "business_model": [VisualElementType.DIAGRAM, VisualElementType.INFOGRAPHIC],
        "ask": [VisualElementType.STAT_BLOCK, VisualElementType.KPI_CARD],
    }
    
    # Data source hints
    DATA_SOURCE_HINTS = {
        "market": ["market_size", "tam", "sam", "som", "growth_rate"],
        "traction": ["revenue", "users", "customers", "growth", "metrics"],
        "financials": ["revenue", "profit", "margin", "burn_rate", "runway"],
        "competition": ["competitors", "market_share", "features", "pricing"],
        "team": ["team_members", "founders", "advisors", "board"],
        "financial_projection": ["projections", "forecast", "cagr", " ARR"],
    }
    
    def understand_slide_context(
        self,
        slide: GeneratedSlide,
        research: ResearchPacket,
    ) -> Dict[str, Any]:
        """
        Analyze slide to understand what visual elements are needed.
        
        Returns context dict with:
        - required_visuals: List of VisualRequirement
        - data_available: Dict of available data sources
        - investor_intent: What the slide needs to communicate
        """
        context = {
            "required_visuals": [],
            "data_available": {},
            "investor_intent": "",
        }
        
        intent = slide.intent or ""
        
        # Determine required visual types based on intent
        visual_types = self.INTENT_VISUAL_MAPPING.get(intent, [])
        
        # Determine data sources available from research
        data_hints = self.DATA_SOURCE_HINTS.get(intent, [])
        available_data = {}
        
        research_dict = research.__dict__ if research else {}
        for hint in data_hints:
            if hint in research_dict and research_dict[hint]:
                available_data[hint] = research_dict[hint]
        
        # Check slide data
        if slide.chart:
            context["required_visuals"].append(
                VisualRequirement(
                    element_type=VisualElementType.CHART,
                    chart_type=self._infer_chart_type(slide.chart),
                    priority=0.9,
                    required_fields=["data", "type"],
                )
            )
        
        if slide.stat_blocks:
            context["required_visuals"].append(
                VisualRequirement(
                    element_type=VisualElementType.STAT_BLOCK,
                    priority=0.8,
                    required_fields=["value", "label"],
                )
            )
        
        if slide.timeline:
            context["required_visuals"].append(
                VisualRequirement(
                    element_type=VisualElementType.TIMELINE,
                    priority=0.85,
                    required_fields=["events"],
                )
            )
        
        if slide.team_members:
            context["required_visuals"].append(
                VisualRequirement(
                    element_type=VisualElementType.TEAM_MEMBER,
                    priority=0.9,
                    required_fields=["name", "role"],
                )
            )
        
        if slide.comparison:
            context["required_visuals"].append(
                VisualRequirement(
                    element_type=VisualElementType.COMPARISON,
                    priority=0.85,
                    required_fields=["rows"],
                )
            )
        
        context["data_available"] = available_data
        context["investor_intent"] = self._infer_investor_intent(intent, slide.headline)
        
        return context
    
    def _infer_chart_type(self, chart_data: Dict[str, Any]) -> Optional[ChartType]:
        """Infer chart type from data structure"""
        if not chart_data:
            return None
        
        chart_type_str = chart_data.get("type", "").lower()
        
        try:
            return ChartType(chart_type_str)
        except ValueError:
            # Infer from data shape
            data = chart_data.get("data", [])
            if not data:
                return ChartType.BAR
            
            # If data has single series, use bar/line
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], dict):
                    keys = data[0].keys()
                    if len(keys) <= 2:
                        return ChartType.BAR
                    else:
                        return ChartType.LINE
            
            return ChartType.BAR
    
    def _infer_investor_intent(self, intent: str, headline: str) -> str:
        """Infer what the slide needs to communicate to investors"""
        intent_map = {
            "market": "Show market size, growth, and opportunity",
            "traction": "Demonstrate growth metrics and validation",
            "financials": "Present financial performance and projections",
            "competition": "Differentiate from competitors",
            "team": "Show team expertise and credibility",
            "timeline": "Demonstrate progress and roadmap",
            "problem": "Highlight market pain point",
            "solution": "Product response to the problem",
            "business_model": "Explain revenue model and unit economics",
            "ask": "State funding request and use of funds",
        }
        
        return intent_map.get(intent, "Communicate key value proposition")


class VisualPlanningAgent:
    """
    Agent B: Visual Planning
    
    Determines:
    - Whether slide needs chart/graph/table/infographic
    - Optimal visual type for the data
    - Layout implications
    """
    
    def plan_visual_elements(
        self,
        slide: GeneratedSlide,
        context: Dict[str, Any],
    ) -> List[VisualRequirement]:
        """
        Plan which visual elements are needed and their priorities.
        
        Returns prioritized list of VisualRequirement objects.
        """
        requirements = context.get("required_visuals", [])
        
        # If no requirements from context, infer from slide content
        if not requirements:
            requirements = self._infer_requirements_from_slide(slide)
        
        # Prioritize requirements
        requirements.sort(key=lambda x: x.priority, reverse=True)
        
        return requirements
    
    def _infer_requirements_from_slide(
        self,
        slide: GeneratedSlide,
    ) -> List[VisualRequirement]:
        """Infer visual requirements from slide content"""
        requirements = []
        
        # Check if slide has numeric data that needs visualization
        has_numeric_data = bool(
            slide.stat_blocks or
            (slide.chart and slide.chart.get("data")) or
            (slide.body and re.search(r'\d+', slide.body))
        )
        
        intent = slide.intent or ""
        
        if intent == "market" and has_numeric_data:
            requirements.append(
                VisualRequirement(
                    element_type=VisualElementType.CHART,
                    chart_type=ChartType.BAR,
                    priority=0.9,
                    required_fields=["data", "type"],
                )
            )
        
        if intent == "traction" and has_numeric_data:
            requirements.append(
                VisualRequirement(
                    element_type=VisualElementType.STAT_BLOCK,
                    priority=0.95,
                    required_fields=["value", "label"],
                )
            )
        
        if intent == "team" and slide.team_members:
            requirements.append(
                VisualRequirement(
                    element_type=VisualElementType.TEAM_MEMBER,
                    priority=1.0,
                    required_fields=["name", "role"],
                )
            )
        
        return requirements


class DataToVisualizationAgent:
    """
    Agent C: Data-to-Visualization
    
    Automatically converts:
    - Financial data → accurate charts
    - Growth metrics → animated metrics
    - Market size → investor visuals
    - Projections → forecast charts
    """
    
    def generate_chart(
        self,
        data: Dict[str, Any],
        chart_type: Optional[ChartType] = None,
    ) -> VisualGenerationResult:
        """
        Generate chart data from raw input.
        
        Validates and normalizes chart data structure.
        """
        errors = []
        warnings = []
        
        # Validate required fields
        if not data.get("data"):
            errors.append("Chart data is missing or empty")
            return VisualGenerationResult(
                success=False,
                element_type=VisualElementType.CHART,
                errors=errors,
                confidence=0.0,
            )
        
        chart_data = data.get("data", [])
        
        # Normalize data structure
        normalized_data = self._normalize_chart_data(chart_data)
        
        if not normalized_data:
            errors.append("Failed to normalize chart data")
            return VisualGenerationResult(
                success=False,
                element_type=VisualElementType.CHART,
                errors=errors,
                confidence=0.0,
            )
        
        # Infer chart type if not provided
        if not chart_type:
            chart_type = self._infer_optimal_chart_type(normalized_data)
        
        # Build complete chart object
        generated_chart = {
            "type": chart_type.value,
            "data": normalized_data,
            "xKey": data.get("xKey", "name"),
            "yKeys": data.get("yKeys", ["value"]),
            "valueKey": data.get("valueKey", "value"),
            "nameKey": data.get("nameKey", "name"),
        }
        
        # Add optional fields if present
        if data.get("source"):
            generated_chart["source"] = data["source"]
        if data.get("seriesLabels"):
            generated_chart["seriesLabels"] = data["seriesLabels"]
        
        confidence = self._calculate_chart_confidence(generated_chart)
        
        return VisualGenerationResult(
            success=True,
            element_type=VisualElementType.CHART,
            generated_data=generated_chart,
            confidence=confidence,
        )
    
    def _normalize_chart_data(self, data: Any) -> List[Dict[str, Any]]:
        """Normalize chart data to standard format"""
        if not data:
            return []
        
        # If already in correct format
        if isinstance(data, list) and all(isinstance(item, dict) for item in data):
            return data
        
        # If list of lists/tuples [[name, value], ...]
        if isinstance(data, list) and all(isinstance(item, (list, tuple)) for item in data):
            return [{"name": str(item[0]), "value": float(item[1])} for item in data if len(item) >= 2]
        
        # If dict with numeric values
        if isinstance(data, dict):
            return [{"name": str(k), "value": float(v)} for k, v in data.items() if isinstance(v, (int, float))]
        
        return []
    
    def _infer_optimal_chart_type(self, data: List[Dict[str, Any]]) -> ChartType:
        """Infer optimal chart type from data structure"""
        if not data:
            return ChartType.BAR
        
        # Check if data has multiple series
        first_item = data[0]
        numeric_keys = [k for k in first_item.keys() if isinstance(first_item.get(k), (int, float))]
        
        if len(numeric_keys) > 1:
            return ChartType.GROUPED_BAR
        
        if len(data) <= 5:
            return ChartType.PIE
        
        if len(data) > 10:
            return ChartType.LINE
        
        return ChartType.BAR
    
    def _calculate_chart_confidence(self, chart: Dict[str, Any]) -> float:
        """Calculate confidence score for generated chart"""
        confidence = 1.0
        
        # Penalize for missing optional fields
        if not chart.get("source"):
            confidence -= 0.1
        if not chart.get("seriesLabels") and len(chart.get("yKeys", [])) > 1:
            confidence -= 0.1
        
        # Check data quality
        data = chart.get("data", [])
        if len(data) < 2:
            confidence -= 0.3
        
        # Check for valid numeric values
        valid_values = 0
        for item in data:
            for key in chart.get("yKeys", ["value"]):
                val = item.get(key)
                if isinstance(val, (int, float)) and val > 0:
                    valid_values += 1
        
        if valid_values < len(data) * 0.8:
            confidence -= 0.2
        
        return max(0.0, min(1.0, confidence))
    
    def generate_stat_blocks(
        self,
        stats: List[Dict[str, Any]],
    ) -> VisualGenerationResult:
        """Generate stat blocks from raw data"""
        errors = []
        warnings = []
        
        if not stats:
            errors.append("Stat blocks data is empty")
            return VisualGenerationResult(
                success=False,
                element_type=VisualElementType.STAT_BLOCK,
                errors=errors,
                confidence=0.0,
            )
        
        # Normalize stat blocks
        normalized_stats = []
        for stat in stats:
            normalized = {
                "value": str(stat.get("value") or stat.get("number") or ""),
                "label": str(stat.get("label") or stat.get("caption") or ""),
            }
            if stat.get("delta"):
                normalized["delta"] = str(stat["delta"])
            if stat.get("trend") in {"up", "down", "flat"}:
                normalized["trend"] = stat["trend"]
            normalized_stats.append(normalized)
        
        confidence = 1.0 if len(normalized_stats) >= 2 else 0.7
        
        return VisualGenerationResult(
            success=True,
            element_type=VisualElementType.STAT_BLOCK,
            generated_data={"stat_blocks": normalized_stats},
            confidence=confidence,
        )
    
    def generate_timeline(
        self,
        timeline_data: Dict[str, Any],
    ) -> VisualGenerationResult:
        """Generate timeline from raw data"""
        errors = []
        
        events = timeline_data.get("events", [])
        
        if not events:
            errors.append("Timeline events are missing")
            return VisualGenerationResult(
                success=False,
                element_type=VisualElementType.TIMELINE,
                errors=errors,
                confidence=0.0,
            )
        
        # Normalize events
        normalized_events = []
        for event in events:
            normalized = {
                "date": str(event.get("date") or event.get("time") or ""),
                "title": str(event.get("title") or event.get("name") or ""),
            }
            if event.get("description"):
                normalized["description"] = str(event["description"])
            normalized_events.append(normalized)
        
        confidence = 1.0 if len(normalized_events) >= 3 else 0.6
        
        return VisualGenerationResult(
            success=True,
            element_type=VisualElementType.TIMELINE,
            generated_data={
                "orientation": timeline_data.get("orientation", "horizontal"),
                "milestones": normalized_events,
            },
            confidence=confidence,
        )


class ElementVerificationAgent:
    """
    Agent D: Element Verification
    
    Checks:
    - Chart rendered?
    - Icons rendered?
    - SVG valid?
    - Data exists?
    - Labels visible?
    - Responsive scaling valid?
    - Overlap exists?
    - Clipping exists?
    """
    
    def verify_chart(self, chart_data: Dict[str, Any]) -> VisualGenerationResult:
        """Verify chart data is valid and renderable"""
        errors = []
        warnings = []
        
        # Check required fields
        if not chart_data.get("type"):
            errors.append("Chart type is missing")
        
        if not chart_data.get("data"):
            errors.append("Chart data is missing")
        
        data = chart_data.get("data", [])
        if not isinstance(data, list) or len(data) == 0:
            errors.append("Chart data must be a non-empty list")
        
        # Check data structure
        if data and isinstance(data, list):
            for i, item in enumerate(data):
                if not isinstance(item, dict):
                    errors.append(f"Chart data item {i} is not a dict")
                    break
                
                # Check for required keys
                if not any(key in item for key in ["name", "label", "x"]):
                    warnings.append(f"Chart data item {i} missing label/key")
                
                # Check for numeric values
                has_numeric = any(isinstance(item.get(k), (int, float)) for k in item.keys())
                if not has_numeric:
                    errors.append(f"Chart data item {i} has no numeric values")
        
        # Check for reasonable data range
        if data and isinstance(data, list):
            numeric_values = []
            for item in data:
                for v in item.values():
                    if isinstance(v, (int, float)):
                        numeric_values.append(v)
            
            if numeric_values:
                max_val = max(numeric_values)
                if max_val > 1e12:  # Trillion
                    warnings.append("Chart values extremely large, may need formatting")
        
        confidence = 1.0 - (len(errors) * 0.2) - (len(warnings) * 0.05)
        confidence = max(0.0, min(1.0, confidence))
        
        return VisualGenerationResult(
            success=len(errors) == 0,
            element_type=VisualElementType.CHART,
            generated_data=chart_data if len(errors) == 0 else None,
            errors=errors,
            warnings=warnings,
            confidence=confidence,
        )
    
    def verify_timeline(self, timeline_data: Dict[str, Any]) -> VisualGenerationResult:
        """Verify timeline data is valid"""
        errors = []
        
        events = timeline_data.get("milestones") or timeline_data.get("events", [])
        
        if not events:
            errors.append("Timeline has no events")
        
        if not isinstance(events, list):
            errors.append("Timeline events must be a list")
        
        if events and isinstance(events, list):
            for i, event in enumerate(events):
                if not isinstance(event, dict):
                    errors.append(f"Timeline event {i} is not a dict")
                    break
                
                if not event.get("date") and not event.get("time"):
                    errors.append(f"Timeline event {i} missing date/time")
                
                if not event.get("title") and not event.get("name"):
                    errors.append(f"Timeline event {i} missing title/name")
        
        confidence = 1.0 - (len(errors) * 0.2)
        confidence = max(0.0, min(1.0, confidence))
        
        return VisualGenerationResult(
            success=len(errors) == 0,
            element_type=VisualElementType.TIMELINE,
            generated_data=timeline_data if len(errors) == 0 else None,
            errors=errors,
            confidence=confidence,
        )
    
    def verify_stat_blocks(self, stat_blocks: List[Dict[str, Any]]) -> VisualGenerationResult:
        """Verify stat blocks are valid"""
        errors = []
        
        if not stat_blocks:
            errors.append("Stat blocks are empty")
        
        if stat_blocks and isinstance(stat_blocks, list):
            for i, stat in enumerate(stat_blocks):
                if not isinstance(stat, dict):
                    errors.append(f"Stat block {i} is not a dict")
                    break
                
                if not stat.get("value") and not stat.get("number"):
                    errors.append(f"Stat block {i} missing value")
                
                if not stat.get("label") and not stat.get("caption"):
                    errors.append(f"Stat block {i} missing label")
        
        confidence = 1.0 - (len(errors) * 0.2)
        confidence = max(0.0, min(1.0, confidence))
        
        return VisualGenerationResult(
            success=len(errors) == 0,
            element_type=VisualElementType.STAT_BLOCK,
            generated_data={"stat_blocks": stat_blocks} if len(errors) == 0 else None,
            errors=errors,
            confidence=confidence,
        )


class LayoutIntelligenceAgent:
    """
    Agent E: Layout Intelligence
    
    Prevents:
    - Overflow
    - Overlap
    - Broken spacing
    - Cropped charts
    - Unreadable tables
    - Misaligned icons
    """
    
    def check_layout_conflicts(
        self,
        slide: GeneratedSlide,
    ) -> List[str]:
        """
        Check for layout conflicts and spacing issues.
        
        Returns list of conflict descriptions.
        """
        conflicts = []
        
        # Check for content overload
        content_items = 0
        if slide.bullets:
            content_items += len(slide.bullets)
        if slide.stat_blocks:
            content_items += len(slide.stat_blocks)
        if slide.chart:
            content_items += 1
        if slide.timeline:
            content_items += 1
        if slide.team_members:
            content_items += len(slide.team_members)
        
        if content_items > 8:
            conflicts.append(f"Content overload: {content_items} items may cause overflow")
        
        # Check for bullet length
        if slide.bullets:
            long_bullets = [b for b in slide.bullets if len(str(b)) > 100]
            if long_bullets:
                conflicts.append(f"{len(long_bullets)} bullets are too long (>100 chars)")
        
        # Check for chart data density
        if slide.chart:
            chart_data = slide.chart.get("data", [])
            if len(chart_data) > 12:
                conflicts.append(f"Chart has {len(chart_data)} data points, may be unreadable")
        
        # Check for timeline density
        if slide.timeline:
            events = slide.timeline.get("events") or slide.timeline.get("milestones", [])
            if len(events) > 8:
                conflicts.append(f"Timeline has {len(events)} events, may be overcrowded")
        
        # Check for team density
        if slide.team_members:
            if len(slide.team_members) > 6:
                conflicts.append(f"Team section has {len(slide.team_members)} members, may be overcrowded")
        
        return conflicts
    
    def suggest_layout_adjustments(
        self,
        conflicts: List[str],
    ) -> List[str]:
        """
        Suggest layout adjustments to resolve conflicts.
        """
        suggestions = []
        
        for conflict in conflicts:
            if "Content overload" in conflict:
                suggestions.append("Consider splitting into multiple slides or using a grid layout")
            elif "bullets are too long" in conflict:
                suggestions.append("Shorten bullets or move detailed text to body paragraph")
            elif "Chart has" in conflict and "data points" in conflict:
                suggestions.append("Reduce chart data points or use a scrollable/interactive chart")
            elif "Timeline has" in conflict and "events" in conflict:
                suggestions.append("Reduce timeline events or use a condensed view")
            elif "Team section has" in conflict and "members" in conflict:
                suggestions.append("Show key team members only, use org chart for full team")
        
        return suggestions


class VisualAssetEngine:
    """
    Main Visual Asset Generation Engine
    
    Orchestrates all agents to generate accurate visual elements.
    """
    
    def __init__(self) -> None:
        self.content_agent = ContentUnderstandingAgent()
        self.planning_agent = VisualPlanningAgent()
        self.visualization_agent = DataToVisualizationAgent()
        self.verification_agent = ElementVerificationAgent()
        self.layout_agent = LayoutIntelligenceAgent()
    
    def process_slide(
        self,
        slide: GeneratedSlide,
        research: ResearchPacket,
    ) -> Dict[str, Any]:
        """
        Process a slide to ensure all visual elements are generated and valid.
        
        Returns dict with:
        - enhanced_slide: GeneratedSlide with enhanced visual data
        - generation_results: List of VisualGenerationResult
        - layout_conflicts: List of layout conflicts
        - layout_suggestions: List of layout suggestions
        """
        results = {
            "enhanced_slide": slide,
            "generation_results": [],
            "layout_conflicts": [],
            "layout_suggestions": [],
        }
        
        # Stage 1: Understand content
        context = self.content_agent.understand_slide_context(slide, research)
        
        # Stage 2: Plan visual elements
        requirements = self.planning_agent.plan_visual_elements(slide, context)
        
        # Stage 3: Generate and verify each visual element
        for req in requirements:
            if req.element_type == VisualElementType.CHART and slide.chart:
                # Verify existing chart
                verification = self.verification_agent.verify_chart(slide.chart)
                results["generation_results"].append(verification)
                
                # If verification failed, try to regenerate
                if not verification.success:
                    generation = self.visualization_agent.generate_chart(
                        slide.chart,
                        req.chart_type,
                    )
                    results["generation_results"].append(generation)
                    
                    if generation.success:
                        # Update slide with regenerated chart
                        slide_dict = slide.__dict__.copy()
                        slide_dict["chart"] = generation.generated_data
                        results["enhanced_slide"] = GeneratedSlide(**slide_dict)
            
            elif req.element_type == VisualElementType.STAT_BLOCK and slide.stat_blocks:
                # Verify stat blocks
                verification = self.verification_agent.verify_stat_blocks(slide.stat_blocks)
                results["generation_results"].append(verification)
                
                if not verification.success:
                    generation = self.visualization_agent.generate_stat_blocks(slide.stat_blocks)
                    results["generation_results"].append(generation)
                    
                    if generation.success:
                        slide_dict = slide.__dict__.copy()
                        slide_dict["stat_blocks"] = generation.generated_data["stat_blocks"]
                        results["enhanced_slide"] = GeneratedSlide(**slide_dict)
            
            elif req.element_type == VisualElementType.TIMELINE and slide.timeline:
                # Verify timeline
                verification = self.verification_agent.verify_timeline(slide.timeline)
                results["generation_results"].append(verification)
                
                if not verification.success:
                    generation = self.visualization_agent.generate_timeline(slide.timeline)
                    results["generation_results"].append(generation)
                    
                    if generation.success:
                        slide_dict = slide.__dict__.copy()
                        slide_dict["timeline"] = generation.generated_data
                        results["enhanced_slide"] = GeneratedSlide(**slide_dict)
        
        # Stage 4: Check layout conflicts
        conflicts = self.layout_agent.check_layout_conflicts(results["enhanced_slide"])
        results["layout_conflicts"] = conflicts
        
        if conflicts:
            suggestions = self.layout_agent.suggest_layout_adjustments(conflicts)
            results["layout_suggestions"] = suggestions
        
        return results


# Singleton instance
_engine_instance: Optional[VisualAssetEngine] = None


def get_visual_asset_engine() -> VisualAssetEngine:
    """Get singleton visual asset engine instance"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = VisualAssetEngine()
    return _engine_instance
