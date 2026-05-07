from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.v4.quality_metrics import (
    QualityEvent,
    evaluate_quality_alerts,
    gate_decision,
    record_quality_event,
    reset_quality_alert_state,
)


@pytest.fixture(autouse=True)
def isolate_quality_alert_state() -> None:
    reset_quality_alert_state()
    yield
    reset_quality_alert_state()


def _event(name: str, *, gate: str | None = None, severity: str = "info", metric_value: float | None = None, tags: dict | None = None) -> QualityEvent:
    return QualityEvent(
        event=name,
        project_id="project-alerts",
        gate=gate,
        severity=severity,
        metric_value=metric_value,
        tags=tags or {},
        created_at=datetime.now(timezone.utc),
    )


def test_schema_failure_rate_alert_disables_schema_gate_in_process() -> None:
    events = [_event("writer_schema_failed", gate="schema", severity="error") for _ in range(5)]

    alerts = evaluate_quality_alerts(events, auto_disable=True)

    assert any(alert.code == "schema_failure_rate_high" for alert in alerts)
    decision = gate_decision("schema", project_id="p", request_id="r")
    assert decision.enabled is False
    assert decision.reason.startswith("runtime_alert:schema_failure_rate_high")


def test_dummy_data_detector_triggers_export_block_alert() -> None:
    alerts = evaluate_quality_alerts([
        _event("no_dummy_gate_failed", gate="provenance", severity="error", metric_value=1.0, tags={"dummy_count": 1})
    ])

    assert len(alerts) == 1
    assert alerts[0].code == "dummy_data_detector_tripped"
    assert alerts[0].action == "block_export"


def test_team_resolution_budget_alert_uses_p95_latency() -> None:
    now = datetime.now(timezone.utc)
    events = [
        QualityEvent(event="team_resolution_complete", gate="provenance", metric_value=value, created_at=now - timedelta(seconds=idx))
        for idx, value in enumerate([620.0, 760.0, 940.0, 810.0])
    ]

    alerts = evaluate_quality_alerts(events)

    assert any(alert.code == "team_resolution_p95_high" and alert.metric_value and alert.metric_value > 750 for alert in alerts)


@pytest.mark.asyncio
async def test_record_quality_event_feeds_alert_window_without_requiring_database() -> None:
    for _ in range(5):
        await record_quality_event(_event("planner_schema_failed", gate="schema", severity="error"))

    decision = gate_decision("schema", project_id="project-alerts", request_id="req-alerts")
    assert decision.enabled is False
    assert "runtime_alert" in decision.reason
