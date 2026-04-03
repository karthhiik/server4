"""Tests for WebEnricher Service.

Tests entity detection, web search caching, and form field extraction.
"""

import pytest
from unittest.mock import patch, AsyncMock
from app.services.intelligence.web_enricher import WebEnricher


class TestWebEnricher:
    """Test suite for WebEnricher service."""

    @pytest.mark.asyncio
    async def test_detect_entities_calls_ner_model(self):
        """Test that detect_entities calls NER model and returns entities."""
        enricher = WebEnricher()
        with patch.object(enricher, '_call_ner_model', new_callable=AsyncMock) as mock_ner:
            mock_ner.return_value = [
                {'name': 'Amazon', 'type': 'company', 'span': (0, 6), 'confidence': 0.95}
            ]
            entities = await enricher.detect_entities("Amazon is great")
            assert len(entities) == 1
            assert entities[0]['name'] == 'Amazon'
            assert entities[0]['type'] == 'company'
            assert entities[0]['confidence'] == 0.95
            mock_ner.assert_called_once()

    @pytest.mark.asyncio
    async def test_web_search_returns_cached_results_within_2hrs(self):
        """Test that web search results are cached for 2 hours."""
        enricher = WebEnricher()

        # First call should hit the API
        with patch.object(enricher, '_call_search_api', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {'revenue': '$200B', 'founded': 1994}
            result1 = await enricher.search_company('Amazon', 'fast')
            assert result1['revenue'] == '$200B'
            assert mock_search.call_count == 1

        # Second call should use cache (not hit API)
        with patch.object(enricher, '_call_search_api', new_callable=AsyncMock) as mock_search:
            result2 = await enricher.search_company('Amazon', 'fast')
            assert result2['revenue'] == '$200B'
            # Should NOT call the API this time due to cache
            assert mock_search.call_count == 0

    @pytest.mark.asyncio
    async def test_extract_form_fields_from_prompt(self):
        """Test that extract_form_fields extracts structured data from prompt."""
        enricher = WebEnricher()
        prompt = "Amazon founded in 1994, works in e-commerce"

        with patch.object(enricher, '_call_extraction_model', new_callable=AsyncMock) as mock:
            mock.return_value = {
                'company_name': 'Amazon',
                'founded_year': 1994,
                'industry': 'e-commerce'
            }
            fields = await enricher.extract_form_fields(prompt)
            assert fields['company_name'] == 'Amazon'
            assert fields['industry'] == 'e-commerce'
            assert fields['founded_year'] == 1994

    @pytest.mark.asyncio
    async def test_entity_detection_caches_for_5_minutes(self):
        """Test that entity detection results cache for 5 minutes."""
        enricher = WebEnricher()
        text = "Google and Microsoft"

        # First call
        with patch.object(enricher, '_call_ner_model', new_callable=AsyncMock) as mock_ner:
            mock_ner.return_value = [
                {'name': 'Google', 'type': 'company', 'span': (0, 6), 'confidence': 0.95},
                {'name': 'Microsoft', 'type': 'company', 'span': (12, 21), 'confidence': 0.95},
            ]
            entities1 = await enricher.detect_entities(text)
            assert len(entities1) == 2
            assert mock_ner.call_count == 1

        # Second call should use cache
        with patch.object(enricher, '_call_ner_model', new_callable=AsyncMock) as mock_ner:
            entities2 = await enricher.detect_entities(text)
            assert len(entities2) == 2
            # Should NOT call the NER model due to cache
            assert mock_ner.call_count == 0

    @pytest.mark.asyncio
    async def test_search_company_returns_empty_dict_on_error(self):
        """Test that search_company gracefully handles errors."""
        enricher = WebEnricher()

        with patch.object(enricher, '_call_search_api', new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = Exception("API error")
            result = await enricher.search_company('UnknownCompany')
            assert result == {'revenue': None, 'competitors': []}

    @pytest.mark.asyncio
    async def test_extract_form_fields_handles_invalid_json(self):
        """Test that extract_form_fields handles invalid JSON response."""
        enricher = WebEnricher()
        prompt = "Some invalid prompt"

        # Mock AI model to return invalid JSON
        with patch.object(enricher, '_call_extraction_model', new_callable=AsyncMock) as mock:
            mock.return_value = "invalid json"
            # The extraction should handle this gracefully
            fields = await enricher.extract_form_fields(prompt)
            # Should return default structure
            assert 'company_name' in fields
