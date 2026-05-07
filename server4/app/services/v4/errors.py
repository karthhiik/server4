"""
V4 Pipeline Exceptions — explicit failure modes the orchestrator can react to.

The pipeline must NEVER silently return an empty deck. EmptyDeckError forces
the caller to either fall back to a canonical scaffold or surface a real
user-facing error.
"""

from __future__ import annotations


class V4PipelineError(Exception):
    """Base for all V4 pipeline failures."""


class EmptyDeckError(V4PipelineError):
    """Raised when a generation stage produced zero usable slides.

    Most often happens when the planner LLM returns valid JSON but under a
    non-`slides` top-level key (Kimi did this on PRM-2 of the deep test).
    """


class ResearchExhaustedError(V4PipelineError):
    """Raised when every external research provider failed AND the local
    Chroma cache returned no relevant cached citations.
    """


class WriterTimeoutError(V4PipelineError):
    """Raised when a slide writer exceeded its per-slide timeout even after
    hedged fallback to a secondary model.
    """


class CriticRejectedError(V4PipelineError):
    """Raised when a slide failed the critic on every retry attempt."""
