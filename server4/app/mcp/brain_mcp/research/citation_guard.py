"""
Citation Guardian — Blocks unsupported claims from shipping.

Every numeric claim in a pitch deck MUST map to a FactPacket.
Every strategic claim MUST have at least qualitative evidence.
"""

import logging
import re
from typing import Optional

from app.mcp.brain_mcp.research.models import (
    ClaimType,
    FactPacket,
    SlideContentContract,
    SlideKind,
    SourceType,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# CLAIM DETECTION PATTERNS
# ═══════════════════════════════════════════════════════════════════════

# Dollar amounts: $1.5B, $200M, $50K, $1,200
NUMERIC_CLAIM_PATTERN = re.compile(
    r"\$[\d,.]+\s*[BMKbmk]?"
    r"|\d+\.?\d*\s*%"
    r"|\d+[BMKbmk]\+?\s*(?:users|customers|downloads|revenue|ARR|MRR)",
    re.IGNORECASE,
)

# Growth claims: 3x, 45% growth, 120% YoY, 25% CAGR
GROWTH_CLAIM_PATTERN = re.compile(
    r"\d+x"
    r"|\d+\.?\d*\s*%\s*(?:growth|increase|CAGR|YoY|MoM|QoQ)",
    re.IGNORECASE,
)

# Market size: TAM of $5B, market opportunity $200M
MARKET_SIZE_PATTERN = re.compile(
    r"(?:TAM|SAM|SOM|market\s*size|market\s*opportunity)"
    r".{0,50}\$[\d,.]+\s*[BMKbmk]?",
    re.IGNORECASE,
)

# Revenue/financial metrics
FINANCIAL_PATTERN = re.compile(
    r"(?:revenue|ARR|MRR|GMV|run[\s-]*rate|burn[\s-]*rate|LTV|CAC|margin)"
    r".{0,30}\$?[\d,.]+\s*[BMKbmk%]?",
    re.IGNORECASE,
)

# Pitch-deck specific confidence thresholds
_PITCH_RULES = {
    "dollar_amount": {"min_confidence": 0.7, "description": "Dollar amounts"},
    "percentage_growth": {"min_confidence": 0.7, "description": "Growth percentages"},
    "cagr": {"min_confidence": 0.8, "description": "CAGR claims"},
    "market_size": {"min_confidence": 0.7, "requires_cross_validation_or_government": True, "description": "Market size claims"},
}


class CitationGuard:
    """Verifies all claims in generated content are backed by evidence."""

    def verify_contract(
        self,
        contract: SlideContentContract,
        evidence: list[FactPacket],
    ) -> tuple[bool, list[str]]:
        """
        Verify all claims in a SlideContentContract are backed by FactPackets.
        Returns (passed, list_of_issues).
        """
        issues: list[str] = []

        # Collect all text from the contract
        all_text = self._extract_all_text(contract)

        # Extract claims from text
        claims = self._extract_claims_from_text(all_text)

        # Verify each claim has supporting evidence
        for claim in claims:
            support = self._find_supporting_evidence(claim, evidence)
            if support is None:
                issues.append(
                    f"Unsupported {claim['type']}: \"{claim['text']}\" — no matching FactPacket found"
                )

        # Run pitch-specific rules
        pitch_issues = self._check_pitch_rules(contract, evidence)
        issues.extend(pitch_issues)

        passed = len(issues) == 0
        if not passed:
            logger.warning(
                "CitationGuard: slide %s failed with %d issues",
                contract.slide_id,
                len(issues),
            )
        return passed, issues

    def _extract_all_text(self, contract: SlideContentContract) -> str:
        """Extract all textual content from a SlideContentContract."""
        parts: list[str] = []

        # Presentation content
        pc = contract.presentation_content
        parts.append(pc.title)
        if pc.subtitle:
            parts.append(pc.subtitle)
        parts.extend(pc.bullets)
        if pc.hero_stat:
            parts.append(pc.hero_stat)
        if pc.annotation:
            parts.append(pc.annotation)

        # Reading content
        rc = contract.reading_content
        parts.append(rc.title)
        parts.append(rc.summary)
        for section in rc.body_sections:
            parts.append(section.heading)
            parts.extend(section.paragraphs)

        # Speaker notes
        parts.extend(contract.speaker_notes)

        return "\n".join(parts)

    def _extract_claims_from_text(self, text: str) -> list[dict]:
        """Extract all claimable statements from text using regex patterns."""
        claims: list[dict] = []
        seen: set[str] = set()

        for match in MARKET_SIZE_PATTERN.finditer(text):
            matched = match.group().strip()
            if matched not in seen:
                seen.add(matched)
                claims.append({"text": matched, "type": "market_size", "start": match.start()})

        for match in GROWTH_CLAIM_PATTERN.finditer(text):
            matched = match.group().strip()
            if matched not in seen:
                seen.add(matched)
                claim_type = "cagr" if "cagr" in matched.lower() else "percentage_growth"
                claims.append({"text": matched, "type": claim_type, "start": match.start()})

        for match in FINANCIAL_PATTERN.finditer(text):
            matched = match.group().strip()
            if matched not in seen:
                seen.add(matched)
                claims.append({"text": matched, "type": "dollar_amount", "start": match.start()})

        for match in NUMERIC_CLAIM_PATTERN.finditer(text):
            matched = match.group().strip()
            if matched not in seen:
                seen.add(matched)
                claims.append({"text": matched, "type": "numeric", "start": match.start()})

        return claims

    def _find_supporting_evidence(
        self,
        claim: dict,
        evidence: list[FactPacket],
    ) -> Optional[FactPacket]:
        """Find a FactPacket that supports a specific claim."""
        claim_text = claim["text"].lower()

        # Extract numeric value from claim for comparison
        claim_numbers = self._extract_numbers(claim_text)

        for fp in evidence:
            # Direct text match — claim text appears in the fact's claim
            if claim_text in fp.claim.lower() or fp.claim.lower() in claim_text:
                return fp

            # Numeric match — compare extracted numbers
            if claim_numbers and fp.numeric_value is not None:
                for cn in claim_numbers:
                    if cn == 0:
                        continue
                    ratio = abs(fp.numeric_value - cn) / max(abs(cn), 1e-9)
                    if ratio < 0.15:  # Within 15% tolerance
                        return fp

            # Snippet match — claim text appears in raw snippet
            if fp.raw_snippet and claim_text in fp.raw_snippet.lower():
                return fp

            # Citation label match
            if fp.citation_label and fp.citation_label.lower() in claim_text:
                return fp

        return None

    def _extract_numbers(self, text: str) -> list[float]:
        """Extract numeric values from a text string, handling $, K, M, B suffixes."""
        numbers: list[float] = []
        # Match patterns like $1.5B, 200M, 50K, 1,200, 45%, 3x
        pattern = re.compile(r"\$?([\d,]+\.?\d*)\s*([BMKbmkx%])?", re.IGNORECASE)
        for match in pattern.finditer(text):
            raw = match.group(1).replace(",", "")
            try:
                value = float(raw)
            except ValueError:
                continue
            suffix = (match.group(2) or "").upper()
            multipliers = {"B": 1e9, "M": 1e6, "K": 1e3}
            if suffix in multipliers:
                value *= multipliers[suffix]
            numbers.append(value)
        return numbers

    def _check_pitch_rules(
        self,
        contract: SlideContentContract,
        evidence: list[FactPacket],
    ) -> list[str]:
        """
        Pitch-deck specific rules:
        - $ amounts require confidence >= 0.7
        - % growth rates require confidence >= 0.7
        - CAGR claims require confidence >= 0.8
        - Market size claims require cross_validated=True OR source_type=GOVERNMENT_DATA
        """
        issues: list[str] = []
        all_text = self._extract_all_text(contract)
        claims = self._extract_claims_from_text(all_text)

        for claim in claims:
            rule = _PITCH_RULES.get(claim["type"])
            if rule is None:
                continue

            support = self._find_supporting_evidence(claim, evidence)
            if support is None:
                # Already flagged in verify_contract
                continue

            # Check minimum confidence
            min_conf = rule.get("min_confidence", 0.0)
            if support.confidence < min_conf:
                issues.append(
                    f"{rule['description']} claim \"{claim['text']}\" backed by "
                    f"evidence with confidence {support.confidence:.2f} "
                    f"(minimum {min_conf:.2f} required)"
                )

            # Market size requires cross-validation or government source
            if rule.get("requires_cross_validation_or_government"):
                if not support.cross_validated and support.source_type != SourceType.government_data:
                    issues.append(
                        f"Market size claim \"{claim['text']}\" from "
                        f"\"{support.source_name}\" is not cross-validated and "
                        f"not from a government source — consider adding a "
                        f"second source or qualifying with 'estimated'"
                    )

        return issues

    def strip_uncitable_claims(self, text: str, evidence: list[FactPacket]) -> str:
        """
        Remove or soften claims that can't be cited.

        For numeric claims without evidence:
        - Replace specific numbers with hedged language
        - Add "estimated" qualifier to dollar amounts
        - Replace percentages with directional language
        """
        result = text
        claims = self._extract_claims_from_text(text)

        # Process in reverse order to preserve string positions
        for claim in sorted(claims, key=lambda c: c["start"], reverse=True):
            support = self._find_supporting_evidence(claim, evidence)
            if support is not None:
                continue

            original = claim["text"]
            claim_type = claim["type"]

            if claim_type == "market_size":
                # Soften to "estimated market opportunity"
                softened = re.sub(
                    r"(\$[\d,.]+\s*[BMKbmk]?)",
                    r"an estimated \1",
                    original,
                    count=1,
                )
                if softened != original:
                    result = result[: claim["start"]] + softened + result[claim["start"] + len(original) :]
            elif claim_type in ("dollar_amount", "numeric"):
                # Add "approximately" before dollar amounts
                if original.startswith("$"):
                    replacement = f"approximately {original}"
                    result = result[: claim["start"]] + replacement + result[claim["start"] + len(original) :]
            elif claim_type in ("percentage_growth", "cagr"):
                # Replace exact growth with directional
                softened = re.sub(
                    r"\d+\.?\d*\s*%\s*(growth|increase|CAGR|YoY|MoM|QoQ)",
                    r"significant \1",
                    original,
                    flags=re.IGNORECASE,
                )
                if softened != original:
                    result = result[: claim["start"]] + softened + result[claim["start"] + len(original) :]

        return result
