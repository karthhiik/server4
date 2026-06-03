"""
V4 Token Usage Tracker — Aggregates token consumption per generation.

Collects token counts from the ModelRouter's trace system and produces a
compact summary that is:
  1. Persisted to MongoDB alongside the presentation document
  2. Emitted via WebSocket progress so the frontend can display it
  3. Logged for cost monitoring

This module does NOT interfere with the generation pipeline — it reads
the trace that ModelRouter already records and computes aggregates.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ModelTokenUsage:
    """Token usage for a single model across all phases."""
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    call_count: int = 0
    failed_calls: int = 0
    total_latency_ms: int = 0


@dataclass
class PhaseTokenUsage:
    """Token usage for a single pipeline phase."""
    phase: str
    task: Optional[str] = None
    total_tokens: int = 0
    call_count: int = 0
    models_used: List[str] = field(default_factory=list)
    latency_ms: int = 0


@dataclass
class TokenUsageSummary:
    """Complete token usage summary for a single generation."""
    generation_id: str
    project_id: str
    mode: str
    total_tokens: int = 0
    total_calls: int = 0
    total_failed_calls: int = 0
    total_latency_ms: int = 0
    by_model: List[ModelTokenUsage] = field(default_factory=list)
    by_phase: List[PhaseTokenUsage] = field(default_factory=list)
    estimated_cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_compact_dict(self) -> Dict[str, Any]:
        """Compact representation for WebSocket emission and frontend display."""
        return {
            "total_tokens": self.total_tokens,
            "total_calls": self.total_calls,
            "total_failed_calls": self.total_failed_calls,
            "total_latency_ms": self.total_latency_ms,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "top_models": [
                {"model": m.model, "tokens": m.total_tokens, "calls": m.call_count}
                for m in sorted(self.by_model, key=lambda x: x.total_tokens, reverse=True)[:5]
            ],
            "phases": [
                {"phase": p.phase, "tokens": p.total_tokens, "calls": p.call_count}
                for p in self.by_phase
            ],
        }


# ── Cost estimation (approximate, based on free-tier / Azure pricing) ──
# These are rough per-1K-token costs. Most of our models are free-tier
# or Azure pay-as-you-go. The tracker uses these for transparency only.
_COST_PER_1K_TOKENS: Dict[str, float] = {
    "kimi-k2-thinking": 0.0,       # Azure free-tier
    "kimi-2.6": 0.0,               # Azure free-tier
    "deepseek-v3": 0.0,            # Azure free-tier
    "gpt-4o-mini": 0.000150,       # Azure ~$0.15/1M input
    "gpt-oss-120b": 0.0,           # Azure free-tier
    "phi-4-reasoning": 0.0,        # Azure free-tier
    "mistral-medium": 0.0,         # Azure free-tier
    "groq": 0.0,                   # Groq free-tier
    "cf-qwen": 0.0,                # Cloudflare Workers free
    "cf-gemma": 0.0,               # Cloudflare Workers free
    "cf-glm": 0.0,                 # Cloudflare Workers free
    "openrouter": 0.0,             # OpenRouter free-tier
}


def aggregate_token_usage(
    trace: List[Dict[str, Any]],
    generation_id: str,
    project_id: str,
    mode: str,
) -> TokenUsageSummary:
    """Aggregate token usage from a ModelRouter trace.

    The trace is a list of events recorded by ModelRouter._record_trace().
    Each 'attempt' event with status='success' contains a 'tokens' field.

    Args:
        trace: Raw trace events from ModelRouter.consume_trace()
        generation_id: The generation's unique ID
        project_id: The project/presentation ID
        mode: 'standard' or 'premium'

    Returns:
        TokenUsageSummary with per-model and per-phase breakdowns
    """
    model_map: Dict[str, ModelTokenUsage] = {}
    phase_map: Dict[str, PhaseTokenUsage] = {}

    total_tokens = 0
    total_calls = 0
    total_failed = 0
    total_latency = 0

    for event in trace:
        if event.get("event") != "attempt":
            continue

        model = str(event.get("model", "unknown"))
        provider = str(event.get("provider", "unknown"))
        phase = str(event.get("phase", "unknown"))
        task = str(event.get("task", ""))
        status = event.get("status", "")
        tokens = int(event.get("tokens", 0) or 0)
        latency = int(event.get("latency_ms", 0) or 0)

        # Per-model aggregation
        if model not in model_map:
            model_map[model] = ModelTokenUsage(model=model, provider=provider)
        mu = model_map[model]

        if status == "success":
            mu.total_tokens += tokens
            mu.call_count += 1
            mu.total_latency_ms += latency
            total_tokens += tokens
            total_calls += 1
            total_latency += latency
        elif status == "failed":
            mu.failed_calls += 1
            total_failed += 1

        # Per-phase aggregation
        if phase not in phase_map:
            phase_map[phase] = PhaseTokenUsage(phase=phase, task=task)
        pu = phase_map[phase]
        if status == "success":
            pu.total_tokens += tokens
            pu.call_count += 1
            pu.latency_ms += latency
            if model not in pu.models_used:
                pu.models_used.append(model)

    # Estimate cost
    estimated_cost = 0.0
    for mu in model_map.values():
        from app.services.llm.cost_table import rate_for

        rate = rate_for(mu.model, mu.provider)
        estimated_cost += (mu.total_tokens / 1000.0) * rate

    summary = TokenUsageSummary(
        generation_id=generation_id,
        project_id=project_id,
        mode=mode,
        total_tokens=total_tokens,
        total_calls=total_calls,
        total_failed_calls=total_failed,
        total_latency_ms=total_latency,
        by_model=list(model_map.values()),
        by_phase=list(phase_map.values()),
        estimated_cost_usd=estimated_cost,
    )

    logger.info(
        "token_usage_aggregated",
        generation_id=generation_id,
        project_id=project_id,
        mode=mode,
        total_tokens=total_tokens,
        total_calls=total_calls,
        failed_calls=total_failed,
        estimated_cost=round(estimated_cost, 6),
    )

    return summary
