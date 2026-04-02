"""CORS configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import LOCALHOST_CORS_ORIGINS, settings


def setup_cors(app: FastAPI) -> None:
    origins = list(LOCALHOST_CORS_ORIGINS)
    if settings.ENVIRONMENT == "production":
        origins.extend([
            "https://barise.in",
            "https://www.barise.in",
            "https://app.barise.in",
        ])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
