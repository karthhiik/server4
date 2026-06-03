"""
Failure Detector - Detects failures in generation process
Identifies when regeneration is needed
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Failure:
    """Represents a detected failure"""
    failure_type: str  # "low_confidence", "validation_error", "generation_error", "timeout"
    severity: str  # "critical", "high", "medium", "low"
    message: str
    context: Dict[str, Any]
    timestamp: datetime
    retry_count: int = 0


class FailureDetector:
    """
    Detects failures in the generation process
    Determines when auto-regeneration is needed
    """
    
    def __init__(self):
        self.confidence_threshold = 0.8
        self.max_retries = 3
        self.failure_history: List[Failure] = []
    
    def detect_failure(
        self,
        generation_result: Dict[str, Any],
        validation_result: Optional[Dict[str, Any]] = None
    ) -> Optional[Failure]:
        """
        Detect if a failure occurred during generation
        
        Args:
            generation_result: Result from generation process
            validation_result: Optional validation result
            
        Returns:
            Failure object if failure detected, None otherwise
        """
        # Check for generation errors
        generation_failure = self._check_generation_error(generation_result)
        if generation_failure:
            return generation_failure
        
        # Check for low confidence
        confidence_failure = self._check_confidence(generation_result)
        if confidence_failure:
            return confidence_failure
        
        # Check for validation errors
        if validation_result:
            validation_failure = self._check_validation_error(validation_result)
            if validation_failure:
                return validation_failure
        
        # No failure detected
        return None
    
    def _check_generation_error(self, generation_result: Dict[str, Any]) -> Optional[Failure]:
        """Check for generation errors"""
        error = generation_result.get("error")
        if error:
            return Failure(
                failure_type="generation_error",
                severity="critical",
                message=f"Generation error: {error}",
                context={"error": error},
                timestamp=datetime.utcnow()
            )
        
        # Check for empty or None results
        content = generation_result.get("content")
        if not content or (isinstance(content, str) and len(content.strip()) == 0):
            return Failure(
                failure_type="generation_error",
                severity="critical",
                message="Empty generation result",
                context=generation_result,
                timestamp=datetime.utcnow()
            )
        
        return None
    
    def _check_confidence(self, generation_result: Dict[str, Any]) -> Optional[Failure]:
        """Check for low confidence scores"""
        confidence = generation_result.get("confidence", 1.0)
        
        if confidence < self.confidence_threshold:
            severity = "critical" if confidence < 0.5 else "high"
            
            return Failure(
                failure_type="low_confidence",
                severity=severity,
                message=f"Low confidence score: {confidence:.2f}",
                context={"confidence": confidence},
                timestamp=datetime.utcnow()
            )
        
        return None
    
    def _check_validation_error(self, validation_result: Dict[str, Any]) -> Optional[Failure]:
        """Check for validation errors"""
        valid = validation_result.get("valid", True)
        
        if not valid:
            return Failure(
                failure_type="validation_error",
                severity="high",
                message="Validation failed",
                context=validation_result,
                timestamp=datetime.utcnow()
            )
        
        # Check for flagged facts
        flagged_facts = validation_result.get("flagged_facts", [])
        if len(flagged_facts) > 0:
            return Failure(
                failure_type="validation_error",
                severity="medium",
                message=f"{len(flagged_facts)} facts flagged for review",
                context={"flagged_facts": len(flagged_facts)},
                timestamp=datetime.utcnow()
            )
        
        return None
    
    def should_regenerate(self, failure: Failure) -> bool:
        """
        Determine if regeneration should be attempted
        
        Args:
            failure: Detected failure
            
        Returns:
            True if regeneration should be attempted
        """
        # Check retry count
        if failure.retry_count >= self.max_retries:
            return False
        
        # Critical failures always trigger regeneration
        if failure.severity == "critical":
            return True
        
        # High severity failures trigger regeneration
        if failure.severity == "high":
            return True
        
        # Medium severity failures trigger regeneration if confidence is very low
        if failure.severity == "medium":
            confidence = failure.context.get("confidence", 1.0)
            if confidence < 0.6:
                return True
        
        # Low severity failures do not trigger regeneration
        return False
    
    def record_failure(self, failure: Failure):
        """Record a failure in history"""
        self.failure_history.append(failure)
    
    def get_failure_stats(self) -> Dict[str, Any]:
        """Get statistics about failures"""
        if not self.failure_history:
            return {
                "total_failures": 0,
                "by_type": {},
                "by_severity": {}
            }
        
        by_type = {}
        by_severity = {}
        
        for failure in self.failure_history:
            by_type[failure.failure_type] = by_type.get(failure.failure_type, 0) + 1
            by_severity[failure.severity] = by_severity.get(failure.severity, 0) + 1
        
        return {
            "total_failures": len(self.failure_history),
            "by_type": by_type,
            "by_severity": by_severity
        }
