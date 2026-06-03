"""LLM cost estimates used for per-deck observability."""

from __future__ import annotations

from typing import Any


MODEL_COST_PER_1K_TOKENS: dict[str, float] = {
    "gpt-4o-mini": 0.000150,
    "kimi-k2-thinking": 0.0,
    "kimi-2.6": 0.0,
    "deepseek-v3": 0.0,
    "gpt-oss-120b": 0.0,
    "phi-4-reasoning": 0.0,
    "mistral-medium": 0.0,
    "groq": 0.0,
    "cf-qwen": 0.0,
    "cf-gemma": 0.0,
    "cf-glm": 0.0,
    "openrouter": 0.0,
}

FREE_PROVIDER_RATES: dict[str, float] = {
    "groq": 0.0,
    "cloudflare": 0.0,
    "openrouter": 0.0,
    "nvidia": 0.0,
    "huggingface": 0.0,
    "local": 0.0,
}


def rate_for(model: str, provider: str | None = None) -> float:
    provider_key = (provider or "").strip().lower()
    if provider_key in FREE_PROVIDER_RATES:
        return FREE_PROVIDER_RATES[provider_key]
    return MODEL_COST_PER_1K_TOKENS.get((model or "").strip().lower(), 0.0)


def estimate_cost_from_token_usage(token_usage: Any) -> dict[str, Any]:
    """Build a JSON-safe provider cost estimate from a token summary."""
    if hasattr(token_usage, "by_model"):
        by_model = getattr(token_usage, "by_model", []) or []
        total_tokens = int(getattr(token_usage, "total_tokens", 0) or 0)
    elif isinstance(token_usage, dict):
        by_model = token_usage.get("by_model") or []
        total_tokens = int(token_usage.get("total_tokens") or 0)
    else:
        by_model = []
        total_tokens = 0

    by_provider: dict[str, dict[str, Any]] = {}
    total_usd = 0.0
    for row in by_model:
        if isinstance(row, dict):
            model = str(row.get("model") or "unknown")
            provider = str(row.get("provider") or "unknown")
            tokens = int(row.get("total_tokens") or row.get("tokens") or 0)
        else:
            model = str(getattr(row, "model", "unknown"))
            provider = str(getattr(row, "provider", "unknown"))
            tokens = int(getattr(row, "total_tokens", 0) or 0)
        usd = (tokens / 1000.0) * rate_for(model, provider)
        total_usd += usd
        bucket = by_provider.setdefault(
            provider,
            {"provider": provider, "tokens": 0, "estimated_cost_usd": 0.0, "models": []},
        )
        bucket["tokens"] += tokens
        bucket["estimated_cost_usd"] += usd
        bucket["models"].append(
            {"model": model, "tokens": tokens, "estimated_cost_usd": round(usd, 6)}
        )

    return {
        "currency": "USD",
        "estimated_total_usd": round(total_usd, 6),
        "total_tokens": total_tokens,
        "by_provider": [
            {**row, "estimated_cost_usd": round(float(row["estimated_cost_usd"]), 6)}
            for row in by_provider.values()
        ],
    }
