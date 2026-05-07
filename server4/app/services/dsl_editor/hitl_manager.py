"""
HITL Manager -- Human-in-the-Loop Checkpoint Gates.

Prevents the pipeline from spending expensive LLM/GPU tokens
rendering slides with the wrong strategic angle.

Gates (from V7 Plan Section 5):
    Gate 1: Narrative Approval     -- CEO output review
    Gate 2: Research/Design Approval -- data + theme review
    Gate 3: Full Render            -- auto-execute (no gate)

Fast Mode: skip all gates for drafts/brainstorming.
"""

import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class HITLGate(str, Enum):
    """The three checkpoint gates in the generation pipeline."""
    NARRATIVE = "narrative"       # Gate 1: archetype + outline review
    RESEARCH_DESIGN = "research_design"  # Gate 2: data + theme review
    FULL_RENDER = "full_render"   # Gate 3: auto (no human gate)


class CheckpointStatus(str, Enum):
    """Lifecycle states of a checkpoint."""
    PENDING = "pending"           # Waiting for user review
    APPROVED = "approved"         # User approved
    REJECTED = "rejected"         # User rejected -- needs revision
    REVISED = "revised"           # Agent revised after rejection
    SKIPPED = "skipped"           # Fast mode -- no review needed
    EXPIRED = "expired"           # Timed out (configurable TTL)


class HITLDecision(str, Enum):
    """User's decision at a checkpoint gate."""
    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"                 # Approve with edits


# ---------------------------------------------------------------------------
# Checkpoint data
# ---------------------------------------------------------------------------

class HITLCheckpoint:
    """
    A single checkpoint in the generation pipeline.

    Stores the agent output waiting for review, user decisions,
    and any edits the user applies before approving.
    """

    def __init__(
        self,
        gate: HITLGate,
        presentation_id: str,
        agent_output: Dict[str, Any],
        auto_approve: bool = False,
    ):
        self.id = f"cp_{uuid.uuid4().hex[:12]}"
        self.gate = gate
        self.presentation_id = presentation_id
        self.agent_output = agent_output
        self.status = CheckpointStatus.SKIPPED if auto_approve else CheckpointStatus.PENDING
        self.decision: Optional[HITLDecision] = None
        self.user_edits: Optional[Dict[str, Any]] = None
        self.user_feedback: Optional[str] = None
        self.created_at = datetime.now(timezone.utc)
        self.decided_at: Optional[datetime] = None
        self.revision_count = 0
        self._revision_history: List[Dict[str, Any]] = []

    @property
    def is_actionable(self) -> bool:
        """Whether this checkpoint needs a user decision."""
        return self.status == CheckpointStatus.PENDING

    @property
    def is_resolved(self) -> bool:
        """Whether this checkpoint has been resolved (approved/skipped/expired)."""
        return self.status in (
            CheckpointStatus.APPROVED,
            CheckpointStatus.SKIPPED,
            CheckpointStatus.EXPIRED,
        )

    @property
    def age_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "gate": self.gate.value,
            "presentation_id": self.presentation_id,
            "status": self.status.value,
            "decision": self.decision.value if self.decision else None,
            "agent_output": self.agent_output,
            "user_edits": self.user_edits,
            "user_feedback": self.user_feedback,
            "created_at": self.created_at.isoformat(),
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "revision_count": self.revision_count,
            "is_actionable": self.is_actionable,
        }


# ---------------------------------------------------------------------------
# HITL Manager
# ---------------------------------------------------------------------------

class HITLManager:
    """
    Manages Human-in-the-Loop checkpoints for the generation pipeline.

    Usage:
        mgr = HITLManager(fast_mode=False)

        # Create Gate 1 checkpoint
        cp = mgr.create_checkpoint(
            gate=HITLGate.NARRATIVE,
            presentation_id="deck_123",
            agent_output={"archetype": "investor-pitch", "outline": [...]},
        )

        # User reviews and approves
        mgr.approve(cp.id)

        # Check if gate is cleared
        if mgr.is_gate_cleared(HITLGate.NARRATIVE, "deck_123"):
            # Proceed to next phase
    """

    # Default TTL for checkpoints (30 min)
    DEFAULT_CHECKPOINT_TTL = 1800

    def __init__(
        self,
        fast_mode: bool = False,
        checkpoint_ttl: int = DEFAULT_CHECKPOINT_TTL,
    ):
        self._fast_mode = fast_mode
        self._ttl = checkpoint_ttl
        self._checkpoints: Dict[str, HITLCheckpoint] = {}
        # Index: (gate, presentation_id) -> checkpoint_id
        self._gate_index: Dict[tuple, str] = {}

    # ── Properties ────────────────────────────────────────────────

    @property
    def fast_mode(self) -> bool:
        return self._fast_mode

    @fast_mode.setter
    def fast_mode(self, value: bool) -> None:
        self._fast_mode = value

    @property
    def checkpoint_count(self) -> int:
        return len(self._checkpoints)

    @property
    def pending_count(self) -> int:
        return sum(
            1 for cp in self._checkpoints.values()
            if cp.status == CheckpointStatus.PENDING
        )

    # ── Core operations ───────────────────────────────────────────

    def create_checkpoint(
        self,
        gate: HITLGate,
        presentation_id: str,
        agent_output: Dict[str, Any],
    ) -> HITLCheckpoint:
        """
        Create a new checkpoint at a pipeline gate.

        Gate 3 (FULL_RENDER) is always auto-approved per the V7 plan.
        In fast_mode, all gates are auto-approved.
        """
        auto_approve = (
            self._fast_mode
            or gate == HITLGate.FULL_RENDER
        )

        cp = HITLCheckpoint(
            gate=gate,
            presentation_id=presentation_id,
            agent_output=agent_output,
            auto_approve=auto_approve,
        )

        # If auto-approved, mark as approved immediately
        if auto_approve:
            cp.status = CheckpointStatus.SKIPPED
            cp.decision = HITLDecision.APPROVE
            cp.decided_at = datetime.now(timezone.utc)

        self._checkpoints[cp.id] = cp
        self._gate_index[(gate.value, presentation_id)] = cp.id

        logger.info(
            "hitl_checkpoint_created",
            checkpoint_id=cp.id,
            gate=gate.value,
            presentation_id=presentation_id,
            auto_approved=auto_approve,
        )

        return cp

    def approve(
        self,
        checkpoint_id: str,
        user_edits: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Approve a checkpoint, optionally with user edits.
        If edits are provided, the decision is EDIT (approve-with-edits).
        """
        cp = self._checkpoints.get(checkpoint_id)
        if cp is None:
            logger.warning("hitl_approve_not_found", checkpoint_id=checkpoint_id)
            return False

        if not cp.is_actionable:
            logger.warning(
                "hitl_approve_not_actionable",
                checkpoint_id=checkpoint_id,
                status=cp.status.value,
            )
            return False

        if user_edits:
            cp.decision = HITLDecision.EDIT
            cp.user_edits = user_edits
        else:
            cp.decision = HITLDecision.APPROVE

        cp.status = CheckpointStatus.APPROVED
        cp.decided_at = datetime.now(timezone.utc)

        logger.info(
            "hitl_checkpoint_approved",
            checkpoint_id=checkpoint_id,
            gate=cp.gate.value,
            has_edits=bool(user_edits),
        )
        return True

    def reject(
        self,
        checkpoint_id: str,
        feedback: str = "",
    ) -> bool:
        """Reject a checkpoint with optional feedback for the agent."""
        cp = self._checkpoints.get(checkpoint_id)
        if cp is None:
            return False

        if not cp.is_actionable:
            return False

        cp.decision = HITLDecision.REJECT
        cp.status = CheckpointStatus.REJECTED
        cp.user_feedback = feedback
        cp.decided_at = datetime.now(timezone.utc)

        logger.info(
            "hitl_checkpoint_rejected",
            checkpoint_id=checkpoint_id,
            gate=cp.gate.value,
            feedback=feedback[:100],
        )
        return True

    def revise(
        self,
        checkpoint_id: str,
        revised_output: Dict[str, Any],
    ) -> bool:
        """
        Submit a revised agent output after rejection.
        The checkpoint resets to PENDING for re-review.
        """
        cp = self._checkpoints.get(checkpoint_id)
        if cp is None:
            return False

        if cp.status != CheckpointStatus.REJECTED:
            return False

        # Store revision history
        cp._revision_history.append({
            "revision": cp.revision_count,
            "output": cp.agent_output,
            "feedback": cp.user_feedback,
        })

        cp.agent_output = revised_output
        cp.status = CheckpointStatus.PENDING
        cp.decision = None
        cp.user_feedback = None
        cp.revision_count += 1

        logger.info(
            "hitl_checkpoint_revised",
            checkpoint_id=checkpoint_id,
            revision=cp.revision_count,
        )
        return True

    def expire_stale(self) -> int:
        """Expire checkpoints that have been pending beyond TTL."""
        expired_count = 0
        for cp in self._checkpoints.values():
            if cp.status == CheckpointStatus.PENDING and cp.age_seconds > self._ttl:
                cp.status = CheckpointStatus.EXPIRED
                expired_count += 1
                logger.info(
                    "hitl_checkpoint_expired",
                    checkpoint_id=cp.id,
                    age_seconds=cp.age_seconds,
                )
        return expired_count

    # ── Query helpers ─────────────────────────────────────────────

    def get_checkpoint(self, checkpoint_id: str) -> Optional[HITLCheckpoint]:
        return self._checkpoints.get(checkpoint_id)

    def is_gate_cleared(self, gate: HITLGate, presentation_id: str) -> bool:
        """Check if a specific gate has been cleared for a presentation."""
        cp_id = self._gate_index.get((gate.value, presentation_id))
        if cp_id is None:
            return False
        cp = self._checkpoints.get(cp_id)
        if cp is None:
            return False
        return cp.is_resolved

    def get_pending_checkpoints(
        self, presentation_id: Optional[str] = None
    ) -> List[HITLCheckpoint]:
        """Get all pending checkpoints, optionally filtered by presentation."""
        result = []
        for cp in self._checkpoints.values():
            if cp.status != CheckpointStatus.PENDING:
                continue
            if presentation_id and cp.presentation_id != presentation_id:
                continue
            result.append(cp)
        return result

    def get_checkpoints_for_presentation(
        self, presentation_id: str
    ) -> List[HITLCheckpoint]:
        """Get all checkpoints for a presentation, ordered by creation time."""
        cps = [
            cp for cp in self._checkpoints.values()
            if cp.presentation_id == presentation_id
        ]
        cps.sort(key=lambda c: c.created_at)
        return cps

    def get_gate_checkpoint(
        self, gate: HITLGate, presentation_id: str
    ) -> Optional[HITLCheckpoint]:
        """Get the current checkpoint for a specific gate and presentation."""
        cp_id = self._gate_index.get((gate.value, presentation_id))
        if cp_id:
            return self._checkpoints.get(cp_id)
        return None

    def get_pipeline_status(self, presentation_id: str) -> Dict[str, Any]:
        """Get the full HITL pipeline status for a presentation."""
        gates = {}
        for gate in HITLGate:
            cp = self.get_gate_checkpoint(gate, presentation_id)
            if cp:
                gates[gate.value] = {
                    "status": cp.status.value,
                    "checkpoint_id": cp.id,
                    "decision": cp.decision.value if cp.decision else None,
                    "revision_count": cp.revision_count,
                }
            else:
                gates[gate.value] = {"status": "not_started"}

        all_cleared = all(
            self.is_gate_cleared(gate, presentation_id)
            for gate in [HITLGate.NARRATIVE, HITLGate.RESEARCH_DESIGN]
        )

        return {
            "presentation_id": presentation_id,
            "fast_mode": self._fast_mode,
            "gates": gates,
            "all_gates_cleared": all_cleared,
            "pending_count": len(self.get_pending_checkpoints(presentation_id)),
        }

    def clear_presentation(self, presentation_id: str) -> int:
        """Remove all checkpoints for a presentation. Returns count removed."""
        to_remove = [
            cp_id for cp_id, cp in self._checkpoints.items()
            if cp.presentation_id == presentation_id
        ]
        for cp_id in to_remove:
            cp = self._checkpoints.pop(cp_id, None)
            if cp:
                key = (cp.gate.value, cp.presentation_id)
                self._gate_index.pop(key, None)
        return len(to_remove)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize all checkpoints for persistence."""
        return {
            "fast_mode": self._fast_mode,
            "checkpoint_ttl": self._ttl,
            "checkpoints": {
                cp_id: cp.to_dict() for cp_id, cp in self._checkpoints.items()
            },
        }
