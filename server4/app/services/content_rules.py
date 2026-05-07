import re
from typing import Dict, List, Optional, Any

# -----------------------------------------------------------------------------
# BANNED PATTERNS
# -----------------------------------------------------------------------------

BANNED_HEADLINES = [
    r"(?i)^investor pitch( overview)?$",
    r"(?i)^market opportunity( today)?$",
    r"(?i)^our business model$",
    r"(?i)^join our journey$",
    r"(?i)^the problem$",
    r"(?i)^the solution$",
    r"(?i)^our team$",
    r"(?i)^financial projections$",
    r"(?i)^competitive landscape$",
    r"(?i)^traction and milestones$",
    r"(?i)^go to market( strategy)?$",
    r"(?i)^our vision$",
    r"(?i)^our mission$"
]

BANNED_SUBHEADS = [
    r"(?i)^revolutionizing the .* industry$",
    r"(?i)^empowering .* to .*$",
    r"(?i)^the future of .*$",
    r"(?i)^disrupting the .* space$",
    r"(?i)^AI-powered .*$"
]

def is_generic_headline(text: str) -> bool:
    if not text:
        return False
    for pattern in BANNED_HEADLINES:
        if re.search(pattern, text.strip()):
            return True
    
    words = text.split()
    if len(words) <= 2 and text.lower() in [
        "market size", "business model", "the ask", "financials", "competition", "traction", "problem", "solution"
    ]:
        return True
    return False

def is_generic_subhead(text: str) -> bool:
    if not text:
        return False
    for pattern in BANNED_SUBHEADS:
        if re.search(pattern, text.strip()):
            return True
    return False

def check_template_risk(text: str) -> bool:
    """Returns True if the text reads like a generic template."""
    return is_generic_headline(text) or is_generic_subhead(text)


# -----------------------------------------------------------------------------
# DATA DENSITY RULES
# -----------------------------------------------------------------------------

REQUIRED_QUANT_SIGNALS = {
    "market": 3,
    "traction": 3,
    "financials": 3,
    "competition": 2,
    "ask": 2
}

def analyze_data_density(text: str) -> int:
    """Counts roughly how many quantitative signals (numbers, percentages, $, etc.) are in the text."""
    if not text:
        return 0
    # Matches $1M, 50%, 10x, 2,000 etc. Noticeably over-counts some, but works as heuristic.
    quant_pattern = r'(\$?\d+(?:,\d+)*(?:\.\d+)?[MBkK%xX]?)'
    matches = re.findall(quant_pattern, text)
    return len(matches)

def validate_traceability(trace: Dict[str, Any]) -> bool:
    """Checks if the trace object meets minimum traceability rules for investor decks."""
    if not trace:
        return False
    
    headline_sources = trace.get("headline_sources", [])
    claim_sources = trace.get("claim_sources", {})
    
    # Must have at least some attribution for core claims
    if not headline_sources and not claim_sources:
        return False
        
    return True
