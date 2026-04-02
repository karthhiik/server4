"""
Comprehensive Unit Tests for Business Plan FastAPI Routes

Covers:
- Create endpoint (POST)
- List endpoint (GET)
- Retrieve endpoint (GET by ID)
- Update endpoints (PUT, PATCH)
- Delete endpoint (DELETE)
- Version endpoints (GET versions, restore version)
- Export endpoint (PDF, CSV)
- Citation endpoints (GET, POST)
- Health check endpoint
- Error handling (404, 400, 401)

Tests: 22 total covering success and error paths
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorDatabase


# ── Test Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def auth_user():
    """Fixture providing authenticated user."""
    return {"user_id": "test_user_123"}


@pytest.fixture
def sample_plan_data():
    """Fixture providing sample business plan creation data."""
    return {
        "company_name": "TechStartup Inc.",
        "industry": "Technology",
        "business_type": "B2B SaaS",
        "description": "A cloud-based project management tool",
        "target_market": "Enterprise teams",
        "current_stage": "Series A",
        "team_size": "10-20 employees",
    }


@pytest.fixture
def sample_plan_doc(sample_plan_data):
    """Fixture providing sample MongoDB document."""
    return {
        "_id": "plan_001",
        "user_id": "test_user_123",
        "company_name": sample_plan_data["company_name"],
        "industry": sample_plan_data["industry"],
        "business_type": sample_plan_data["business_type"],
        "description": sample_plan_data["description"],
        "target_market": sample_plan_data["target_market"],
        "current_stage": sample_plan_data["current_stage"],
        "team_size": sample_plan_data["team_size"],
        "status": "draft",
        "sections": {},
        "versions": [
            {
                "version_id": "v_001",
                "version_number": 1,
                "created_at": datetime.now(),
                "status": "created",
            }
        ],
        "citations": [],
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }


@pytest.fixture
def client():
    """Fixture providing TestClient with mocked dependencies."""
    from app.routers import business_plans
    from app.database import get_db
    from app.dependencies import require_auth

    # Create app
    app = FastAPI()
    app.include_router(business_plans.router)

    # Setup dependency overrides
    def mock_get_db():
        db = MagicMock(spec=AsyncIOMotorDatabase)
        db.business_plans = AsyncMock()
        return db

    def mock_require_auth():
        return {"user_id": "test_user_123"}

    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[require_auth] = mock_require_auth

    return TestClient(app)


# ── Quality Gate 1: Spec Compliance Tests ──────────────────────────


class TestHealthEndpoint:
    """Tests for health check endpoint (1 test)"""

    def test_health_check_returns_200(self, client):
        """Verify GET /health returns 200 with correct response"""
        # Health check doesn't need DB or auth
        response = client.get("/api/business-plans/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "business-plan-service"
        assert "version" in data


class TestCreateEndpoint:
    """Tests for POST /api/business-plans endpoint (2 tests)"""

    def test_create_plan_success(self, client, sample_plan_data):
        """Verify POST /api/business-plans with valid data returns 201"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.insert_one = AsyncMock()
            mock_get_db_fn.return_value = mock_db

            response = client.post("/api/business-plans", json=sample_plan_data)

            assert response.status_code == 201
            data = response.json()
            assert data["company_name"] == sample_plan_data["company_name"]
            assert data["industry"] == sample_plan_data["industry"]
            assert data["status"] == "draft"
            assert "id" in data
            assert "created_at" in data

    def test_create_plan_invalid_data(self, client):
        """Verify POST /api/business-plans with invalid data returns 422"""
        with patch("app.routers.business_plans.get_db"):
            invalid_data = {
                "company_name": "Test Co",
                # Missing required fields: industry, business_type, description
            }

            response = client.post("/api/business-plans", json=invalid_data)

            assert response.status_code == 422
            assert "detail" in response.json()


class TestRetrieveEndpoints:
    """Tests for GET endpoints (3 tests)"""

    def test_get_plan_by_id_success(self, client, sample_plan_doc):
        """Verify GET /api/business-plans/{plan_id} returns 200 with plan data"""
        # Modify mock to return our sample doc
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=sample_plan_doc)
            mock_get_db_fn.return_value = mock_db

            response = client.get("/api/business-plans/plan_001")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "plan_001"
            assert data["company_name"] == "TechStartup Inc."

    def test_get_plan_not_found(self, client):
        """Verify GET /api/business-plans/{plan_id} returns 404 for missing plan"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=None)
            mock_get_db_fn.return_value = mock_db

            response = client.get("/api/business-plans/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_list_plans_with_pagination(self, client, sample_plan_doc):
        """Verify GET /api/business-plans with pagination returns 200 with list"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=[sample_plan_doc])
            mock_db.business_plans.find.return_value.sort.return_value.skip.return_value.limit.return_value = (
                mock_cursor
            )
            mock_db.business_plans.count_documents = AsyncMock(return_value=1)
            mock_get_db_fn.return_value = mock_db

            response = client.get("/api/business-plans?skip=0&limit=20")

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert data["skip"] == 0
            assert data["limit"] == 20
            assert len(data["items"]) == 1


class TestUpdateEndpoints:
    """Tests for PUT and PATCH endpoints (3 tests)"""

    def test_update_plan_success(self, client, sample_plan_doc):
        """Verify PUT /api/business-plans/{plan_id} updates and returns 200"""
        updated_doc = {**sample_plan_doc, "company_name": "Updated Inc."}

        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one_and_update = AsyncMock(return_value=updated_doc)
            mock_get_db_fn.return_value = mock_db

            update_data = {
                "company_name": "Updated Inc.",
                "description": "Updated description",
            }
            response = client.put("/api/business-plans/plan_001", json=update_data)

            assert response.status_code == 200
            data = response.json()
            assert data["company_name"] == "Updated Inc."

    def test_update_section_success(self, client, sample_plan_doc):
        """Verify PATCH /api/business-plans/{plan_id}/sections/{section_id} returns 200"""
        updated_doc = {
            **sample_plan_doc,
            "sections": {"executive_summary": "Updated content"}
        }

        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one_and_update = AsyncMock(return_value=updated_doc)
            mock_get_db_fn.return_value = mock_db

            section_data = {
                "content": "Updated executive summary content",
                "metadata": {"key": "value"},
            }
            response = client.patch(
                "/api/business-plans/plan_001/sections/executive_summary",
                json=section_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "plan_001"

    def test_update_plan_not_found(self, client):
        """Verify PUT with invalid ID returns 404"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one_and_update = AsyncMock(return_value=None)
            mock_get_db_fn.return_value = mock_db

            update_data = {"company_name": "Updated Inc."}
            response = client.put("/api/business-plans/nonexistent", json=update_data)

            assert response.status_code == 404


class TestDeleteEndpoint:
    """Tests for DELETE endpoint (2 tests)"""

    def test_delete_plan_success(self, client):
        """Verify DELETE /api/business-plans/{plan_id} returns 204"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_result = MagicMock()
            mock_result.deleted_count = 1
            mock_db.business_plans.delete_one = AsyncMock(return_value=mock_result)
            mock_get_db_fn.return_value = mock_db

            response = client.delete("/api/business-plans/plan_001")

            assert response.status_code == 204
            assert response.content == b""

    def test_delete_plan_not_found(self, client):
        """Verify DELETE /api/business-plans/{plan_id} returns 404 for missing plan"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_result = MagicMock()
            mock_result.deleted_count = 0
            mock_db.business_plans.delete_one = AsyncMock(return_value=mock_result)
            mock_get_db_fn.return_value = mock_db

            response = client.delete("/api/business-plans/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestVersionEndpoints:
    """Tests for version management endpoints (4 tests)"""

    def test_get_versions_success(self, client, sample_plan_doc):
        """Verify GET /api/business-plans/{plan_id}/versions returns version list"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=sample_plan_doc)
            mock_get_db_fn.return_value = mock_db

            response = client.get("/api/business-plans/plan_001/versions")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["version_number"] == 1

    def test_get_versions_plan_not_found(self, client):
        """Verify GET /api/business-plans/{plan_id}/versions returns 404 for missing plan"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=None)
            mock_get_db_fn.return_value = mock_db

            response = client.get("/api/business-plans/nonexistent/versions")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_restore_version_success(self, client, sample_plan_doc):
        """Verify POST /api/business-plans/{plan_id}/versions/{version_id}/restore returns 200"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=sample_plan_doc)
            mock_db.business_plans.find_one_and_update = AsyncMock(return_value=sample_plan_doc)
            mock_get_db_fn.return_value = mock_db

            response = client.post(
                "/api/business-plans/plan_001/versions/v_001/restore"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "plan_001"

    def test_restore_version_plan_not_found(self, client):
        """Verify POST restore returns 404 when plan doesn't exist"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=None)
            mock_get_db_fn.return_value = mock_db

            response = client.post(
                "/api/business-plans/nonexistent/versions/v_001/restore"
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestExportEndpoint:
    """Tests for export endpoint (4 tests)"""

    def test_export_plan_as_pdf(self, client, sample_plan_doc):
        """Verify GET /api/business-plans/{plan_id}/export?format=pdf returns PDF metadata"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=sample_plan_doc)
            mock_get_db_fn.return_value = mock_db

            response = client.get("/api/business-plans/plan_001/export?format=pdf")

            assert response.status_code == 200
            data = response.json()
            assert data["format"] == "pdf"
            assert "filename" in data
            assert ".pdf" in data["filename"]

    def test_export_plan_as_csv(self, client, sample_plan_doc):
        """Verify GET /api/business-plans/{plan_id}/export?format=csv returns CSV metadata"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=sample_plan_doc)
            mock_get_db_fn.return_value = mock_db

            response = client.get("/api/business-plans/plan_001/export?format=csv")

            assert response.status_code == 200
            data = response.json()
            assert data["format"] == "csv"
            assert "filename" in data
            assert ".csv" in data["filename"]

    def test_export_plan_not_found(self, client):
        """Verify GET export returns 404 when plan doesn't exist"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=None)
            mock_get_db_fn.return_value = mock_db

            response = client.get("/api/business-plans/nonexistent/export?format=pdf")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_export_invalid_format(self, client, sample_plan_doc):
        """Verify GET export with invalid format returns 400"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=sample_plan_doc)
            mock_get_db_fn.return_value = mock_db

            response = client.get("/api/business-plans/plan_001/export?format=docx")

            assert response.status_code == 400
            assert "invalid" in response.json()["detail"].lower()


class TestCitationEndpoints:
    """Tests for citation management endpoints (4 tests)"""

    def test_get_citations_success(self, client, sample_plan_doc):
        """Verify GET /api/business-plans/{plan_id}/citations returns citation list"""
        plan_with_citations = {
            **sample_plan_doc,
            "citations": [
                {
                    "source": "Gartner",
                    "title": "Industry Report",
                    "url": "https://gartner.com",
                },
                {
                    "source": "McKinsey",
                    "title": "Strategy Analysis",
                    "url": "https://mckinsey.com",
                },
            ],
        }

        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=plan_with_citations)
            mock_get_db_fn.return_value = mock_db

            response = client.get("/api/business-plans/plan_001/citations")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]["source"] == "Gartner"

    def test_get_citations_plan_not_found(self, client):
        """Verify GET citations returns 404 when plan doesn't exist"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=None)
            mock_get_db_fn.return_value = mock_db

            response = client.get("/api/business-plans/nonexistent/citations")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_add_citation_success(self, client, sample_plan_doc):
        """Verify POST /api/business-plans/{plan_id}/citations adds citation and returns 201"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=sample_plan_doc)
            mock_db.business_plans.update_one = AsyncMock()
            mock_get_db_fn.return_value = mock_db

            citation_data = {
                "source": "Gartner",
                "title": "Market Analysis Report",
                "url": "https://gartner.com/report",
            }
            response = client.post(
                "/api/business-plans/plan_001/citations", json=citation_data
            )

            assert response.status_code == 201
            data = response.json()
            assert data["source"] == "Gartner"
            assert data["title"] == "Market Analysis Report"

    def test_add_citation_plan_not_found(self, client):
        """Verify POST citation returns 404 when plan doesn't exist"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=None)
            mock_get_db_fn.return_value = mock_db

            citation_data = {
                "source": "Gartner",
                "title": "Market Analysis Report",
            }
            response = client.post(
                "/api/business-plans/nonexistent/citations",
                json=citation_data
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


# ── Quality Gate 2: Error Handling Tests ───────────────────────────


class TestErrorHandling:
    """Tests for error cases and validation (6 tests)"""

    def test_missing_required_citation_field(self, client):
        """Verify missing required citation fields returns 422"""
        with patch("app.routers.business_plans.get_db"):
            invalid_citation = {
                "source": "Gartner",
                # Missing required field: title
            }
            response = client.post(
                "/api/business-plans/plan_001/citations", json=invalid_citation
            )

            assert response.status_code == 422

    def test_update_section_plan_not_found(self, client):
        """Verify updating section of nonexistent plan returns 404"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one_and_update = AsyncMock(return_value=None)
            mock_get_db_fn.return_value = mock_db

            section_data = {"content": "Updated content"}
            response = client.patch(
                "/api/business-plans/nonexistent/sections/summary",
                json=section_data,
            )

            assert response.status_code == 404

    def test_restore_nonexistent_version(self, client, sample_plan_doc):
        """Verify restoring nonexistent version returns 404"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            # Return plan doc with empty versions list
            plan_no_versions = {**sample_plan_doc, "versions": []}
            mock_db.business_plans.find_one = AsyncMock(return_value=plan_no_versions)
            mock_get_db_fn.return_value = mock_db

            response = client.post(
                "/api/business-plans/plan_001/versions/nonexistent/restore"
            )

            assert response.status_code == 404

    def test_section_update_missing_required_field(self, client):
        """Verify missing required section field returns 422"""
        with patch("app.routers.business_plans.get_db"):
            invalid_section = {
                # Missing required field: content
                "metadata": {"key": "value"}
            }
            response = client.patch(
                "/api/business-plans/plan_001/sections/summary",
                json=invalid_section,
            )

            assert response.status_code == 422

    def test_list_plans_invalid_pagination(self, client):
        """Verify invalid pagination parameters return 422"""
        with patch("app.routers.business_plans.get_db"):
            response = client.get("/api/business-plans?skip=-1&limit=20")

            assert response.status_code == 422

    def test_list_plans_limit_exceeds_max(self, client):
        """Verify limit exceeding maximum returns 422"""
        with patch("app.routers.business_plans.get_db"):
            response = client.get("/api/business-plans?skip=0&limit=101")

            assert response.status_code == 422


# ── Integration Test Helper ────────────────────────────────────────


class TestResponseValidation:
    """Tests for response body validation (3 tests)"""

    def test_create_response_has_required_fields(self, client, sample_plan_data):
        """Verify created plan response has all required fields"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.insert_one = AsyncMock()
            mock_get_db_fn.return_value = mock_db

            response = client.post("/api/business-plans", json=sample_plan_data)

            assert response.status_code == 201
            data = response.json()
            required_fields = [
                "id",
                "company_name",
                "industry",
                "business_type",
                "description",
                "status",
                "created_at",
                "updated_at",
            ]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"

    def test_list_response_structure(self, client, sample_plan_doc):
        """Verify list response has pagination metadata"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=[sample_plan_doc])
            mock_db.business_plans.find.return_value.sort.return_value.skip.return_value.limit.return_value = (
                mock_cursor
            )
            mock_db.business_plans.count_documents = AsyncMock(return_value=1)
            mock_get_db_fn.return_value = mock_db

            response = client.get("/api/business-plans")

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert "skip" in data
            assert "limit" in data
            assert isinstance(data["items"], list)

    def test_version_response_structure(self, client, sample_plan_doc):
        """Verify version response has expected fields"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=sample_plan_doc)
            mock_get_db_fn.return_value = mock_db

            response = client.get("/api/business-plans/plan_001/versions")

            assert response.status_code == 200
            data = response.json()
            assert len(data) > 0
            version = data[0]
            assert "version_id" in version
            assert "version_number" in version
            assert "created_at" in version
            assert "status" in version


class TestPaginationEdgeCases:
    """Tests for pagination edge cases (3 tests)"""

    def test_list_plans_with_zero_skip(self, client, sample_plan_doc):
        """Verify list with skip=0 returns correct pagination"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=[sample_plan_doc])
            mock_db.business_plans.find.return_value.sort.return_value.skip.return_value.limit.return_value = (
                mock_cursor
            )
            mock_db.business_plans.count_documents = AsyncMock(return_value=1)
            mock_get_db_fn.return_value = mock_db

            response = client.get("/api/business-plans?skip=0&limit=20")

            assert response.status_code == 200
            data = response.json()
            assert data["skip"] == 0

    def test_list_plans_with_large_limit(self, client, sample_plan_doc):
        """Verify list with limit=100 (max) returns correct pagination"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=[sample_plan_doc])
            mock_db.business_plans.find.return_value.sort.return_value.skip.return_value.limit.return_value = (
                mock_cursor
            )
            mock_db.business_plans.count_documents = AsyncMock(return_value=100)
            mock_get_db_fn.return_value = mock_db

            response = client.get("/api/business-plans?skip=0&limit=100")

            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == 100

    def test_list_plans_with_high_skip(self, client, sample_plan_doc):
        """Verify list with high skip value returns correct pagination"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_db.business_plans.find.return_value.sort.return_value.skip.return_value.limit.return_value = (
                mock_cursor
            )
            mock_db.business_plans.count_documents = AsyncMock(return_value=50)
            mock_get_db_fn.return_value = mock_db

            response = client.get("/api/business-plans?skip=1000&limit=20")

            assert response.status_code == 200
            data = response.json()
            assert data["skip"] == 1000
            assert len(data["items"]) == 0


class TestStatusCodeCoverage:
    """Tests ensuring all HTTP status codes are verified (3 tests)"""

    def test_create_returns_201_status(self, client, sample_plan_data):
        """Verify POST /api/business-plans returns 201 Created status code"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.insert_one = AsyncMock()
            mock_get_db_fn.return_value = mock_db

            response = client.post("/api/business-plans", json=sample_plan_data)

            # Verify status code explicitly is 201
            assert response.status_code == 201
            assert response.status_code == status.HTTP_201_CREATED

    def test_delete_returns_204_status(self, client):
        """Verify DELETE /api/business-plans/{plan_id} returns 204 No Content"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_result = MagicMock()
            mock_result.deleted_count = 1
            mock_db.business_plans.delete_one = AsyncMock(return_value=mock_result)
            mock_get_db_fn.return_value = mock_db

            response = client.delete("/api/business-plans/plan_001")

            # Verify status code explicitly is 204
            assert response.status_code == 204
            assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_get_returns_200_status(self, client, sample_plan_doc):
        """Verify GET endpoints return 200 OK status code"""
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=sample_plan_doc)
            mock_get_db_fn.return_value = mock_db

            response = client.get("/api/business-plans/plan_001")

            # Verify status code explicitly is 200
            assert response.status_code == 200
            assert response.status_code == status.HTTP_200_OK


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
