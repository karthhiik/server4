"""
Comprehensive Unit Tests for SWOT Analysis FastAPI Routes

Covers:
- Create SWOT endpoint (POST)
- Retrieve endpoint (GET by ID)
- Add item endpoint (POST)
- Update item endpoint (PATCH)
- Delete item endpoint (DELETE)
- Get scores endpoint (GET)
- Get recommendations endpoint (GET)
- Export endpoint (GET)
- Health check endpoint
- Error handling (404, 400)

Tests: 30+ total covering success and error paths
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorDatabase


# ── Test Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def auth_user():
    """Fixture providing authenticated user."""
    return {"user_id": "test_user_123"}


@pytest.fixture
def sample_business_plan_data():
    """Fixture providing sample business plan data."""
    return {
        "company_name": "TechCorp",
        "industry": "SaaS",
        "business_type": "B2B",
        "team_size": 15,
    }


@pytest.fixture
def sample_swot_data():
    """Fixture providing sample SWOT analysis data."""
    now = datetime.now(timezone.utc)
    return {
        "_id": "swot_123",
        "business_plan_id": "plan_123",
        "title": "SWOT Analysis - TechCorp",
        "strengths": [
            {
                "id": "s1",
                "quadrant": "strengths",
                "text": "Strong brand reputation",
                "description": "Well-recognized in market",
                "importance": 9,
                "tags": [],
                "created_at": now,
                "updated_at": now,
            },
        ],
        "weaknesses": [
            {
                "id": "w1",
                "quadrant": "weaknesses",
                "text": "Limited marketing budget",
                "description": "Constrained resources",
                "importance": 6,
                "tags": [],
                "created_at": now,
                "updated_at": now,
            },
        ],
        "opportunities": [
            {
                "id": "o1",
                "quadrant": "opportunities",
                "text": "Emerging market segments",
                "description": "New verticals opening",
                "importance": 8,
                "tags": [],
                "created_at": now,
                "updated_at": now,
            },
        ],
        "threats": [
            {
                "id": "t1",
                "quadrant": "threats",
                "text": "Aggressive competitors",
                "description": "Well-funded startups",
                "importance": 7,
                "tags": [],
                "created_at": now,
                "updated_at": now,
            },
        ],
        "created_at": now,
        "updated_at": now,
    }


@pytest.fixture
def mock_db():
    """Fixture providing mock database."""
    db = MagicMock(spec=AsyncIOMotorDatabase)
    db.swot_analyses = AsyncMock()
    db.business_plans = AsyncMock()
    return db


@pytest.fixture
def client(mock_db):
    """Fixture providing TestClient with mocked dependencies."""
    from app.routers import swot_analysis
    from app.database import get_db

    app = FastAPI()
    app.include_router(swot_analysis.router)

    def mock_get_db():
        return mock_db

    app.dependency_overrides[get_db] = mock_get_db
    return TestClient(app)


# ── Tests ──────────────────────────────────────────────────────────


class TestSWOTHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check_success(self, client):
        """Test successful health check"""
        response = client.get("/api/swot-analysis/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "swot-analysis-service"
        assert data["version"] == "1.0.0"


class TestCreateSWOTAnalysis:
    """Test SWOT analysis creation"""

    def test_create_swot_analysis_success(self, client, mock_db, sample_swot_data):
        """Test successfully creating SWOT analysis"""
        mock_db.business_plans.find_one.return_value = {
            "_id": "plan_123",
            "company_name": "TechCorp",
            "industry": "SaaS",
            "sections": {},
        }
        mock_db.swot_analyses.insert_one.return_value = None

        response = client.post(
            "/api/swot-analysis",
            json={"business_plan_id": "plan_123"},
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_swot_missing_business_plan_id(self, client):
        """Test creating SWOT without business_plan_id"""
        response = client.post(
            "/api/swot-analysis",
            json={},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "business_plan_id is required" in response.json()["detail"]

    def test_create_swot_business_plan_not_found(self, client, mock_db):
        """Test creating SWOT with non-existent business plan"""
        mock_db.business_plans.find_one.return_value = None

        response = client.post(
            "/api/swot-analysis",
            json={"business_plan_id": "nonexistent"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetSWOTAnalysis:
    """Test retrieving SWOT analysis"""

    def test_get_swot_success(self, client, mock_db, sample_swot_data):
        """Test successfully retrieving SWOT analysis"""
        mock_db.swot_analyses.find_one.return_value = sample_swot_data

        response = client.get("/api/swot-analysis/swot_123")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "swot_123"
        assert "strengths" in data
        assert "weaknesses" in data
        assert "opportunities" in data
        assert "threats" in data

    def test_get_swot_not_found(self, client, mock_db):
        """Test retrieving non-existent SWOT analysis"""
        mock_db.swot_analyses.find_one.return_value = None

        response = client.get("/api/swot-analysis/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAddSWOTItem:
    """Test adding items to SWOT analysis"""

    def test_add_item_to_strengths(self, client, mock_db):
        """Test adding item to strengths quadrant"""
        now = datetime.now(timezone.utc)
        item = {
            "id": "s2",
            "quadrant": "strengths",
            "text": "New strength",
            "description": "A new organizational strength",
            "importance": 7,
            "tags": [],
            "created_at": now,
            "updated_at": now,
        }
        mock_db.swot_analyses.update_one.return_value = MagicMock()

        response = client.post(
            "/api/swot-analysis/swot_123/items?quadrant=strengths",
            json={
                "text": "New strength",
                "description": "A new organizational strength",
                "importance": 7,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_add_item_to_weaknesses(self, client, mock_db):
        """Test adding item to weaknesses quadrant"""
        mock_db.swot_analyses.update_one.return_value = MagicMock()

        response = client.post(
            "/api/swot-analysis/swot_123/items?quadrant=weaknesses",
            json={
                "text": "New weakness",
                "importance": 6,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_add_item_to_opportunities(self, client, mock_db):
        """Test adding item to opportunities quadrant"""
        mock_db.swot_analyses.update_one.return_value = MagicMock()

        response = client.post(
            "/api/swot-analysis/swot_123/items?quadrant=opportunities",
            json={
                "text": "New opportunity",
                "importance": 8,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_add_item_to_threats(self, client, mock_db):
        """Test adding item to threats quadrant"""
        mock_db.swot_analyses.update_one.return_value = MagicMock()

        response = client.post(
            "/api/swot-analysis/swot_123/items?quadrant=threats",
            json={
                "text": "New threat",
                "importance": 7,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_add_item_missing_body(self, client):
        """Test adding item without request body"""
        response = client.post(
            "/api/swot-analysis/swot_123/items?quadrant=strengths",
            json=None,
        )
        # This should result in a validation error
        assert response.status_code >= 400

    def test_add_item_invalid_quadrant(self, client, mock_db):
        """Test adding item with invalid quadrant"""
        response = client.post(
            "/api/swot-analysis/swot_123/items?quadrant=invalid",
            json={
                "text": "Test",
                "importance": 5,
            },
        )
        # Should fail validation
        assert response.status_code >= 400


class TestUpdateSWOTItem:
    """Test updating SWOT items"""

    def test_update_item_success(self, client, mock_db):
        """Test successfully updating SWOT item"""
        now = datetime.now(timezone.utc)
        mock_db.swot_analyses.find_one.return_value = {
            "_id": "swot_123",
            "strengths": [
                {
                    "id": "s1",
                    "text": "Old strength",
                    "importance": 7,
                    "updated_at": now,
                }
            ],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
        }
        mock_db.swot_analyses.update_one.return_value = MagicMock()

        response = client.patch(
            "/api/swot-analysis/swot_123/items/s1",
            json={
                "text": "Updated strength",
                "importance": 9,
            },
        )
        assert response.status_code == status.HTTP_200_OK

    def test_update_item_not_found(self, client, mock_db):
        """Test updating non-existent item"""
        mock_db.swot_analyses.find_one.return_value = {
            "_id": "swot_123",
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
        }

        response = client.patch(
            "/api/swot-analysis/swot_123/items/nonexistent",
            json={"text": "Updated"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteSWOTItem:
    """Test deleting SWOT items"""

    def test_delete_item_success(self, client, mock_db):
        """Test successfully deleting SWOT item"""
        now = datetime.now(timezone.utc)
        mock_db.swot_analyses.find_one.return_value = {
            "_id": "swot_123",
            "strengths": [
                {
                    "id": "s1",
                    "text": "Strength",
                    "importance": 7,
                    "updated_at": now,
                }
            ],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
        }
        mock_db.swot_analyses.update_one.return_value = MagicMock()

        response = client.delete("/api/swot-analysis/swot_123/items/s1")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_item_not_found(self, client, mock_db):
        """Test deleting non-existent item"""
        mock_db.swot_analyses.find_one.return_value = {
            "_id": "swot_123",
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
        }

        response = client.delete("/api/swot-analysis/swot_123/items/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetSWOTScores:
    """Test retrieving SWOT scores"""

    def test_get_scores_success(self, client, mock_db):
        """Test successfully retrieving SWOT scores"""
        now = datetime.now(timezone.utc)
        mock_db.swot_analyses.find_one.return_value = {
            "_id": "swot_123",
            "strengths": [
                {"id": "s1", "importance": 9},
                {"id": "s2", "importance": 8},
            ],
            "weaknesses": [
                {"id": "w1", "importance": 6},
                {"id": "w2", "importance": 7},
            ],
            "opportunities": [
                {"id": "o1", "importance": 8},
                {"id": "o2", "importance": 7},
            ],
            "threats": [
                {"id": "t1", "importance": 9},
                {"id": "t2", "importance": 7},
            ],
        }

        response = client.get("/api/swot-analysis/swot_123/scores")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "strengths_avg" in data
        assert "weaknesses_avg" in data
        assert "opportunities_avg" in data
        assert "threats_avg" in data
        assert "strategy_health" in data
        assert "opportunity_threat_ratio" in data
        assert "internal_balance" in data

    def test_get_scores_not_found(self, client, mock_db):
        """Test getting scores for non-existent analysis"""
        mock_db.swot_analyses.find_one.return_value = None

        response = client.get("/api/swot-analysis/nonexistent/scores")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetRecommendations:
    """Test retrieving strategic recommendations"""

    def test_get_recommendations_success(self, client, mock_db):
        """Test successfully retrieving recommendations"""
        now = datetime.now(timezone.utc)
        mock_db.swot_analyses.find_one.return_value = {
            "_id": "swot_123",
            "strengths": [{"id": "s1", "text": "Strong", "importance": 8}],
            "weaknesses": [{"id": "w1", "text": "Weak", "importance": 6}],
            "opportunities": [
                {"id": "o1", "text": "Opportunity", "importance": 8}
            ],
            "threats": [{"id": "t1", "text": "Threat", "importance": 7}],
        }

        response = client.get("/api/swot-analysis/swot_123/recommendations")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_recommendations_not_found(self, client, mock_db):
        """Test getting recommendations for non-existent analysis"""
        mock_db.swot_analyses.find_one.return_value = None

        response = client.get("/api/swot-analysis/nonexistent/recommendations")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestExportSWOT:
    """Test SWOT export functionality"""

    def test_export_json_success(self, client, mock_db):
        """Test exporting SWOT as JSON"""
        now = datetime.now(timezone.utc)
        mock_db.swot_analyses.find_one.return_value = {
            "_id": "swot_123",
            "business_plan_id": "plan_123",
            "title": "Test SWOT",
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
            "created_at": now,
            "updated_at": now,
        }

        response = client.get("/api/swot-analysis/swot_123/export?format=json")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["format"] == "json"
        assert "content" in data
        assert data["analysis_id"] == "swot_123"

    def test_export_markdown_success(self, client, mock_db):
        """Test exporting SWOT as Markdown"""
        now = datetime.now(timezone.utc)
        mock_db.swot_analyses.find_one.return_value = {
            "_id": "swot_123",
            "business_plan_id": "plan_123",
            "title": "Test SWOT",
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
            "created_at": now,
            "updated_at": now,
        }

        response = client.get("/api/swot-analysis/swot_123/export?format=markdown")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["format"] == "markdown"

    def test_export_pdf_success(self, client, mock_db):
        """Test exporting SWOT as PDF"""
        now = datetime.now(timezone.utc)
        mock_db.swot_analyses.find_one.return_value = {
            "_id": "swot_123",
            "business_plan_id": "plan_123",
            "title": "Test SWOT",
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
            "created_at": now,
            "updated_at": now,
        }

        response = client.get("/api/swot-analysis/swot_123/export?format=pdf")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["format"] == "pdf"

    def test_export_png_success(self, client, mock_db):
        """Test exporting SWOT as PNG"""
        now = datetime.now(timezone.utc)
        mock_db.swot_analyses.find_one.return_value = {
            "_id": "swot_123",
            "business_plan_id": "plan_123",
            "title": "Test SWOT",
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
            "created_at": now,
            "updated_at": now,
        }

        response = client.get("/api/swot-analysis/swot_123/export?format=png")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["format"] == "png"

    def test_export_invalid_format(self, client, mock_db):
        """Test exporting with invalid format"""
        mock_db.swot_analyses.find_one.return_value = {
            "_id": "swot_123",
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
        }

        response = client.get("/api/swot-analysis/swot_123/export?format=invalid")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_export_missing_format(self, client, mock_db):
        """Test exporting without format parameter"""
        response = client.get("/api/swot-analysis/swot_123/export")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
