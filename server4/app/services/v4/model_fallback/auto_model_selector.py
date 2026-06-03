"""
Auto Model Selector - Automatically selects best model for a task
Considers model health, capabilities, and task requirements
"""

from typing import Dict, Any, List, Optional
from app.services.v4.model_fallback.model_health_monitor import ModelHealthMonitor
from app.services.v4.zero_defect.council.council_config import ZeroDefectCouncilConfig


class AutoModelSelector:
    """
    Automatically selects the best model for a task
    Considers health, capabilities, and task requirements
    """
    
    def __init__(self):
        self.health_monitor = ModelHealthMonitor()
        self.config = ZeroDefectCouncilConfig()
    
    def select(
        self,
        task: str,
        task_type: str,
        available_models: Optional[List[str]] = None,
        mode: str = "standard"
    ) -> str:
        """
        Select the best model for a task
        
        Args:
            task: Task description
            task_type: Type of task (content_generation, layout_intent, etc.)
            available_models: Optional list of available models
            mode: "standard" or "premium"
            
        Returns:
            Selected model name
        """
        # Get available models
        if available_models is None:
            if mode == "premium":
                available_models = self.config.get_premium_council()
            else:
                available_models = self.config.get_primary_council()
        
        # Filter healthy models
        healthy_models = self.health_monitor.get_healthy_models(available_models)
        
        if not healthy_models:
            # No healthy models, use all models
            healthy_models = available_models
        
        # Score models based on task
        scored_models = []
        for model in healthy_models:
            score = self._score_model(model, task, task_type)
            scored_models.append((model, score))
        
        # Sort by score
        scored_models.sort(key=lambda x: x[1], reverse=True)
        
        # Return best model
        return scored_models[0][0] if scored_models else available_models[0]
    
    def _score_model(self, model: str, task: str, task_type: str) -> float:
        """
        Score a model for a task
        
        Args:
            model: Model name
            task: Task description
            task_type: Type of task
            
        Returns:
            Score (0.0-1.0)
        """
        score = 0.0
        
        # Health score (40%)
        health_status = self.health_monitor.get_health_status(model)
        if health_status["healthy"]:
            score += 0.4
        else:
            score += 0.4 * health_status["success_rate"]
        
        # Capability score (40%)
        capabilities = self.config.get_model_capabilities(model)
        capability_score = self._calculate_capability_score(capabilities, task_type)
        score += 0.4 * capability_score
        
        # Task-specific score (20%)
        task_score = self._calculate_task_score(model, task, task_type)
        score += 0.2 * task_score
        
        return score
    
    def _calculate_capability_score(self, capabilities: Dict[str, Any], task_type: str) -> float:
        """
        Calculate capability score based on model capabilities and task type
        
        Args:
            capabilities: Model capabilities
            task_type: Type of task
            
        Returns:
            Capability score (0.0-1.0)
        """
        if not capabilities:
            return 0.5  # Neutral score if no capabilities data
        
        strengths = capabilities.get("strengths", [])
        task_requirements = self._get_task_requirements(task_type)
        
        # Calculate match score
        match_count = sum(1 for req in task_requirements if req in strengths)
        match_score = match_count / len(task_requirements) if task_requirements else 0.5
        
        return match_score
    
    def _get_task_requirements(self, task_type: str) -> List[str]:
        """
        Get required capabilities for a task type
        
        Args:
            task_type: Type of task
            
        Returns:
            List of required capabilities
        """
        requirements = {
            "content_generation": ["reasoning", "storytelling"],
            "layout_intent": ["reasoning", "creative"],
            "typography_styling": ["creative"],
            "image_generation": ["creative", "reasoning"],
            "data_visualization": ["technical", "precision"],
            "slide_assembly": ["reasoning", "synthesis"]
        }
        
        return requirements.get(task_type, ["reasoning"])
    
    def _calculate_task_score(self, model: str, task: str, task_type: str) -> float:
        """
        Calculate task-specific score
        
        Args:
            model: Model name
            task: Task description
            task_type: Type of task
            
        Returns:
            Task score (0.0-1.0)
        """
        # Simple heuristic based on model tier
        capabilities = self.config.get_model_capabilities(model)
        tier = capabilities.get("tier", "T5")
        
        tier_scores = {
            "T0": 1.0,    # Best
            "T0+": 0.95,
            "T0.5": 0.9,
            "T1": 0.85,
            "T2": 0.8,
            "T2.5": 0.75,
            "T3": 0.7,
            "T4": 0.65,
            "T5": 0.6,    # Fallback
            "T6": 0.55    # Local
        }
        
        return tier_scores.get(tier, 0.5)
