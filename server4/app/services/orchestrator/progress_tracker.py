"""
WebSocket progress streaming — real-time updates to frontend.
"""

import asyncio
import json
from typing import Optional

from fastapi import WebSocket

import structlog

logger = structlog.get_logger()


class ProgressTracker:
    """
    Manages WebSocket connections for real-time progress streaming.
    One connection per generation task (project_id).
    """

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, project_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if project_id not in self._connections:
            self._connections[project_id] = []
        self._connections[project_id].append(websocket)
        logger.info("ws_connected", project_id=project_id)

    async def disconnect(self, project_id: str, websocket: WebSocket) -> None:
        if project_id in self._connections:
            self._connections[project_id] = [
                ws for ws in self._connections[project_id] if ws != websocket
            ]
            if not self._connections[project_id]:
                del self._connections[project_id]
        logger.info("ws_disconnected", project_id=project_id)

    async def send_progress(
        self,
        project_id: str,
        state: str,
        progress: int,
        message: str,
        extra: Optional[dict] = None,
    ) -> None:
        """Broadcast progress to all connected clients for this project."""
        if project_id not in self._connections:
            return

        payload = {
            "type": "progress",
            "state": state,
            "progress": progress,
            "message": message,
        }
        if extra:
            payload.update(extra)

        data = json.dumps(payload)
        dead = []
        for ws in self._connections[project_id]:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)

        # Clean up dead connections
        for ws in dead:
            await self.disconnect(project_id, ws)

    async def send_slide_image_ready(
        self, project_id: str, slide_id: str, image_url: str, slide_index: int
    ) -> None:
        """Push an updated slide image URL to connected clients."""
        if project_id not in self._connections:
            return

        payload = {
            "type": "slide_image_ready",
            "slide_id": slide_id,
            "image_url": image_url,
            "slide_index": slide_index,
        }

        data = json.dumps(payload)
        dead = []
        for ws in self._connections[project_id]:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)

        for ws in dead:
            await self.disconnect(project_id, ws)

    async def send_complete(self, project_id: str, result: dict) -> None:
        """Send completion event with final data."""
        await self.send_progress(
            project_id,
            state="completed",
            progress=100,
            message="Presentation ready!",
            extra={"result": result},
        )

    async def send_error(self, project_id: str, error: str) -> None:
        """Send error event."""
        await self.send_progress(
            project_id,
            state="failed",
            progress=0,
            message=error,
        )


# Singleton instance
progress_tracker = ProgressTracker()
