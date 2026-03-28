from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from urllib.parse import urlparse
from app.core.config import get_settings
from app.core.rate_limiter import build_rate_limit_headers, evaluate_http_request
from app.db.mongo import db as mongo_db
from app.db.redis import redis_client
from app.routers import websocket, chat, upload_v2, health
from app.services.cleanup import start_scheduler
from app.services.connection_manager import manager
# from fastapi.staticfiles import StaticFiles  <-- Removed
from contextlib import asynccontextmanager
import os
import logging

logger = logging.getLogger(__name__)

settings = get_settings()
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def _uses_cookie_auth(request) -> bool:
    has_auth_cookie = bool(request.cookies.get(settings.AUTH_COOKIE_NAME, "").strip())
    has_bearer_header = bool(request.headers.get("Authorization", "").strip())
    return has_auth_cookie and not has_bearer_header


def _is_trusted_origin(origin: str | None) -> bool:
    if not origin:
        return False

    parsed_origin = urlparse(origin)
    normalized_origin = f"{parsed_origin.scheme}://{parsed_origin.netloc}"
    return normalized_origin in set(settings.BACKEND_CORS_ORIGINS)


def _validate_csrf(request) -> tuple[bool, str]:
    if request.method in _SAFE_METHODS or not _uses_cookie_auth(request):
        return True, ""

    origin = request.headers.get("Origin")
    if origin and not _is_trusted_origin(origin):
        return False, "Untrusted request origin."

    csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME, "").strip()
    csrf_header = request.headers.get(settings.CSRF_HEADER_NAME, "").strip()
    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        return False, "CSRF validation failed."

    return True, ""

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if not settings.VAPID_PUBLIC_KEY or not settings.VAPID_PRIVATE_KEY:
        logger.warning("VAPID keys are missing; web push notifications are disabled")
    try:
        await mongo_db.connect()
    except Exception as exc:
        logger.error("MongoDB startup connection failed: %s", exc)

    try:
        await redis_client.connect()
    except Exception as exc:
        logger.error("Redis startup connection failed: %s", exc)

    try:
        await manager.start_pubsub()
    except Exception as exc:
        logger.error("Chat pubsub startup failed: %s", exc)

    start_scheduler()
    yield
    # Shutdown
    try:
        await manager.stop_pubsub()
    except Exception as exc:
        logger.warning("Chat pubsub shutdown encountered a non-fatal error: %s", exc)

    await mongo_db.close()
    await redis_client.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def apply_phase_zero_rate_limit(request, call_next):
    decision = evaluate_http_request(request)
    if decision and not decision.allowed:
        response = JSONResponse(
            status_code=429,
            content={
                "detail": "Too many requests. Please slow down and try again.",
                "policy": decision.policy.name,
                "retry_after_seconds": decision.retry_after_seconds,
            },
        )
        for header_name, header_value in build_rate_limit_headers(decision).items():
            response.headers[header_name] = header_value
        return response

    csrf_valid, csrf_message = _validate_csrf(request)
    if not csrf_valid:
        response = JSONResponse(status_code=403, content={"detail": csrf_message})
        for header_name, header_value in build_rate_limit_headers(decision).items():
            response.headers[header_name] = header_value
        return response

    response = await call_next(request)
    for header_name, header_value in build_rate_limit_headers(decision).items():
        response.headers.setdefault(header_name, header_value)
    return response

# Mount Uploads - REMOVED
# UPLOAD_DIR = "uploads"
# if not os.path.exists(UPLOAD_DIR):
#    os.makedirs(UPLOAD_DIR)
# app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Routes
app.include_router(websocket.router, tags=["websocket"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(upload_v2.router, prefix="/api/chat/upload", tags=["upload"])
app.include_router(health.router, tags=["health"])
