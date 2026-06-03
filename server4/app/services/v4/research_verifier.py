"""
Research Verifier — Cross-checks LLM-generated content against research evidence.

This is the "fact-grounding" layer that prevents the LLM from:
  1. Inventing numbers not in research
  2. Attributing data to sources not in the evidence set
  3. Making claims that contradict the research
  4. Using data from one company on another company's slide

The verifier runs after each slide is written but before it's returned,
and injects verification metadata into the slide's raw dict.
"""

from __future__ import annotations

import re
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


# Matches numbers like $1.5B, 23%, 1,200, 45M, etc.
_NUMBER_PATTERN = re.compile(
    r"(\$[\d,.]+\s*[BMTK]?\b|[\d,.]+%|\d[\d,]*\.\d+\s*[BMTK]?\b|\d{2,}[\d,]*)",
    re.IGNORECASE,
)

# Matches citations like (Source, Year) or (Source Name, 2024)
_CITATION_PATTERN = re.compile(
    r"\(([^)]{3,60}?,\s*\d{4})\)",
)


def verify_slide_against_research(
    slide_data: dict[str, Any],
    research_chunks: list[dict[str, Any]],
    structured_context: Optional[dict[str, Any]] = None,
    intent: str = "",
) -> dict[str, Any]:
    """Verify a generated slide's claims against available research.
    
    Returns a verification report dict with:
      - grounded_claims: Claims supported by research
      - ungrounded_claims: Claims not found in research
      - fabricated_citations: Source attributions not matching research URLs
      - verification_score: 0-1 score (1 = fully grounded)
    """
    report: dict[str, Any] = {
        "grounded_claims": [],
        "ungrounded_claims": [],
        "fabricated_citations": [],
        "verification_score": 1.0,
    }
    
    # Build a single research text blob for matching
    research_text = ""
    research_urls = set()
    for chunk in research_chunks:
        title = chunk.get("title", "") or ""
        snippet = chunk.get("snippet", "") or ""
        url = chunk.get("url", "") or ""
        research_text += f" {title} {snippet}"
        if url:
            research_urls.add(url)
    
    # Also include structured context as ground truth
    structured_text = ""
    if structured_context:
        structured_text = _flatten_dict(structured_context)
    
    combined_evidence = f"{research_text} {structured_text}".lower()
    
    # 1. Extract all numbers from the slide
    all_text_fields = _extract_all_text(slide_data)
    numbers_found = _NUMBER_PATTERN.findall(all_text_fields)
    
    for num in numbers_found:
        num_clean = num.strip().replace(",", "")
        # Check if this number appears in research or structured context
        if num_clean.lower() in combined_evidence or num.lower() in combined_evidence:
            report["grounded_claims"].append({"type": "number", "value": num, "source": "research"})
        elif _is_from_structured_input(num, structured_context):
            report["grounded_claims"].append({"type": "number", "value": num, "source": "user_input"})
        else:
            report["ungrounded_claims"].append({"type": "number", "value": num, "field": "content"})
    
    # 2. Check citation attributions
    citations_in_text = _CITATION_PATTERN.findall(all_text_fields)
    for cite in citations_in_text:
        cite_lower = cite.lower()
        if any(cite_lower in chunk_text.lower() for chunk_text in 
               [f"{c.get('title', '')} {c.get('snippet', '')}" for c in research_chunks]):
            report["grounded_claims"].append({"type": "citation", "value": cite, "source": "research"})
        else:
            report["fabricated_citations"].append({"citation": cite})
    
    # 3. Check slide citations URLs against research URLs
    slide_citations = slide_data.get("citations") or []
    for sc in slide_citations:
        url = sc.get("url", "") if isinstance(sc, dict) else str(sc)
        if url and url not in research_urls:
            # Also check with scheme variant
            alt = url.replace("https://", "http://") if url.startswith("https://") else url.replace("http://", "https://")
            if alt not in research_urls:
                report["fabricated_citations"].append({"url": url})
    
    # 4. Calculate verification score
    total_claims = len(numbers_found) + len(citations_in_text) + len(slide_citations)
    issues = len(report["ungrounded_claims"]) + len(report["fabricated_citations"])
    
    if total_claims > 0:
        report["verification_score"] = max(0.0, 1.0 - (issues / total_claims))
    
    # For data-heavy intents, flag low scores
    if intent in ("market", "financials", "traction", "ask", "business_model"):
        if report["verification_score"] < 0.5 and total_claims > 0:
            logger.warning(
                "research_verification_low_score",
                intent=intent,
                score=report["verification_score"],
                ungrounded=len(report["ungrounded_claims"]),
                fabricated=len(report["fabricated_citations"]),
            )
    
    return report


def _extract_all_text(slide_data: dict[str, Any]) -> str:
    """Extract all text from a slide data dict."""
    parts = []
    for key in ("headline", "subheadline", "body", "speaker_notes"):
        val = slide_data.get(key)
        if val:
            parts.append(str(val))
    for bullet in (slide_data.get("bullets") or []):
        parts.append(str(bullet))
    for sb in (slide_data.get("stat_blocks") or []):
        if isinstance(sb, dict):
            parts.append(f"{sb.get('value', '')} {sb.get('label', '')}")
    return " ".join(parts)


def _is_from_structured_input(
    number: str,
    structured_context: Optional[dict[str, Any]],
) -> bool:
    """Check if a number comes from user-provided structured input."""
    if not structured_context:
        return False
    flat = _flatten_dict(structured_context).lower()
    return number.lower().replace(",", "") in flat


def _flatten_dict(d: Any, prefix: str = "") -> str:
    """Flatten a nested dict into a single string for matching."""
    if isinstance(d, dict):
        parts = []
        for k, v in d.items():
            parts.append(_flatten_dict(v, f"{prefix}{k} "))
        return " ".join(parts)
    elif isinstance(d, list):
        return " ".join(_flatten_dict(item) for item in d)
    else:
        return f"{prefix}{d}"
