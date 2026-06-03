"""
OpenRouter Client — Multi-model free tier access.

Models configured:
  - openrouter (qwen/qwen3.6-plus:free) — universal safety net
  - openrouter-glm45 (z-ai/glm-4.5-air:free) — GLM 4.5 for standard mode
  - openrouter-gemma (google/gemma-4-31b-it:free) — Gemma for standard mode
  - openrouter-nvidia (nvidia/nemotron-3-super-120b-a12b:free) — NVIDIA free
  - openrouter-minimax (minimax/minimax-m2.5:free) — MiniMax free
"""

import time
from typing import Optional

from openai import AsyncOpenAI

from app.config import settings
from app.services.llm.base_client import BaseLLMClient, LLMResponse

import structlog

logger = structlog.get_logger()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterClient(BaseLLMClient):
    """T7: OpenRouter free tier — qwen/qwen3.6-plus:free (universal safety net)"""

    name = "openrouter"
    provider = "openrouter"

    def __init__(self):
        api_key = settings.OPENROUTE_SERVICE_API_KEY.strip().strip('"')
        self._client = (
            AsyncOpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=api_key,
            )
            if api_key
            else None
        )
        self._model = "qwen/qwen3.6-plus:free"

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        if not self._client:
            raise ConnectionError("OpenRouter not configured")

        start = time.monotonic()
        kwargs: dict = {
            "model": model or self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        resp = await self._client.chat.completions.create(**kwargs)
        elapsed = int((time.monotonic() - start) * 1000)

        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=self.name,
            provider=self.provider,
            tokens_used=resp.usage.total_tokens if resp.usage else 0,
            latency_ms=elapsed,
        )


class OpenRouterGLM45Client(BaseLLMClient):
    """OpenRouter GLM 4.5 Air (free tier) — fast structured JSON for standard mode"""

    name = "openrouter-glm45"
    provider = "openrouter"

    def __init__(self):
        api_key = settings.OPENROUTER_APIKEY_GLM45.strip().strip('"')
        self._client = (
            AsyncOpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
            if api_key else None
        )
        self._model = settings.OPENROUTER_MODEL_GLM45 or "z-ai/glm-4.5-air:free"

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        if not self._client:
            raise ConnectionError("OpenRouter GLM 4.5 not configured")
        start = time.monotonic()
        kwargs: dict = {
            "model": model or self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        resp = await self._client.chat.completions.create(**kwargs)
        elapsed = int((time.monotonic() - start) * 1000)
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=self.name,
            provider=self.provider,
            tokens_used=resp.usage.total_tokens if resp.usage else 0,
            latency_ms=elapsed,
        )


class OpenRouterGemmaClient(BaseLLMClient):
    """OpenRouter Gemma-4-31b (free tier) — narrative content for standard mode"""

    name = "openrouter-gemma"
    provider = "openrouter"

    def __init__(self):
        api_key = settings.OPENROUTER_APIKEY_GEMMA.strip().strip('"')
        self._client = (
            AsyncOpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
            if api_key else None
        )
        self._model = settings.OPENROUTER_MODEL_GEMMA or "google/gemma-4-31b-it:free"

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        if not self._client:
            raise ConnectionError("OpenRouter Gemma not configured")
        start = time.monotonic()
        kwargs: dict = {
            "model": model or self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        resp = await self._client.chat.completions.create(**kwargs)
        elapsed = int((time.monotonic() - start) * 1000)
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=self.name,
            provider=self.provider,
            tokens_used=resp.usage.total_tokens if resp.usage else 0,
            latency_ms=elapsed,
        )


class OpenRouterNvidiaClient(BaseLLMClient):
    """OpenRouter NVIDIA Nemotron (free tier) — reasoning for premium mode"""

    name = "openrouter-nvidia"
    provider = "openrouter"

    def __init__(self):
        api_key = settings.OPENROUTER_APIKEY_NVIDIA.strip().strip('"')
        self._client = (
            AsyncOpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
            if api_key else None
        )
        self._model = settings.OPENROUTER_MODEL_NVIDIA or "nvidia/nemotron-3-super-120b-a12b:free"

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        if not self._client:
            raise ConnectionError("OpenRouter NVIDIA not configured")
        start = time.monotonic()
        kwargs: dict = {
            "model": model or self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        resp = await self._client.chat.completions.create(**kwargs)
        elapsed = int((time.monotonic() - start) * 1000)
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=self.name,
            provider=self.provider,
            tokens_used=resp.usage.total_tokens if resp.usage else 0,
            latency_ms=elapsed,
        )


class OpenRouterMiniMaxClient(BaseLLMClient):
    """OpenRouter MiniMax M2.5 (free tier) — long-form composition"""

    name = "openrouter-minimax"
    provider = "openrouter"

    def __init__(self):
        api_key = settings.OPENROUTER_APIKEY_MINIMAX.strip().strip('"')
        self._client = (
            AsyncOpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
            if api_key else None
        )
        self._model = settings.OPENROUTER_MODEL_MINIMAX or "minimax/minimax-m2.5:free"

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        if not self._client:
            raise ConnectionError("OpenRouter MiniMax not configured")
        start = time.monotonic()
        kwargs: dict = {
            "model": model or self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        resp = await self._client.chat.completions.create(**kwargs)
        elapsed = int((time.monotonic() - start) * 1000)
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=self.name,
            provider=self.provider,
            tokens_used=resp.usage.total_tokens if resp.usage else 0,
            latency_ms=elapsed,
        )
