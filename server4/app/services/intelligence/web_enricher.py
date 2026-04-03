"""WebEnricher Service for entity detection and web search.

Handles:
1. Named Entity Recognition (NER) for company/organization extraction
2. Web search for company information with 2-hour caching
3. Form field extraction from prompts

Uses OpenAI NER model, search API, and structured extraction model.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp

from app.core.ai import ai_factory
from app.core.cache_service import cache_service

logger = logging.getLogger(__name__)


class WebEnricher:
    """Extract entities, search web data, and enrich form fields."""

    def __init__(self):
        """Initialize WebEnricher with cache configuration."""
        self.cache_ttl = 7200  # 2 hours for web search cache
        self.max_companies = 15

    async def detect_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract companies/entities from text using NER.

        Args:
            text: Input text to analyze

        Returns:
            List of extracted entities with name, type, confidence, and span
        """
        cache_key = f"entities:{hash(text)}"
        cached = await cache_service.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for entities from text")
            return cached

        entities = await self._call_ner_model(text)
        await cache_service.set(cache_key, entities, ttl=300)  # 5 min cache
        return entities

    async def _call_ner_model(self, text: str) -> List[Dict]:
        """Call NER model for entity extraction.

        Args:
            text: Input text to analyze

        Returns:
            List of extracted entities
        """
        ai = ai_factory.get_model('utility')  # Fast, cheap model
        prompt = f"""Extract company/organization names from text. Return JSON array.
Text: {text}
Return: [{{"name": "Company", "type": "company", "span": [0, 7], "confidence": 0.9}}]"""

        try:
            response = await ai.complete(prompt)
            entities = json.loads(response)
            if not isinstance(entities, list):
                return []
            return entities
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse NER response: {e}")
            return []

    async def search_company(
        self, company_name: str, research_mode: str = 'fast'
    ) -> Dict[str, Any]:
        """Search for company data via web search API.

        Args:
            company_name: Name of company to search
            research_mode: 'fast' or 'detailed' search mode

        Returns:
            Dictionary with revenue, competitors, and other data
        """
        cache_key = f"web_search:{company_name}"
        cached = await cache_service.get(cache_key)
        if cached:
            logger.info(f"Cache hit for web search: {company_name}")
            return cached

        try:
            results = await self._call_search_api(company_name, research_mode)
            await cache_service.set(cache_key, results, ttl=self.cache_ttl)
            return {
                'revenue': results.get('revenue'),
                'competitors': results.get('competitors', []),
                'founded': results.get('founded'),
                'market_cap': results.get('market_cap'),
            }
        except Exception as e:
            logger.error(f"Search failed for {company_name}: {e}")
            return {'revenue': None, 'competitors': []}

    async def _call_search_api(self, company_name: str, mode: str) -> Dict:
        """Call search API (Serper, Tavily, or Exa).

        Args:
            company_name: Company to search
            mode: Search mode

        Returns:
            Search results dictionary
        """
        # Mock implementation - in production, call actual search API
        logger.debug(f"Searching for {company_name} in {mode} mode")
        return {
            'revenue': '$200B',
            'market_cap': '$2.1T',
            'founded': 1994,
            'competitors': ['Microsoft', 'Google'],
        }

    async def extract_form_fields(self, prompt: str) -> Dict[str, Any]:
        """Extract structured form fields from prompt text.

        Args:
            prompt: User prompt containing business information

        Returns:
            Dictionary with extracted form fields
        """
        cache_key = f"form_fields:{hash(prompt)}"
        cached = await cache_service.get(cache_key)
        if cached:
            logger.debug("Cache hit for form fields extraction")
            return cached

        try:
            fields = await self._call_extraction_model(prompt)
            if not isinstance(fields, dict):
                fields = {'company_name': None}
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse extraction response: {e}")
            fields = {'company_name': None}

        await cache_service.set(cache_key, fields, ttl=300)
        return fields

    async def _call_extraction_model(self, prompt: str) -> Dict:
        """Call extraction model for form field parsing.

        Args:
            prompt: Input prompt

        Returns:
            Extracted form fields
        """
        ai = ai_factory.get_model('utility')
        extraction_prompt = f"""Extract business form fields from prompt.
Prompt: {prompt}
Return JSON with: company_name, industry, stage, team_size, revenue (if mentioned)
Only include fields that are explicitly mentioned."""

        try:
            response = await ai.complete(extraction_prompt)
            fields = json.loads(response)
            if not isinstance(fields, dict):
                return {'company_name': None}
            return fields
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse extraction response: {e}")
            return {'company_name': None}

    async def enrich_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich business context with web data and extracted fields.

        Args:
            context: Initial context dictionary

        Returns:
            Enriched context with web search results and entity data
        """
        companies = context.get('companies', [])
        if not companies:
            return context

        enriched = context.copy()
        enriched['web_data'] = {}

        # Search for each company (limited to max_companies)
        for company in companies[:self.max_companies]:
            try:
                search_result = await self.search_company(company)
                enriched['web_data'][company] = search_result
            except Exception as e:
                logger.error(f"Failed to enrich {company}: {e}")

        return enriched
