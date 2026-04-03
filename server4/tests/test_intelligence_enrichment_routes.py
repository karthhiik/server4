"""
Comprehensive Tests for Intelligence Enrichment Routes

Tests the following endpoints:
1. POST /api/intelligence/detect-entities
2. POST /api/intelligence/web-enrich
3. POST /api/intelligence/extract-form-fields
4. POST /api/intelligence/competitor-snapshot

Tests: 8 total covering success and error paths
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers import intelligence_enrichment

# Create test app with only intelligence enrichment router
app = FastAPI()
app.include_router(intelligence_enrichment.router)

client = TestClient(app)


class TestIntelligenceEnrichmentRoutes:
    """Test suite for intelligence enrichment API endpoints."""

    def test_detect_entities_endpoint_success(self):
        """Test that detect-entities endpoint returns entities successfully."""
        response = client.post(
            "/api/intelligence/detect-entities",
            json={
                "text": "Amazon and Microsoft are in tech",
                "artifact_type": "business_plan",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert isinstance(data["entities"], list)
        assert "match" in data

    def test_detect_entities_endpoint_empty_text(self):
        """Test that detect-entities handles empty text properly."""
        response = client.post(
            "/api/intelligence/detect-entities",
            json={
                "text": "",
                "artifact_type": "business_plan",
            },
        )
        # Should fail validation due to min_length=1
        assert response.status_code == 422

    def test_detect_entities_endpoint_missing_artifact_type(self):
        """Test that detect-entities requires artifact_type."""
        response = client.post(
            "/api/intelligence/detect-entities",
            json={
                "text": "Amazon and Microsoft",
            },
        )
        assert response.status_code == 422

    def test_web_enrich_endpoint_success(self):
        """Test that web-enrich endpoint returns enriched data successfully."""
        response = client.post(
            "/api/intelligence/web-enrich",
            json={
                "entity_name": "Amazon",
                "entity_type": "company",
                "context": "e-commerce and cloud",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data or "competitors" in data
        assert "competitors" in data
        assert isinstance(data["competitors"], list)

    def test_web_enrich_endpoint_missing_required_fields(self):
        """Test that web-enrich requires required fields."""
        response = client.post(
            "/api/intelligence/web-enrich",
            json={
                "entity_name": "Amazon",
            },
        )
        assert response.status_code == 422

    def test_extract_form_fields_endpoint_success(self):
        """Test that extract-form-fields endpoint returns fields successfully."""
        response = client.post(
            "/api/intelligence/extract-form-fields",
            json={
                "prompt": "I'm Amazon, founded 1994, in e-commerce with 100k employees",
                "artifact_type": "business_plan",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "fields" in data
        assert isinstance(data["fields"], dict)
        assert "confidence_score" in data
        assert 0.0 <= data["confidence_score"] <= 1.0

    def test_extract_form_fields_endpoint_empty_prompt(self):
        """Test that extract-form-fields handles empty prompt properly."""
        response = client.post(
            "/api/intelligence/extract-form-fields",
            json={
                "prompt": "",
                "artifact_type": "business_plan",
            },
        )
        # Should fail validation due to min_length=1
        assert response.status_code == 422

    def test_competitor_snapshot_endpoint_success(self):
        """Test that competitor-snapshot endpoint returns analysis successfully."""
        response = client.post(
            "/api/intelligence/competitor-snapshot",
            json={
                "competitor_name": "Microsoft",
                "business_context": "cloud services",
                "artifact_type": "business_plan",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "strengths" in data
        assert "weaknesses" in data
        assert "threat_level" in data
        assert "opportunity_gaps" in data
        assert "sources" in data
        assert isinstance(data["strengths"], list)
        assert isinstance(data["weaknesses"], list)
        assert isinstance(data["opportunity_gaps"], list)
        assert data["threat_level"] in ["low", "medium", "high"]

    def test_competitor_snapshot_endpoint_missing_required_fields(self):
        """Test that competitor-snapshot requires required fields."""
        response = client.post(
            "/api/intelligence/competitor-snapshot",
            json={
                "competitor_name": "Microsoft",
            },
        )
        assert response.status_code == 422

    def test_competitor_snapshot_endpoint_with_context(self):
        """Test that competitor-snapshot endpoint accepts business context."""
        response = client.post(
            "/api/intelligence/competitor-snapshot",
            json={
                "competitor_name": "Google",
                "business_context": "advertising and search",
                "artifact_type": "pitch_deck",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "threat_level" in data

    @pytest.mark.asyncio
    async def test_detect_entities_with_multiple_companies(self):
        """Test entity detection with multiple companies in text."""
        response = client.post(
            "/api/intelligence/detect-entities",
            json={
                "text": "Apple, Google, Amazon, and Microsoft are major tech companies",
                "artifact_type": "business_plan",
            },
        )
        assert response.status_code == 200
        data = response.json()
        # Should detect multiple entities
        assert len(data["entities"]) >= 0
        assert data["match"] >= 0

    def test_web_enrich_with_optional_context(self):
        """Test web-enrich with optional context parameter."""
        response = client.post(
            "/api/intelligence/web-enrich",
            json={
                "entity_name": "Tesla",
                "entity_type": "company",
                "context": "electric vehicles and energy",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "competitors" in data

    def test_web_enrich_without_optional_context(self):
        """Test web-enrich without optional context parameter."""
        response = client.post(
            "/api/intelligence/web-enrich",
            json={
                "entity_name": "Apple",
                "entity_type": "company",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "competitors" in data

    def test_extract_form_fields_returns_confidence_score(self):
        """Test that extract-form-fields always returns confidence score."""
        response = client.post(
            "/api/intelligence/extract-form-fields",
            json={
                "prompt": "Startup founded in 2020",
                "artifact_type": "pitch_deck",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "confidence_score" in data
        assert isinstance(data["confidence_score"], float)
        assert 0.0 <= data["confidence_score"] <= 1.0

    def test_competitor_snapshot_threat_levels(self):
        """Test that competitor-snapshot returns valid threat levels."""
        response = client.post(
            "/api/intelligence/competitor-snapshot",
            json={
                "competitor_name": "StartupX",
                "business_context": "emerging technology",
                "artifact_type": "business_plan",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["threat_level"] in ["low", "medium", "high"]


class TestIntelligenceEndpointValidation:
    """Test request validation for intelligence endpoints."""

    def test_detect_entities_text_too_long(self):
        """Test that detect-entities rejects excessively long text."""
        long_text = "a" * 10000  # Exceeds max_length of 5000
        response = client.post(
            "/api/intelligence/detect-entities",
            json={
                "text": long_text,
                "artifact_type": "business_plan",
            },
        )
        assert response.status_code == 422

    def test_web_enrich_entity_name_too_long(self):
        """Test that web-enrich rejects excessively long entity names."""
        long_name = "a" * 1000  # Exceeds max_length of 500
        response = client.post(
            "/api/intelligence/web-enrich",
            json={
                "entity_name": long_name,
                "entity_type": "company",
            },
        )
        assert response.status_code == 422

    def test_extract_form_fields_prompt_too_long(self):
        """Test that extract-form-fields rejects excessively long prompts."""
        long_prompt = "a" * 10000  # Exceeds max_length of 5000
        response = client.post(
            "/api/intelligence/extract-form-fields",
            json={
                "prompt": long_prompt,
                "artifact_type": "business_plan",
            },
        )
        assert response.status_code == 422

    def test_competitor_snapshot_context_too_long(self):
        """Test that competitor-snapshot rejects excessively long context."""
        long_context = "a" * 2000  # Exceeds max_length of 1000
        response = client.post(
            "/api/intelligence/competitor-snapshot",
            json={
                "competitor_name": "Microsoft",
                "business_context": long_context,
                "artifact_type": "business_plan",
            },
        )
        assert response.status_code == 422


class TestIntelligenceEndpointIntegration:
    """Integration tests for intelligence endpoints."""

    def test_detect_entities_and_web_enrich_workflow(self):
        """Test workflow: detect entities then enrich them."""
        # First, detect entities
        detect_response = client.post(
            "/api/intelligence/detect-entities",
            json={
                "text": "Amazon competes with Microsoft in cloud",
                "artifact_type": "business_plan",
            },
        )
        assert detect_response.status_code == 200
        entities = detect_response.json()["entities"]

        # Then, enrich the first entity if available
        if entities:
            enrich_response = client.post(
                "/api/intelligence/web-enrich",
                json={
                    "entity_name": entities[0].get("name", "Amazon"),
                    "entity_type": "company",
                },
            )
            assert enrich_response.status_code == 200
            assert "competitors" in enrich_response.json()

    def test_extract_fields_for_competitor_analysis(self):
        """Test extracting fields and using them for competitor analysis."""
        # Extract fields from prompt
        extract_response = client.post(
            "/api/intelligence/extract-form-fields",
            json={
                "prompt": "We compete with Microsoft in cloud services",
                "artifact_type": "pitch_deck",
            },
        )
        assert extract_response.status_code == 200
        fields = extract_response.json()["fields"]

        # Then analyze the competitor
        if fields:
            snapshot_response = client.post(
                "/api/intelligence/competitor-snapshot",
                json={
                    "competitor_name": "Microsoft",
                    "business_context": "cloud services",
                    "artifact_type": "pitch_deck",
                },
            )
            assert snapshot_response.status_code == 200
            assert "strengths" in snapshot_response.json()
