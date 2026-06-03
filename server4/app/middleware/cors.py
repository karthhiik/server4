"""CORS configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import LOCALHOST_CORS_ORIGINS, settings


def setup_cors(app: FastAPI) -> None:
    origins = list(LOCALHOST_CORS_ORIGINS)
    allow_origin_regex = None
    if settings.ENVIRONMENT == "production":
        origins.extend([
            "https://barise.in",
            "https://www.barise.in",
            "https://app.barise.in",
        ])
    else:
        allow_origin_regex = (
            r"^https?://("
            r"localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|"
            r"10(?:\.\d{1,3}){3}|"
            r"192\.168(?:\.\d{1,3}){2}|"
            r"172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}"
            r")(?::\d+)?$"
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
