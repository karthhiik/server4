"""
Investor intelligence engine for Barise v4 - the unfair advantage.

Matches investors, generates pitch strategies, and tracks engagement.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.v4 import CompiledSlide, InvestorProfile


class InvestorIntelligenceEngine:
    """Analyzes investors and recommends pitch strategies."""

    def __init__(self, db: Any):
        """
        Initialize with MongoDB client.

        Args:
            db: MongoDB async client
        """
        self.db = db

    async def match_investors(
        self,
        deck_id: str,
        brief: str,
        stage: str,
        sector: str,
        target_raise: float,
    ) -> List[InvestorProfile]:
        """
        Match investors based on stage, sector, check size, and thesis overlap.

        Args:
            deck_id: Presentation ID
            brief: Company brief/description
            stage: Funding stage (seed, series-a, series-b, etc.)
            sector: Industry sector
            target_raise: Target raise amount

        Returns:
            Top 10 matching investors sorted by score
        """
        investors_collection = self.db["investors"]

        # Query: stage and sector focus, check size match
        query = {
            "stage_focus": {"$regex": stage, "$options": "i"},
            "sector_focus": {"$regex": sector, "$options": "i"},
            "$expr": {
                "$and": [
                    {"$lte": ["$check_size_min", target_raise]},
                    {"$gte": ["$check_size_max", target_raise]},
                ]
            },
        }

        investors = await investors_collection.find(query).to_list(None)

        # Score each investor
        scored = []
        brief_keywords = set(brief.lower().split())

        for investor in investors:
            score = 0

            # Thesis overlap: +10 per matching keyword
            investor_keywords = set(
                kw.lower() for kw in investor.get("thesis_keywords", [])
            )
            thesis_overlap = len(brief_keywords & investor_keywords)
            score += thesis_overlap * 10

            # Recency: +30 if invested in 2025+
            recent_investments = investor.get("recent_investments", [])
            if any(inv.get("year", 0) >= 2025 for inv in recent_investments):
                score += 30

            # Warm intro paths: +50 if available
            if investor.get("warm_intro_paths"):
                score += 50

            scored.append((score, investor))

        # Sort by score descending and return top 10
        scored.sort(key=lambda x: x[0], reverse=True)
        top_investors = [InvestorProfile(**inv) for _, inv in scored[:10]]

        return top_investors

    async def generate_pitch_strategy(
        self,
        investor: InvestorProfile,
        slides: List[CompiledSlide],
    ) -> Dict[str, Any]:
        """
        Generate pitch strategy tailored to investor thesis.

        Args:
            investor: Target investor profile
            slides: Compiled slides in deck

        Returns:
            Strategy dict with lead slide, emphasis, risk questions, warm intro message
        """
        # Analyze slide intents vs investor thesis
        investor_keywords = set(kw.lower() for kw in investor.thesis_keywords)

        # Find slides with highest keyword overlap
        slide_scores = {}
        for slide in slides:
            intent_keywords = set(slide.intent.lower().split())
            overlap = len(intent_keywords & investor_keywords)
            slide_scores[slide.slide_no] = overlap

        lead_slide_no = max(slide_scores, key=slide_scores.get) if slide_scores else 1
        lead_slide_intent = next(
            (s.intent for s in slides if s.slide_no == lead_slide_no), "cover"
        )

        # Emphasis: slides matching investor focus
        emphasis = [
            s.intent for s in slides if slide_scores.get(s.slide_no, 0) > 0
        ]

        # Risk questions based on sector/stage
        risk_questions = self._generate_risk_questions(
            investor.sector_focus, investor.stage_focus
        )

        # Warm intro message template
        warm_intro = self._generate_warm_intro(investor)

        return {
            "lead_slide": lead_slide_intent,
            "emphasis": emphasis,
            "risk_questions": risk_questions,
            "warm_intro_message": warm_intro,
        }

    async def track_engagement(
        self,
        deck_id: str,
        investor_id: str,
        event: str,
        metadata: Dict[str, Any],
    ) -> None:
        """
        Record investor engagement event.

        Args:
            deck_id: Presentation ID
            investor_id: Investor profile ID
            event: Event type (view, click, download, etc.)
            metadata: Event-specific metadata
        """
        engagement_collection = self.db["engagement_events"]

        doc = {
            "deck_id": deck_id,
            "investor_id": investor_id,
            "event": event,
            "metadata": metadata,
            "timestamp": datetime.utcnow(),
        }

        await engagement_collection.insert_one(doc)

    def _generate_risk_questions(self, sectors: List[str], stages: List[str]) -> List[str]:
        """Generate anticipated tough questions based on sector/stage."""
        questions = []

        # Stage-based questions
        stage_questions = {
            "seed": [
                "What's your path to product-market fit?",
                "How will you use this capital?",
                "What are your key metrics?",
            ],
            "series-a": [
                "What's your go-to-market strategy?",
                "How do you plan to scale the team?",
                "What are your unit economics?",
            ],
            "series-b": [
                "How will you expand to new markets?",
                "What's your path to profitability?",
                "How will you defend your moat?",
            ],
        }

        # Sector-based questions
        sector_questions = {
            "saas": [
                "What's your CAC and LTV?",
                "How do you handle churn?",
                "What's your NRR?",
            ],
            "fintech": [
                "How do you comply with regulations?",
                "What's your security model?",
                "How do you acquire users?",
            ],
            "deeptech": [
                "What's your IP moat?",
                "How long to revenue?",
                "What's your tech advantage?",
            ],
        }

        # Add stage questions
        for stage in stages:
            questions.extend(stage_questions.get(stage, [])[:1])

        # Add sector questions
        for sector in sectors:
            questions.extend(sector_questions.get(sector, [])[:2])

        return questions[:3]  # Return top 3

    def _generate_warm_intro(self, investor: InvestorProfile) -> str:
        """Generate warm intro message template."""
        if not investor.warm_intro_paths:
            return f"I'd love to introduce you to {investor.name} from {investor.firm}."

        first_path = investor.warm_intro_paths[0]
        connector = first_path.get("name", "a mutual connection")

        return (
            f"I'd like to introduce you to {investor.name} from {investor.firm}. "
            f"{connector} thought we should connect given your interest in our space."
        )
