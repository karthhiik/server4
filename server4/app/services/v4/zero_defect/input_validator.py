"""
Input Validator - Main validation orchestrator
Ties together fact extraction, verification, ambiguity detection, and clarification
"""

from typing import Optional
import uuid
from app.services.v4.zero_defect.models import ValidationResult, Fact, Ambiguity
from app.services.v4.zero_defect.fact_extractor import FactExtractor
from app.services.v4.zero_defect.fact_verifier import FactVerifier
from app.services.v4.zero_defect.ambiguity_detector import AmbiguityDetector
from app.services.v4.zero_defect.clarification_system import ClarificationSystem


class InputValidator:
    """
    Main validation orchestrator
    Ensures input is valid, verifiable, and unambiguous
    """
    
    def __init__(self):
        self.fact_extractor = FactExtractor()
        self.fact_verifier = FactVerifier()
        self.ambiguity_detector = AmbiguityDetector()
        self.clarification_system = ClarificationSystem()
    
    async def validate(
        self,
        user_input: str,
        session_id: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate user input through the zero-defect pipeline
        
        Args:
            user_input: Raw user input text
            session_id: Optional session identifier for clarification tracking
            
        Returns:
            ValidationResult with all validation results
        """
        # Generate session ID if not provided
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        # Step 1: Extract facts
        facts = await self.fact_extractor.extract(user_input)
        
        # Step 2: Verify facts
        verified_facts = await self.fact_verifier.verify_batch(facts)
        
        # Step 3: Detect ambiguities
        ambiguities = await self.ambiguity_detector.detect(user_input)
        
        # Step 4: Check if clarification needed
        clarification_needed = len(ambiguities) > 0
        
        # Step 5: Request clarification if needed
        if clarification_needed:
            await self.clarification_system.request_clarification(
                session_id,
                ambiguities
            )
        
        # Step 6: Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(verified_facts, ambiguities)
        
        # Step 7: Determine if input is valid
        valid = self._determine_validity(verified_facts, ambiguities, overall_confidence)
        
        # Create validation result
        result = ValidationResult(
            valid=valid,
            facts=verified_facts,
            ambiguities=ambiguities,
            clarification_needed=clarification_needed,
            overall_confidence=overall_confidence,
            metadata={
                "session_id": session_id,
                "input_length": len(user_input),
                "facts_extracted": len(facts),
                "facts_verified": len([f for f in verified_facts if f.verified]),
                "ambiguities_detected": len(ambiguities)
            }
        )
        
        return result
    
    async def validate_with_clarification(
        self,
        user_input: str,
        session_id: str,
        clarifications: dict
    ) -> ValidationResult:
        """
        Validate input with user-provided clarifications
        
        Args:
            user_input: Raw user input text
            session_id: Session identifier
            clarifications: Dictionary of clarifications from user
            
        Returns:
            ValidationResult with clarifications applied
        """
        # Receive clarifications
        await self.clarification_system.receive_clarification(session_id, clarifications)
        
        # Apply clarifications to input
        clarified_input = self._apply_clarifications(user_input, clarifications)
        
        # Re-validate with clarified input
        result = await self.validate(clarified_input, session_id)
        
        return result
    
    def _calculate_overall_confidence(
        self,
        facts: list[Fact],
        ambiguities: list[Ambiguity]
    ) -> float:
        """
        Calculate overall confidence score for validation
        
        Args:
            facts: List of verified facts
            ambiguities: List of detected ambiguities
            
        Returns:
            Overall confidence score (0.0-1.0)
        """
        if not facts and not ambiguities:
            return 1.0  # No issues, perfect confidence
        
        # Calculate fact confidence
        fact_confidence = 0.0
        if facts:
            fact_confidence = sum(f.confidence for f in facts) / len(facts)
        
        # Calculate ambiguity penalty
        ambiguity_penalty = 0.0
        if ambiguities:
            ambiguity_penalty = sum(a.confidence for a in ambiguities) / len(ambiguities) * 0.5
        
        # Combine
        overall = fact_confidence - ambiguity_penalty
        overall = max(0.0, min(1.0, overall))  # Clamp to [0, 1]
        
        return overall
    
    def _determine_validity(
        self,
        facts: list[Fact],
        ambiguities: list[Ambiguity],
        overall_confidence: float
    ) -> bool:
        """
        Determine if input is valid based on validation results
        
        Args:
            facts: List of verified facts
            ambiguities: List of detected ambiguities
            overall_confidence: Overall confidence score
            
        Returns:
            True if input is valid, False otherwise
        """
        # Must have overall confidence >= 0.8
        if overall_confidence < 0.8:
            return False
        
        # No critical ambiguities
        critical_ambiguities = [a for a in ambiguities if a.ambiguity_type in ["contradictory", "missing_context"]]
        if critical_ambiguities:
            return False
        
        # Most facts should be verified
        if facts:
            verified_count = len([f for f in facts if f.verified])
            if verified_count / len(facts) < 0.7:
                return False
        
        return True
    
    def _apply_clarifications(self, user_input: str, clarifications: dict) -> str:
        """
        Apply user clarifications to input
        
        Args:
            user_input: Original user input
            clarifications: Dictionary of clarifications
            
        Returns:
            Clarified input string
        """
        clarified_input = user_input
        
        for statement, clarification in clarifications.items():
            clarified_input = clarified_input.replace(statement, clarification)
        
        return clarified_input
    
    def get_clarification_status(self, session_id: str) -> dict:
        """
        Get clarification status for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with clarification status
        """
        pending = self.clarification_system.has_pending_clarifications(session_id)
        responses = self.clarification_system.get_clarification_responses(session_id)
        
        return {
            "session_id": session_id,
            "has_pending": pending,
            "has_responses": responses is not None,
            "pending_count": len(self.clarification_system.get_pending_clarifications(session_id) or []),
            "response_count": len(responses or {})
        }
