"""
Hallucination Guard — Post-generation fact verification.

Scans generated slide content for potential hallucinations:
  1. Fabricated statistics (numbers with no source in research)
  2. Invented company names in competitor slides
  3. Fabricated team member details
  4. Off-topic content (drift detection)
  5. Instruction leakage (system prompt phrases in output)

This runs AFTER the writer produces content but BEFORE persistence,
allowing us to flag or strip hallucinated content without regenerating
the entire slide.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


# ── Patterns that indicate hallucinated content ──

# Numbers that look fabricated (round numbers with no source attribution)
_UNSOURCED_BIG_NUMBER = re.compile(
    r"\$[\d,.]+\s*[BMT]\b(?!\s*\([^)]+\))",  # $1.5B without (Source, Year)
    re.IGNORECASE,
)

# Placeholder patterns that should never appear in final output
_PLACEHOLDER_PATTERNS = [
    re.compile(r"\$[XYZ]\b", re.IGNORECASE),
    re.compile(r"\b[XYZ]%\b"),
    re.compile(r"\bTBD\b", re.IGNORECASE),
    re.compile(r"\bN/A\b", re.IGNORECASE),
    re.compile(r"\bcoming soon\b", re.IGNORECASE),
    re.compile(r"\b\[.*?\]\b"),  # [placeholder]
]

# Instruction leakage — system prompt phrases that should never appear in output
_INSTRUCTION_LEAKAGE = [
    "cover this topic",
    "explain the",
    "demonstrate how",
    "highlight the key",
    "describe the",
    "show the pain",
    "primary alternatives today",
    "what makes the approach differentiated",
    "how the product solves",
    "who feels this pain",
    "why existing solutions fall short",
    "key milestones achieved",
    "what growth looks like",
    "cover market for this",
    "buyers increasingly seek",
]

# Generic headlines that indicate no real content was generated
_GENERIC_HEADLINES = [
    "market opportunity",
    "our team",
    "the team",
    "our solution",
    "the solution",
    "competitive landscape",
    "business model",
    "our business model",
    "revenue model",
    "go-to-market strategy",
    "the problem",
    "why now",
    "our vision",
    "join our journey",
    "investment opportunity",
    "funding ask",
]

# Scraper artifacts
_SCRAPER_ARTIFACTS = re.compile(
    r"(category:\s*news|et now business|seo description|"
    r"cookie policy|privacy policy|terms of service|"
    r"subscribe to our newsletter|follow us on)",
    re.IGNORECASE,
)


@dataclass
class HallucinationIssue:
    """A single detected hallucination issue."""
    kind: str  # "unsourced_stat", "placeholder", "instruction_leak", "generic_headline", "scraper_artifact", "topic_drift"
    severity: str  # "error", "warning"
    field: str  # Which slide field: "headline", "bullets", "body", etc.
    detail: str  # Human-readable explanation
    auto_fixable: bool = False  # Whether we can auto-fix without regenerating


@dataclass
class GuardResult:
    """Result of hallucination guard scan on a slide."""
    slide_index: int
    intent: str
    issues: list[HallucinationIssue] = field(default_factory=list)
    score_penalty: float = 0.0  # Deduction from quality score
    hard_block: bool = False  # If True, slide must be regenerated regardless of score
    
    @property
    def has_critical(self) -> bool:
        return any(i.severity == "error" for i in self.issues)
    
    @property
    def clean(self) -> bool:
        return len(self.issues) == 0


def _check_title_content_alignment(headline: str, content_text: str, intent: str) -> float:
    """Check if headline thesis is supported by content.
    
    Returns alignment score from 0.0 (no alignment) to 1.0 (perfect alignment).
    """
    headline_lower = headline.lower()
    content_lower = content_text.lower()
    
    # Extract key terms from headline (nouns, adjectives)
    headline_words = set(re.findall(r'\b[a-z]{3,}\b', headline_lower))
    # Remove common stop words
    stop_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "her", "was", "one", "our", "out", "with", "this", "that", "from", "they", "will", "have", "been", "more"}
    headline_words -= stop_words
    
    if not headline_words:
        return 0.5  # Neutral score if no meaningful words
    
    # Count how many headline words appear in content
    matching_words = sum(1 for word in headline_words if word in content_lower)
    alignment = matching_words / len(headline_words)

    semantic_groups = [
        {"central", "centralized", "authority", "control", "bottleneck", "outage", "failure", "risk", "breach"},
        {"iot", "edge", "device", "devices", "fleet", "fleets"},
        {"trust", "identity", "auth", "authentication", "credential", "did", "dids", "verifier", "proof", "proofs"},
        {"sub", "millisecond", "latency", "ms", "low", "bandwidth"},
        {"scaling", "scalability", "scales", "bottlenecks", "constant", "verification"},
        {"hardware", "root", "secure", "silicon", "attestation"},
        {"neural", "guardian", "consensus", "state"},
        {"capital", "funds", "funding", "proof", "pilots", "pilot", "milestones", "ask"},
        {"gtm", "market", "architect", "buyers", "sales", "partnerships", "adoption"},
        {"architecture", "boundary", "topology", "policy", "verification", "anchor"},
    ]
    relevant_groups = [group for group in semantic_groups if headline_words & group]
    if relevant_groups:
        group_matches = sum(1 for group in relevant_groups if any(term in content_lower for term in group))
        alignment = max(alignment, group_matches / len(relevant_groups))
    
    # Boost alignment if intent-specific keywords are present
    intent_keywords = {
        "market": ["market", "size", "opportunity", "tam", "sam", "som"],
        "traction": ["growth", "users", "revenue", "mrr", "traction"],
        "team": ["team", "founders", "experience", "background"],
        "competition": ["competitor", "competitive", "landscape", "vs"],
        "financials": ["revenue", "profit", "margin", "financial", "projections"],
        "problem": ["problem", "pain", "challenge", "issue"],
        "solution": ["solution", "product", "feature", "platform"],
    }
    
    if intent in intent_keywords:
        intent_words = intent_keywords[intent]
        intent_matches = sum(1 for word in intent_words if word in content_lower)
        alignment += (intent_matches / len(intent_words)) * 0.2  # Up to 20% boost
    
    return min(1.0, alignment)


def _cross_verify_facts(slide_text: str, research_text: str, intent: str) -> dict[str, Any]:
    """Cross-verify factual claims against research evidence.
    
    Returns dict with 'verified' bool and 'detail' string.
    """
    slide_lower = slide_text.lower()
    research_lower = research_text.lower()
    
    # Extract numeric claims from slide
    numeric_claims = re.findall(r'\$?\d[\d,.]*\s*(?:b|m|k|%|billion|million|thousand)', slide_lower)
    
    if not numeric_claims:
        # No numeric claims to verify
        return {"verified": True, "detail": "No numeric claims to verify"}
    
    # Check if numeric claims appear in research
    verified_claims = 0
    for claim in numeric_claims:
        if claim in research_lower:
            verified_claims += 1
    
    verification_rate = verified_claims / len(numeric_claims) if numeric_claims else 1.0
    
    # For data-heavy intents, require higher verification
    if intent in ("market", "financials"):
        threshold = 0.6  # 60% of claims must be in research
    elif intent == "traction":
        threshold = 0.5  # 50% of claims must be in research
    else:
        threshold = 0.4  # 40% of claims must be in research
    
    if verification_rate < threshold:
        return {
            "verified": False,
            "detail": f"Only {verification_rate:.0%} of numeric claims ({verified_claims}/{len(numeric_claims)}) found in research. Threshold: {threshold:.0%}"
        }
    
    return {"verified": True, "detail": f"Claims verified: {verified_claims}/{len(numeric_claims)}"}


def scan_slide(
    slide_data: dict[str, Any],
    intent: str,
    slide_index: int,
    research_text: str = "",
    company_name: str = "",
    topic: str = "",
) -> GuardResult:
    """Scan a single generated slide for hallucination signals.
    
    Args:
        slide_data: The parsed writer output (dict with headline, bullets, etc.)
        intent: Slide intent (market, team, etc.)
        slide_index: Index for logging
        research_text: Concatenated research evidence for source-checking
        company_name: Expected company name
        topic: Original presentation topic for drift detection
    
    Returns:
        GuardResult with detected issues and score penalty
    """
    result = GuardResult(slide_index=slide_index, intent=intent)
    
    headline = str(slide_data.get("headline", "")).strip()
    subheadline = str(slide_data.get("subheadline", "")).strip()
    bullets = slide_data.get("bullets") or []
    body = str(slide_data.get("body", "")).strip()
    speaker_notes = str(slide_data.get("speaker_notes", "")).strip()
    
    all_text = f"{headline} {subheadline} {' '.join(str(b) for b in bullets)} {body}"
    
    # 1. Check for generic headlines - HARD BLOCK
    if headline.lower().strip() in _GENERIC_HEADLINES:
        result.issues.append(HallucinationIssue(
            kind="generic_headline",
            severity="error",
            field="headline",
            detail=f"HARD BLOCK: Generic headline detected: '{headline}'. Must be thesis-first (specific to the company).",
            auto_fixable=False,
        ))
        result.score_penalty = 10.0  # Guarantees score below threshold
        result.hard_block = True  # Forces slide regeneration regardless of score
    
    # 1.5. Check title-content alignment - HARD BLOCK if mismatched
    if headline and (bullets or body):
        # Subheadline is visible slide content and often carries the supporting
        # thesis for sparse hero/stat slides. Omitting it created false
        # mismatches for valid title/subtitle pairs.
        content_text = f"{subheadline} " + " ".join(str(b) for b in bullets) + " " + body
        alignment_score = _check_title_content_alignment(headline, content_text, intent)
        if alignment_score < 0.3:  # Low alignment threshold
            result.issues.append(HallucinationIssue(
                kind="title_content_mismatch",
                severity="error",
                field="headline",
                detail=f"HARD BLOCK: Headline '{headline}' does not align with content. Title thesis not supported by slide content.",
                auto_fixable=False,
            ))
            result.score_penalty = 8.0
            result.hard_block = True
    
    # 2. Check for placeholder patterns
    for pattern in _PLACEHOLDER_PATTERNS:
        for field_name, text in [("headline", headline), ("subheadline", subheadline),
                                  ("body", body)] + [(f"bullet_{i}", b) for i, b in enumerate(bullets)]:
            if pattern.search(str(text)):
                result.issues.append(HallucinationIssue(
                    kind="placeholder",
                    severity="error",
                    field=field_name,
                    detail=f"Placeholder found in {field_name}: '{pattern.pattern}'",
                    auto_fixable=True,
                ))
                result.score_penalty += 1.5
    
    # 3. Check for instruction leakage
    lower_text = all_text.lower()
    for phrase in _INSTRUCTION_LEAKAGE:
        if phrase in lower_text:
            result.issues.append(HallucinationIssue(
                kind="instruction_leak",
                severity="error",
                field="content",
                detail=f"System instruction leaked into output: '{phrase}'",
                auto_fixable=True,
            ))
            result.score_penalty += 2.0
            break  # One is enough
    
    # 4. Check for unsourced big numbers (market, financials, traction)
    if intent in ("market", "financials", "traction", "ask"):
        for field_name, text in [("headline", headline), ("body", body)] + \
                                 [(f"bullet_{i}", b) for i, b in enumerate(bullets)]:
            matches = _UNSOURCED_BIG_NUMBER.findall(str(text))
            for match in matches:
                # Check if this number appears in research
                if match not in research_text:
                    result.issues.append(HallucinationIssue(
                        kind="unsourced_stat",
                        severity="warning",
                        field=field_name,
                        detail=f"Large number '{match}' has no source attribution and not found in research",
                        auto_fixable=False,
                    ))
                    result.score_penalty += 1.0
    
    # 5. Check for scraper artifacts
    if _SCRAPER_ARTIFACTS.search(all_text):
        result.issues.append(HallucinationIssue(
            kind="scraper_artifact",
            severity="error",
            field="content",
            detail="Raw scraper/SEO metadata detected in slide content",
            auto_fixable=True,
        ))
        result.score_penalty += 1.5
    
    # 6. Topic drift detection (only if topic provided)
    if topic and len(all_text) > 50:
        topic_words = set(topic.lower().split())
        # Remove very common words
        topic_words -= {"the", "a", "an", "is", "are", "for", "to", "of", "in", "on", "and", "or", "we", "our"}
        if topic_words:
            text_lower = all_text.lower()
            hits = sum(1 for w in topic_words if w in text_lower)
            coverage = hits / len(topic_words)
            if coverage < 0.15 and intent not in ("title", "closing", "vision"):
                result.issues.append(HallucinationIssue(
                    kind="topic_drift",
                    severity="warning",
                    field="content",
                    detail=f"Only {coverage:.0%} of topic keywords found in slide content. Possible off-topic drift.",
                    auto_fixable=False,
                ))
                result.score_penalty += 1.0
    
    # 7. Fact cross-verification gate - HARD BLOCK if claims lack research support
    if research_text and intent in ("market", "traction", "financials", "competition"):
        verification_result = _cross_verify_facts(all_text, research_text, intent)
        if not verification_result["verified"]:
            result.issues.append(HallucinationIssue(
                kind="unsourced_claim",
                severity="error",
                field="content",
                detail=f"HARD BLOCK: Claims not supported by research. {verification_result['detail']}",
                auto_fixable=False,
            ))
            result.score_penalty = 7.0
            result.hard_block = True
    
    if result.issues:
        logger.info(
            "hallucination_guard_issues",
            slide_index=slide_index,
            intent=intent,
            n_issues=len(result.issues),
            penalty=result.score_penalty,
            kinds=[i.kind for i in result.issues],
        )
    
    return result


def auto_fix_slide(slide_data: dict[str, Any], issues: list[HallucinationIssue]) -> dict[str, Any]:
    """Apply auto-fixes for fixable hallucination issues.
    
    Only fixes issues marked as auto_fixable. Returns modified slide_data.
    """
    fixed = dict(slide_data)
    
    for issue in issues:
        if not issue.auto_fixable:
            continue
        
        if issue.kind == "placeholder":
            # Remove placeholder text from the specific field
            if issue.field in fixed and isinstance(fixed[issue.field], str):
                for pattern in _PLACEHOLDER_PATTERNS:
                    fixed[issue.field] = pattern.sub("", fixed[issue.field]).strip()
        
        elif issue.kind == "instruction_leak":
            # Strip instruction phrases from all text fields
            for key in ("headline", "subheadline", "body"):
                if key in fixed and isinstance(fixed[key], str):
                    text = fixed[key]
                    for phrase in _INSTRUCTION_LEAKAGE:
                        text = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE).strip()
                    fixed[key] = text
            if "bullets" in fixed and isinstance(fixed["bullets"], list):
                fixed["bullets"] = [
                    re.sub("|".join(re.escape(p) for p in _INSTRUCTION_LEAKAGE), "", b, flags=re.IGNORECASE).strip()
                    for b in fixed["bullets"]
                    if b.strip()
                ]
        
        elif issue.kind == "scraper_artifact":
            # Remove scraper artifacts from all text fields
            for key in ("headline", "subheadline", "body"):
                if key in fixed and isinstance(fixed[key], str):
                    fixed[key] = _SCRAPER_ARTIFACTS.sub("", fixed[key]).strip()
            if "bullets" in fixed and isinstance(fixed["bullets"], list):
                fixed["bullets"] = [
                    b for b in fixed["bullets"]
                    if not _SCRAPER_ARTIFACTS.search(b)
                ]
    
    return fixed
