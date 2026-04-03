"""
Orchestrator Module
"""

from app.services.slides_new.orchestrator.orchestrator import (
    SlideGenerationOrchestrator,
)
from app.services.slides_new.orchestrator.pipeline import PipelineOrchestrator

__all__ = ["SlideGenerationOrchestrator", "PipelineOrchestrator"]
