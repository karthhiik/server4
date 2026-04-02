"""
T5: Cloudflare Workers AI — Emergency fallback.
GLM (text), Qwen (code), Gemma (design), Lucid (creative images).

Modes:
  - "openai": Standard OpenAI-compatible workers (messages/choices format)
  - "text":   Simple text workers from pp.py pattern (message/response format)
  - "image":  Image generation workers from pp.py pattern (prompt → raw bytes)
"""

import time
from typing import Optional

import httpx

from app.config import settings
from app.services.llm.base_client import BaseLLMClient, LLMResponse

import structlog

logger = structlog.get_logger()


class CloudflareWorkerClient(BaseLLMClient):
    """Generic Cloudflare Worker LLM client with mode switching."""

    def __init__(self, name: str, worker_url: str, token: str, mode: str = "openai"):
        self.name = name
        self.provider = "cloudflare"
        self._url = worker_url
        self._token = token
        self.mode = mode  # "openai" | "text" | "image"

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        if not self._url or not self._token:
            raise ConnectionError(f"CF Worker {self.name} not configured")

        start = time.monotonic()

        # Build payload based on mode
        if self.mode == "text":
            # pp.py pattern: flatten messages to single prompt string
            prompt = "\n".join(m["content"] for m in messages)
            payload = {"message": prompt}
        else:
            # OpenAI-compatible format
            payload = {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                self._url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        elapsed = int((time.monotonic() - start) * 1000)

        # Response parsing per mode
        if self.mode == "text":
            # Text workers return response in various keys (pp.py pattern)
            content = (
                data.get("response")
                or data.get("content")
                or data.get("output")
                or str(data)
            )
        else:
            # OpenAI-compatible or unknown format
            content = ""
            if isinstance(data, dict):
                if "choices" in data:
                    content = data["choices"][0]["message"]["content"]
                elif "result" in data:
                    content = data["result"].get("response", str(data["result"]))
                elif "response" in data:
                    content = data["response"]
                else:
                    content = str(data)
            else:
                content = str(data)

        return LLMResponse(
            content=content,
            model=self.name,
            provider=self.provider,
            tokens_used=0,
            latency_ms=elapsed,
        )

    async def generate_image(self, prompt: str) -> bytes:
        """Generate image via Lucid worker (pp.py pattern).

        Sends {"prompt": "..."} and returns raw image bytes.
        """
        if not self._url or not self._token:
            raise ConnectionError(f"CF Worker {self.name} not configured")

        start = time.monotonic()
        payload = {"prompt": prompt}

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self._url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            image_bytes = resp.content

        elapsed = int((time.monotonic() - start) * 1000)
        logger.info(
            "cf_image_generated",
            worker=self.name,
            size_kb=len(image_bytes) // 1024,
            latency_ms=elapsed,
        )
        return image_bytes


def create_cf_glm_client() -> CloudflareWorkerClient:
    return CloudflareWorkerClient(
        "cf-glm", settings.CF_WORKER_GLM_URL, settings.CF_WORKER_GLM_TOKEN, mode="text"
    )


def create_cf_qwen_client() -> CloudflareWorkerClient:
    return CloudflareWorkerClient(
        "cf-qwen",
        settings.CF_WORKER_QWEN_URL,
        settings.CF_WORKER_QWEN_TOKEN,
        mode="text",
    )


def create_cf_gemma_client() -> CloudflareWorkerClient:
    return CloudflareWorkerClient(
        "cf-gemma",
        settings.CF_WORKER_GEMMA_URL,
        settings.CF_WORKER_GEMMA_TOKEN,
        mode="text",
    )


def create_cf_lucid_client() -> CloudflareWorkerClient:
    return CloudflareWorkerClient(
        "cf-lucid",
        settings.CF_WORKER_LUCID_URL,
        settings.CF_WORKER_LUCID_TOKEN,
        mode="image",
    )
