"""
Root Cause Analyzer - Analyzes failures to determine root cause
Uses LLM to analyze why a failure occurred
"""

from typing import Dict, Any, Optional
from app.services.v4.auto_regeneration.failure_detector import Failure


class RootCauseAnalyzer:
    """
    Analyzes failures to determine root cause
    Uses LLM to understand why a failure occurred
    """
    
    async def analyze(self, failure: Failure, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the root cause of a failure
        
        Args:
            failure: Detected failure
            context: Additional context about the generation
            
        Returns:
            Dictionary with root cause analysis
        """
        from app.services.llm.model_router import ModelRouter
        
        model_router = ModelRouter()
        
        system_prompt = """You are a root cause analysis expert. Your task is to analyze why a failure occurred in a slide generation process.

Analyze the failure and determine:
- Root cause: The primary reason for the failure
- Contributing factors: Other factors that contributed to the failure
- Suggested fixes: Specific recommendations to fix the issue
- Prevention: How to prevent this failure in the future

Return JSON with:
- root_cause: string description of the root cause
- contributing_factors: list of contributing factors
- suggested_fixes: list of specific fixes
- prevention: list of prevention strategies
- confidence: 0.0-1.0 confidence in this analysis"""

        user_prompt = f"""Failure Type: {failure.failure_type}
Severity: {failure.severity}
Message: {failure.message}

Failure Context:
{failure.context}

Generation Context:
{context}

Analyze the root cause and return JSON only."""

        try:
            from app.services.llm.model_router import TaskType
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await model_router.complete(
                task_type=TaskType.TEMPLATE_FILL,
                messages=messages,
                max_tokens=800,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.content)
            
            return {
                "root_cause": result.get("root_cause", "Unknown"),
                "contributing_factors": result.get("contributing_factors", []),
                "suggested_fixes": result.get("suggested_fixes", []),
                "prevention": result.get("prevention", []),
                "confidence": result.get("confidence", 0.5)
            }
            
        except Exception as e:
            print(f"Error analyzing root cause: {e}")
            
            # Fallback: Simple rule-based analysis
            return self._fallback_analysis(failure, context)
    
    def _fallback_analysis(self, failure: Failure, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback rule-based analysis when LLM fails
        
        Args:
            failure: Detected failure
            context: Generation context
            
        Returns:
            Dictionary with basic analysis
        """
        root_cause = "Unknown"
        contributing_factors = []
        suggested_fixes = []
        
        if failure.failure_type == "low_confidence":
            root_cause = "Low confidence in generated content"
            contributing_factors = ["Insufficient source verification", "Ambiguous input"]
            suggested_fixes = ["Add more specific input", "Enable additional verification"]
            
        elif failure.failure_type == "generation_error":
            root_cause = "Error during generation process"
            contributing_factors = ["Model failure", "API timeout", "Invalid input"]
            suggested_fixes = ["Retry with different model", "Check input format"]
            
        elif failure.failure_type == "validation_error":
            root_cause = "Validation failed on generated content"
            contributing_factors = ["Factual inaccuracies", "Missing information"]
            suggested_fixes = ["Add source citations", "Complete missing information"]
        
        return {
            "root_cause": root_cause,
            "contributing_factors": contributing_factors,
            "suggested_fixes": suggested_fixes,
            "prevention": ["Improve input validation", "Add more sources"],
            "confidence": 0.5
        }
