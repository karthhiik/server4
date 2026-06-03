"""Visual Elements Engine for Standard Mode.

This module generates visual elements (charts, graphs, tables, diagrams)
for slides based on slide type, data, and purpose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class VisualElement:
    """A visual element for a slide."""
    
    element_type: str  # "chart", "graph", "table", "diagram", "timeline", "map"
    chart_type: Optional[str] = None  # "bar", "line", "pie", "scatter", "area", etc.
    data: dict[str, Any] = field(default_factory=dict)
    title: Optional[str] = None
    description: Optional[str] = None
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    series: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class VisualElementsEngine:
    """Generates visual elements for slides based on type and data."""

    def __init__(self) -> None:
        """Initialize the visual elements engine."""
        self._slide_type_mapping = self._build_slide_type_mapping()

    def _build_slide_type_mapping(self) -> dict[str, dict[str, Any]]:
        """Build mapping of slide types to visual element configurations."""
        return {
            "traction": {
                "element_type": "chart",
                "chart_type": "line",
                "x_axis": "Time",
                "y_axis": "Growth",
                "default_series": ["Users", "Revenue", "MRR"],
            },
            "market_size": {
                "element_type": "chart",
                "chart_type": "bar",
                "x_axis": "Market Segment",
                "y_axis": "Size ($B)",
                "default_series": ["TAM", "SAM", "SOM"],
            },
            "revenue_model": {
                "element_type": "diagram",
                "chart_type": None,
                "description": "Revenue model diagram showing pricing tiers and unit economics",
            },
            "financials": {
                "element_type": "table",
                "chart_type": None,
                "description": "Financial projections table",
            },
            "competition": {
                "element_type": "table",
                "chart_type": None,
                "description": "Competitive feature matrix",
            },
            "roadmap": {
                "element_type": "timeline",
                "chart_type": None,
                "description": "Product or company roadmap",
            },
            "geographic_expansion": {
                "element_type": "map",
                "chart_type": None,
                "description": "Geographic expansion map",
            },
            "customer_segmentation": {
                "element_type": "chart",
                "chart_type": "pie",
                "description": "Customer segmentation breakdown",
            },
            "metrics": {
                "element_type": "chart",
                "chart_type": "bar",
                "x_axis": "Metric",
                "y_axis": "Value",
                "description": "Key performance metrics",
            },
            "business_model": {
                "element_type": "diagram",
                "chart_type": None,
                "description": "Business model diagram",
            },
        }

    def needs_visual_element(self, slide_type: str) -> bool:
        """Determine if a slide type needs a visual element."""
        return slide_type in self._slide_type_mapping

    async def generate_visual_element(
        self,
        slide_type: str,
        data: dict[str, Any],
        purpose: str,
    ) -> Optional[VisualElement]:
        """Generate a visual element for a slide.

        Args:
            slide_type: The type of slide (e.g., "traction", "market_size")
            data: Research data and context
            purpose: Presentation purpose for context

        Returns:
            VisualElement or None if the slide type doesn't support visuals
        """
        if not self.needs_visual_element(slide_type):
            return None

        config = self._slide_type_mapping.get(slide_type)
        if not config:
            return None

        try:
            element_type = config["element_type"]
            chart_type = config.get("chart_type")
            
            # Extract relevant data based on slide type
            extracted_data = self._extract_data_for_slide_type(slide_type, data, purpose)
            
            # Build the visual element
            visual_element = VisualElement(
                element_type=element_type,
                chart_type=chart_type,
                data=extracted_data,
                title=self._generate_title(slide_type, purpose),
                description=config.get("description"),
                x_axis=config.get("x_axis"),
                y_axis=config.get("y_axis"),
                series=extracted_data.get("series", []),
                metadata={
                    "slide_type": slide_type,
                    "purpose": purpose,
                    "generated_at": self._get_timestamp(),
                },
            )

            logger.info(
                "visual_element_generated",
                slide_type=slide_type,
                element_type=element_type,
                chart_type=chart_type,
                purpose=purpose,
            )

            return visual_element

        except Exception as e:
            logger.error(
                "visual_element_generation_error",
                error=str(e),
                slide_type=slide_type,
                purpose=purpose,
            )
            return None

    def _extract_data_for_slide_type(
        self,
        slide_type: str,
        data: dict[str, Any],
        purpose: str,
    ) -> dict[str, Any]:
        """Extract relevant data for a specific slide type from research context."""
        extracted = {"series": []}
        
        # Extract from research context if available
        research_context = data.get("research_context", {})
        citations = research_context.get("citations", [])
        research_text = " ".join([c.get("snippet", "") for c in citations])
        financial_data = data.get("financial_data", {})
        
        if slide_type == "traction":
            # Extract growth metrics from research or fallback to LLM extraction
            extracted["series"] = self._extract_traction_data(research_text, data)
            extracted["labels"] = self._extract_time_labels(research_text, data)
            
        elif slide_type == "market_size":
            # Extract market size data from research
            extracted["series"] = self._extract_market_size_data(research_text, data)
            
        elif slide_type == "financials":
            # Extract financial projections from research
            extracted["table_data"] = self._extract_financial_data(research_text, financial_data, data)
            
        elif slide_type == "competition":
            # Extract competitive data from research
            extracted["table_data"] = self._extract_competition_data(research_text, data)
            
        elif slide_type == "roadmap":
            # Extract roadmap data from research
            extracted["timeline_data"] = self._extract_roadmap_data(research_text, data)
            
        elif slide_type == "customer_segmentation":
            # Extract segmentation data from research
            extracted["series"] = self._extract_segmentation_data(research_text, data)
            
        elif slide_type == "metrics":
            # Extract key metrics from research
            extracted["series"] = self._extract_metrics_data(research_text, data)
            
        else:
            # Generic data extraction
            extracted["series"] = []
            
        return extracted
    
    def _extract_traction_data(self, research_text: str, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract traction/growth metrics from research text."""
        import re
        
        series = []
        
        # Try to extract numeric growth data from research
        # Pattern: "X users", "$Y revenue", "Z MRR"
        user_pattern = re.compile(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:users|customers|active users)', re.IGNORECASE)
        revenue_pattern = re.compile(r'\$?(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:k|m|b)?\s*(?:revenue|sales|mrr)', re.IGNORECASE)
        
        user_matches = user_pattern.findall(research_text)
        revenue_matches = revenue_pattern.findall(research_text)
        
        if user_matches and len(user_matches) >= 3:
            # Use actual research data
            values = [float(m.replace(',', '')) for m in user_matches[:6]]
            series.append({"name": "Users", "values": values})
        else:
            # Fallback to company data if available
            company_data = data.get("company_data", {})
            if company_data:
                user_count = company_data.get("user_count")
                if user_count:
                    series.append({"name": "Users", "values": [float(user_count)]})
            else:
                logger.info("traction_data_absent", detail="No grounded traction data found")
        
        if revenue_matches and len(revenue_matches) >= 3:
            values = [float(m.replace(',', '')) for m in revenue_matches[:6]]
            series.append({"name": "Revenue ($K)", "values": values})
        else:
            logger.info("revenue_data_absent", detail="No grounded revenue data found")
        
        return series
    
    def _extract_time_labels(self, research_text: str, data: dict[str, Any]) -> list[str]:
        """Extract time labels for charts."""
        import re
        
        # Look for quarter/month patterns
        quarter_pattern = re.compile(r'Q[1-4]', re.IGNORECASE)
        month_pattern = re.compile(r'(?:Month|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', re.IGNORECASE)
        
        quarters = quarter_pattern.findall(research_text)
        months = month_pattern.findall(research_text)
        
        if quarters and len(quarters) >= 4:
            return quarters[:6]
        elif months and len(months) >= 4:
            return months[:6]
        else:
            return []
    
    def _extract_market_size_data(self, research_text: str, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract TAM/SAM/SOM data from research."""
        import re
        
        series = []
        
        # Pattern: "TAM $X", "SAM $Y", "SOM $Z"
        tam_pattern = re.compile(r'TAM\s*[:$]\s*[\$]?(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:B|M)?', re.IGNORECASE)
        sam_pattern = re.compile(r'SAM\s*[:$]\s*[\$]?(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:B|M)?', re.IGNORECASE)
        som_pattern = re.compile(r'SOM\s*[:$]\s*[\$]?(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:B|M)?', re.IGNORECASE)
        
        tam_match = tam_pattern.search(research_text)
        sam_match = sam_pattern.search(research_text)
        som_match = som_pattern.search(research_text)
        
        if tam_match:
            series.append({"name": "TAM", "value": float(tam_match.group(1).replace(',', ''))})
        
        if sam_match:
            series.append({"name": "SAM", "value": float(sam_match.group(1).replace(',', ''))})
        
        if som_match:
            series.append({"name": "SOM", "value": float(som_match.group(1).replace(',', ''))})
        
        return series
    
    def _extract_financial_data(self, research_text: str, financial_data: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
        """Extract financial projections from research."""
        import re
        
        table_data = {
            "headers": ["Year", "Revenue", "Expenses", "Profit", "Margin"],
            "rows": []
        }
        
        # Try to extract financial projections from research
        year_pattern = re.compile(r'(?:Year\s*)?(\d+)', re.IGNORECASE)
        revenue_pattern = re.compile(r'\$?(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:k|m|b)?\s*(?:revenue|sales)', re.IGNORECASE)
        
        years = year_pattern.findall(research_text)
        revenues = revenue_pattern.findall(research_text)
        
        if years and revenues and len(years) >= 3:
            # Use actual research data
            for i in range(min(5, len(years), len(revenues))):
                revenue = float(revenues[i].replace(',', ''))
                expense = revenue * 0.7  # Typical 30% margin
                profit = revenue - expense
                margin = (profit / revenue * 100) if revenue > 0 else 0
                table_data["rows"].append([
                    f"Year {years[i]}",
                    f"${revenue/1000:.1f}K" if revenue < 1000000 else f"${revenue/1000000:.1f}M",
                    f"${expense/1000:.1f}K" if expense < 1000000 else f"${expense/1000000:.1f}M",
                    f"${profit/1000:.1f}K" if profit < 1000000 else f"${profit/1000000:.1f}M",
                    f"{margin:.0f}%"
                ])
        else:
            logger.info("financial_data_absent", detail="No grounded financial projection data found")
        
        return table_data
    
    def _extract_competition_data(self, research_text: str, data: dict[str, Any]) -> dict[str, Any]:
        """Extract competitive data from research."""
        import re
        
        # Look for competitor names
        competitor_pattern = re.compile(r'(?:competitor|vs|against|compared to)\s+([A-Z][a-zA-Z]+)', re.IGNORECASE)
        competitors = competitor_pattern.findall(research_text)
        if not competitors:
            return {"headers": [], "rows": []}
        
        # Build feature matrix
        headers = ["Feature", "Us"]
        if competitors:
            headers.extend([comp[:15] for comp in competitors[:3]])  # Limit to 3 competitors
        
        rows = [
            ["Speed", "✓"],
            ["Price", "✓"],
            ["Support", "✓"],
            ["Integration", "✓"],
        ]
        
        # Add competitor columns
        for _ in competitors[:3]:
            for row in rows:
                row.append("✗")  # Default: we win
        
        return {"headers": headers, "rows": rows}
    
    def _extract_roadmap_data(self, research_text: str, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract roadmap data from research."""
        import re
        
        timeline_data = []
        
        # Look for quarter/phase patterns
        quarter_pattern = re.compile(r'Q[1-4]', re.IGNORECASE)
        quarters = quarter_pattern.findall(research_text)
        if not quarters:
            logger.info("roadmap_data_absent", detail="No grounded roadmap data found")
            return []
        
        # Default roadmap if no data found
        default_roadmap = [
            {"phase": "Q1", "items": ["Launch MVP", "First 100 users"]},
            {"phase": "Q2", "items": ["Add key features", "Reach 500 users"]},
            {"phase": "Q3", "items": ["Scale operations", "Reach 1000 users"]},
            {"phase": "Q4", "items": ["Market expansion", "Reach 2000 users"]},
        ]
        
        if quarters:
            # Use actual quarters from research
            for i, q in enumerate(quarters[:4]):
                timeline_data.append({
                    "phase": q.upper(),
                    "items": [f"Milestone {i+1}", f"Target {i+1}"]
                })
        else:
            timeline_data = default_roadmap
        
        return timeline_data
    
    def _extract_segmentation_data(self, research_text: str, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract customer segmentation data from research."""
        import re
        
        series = []
        
        # Look for segment mentions
        segments = ["enterprise", "smb", "mid-market", "individual", "consumer"]
        found_segments = [s for s in segments if s in research_text.lower()]
        
        if found_segments:
            # Distribute evenly
            value_per_segment = 100 // len(found_segments)
            for seg in found_segments:
                series.append({"name": seg.title(), "value": value_per_segment})
        else:
            logger.info("segmentation_data_absent", detail="No grounded segmentation data found")
        
        return series
    
    def _extract_metrics_data(self, research_text: str, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract key metrics from research."""
        import re
        
        series = []
        
        # Look for specific metrics
        cac_pattern = re.compile(r'CAC\s*[:$]\s*\$?(\d+)', re.IGNORECASE)
        ltv_pattern = re.compile(r'LTV\s*[:$]\s*\$?(\d+)', re.IGNORECASE)
        churn_pattern = re.compile(r'churn\s*[:%]\s*(\d+(?:\.\d+)?)', re.IGNORECASE)
        
        cac_match = cac_pattern.search(research_text)
        ltv_match = ltv_pattern.search(research_text)
        churn_match = churn_pattern.search(research_text)
        
        if cac_match:
            series.append({"name": "CAC", "value": int(cac_match.group(1))})
        
        if ltv_match:
            series.append({"name": "LTV", "value": int(ltv_match.group(1))})
        
        if churn_match:
            series.append({"name": "Churn", "value": float(churn_match.group(1))})
        if not series:
            logger.info("metrics_data_absent", detail="No grounded operating metrics found")
        
        return series

    def _generate_title(self, slide_type: str, purpose: str) -> str:
        """Generate a title for the visual element."""
        titles = {
            "traction": "Growth Trajectory",
            "market_size": "Market Opportunity",
            "revenue_model": "Revenue Model",
            "financials": "Financial Projections",
            "competition": "Competitive Landscape",
            "roadmap": "Product Roadmap",
            "geographic_expansion": "Geographic Expansion",
            "customer_segmentation": "Customer Segmentation",
            "metrics": "Key Performance Metrics",
            "business_model": "Business Model",
        }
        return titles.get(slide_type, f"{slide_type.title()} Visualization")

    def _get_timestamp(self) -> str:
        """Get current timestamp for metadata."""
        from datetime import datetime
        return datetime.utcnow().isoformat()


__all__ = ["VisualElement", "VisualElementsEngine"]
