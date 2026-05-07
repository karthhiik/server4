"""
V4 Consensus Engine — package entry point.

Multi-model consensus generation for slide content. Reduces single-model
failure modes (hallucination, off-palette content, thin narrative) by
running 2-4 diverse drafters, a debate round, an aggregator, and parallel
graders. Backed by asyncio.wait_for budgets so a stuck provider cannot
stall the real-time pipeline.

Public API:
    run_consensus(router, *, mode, system, user_msg, project_id, phase) -> ConsensusResult

Modes:
    "standard" → writer+critic loop (2 rounds, 15s budget)
    "premium"  → persona panel → debate → aggregator → graders (25s budget)
"""

from app.services.v4.consensus.panel import (
    ConsensusResult,
    run_consensus,
)

__all__ = ["ConsensusResult", "run_consensus"]
