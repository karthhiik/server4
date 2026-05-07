"""
V4 Content Generation Pipeline — Phase 2.

A new, independent pipeline for slide content generation. Built fresh to avoid
the legacy orchestrator's known issues. Composed of:

- research_collector  : multi-API research with real provider keys from .env
- skeleton_planner    : Skeleton-of-Thought outline generation
- parallel_writer     : per-slide parallel content fan-out
- critic_engine       : rubric-based scoring + targeted re-gen
- learning_store      : retrieval-augmented self-improvement (no recursive training)
- content_pipeline    : the orchestrator that ties it all together

Public entry point: V4ContentPipeline.generate(...)
"""

from app.services.v4.content_pipeline import V4ContentPipeline, PipelineResult, make_redis_progress_emitter
from app.services.v4.research_collector import ResearchCollector, ResearchPacket
from app.services.v4.skeleton_planner import SkeletonPlanner, SlideSkeleton, DeckSkeleton
from app.services.v4.parallel_writer import ParallelWriter, GeneratedSlide
from app.services.v4.critic_engine import CriticEngine, CriticReport, SlideScore
from app.services.v4.learning_store import LearningStore, GenerationOutcome

__all__ = [
    "V4ContentPipeline",
    "PipelineResult",
    "make_redis_progress_emitter",
    "ResearchCollector",
    "ResearchPacket",
    "SkeletonPlanner",
    "SlideSkeleton",
    "DeckSkeleton",
    "ParallelWriter",
    "GeneratedSlide",
    "CriticEngine",
    "CriticReport",
    "SlideScore",
    "LearningStore",
    "GenerationOutcome",
]
