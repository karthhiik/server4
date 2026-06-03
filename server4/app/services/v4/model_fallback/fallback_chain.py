"""
Fallback Chain - Implements automatic fallback chain for failed models
Automatically switches to next model in chain when a model fails
"""

from typing import Dict, Any, List, Optional
from app.services.v4.model_fallback.model_health_monitor import ModelHealthMonitor
from app.services.v4.zero_defect.council.council_config import ZeroDefectCouncilConfig


class FallbackChain:
    """
    Implements automatic fallback chain
    Switches to next model in chain when current model fails
    """
    
    def __init__(self):
        self.health_monitor = ModelHealthMonitor()
        self.config = ZeroDefectCouncilConfig()
        self.current_model_index: Dict[str, int] = {}
    
    async def execute_with_fallback(
        self,
        task: str,
        task_type: str,
        context: Dict[str, Any],
        initial_model: Optional[str] = None,
        mode: str = "standard"
    ) -> Dict[str, Any]:
        """
        Execute task with automatic fallback
        
        Args:
            task: Task description
            task_type: Type of task
            context: Task context
            initial_model: Optional initial model to use
            mode: "standard" or "premium"
            
        Returns:
            Dictionary with execution result
        """
        # Get fallback chain
        if initial_model:
            fallback_chain = self.config.get_fallback_chain(initial_model)
            fallback_chain = [initial_model] + fallback_chain
        else:
            if mode == "premium":
                fallback_chain = self.config.get_premium_council()
            else:
                fallback_chain = self.config.get_primary_council()
        
        # Try each model in chain
        for model in fallback_chain:
            # Check if model is healthy
            if not self.health_monitor.is_healthy(model):
                continue
            
            # Try to execute with this model
            result = await self._execute_with_model(model, task, task_type, context)
            
            if result["success"]:
                # Record success
                self.health_monitor.record_success(model, result.get("response_time", 0))
                
                return {
                    "success": True,
                    "model": model,
                    "result": result["result"],
                    "fallback_used": model != fallback_chain[0]
                }
            else:
                # Record failure
                self.health_monitor.record_failure(model, result.get("error_type", "unknown"))
        
        # All models failed
        return {
            "success": False,
            "error": "All models in fallback chain failed",
            "models_attempted": fallback_chain
        }
    
    async def _execute_with_model(
        self,
        model: str,
        task: str,
        task_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute task with a specific model
        
        Args:
            model: Model name
            task: Task description
            task_type: Type of task
            context: Task context
            
        Returns:
            Dictionary with execution result
        """
        import time
        from app.services.llm.model_router import ModelRouter
        
        model_router = ModelRouter()
        
        try:
            start_time = time.time()
            
            # Generate system prompt based on task type
            system_prompt = self._get_system_prompt(task_type)
            
            # Generate user prompt
            user_prompt = self._get_user_prompt(task, context)
            
            # Execute with model
            from app.services.llm.model_router import TaskType
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await model_router.complete(
                task_type=TaskType.TEMPLATE_FILL,
                messages=messages,
                max_tokens=1500,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            response_time = time.time() - start_time
            
            return {
                "success": True,
                "result": response,
                "response_time": response_time
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def _get_system_prompt(self, task_type: str) -> str:
        """Get system prompt based on task type"""
        prompts = {
            "content_generation": "You are a content generation expert. Generate high-quality slide content.",
            "layout_intent": "You are a layout design expert. Determine optimal layout for slide content.",
            "typography_styling": "You are a typography and styling expert. Select appropriate fonts and styles.",
            "image_generation": "You are an image generation expert. Create detailed image prompts.",
            "data_visualization": "You are a data visualization expert. Determine best way to present data.",
            "slide_assembly": "You are a slide assembly expert. Combine all elements into a cohesive slide."
        }
        
        return prompts.get(task_type, "You are a helpful assistant.")
    
    def _get_user_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Get user prompt with task and context"""
        prompt = f"Task: {task}\n\n"
        
        for key, value in context.items():
            prompt += f"{key}: {value}\n"
        
        return prompt
    
    def get_fallback_chain(self, model: str) -> List[str]:
        """
        Get fallback chain for a model
        
        Args:
            model: Model name
            
        Returns:
            List of models in fallback chain
        """
        chain = self.config.get_fallback_chain(model)
        return [model] + chain
    
    def get_current_model(self, session_id: str) -> Optional[str]:
        """
        Get current model for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Current model or None
        """
        return self.current_model_index.get(session_id)
    
    def set_current_model(self, session_id: str, model: str):
        """
        Set current model for a session
        
        Args:
            session_id: Session identifier
            model: Model name
        """
        self.current_model_index[session_id] = model
