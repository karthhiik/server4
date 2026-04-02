"""
Crash-proof generation state machine.
State persisted to MongoDB — survives server restart.
"""

from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.presentation import GenerationState
from app.services.orchestrator.progress_tracker import ProgressTracker

import structlog

logger = structlog.get_logger()


class GenerationStateMachine:
    """
    Tracks generation progress and persists state to MongoDB.
    If the server crashes mid-generation, the state can be resumed.
    """

    def __init__(
        self,
        project_id: str,
        db: AsyncIOMotorDatabase,
        progress_tracker: Optional[ProgressTracker] = None,
    ):
        self.project_id = project_id
        self.db = db
        self.progress_tracker = progress_tracker
        self.current_state = GenerationState.IDLE
        self._last_model: Optional[str] = None
        self._last_provider: Optional[str] = None

    async def transition_to(
        self,
        new_state: GenerationState,
        progress: int = 0,
        message: str = "",
    ) -> None:
        self.current_state = new_state

        # Persist to MongoDB (crash-proof)
        await self.db.presentations.update_one(
            {"_id": self.project_id},
            {"$set": {
                "generation_state": new_state.value,
                "generation_progress": progress,
                "generation_message": message,
                "updated_at": datetime.utcnow(),
            }},
        )

        # Stream to frontend via WebSocket
        if self.progress_tracker:
            await self.progress_tracker.send_progress(
                self.project_id,
                state=new_state.value,
                progress=progress,
                message=message,
            )

        logger.info(
            "state_transition",
            project_id=self.project_id,
            state=new_state.value,
            progress=progress,
            message=message,
        )

    async def handle_failure(self, error: str, phase: str) -> None:
        await self.transition_to(GenerationState.FAILED, message=error)

        # Log for observability
        await self.db.generation_logs.insert_one({
            "presentation_id": self.project_id,
            "phase": phase,
            "error": error,
            "model_used": self._last_model,
            "provider": self._last_provider,
            "success": False,
            "created_at": datetime.utcnow(),
        })

    async def log_call(
        self,
        phase: str,
        model: str,
        provider: str,
        latency_ms: int,
        tokens_used: int,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Log every LLM/API call for observability."""
        self._last_model = model
        self._last_provider = provider

        await self.db.generation_logs.insert_one({
            "presentation_id": self.project_id,
            "phase": phase,
            "model": model,
            "provider": provider,
            "latency_ms": latency_ms,
            "tokens_used": tokens_used,
            "success": success,
            "error": error,
            "created_at": datetime.utcnow(),
        })

    async def can_resume(self) -> bool:
        """Check if an interrupted generation can be resumed."""
        doc = await self.db.presentations.find_one({"_id": self.project_id})
        if not doc:
            return False
        state = doc.get("generation_state")
        return state not in [
            GenerationState.COMPLETED.value,
            GenerationState.IDLE.value,
            GenerationState.READY_FOR_EDITING.value,
        ]

    async def get_resume_state(self) -> Optional[GenerationState]:
        """Get the state to resume from."""
        doc = await self.db.presentations.find_one({"_id": self.project_id})
        if not doc:
            return None
        state_val = doc.get("generation_state")
        try:
            return GenerationState(state_val)
        except ValueError:
            return None
