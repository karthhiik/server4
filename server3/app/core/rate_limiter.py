import math
import time
from dataclasses import dataclass
from threading import Lock

from fastapi import Request, WebSocket

from app.core.config import get_settings

settings = get_settings()


@dataclass(frozen=True)
class RateLimitPolicy:
    name: str
    capacity: int
    refill_per_minute: int


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    policy: RateLimitPolicy
    remaining: int
    retry_after_seconds: int


class TokenBucketLimiter:
    def __init__(self) -> None:
        self._lock = Lock()
        self._buckets: dict[str, dict[str, float]] = {}

    def consume(self, key: str, policy: RateLimitPolicy) -> RateLimitDecision:
        now = time.monotonic()
        refill_per_second = policy.refill_per_minute / 60.0

        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = {"tokens": float(policy.capacity), "updated_at": now}
            else:
                elapsed = max(0.0, now - bucket["updated_at"])
                bucket["tokens"] = min(
                    float(policy.capacity),
                    bucket["tokens"] + (elapsed * refill_per_second),
                )
                bucket["updated_at"] = now

            allowed = bucket["tokens"] >= 1.0
            if allowed:
                bucket["tokens"] -= 1.0

            self._buckets[key] = bucket
            remaining = max(0, int(bucket["tokens"]))
            retry_after_seconds = 0
            if not allowed:
                retry_after_seconds = (
                    60
                    if refill_per_second <= 0
                    else max(1, math.ceil((1.0 - bucket["tokens"]) / refill_per_second))
                )

        return RateLimitDecision(
            allowed=allowed,
            policy=policy,
            remaining=remaining,
            retry_after_seconds=retry_after_seconds,
        )


_limiter = TokenBucketLimiter()

_DEFAULT_POLICY = RateLimitPolicy(
    name="default",
    capacity=settings.RATE_LIMIT_DEFAULT_PER_MINUTE,
    refill_per_minute=settings.RATE_LIMIT_DEFAULT_PER_MINUTE,
)
_AUTH_POLICY = RateLimitPolicy(
    name="auth",
    capacity=settings.RATE_LIMIT_AUTH_PER_MINUTE,
    refill_per_minute=settings.RATE_LIMIT_AUTH_PER_MINUTE,
)
_HEAVY_POLICY = RateLimitPolicy(
    name="heavy",
    capacity=settings.RATE_LIMIT_HEAVY_PER_MINUTE,
    refill_per_minute=settings.RATE_LIMIT_HEAVY_PER_MINUTE,
)
_UPLOAD_POLICY = RateLimitPolicy(
    name="upload",
    capacity=settings.RATE_LIMIT_UPLOAD_PER_MINUTE,
    refill_per_minute=settings.RATE_LIMIT_UPLOAD_PER_MINUTE,
)
_WEBSOCKET_POLICY = RateLimitPolicy(
    name="websocket_connect",
    capacity=settings.RATE_LIMIT_WS_CONNECT_PER_MINUTE,
    refill_per_minute=settings.RATE_LIMIT_WS_CONNECT_PER_MINUTE,
)

_EXEMPT_PREFIXES = ("/docs", "/redoc", "/openapi.json")
_AUTH_HINTS = ("/login", "/register", "/token", "/auth")
_HEAVY_HINTS = ("/api/chat", "/api/chat/upload", "/api/report", "/api/chat/export")
_UPLOAD_HINTS = ("/upload",)


def _client_ip(headers, fallback: str | None) -> str:
    forwarded_for = headers.get("cf-connecting-ip") or headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return fallback or "unknown"


def _policy_for_path(path: str) -> RateLimitPolicy | None:
    normalized_path = path.lower()
    if normalized_path.startswith(_EXEMPT_PREFIXES):
        return None
    if any(hint in normalized_path for hint in _AUTH_HINTS):
        return _AUTH_POLICY
    if any(hint in normalized_path for hint in _UPLOAD_HINTS):
        return _UPLOAD_POLICY
    if any(hint in normalized_path for hint in _HEAVY_HINTS):
        return _HEAVY_POLICY
    return _DEFAULT_POLICY


def evaluate_http_request(request: Request) -> RateLimitDecision | None:
    if not settings.RATE_LIMIT_ENABLED or request.method == "OPTIONS":
        return None

    policy = _policy_for_path(request.url.path)
    if policy is None:
        return None

    client_key = _client_ip(request.headers, request.client.host if request.client else None)
    return _limiter.consume(f"http:{policy.name}:{client_key}", policy)


def evaluate_websocket_connection(websocket: WebSocket) -> RateLimitDecision | None:
    if not settings.RATE_LIMIT_ENABLED:
        return None

    client_key = _client_ip(
        websocket.headers,
        websocket.client.host if websocket.client else None,
    )
    return _limiter.consume(f"ws:{client_key}", _WEBSOCKET_POLICY)


def build_rate_limit_headers(decision: RateLimitDecision | None) -> dict[str, str]:
    if decision is None:
        return {}

    headers = {
        "X-RateLimit-Policy": decision.policy.name,
        "X-RateLimit-Limit": str(decision.policy.capacity),
        "X-RateLimit-Remaining": str(decision.remaining),
    }
    if not decision.allowed:
        headers["Retry-After"] = str(decision.retry_after_seconds)
    return headers
