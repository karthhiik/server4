"""
Evidence assembler — converts raw FactPackets into slide-specific
SlideEvidenceBundles with deduplication, relevance scoring, missing-data
detection, source mixing, and cross-validation scoring.
"""

from __future__ import annotations

import logging
from collections import Counter
from difflib import SequenceMatcher
from typing import Optional

from app.mcp.brain_mcp.research.models import (
    ClaimType,
    FactPacket,
    FreshnessClass,
    MissingDataItem,
    RejectedClaim,
    SlideEvidenceBundle,
    SlideKind,
    SourceMix,
    SourceType,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# SLIDE-KIND → RELEVANCE KEYWORDS  (used by _compute_relevance)
# ═══════════════════════════════════════════════════════════════════════

_SLIDE_RELEVANCE_SIGNALS: dict[SlideKind, list[str]] = {
    SlideKind.problem: [
        "pain", "problem", "challenge", "frustrat", "inefficien",
        "cost", "waste", "difficult", "complex", "fail", "gap",
        "unmet", "underserved", "struggle",
    ],
    SlideKind.solution: [
        "solution", "product", "platform", "approach", "innovat",
        "automat", "feature", "benefit", "advantage", "enable",
        "simplif", "improv",
    ],
    SlideKind.market: [
        "market", "TAM", "SAM", "SOM", "billion", "million",
        "CAGR", "growth", "forecast", "revenue", "size", "opportunity",
        "addressable", "segment",
    ],
    SlideKind.competition: [
        "competit", "rival", "alternative", "market share", "versus",
        "comparison", "benchmark", "differentiat", "funding", "raised",
    ],
    SlideKind.gtm: [
        "go to market", "GTM", "acquisition", "channel", "distribut",
        "partnership", "sales", "marketing", "strategy", "pricing",
    ],
    SlideKind.traction: [
        "traction", "revenue", "user", "customer", "growth",
        "MRR", "ARR", "milestone", "metric", "retention",
        "engagement", "sign-up",
    ],
    SlideKind.financial: [
        "financial", "revenue", "margin", "valuation", "multiple",
        "burn", "runway", "profit", "EBITDA", "unit econom",
        "LTV", "CAC", "cost",
    ],
    SlideKind.ask: [
        "funding", "raise", "round", "invest", "capital",
        "use of proceeds", "allocation", "terms", "valuation",
    ],
    SlideKind.why_now: [
        "timing", "trend", "regulation", "shift", "inflection",
        "catalyst", "tailwind", "macro", "pandemic", "digital",
    ],
    SlideKind.product_demo: [
        "demo", "feature", "screenshot", "workflow", "interface",
        "user experience", "design",
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# SLIDE-KIND → REQUIRED EVIDENCE TYPES  (used for missing-data detection)
# ═══════════════════════════════════════════════════════════════════════

_REQUIRED_EVIDENCE: dict[SlideKind, list[dict[str, str]]] = {
    SlideKind.market: [
        {
            "what": "Total Addressable Market (TAM) size",
            "how_to_get": "Search for '{topic} TAM market size' or use industry reports",
            "provider": "serper",
            "severity": "critical",
        },
        {
            "what": "Serviceable Addressable Market (SAM)",
            "how_to_get": "Search for '{topic} SAM serviceable market segment'",
            "provider": "tavily",
            "severity": "important",
        },
        {
            "what": "Serviceable Obtainable Market (SOM)",
            "how_to_get": "Estimate from TAM/SAM based on go-to-market reach",
            "provider": "tavily",
            "severity": "important",
        },
        {
            "what": "Market CAGR / growth rate with date stamp",
            "how_to_get": "Search for '{topic} market CAGR growth rate forecast 2025-2030'",
            "provider": "serper",
            "severity": "critical",
        },
        {
            "what": "Market trend or analyst commentary",
            "how_to_get": "Search recent news for analyst forecasts or industry trends",
            "provider": "newsapi",
            "severity": "nice_to_have",
        },
    ],
    SlideKind.problem: [
        {
            "what": "Quantified cost of the problem",
            "how_to_get": "Search '{topic} cost of problem economic impact statistics'",
            "provider": "serper",
            "severity": "critical",
        },
        {
            "what": "User pain point with testimonial or survey data",
            "how_to_get": "Search '{topic} user frustration survey customer complaints'",
            "provider": "reddit",
            "severity": "important",
        },
        {
            "what": "Market inefficiency evidence",
            "how_to_get": "Search '{topic} inefficiency status quo industry challenges'",
            "provider": "tavily",
            "severity": "important",
        },
        {
            "what": "Affected population or segment size",
            "how_to_get": "Search '{topic} number of affected users businesses market size'",
            "provider": "serper",
            "severity": "important",
        },
    ],
    SlideKind.solution: [
        {
            "what": "Differentiation from existing solutions",
            "how_to_get": "Search '{topic} competitive advantage unique approach'",
            "provider": "serper",
            "severity": "critical",
        },
        {
            "what": "Social proof or user testimonial",
            "how_to_get": "Search '{topic} customer success story review testimonial'",
            "provider": "reddit",
            "severity": "important",
        },
        {
            "what": "Technology validation or credibility signal",
            "how_to_get": "Search '{topic} technology validation patent peer review'",
            "provider": "core",
            "severity": "nice_to_have",
        },
    ],
    SlideKind.competition: [
        {
            "what": "Named competitors with funding data",
            "how_to_get": "Search '{topic} competitors funding raised crunchbase'",
            "provider": "serper",
            "severity": "critical",
        },
        {
            "what": "Feature comparison matrix data",
            "how_to_get": "Search '{topic} feature comparison alternatives G2 Capterra'",
            "provider": "tavily",
            "severity": "critical",
        },
        {
            "what": "Market share distribution",
            "how_to_get": "Search '{topic} market share top players breakdown'",
            "provider": "serper",
            "severity": "important",
        },
        {
            "what": "Competitor weakness or gap",
            "how_to_get": "Search '{topic} competitor limitations complaints negative reviews'",
            "provider": "reddit",
            "severity": "important",
        },
        {
            "what": "Competitive positioning data (magic quadrant / wave)",
            "how_to_get": "Search '{topic} Gartner magic quadrant Forrester wave analyst report'",
            "provider": "tavily",
            "severity": "nice_to_have",
        },
    ],
    SlideKind.traction: [
        {
            "what": "Revenue or ARR figures",
            "how_to_get": "Search '{topic} revenue ARR MRR annual report'",
            "provider": "serper",
            "severity": "critical",
        },
        {
            "what": "User/customer growth metrics",
            "how_to_get": "Search '{topic} users customers growth milestones'",
            "provider": "tavily",
            "severity": "critical",
        },
        {
            "what": "Key partnerships or logos",
            "how_to_get": "Search '{topic} customer logos partnerships enterprise clients'",
            "provider": "serper",
            "severity": "important",
        },
        {
            "what": "Engagement or retention rates",
            "how_to_get": "Search '{topic} retention rate engagement DAU MAU metrics'",
            "provider": "tavily",
            "severity": "important",
        },
    ],
    SlideKind.financial: [
        {
            "what": "Comparable company valuation multiples",
            "how_to_get": "Search '{topic} comparable company valuation EV/revenue multiples'",
            "provider": "polygon",
            "severity": "critical",
        },
        {
            "what": "Unit economics benchmarks (LTV, CAC, payback)",
            "how_to_get": "Search '{topic} SaaS unit economics LTV CAC benchmarks'",
            "provider": "serper",
            "severity": "critical",
        },
        {
            "what": "Gross margin or cost structure data",
            "how_to_get": "Search '{topic} gross margin operating cost structure industry average'",
            "provider": "fmp",
            "severity": "important",
        },
        {
            "what": "Recent funding round comps in same sector",
            "how_to_get": "Search '{topic} recent funding rounds seed series A sector'",
            "provider": "tavily",
            "severity": "important",
        },
        {
            "what": "Industry financial ratio benchmarks",
            "how_to_get": "Search '{topic} industry average financial ratios SaaS benchmarks'",
            "provider": "serper",
            "severity": "nice_to_have",
        },
    ],
    SlideKind.gtm: [
        {
            "what": "Customer acquisition channel performance data",
            "how_to_get": "Search '{topic} customer acquisition channels CAC by channel'",
            "provider": "serper",
            "severity": "critical",
        },
        {
            "what": "Industry GTM benchmark or case study",
            "how_to_get": "Search '{topic} go to market strategy case study SaaS'",
            "provider": "tavily",
            "severity": "important",
        },
        {
            "what": "Partnership or channel distribution evidence",
            "how_to_get": "Search '{topic} distribution partnerships channel strategy'",
            "provider": "serper",
            "severity": "nice_to_have",
        },
    ],
    SlideKind.ask: [
        {
            "what": "Comparable funding round data",
            "how_to_get": "Search '{topic} comparable raises seed Series A funding'",
            "provider": "serper",
            "severity": "critical",
        },
        {
            "what": "Sector-specific valuation benchmarks",
            "how_to_get": "Search '{topic} startup valuation benchmark median sector'",
            "provider": "tavily",
            "severity": "important",
        },
        {
            "what": "Use-of-proceeds breakdown examples",
            "how_to_get": "Search 'startup use of proceeds allocation plan template'",
            "provider": "serper",
            "severity": "nice_to_have",
        },
    ],
    SlideKind.why_now: [
        {
            "what": "Macro trend or regulatory catalyst",
            "how_to_get": "Search '{topic} regulatory change technology shift macro trend'",
            "provider": "guardian",
            "severity": "critical",
        },
        {
            "what": "Technology inflection evidence",
            "how_to_get": "Search '{topic} technology adoption curve inflection point'",
            "provider": "tavily",
            "severity": "important",
        },
        {
            "what": "Academic or industry forecast supporting timing",
            "how_to_get": "Search '{topic} market forecast analyst prediction timing'",
            "provider": "core",
            "severity": "important",
        },
    ],
    SlideKind.product_demo: [
        {
            "what": "Product review or user testimonial",
            "how_to_get": "Search '{topic} product review user feedback experience'",
            "provider": "reddit",
            "severity": "important",
        },
        {
            "what": "Feature comparison or benchmark",
            "how_to_get": "Search '{topic} features comparison benchmark product'",
            "provider": "serper",
            "severity": "nice_to_have",
        },
    ],
}

# Source-type → SourceMix bucket
_SOURCE_TYPE_BUCKET: dict[SourceType, str] = {
    SourceType.government_data: "deterministic",
    SourceType.financial_api: "deterministic",
    SourceType.company_filing: "deterministic",
    SourceType.academic_paper: "academic",
    SourceType.news_article: "llm_extracted",
    SourceType.industry_report: "llm_extracted",
    SourceType.web_extracted: "llm_extracted",
    SourceType.social_signal: "social",
}

# Minimum evidence score to consider a bundle "good enough"
_MIN_EVIDENCE_SCORE = 0.35


class EvidenceAssembler:
    """
    Takes raw FactPackets from research and assembles slide-specific
    evidence bundles.  Handles deduplication, relevance scoring,
    missing-data detection, and source mixing.
    """

    # ── Main entry point ────────────────────────────────────────

    def assemble(
        self,
        slide_id: str,
        slide_kind: SlideKind,
        all_packets: list[FactPacket],
        approved_ids: Optional[list[str]] = None,
        rejected: Optional[list[RejectedClaim]] = None,
    ) -> SlideEvidenceBundle:
        """Assemble a SlideEvidenceBundle from available FactPackets.

        Steps:
        1. Filter packets relevant to this slide.
        2. Sort by confidence and relevance.
        3. Deduplicate.
        4. Build source mix.
        5. Detect missing data.
        6. Compute evidence and cross-validation scores.
        """
        approved_ids = approved_ids or []
        rejected = rejected or []

        # 1 — Relevance filter + scoring
        scored: list[tuple[float, FactPacket]] = []
        for pkt in all_packets:
            rel = self._compute_relevance(pkt, slide_kind)
            if rel > 0.0:
                scored.append((rel, pkt))

        # 2 — Sort by (relevance DESC, confidence DESC)
        scored.sort(key=lambda t: (t[0], t[1].confidence), reverse=True)

        # 3 — Deduplicate (keep highest confidence of near-duplicates)
        unique_packets = self._deduplicate([pkt for _, pkt in scored])

        # 4 — Build source mix
        source_mix = self._build_source_mix(unique_packets)

        # 5 — Detect missing data
        missing = self._detect_missing_data(slide_kind, unique_packets)

        # 6 — Compute scores
        evidence_score = self._compute_evidence_score(
            unique_packets, missing, slide_kind,
        )
        cross_val_score = self._compute_cross_validation_score(unique_packets)

        bundle = SlideEvidenceBundle(
            slide_id=slide_id,
            slide_kind=slide_kind,
            evidence_packets=unique_packets,
            source_mix=source_mix,
            missing_data=missing,
            evidence_score=evidence_score,
            approved_claim_ids=approved_ids,
            rejected_claims=rejected,
            cross_validation_score=cross_val_score,
            debate_approved=len(approved_ids) > 0,
        )

        logger.info(
            "Assembled evidence bundle for slide=%s kind=%s: "
            "%d packets, score=%.2f, cross_val=%.2f, missing=%d",
            slide_id,
            slide_kind.value,
            len(unique_packets),
            evidence_score,
            cross_val_score,
            len(missing),
        )
        return bundle

    # ── Relevance scoring ───────────────────────────────────────

    def _compute_relevance(
        self, packet: FactPacket, slide_kind: SlideKind,
    ) -> float:
        """Score how relevant a FactPacket is to a specific slide kind.

        Returns 0.0–1.0.  Zero means the packet should be excluded.
        """
        # Check if slide_relevance was already set during creation
        if packet.slide_relevance:
            pre_set = packet.slide_relevance.get(slide_kind.value, 0.0)
            if pre_set > 0.0:
                return pre_set

        signals = _SLIDE_RELEVANCE_SIGNALS.get(slide_kind)
        if not signals:
            # For title / team / appendix — everything is mildly relevant
            return 0.3

        claim_lower = packet.claim.lower()
        snippet_lower = (packet.raw_snippet or "").lower()
        text = f"{claim_lower} {snippet_lower}"

        hit_count = 0
        for signal in signals:
            if signal.lower() in text:
                hit_count += 1

        if hit_count == 0:
            # Give a small baseline so we don't discard all evidence
            return 0.15

        # Scale hits → 0.3–1.0
        max_signals = min(len(signals), 6)
        score = 0.3 + 0.7 * (min(hit_count, max_signals) / max_signals)

        # Boost for numeric claims on data-heavy slides
        data_heavy = {
            SlideKind.market, SlideKind.financial, SlideKind.traction,
            SlideKind.competition, SlideKind.ask,
        }
        if slide_kind in data_heavy and packet.claim_type == ClaimType.numeric:
            score = min(1.0, score + 0.1)

        # Boost for fresh data
        if packet.freshness_class in (FreshnessClass.real_time, FreshnessClass.breaking, FreshnessClass.recent):
            score = min(1.0, score + 0.05)

        return round(score, 3)

    # ── Deduplication ───────────────────────────────────────────

    @staticmethod
    def _deduplicate(
        packets: list[FactPacket],
        threshold: float = 0.80,
    ) -> list[FactPacket]:
        """Remove near-duplicate FactPackets, keeping highest confidence."""
        if len(packets) <= 1:
            return list(packets)

        keep: list[FactPacket] = []
        for pkt in packets:
            is_dup = False
            for kept in keep:
                sim = SequenceMatcher(
                    None,
                    pkt.claim.lower(),
                    kept.claim.lower(),
                ).ratio()
                if sim >= threshold:
                    is_dup = True
                    # Absorb cross-validation info into the keeper
                    if pkt.provider not in kept.cross_validation_sources:
                        kept.cross_validation_sources.append(pkt.provider)
                        kept.cross_validated = True
                    break
            if not is_dup:
                keep.append(pkt)

        return keep

    # ── Missing data detection ──────────────────────────────────

    def _detect_missing_data(
        self,
        slide_kind: SlideKind,
        packets: list[FactPacket],
    ) -> list[MissingDataItem]:
        """Detect what evidence is missing for this slide kind.

        Checks _REQUIRED_EVIDENCE templates against the available packets.
        """
        required = _REQUIRED_EVIDENCE.get(slide_kind, [])
        if not required:
            return []

        existing_text = " ".join(p.claim.lower() for p in packets)
        missing: list[MissingDataItem] = []

        for req in required:
            what_lower = req["what"].lower()
            # Extract key terms from the "what" description
            key_terms = self._extract_key_terms(what_lower)

            # Check if any key terms appear in existing evidence
            found = False
            for term in key_terms:
                if term in existing_text:
                    found = True
                    break

            if not found:
                missing.append(
                    MissingDataItem(
                        what=req["what"],
                        how_to_get=req["how_to_get"],
                        suggested_provider=req["provider"],
                        severity=req["severity"],
                    )
                )

        return missing

    @staticmethod
    def _extract_key_terms(text: str) -> list[str]:
        """Extract discriminating terms from a requirement description."""
        # Split on common delimiters and filter short/generic words
        stop = {
            "a", "an", "the", "or", "and", "of", "in", "for", "to",
            "with", "by", "from", "data", "evidence", "signal",
        }
        words = text.replace("(", " ").replace(")", " ").replace("/", " ").split()
        terms = [w.strip(",. ") for w in words if len(w) > 2 and w not in stop]

        # Build bigrams for multi-word concepts
        bigrams = []
        for i in range(len(terms) - 1):
            bigrams.append(f"{terms[i]} {terms[i+1]}")

        # Return bigrams first (more specific), then unigrams
        return bigrams + terms

    # ── Evidence score ──────────────────────────────────────────

    def _compute_evidence_score(
        self,
        packets: list[FactPacket],
        missing: list[MissingDataItem],
        slide_kind: SlideKind,
    ) -> float:
        """0.0–1.0 score based on evidence quality and completeness."""
        if not packets:
            return 0.0

        # Component 1: Volume (0–0.3)
        # Scale: 0 packets → 0, 5+ packets → 0.3
        volume_score = min(len(packets) / 5.0, 1.0) * 0.3

        # Component 2: Average confidence (0–0.3)
        avg_conf = sum(p.confidence for p in packets) / len(packets)
        confidence_score = avg_conf * 0.3

        # Component 3: Source diversity (0–0.2)
        unique_providers = len(set(p.provider for p in packets))
        unique_source_types = len(set(p.source_type for p in packets))
        diversity_raw = (min(unique_providers, 4) / 4.0 + min(unique_source_types, 3) / 3.0) / 2.0
        diversity_score = diversity_raw * 0.2

        # Component 4: Completeness (0–0.2)
        required = _REQUIRED_EVIDENCE.get(slide_kind, [])
        if required:
            critical_missing = sum(
                1 for m in missing if m.severity == "critical"
            )
            total_critical = sum(
                1 for r in required if r.get("severity") == "critical"
            )
            if total_critical > 0:
                completeness = 1.0 - (critical_missing / total_critical)
            else:
                completeness = 1.0
        else:
            completeness = 1.0
        completeness_score = completeness * 0.2

        total = volume_score + confidence_score + diversity_score + completeness_score
        return round(max(0.0, min(1.0, total)), 3)

    # ── Cross-validation score ──────────────────────────────────

    @staticmethod
    def _compute_cross_validation_score(packets: list[FactPacket]) -> float:
        """How well-corroborated is the evidence?

        Returns 0.0–1.0 based on the fraction of packets that are
        cross-validated (confirmed by multiple providers).
        """
        if not packets:
            return 0.0

        cross_val_count = sum(1 for p in packets if p.cross_validated)
        ratio = cross_val_count / len(packets)

        # Bonus if we have multiple source types confirming the same facts
        source_types = Counter(p.source_type for p in packets)
        type_diversity_bonus = min(len(source_types) - 1, 3) * 0.05

        score = ratio * 0.8 + type_diversity_bonus
        return round(max(0.0, min(1.0, score)), 3)

    # ── Source mix ──────────────────────────────────────────────

    @staticmethod
    def _build_source_mix(packets: list[FactPacket]) -> SourceMix:
        """Categorise packets into SourceMix buckets."""
        mix = SourceMix()

        for pkt in packets:
            bucket = _SOURCE_TYPE_BUCKET.get(pkt.source_type, "llm_extracted")

            if bucket == "deterministic":
                mix.deterministic.append(pkt)
            elif bucket == "academic":
                mix.academic.append(pkt)
            elif bucket == "social":
                mix.social.append(pkt)
            elif bucket == "specialty":
                mix.specialty.append(pkt)
            else:
                mix.llm_extracted.append(pkt)

        return mix
