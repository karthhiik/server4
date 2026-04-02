"""
T4: Groq — 8-key round-robin for ultra-fast inference.
Used for translations, summaries, quick edits.
"""

import time
import threading
from typing import Optional

import httpx

from app.config import settings
from app.services.llm.base_client import BaseLLMClient, LLMResponse

import structlog

logger = structlog.get_logger()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


class GroqRoundRobinClient(BaseLLMClient):
    """
    Round-robin across 8 Groq API keys for ultra-fast inference.
    On rate limit (429), advances to next key.
    On all keys exhausted, raises so model_router can fallback.
    """

    name = "groq"
    provider = "groq"

    def __init__(self):
        self._keys = settings.groq_keys
        self._index = 0
        self._lock = threading.Lock()

    def _next_key(self) -> str:
        with self._lock:
            if not self._keys:
                raise ConnectionError("No Groq API keys configured")
            key = self._keys[self._index % len(self._keys)]
            self._index += 1
            return key

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        if not self._keys:
            raise ConnectionError("No Groq API keys configured")

        errors = []
        for _attempt in range(len(self._keys)):
            key = self._next_key()
            try:
                return await self._call(key, messages, model, temperature, max_tokens, response_format)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning("groq_rate_limited", key_index=self._index - 1)
                    errors.append(f"429 on key {self._index - 1}")
                    continue
                raise
            except Exception as e:
                errors.append(str(e))
                continue

        raise ConnectionError(f"All {len(self._keys)} Groq keys exhausted: {errors}")

    async def _call(
        self,
        api_key: str,
        messages: list[dict[str, str]],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
        response_format: Optional[dict],
    ) -> LLMResponse:
        start = time.monotonic()
        payload: dict = {
            "model": model or DEFAULT_GROQ_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                GROQ_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        elapsed = int((time.monotonic() - start) * 1000)
        usage = data.get("usage", {})

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=self.name,
            provider=self.provider,
            tokens_used=usage.get("total_tokens", 0),
            latency_ms=elapsed,
        )
