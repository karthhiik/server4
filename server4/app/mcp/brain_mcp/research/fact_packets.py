"""
FactPacket creation, normalisation, confidence scoring, and deduplication.

This module is the only place FactPackets should be constructed.
It assigns IDs, computes confidence, classifies claims, scores freshness,
and deduplicates evidence across providers.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Optional

from app.mcp.brain_mcp.research.models import (
    ClaimType,
    FactPacket,
    FreshnessClass,
    SlideKind,
    SourceType,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# CONFIDENCE WEIGHTS
# ═══════════════════════════════════════════════════════════════════════

_SOURCE_TYPE_BASE_CONFIDENCE: dict[SourceType, float] = {
    SourceType.government_data: 0.95,
    SourceType.financial_api: 0.90,
    SourceType.academic_paper: 0.85,
    SourceType.industry_report: 0.80,
    SourceType.company_filing: 0.80,
    SourceType.news_article: 0.70,
    SourceType.web_extracted: 0.60,
    SourceType.social_signal: 0.50,
}

_FRESHNESS_BONUS: dict[FreshnessClass, float] = {
    FreshnessClass.real_time: 0.05,
    FreshnessClass.breaking: 0.04,
    FreshnessClass.recent: 0.03,
    FreshnessClass.current: 0.01,
    FreshnessClass.dated: 0.00,
    FreshnessClass.archival: -0.05,
    FreshnessClass.undated: -0.03,
}

_EXTRACTION_BONUS: dict[str, float] = {
    "api_structured": 0.05,
    "manual": 0.03,
    "llm_extracted": 0.00,
    "scraped": -0.03,
}

_CROSS_VALIDATION_BONUS: float = 0.08

# ═══════════════════════════════════════════════════════════════════════
# CLAIM CLASSIFICATION PATTERNS
# ═══════════════════════════════════════════════════════════════════════

_NUMERIC_PATTERNS = [
    re.compile(r"\$[\d,.]+[BMKTbmkt]?"),
    re.compile(r"[\d,.]+\s*%"),
    re.compile(r"[\d,.]+\s*(billion|million|thousand|trillion)", re.IGNORECASE),
    re.compile(r"\b\d{1,3}(,\d{3})+\b"),
    re.compile(r"\b\d+(\.\d+)?\s*(x|X)\b"),
]

_TREND_WORDS = re.compile(
    r"\b(growing|declining|increasing|decreasing|surging|plummeting|"
    r"accelerating|decelerating|rising|falling|expanding|contracting|"
    r"trend|trajectory|momentum|uptick|downturn|CAGR)\b",
    re.IGNORECASE,
)

_COMPARISON_WORDS = re.compile(
    r"\b(compared to|versus|vs\.?|more than|less than|higher than|lower than|"
    r"outperform\w*|underperform\w*|ahead of|behind|exceed\w*|surpass\w*|lag\w*|"
    r"relative to|in contrast|unlike|better than|worse than|faster than|slower than)\b",
    re.IGNORECASE,
)

_TESTIMONIAL_PATTERNS = re.compile(
    r'(".*?")|(\u201c.*?\u201d)|(said\s)|(\baccording to\b.*(?:CEO|CTO|founder|director))',
    re.IGNORECASE,
)

_REGULATORY_WORDS = re.compile(
    r"\b(regulation|regulatory|compliance|GDPR|SEC|FDA|FTC|EU|mandate|"
    r"legislation|law|statute|ordinance|directive|ruling|enforcement|"
    r"license|permit|approved|prohibited)\b",
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════


class FactPacketFactory:
    """Single entry-point for creating, normalising and scoring FactPackets."""

    _counter: int = 0

    # ── Primary factory method ──────────────────────────────────

    @classmethod
    def create(
        cls,
        claim: str,
        source_name: str,
        provider: str,
        source_type: SourceType,
        claim_type: ClaimType | None = None,
        source_url: str | None = None,
        date_published: str | None = None,
        freshness_class: FreshnessClass | None = None,
        numeric_value: float | None = None,
        numeric_unit: str | None = None,
        extraction_method: str = "llm_extracted",
        cross_validated: bool = False,
        cross_validation_sources: list[str] | None = None,
        slide_relevance: dict[str, float] | None = None,
        raw_snippet: str | None = None,
        citation_label: str | None = None,
        provider_request_id: str | None = None,
        confidence_override: float | None = None,
    ) -> FactPacket:
        """Build a fully scored FactPacket."""
        cls._counter += 1
        packet_id = f"fp_{provider}_{cls._counter:04d}_{uuid.uuid4().hex[:6]}"

        if claim_type is None:
            claim_type = cls.classify_claim(claim)

        if freshness_class is None:
            freshness_class = cls.compute_freshness(date_published)

        if confidence_override is not None:
            confidence = max(0.0, min(1.0, confidence_override))
        else:
            confidence = cls.compute_confidence(
                source_type=source_type,
                freshness=freshness_class,
                cross_validated=cross_validated,
                extraction_method=extraction_method,
            )

        now_iso = datetime.now(timezone.utc).isoformat()

        return FactPacket(
            id=packet_id,
            claim=claim.strip(),
            claim_type=claim_type,
            source_url=source_url,
            source_name=source_name,
            source_type=source_type,
            date_published=date_published,
            date_retrieved=now_iso,
            freshness_class=freshness_class,
            confidence=confidence,
            numeric_value=numeric_value,
            numeric_unit=numeric_unit,
            extraction_method=extraction_method,
            provider=provider,
            cross_validated=cross_validated,
            cross_validation_sources=cross_validation_sources or [],
            slide_relevance=slide_relevance or {},
            raw_snippet=raw_snippet,
            citation_label=citation_label,
            provider_request_id=provider_request_id,
        )

    # ── Build from structured API response ──────────────────────

    @classmethod
    def from_api_response(
        cls,
        provider: str,
        raw_data: dict[str, Any],
        slide_kind: SlideKind,
    ) -> list[FactPacket]:
        """
        Convert a provider-specific API response into FactPackets.

        Supports normalized structures from the engine layer:
        ```json
        {
          "results": [
            {
              "claim": "...",
              "source_name": "...",
              "source_url": "...",
              "date_published": "...",
              "numeric_value": 123.4,
              "numeric_unit": "USD billion",
              "raw_snippet": "..."
            }
          ],
          "source_type": "financial_api",
          "request_id": "req_xxx"
        }
        ```
        """
        packets: list[FactPacket] = []
        results = raw_data.get("results", [])
        source_type_str = raw_data.get("source_type", "web_extracted")
        request_id = raw_data.get("request_id")

        try:
            source_type = SourceType(source_type_str)
        except ValueError:
            source_type = SourceType.web_extracted

        for item in results:
            claim = item.get("claim") or item.get("title") or item.get("snippet", "")
            if not claim:
                continue

            fp = cls.create(
                claim=claim,
                source_name=item.get("source_name", provider),
                provider=provider,
                source_type=source_type,
                source_url=item.get("source_url") or item.get("url"),
                date_published=item.get("date_published") or item.get("date"),
                numeric_value=item.get("numeric_value"),
                numeric_unit=item.get("numeric_unit"),
                extraction_method="api_structured",
                raw_snippet=item.get("raw_snippet") or item.get("snippet"),
                provider_request_id=request_id,
                slide_relevance={slide_kind.value: 1.0},
            )
            packets.append(fp)

        logger.debug(
            "from_api_response produced %d packets from %s",
            len(packets),
            provider,
        )
        return packets

    # ── Build from search result ────────────────────────────────

    @classmethod
    def from_search_result(
        cls,
        result: dict[str, Any],
        provider: str,
        extraction_model: str = "llm_extracted",
    ) -> FactPacket:
        """Create a FactPacket from a single search-engine result dict."""
        claim = (
            result.get("claim")
            or result.get("snippet")
            or result.get("title", "No claim extracted")
        )
        return cls.create(
            claim=claim,
            source_name=result.get("source", result.get("source_name", provider)),
            provider=provider,
            source_type=SourceType.web_extracted,
            source_url=result.get("url") or result.get("link"),
            date_published=result.get("date") or result.get("date_published"),
            extraction_method=extraction_model,
            raw_snippet=result.get("snippet"),
        )

    # ── Confidence scoring ──────────────────────────────────────

    @staticmethod
    def compute_confidence(
        source_type: SourceType,
        freshness: FreshnessClass,
        cross_validated: bool,
        extraction_method: str,
    ) -> float:
        """
        Deterministic confidence score in [0.0, 1.0].

        Formula:
            base(source_type)
          + freshness_bonus
          + extraction_bonus
          + cross_validation_bonus
        Clamped to [0.0, 1.0].
        """
        base = _SOURCE_TYPE_BASE_CONFIDENCE.get(source_type, 0.60)
        fresh_bonus = _FRESHNESS_BONUS.get(freshness, 0.0)
        extract_bonus = _EXTRACTION_BONUS.get(extraction_method, 0.0)
        cv_bonus = _CROSS_VALIDATION_BONUS if cross_validated else 0.0

        return max(0.0, min(1.0, base + fresh_bonus + extract_bonus + cv_bonus))

    # ── Claim classification ────────────────────────────────────

    @staticmethod
    def classify_claim(claim_text: str) -> ClaimType:
        """Rule-based claim type classification using regex patterns."""
        text = claim_text.strip()

        # Check numeric patterns first (most specific)
        for pat in _NUMERIC_PATTERNS:
            if pat.search(text):
                return ClaimType.numeric

        if _REGULATORY_WORDS.search(text):
            return ClaimType.regulatory

        if _TESTIMONIAL_PATTERNS.search(text):
            return ClaimType.testimonial

        if _COMPARISON_WORDS.search(text):
            return ClaimType.comparison

        if _TREND_WORDS.search(text):
            return ClaimType.trend

        # Check for citation-style references
        if re.search(r"\(\d{4}\)|\[\d+\]|et\s+al\.", text):
            return ClaimType.citation

        return ClaimType.qualitative

    # ── Freshness classification ────────────────────────────────

    @staticmethod
    def compute_freshness(date_str: Optional[str]) -> FreshnessClass:
        """Classify a date string into a FreshnessClass."""
        if not date_str:
            return FreshnessClass.undated

        try:
            # Parse common ISO and date-only formats
            dt: datetime | None = None
            for fmt in (
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d",
                "%B %d, %Y",
                "%b %d, %Y",
                "%d %b %Y",
                "%d %B %Y",
                "%m/%d/%Y",
            ):
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    break
                except ValueError:
                    continue

            if dt is None:
                return FreshnessClass.undated

            # Make timezone-aware for comparison
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            delta = now - dt
            hours = delta.total_seconds() / 3600

            if hours < 1:
                return FreshnessClass.real_time
            if hours < 24:
                return FreshnessClass.breaking
            if delta.days < 7:
                return FreshnessClass.recent
            if delta.days < 28:
                return FreshnessClass.current
            if delta.days < 365:
                return FreshnessClass.dated
            return FreshnessClass.archival

        except Exception:
            logger.debug("Failed to parse date string: %s", date_str)
            return FreshnessClass.undated

    # ── Deduplication ───────────────────────────────────────────

    @staticmethod
    def deduplicate(
        packets: list[FactPacket],
        similarity_threshold: float = 0.85,
    ) -> list[FactPacket]:
        """
        Remove near-duplicate FactPackets, keeping the one with highest confidence.

        Uses SequenceMatcher for string similarity on the claim text.
        When two packets are similar enough, the higher-confidence one wins
        and absorbs cross-validation sources from the other.
        """
        if len(packets) <= 1:
            return list(packets)

        # Sort by confidence descending so we keep higher-quality first
        sorted_packets = sorted(packets, key=lambda fp: fp.confidence, reverse=True)
        kept: list[FactPacket] = []

        for candidate in sorted_packets:
            is_duplicate = False
            for existing in kept:
                ratio = SequenceMatcher(
                    None,
                    candidate.claim.lower(),
                    existing.claim.lower(),
                ).ratio()
                if ratio >= similarity_threshold:
                    # Merge cross-validation sources
                    if candidate.provider not in existing.cross_validation_sources:
                        existing.cross_validation_sources.append(candidate.provider)
                    if candidate.source_url and candidate.source_url not in (
                        existing.cross_validation_sources
                    ):
                        existing.cross_validation_sources.append(
                            candidate.source_url
                        )
                    existing.cross_validated = True
                    # Recompute confidence with cross-validation bonus
                    existing.confidence = min(
                        1.0, existing.confidence + _CROSS_VALIDATION_BONUS
                    )
                    is_duplicate = True
                    break

            if not is_duplicate:
                kept.append(candidate)

        logger.debug(
            "Deduplication: %d → %d packets (threshold=%.2f)",
            len(packets),
            len(kept),
            similarity_threshold,
        )
        return kept
