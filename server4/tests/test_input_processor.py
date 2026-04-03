"""Tests for InputProcessor Service."""

import pytest
from app.services.intelligence.input_processor import InputProcessor


class TestInputProcessor:
    """Test suite for InputProcessor service."""

    def test_parse_prompt_detects_companies(self):
        """Test that parse_prompt detects company names in text."""
        processor = InputProcessor()
        context = processor.parse_prompt("Give business plan for Amazon and Microsoft")
        assert "Amazon" in context['companies']
        assert "Microsoft" in context['companies']
        assert context['prompt_text'] == "Give business plan for Amazon and Microsoft"

    def test_parse_form_fills_context(self):
        """Test that parse_form correctly processes form data."""
        processor = InputProcessor()
        form_data = {
            'company_name': 'Tesla',
            'industry': 'Automotive',
            'target_market': 'Premium buyers',
        }
        context = processor.parse_form(form_data)
        assert context['company_name'] == 'Tesla'
        assert context['industry'] == 'Automotive'
        assert context['filled_fields'] == 3

    def test_merge_contexts_prioritizes_by_completeness(self):
        """Test that merge_contexts prioritizes sources by completeness."""
        processor = InputProcessor()
        prompt_ctx = {'companies': ['Amazon'], 'prompt_text': 'test', 'completeness': 0.3, 'source': 'prompt'}
        form_ctx = {'company_name': 'Amazon', 'industry': 'Tech', 'completeness': 0.5, 'source': 'form'}
        merged = processor.merge_contexts([prompt_ctx, form_ctx])
        assert merged['primary_source'] == 'form'
        assert merged['company_name'] == 'Amazon'

    def test_extract_entities_from_text(self):
        """Test that extract_entities finds company names."""
        processor = InputProcessor()
        text = "Amazon competes with Microsoft and Google"
        entities = processor.extract_entities(text)
        assert len(entities) >= 3
        assert any(e['name'] == 'Amazon' for e in entities)
