"""
Multi-Provider LLM Router with priority-based fallback and round-robin.

Implements the V9 Meridian Model Routing strategy:
  Standard Mode → FREE models only (Groq → Cloudflare → OpenRouter)
  Premium Mode  → Azure paid (GPT-4o-mini → DeepSeek → Mistral) → fallback to free
"""
import httpx
import json
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

import config

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    latency: float
    cost: float
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass
class CallRecord:
    provider: str
    model: str
    latency: float
    cost: float
    success: bool
    error: str = ""
    timestamp: float = field(default_factory=time.time)


class LLMRouter:
    """Routes LLM requests across providers with automatic fallback."""

    def __init__(self):
        self._groq_idx = 0
        self._calls: list[CallRecord] = []
        self._total_cost = 0.0

    @property
    def call_log(self) -> list[CallRecord]:
        return self._calls

    @property
    def total_cost(self) -> float:
        return self._total_cost

    @property
    def total_calls(self) -> int:
        return len(self._calls)

    def get_providers(self, mode: str = "standard") -> list[dict]:
        """List available providers for the selected mode."""
        providers = []
        if config.GROQ_API_KEYS:
            providers.append({
                "name": "Groq", "model": config.GROQ_MODEL,
                "tier": "FREE", "detail": f"{len(config.GROQ_API_KEYS)} keys (round-robin)",
            })
        if config.CF_GLM_URL:
            providers.append({"name": "Cloudflare GLM", "model": "GLM-4.7-Flash", "tier": "FREE", "detail": "Workers AI"})
        if config.CF_QWEN_URL:
            providers.append({"name": "Cloudflare Qwen", "model": "Qwen-2.5-Coder-32B", "tier": "FREE", "detail": "Workers AI"})
        if config.OPENROUTER_KEY:
            providers.append({"name": "OpenRouter", "model": config.OPENROUTER_MODEL, "tier": "FREE", "detail": "Free tier"})
        if mode == "premium":
            if config.AZURE_GPT4O_API_KEY:
                providers.append({"name": "Azure GPT-4o-mini", "model": config.AZURE_GPT4O_DEPLOYMENT, "tier": "PAID", "detail": "~$0.15/1M tokens"})
            if config.DEEPSEEK_API_KEY:
                providers.append({"name": "Azure DeepSeek", "model": config.DEEPSEEK_MODEL, "tier": "PAID", "detail": "~$0.30/1M tokens"})
            if config.MISTRAL_API_KEY:
                providers.append({"name": "Azure Mistral", "model": config.MISTRAL_DEPLOYMENT, "tier": "PAID", "detail": "~$0.40/1M tokens"})
            if config.KIMI_API_KEY:
                providers.append({"name": "Azure Kimi-K2", "model": config.KIMI_DEPLOYMENT, "tier": "PAID", "detail": "Reasoning model"})
        return providers

    def chat(
        self,
        messages: list[dict],
        mode: str = "standard",
        max_tokens: int = 4000,
    ) -> LLMResponse:
        """Route a chat request to the best available provider."""
        if mode == "premium":
            return self._premium_route(messages, max_tokens)
        return self._standard_route(messages, max_tokens)

    # ── Standard Route (FREE only) ───────────────────────────

    def _standard_route(self, messages: list[dict], max_tokens: int) -> LLMResponse:
        errors: list[str] = []

        # 1. Groq (fastest free — round-robin across keys)
        if config.GROQ_API_KEYS:
            key = config.GROQ_API_KEYS[self._groq_idx % len(config.GROQ_API_KEYS)]
            self._groq_idx += 1
            try:
                return self._call_openai_compat(
                    url="https://api.groq.com/openai/v1/chat/completions",
                    api_key=key, model=config.GROQ_MODEL,
                    messages=messages, max_tokens=max_tokens,
                    provider_name="Groq",
                )
            except Exception as e:
                errors.append(f"Groq: {e}")
                self._calls.append(CallRecord("Groq", config.GROQ_MODEL, 0, 0, False, str(e)))

        # 2. Cloudflare GLM (free worker)
        if config.CF_GLM_URL:
            try:
                return self._call_cloudflare(
                    config.CF_GLM_URL, config.CF_GLM_TOKEN,
                    "GLM-4.7-Flash", messages, max_tokens,
                )
            except Exception as e:
                errors.append(f"CF-GLM: {e}")
                self._calls.append(CallRecord("CF-GLM", "GLM-4.7-Flash", 0, 0, False, str(e)))

        # 3. Cloudflare Qwen (free worker)
        if config.CF_QWEN_URL:
            try:
                return self._call_cloudflare(
                    config.CF_QWEN_URL, config.CF_QWEN_TOKEN,
                    "Qwen-2.5-Coder-32B", messages, max_tokens,
                )
            except Exception as e:
                errors.append(f"CF-Qwen: {e}")
                self._calls.append(CallRecord("CF-Qwen", "Qwen-2.5-Coder-32B", 0, 0, False, str(e)))

        # 4. OpenRouter (free tier)
        if config.OPENROUTER_KEY:
            try:
                return self._call_openai_compat(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    api_key=config.OPENROUTER_KEY, model=config.OPENROUTER_MODEL,
                    messages=messages, max_tokens=max_tokens,
                    provider_name="OpenRouter",
                )
            except Exception as e:
                errors.append(f"OpenRouter: {e}")
                self._calls.append(CallRecord("OpenRouter", config.OPENROUTER_MODEL, 0, 0, False, str(e)))

        raise RuntimeError(f"All standard providers failed: {'; '.join(errors)}")

    # ── Premium Route (Azure paid → fallback free) ───────────

    def _premium_route(self, messages: list[dict], max_tokens: int) -> LLMResponse:
        errors: list[str] = []

        # 1. Azure GPT-4o-mini (cheapest paid)
        if config.AZURE_GPT4O_API_KEY:
            try:
                return self._call_azure(
                    endpoint=config.AZURE_GPT4O_ENDPOINT,
                    api_key=config.AZURE_GPT4O_API_KEY,
                    deployment=config.AZURE_GPT4O_DEPLOYMENT,
                    api_version=config.AZURE_GPT4O_VERSION,
                    messages=messages, max_tokens=max_tokens,
                    provider_name="Azure GPT-4o-mini",
                    cost_in=0.00015, cost_out=0.0006,
                )
            except Exception as e:
                errors.append(f"Azure GPT-4o-mini: {e}")
                self._calls.append(CallRecord("Azure GPT-4o-mini", config.AZURE_GPT4O_DEPLOYMENT, 0, 0, False, str(e)))

        # 2. Azure DeepSeek-V3.2
        if config.DEEPSEEK_API_KEY:
            try:
                return self._call_azure(
                    endpoint=config.DEEPSEEK_ENDPOINT,
                    api_key=config.DEEPSEEK_API_KEY,
                    deployment=config.DEEPSEEK_MODEL,
                    api_version=config.DEEPSEEK_VERSION,
                    messages=messages, max_tokens=max_tokens,
                    provider_name="Azure DeepSeek-V3.2",
                    cost_in=0.0003, cost_out=0.0012,
                )
            except Exception as e:
                errors.append(f"Azure DeepSeek: {e}")
                self._calls.append(CallRecord("Azure DeepSeek", config.DEEPSEEK_MODEL, 0, 0, False, str(e)))

        # 3. Azure Mistral-medium
        if config.MISTRAL_API_KEY:
            try:
                return self._call_azure(
                    endpoint=config.MISTRAL_ENDPOINT,
                    api_key=config.MISTRAL_API_KEY,
                    deployment=config.MISTRAL_DEPLOYMENT,
                    api_version="2024-12-01-preview",
                    messages=messages, max_tokens=max_tokens,
                    provider_name="Azure Mistral-medium",
                    cost_in=0.0004, cost_out=0.0012,
                )
            except Exception as e:
                errors.append(f"Azure Mistral: {e}")
                self._calls.append(CallRecord("Azure Mistral", config.MISTRAL_DEPLOYMENT, 0, 0, False, str(e)))

        # Fallback to free models
        try:
            return self._standard_route(messages, max_tokens)
        except RuntimeError as e:
            errors.append(f"Free fallback: {e}")

        raise RuntimeError(f"All providers failed: {'; '.join(errors)}")

    # ── Provider Implementations ─────────────────────────────

    def _call_openai_compat(
        self, url: str, api_key: str, model: str,
        messages: list[dict], max_tokens: int, provider_name: str,
    ) -> LLMResponse:
        """Call any OpenAI-compatible API (Groq, OpenRouter)."""
        start = time.time()
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        text = data["choices"][0]["message"]["content"]
        latency = time.time() - start
        usage = data.get("usage", {})

        result = LLMResponse(
            text=text, model=model,
            provider=f"{provider_name} (FREE)",
            latency=latency, cost=0.0,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
        )
        self._calls.append(CallRecord(provider_name, model, latency, 0.0, True))
        return result

    def _call_azure(
        self, endpoint: str, api_key: str, deployment: str,
        api_version: str, messages: list[dict], max_tokens: int,
        provider_name: str, cost_in: float = 0, cost_out: float = 0,
    ) -> LLMResponse:
        """Call Azure OpenAI or Azure AI Foundry endpoint."""
        start = time.time()

        # Azure AI Foundry endpoints include /openai/v1/ in the path
        if "/openai/v1" in endpoint:
            url = f"{endpoint.rstrip('/')}/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        else:
            url = f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
            headers = {"api-key": api_key, "Content-Type": "application/json"}

        body = {"messages": messages, "max_tokens": max_tokens, "temperature": 0.7}

        with httpx.Client(timeout=90.0) as client:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()

        text = data["choices"][0]["message"]["content"]
        latency = time.time() - start
        usage = data.get("usage", {})
        ti = usage.get("prompt_tokens", 0)
        to = usage.get("completion_tokens", 0)
        cost = (ti / 1000) * cost_in + (to / 1000) * cost_out
        self._total_cost += cost

        result = LLMResponse(
            text=text, model=deployment,
            provider=provider_name,
            latency=latency, cost=cost,
            tokens_in=ti, tokens_out=to,
        )
        self._calls.append(CallRecord(provider_name, deployment, latency, cost, True))
        return result

    def _call_cloudflare(
        self, url: str, token: str, model_name: str,
        messages: list[dict], max_tokens: int,
    ) -> LLMResponse:
        """Call Cloudflare Workers AI endpoint.

        CF Workers in this project use:
          POST /  with {"message": "..."} body
        """
        start = time.time()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # Cloudflare Workers expect {"message": "..."} format
        # Combine messages into a single prompt
        combined = "\n".join(
            f"{'User' if m['role'] == 'user' else 'System'}: {m['content']}"
            for m in messages
        )

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                url.rstrip("/") + "/",
                headers=headers,
                json={"message": combined},
            )
            resp.raise_for_status()
            data = resp.json()

        # Workers can return in different formats
        if isinstance(data, dict):
            if "choices" in data:
                text = data["choices"][0]["message"]["content"]
            elif "result" in data:
                r = data["result"]
                text = r.get("response", r) if isinstance(r, dict) else str(r)
            elif "response" in data:
                text = data["response"]
            elif "message" in data:
                text = data["message"]
            else:
                text = json.dumps(data)
        else:
            text = str(data)

        latency = time.time() - start
        result = LLMResponse(
            text=text, model=model_name,
            provider=f"Cloudflare {model_name} (FREE)",
            latency=latency, cost=0.0,
        )
        self._calls.append(CallRecord(f"CF-{model_name}", model_name, latency, 0.0, True))
        return result
