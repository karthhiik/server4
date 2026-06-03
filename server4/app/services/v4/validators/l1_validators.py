"""Fast deterministic validators for compiled V4 slides."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class L1ValidationIssue:
    code: str
    severity: str
    message: str
    target: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "target": self.target,
        }


@dataclass(frozen=True)
class L1ValidationReport:
    passed: bool
    issues: list[L1ValidationIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def validate_compiled_slide(compiled: Mapping[str, Any]) -> L1ValidationReport:
    issues: list[L1ValidationIssue] = []
    props = _props(compiled)
    kit = str(compiled.get("kit_component") or "")
    composition = compiled.get("composition_plan") or {}

    if not kit:
        issues.append(_issue("missing_kit", "error", "Compiled slide has no kit component.", "kit_component"))
    if not props:
        issues.append(_issue("missing_props", "error", "Compiled slide has no canonical props.", "artifacts.kit_jsx.props_json"))

    headline = str(props.get("headline") or props.get("title") or "").strip()
    if not headline:
        issues.append(_issue("missing_headline", "error", "Slide is missing a visible headline.", "headline"))
    elif len(headline) > 140:
        issues.append(_issue("headline_overflow_risk", "warn", "Headline is likely too long for projector-safe rendering.", "headline"))

    visible_words = _visible_word_count(props)
    if visible_words > 120:
        issues.append(_issue("text_density_high", "warn", "Slide has too much visible text for a single executive slide.", "props"))

    chart = props.get("chart")
    if kit == "ChartBlock" or isinstance(chart, Mapping):
        _validate_chart(chart if isinstance(chart, Mapping) else props, issues)

    rows = props.get("rows")
    if isinstance(rows, list) and len(rows) > 5:
        issues.append(_issue("table_too_many_rows", "warn", "Table-like slide exceeds 5 rows.", "rows"))

    slots = composition.get("slots") if isinstance(composition, Mapping) else None
    if isinstance(slots, list):
        _validate_slots(slots, issues)

    return L1ValidationReport(
        passed=not any(issue.severity == "error" for issue in issues),
        issues=issues,
    )


def _props(compiled: Mapping[str, Any]) -> Mapping[str, Any]:
    artifacts = compiled.get("artifacts")
    if isinstance(artifacts, Mapping):
        kit_artifact = artifacts.get("kit_jsx")
        if isinstance(kit_artifact, Mapping):
            props = kit_artifact.get("props_json")
            if isinstance(props, Mapping):
                return props
    return {}


def _visible_word_count(value: Any) -> int:
    if isinstance(value, str):
        return len(value.split())
    if isinstance(value, Mapping):
        return sum(_visible_word_count(v) for k, v in value.items() if k not in {"designTokens", "imageUrl", "watermark", "sources"})
    if isinstance(value, list):
        return sum(_visible_word_count(v) for v in value)
    return 0


def _validate_chart(chart: Any, issues: list[L1ValidationIssue]) -> None:
    if not isinstance(chart, Mapping):
        issues.append(_issue("chart_missing", "error", "Chart slide has no chart object.", "chart"))
        return
    data = chart.get("data")
    if not isinstance(data, list) or not data:
        issues.append(_issue("chart_data_missing", "error", "Chart has no data rows.", "chart.data"))
        return
    for i, row in enumerate(data[:12]):
        if not isinstance(row, Mapping):
            issues.append(_issue("chart_row_invalid", "error", "Chart data row is not an object.", f"chart.data[{i}]"))
            continue
        if "label" not in row:
            issues.append(_issue("chart_label_missing", "warn", "Chart data row is missing a label.", f"chart.data[{i}].label"))
        if "value" not in row:
            issues.append(_issue("chart_value_missing", "error", "Chart data row is missing a value.", f"chart.data[{i}].value"))


def _validate_slots(slots: list[Any], issues: list[L1ValidationIssue]) -> None:
    for i, slot in enumerate(slots):
        if not isinstance(slot, Mapping):
            issues.append(_issue("slot_invalid", "error", "Composition slot is not an object.", f"slots[{i}]"))
            continue
        for key in ("x_pct", "y_pct", "width_pct", "height_pct"):
            value = slot.get(key)
            if not isinstance(value, (int, float)):
                issues.append(_issue("slot_metric_missing", "error", f"Slot missing numeric {key}.", f"slots[{i}].{key}"))
        x = float(slot.get("x_pct", 0) or 0)
        y = float(slot.get("y_pct", 0) or 0)
        w = float(slot.get("width_pct", 0) or 0)
        h = float(slot.get("height_pct", 0) or 0)
        if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > 100 or y + h > 100:
            issues.append(_issue("slot_out_of_bounds", "error", "Composition slot exceeds virtual canvas bounds.", f"slots[{i}]"))


def _issue(code: str, severity: str, message: str, target: str) -> L1ValidationIssue:
    return L1ValidationIssue(code=code, severity=severity, message=message, target=target)
