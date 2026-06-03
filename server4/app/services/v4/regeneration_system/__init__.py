"""
Re-Generation System
Auto re-generation (same content, different slides) and prompt-based re-generation
"""

from .auto_regenerator import AutoRegenerator
from .prompt_regenerator import PromptRegenerator

__all__ = [
    "AutoRegenerator",
    "PromptRegenerator",
]
