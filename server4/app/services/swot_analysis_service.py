"""SWOT Analysis Service - Generate, manage, and analyze SWOT data."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.swot_models import (
    ExportFormat,
    RecommendationPriority,
    RecommendationType,
    SWOTAnalysisResponse,
    SWOTItem,
    SWOTQuadrant,
    SWOTRecommendation,
    SWOTScores,
)


class SWOTAnalysisService:
    """Service for SWOT analysis operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize SWOT service with database."""
        self.db = db
        self.collection = db.swot_analyses

    async def generate_swot_analysis(self, business_plan_id: str) -> Dict[str, Any]:
        """Generate SWOT analysis from business plan data.

        Args:
            business_plan_id: ID of the business plan to analyze

        Returns:
            Generated SWOT analysis document
        """
        # Fetch business plan
        bp_collection = self.db.business_plans
        business_plan = await bp_collection.find_one({"_id": business_plan_id})

        if not business_plan:
            raise ValueError(f"Business plan {business_plan_id} not found")

        # Create SWOT analysis document
        swot_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Extract content from business plan sections
        sections = business_plan.get("sections", {})
        strengths = self._extract_strengths(business_plan, sections)
        weaknesses = self._extract_weaknesses(business_plan, sections)
        opportunities = self._extract_opportunities(business_plan, sections)
        threats = self._extract_threats(business_plan, sections)

        swot_doc = {
            "_id": swot_id,
            "business_plan_id": business_plan_id,
            "title": f"SWOT Analysis - {business_plan.get('company_name', 'Untitled')}",
            "strengths": strengths,
            "weaknesses": weaknesses,
            "opportunities": opportunities,
            "threats": threats,
            "created_at": now,
            "updated_at": now,
        }

        # Save to database
        await self.collection.insert_one(swot_doc)

        return swot_doc

    async def get_swot_analysis(self, analysis_id: str) -> Dict[str, Any]:
        """Retrieve a SWOT analysis by ID.

        Args:
            analysis_id: ID of the SWOT analysis

        Returns:
            SWOT analysis document
        """
        doc = await self.collection.find_one({"_id": analysis_id})
        if not doc:
            raise ValueError(f"SWOT analysis {analysis_id} not found")
        return doc

    async def add_swot_item(
        self, analysis_id: str, quadrant: str, item_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add an item to a SWOT quadrant.

        Args:
            analysis_id: ID of the SWOT analysis
            quadrant: Quadrant name (strengths, weaknesses, opportunities, threats)
            item_data: Item data (text, description, importance)

        Returns:
            Created item
        """
        # Validate quadrant
        if quadrant not in [q.value for q in SWOTQuadrant]:
            raise ValueError(f"Invalid quadrant: {quadrant}")

        # Create item
        item_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        item = {
            "id": item_id,
            "quadrant": quadrant,
            "text": item_data.get("text", ""),
            "description": item_data.get("description"),
            "importance": item_data.get("importance", 5),
            "tags": item_data.get("tags", []),
            "created_at": now,
            "updated_at": now,
        }

        # Add to analysis
        await self.collection.update_one(
            {"_id": analysis_id}, {
                "$push": {quadrant: item},
                "$set": {"updated_at": now},
            }
        )

        return item

    async def update_swot_item(
        self, analysis_id: str, item_id: str, updated_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a SWOT item.

        Args:
            analysis_id: ID of the SWOT analysis
            item_id: ID of the item to update
            updated_data: Updated item data

        Returns:
            Updated item
        """
        now = datetime.now(timezone.utc)

        # Find the item to determine quadrant
        doc = await self.get_swot_analysis(analysis_id)
        quadrant = None
        item = None

        for q in [q.value for q in SWOTQuadrant]:
            items = doc.get(q, [])
            for i in items:
                if i.get("id") == item_id:
                    quadrant = q
                    item = i
                    break
            if quadrant:
                break

        if not item:
            return {"error": f"Item {item_id} not found"}

        # Update item
        item.update(updated_data)
        item["updated_at"] = now

        # Update in database
        await self.collection.update_one(
            {"_id": analysis_id, f"{quadrant}.id": item_id},
            {
                "$set": {f"{quadrant}.$": item, "updated_at": now},
            },
        )

        return item

    async def delete_swot_item(self, analysis_id: str, item_id: str) -> bool:
        """Delete a SWOT item.

        Args:
            analysis_id: ID of the SWOT analysis
            item_id: ID of the item to delete

        Returns:
            True if deleted, False if not found
        """
        doc = await self.get_swot_analysis(analysis_id)
        now = datetime.now(timezone.utc)

        # Find and remove item
        for q in [q.value for q in SWOTQuadrant]:
            items = doc.get(q, [])
            new_items = [i for i in items if i.get("id") != item_id]
            if len(new_items) < len(items):
                # Item was found and removed
                await self.collection.update_one(
                    {"_id": analysis_id},
                    {
                        "$set": {q: new_items, "updated_at": now},
                    },
                )
                return True

        return False

    async def calculate_swot_scores(self, analysis_id: str) -> Dict[str, float]:
        """Calculate SWOT scores and metrics.

        Args:
            analysis_id: ID of the SWOT analysis

        Returns:
            Dictionary with calculated scores
        """
        doc = await self.get_swot_analysis(analysis_id)

        strengths = doc.get("strengths", [])
        weaknesses = doc.get("weaknesses", [])
        opportunities = doc.get("opportunities", [])
        threats = doc.get("threats", [])

        # Calculate averages
        strengths_avg = (
            sum(i.get("importance", 5) for i in strengths) / len(strengths)
            if strengths
            else 0
        )
        weaknesses_avg = (
            sum(i.get("importance", 5) for i in weaknesses) / len(weaknesses)
            if weaknesses
            else 0
        )
        opportunities_avg = (
            sum(i.get("importance", 5) for i in opportunities) / len(opportunities)
            if opportunities
            else 0
        )
        threats_avg = (
            sum(i.get("importance", 5) for i in threats) / len(threats)
            if threats
            else 0
        )

        # Calculate strategy health
        # Higher strengths and opportunities = better health
        # Higher weaknesses and threats = worse health
        strategy_health = (
            (strengths_avg + opportunities_avg) / 2 * 0.7
            + (10 - weaknesses_avg) / 2 * 0.15
            + (10 - threats_avg) / 2 * 0.15
        )
        strategy_health = min(10.0, max(0.0, strategy_health))

        # Calculate opportunity/threat ratio
        if threats_avg > 0:
            opportunity_threat_ratio = opportunities_avg / threats_avg
        else:
            opportunity_threat_ratio = opportunities_avg / 0.1 if opportunities_avg > 0 else 1.0

        # Calculate internal balance (strengths vs weaknesses)
        if weaknesses_avg > 0:
            internal_balance = strengths_avg / weaknesses_avg
        else:
            internal_balance = (
                strengths_avg / 0.1 if strengths_avg > 0 else 1.0
            )

        return {
            "strengths_avg": round(strengths_avg, 2),
            "weaknesses_avg": round(weaknesses_avg, 2),
            "opportunities_avg": round(opportunities_avg, 2),
            "threats_avg": round(threats_avg, 2),
            "strategy_health": round(strategy_health, 2),
            "opportunity_threat_ratio": round(opportunity_threat_ratio, 2),
            "internal_balance": round(internal_balance, 2),
        }

    async def generate_recommendations(
        self, analysis_id: str
    ) -> List[Dict[str, Any]]:
        """Generate strategic recommendations from SWOT analysis.

        Args:
            analysis_id: ID of the SWOT analysis

        Returns:
            List of strategic recommendations
        """
        doc = await self.get_swot_analysis(analysis_id)
        scores = await self.calculate_swot_scores(analysis_id)

        strengths = doc.get("strengths", [])
        weaknesses = doc.get("weaknesses", [])
        opportunities = doc.get("opportunities", [])
        threats = doc.get("threats", [])

        now = datetime.now(timezone.utc)
        recommendations = []

        # SO: Leverage Strengths + Opportunities
        if strengths and opportunities:
            actions = [
                f"Use {s['text']} to pursue {o['text']}"
                for s in strengths[:2]
                for o in opportunities[:2]
            ]
            recommendations.append({
                "id": f"so-{uuid.uuid4()}",
                "type": RecommendationType.LEVERAGE.value,
                "title": "Leverage Strategy: Maximize Opportunities",
                "description": "Use organizational strengths to capture emerging opportunities",
                "priority": RecommendationPriority.HIGH.value,
                "actions": actions[:3],
                "created_at": now,
            })

        # ST: Strengths counter Threats (Defensive)
        if strengths and threats:
            actions = [
                f"Leverage {s['text']} to mitigate {t['text']}"
                for s in strengths[:2]
                for t in threats[:2]
            ]
            recommendations.append({
                "id": f"st-{uuid.uuid4()}",
                "type": RecommendationType.DEFENSIVE.value,
                "title": "Defensive Strategy: Counter Threats",
                "description": "Protect market position and mitigate external threats",
                "priority": RecommendationPriority.HIGH.value,
                "actions": actions[:3],
                "created_at": now,
            })

        # WO: Address Weaknesses via Opportunities (Growth)
        if weaknesses and opportunities:
            actions = [
                f"Address {w['text']} to enable {o['text']}"
                for w in weaknesses[:2]
                for o in opportunities[:2]
            ]
            recommendations.append({
                "id": f"wo-{uuid.uuid4()}",
                "type": RecommendationType.GROWTH.value,
                "title": "Growth Strategy: Address Weaknesses",
                "description": "Invest in capability building to unlock opportunities",
                "priority": RecommendationPriority.MEDIUM.value,
                "actions": actions[:3],
                "created_at": now,
            })

        # WT: Weaknesses + Threats (Survival)
        if weaknesses and threats:
            actions = [
                f"Address {w['text']} before {t['text']} impacts business"
                for w in weaknesses[:2]
                for t in threats[:2]
            ]
            recommendations.append({
                "id": f"wt-{uuid.uuid4()}",
                "type": RecommendationType.SURVIVAL.value,
                "title": "Survival Strategy: Risk Mitigation",
                "description": "Minimize risk from combination of weaknesses and threats",
                "priority": RecommendationPriority.CRITICAL.value,
                "actions": actions[:3],
                "created_at": now,
            })

        return recommendations

    async def export_swot_analysis(
        self, analysis_id: str, export_format: str
    ) -> str:
        """Export SWOT analysis in specified format.

        Args:
            analysis_id: ID of the SWOT analysis
            export_format: Format (json, markdown, pdf, png)

        Returns:
            Exported content as string
        """
        doc = await self.get_swot_analysis(analysis_id)
        scores = await self.calculate_swot_scores(analysis_id)
        recommendations = await self.generate_recommendations(analysis_id)

        if export_format == ExportFormat.JSON.value:
            return self._export_json(doc, scores, recommendations)
        elif export_format == ExportFormat.MARKDOWN.value:
            return self._export_markdown(doc, scores, recommendations)
        elif export_format == ExportFormat.PDF.value:
            return self._export_pdf(doc, scores, recommendations)
        elif export_format == ExportFormat.PNG.value:
            return self._export_png(doc, scores, recommendations)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")

    def _export_json(
        self, doc: Dict, scores: Dict, recommendations: List
    ) -> str:
        """Export as JSON."""
        export_data = {
            "id": doc["_id"],
            "business_plan_id": doc.get("business_plan_id"),
            "title": doc.get("title"),
            "strengths": doc.get("strengths", []),
            "weaknesses": doc.get("weaknesses", []),
            "opportunities": doc.get("opportunities", []),
            "threats": doc.get("threats", []),
            "scores": scores,
            "recommendations": recommendations,
            "generated_at": doc["generated_at"].isoformat() if "generated_at" in doc else doc["created_at"].isoformat(),
            "updated_at": doc["updated_at"].isoformat(),
        }
        return json.dumps(export_data, default=str)

    def _export_markdown(
        self, doc: Dict, scores: Dict, recommendations: List
    ) -> str:
        """Export as Markdown."""
        md = f"# SWOT Analysis\n\n"
        md += f"**{doc.get('title', 'SWOT Analysis')}**\n\n"

        # Strengths
        md += "## Strengths\n"
        for item in doc.get("strengths", []):
            md += f"- {item['text']} (Importance: {item['importance']}/10)\n"
        md += "\n"

        # Weaknesses
        md += "## Weaknesses\n"
        for item in doc.get("weaknesses", []):
            md += f"- {item['text']} (Importance: {item['importance']}/10)\n"
        md += "\n"

        # Opportunities
        md += "## Opportunities\n"
        for item in doc.get("opportunities", []):
            md += f"- {item['text']} (Importance: {item['importance']}/10)\n"
        md += "\n"

        # Threats
        md += "## Threats\n"
        for item in doc.get("threats", []):
            md += f"- {item['text']} (Importance: {item['importance']}/10)\n"
        md += "\n"

        # Scores
        md += "## Analysis Scores\n"
        for key, value in scores.items():
            formatted_key = key.replace("_", " ").title()
            md += f"- {formatted_key}: {value}\n"
        md += "\n"

        # Recommendations
        md += "## Strategic Recommendations\n"
        for rec in recommendations:
            md += f"### {rec['title']}\n"
            md += f"**Priority**: {rec['priority']}\n"
            md += f"**Type**: {rec['type']}\n"
            md += "**Actions**:\n"
            for action in rec.get("actions", []):
                md += f"- {action}\n"
            md += "\n"

        return md

    def _export_pdf(
        self, doc: Dict, scores: Dict, recommendations: List
    ) -> str:
        """Export as PDF (placeholder - returns markdown for now)."""
        # In production, would use reportlab or similar
        return self._export_markdown(doc, scores, recommendations)

    def _export_png(
        self, doc: Dict, scores: Dict, recommendations: List
    ) -> str:
        """Export as PNG (placeholder - returns base64 image data)."""
        # In production, would use matplotlib or similar to generate image
        return "PNG_IMAGE_DATA_PLACEHOLDER"

    def _extract_strengths(self, bp: Dict, sections: Dict) -> List[Dict]:
        """Extract strengths from business plan."""
        strengths = []

        # Look for competitive advantage
        if "competitive_advantage" in sections:
            content = sections["competitive_advantage"].get("content", "")
            strengths.append({
                "id": str(uuid.uuid4()),
                "quadrant": "strengths",
                "text": "Competitive Advantage",
                "description": content[:200] if content else None,
                "importance": 9,
                "tags": ["competitive"],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            })

        # Look for experienced team
        if bp.get("team_size"):
            strengths.append({
                "id": str(uuid.uuid4()),
                "quadrant": "strengths",
                "text": "Team Experience",
                "description": f"Team size: {bp['team_size']}",
                "importance": 7,
                "tags": ["team"],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            })

        return strengths

    def _extract_weaknesses(self, bp: Dict, sections: Dict) -> List[Dict]:
        """Extract weaknesses from business plan."""
        weaknesses = []

        # Generic weakness - can be inferred from lack of certain sections
        if not sections.get("market_analysis"):
            weaknesses.append({
                "id": str(uuid.uuid4()),
                "quadrant": "weaknesses",
                "text": "Limited Market Analysis",
                "description": "May benefit from deeper market research",
                "importance": 6,
                "tags": ["market"],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            })

        return weaknesses

    def _extract_opportunities(self, bp: Dict, sections: Dict) -> List[Dict]:
        """Extract opportunities from business plan."""
        opportunities = []

        # Look for market opportunity
        if "market_opportunity" in sections:
            content = sections["market_opportunity"].get("content", "")
            opportunities.append({
                "id": str(uuid.uuid4()),
                "quadrant": "opportunities",
                "text": "Market Opportunity",
                "description": content[:200] if content else None,
                "importance": 8,
                "tags": ["market"],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            })

        # Look for expansion potential
        if bp.get("industry"):
            opportunities.append({
                "id": str(uuid.uuid4()),
                "quadrant": "opportunities",
                "text": f"{bp['industry']} Growth Potential",
                "description": f"Industry: {bp['industry']}",
                "importance": 7,
                "tags": ["industry"],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            })

        return opportunities

    def _extract_threats(self, bp: Dict, sections: Dict) -> List[Dict]:
        """Extract threats from business plan."""
        threats = []

        # Generic competitive threat
        threats.append({
            "id": str(uuid.uuid4()),
            "quadrant": "threats",
            "text": "Market Competition",
            "description": "Competitive pressures in the industry",
            "importance": 7,
            "tags": ["competition"],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })

        return threats
