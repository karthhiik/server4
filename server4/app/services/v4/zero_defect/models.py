"""
Data models for Zero-Defect Foundation
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class Fact:
    """Represents a factual claim extracted from user input"""
    claim: str
    confidence: float = 0.0
    verified: bool = False
    sources: List[str] = field(default_factory=list)
    flagged: bool = False
    context: str = ""
    extraction_timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Ambiguity:
    """Represents an ambiguous statement detected in input"""
    statement: str
    ambiguity_type: str  # "vague", "contradictory", "missing_context", "unclear_reference"
    clarification_question: str = ""
    suggested_clarification: str = ""
    confidence: float = 0.0


@dataclass
class ValidationResult:
    """Result of input validation"""
    valid: bool
    facts: List[Fact] = field(default_factory=list)
    ambiguities: List[Ambiguity] = field(default_factory=list)
    clarification_needed: bool = False
    overall_confidence: float = 0.0
    validation_timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_low_confidence_facts(self, threshold: float = 0.8) -> List[Fact]:
        """Get facts with confidence below threshold"""
        return [f for f in self.facts if f.confidence < threshold]
    
    def get_flagged_facts(self) -> List[Fact]:
        """Get facts that are flagged for review"""
        return [f for f in self.facts if f.flagged]
    
    def get_unverified_facts(self) -> List[Fact]:
        """Get facts that are not verified"""
        return [f for f in self.facts if not f.verified]
