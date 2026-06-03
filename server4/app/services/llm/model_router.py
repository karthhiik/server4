"""
LLM Model Router — Routes to optimal model per task type.
Every call has a 3-deep fallback chain.
Every call is logged for observability.

Updated 2026-04-03: All tested working models included
"""

import asyncio
import time
from enum import Enum
from typing import Any, Optional

import structlog

from app.services.llm.base_client import BaseLLMClient, LLMResponse
from app.services.llm.azure_client import (
    AzureDeepSeekClient,
    AzureMistralClient,
    AzureGPT4oMiniClient,
    AzureGPTOssClient,
    AzureKimiClient,
    AzureKimi26Client,
    AzurePhi4Client,
)
from app.config import settings
from app.services.llm.groq_client import GroqRoundRobinClient, ProviderPoolExhaustedError
from app.services.llm.cloudflare_client import (
    create_cf_qwen_client,
    create_cf_gemma_client,
    create_cf_glm_client,
)
from app.services.llm.openrouter_client import (
    OpenRouterClient,
    OpenRouterGLM45Client,
    OpenRouterGemmaClient,
    OpenRouterNvidiaClient,
    OpenRouterMiniMaxClient,
)
from app.services.llm.nvidia_client import all_nvidia_clients, NVIDIA_MODEL_REGISTRY
from app.services.llm import token_bucket
from app.services.llm.error_classifier import (
    ErrorClass,
    classify as classify_error,
    parse_retry_after,
    SKIP_DURATIONS,
    is_retryable_same_model,
    should_skip_model,
)

logger = structlog.get_logger()


class TaskType(str, Enum):
    """Task types that determine model routing."""

    OUTLINE_PLANNING = "outline_planning"
    NARRATIVE_STORYTELLING = "narrative_storytelling"
    STRUCTURED_JSON = "structured_json"
    TECHNICAL_CODE = "technical_code"
    TRANSLATION_QUICK_EDIT = "translation_quick_edit"
    TEMPLATE_FILL = "template_fill"
    CONTENT_FIT_RESIZE = "content_fit_resize"
    REFINEMENT = "refinement"
    GENERAL = "general"
    DESIGNER_LAYOUT = "designer_layout"
    # V2 Content Generation task types
    DEEP_RESEARCH_PLAN = "deep_research_plan"
    FACT_SYNTHESIS_JSON = "fact_synthesis_json"
    PITCH_DEBATE = "pitch_debate"
    DUAL_MODE_REWRITE = "dual_mode_rewrite"
    STYLE_ADAPTATION = "style_adaptation"
    CITATION_GUARD = "citation_guard"
    EVIDENCE_EXTRACTION = "evidence_extraction"
    QUERY_REWRITE = "query_rewrite"
    CROSS_VALIDATION = "cross_validation"
    SPEAKER_NOTES = "speaker_notes"
    IMAGE_PROMPT = "image_prompt"
    INTENT_CLASSIFICATION = "intent_classification"
    ENTITY_EXTRACTION = "entity_extraction"
    COMMUNITY_SUMMARY = "community_summary"
    # Phase 3: Code Agent task types
    DSL_GENERATION = "dsl_generation"
    REACT_COMPILATION = "react_compilation"
    REVEALJS_HTML = "revealjs_html"
    THREEJS_SCENE = "threejs_scene"
    SKILL_EVALUATION = "skill_evaluation"
    LAYOUT_OPTIMIZATION = "layout_optimization"
    # Founder replan — narrowly used premium-only tasks that prefer Kimi 2.6.
    PREMIUM_THESIS_PLANNING = "premium_thesis_planning"
    PREMIUM_TARGETED_REWRITE = "premium_targeted_rewrite"


# Routing table: task_type → ordered list of model names to try
# ──────────────────────────────────────────────────────────────────────
# Plan-v4 (2026-04-21): family-tiered routing.
#
# Each task now maps to a composed list built from *family tiers*. The
# families group models by capability, not by provider. Groq is no longer
# first on narrative / template tasks — it produced generic "Transforming
# industries" slop. It stays on fast-JSON and weak-classify tasks where
# its 8s attempt budget fits.
#
# Every chain ends with "openrouter" (qwen3.6-plus:free) as the universal
# safety-net tail: one free-tier model that is never removed, so no chain
# can ever fully exhaust.
# ──────────────────────────────────────────────────────────────────────

# ─── Family tiers ─────────────────────────────────────────────────────
# Updated 2026-05-17: All available free-tier models included.
# Premium mode gets reasoning-heavy chains; standard mode gets fast chains.
_MAIN_REASONING = [
    "kimi-k2-thinking", "kimi-2.6", "deepseek-v3", "gpt-oss-120b",
    "nv-glm-5.1", "nv-glm-4.7", "phi-4-reasoning",
    "nv-devstral-2-123b", "openrouter-nvidia",
]
_MAIN_NARRATIVE = [
    "deepseek-v3", "kimi-k2-thinking", "kimi-2.6",
    "nv-glm-4.7", "nv-minimax-m2.7", "gpt-oss-120b",
    "nv-gemma-4-31b", "openrouter-minimax",
]
_MAIN_DESIGN = [
    "kimi-2.6", "kimi-k2-thinking", "deepseek-v3", "nv-glm-4.7", "cf-glm", "cf-gemma",
    "nv-gemma-4-31b", "openrouter-gemma",
]
_EDITOR_FILL = [
    "gpt-4o-mini", "deepseek-v3", "cf-qwen", "cf-gemma",
    "nv-step-3.5-flash", "nv-glm-4.7", "groq", "kimi-k2-thinking",
    "openrouter-glm45",
]
_EDITOR_REFINE = [
    "gpt-4o-mini", "deepseek-v3", "kimi-k2-thinking", "nv-glm-4.7",
    "cf-qwen", "cf-gemma", "nv-step-3.5-flash", "phi-4-reasoning",
    "openrouter-glm45",
]
_CODING = [
    "nv-devstral-2-123b", "deepseek-v3", "cf-qwen",
    "gpt-oss-120b", "openrouter-nvidia",
]
_FAST_JSON = [
    "nv-step-3.5-flash", "cf-qwen", "groq",
    "gpt-4o-mini", "openrouter-glm45",
]
_WEAK_CLASSIFY = [
    "groq", "nv-step-3.5-flash", "cf-qwen",
    "openrouter-glm45",
]

# Legacy aliases preserved for any external code still importing them.
_NV_NARRATIVE = ["nv-glm-5.1", "nv-glm-4.7", "nv-minimax-m2.7"]
_NV_FAST_JSON = ["nv-step-3.5-flash", "nv-glm-4.7"]
_NV_TECHNICAL = ["nv-devstral-2-123b", "nv-glm-4.7"]
_NV_GENERAL   = ["nv-glm-4.7", "nv-gemma-4-31b", "nv-step-3.5-flash"]


def _with_openrouter_tail(chain: list[str]) -> list[str]:
    """Ensure every chain ends with the universal OpenRouter safety net.
    Dedupe-preserving (keeps first occurrence)."""
    seen: set[str] = set()
    out: list[str] = []
    for m in chain:
        if m not in seen:
            out.append(m)
            seen.add(m)
    if "openrouter" not in seen:
        out.append("openrouter")
    return out


# ── Empirically-dead model exclusion list ────────────────────────────
# Verified failures from a live smoke test (`_llm_smoke.py`) against the
# user-supplied keys in server4/.env. These models were registered in the
# router but did not return usable content:
#
#   nv-glm-5.1            → 403 Forbidden (auth failure on user's key)
#   nv-glm-4.7            → 410 Gone (model retired by NVIDIA on 2026-05-14)
#   nv-devstral-2-123b    → 404 Not Found (model removed from NVIDIA inventory)
#   openrouter (qwen3.6+) → 404 "free model has been deprecated"
#
# Filtering at chain-build time removes ~3-6 wasted attempts per writer call,
# which previously caused every writer in standard mode to time out before
# reaching a working provider. The chain still walks the same length — dead
# entries just never enter it.
#
# This list MUST stay narrow. A model that occasionally rate-limits or
# returns empty does NOT belong here — those failures are handled by the
# token-bucket and the chain walk. Only put a model here when it returns a
# permanent error (404/410 for the model, or 403 for the key) on every call.
_DEAD_MODELS: frozenset[str] = frozenset({
    "nv-glm-5.1",
    "nv-glm-4.7",
    "nv-devstral-2-123b",
    "openrouter",  # the legacy free-tier qwen3.6 endpoint, now deprecated
})


def _filter_dead(chain: list[str]) -> list[str]:
    """Strip empirically-dead models without altering chain length contracts.

    Used at lookup time inside ``_chain_for`` so dead entries can be removed
    from a single source of truth (``_DEAD_MODELS``) without touching each
    chain definition. The filter is intentionally idempotent and preserves
    the relative order of remaining entries.
    """
    return [m for m in chain if m not in _DEAD_MODELS]


# Plan 02 (Slide Count Bug v2) — the *absolute* final safety tail for the
# OUTLINE_PLANNING chain. Advanced reasoning models lead (kimi, deepseek,
# gpt-oss, glm, phi, mistral, openrouter). Azure GPT-4o-mini from
# AZURE_GPT4O_MINI_* env vars is appended last because:
#   1. It is the only Azure OpenAI deployment guaranteed to honor strict
#      json_schema response_format (per OpenAI Structured Outputs spec).
#   2. Reaching this tier means seven advanced models could not satisfy
#      the structured contract — we want the strongest available
#      structural guarantee at that point.
# Callers can opt in to strict-schema mode by checking
# ``is_final_safety_tail(model_id)`` from ``skeleton_planner``.
_FINAL_SAFETY_TAIL_MODEL: str = "gpt-4o-mini"


def _with_safety_tail(chain: list[str]) -> list[str]:
    """Wrap ``_with_openrouter_tail`` and append the GPT-4o-mini final tail.

    Used only on planning chains where structural correctness (e.g. exact
    slide count) is contractual. Does not mutate the input list.
    """
    base = _with_openrouter_tail(chain)
    if _FINAL_SAFETY_TAIL_MODEL not in base:
        base = base + [_FINAL_SAFETY_TAIL_MODEL]
    return base


def is_final_safety_tail(model_id: str) -> bool:
    """Public predicate — True iff ``model_id`` is the deepest fallback in
    a structural-contract chain (currently only the Azure GPT-4o-mini
    deployment from ``AZURE_GPT4O_MINI_*`` env vars).

    Consumers (e.g. ``skeleton_planner._safety_tail_replan``) use this to
    decide whether to upgrade ``response_format`` from ``json_object`` to
    ``json_schema`` strict mode.
    """
    return (model_id or "").strip() == _FINAL_SAFETY_TAIL_MODEL


ROUTING_TABLE: dict[TaskType, list[str]] = {
    # Planner / reasoning
    # Plan 02 v2: OUTLINE_PLANNING ends with the GPT-4o-mini safety tail
    # so the slide-count contract has a strict-json-schema-capable model
    # to fall through to.
    TaskType.OUTLINE_PLANNING:       _with_safety_tail(["gpt-4o-mini", "groq", "cf-qwen", "nv-step-3.5-flash", "cf-gemma", "nv-gemma-4-31b", "cf-glm", "nv-glm-4.7"]),
    TaskType.DEEP_RESEARCH_PLAN:     _with_openrouter_tail(_MAIN_REASONING),
    # Narrative / storytelling / debate
    TaskType.NARRATIVE_STORYTELLING: _with_openrouter_tail(_MAIN_NARRATIVE),
    TaskType.PITCH_DEBATE:           _with_openrouter_tail(_MAIN_NARRATIVE),
    TaskType.DUAL_MODE_REWRITE:      _with_openrouter_tail(_MAIN_NARRATIVE),
    TaskType.COMMUNITY_SUMMARY:      _with_openrouter_tail(_MAIN_NARRATIVE),
    TaskType.STYLE_ADAPTATION:       _with_openrouter_tail(_EDITOR_REFINE),
    # Design / layout
    TaskType.DESIGNER_LAYOUT:        _with_openrouter_tail(_MAIN_DESIGN),
    TaskType.LAYOUT_OPTIMIZATION:    _with_openrouter_tail(_MAIN_DESIGN),
    # Editor fill / template fill
    TaskType.TEMPLATE_FILL:          _with_openrouter_tail(_EDITOR_FILL),
    TaskType.CONTENT_FIT_RESIZE:     _with_openrouter_tail(_EDITOR_FILL),
    TaskType.TRANSLATION_QUICK_EDIT: _with_openrouter_tail(_EDITOR_FILL),
    TaskType.GENERAL:                _with_openrouter_tail(_EDITOR_FILL + ["deepseek-v3"]),
    # Editor refine / critic / grader
    TaskType.REFINEMENT:             _with_openrouter_tail(_EDITOR_REFINE),
    TaskType.CITATION_GUARD:         _with_openrouter_tail(_EDITOR_REFINE),
    TaskType.EVIDENCE_EXTRACTION:    _with_openrouter_tail(_EDITOR_REFINE),
    TaskType.CROSS_VALIDATION:       _with_openrouter_tail(_EDITOR_REFINE),
    TaskType.SPEAKER_NOTES:          _with_openrouter_tail(_EDITOR_REFINE),
    TaskType.IMAGE_PROMPT:           _with_openrouter_tail(_EDITOR_FILL),
    # Coding
    TaskType.TECHNICAL_CODE:         _with_openrouter_tail(_CODING),
    TaskType.DSL_GENERATION:         _with_openrouter_tail(_CODING),
    TaskType.REACT_COMPILATION:      _with_openrouter_tail(["cf-qwen"] + _CODING),
    TaskType.REVEALJS_HTML:          _with_openrouter_tail(["cf-glm", "cf-qwen"] + _CODING),
    TaskType.THREEJS_SCENE:          _with_openrouter_tail(_CODING),
    # Fast structured JSON / weak classification
    TaskType.STRUCTURED_JSON:        _with_openrouter_tail(_FAST_JSON),
    TaskType.FACT_SYNTHESIS_JSON:    _with_openrouter_tail(_FAST_JSON),
    TaskType.QUERY_REWRITE:          _with_openrouter_tail(_FAST_JSON),
    TaskType.INTENT_CLASSIFICATION:  _with_openrouter_tail(_WEAK_CLASSIFY),
    TaskType.ENTITY_EXTRACTION:      _with_openrouter_tail(_WEAK_CLASSIFY),
    TaskType.SKILL_EVALUATION:       _with_openrouter_tail(_EDITOR_REFINE),
    # Founder replan — premium-only Kimi 2.6 tasks. Kimi 2.6 sits at the
    # head of the chain; router-level budget (can_call_kimi26) decides
    # whether to actually use it before each call.
    TaskType.PREMIUM_THESIS_PLANNING:
        _with_safety_tail(["kimi-2.6"] + _MAIN_REASONING),
    TaskType.PREMIUM_TARGETED_REWRITE:
        _with_openrouter_tail(["kimi-2.6", "kimi-k2-thinking", "deepseek-v3", "gpt-oss-120b"]),
}

# Plan 05 — standard mode is the real-time tier. It must not inherit the
# premium reasoning/narrative chain by accident. These overrides use only
# already-configured model IDs from this file, preserving premium/default
# behavior while giving V4 callers an explicit fast path via
# ``complete(..., mode="standard")``.
#
# Plan 06 (Standard Mode Rebuild) — Groq is now the PRIMARY model for
# standard mode. With 8 API keys (free tier, round-robin) and 330+ tok/s,
# Groq delivers <10s pitch deck content generation. GPT-4o-mini (Azure)
# and free CF/NV models serve as fallbacks for rate-limit bursts.
STANDARD_MODE_ROUTING_TABLE: dict[TaskType, list[str]] = {
    # Standard mode chains, reordered 2026-05-25 to lead with verified-working
    # providers. Live smoke test against the user-supplied keys showed
    # gpt-4o-mini (Azure), deepseek-v3 (Azure), groq, cf-qwen, cf-glm, cf-gemma,
    # openrouter-nvidia respond reliably; the rest of the original chain entries
    # either return empty content, time out, or are filtered by ``_DEAD_MODELS``.
    # Dead entries are still listed for audit clarity but skipped at lookup time.
    TaskType.INTENT_CLASSIFICATION:
        _with_openrouter_tail(["groq", "gpt-4o-mini", "cf-qwen", "cf-gemma", "cf-glm", "deepseek-v3", "nv-step-3.5-flash", "nv-gemma-4-31b", "openrouter-glm45"]),
    TaskType.ENTITY_EXTRACTION:
        _with_openrouter_tail(["groq", "gpt-4o-mini", "cf-qwen", "cf-gemma", "cf-glm", "deepseek-v3", "nv-step-3.5-flash", "nv-gemma-4-31b", "openrouter-glm45"]),
    TaskType.OUTLINE_PLANNING:
        _with_openrouter_tail(["gpt-4o-mini", "deepseek-v3", "groq", "cf-glm", "cf-qwen", "cf-gemma", "nv-gemma-4-31b", "nv-step-3.5-flash", "openrouter-glm45"]),
    TaskType.NARRATIVE_STORYTELLING:
        _with_openrouter_tail(["gpt-4o-mini", "deepseek-v3", "cf-qwen", "cf-glm", "cf-gemma", "groq", "openrouter-nvidia", "nv-gemma-4-31b", "openrouter-gemma", "openrouter-glm45"]),
    TaskType.TEMPLATE_FILL:
        _with_openrouter_tail(["gpt-4o-mini", "deepseek-v3", "cf-qwen", "cf-glm", "cf-gemma", "groq", "nv-gemma-4-31b", "nv-step-3.5-flash", "openrouter-glm45"]),
    TaskType.STRUCTURED_JSON:
        _with_openrouter_tail(["gpt-4o-mini", "groq", "cf-qwen", "cf-gemma", "cf-glm", "nv-step-3.5-flash", "nv-gemma-4-31b", "openrouter-glm45"]),
    TaskType.REFINEMENT:
        _with_openrouter_tail(["gpt-4o-mini", "deepseek-v3", "groq", "cf-glm", "cf-qwen", "cf-gemma", "nv-gemma-4-31b", "nv-step-3.5-flash", "openrouter-glm45"]),
}

# Max retries per model before moving to next in chain
MAX_RETRIES_PER_MODEL = 2
V4_MAX_RETRIES_PER_MODEL = 1

# ─── Per-task default wall-clock budget ───────────────────────────────
# Used by safe_complete callers as the outer cap. One stuck chain cannot
# eat the entire pipeline.
V4_TASK_WALL_CLOCK_BUDGET: dict[TaskType, float] = {
    TaskType.NARRATIVE_STORYTELLING: 45.0,
    TaskType.TEMPLATE_FILL:          25.0,
    TaskType.OUTLINE_PLANNING:       60.0,
    TaskType.REFINEMENT:             20.0,
    TaskType.DESIGNER_LAYOUT:        35.0,
    TaskType.LAYOUT_OPTIMIZATION:    25.0,
    TaskType.TECHNICAL_CODE:         40.0,
    TaskType.STRUCTURED_JSON:        15.0,
    TaskType.INTENT_CLASSIFICATION:  10.0,
}

# V4 is a real-time pipeline. Bound each provider attempt so the router can
# move across the fallback chain before the outer safe_complete timeout fires.
V4_TASK_ATTEMPT_TIMEOUTS: dict[TaskType, float] = {
    TaskType.OUTLINE_PLANNING: 14.0,
    TaskType.NARRATIVE_STORYTELLING: 18.0,
    TaskType.TEMPLATE_FILL: 12.0,
    TaskType.INTENT_CLASSIFICATION: 8.0,
    TaskType.REFINEMENT: 15.0,
}

# Plan-v4 timeouts — reflect real cold-start vs steady-state behavior seen
# in telemetry. Kimi dropped 40→25 so the chain stays walkable. NVIDIA
# models bumped 8→12 to survive NIM cold boots. step-3.5-flash tightened
# 8→6 because it IS flash.
V4_MODEL_ATTEMPT_TIMEOUTS: dict[str, float] = {
    # Groq: avg 2-4s per call, 15s allows for cold starts and retries
    "groq":               15.0,
    "openrouter":        15.0,   # qwen3.6 free can be slow first hit
    "openrouter-glm45":  12.0,   # GLM 4.5 Air — fast structured JSON
    "openrouter-gemma":  12.0,   # Gemma-4-31b — narrative content
    "openrouter-nvidia": 15.0,   # Nemotron — reasoning
    "openrouter-minimax": 14.0,  # MiniMax M2.5 — long-form
    "gpt-4o-mini":       12.0,
    "gpt-oss-120b":      18.0,
    "deepseek-v3":       14.0,
    "mistral-medium":    15.0,
    "phi-4-reasoning":   20.0,
    "kimi-k2-thinking":  25.0,   # down from 40 - keep chain walkable
    "kimi-2.6":          25.0,   # same budget as 2.0 - bounded + narrow use
    "cf-qwen":            8.0,
    "cf-gemma":           8.0,
    "cf-glm":            10.0,
    "nv-glm-5.1":        12.0,   # up from 8 - cold-start reality
    "nv-glm-4.7":        12.0,
    "nv-minimax-m2.7":   14.0,   # long-context model, needs more
    "nv-devstral-2-123b": 14.0,
    "nv-gemma-4-31b":    10.0,
    "nv-step-3.5-flash":  6.0,   # it IS flash — tighten
}


class ModelRouter:
    """
    Singleton model router. Initializes all LLM clients once.
    Routes requests to the optimal model with automatic fallback.
    """

    _instance: Optional["ModelRouter"] = None

    def __init__(self):
        self._clients: dict[str, BaseLLMClient] = {}
        self._request_traces: dict[str, list[dict[str, object]]] = {}
        # Founder replan — per-project Kimi 2.6 call counter. Narrow-use
        # budget: premium decks get KIMI26_PREMIUM_MAX_CALLS, standard decks
        # get KIMI26_STANDARD_MAX_CALLS. Once exhausted, the router silently
        # skips "kimi-2.6" in the chain and falls through to Kimi 2.0.
        self._kimi26_calls: dict[str, int] = {}
        # Forced-model override. When set, every `complete()` call ignores the
        # routing chain and uses this single model directly. Used by the
        # tests/v4_forced_model_capture.py harness to lock the entire pipeline
        # onto one model (e.g. "gpt-oss-120b") for evaluation.
        self._forced_model: Optional[str] = None
        self._init_clients()

    def set_forced_model(self, model_name: Optional[str]) -> None:
        """Force every subsequent complete() call to use `model_name` (no fallback).
        Pass None to clear."""
        if model_name is not None and model_name not in self._clients:
            raise ValueError(f"Unknown model for forced override: {model_name}")
        self._forced_model = model_name

    @property
    def forced_model(self) -> Optional[str]:
        return self._forced_model

    @classmethod
    def get_instance(cls) -> "ModelRouter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Kimi 2.6 narrow-use budget ──────────────────────────────
    def _kimi26_budget_for(self, phase: Optional[str]) -> int:
        """Premium phases use the larger budget; everything else uses the
        standard budget. We infer mode from the phase name convention used
        across v4 (`v4_..._prem_...` or `v4_..._premium`)."""
        p = (phase or "").lower()
        if "prem" in p or "premium" in p:
            return int(settings.KIMI26_PREMIUM_MAX_CALLS)
        return int(settings.KIMI26_STANDARD_MAX_CALLS)

    def can_call_kimi26(self, presentation_id: Optional[str], phase: Optional[str]) -> bool:
        """Return True if the per-project Kimi 2.6 budget is not exhausted.
        Called by `complete()` before attempting the kimi-2.6 client."""
        if not settings.ENABLE_KIMI26:
            return False
        if not presentation_id:
            # Ad-hoc calls (no project context) always share the same budget
            # key to prevent runaway cost from unrelated code paths.
            presentation_id = "__global__"
        used = self._kimi26_calls.get(presentation_id, 0)
        return used < self._kimi26_budget_for(phase)

    def _consume_kimi26_budget(self, presentation_id: Optional[str]) -> None:
        key = presentation_id or "__global__"
        self._kimi26_calls[key] = self._kimi26_calls.get(key, 0) + 1

    def reset_kimi26_budget(self, presentation_id: Optional[str]) -> None:
        """Called at the END of generate() to free memory across projects."""
        if presentation_id and presentation_id in self._kimi26_calls:
            self._kimi26_calls.pop(presentation_id, None)

    def _init_clients(self) -> None:
        # T0: Kimi-K2-Thinking (Planning/Reasoning)
        self._clients["kimi-k2-thinking"] = AzureKimiClient()
        # T0+: Kimi-K2.6 (premium-only narrow-use)
        self._clients["kimi-2.6"] = AzureKimi26Client()
        # T0.5: Phi-4-reasoning (Reasoning)
        self._clients["phi-4-reasoning"] = AzurePhi4Client()
        # T1: DeepSeek-V3 (Storytelling, narrative)
        self._clients["deepseek-v3"] = AzureDeepSeekClient()
        # T2: GPT-4o-mini (Fast structured JSON)
        self._clients["gpt-4o-mini"] = AzureGPT4oMiniClient()
        # T2.5: gpt-oss-120b (open-weights 120B workhorse)
        self._clients["gpt-oss-120b"] = AzureGPTOssClient()
        # T3: Mistral-medium (Technical, code)
        self._clients["mistral-medium"] = AzureMistralClient()
        # T4: Groq round-robin (Fast, structured JSON)
        self._clients["groq"] = GroqRoundRobinClient()
        # T5: Cloudflare Workers (Free fallback)
        self._clients["cf-qwen"] = create_cf_qwen_client()
        self._clients["cf-gemma"] = create_cf_gemma_client()
        self._clients["cf-glm"] = create_cf_glm_client()
        # T7: OpenRouter (Free tier — multi-model)
        self._clients["openrouter"] = OpenRouterClient()
        self._clients["openrouter-glm45"] = OpenRouterGLM45Client()
        self._clients["openrouter-gemma"] = OpenRouterGemmaClient()
        self._clients["openrouter-nvidia"] = OpenRouterNvidiaClient()
        self._clients["openrouter-minimax"] = OpenRouterMiniMaxClient()
        # T8: NVIDIA NIM (free serverless tier — 6 models, OpenAI-compatible)
        for nv_name, nv_client in all_nvidia_clients().items():
            self._clients[nv_name] = nv_client
            if not nv_client.is_configured:
                logger.warning("nvidia_model_unconfigured",
                    model=nv_name, env_key=NVIDIA_MODEL_REGISTRY[nv_name][1])

    def get_client(self, model_name: str) -> BaseLLMClient:
        client = self._clients.get(model_name)
        if not client:
            raise ValueError(f"Unknown model: {model_name}")
        return client

    def start_trace(self, presentation_id: Optional[str]) -> None:
        if presentation_id:
            self._request_traces[presentation_id] = []

    def consume_trace(self, presentation_id: Optional[str]) -> list[dict[str, object]]:
        if not presentation_id:
            return []
        return list(self._request_traces.pop(presentation_id, []))

    def _record_trace(self, presentation_id: Optional[str], **event: object) -> None:
        if not presentation_id:
            return
        trace = self._request_traces.setdefault(presentation_id, [])
        trace.append({
            "ts_ms": int(time.time() * 1000),
            **event,
        })

    @staticmethod
    def summarize_trace(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
        phases: dict[str, dict[str, Any]] = {}
        for event in trace:
            phase = str(event.get("phase") or "")
            phase_entry = phases.setdefault(
                phase,
                {
                    "phase": phase,
                    "task": event.get("task"),
                    "response_format_type": event.get("response_format_type"),
                    "attempts": [],
                },
            )
            if event.get("event") != "attempt":
                continue

            phase_entry["attempts"].append(
                {
                    "status": event.get("status"),
                    "attempt": event.get("attempt"),
                    "model": event.get("model"),
                    "provider": event.get("provider"),
                    "latency_ms": event.get("latency_ms"),
                    "attempt_timeout_s": event.get("attempt_timeout_s"),
                    "retryable": event.get("retryable"),
                    "error": event.get("error"),
                    "tokens": event.get("tokens"),
                }
            )

        return list(phases.values())

    @staticmethod
    def _is_v4_phase(phase: Optional[str]) -> bool:
        return bool(phase and phase.startswith("v4_"))

    @classmethod
    def _max_retries_for_phase(cls, phase: Optional[str]) -> int:
        return V4_MAX_RETRIES_PER_MODEL if cls._is_v4_phase(phase) else MAX_RETRIES_PER_MODEL

    @classmethod
    def _attempt_timeout_for(
        cls,
        task_type: TaskType,
        model_name: str,
        phase: Optional[str],
    ) -> Optional[float]:
        if not cls._is_v4_phase(phase):
            return None
        return V4_MODEL_ATTEMPT_TIMEOUTS.get(model_name, V4_TASK_ATTEMPT_TIMEOUTS.get(task_type))

    @classmethod
    def _chain_for(cls, task_type: TaskType, mode: Optional[str] = None) -> list[str]:
        if (mode or "").strip().lower() == "standard":
            chain = STANDARD_MODE_ROUTING_TABLE.get(
                task_type,
                ROUTING_TABLE.get(task_type, ROUTING_TABLE[TaskType.GENERAL]),
            )
        else:
            chain = ROUTING_TABLE.get(task_type, ROUTING_TABLE[TaskType.GENERAL])
        # Filter empirically-dead models so the writer/critic don't burn
        # their per-attempt timeout on providers known to return permanent
        # errors. See ``_DEAD_MODELS`` for the audit trail.
        return _filter_dead(chain)

    def get_models_for_purpose(self, purpose: str, task_type: Optional[TaskType] = None) -> list[str]:
        """Get prioritized models for specific presentation purpose.

        Args:
            purpose: Presentation purpose (e.g., "deep_tech", "vc_pitch", "series_a")
            task_type: Optional task type to further refine model selection

        Returns:
            Ordered list of model IDs to try for this purpose
        """
        # Purpose-specific model mapping
        # Deep technical purposes prefer reasoning models
        deep_tech_purposes = {
            "deep_tech",
            "trust_compliance",
            "technical_deep",
        }
        # Financial/metric-heavy purposes prefer structured JSON models
        financial_purposes = {
            "series_a",
            "growth_deck",
            "financial_projection",
            "executive_brief",
        }
        # Narrative/storytelling purposes prefer narrative models
        narrative_purposes = {
            "vc_pitch",
            "seed_round",
            "pre_seed_pitch",
            "cinematic_keynote",
            "product_launch",
            "demo_day",
            "partnership",
            "customer_case",
            "team_deck",
            "advisory_board",
            "strategic_partnership",
        }
        # Market/competitive purposes prefer reasoning + narrative blend
        market_purposes = {
            "market_analysis",
            "competitive_analysis",
            "fundraising_roadshow",
            "expansion_plan",
        }

        # Default to standard routing table
        if task_type:
            return self._chain_for(task_type, mode="standard")

        # Purpose-based fallback
        if purpose in deep_tech_purposes:
            # Prefer reasoning models: kimi-k2-thinking, deepseek-v3, phi-4-reasoning
            return _with_openrouter_tail(["kimi-k2-thinking", "deepseek-v3", "phi-4-reasoning", "mistral-medium"])
        elif purpose in financial_purposes:
            # Prefer structured JSON models: gpt-4o-mini, groq, cf-qwen
            return _with_openrouter_tail(["gpt-4o-mini", "groq", "cf-qwen", "nv-step-3.5-flash"])
        elif purpose in narrative_purposes:
            # Prefer narrative models: deepseek-v3, kimi-k2-thinking, mistral-medium
            return _with_openrouter_tail(["deepseek-v3", "kimi-k2-thinking", "mistral-medium", "nv-glm-4.7"])
        elif purpose in market_purposes:
            # Blend of reasoning and narrative
            return _with_openrouter_tail(["kimi-k2-thinking", "deepseek-v3", "nv-glm-4.7", "mistral-medium"])
        else:
            # Default to standard mode routing
            return _with_openrouter_tail(["groq", "cf-qwen", "nv-step-3.5-flash", "gpt-4o-mini"])

    @staticmethod
    def _is_non_retryable_error(error: Exception) -> bool:
        return isinstance(error, ProviderPoolExhaustedError)

    @staticmethod
    async def _handle_error_class(
        *,
        model_name: str,
        error: Exception,
        err_class: ErrorClass,
    ) -> None:
        """Apply the dispatch matrix defined in error_classifier.SKIP_DURATIONS.

        RATE_LIMIT  → Redis token-bucket skip (Retry-After or default)
        QUOTA_DAILY → skip until 00:00 UTC
        AUTH        → mark dead for process lifetime
        others      → no-op (retry/move-on handled by caller)
        """
        if err_class == ErrorClass.RATE_LIMIT:
            cooldown = parse_retry_after(error) or SKIP_DURATIONS[ErrorClass.RATE_LIMIT]
            await token_bucket.mark_rate_limited(model_name, cooldown)
        elif err_class == ErrorClass.QUOTA_DAILY:
            await token_bucket.mark_quota_exhausted(model_name)
        elif err_class == ErrorClass.AUTH:
            token_bucket.mark_dead_local(model_name)

    async def complete(
        self,
        task_type: TaskType,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
        presentation_id: Optional[str] = None,
        phase: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> LLMResponse:
        """
        Route to optimal model for the given task type.
        Tries each model in the fallback chain with retries.
        Logs every attempt for observability.

        Plan-v4 additions:
          - Pre-call skip via token_bucket.can_call (drops known-exhausted models)
          - Per-error-class dispatch: AUTH/RATE_LIMIT/QUOTA update bucket state
          - Same-model retry only on TRANSIENT/UNKNOWN (per is_retryable_same_model)
        """
        chain = self._chain_for(task_type, mode)
        # Forced-model override: lock the chain to a single model so the entire
        # pipeline can be evaluated against one provider (capture harness).
        if self._forced_model:
            chain = [self._forced_model]
        max_retries = self._max_retries_for_phase(phase)

        last_error: Optional[Exception] = None
        for model_name in chain:
            client = self._clients.get(model_name)
            if not client:
                continue

            # Founder replan — enforce Kimi 2.6 per-project budget. Once the
            # project has spent its KIMI26_*_MAX_CALLS allotment, we silently
            # skip to the next model in the chain (Kimi 2.0 / DeepSeek / ...).
            if model_name == "kimi-2.6":
                if not self.can_call_kimi26(presentation_id, phase):
                    self._record_trace(
                        presentation_id,
                        event="attempt",
                        status="skipped",
                        task=task_type.value,
                        model=model_name,
                        provider=client.provider,
                        phase=phase or "",
                        attempt=0,
                        error="kimi26_budget_exhausted",
                    )
                    continue
                # Reserve a slot up front so concurrent calls don't oversubscribe.
                self._consume_kimi26_budget(presentation_id)

            # Pre-call skip: known rate-limited / quota-exhausted / dead models.
            # Forced-model override bypasses the bucket (tests/capture harness).
            if not self._forced_model and not await token_bucket.can_call(model_name):
                logger.debug("llm_call_skipped_bucket_exhausted",
                             model=model_name, task=task_type.value, phase=phase)
                self._record_trace(
                    presentation_id,
                    event="attempt",
                    status="skipped",
                    task=task_type.value,
                    model=model_name,
                    provider=client.provider,
                    phase=phase or "",
                    attempt=0,
                    error="bucket_exhausted",
                )
                continue

            attempt_timeout_s = self._attempt_timeout_for(task_type, model_name, phase)

            # Try this model up to max_retries times.
            for attempt in range(max_retries):
                start = time.monotonic()
                try:
                    # Increase temperature slightly on retry for variety
                    retry_temp = min(temperature + (attempt * 0.1), 1.0)

                    call = client.complete(
                        messages=messages,
                        temperature=retry_temp,
                        max_tokens=max_tokens,
                        response_format=response_format,
                    )
                    if attempt_timeout_s:
                        response = await asyncio.wait_for(call, timeout=attempt_timeout_s)
                    else:
                        response = await call
                    elapsed = int((time.monotonic() - start) * 1000)

                    # Validate response has content
                    if not response.content or not response.content.strip():
                        raise ValueError("Empty response content")

                    logger.info(
                        "llm_call_success",
                        task=task_type.value,
                        model=model_name,
                        provider=client.provider,
                        latency_ms=elapsed,
                        tokens=response.tokens_used,
                        presentation_id=presentation_id,
                        phase=phase,
                        attempt=attempt + 1,
                    )
                    self._record_trace(
                        presentation_id,
                        event="attempt",
                        status="success",
                        task=task_type.value,
                        model=model_name,
                        provider=client.provider,
                        phase=phase or "",
                        attempt=attempt + 1,
                        latency_ms=elapsed,
                        attempt_timeout_s=attempt_timeout_s,
                        response_format_type=(response_format or {}).get("type"),
                        tokens=response.tokens_used,
                    )
                    # Clear any lingering skip marker on success.
                    try:
                        await token_bucket.mark_healthy(model_name)
                    except Exception:  # noqa: BLE001
                        pass
                    return response

                except Exception as e:
                    elapsed = int((time.monotonic() - start) * 1000)
                    last_error = e
                    non_retryable = self._is_non_retryable_error(e)
                    # Plan-v4: classify error, update buckets, decide retry.
                    try:
                        err_class = classify_error(e)
                    except Exception:  # noqa: BLE001
                        err_class = ErrorClass.UNKNOWN
                    try:
                        await self._handle_error_class(
                            model_name=model_name, error=e, err_class=err_class,
                        )
                    except Exception:  # noqa: BLE001
                        pass

                    logger.warning(
                        "llm_call_failed",
                        task=task_type.value,
                        model=model_name,
                        provider=client.provider,
                        error=str(e)[:300],
                        error_class=err_class.value,
                        latency_ms=elapsed,
                        presentation_id=presentation_id,
                        phase=phase,
                        attempt=attempt + 1,
                        attempt_timeout_s=attempt_timeout_s,
                        retryable=not non_retryable,
                    )
                    self._record_trace(
                        presentation_id,
                        event="attempt",
                        status="failed",
                        task=task_type.value,
                        model=model_name,
                        provider=client.provider,
                        phase=phase or "",
                        attempt=attempt + 1,
                        latency_ms=elapsed,
                        attempt_timeout_s=attempt_timeout_s,
                        response_format_type=(response_format or {}).get("type"),
                        error=str(e)[:300],
                        error_class=err_class.value,
                        retryable=not non_retryable,
                    )
                    if non_retryable:
                        break
                    # Plan-v4: AUTH/RATE_LIMIT/QUOTA → skip this model entirely
                    # (already marked in bucket above). TRANSIENT/UNKNOWN → one
                    # more attempt on same model. Others → advance chain.
                    if should_skip_model(err_class):
                        break
                    if not is_retryable_same_model(err_class):
                        break
                    # Small delay before retry
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)
                    continue

            # If we exhausted retries for this model, move to next
            logger.warning(
                "model_exhausted",
                model=model_name,
                task=task_type.value,
                phase=phase,
            )
            self._record_trace(
                presentation_id,
                event="model_exhausted",
                task=task_type.value,
                model=model_name,
                provider=client.provider,
                phase=phase or "",
                response_format_type=(response_format or {}).get("type"),
            )

        raise ConnectionError(
            f"All models failed for task {task_type.value}: {last_error}"
        )

    async def complete_with_model(
        self,
        model_name: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> LLMResponse:
        """Direct call to a specific model (no routing)."""
        client = self.get_client(model_name)
        return await client.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )


def get_model_router() -> ModelRouter:
    """Convenience accessor for the singleton ModelRouter."""
    return ModelRouter.get_instance()
