"""
Confidence Scorer - Calculates confidence scores for council outputs
Implements multi-factor confidence scoring
"""

from typing import List, Dict, Any
from app.services.v4.zero_defect.council.council_config import ZeroDefectCouncilConfig


class ConfidenceScorer:
    """
    Calculates confidence scores for council outputs
    Considers multiple factors: verification, agreement, consistency, language quality
    """
    
    def __init__(self):
        self.config = ZeroDefectCouncilConfig()
    
    def calculate_final_confidence(
        self,
        stage3_results: Dict[str, Any],
        stage2_results: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate final confidence score for synthesized output
        
        Args:
            stage3_results: Results from Stage 3 (Synthesis)
            stage2_results: Results from Stage 2 (Cross-Verification)
            
        Returns:
            Final confidence score (0.0-1.0)
        """
        confidence = 0.0
        
        # Source verification (40% weight)
        source_confidence = self._calculate_source_confidence(stage2_results)
        confidence += 0.4 * source_confidence
        
        # Cross-model agreement (30% weight)
        agreement_confidence = self._calculate_agreement_confidence(stage2_results)
        confidence += 0.3 * agreement_confidence
        
        # Internal consistency (20% weight)
        consistency_confidence = self._calculate_consistency_confidence(stage3_results)
        confidence += 0.2 * consistency_confidence
        
        # Language quality (10% weight)
        language_confidence = self._calculate_language_confidence(stage3_results)
        confidence += 0.1 * language_confidence
        
        return max(0.0, min(1.0, confidence))
    
    def _calculate_source_confidence(self, stage2_results: List[Dict[str, Any]]) -> float:
        """Calculate confidence based on source verification"""
        if not stage2_results:
            return 0.0
        
        # Average verification confidence from Stage 2
        verification_scores = [r["confidence"] for r in stage2_results]
        return sum(verification_scores) / len(verification_scores)
    
    def _calculate_agreement_confidence(self, stage2_results: List[Dict[str, Any]]) -> float:
        """Calculate confidence based on cross-model agreement"""
        if not stage2_results or len(stage2_results) < 2:
            return 0.5  # Neutral if insufficient data
        
        # Calculate variance in verification scores
        verification_scores = [r["confidence"] for r in stage2_results]
        
        if len(verification_scores) == 1:
            return verification_scores[0]
        
        # Low variance = high agreement
        variance = sum((x - sum(verification_scores)/len(verification_scores))**2 for x in verification_scores) / len(verification_scores)
        
        # Convert variance to confidence (inverse relationship)
        agreement = 1.0 / (1.0 + variance * 10)
        
        return agreement
    
    def _calculate_consistency_confidence(self, stage3_results: Dict[str, Any]) -> float:
        """Calculate confidence based on internal consistency"""
        content = stage3_results.get("content", "")
        
        if not content:
            return 0.0
        
        # Simple consistency checks
        consistency_score = 1.0
        
        # Check for contradictions (simplified)
        contradiction_indicators = ["but", "however", "although", "despite"]
        contradiction_count = sum(1 for indicator in contradiction_indicators if indicator in content.lower())
        
        # Too many contradictions might indicate inconsistency
        if contradiction_count > 3:
            consistency_score -= 0.2
        
        # Check for incomplete sentences
        if not content.strip().endswith(('.', '!', '?')):
            consistency_score -= 0.1
        
        return max(0.0, consistency_score)
    
    def _calculate_language_confidence(self, stage3_results: Dict[str, Any]) -> float:
        """Calculate confidence based on language quality"""
        content = stage3_results.get("content", "")
        
        if not content:
            return 0.0
        
        # Simple language quality checks
        quality_score = 1.0
        
        # Check for common errors
        if "  " in content:  # Double spaces
            quality_score -= 0.1
        
        if content.lower().startswith(("and", "or", "but")):  # Starts with conjunction
            quality_score -= 0.1
        
        # Check for reasonable length
        if len(content) < 50:  # Too short
            quality_score -= 0.3
        
        if len(content) > 5000:  # Too long
            quality_score -= 0.2
        
        return max(0.0, quality_score)
    
    def calculate_claim_confidence(
        self,
        claim: str,
        sources: List[str],
        verification_results: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate confidence for a specific claim
        
        Args:
            claim: The claim to evaluate
            sources: Sources that support the claim
            verification_results: Verification results from models
            
        Returns:
            Confidence score (0.0-1.0)
        """
        confidence = 0.0
        
        # Source availability (30%)
        if sources:
            confidence += 0.3
        else:
            confidence += 0.0
        
        # Verification results (50%)
        if verification_results:
            avg_verification = sum(r["confidence"] for r in verification_results) / len(verification_results)
            confidence += 0.5 * avg_verification
        else:
            confidence += 0.0
        
        # Claim specificity (20%)
        specificity = self._calculate_claim_specificity(claim)
        confidence += 0.2 * specificity
        
        return max(0.0, min(1.0, confidence))
    
    def _calculate_claim_specificity(self, claim: str) -> float:
        """
        Calculate specificity of a claim
        More specific claims get higher confidence
        """
        specificity = 0.5  # Base score
        
        # Contains numbers
        if any(char.isdigit() for char in claim):
            specificity += 0.2
        
        # Contains dates
        if any(word in claim.lower() for word in ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]):
            specificity += 0.1
        
        # Contains company names (simplified check)
        if claim[0].isupper() and " " in claim:
            specificity += 0.1
        
        # Length
        if len(claim) > 50:
            specificity += 0.1
        
        return min(1.0, specificity)
