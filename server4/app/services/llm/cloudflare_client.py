"""
T5: Cloudflare Workers AI — Emergency fallback.
GLM (text), Qwen (code), Gemma (design), Lucid (creative images).

Modes:
  - "openai": Standard OpenAI-compatible workers (messages/choices format)
  - "text":   Simple text workers from pp.py pattern (message/response format)
  - "image":  Image generation workers from pp.py pattern (prompt → raw bytes)
"""

import json
import time
from typing import Optional

import httpx

from app.config import settings
from app.services.llm.base_client import BaseLLMClient, LLMResponse

import structlog

logger = structlog.get_logger()


class CloudflareWorkerClient(BaseLLMClient):
    """Generic Cloudflare Worker LLM client with mode switching."""

    @staticmethod
    def _build_text_prompt(messages: list[dict[str, str]], response_format: Optional[dict]) -> str:
        parts = [f"{m.get('role', 'user').upper()}:\n{m.get('content', '')}" for m in messages]
        prompt = "\n\n".join(parts)
        if response_format and response_format.get("type") == "json_object":
            prompt += (
                "\n\nSTRICT OUTPUT CONTRACT:\n"
                "Return ONLY one valid JSON object. No prose. No markdown fences. "
                "The first character must be { and the last character must be }."
            )
        return prompt

    @staticmethod
    def _extract_first_json_object(text: str) -> Optional[str]:
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escaped = False
        for idx in range(start, len(text)):
            ch = text[idx]
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:idx + 1]
        return None

    @classmethod
    def _normalize_json_content(cls, content: str) -> str:
        try:
            return json.dumps(json.loads(content), ensure_ascii=False)
        except Exception:
            extracted = cls._extract_first_json_object(content)
            if not extracted:
                raise ValueError("Cloudflare text worker did not return a valid JSON object")
            return json.dumps(json.loads(extracted), ensure_ascii=False)

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
            prompt = self._build_text_prompt(messages, response_format)
            payload = {"message": prompt}
        else:
            # OpenAI-compatible format
            payload = {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                payload["response_format"] = response_format

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
            if response_format and response_format.get("type") == "json_object":
                content = self._normalize_json_content(content)
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


def create_cf_phoenix_client() -> CloudflareWorkerClient:
    return CloudflareWorkerClient(
        "cf-phoenix",
        settings.CF_WORKER_PHOENIX_URL,
        settings.CF_WORKER_PHOENIX_TOKEN,
        mode="image",
    )


def create_cf_lucid_client() -> CloudflareWorkerClient:
    return CloudflareWorkerClient(
        "cf-lucid",
        settings.CF_WORKER_LUCID_URL,
        settings.CF_WORKER_LUCID_TOKEN,
        mode="image",
    )
