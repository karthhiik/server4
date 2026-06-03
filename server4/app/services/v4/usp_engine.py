"""
USP Engine — Unique Selling Proposition extraction, verification, and moat scoring.

This module identifies and validates the company's unique value proposition:
1. Extract USP from company description, problem statement, and solution
2. Verify USP against competitor claims (from research)
3. Score moat depth across multiple dimensions (technical, network, data, switching cost)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class MoatType(Enum):
    """Types of competitive moats."""
    TECHNICAL = "technical"  # Proprietary tech, patents, IP
    NETWORK = "network"  # Network effects, user base
    DATA = "data"  # Data advantage, unique datasets
    SWITCHING_COST = "switching_cost"  # High switching costs, lock-in
    BRAND = "brand"  # Brand recognition, trust
    OPERATIONAL = "operational"  # Operational excellence, supply chain


@dataclass
class USP:
    """Extracted unique selling proposition."""
    primary_statement: str  # Main value prop (1-2 sentences)
    differentiators: list[str] = field(default_factory=list)  # Key differentiators
    target_pain: Optional[str] = None  # Specific pain point addressed
    unique_mechanism: Optional[str] = None  # How it's uniquely solved
    evidence_sources: list[str] = field(default_factory=list)  # Research citations


@dataclass
class MoatScore:
    """Score for a specific moat type."""
    moat_type: MoatType
    score: float  # 0-10 scale
    rationale: str  # Explanation of the score
    evidence: list[str] = field(default_factory=list)  # Supporting evidence


@dataclass
class USPAnalysis:
    """Complete USP analysis with verification and moat scoring."""
    usp: USP
    verification_passed: bool  # Whether USP is supported by research
    verification_notes: list[str] = field(default_factory=list)
    moat_scores: list[MoatScore] = field(default_factory=list)
    overall_moat_strength: float = 0.0  # 0-10 average
    recommendations: list[str] = field(default_factory=list)


class USPEngine:
    """Extracts, verifies, and scores USP and competitive moats."""

    def __init__(self) -> None:
        """Initialize the USP engine."""
        self._usp_patterns = self._build_usp_patterns()
        self._moat_keywords = self._build_moat_keywords()

    def _build_usp_patterns(self) -> dict[str, re.Pattern]:
        """Build regex patterns for USP extraction."""
        return {
            "differentiation": re.compile(
                r'(?:unlike|different from|vs|compared to|unlike traditional|unlike existing)',
                re.IGNORECASE,
            ),
            "uniqueness": re.compile(
                r'(?:first|only|unique|proprietary|patented|exclusive|breakthrough)',
                re.IGNORECASE,
            ),
            "advantage": re.compile(
                r'(?:faster|cheaper|better|easier|more efficient|more accurate|more reliable)',
                re.IGNORECASE,
            ),
            "mechanism": re.compile(
                r'(?:using|by|through|via|leveraging|powered by|built on)',
                re.IGNORECASE,
            ),
        }

    def _build_moat_keywords(self) -> dict[MoatType, list[str]]:
        """Build keyword lists for moat detection."""
        return {
            MoatType.TECHNICAL: [
                "patent", "proprietary", "ip", "technology", "algorithm", "invention",
                "technical", "engineering", "r&d", "innovation", "breakthrough",
            ],
            MoatType.NETWORK: [
                "network effect", "user base", "community", "marketplace", "platform",
                "ecosystem", "network", "users", "customers", "connections",
            ],
            MoatType.DATA: [
                "data", "dataset", "machine learning", "ai", "analytics", "insights",
                "training data", "database", "intelligence", "prediction",
            ],
            MoatType.SWITCHING_COST: [
                "integration", "embedded", "workflow", "lock-in", "migration",
                "switching cost", "sticky", "retention", "churn", "adoption",
            ],
            MoatType.BRAND: [
                "brand", "reputation", "trust", "recognition", "loyalty", "premium",
                "trusted", "established", "leader", "market leader",
            ],
            MoatType.OPERATIONAL: [
                "operations", "supply chain", "logistics", "distribution", "scale",
                "efficiency", "cost advantage", "margin", "profitability",
            ],
        }

    async def analyze_usp(
        self,
        company_description: str,
        problem_statement: str,
        solution_description: str,
        research_context: dict[str, Any],
        company_name: str = "",
    ) -> USPAnalysis:
        """Perform complete USP analysis.

        Args:
            company_description: Company overview
            problem_statement: Problem being solved
            solution_description: How the problem is solved
            research_context: Research data with citations
            company_name: Company name for verification

        Returns:
            USPAnalysis with extraction, verification, and moat scoring
        """
        # Extract USP
        usp = self._extract_usp(
            company_description,
            problem_statement,
            solution_description,
        )

        # Verify against research
        verification_passed, verification_notes = self._verify_usp(
            usp,
            research_context,
            company_name,
        )

        # Score moats
        moat_scores = self._score_moats(
            usp,
            research_context,
            company_description,
        )

        # Calculate overall moat strength
        overall_moat_strength = sum(m.score for m in moat_scores) / len(moat_scores) if moat_scores else 0.0

        # Generate recommendations
        recommendations = self._generate_recommendations(usp, verification_passed, moat_scores)

        return USPAnalysis(
            usp=usp,
            verification_passed=verification_passed,
            verification_notes=verification_notes,
            moat_scores=moat_scores,
            overall_moat_strength=overall_moat_strength,
            recommendations=recommendations,
        )

    def _extract_usp(
        self,
        company_description: str,
        problem_statement: str,
        solution_description: str,
    ) -> USP:
        """Extract USP from company materials."""
        combined_text = f"{company_description} {problem_statement} {solution_description}"

        # Extract primary statement (first meaningful sentence with differentiation)
        primary_statement = self._extract_primary_statement(combined_text)

        # Extract differentiators
        differentiators = self._extract_differentiators(combined_text)

        # Extract target pain
        target_pain = self._extract_target_pain(problem_statement)

        # Extract unique mechanism
        unique_mechanism = self._extract_unique_mechanism(solution_description)

        return USP(
            primary_statement=primary_statement,
            differentiators=differentiators,
            target_pain=target_pain,
            unique_mechanism=unique_mechanism,
            evidence_sources=[],
        )

    def _extract_primary_statement(self, text: str) -> str:
        """Extract the primary USP statement."""
        sentences = re.split(r'[.!?]+', text)
        
        # Look for sentences with differentiation keywords
        for sentence in sentences:
            if any(
                pattern.search(sentence)
                for pattern in self._usp_patterns.values()
            ):
                return sentence.strip()
        
        # Fallback: first meaningful sentence
        for sentence in sentences:
            if len(sentence.strip()) > 20:
                return sentence.strip()
        
        return "Unique value proposition not clearly stated"

    def _extract_differentiators(self, text: str) -> list[str]:
        """Extract key differentiators from text."""
        differentiators = []
        
        # Look for phrases following "unlike", "vs", "different from"
        diff_pattern = re.compile(
            r'(?:unlike|vs|different from|compared to)\s+([^,.]+)[,.]?',
            re.IGNORECASE,
        )
        matches = diff_pattern.findall(text)
        differentiators.extend(matches)
        
        # Look for uniqueness claims
        unique_pattern = re.compile(
            r'(?:the\s+(?:first|only|unique)\s+(?:[^,.]+))',
            re.IGNORECASE,
        )
        matches = unique_pattern.findall(text)
        differentiators.extend(matches)
        
        return list(set(d[:100] for d in differentiators))  # Deduplicate and truncate

    def _extract_target_pain(self, problem_statement: str) -> Optional[str]:
        """Extract the specific pain point being addressed."""
        if not problem_statement:
            return None
        
        # Extract first sentence as pain statement
        sentences = re.split(r'[.!?]+', problem_statement)
        if sentences:
            return sentences[0].strip()
        
        return None

    def _extract_unique_mechanism(self, solution_description: str) -> Optional[str]:
        """Extract the unique mechanism of the solution."""
        if not solution_description:
            return None
        
        # Look for mechanism phrases
        mechanism_pattern = re.compile(
            r'(?:using|by|through|via|leveraging)\s+([^,.]+)[,.]?',
            re.IGNORECASE,
        )
        match = mechanism_pattern.search(solution_description)
        if match:
            return match.group(1).strip()
        
        return None

    def _verify_usp(
        self,
        usp: USP,
        research_context: dict[str, Any],
        company_name: str,
    ) -> tuple[bool, list[str]]:
        """Verify USP against research evidence."""
        verification_notes = []
        citations = research_context.get("citations", [])
        research_text = " ".join([c.get("snippet", "") for c in citations])
        
        passed = True
        
        # Check if differentiators are supported by research
        for diff in usp.differentiators:
            diff_lower = diff.lower()
            if diff_lower in research_text.lower():
                verification_notes.append(f"Differentiator supported: '{diff}'")
            else:
                verification_notes.append(f"WARNING: Differentiator not found in research: '{diff}'")
                passed = False
        
        # Check if company is mentioned in research
        if company_name and company_name.lower() in research_text.lower():
            verification_notes.append("Company mentioned in research")
        else:
            verification_notes.append("WARNING: Company not prominently mentioned in research")
            passed = False
        
        # Check for competitor contradictions
        competitor_claims = self._check_competitor_contradictions(usp, research_text)
        if competitor_claims:
            verification_notes.extend(competitor_claims)
            passed = False
        
        return passed, verification_notes

    def _check_competitor_contradictions(self, usp: USP, research_text: str) -> list[str]:
        """Check if competitors already claim similar differentiators."""
        contradictions = []
        
        # Look for competitor claims
        for diff in usp.differentiators:
            # Simplified check: if differentiator appears with "competitor" or similar
            if re.search(rf'(?:competitor|existing|traditional).*{re.escape(diff)}', research_text, re.IGNORECASE):
                contradictions.append(f"WARNING: Competitor may already claim: '{diff}'")
        
        return contradictions

    def _score_moats(
        self,
        usp: USP,
        research_context: dict[str, Any],
        company_description: str,
    ) -> list[MoatScore]:
        """Score moat strength across all dimensions."""
        moat_scores = []
        
        combined_text = f"{company_description} {usp.primary_statement} {' '.join(usp.differentiators)}"
        
        for moat_type, keywords in self._moat_keywords.items():
            score, rationale, evidence = self._score_single_moat(
                moat_type,
                keywords,
                combined_text,
                research_context,
            )
            moat_scores.append(MoatScore(
                moat_type=moat_type,
                score=score,
                rationale=rationale,
                evidence=evidence,
            ))
        
        return moat_scores

    def _score_single_moat(
        self,
        moat_type: MoatType,
        keywords: list[str],
        text: str,
        research_context: dict[str, Any],
    ) -> tuple[float, str, list[str]]:
        """Score a single moat type."""
        text_lower = text.lower()
        keyword_hits = sum(1 for kw in keywords if kw in text_lower)
        
        # Base score from keyword presence
        base_score = min(10.0, keyword_hits * 2.0)
        
        # Research evidence boost
        citations = research_context.get("citations", [])
        research_text = " ".join([c.get("snippet", "") for c in citations]).lower()
        research_hits = sum(1 for kw in keywords if kw in research_text)
        
        if research_hits > 0:
            base_score = min(10.0, base_score + research_hits)
        
        # Rationale generation
        if keyword_hits == 0:
            rationale = f"No {moat_type.value} moat detected"
        elif keyword_hits <= 2:
            rationale = f"Weak {moat_type.value} moat - some keywords present"
        elif keyword_hits <= 4:
            rationale = f"Moderate {moat_type.value} moat - clear indicators"
        else:
            rationale = f"Strong {moat_type.value} moat - multiple indicators"
        
        # Evidence extraction
        evidence = []
        for kw in keywords:
            if kw in text_lower:
                # Find context around keyword
                idx = text_lower.find(kw)
                context = text[max(0, idx-20):min(len(text), idx+len(kw)+20)]
                evidence.append(context.strip())
        
        return base_score, rationale, evidence[:3]  # Limit to 3 evidence items

    def _generate_recommendations(
        self,
        usp: USP,
        verification_passed: bool,
        moat_scores: list[MoatScore],
    ) -> list[str]:
        """Generate recommendations based on USP analysis."""
        recommendations = []
        
        if not verification_passed:
            recommendations.append("Strengthen USP with more research-backed claims")
        
        # Identify weak moats
        weak_moats = [m for m in moat_scores if m.score < 4.0]
        if weak_moats:
            recommendations.append(
                f"Strengthen weak moats: {', '.join(m.moat_type.value for m in weak_moats)}"
            )
        
        # Identify strong moats
        strong_moats = [m for m in moat_scores if m.score >= 7.0]
        if strong_moats:
            recommendations.append(
                f"Leverage strong moats in messaging: {', '.join(m.moat_type.value for m in strong_moats)}"
            )
        
        if not usp.unique_mechanism:
            recommendations.append("Clarify the unique mechanism of the solution")
        
        if len(usp.differentiators) < 2:
            recommendations.append("Add more specific differentiators")
        
        return recommendations


__all__ = ["USPEngine", "USP", "MoatScore", "USPAnalysis", "MoatType"]
