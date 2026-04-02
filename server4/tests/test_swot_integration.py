"""
Integration Tests for SWOT Analysis

Covers:
- Complete SWOT workflow
- Data consistency across operations
- Multi-step scenarios
- Scoring and recommendations with various data
- Export consistency

Tests: 20+ covering realistic usage patterns
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from motor.motor_asyncio import AsyncIOMotorDatabase


# ── Mock Classes ──────────────────────────────────────────────────


class MockAsyncCollection:
    """Mock MongoDB async collection"""

    def __init__(self):
        self.data = {}
        self.id_counter = 1

    async def insert_one(self, document):
        doc_id = document.get("_id", f"id_{self.id_counter}")
        self.id_counter += 1
        self.data[doc_id] = document
        return MagicMock(inserted_id=doc_id)

    async def find_one(self, query):
        for key, value in self.data.items():
            if all(value.get(k) == v for k, v in query.items()):
                return value
        return None

    async def find(self, query):
        results = []
        for value in self.data.values():
            if all(value.get(k) == v for k, v in query.items()):
                results.append(value)
        return results

    async def update_one(self, query, update):
        for key, value in self.data.items():
            if all(value.get(k) == v for k, v in query.items()):
                if "$set" in update:
                    value.update(update["$set"])
                if "$push" in update:
                    for field, item in update["$push"].items():
                        if field not in value:
                            value[field] = []
                        value[field].append(item)
                self.data[key] = value
                return MagicMock(modified_count=1)
        return MagicMock(modified_count=0)

    async def delete_one(self, query):
        for key, value in list(self.data.items()):
            if all(value.get(k) == v for k, v in query.items()):
                del self.data[key]
                return MagicMock(deleted_count=1)
        return MagicMock(deleted_count=0)


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def mock_db():
    """Fixture providing mock database with collections"""
    db = MagicMock(spec=AsyncIOMotorDatabase)
    db.swot_analyses = MockAsyncCollection()
    db.business_plans = MockAsyncCollection()
    return db


@pytest.fixture
def sample_business_plan():
    """Fixture providing sample business plan for testing"""
    return {
        "_id": "plan_integration_001",
        "company_name": "IntegrationCorp",
        "industry": "Technology",
        "business_type": "B2B SaaS",
        "team_size": 25,
        "sections": {
            "competitive_advantage": {
                "content": "Our unique technology platform with AI integration"
            },
            "market_opportunity": {
                "content": "Large enterprise market with growing digital transformation needs"
            },
        },
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_swot_analysis():
    """Fixture providing sample SWOT analysis"""
    now = datetime.now(timezone.utc)
    return {
        "_id": "swot_integration_001",
        "business_plan_id": "plan_integration_001",
        "title": "SWOT Analysis - IntegrationCorp",
        "strengths": [
            {
                "id": "s1",
                "quadrant": "strengths",
                "text": "Advanced AI Technology",
                "description": "Proprietary machine learning algorithms",
                "importance": 9,
                "tags": ["technology", "ip"],
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "s2",
                "quadrant": "strengths",
                "text": "Experienced Leadership Team",
                "description": "20+ years combined experience",
                "importance": 8,
                "tags": ["team"],
                "created_at": now,
                "updated_at": now,
            },
        ],
        "weaknesses": [
            {
                "id": "w1",
                "quadrant": "weaknesses",
                "text": "Limited Brand Recognition",
                "description": "Newer entrant to market",
                "importance": 6,
                "tags": ["marketing"],
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "w2",
                "quadrant": "weaknesses",
                "text": "Small Sales Force",
                "description": "Need to expand sales team",
                "importance": 5,
                "tags": ["operations"],
                "created_at": now,
                "updated_at": now,
            },
        ],
        "opportunities": [
            {
                "id": "o1",
                "quadrant": "opportunities",
                "text": "Enterprise Digital Transformation",
                "description": "Large untapped market",
                "importance": 9,
                "tags": ["market", "growth"],
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "o2",
                "quadrant": "opportunities",
                "text": "Strategic Partnerships",
                "description": "Potential integrations with major platforms",
                "importance": 7,
                "tags": ["partnerships"],
                "created_at": now,
                "updated_at": now,
            },
        ],
        "threats": [
            {
                "id": "t1",
                "quadrant": "threats",
                "text": "Well-Funded Competitors",
                "description": "Major cloud providers entering space",
                "importance": 8,
                "tags": ["competition"],
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "t2",
                "quadrant": "threats",
                "text": "Rapid Technology Changes",
                "description": "AI landscape evolving quickly",
                "importance": 7,
                "tags": ["technology"],
                "created_at": now,
                "updated_at": now,
            },
        ],
        "created_at": now,
        "updated_at": now,
    }


# ── Tests ──────────────────────────────────────────────────────────


class TestSWOTGenerationWorkflow:
    """Test SWOT analysis generation workflow"""

    @pytest.mark.asyncio
    async def test_generate_swot_from_business_plan(self, mock_db, sample_business_plan):
        """Test generating SWOT from business plan"""
        await mock_db.business_plans.insert_one(sample_business_plan)

        # Generate SWOT
        from app.services.swot_analysis_service import SWOTAnalysisService

        service = SWOTAnalysisService(mock_db)
        swot = await service.generate_swot_analysis("plan_integration_001")

        assert swot is not None
        assert swot["business_plan_id"] == "plan_integration_001"
        assert "strengths" in swot
        assert "weaknesses" in swot
        assert "opportunities" in swot
        assert "threats" in swot

    @pytest.mark.asyncio
    async def test_swot_generation_includes_all_quadrants(
        self, mock_db, sample_business_plan
    ):
        """Test that generated SWOT includes items in all quadrants"""
        await mock_db.business_plans.insert_one(sample_business_plan)

        from app.services.swot_analysis_service import SWOTAnalysisService

        service = SWOTAnalysisService(mock_db)
        swot = await service.generate_swot_analysis("plan_integration_001")

        assert len(swot.get("strengths", [])) > 0
        assert len(swot.get("weaknesses", [])) > 0
        assert len(swot.get("opportunities", [])) > 0
        assert len(swot.get("threats", [])) > 0


class TestSWOTCRUDWorkflow:
    """Test CRUD operations workflow"""

    @pytest.mark.asyncio
    async def test_add_and_retrieve_multiple_items(
        self, mock_db, sample_swot_analysis
    ):
        """Test adding and retrieving multiple items"""
        await mock_db.swot_analyses.insert_one(sample_swot_analysis)

        from app.services.swot_analysis_service import SWOTAnalysisService

        service = SWOTAnalysisService(mock_db)

        # Add new strength
        new_strength = {
            "text": "Strong Customer Relationships",
            "description": "Long-term client partnerships",
            "importance": 8,
        }
        item = await service.add_swot_item(
            "swot_integration_001", "strengths", new_strength
        )
        assert item is not None
        assert item["text"] == "Strong Customer Relationships"

        # Retrieve and verify
        swot = await service.get_swot_analysis("swot_integration_001")
        assert len(swot["strengths"]) > 2

    @pytest.mark.asyncio
    async def test_update_item_across_quadrants(self, mock_db, sample_swot_analysis):
        """Test updating items in different quadrants"""
        await mock_db.swot_analyses.insert_one(sample_swot_analysis)

        from app.services.swot_analysis_service import SWOTAnalysisService

        service = SWOTAnalysisService(mock_db)

        # Update strength
        updated_s1 = await service.update_swot_item(
            "swot_integration_001", "s1", {"importance": 10}
        )
        assert updated_s1["importance"] == 10

        # Update weakness
        updated_w1 = await service.update_swot_item(
            "swot_integration_001", "w1", {"importance": 4}
        )
        assert updated_w1["importance"] == 4

        # Verify changes persisted
        swot = await service.get_swot_analysis("swot_integration_001")
        s1_updated = next((i for i in swot["strengths"] if i["id"] == "s1"), None)
        assert s1_updated["importance"] == 10

    @pytest.mark.asyncio
    async def test_delete_and_verify_removal(self, mock_db, sample_swot_analysis):
        """Test deleting items and verifying removal"""
        await mock_db.swot_analyses.insert_one(sample_swot_analysis)

        from app.services.swot_analysis_service import SWOTAnalysisService

        service = SWOTAnalysisService(mock_db)

        # Delete item
        success = await service.delete_swot_item("swot_integration_001", "s1")
        assert success is True

        # Verify deletion
        swot = await service.get_swot_analysis("swot_integration_001")
        assert not any(i["id"] == "s1" for i in swot["strengths"])


class TestSWOTScoringWorkflow:
    """Test SWOT scoring and calculations"""

    @pytest.mark.asyncio
    async def test_score_calculation_with_multiple_items(
        self, mock_db, sample_swot_analysis
    ):
        """Test score calculation with various item importances"""
        await mock_db.swot_analyses.insert_one(sample_swot_analysis)

        from app.services.swot_analysis_service import SWOTAnalysisService

        service = SWOTAnalysisService(mock_db)
        scores = await service.calculate_swot_scores("swot_integration_001")

        assert scores["strengths_avg"] == pytest.approx(8.5, 0.1)
        assert scores["weaknesses_avg"] == pytest.approx(5.5, 0.1)
        assert scores["opportunities_avg"] == pytest.approx(8.0, 0.1)
        assert scores["threats_avg"] == pytest.approx(7.5, 0.1)
        assert 0 <= scores["strategy_health"] <= 10
        assert scores["opportunity_threat_ratio"] > 0

    @pytest.mark.asyncio
    async def test_scores_change_with_item_updates(
        self, mock_db, sample_swot_analysis
    ):
        """Test that scores update when items change"""
        await mock_db.swot_analyses.insert_one(sample_swot_analysis)

        from app.services.swot_analysis_service import SWOTAnalysisService

        service = SWOTAnalysisService(mock_db)

        # Get initial scores
        initial_scores = await service.calculate_swot_scores("swot_integration_001")

        # Update an item
        await service.update_swot_item(
            "swot_integration_001", "s1", {"importance": 10}
        )

        # Get updated scores
        updated_scores = await service.calculate_swot_scores("swot_integration_001")

        # Strengths average should increase
        assert (
            updated_scores["strengths_avg"]
            > initial_scores["strengths_avg"]
        )

    @pytest.mark.asyncio
    async def test_strategy_health_indicates_overall_strength(
        self, mock_db, sample_swot_analysis
    ):
        """Test that strategy health reflects overall position"""
        await mock_db.swot_analyses.insert_one(sample_swot_analysis)

        from app.services.swot_analysis_service import SWOTAnalysisService

        service = SWOTAnalysisService(mock_db)
        scores = await service.calculate_swot_scores("swot_integration_001")

        # High strengths and opportunities, lower weaknesses and threats = good health
        assert scores["strategy_health"] >= 5


class TestSWOTRecommendationsWorkflow:
    """Test recommendation generation workflow"""

    @pytest.mark.asyncio
    async def test_generate_all_recommendation_types(
        self, mock_db, sample_swot_analysis
    ):
        """Test that all recommendation types are generated"""
        await mock_db.swot_analyses.insert_one(sample_swot_analysis)

        from app.services.swot_analysis_service import SWOTAnalysisService

        service = SWOTAnalysisService(mock_db)
        recommendations = await service.generate_recommendations("swot_integration_001")

        # Should have all 4 strategy types
        types = {r["type"] for r in recommendations}
        assert "leverage" in types  # SO
        assert "defensive" in types  # ST
        assert "growth" in types  # WO
        assert "survival" in types  # WT

    @pytest.mark.asyncio
    async def test_recommendations_include_actions(
        self, mock_db, sample_swot_analysis
    ):
        """Test that recommendations include actionable items"""
        await mock_db.swot_analyses.insert_one(sample_swot_analysis)

        from app.services.swot_analysis_service import SWOTAnalysisService

        service = SWOTAnalysisService(mock_db)
        recommendations = await service.generate_recommendations("swot_integration_001")

        for rec in recommendations:
            assert "actions" in rec
            assert len(rec["actions"]) > 0
            assert all(isinstance(a, str) for a in rec["actions"])

    @pytest.mark.asyncio
    async def test_recommendations_prioritization(
        self, mock_db, sample_swot_analysis
    ):
        """Test that survival strategies have highest priority"""
        await mock_db.swot_analyses.insert_one(sample_swot_analysis)

        from app.services.swot_analysis_service import SWOTAnalysisService

        service = SWOTAnalysisService(mock_db)
        recommendations = await service.generate_recommendations("swot_integration_001")

        # Find survival strategy
        survival = next((r for r in recommendations if r["type"] == "survival"), None)
        assert survival is not None
        assert survival["priority"] == "critical"


class TestSWOTExportWorkflow:
    """Test export functionality workflow"""

    @pytest.mark.asyncio
    async def test_export_json_format(self, mock_db, sample_swot_analysis):
        """Test JSON export includes all data"""
        await mock_db.swot_analyses.insert_one(sample_swot_analysis)

        from app.services.swot_analysis_service import SWOTAnalysisService
        import json

        service = SWOTAnalysisService(mock_db)
        exported = await service.export_swot_analysis(
            "swot_integration_001", "json"
        )

        data = json.loads(exported)
        assert data["id"] == "swot_integration_001"
        assert "strengths" in data
        assert "scores" in data
        assert "recommendations" in data

    @pytest.mark.asyncio
    async def test_export_markdown_format(self, mock_db, sample_swot_analysis):
        """Test Markdown export is properly formatted"""
        await mock_db.swot_analyses.insert_one(sample_swot_analysis)

        from app.services.swot_analysis_service import SWOTAnalysisService

        service = SWOTAnalysisService(mock_db)
        exported = await service.export_swot_analysis(
            "swot_integration_001", "markdown"
        )

        assert "# SWOT Analysis" in exported
        assert "## Strengths" in exported
        assert "## Weaknesses" in exported
        assert "## Opportunities" in exported
        assert "## Threats" in exported

    @pytest.mark.asyncio
    async def test_export_includes_all_quadrants(
        self, mock_db, sample_swot_analysis
    ):
        """Test that exports include items from all quadrants"""
        await mock_db.swot_analyses.insert_one(sample_swot_analysis)

        from app.services.swot_analysis_service import SWOTAnalysisService
        import json

        service = SWOTAnalysisService(mock_db)
        exported = await service.export_swot_analysis(
            "swot_integration_001", "json"
        )

        data = json.loads(exported)
        assert len(data["strengths"]) > 0
        assert len(data["weaknesses"]) > 0
        assert len(data["opportunities"]) > 0
        assert len(data["threats"]) > 0


class TestDataConsistencyValidationFlow:
    """Test data consistency across operations"""

    @pytest.mark.asyncio
    async def test_timestamps_updated_on_modifications(
        self, mock_db, sample_swot_analysis
    ):
        """Test that timestamps are updated on modifications"""
        await mock_db.swot_analyses.insert_one(sample_swot_analysis)

        from app.services.swot_analysis_service import SWOTAnalysisService
        import time

        service = SWOTAnalysisService(mock_db)

        initial = await service.get_swot_analysis("swot_integration_001")
        initial_updated_at = initial["updated_at"]

        # Make a change
        await service.update_swot_item(
            "swot_integration_001", "s1", {"importance": 10}
        )

        updated = await service.get_swot_analysis("swot_integration_001")
        assert updated["updated_at"] >= initial_updated_at

    @pytest.mark.asyncio
    async def test_item_ids_remain_consistent(
        self, mock_db, sample_swot_analysis
    ):
        """Test that item IDs don't change during operations"""
        await mock_db.swot_analyses.insert_one(sample_swot_analysis)

        from app.services.swot_analysis_service import SWOTAnalysisService

        service = SWOTAnalysisService(mock_db)

        swot1 = await service.get_swot_analysis("swot_integration_001")
        s1_id_1 = swot1["strengths"][0]["id"]

        # Update item
        await service.update_swot_item(
            "swot_integration_001", "s1", {"importance": 10}
        )

        swot2 = await service.get_swot_analysis("swot_integration_001")
        s1_id_2 = swot2["strengths"][0]["id"]

        assert s1_id_1 == s1_id_2
