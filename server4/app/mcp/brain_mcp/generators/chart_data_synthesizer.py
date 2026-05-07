"""
Chart Data Synthesizer -- No-hallucination chart generation from FactPackets.

Creates structured chart data objects directly from verified evidence.
Never invents data points. Every value traces back to a FactPacket.
"""

import logging
from typing import Optional

from app.mcp.brain_mcp.research.models import FactPacket, SlideKind

logger = logging.getLogger(__name__)

# Chart types and their requirements
_CHART_REQUIREMENTS = {
    "bar": {"min_points": 2, "max_points": 10},
    "line": {"min_points": 3, "max_points": 20},
    "pie": {"min_points": 2, "max_points": 8},
    "donut": {"min_points": 2, "max_points": 8},
    "area": {"min_points": 3, "max_points": 15},
}

# Slide kind to suggested chart type
_SLIDE_CHART_DEFAULTS = {
    SlideKind.traction: "line",
    SlideKind.financial: "bar",
    SlideKind.market: "pie",
    SlideKind.competition: "bar",
    SlideKind.gtm: "bar",
}


class ChartDataSynthesizer:
    """Generates chart data directly from verified FactPackets."""

    def synthesize(
        self,
        packets: list[FactPacket],
        chart_type: str,
        slide_kind: SlideKind,
    ) -> Optional[dict]:
        """Create chart data from FactPackets.

        Only uses verified numeric data. Never invents data points.

        Returns:
            Dict with chart_type, title, labels, datasets, source_attribution.
            None if insufficient data for the requested chart type.
        """
        if chart_type not in _CHART_REQUIREMENTS:
            chart_type = _SLIDE_CHART_DEFAULTS.get(slide_kind, "bar")

        # Filter to packets with numeric values
        numeric_packets = [
            fp for fp in packets
            if fp.numeric_value is not None
        ]

        reqs = _CHART_REQUIREMENTS[chart_type]
        if len(numeric_packets) < reqs["min_points"]:
            logger.info(
                "Insufficient data for %s chart: %d packets, need %d",
                chart_type,
                len(numeric_packets),
                reqs["min_points"],
            )
            return None

        # Trim to max points
        numeric_packets = numeric_packets[:reqs["max_points"]]

        # Route to specific chart builder
        builders = {
            "bar": self._build_bar,
            "line": self._build_line,
            "pie": self._build_pie,
            "donut": self._build_donut,
            "area": self._build_area,
        }
        builder = builders.get(chart_type, self._build_bar)
        return builder(numeric_packets, slide_kind)

    def _build_bar(
        self,
        packets: list[FactPacket],
        slide_kind: SlideKind,
    ) -> dict:
        """Build bar chart data."""
        # Group by unit if possible, otherwise use claim as label
        labels: list[str] = []
        values: list[float] = []
        sources: list[str] = []

        for fp in packets:
            label = self._extract_label(fp)
            labels.append(label)
            values.append(fp.numeric_value)
            if fp.source_name not in sources:
                sources.append(fp.source_name)

        unit = self._common_unit(packets)
        title = self._generate_chart_title(packets, slide_kind, "bar")

        return {
            "chart_type": "bar",
            "title": title,
            "labels": labels,
            "datasets": [
                {
                    "label": unit or "Value",
                    "data": values,
                }
            ],
            "source_attribution": ", ".join(sources),
            "unit": unit,
            "fact_packet_ids": [fp.id for fp in packets],
        }

    def _build_line(
        self,
        packets: list[FactPacket],
        slide_kind: SlideKind,
    ) -> dict:
        """Build line chart data. Sorts by date if available."""
        # Sort by date_published if available
        sorted_packets = sorted(
            packets,
            key=lambda fp: fp.date_published or "9999",
        )

        labels = []
        values = []
        sources: list[str] = []

        for fp in sorted_packets:
            label = fp.date_published or self._extract_label(fp)
            labels.append(label)
            values.append(fp.numeric_value)
            if fp.source_name not in sources:
                sources.append(fp.source_name)

        unit = self._common_unit(sorted_packets)
        title = self._generate_chart_title(sorted_packets, slide_kind, "line")

        return {
            "chart_type": "line",
            "title": title,
            "labels": labels,
            "datasets": [
                {
                    "label": unit or "Value",
                    "data": values,
                }
            ],
            "source_attribution": ", ".join(sources),
            "unit": unit,
            "fact_packet_ids": [fp.id for fp in sorted_packets],
        }

    def _build_pie(
        self,
        packets: list[FactPacket],
        slide_kind: SlideKind,
    ) -> dict:
        """Build pie chart data. Values become proportional slices."""
        labels = []
        values = []
        sources: list[str] = []

        for fp in packets:
            label = self._extract_label(fp)
            labels.append(label)
            values.append(abs(fp.numeric_value))
            if fp.source_name not in sources:
                sources.append(fp.source_name)

        title = self._generate_chart_title(packets, slide_kind, "pie")

        return {
            "chart_type": "pie",
            "title": title,
            "labels": labels,
            "datasets": [
                {
                    "data": values,
                }
            ],
            "source_attribution": ", ".join(sources),
            "unit": self._common_unit(packets),
            "fact_packet_ids": [fp.id for fp in packets],
        }

    def _build_donut(
        self,
        packets: list[FactPacket],
        slide_kind: SlideKind,
    ) -> dict:
        """Build donut chart data (pie with center hole)."""
        result = self._build_pie(packets, slide_kind)
        result["chart_type"] = "donut"
        # Add center label: total or most significant value
        total = sum(abs(fp.numeric_value) for fp in packets if fp.numeric_value)
        unit = self._common_unit(packets)
        result["center_label"] = self._format_value(total, unit)
        return result

    def _build_area(
        self,
        packets: list[FactPacket],
        slide_kind: SlideKind,
    ) -> dict:
        """Build area chart data (filled line chart)."""
        result = self._build_line(packets, slide_kind)
        result["chart_type"] = "area"
        result["datasets"][0]["fill"] = True
        return result

    def _extract_label(self, fp: FactPacket) -> str:
        """Extract a short label from a FactPacket claim."""
        claim = fp.claim
        # Try to extract a meaningful short label
        # Use first noun phrase or first 4 words
        words = claim.split()
        if len(words) <= 4:
            return claim
        # Remove common prefixes
        skip_words = {"the", "a", "an", "in", "of", "for", "is", "was", "are", "to"}
        meaningful = [w for w in words if w.lower() not in skip_words]
        return " ".join(meaningful[:4])

    def _common_unit(self, packets: list[FactPacket]) -> Optional[str]:
        """Find the most common unit among packets."""
        units: dict[str, int] = {}
        for fp in packets:
            if fp.numeric_unit:
                unit = fp.numeric_unit.strip()
                units[unit] = units.get(unit, 0) + 1
        if not units:
            return None
        return max(units, key=lambda u: units[u])

    def _generate_chart_title(
        self,
        packets: list[FactPacket],
        slide_kind: SlideKind,
        chart_type: str,
    ) -> str:
        """Generate a descriptive chart title from the data."""
        kind_labels = {
            SlideKind.traction: "Growth Trajectory",
            SlideKind.financial: "Financial Overview",
            SlideKind.market: "Market Breakdown",
            SlideKind.competition: "Competitive Landscape",
            SlideKind.gtm: "Go-to-Market Metrics",
        }
        base = kind_labels.get(slide_kind, "Data Overview")
        unit = self._common_unit(packets)
        if unit:
            return f"{base} ({unit})"
        return base

    def _format_value(self, value: float, unit: Optional[str]) -> str:
        """Format a numeric value for display."""
        if abs(value) >= 1_000_000_000:
            formatted = f"{value / 1_000_000_000:.1f}B"
        elif abs(value) >= 1_000_000:
            formatted = f"{value / 1_000_000:.1f}M"
        elif abs(value) >= 1_000:
            formatted = f"{value / 1_000:.1f}K"
        else:
            formatted = f"{value:.1f}"

        if unit and unit.upper() in ("USD", "$", "DOLLAR", "DOLLARS"):
            return f"${formatted}"
        if unit and unit == "%":
            return f"{formatted}%"
        if unit:
            return f"{formatted} {unit}"
        return formatted
