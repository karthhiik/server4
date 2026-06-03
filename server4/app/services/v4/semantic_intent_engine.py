"""
Semantic Slide Intent Engine - CTO Mission-Critical Fix

This module implements a semantic understanding system that prevents:
- Fake visuals
- Random icons
- Irrelevant graphics
- Generic startup slides
- Repeated layouts
- Low-context designs

STRICT RULE: ONE CORE IDEA PER SLIDE

Each slide MUST understand:
- WHY it exists
- WHAT message it communicates
- WHAT visual hierarchy is needed
- WHAT emotional tone is needed
- WHAT investor action is intended

Slides MUST follow:
- Narrative progression
- Visual storytelling
- Cognitive load balancing
- Investor readability
- Presentation pacing
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import structlog

from app.services.v4.parallel_writer import GeneratedSlide

logger = structlog.get_logger(__name__)


class SlidePurpose(Enum):
    """The fundamental purpose of a slide"""
    PROBLEM = "problem"  # Define the pain point
    SOLUTION = "solution"  # Present the concrete product response
    MARKET = "market"  # Prove the opportunity exists
    TRACTION = "traction"  # Demonstrate validation
    COMPETITION = "competition"  # Differentiate from alternatives
    BUSINESS_MODEL = "business_model"  # Explain how we make money
    TEAM = "team"  # Show execution capability
    FINANCIALS = "financials"  # Present financial performance
    ASK = "ask"  # State the funding request
    TIMELINE = "timeline"  # Show roadmap and milestones
    VISION = "vision"  # Paint the future picture
    PRODUCT = "product"  # Showcase the solution
    GO_TO_MARKET = "go_to_market"  # Explain distribution strategy


class EmotionalTone(Enum):
    """Emotional tone for the slide"""
    INSPIRING = "inspiring"
    CONFIDENT = "confident"
    TRUSTWORTHY = "trustworthy"
    URGENT = "urgent"
    CALM = "calm"
    EXCITING = "exciting"
    PROFESSIONAL = "professional"
    VISIONARY = "visionary"


class InvestorAction(Enum):
    """What action the investor should take after viewing this slide"""
    UNDERSTAND_PROBLEM = "understand_problem"
    BELIEVE_SOLUTION = "believe_solution"
    TRUST_MARKET = "trust_market"
    VALIDATE_TRACTION = "validate_traction"
    DIFFERENTIATE = "differentiate"
    TRUST_BUSINESS_MODEL = "trust_business_model"
    TRUST_TEAM = "trust_team"
    BELIEVE_FINANCIALS = "believe_financials"
    INVEST = "invest"
    BELIEVE_ROADMAP = "believe_roadmap"
    SHARE_VISION = "share_vision"
    WANT_PRODUCT = "want_product"
    TRUST_GTM = "trust_gtm"


class VisualHierarchy(Enum):
    """Visual hierarchy level for the slide"""
    HERO = "hero"  # Single dominant element
    BALANCED = "balanced"  # Equal weight to multiple elements
    DATA_DRIVEN = "data_driven"  # Charts/tables dominate
    TEXT_DRIVEN = "text_driven"  # Narrative dominates
    VISUAL_DRIVEN = "visual_driven"  # Images/diagrams dominate


@dataclass
class SlideSemanticContext:
    """Complete semantic understanding of a slide"""
    core_idea: str  # ONE core idea
    purpose: SlidePurpose
    emotional_tone: EmotionalTone
    investor_action: InvestorAction
    visual_hierarchy: VisualHierarchy
    narrative_role: str  # How this slide fits in the story
    cognitive_load: float  # 0.0 (light) to 1.0 (heavy)
    specificity_score: float  # 0.0 (generic) to 1.0 (specific)
    relevance_score: float  # 0.0 (irrelevant) to 1.0 (highly relevant)


@dataclass
class SemanticAnalysisResult:
    """Result of semantic analysis"""
    is_valid: bool
    context: Optional[SlideSemanticContext] = None
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    specificity_score: float = 0.0


class SemanticIntentEngine:
    """
    Semantic Slide Intent Engine
    
    Ensures every slide has a clear, specific purpose and message.
    Prevents generic, AI-generated fluff.
    """
    
    # Generic headline patterns that indicate lack of specificity
    GENERIC_PATTERNS = [
        r"our unique value proposition",
        r"our strategic edge",
        r"our distinctive edge",
        r"our solution",
        r"the problem",
        r"the solution",
        r"market opportunity",
        r"how we operate",
        r"empowering resilience",
        r"strategic advantages",
        r"our approach",
        r"our platform",
        r"our technology",
        r"innovative approach",
        r"cutting-edge technology",
        r"industry-leading",
        r"world-class",
        r"state-of-the-art",
        r"best-in-class",
        r"transforming industries",
        r"revolutionizing",
        r"disrupting",
    ]

    INDUSTRY_HEADLINE_SIGNALS = {
        "cybersecurity": (
            "security",
            "trust",
            "zero-trust",
            "zero trust",
            "identity",
            "auth",
            "proof",
            "did",
            "zk",
            "device",
            "edge",
            "root-of-trust",
            "consensus",
            "neural-guardian",
        ),
        "edge computing": (
            "edge",
            "iot",
            "device",
            "fleet",
            "latency",
            "low-bandwidth",
            "trust",
        ),
        "space cyber insurance": (
            "space",
            "satellite",
            "orbital",
            "insurance",
            "coverage",
            "underwriting",
            "payout",
            "jamming",
            "spoofing",
            "cyber-kinetic",
            "orbital-threat-index",
        ),
        "cyber insurance": (
            "insurance",
            "coverage",
            "underwriting",
            "risk",
            "claims",
            "payout",
            "cyber",
        ),
        "space technology": (
            "space",
            "satellite",
            "orbital",
            "constellation",
            "aerospace",
        ),
        "post-quantum data archiving": (
            "post-quantum",
            "quantum",
            "lattice",
            "archive",
            "archiving",
            "vault",
            "heritage",
            "harvest now",
            "decrypt later",
            "quantum-y2k",
        ),
        "data security": (
            "security",
            "archive",
            "vault",
            "encryption",
            "cryptography",
        ),
    }
    
    # Purpose to action mapping
    PURPOSE_ACTION_MAP = {
        SlidePurpose.PROBLEM: InvestorAction.UNDERSTAND_PROBLEM,
        SlidePurpose.SOLUTION: InvestorAction.BELIEVE_SOLUTION,
        SlidePurpose.MARKET: InvestorAction.TRUST_MARKET,
        SlidePurpose.TRACTION: InvestorAction.VALIDATE_TRACTION,
        SlidePurpose.COMPETITION: InvestorAction.DIFFERENTIATE,
        SlidePurpose.BUSINESS_MODEL: InvestorAction.TRUST_BUSINESS_MODEL,
        SlidePurpose.TEAM: InvestorAction.TRUST_TEAM,
        SlidePurpose.FINANCIALS: InvestorAction.BELIEVE_FINANCIALS,
        SlidePurpose.ASK: InvestorAction.INVEST,
        SlidePurpose.TIMELINE: InvestorAction.BELIEVE_ROADMAP,
        SlidePurpose.VISION: InvestorAction.SHARE_VISION,
        SlidePurpose.PRODUCT: InvestorAction.WANT_PRODUCT,
        SlidePurpose.GO_TO_MARKET: InvestorAction.TRUST_GTM,
    }
    
    # Purpose to tone mapping
    PURPOSE_TONE_MAP = {
        SlidePurpose.PROBLEM: EmotionalTone.URGENT,
        SlidePurpose.SOLUTION: EmotionalTone.CONFIDENT,
        SlidePurpose.MARKET: EmotionalTone.EXCITING,
        SlidePurpose.TRACTION: EmotionalTone.CONFIDENT,
        SlidePurpose.COMPETITION: EmotionalTone.CONFIDENT,
        SlidePurpose.BUSINESS_MODEL: EmotionalTone.PROFESSIONAL,
        SlidePurpose.TEAM: EmotionalTone.TRUSTWORTHY,
        SlidePurpose.FINANCIALS: EmotionalTone.PROFESSIONAL,
        SlidePurpose.ASK: EmotionalTone.CONFIDENT,
        SlidePurpose.TIMELINE: EmotionalTone.EXCITING,
        SlidePurpose.VISION: EmotionalTone.INSPIRING,
        SlidePurpose.PRODUCT: EmotionalTone.EXCITING,
        SlidePurpose.GO_TO_MARKET: EmotionalTone.PROFESSIONAL,
    }
    
    # Purpose to visual hierarchy mapping
    PURPOSE_HIERARCHY_MAP = {
        SlidePurpose.PROBLEM: VisualHierarchy.TEXT_DRIVEN,
        SlidePurpose.SOLUTION: VisualHierarchy.VISUAL_DRIVEN,
        SlidePurpose.MARKET: VisualHierarchy.DATA_DRIVEN,
        SlidePurpose.TRACTION: VisualHierarchy.DATA_DRIVEN,
        SlidePurpose.COMPETITION: VisualHierarchy.BALANCED,
        SlidePurpose.BUSINESS_MODEL: VisualHierarchy.BALANCED,
        SlidePurpose.TEAM: VisualHierarchy.VISUAL_DRIVEN,
        SlidePurpose.FINANCIALS: VisualHierarchy.DATA_DRIVEN,
        SlidePurpose.ASK: VisualHierarchy.TEXT_DRIVEN,
        SlidePurpose.TIMELINE: VisualHierarchy.VISUAL_DRIVEN,
        SlidePurpose.VISION: VisualHierarchy.HERO,
        SlidePurpose.PRODUCT: VisualHierarchy.VISUAL_DRIVEN,
        SlidePurpose.GO_TO_MARKET: VisualHierarchy.BALANCED,
    }
    
    def analyze_slide(
        self,
        slide: GeneratedSlide,
        company_name: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> SemanticAnalysisResult:
        """
        Analyze slide for semantic quality and specificity.
        
        Returns analysis with context, issues, and suggestions.
        """
        issues = []
        suggestions = []
        
        # Determine purpose from intent
        purpose = self._infer_purpose(slide.intent or "")
        
        # Check headline specificity
        headline = slide.headline or ""
        specificity_score = self._calculate_specificity(headline, company_name, industry)
        
        # Check for generic patterns
        generic_matches = self._detect_generic_patterns(headline)
        if generic_matches:
            issues.append(f"Headline contains generic phrases: {', '.join(generic_matches)}")
            suggestions.append("Replace generic phrases with specific, company-specific language")
        
        # Check if headline mentions company or industry
        has_company = company_name and company_name.lower() in headline.lower()
        has_industry = self._has_industry_signal(headline, industry)
        has_metric = bool(re.search(r'\d+|\$\d+|\d+%', headline))
        
        if not (has_company or has_industry or has_metric):
            issues.append("Headline lacks company name, industry, or specific metric")
            suggestions.append(f"Include '{company_name or 'company name'}', '{industry or 'industry'}', or a specific metric")
        
        # Check for single core idea
        core_ideas = self._extract_core_ideas(slide)
        if len(core_ideas) > 1:
            issues.append(f"Slide has multiple core ideas: {', '.join(core_ideas[:3])}")
            suggestions.append("Focus on ONE core idea per slide. Split into multiple slides if needed")
        
        # Build semantic context
        context = SlideSemanticContext(
            core_idea=core_ideas[0] if core_ideas else headline,
            purpose=purpose,
            emotional_tone=self.PURPOSE_TONE_MAP.get(purpose, EmotionalTone.PROFESSIONAL),
            investor_action=self.PURPOSE_ACTION_MAP.get(purpose, InvestorAction.UNDERSTAND_PROBLEM),
            visual_hierarchy=self.PURPOSE_HIERARCHY_MAP.get(purpose, VisualHierarchy.BALANCED),
            narrative_role=self._infer_narrative_role(purpose),
            cognitive_load=self._calculate_cognitive_load(slide),
            specificity_score=specificity_score,
            relevance_score=self._calculate_relevance(slide, purpose),
        )
        
        # Determine if slide is valid
        is_valid = (
            len(issues) == 0 and
            specificity_score >= 0.6 and
            context.relevance_score >= 0.7
        )
        
        return SemanticAnalysisResult(
            is_valid=is_valid,
            context=context,
            issues=issues,
            suggestions=suggestions,
            specificity_score=specificity_score,
        )
    
    def _infer_purpose(self, intent: str) -> SlidePurpose:
        """Infer slide purpose from intent"""
        intent_lower = intent.lower()
        
        purpose_map = {
            "problem": SlidePurpose.PROBLEM,
            "solution": SlidePurpose.SOLUTION,
            "market": SlidePurpose.MARKET,
            "traction": SlidePurpose.TRACTION,
            "competition": SlidePurpose.COMPETITION,
            "business_model": SlidePurpose.BUSINESS_MODEL,
            "team": SlidePurpose.TEAM,
            "financials": SlidePurpose.FINANCIALS,
            "ask": SlidePurpose.ASK,
            "timeline": SlidePurpose.TIMELINE,
            "vision": SlidePurpose.VISION,
            "product": SlidePurpose.PRODUCT,
            "go_to_market": SlidePurpose.GO_TO_MARKET,
            "title": SlidePurpose.VISION,
            "cover": SlidePurpose.VISION,
        }
        
        for key, purpose in purpose_map.items():
            if key in intent_lower:
                return purpose
        
        return SlidePurpose.SOLUTION  # Default fallback
    
    def _calculate_specificity(
        self,
        headline: str,
        company_name: Optional[str],
        industry: Optional[str],
    ) -> float:
        """Calculate specificity score (0.0 to 1.0)"""
        score = 1.0
        
        headline_lower = headline.lower()
        
        # Penalize for generic patterns
        for pattern in self.GENERIC_PATTERNS:
            if re.search(pattern, headline_lower):
                score -= 0.2
        
        # Reward for company name
        if company_name and company_name.lower() in headline_lower:
            score += 0.15
        
        # Reward for industry or domain-specific technical vocabulary.
        if self._has_industry_signal(headline, industry):
            score += 0.1
        
        # Reward for metrics
        if re.search(r'\d+|\$\d+|\d+%', headline):
            score += 0.2
        
        # Reward for specific numbers
        if re.search(r'\d{2,}', headline):
            score += 0.1
        
        # Penalize for short headlines
        if len(headline) < 15:
            score -= 0.2
        
        # Penalize for very long headlines
        if len(headline) > 100:
            score -= 0.1
        
        return max(0.0, min(1.0, score))

    def _has_industry_signal(self, text: str, industry: Optional[str]) -> bool:
        if not industry or not text:
            return False
        text_lower = text.lower()
        industry_lower = industry.lower()
        if industry_lower in text_lower:
            return True
        return any(
            signal in text_lower
            for signal in self.INDUSTRY_HEADLINE_SIGNALS.get(industry_lower, ())
        )
    
    def _detect_generic_patterns(self, headline: str) -> List[str]:
        """Detect generic patterns in headline"""
        matches = []
        headline_lower = headline.lower()
        
        for pattern in self.GENERIC_PATTERNS:
            if re.search(pattern, headline_lower):
                matches.append(pattern)
        
        return matches
    
    def _extract_core_ideas(self, slide: GeneratedSlide) -> List[str]:
        """Extract core ideas from slide"""
        ideas = []
        
        # From headline
        if slide.headline:
            ideas.append(slide.headline)
        
        # From bullets
        if slide.bullets:
            for bullet in slide.bullets[:3]:  # First 3 bullets
                ideas.append(str(bullet))
        
        # From body
        if slide.body:
            # Extract first sentence
            sentences = re.split(r'[.!?]', slide.body)
            if sentences:
                ideas.append(sentences[0].strip())
        
        return ideas
    
    def _infer_narrative_role(self, purpose: SlidePurpose) -> str:
        """Infer the narrative role of this slide"""
        role_map = {
            SlidePurpose.PROBLEM: "Establish the pain point",
            SlidePurpose.SOLUTION: "Present the concrete product response",
            SlidePurpose.MARKET: "Prove market opportunity",
            SlidePurpose.TRACTION: "Demonstrate validation",
            SlidePurpose.COMPETITION: "Differentiate from alternatives",
            SlidePurpose.BUSINESS_MODEL: "Explain revenue model",
            SlidePurpose.TEAM: "Show execution capability",
            SlidePurpose.FINANCIALS: "Present financial performance",
            SlidePurpose.ASK: "State funding request",
            SlidePurpose.TIMELINE: "Show roadmap",
            SlidePurpose.VISION: "Paint future picture",
            SlidePurpose.PRODUCT: "Showcase solution",
            SlidePurpose.GO_TO_MARKET: "Explain distribution",
        }
        
        return role_map.get(purpose, "Communicate value proposition")
    
    def _calculate_cognitive_load(self, slide: GeneratedSlide) -> float:
        """Calculate cognitive load (0.0 light to 1.0 heavy)"""
        load = 0.0
        
        # Count content items
        if slide.bullets:
            load += len(slide.bullets) * 0.1
        if slide.stat_blocks:
            load += len(slide.stat_blocks) * 0.15
        if slide.chart:
            load += 0.2
        if slide.timeline:
            load += 0.15
        if slide.team_members:
            load += len(slide.team_members) * 0.1
        if slide.body:
            load += len(slide.body) * 0.005  # Per character
        
        return min(1.0, load)
    
    def _calculate_relevance(self, slide: GeneratedSlide, purpose: SlidePurpose) -> float:
        """Calculate relevance score (0.0 to 1.0)"""
        score = 0.5  # Base score
        
        # Check if content matches purpose
        if purpose == SlidePurpose.TRACTION and slide.stat_blocks:
            score += 0.3
        if purpose == SlidePurpose.FINANCIALS and slide.chart:
            score += 0.3
        if purpose == SlidePurpose.TEAM and slide.team_members:
            score += 0.3
        if purpose == SlidePurpose.TIMELINE and slide.timeline:
            score += 0.3
        if purpose == SlidePurpose.COMPETITION and slide.comparison:
            score += 0.3
        
        # Check for empty content
        has_content = bool(
            slide.bullets or
            slide.stat_blocks or
            slide.chart or
            slide.timeline or
            slide.team_members or
            slide.body
        )
        
        if not has_content:
            score -= 0.4
        
        return max(0.0, min(1.0, score))
    
    def improve_slide_specificity(
        self,
        slide: GeneratedSlide,
        company_name: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> Optional[GeneratedSlide]:
        """
        Attempt to improve slide specificity by adding context.
        
        Returns improved slide or None if improvement is not possible.
        """
        analysis = self.analyze_slide(slide, company_name, industry)
        
        if analysis.is_valid:
            return slide
        
        # Attempt to improve headline
        headline = slide.headline or ""
        
        # Add company name if missing
        if company_name and company_name.lower() not in headline.lower():
            headline = f"{company_name}: {headline}"
        
        # Do not suffix headlines with a detected industry. Audience phrases
        # like "FinTech investors" are not product categories, and appending
        # them creates visible mail-merge errors. Specificity is enforced by
        # scoring and rewrite prompts, not by mutating audience-facing copy.
        
        # Create improved slide
        try:
            slide_dict = slide.__dict__.copy()
            slide_dict["headline"] = headline
            return GeneratedSlide(**slide_dict)
        except Exception as e:
            logger.error("slide_specificity_improvement_failed", error=str(e))
            return None


# Singleton instance
_engine_instance: Optional[SemanticIntentEngine] = None


def get_semantic_intent_engine() -> SemanticIntentEngine:
    """Get singleton semantic intent engine instance"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SemanticIntentEngine()
    return _engine_instance
