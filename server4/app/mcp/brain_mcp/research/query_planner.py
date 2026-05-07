"""
Query planner — generates optimised sub-queries for each slide kind.

Uses LLM (Groq via ModelRouter, free tier) for query rewriting when
beneficial.  Falls back to template-based query generation at zero cost.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.mcp.brain_mcp.research.models import SlideKind

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# SLIDE-KIND → TEMPLATE QUERIES
# ═══════════════════════════════════════════════════════════════════════

_QUERY_TEMPLATES: dict[SlideKind, list[str]] = {
    SlideKind.title: [
        "{topic} company overview",
        "{topic} mission statement value proposition",
    ],
    SlideKind.problem: [
        "{topic} pain points user problems {sector_q}",
        "{topic} market challenges frustrated customers",
        "{topic} industry inefficiencies current solutions failing",
        "{topic} cost of problem status quo",
        "{topic} underserved market segment unmet needs",
    ],
    SlideKind.solution: [
        "{topic} solution approach product overview",
        "{topic} technology innovation differentiation",
        "{topic} how it works key features benefits",
        "{topic} user experience customer success stories",
        "{topic} competitive advantage moat",
    ],
    SlideKind.market: [
        "{topic} market size TAM SAM SOM {year}",
        "{topic} industry CAGR growth rate forecast",
        "{topic} market trends {sector_q} {year}",
        "{topic} addressable market opportunity revenue potential",
        "{topic} industry report market research {sector_q}",
    ],
    SlideKind.competition: [
        "{topic} competitors competitive landscape {sector_q}",
        "{topic} market share top companies comparison",
        "{topic} competitive analysis strengths weaknesses",
        "{topic} alternative solutions competitor funding raised",
        "{topic} feature comparison pricing benchmark",
    ],
    SlideKind.gtm: [
        "{topic} go to market strategy customer acquisition",
        "{topic} sales channels distribution strategy",
        "{topic} marketing strategy growth hacking {sector_q}",
        "{topic} customer acquisition cost CAC LTV unit economics",
        "{topic} partnership strategy channel partners",
    ],
    SlideKind.traction: [
        "{topic} traction metrics revenue growth users",
        "{topic} customer testimonials case studies",
        "{topic} key milestones achievements",
        "{topic} month over month growth rate MRR ARR",
        "{topic} social proof press coverage awards",
    ],
    SlideKind.financial: [
        "{topic} financial projections revenue forecast {year}",
        "{topic} comparable company valuation multiples {sector_q}",
        "{topic} unit economics gross margin burn rate",
        "{topic} SaaS benchmarks industry financial ratios {sector_q}",
        "{topic} funding rounds startup valuation {sector_q}",
    ],
    SlideKind.team: [
        "{topic} founders team background experience",
        "{topic} leadership team advisors board members",
    ],
    SlideKind.ask: [
        "{topic} funding round investment terms {sector_q}",
        "{topic} use of proceeds capital allocation plan",
        "{topic} startup funding benchmarks {sector_q} {year}",
        "{topic} comparable raises seed Series A {sector_q}",
    ],
    SlideKind.why_now: [
        "{topic} market timing why now opportunity",
        "{topic} regulatory changes technology shift enabling {sector_q}",
        "{topic} macro trends tailwinds {year} {sector_q}",
        "{topic} inflection point catalyst industry disruption",
        "{topic} COVID digital transformation acceleration {sector_q}",
    ],
    SlideKind.product_demo: [
        "{topic} product demo features user interface",
        "{topic} product walkthrough screenshots workflow",
        "{topic} user experience design product highlights",
    ],
    SlideKind.appendix: [
        "{topic} detailed financials assumptions",
        "{topic} market research methodology sources",
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# PROVIDER-SPECIFIC QUERY FORMATTING
# ═══════════════════════════════════════════════════════════════════════

_PROVIDER_STYLES: dict[str, str] = {
    # Serper / SerpAPI → keyword-heavy, concise
    "serper":   "keywords",
    "serpapi":  "keywords",
    # Tavily / Exa → natural-language questions
    "tavily":   "natural_language",
    "exa":      "natural_language",
    # You.com → natural language with specifics
    "you_com":  "natural_language",
    "search_api": "keywords",
    # News → event-oriented
    "newsapi":  "news",
    "newsdata": "news",
    "guardian":  "news",
    "world_news": "news",
    # Academic → paper titles / concepts
    "core": "academic",
}


# ═══════════════════════════════════════════════════════════════════════
# LLM REWRITE PROMPT
# ═══════════════════════════════════════════════════════════════════════

_REWRITE_SYSTEM_PROMPT = (
    "You are a search-query optimiser. Given an original search query "
    "and a target provider style, rewrite the query to maximise recall "
    "and precision for that provider. Reply ONLY with the rewritten query "
    "(one line, no explanation)."
)


class QueryPlanner:
    """
    Generates optimised sub-queries for each slide and evidence type.

    Uses LLM (Groq, free) for query rewriting when beneficial.
    Falls back to template-based query generation.
    """

    def __init__(self, model_router: Any = None) -> None:
        self._router = model_router

    # ── Main entry point ────────────────────────────────────────

    async def plan_queries(
        self,
        topic: str,
        description: str,
        slide_kind: SlideKind,
        audience: str = "investors",
        sector: Optional[str] = None,
    ) -> list[str]:
        """Generate optimised search queries for a specific slide type.

        1. Start with template-based queries (zero cost).
        2. Optionally rewrite 1-2 via LLM for extra precision.
        """
        templates = self._template_queries(topic, slide_kind, sector)

        if not templates:
            # Fallback: construct a generic query from the topic
            templates = [
                f"{topic} {slide_kind.value} {audience}",
                f"{topic} {description[:60]}",
            ]

        # Try LLM rewrite for the first query to add a high-quality variant
        if self._router is not None and templates:
            try:
                rewritten = await self.rewrite_query(
                    templates[0], target_provider="tavily",
                )
                if rewritten and rewritten != templates[0]:
                    templates.append(rewritten)
            except Exception as exc:
                logger.debug("LLM query rewrite skipped: %s", exc)

        return templates

    # ── Template-based query generation ─────────────────────────

    def _template_queries(
        self,
        topic: str,
        slide_kind: SlideKind,
        sector: Optional[str],
    ) -> list[str]:
        """Template-based query generation (zero-cost fallback).

        Replaces {topic}, {sector_q}, and {year} placeholders.
        """
        raw_templates = _QUERY_TEMPLATES.get(slide_kind, [])
        if not raw_templates:
            return [f"{topic} {slide_kind.value}"]

        import datetime as _dt
        current_year = str(_dt.date.today().year)
        sector_q = sector if sector else ""

        queries: list[str] = []
        for tpl in raw_templates:
            q = (
                tpl
                .replace("{topic}", topic)
                .replace("{sector_q}", sector_q)
                .replace("{year}", current_year)
            )
            # Clean up double spaces from empty placeholders
            q = " ".join(q.split())
            queries.append(q)

        return queries

    # ── LLM-powered query rewriting ─────────────────────────────

    async def rewrite_query(
        self,
        original: str,
        target_provider: str,
    ) -> str:
        """Rewrite a query for a specific provider's strengths.

        Uses Groq (free tier) via the ModelRouter.  Returns original
        unchanged if LLM is unavailable.
        """
        if self._router is None:
            return self._provider_query_format(original, target_provider)

        style = _PROVIDER_STYLES.get(target_provider, "keywords")
        user_prompt = (
            f"Original query: {original}\n"
            f"Target style: {style}\n"
            f"Provider: {target_provider}\n"
            f"Rewrite the query."
        )

        try:
            from app.services.llm.model_router import TaskType

            response = await self._router.complete(
                task_type=TaskType.TRANSLATION_QUICK_EDIT,
                messages=[
                    {"role": "system", "content": _REWRITE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=128,
            )
            rewritten = response.content.strip()
            if rewritten:
                logger.debug(
                    "Query rewritten: '%s' → '%s' (provider=%s)",
                    original[:60],
                    rewritten[:60],
                    target_provider,
                )
                return rewritten
        except Exception as exc:
            logger.debug("LLM rewrite failed, using format fallback: %s", exc)

        return self._provider_query_format(original, target_provider)

    # ── Provider-specific formatting ────────────────────────────

    @staticmethod
    def _provider_query_format(query: str, provider: str) -> str:
        """Format a query for a specific provider's API expectations."""
        style = _PROVIDER_STYLES.get(provider, "keywords")

        if style == "keywords":
            # Strip filler words, keep nouns/concepts
            filler = {
                "the", "a", "an", "is", "are", "was", "were", "be",
                "been", "being", "and", "or", "but", "in", "on", "at",
                "to", "for", "of", "with", "by", "from", "as", "into",
                "about", "what", "how", "why", "when", "where", "which",
                "that", "this", "it", "its", "do", "does", "did", "has",
                "have", "had", "can", "could", "will", "would", "shall",
                "should", "may", "might",
            }
            words = query.split()
            keywords = [w for w in words if w.lower() not in filler]
            return " ".join(keywords) if keywords else query

        if style == "natural_language":
            # Ensure it reads as a question / full sentence
            q = query.strip()
            if not q.endswith("?"):
                q = f"What are the key facts about {q}?"
            return q

        if style == "news":
            # Add recency signals
            return f"{query} latest news recent developments"

        if style == "academic":
            # Add scholarly terms
            return f"{query} research study findings peer reviewed"

        return query
