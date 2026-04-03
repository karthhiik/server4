"""
OpenRouter Client — Free tier model access.
"""

import time
from typing import Optional

from openai import AsyncOpenAI

from app.config import settings
from app.services.llm.base_client import BaseLLMClient, LLMResponse

import structlog

logger = structlog.get_logger()


class OpenRouterClient(BaseLLMClient):
    """T7: OpenRouter free tier — qwen/qwen3.6-plus:free"""

    name = "openrouter"
    provider = "openrouter"

    def __init__(self):
        api_key = settings.OPENROUTE_SERVICE_API_KEY.strip().strip('"')
        self._client = (
            AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
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
