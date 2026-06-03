"""Session Context Reset — Prevents Cross-Deck Contamination.

CEO-identified issue: Vocabulary from previous sessions bleeds into new decks.
Example: "Coverage" (insurance terminology) appeared in an energy grid deck
because the AI didn't reset its vocabulary between sessions.

This module:
  1. Builds a clean context for each new generation session
  2. Injects forbidden vocabulary lists based on detected industry
  3. Provides mandatory vocabulary constraints for the writer prompts

Usage:
    from app.services.v4.session_context import build_session_context

    context = build_session_context(
        company_name="AetherGrid",
        industry="energy",
        user_input=user_input_dict,
    )

    # context contains:
    #   - forbidden_vocabulary: terms that must NOT appear
    #   - mandatory_vocabulary: terms that SHOULD appear
    #   - session_reset_prompt: system prompt addition for writer
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


# Industry-specific forbidden vocabulary
# These terms should NEVER appear in decks for OTHER industries
_INDUSTRY_FORBIDDEN_VOCABULARY: dict[str, list[str]] = {
    "insurance": [
        # These are ONLY allowed in insurance decks
    ],
    # For non-insurance decks, these terms are FORBIDDEN
    "_non_insurance_forbidden": [
        "coverage", "premium", "underwriting", "policy", "claims",
        "insurer", "insured", "deductible", "policyholder", "actuary",
        "reinsurance", "indemnity", "liability coverage",
    ],
    "energy": [
        # Energy terms are generally fine elsewhere
    ],
    "fintech": [
        # Fintech terms are generally fine elsewhere
    ],
    "space": [
        # Space-specific terms
    ],
    "healthcare": [
        # Healthcare-specific terms
    ],
}

# Industry-specific expected vocabulary
# These terms SHOULD appear in decks for their respective industries
_INDUSTRY_EXPECTED_VOCABULARY: dict[str, list[str]] = {
    "energy": [
        "grid", "blackout", "load balancing", "renewable", "orchestration",
        "edge-computing", "energy", "power", "electricity", "utility",
        "decentralized", "surplus", "real-time", "distribution",
    ],
    "insurance": [
        "risk", "protection", "coverage", "premium", "claims",
        "underwriting", "policy", "insured", "liability",
    ],
    "fintech": [
        "payment", "transaction", "settlement", "ledger", "wallet",
        "financial", "banking", "money", "funds", "transfer",
    ],
    "space": [
        "satellite", "orbit", "launch", "payload", "mission",
        "spacecraft", "constellation", "ground station", "telemetry",
    ],
    "healthcare": [
        "patient", "diagnosis", "treatment", "clinical", "healthcare",
        "medical", "health", "therapy", "drug", "device",
    ],
    "cybersecurity": [
        "threat", "vulnerability", "attack", "breach", "security",
        "cyber", "malware", "ransomware", "phishing", "encryption",
    ],
}

# Generic template phrases that are ALWAYS forbidden
_ALWAYS_FORBIDDEN: list[str] = [
    "unique value proposition",
    "distinctive edge",
    "empowering resilience",
    "how we operate",
    "our approach",
    "streamlined processes",
    "comprehensive solution",
    "holistic approach",
    "seamless integration",
    "paradigm shift",
    "game-changer",
    "revolutionizing",
    "disrupting the industry",
    "industry-leading",
    "world-class",
    "best-in-class",
    "cutting-edge",
    "next-generation",
    "proven track record",
    "join us on this journey",
    "investment opportunity",
]


@dataclass
class SessionContext:
    """Clean session context for a single generation."""

    company_name: str
    industry: str
    forbidden_vocabulary: list[str] = field(default_factory=list)
    mandatory_vocabulary: list[str] = field(default_factory=list)
    user_input_keywords: list[str] = field(default_factory=list)
    session_reset_prompt: str = ""

    def get_writer_constraints_block(self) -> str:
        """Generate the constraint block to append to writer prompts."""
        lines: list[str] = []

        # Forbidden vocabulary
        if self.forbidden_vocabulary:
            lines.append(
                "\n\nCRITICAL — FORBIDDEN VOCABULARY (NEVER use these words):\n"
                "The following terms are from OTHER industries or are generic fluff.\n"
                "Using ANY of these will cause immediate rejection:\n"
            )
            # Group in rows of 5 for readability
            for i in range(0, len(self.forbidden_vocabulary), 5):
                chunk = self.forbidden_vocabulary[i:i+5]
                lines.append(f"  • {', '.join(chunk)}")

        # Mandatory vocabulary
        if self.mandatory_vocabulary:
            lines.append(
                f"\n\nMANDATORY VOCABULARY (use at least 2-3 of these terms):\n"
                f"These are industry-appropriate terms for {self.industry}:\n"
            )
            for i in range(0, len(self.mandatory_vocabulary), 5):
                chunk = self.mandatory_vocabulary[i:i+5]
                lines.append(f"  • {', '.join(chunk)}")

        # User input keywords
        if self.user_input_keywords:
            lines.append(
                "\n\nUSER INPUT KEYWORDS (MANDATORY — at least ONE must appear in headline or bullets):\n"
                "These are specific facts from the user. They MUST be referenced:\n"
            )
            for kw in self.user_input_keywords[:10]:
                lines.append(f"  • {kw}")

        return "\n".join(lines) + "\n"


def _detect_industry(text: str, company_name: Optional[str] = None) -> str:
    """Detect industry from user input text."""
    text_lower = text.lower()

    # Industry keyword patterns
    industry_patterns = {
        "energy": [
            "grid", "energy", "power", "electricity", "renewable", "blackout",
            "utility", "load balancing", "edge-computing", "decentralized",
        ],
        "insurance": [
            "insurance", "coverage", "premium", "underwriting", "policy",
            "claims", "risk", "actuary", "reinsurance",
        ],
        "fintech": [
            "payment", "fintech", "banking", "transaction", "wallet",
            "ledger", "settlement", "financial", "money transfer",
        ],
        "space": [
            "satellite", "space", "orbit", "launch", "payload",
            "constellation", "spacecraft", "aerospace",
        ],
        "healthcare": [
            "healthcare", "medical", "patient", "clinical", "diagnosis",
            "treatment", "drug", "therapy", "hospital",
        ],
        "cybersecurity": [
            "cyber", "security", "threat", "vulnerability", "breach",
            "malware", "ransomware", "encryption", "phishing",
        ],
    }

    for industry, keywords in industry_patterns.items():
        if any(kw in text_lower for kw in keywords):
            return industry

    return "general"


def _extract_user_input_keywords(user_input: dict[str, Any]) -> list[str]:
    """Extract specific keywords from user input that MUST appear in slides."""
    keywords: list[str] = []

    # Company name is always mandatory
    if user_input.get("company", {}).get("name"):
        keywords.append(user_input["company"]["name"])

    # Traction milestones
    traction = user_input.get("traction", {})
    if traction.get("key_milestones"):
        for m in traction["key_milestones"][:3]:
            # Extract key phrases - if it's a long string, split it
            if isinstance(m, str):
                # Split by common delimiters to extract individual metrics
                parts = []
                for delimiter in ["+", "&", "and", ",", ";"]:
                    if delimiter in m:
                        parts = [p.strip() for p in m.split(delimiter)]
                        break
                if not parts:
                    # If no delimiters, split by spaces and recombine meaningful phrases
                    words = m.split()
                    if len(words) > 3:
                        # Try to keep 2-3 word phrases together
                        for i in range(0, len(words) - 1, 2):
                            phrase = " ".join(words[i:i+2])
                            parts.append(phrase)
                    else:
                        parts = [m]
                keywords.extend(parts[:5])
            else:
                keywords.append(str(m)[:50])

    # Funding amount
    fundraising = user_input.get("fundraising", {})
    if fundraising.get("amount"):
        keywords.append(f"${fundraising['amount']}")
    if fundraising.get("round"):
        keywords.append(fundraising["round"])

    # Round type
    if fundraising.get("round_type"):
        keywords.append(fundraising["round_type"])

    # Notable customers/partners
    if traction.get("notable_customers"):
        keywords.extend(traction["notable_customers"][:3])
    if traction.get("partnerships"):
        keywords.extend(traction["partnerships"][:3])

    # Patents
    if traction.get("patents"):
        keywords.append("patent pending" if traction["patents"] else "")

    # Market size
    market = user_input.get("market", {})
    for key in ["tam", "sam", "som"]:
        if market.get(key):
            keywords.append(f"{key.upper()}: ${market[key]}")

    # Team credentials
    team = user_input.get("team", [])
    for member in team[:2]:
        if member.get("name"):
            keywords.append(member["name"])
        if member.get("notable_credentials"):
            keywords.extend(member["notable_credentials"][:2])

    # Filter empty strings and dedupe
    return list(dict.fromkeys(kw for kw in keywords if kw))


def build_session_context(
    company_name: str,
    industry: Optional[str] = None,
    user_input: Optional[dict[str, Any]] = None,
    user_query: Optional[str] = None,
) -> SessionContext:
    """Build a clean session context for generation.

    Args:
        company_name: Name of the company
        industry: Detected or provided industry
        user_input: Structured user input (Premium mode)
        user_query: Raw user query (Standard mode)

    Returns:
        SessionContext with forbidden/mandatory vocabulary and reset prompt
    """
    # Detect industry if not provided
    if not industry:
        combined_text = (user_query or "") + " " + str(user_input or {})
        industry = _detect_industry(combined_text, company_name)

    # Build forbidden vocabulary
    forbidden: list[str] = list(_ALWAYS_FORBIDDEN)

    # Add cross-industry contamination prevention
    # If this is NOT an insurance deck, forbid insurance terminology
    if industry != "insurance":
        forbidden.extend(_INDUSTRY_FORBIDDEN_VOCABULARY.get("_non_insurance_forbidden", []))

    # Build mandatory vocabulary
    mandatory = list(_INDUSTRY_EXPECTED_VOCABULARY.get(industry, []))

    # Extract user input keywords
    user_keywords: list[str] = []
    if user_input:
        user_keywords = _extract_user_input_keywords(user_input)
    elif user_query:
        # Extract key entities from query
        # Simple extraction: look for capitalized phrases and numbers
        import re
        # Numbers with units
        numbers = re.findall(r'\$?[\d,.]+[MBKmbk]?(?:\s*(?:million|billion|thousand))?', user_query)
        user_keywords.extend(numbers[:5])
        # Preserve explicit technical terms from raw prompt text. These are
        # user-provided facts, so carrying them forward improves grounding
        # without inventing research or metrics.
        quoted_terms = re.findall(r'"([^"\n]{3,80})"', user_query)
        user_keywords.extend(quoted_terms[:5])
        technical_patterns = [
            r"(?<!\w)O\(\d+\)(?!\w)",
            r"\b[A-Z]{2,}s?\b",
            r"\b[A-Z][A-Za-z]+(?:-[A-Z][A-Za-z]+)+\b",
            r"\b(?:zero-knowledge proofs?|zero-trust|hardware-root-of-trust|low-bandwidth|self-healing|sub-millisecond)\b",
        ]
        for pattern in technical_patterns:
            user_keywords.extend(re.findall(pattern, user_query, flags=re.IGNORECASE)[:8])
        # Audience and purpose labels are routing metadata, not product facts.
        # Promoting "FinTech investors" or "Partnership Proposal" into
        # mandatory headline terms caused decks to inherit the wrong sector.
        for label in ("Presentation Topic",):
            match = re.search(rf"{label}\s*:\s*([^.\n]+)", user_query, flags=re.IGNORECASE)
            if match:
                user_keywords.append(match.group(1).strip())
        # Capitalized phrases (potential names)
        caps = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', user_query)
        user_keywords.extend(caps[:5])

    # Build session reset prompt
    reset_prompt = f"""SESSION CONTEXT RESET — You are starting a FRESH session.

Company: {company_name}
Industry: {industry}

CRITICAL: You must NOT use vocabulary from previous sessions or other industries.
This is a {industry} deck. Use ONLY {industry}-appropriate terminology.

FORBIDDEN TERMS (never use):
{', '.join(forbidden[:15])}

EXPECTED TERMS (use 2-3 of these):
{', '.join(mandatory[:10])}

USER INPUT FACTS (MANDATORY — reference at least one):
{', '.join(user_keywords[:10]) if user_keywords else '(extract from user message)'}
"""

    return SessionContext(
        company_name=company_name,
        industry=industry,
        forbidden_vocabulary=forbidden,
        mandatory_vocabulary=mandatory,
        user_input_keywords=user_keywords,
        session_reset_prompt=reset_prompt,
    )


def get_session_reset_system_prompt_addition(
    company_name: str,
    industry: str,
    forbidden: list[str],
    mandatory: list[str],
    user_keywords: list[str],
) -> str:
    """Generate the system prompt addition for session reset.

    This is appended to the writer's system prompt to ensure
    the LLM starts fresh with no cross-session contamination.
    """
    return f"""
═══════════════════════════════════════════════════════════════
SESSION CONTEXT RESET — CRITICAL
═══════════════════════════════════════════════════════════════

You are writing a pitch deck for: {company_name}
Industry: {industry}

NEVER use terminology from previous sessions. This is a FRESH start.

FORBIDDEN VOCABULARY (using these will cause immediate rejection):
{chr(10).join(f'  ✗ {term}' for term in forbidden[:20])}

MANDATORY USER INPUT (at least ONE must appear in headline or bullets):
{chr(10).join(f'  ✓ {kw}' for kw in user_keywords[:10]) if user_keywords else '  (Extract from user message)'}

═══════════════════════════════════════════════════════════════
"""
