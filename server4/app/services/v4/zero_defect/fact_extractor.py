"""
Fact Extractor - Extracts factual claims from user input
Uses LLM to identify statements that can be verified
"""

import re
from typing import List
from app.services.v4.zero_defect.models import Fact
from app.config import settings


class FactExtractor:
    """Extracts factual claims from user input for verification"""
    
    def __init__(self):
        self.fact_patterns = [
            # Numbers and measurements
            r'\$\d+(?:,\d{3})*(?:\.\d{2})?',  # Money amounts
            r'\d+(?:,\d{3})*(?:\.\d+)?\s*(?:million|billion|trillion|thousand|hundred)',
            r'\d+%',
            # Time references
            r'(?:in|since|by|during|as of)\s+\d{4}',
            r'(?:Q[1-4]|quarter\s+\d)',
            # Company claims
            r'(?:raised|funded|secured|invested)\s+\$',
            r'(?:CEO|CTO|CFO|founder|co-founder)',
            # Product claims
            r'(?:launched|released|introduced|announced)',
            # Market claims
            r'(?:market share|revenue|users|customers)',
        ]
    
    async def extract(self, user_input: str) -> List[Fact]:
        """
        Extract factual claims from user input
        
        Args:
            user_input: Raw user input text
            
        Returns:
            List of Fact objects
        """
        facts = []
        
        # Use LLM to extract facts
        llm_facts = await self._extract_with_llm(user_input)
        
        # Use regex patterns as fallback
        regex_facts = self._extract_with_regex(user_input)
        
        # Combine and deduplicate
        all_facts = llm_facts + regex_facts
        seen_claims = set()
        
        for fact in all_facts:
            if fact.claim not in seen_claims:
                seen_claims.add(fact.claim)
                facts.append(fact)
        
        return facts
    
    async def _extract_with_llm(self, user_input: str) -> List[Fact]:
        """
        Use LLM to extract factual claims
        
        Args:
            user_input: Raw user input text
            
        Returns:
            List of Fact objects
        """
        from app.services.llm.model_router import ModelRouter, TaskType
        
        model_router = ModelRouter.get_instance()
        
        system_prompt = """You are a fact extraction expert. Your task is to extract factual claims from user input that can be verified through web search.

Extract claims that are:
- Quantitative (numbers, dates, money amounts)
- Specific (company names, person names, locations)
- Verifiable (can be checked against external sources)

DO NOT extract:
- Opinions
- Vague statements
- Future predictions
- Subjective descriptions

Return your response as a JSON array of objects with:
- claim: the exact factual claim
- context: surrounding context for the claim
- confidence: 0.0-1.0 confidence score that this is a verifiable fact"""

        user_prompt = f"""Extract factual claims from this user input:

{user_input}

Return only the JSON array, no other text."""

        try:
            response = await model_router.complete(
                task_type=TaskType.FACT_SYNTHESIS_JSON,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            import json
            facts_data = json.loads(response.content)
            
            # Handle both array and object with array field
            if isinstance(facts_data, dict) and "facts" in facts_data:
                facts_data = facts_data["facts"]
            elif isinstance(facts_data, dict):
                facts_data = [facts_data]
            
            facts = []
            for fact_data in facts_data:
                fact = Fact(
                    claim=fact_data.get("claim", ""),
                    context=fact_data.get("context", ""),
                    confidence=fact_data.get("confidence", 0.5)
                )
                facts.append(fact)
            
            return facts
            
        except Exception as e:
            # Log error and return empty list
            print(f"Error extracting facts with LLM: {e}")
            return []
    
    def _extract_with_regex(self, user_input: str) -> List[Fact]:
        """
        Use regex patterns to extract factual claims as fallback
        
        Args:
            user_input: Raw user input text
            
        Returns:
            List of Fact objects
        """
        facts = []
        
        for pattern in self.fact_patterns:
            matches = re.finditer(pattern, user_input, re.IGNORECASE)
            for match in matches:
                # Extract surrounding context
                start = max(0, match.start() - 50)
                end = min(len(user_input), match.end() + 50)
                context = user_input[start:end].strip()
                
                fact = Fact(
                    claim=match.group(),
                    context=context,
                    confidence=0.6  # Lower confidence for regex extraction
                )
                facts.append(fact)
        
        return facts
