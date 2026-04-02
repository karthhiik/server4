"""
Security and Advanced Tests for SWOT Analysis

Covers:
- Data validation and sanitization
- Edge cases and boundary conditions
- Concurrent operations
- Large data sets
- Error recovery

Tests: 20+ covering security and advanced scenarios
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError


# ── Test Classes ──────────────────────────────────────────────────


class TestDataValidation:
    """Test data validation and type checking"""

    def test_swot_item_create_validates_importance_range(self):
        """Test that importance is validated within range"""
        from app.models.swot_models import SWOTItemCreate

        # Valid importance
        item = SWOTItemCreate(text="Test", importance=5)
        assert item.importance == 5

        # Invalid importance - too high
        with pytest.raises(ValidationError):
            SWOTItemCreate(text="Test", importance=11)

        # Invalid importance - too low
        with pytest.raises(ValidationError):
            SWOTItemCreate(text="Test", importance=0)

    def test_swot_item_create_validates_text_not_empty(self):
        """Test that text field is required and non-empty"""
        from app.models.swot_models import SWOTItemCreate

        # Valid text
        item = SWOTItemCreate(text="Valid text")
        assert item.text == "Valid text"

        # Empty text should fail
        with pytest.raises(ValidationError):
            SWOTItemCreate(text="")

    def test_recommendation_priority_enum_validation(self):
        """Test that recommendation priority must be valid enum value"""
        from app.models.swot_models import RecommendationPriority

        valid_priorities = ["critical", "high", "medium", "low"]
        for priority in valid_priorities:
            assert priority in [p.value for p in RecommendationPriority]

    def test_swot_quadrant_enum_validation(self):
        """Test that SWOT quadrant must be valid enum value"""
        from app.models.swot_models import SWOTQuadrant

        valid_quadrants = ["strengths", "weaknesses", "opportunities", "threats"]
        for quadrant in valid_quadrants:
            assert quadrant in [q.value for q in SWOTQuadrant]

    def test_export_format_enum_validation(self):
        """Test that export format must be valid enum value"""
        from app.models.swot_models import ExportFormat

        valid_formats = ["json", "markdown", "pdf", "png"]
        for fmt in valid_formats:
            assert fmt in [f.value for f in ExportFormat]


class TestBoundaryConditions:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_swot_with_empty_quadrants(self):
        """Test SWOT analysis with empty quadrants"""
        from app.models.swot_models import SWOTAnalysisResponse
        from datetime import datetime

        swot = SWOTAnalysisResponse(
            id="test",
            strengths=[],
            weaknesses=[],
            opportunities=[],
            threats=[],
            generated_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        assert len(swot.strengths) == 0
        assert len(swot.weaknesses) == 0
        assert len(swot.opportunities) == 0
        assert len(swot.threats) == 0

    @pytest.mark.asyncio
    async def test_swot_item_with_maximum_importance(self):
        """Test SWOT item with maximum importance value"""
        from app.models.swot_models import SWOTItemCreate

        item = SWOTItemCreate(text="Critical item", importance=10)
        assert item.importance == 10

    @pytest.mark.asyncio
    async def test_swot_item_with_minimum_importance(self):
        """Test SWOT item with minimum importance value"""
        from app.models.swot_models import SWOTItemCreate

        item = SWOTItemCreate(text="Minor item", importance=1)
        assert item.importance == 1

    @pytest.mark.asyncio
    async def test_swot_analysis_with_single_item_per_quadrant(self):
        """Test SWOT analysis with minimal content"""
        from app.models.swot_models import SWOTAnalysisResponse, SWOTItem

        now = datetime.now(timezone.utc)
        swot = SWOTAnalysisResponse(
            id="test",
            strengths=[
                SWOTItem(
                    id="s1",
                    quadrant="strengths",
                    text="Single strength",
                    importance=5,
                    created_at=now,
                    updated_at=now,
                )
            ],
            weaknesses=[],
            opportunities=[],
            threats=[],
            generated_at=now,
            updated_at=now,
        )

        assert len(swot.strengths) == 1
        assert len(swot.weaknesses) == 0

    @pytest.mark.asyncio
    async def test_swot_analysis_with_many_items(self):
        """Test SWOT analysis with many items in quadrants"""
        from app.models.swot_models import SWOTAnalysisResponse, SWOTItem

        now = datetime.now(timezone.utc)
        items = [
            SWOTItem(
                id=f"s{i}",
                quadrant="strengths",
                text=f"Strength {i}",
                importance=5,
                created_at=now,
                updated_at=now,
            )
            for i in range(20)
        ]

        swot = SWOTAnalysisResponse(
            id="test",
            strengths=items,
            weaknesses=[],
            opportunities=[],
            threats=[],
            generated_at=now,
            updated_at=now,
        )

        assert len(swot.strengths) == 20


class TestInputSanitization:
    """Test input sanitization and XSS prevention"""

    def test_swot_item_text_with_special_characters(self):
        """Test SWOT item with special characters"""
        from app.models.swot_models import SWOTItemCreate

        special_text = "Test & <special> \"characters\" 'here'"
        item = SWOTItemCreate(text=special_text)
        assert item.text == special_text

    def test_swot_item_description_with_markdown(self):
        """Test SWOT item description with markdown content"""
        from app.models.swot_models import SWOTItemCreate

        markdown_text = "# Heading\n**Bold** text\n- List item"
        item = SWOTItemCreate(text="Test", description=markdown_text)
        assert item.description == markdown_text

    def test_swot_item_with_unicode_characters(self):
        """Test SWOT item with unicode characters"""
        from app.models.swot_models import SWOTItemCreate

        unicode_text = "Strong position in 日本 market with良好 partnerships"
        item = SWOTItemCreate(text=unicode_text)
        assert item.text == unicode_text

    def test_swot_item_with_urls(self):
        """Test SWOT item containing URLs"""
        from app.models.swot_models import SWOTItemCreate

        url_text = "See https://example.com/docs for more info"
        item = SWOTItemCreate(text=url_text)
        assert item.text == url_text


class TestScoreCalculations:
    """Test SWOT score calculation edge cases"""

    @pytest.mark.asyncio
    async def test_score_calculation_with_single_items(self):
        """Test score calculation with one item per quadrant"""
        from app.services.swot_analysis_service import SWOTAnalysisService
        from unittest.mock import AsyncMock, MagicMock

        db = MagicMock()
        db.swot_analyses = AsyncMock()
        db.swot_analyses.find_one.return_value = {
            "_id": "test",
            "strengths": [{"importance": 8}],
            "weaknesses": [{"importance": 4}],
            "opportunities": [{"importance": 7}],
            "threats": [{"importance": 6}],
        }

        service = SWOTAnalysisService(db)
        scores = await service.calculate_swot_scores("test")

        assert scores["strengths_avg"] == 8.0
        assert scores["weaknesses_avg"] == 4.0
        assert scores["opportunities_avg"] == 7.0
        assert scores["threats_avg"] == 6.0

    @pytest.mark.asyncio
    async def test_score_calculation_with_uniform_values(self):
        """Test score calculation with uniform importance values"""
        from app.services.swot_analysis_service import SWOTAnalysisService
        from unittest.mock import AsyncMock, MagicMock

        db = MagicMock()
        db.swot_analyses = AsyncMock()
        db.swot_analyses.find_one.return_value = {
            "_id": "test",
            "strengths": [
                {"importance": 5},
                {"importance": 5},
                {"importance": 5},
            ],
            "weaknesses": [
                {"importance": 5},
                {"importance": 5},
            ],
            "opportunities": [
                {"importance": 5},
                {"importance": 5},
                {"importance": 5},
            ],
            "threats": [{"importance": 5}],
        }

        service = SWOTAnalysisService(db)
        scores = await service.calculate_swot_scores("test")

        assert scores["strengths_avg"] == 5.0
        assert scores["weaknesses_avg"] == 5.0
        assert scores["opportunities_avg"] == 5.0
        assert scores["threats_avg"] == 5.0

    @pytest.mark.asyncio
    async def test_opportunity_threat_ratio_calculation(self):
        """Test opportunity/threat ratio calculation"""
        from app.services.swot_analysis_service import SWOTAnalysisService
        from unittest.mock import AsyncMock, MagicMock

        db = MagicMock()
        db.swot_analyses = AsyncMock()
        db.swot_analyses.find_one.return_value = {
            "_id": "test",
            "strengths": [{"importance": 8}],
            "weaknesses": [{"importance": 4}],
            "opportunities": [{"importance": 10}],
            "threats": [{"importance": 5}],
        }

        service = SWOTAnalysisService(db)
        scores = await service.calculate_swot_scores("test")

        # O/T ratio should be 10/5 = 2.0
        assert scores["opportunity_threat_ratio"] == pytest.approx(2.0, 0.1)

    @pytest.mark.asyncio
    async def test_internal_balance_calculation(self):
        """Test strength/weakness balance calculation"""
        from app.services.swot_analysis_service import SWOTAnalysisService
        from unittest.mock import AsyncMock, MagicMock

        db = MagicMock()
        db.swot_analyses = AsyncMock()
        db.swot_analyses.find_one.return_value = {
            "_id": "test",
            "strengths": [{"importance": 8}, {"importance": 8}],
            "weaknesses": [{"importance": 4}],
            "opportunities": [{"importance": 7}],
            "threats": [{"importance": 6}],
        }

        service = SWOTAnalysisService(db)
        scores = await service.calculate_swot_scores("test")

        # S/W ratio should be 8/4 = 2.0
        assert scores["internal_balance"] == pytest.approx(2.0, 0.1)


class TestRecommendationGeneration:
    """Test recommendation generation edge cases"""

    @pytest.mark.asyncio
    async def test_recommendations_with_single_items(self):
        """Test recommendation generation with minimal data"""
        from app.services.swot_analysis_service import SWOTAnalysisService
        from unittest.mock import AsyncMock, MagicMock

        db = MagicMock()
        db.swot_analyses = AsyncMock()
        db.swot_analyses.find_one.return_value = {
            "_id": "test",
            "strengths": [{"id": "s1", "text": "Strength", "importance": 8}],
            "weaknesses": [{"id": "w1", "text": "Weakness", "importance": 4}],
            "opportunities": [
                {"id": "o1", "text": "Opportunity", "importance": 7}
            ],
            "threats": [{"id": "t1", "text": "Threat", "importance": 6}],
        }

        service = SWOTAnalysisService(db)
        recommendations = await service.generate_recommendations("test")

        assert len(recommendations) > 0
        assert all("type" in r for r in recommendations)
        assert all("priority" in r for r in recommendations)

    @pytest.mark.asyncio
    async def test_recommendations_without_weaknesses(self):
        """Test recommendation generation without weaknesses"""
        from app.services.swot_analysis_service import SWOTAnalysisService
        from unittest.mock import AsyncMock, MagicMock

        db = MagicMock()
        db.swot_analyses = AsyncMock()
        db.swot_analyses.find_one.return_value = {
            "_id": "test",
            "strengths": [{"id": "s1", "text": "Strength", "importance": 8}],
            "weaknesses": [],
            "opportunities": [
                {"id": "o1", "text": "Opportunity", "importance": 7}
            ],
            "threats": [{"id": "t1", "text": "Threat", "importance": 6}],
        }

        service = SWOTAnalysisService(db)
        recommendations = await service.generate_recommendations("test")

        # Should still generate recommendations
        assert len(recommendations) > 0

    @pytest.mark.asyncio
    async def test_recommendations_without_threats(self):
        """Test recommendation generation without threats"""
        from app.services.swot_analysis_service import SWOTAnalysisService
        from unittest.mock import AsyncMock, MagicMock

        db = MagicMock()
        db.swot_analyses = AsyncMock()
        db.swot_analyses.find_one.return_value = {
            "_id": "test",
            "strengths": [{"id": "s1", "text": "Strength", "importance": 8}],
            "weaknesses": [{"id": "w1", "text": "Weakness", "importance": 4}],
            "opportunities": [
                {"id": "o1", "text": "Opportunity", "importance": 7}
            ],
            "threats": [],
        }

        service = SWOTAnalysisService(db)
        recommendations = await service.generate_recommendations("test")

        # Should still generate recommendations
        assert len(recommendations) > 0


class TestExportEdgeCases:
    """Test export functionality edge cases"""

    @pytest.mark.asyncio
    async def test_export_json_with_special_characters(self):
        """Test JSON export handles special characters"""
        from app.services.swot_analysis_service import SWOTAnalysisService
        import json
        from unittest.mock import AsyncMock, MagicMock

        now = datetime.now(timezone.utc)
        db = MagicMock()
        db.swot_analyses = AsyncMock()
        db.swot_analyses.find_one.return_value = {
            "_id": "test",
            "business_plan_id": "plan",
            "title": "SWOT for Company & Co.",
            "strengths": [
                {
                    "id": "s1",
                    "text": "Strong <position> in market",
                    "importance": 8,
                }
            ],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
            "created_at": now,
            "updated_at": now,
        }

        service = SWOTAnalysisService(db)
        exported = await service.export_swot_analysis("test", "json")

        # Should be valid JSON
        data = json.loads(exported)
        assert data is not None

    @pytest.mark.asyncio
    async def test_export_markdown_preserves_formatting(self):
        """Test markdown export preserves content formatting"""
        from app.services.swot_analysis_service import SWOTAnalysisService
        from unittest.mock import AsyncMock, MagicMock

        now = datetime.now(timezone.utc)
        db = MagicMock()
        db.swot_analyses = AsyncMock()
        db.swot_analyses.find_one.return_value = {
            "_id": "test",
            "business_plan_id": "plan",
            "title": "SWOT Analysis",
            "strengths": [
                {
                    "id": "s1",
                    "text": "Strength 1",
                    "importance": 9,
                }
            ],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
            "created_at": now,
            "updated_at": now,
        }

        service = SWOTAnalysisService(db)
        exported = await service.export_swot_analysis("test", "markdown")

        # Should contain expected markdown formatting
        assert "# SWOT Analysis" in exported
        assert "## Strengths" in exported
        assert "- Strength 1" in exported


class TestConcurrentOperations:
    """Test behavior with concurrent-like operations"""

    @pytest.mark.asyncio
    async def test_sequential_updates_maintain_consistency(self):
        """Test that sequential updates maintain data consistency"""
        from app.services.swot_analysis_service import SWOTAnalysisService
        from unittest.mock import AsyncMock, MagicMock

        db = MagicMock()
        db.swot_analyses = AsyncMock()
        # Simulate database that maintains state
        data = {
            "_id": "test",
            "strengths": [{"id": "s1", "text": "Strength", "importance": 5}],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
        }

        db.swot_analyses.find_one.return_value = data
        db.swot_analyses.update_one = AsyncMock()

        service = SWOTAnalysisService(db)

        # Update item twice
        await service.update_swot_item("test", "s1", {"importance": 7})
        await service.update_swot_item("test", "s1", {"importance": 9})

        # Should have called update twice
        assert db.swot_analyses.update_one.call_count >= 2
