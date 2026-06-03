"""Rule-based chart selection for V4 structured data."""

from __future__ import annotations


CHART_SELECTION_RULES: dict[str, str] = {
    "growth_over_time": "line",
    "category_comparison": "bar",
    "market_share": "stacked_bar",
    "composition": "pie",
    "unit_economics": "waterfall",
    "customer_journey": "journey_map",
}


def select_chart_type(intent: str, labels: list[str] | None = None, values: list[float] | None = None) -> str:
    text = (intent or "").lower()
    labels = labels or []
    if any(word in text for word in ("growth", "traction", "trend", "over time", "forecast")):
        return CHART_SELECTION_RULES["growth_over_time"]
    if any(word in text for word in ("share", "composition", "mix")):
        return CHART_SELECTION_RULES["composition"]
    if any(word in text for word in ("unit", "economics", "waterfall")):
        return CHART_SELECTION_RULES["unit_economics"]
    if len(labels) >= 2:
        return CHART_SELECTION_RULES["category_comparison"]
    return "bar"
