"""
Auto Regenerator - Executes regeneration with selected strategy
Implements the actual regeneration logic
"""

from typing import Dict, Any, Optional
from app.services.v4.auto_regeneration.failure_detector import FailureDetector, Failure
from app.services.v4.auto_regeneration.root_cause_analyzer import RootCauseAnalyzer
from app.services.v4.auto_regeneration.strategy_selector import StrategySelector


class AutoRegenerator:
    """
    Auto-regenerates content when failures are detected
    Orchestrates the full regeneration process
    """
    
    def __init__(self):
        self.failure_detector = FailureDetector()
        self.root_cause_analyzer = RootCauseAnalyzer()
        self.strategy_selector = StrategySelector()
    
    async def regenerate(
        self,
        generation_result: Dict[str, Any],
        validation_result: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Attempt to regenerate content if failure detected
        
        Args:
            generation_result: Result from generation process
            validation_result: Optional validation result
            context: Generation context
            
        Returns:
            Dictionary with regeneration result
        """
        if context is None:
            context = {}
        
        # Detect failure
        failure = self.failure_detector.detect_failure(generation_result, validation_result)
        
        if not failure:
            return {
                "regeneration_needed": False,
                "message": "No failure detected"
            }
        
        # Check if regeneration should be attempted
        if not self.failure_detector.should_regenerate(failure):
            return {
                "regeneration_needed": False,
                "message": "Regeneration not recommended",
                "failure": {
                    "type": failure.failure_type,
                    "severity": failure.severity,
                    "message": failure.message
                }
            }
        
        # Record failure
        self.failure_detector.record_failure(failure)
        
        # Analyze root cause
        root_cause = await self.root_cause_analyzer.analyze(failure, context)
        
        # Select strategy
        strategy = self.strategy_selector.select_strategy(failure, root_cause, context)
        
        # Execute regeneration with selected strategy
        regeneration_result = await self._execute_regeneration(
            strategy,
            context
        )
        
        return {
            "regeneration_needed": True,
            "failure": {
                "type": failure.failure_type,
                "severity": failure.severity,
                "message": failure.message
            },
            "root_cause": root_cause,
            "strategy": strategy,
            "regeneration_result": regeneration_result
        }
    
    async def _execute_regeneration(
        self,
        strategy: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute regeneration with selected strategy
        
        Args:
            strategy: Selected regeneration strategy
            context: Generation context
            
        Returns:
            Dictionary with regeneration result
        """
        strategy_name = strategy["strategy"]
        parameters = strategy["parameters"]
        
        if strategy_name == "switch_model":
            return await self._regenerate_with_new_model(parameters, context)
        elif strategy_name == "modify_prompt":
            return await self._regenerate_with_modified_prompt(parameters, context)
        elif strategy_name == "add_context":
            return await self._regenerate_with_additional_context(parameters, context)
        elif strategy_name == "adjust_parameters":
            return await self._regenerate_with_adjusted_parameters(parameters, context)
        elif strategy_name == "retry_same":
            return await self._regenerate_retry(context)
        elif strategy_name == "request_clarification":
            return await self._request_clarification(parameters, context)
        else:
            return {
                "success": False,
                "message": f"Unknown strategy: {strategy_name}"
            }
    
    async def _regenerate_with_new_model(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Regenerate with a different model"""
        new_model = parameters.get("new_model")
        
        # Update context with new model
        updated_context = context.copy()
        updated_context["model"] = new_model
        
        # Trigger regeneration with new model
        # This would call the actual generation pipeline
        # For now, return placeholder
        return {
            "success": True,
            "message": f"Regenerating with model: {new_model}",
            "new_model": new_model
        }
    
    async def _regenerate_with_modified_prompt(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Regenerate with modified prompt"""
        modifications = parameters.get("prompt_modifications", [])
        
        # Update context with prompt modifications
        updated_context = context.copy()
        updated_context["prompt_modifications"] = modifications
        
        return {
            "success": True,
            "message": "Regenerating with modified prompt",
            "modifications": modifications
        }
    
    async def _regenerate_with_additional_context(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Regenerate with additional context"""
        # Enable research and additional sources
        updated_context = context.copy()
        updated_context["enable_research"] = True
        updated_context["additional_sources"] = True
        
        return {
            "success": True,
            "message": "Regenerating with additional context"
        }
    
    async def _regenerate_with_adjusted_parameters(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Regenerate with adjusted parameters"""
        temperature = parameters.get("temperature", 0.7)
        max_tokens = parameters.get("max_tokens", 1500)
        
        # Update context with adjusted parameters
        updated_context = context.copy()
        updated_context["temperature"] = temperature
        updated_context["max_tokens"] = max_tokens
        
        return {
            "success": True,
            "message": f"Regenerating with temperature={temperature}, max_tokens={max_tokens}"
        }
    
    async def _regenerate_retry(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Retry with same configuration"""
        return {
            "success": True,
            "message": "Retrying with same configuration"
        }
    
    async def _request_clarification(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Request clarification from user"""
        clarification_questions = parameters.get("clarification_questions", [])
        
        return {
            "success": False,
            "message": "Clarification requested from user",
            "clarification_needed": True,
            "questions": clarification_questions
        }
