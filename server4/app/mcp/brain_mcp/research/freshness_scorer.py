"""
Evidence freshness scoring — stale data is worse than no data for market slides.

Scores evidence age relative to slide importance and adjusts confidence
accordingly. Market and traction slides demand very recent data while
team bios are stable.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.mcp.brain_mcp.research.models import (
    FactPacket,
    FreshnessClass,
    SlideKind,
)

logger = logging.getLogger(__name__)

# Freshness importance by slide kind (0.0 = age irrelevant, 1.0 = must be live)
FRESHNESS_WEIGHTS: dict[SlideKind, float] = {
    SlideKind.market: 0.9,
    SlideKind.traction: 0.95,
    SlideKind.why_now: 0.85,
    SlideKind.competition: 0.8,
    SlideKind.financial: 0.7,
    SlideKind.problem: 0.6,
    SlideKind.team: 0.1,
    SlideKind.product_demo: 0.2,
    SlideKind.title: 0.05,
    SlideKind.solution: 0.4,
    SlideKind.gtm: 0.65,
    SlideKind.ask: 0.5,
    SlideKind.appendix: 0.3,
}

# Age thresholds in days for each FreshnessClass
_CLASS_BOUNDARIES_DAYS: list[tuple[float, FreshnessClass]] = [
    (1 / 24, FreshnessClass.real_time),     # < 1 hour
    (1.0, FreshnessClass.breaking),          # 1-24 hours
    (7.0, FreshnessClass.recent),            # 1-7 days
    (30.0, FreshnessClass.current),          # 1-4 weeks
    (365.0, FreshnessClass.dated),           # 1-12 months
    (float("inf"), FreshnessClass.archival), # > 1 year
]

# Base freshness score for each class
_CLASS_BASE_SCORES: dict[FreshnessClass, float] = {
    FreshnessClass.real_time: 1.0,
    FreshnessClass.breaking: 0.95,
    FreshnessClass.recent: 0.85,
    FreshnessClass.current: 0.7,
    FreshnessClass.dated: 0.4,
    FreshnessClass.archival: 0.15,
    FreshnessClass.undated: 0.3,
}

# Common date formats for parsing
_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%Y",
]


class FreshnessScorer:
    """Scores evidence freshness and adjusts confidence based on age."""

    def score(self, packet: FactPacket) -> float:
        """
        Return freshness score 0.0-1.0 based on date_published.
        If no date, returns the undated base score.
        """
        freshness_class = self.classify_freshness(packet.date_published)
        return _CLASS_BASE_SCORES.get(freshness_class, 0.3)

    def adjust_confidence(self, packet: FactPacket, slide_kind: SlideKind) -> float:
        """
        Adjust packet confidence based on freshness relative to slide importance.

        Formula: adjusted = original * (1 - weight * (1 - freshness_score))

        For a market slide (weight=0.9) with archival data (score=0.15):
          adjusted = original * (1 - 0.9 * 0.85) = original * 0.235

        For a team slide (weight=0.1) with archival data:
          adjusted = original * (1 - 0.1 * 0.85) = original * 0.915
        """
        freshness_score = self.score(packet)
        weight = FRESHNESS_WEIGHTS.get(slide_kind, 0.5)

        # Penalty increases with staleness and slide freshness importance
        penalty = weight * (1.0 - freshness_score)
        adjusted = packet.confidence * (1.0 - penalty)
        return max(0.0, min(1.0, round(adjusted, 4)))

    def classify_freshness(self, date_str: Optional[str]) -> FreshnessClass:
        """Classify a date string into a FreshnessClass."""
        if not date_str:
            return FreshnessClass.undated

        parsed = self._parse_date(date_str)
        if parsed is None:
            return FreshnessClass.undated

        now = datetime.now(timezone.utc)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        age_days = (now - parsed).total_seconds() / 86400.0

        if age_days < 0:
            # Future date — treat as real-time (likely just published)
            return FreshnessClass.real_time

        for threshold_days, cls in _CLASS_BOUNDARIES_DAYS:
            if age_days <= threshold_days:
                return cls

        return FreshnessClass.archival

    def filter_stale(
        self,
        packets: list[FactPacket],
        slide_kind: SlideKind,
        threshold: float = 0.3,
    ) -> list[FactPacket]:
        """
        Remove packets that are too stale for this slide kind.

        A packet is removed if its adjusted confidence falls below the threshold.
        Always keeps at least one packet if any exist (never return empty from non-empty).
        """
        if not packets:
            return []

        scored = []
        for fp in packets:
            adj_conf = self.adjust_confidence(fp, slide_kind)
            scored.append((fp, adj_conf))

        # Filter by threshold
        kept = [(fp, ac) for fp, ac in scored if ac >= threshold]

        if not kept and scored:
            # Keep the best one even if below threshold
            scored.sort(key=lambda x: x[1], reverse=True)
            best_fp, best_score = scored[0]
            logger.warning(
                "All packets stale for %s slide, keeping best (confidence=%.3f)",
                slide_kind.value,
                best_score,
            )
            return [best_fp]

        filtered_count = len(packets) - len(kept)
        if filtered_count > 0:
            logger.info(
                "Freshness filter: removed %d/%d stale packets for %s slide (threshold=%.2f)",
                filtered_count,
                len(packets),
                slide_kind.value,
                threshold,
            )

        return [fp for fp, _ in kept]

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Try multiple date formats to parse a date string."""
        text = date_str.strip()
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue

        # Try year-only as a fallback (e.g. "2024")
        try:
            year = int(text[:4])
            if 1900 <= year <= 2100:
                return datetime(year, 7, 1, tzinfo=timezone.utc)  # Mid-year estimate
        except (ValueError, IndexError):
            pass

        logger.debug("Could not parse date: %s", date_str)
        return None
