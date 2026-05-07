"""
Missing data reporter — tells users what's missing and how to fix it.

Generates user-friendly failure messages when evidence is incomplete
or below quality thresholds. Provides actionable suggestions for
manual data enrichment.
"""

import logging
from typing import Optional

from app.mcp.brain_mcp.research.models import (
    FactPacket,
    MissingDataItem,
    SlideFailureState,
    SlideFailureType,
    SlideKind,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# USER-FRIENDLY MESSAGES
# ═══════════════════════════════════════════════════════════════════════

USER_MESSAGES: dict[str, str] = {
    "no_market_data": (
        "We couldn't find verified market size data for this specific niche. "
        "Consider providing your own TAM estimate with a source reference."
    ),
    "no_competitor_data": (
        "Limited competitor information found. Try specifying competitor "
        "names directly in your description."
    ),
    "no_financial_data": (
        "Financial benchmarks are limited for this sector. You may want "
        "to add your own comparable company data."
    ),
    "no_traction_data": (
        "We found limited public traction data. Consider adding your own "
        "metrics (users, revenue, growth rate) for a stronger pitch."
    ),
    "stale_market_data": (
        "The market data we found is over 12 months old. For a pitch deck, "
        "consider sourcing more recent industry reports."
    ),
    "single_source_warning": (
        "Some claims rely on a single source. Cross-referencing with "
        "additional sources would strengthen credibility."
    ),
    "weak_evidence": (
        "The evidence quality for this slide is below our recommended "
        "threshold. Review the sources and consider manual enrichment."
    ),
    "debate_rejected": (
        "Key claims were challenged during our internal review process. "
        "The slide content has been adjusted to reflect only well-supported points."
    ),
    "no_evidence": (
        "We couldn't find any relevant evidence for this slide. "
        "Try adding more context to your description or providing data directly."
    ),
    "conflicting_evidence": (
        "We found conflicting data from multiple sources. "
        "The most authoritative source was used, but manual review is recommended."
    ),
}

# Required data by slide kind
_REQUIRED_DATA: dict[SlideKind, list[dict[str, str]]] = {
    SlideKind.market: [
        {"what": "Total Addressable Market (TAM)", "category": "no_market_data"},
        {"what": "Serviceable Addressable Market (SAM)", "category": "no_market_data"},
        {"what": "Market growth rate / CAGR", "category": "no_market_data"},
    ],
    SlideKind.competition: [
        {"what": "Competitor names and positioning", "category": "no_competitor_data"},
        {"what": "Competitive differentiation points", "category": "no_competitor_data"},
    ],
    SlideKind.financial: [
        {"what": "Revenue projections or benchmarks", "category": "no_financial_data"},
        {"what": "Unit economics (LTV, CAC, margins)", "category": "no_financial_data"},
    ],
    SlideKind.traction: [
        {"what": "Key metrics (users, revenue, growth)", "category": "no_traction_data"},
        {"what": "Growth trajectory data", "category": "no_traction_data"},
    ],
    SlideKind.why_now: [
        {"what": "Market timing indicators", "category": "no_market_data"},
        {"what": "Recent industry developments", "category": "no_market_data"},
    ],
}

# Suggested actions by slide kind
_ACTION_TEMPLATES: dict[SlideKind, list[str]] = {
    SlideKind.market: [
        "Add your own TAM/SAM/SOM estimates with source citations",
        "Reference a specific industry report (e.g., Gartner, IDC, Statista)",
        "Include geographic or segment-specific market data",
        "Add a 'bottom-up' market sizing calculation",
    ],
    SlideKind.competition: [
        "Name your top 3-5 competitors directly in the slide description",
        "Provide a feature comparison matrix",
        "Add links to competitor websites for automated analysis",
        "Include your key differentiators explicitly",
    ],
    SlideKind.financial: [
        "Add your own financial projections or current metrics",
        "Include comparable company benchmarks from your sector",
        "Provide unit economics breakdown (CAC, LTV, payback period)",
        "Reference public financial data from comparable companies",
    ],
    SlideKind.traction: [
        "Include your actual user/customer count and growth rate",
        "Add revenue numbers or MRR/ARR if available",
        "Provide engagement metrics (DAU/MAU, retention, NPS)",
        "List notable customers, partnerships, or milestones",
    ],
    SlideKind.why_now: [
        "Reference recent regulatory changes or market events",
        "Add technology enabler developments",
        "Include recent funding trends in your sector",
        "Cite specific articles or reports about market timing",
    ],
}


class MissingDataReporter:
    """Generates user-friendly missing data reports."""

    def report(
        self,
        slide_kind: SlideKind,
        missing: list[MissingDataItem],
        failure: Optional[SlideFailureState] = None,
    ) -> dict:
        """
        Generate a user-friendly report of missing data.

        Returns:
            {
                "slide_kind": "market",
                "severity": "critical" | "warning" | "info",
                "summary": "...",
                "missing_items": [...],
                "suggested_actions": [...],
                "user_message": "...",
                "can_proceed": True/False
            }
        """
        severity = self._compute_severity(missing, failure)
        user_message = self._pick_user_message(slide_kind, missing, failure)
        actions = self.suggest_actions(slide_kind, missing)

        # Determine if we can still proceed
        critical_count = sum(1 for m in missing if m.severity == "critical")
        can_proceed = critical_count == 0

        summary = self._build_summary(slide_kind, missing, failure, severity)

        report_dict = {
            "slide_kind": slide_kind.value,
            "severity": severity,
            "summary": summary,
            "missing_items": [m.to_dict() for m in missing],
            "suggested_actions": actions,
            "user_message": user_message,
            "can_proceed": can_proceed,
        }

        if failure:
            report_dict["failure"] = failure.to_dict()

        log_fn = logger.error if severity == "critical" else (logger.warning if severity == "warning" else logger.info)
        log_fn(
            "Missing data report for %s slide: severity=%s, missing=%d, can_proceed=%s",
            slide_kind.value,
            severity,
            len(missing),
            can_proceed,
        )

        return report_dict

    def suggest_actions(
        self,
        slide_kind: SlideKind,
        missing: list[MissingDataItem],
    ) -> list[str]:
        """Suggest specific actions the user can take."""
        actions: list[str] = []

        # Add template actions for the slide kind
        template_actions = _ACTION_TEMPLATES.get(slide_kind, [])
        actions.extend(template_actions)

        # Add actions from missing data items
        for item in missing:
            if item.how_to_get and item.how_to_get not in actions:
                actions.append(item.how_to_get)

        # Add provider-specific suggestions
        providers_tried = {item.suggested_provider for item in missing if item.suggested_provider}
        if providers_tried:
            actions.append(
                f"Alternative data sources may be available beyond "
                f"{', '.join(sorted(providers_tried))}"
            )

        # Generic fallback actions
        if not actions:
            actions = [
                "Add more details to your slide description",
                "Provide specific data points or metrics directly",
                "Include URLs to relevant sources for automated extraction",
            ]

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_actions: list[str] = []
        for action in actions:
            if action not in seen:
                seen.add(action)
                unique_actions.append(action)

        return unique_actions

    def create_failure_state(
        self,
        slide_id: str,
        failure_type: SlideFailureType,
        providers: list[str],
        partial: list[FactPacket],
        message: str,
    ) -> SlideFailureState:
        """Create a failure state with user-friendly messaging."""
        # Map failure type to user message key
        message_key_map: dict[SlideFailureType, str] = {
            SlideFailureType.no_evidence: "no_evidence",
            SlideFailureType.weak_evidence: "weak_evidence",
            SlideFailureType.conflicting_evidence: "conflicting_evidence",
            SlideFailureType.debate_rejected: "debate_rejected",
            SlideFailureType.citation_failed: "weak_evidence",
            SlideFailureType.generation_failed: "no_evidence",
        }
        msg_key = message_key_map.get(failure_type, "no_evidence")
        user_msg = message or USER_MESSAGES.get(msg_key, USER_MESSAGES["no_evidence"])

        # Build recovery actions
        user_actions: list[str] = [
            "Add more context or data to your slide description",
            "Try regenerating with a different research depth",
        ]
        if partial:
            user_actions.insert(0, f"Review the {len(partial)} partial evidence items we found")
        if failure_type == SlideFailureType.conflicting_evidence:
            user_actions.append("Manually select which data source to trust")

        return SlideFailureState(
            slide_id=slide_id,
            failure_type=failure_type,
            attempted_providers=providers,
            partial_evidence=partial,
            recovery_attempted=bool(partial),
            user_message=user_msg,
            user_actions=user_actions,
        )

    # ── Private helpers ─────────────────────────────────────────

    def _compute_severity(
        self,
        missing: list[MissingDataItem],
        failure: Optional[SlideFailureState],
    ) -> str:
        """Compute overall severity from missing items and failure state."""
        if failure and failure.failure_type in (
            SlideFailureType.no_evidence,
            SlideFailureType.generation_failed,
        ):
            return "critical"

        critical_count = sum(1 for m in missing if m.severity == "critical")
        important_count = sum(1 for m in missing if m.severity == "important")

        if critical_count > 0:
            return "critical"
        elif important_count > 0:
            return "warning"
        elif missing:
            return "info"
        else:
            return "info"

    def _pick_user_message(
        self,
        slide_kind: SlideKind,
        missing: list[MissingDataItem],
        failure: Optional[SlideFailureState],
    ) -> str:
        """Pick the most relevant user-facing message."""
        if failure and failure.user_message:
            return failure.user_message

        # Check for specific patterns
        categories = {m.what.lower() for m in missing}

        if slide_kind == SlideKind.market and any("market" in c or "tam" in c for c in categories):
            return USER_MESSAGES["no_market_data"]
        if slide_kind == SlideKind.competition and any("competitor" in c for c in categories):
            return USER_MESSAGES["no_competitor_data"]
        if slide_kind == SlideKind.financial and any("financial" in c or "revenue" in c for c in categories):
            return USER_MESSAGES["no_financial_data"]
        if slide_kind == SlideKind.traction and any("traction" in c or "metric" in c for c in categories):
            return USER_MESSAGES["no_traction_data"]

        # Severity-based fallback
        severities = {m.severity for m in missing}
        if "critical" in severities:
            return USER_MESSAGES["no_evidence"]
        elif missing:
            return USER_MESSAGES["weak_evidence"]
        else:
            return USER_MESSAGES["single_source_warning"]

    def _build_summary(
        self,
        slide_kind: SlideKind,
        missing: list[MissingDataItem],
        failure: Optional[SlideFailureState],
        severity: str,
    ) -> str:
        """Build a concise summary string."""
        parts: list[str] = []

        if failure:
            parts.append(f"Failure: {failure.failure_type.value}")
        if missing:
            critical = sum(1 for m in missing if m.severity == "critical")
            important = sum(1 for m in missing if m.severity == "important")
            nice = sum(1 for m in missing if m.severity == "nice_to_have")
            counts = []
            if critical:
                counts.append(f"{critical} critical")
            if important:
                counts.append(f"{important} important")
            if nice:
                counts.append(f"{nice} optional")
            parts.append(f"Missing data: {', '.join(counts)}")

        if not parts:
            return f"{slide_kind.value} slide: all data requirements met"

        return f"{slide_kind.value} slide [{severity}]: {'; '.join(parts)}"
