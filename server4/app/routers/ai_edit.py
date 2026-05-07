"""
AI Edit Endpoint — Element-level AI regeneration with model chain
Model Chain (from Problem #2 plan):
  1. Kimi-K2-Thinking (Azure) — PRIMARY
  2. DeepSeek-V3.2 — SECONDARY
  3. Groq Llama3.1-8b — FALLBACK 1 (15s timeout)
  4. Azure GPT-4o-mini — FALLBACK 2
  5. Cloudflare Workers AI — EDGE/FALLBACK 3
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
import structlog
import json

from app.database import get_db
from app.config import settings
from app.services.llm.model_router import TaskType

logger = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["AI Edit"])


class AIEditRequest(BaseModel):
    element_type: str
    current_props: dict[str, Any]
    prompt: str
    provider: Optional[str] = None  # If provided, try this provider first


class AIEditResponse(BaseModel):
    new_props: dict[str, Any]
    provider_used: str


@router.post("/ai-edit", response_model=AIEditResponse)
async def ai_edit_element(request: AIEditRequest, db=Depends(get_db)):
    """
    Regenerate a kit component's props_json using the AI model chain.
    Uses the full model chain with fallback.
    """
    # Build the prompt for the AI
    system_prompt = f"""You are an expert presentation designer and React component pro.
Regenerate the following {request.element_type} component with the user's instructions.

Current props: {json.dumps(request.current_props, indent=2)}

User instruction: {request.prompt}

Return ONLY valid JSON for the new props_json. The JSON must be complete and valid.
Maintain the same structure as the original props, but apply the requested changes.
"""

    # Model chain (from .env lines 51-192)
    model_chain = [
        {
            "name": "kimi",
            "label": "Kimi-K2-Thinking (Azure)",
            "task_type": TaskType.PREMIUM_TARGETED_REWRITE,
        },
        {
            "name": "deepseek",
            "label": "DeepSeek-V3.2",
            "task_type": TaskType.TRANSLATION_QUICK_EDIT,
        },
        {
            "name": "groq",
            "label": "Groq Llama3.1-8b",
            "task_type": TaskType.STRUCTURED_JSON,
        },
        {
            "name": "azure",
            "label": "Azure GPT-4o-mini",
            "task_type": TaskType.STRUCTURED_JSON,
        },
        {
            "name": "cloudflare",
            "label": "Cloudflare Workers AI",
            "task_type": TaskType.GENERAL,
        },
    ]

    # If user specified a provider, try it first
    if request.provider:
        model_chain = [m for m in model_chain if m["name"] == request.provider] + \
                     [m for m in model_chain if m["name"] != request.provider]

    last_error = None
    for model in model_chain:
        try:
            logger.info("AI Edit: trying provider", provider=model["name"], element_type=request.element_type)
            
            # Call the model router
            from app.services.llm.model_router import model_router
            
            response = await model_router.route(
                task_type=model["task_type"],
                prompt=system_prompt,
                max_tokens=2048,
            )

            if not response or not response.content:
                logger.warning("Empty response from provider", provider=model["name"])
                continue

            # Parse the response as JSON
            try:
                new_props = json.loads(response.content)
                if not isinstance(new_props, dict):
                    raise ValueError("Response is not a dict")
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Invalid JSON from provider", provider=model["name"], error=str(e))
                last_error = e
                continue

            logger.info("AI Edit: success", provider=model["name"])
            return AIEditResponse(new_props=new_props, provider_used=model["label"])

        except Exception as e:
            logger.warning("Provider failed", provider=model["name"], error=str(e))
            last_error = e
            continue

    # All providers failed
    logger.error("All AI providers failed for element edit")
    raise HTTPException(
        status_code=500,
        detail=f"All AI providers failed. Last error: {str(last_error) if last_error else 'Unknown'}"
    )
