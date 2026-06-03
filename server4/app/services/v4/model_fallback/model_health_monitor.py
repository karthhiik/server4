"""
Model Health Monitor - Monitors health of LLM models
Tracks success rates, response times, and error rates
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict


class ModelHealthMonitor:
    """
    Monitors health of LLM models
    Tracks metrics to determine if a model is healthy
    """
    
    def __init__(self):
        self.model_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "success_count": 0,
            "error_count": 0,
            "total_requests": 0,
            "response_times": [],
            "last_success": None,
            "last_failure": None,
            "consecutive_failures": 0,
            "error_types": defaultdict(int)
        })
        
        self.health_threshold = 0.95  # 95% success rate threshold
        self.max_consecutive_failures = 5
        self.response_time_threshold = 30.0  # 30 seconds
    
    def record_success(self, model: str, response_time: float):
        """
        Record a successful generation
        
        Args:
            model: Model name
            response_time: Response time in seconds
        """
        metrics = self.model_metrics[model]
        metrics["success_count"] += 1
        metrics["total_requests"] += 1
        metrics["response_times"].append(response_time)
        metrics["last_success"] = datetime.utcnow()
        metrics["consecutive_failures"] = 0
        
        # Keep only last 100 response times
        if len(metrics["response_times"]) > 100:
            metrics["response_times"] = metrics["response_times"][-100:]
    
    def record_failure(self, model: str, error_type: str = "unknown"):
        """
        Record a failed generation
        
        Args:
            model: Model name
            error_type: Type of error
        """
        metrics = self.model_metrics[model]
        metrics["error_count"] += 1
        metrics["total_requests"] += 1
        metrics["last_failure"] = datetime.utcnow()
        metrics["consecutive_failures"] += 1
        metrics["error_types"][error_type] += 1
    
    def is_healthy(self, model: str) -> bool:
        """
        Check if a model is healthy
        
        Args:
            model: Model name
            
        Returns:
            True if model is healthy
        """
        metrics = self.model_metrics[model]
        
        # No data yet - assume healthy
        if metrics["total_requests"] == 0:
            return True
        
        # Check consecutive failures
        if metrics["consecutive_failures"] >= self.max_consecutive_failures:
            return False
        
        # Check success rate
        if metrics["total_requests"] >= 10:  # Only check after sufficient data
            success_rate = metrics["success_count"] / metrics["total_requests"]
            if success_rate < self.health_threshold:
                return False
        
        # Check average response time
        if metrics["response_times"]:
            avg_response_time = sum(metrics["response_times"]) / len(metrics["response_times"])
            if avg_response_time > self.response_time_threshold:
                return False
        
        return True
    
    def get_health_status(self, model: str) -> Dict[str, Any]:
        """
        Get detailed health status for a model
        
        Args:
            model: Model name
            
        Returns:
            Dictionary with health status
        """
        metrics = self.model_metrics[model]
        
        success_rate = 0.0
        if metrics["total_requests"] > 0:
            success_rate = metrics["success_count"] / metrics["total_requests"]
        
        avg_response_time = 0.0
        if metrics["response_times"]:
            avg_response_time = sum(metrics["response_times"]) / len(metrics["response_times"])
        
        return {
            "model": model,
            "healthy": self.is_healthy(model),
            "success_rate": success_rate,
            "error_rate": 1.0 - success_rate,
            "total_requests": metrics["total_requests"],
            "success_count": metrics["success_count"],
            "error_count": metrics["error_count"],
            "consecutive_failures": metrics["consecutive_failures"],
            "avg_response_time": avg_response_time,
            "last_success": metrics["last_success"],
            "last_failure": metrics["last_failure"],
            "error_types": dict(metrics["error_types"])
        }
    
    def get_all_health_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health status for all models
        
        Returns:
            Dictionary mapping model names to health status
        """
        return {
            model: self.get_health_status(model)
            for model in self.model_metrics.keys()
        }
    
    def get_healthy_models(self, available_models: List[str]) -> List[str]:
        """
        Get list of healthy models from available models
        
        Args:
            available_models: List of available model names
            
        Returns:
            List of healthy model names
        """
        return [model for model in available_models if self.is_healthy(model)]
    
    def reset_metrics(self, model: str):
        """
        Reset metrics for a model
        
        Args:
            model: Model name
        """
        self.model_metrics[model] = {
            "success_count": 0,
            "error_count": 0,
            "total_requests": 0,
            "response_times": [],
            "last_success": None,
            "last_failure": None,
            "consecutive_failures": 0,
            "error_types": defaultdict(int)
        }
    
    def cleanup_old_metrics(self, days: int = 7):
        """
        Clean up old metrics (not implemented in this version)
        In production, would use Redis/DB with TTL
        """
        pass
