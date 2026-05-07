"""
Configuration loader for the Meridian V9 Prototype.
Loads all LLM provider settings from server4/.env
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load from server4/.env (parent directory of prototype/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


def _env(key: str, default: str = "") -> str:
    """Get environment variable with default."""
    return (os.getenv(key) or default).strip()


# ── Groq (FREE — round-robin across multiple keys) ──────────
GROQ_API_KEYS: list[str] = [
    v for name in [
        "GROQ_API_KEY", "GROQ_API_KEY1", "GROQ_API_KEY2", "GROQ_API_KEY3",
        "GROQ_API_KEY4", "GROQ_API_KEY5", "GROQ_API_KEY6", "GROQ_API_KEY7",
    ] if (v := _env(name))
]
GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Azure GPT-4o-mini ────────────────────────────────────────
AZURE_GPT4O_ENDPOINT = _env("AZURE_GPT4O_MINI_ENDPOINT")
AZURE_GPT4O_API_KEY = _env("AZURE_GPT4O_MINI_API_KEY")
AZURE_GPT4O_DEPLOYMENT = _env("AZURE_GPT4O_MINI_DEPLOYMENT_NAME", "gpt-4o-mini")
AZURE_GPT4O_VERSION = _env("AZURE_GPT4O_MINI_VERSION", "2024-12-01-preview")

# ── Azure DeepSeek-V3.2 ─────────────────────────────────────
DEEPSEEK_ENDPOINT = _env("DEEPSEEK_ENDPOINT")
DEEPSEEK_API_KEY = _env("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = _env("DEEPSEEK_MODEL_NAME", "DeepSeek-V3.2")
DEEPSEEK_VERSION = _env("DEEPSEEK_API_VERSION", "2024-05-01-preview")

# ── Azure Mistral ────────────────────────────────────────────
MISTRAL_ENDPOINT = _env("Mistral_endpoint")
MISTRAL_API_KEY = _env("Mistral_api_key")
MISTRAL_DEPLOYMENT = _env("Mistral_deployment_name", "mistral-medium-2505")

# ── Azure Kimi-K2 ────────────────────────────────────────────
KIMI_ENDPOINT = _env("AZURE_KIMI_ENDPOINT")
KIMI_API_KEY = _env("AZURE_KIMI_API_KEY")
KIMI_DEPLOYMENT = _env("AZURE_KIMI_VERSION_DEPLOYMENT", "Kimi-K2-Thinking")

# ── Azure Phi-4-reasoning ────────────────────────────────────
PHI4_ENDPOINT = _env("Phi-4-reasoning_endpoint")
PHI4_API_KEY = _env("Phi-4-reasoning_api_key")
PHI4_DEPLOYMENT = _env("Phi-4-reasoning_deployment_name", "Phi-4-reasoning")

# ── Cloudflare Workers (FREE) ────────────────────────────────
CF_GLM_URL = _env("CF_WORKER_GLM_URL")
CF_GLM_TOKEN = _env("CF_WORKER_GLM_TOKEN")
CF_QWEN_URL = _env("CF_WORKER_QWEN_URL")
CF_QWEN_TOKEN = _env("CF_WORKER_QWEN_TOKEN") or _env("CF_WORKER_BEARER_TOKEN")
CF_GEMMA_URL = _env("CF_WORKER_GEMMA_URL")
CF_GEMMA_TOKEN = _env("CF_WORKER_GEMMA_TOKEN")

# ── OpenRouter (FREE) ────────────────────────────────────────
OPENROUTER_KEY = _env("openroute_service_api_key")
OPENROUTER_MODEL = _env("openroute_model_free", "qwen/qwen3-plus:free")

# ── Image Generation ─────────────────────────────────────────
CF_PHOENIX_URL = _env("CF_WORKER_PHOENIX_URL")
CF_PHOENIX_TOKEN = _env("CF_WORKER_PHOENIX_TOKEN")
CF_LUCID_URL = _env("CF_WORKER_LUCID_URL")
CF_LUCID_TOKEN = _env("CF_WORKER_LUCID_TOKEN")
AZURE_FLUX_ENDPOINT = _env("AZURE_FLUX_ENDPOINT")
AZURE_FLUX_KEY = _env("AZURE_FLUX_API_KEY")
AZURE_FLUX_DEPLOYMENT = _env("AZURE_FLUX_DEPLOYMENT_NAME", "FLUX.1-Kontext-pro")
