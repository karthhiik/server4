"""
Azure AI / OpenAI-compatible clients — handles GPT-4o-mini, DeepSeek-V3, Kimi-K2-Thinking, Mistral-medium.
All use the standard OpenAI SDK (not Azure-specific) with custom base_url endpoints.
"""

import time
from typing import Optional

from openai import AsyncOpenAI

from app.config import settings
from app.services.llm.base_client import BaseLLMClient, LLMResponse

import structlog

logger = structlog.get_logger()


class AzureGPT4oMiniClient(BaseLLMClient):
    """T2: GPT-4o-mini — Fast structured JSON, workhorse."""

    name = "gpt-4o-mini"
    provider = "azure-openai"

    def __init__(self):
        endpoint = settings.AZURE_GPT4O_MINI_ENDPOINT.strip().strip('"')
        api_key = settings.AZURE_GPT4O_MINI_API_KEY.strip().strip('"')
        self._client = (
            AsyncOpenAI(
                base_url=endpoint.rstrip("/") if endpoint else None,
                api_key=api_key,
            )
            if endpoint
            else None
        )

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        if not self._client:
            raise ConnectionError("GPT-4o-mini not configured")

        start = time.monotonic()
        kwargs: dict = {
            "model": model or settings.AZURE_GPT4O_MINI_DEPLOYMENT.strip().strip('"'),
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


class AzurePhi4Client(BaseLLMClient):
    """T0.5: Phi-4-reasoning — Reasoning and problem solving."""

    name = "phi-4-reasoning"
    provider = "azure-ai"

    def __init__(self):
        endpoint = settings.PHI4_REASONING_ENDPOINT.strip().strip('"')
        api_key = settings.PHI4_REASONING_API_KEY.strip().strip('"')
        self._client = (
            AsyncOpenAI(
                base_url=endpoint.rstrip("/") if endpoint else None,
                api_key=api_key,
            )
            if endpoint
            else None
        )

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        if not self._client:
            raise ConnectionError("Phi-4-reasoning not configured")

        start = time.monotonic()
        deployment = settings.PHI4_REASONING_DEPLOYMENT.strip().strip('"')
        kwargs: dict = {
            "model": model or deployment,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        resp = await self._client.chat.completions.create(**kwargs)
        elapsed = int((time.monotonic() - start) * 1000)

        content = resp.choices[0].message.content or ""

        # Handle reasoning model - content may be None but reasoning in reasoning_content
        if not content and hasattr(resp.choices[0].message, "reasoning_content"):
            reasoning = resp.choices[0].message.reasoning_content
            if reasoning:
                # Extract final answer from reasoning
                lines = reasoning.split("\n")
                content = lines[-1] if lines else "[See reasoning]"

        return LLMResponse(
            content=content,
            model=self.name,
            provider=self.provider,
            tokens_used=resp.usage.total_tokens if resp.usage else 0,
            latency_ms=elapsed,
        )


class AzureDeepSeekClient(BaseLLMClient):
    """T1: DeepSeek-V3.2 — Storytelling & narrative content."""

    name = "deepseek-v3"
    provider = "azure-ai"

    def __init__(self):
        endpoint = settings.DEEPSEEK_ENDPOINT.strip().strip('"')
        api_key = settings.DEEPSEEK_API_KEY.strip().strip('"')
        self._client = (
            AsyncOpenAI(
                base_url=endpoint.rstrip("/") if endpoint else None,
                api_key=api_key,
            )
            if endpoint
            else None
        )

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        if not self._client:
            raise ConnectionError("DeepSeek-V3 not configured")

        start = time.monotonic()
        kwargs: dict = {
            "model": model or settings.DEEPSEEK_MODEL_NAME.strip().strip('"'),
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


class AzureKimiClient(BaseLLMClient):
    """T0: Kimi-K2-Thinking — Deep reasoning & planning."""

    name = "kimi-k2-thinking"
    provider = "azure-ai"

    def __init__(self):
        endpoint = settings.AZURE_KIMI_ENDPOINT.strip().strip('"')
        api_key = settings.AZURE_KIMI_API_KEY.strip().strip('"')
        self._client = (
            AsyncOpenAI(
                base_url=endpoint.rstrip("/") if endpoint else None,
                api_key=api_key,
            )
            if endpoint
            else None
        )

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        if not self._client:
            raise ConnectionError("Kimi-K2 not configured")

        start = time.monotonic()
        kwargs: dict = {
            "model": model or settings.AZURE_KIMI_DEPLOYMENT.strip().strip('"'),
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


class AzureMistralClient(BaseLLMClient):
    """T3: Mistral-medium-2505 — Technical & code content."""

    name = "mistral-medium"
    provider = "azure-ai"

    def __init__(self):
        endpoint = settings.MISTRAL_ENDPOINT.strip().strip('"')
        api_key = settings.MISTRAL_API_KEY.strip().strip('"')
        self._client = (
            AsyncOpenAI(
                base_url=endpoint.rstrip("/") if endpoint else None,
                api_key=api_key,
            )
            if endpoint
            else None
        )

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        if not self._client:
            raise ConnectionError("Mistral not configured")

        deployment = settings.MISTRAL_DEPLOYMENT.strip().strip('"')
        start = time.monotonic()
        kwargs: dict = {
            "model": model or deployment,
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
