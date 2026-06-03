"""Research synthesizer - converts raw web research into clean, synthesized facts.

This module implements the intermediate synthesis step recommended by the CEO:
- research_collector → research_synthesizer (turns raw web text into bulleted facts) → parallel_writer

The synthesizer removes webpage titles, URLs, SEO descriptions, and other artifacts
that cause the LLM to copy-paste raw search results instead of writing original copy.
"""

import re
from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.v4.research_collector import Citation, ResearchPacket


@dataclass
class SynthesizedFact:
    """A single synthesized fact from research."""
    text: str
    source: str
    relevance_score: float = 0.0


@dataclass
class SynthesizedResearch:
    """Synthesized research packet ready for writer consumption."""
    facts: list[SynthesizedFact]
    market_insights: list[str]
    competitive_landscape: list[str]
    industry_trends: list[str]
    user_query: str
    company_name: Optional[str]


def _clean_webpage_title(title: str) -> str:
    """Remove webpage artifacts from titles."""
    if not title:
        return ""
    
    # Remove common webpage separators
    title = re.sub(r"\s*[|–-]\s.*$", "", title)  # Remove " - Site Name" suffix
    title = re.sub(r"\s*\|\s.*$", "", title)  # Remove " | Site Name" suffix
    
    # Remove SEO patterns
    title = re.sub(r"\s*\|\s.*Blog.*$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*\|\s.*News.*$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*\|\s.*Article.*$", "", title, flags=re.IGNORECASE)
    
    return title.strip()


def _is_webpage_artifact(text: str) -> bool:
    """Check if text is a webpage artifact (title, URL, SEO description)."""
    if not text:
        return False
    
    # Check for URLs
    if re.search(r"https?://", text):
        return True
    
    # Check for webpage title patterns (dash-separated, pipe-separated)
    if re.search(r"\s*[|–-]\s", text):
        return True
    
    # Check for SEO patterns
    if re.search(r"\|\s.*(Blog|News|Article|LinkedIn|Medium)", text, re.IGNORECASE):
        return True
    
    # Check for "How do people..." type questions (search queries)
    if re.search(r"^(How|What|Why|When|Where|Who) (do|does|is|are|can|will)", text):
        return True
    
    # Check for long title-case strings that look like article headlines
    # e.g. "Space Insurance Basics For Military Satellites"
    if len(text) > 60 and text.count(" ") >= 5:
        title_words = sum(1 for w in text.split() if w and w[0].isupper())
        if title_words / max(text.count(" "), 1) > 0.7:
            return True
    
    # Check for parenthetical site references like "(Aerospace and Defense)"
    if re.search(r"\([^)]*\.(com|org|net|io)[^)]*\)", text):
        return True
    
    return False


def _synthesize_citation(citation: "Citation") -> list[SynthesizedFact]:
    """Synthesize a single citation into clean facts."""
    facts = []
    
    # Clean the title
    clean_title = _clean_webpage_title(citation.title or "")
    
    # Extract facts from snippet (avoid webpage artifacts)
    if citation.snippet and not _is_webpage_artifact(citation.snippet):
        # Split snippet into sentences
        sentences = re.split(r"(?<=[.!?])\s+", citation.snippet.strip())
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and not _is_webpage_artifact(sentence):
                facts.append(SynthesizedFact(
                    text=sentence,
                    source=citation.source or "Unknown",
                    relevance_score=citation.rank_score
                ))
    
    # Also use cleaned title if it's substantive
    if clean_title and len(clean_title) > 20 and not _is_webpage_artifact(clean_title):
        facts.append(SynthesizedFact(
            text=clean_title,
            source=citation.source or "Unknown",
            relevance_score=citation.rank_score
        ))
    
    return facts


def synthesize_research(packet: "ResearchPacket") -> SynthesizedResearch:
    """Synthesize raw research packet into clean facts for writer consumption.
    
    This function implements the CEO's recommended synthesis step:
    - Removes webpage titles, URLs, and SEO descriptions
    - Converts raw search results into bulleted facts
    - Prevents LLM from copy-pasting raw research
    """
    all_facts: list[SynthesizedFact] = []
    
    # Synthesize all citations
    for citation in packet.citations + packet.news_citations:
        facts = _synthesize_citation(citation)
        all_facts.extend(facts)
    
    # Sort by relevance score
    all_facts.sort(key=lambda f: f.relevance_score, reverse=True)
    
    # Categorize facts (simple keyword-based categorization)
    market_insights = []
    competitive_landscape = []
    industry_trends = []
    
    for fact in all_facts[:20]:  # Top 20 facts
        text_lower = fact.text.lower()
        
        if any(kw in text_lower for kw in ["market", "tam", "sam", "som", "demand", "opportunity"]):
            market_insights.append(fact.text)
        elif any(kw in text_lower for kw in ["competitor", "alternative", "vs", "versus", "different"]):
            competitive_landscape.append(fact.text)
        elif any(kw in text_lower for kw in ["trend", "growth", "shift", "emerging", "future"]):
            industry_trends.append(fact.text)
    
    return SynthesizedResearch(
        facts=all_facts[:30],  # Top 30 facts
        market_insights=market_insights[:10],
        competitive_landscape=competitive_landscape[:10],
        industry_trends=industry_trends[:10],
        user_query=packet.query,
        company_name=packet.company_name,
    )


def as_prompt_context(synthesized: SynthesizedResearch, max_chars: int = 3000) -> str:
    """Format synthesized research as a clean context block for LLM prompts.
    
    This format prevents the LLM from seeing raw webpage titles and URLs,
    reducing the likelihood of copy-pasting artifacts.
    """
    lines = []
    
    if synthesized.market_insights:
        lines.append("MARKET INSIGHTS:")
        for insight in synthesized.market_insights[:5]:
            lines.append(f"- {insight}")
        lines.append("")
    
    if synthesized.competitive_landscape:
        lines.append("COMPETITIVE LANDSCAPE:")
        for fact in synthesized.competitive_landscape[:5]:
            lines.append(f"- {fact}")
        lines.append("")
    
    if synthesized.industry_trends:
        lines.append("INDUSTRY TRENDS:")
        for trend in synthesized.industry_trends[:5]:
            lines.append(f"- {trend}")
        lines.append("")
    
    if synthesized.facts:
        lines.append("ADDITIONAL FACTS:")
        for fact in synthesized.facts[:10]:
            lines.append(f"- {fact.text}")
        lines.append("")
    
    text = "\n".join(lines)
    return text[:max_chars]
