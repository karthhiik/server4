"""
LLM Error Classifier — maps raw provider exceptions to dispatch classes.

Why:
    The existing router retries blindly on any exception. That wastes seconds
    on RATE_LIMIT (we should skip the model and mark the bucket) and on AUTH
    (we should mark the model dead for the process).

Public API:
    classify(exc) -> ErrorClass           # main entry point
    ErrorClass                            # enum the router dispatches on
    parse_retry_after(exc) -> float|None  # best-effort Retry-After seconds

This module has zero runtime dependencies on the clients it inspects. It uses
duck-typing on attribute names (`status_code`, `response.status_code`, the
exception's `str()` form). That keeps it decoupled from OpenAI/httpx version
bumps.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Optional


class ErrorClass(str, Enum):
    """Dispatch classes for per-error routing decisions."""

    TRANSIENT     = "transient"       # 5xx / connection reset / read timeout
    RATE_LIMIT    = "rate_limit"      # 429
    QUOTA_DAILY   = "quota_daily"     # hard quota (e.g. OpenRouter "insufficient_quota")
    AUTH          = "auth"            # 401 / 403
    BAD_REQUEST   = "bad_request"     # 400 / context-length / unsupported param
    MODEL_ERROR   = "model_error"     # refusal, empty output, truncated JSON
    TIMEOUT       = "timeout"         # asyncio.TimeoutError
    UNKNOWN       = "unknown"


# ── Status-code buckets ────────────────────────────────────────────

_AUTH_STATUSES = {401, 403}
_BAD_REQUEST_STATUSES = {400, 404, 422}
_RATE_LIMIT_STATUSES = {429}
_TRANSIENT_STATUSES = {500, 502, 503, 504, 507, 508, 525}


# ── String-pattern detectors ───────────────────────────────────────

_QUOTA_PATTERNS = (
    "insufficient_quota",
    "quota exceeded",
    "quota_exceeded",
    "exceeded your current quota",
    "monthly limit",
    "daily limit",
    "you exceeded",
    "no credits",
    "credits exhausted",
)

_BAD_REQUEST_PATTERNS = (
    "context_length_exceeded",
    "maximum context length",
    "too many tokens",
    "invalid_request_error",
    "unsupported_parameter",
    "content filter",
    "content_filter",
    "responsible ai",
)

_MODEL_ERROR_PATTERNS = (
    "empty response content",
    "no completion returned",
    "i can't help with",
    "i cannot assist",
    "response truncated",
    "invalid json",
    "finish_reason=length",
)

_TRANSIENT_PATTERNS = (
    "connection reset",
    "connection aborted",
    "connection refused",
    "read timed out",
    "temporarily unavailable",
    "service unavailable",
    "bad gateway",
    "gateway timeout",
    "remote end closed",
    "server disconnected",
)


def _extract_status(exc: BaseException) -> Optional[int]:
    # openai.APIStatusError, httpx.HTTPStatusError, aiohttp.ClientResponseError
    for attr in ("status_code", "status", "code"):
        v = getattr(exc, attr, None)
        if isinstance(v, int) and 100 <= v < 600:
            return v
    resp = getattr(exc, "response", None)
    if resp is not None:
        for attr in ("status_code", "status"):
            v = getattr(resp, attr, None)
            if isinstance(v, int) and 100 <= v < 600:
                return v
    return None


def _match_any(text: str, patterns: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(p in low for p in patterns)


def classify(exc: BaseException) -> ErrorClass:
    """Return the ErrorClass for a raised exception.

    Order: TimeoutError → status code → string patterns → UNKNOWN.
    """
    import asyncio

    if isinstance(exc, asyncio.TimeoutError):
        return ErrorClass.TIMEOUT

    status = _extract_status(exc)
    text = f"{type(exc).__name__}: {exc}"

    if status is not None:
        if status in _AUTH_STATUSES:
            return ErrorClass.AUTH
        if status in _RATE_LIMIT_STATUSES:
            # Some providers return 429 for daily-quota — disambiguate.
            if _match_any(text, _QUOTA_PATTERNS):
                return ErrorClass.QUOTA_DAILY
            return ErrorClass.RATE_LIMIT
        if status in _BAD_REQUEST_STATUSES:
            return ErrorClass.BAD_REQUEST
        if status in _TRANSIENT_STATUSES:
            return ErrorClass.TRANSIENT

    if _match_any(text, _QUOTA_PATTERNS):
        return ErrorClass.QUOTA_DAILY
    if _match_any(text, _BAD_REQUEST_PATTERNS):
        return ErrorClass.BAD_REQUEST
    if _match_any(text, _MODEL_ERROR_PATTERNS):
        return ErrorClass.MODEL_ERROR
    if _match_any(text, _TRANSIENT_PATTERNS):
        return ErrorClass.TRANSIENT

    # ValueError on empty content etc. are MODEL_ERROR not UNKNOWN
    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return ErrorClass.MODEL_ERROR

    return ErrorClass.UNKNOWN


def parse_retry_after(exc: BaseException) -> Optional[float]:
    """Extract Retry-After seconds from a 429/503 response when present."""
    # Direct header access (httpx / aiohttp)
    resp = getattr(exc, "response", None)
    if resp is not None:
        headers = getattr(resp, "headers", None)
        if headers:
            ra = None
            try:
                ra = headers.get("retry-after") or headers.get("Retry-After")
            except Exception:  # noqa: BLE001
                ra = None
            if ra:
                try:
                    return max(0.0, float(ra))
                except ValueError:
                    pass
    # String mine for "retry after Ns" / "try again in Ns"
    text = str(exc)
    m = re.search(r"(?:retry[-\s]?after|try again in)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(m?s|seconds?|minutes?)?",
                  text, re.IGNORECASE)
    if m:
        val = float(m.group(1))
        unit = (m.group(2) or "").lower()
        if unit.startswith("min"):
            val *= 60.0
        elif unit in ("ms",):
            val /= 1000.0
        return val
    return None


# Cache / skip duration per ErrorClass (seconds). Read by the router.
SKIP_DURATIONS: dict[ErrorClass, float] = {
    ErrorClass.RATE_LIMIT:  30.0,   # default if no Retry-After header
    ErrorClass.QUOTA_DAILY: 0.0,    # handled separately — skip until 00:00 UTC
    ErrorClass.AUTH:        0.0,    # handled separately — permanent process-local
    ErrorClass.TRANSIENT:   0.0,    # no skip — retry next call
    ErrorClass.BAD_REQUEST: 0.0,    # no skip — truncate+retry once
    ErrorClass.MODEL_ERROR: 0.0,
    ErrorClass.TIMEOUT:     0.0,
    ErrorClass.UNKNOWN:     0.0,
}


def is_retryable_same_model(err_class: ErrorClass) -> bool:
    """Should safe_complete retry the same model once before moving on?"""
    return err_class in (ErrorClass.TRANSIENT, ErrorClass.UNKNOWN)


def should_skip_model(err_class: ErrorClass) -> bool:
    """Should the router skip this model for the current process / bucket?"""
    return err_class in (
        ErrorClass.RATE_LIMIT,
        ErrorClass.QUOTA_DAILY,
        ErrorClass.AUTH,
    )


__all__ = [
    "ErrorClass",
    "classify",
    "parse_retry_after",
    "SKIP_DURATIONS",
    "is_retryable_same_model",
    "should_skip_model",
]
