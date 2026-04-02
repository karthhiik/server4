"""
Quality guard pipeline — validates generated slide content before returning.
Catches fluff, missing sources, density violations, and investor-readiness issues.
"""

import re
from typing import Optional

import structlog

logger = structlog.get_logger()

# ── Fluff words that signal weak writing ────────────────────
FLUFF_WORDS = [
    "revolutionary", "disruptive", "cutting-edge", "best-in-class",
    "world-class", "game-changer", "synergy", "holistic", "leverage",
    "paradigm shift", "next-generation", "state-of-the-art", "scalable solution",
    "innovative", "groundbreaking", "seamless", "robust",
    "empower", "unlock", "supercharge",
]

# Compiled regex for performance
FLUFF_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(w) for w in FLUFF_WORDS) + r')\b',
    re.IGNORECASE,
)

# Numbers that need sources (anything $1M+ or percentages claiming market data)
UNSOURCED_CLAIM_PATTERN = re.compile(
    r'(?:\$[\d,.]+\s*[BMTbmt](?:illion)?|\d+(?:\.\d+)?%\s*(?:CAGR|growth|market|revenue|increase|decrease))',
    re.IGNORECASE,
)

SOURCE_INDICATORS = [
    "(", "source:", "according to", "per ", "based on", "data from",
    "report", "research", "survey", "study", "internal data",
    "McKinsey", "Gartner", "Forrester", "Statista", "Grand View",
    "CB Insights", "PitchBook", "Crunchbase",
]


class QualityGuardResult:
    """Result of running quality guards on content."""

    def __init__(self):
        self.passed = True
        self.warnings: list[str] = []
        self.fluff_found: list[str] = []
        self.unsourced_claims: list[str] = []
        self.density_issues: list[str] = []
        self.investor_issues: list[str] = []

    @property
    def has_issues(self) -> bool:
        return bool(self.warnings or self.fluff_found or self.unsourced_claims
                     or self.density_issues or self.investor_issues)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "warnings": self.warnings,
            "fluff_found": self.fluff_found,
            "unsourced_claims": self.unsourced_claims,
            "density_issues": self.density_issues,
            "investor_issues": self.investor_issues,
        }


def run_quality_guards(
    content: dict,
    layout: str = "",
    purpose: str = "",
    is_investor_deck: bool = False,
) -> QualityGuardResult:
    """Run all quality guards on slide content. Returns QualityGuardResult."""
    result = QualityGuardResult()

    fluff_check(content, result)
    slide_density_check(content, layout, result)
    claim_source_check(content, result)

    if is_investor_deck:
        investor_readiness_check(content, layout, purpose, result)

    if result.has_issues:
        result.passed = False
        logger.info(
            "quality_guard_flagged",
            fluff=len(result.fluff_found),
            unsourced=len(result.unsourced_claims),
            density=len(result.density_issues),
            investor=len(result.investor_issues),
        )

    return result


def fluff_check(content: dict, result: QualityGuardResult) -> None:
    """Detect fluff words that weaken pitch deck content."""
    text = _extract_text(content)
    matches = FLUFF_PATTERN.findall(text)
    if matches:
        unique = list(set(m.lower() for m in matches))
        result.fluff_found = unique
        result.warnings.append(
            f"Fluff detected: {', '.join(unique)}. Replace with concrete language."
        )


def slide_density_check(content: dict, layout: str, result: QualityGuardResult) -> None:
    """Check that slide content fits reasonable density constraints."""
    title = content.get("title", "")
    if title and len(title.split()) > 10:
        result.density_issues.append(f"Title too long ({len(title.split())} words). Target 3-8 words.")

    bullets = content.get("bullets", [])
    if bullets:
        if len(bullets) > 6:
            result.density_issues.append(f"Too many bullets ({len(bullets)}). Max 6 per slide.")
        for i, b in enumerate(bullets):
            words = len(str(b).split())
            if words > 20:
                result.density_issues.append(f"Bullet {i+1} too long ({words} words). Target ≤15 words.")

    body = content.get("body_text", "")
    if body and len(body.split()) > 60:
        result.density_issues.append(f"Body text too long ({len(body.split())} words). Slides ≠ documents.")

    left = content.get("left_content", "")
    right = content.get("right_content", "")
    for side, text in [("Left column", left), ("Right column", right)]:
        if text and len(str(text).split()) > 50:
            result.density_issues.append(f"{side} too dense ({len(str(text).split())} words).")


def claim_source_check(content: dict, result: QualityGuardResult) -> None:
    """Check that large numeric claims have source attribution."""
    text = _extract_text(content)
    claims = UNSOURCED_CLAIM_PATTERN.findall(text)

    for claim in claims:
        # Check if there's a source indicator near this claim
        claim_pos = text.lower().find(claim.lower())
        if claim_pos < 0:
            continue
        # Look within 200 chars after the claim for a source
        context_after = text[claim_pos:claim_pos + 200].lower()
        has_source = any(indicator.lower() in context_after for indicator in SOURCE_INDICATORS)
        if not has_source:
            result.unsourced_claims.append(claim)

    if result.unsourced_claims:
        result.warnings.append(
            f"Unsourced claims: {', '.join(result.unsourced_claims)}. Add source attribution."
        )


def investor_readiness_check(
    content: dict, layout: str, purpose: str, result: QualityGuardResult
) -> None:
    """Check investor-specific quality requirements."""
    purpose_lower = purpose.lower()

    # Traction slides must show trajectory
    if "traction" in purpose_lower:
        if layout not in ("chart", "kpi-dashboard"):
            result.investor_issues.append(
                "Traction should use chart layout to show trajectory (graph going up-right)."
            )
        chart_data = content.get("chart_data", {})
        if layout == "chart" and not chart_data:
            result.investor_issues.append("Traction chart slide has no chart data.")

    # Market slides must have TAM/SAM/SOM
    if "market" in purpose_lower and ("opportunity" in purpose_lower or "size" in purpose_lower):
        text = _extract_text(content).lower()
        has_tam = "tam" in text or "total addressable" in text
        has_sam = "sam" in text or "serviceable addressable" in text
        has_som = "som" in text or "serviceable obtainable" in text
        if not (has_tam and has_sam):
            result.investor_issues.append(
                "Market slide should include TAM/SAM/SOM breakdown."
            )

    # Ask slides must have use-of-funds
    if "ask" in purpose_lower or "funding" in purpose_lower:
        text = _extract_text(content).lower()
        has_amount = "$" in text or "raise" in text or "funding" in text
        has_use = "hire" in text or "engineering" in text or "marketing" in text or "use of funds" in text
        if has_amount and not has_use:
            result.investor_issues.append(
                "Ask slide has a funding amount but no use-of-funds breakdown."
            )

    # Competition slides should not say "no competitors"
    if "compet" in purpose_lower:
        text = _extract_text(content).lower()
        if "no direct competitor" in text or "no competitor" in text:
            result.investor_issues.append(
                "Never say 'no competitors.' Position on a comparison matrix instead."
            )


def consistency_check(slides: list[dict]) -> list[str]:
    """Check cross-slide consistency (company name, numbers, tense)."""
    issues = []

    # Extract all company-name-like references
    company_names = set()
    for slide in slides:
        text = _extract_text(slide.get("content", {}))
        # Look for title-case multi-word phrases that appear in title positions
        title = slide.get("content", {}).get("title", "")
        if title and title[0].isupper():
            company_names.add(title.strip())

    # Check for number contradictions across slides
    # (basic: collect all dollar amounts and check for impossible combinations)
    all_revenue_mentions = []
    for slide in slides:
        text = _extract_text(slide.get("content", {}))
        revenue_matches = re.findall(r'\$[\d,.]+[KMBkmb]?\s*(?:MRR|ARR|revenue)', text, re.IGNORECASE)
        all_revenue_mentions.extend(revenue_matches)

    if len(all_revenue_mentions) > 1:
        # Just flag for manual review if multiple revenue figures
        unique_amounts = list(set(all_revenue_mentions))
        if len(unique_amounts) > 2:
            issues.append(
                f"Multiple revenue figures found across slides: {', '.join(unique_amounts)}. Verify consistency."
            )

    return issues


def _extract_text(content: dict) -> str:
    """Extract all text from slide content for analysis."""
    parts = []
    for key in ["title", "subtitle", "body_text", "left_content", "right_content",
                 "quote_text", "caption", "source_attribution"]:
        val = content.get(key)
        if val and isinstance(val, str):
            parts.append(val)

    for key in ["bullets", "left_items", "right_items"]:
        items = content.get(key)
        if items and isinstance(items, list):
            parts.extend(str(item) for item in items)

    for member in content.get("members", []):
        if isinstance(member, dict):
            parts.extend(str(v) for v in member.values())

    for metric in content.get("metrics", []):
        if isinstance(metric, dict):
            parts.extend(str(v) for v in metric.values())

    for event in content.get("events", []):
        if isinstance(event, dict):
            parts.extend(str(v) for v in event.values())

    return " ".join(parts)
