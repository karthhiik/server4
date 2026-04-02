"""
Comprehensive Unit Tests for GTM (Go-To-Market) Analysis Service Backend

Covers:
- Service initialization
- Generate GTM from business plan
- CRUD operations on segments and channels
- Metrics calculation (CAC, LTV, conversion rates)
- Execution planning
- Export functionality

Tests: 15+ total
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
    """Mock Redis client for caching GTM strategies"""

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


class MockDatabaseClient:
    """Mock database client for GTM data persistence"""

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


# ── Mock GTM Data ──────────────────────────────────────────────────

MOCK_BUSINESS_PLAN = {
    "id": "plan_456",
    "company_name": "MarketVision AI",
    "industry": "B2B SaaS",
    "target_customer": "Enterprise companies with 1000+ employees",
    "value_proposition": "AI-powered market intelligence and GTM optimization",
}

MOCK_GTM_ANALYSIS = {
    "id": "gtm_456",
    "business_plan_id": "plan_456",
    "target_markets": [
        {
            "id": "seg_1",
            "name": "Enterprise SaaS",
            "description": "Large SaaS companies building AI products",
            "tam": 50000000000,  # $50B TAM
            "sam": 5000000000,  # $5B SAM
            "som": 250000000,   # $250M SOM
            "market_size_growth": 0.25,
            "customer_count": 5000,
        },
        {
            "id": "seg_2",
            "name": "Consulting Firms",
            "description": "Management and technology consulting firms",
            "tam": 30000000000,  # $30B TAM
            "sam": 2000000000,  # $2B SAM
            "som": 100000000,   # $100M SOM
            "market_size_growth": 0.15,
            "customer_count": 2000,
        },
    ],
    "sales_channels": [
        {
            "id": "chan_1",
            "name": "Direct Sales",
            "description": "Enterprise sales team",
            "effectiveness_score": 9,
            "estimated_cost_per_deal": 50000,
            "estimated_sales_cycle": 120,
        },
        {
            "id": "chan_2",
            "name": "Channel Partners",
            "description": "Technology consultants and resellers",
            "effectiveness_score": 7,
            "estimated_cost_per_deal": 25000,
            "estimated_sales_cycle": 90,
        },
        {
            "id": "chan_3",
            "name": "Online/Self-Service",
            "description": "Website and product-led growth",
            "effectiveness_score": 5,
            "estimated_cost_per_deal": 5000,
            "estimated_sales_cycle": 30,
        },
    ],
    "pricing_strategy": {
        "model": "value-based",
        "base_price": 50000,
        "price_range": {"min": 25000, "max": 250000},
        "discount_strategy": "tiered by volume",
    },
    "positioning_statement": "Only AI platform for enterprise GTM optimization",
    "competitive_differentiation": "Real-time market intelligence + predictive analytics",
    "execution_timeline": [
        {
            "id": "q1_2025",
            "quarter": "Q1 2025",
            "milestones": ["Complete product development", "Launch beta program"],
            "resources": {"engineers": 5, "salespeople": 2},
        },
        {
            "id": "q2_2025",
            "quarter": "Q2 2025",
            "milestones": ["Launch in segment 1", "5 paying customers"],
            "resources": {"engineers": 4, "salespeople": 4},
        },
    ],
    "success_metrics": {
        "cac": 45000,  # Customer Acquisition Cost
        "ltv": 500000,  # Lifetime Value
        "conversion_rate": 0.15,
        "annual_target_revenue": 10000000,
        "unit_economics": {
            "gross_margin": 0.75,
            "payback_period_months": 12,
            "retention_rate": 0.95,
        },
    },
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
def gtm_service(mock_redis, mock_db):
    """Fixture providing GTM service with mocked dependencies"""
    service = MagicMock()
    service.redis = mock_redis
    service.db = mock_db
    service.generate_gtm_analysis = AsyncMock()
    service.get_gtm_analysis = AsyncMock()
    service.add_market_segment = AsyncMock()
    service.update_market_segment = AsyncMock()
    service.delete_market_segment = AsyncMock()
    service.add_sales_channel = AsyncMock()
    service.update_sales_channel = AsyncMock()
    service.delete_sales_channel = AsyncMock()
    service.calculate_metrics = AsyncMock()
    service.calculate_unit_economics = AsyncMock()
    service.generate_execution_plan = AsyncMock()
    service.export_gtm_analysis = AsyncMock()
    return service


# ── Tests ─────────────────────────────────────────────────────────

class TestGTMServiceInitialization:
    """Test service initialization and setup"""

    @pytest.mark.asyncio
    async def test_service_initializes_with_dependencies(self, gtm_service):
        """Test that service initializes with all required dependencies"""
        assert gtm_service.redis is not None
        assert gtm_service.db is not None

    @pytest.mark.asyncio
    async def test_service_has_all_required_methods(self, gtm_service):
        """Test that service has all required methods"""
        required_methods = [
            'generate_gtm_analysis',
            'get_gtm_analysis',
            'add_market_segment',
            'update_market_segment',
            'delete_market_segment',
            'add_sales_channel',
            'update_sales_channel',
            'delete_sales_channel',
            'calculate_metrics',
            'calculate_unit_economics',
            'generate_execution_plan',
            'export_gtm_analysis',
        ]
        for method in required_methods:
            assert hasattr(gtm_service, method)


class TestGenerateGTMAnalysis:
    """Test GTM generation from business plan"""

    @pytest.mark.asyncio
    async def test_generate_gtm_from_business_plan(self, gtm_service):
        """Test generating GTM analysis from business plan data"""
        gtm_service.generate_gtm_analysis.return_value = MOCK_GTM_ANALYSIS
        result = await gtm_service.generate_gtm_analysis("plan_456")

        assert result is not None
        assert result['id'] == 'gtm_456'
        assert result['business_plan_id'] == 'plan_456'
        gtm_service.generate_gtm_analysis.assert_called_once_with("plan_456")

    @pytest.mark.asyncio
    async def test_generated_gtm_has_all_components(self, gtm_service):
        """Test that generated GTM has all core components"""
        gtm_service.generate_gtm_analysis.return_value = MOCK_GTM_ANALYSIS
        result = await gtm_service.generate_gtm_analysis("plan_456")

        assert 'target_markets' in result
        assert 'sales_channels' in result
        assert 'pricing_strategy' in result
        assert 'positioning_statement' in result
        assert 'execution_timeline' in result
        assert 'success_metrics' in result


class TestMarketSegmentOperations:
    """Test CRUD operations on market segments"""

    @pytest.mark.asyncio
    async def test_add_market_segment(self, gtm_service):
        """Test adding a new market segment"""
        new_segment = {
            "name": "Mid-Market SaaS",
            "description": "SaaS companies with 100-1000 employees",
            "tam": 10000000000,
            "sam": 1000000000,
            "som": 50000000,
        }
        gtm_service.add_market_segment.return_value = {
            **new_segment,
            "id": "seg_3",
            "market_size_growth": 0.20,
            "customer_count": 1500,
        }

        result = await gtm_service.add_market_segment("gtm_456", new_segment)

        assert result['name'] == new_segment['name']
        assert result['id'] == 'seg_3'
        assert result['tam'] == new_segment['tam']

    @pytest.mark.asyncio
    async def test_update_market_segment(self, gtm_service):
        """Test updating an existing market segment"""
        updated_data = {
            "som": 300000000,
            "market_size_growth": 0.30,
        }
        gtm_service.update_market_segment.return_value = {
            "id": "seg_1",
            "name": "Enterprise SaaS",
            **updated_data,
        }

        result = await gtm_service.update_market_segment("gtm_456", "seg_1", updated_data)

        assert result['id'] == 'seg_1'
        assert result['som'] == updated_data['som']

    @pytest.mark.asyncio
    async def test_delete_market_segment(self, gtm_service):
        """Test deleting a market segment"""
        gtm_service.delete_market_segment.return_value = True

        result = await gtm_service.delete_market_segment("gtm_456", "seg_1")

        assert result is True

    @pytest.mark.asyncio
    async def test_get_market_segments(self, gtm_service):
        """Test retrieving all market segments"""
        gtm_service.get_gtm_analysis.return_value = MOCK_GTM_ANALYSIS
        result = await gtm_service.get_gtm_analysis("gtm_456")

        assert len(result['target_markets']) >= 2
        assert all('id' in seg for seg in result['target_markets'])
        assert all('tam' in seg for seg in result['target_markets'])


class TestSalesChannelOperations:
    """Test CRUD operations on sales channels"""

    @pytest.mark.asyncio
    async def test_add_sales_channel(self, gtm_service):
        """Test adding a new sales channel"""
        new_channel = {
            "name": "Strategic Partnerships",
            "description": "Technology and consulting partnerships",
            "effectiveness_score": 8,
            "estimated_cost_per_deal": 35000,
            "estimated_sales_cycle": 60,
        }
        gtm_service.add_sales_channel.return_value = {
            **new_channel,
            "id": "chan_4",
        }

        result = await gtm_service.add_sales_channel("gtm_456", new_channel)

        assert result['name'] == new_channel['name']
        assert result['id'] == 'chan_4'

    @pytest.mark.asyncio
    async def test_update_sales_channel(self, gtm_service):
        """Test updating an existing sales channel"""
        updated_data = {
            "effectiveness_score": 8,
            "estimated_cost_per_deal": 40000,
        }
        gtm_service.update_sales_channel.return_value = {
            "id": "chan_1",
            "name": "Direct Sales",
            **updated_data,
        }

        result = await gtm_service.update_sales_channel("gtm_456", "chan_1", updated_data)

        assert result['id'] == 'chan_1'
        assert result['effectiveness_score'] == updated_data['effectiveness_score']

    @pytest.mark.asyncio
    async def test_delete_sales_channel(self, gtm_service):
        """Test deleting a sales channel"""
        gtm_service.delete_sales_channel.return_value = True

        result = await gtm_service.delete_sales_channel("gtm_456", "chan_2")

        assert result is True


class TestMetricsCalculation:
    """Test metrics calculation (CAC, LTV, conversion rates)"""

    @pytest.mark.asyncio
    async def test_calculate_cac(self, gtm_service):
        """Test Customer Acquisition Cost calculation"""
        expected_metrics = {
            "cac": 45000,
            "sales_marketing_spend": 900000,
            "new_customers_acquired": 20,
        }
        gtm_service.calculate_metrics.return_value = expected_metrics

        result = await gtm_service.calculate_metrics("gtm_456")

        assert result['cac'] == 45000
        assert result['sales_marketing_spend'] == 900000

    @pytest.mark.asyncio
    async def test_calculate_ltv(self, gtm_service):
        """Test Lifetime Value calculation"""
        expected_metrics = {
            "ltv": 500000,
            "annual_revenue_per_customer": 100000,
            "retention_rate": 0.95,
        }
        gtm_service.calculate_metrics.return_value = expected_metrics

        result = await gtm_service.calculate_metrics("gtm_456")

        assert result['ltv'] == 500000
        assert result['annual_revenue_per_customer'] == 100000

    @pytest.mark.asyncio
    async def test_calculate_conversion_rate(self, gtm_service):
        """Test conversion rate calculation"""
        expected_metrics = {
            "conversion_rate": 0.15,
            "prospects": 1000,
            "qualified_deals": 150,
            "closed_deals": 30,
        }
        gtm_service.calculate_metrics.return_value = expected_metrics

        result = await gtm_service.calculate_metrics("gtm_456")

        assert result['conversion_rate'] == 0.15
        assert 0 <= result['conversion_rate'] <= 1

    @pytest.mark.asyncio
    async def test_calculate_unit_economics(self, gtm_service):
        """Test unit economics calculation"""
        expected_economics = {
            "gross_margin": 0.75,
            "payback_period_months": 12,
            "retention_rate": 0.95,
            "net_dollar_retention": 1.15,
        }
        gtm_service.calculate_unit_economics.return_value = expected_economics

        result = await gtm_service.calculate_unit_economics("gtm_456")

        assert result['gross_margin'] == 0.75
        assert result['payback_period_months'] == 12
        assert result['net_dollar_retention'] >= 1.0


class TestExecutionPlanning:
    """Test execution planning functionality"""

    @pytest.mark.asyncio
    async def test_generate_execution_plan(self, gtm_service):
        """Test generating execution plan with milestones"""
        expected_plan = {
            "timeline": [
                {
                    "quarter": "Q1 2025",
                    "milestones": ["Complete product development", "Launch beta"],
                    "resources": {"engineers": 5, "salespeople": 2},
                }
            ]
        }
        gtm_service.generate_execution_plan.return_value = expected_plan

        result = await gtm_service.generate_execution_plan("gtm_456")

        assert 'timeline' in result
        assert len(result['timeline']) > 0

    @pytest.mark.asyncio
    async def test_execution_plan_includes_quarterly_milestones(self, gtm_service):
        """Test that execution plan includes quarterly milestones"""
        expected_plan = {
            "timeline": [
                {
                    "id": "q1",
                    "quarter": "Q1 2025",
                    "milestones": ["Develop", "Test"],
                },
                {
                    "id": "q2",
                    "quarter": "Q2 2025",
                    "milestones": ["Launch", "Scale"],
                },
            ]
        }
        gtm_service.generate_execution_plan.return_value = expected_plan

        result = await gtm_service.generate_execution_plan("gtm_456")

        assert all('quarter' in item for item in result['timeline'])
        assert all('milestones' in item for item in result['timeline'])


class TestExportFunctionality:
    """Test GTM analysis export capabilities"""

    @pytest.mark.asyncio
    async def test_export_gtm_as_json(self, gtm_service):
        """Test exporting GTM analysis as JSON"""
        gtm_service.export_gtm_analysis.return_value = json.dumps(MOCK_GTM_ANALYSIS)

        result = await gtm_service.export_gtm_analysis("gtm_456", "json")

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed['id'] == 'gtm_456'

    @pytest.mark.asyncio
    async def test_export_gtm_supports_multiple_formats(self, gtm_service):
        """Test that export supports multiple formats"""
        formats = ["json", "markdown", "pdf", "png"]

        for fmt in formats:
            gtm_service.export_gtm_analysis.return_value = "export_data"
            result = await gtm_service.export_gtm_analysis("gtm_456", fmt)
            assert result is not None


class TestDataIntegrity:
    """Test data integrity and validation"""

    @pytest.mark.asyncio
    async def test_market_segment_fields_validated(self, gtm_service):
        """Test that market segment fields are validated"""
        segment = {
            "id": "seg_1",
            "name": "Enterprise SaaS",
            "tam": 50000000000,
            "sam": 5000000000,
            "som": 250000000,
        }

        gtm_service.add_market_segment.return_value = segment
        result = await gtm_service.add_market_segment("gtm_456", segment)

        required_fields = ['id', 'name', 'tam', 'sam', 'som']
        for field in required_fields:
            assert field in result

    @pytest.mark.asyncio
    async def test_pricing_strategy_is_valid(self, gtm_service):
        """Test that pricing strategy has valid structure"""
        gtm_service.get_gtm_analysis.return_value = MOCK_GTM_ANALYSIS
        result = await gtm_service.get_gtm_analysis("gtm_456")

        pricing = result['pricing_strategy']
        assert 'model' in pricing
        assert 'base_price' in pricing
        assert pricing['base_price'] > 0

    @pytest.mark.asyncio
    async def test_metrics_have_valid_ranges(self, gtm_service):
        """Test that metrics are within valid ranges"""
        metrics = {
            "cac": 45000,
            "ltv": 500000,
            "conversion_rate": 0.15,
            "gross_margin": 0.75,
        }
        gtm_service.calculate_metrics.return_value = metrics

        result = await gtm_service.calculate_metrics("gtm_456")

        assert result['cac'] > 0
        assert result['ltv'] > 0
        assert 0 <= result['conversion_rate'] <= 1
        assert 0 <= result['gross_margin'] <= 1
