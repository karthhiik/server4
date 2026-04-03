"""InputProcessor Service for Business Plan Canvas.

Parses user input from 3 sources (prompt/PDF/form) into unified context.
First service in the Business Plan generation pipeline.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import re


@dataclass
class ParsedContext:
    """Represents parsed context from user input."""
    companies: List[str]
    filled_fields: int
    completeness: float
    primary_source: str
    prompt_text: Optional[str] = None
    form_data: Optional[Dict] = None
    pdf_data: Optional[Dict] = None


class InputProcessor:
    """Parse and merge input from multiple sources (prompt, form, PDF)."""

    def __init__(self):
        """Initialize InputProcessor with company name patterns."""
        # Pattern for detecting known companies
        self.company_pattern = r'\b(?:Amazon|Microsoft|Google|Apple|Meta|Tesla|Netflix|Spotify)\b'

    def parse_prompt(self, prompt_text: str) -> Dict[str, Any]:
        """Extract companies and context from prompt.

        Args:
            prompt_text: The user's prompt text

        Returns:
            Dictionary with extracted context including companies, completeness score
        """
        companies = self.extract_entities(prompt_text)
        return {
            'companies': [c['name'] for c in companies],
            'prompt_text': prompt_text,
            'completeness': 0.3,
            'filled_fields': 1,
            'source': 'prompt'
        }

    def parse_form(self, form_data: Dict) -> Dict[str, Any]:
        """Convert form data to context.

        Args:
            form_data: Dictionary of form field values

        Returns:
            Dictionary with parsed form context and completeness metrics
        """
        filled = sum(1 for v in form_data.values() if v)
        total = len(form_data)
        return {
            'company_name': form_data.get('company_name'),
            'industry': form_data.get('industry'),
            'target_market': form_data.get('target_market'),
            'filled_fields': filled,
            'completeness': filled / total if total > 0 else 0,
            'source': 'form',
            'form_data': form_data
        }

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract company names using regex + NER.

        Args:
            text: The input text to search for entities

        Returns:
            List of extracted entities with name, type, and confidence
        """
        pattern = r'\b(?:Amazon|Microsoft|Google|Apple|Meta|Tesla|Netflix|Spotify)\b'
        matches = re.findall(pattern, text, re.IGNORECASE)
        return [{'name': m, 'type': 'company', 'confidence': 0.9} for m in matches]

    def merge_contexts(self, contexts: List[Dict]) -> Dict[str, Any]:
        """Intelligently merge multiple context sources.

        Prioritizes by completeness score and intelligently combines data
        from prompt, form, and PDF sources.

        Args:
            contexts: List of context dictionaries from different sources

        Returns:
            Merged context with primary source selection and combined data
        """
        if not contexts:
            return {}

        # Find primary source (highest completeness)
        primary = max(contexts, key=lambda c: c.get('completeness', 0))
        merged = {
            'primary_source': primary.get('source', 'unknown'),
            'completeness_score': primary.get('completeness', 0),
            'all_companies': [],
            'all_fields': {}
        }

        # Collect all companies
        for ctx in contexts:
            if 'companies' in ctx:
                merged['all_companies'].extend(ctx['companies'])

        # Merge all fields
        for ctx in contexts:
            if 'form_data' in ctx:
                merged['all_fields'].update(ctx['form_data'])
            if 'company_name' in ctx:
                merged['company_name'] = ctx['company_name']
            if 'industry' in ctx:
                merged['industry'] = ctx['industry']

        return merged
