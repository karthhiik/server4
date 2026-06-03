"""
Pitch Coach AI - Quick Scan against Y Combinator Pitch Deck Checklist

Analyzes pitch decks against YC's recommended pitch deck structure and provides
quick feedback on missing elements, weak areas, and improvement suggestions.

YC Pitch Deck Checklist (based on YC's official recommendations):
1. Problem - What problem are you solving?
2. Solution - How do you solve it?
3. Why Now - Why is this the right time?
4. Market Size - How big is the opportunity?
5. Competition - Who else is doing this?
6. Business Model - How do you make money?
7. Team - Who are you and why are you the right team?
8. Traction - What have you accomplished so far?
9. Ask - How much are you raising and what will you do with it?
10. Vision - Where is this going in 5-10 years?
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class ChecklistItem(Enum):
    """YC Pitch Deck Checklist items"""
    PROBLEM = "problem"
    SOLUTION = "solution"
    WHY_NOW = "why_now"
    MARKET_SIZE = "market_size"
    COMPETITION = "competition"
    BUSINESS_MODEL = "business_model"
    TEAM = "team"
    TRACTION = "traction"
    ASK = "ask"
    VISION = "vision"


@dataclass
class ChecklistResult:
    """Result for a single checklist item"""
    item: ChecklistItem
    present: bool
    slide_indices: List[int] = field(default_factory=list)
    score: float = 0.0  # 0.0 to 1.0
    feedback: str = ""
    suggestions: List[str] = field(default_factory=list)


@dataclass
class PitchCoachReport:
    """Complete pitch coach analysis report"""
    overall_score: float  # 0.0 to 1.0
    checklist_results: List[ChecklistResult] = field(default_factory=list)
    missing_items: List[ChecklistItem] = field(default_factory=list)
    weak_areas: List[ChecklistItem] = field(default_factory=list)
    strong_areas: List[ChecklistItem] = field(default_factory=list)
    top_suggestions: List[str] = field(default_factory=list)
    narrative_flow_score: float = 0.0
    data_quality_score: float = 0.0


class PitchCoach:
    """
    Pitch Coach AI - analyzes pitch decks against YC checklist
    """
    
    # Intent to checklist mapping
    INTENT_TO_CHECKLIST: Dict[str, ChecklistItem] = {
        "problem": ChecklistItem.PROBLEM,
        "solution": ChecklistItem.SOLUTION,
        "why_now": ChecklistItem.WHY_NOW,
        "market": ChecklistItem.MARKET_SIZE,
        "market_size": ChecklistItem.MARKET_SIZE,
        "competition": ChecklistItem.COMPETITION,
        "business_model": ChecklistItem.BUSINESS_MODEL,
        "team": ChecklistItem.TEAM,
        "traction": ChecklistItem.TRACTION,
        "ask": ChecklistItem.ASK,
        "vision": ChecklistItem.VISION,
        "opportunity": ChecklistItem.WHY_NOW,
    }
    
    # Minimum content thresholds for scoring
    MIN_HEADLINE_LENGTH = 10
    MIN_BODY_LENGTH = 50
    MIN_BULLETS = 2
    
    def __init__(self):
        self.logger = logger
    
    def scan_deck(self, slides: List[Dict[str, Any]]) -> PitchCoachReport:
        """
        Scan a deck against YC pitch deck checklist
        
        Args:
            slides: List of slide dictionaries with keys: intent, headline, body, bullets, etc.
            
        Returns:
            PitchCoachReport with analysis results
        """
        self.logger.info("pitch_coach_scan_start", n_slides=len(slides))
        
        # Analyze each checklist item
        checklist_results = []
        
        for item in ChecklistItem:
            result = self._analyze_checklist_item(item, slides)
            checklist_results.append(result)
        
        # Calculate overall scores
        overall_score = self._calculate_overall_score(checklist_results)
        narrative_flow_score = self._analyze_narrative_flow(slides)
        data_quality_score = self._analyze_data_quality(slides)
        
        # Categorize items
        missing_items = [r.item for r in checklist_results if not r.present]
        weak_areas = [r.item for r in checklist_results if r.present and r.score < 0.5]
        strong_areas = [r.item for r in checklist_results if r.score >= 0.7]
        
        # Generate top suggestions
        top_suggestions = self._generate_top_suggestions(checklist_results)
        
        report = PitchCoachReport(
            overall_score=overall_score,
            checklist_results=checklist_results,
            missing_items=missing_items,
            weak_areas=weak_areas,
            strong_areas=strong_areas,
            top_suggestions=top_suggestions,
            narrative_flow_score=narrative_flow_score,
            data_quality_score=data_quality_score,
        )
        
        self.logger.info(
            "pitch_coach_scan_complete",
            overall_score=overall_score,
            missing=len(missing_items),
            weak=len(weak_areas),
            strong=len(strong_areas),
        )
        
        return report
    
    def _analyze_checklist_item(self, item: ChecklistItem, slides: List[Dict[str, Any]]) -> ChecklistResult:
        """Analyze a single checklist item across the deck"""
        matching_slides = []
        
        # Find slides with matching intent
        for idx, slide in enumerate(slides):
            intent = slide.get("intent", "").lower()
            if intent in self.INTENT_TO_CHECKLIST and self.INTENT_TO_CHECKLIST[intent] == item:
                matching_slides.append((idx, slide))
        
        # Check if item is present
        present = len(matching_slides) > 0
        
        # Calculate score based on content quality
        score = 0.0
        feedback = ""
        suggestions = []
        
        if present:
            # Use the best matching slide for scoring
            best_slide_idx, best_slide = max(
                matching_slides,
                key=lambda x: self._slide_content_score(x[1])
            )
            
            score = self._slide_content_score(best_slide)
            feedback = self._generate_feedback(item, best_slide, score)
            suggestions = self._generate_suggestions(item, best_slide, score)
        else:
            feedback = f"Missing {item.value.replace('_', ' ')} slide"
            suggestions = self._generate_missing_suggestions(item)
        
        return ChecklistResult(
            item=item,
            present=present,
            slide_indices=[s[0] for s in matching_slides],
            score=score,
            feedback=feedback,
            suggestions=suggestions,
        )
    
    def _slide_content_score(self, slide: Dict[str, Any]) -> float:
        """Score a slide's content quality (0.0 to 1.0)"""
        score = 0.0
        
        # Headline quality
        headline = slide.get("headline", "") or slide.get("title", "")
        if len(headline) >= self.MIN_HEADLINE_LENGTH:
            score += 0.3
        elif len(headline) > 0:
            score += 0.1
        
        # Body content
        body = slide.get("body", "") or slide.get("content", "")
        if len(body) >= self.MIN_BODY_LENGTH:
            score += 0.3
        elif len(body) > 0:
            score += 0.1
        
        # Bullets
        bullets = slide.get("bullets", [])
        if len(bullets) >= self.MIN_BULLETS:
            score += 0.3
        elif len(bullets) > 0:
            score += 0.1
        
        # Data/stat blocks
        stat_blocks = slide.get("stat_blocks", [])
        if len(stat_blocks) > 0:
            score += 0.1
        
        return min(score, 1.0)
    
    def _generate_feedback(self, item: ChecklistItem, slide: Dict[str, Any], score: float) -> str:
        """Generate feedback for a checklist item"""
        if score >= 0.7:
            return f"Strong {item.value.replace('_', ' ')} section"
        elif score >= 0.4:
            return f"{item.value.replace('_', ' ')} section needs improvement"
        else:
            return f"{item.value.replace('_', ' ')} section is weak"
    
    def _generate_suggestions(self, item: ChecklistItem, slide: Dict[str, Any], score: float) -> List[str]:
        """Generate suggestions for improving a checklist item"""
        suggestions = []
        
        headline = slide.get("headline", "") or slide.get("title", "")
        body = slide.get("body", "") or slide.get("content", "")
        bullets = slide.get("bullets", [])
        
        if len(headline) < self.MIN_HEADLINE_LENGTH:
            suggestions.append(f"Add a more descriptive headline for {item.value.replace('_', ' ')}")
        
        if len(body) < self.MIN_BODY_LENGTH:
            suggestions.append(f"Expand the {item.value.replace('_', ' ')} description with more detail")
        
        if len(bullets) < self.MIN_BULLETS:
            suggestions.append(f"Add bullet points to highlight key aspects of {item.value.replace('_', ' ')}")
        
        # Item-specific suggestions
        if item == ChecklistItem.MARKET_SIZE:
            suggestions.append("Include TAM, SAM, and SOM figures")
            suggestions.append("Cite market research sources")
        elif item == ChecklistItem.TRACTION:
            suggestions.append("Include specific metrics (revenue, users, growth rate)")
            suggestions.append("Show a timeline of key milestones")
        elif item == ChecklistItem.COMPETITION:
            suggestions.append("Include a competitive matrix")
            suggestions.append("Highlight your unique differentiator")
        elif item == ChecklistItem.ASK:
            suggestions.append("Specify the exact amount being raised")
            suggestions.append("Break down use of funds")
        
        return suggestions[:3]  # Limit to top 3 suggestions
    
    def _generate_missing_suggestions(self, item: ChecklistItem) -> List[str]:
        """Generate suggestions for a missing checklist item"""
        return [
            f"Add a {item.value.replace('_', ' ')} slide to your deck",
            f"YC partners expect to see {item.value.replace('_', ' ')} covered",
        ]
    
    def _calculate_overall_score(self, checklist_results: List[ChecklistResult]) -> float:
        """Calculate overall deck score from checklist results"""
        if not checklist_results:
            return 0.0
        
        # Score based on presence and quality
        total_score = 0.0
        for result in checklist_results:
            if result.present:
                total_score += result.score
            else:
                total_score += 0.0  # Missing items get 0
        
        return total_score / len(checklist_results)
    
    def _analyze_narrative_flow(self, slides: List[Dict[str, Any]]) -> float:
        """Analyze the narrative flow of the deck"""
        if len(slides) < 3:
            return 0.0
        
        intents = [s.get("intent", "").lower() for s in slides]
        
        # Check for logical flow patterns
        # Expected flow: problem -> solution -> market -> traction -> team -> ask
        expected_order = ["problem", "solution", "market", "traction", "team", "ask"]
        
        score = 0.0
        for i in range(len(expected_order) - 1):
            if expected_order[i] in intents and expected_order[i + 1] in intents:
                idx1 = intents.index(expected_order[i])
                idx2 = intents.index(expected_order[i + 1])
                if idx1 < idx2:
                    score += 0.2
        
        return min(score, 1.0)
    
    def _analyze_data_quality(self, slides: List[Dict[str, Any]]) -> float:
        """Analyze the quality of data/statements in the deck"""
        total_stat_blocks = sum(len(s.get("stat_blocks", [])) for s in slides)
        total_citations = sum(len(s.get("citations", [])) for s in slides)
        
        score = 0.0
        
        # Points for having data
        if total_stat_blocks > 0:
            score += 0.4
        if total_citations > 0:
            score += 0.3
        
        # Points for data density
        avg_stat_blocks = total_stat_blocks / len(slides) if slides else 0
        if avg_stat_blocks >= 1:
            score += 0.3
        
        return min(score, 1.0)
    
    def _generate_top_suggestions(self, checklist_results: List[ChecklistResult]) -> List[str]:
        """Generate top priority suggestions for the deck"""
        suggestions = []
        
        # Prioritize missing items
        missing = [r for r in checklist_results if not r.present]
        for result in missing[:3]:
            suggestions.append(f"Add {result.item.value.replace('_', ' ')} slide")
        
        # Then weak areas
        weak = [r for r in checklist_results if r.present and r.score < 0.5]
        for result in weak[:2]:
            if result.suggestions:
                suggestions.append(result.suggestions[0])
        
        return suggestions[:5]
