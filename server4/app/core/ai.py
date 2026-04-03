"""AI Model Factory providing access to different LLM tiers.

Supports multiple providers: Azure OpenAI, DeepSeek, Groq, Mistral, etc.
"""

import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class AIModel:
    """Base AI model interface."""

    async def complete(self, prompt: str, **kwargs) -> str:
        """Generate completion for prompt.

        Args:
            prompt: The prompt text
            **kwargs: Additional model parameters

        Returns:
            Model completion text
        """
        raise NotImplementedError


class UtilityModel(AIModel):
    """Fast, cheap utility model for quick tasks (NER, extraction)."""

    async def complete(self, prompt: str, **kwargs) -> str:
        """Generate completion using utility model.

        Args:
            prompt: The prompt text
            **kwargs: Additional model parameters

        Returns:
            Model completion text
        """
        # For now, return a mock response
        # In production, call actual API (GPT-4o-mini, Groq, etc.)
        logger.info(f"Utility model called with prompt: {prompt[:50]}...")
        return '[]'  # Return empty JSON by default


class StorytellingModel(AIModel):
    """Creative storytelling model (DeepSeek)."""

    async def complete(self, prompt: str, **kwargs) -> str:
        """Generate completion using storytelling model.

        Args:
            prompt: The prompt text
            **kwargs: Additional model parameters

        Returns:
            Model completion text
        """
        logger.info(f"Storytelling model called")
        return "Generated narrative..."


class ReasoningModel(AIModel):
    """Deep reasoning model (Kimi K2, Phi-4-reasoning)."""

    async def complete(self, prompt: str, **kwargs) -> str:
        """Generate completion using reasoning model.

        Args:
            prompt: The prompt text
            **kwargs: Additional model parameters

        Returns:
            Model completion text
        """
        logger.info(f"Reasoning model called")
        return "Reasoned output..."


class AIFactory:
    """Factory for accessing different AI models by tier."""

    def __init__(self):
        """Initialize AI factory with model instances."""
        self.models = {
            'utility': UtilityModel(),
            'storytelling': StorytellingModel(),
            'reasoning': ReasoningModel(),
        }

    def get_model(self, tier: str = 'utility') -> AIModel:
        """Get AI model by tier.

        Args:
            tier: Model tier ('utility', 'storytelling', 'reasoning')

        Returns:
            AI model instance

        Raises:
            ValueError: If tier is invalid
        """
        if tier not in self.models:
            raise ValueError(f"Invalid tier: {tier}. Valid: {list(self.models.keys())}")
        return self.models[tier]


# Global AI factory instance
ai_factory = AIFactory()
