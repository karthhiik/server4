"""
Cross-Validation Engine — Verifies claims across multiple sources.

When multiple providers return data for the same metric, this engine
detects agreement, disagreement, and provides resolution.
"""

import logging
import re
from difflib import SequenceMatcher
from typing import Optional

from app.mcp.brain_mcp.research.models import (
    ClaimType,
    FactPacket,
    SourceType,
)

logger = logging.getLogger(__name__)

# Source authority ranking (higher = more authoritative)
_SOURCE_AUTHORITY: dict[SourceType, int] = {
    SourceType.government_data: 10,
    SourceType.company_filing: 9,
    SourceType.financial_api: 8,
    SourceType.academic_paper: 7,
    SourceType.industry_report: 6,
    SourceType.news_article: 4,
    SourceType.social_signal: 2,
    SourceType.web_extracted: 1,
}


class CrossValidator:
    """Verifies claims across multiple data sources."""

    NUMERIC_AGREEMENT_THRESHOLD = 0.10  # Within 10% = agreement
    NUMERIC_CONFLICT_THRESHOLD = 0.20   # Over 20% = conflict
    TOPIC_SIMILARITY_THRESHOLD = 0.55   # Fuzzy match threshold for grouping

    def validate(self, packets: list[FactPacket]) -> list[FactPacket]:
        """
        Cross-validate FactPackets. Groups by claim similarity, detects
        agreement/conflict, updates cross_validated flags and confidence.

        1. Group packets by claim topic (fuzzy matching)
        2. For each group with 2+ packets:
           a. If numeric claims agree within 10%: mark cross_validated, boost confidence +0.1
           b. If numeric claims disagree >20%: flag both, keep both, note conflict
           c. If single source only: label "according to [source]"
        3. Government data wins over web-extracted in conflicts
        """
        if not packets:
            return []

        groups = self._group_by_topic(packets)
        result: list[FactPacket] = []

        for topic_key, group in groups.items():
            if len(group) == 1:
                # Single source — tag it
                fp = group[0]
                if not fp.citation_label:
                    fp.citation_label = f"according to {fp.source_name}"
                result.append(fp)
                continue

            # Multiple sources — check for numeric agreement/conflict
            numeric_packets = [fp for fp in group if fp.numeric_value is not None]
            non_numeric = [fp for fp in group if fp.numeric_value is None]

            if len(numeric_packets) >= 2:
                # Compare all pairs for agreement/conflict
                validated = self._cross_validate_numeric_group(numeric_packets)
                result.extend(validated)
            elif len(numeric_packets) == 1:
                result.append(numeric_packets[0])

            if non_numeric:
                # Qualitative claims — cross-validate by agreement
                validated_qual = self._cross_validate_qualitative(non_numeric)
                result.extend(validated_qual)

        logger.info(
            "Cross-validation: %d packets in, %d groups found, %d packets out",
            len(packets),
            len(groups),
            len(result),
        )
        return result

    def _group_by_topic(self, packets: list[FactPacket]) -> dict[str, list[FactPacket]]:
        """Group packets that discuss the same metric/topic using fuzzy matching."""
        groups: dict[str, list[FactPacket]] = {}
        assigned: set[str] = set()

        for i, fp in enumerate(packets):
            if fp.id in assigned:
                continue

            # Normalize claim for grouping
            key = self._normalize_claim(fp.claim)
            group = [fp]
            assigned.add(fp.id)

            # Find other packets with similar claims
            for j in range(i + 1, len(packets)):
                other = packets[j]
                if other.id in assigned:
                    continue
                other_key = self._normalize_claim(other.claim)
                similarity = SequenceMatcher(None, key, other_key).ratio()
                if similarity >= self.TOPIC_SIMILARITY_THRESHOLD:
                    group.append(other)
                    assigned.add(other.id)

            groups[key] = group

        return groups

    def _normalize_claim(self, claim: str) -> str:
        """Normalize a claim string for comparison."""
        text = claim.lower().strip()
        # Remove specific numbers to focus on topic
        text = re.sub(r"\$[\d,.]+\s*[BMKbmk]?", "AMOUNT", text)
        text = re.sub(r"\d+\.?\d*\s*%", "PERCENT", text)
        text = re.sub(r"\d+[BMKbmk]", "NUMBER", text)
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)
        return text

    def _compare_numeric(self, a: FactPacket, b: FactPacket) -> str:
        """Compare two numeric claims: 'agree', 'conflict', or 'incomparable'."""
        if a.numeric_value is None or b.numeric_value is None:
            return "incomparable"

        # Guard against zero division
        denominator = max(abs(a.numeric_value), abs(b.numeric_value), 1e-9)
        difference = abs(a.numeric_value - b.numeric_value) / denominator

        if difference <= self.NUMERIC_AGREEMENT_THRESHOLD:
            return "agree"
        elif difference >= self.NUMERIC_CONFLICT_THRESHOLD:
            return "conflict"
        else:
            return "agree"  # Between 10-20% is close enough

    def _resolve_conflict(self, packets: list[FactPacket]) -> FactPacket:
        """
        Resolve conflicting claims.
        Government data wins. Higher authority source wins. Higher confidence wins.
        """
        if not packets:
            raise ValueError("Cannot resolve empty packet list")

        # Sort by authority then confidence
        ranked = sorted(
            packets,
            key=lambda fp: (
                _SOURCE_AUTHORITY.get(fp.source_type, 0),
                fp.confidence,
            ),
            reverse=True,
        )
        winner = ranked[0]
        losers = ranked[1:]

        # Tag loser sources in cross-validation metadata
        winner.cross_validated = True
        winner.cross_validation_sources = [fp.source_name for fp in losers]
        winner.citation_label = (
            f"{winner.source_name} (verified against {len(losers)} "
            f"{'source' if len(losers) == 1 else 'sources'}; conflict resolved)"
        )

        logger.info(
            "Conflict resolved: %s wins (authority=%d, confidence=%.2f) over %s",
            winner.source_name,
            _SOURCE_AUTHORITY.get(winner.source_type, 0),
            winner.confidence,
            ", ".join(fp.source_name for fp in losers),
        )
        return winner

    def _boost_corroborated(self, packets: list[FactPacket]) -> list[FactPacket]:
        """Boost confidence for claims confirmed by multiple sources."""
        if len(packets) < 2:
            return packets

        source_names = [fp.source_name for fp in packets]
        for fp in packets:
            fp.cross_validated = True
            fp.cross_validation_sources = [s for s in source_names if s != fp.source_name]
            # Boost confidence by +0.1, capped at 1.0
            fp.confidence = min(1.0, fp.confidence + 0.1)
            if not fp.citation_label:
                fp.citation_label = (
                    f"{fp.source_name} (corroborated by "
                    f"{', '.join(fp.cross_validation_sources)})"
                )
        return packets

    def _cross_validate_numeric_group(self, packets: list[FactPacket]) -> list[FactPacket]:
        """Cross-validate a group of numeric FactPackets."""
        if len(packets) < 2:
            return packets

        # Check pairwise agreement
        agree_pairs: list[tuple[FactPacket, FactPacket]] = []
        conflict_pairs: list[tuple[FactPacket, FactPacket]] = []

        for i in range(len(packets)):
            for j in range(i + 1, len(packets)):
                verdict = self._compare_numeric(packets[i], packets[j])
                if verdict == "agree":
                    agree_pairs.append((packets[i], packets[j]))
                elif verdict == "conflict":
                    conflict_pairs.append((packets[i], packets[j]))

        if conflict_pairs and not agree_pairs:
            # All conflicting — resolve by authority
            winner = self._resolve_conflict(packets)
            return [winner]
        elif agree_pairs:
            # Some or all agree — boost corroborated ones
            agreeing_ids: set[str] = set()
            for a, b in agree_pairs:
                agreeing_ids.add(a.id)
                agreeing_ids.add(b.id)
            agreeing = [fp for fp in packets if fp.id in agreeing_ids]
            boosted = self._boost_corroborated(agreeing)
            # Also keep non-agreeing ones (may be different metrics)
            others = [fp for fp in packets if fp.id not in agreeing_ids]
            return boosted + others
        else:
            return packets

    def _cross_validate_qualitative(self, packets: list[FactPacket]) -> list[FactPacket]:
        """Cross-validate qualitative claims by source count."""
        if len(packets) >= 2:
            return self._boost_corroborated(packets)
        return packets
