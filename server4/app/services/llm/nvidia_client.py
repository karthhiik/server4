"""
NVIDIA NIM OpenAI-compatible chat-completions client.

NVIDIA Build (https://build.nvidia.com) exposes serverless free-tier models
through a single OpenAI-compatible endpoint:

    POST https://integrate.api.nvidia.com/v1/chat/completions
    Authorization: Bearer <nvapi-...>
    {"model": "z-ai/glm4.7", "messages": [...], ...}

Each model in the user's free-tier inventory has its own API key (separate
quota buckets), but the URL and request schema are identical for all.

The 6 models wired here:
  - z-ai/glm-5.1                       (limited free, premium narrative)
  - z-ai/glm4.7                        (free, fast writer)
  - minimaxai/minimax-m2.7             (free, long-form composition)
  - google/gemma-4-31b-it              (free, multimodal-capable text)
  - stepfun-ai/step-3.5-flash          (free, ultra-fast critic/refiner)
  - mistralai/devstral-2-123b-instruct-2512 (free, code/diagram)

Keys are read directly from server4/.env via python-dotenv (the FastAPI
runtime uses pydantic-settings; this client deliberately does not depend on
the Settings class so it can also work in standalone test harnesses).
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

import httpx
import structlog

from app.services.llm.base_client import BaseLLMClient, LLMResponse

logger = structlog.get_logger(__name__)

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


def _load_env_keys() -> dict[str, str]:
    """Load NVIDIA-related keys from server4/.env without polluting os.environ.

    Returns a dict {env_key: value}. Keys may contain dots (`glm_5.1_apikey`)
    which are valid in dotenv but not in pydantic field names — that's why
    we read the file directly.
    """
    env: dict[str, str] = {}
    # First pull whatever is already in the process env (e.g. tests/v10_e2e_runner
    # already calls load_dotenv()).
    for k, v in os.environ.items():
        env[k] = v
    # Then layer the .env file (does not overwrite existing process env)
    env_path = Path(__file__).resolve().parents[2].parent / ".env"  # server4/.env
    if env_path.exists():
        try:
            from dotenv import dotenv_values  # type: ignore

            for k, v in dotenv_values(str(env_path)).items():
                if v is not None and k not in env:
                    env[k] = v
        except Exception:  # noqa: BLE001
            pass
    return env


# Map: internal model name → (NVIDIA model id, env key holding API key)
NVIDIA_MODEL_REGISTRY: dict[str, tuple[str, str]] = {
    "nv-glm-5.1":         ("z-ai/glm-5.1",                              "glm_5.1_apikey"),
    "nv-glm-4.7":         ("z-ai/glm4.7",                               "glm_4.7_apikey"),
    "nv-minimax-m2.7":    ("minimaxai/minimax-m2.7",                    "minimax_m2.7_apikey"),
    "nv-gemma-4-31b":     ("google/gemma-4-31b-it",                     "gemma_apikey"),
    "nv-step-3.5-flash":  ("stepfun-ai/step-3.5-flash",                 "stepfun_apikey"),
    "nv-devstral-2-123b": ("mistralai/devstral-2-123b-instruct-2512",   "mistral_apikey"),
}


class NvidiaNIMClient(BaseLLMClient):
    """One client per NVIDIA model — each holds its own API key.

    OpenAI-compatible: passes messages straight through, supports
    response_format={"type": "json_object"} as some NVIDIA models honor it.
    """

    provider = "nvidia"

    def __init__(self, internal_name: str):
        if internal_name not in NVIDIA_MODEL_REGISTRY:
            raise ValueError(f"Unknown NVIDIA model: {internal_name}")
        self.name = internal_name
        self._model_id, env_key = NVIDIA_MODEL_REGISTRY[internal_name]
        env = _load_env_keys()
        self._api_key = env.get(env_key, "").strip()
        if not self._api_key:
            logger.warning(
                "nvidia_client_missing_key",
                model=internal_name, env_key=env_key,
            )

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        if not self._api_key:
            raise ConnectionError(f"NVIDIA client {self.name} has no API key configured")

        payload: dict = {
            "model": model or self._model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        # Only attach response_format when caller explicitly asked for JSON
        # (not all NVIDIA-hosted models support it; sending it unsolicited
        # can 400 on some endpoints).
        if response_format and response_format.get("type") == "json_object":
            payload["response_format"] = response_format

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                NVIDIA_BASE_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError:
                # Surface response body for diagnosis (truncated)
                body = ""
                try:
                    body = resp.text[:500]
                except Exception:  # noqa: BLE001
                    pass
                logger.warning(
                    "nvidia_call_http_error",
                    model=self.name, status=resp.status_code, body=body,
                )
                raise
            data = resp.json()

        elapsed_ms = int((time.monotonic() - start) * 1000)
        try:
            content = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"NVIDIA response malformed: {e}; raw={str(data)[:300]}") from e

        usage = data.get("usage", {}) or {}
        return LLMResponse(
            content=content,
            model=self.name,
            provider=self.provider,
            tokens_used=int(usage.get("total_tokens", 0) or 0),
            latency_ms=elapsed_ms,
        )


def all_nvidia_clients() -> dict[str, NvidiaNIMClient]:
    """Build one client per registered NVIDIA model.

    Clients without an API key are still registered (so the router sees them)
    but `is_configured` will be False and any attempt to use them raises,
    causing the router to fall through to the next model in the chain.
    """
    return {name: NvidiaNIMClient(name) for name in NVIDIA_MODEL_REGISTRY.keys()}
