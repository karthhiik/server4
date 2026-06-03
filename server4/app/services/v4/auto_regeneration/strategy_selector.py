"""
Strategy Selector - Selects regeneration strategy based on root cause
Chooses the best approach to fix the failure
"""

from typing import Dict, Any, List
from app.services.v4.auto_regeneration.failure_detector import Failure


class StrategySelector:
    """
    Selects the best regeneration strategy based on failure analysis
    """
    
    def __init__(self):
        self.strategies = {
            "switch_model": {
                "description": "Switch to a different model for generation",
                "priority": 1,
                "applicable_failures": ["generation_error", "low_confidence"]
            },
            "modify_prompt": {
                "description": "Modify the generation prompt for better results",
                "priority": 2,
                "applicable_failures": ["low_confidence", "validation_error"]
            },
            "add_context": {
                "description": "Add more context or sources to improve generation",
                "priority": 2,
                "applicable_failures": ["validation_error", "low_confidence"]
            },
            "adjust_parameters": {
                "description": "Adjust generation parameters (temperature, max_tokens)",
                "priority": 3,
                "applicable_failures": ["low_confidence"]
            },
            "retry_same": {
                "description": "Retry with the same configuration",
                "priority": 4,
                "applicable_failures": ["generation_error"]
            },
            "request_clarification": {
                "description": "Request clarification from user",
                "priority": 5,
                "applicable_failures": ["validation_error"]
            }
        }
    
    def select_strategy(
        self,
        failure: Failure,
        root_cause: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Select the best regeneration strategy
        
        Args:
            failure: Detected failure
            root_cause: Root cause analysis
            context: Generation context
            
        Returns:
            Dictionary with selected strategy and parameters
        """
        # Get applicable strategies based on failure type
        applicable_strategies = self._get_applicable_strategies(failure.failure_type)
        
        # Sort by priority
        applicable_strategies.sort(key=lambda x: x["priority"])
        
        # Select best strategy
        if not applicable_strategies:
            # Fallback to retry
            strategy = "retry_same"
        else:
            strategy = applicable_strategies[0]["name"]
        
        # Generate strategy parameters
        parameters = self._generate_strategy_parameters(
            strategy,
            failure,
            root_cause,
            context
        )
        
        return {
            "strategy": strategy,
            "description": self.strategies[strategy]["description"],
            "parameters": parameters,
            "priority": self.strategies[strategy]["priority"]
        }
    
    def _get_applicable_strategies(self, failure_type: str) -> List[Dict[str, Any]]:
        """Get strategies applicable to a failure type"""
        applicable = []
        
        for strategy_name, strategy_info in self.strategies.items():
            if failure_type in strategy_info["applicable_failures"]:
                applicable.append({
                    "name": strategy_name,
                    "priority": strategy_info["priority"]
                })
        
        return applicable
    
    def _generate_strategy_parameters(
        self,
        strategy: str,
        failure: Failure,
        root_cause: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate parameters for the selected strategy"""
        parameters = {}
        
        if strategy == "switch_model":
            parameters = self._generate_switch_model_params(failure, context)
        elif strategy == "modify_prompt":
            parameters = self._generate_modify_prompt_params(failure, root_cause)
        elif strategy == "add_context":
            parameters = self._generate_add_context_params(failure, root_cause)
        elif strategy == "adjust_parameters":
            parameters = self._generate_adjust_params_params(failure)
        elif strategy == "retry_same":
            parameters = {}
        elif strategy == "request_clarification":
            parameters = self._generate_clarification_params(failure, root_cause)
        
        return parameters
    
    def _generate_switch_model_params(self, failure: Failure, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate parameters for switch_model strategy"""
        current_model = context.get("model", "gpt-4o-mini")
        
        # Get fallback chain from config
        from app.services.v4.zero_defect.council.council_config import ZeroDefectCouncilConfig
        config = ZeroDefectCouncilConfig()
        fallback_chain = config.get_fallback_chain(current_model)
        
        if fallback_chain:
            new_model = fallback_chain[0]
        else:
            # Default fallback
            new_model = "gpt-4o-mini" if current_model != "gpt-4o-mini" else "DeepSeek-V3.2"
        
        return {
            "new_model": new_model,
            "reason": f"Switching from {current_model} to {new_model}"
        }
    
    def _generate_modify_prompt_params(self, failure: Failure, root_cause: Dict[str, Any]) -> Dict[str, Any]:
        """Generate parameters for modify_prompt strategy"""
        suggested_fixes = root_cause.get("suggested_fixes", [])
        
        modifications = []
        for fix in suggested_fixes[:3]:  # Use top 3 fixes
            modifications.append(fix)
        
        return {
            "prompt_modifications": modifications,
            "reason": "Modifying prompt based on root cause analysis"
        }
    
    def _generate_add_context_params(self, failure: Failure, root_cause: Dict[str, Any]) -> Dict[str, Any]:
        """Generate parameters for add_context strategy"""
        return {
            "additional_sources": True,
            "enable_research": True,
            "reason": "Adding more context to improve generation"
        }
    
    def _generate_adjust_params_params(self, failure: Failure) -> Dict[str, Any]:
        """Generate parameters for adjust_parameters strategy"""
        current_temp = failure.context.get("temperature", 0.7)
        current_max_tokens = failure.context.get("max_tokens", 1500)
        
        # Adjust temperature based on confidence
        if failure.failure_type == "low_confidence":
            new_temp = max(0.1, current_temp - 0.2)  # Lower temperature for more deterministic output
        else:
            new_temp = min(1.0, current_temp + 0.1)  # Higher temperature for more creative output
        
        # Increase max tokens for longer generation
        new_max_tokens = min(4000, current_max_tokens + 500)
        
        return {
            "temperature": new_temp,
            "max_tokens": new_max_tokens,
            "reason": "Adjusting generation parameters"
        }
    
    def _generate_clarification_params(self, failure: Failure, root_cause: Dict[str, Any]) -> Dict[str, Any]:
        """Generate parameters for request_clarification strategy"""
        contributing_factors = root_cause.get("contributing_factors", [])
        
        clarification_questions = []
        for factor in contributing_factors:
            if "ambiguous" in factor.lower() or "missing" in factor.lower():
                clarification_questions.append({
                    "question": f"Can you provide more details about: {factor}?",
                    "context": factor
                })
        
        return {
            "clarification_questions": clarification_questions,
            "reason": "Requesting clarification to resolve ambiguity"
        }
