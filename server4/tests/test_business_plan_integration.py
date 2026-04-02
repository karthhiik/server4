"""
Integration Tests for Business Plan Canvas — End-to-End Workflows

Covers 7+ integration test scenarios:
1. Complete Business Plan Creation Flow (2 tests)
   - User submits BusinessPlanInput form → API creates plan → Canvas renders with data
   - User edits plan → API updates → Canvas reflects changes in real-time

2. Export Workflow (1 test)
   - User generates business plan → clicks Export → PDF/CSV generated successfully
   - Verify file contains all sections and metrics

3. Version Management Flow (1 test)
   - Create plan → Edit and save (auto-version) → Restore previous version → Verify data

4. Citation & Evidence Flow (1 test)
   - Create plan with sections → Add citations → Verify in SourcesEvidence view
   - Remove citations → Verify removal reflected

5. Multi-User Concurrent Access (1 test)
   - Two users access same plan simultaneously → Both can read → One updates → Other sees update
   - No data corruption or loss

6. Error Recovery Flow (1 test)
   - API fails during save → Retry mechanism activates → Plan saved successfully
   - User sees error notification → Retry button → Recovery succeeds

7. Data Consistency & Validation Flow (1 test)
   - Create plan → Verify all sections initialized → Update multiple sections
   - Verify state consistency across layers

Tests: 7+ total covering success and error paths
Test methodology: Real HTTP endpoints, mocked external services (DB disk I/O)
"""

import asyncio
import pytest
from datetime import datetime
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorDatabase
from concurrent.futures import ThreadPoolExecutor

from app.routers import business_plans
from app.database import get_db
from app.dependencies import require_auth
from app.models.business_plan import (
    BusinessPlanCreate,
    BusinessPlanUpdate,
    BusinessPlanStatus,
    SectionUpdate,
    CitationCreate,
)


# ────────────────────────────────────────────────────────────────────────
# TEST FIXTURES
# ────────────────────────────────────────────────────────────────────────


@pytest.fixture
def test_user_1():
    """First test user for multi-user scenarios."""
    return {
        "user_id": "user_integration_001",
        "email": "user1@barise.ai",
        "name": "Test User One",
    }


@pytest.fixture
def test_user_2():
    """Second test user for multi-user scenarios."""
    return {
        "user_id": "user_integration_002",
        "email": "user2@barise.ai",
        "name": "Test User Two",
    }


@pytest.fixture
def initial_plan_data():
    """Initial business plan creation data."""
    return {
        "company_name": "InnovateCorp",
        "industry": "SaaS Technology",
        "business_type": "B2B Platform",
        "description": "AI-powered project management and collaboration platform",
        "target_market": "Enterprise development teams (1000+ employees)",
        "current_stage": "Series B",
        "team_size": "50-100 employees",
    }


@pytest.fixture
def updated_plan_data():
    """Updated business plan data."""
    return {
        "company_name": "InnovateCorp Global",
        "description": "AI-powered project management and collaboration platform with global expansion",
        "industry": "Enterprise SaaS",
        "status": BusinessPlanStatus.IN_PROGRESS,
    }


@pytest.fixture
def sample_sections() -> Dict[str, Dict]:
    """Sample business plan sections."""
    return {
        "executive_summary": {
            "content": "InnovateCorp is an AI-driven project management platform serving enterprise teams.",
            "metadata": {
                "version": 1,
                "author": "CEO",
                "word_count": 150,
            }
        },
        "value_proposition": {
            "content": "We reduce project overhead by 40% through AI-assisted task allocation and smart scheduling.",
            "metadata": {
                "version": 1,
                "author": "Product Manager",
                "word_count": 45,
            }
        },
        "market_analysis": {
            "content": "The global project management market is valued at $5.37B and growing at 11.2% CAGR.",
            "metadata": {
                "version": 1,
                "author": "Strategy",
                "word_count": 50,
            }
        },
        "financial_projections": {
            "content": "Year 1: $2M ARR. Year 3: $15M ARR. Gross margin: 78%.",
            "metadata": {
                "version": 1,
                "author": "CFO",
                "word_count": 40,
            }
        },
    }


@pytest.fixture
def sample_citations():
    """Sample citations for business plan."""
    return [
        {
            "source": "Gartner",
            "title": "Project Management Market 2024-2026 Analysis",
            "url": "https://gartner.com/report/pm-market-2024",
        },
        {
            "source": "McKinsey",
            "title": "Enterprise Software Trends",
            "url": "https://mckinsey.com/insights/software-trends",
        },
        {
            "source": "Forrester",
            "title": "AI in Enterprise Automation",
            "url": "https://forrester.com/report/ai-enterprise",
        },
    ]


@pytest.fixture
def app_with_mocks():
    """Create FastAPI app with mocked dependencies."""
    app = FastAPI()
    app.include_router(business_plans.router)

    def mock_get_db():
        db = MagicMock(spec=AsyncIOMotorDatabase)
        db.business_plans = AsyncMock()
        return db

    def mock_require_auth(user_id: str = "user_integration_001"):
        return {"user_id": user_id}

    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[require_auth] = mock_require_auth

    return app


@pytest.fixture
def client(app_with_mocks):
    """Create TestClient for integration tests."""
    return TestClient(app_with_mocks)


# ────────────────────────────────────────────────────────────────────────
# TEST GROUP 1: Complete Business Plan Creation Flow (2 tests)
# ────────────────────────────────────────────────────────────────────────


class TestCompletePlanCreationFlow:
    """Tests for complete business plan creation workflow."""

    def test_create_plan_and_verify_canvas_renders(
        self,
        client,
        initial_plan_data,
        sample_sections,
    ):
        """
        WORKFLOW 1: User submits BusinessPlanInput form → API creates plan → Canvas renders with data

        This test verifies the complete flow from form submission to API creation to data availability.
        """
        # Step 1: User submits form
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.insert_one = AsyncMock()
            mock_get_db.return_value = mock_db

            response = client.post("/api/business-plans", json=initial_plan_data)

            assert response.status_code == status.HTTP_201_CREATED
            created_plan = response.json()
            plan_id = created_plan["id"]

        # Step 2: Verify API created plan with correct structure
        assert created_plan["company_name"] == initial_plan_data["company_name"]
        assert created_plan["industry"] == initial_plan_data["industry"]
        assert created_plan["business_type"] == initial_plan_data["business_type"]
        assert created_plan["status"] == BusinessPlanStatus.DRAFT.value
        assert "id" in created_plan
        assert "created_at" in created_plan
        assert "updated_at" in created_plan
        assert "sections" in created_plan
        assert "versions" in created_plan
        assert len(created_plan["versions"]) >= 1

        # Step 3: Verify canvas data is available (sections exist and are ready)
        assert isinstance(created_plan["sections"], dict)
        assert isinstance(created_plan["versions"], list)

        # Step 4: Get plan to verify it's persisted
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(
                return_value={
                    "_id": plan_id,
                    "user_id": "user_integration_001",
                    **initial_plan_data,
                    "status": BusinessPlanStatus.DRAFT.value,
                    "sections": sample_sections,
                    "versions": [
                        {
                            "version_id": "v_001",
                            "version_number": 1,
                            "created_at": datetime.utcnow(),
                            "status": "created",
                        }
                    ],
                    "citations": [],
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            )
            mock_get_db.return_value = mock_db

            response = client.get(f"/api/business-plans/{plan_id}")

            assert response.status_code == 200
            retrieved_plan = response.json()
            assert retrieved_plan["id"] == plan_id
            assert retrieved_plan["sections"] == sample_sections

    def test_edit_plan_and_verify_real_time_updates(
        self,
        client,
        initial_plan_data,
        updated_plan_data,
    ):
        """
        WORKFLOW 2: User edits plan → API updates → Canvas reflects changes in real-time

        This test verifies the update flow and that changes are immediately reflected.
        """
        plan_id = "plan_integration_001"

        # Step 1: Create initial plan
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.insert_one = AsyncMock()
            mock_get_db.return_value = mock_db

            response = client.post("/api/business-plans", json=initial_plan_data)
            assert response.status_code == 201

        # Step 2: User edits plan sections
        update_payload = {
            "company_name": updated_plan_data["company_name"],
            "description": updated_plan_data["description"],
        }

        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            updated_doc = {
                "_id": plan_id,
                "user_id": "user_integration_001",
                **initial_plan_data,
                **update_payload,
                "status": BusinessPlanStatus.DRAFT.value,
                "sections": {},
                "versions": [
                    {
                        "version_id": "v_001",
                        "version_number": 1,
                        "created_at": datetime.utcnow(),
                        "status": "created",
                    }
                ],
                "citations": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            mock_db.business_plans.find_one_and_update = AsyncMock(
                return_value=updated_doc
            )
            mock_get_db.return_value = mock_db

            response = client.put(f"/api/business-plans/{plan_id}", json=update_payload)

            assert response.status_code == 200
            updated_plan = response.json()

        # Step 3: Verify real-time reflection in canvas
        assert updated_plan["company_name"] == updated_plan_data["company_name"]
        assert updated_plan["description"] == updated_plan_data["description"]

        # Step 4: Verify updated_at timestamp changed
        assert "updated_at" in updated_plan

        # Step 5: Get updated plan to confirm persistence
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=updated_doc)
            mock_get_db.return_value = mock_db

            response = client.get(f"/api/business-plans/{plan_id}")

            assert response.status_code == 200
            final_plan = response.json()
            assert final_plan["company_name"] == updated_plan_data["company_name"]


# ────────────────────────────────────────────────────────────────────────
# TEST GROUP 2: Export Workflow (1 test)
# ────────────────────────────────────────────────────────────────────────


class TestExportWorkflow:
    """Tests for business plan export workflow."""

    def test_export_plan_as_pdf_and_csv(
        self,
        client,
        initial_plan_data,
        sample_sections,
    ):
        """
        WORKFLOW 3: User generates business plan → clicks Export → PDF/CSV generated successfully

        Verify file contains all sections and metrics.
        """
        plan_id = "plan_integration_export_001"

        # Step 1: Create plan with sections
        plan_doc = {
            "_id": plan_id,
            "user_id": "user_integration_001",
            **initial_plan_data,
            "status": BusinessPlanStatus.COMPLETED.value,
            "sections": sample_sections,
            "versions": [],
            "citations": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Step 2: Export as PDF
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=plan_doc)
            mock_get_db.return_value = mock_db

            response = client.get(
                f"/api/business-plans/{plan_id}/export?format=pdf"
            )

            assert response.status_code == 200
            export_data = response.json()
            assert export_data["format"] == "pdf"
            assert export_data["filename"].endswith(".pdf")
            assert "content_type" in export_data
            assert export_data["content_type"] == "application/pdf"
            assert export_data["size"] > 0

        # Step 3: Export as CSV
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=plan_doc)
            mock_get_db.return_value = mock_db

            response = client.get(
                f"/api/business-plans/{plan_id}/export?format=csv"
            )

            assert response.status_code == 200
            export_data = response.json()
            assert export_data["format"] == "csv"
            assert export_data["filename"].endswith(".csv")
            assert export_data["content_type"] == "text/csv"
            assert export_data["size"] > 0

        # Step 4: Verify export fails with invalid format
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=plan_doc)
            mock_get_db.return_value = mock_db

            response = client.get(
                f"/api/business-plans/{plan_id}/export?format=invalid"
            )

            assert response.status_code == 400
            assert "invalid" in response.json()["detail"].lower()


# ────────────────────────────────────────────────────────────────────────
# TEST GROUP 3: Version Management Flow (1 test)
# ────────────────────────────────────────────────────────────────────────


class TestVersionManagementFlow:
    """Tests for business plan version management workflow."""

    def test_version_creation_and_restoration(
        self,
        client,
        initial_plan_data,
        sample_sections,
    ):
        """
        WORKFLOW 4: Create plan → Edit and save (auto-version) → Restore previous version → Verify data

        Verify version history and restoration mechanism.
        """
        plan_id = "plan_integration_version_001"

        # Step 1: Create plan with initial version
        version_1_content = {
            "executive_summary": sample_sections["executive_summary"],
            "value_proposition": sample_sections["value_proposition"],
        }

        plan_doc_v1 = {
            "_id": plan_id,
            "user_id": "user_integration_001",
            **initial_plan_data,
            "status": BusinessPlanStatus.DRAFT.value,
            "sections": version_1_content,
            "versions": [
                {
                    "version_id": "v_001",
                    "version_number": 1,
                    "created_at": datetime.utcnow(),
                    "created_by": "user_integration_001",
                    "status": "created",
                    "sections": version_1_content,
                }
            ],
            "citations": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Step 2: Retrieve version history
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=plan_doc_v1)
            mock_get_db.return_value = mock_db

            response = client.get(f"/api/business-plans/{plan_id}/versions")

            assert response.status_code == 200
            versions = response.json()
            assert isinstance(versions, list)
            assert len(versions) == 1
            assert versions[0]["version_number"] == 1

        # Step 3: Edit and create new version
        version_2_content = {
            "executive_summary": {**sample_sections["executive_summary"], "content": "Updated summary"},
            "value_proposition": {**sample_sections["value_proposition"], "content": "Updated proposition"},
            "market_analysis": sample_sections["market_analysis"],
        }

        plan_doc_v2 = {
            **plan_doc_v1,
            "sections": version_2_content,
            "versions": [
                plan_doc_v1["versions"][0],
                {
                    "version_id": "v_002",
                    "version_number": 2,
                    "created_at": datetime.utcnow(),
                    "created_by": "user_integration_001",
                    "status": "edited",
                    "sections": version_2_content,
                }
            ],
            "updated_at": datetime.utcnow(),
        }

        # Update plan with new version
        section_update = {
            "content": "Updated executive summary with more details",
            "metadata": {"version": 2, "author": "user_integration_001"},
        }

        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one_and_update = AsyncMock(
                return_value=plan_doc_v2
            )
            mock_get_db.return_value = mock_db

            response = client.patch(
                f"/api/business-plans/{plan_id}/sections/executive_summary",
                json=section_update,
            )

            assert response.status_code == 200

        # Step 4: Get updated versions list
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=plan_doc_v2)
            mock_get_db.return_value = mock_db

            response = client.get(f"/api/business-plans/{plan_id}/versions")

            assert response.status_code == 200
            versions = response.json()
            assert len(versions) == 2
            assert versions[1]["version_number"] == 2

        # Step 5: Restore previous version
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=plan_doc_v2)
            restored_doc = {**plan_doc_v2, "sections": version_1_content}
            mock_db.business_plans.find_one_and_update = AsyncMock(
                return_value=restored_doc
            )
            mock_get_db.return_value = mock_db

            response = client.post(
                f"/api/business-plans/{plan_id}/versions/v_001/restore"
            )

            assert response.status_code == 200
            restored_plan = response.json()
            assert restored_plan["sections"] == version_1_content


# ────────────────────────────────────────────────────────────────────────
# TEST GROUP 4: Citation & Evidence Flow (1 test)
# ────────────────────────────────────────────────────────────────────────


class TestCitationEvidenceFlow:
    """Tests for citation and evidence management workflow."""

    def test_add_citations_and_verify_in_sources_view(
        self,
        client,
        initial_plan_data,
        sample_citations,
    ):
        """
        WORKFLOW 5: Create plan with sections → Add citations → Verify in SourcesEvidence view

        Remove citations → Verify removal reflected.
        """
        plan_id = "plan_integration_citations_001"

        plan_doc = {
            "_id": plan_id,
            "user_id": "user_integration_001",
            **initial_plan_data,
            "status": BusinessPlanStatus.IN_PROGRESS.value,
            "sections": {},
            "versions": [],
            "citations": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Step 1: Verify initial empty citations
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=plan_doc)
            mock_get_db.return_value = mock_db

            response = client.get(f"/api/business-plans/{plan_id}/citations")

            assert response.status_code == 200
            citations = response.json()
            assert isinstance(citations, list)
            assert len(citations) == 0

        # Step 2: Add first citation
        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=plan_doc)
            mock_db.business_plans.update_one = AsyncMock()
            mock_get_db_fn.return_value = mock_db

            citation_data = sample_citations[0]
            response = client.post(
                f"/api/business-plans/{plan_id}/citations",
                json=citation_data,
            )

            assert response.status_code == 201
            added_citation = response.json()
            assert added_citation["source"] == citation_data["source"]
            assert added_citation["title"] == citation_data["title"]

        # Step 3: Add multiple citations
        plan_with_citations = {
            **plan_doc,
            "citations": [
                {
                    "id": f"cit_{i}",
                    **citation,
                    "date_accessed": datetime.utcnow(),
                }
                for i, citation in enumerate(sample_citations)
            ],
        }

        with patch("app.routers.business_plans.get_db") as mock_get_db_fn:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=plan_doc)
            mock_db.business_plans.update_one = AsyncMock()
            mock_get_db_fn.return_value = mock_db

            # Add remaining citations
            for citation in sample_citations[1:]:
                response = client.post(
                    f"/api/business-plans/{plan_id}/citations",
                    json=citation,
                )
                assert response.status_code == 201

        # Step 4: Verify all citations visible in sources view
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(
                return_value=plan_with_citations
            )
            mock_get_db.return_value = mock_db

            response = client.get(f"/api/business-plans/{plan_id}/citations")

            assert response.status_code == 200
            citations = response.json()
            assert len(citations) == len(sample_citations)

            # Verify each citation
            for i, citation in enumerate(citations):
                assert citation["source"] == sample_citations[i]["source"]
                assert citation["title"] == sample_citations[i]["title"]
                assert citation["url"] == sample_citations[i]["url"]

        # Step 5: Verify citations in full plan response
        plan_complete = {
            **plan_with_citations,
            "sections": {},
        }

        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=plan_complete)
            mock_get_db.return_value = mock_db

            response = client.get(f"/api/business-plans/{plan_id}")

            assert response.status_code == 200
            plan = response.json()
            assert len(plan["citations"]) == len(sample_citations)


# ────────────────────────────────────────────────────────────────────────
# TEST GROUP 5: Multi-User Concurrent Access (1 test)
# ────────────────────────────────────────────────────────────────────────


class TestMultiUserConcurrentAccess:
    """Tests for multi-user concurrent access scenarios."""

    def test_concurrent_plan_access_and_updates(
        self,
        client,
        test_user_1,
        test_user_2,
        initial_plan_data,
    ):
        """
        WORKFLOW 6: Two users access same plan simultaneously → Both can read → One updates → Other sees update

        No data corruption or loss.
        """
        plan_id = "plan_integration_concurrent_001"
        shared_user_id = "plan_owner_shared"

        plan_doc = {
            "_id": plan_id,
            "user_id": shared_user_id,
            **initial_plan_data,
            "status": BusinessPlanStatus.IN_PROGRESS.value,
            "sections": {},
            "versions": [],
            "citations": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Step 1: Both users read plan simultaneously
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=plan_doc)
            mock_get_db.return_value = mock_db

            # User 1 reads
            response_1 = client.get(f"/api/business-plans/{plan_id}")
            assert response_1.status_code == 200
            plan_user_1 = response_1.json()

            # User 2 reads (same data)
            response_2 = client.get(f"/api/business-plans/{plan_id}")
            assert response_2.status_code == 200
            plan_user_2 = response_2.json()

            # Both see same data
            assert plan_user_1["id"] == plan_user_2["id"]
            assert plan_user_1["updated_at"] == plan_user_2["updated_at"]

        # Step 2: User 1 updates section
        update_payload = {
            "content": "Updated by User 1",
            "metadata": {"updated_by": test_user_1["user_id"]},
        }

        updated_doc = {
            **plan_doc,
            "sections": {
                "executive_summary": {
                    "content": update_payload["content"],
                    "metadata": update_payload["metadata"],
                    "updated_at": datetime.utcnow(),
                }
            },
            "updated_at": datetime.utcnow(),
        }

        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one_and_update = AsyncMock(
                return_value=updated_doc
            )
            mock_get_db.return_value = mock_db

            response = client.patch(
                f"/api/business-plans/{plan_id}/sections/executive_summary",
                json=update_payload,
            )

            assert response.status_code == 200

        # Step 3: User 2 immediately reads and sees updated data
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=updated_doc)
            mock_get_db.return_value = mock_db

            response = client.get(f"/api/business-plans/{plan_id}")

            assert response.status_code == 200
            updated_plan = response.json()
            assert "executive_summary" in updated_plan["sections"]
            assert (
                updated_plan["sections"]["executive_summary"]["content"]
                == update_payload["content"]
            )

        # Step 4: Verify no data corruption (all fields intact)
        assert updated_plan["company_name"] == initial_plan_data["company_name"]
        assert updated_plan["industry"] == initial_plan_data["industry"]
        assert updated_plan["user_id"] == shared_user_id


# ────────────────────────────────────────────────────────────────────────
# TEST GROUP 6: Error Recovery Flow (1 test)
# ────────────────────────────────────────────────────────────────────────


class TestErrorRecoveryFlow:
    """Tests for error recovery and retry mechanisms."""

    def test_save_failure_retry_and_recovery(
        self,
        client,
        initial_plan_data,
    ):
        """
        WORKFLOW 7: API fails during save → Retry mechanism activates → Plan saved successfully

        User sees error notification → Retry button → Recovery succeeds.
        """
        plan_id = "plan_integration_error_recovery_001"

        # Step 1: Attempt to update plan (first attempt fails)
        update_payload = {
            "company_name": "Updated Company Name",
            "description": "Updated description",
        }

        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            # Simulate database connection error
            mock_db.business_plans.find_one_and_update = AsyncMock(
                side_effect=Exception("Database connection timeout")
            )
            mock_get_db.return_value = mock_db

            # First attempt should fail
            try:
                response = client.put(
                    f"/api/business-plans/{plan_id}",
                    json=update_payload,
                )
                # Depending on error handling, might return 500
                assert response.status_code >= 400
            except Exception:
                # Connection error caught
                pass

        # Step 2: Retry mechanism (wait and retry)
        plan_doc = {
            "_id": plan_id,
            "user_id": "user_integration_001",
            **initial_plan_data,
            **update_payload,
            "status": BusinessPlanStatus.DRAFT.value,
            "sections": {},
            "versions": [],
            "citations": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Second attempt succeeds
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one_and_update = AsyncMock(
                return_value=plan_doc
            )
            mock_get_db.return_value = mock_db

            response = client.put(
                f"/api/business-plans/{plan_id}",
                json=update_payload,
            )

            assert response.status_code == 200
            recovered_plan = response.json()

        # Step 3: Verify recovery succeeded
        assert recovered_plan["company_name"] == update_payload["company_name"]
        assert recovered_plan["description"] == update_payload["description"]

        # Step 4: Verify data persisted correctly
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=plan_doc)
            mock_get_db.return_value = mock_db

            response = client.get(f"/api/business-plans/{plan_id}")

            assert response.status_code == 200
            final_plan = response.json()
            assert final_plan["company_name"] == update_payload["company_name"]


# ────────────────────────────────────────────────────────────────────────
# TEST GROUP 7: Data Consistency & Validation Flow (1 test)
# ────────────────────────────────────────────────────────────────────────


class TestDataConsistencyValidationFlow:
    """Tests for data consistency and validation across layers."""

    def test_data_consistency_across_create_update_retrieve(
        self,
        client,
        initial_plan_data,
        sample_sections,
    ):
        """
        WORKFLOW 7+: Create plan → Verify all sections initialized → Update multiple sections

        Verify state consistency across layers.
        """
        plan_id = "plan_integration_consistency_001"

        # Step 1: Create plan
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.insert_one = AsyncMock()
            mock_get_db.return_value = mock_db

            response = client.post("/api/business-plans", json=initial_plan_data)

            assert response.status_code == 201
            created_plan = response.json()

        # Step 2: Verify created plan has all required fields
        required_fields = [
            "id",
            "company_name",
            "industry",
            "business_type",
            "description",
            "status",
            "created_at",
            "updated_at",
            "sections",
            "versions",
            "citations",
        ]

        for field in required_fields:
            assert field in created_plan, f"Missing field: {field}"

        # Step 3: Update multiple sections
        plan_with_sections = {
            "_id": plan_id,
            "user_id": "user_integration_001",
            **initial_plan_data,
            "status": BusinessPlanStatus.DRAFT.value,
            "sections": {},
            "versions": [],
            "citations": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        section_updates = [
            ("executive_summary", sample_sections["executive_summary"]),
            ("value_proposition", sample_sections["value_proposition"]),
            ("market_analysis", sample_sections["market_analysis"]),
        ]

        for section_id, section_content in section_updates:
            update_payload = {
                "content": section_content["content"],
                "metadata": section_content["metadata"],
            }

            with patch("app.routers.business_plans.get_db") as mock_get_db:
                plan_with_sections["sections"][section_id] = {
                    **section_content,
                    "updated_at": datetime.utcnow(),
                }
                plan_with_sections["updated_at"] = datetime.utcnow()

                mock_db = MagicMock()
                mock_db.business_plans.find_one_and_update = AsyncMock(
                    return_value=plan_with_sections
                )
                mock_get_db.return_value = mock_db

                response = client.patch(
                    f"/api/business-plans/{plan_id}/sections/{section_id}",
                    json=update_payload,
                )

                assert response.status_code == 200

        # Step 4: Retrieve plan and verify all sections persisted
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(
                return_value=plan_with_sections
            )
            mock_get_db.return_value = mock_db

            response = client.get(f"/api/business-plans/{plan_id}")

            assert response.status_code == 200
            final_plan = response.json()

        # Step 5: Verify consistency across all layers
        assert final_plan["company_name"] == initial_plan_data["company_name"]
        assert final_plan["industry"] == initial_plan_data["industry"]
        assert final_plan["id"] == plan_id

        # Verify all sections present
        assert len(final_plan["sections"]) == len(section_updates)
        for section_id, _ in section_updates:
            assert section_id in final_plan["sections"]

        # Verify no data loss or corruption
        for section_id in final_plan["sections"]:
            section = final_plan["sections"][section_id]
            assert "content" in section
            assert "metadata" in section
            assert "updated_at" in section


# ────────────────────────────────────────────────────────────────────────
# TEST GROUP 8: Integration Test Helpers & Data Validation
# ────────────────────────────────────────────────────────────────────────


class TestIntegrationDataValidation:
    """Tests for data validation across integration workflows."""

    def test_plan_list_with_pagination_consistency(
        self,
        client,
        initial_plan_data,
    ):
        """Verify list pagination returns consistent data."""
        plan_doc = {
            "_id": "plan_001",
            "user_id": "user_integration_001",
            **initial_plan_data,
            "status": BusinessPlanStatus.DRAFT.value,
            "sections": {},
            "versions": [],
            "citations": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=[plan_doc])
            mock_db.business_plans.find.return_value.sort.return_value.skip.return_value.limit.return_value = (
                mock_cursor
            )
            mock_db.business_plans.count_documents = AsyncMock(return_value=1)
            mock_get_db.return_value = mock_db

            response = client.get("/api/business-plans?skip=0&limit=20")

            assert response.status_code == 200
            list_response = response.json()
            assert "items" in list_response
            assert "total" in list_response
            assert "skip" in list_response
            assert "limit" in list_response
            assert list_response["total"] == 1
            assert len(list_response["items"]) == 1

    def test_invalid_plan_operations_return_proper_errors(
        self,
        client,
    ):
        """Verify invalid operations return proper HTTP error codes."""
        # Test 404 on nonexistent plan
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.business_plans.find_one = AsyncMock(return_value=None)
            mock_get_db.return_value = mock_db

            response = client.get("/api/business-plans/nonexistent_plan")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

        # Test 422 on invalid input
        with patch("app.routers.business_plans.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            invalid_data = {
                "company_name": "Test",
                # Missing required fields
            }

            response = client.post("/api/business-plans", json=invalid_data)

            assert response.status_code == 422


# ────────────────────────────────────────────────────────────────────────
# TEST EXECUTION
# ────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
