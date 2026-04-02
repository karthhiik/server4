"""
LLM Model Router — Routes to optimal model per task type.
Every call has a 3-deep fallback chain.
Every call is logged for observability.

Updated 2026-04-02: Only working models (Kimi/GPT-4o-mini/Phoenix/Lucid/GLM removed)
"""

import time
from enum import Enum
from typing import Optional

import structlog

from app.services.llm.base_client import BaseLLMClient, LLMResponse
from app.services.llm.azure_client import (
    AzureDeepSeekClient,
    AzureMistralClient,
)
from app.services.llm.groq_client import GroqRoundRobinClient
from app.services.llm.cloudflare_client import (
    create_cf_qwen_client,
    create_cf_gemma_client,
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


# Routing table: task_type → ordered list of model names to try
# Updated 2026-04-02: Only working models
ROUTING_TABLE: dict[TaskType, list[str]] = {
    TaskType.OUTLINE_PLANNING: ["deepseek-v3", "mistral-medium", "cf-qwen"],
    TaskType.NARRATIVE_STORYTELLING: ["deepseek-v3", "mistral-medium", "cf-qwen"],
    TaskType.STRUCTURED_JSON: ["groq", "deepseek-v3", "cf-qwen"],
    TaskType.TECHNICAL_CODE: ["mistral-medium", "deepseek-v3", "groq"],
    TaskType.TRANSLATION_QUICK_EDIT: ["groq", "cf-qwen", "cf-gemma"],
    TaskType.TEMPLATE_FILL: ["deepseek-v3", "groq", "cf-qwen"],
    TaskType.CONTENT_FIT_RESIZE: ["groq", "cf-qwen", "cf-gemma"],
    TaskType.REFINEMENT: ["deepseek-v3", "groq", "cf-qwen"],
    TaskType.GENERAL: ["deepseek-v3", "groq", "cf-qwen"],
}

# Max retries per model before moving to next in chain
MAX_RETRIES_PER_MODEL = 2


class ModelRouter:
    """
    Singleton model router. Initializes all LLM clients once.
    Routes requests to the optimal model with automatic fallback.
    """

    _instance: Optional["ModelRouter"] = None

    def __init__(self):
        self._clients: dict[str, BaseLLMClient] = {}
        self._init_clients()

    @classmethod
    def get_instance(cls) -> "ModelRouter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_clients(self) -> None:
        # T1: DeepSeek-V3 (Storytelling, narrative)
        self._clients["deepseek-v3"] = AzureDeepSeekClient()
        # T3: Mistral-medium (Technical, code)
        self._clients["mistral-medium"] = AzureMistralClient()
        # T4: Groq round-robin (Fast, structured JSON)
        self._clients["groq"] = GroqRoundRobinClient()
        # T5: Cloudflare Workers (Free fallback)
        self._clients["cf-qwen"] = create_cf_qwen_client()
        self._clients["cf-gemma"] = create_cf_gemma_client()

    def get_client(self, model_name: str) -> BaseLLMClient:
        client = self._clients.get(model_name)
        if not client:
            raise ValueError(f"Unknown model: {model_name}")
        return client

    async def complete(
        self,
        task_type: TaskType,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
        presentation_id: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> LLMResponse:
        """
        Route to optimal model for the given task type.
        Tries each model in the fallback chain with retries.
        Logs every attempt for observability.
        """
        chain = ROUTING_TABLE.get(task_type, ROUTING_TABLE[TaskType.GENERAL])

        last_error: Optional[Exception] = None
        for model_name in chain:
            client = self._clients.get(model_name)
            if not client:
                continue

            # Try this model up to MAX_RETRIES_PER_MODEL times
            for attempt in range(MAX_RETRIES_PER_MODEL):
                start = time.monotonic()
                try:
                    # Increase temperature slightly on retry for variety
                    retry_temp = min(temperature + (attempt * 0.1), 1.0)

                    response = await client.complete(
                        messages=messages,
                        temperature=retry_temp,
                        max_tokens=max_tokens,
                        response_format=response_format,
                    )
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
                    return response

                except Exception as e:
                    elapsed = int((time.monotonic() - start) * 1000)
                    last_error = e
                    logger.warning(
                        "llm_call_failed",
                        task=task_type.value,
                        model=model_name,
                        provider=client.provider,
                        error=str(e),
                        latency_ms=elapsed,
                        presentation_id=presentation_id,
                        phase=phase,
                        attempt=attempt + 1,
                    )
                    # Small delay before retry
                    if attempt < MAX_RETRIES_PER_MODEL - 1:
                        await asyncio.sleep(0.5)
                    continue

            # If we exhausted retries for this model, move to next
            logger.warning(
                "model_exhausted",
                model=model_name,
                task=task_type.value,
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
