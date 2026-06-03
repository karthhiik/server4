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


class ExportContentEmpty(V4PipelineError, ValueError):
    """Raised by export builders when the input slides list is empty.

    Slice 4 (Export Parity): export builders must refuse to emit a corrupt
    artifact (e.g. a 0-slide ``.pptx`` that crashes PowerPoint). Routers
    catch this and translate it into a structured 409 error envelope with
    code ``no_slides_yet`` (v4-direct routes) or ``deck_not_compiled``
    (legacy job route).

    Multi-inherits from ``ValueError`` for backwards compatibility with
    existing callers that catch ``ValueError`` from the public builders.
    """

    def __init__(self, message: str = "no_slides") -> None:
        super().__init__(message)
