"""WebSocket endpoint for real-time generation progress."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.orchestrator.progress_tracker import progress_tracker

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/generation/{project_id}")
async def generation_progress_ws(websocket: WebSocket, project_id: str):
    """
    WebSocket for tracking generation progress.
    Frontend connects here after POST /api/generate/ai or /api/generate/template.

    Events sent:
    - {"type": "progress", "state": "researching", "progress": 25, "message": "..."}
    - {"type": "progress", "state": "completed", "progress": 100, "message": "Ready!"}
    - {"type": "progress", "state": "failed", "progress": 0, "message": "Error: ..."}
    """
    await progress_tracker.connect(project_id, websocket)
    try:
        while True:
            # Keep connection alive, listen for client pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type": "pong"}')
    except WebSocketDisconnect:
        await progress_tracker.disconnect(project_id, websocket)
