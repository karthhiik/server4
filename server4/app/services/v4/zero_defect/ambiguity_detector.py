"""
Ambiguity Detector - Detects ambiguous statements in user input
Uses LLM to identify statements that need clarification
"""

from typing import List
from app.services.v4.zero_defect.models import Ambiguity
from app.config import settings


class AmbiguityDetector:
    """Detects ambiguous statements that need clarification"""
    
    async def detect(self, user_input: str) -> List[Ambiguity]:
        """
        Detect ambiguous statements in user input
        
        Args:
            user_input: Raw user input text
            
        Returns:
            List of Ambiguity objects
        """
        from app.services.llm.model_router import ModelRouter
        
        model_router = ModelRouter()
        
        system_prompt = """You are an ambiguity detection expert. Your task is to identify statements in user input that are ambiguous and need clarification.

Look for:
- Vague terms (e.g., "soon", "recent", "large")
- Contradictory statements
- Missing context (e.g., "we raised money" without amount)
- Unclear references (e.g., "they" without specifying who)
- Incomplete information

For each ambiguity, provide:
- statement: the exact ambiguous statement
- ambiguity_type: one of "vague", "contradictory", "missing_context", "unclear_reference"
- clarification_question: question to ask user to clarify
- suggested_clarification: suggested clarification based on context
- confidence: 0.0-1.0 confidence score that this is ambiguous

Return your response as a JSON array of objects."""

        user_prompt = f"""Detect ambiguous statements in this user input:

{user_input}

Return only the JSON array, no other text."""

        try:
            from app.services.llm.model_router import ModelRouter, TaskType
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await model_router.complete(
                task_type=TaskType.TEMPLATE_FILL,
                messages=messages,
                max_tokens=1000,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            import json
            ambiguities_data = json.loads(response.content)
            
            ambiguities = []
            for amb_data in ambiguities_data:
                ambiguity = Ambiguity(
                    statement=amb_data.get("statement", ""),
                    ambiguity_type=amb_data.get("ambiguity_type", "vague"),
                    clarification_question=amb_data.get("clarification_question", ""),
                    suggested_clarification=amb_data.get("suggested_clarification", ""),
                    confidence=amb_data.get("confidence", 0.5)
                )
                ambiguities.append(ambiguity)
            
            return ambiguities
            
        except Exception as e:
            print(f"Error detecting ambiguities: {e}")
            return []
