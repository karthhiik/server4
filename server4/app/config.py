"""
Server 4 — Presentation Service Configuration
Pydantic Settings loading all .env vars for LLMs, research APIs, storage, auth.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


LOCALHOST_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:8003",
    "http://127.0.0.1:8003",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_project_root() / ".env"), ".env"),
        case_sensitive=True,
        extra="ignore",
    )

    # ── Server ──────────────────────────────────────────────────
    ENVIRONMENT: str = Field(default="development")
    PROJECT_NAME: str = Field(default="Barise Presentation Service")
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(
        default=8003, validation_alias=AliasChoices("PORT", "API_PORT")
    )

    # ── Auth (shared with Server 1) ─────────────────────────────
    SECRET_KEY: str = Field(
        default="local-dev-secret-change-me",
        validation_alias=AliasChoices("BARISE_JWT_SECRET_KEY", "SECRET_KEY"),
    )
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)

    # ── MongoDB ─────────────────────────────────────────────────
    MONGODB_URI: str = Field(
        default="mongodb://localhost:27017/pitchdecks",
        validation_alias=AliasChoices("MONGODB_URI", "MONGO_URI", "AZURE_MONGO_URI"),
    )
    MONGODB_DB_NAME: str = Field(
        default="barise_presentations",
        validation_alias=AliasChoices("MONGODB_DB_NAME", "COSMOS_DATABASE_NAME"),
    )

    # ── Redis ───────────────────────────────────────────────────
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )

    # ── Celery ──────────────────────────────────────────────────
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        validation_alias="CELERY_BROKER_URL",
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2",
        validation_alias="CELERY_RESULT_BACKEND",
    )

    # ── Storage paths ───────────────────────────────────────────
    DATA_PATH: str = Field(
        default="D:/Desktop/newpitchdecks/data", validation_alias="DATA_PATH"
    )
    CACHE_PATH: str = Field(
        default="D:/Desktop/newpitchdecks/data/cache", validation_alias="CACHE_PATH"
    )
    LOGS_PATH: str = Field(
        default="D:/Desktop/newpitchdecks/data/logs", validation_alias="LOGS_PATH"
    )

    # ── Azure Blob Storage ──────────────────────────────────────
    BLOB_STORAGE_CONNECTION_STRING: str = Field(
        default="", validation_alias="BLOB_STORAGE_CONNECTION_STRING"
    )
    BLOB_CONTAINER_NAME: str = Field(
        default="blobpitchdeckstorage", validation_alias="BLOB_CONTAINER_NAME"
    )

    # ══════════════════════════════════════════════════════════════
    # LLM MODELS — 6 Tiers
    # ══════════════════════════════════════════════════════════════

    # T0: Kimi-K2-Thinking (Planning/Reasoning)
    AZURE_KIMI_ENDPOINT: str = Field(default="", validation_alias="AZURE_KIMI_ENDPOINT")
    AZURE_KIMI_API_KEY: str = Field(default="", validation_alias="AZURE_KIMI_API_KEY")
    AZURE_KIMI_DEPLOYMENT: str = Field(
        default="Kimi-K2-Thinking",
        validation_alias=AliasChoices(
            "AZURE_KIMI_VERSION_DEPLOYMENT", "AZURE_KIMI_DEPLOYMENT"
        ),
    )
    AZURE_KIMI_MODEL: str = Field(
        default="Kimi-K2-Thinking",
        validation_alias=AliasChoices("AZURE_KIMI_VERSION_MODEL", "AZURE_KIMI_MODEL"),
    )

    # T1: DeepSeek-V3.2 (Storytelling)
    DEEPSEEK_ENDPOINT: str = Field(default="", validation_alias="DEEPSEEK_ENDPOINT")
    DEEPSEEK_API_KEY: str = Field(default="", validation_alias="DEEPSEEK_API_KEY")
    DEEPSEEK_MODEL_NAME: str = Field(
        default="DeepSeek-V3.2", validation_alias="DEEPSEEK_MODEL_NAME"
    )
    DEEPSEEK_API_VERSION: str = Field(
        default="2024-05-01-preview", validation_alias="DEEPSEEK_API_VERSION"
    )

    # T2: GPT-4o-mini (Fast structured JSON)
    AZURE_GPT4O_MINI_ENDPOINT: str = Field(
        default="", validation_alias="AZURE_GPT4O_MINI_ENDPOINT"
    )
    AZURE_GPT4O_MINI_API_KEY: str = Field(
        default="", validation_alias="AZURE_GPT4O_MINI_API_KEY"
    )
    AZURE_GPT4O_MINI_DEPLOYMENT: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices(
            "AZURE_GPT4O_MINI_DEPLOYMENT_NAME", "AZURE_GPT4O_MINI_DEPLOYMENT"
        ),
    )
    AZURE_GPT4O_MINI_MODEL: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices(
            "AZURE_GPT4O_MINI_Model_NAME", "AZURE_GPT4O_MINI_MODEL"
        ),
    )
    AZURE_GPT4O_MINI_VERSION: str = Field(
        default="2024-12-01-preview", validation_alias="AZURE_GPT4O_MINI_VERSION"
    )

    # T3: Mistral-medium (Technical/Code)
    MISTRAL_ENDPOINT: str = Field(
        default="",
        validation_alias=AliasChoices("Mistral_endpoint", "MISTRAL_ENDPOINT"),
    )
    MISTRAL_API_KEY: str = Field(
        default="", validation_alias=AliasChoices("Mistral_api_key", "MISTRAL_API_KEY")
    )
    MISTRAL_DEPLOYMENT: str = Field(
        default="mistral-medium-2505",
        validation_alias=AliasChoices("Mistral_deployment_name", "MISTRAL_DEPLOYMENT"),
    )

    # T4: Groq (8-key round-robin, ultra-fast)
    GROQ_API_KEY_0: str = Field(default="", validation_alias="GROQ_API_KEY")
    GROQ_API_KEY_1: str = Field(default="", validation_alias="GROQ_API_KEY1")
    GROQ_API_KEY_2: str = Field(default="", validation_alias="GROQ_API_KEY2")
    GROQ_API_KEY_3: str = Field(default="", validation_alias="GROQ_API_KEY3")
    GROQ_API_KEY_4: str = Field(default="", validation_alias="GROQ_API_KEY4")
    GROQ_API_KEY_5: str = Field(default="", validation_alias="GROQ_API_KEY5")
    GROQ_API_KEY_6: str = Field(default="", validation_alias="GROQ_API_KEY6")
    GROQ_API_KEY_7: str = Field(default="", validation_alias="GROQ_API_KEY7")

    @property
    def groq_keys(self) -> list[str]:
        keys = [
            self.GROQ_API_KEY_0,
            self.GROQ_API_KEY_1,
            self.GROQ_API_KEY_2,
            self.GROQ_API_KEY_3,
            self.GROQ_API_KEY_4,
            self.GROQ_API_KEY_5,
            self.GROQ_API_KEY_6,
            self.GROQ_API_KEY_7,
        ]
        return [k for k in keys if k]

    # T5: Cloudflare Workers (Fallback)
    CF_WORKER_BEARER_TOKEN: str = Field(
        default="", validation_alias="CF_WORKER_BEARER_TOKEN"
    )
    CF_WORKER_GLM_URL: str = Field(default="", validation_alias="CF_WORKER_GLM_URL")
    CF_WORKER_GLM_TOKEN: str = Field(default="", validation_alias="CF_WORKER_GLM_TOKEN")
    CF_WORKER_QWEN_URL: str = Field(default="", validation_alias="CF_WORKER_QWEN_URL")
    CF_WORKER_QWEN_TOKEN: str = Field(
        default="", validation_alias="CF_WORKER_QWEN_TOKEN"
    )
    CF_WORKER_GEMMA_URL: str = Field(default="", validation_alias="CF_WORKER_GEMMA_URL")
    CF_WORKER_GEMMA_TOKEN: str = Field(
        default="", validation_alias="CF_WORKER_GEMMA_TOKEN"
    )
    CF_WORKER_PHOENIX_URL: str = Field(
        default="", validation_alias="CF_WORKER_PHOENIX_URL"
    )
    CF_WORKER_PHOENIX_TOKEN: str = Field(
        default="", validation_alias="CF_WORKER_PHOENIX_TOKEN"
    )
    CF_WORKER_LUCID_URL: str = Field(default="", validation_alias="CF_WORKER_LUCID_URL")
    CF_WORKER_LUCID_TOKEN: str = Field(
        default="", validation_alias="CF_WORKER_LUCID_TOKEN"
    )

    # T6: HuggingFace Local Models
    HUGGINGFACE_API_TOKEN: str = Field(
        default="", validation_alias="HUGGINGFACE_API_TOKEN"
    )

    # OpenRouter (free tier)
    OPENROUTE_SERVICE_API_KEY: str = Field(
        default="", validation_alias="openroute_service_api_key"
    )
    OPENROUTER_MODEL_FREE: str = Field(
        default="qwen/qwen3.6-plus:free",
        validation_alias="openroute_model_free",
    )

    # ══════════════════════════════════════════════════════════════
    # IMAGE GENERATION
    # ══════════════════════════════════════════════════════════════
    AZURE_FLUX_ENDPOINT: str = Field(default="", validation_alias="AZURE_FLUX_ENDPOINT")
    AZURE_FLUX_API_KEY: str = Field(default="", validation_alias="AZURE_FLUX_API_KEY")
    AZURE_FLUX_DEPLOYMENT_NAME: str = Field(
        default="flux-pro-2", validation_alias="AZURE_FLUX_DEPLOYMENT_NAME"
    )
    AZURE_FLUX_VERSION: str = Field(
        default="2024-12-01-preview", validation_alias="AZURE_FLUX_VERSION"
    )

    # ══════════════════════════════════════════════════════════════
    # RESEARCH APIs
    # ══════════════════════════════════════════════════════════════

    # Web Search (3 Serper keys for round-robin)
    SERPER_API_KEY: str = Field(default="", validation_alias="SERPER_API_KEY")
    SERPER_API_KEY_2: str = Field(default="", validation_alias="SERPER_API_KEY2")
    SERPER_API_KEY_3: str = Field(default="", validation_alias="SERPER_API_KEY3")

    @property
    def serper_keys(self) -> list[str]:
        keys = [self.SERPER_API_KEY, self.SERPER_API_KEY_2, self.SERPER_API_KEY_3]
        return [k for k in keys if k]

    # SerpAPI (2 keys)
    SERPAPI_KEY: str = Field(default="", validation_alias="SERPAPI_KEY")
    SERPAPI_KEY_2: str = Field(default="", validation_alias="SERPAPI_KEY2")

    # AI-powered search
    TAVILY_API_KEY: str = Field(default="", validation_alias="TAVILY_API_KEY")
    EXA_API_KEY: str = Field(default="", validation_alias="exa.ai_key")
    FIRECRAWL_API_KEY: str = Field(default="", validation_alias="firecrawl.dev_key")
    JINA_API_KEY: str = Field(default="", validation_alias="jina.ai_key")
    YOU_COM_API_KEY: str = Field(default="", validation_alias="you.com_API")

    # Financial data
    ALPHA_VANTAGE_API_KEY: str = Field(
        default="", validation_alias="ALPHA_VANTAGE_API_KEY"
    )
    FINNHUB_API_KEY: str = Field(default="", validation_alias="FINNHUB_API_KEY")
    POLYGON_API_KEY: str = Field(default="", validation_alias="POLYGON_API_KEY")
    FRED_API_KEY: str = Field(default="", validation_alias="FRED_API_KEY")
    CENSUS_API_KEY: str = Field(default="", validation_alias="CENSUS_API_KEY")
    FMP_API_KEY: str = Field(
        default="", validation_alias="financialmodelingprep.com_key"
    )

    # News
    NEWSAPI_KEY: str = Field(default="", validation_alias="NEWSAPI_KEY")
    NEWSDATA_API_KEY: str = Field(default="", validation_alias="NEWSDATA_API_KEY")
    GUARDIAN_API_KEY: str = Field(default="", validation_alias="The_Guardian_API_key")
    WORLD_NEWS_API_KEY: str = Field(default="", validation_alias="World_news_api_key")

    # Social / Developer
    REDDIT_CLIENT_ID: str = Field(default="", validation_alias="REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: str = Field(
        default="", validation_alias="REDDIT_CLIENT_SECRET"
    )
    REDDIT_USER_AGENT: str = Field(
        default="PitchDeckBot/1.0", validation_alias="REDDIT_USER_AGENT"
    )
    GITHUB_TOKEN: str = Field(default="", validation_alias="GITHUB_TOKEN")
    YOUTUBE_API_KEY: str = Field(default="", validation_alias="YOUTUBE_API_KEY")
    PRODUCTHUNT_API_KEY: str = Field(default="", validation_alias="PRODUCTHUNT_API_KEY")

    # Academic
    CORE_API_KEY: str = Field(default="", validation_alias="CORE_API_KEY")

    # ── Rate Limiting ───────────────────────────────────────────
    RATE_LIMIT_STANDARD: int = Field(default=20)
    RATE_LIMIT_PREMIUM: int = Field(default=100)


settings = Settings()
