"""GTM (Go-To-Market) Analysis Service - Generate, manage, and analyze GTM strategy."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.gtm_models import (
    ExportFormat,
    GTMAnalysisResponse,
    GTMMetrics,
    MarketSegment,
    SalesChannel,
    UnitEconomics,
)


class GTMAnalysisService:
    """Service for GTM analysis operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize GTM service with database."""
        self.db = db
        self.collection = db.gtm_analyses

    async def generate_gtm_analysis(self, business_plan_id: str) -> Dict[str, Any]:
        """Generate GTM analysis from business plan data.

        Args:
            business_plan_id: ID of the business plan to analyze

        Returns:
            Generated GTM analysis document
        """
        # Fetch business plan
        bp_collection = self.db.business_plans
        business_plan = await bp_collection.find_one({"_id": business_plan_id})

        if not business_plan:
            raise ValueError(f"Business plan {business_plan_id} not found")

        # Create GTM analysis document
        gtm_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Generate default GTM structure from business plan
        gtm_doc = {
            "_id": gtm_id,
            "business_plan_id": business_plan_id,
            "positioning_statement": f"Market leader in {business_plan.get('industry', 'AI')}",
            "competitive_differentiation": business_plan.get("value_proposition", ""),
            "target_markets": [],
            "sales_channels": [],
            "pricing_strategy": {
                "id": str(uuid.uuid4()),
                "model": "value-based",
                "base_price": 50000,
                "price_range": {"min": 25000, "max": 250000},
                "discount_strategy": "tiered by volume",
                "created_at": now,
                "updated_at": now,
            },
            "execution_timeline": [],
            "success_metrics": {
                "cac": 45000,
                "ltv": 500000,
                "conversion_rate": 0.15,
                "annual_target_revenue": 10000000,
                "unit_economics": {
                    "gross_margin": 0.75,
                    "payback_period_months": 12,
                    "retention_rate": 0.95,
                    "net_dollar_retention": 1.15,
                },
            },
            "created_at": now,
            "updated_at": now,
        }

        # Save to database
        await self.collection.insert_one(gtm_doc)

        return gtm_doc

    async def get_gtm_analysis(self, analysis_id: str) -> Dict[str, Any]:
        """Retrieve a GTM analysis by ID.

        Args:
            analysis_id: ID of the GTM analysis

        Returns:
            GTM analysis document
        """
        doc = await self.collection.find_one({"_id": analysis_id})
        if not doc:
            raise ValueError(f"GTM analysis {analysis_id} not found")
        return doc

    async def add_market_segment(
        self, analysis_id: str, segment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add a market segment to GTM analysis.

        Args:
            analysis_id: ID of the GTM analysis
            segment_data: Market segment data

        Returns:
            Created segment
        """
        gtm = await self.get_gtm_analysis(analysis_id)

        segment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        segment = {
            "id": segment_id,
            **segment_data,
            "created_at": now,
            "updated_at": now,
        }

        # Add segment to GTM
        await self.collection.update_one(
            {"_id": analysis_id}, {"$push": {"target_markets": segment}}
        )

        return segment

    async def update_market_segment(
        self, analysis_id: str, segment_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a market segment.

        Args:
            analysis_id: ID of the GTM analysis
            segment_id: ID of the segment
            update_data: Data to update

        Returns:
            Updated segment
        """
        gtm = await self.get_gtm_analysis(analysis_id)

        # Find and update segment
        updated = False
        for segment in gtm.get("target_markets", []):
            if segment.get("id") == segment_id:
                segment.update(update_data)
                segment["updated_at"] = datetime.now(timezone.utc)
                updated = True
                break

        if not updated:
            raise ValueError(f"Segment {segment_id} not found")

        # Update in database
        await self.collection.update_one(
            {"_id": analysis_id}, {"$set": {"target_markets": gtm["target_markets"]}}
        )

        return segment

    async def delete_market_segment(self, analysis_id: str, segment_id: str) -> bool:
        """Delete a market segment.

        Args:
            analysis_id: ID of the GTM analysis
            segment_id: ID of the segment

        Returns:
            True if deleted, False otherwise
        """
        gtm = await self.get_gtm_analysis(analysis_id)

        # Find and remove segment
        original_count = len(gtm.get("target_markets", []))
        gtm["target_markets"] = [
            s for s in gtm.get("target_markets", []) if s.get("id") != segment_id
        ]

        if len(gtm["target_markets"]) == original_count:
            return False

        # Update in database
        await self.collection.update_one(
            {"_id": analysis_id}, {"$set": {"target_markets": gtm["target_markets"]}}
        )

        return True

    async def add_sales_channel(
        self, analysis_id: str, channel_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add a sales channel to GTM analysis.

        Args:
            analysis_id: ID of the GTM analysis
            channel_data: Sales channel data

        Returns:
            Created channel
        """
        gtm = await self.get_gtm_analysis(analysis_id)

        channel_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        channel = {
            "id": channel_id,
            **channel_data,
            "created_at": now,
            "updated_at": now,
        }

        # Add channel to GTM
        await self.collection.update_one(
            {"_id": analysis_id}, {"$push": {"sales_channels": channel}}
        )

        return channel

    async def update_sales_channel(
        self, analysis_id: str, channel_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a sales channel.

        Args:
            analysis_id: ID of the GTM analysis
            channel_id: ID of the channel
            update_data: Data to update

        Returns:
            Updated channel
        """
        gtm = await self.get_gtm_analysis(analysis_id)

        # Find and update channel
        updated = False
        for channel in gtm.get("sales_channels", []):
            if channel.get("id") == channel_id:
                channel.update(update_data)
                channel["updated_at"] = datetime.now(timezone.utc)
                updated = True
                break

        if not updated:
            raise ValueError(f"Channel {channel_id} not found")

        # Update in database
        await self.collection.update_one(
            {"_id": analysis_id}, {"$set": {"sales_channels": gtm["sales_channels"]}}
        )

        return channel

    async def delete_sales_channel(self, analysis_id: str, channel_id: str) -> bool:
        """Delete a sales channel.

        Args:
            analysis_id: ID of the GTM analysis
            channel_id: ID of the channel

        Returns:
            True if deleted, False otherwise
        """
        gtm = await self.get_gtm_analysis(analysis_id)

        # Find and remove channel
        original_count = len(gtm.get("sales_channels", []))
        gtm["sales_channels"] = [
            c for c in gtm.get("sales_channels", []) if c.get("id") != channel_id
        ]

        if len(gtm["sales_channels"]) == original_count:
            return False

        # Update in database
        await self.collection.update_one(
            {"_id": analysis_id}, {"$set": {"sales_channels": gtm["sales_channels"]}}
        )

        return True

    async def calculate_metrics(self, analysis_id: str) -> Dict[str, Any]:
        """Calculate GTM metrics (CAC, LTV, conversion rates).

        Args:
            analysis_id: ID of the GTM analysis

        Returns:
            Calculated metrics
        """
        gtm = await self.get_gtm_analysis(analysis_id)
        metrics = gtm.get("success_metrics", {})

        # Calculate derived metrics
        cac = metrics.get("cac", 45000)
        ltv = metrics.get("ltv", 500000)
        conversion_rate = metrics.get("conversion_rate", 0.15)

        # Calculate LTV:CAC ratio
        ltv_cac_ratio = ltv / cac if cac > 0 else 0

        # Calculate unit economics
        unit_econ = metrics.get("unit_economics", {})
        gross_margin = unit_econ.get("gross_margin", 0.75)
        payback_months = unit_econ.get("payback_period_months", 12)
        retention = unit_econ.get("retention_rate", 0.95)
        net_dollar_retention = unit_econ.get("net_dollar_retention", 1.15)

        return {
            "cac": cac,
            "ltv": ltv,
            "ltv_cac_ratio": ltv_cac_ratio,
            "conversion_rate": conversion_rate,
            "gross_margin": gross_margin,
            "payback_period_months": payback_months,
            "retention_rate": retention,
            "net_dollar_retention": net_dollar_retention,
            "sales_marketing_spend": metrics.get("sales_marketing_spend", 900000),
            "new_customers_acquired": metrics.get("new_customers_acquired", 20),
            "prospects": metrics.get("prospects", 1000),
            "qualified_deals": metrics.get("qualified_deals", 150),
            "closed_deals": metrics.get("closed_deals", 30),
            "annual_target_revenue": metrics.get("annual_target_revenue", 10000000),
        }

    async def calculate_unit_economics(self, analysis_id: str) -> Dict[str, Any]:
        """Calculate unit economics for GTM strategy.

        Args:
            analysis_id: ID of the GTM analysis

        Returns:
            Unit economics metrics
        """
        gtm = await self.get_gtm_analysis(analysis_id)
        metrics = gtm.get("success_metrics", {})
        unit_econ = metrics.get("unit_economics", {})

        return {
            "gross_margin": unit_econ.get("gross_margin", 0.75),
            "payback_period_months": unit_econ.get("payback_period_months", 12),
            "retention_rate": unit_econ.get("retention_rate", 0.95),
            "net_dollar_retention": unit_econ.get("net_dollar_retention", 1.15),
        }

    async def generate_execution_plan(self, analysis_id: str) -> Dict[str, Any]:
        """Generate execution plan with milestones.

        Args:
            analysis_id: ID of the GTM analysis

        Returns:
            Execution plan with timeline
        """
        gtm = await self.get_gtm_analysis(analysis_id)

        timeline = gtm.get("execution_timeline", [])

        # If no timeline exists, generate default
        if not timeline:
            now = datetime.now(timezone.utc)
            timeline = [
                {
                    "id": "q1_2025",
                    "quarter": "Q1 2025",
                    "milestones": [
                        "Complete product development",
                        "Launch beta program",
                    ],
                    "resources": {"engineers": 5, "salespeople": 2},
                    "status": "in-progress",
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": "q2_2025",
                    "quarter": "Q2 2025",
                    "milestones": ["Launch in primary segment", "5 paying customers"],
                    "resources": {"engineers": 4, "salespeople": 4},
                    "status": "pending",
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": "q3_2025",
                    "quarter": "Q3 2025",
                    "milestones": ["Expand to segment 2", "20 paying customers"],
                    "resources": {"engineers": 4, "salespeople": 6},
                    "status": "pending",
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": "q4_2025",
                    "quarter": "Q4 2025",
                    "milestones": ["Launch partnerships", "$1M ARR"],
                    "resources": {"engineers": 3, "salespeople": 8},
                    "status": "pending",
                    "created_at": now,
                    "updated_at": now,
                },
            ]

        return {"timeline": timeline}

    async def export_gtm_analysis(
        self, analysis_id: str, export_format: str
    ) -> str:
        """Export GTM analysis in specified format.

        Args:
            analysis_id: ID of the GTM analysis
            export_format: Format to export (json, markdown, pdf, png)

        Returns:
            Exported content
        """
        gtm = await self.get_gtm_analysis(analysis_id)

        if export_format == ExportFormat.JSON:
            # Convert datetime objects to ISO format strings
            gtm_copy = self._serialize_for_export(gtm)
            return json.dumps(gtm_copy, indent=2)

        elif export_format == ExportFormat.MARKDOWN:
            return self._export_as_markdown(gtm)

        elif export_format == ExportFormat.PDF:
            # In real implementation, would generate PDF
            return self._export_as_markdown(gtm)

        elif export_format == ExportFormat.PNG:
            # In real implementation, would generate PNG chart
            return json.dumps({"format": "png", "status": "pending"})

        return json.dumps({"error": f"Unsupported format: {export_format}"})

    def _serialize_for_export(self, obj: Any) -> Any:
        """Recursively serialize datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._serialize_for_export(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_for_export(item) for item in obj]
        return obj

    def _export_as_markdown(self, gtm: Dict[str, Any]) -> str:
        """Export GTM analysis as markdown."""
        md = f"# GTM Analysis\n\n"
        md += f"**ID:** {gtm.get('_id')}\n"
        md += f"**Business Plan:** {gtm.get('business_plan_id')}\n\n"

        md += "## Positioning\n\n"
        md += f"**Statement:** {gtm.get('positioning_statement', 'N/A')}\n"
        md += f"**Differentiation:** {gtm.get('competitive_differentiation', 'N/A')}\n\n"

        md += "## Target Markets\n\n"
        for market in gtm.get("target_markets", []):
            md += f"### {market.get('name', 'Unknown')}\n"
            md += f"- TAM: ${market.get('tam', 0):,.0f}\n"
            md += f"- SAM: ${market.get('sam', 0):,.0f}\n"
            md += f"- SOM: ${market.get('som', 0):,.0f}\n"
            md += f"- Growth: {market.get('market_size_growth', 0)*100:.1f}%\n\n"

        md += "## Sales Channels\n\n"
        for channel in gtm.get("sales_channels", []):
            md += f"### {channel.get('name', 'Unknown')}\n"
            md += f"- Effectiveness: {channel.get('effectiveness_score', 0)}/10\n"
            md += f"- Cost/Deal: ${channel.get('estimated_cost_per_deal', 0):,.0f}\n"
            md += f"- Sales Cycle: {channel.get('estimated_sales_cycle', 0)} days\n\n"

        md += "## Pricing Strategy\n\n"
        pricing = gtm.get("pricing_strategy", {})
        md += f"**Model:** {pricing.get('model', 'N/A')}\n"
        md += f"**Base Price:** ${pricing.get('base_price', 0):,.0f}\n\n"

        return md
