"""Session persistence for real-time collaboration.

This module manages user sessions and persistence for the V4 generation pipeline,
enabling real-time question-asking flows and session state management across WebSocket connections.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class SessionManager:
    """Manages user sessions and persistence for real-time collaboration.

    Handles session state, conversation history, generation progress, and user preferences
    with Redis-backed persistence for reliability across WebSocket disconnections.
    """

    def __init__(self) -> None:
        """Initialize the session manager."""
        self._redis_prefix = "v4:session:"

    async def save_session(
        self,
        user_id: str,
        generation_id: str,
        session_data: Dict[str, Any],
    ) -> None:
        """Save session state to Redis.

        Args:
            user_id: Authenticated user ID
            generation_id: Unique generation identifier
            session_data: Session state including conversation history, progress, preferences
        """
        try:
            from app.utils.rate_limiter import get_redis
            r = await get_redis()
            if r is None:
                logger.warning("redis_not_available_for_session_save")
                return

            session_key = f"{self._redis_prefix}{user_id}:{generation_id}"
            session_payload = {
                "user_id": user_id,
                "generation_id": generation_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": session_data,
            }

            await r.setex(
                session_key,
                7200,  # 2 hour TTL
                json.dumps(session_payload, default=str),
            )

            logger.info(
                "session_saved",
                user_id=user_id,
                generation_id=generation_id,
                keys=list(session_data.keys()),
            )

        except Exception as e:
            logger.error(
                "session_save_failed",
                user_id=user_id,
                generation_id=generation_id,
                error=str(e)[:200],
                exc_info=True,
            )

    async def load_session(
        self,
        user_id: str,
        generation_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load session state from Redis.

        Args:
            user_id: Authenticated user ID
            generation_id: Unique generation identifier

        Returns:
            Session data if exists, None otherwise
        """
        try:
            from app.utils.rate_limiter import get_redis
            r = await get_redis()
            if r is None:
                logger.warning("redis_not_available_for_session_load")
                return None

            session_key = f"{self._redis_prefix}{user_id}:{generation_id}"
            session_json = await r.get(session_key)

            if not session_json:
                logger.info(
                    "session_not_found",
                    user_id=user_id,
                    generation_id=generation_id,
                )
                return None

            session_payload = json.loads(session_json)
            session_data = session_payload.get("data", {})

            logger.info(
                "session_loaded",
                user_id=user_id,
                generation_id=generation_id,
                keys=list(session_data.keys()),
            )

            return session_data

        except Exception as e:
            logger.error(
                "session_load_failed",
                user_id=user_id,
                generation_id=generation_id,
                error=str(e)[:200],
                exc_info=True,
            )
            return None

    async def update_session_field(
        self,
        user_id: str,
        generation_id: str,
        field: str,
        value: Any,
    ) -> None:
        """Update a specific field in the session.

        Args:
            user_id: Authenticated user ID
            generation_id: Unique generation identifier
            field: Field name to update
            value: New value for the field
        """
        try:
            session_data = await self.load_session(user_id, generation_id)
            if session_data is None:
                session_data = {}

            session_data[field] = value
            await self.save_session(user_id, generation_id, session_data)

            logger.info(
                "session_field_updated",
                user_id=user_id,
                generation_id=generation_id,
                field=field,
            )

        except Exception as e:
            logger.error(
                "session_field_update_failed",
                user_id=user_id,
                generation_id=generation_id,
                field=field,
                error=str(e)[:200],
                exc_info=True,
            )

    async def delete_session(
        self,
        user_id: str,
        generation_id: str,
    ) -> None:
        """Delete a session from Redis.

        Args:
            user_id: Authenticated user ID
            generation_id: Unique generation identifier
        """
        try:
            from app.utils.rate_limiter import get_redis
            r = await get_redis()
            if r is None:
                return

            session_key = f"{self._redis_prefix}{user_id}:{generation_id}"
            await r.delete(session_key)

            logger.info(
                "session_deleted",
                user_id=user_id,
                generation_id=generation_id,
            )

        except Exception as e:
            logger.error(
                "session_delete_failed",
                user_id=user_id,
                generation_id=generation_id,
                error=str(e)[:200],
                exc_info=True,
            )

    async def get_conversation_history(
        self,
        user_id: str,
        generation_id: str,
    ) -> list[Dict[str, Any]]:
        """Get conversation history from session.

        Args:
            user_id: Authenticated user ID
            generation_id: Unique generation identifier

        Returns:
            List of conversation messages (question-answer pairs)
        """
        session_data = await self.load_session(user_id, generation_id)
        if session_data is None:
            return []

        return session_data.get("conversation_history", [])

    async def append_conversation_message(
        self,
        user_id: str,
        generation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append a message to the conversation history.

        Args:
            user_id: Authenticated user ID
            generation_id: Unique generation identifier
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional metadata for the message
        """
        session_data = await self.load_session(user_id, generation_id)
        if session_data is None:
            session_data = {}

        conversation_history = session_data.get("conversation_history", [])
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }

        conversation_history.append(message)
        session_data["conversation_history"] = conversation_history

        await self.save_session(user_id, generation_id, session_data)

        logger.info(
            "conversation_message_appended",
            user_id=user_id,
            generation_id=generation_id,
            role=role,
            total_messages=len(conversation_history),
        )

    async def get_generation_progress(
        self,
        user_id: str,
        generation_id: str,
    ) -> Dict[str, Any]:
        """Get generation progress from session.

        Args:
            user_id: Authenticated user ID
            generation_id: Unique generation identifier

        Returns:
            Generation progress data
        """
        session_data = await self.load_session(user_id, generation_id)
        if session_data is None:
            return {}

        return session_data.get("generation_progress", {})

    async def update_generation_progress(
        self,
        user_id: str,
        generation_id: str,
        stage: str,
        progress_data: Dict[str, Any],
    ) -> None:
        """Update generation progress.

        Args:
            user_id: Authenticated user ID
            generation_id: Unique generation identifier
            stage: Current generation stage
            progress_data: Progress data for the stage
        """
        session_data = await self.load_session(user_id, generation_id)
        if session_data is None:
            session_data = {}

        generation_progress = session_data.get("generation_progress", {})
        generation_progress[stage] = {
            "status": "in_progress",
            "data": progress_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        session_data["generation_progress"] = generation_progress
        await self.save_session(user_id, generation_id, session_data)

        logger.info(
            "generation_progress_updated",
            user_id=user_id,
            generation_id=generation_id,
            stage=stage,
        )


__all__ = ["SessionManager"]
