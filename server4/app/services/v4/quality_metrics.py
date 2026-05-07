"""Plan 10 quality metrics, kill switches, and canary rollout helpers.

All helpers are best-effort and non-blocking from the caller's point of view:
quality telemetry must help us protect users, never make generation feel slow.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Mapping, Optional

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

ProgressEmit = Callable[[str, dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True)
class GateDecision:
    gate: str
    enabled: bool
    reason: str
    rollout_percent: float
    cohort_percent: float


@dataclass(frozen=True)
class QualityAlert:
    code: str
    severity: str
    message: str
    gate: Optional[str] = None
    action: str = "observe"
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    window_s: float = 120.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_doc(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QualityEvent:
    event: str
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None
    gate: Optional[str] = None
    severity: str = "info"
    metric_value: Optional[float] = None
    tags: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_doc(self) -> dict[str, Any]:
        return asdict(self)


_GATE_FLAGS: dict[str, str] = {
    "schema": "ENABLE_SCHEMA_GATE",
    "provenance": "ENABLE_PROVENANCE_GATE",
    "style": "ENABLE_STYLE_GUARD",
    "layout_rhythm": "ENABLE_LAYOUT_RHYTHM_GATE",
    "learning": "ENABLE_LEARNING_INFLUENCE",
    "image_prompt": "ENABLE_IMAGE_PROMPT_ENRICHMENT",
    "standard_routing": "ENABLE_STANDARD_ROUTING_EXPERIMENT",
}

_GATE_DEFAULT_ROLLOUT: dict[str, str] = {
    "standard_routing": "STANDARD_ROUTING_EXPERIMENT_ROLLOUT_PERCENT",
}

_RECENT_FAILURES: dict[str, list[float]] = {}
_RECENT_QUALITY_EVENTS: list[QualityEvent] = []
_RUNTIME_GATE_DISABLED_UNTIL: dict[str, tuple[float, str]] = {}

_SCHEMA_FAILURE_EVENTS = {
    "writer_schema_failed",
    "writer_schema_retry_failed",
    "writer_schema_circuit_open",
    "planner_schema_failed",
    "planner_schema_retry_failed",
    "planner_schema_circuit_open",
}
_SCHEMA_SUCCESS_EVENTS = {
    "writer_schema_retry_succeeded",
    "planner_schema_retry_succeeded",
}
_DUMMY_DATA_EVENTS = {
    "dummy_data_detected",
    "fake_data_detected",
    "export_blocked_fake_data",
    "no_dummy_gate_failed",
}


def cohort_percent(*parts: Optional[str]) -> float:
    seed = "|".join(str(p or "") for p in parts if p is not None) or "global"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]
    return int(digest, 16) / 0xFFFFFFFF * 100.0


def gate_decision(
    gate: str,
    *,
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    request_id: Optional[str] = None,
    rollout_percent: Optional[float] = None,
) -> GateDecision:
    flag_name = _GATE_FLAGS.get(gate)
    if flag_name and not bool(getattr(settings, flag_name, True)):
        return GateDecision(gate, False, f"disabled:{flag_name}", 0.0, 100.0)

    disabled = _runtime_gate_disabled_reason(gate)
    if disabled:
        return GateDecision(gate, False, f"runtime_alert:{disabled}", 0.0, 100.0)

    if rollout_percent is None:
        rollout_field = _GATE_DEFAULT_ROLLOUT.get(gate)
        if rollout_field:
            rollout_percent = float(getattr(settings, rollout_field, 0.0))
        else:
            rollout_percent = float(getattr(settings, "QUALITY_GATE_ROLLOUT_PERCENT", 100.0))
    rollout = max(0.0, min(100.0, float(rollout_percent)))
    cohort = cohort_percent(gate, tenant_id, user_id, project_id, request_id)
    enabled = cohort < rollout
    reason = "enabled" if enabled else "outside_canary"
    return GateDecision(gate, enabled, reason, rollout, cohort)


def record_failure_window(key: str, *, window_s: float = 120.0) -> int:
    now = time.monotonic()
    entries = [t for t in _RECENT_FAILURES.get(key, []) if now - t <= window_s]
    entries.append(now)
    _RECENT_FAILURES[key] = entries
    return len(entries)


def circuit_open(key: str, *, threshold: int = 3, window_s: float = 120.0) -> bool:
    now = time.monotonic()
    entries = [t for t in _RECENT_FAILURES.get(key, []) if now - t <= window_s]
    _RECENT_FAILURES[key] = entries
    return len(entries) >= threshold


def _runtime_gate_disabled_reason(gate: str) -> Optional[str]:
    disabled = _RUNTIME_GATE_DISABLED_UNTIL.get(gate)
    if not disabled:
        return None
    expires_at, reason = disabled
    if time.monotonic() >= expires_at:
        _RUNTIME_GATE_DISABLED_UNTIL.pop(gate, None)
        return None
    return reason


def disable_gate_for_process(gate: str, reason: str, *, ttl_s: float = 600.0) -> None:
    _RUNTIME_GATE_DISABLED_UNTIL[gate] = (time.monotonic() + ttl_s, reason)


def reset_quality_alert_state() -> None:
    _RECENT_QUALITY_EVENTS.clear()
    _RUNTIME_GATE_DISABLED_UNTIL.clear()
    _RECENT_FAILURES.clear()


def _value(doc: QualityEvent | Mapping[str, Any], key: str, default: Any = None) -> Any:
    if isinstance(doc, QualityEvent):
        return getattr(doc, key, default)
    return doc.get(key, default)


def _tags(doc: QualityEvent | Mapping[str, Any]) -> Mapping[str, Any]:
    value = _value(doc, "tags", {})
    return value if isinstance(value, Mapping) else {}


def _payload(doc: QualityEvent | Mapping[str, Any]) -> Mapping[str, Any]:
    value = _value(doc, "payload", {})
    return value if isinstance(value, Mapping) else {}


def _created_at(doc: QualityEvent | Mapping[str, Any]) -> datetime:
    value = _value(doc, "created_at")
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[index]


def _numeric_hint(doc: QualityEvent | Mapping[str, Any], *keys: str) -> Optional[float]:
    candidates: list[Any] = [_value(doc, "metric_value")]
    tags = _tags(doc)
    payload = _payload(doc)
    for key in keys:
        candidates.append(tags.get(key))
        candidates.append(payload.get(key))
    for candidate in candidates:
        if isinstance(candidate, (int, float)):
            return float(candidate)
    return None


def evaluate_quality_alerts(
    events: list[QualityEvent | Mapping[str, Any]],
    *,
    now: Optional[datetime] = None,
    window_s: float = 120.0,
    auto_disable: bool = False,
) -> list[QualityAlert]:
    current = now or datetime.now(timezone.utc)
    cutoff = current.timestamp() - window_s
    window = [e for e in events if _created_at(e).timestamp() >= cutoff]
    alerts: list[QualityAlert] = []

    schema_events = [
        e for e in window
        if _value(e, "gate") == "schema"
        or _value(e, "event") in _SCHEMA_FAILURE_EVENTS
        or _value(e, "event") in _SCHEMA_SUCCESS_EVENTS
    ]
    schema_failures = [e for e in schema_events if _value(e, "event") in _SCHEMA_FAILURE_EVENTS or _value(e, "severity") == "error"]
    if len(schema_events) >= 5:
        failure_rate = len(schema_failures) / max(len(schema_events), 1) * 100.0
        if failure_rate >= 90.0:
            alerts.append(QualityAlert(
                code="schema_failure_rate_high",
                severity="critical",
                gate="schema",
                message="Schema gate failure rate exceeded 90% in the rolling production window.",
                action="disable_gate:schema",
                metric_value=round(failure_rate, 2),
                threshold=90.0,
                window_s=window_s,
                created_at=current,
            ))
            if auto_disable:
                disable_gate_for_process("schema", "schema_failure_rate_high")

    for event in window:
        name = str(_value(event, "event", ""))
        if name in _DUMMY_DATA_EVENTS or _numeric_hint(event, "dummy_count", "fake_count", "unsupported_fake_count"):
            alerts.append(QualityAlert(
                code="dummy_data_detector_tripped",
                severity="critical",
                gate="provenance",
                message="A no-dummy-data detector reported user-visible fake or placeholder content.",
                action="block_export",
                metric_value=_numeric_hint(event, "dummy_count", "fake_count", "unsupported_fake_count") or 1.0,
                threshold=0.0,
                window_s=window_s,
                created_at=current,
            ))
            break

    team_samples = [
        float(_value(e, "metric_value"))
        for e in window
        if _value(e, "event") == "team_resolution_complete" and isinstance(_value(e, "metric_value"), (int, float))
    ]
    if len(team_samples) >= 3:
        p95 = _percentile(team_samples, 95.0)
        if p95 > 750.0:
            alerts.append(QualityAlert(
                code="team_resolution_p95_high",
                severity="warn",
                gate="provenance",
                message="Team resolution p95 exceeded the real-time budget; unresolved team fallback remains required.",
                action="keep_unresolved_team_fallback",
                metric_value=round(p95, 2),
                threshold=750.0,
                window_s=window_s,
                created_at=current,
            ))

    generation_samples = [
        e for e in window
        if _value(e, "event") == "generation_latency_ms" and isinstance(_value(e, "metric_value"), (int, float))
    ]
    regression_values: list[float] = []
    for event in generation_samples:
        baseline = _numeric_hint(event, "baseline_ms")
        current_value = _numeric_hint(event)
        if baseline and current_value and baseline > 0:
            regression_values.append((current_value - baseline) / baseline * 100.0)
    if regression_values:
        p95_regression = _percentile(regression_values, 95.0)
        if p95_regression > 20.0:
            alerts.append(QualityAlert(
                code="generation_latency_regression",
                severity="warn",
                message="Generation latency regressed by more than 20% against the recorded baseline.",
                action="hold_rollout",
                metric_value=round(p95_regression, 2),
                threshold=20.0,
                window_s=window_s,
                created_at=current,
            ))
    return alerts


def _record_event_for_alerts(event: QualityEvent) -> list[QualityAlert]:
    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - 120.0
    _RECENT_QUALITY_EVENTS[:] = [e for e in _RECENT_QUALITY_EVENTS if e.created_at.timestamp() >= cutoff]
    _RECENT_QUALITY_EVENTS.append(event)
    return evaluate_quality_alerts(_RECENT_QUALITY_EVENTS, now=now, auto_disable=True)


async def record_quality_event(event: QualityEvent) -> None:
    alerts = _record_event_for_alerts(event)
    doc = event.to_doc()
    log_doc = {k: v for k, v in doc.items() if k != "payload"}
    log_doc["event_name"] = log_doc.pop("event", event.event)
    logger.info("v4_quality_metric", **log_doc)
    for alert in alerts:
        logger.warning("v4_quality_alert", **alert.to_doc())
    try:
        from app.database import get_db, is_db_initialized

        if not is_db_initialized():
            return
        db = get_db()
        await db[settings.QUALITY_METRICS_COLLECTION].insert_one(doc)
    except Exception as exc:  # noqa: BLE001
        logger.debug("v4_quality_metric_persist_skipped", event=event.event, error=str(exc))


async def emit_quality_event(
    emit: Optional[ProgressEmit],
    event: QualityEvent,
) -> None:
    await record_quality_event(event)
    if emit is None:
        return
    try:
        payload = event.to_doc()
        payload["created_at"] = event.created_at.isoformat()
        await emit("quality_metric", payload)
    except Exception as exc:  # noqa: BLE001
        logger.debug("v4_quality_metric_emit_skipped", event=event.event, error=str(exc))


class QualityMetricsRecorder:
    def __init__(
        self,
        *,
        project_id: Optional[str],
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        request_id: Optional[str] = None,
        emit: Optional[ProgressEmit] = None,
    ) -> None:
        self.project_id = project_id
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.request_id = request_id or project_id
        self.emit = emit

    def gate(self, gate: str, *, rollout_percent: Optional[float] = None) -> GateDecision:
        return gate_decision(
            gate,
            project_id=self.project_id,
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            request_id=self.request_id,
            rollout_percent=rollout_percent,
        )

    async def event(
        self,
        name: str,
        *,
        gate: Optional[str] = None,
        severity: str = "info",
        metric_value: Optional[float] = None,
        tags: Optional[dict[str, Any]] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> None:
        await emit_quality_event(
            self.emit,
            QualityEvent(
                event=name,
                project_id=self.project_id,
                user_id=self.user_id,
                tenant_id=self.tenant_id,
                request_id=self.request_id,
                gate=gate,
                severity=severity,
                metric_value=metric_value,
                tags=tags or {},
                payload=payload or {},
            ),
        )