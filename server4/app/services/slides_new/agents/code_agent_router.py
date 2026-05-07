"""
Code Agent Router — Multi-provider routing for Phase 3 Code Agent tasks.

Routes different code generation sub-tasks to the optimal model:
  - DSL generation → DeepSeek-V3 (structured JSON output)
  - React compilation → Cloudflare Qwen (fast code gen)
  - Reveal.js HTML → Cloudflare GLM (template fill)
  - Three.js/3D scenes → DeepSeek-V3 (complex code)
  - Skill evaluation → GPT-4o-mini (fast structured)
  - Layout optimization → Phi-4-reasoning (spatial reasoning)
"""

from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

from app.services.llm import ModelRouter, TaskType
from app.services.llm.base_client import LLMResponse
from app.services.slides_new.skills.models import SkillGenerationMode

logger = structlog.get_logger()


class CodeTaskType(str, Enum):
    """Fine-grained task types for the Code Agent's sub-tasks."""

    DSL_GENERATION = "dsl_generation"
    REACT_COMPILATION = "react_compilation"
    REVEALJS_HTML = "revealjs_html"
    THREEJS_SCENE = "threejs_scene"
    SKILL_EVALUATION = "skill_evaluation"
    LAYOUT_OPTIMIZATION = "layout_optimization"
    FALLBACK_TEMPLATE = "fallback_template"


# Maps CodeTaskType → ordered list of models to try
CODE_ROUTING_TABLE: Dict[CodeTaskType, List[str]] = {
    # DSL generation needs strong structured JSON output
    CodeTaskType.DSL_GENERATION: ["deepseek-v3", "gpt-4o-mini", "groq"],
    # React code gen — fast models that write good code
    CodeTaskType.REACT_COMPILATION: ["cf-qwen", "mistral-medium", "deepseek-v3"],
    # reveal.js HTML — template-friendly models
    CodeTaskType.REVEALJS_HTML: ["cf-glm", "cf-qwen", "groq"],
    # Three.js / 3D — needs strong reasoning for spatial code
    CodeTaskType.THREEJS_SCENE: ["deepseek-v3", "mistral-medium", "cf-qwen"],
    # Skill evaluation — fast structured output
    CodeTaskType.SKILL_EVALUATION: ["gpt-4o-mini", "groq", "cf-qwen"],
    # Layout optimization — spatial reasoning
    CodeTaskType.LAYOUT_OPTIMIZATION: ["phi-4-reasoning", "deepseek-v3", "gpt-4o-mini"],
    # Fallback templates — anything fast
    CodeTaskType.FALLBACK_TEMPLATE: ["groq", "cf-qwen", "cf-gemma"],
}

# Maps CodeTaskType → whether to use reasoning mode (thinking models)
THINKING_ROUTES: Dict[CodeTaskType, bool] = {
    CodeTaskType.DSL_GENERATION: False,
    CodeTaskType.REACT_COMPILATION: False,
    CodeTaskType.REVEALJS_HTML: False,
    CodeTaskType.THREEJS_SCENE: True,
    CodeTaskType.SKILL_EVALUATION: False,
    CodeTaskType.LAYOUT_OPTIMIZATION: True,
    CodeTaskType.FALLBACK_TEMPLATE: False,
}


class CodeAgentRouter:
    """
    Multi-provider router for the Code Agent's sub-tasks.

    Uses the global ModelRouter for actual LLM calls,
    but selects models based on the fine-grained CodeTaskType
    rather than the coarse TaskType enum.
    """

    def __init__(self) -> None:
        self._router = ModelRouter.get_instance()

    def _get_chain(
        self,
        task: CodeTaskType,
        mode: SkillGenerationMode = SkillGenerationMode.INSTANT,
    ) -> List[str]:
        """
        Get the model chain for a task, adjusted by generation mode.

        If mode == THINKING, prepend reasoning models to the chain.
        """
        base_chain = list(CODE_ROUTING_TABLE.get(task, CODE_ROUTING_TABLE[CodeTaskType.DSL_GENERATION]))

        if mode == SkillGenerationMode.THINKING or THINKING_ROUTES.get(task, False):
            # Prepend reasoning models for thinking mode
            thinking_models = ["kimi-k2-thinking", "phi-4-reasoning"]
            # Avoid duplicates
            for m in thinking_models:
                if m in base_chain:
                    base_chain.remove(m)
            return thinking_models + base_chain

        return base_chain

    def _task_to_router_type(self, task: CodeTaskType) -> TaskType:
        """Map CodeTaskType to the global TaskType for logging."""
        mapping = {
            CodeTaskType.DSL_GENERATION: TaskType.STRUCTURED_JSON,
            CodeTaskType.REACT_COMPILATION: TaskType.TECHNICAL_CODE,
            CodeTaskType.REVEALJS_HTML: TaskType.TEMPLATE_FILL,
            CodeTaskType.THREEJS_SCENE: TaskType.TECHNICAL_CODE,
            CodeTaskType.SKILL_EVALUATION: TaskType.STRUCTURED_JSON,
            CodeTaskType.LAYOUT_OPTIMIZATION: TaskType.DESIGNER_LAYOUT,
            CodeTaskType.FALLBACK_TEMPLATE: TaskType.TEMPLATE_FILL,
        }
        return mapping.get(task, TaskType.GENERAL)

    async def complete(
        self,
        task: CodeTaskType,
        messages: List[Dict[str, str]],
        mode: SkillGenerationMode = SkillGenerationMode.INSTANT,
        temperature: float = 0.5,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        presentation_id: Optional[str] = None,
    ) -> LLMResponse:
        """
        Route a Code Agent sub-task to the optimal model chain.

        Tries each model in the chain with the global ModelRouter's retry logic.
        """
        chain = self._get_chain(task, mode)
        global_task = self._task_to_router_type(task)

        last_error: Optional[Exception] = None
        for model_name in chain:
            try:
                response = await self._router.complete_with_model(
                    model_name=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )

                if not response.content or not response.content.strip():
                    logger.warning(
                        "code_router_empty",
                        task=task.value,
                        model=model_name,
                    )
                    continue

                logger.info(
                    "code_router_success",
                    task=task.value,
                    model=model_name,
                    mode=mode.value,
                    tokens=response.tokens_used if hasattr(response, "tokens_used") else 0,
                    presentation_id=presentation_id,
                )
                return response

            except Exception as e:
                last_error = e
                logger.warning(
                    "code_router_fallback",
                    task=task.value,
                    model=model_name,
                    error=str(e),
                )
                continue

        raise ConnectionError(
            f"All models failed for code task {task.value}: {last_error}"
        )

    async def generate_dsl(
        self,
        system_prompt: str,
        user_prompt: str,
        mode: SkillGenerationMode = SkillGenerationMode.INSTANT,
        presentation_id: Optional[str] = None,
    ) -> LLMResponse:
        """Convenience: generate DSL output."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return await self.complete(
            task=CodeTaskType.DSL_GENERATION,
            messages=messages,
            mode=mode,
            temperature=0.4,
            max_tokens=4096,
            response_format={"type": "json_object"},
            presentation_id=presentation_id,
        )

    async def generate_react(
        self,
        system_prompt: str,
        user_prompt: str,
        presentation_id: Optional[str] = None,
    ) -> LLMResponse:
        """Convenience: generate React/Tailwind code."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return await self.complete(
            task=CodeTaskType.REACT_COMPILATION,
            messages=messages,
            temperature=0.3,
            max_tokens=6144,
            presentation_id=presentation_id,
        )

    async def evaluate_output(
        self,
        system_prompt: str,
        user_prompt: str,
        presentation_id: Optional[str] = None,
    ) -> LLMResponse:
        """Convenience: run skill evaluation."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return await self.complete(
            task=CodeTaskType.SKILL_EVALUATION,
            messages=messages,
            temperature=0.2,
            max_tokens=2048,
            response_format={"type": "json_object"},
            presentation_id=presentation_id,
        )
