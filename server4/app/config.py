"""
Server 4 — Presentation Service Configuration
Pydantic Settings loading all .env vars for LLMs, research APIs, storage, auth.
"""

import os
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _fix_rediss_url(url: str) -> str:
    """Append ssl_cert_reqs=CERT_REQUIRED to rediss:// URLs if missing.

    Celery's Redis backend requires this parameter for SSL connections
    (e.g. Azure Redis Cache).
    """
    if not url.startswith("rediss://"):
        return url
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "ssl_cert_reqs" not in qs:
        sep = "&" if parsed.query else "?"
        return url + sep + "ssl_cert_reqs=CERT_REQUIRED"
    return url


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


LOCALHOST_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8081",
    "http://127.0.0.1:8081",
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
    PUBLIC_BASE_URL: str = Field(default="", validation_alias="PUBLIC_BASE_URL")
    # Origin of the frontend SPA. Used to build share links and the
    # screenshot capture URL. Defaults to the local dev frontend at
    # http://localhost:8080 — override in production via FRONTEND_ORIGIN
    # env var or the deployed share links will point at localhost.
    FRONTEND_ORIGIN: str = Field(
        default="http://localhost:8080",
        validation_alias=AliasChoices("FRONTEND_ORIGIN", "BARISE_FRONTEND_ORIGIN"),
    )

    @field_validator("FRONTEND_ORIGIN", mode="before")
    @classmethod
    def sanitize_frontend_origin(cls, v: Any) -> str:
        if isinstance(v, str) and "," in v:
            parts = [p.strip() for p in v.split(",") if p.strip()]
            for part in parts:
                if "localhost" not in part and "127.0.0.1" not in part:
                    return part
            return parts[0] if parts else "http://localhost:8080"
        return v

    # ── Dev / debugging ─────────────────────────────────────────
    # Gates the `/api/v4/dev/*` fixture-seed endpoints. Defaults to True
    # in development environments (ENVIRONMENT != "production") so the
    # founder can seed test projects without burning API credits; flip
    # to False or leave unset on prod deployments.
    ENABLE_DEV_ROUTES: bool = Field(
        default=True,
        validation_alias=AliasChoices("ENABLE_DEV_ROUTES", "DEBUG_DEV_ROUTES"),
    )
    BARISE_REQUIRE_STRONG_SECRETS: bool = Field(
        default=True,
        validation_alias="BARISE_REQUIRE_STRONG_SECRETS",
    )

    # ── Auth (shared with Server 1) ─────────────────────────────
    SECRET_KEY: str = Field(
        default="local-dev-secret-change-me",
        validation_alias=AliasChoices("BARISE_JWT_SECRET_KEY", "JWT_SECRET_KEY", "SECRET_KEY"),
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
    MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = Field(
        default=8000,
        validation_alias="MONGODB_SERVER_SELECTION_TIMEOUT_MS",
    )
    MONGODB_CONNECT_TIMEOUT_MS: int = Field(
        default=8000,
        validation_alias="MONGODB_CONNECT_TIMEOUT_MS",
    )
    MONGODB_SOCKET_TIMEOUT_MS: int = Field(
        default=20000,
        validation_alias="MONGODB_SOCKET_TIMEOUT_MS",
    )
    REQUIRE_DB_ON_STARTUP: bool = Field(
        default=False,
        validation_alias="REQUIRE_DB_ON_STARTUP",
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
    CELERY_TASK_TIME_LIMIT: int = Field(
        default=600,
        validation_alias="CELERY_TASK_TIME_LIMIT",
    )
    CELERY_WORKER_CONCURRENCY: int = Field(
        default=4,
        validation_alias="CELERY_WORKER_CONCURRENCY",
    )

    # ── Slice 2 (Durable V4 Generation) ─────────────────────────
    # When true, ``POST /api/v4/generate`` dispatches the V4 pipeline to
    # Celery (queues ``content-fast`` for standard, ``content-premium``
    # for premium). When false, the legacy ``BackgroundTasks`` path runs
    # in-process. The dispatcher falls back to BackgroundTasks if the
    # broker is unreachable so a misconfigured deployment never silently
    # loses generations. Default is False to keep existing behaviour
    # until ops verify a worker is running.
    V4_USE_CELERY_QUEUE: bool = Field(
        default=False,
        validation_alias="V4_USE_CELERY_QUEUE",
    )
    V4_CELERY_QUEUE_STANDARD: str = Field(
        default="content-fast",
        validation_alias="V4_CELERY_QUEUE_STANDARD",
    )
    V4_CELERY_QUEUE_PREMIUM: str = Field(
        default="content-premium",
        validation_alias="V4_CELERY_QUEUE_PREMIUM",
    )
    # Wall-clock budget (seconds) for the V4 Celery task. Exceeding the
    # soft limit ⇒ task receives SoftTimeLimitExceeded and can clean up;
    # exceeding the hard limit ⇒ worker kills the task. The reaper marks
    # rows still in ``generating_content`` after this window as failed.
    V4_CELERY_TASK_TIME_LIMIT: int = Field(
        default=900,  # 15 minutes hard cap
        validation_alias="V4_CELERY_TASK_TIME_LIMIT",
    )
    V4_CELERY_TASK_SOFT_TIME_LIMIT: int = Field(
        default=840,  # 14 minutes soft cap
        validation_alias="V4_CELERY_TASK_SOFT_TIME_LIMIT",
    )
    V4_STALLED_JOB_REAP_MINUTES: int = Field(
        default=20,  # >15 min in generating_content with no updates ⇒ reaped
        validation_alias="V4_STALLED_JOB_REAP_MINUTES",
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

    # T0+: Kimi-K2.6 (Azure) — premium-only strategist + targeted rewriter.
    # Narrowly used (budgeted per project) because it's the most expensive
    # model in the stack. Env aliases match the keys already in server4/.env:
    #   Kimi2.6_endpoint, Kimi2.6_api_key, Kimi2.6_deployment_name
    AZURE_KIMI26_ENDPOINT: str = Field(
        default="",
        validation_alias=AliasChoices("Kimi2.6_endpoint", "AZURE_KIMI26_ENDPOINT"),
    )
    AZURE_KIMI26_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("Kimi2.6_api_key", "AZURE_KIMI26_API_KEY"),
    )
    AZURE_KIMI26_DEPLOYMENT: str = Field(
        default="Kimi-K2.6",
        validation_alias=AliasChoices(
            "Kimi2.6_deployment_name", "AZURE_KIMI26_DEPLOYMENT"
        ),
    )
    AZURE_KIMI26_MODEL: str = Field(
        default="Kimi-K2.6",
        validation_alias=AliasChoices("Kimi2.6_model_name", "AZURE_KIMI26_MODEL"),
    )

    # T0.5: Phi-4-reasoning (Azure) - alternate names
    PHI4_REASONING_ENDPOINT: str = Field(
        default="",
        validation_alias=AliasChoices(
            "Phi_4_reasoning_endpoint",
            "Phi-4-reasoning_endpoint",
            "PHI4_REASONING_ENDPOINT",
        ),
    )
    PHI4_REASONING_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices(
            "Phi_4_reasoning_api_key",
            "Phi-4-reasoning_api_key",
            "PHI4_REASONING_API_KEY",
        ),
    )
    PHI4_REASONING_DEPLOYMENT: str = Field(
        default="Phi-4-reasoning",
        validation_alias=AliasChoices(
            "Phi_4_reasoning_deployment_name",
            "Phi-4-reasoning_deployment_name",
            "PHI4_REASONING_DEPLOYMENT",
        ),
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
        default="",
        validation_alias=AliasChoices("Mistral_deployment_name", "MISTRAL_DEPLOYMENT"),
    )

    # T2.5: GPT-OSS-120B (Azure) — open-source large-context workhorse
    GPT_OSS_ENDPOINT: str = Field(
        default="",
        validation_alias=AliasChoices("gpt_oss_endpoint", "GPT_OSS_ENDPOINT"),
    )
    GPT_OSS_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("gpt_oss_api_key", "GPT_OSS_API_KEY"),
    )
    GPT_OSS_DEPLOYMENT: str = Field(
        default="gpt-oss-120b",
        validation_alias=AliasChoices("gpt_oss_deployment_name", "GPT_OSS_DEPLOYMENT"),
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

    # OpenRouter free tier — multi-model access
    OPENROUTE_SERVICE_API_KEY: str = Field(
        default="", validation_alias="openroute_service_api_key"
    )
    # OpenRouter GLM 4.5 Air (free)
    OPENROUTER_MODEL_GLM45: str = Field(
        default="z-ai/glm-4.5-air:free", validation_alias="openrouter_model_glm45"
    )
    OPENROUTER_APIKEY_GLM45: str = Field(
        default="", validation_alias="openrouter_apikey_glm45"
    )
    # OpenRouter Gemma-4-31b (free)
    OPENROUTER_MODEL_GEMMA: str = Field(
        default="google/gemma-4-31b-it:free", validation_alias="openrouter_model_gemma"
    )
    OPENROUTER_APIKEY_GEMMA: str = Field(
        default="", validation_alias="openrouter_apikey_gemma"
    )
    # OpenRouter NVIDIA Nemotron (free)
    OPENROUTER_MODEL_NVIDIA: str = Field(
        default="nvidia/nemotron-3-super-120b-a12b:free", validation_alias="openrouter_model_nvidia"
    )
    OPENROUTER_APIKEY_NVIDIA: str = Field(
        default="", validation_alias="openrouter_apikey_nvidia"
    )
    # OpenRouter MiniMax M2.5 (free)
    OPENROUTER_MODEL_MINIMAX: str = Field(
        default="minimax/minimax-m2.5:free", validation_alias="openrouter_model_minimax"
    )
    OPENROUTER_APIKEY_MINIMAX: str = Field(
        default="", validation_alias="openrouter_apikey_minimax"
    )

    # ══════════════════════════════════════════════════════════════
    # IMAGE GENERATION
    # ══════════════════════════════════════════════════════════════
    AZURE_FLUX_ENDPOINT: str = Field(default="", validation_alias="AZURE_FLUX_ENDPOINT")
    AZURE_FLUX_API_KEY: str = Field(default="", validation_alias="AZURE_FLUX_API_KEY")
    AZURE_FLUX_DEPLOYMENT_NAME: str = Field(
        default="FLUX.1-Kontext-pro", validation_alias="AZURE_FLUX_DEPLOYMENT_NAME"
    )
    AZURE_FLUX_VERSION: str = Field(
        default="2024-12-01-preview", validation_alias="AZURE_FLUX_VERSION"
    )

    # Nvidia Stable Diffusion 3 Medium (free tier)
    NVIDIA_STABLE_API_KEY: str = Field(
        default="", validation_alias="Nvidia_stable_api_key"
    )
    NVIDIA_STABLE_ENDPOINT: str = Field(
        default="https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-3-medium",
        validation_alias="NVIDIA_STABLE_ENDPOINT",
    )

    # HuggingFace Inference API (free tier fallback)
    HUGGINGFACE_API_TOKEN: str = Field(
        default="", validation_alias="HUGGINGFACE_API_TOKEN"
    )

    # ══════════════════════════════════════════════════════════════
    # RESEARCH APIs
    # ══════════════════════════════════════════════════════════════

    # Web Search (5 Serper keys for round-robin)
    SERPER_API_KEY: str = Field(default="", validation_alias="SERPER_API_KEY")
    SERPER_API_KEY_2: str = Field(default="", validation_alias="SERPER_API_KEY2")
    SERPER_API_KEY_3: str = Field(default="", validation_alias="SERPER_API_KEY3")
    SERPER_API_KEY_4: str = Field(default="", validation_alias="SERPER_API_KEY4")
    SERPER_API_KEY_5: str = Field(default="", validation_alias="SERPER_API_KEY5")

    @property
    def serper_keys(self) -> list[str]:
        keys = [self.SERPER_API_KEY, self.SERPER_API_KEY_2, self.SERPER_API_KEY_3,
                self.SERPER_API_KEY_4, self.SERPER_API_KEY_5]
        seen: set[str] = set()
        out: list[str] = []
        for k in keys:
            k = (k or "").strip()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    # SerpAPI (2 keys)
    SERPAPI_KEY: str = Field(default="", validation_alias="SERPAPI_KEY")
    SERPAPI_KEY_2: str = Field(default="", validation_alias="SERPAPI_KEY2")

    # AI-powered search (5 Tavily keys for round-robin)
    TAVILY_API_KEY: str = Field(default="", validation_alias="TAVILY_API_KEY")
    TAVILY_API_KEY_1: str = Field(default="", validation_alias="TAVILY_API_KEY1")
    TAVILY_API_KEY_2: str = Field(default="", validation_alias="TAVILY_API_KEY2")
    TAVILY_API_KEY_3: str = Field(default="", validation_alias="TAVILY_API_KEY3")
    TAVILY_API_KEY_4: str = Field(default="", validation_alias="TAVILY_API_KEY4")

    @property
    def tavily_keys(self) -> list[str]:
        keys = [self.TAVILY_API_KEY, self.TAVILY_API_KEY_1, self.TAVILY_API_KEY_2,
                self.TAVILY_API_KEY_3, self.TAVILY_API_KEY_4]
        seen: set[str] = set()
        out: list[str] = []
        for k in keys:
            k = (k or "").strip()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    # Exa: primary key (lowercase env name) + 5 pooled keys for round-robin.
    # Old `exa.ai_key` alias kept for backward compat.
    EXA_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("exa_ai_key", "exa.ai_key", "EXA_API_KEY"),
    )
    EXA_API_KEY_1: str = Field(default="", validation_alias="Exa1_api_key")
    EXA_API_KEY_2: str = Field(default="", validation_alias="Exa2_api_key")
    EXA_API_KEY_3: str = Field(default="", validation_alias="Exa3_api_key")
    EXA_API_KEY_4: str = Field(default="", validation_alias="Exa4_api_key")
    EXA_API_KEY_5: str = Field(default="", validation_alias="Exa5_api_key")

    # Firecrawl: 2 keys for round-robin
    FIRECRAWL_API_KEY: str = Field(default="", validation_alias="firecrawl.dev_key")
    FIRECRAWL_API_KEY_2: str = Field(default="", validation_alias="firecrawl.dev_key2")

    @property
    def firecrawl_keys(self) -> list[str]:
        keys = [self.FIRECRAWL_API_KEY, self.FIRECRAWL_API_KEY_2]
        seen: set[str] = set()
        out: list[str] = []
        for k in keys:
            k = (k or "").strip()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    # Jina: primary + 2 pooled keys
    JINA_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("jina_ai_key", "jina.ai_key", "JINA_API_KEY"),
    )
    JINA_API_KEY_1: str = Field(default="", validation_alias="Jina1_api_key")
    JINA_API_KEY_2: str = Field(default="", validation_alias="Jina2_api_key")
    JINA_API_KEY_3: str = Field(default="", validation_alias="Jina3_api_key")

    # TinyFish: 5 pooled keys (free web search tier)
    TINYFISH_API_KEY_1: str = Field(default="", validation_alias="TinyFish_api1")
    TINYFISH_API_KEY_2: str = Field(default="", validation_alias="TinyFish_api2")
    TINYFISH_API_KEY_3: str = Field(default="", validation_alias="TinyFish_api3")
    TINYFISH_API_KEY_4: str = Field(default="", validation_alias="TinyFish_api4")
    TINYFISH_API_KEY_5: str = Field(default="", validation_alias="TinyFish_api5")

    @property
    def tinyfish_keys(self) -> list[str]:
        keys = [
            self.TINYFISH_API_KEY_1,
            self.TINYFISH_API_KEY_2,
            self.TINYFISH_API_KEY_3,
            self.TINYFISH_API_KEY_4,
            self.TINYFISH_API_KEY_5,
        ]
        seen: set[str] = set()
        out: list[str] = []
        for k in keys:
            k = (k or "").strip()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    # You.com: primary + 5 pooled keys
    YOU_COM_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("you_com_API", "you.com_API", "YOU_COM_API_KEY"),
    )
    YOU_COM_API_KEY_1: str = Field(default="", validation_alias="you_com1_API")
    YOU_COM_API_KEY_2: str = Field(default="", validation_alias="you_com2_API")
    YOU_COM_API_KEY_3: str = Field(default="", validation_alias="you_com3_API")
    YOU_COM_API_KEY_4: str = Field(default="", validation_alias="you_com4_API")
    YOU_COM_API_KEY_5: str = Field(default="", validation_alias="you_com5_Api")

    @property
    def exa_keys(self) -> list[str]:
        keys = [
            self.EXA_API_KEY,
            self.EXA_API_KEY_1,
            self.EXA_API_KEY_2,
            self.EXA_API_KEY_3,
            self.EXA_API_KEY_4,
            self.EXA_API_KEY_5,
        ]
        # De-duplicate while preserving order; strip whitespace from .env values.
        seen: set[str] = set()
        out: list[str] = []
        for k in keys:
            k = (k or "").strip()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    @property
    def jina_keys(self) -> list[str]:
        keys = [self.JINA_API_KEY, self.JINA_API_KEY_1, self.JINA_API_KEY_2, self.JINA_API_KEY_3]
        seen: set[str] = set()
        out: list[str] = []
        for k in keys:
            k = (k or "").strip()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    @property
    def you_com_keys(self) -> list[str]:
        keys = [
            self.YOU_COM_API_KEY,
            self.YOU_COM_API_KEY_1,
            self.YOU_COM_API_KEY_2,
            self.YOU_COM_API_KEY_3,
            self.YOU_COM_API_KEY_4,
            self.YOU_COM_API_KEY_5,
        ]
        seen: set[str] = set()
        out: list[str] = []
        for k in keys:
            k = (k or "").strip()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

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

    # Scraping / Proxy
    SCRAPE_DO_API_KEY: str = Field(default="", validation_alias="SCRAPE_DO_API_KEY")

    # Alternative search
    SEARCH_API_KEY: str = Field(default="", validation_alias="search_api")

    # ── New AI-search / web-search providers (added 2026-05-25) ───────
    # Each is a key-pool provider following the same pattern as Tavily /
    # Serper / Exa: round-robin via ``app.services.v4.key_pool``, gated by
    # ``provider_health.is_healthy(<name>)``. Helpers live on
    # ``ResearchCollector`` and are dispatched through
    # ``_dispatch_web_provider``.
    #
    # Linkup — AI-search engine, https://www.linkup.so/api
    LINKUP_API_KEY_1: str = Field(default="", validation_alias="linkup_api_key1")
    LINKUP_API_KEY_2: str = Field(default="", validation_alias="linkup_api_key2")
    LINKUP_API_KEY_3: str = Field(default="", validation_alias="linkup_api_key3")
    LINKUP_API_KEY_4: str = Field(default="", validation_alias="linkup_api_key4")
    LINKUP_API_KEY_5: str = Field(default="", validation_alias="linkup_api_key5")
    LINKUP_API_KEY_6: str = Field(default="", validation_alias="linkup_api_key6")
    LINKUP_API_KEY_7: str = Field(default="", validation_alias="linkup_api_key7")
    LINKUP_API_KEY_8: str = Field(default="", validation_alias="linkup_api_key8")
    LINKUP_API_KEY_9: str = Field(default="", validation_alias="linkup_api_key9")
    LINKUP_API_KEY_10: str = Field(default="", validation_alias="linkup_api_key10")

    # SearchAPI — Google SERP API, https://www.searchapi.io
    SEARCHAPI_KEY_1: str = Field(default="", validation_alias="searchApi_key1")
    SEARCHAPI_KEY_2: str = Field(default="", validation_alias="searchApi_key2")
    SEARCHAPI_KEY_3: str = Field(default="", validation_alias="searchApi_key3")
    SEARCHAPI_KEY_4: str = Field(default="", validation_alias="searchApi_key4")
    SEARCHAPI_KEY_5: str = Field(default="", validation_alias="searchApi_key5")

    # Zenserp — Google SERP API, https://app.zenserp.com
    ZENSERP_KEY_1: str = Field(default="", validation_alias="zenserp_api_key1")
    ZENSERP_KEY_2: str = Field(default="", validation_alias="zenserp_api_key2")
    ZENSERP_KEY_3: str = Field(default="", validation_alias="zenserp_api_key3")

    # ScrapingBog — Google SERP scraper, https://scrapingdog.com
    SCRAPINGBOG_KEY_1: str = Field(default="", validation_alias="scrapingbog_api_key1")
    SCRAPINGBOG_KEY_2: str = Field(default="", validation_alias="scrapingbog_api_key2")
    SCRAPINGBOG_KEY_3: str = Field(default="", validation_alias="scrapingbog_api_key3")

    # ScrapingBee — page-render scraper, https://www.scrapingbee.com
    SCRAPINGBEE_KEY_1: str = Field(default="", validation_alias="scrapingbee_api_key1")
    SCRAPINGBEE_KEY_2: str = Field(default="", validation_alias="scrapingbee_api_key2")
    SCRAPINGBEE_KEY_3: str = Field(default="", validation_alias="scrapingbee_api_key3")

    # Scrape.do — proxy + render, https://scrape.do
    SCRAPE_DO_KEY_1: str = Field(default="", validation_alias="scrape_do_api_key1")
    SCRAPE_DO_KEY_2: str = Field(default="", validation_alias="scrape_do_api_key2")

    # ValueSerp — SERP API, https://www.valueserp.com
    VALUESERP_KEY_1: str = Field(default="", validation_alias="valueserp_api_key1")
    VALUESERP_KEY_2: str = Field(default="", validation_alias="valueserp_api_key2")
    VALUESERP_KEY_3: str = Field(default="", validation_alias="valueserp_api_key3")

    # Apify — actor-based scraping, https://apify.com
    APIFY_KEY_1: str = Field(default="", validation_alias="apify_api_key1")
    APIFY_KEY_2: str = Field(default="", validation_alias="apify_api_key2")
    APIFY_KEY_3: str = Field(default="", validation_alias="apify_api_key3")

    @property
    def linkup_keys(self) -> list[str]:
        keys = [
            self.LINKUP_API_KEY_1, self.LINKUP_API_KEY_2, self.LINKUP_API_KEY_3,
            self.LINKUP_API_KEY_4, self.LINKUP_API_KEY_5, self.LINKUP_API_KEY_6,
            self.LINKUP_API_KEY_7, self.LINKUP_API_KEY_8, self.LINKUP_API_KEY_9,
            self.LINKUP_API_KEY_10,
        ]
        seen: set[str] = set()
        out: list[str] = []
        for k in keys:
            k = (k or "").strip()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    @property
    def searchapi_keys(self) -> list[str]:
        keys = [
            self.SEARCHAPI_KEY_1, self.SEARCHAPI_KEY_2, self.SEARCHAPI_KEY_3,
            self.SEARCHAPI_KEY_4, self.SEARCHAPI_KEY_5,
        ]
        seen: set[str] = set()
        out: list[str] = []
        for k in keys:
            k = (k or "").strip()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    @property
    def zenserp_keys(self) -> list[str]:
        keys = [self.ZENSERP_KEY_1, self.ZENSERP_KEY_2, self.ZENSERP_KEY_3]
        seen: set[str] = set()
        out: list[str] = []
        for k in keys:
            k = (k or "").strip()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    @property
    def scrapingbog_keys(self) -> list[str]:
        keys = [self.SCRAPINGBOG_KEY_1, self.SCRAPINGBOG_KEY_2, self.SCRAPINGBOG_KEY_3]
        seen: set[str] = set()
        out: list[str] = []
        for k in keys:
            k = (k or "").strip()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    @property
    def scrapingbee_keys(self) -> list[str]:
        keys = [self.SCRAPINGBEE_KEY_1, self.SCRAPINGBEE_KEY_2, self.SCRAPINGBEE_KEY_3]
        seen: set[str] = set()
        out: list[str] = []
        for k in keys:
            k = (k or "").strip()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    @property
    def scrape_do_keys(self) -> list[str]:
        # Pooled scrape.do keys plus the legacy single-key ``SCRAPE_DO_API_KEY``
        # so existing callers that read the single field still work while new
        # research providers benefit from rotation.
        keys = [self.SCRAPE_DO_API_KEY, self.SCRAPE_DO_KEY_1, self.SCRAPE_DO_KEY_2]
        seen: set[str] = set()
        out: list[str] = []
        for k in keys:
            k = (k or "").strip()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    @property
    def valueserp_keys(self) -> list[str]:
        keys = [self.VALUESERP_KEY_1, self.VALUESERP_KEY_2, self.VALUESERP_KEY_3]
        seen: set[str] = set()
        out: list[str] = []
        for k in keys:
            k = (k or "").strip()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    @property
    def apify_keys(self) -> list[str]:
        keys = [self.APIFY_KEY_1, self.APIFY_KEY_2, self.APIFY_KEY_3]
        seen: set[str] = set()
        out: list[str] = []
        for k in keys:
            k = (k or "").strip()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    # Crypto & Historical Finance
    COINDESK_API_KEY: str = Field(
        default="", validation_alias="coindesk.com_api_key"
    )
    EODHD_API_KEY: str = Field(default="", validation_alias="EODHD_API_key")

    # Specialty APIs
    API_NINJAS_KEY: str = Field(default="", validation_alias="API_NINJAS_KEY")
    NASA_APOD_API_KEY: str = Field(default="", validation_alias="NASA_APDO_API")

    # Academic
    CORE_API_KEY: str = Field(default="", validation_alias="CORE_API_KEY")

    # ── Local Models (HuggingFace T6) ───────────────────────────
    USE_TINYLLAMA: bool = Field(default=False, validation_alias="USE_TINYLLAMA")
    USE_FLAN_T5: bool = Field(default=False, validation_alias="USE_FLAN_T5")
    USE_PHI2: bool = Field(default=False, validation_alias="USE_PHI2")
    MODEL_DEVICE: str = Field(default="cpu", validation_alias="MODEL_DEVICE")
    EMBEDDINGS_PATH: str = Field(default="./data/embeddings", validation_alias="EMBEDDINGS_PATH")

    # ── Rate Limiting ───────────────────────────────────────────
    RATE_LIMIT_STANDARD: int = Field(default=20)
    RATE_LIMIT_PREMIUM: int = Field(default=100)

    # ── V4 Multi-model Consensus (Plan-v4 Section K) ────────────
    ENABLE_CONSENSUS: bool = Field(
        default=True,
        validation_alias=AliasChoices("V4_ENABLE_CONSENSUS", "ENABLE_CONSENSUS"),
    )
    CONSENSUS_STANDARD_BUDGET_S: float = Field(
        default=15.0, validation_alias="V4_CONSENSUS_STANDARD_BUDGET_S",
    )
    CONSENSUS_PREMIUM_BUDGET_S: float = Field(
        default=25.0, validation_alias="V4_CONSENSUS_PREMIUM_BUDGET_S",
    )

    # ── V4 Phase 12: Few-shot prompt injection ──────────────────
    # Appends a curated reference slide example to each writer's user
    # message so the LLM has a concrete cadence anchor. The anchor is
    # a clearly-labelled SHAPE reference; the writer system prompt and
    # the anchor block both forbid copying the example's data.
    ENABLE_FEW_SHOT_ANCHORS: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "V4_ENABLE_FEW_SHOT_ANCHORS", "ENABLE_FEW_SHOT_ANCHORS"
        ),
    )

    # ── V4 Content-quality gates (Founder replan) ───────────────
    # Kill-switches so we can disable individual gates in prod without
    # shipping a new release. All default to ON.
    ENABLE_CONTENT_RULES_GATE: bool = Field(
        default=True, validation_alias="V4_ENABLE_CONTENT_RULES_GATE",
    )
    ENABLE_TEMPLATE_DETECTOR: bool = Field(
        default=True, validation_alias="V4_ENABLE_TEMPLATE_DETECTOR",
    )
    ENABLE_PROGRESS_LOG: bool = Field(
        default=True, validation_alias="V4_ENABLE_PROGRESS_LOG",
    )
    ENABLE_SCHEMA_GATE: bool = Field(
        default=True, validation_alias="V4_ENABLE_SCHEMA_GATE",
    )
    ENABLE_PROVENANCE_GATE: bool = Field(
        default=True, validation_alias="V4_ENABLE_PROVENANCE_GATE",
    )
    ENABLE_STYLE_GUARD: bool = Field(
        default=True, validation_alias="V4_ENABLE_STYLE_GUARD",
    )
    ENABLE_LAYOUT_RHYTHM_GATE: bool = Field(
        default=True, validation_alias="V4_ENABLE_LAYOUT_RHYTHM_GATE",
    )
    ENABLE_BOARDROOM_JUDGE: bool = Field(
        default=False, validation_alias="V4_ENABLE_BOARDROOM_JUDGE",
    )
    ENABLE_LEARNING_INFLUENCE: bool = Field(
        default=True, validation_alias="V4_ENABLE_LEARNING_INFLUENCE",
    )
    ENABLE_IMAGE_PROMPT_ENRICHMENT: bool = Field(
        default=True, validation_alias="V4_ENABLE_IMAGE_PROMPT_ENRICHMENT",
    )
    ENABLE_STANDARD_ROUTING_EXPERIMENT: bool = Field(
        default=False, validation_alias="V4_ENABLE_STANDARD_ROUTING_EXPERIMENT",
    )
    STANDARD_ROUTING_EXPERIMENT_ROLLOUT_PERCENT: float = Field(
        default=0.0, validation_alias="V4_STANDARD_ROUTING_EXPERIMENT_ROLLOUT_PERCENT",
    )
    QUALITY_GATE_ROLLOUT_PERCENT: float = Field(
        default=100.0, validation_alias="V4_QUALITY_GATE_ROLLOUT_PERCENT",
    )
    QUALITY_METRICS_COLLECTION: str = Field(
        default="v4_quality_metrics", validation_alias="V4_QUALITY_METRICS_COLLECTION",
    )
    ALLOW_POLLINATIONS_IMAGES: bool = Field(
        default=False, validation_alias="V4_ALLOW_POLLINATIONS_IMAGES",
    )

    # ── Instruction Decomposition & TOON (anti-hallucination) ────
    ENABLE_DECOMPOSED_PROMPTS: bool = Field(
        default=True,
        validation_alias="V4_ENABLE_DECOMPOSED_PROMPTS",
        description="Use focused per-intent prompts instead of monolithic 3000-token prompts",
    )
    ENABLE_TOON_FORMAT: bool = Field(
        default=True,
        validation_alias="V4_ENABLE_TOON_FORMAT",
        description="Use TOON (Token-Oriented Object Notation) for LLM responses - saves 40-60% tokens",
    )

    # ── Kimi 2.6 narrow-use budget (Founder replan) ─────────────
    # Kimi 2.6 is expensive. It only runs for two narrow tasks:
    #   (a) premium skeleton-planner thesis pass
    #   (b) critic's targeted rewrite of top-N slides when score < gate
    # Per-project call-count budget is enforced inside ModelRouter.
    ENABLE_KIMI26: bool = Field(
        default=True, validation_alias="V4_ENABLE_KIMI26",
    )
    KIMI26_PREMIUM_MAX_CALLS: int = Field(
        default=3, validation_alias="V4_KIMI26_PREMIUM_MAX_CALLS",
    )
    KIMI26_STANDARD_MAX_CALLS: int = Field(
        default=1, validation_alias="V4_KIMI26_STANDARD_MAX_CALLS",
    )

    # Critic score targets - configurable per company policy
    # Premium mode target for investor-critical slides rescore
    PREMIUM_CRITICAL_RESCORE_TARGET: float = Field(
        default=9.0, validation_alias="V4_PREMIUM_CRITICAL_RESCORE_TARGET",
    )
    # Standard mode shortcut threshold
    STANDARD_SHORTCUT_THRESHOLD: float = Field(
        default=8.5, validation_alias="V4_STANDARD_SHORTCUT_THRESHOLD",
    )
    # Premium mode shortcut threshold
    PREMIUM_SHORTCUT_THRESHOLD: float = Field(
        default=9.2, validation_alias="V4_PREMIUM_SHORTCUT_THRESHOLD",
    )


settings = Settings()
