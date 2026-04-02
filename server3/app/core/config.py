import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def _env_first(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is None:
            continue
        return value.strip().strip('"').strip("'")
    return None


def _env_str(*names: str, default: str) -> str:
    value = _env_first(*names)
    return default if value is None else value


def _env_optional(*names: str) -> str | None:
    value = _env_first(*names)
    return value or None


def _env_bool(*names: str, default: bool) -> bool:
    value = _env_first(*names)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_int(*names: str, default: int) -> int:
    value = _env_first(*names)
    if value is None or value == "":
        return default
    return int(value)


def _default_instance_id() -> str:
    website_instance = os.getenv("WEBSITE_INSTANCE_ID", "").strip()
    hostname = os.getenv("HOSTNAME", "").strip()
    if website_instance:
        return website_instance
    if hostname:
        return hostname
    return f"server3-{os.getpid()}"


def _split_origins(raw_value: str) -> list[str]:
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


LOCALHOST_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]


class Settings(BaseSettings):
    PROJECT_NAME: str = _env_str("PROJECT_NAME", default="Barise Chat Server")
    VERSION: str = _env_str("VERSION", default="1.0.0")
    API_V1_STR: str = _env_str("API_V1_STR", default="/api/v1")
    ENVIRONMENT: str = _env_str("ENVIRONMENT", default="production")

    SECRET_KEY: str = _env_str("BARISE_JWT_SECRET_KEY", "SECRET_KEY", default="local-dev-secret-change-me")
    ALGORITHM: str = _env_str("ALGORITHM", default="HS256")
    ENCRYPTION_ENABLED: bool = _env_bool("ENCRYPTION_ENABLED", default=False)
    ENCRYPTION_MASTER_KEY: str = _env_str("ENCRYPTION_MASTER_KEY", default="local-dev-encryption-key-change-me")
    ENCRYPTION_KEY_VERSION: str = _env_str("ENCRYPTION_KEY_VERSION", default="v1")
    AUTH_COOKIE_NAME: str = _env_str("AUTH_COOKIE_NAME", default="jwt_token")
    CSRF_COOKIE_NAME: str = _env_str("CSRF_COOKIE_NAME", default="csrf_token")
    CSRF_HEADER_NAME: str = _env_str("CSRF_HEADER_NAME", default="X-CSRF-Token")
    AUTH_COOKIE_SECURE: bool = _env_bool("AUTH_COOKIE_SECURE", default=False)
    AUTH_COOKIE_SAMESITE: str = _env_str("AUTH_COOKIE_SAMESITE", default="Lax")
    AUTH_COOKIE_DOMAIN: str | None = _env_optional("AUTH_COOKIE_DOMAIN")

    MONGO_URI: str = _env_str("MONGO_URI", "MONGODB_URI", default="mongodb://localhost:27017")
    DATABASE_NAME: str = _env_str("DATABASE_NAME", default="barise_chat_db")
    COMMUNITY_DB_NAME: str = _env_str("COMMUNITY_DB_NAME", default="barise_auth_db")

    REDIS_HOST: str = _env_str("REDIS_HOST", "AZURE_REDIS_HOST", default="localhost")
    REDIS_PORT: int = _env_int("REDIS_PORT", "AZURE_REDIS_PORT", default=6379)
    REDIS_PASSWORD: str | None = _env_optional("REDIS_PASSWORD", "AZURE_REDIS_PASSWORD")
    REDIS_SSL: bool = _env_bool("REDIS_SSL", "AZURE_REDIS_SSL", default=True)
    REDIS_DB: int = _env_int("REDIS_DB", default=0)

    BLOB_STORAGE_CONNECTION_STRING: str = _env_str("BLOB_STORAGE_CONNECTION_STRING", default="")
    BLOB_CONTAINER_NAME: str = _env_str("BLOB_CONTAINER_NAME", default="blobpitchdeckstorage")

    BACKEND_CORS_ORIGINS_RAW: str = _env_str(
        "BACKEND_CORS_ORIGINS",
        default="https://ai.barise.in,https://barise.in",
    )

    API_BASE_URL3: str = _env_str("API_BASE_URL3", default="https://ai.barise.in")
    COMMUNITY_ASSET_BASE_URL: str = _env_str(
        "COMMUNITY_ASSET_BASE_URL",
        "API_BASE_URL2",
        default="https://ai.barise.in",
    )

    VAPID_PUBLIC_KEY: str = _env_str("VAPID_PUBLIC_KEY", default="")
    VAPID_PRIVATE_KEY: str = _env_str("VAPID_PRIVATE_KEY", default="")
    VAPID_SUBJECT: str = _env_str("VAPID_SUBJECT", default="mailto:admin@barise.local")

    RATE_LIMIT_ENABLED: bool = _env_bool("RATE_LIMIT_ENABLED", default=True)
    RATE_LIMIT_DEFAULT_PER_MINUTE: int = _env_int("RATE_LIMIT_DEFAULT_PER_MINUTE", default=240)
    RATE_LIMIT_AUTH_PER_MINUTE: int = _env_int("RATE_LIMIT_AUTH_PER_MINUTE", default=30)
    RATE_LIMIT_HEAVY_PER_MINUTE: int = _env_int("RATE_LIMIT_HEAVY_PER_MINUTE", default=30)
    RATE_LIMIT_UPLOAD_PER_MINUTE: int = _env_int("RATE_LIMIT_UPLOAD_PER_MINUTE", default=60)
    RATE_LIMIT_WS_CONNECT_PER_MINUTE: int = _env_int("RATE_LIMIT_WS_CONNECT_PER_MINUTE", default=20)

    # FASTAPI_COMMUNITY Internal API for cross-server communication (DEPRECATED)
    FASTAPI_COMMUNITY_URL: str = _env_str("FASTAPI_COMMUNITY_URL", default="http://localhost:8002")
    INTERNAL_API_TOKEN: str = _env_str("INTERNAL_API_TOKEN", default="")

    # Email Configuration (Direct Brevo Integration)
    MAIL_SERVER: str = _env_str("MAIL_SERVER", default="smtp-relay.brevo.com")
    MAIL_PORT: int = _env_int("MAIL_PORT", default=587)
    MAIL_USE_TLS: bool = _env_bool("MAIL_USE_TLS", default=True)
    MAIL_USERNAME: str = _env_str("MAIL_USERNAME", default="")
    MAIL_PASSWORD: str = _env_str("MAIL_PASSWORD", default="")
    MAIL_API_KEY: str = _env_str("MAIL_API_KEY", default="")
    MAIL_SENDER_EMAIL: str = _env_str("MAIL_SENDER_EMAIL", default="barisebot@gmail.com")
    MAIL_SENDER_NAME: str = _env_str("MAIL_SENDER_NAME", default="Barise Community")
    EMAIL_DAILY_QUOTA: int = _env_int("EMAIL_DAILY_QUOTA", default=300)
    EMAIL_RATE_LIMIT_ENABLED: bool = _env_bool("EMAIL_RATE_LIMIT_ENABLED", default=True)
    MAILJET_API_KEY: str = _env_str("mailjet_api_key", "MAILJET_API_KEY", default="")
    MAILJET_SECRET_KEY: str = _env_str("mailjet_secret_key", "MAILJET_SECRET_KEY", default="")
    MAILJET_SENDER_MAIL: str = _env_str(
        "mailjet_sender_mail", "MAILJET_SENDER_MAIL", default=""
    )
    MAILJET_SENDER_NAME: str = _env_str(
        "mailjet_sender_name",
        "MAILJET_SENDER_NAME",
        default="Barise Community",
    )
    MAILJET_DAILY_QUOTA: int = _env_int("MAILJET_DAILY_QUOTA", default=200)
    MAILJET_RATE_LIMIT_ENABLED: bool = _env_bool(
        "MAILJET_RATE_LIMIT_ENABLED", default=True
    )
    EMAIL_PROVIDER_CHAT_PRIMARY: str = _env_str(
        "EMAIL_PROVIDER_CHAT_PRIMARY", default="brevo"
    )
    EMAIL_PROVIDER_CHAT_FALLBACK: str = _env_str(
        "EMAIL_PROVIDER_CHAT_FALLBACK", default="mailjet"
    )

    # LLM Configuration (Mistral via Azure OpenAI)
    MISTRAL_ENDPOINT: str = _env_str("MISTRAL_ENDPOINT", default="")
    MISTRAL_DEPLOYMENT_NAME: str = _env_str("MISTRAL_DEPLOYMENT_NAME", default="mistral-medium-2505")
    MISTRAL_API_KEY: str = _env_str("MISTRAL_API_KEY", default="")

    # Frontend URL for email links
    FRONTEND_URL: str = _env_str("FRONTEND_URL", default="https://ai.barise.in")
    BARISE_EMAIL_LOGO_URL: str = _env_str(
        "BARISE_EMAIL_LOGO_URL", default=""
    )

    # Realtime chat presence and notification controls
    CHAT_SERVER_INSTANCE_ID: str = _env_str(
        "CHAT_SERVER_INSTANCE_ID", default=_default_instance_id()
    )
    CHAT_REDIS_EVENT_CHANNEL: str = _env_str(
        "CHAT_REDIS_EVENT_CHANNEL", default="barise:chat:events"
    )
    CHAT_PRESENCE_TTL_SECONDS: int = _env_int(
        "CHAT_PRESENCE_TTL_SECONDS", default=90
    )
    CHAT_PRESENCE_SET_TTL_SECONDS: int = _env_int(
        "CHAT_PRESENCE_SET_TTL_SECONDS", default=180
    )
    CHAT_EMAIL_MIN_UNREAD_COUNT: int = _env_int(
        "CHAT_EMAIL_MIN_UNREAD_COUNT", default=4
    )
    CHAT_EMAIL_MAX_SUMMARY_MESSAGES: int = _env_int(
        "CHAT_EMAIL_MAX_SUMMARY_MESSAGES", default=9
    )
    CHAT_EMAIL_COOLDOWN_MINUTES: int = _env_int(
        "CHAT_EMAIL_COOLDOWN_MINUTES", default=180
    )
    CHAT_EMAIL_MIN_OFFLINE_MINUTES: int = _env_int(
        "CHAT_EMAIL_MIN_OFFLINE_MINUTES", default=15
    )
    CHAT_EMAIL_BATCH_RETENTION_DAYS: int = _env_int(
        "CHAT_EMAIL_BATCH_RETENTION_DAYS", default=14
    )
    CHAT_PUSH_REQUIRE_OFFLINE: bool = _env_bool(
        "CHAT_PUSH_REQUIRE_OFFLINE", default=True
    )
    CHAT_NOTIFICATION_BRAND_NAME: str = _env_str(
        "CHAT_NOTIFICATION_BRAND_NAME", default="Barise"
    )

    @property
    def BACKEND_CORS_ORIGINS(self) -> list[str]:
        configured_origins = [
            origin
            for origin in _split_origins(self.BACKEND_CORS_ORIGINS_RAW)
            if origin.startswith(("http://", "https://"))
        ]
        if not configured_origins:
            configured_origins = [
                "https://ai.barise.in",
                "https://barise.in",
            ]
        return list(dict.fromkeys([*configured_origins, *LOCALHOST_CORS_ORIGINS]))

    class Config:
        case_sensitive = True


@lru_cache()
def get_settings():
    return Settings()
