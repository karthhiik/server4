"""
Community Summarizer — Extracts deck-wide themes using map-reduce.

Takes all FactPackets for a deck run and clusters them into thematic
communities, then generates summaries for narrative consistency.

Themes: market_urgency, competitive_landscape, traction_narrative,
        financial_trajectory, technology_moat, team_strength
"""

import json
import logging
from typing import Any, Optional

from app.mcp.brain_mcp.research.models import ClaimType, FactPacket, SlideKind

logger = logging.getLogger(__name__)

# ── Theme definitions ─────────────────────────────────────────────

THEMES: dict[str, dict[str, Any]] = {
    "market_urgency": {
        "description": "Why this market matters now",
        "claim_types": [ClaimType.trend, ClaimType.numeric],
        "keywords": [
            "market", "growth", "TAM", "SAM", "SOM", "opportunity",
            "emerging", "growing", "trillion", "billion", "demand",
            "adoption", "penetration", "addressable",
        ],
    },
    "competitive_landscape": {
        "description": "Who else is playing and how we're different",
        "claim_types": [ClaimType.comparison, ClaimType.qualitative],
        "keywords": [
            "competitor", "alternative", "versus", "compared", "advantage",
            "moat", "differentiation", "market share", "incumbent",
            "disrupt", "outperform", "leader", "rival",
        ],
    },
    "traction_narrative": {
        "description": "Evidence of product-market fit and momentum",
        "claim_types": [ClaimType.numeric, ClaimType.trend],
        "keywords": [
            "users", "revenue", "growth", "retention", "customers",
            "ARR", "MRR", "DAU", "MAU", "engagement", "activation",
            "churn", "NPS", "waitlist", "conversion", "pipeline",
        ],
    },
    "financial_trajectory": {
        "description": "Financial health and projection credibility",
        "claim_types": [ClaimType.numeric],
        "keywords": [
            "revenue", "margin", "burn", "runway", "unit economics",
            "CAC", "LTV", "ARPU", "gross margin", "net revenue",
            "profitability", "break-even", "cash flow", "valuation",
        ],
    },
    "technology_moat": {
        "description": "Technical defensibility and innovation",
        "claim_types": [ClaimType.qualitative, ClaimType.citation],
        "keywords": [
            "patent", "algorithm", "proprietary", "infrastructure",
            "platform", "API", "IP", "architecture", "scalable",
            "latency", "throughput", "accuracy", "benchmark", "model",
        ],
    },
    "team_strength": {
        "description": "Team credibility and relevant experience",
        "claim_types": [ClaimType.qualitative, ClaimType.testimonial],
        "keywords": [
            "founder", "team", "experience", "advisor", "previous exit",
            "serial entrepreneur", "PhD", "executive", "board",
            "domain expert", "track record", "leadership",
        ],
    },
}


class CommunitySummarizer:
    """Extracts and summarizes deck-wide themes from evidence."""

    def __init__(self, model_router: Any = None) -> None:
        self._router = model_router

    async def summarize(
        self, all_packets: list[FactPacket], topic: str
    ) -> dict[str, dict[str, Any]]:
        """
        Cluster FactPackets into thematic communities and generate summaries.

        Uses map-reduce:
        1. MAP: Assign each FactPacket to relevant themes
        2. REDUCE: For each theme with 2+ packets, generate a narrative summary

        Returns: {
            "market_urgency": {
                "summary": "...",
                "key_facts": [...],
                "strength": 0.0-1.0,
                "packet_count": int,
            },
            ...
        }
        """
        if not all_packets:
            return {}

        # MAP phase: assign packets to themes
        theme_clusters = self._assign_themes(all_packets)

        # REDUCE phase: generate summaries per theme
        result: dict[str, dict[str, Any]] = {}
        for theme_name, packets in theme_clusters.items():
            if len(packets) < 2:
                # Not enough evidence for a theme
                result[theme_name] = {
                    "summary": "",
                    "key_facts": [p.claim for p in packets],
                    "strength": self._compute_theme_strength(packets),
                    "packet_count": len(packets),
                }
                continue

            theme_def = THEMES[theme_name]
            summary = await self._generate_theme_summary(
                theme_name, theme_def, packets, topic
            )
            result[theme_name] = summary

        logger.info(
            "community_summarization_complete",
            total_packets=len(all_packets),
            themes_found=len(result),
            themes_with_summary=sum(
                1 for v in result.values() if v.get("summary")
            ),
        )
        return result

    def _assign_themes(
        self, packets: list[FactPacket]
    ) -> dict[str, list[FactPacket]]:
        """Assign packets to themes based on keywords and claim types."""
        clusters: dict[str, list[FactPacket]] = {name: [] for name in THEMES}

        for packet in packets:
            claim_lower = packet.claim.lower()
            source_lower = packet.source_name.lower()
            combined_text = f"{claim_lower} {source_lower}"
            snippet_lower = (packet.raw_snippet or "").lower()

            for theme_name, theme_def in THEMES.items():
                score = 0.0

                # Keyword matching (case-insensitive)
                keyword_hits = sum(
                    1 for kw in theme_def["keywords"]
                    if kw.lower() in combined_text or kw.lower() in snippet_lower
                )
                score += keyword_hits * 0.3

                # Claim type matching
                if packet.claim_type in theme_def["claim_types"]:
                    score += 0.4

                # Threshold for assignment
                if score >= 0.3:
                    clusters[theme_name].append(packet)

        # Remove empty themes
        return {k: v for k, v in clusters.items() if v}

    async def _generate_theme_summary(
        self,
        theme_name: str,
        theme_def: dict[str, Any],
        packets: list[FactPacket],
        topic: str,
    ) -> dict[str, Any]:
        """Generate narrative summary for a theme using LLM or fallback."""
        # Sort packets by confidence descending
        sorted_packets = sorted(packets, key=lambda p: p.confidence, reverse=True)
        top_facts = [p.claim for p in sorted_packets[:8]]
        strength = self._compute_theme_strength(sorted_packets)

        # Try LLM-based summary if router is available
        if self._router:
            summary = await self._llm_summary(
                theme_name, theme_def, top_facts, topic
            )
            if summary:
                return {
                    "summary": summary,
                    "key_facts": top_facts,
                    "strength": strength,
                    "packet_count": len(packets),
                }

        # Fallback: deterministic summary construction
        summary = self._build_deterministic_summary(
            theme_name, theme_def, sorted_packets, topic
        )
        return {
            "summary": summary,
            "key_facts": top_facts,
            "strength": strength,
            "packet_count": len(packets),
        }

    async def _llm_summary(
        self,
        theme_name: str,
        theme_def: dict[str, Any],
        facts: list[str],
        topic: str,
    ) -> Optional[str]:
        """Attempt LLM-based summarization via model_router."""
        prompt = (
            f"You are a pitch deck analyst summarizing the '{theme_name}' theme "
            f"for a presentation about '{topic}'.\n\n"
            f"Theme description: {theme_def['description']}\n\n"
            f"Key evidence:\n"
        )
        for i, fact in enumerate(facts, 1):
            prompt += f"  {i}. {fact}\n"
        prompt += (
            "\nWrite a concise 2-3 sentence narrative summary that weaves these "
            "facts into a compelling story. Focus on the 'so what' — why does "
            "this evidence matter for investors? Return ONLY the summary text."
        )

        try:
            # Use Groq for speed (T4 tier)
            if hasattr(self._router, "route"):
                response = await self._router.route(
                    task_type="translation_quick_edit",
                    prompt=prompt,
                    max_tokens=250,
                    temperature=0.4,
                )
                if response and hasattr(response, "content"):
                    return response.content.strip()
            # Fallback to direct call if router has generate method
            if hasattr(self._router, "generate"):
                result = await self._router.generate(prompt, max_tokens=250)
                if isinstance(result, str):
                    return result.strip()
                if hasattr(result, "content"):
                    return result.content.strip()
        except Exception:
            logger.warning(
                "llm_theme_summary_failed",
                theme=theme_name,
                exc_info=True,
            )

        return None

    def _build_deterministic_summary(
        self,
        theme_name: str,
        theme_def: dict[str, Any],
        packets: list[FactPacket],
        topic: str,
    ) -> str:
        """Build a deterministic summary without LLM."""
        desc = theme_def["description"]
        count = len(packets)

        # Pick top 3 claims by confidence
        top_claims = [p.claim for p in packets[:3]]

        # Count numeric vs qualitative
        numeric_count = sum(
            1 for p in packets if p.claim_type == ClaimType.numeric
        )

        intro = (
            f"Regarding {desc.lower()} for '{topic}', "
            f"{count} evidence points were gathered"
        )
        if numeric_count > 0:
            intro += f" ({numeric_count} quantitative)"
        intro += ". "

        body = "Key findings include: " + "; ".join(top_claims[:3]) + "."

        source_names = list({p.source_name for p in packets[:5]})
        if source_names:
            body += f" Sources include {', '.join(source_names[:3])}."

        return intro + body

    def _compute_theme_strength(self, packets: list[FactPacket]) -> float:
        """
        Score theme strength based on evidence quality and quantity.

        Factors:
        - Number of packets (more = stronger, diminishing returns)
        - Average confidence
        - Source diversity (more diverse sources = stronger)
        - Cross-validation rate
        """
        if not packets:
            return 0.0

        # Quantity score (log scale, caps at ~1.0 around 10 packets)
        import math
        quantity = min(1.0, math.log2(len(packets) + 1) / 3.5)

        # Average confidence
        avg_conf = sum(p.confidence for p in packets) / len(packets)

        # Source diversity (unique providers / total, bonus for multi-source)
        unique_providers = len({p.provider for p in packets})
        diversity = min(1.0, unique_providers / max(3, len(packets) * 0.5))

        # Cross-validation rate
        cross_val = sum(1 for p in packets if p.cross_validated) / len(packets)

        # Weighted combination
        strength = (
            quantity * 0.25
            + avg_conf * 0.35
            + diversity * 0.25
            + cross_val * 0.15
        )
        return round(min(1.0, strength), 3)

    def get_narrative_anchors(
        self, summaries: dict[str, dict[str, Any]]
    ) -> list[str]:
        """
        Extract key sentences that can anchor slide narratives for consistency.

        Returns the strongest summary sentences across all themes,
        ordered by theme strength.
        """
        scored: list[tuple[float, str]] = []
        for theme_name, data in summaries.items():
            summary = data.get("summary", "")
            strength = data.get("strength", 0.0)
            if summary:
                # Split summary into sentences and score each
                sentences = [
                    s.strip() for s in summary.replace(". ", ".\n").split("\n")
                    if s.strip() and len(s.strip()) > 20
                ]
                for sent in sentences:
                    scored.append((strength, sent))

        # Sort by strength descending, return top anchors
        scored.sort(key=lambda x: x[0], reverse=True)
        return [sent for _, sent in scored[:10]]
