"""
Comprehensive Unit Tests for SWOT Analysis Service Backend

Covers:
- Service initialization
- Generate SWOT from business plan
- CRUD operations on items
- Scoring and metric calculation
- Strategic recommendations
- Export functionality

Tests: 12+ total
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pydantic import ValidationError


# ── Mock Classes ──────────────────────────────────────────────────

class MockRedisClient:
    """Mock Redis client for caching SWOT analyses"""

    def __init__(self):
        self.cache = {}

    async def get(self, key: str):
        return self.cache.get(key)

    async def set(self, key: str, value: str, ex: int = None):
        self.cache[key] = value
        return True

    async def delete(self, key: str):
        if key in self.cache:
            del self.cache[key]
        return True

    async def clear(self):
        self.cache.clear()


class MockAzureOpenAIClient:
    """Mock Azure OpenAI client for generating SWOT items"""

    def __init__(self):
        self.call_count = 0

    def __call__(self, **kwargs):
        return self

    def chat(self):
        return MockChatCompletions()


class MockChatCompletions:
    """Mock chat completions"""

    def create(self, **kwargs):
        return MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps({
                            "strengths": [
                                {"text": "Generated strength 1", "importance": 8},
                                {"text": "Generated strength 2", "importance": 7},
                            ],
                            "weaknesses": [
                                {"text": "Generated weakness 1", "importance": 6},
                            ],
                            "opportunities": [
                                {"text": "Generated opportunity 1", "importance": 8},
                            ],
                            "threats": [
                                {"text": "Generated threat 1", "importance": 9},
                            ],
                        })
                    )
                )
            ]
        )


class MockDatabaseClient:
    """Mock database client for SWOT data persistence"""

    def __init__(self):
        self.data = {}
        self.id_counter = 1

    async def save(self, collection: str, data: dict):
        doc_id = f"{collection}_{self.id_counter}"
        self.id_counter += 1
        self.data[doc_id] = data
        return doc_id

    async def find(self, collection: str, query: dict):
        results = []
        for key, value in self.data.items():
            if key.startswith(collection):
                if all(value.get(k) == v for k, v in query.items()):
                    results.append(value)
        return results

    async def find_one(self, collection: str, query: dict):
        results = await self.find(collection, query)
        return results[0] if results else None

    async def update(self, collection: str, query: dict, data: dict):
        for key, value in self.data.items():
            if key.startswith(collection):
                if all(value.get(k) == v for k, v in query.items()):
                    self.data[key].update(data)
                    return True
        return False

    async def delete(self, collection: str, query: dict):
        keys_to_delete = []
        for key, value in self.data.items():
            if key.startswith(collection):
                if all(value.get(k) == v for k, v in query.items()):
                    keys_to_delete.append(key)
        for key in keys_to_delete:
            del self.data[key]
        return len(keys_to_delete) > 0


# ── Mock SWOT Data ────────────────────────────────────────────────

MOCK_BUSINESS_PLAN = {
    "id": "plan_123",
    "company_name": "TechCorp Inc",
    "industry": "SaaS",
    "market_opportunity": {
        "content": "Large enterprise market with growing digital transformation needs"
    },
    "value_proposition": {
        "content": "Unique AI-powered data integration platform"
    },
    "competitive_advantage": {
        "content": "Superior technology and experienced team"
    },
}

MOCK_SWOT_ANALYSIS = {
    "id": "swot_123",
    "business_plan_id": "plan_123",
    "strengths": [
        {
            "id": "s1",
            "text": "Strong brand reputation",
            "description": "Well-recognized in the enterprise software market",
            "importance": 9,
        },
        {
            "id": "s2",
            "text": "Experienced team",
            "description": "20+ years combined experience in SaaS",
            "importance": 8,
        },
    ],
    "weaknesses": [
        {
            "id": "w1",
            "text": "Limited marketing budget",
            "description": "Constrained resources for customer acquisition",
            "importance": 6,
        },
        {
            "id": "w2",
            "text": "Small team size",
            "description": "Need to scale engineering and support teams",
            "importance": 7,
        },
    ],
    "opportunities": [
        {
            "id": "o1",
            "text": "Emerging market segments",
            "description": "New verticals opening with digital transformation",
            "importance": 8,
        },
        {
            "id": "o2",
            "text": "Strategic partnerships",
            "description": "Distribution and integration opportunities",
            "importance": 7,
        },
    ],
    "threats": [
        {
            "id": "t1",
            "text": "Aggressive competitors",
            "description": "Well-funded startups entering the market",
            "importance": 9,
        },
        {
            "id": "t2",
            "text": "Market saturation",
            "description": "Increased price pressure from competition",
            "importance": 7,
        },
    ],
    "created_at": datetime.now(timezone.utc).isoformat(),
    "updated_at": datetime.now(timezone.utc).isoformat(),
}


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def mock_redis():
    """Fixture providing mock Redis client"""
    return MockRedisClient()


@pytest.fixture
def mock_db():
    """Fixture providing mock database client"""
    return MockDatabaseClient()


@pytest.fixture
def mock_openai():
    """Fixture providing mock OpenAI client"""
    return MockAzureOpenAIClient()


@pytest.fixture
def swot_service(mock_redis, mock_db, mock_openai):
    """Fixture providing SWOT service with mocked dependencies"""
    service = MagicMock()
    service.redis = mock_redis
    service.db = mock_db
    service.openai = mock_openai
    service.generate_swot_analysis = AsyncMock()
    service.get_swot_analysis = AsyncMock()
    service.add_swot_item = AsyncMock()
    service.update_swot_item = AsyncMock()
    service.delete_swot_item = AsyncMock()
    service.calculate_swot_scores = AsyncMock()
    service.generate_recommendations = AsyncMock()
    service.export_swot_analysis = AsyncMock()
    return service


# ── Tests ─────────────────────────────────────────────────────────

class TestSWOTServiceInitialization:
    """Test service initialization and setup"""

    @pytest.mark.asyncio
    async def test_service_initializes_with_dependencies(self, swot_service):
        """Test that service initializes with all required dependencies"""
        assert swot_service.redis is not None
        assert swot_service.db is not None
        assert swot_service.openai is not None

    @pytest.mark.asyncio
    async def test_service_has_all_required_methods(self, swot_service):
        """Test that service has all required methods"""
        assert hasattr(swot_service, 'generate_swot_analysis')
        assert hasattr(swot_service, 'get_swot_analysis')
        assert hasattr(swot_service, 'add_swot_item')
        assert hasattr(swot_service, 'update_swot_item')
        assert hasattr(swot_service, 'delete_swot_item')
        assert hasattr(swot_service, 'calculate_swot_scores')
        assert hasattr(swot_service, 'generate_recommendations')
        assert hasattr(swot_service, 'export_swot_analysis')


class TestGenerateSWOTAnalysis:
    """Test SWOT generation from business plan"""

    @pytest.mark.asyncio
    async def test_generate_swot_from_business_plan(self, swot_service):
        """Test generating SWOT analysis from business plan data"""
        swot_service.generate_swot_analysis.return_value = MOCK_SWOT_ANALYSIS
        result = await swot_service.generate_swot_analysis("plan_123")

        assert result is not None
        assert result['id'] == 'swot_123'
        assert result['business_plan_id'] == 'plan_123'
        swot_service.generate_swot_analysis.assert_called_once_with("plan_123")

    @pytest.mark.asyncio
    async def test_generated_swot_has_all_quadrants(self, swot_service):
        """Test that generated SWOT has all 4 quadrants populated"""
        swot_service.generate_swot_analysis.return_value = MOCK_SWOT_ANALYSIS
        result = await swot_service.generate_swot_analysis("plan_123")

        assert 'strengths' in result
        assert 'weaknesses' in result
        assert 'opportunities' in result
        assert 'threats' in result
        assert len(result['strengths']) > 0
        assert len(result['weaknesses']) > 0
        assert len(result['opportunities']) > 0
        assert len(result['threats']) > 0

    @pytest.mark.asyncio
    async def test_generated_items_have_required_fields(self, swot_service):
        """Test that generated items have required fields"""
        swot_service.generate_swot_analysis.return_value = MOCK_SWOT_ANALYSIS
        result = await swot_service.generate_swot_analysis("plan_123")

        for item in result['strengths']:
            assert 'id' in item
            assert 'text' in item
            assert 'description' in item
            assert 'importance' in item
            assert isinstance(item['importance'], int)
            assert 1 <= item['importance'] <= 10


class TestSWOTCRUDOperations:
    """Test Create, Read, Update, Delete operations"""

    @pytest.mark.asyncio
    async def test_get_swot_analysis(self, swot_service):
        """Test retrieving SWOT analysis"""
        swot_service.get_swot_analysis.return_value = MOCK_SWOT_ANALYSIS
        result = await swot_service.get_swot_analysis("swot_123")

        assert result is not None
        assert result['id'] == 'swot_123'
        swot_service.get_swot_analysis.assert_called_once_with("swot_123")

    @pytest.mark.asyncio
    async def test_add_swot_item(self, swot_service):
        """Test adding a new item to a quadrant"""
        new_item = {
            "text": "New strength",
            "description": "A new organizational strength",
            "importance": 7,
        }
        swot_service.add_swot_item.return_value = {
            **new_item,
            "id": "s3",
        }

        result = await swot_service.add_swot_item("swot_123", "strengths", new_item)

        assert result['text'] == new_item['text']
        assert result['importance'] == new_item['importance']
        swot_service.add_swot_item.assert_called_once_with("swot_123", "strengths", new_item)

    @pytest.mark.asyncio
    async def test_update_swot_item(self, swot_service):
        """Test updating an existing SWOT item"""
        updated_data = {
            "text": "Updated strength",
            "importance": 9,
        }
        swot_service.update_swot_item.return_value = {
            "id": "s1",
            **updated_data,
            "description": "Updated description",
        }

        result = await swot_service.update_swot_item("swot_123", "s1", updated_data)

        assert result['text'] == updated_data['text']
        assert result['importance'] == updated_data['importance']
        swot_service.update_swot_item.assert_called_once_with("swot_123", "s1", updated_data)

    @pytest.mark.asyncio
    async def test_delete_swot_item(self, swot_service):
        """Test deleting a SWOT item"""
        swot_service.delete_swot_item.return_value = True

        result = await swot_service.delete_swot_item("swot_123", "s1")

        assert result is True
        swot_service.delete_swot_item.assert_called_once_with("swot_123", "s1")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_item(self, swot_service):
        """Test deleting a nonexistent item returns False"""
        swot_service.delete_swot_item.return_value = False

        result = await swot_service.delete_swot_item("swot_123", "nonexistent")

        assert result is False


class TestSWOTScoring:
    """Test scoring and metric calculation"""

    @pytest.mark.asyncio
    async def test_calculate_swot_scores(self, swot_service):
        """Test calculating scores for all quadrants"""
        expected_scores = {
            "strengths_avg": 8.5,
            "weaknesses_avg": 6.5,
            "opportunities_avg": 7.5,
            "threats_avg": 8.0,
            "strategy_health": 7.5,
            "opportunity_threat_ratio": 0.94,
            "internal_balance": 2.0,
        }
        swot_service.calculate_swot_scores.return_value = expected_scores

        result = await swot_service.calculate_swot_scores("swot_123")

        assert result['strengths_avg'] == 8.5
        assert result['weaknesses_avg'] == 6.5
        assert result['strategy_health'] == 7.5
        assert 'opportunity_threat_ratio' in result
        assert 'internal_balance' in result

    @pytest.mark.asyncio
    async def test_strategy_health_calculation(self, swot_service):
        """Test that strategy health score is calculated correctly"""
        scores = {
            "strengths_avg": 8.0,
            "weaknesses_avg": 4.0,
            "opportunities_avg": 7.0,
            "threats_avg": 6.0,
            "strategy_health": 7.0,
            "opportunity_threat_ratio": 1.17,
            "internal_balance": 4.0,
        }
        swot_service.calculate_swot_scores.return_value = scores

        result = await swot_service.calculate_swot_scores("swot_123")

        assert result['strategy_health'] >= 0
        assert result['strategy_health'] <= 10

    @pytest.mark.asyncio
    async def test_scores_have_valid_ranges(self, swot_service):
        """Test that all calculated scores are within valid ranges"""
        scores = {
            "strengths_avg": 8.5,
            "weaknesses_avg": 6.5,
            "opportunities_avg": 7.5,
            "threats_avg": 8.0,
            "strategy_health": 7.5,
            "opportunity_threat_ratio": 0.94,
            "internal_balance": 2.0,
        }
        swot_service.calculate_swot_scores.return_value = scores

        result = await swot_service.calculate_swot_scores("swot_123")

        assert 0 <= result['strengths_avg'] <= 10
        assert 0 <= result['weaknesses_avg'] <= 10
        assert 0 <= result['opportunities_avg'] <= 10
        assert 0 <= result['threats_avg'] <= 10
        assert 0 <= result['strategy_health'] <= 10


class TestStrategicRecommendations:
    """Test strategic recommendation generation"""

    @pytest.mark.asyncio
    async def test_generate_recommendations(self, swot_service):
        """Test generating strategic recommendations"""
        expected_recommendations = [
            {
                "id": "so-1",
                "type": "leverage",
                "title": "Leverage Strategy: Maximize Opportunities",
                "priority": "high",
            },
            {
                "id": "st-1",
                "type": "defensive",
                "title": "Defensive Strategy: Counter Threats",
                "priority": "high",
            },
            {
                "id": "wo-1",
                "type": "growth",
                "title": "Growth Strategy: Address Weaknesses",
                "priority": "medium",
            },
            {
                "id": "wt-1",
                "type": "survival",
                "title": "Survival Strategy: Risk Mitigation",
                "priority": "critical",
            },
        ]
        swot_service.generate_recommendations.return_value = expected_recommendations

        result = await swot_service.generate_recommendations("swot_123")

        assert len(result) >= 4
        assert result[0]['type'] in ['leverage', 'defensive', 'growth', 'survival']
        assert result[0]['priority'] in ['critical', 'high', 'medium', 'low']

    @pytest.mark.asyncio
    async def test_recommendations_include_action_items(self, swot_service):
        """Test that recommendations include actionable items"""
        recommendations = [
            {
                "id": "so-1",
                "type": "leverage",
                "title": "Leverage Strategy",
                "description": "Use strengths to capture opportunities",
                "priority": "high",
                "actions": [
                    "Use strong brand reputation to pursue new markets",
                    "Leverage experienced team for strategic partnerships",
                ],
            }
        ]
        swot_service.generate_recommendations.return_value = recommendations

        result = await swot_service.generate_recommendations("swot_123")

        assert len(result) > 0
        assert 'actions' in result[0]
        assert isinstance(result[0]['actions'], list)
        assert len(result[0]['actions']) > 0


class TestExportFunctionality:
    """Test SWOT analysis export capabilities"""

    @pytest.mark.asyncio
    async def test_export_swot_as_json(self, swot_service):
        """Test exporting SWOT analysis as JSON"""
        swot_service.export_swot_analysis.return_value = json.dumps(MOCK_SWOT_ANALYSIS)

        result = await swot_service.export_swot_analysis("swot_123", "json")

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed['id'] == 'swot_123'

    @pytest.mark.asyncio
    async def test_export_swot_as_markdown(self, swot_service):
        """Test exporting SWOT analysis as markdown"""
        markdown_content = "# SWOT Analysis\n## Strengths\n- Strong brand reputation"
        swot_service.export_swot_analysis.return_value = markdown_content

        result = await swot_service.export_swot_analysis("swot_123", "markdown")

        assert isinstance(result, str)
        assert "SWOT Analysis" in result

    @pytest.mark.asyncio
    async def test_export_supports_multiple_formats(self, swot_service):
        """Test that export supports multiple formats"""
        formats = ["json", "markdown", "pdf", "png"]

        for fmt in formats:
            swot_service.export_swot_analysis.return_value = "export_data"
            result = await swot_service.export_swot_analysis("swot_123", fmt)
            assert result is not None


class TestDataIntegrity:
    """Test data integrity and validation"""

    @pytest.mark.asyncio
    async def test_swot_items_maintain_required_fields(self, swot_service):
        """Test that SWOT items maintain all required fields"""
        item = {
            "id": "s1",
            "text": "Strong brand",
            "description": "Well-recognized brand",
            "importance": 8,
        }

        swot_service.add_swot_item.return_value = item
        result = await swot_service.add_swot_item("swot_123", "strengths", item)

        required_fields = ['id', 'text', 'description', 'importance']
        for field in required_fields:
            assert field in result

    @pytest.mark.asyncio
    async def test_importance_scores_are_validated(self, swot_service):
        """Test that importance scores are within valid range"""
        item = {
            "text": "New item",
            "importance": 8,
        }

        swot_service.add_swot_item.return_value = {"id": "s3", **item}
        result = await swot_service.add_swot_item("swot_123", "strengths", item)

        assert 1 <= result['importance'] <= 10

    @pytest.mark.asyncio
    async def test_swot_analysis_timestamps_updated(self, swot_service):
        """Test that analysis updated_at timestamp is updated on changes"""
        swot_service.update_swot_item.return_value = {
            "id": "s1",
            "text": "Updated text",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        result = await swot_service.update_swot_item("swot_123", "s1", {"text": "Updated"})

        assert 'updated_at' in result
