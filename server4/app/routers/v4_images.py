"""
V4 slide image static-serving route.

Founder Plan-v5 (Apr 2026): every generated slide image is persisted to
the local store (`app/services/storage/local_image_store.py`) and served
from this route. Same-origin to the API, no SAS expiry, no Azure CORS
quirks. Cache-Control is `immutable` because filenames are stable per
(project_id, slide_id) and overwriting is intentional — clients should
re-fetch on a fresh URL only when the writer regenerates the slide
(which produces a new slide_id segment in `compiled_slides[i]`).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from app.services.storage.local_image_store import resolve_path

router = APIRouter(prefix="/api/v4/images", tags=["v4-images"])


@router.get("/{project_id}/{filename}")
async def get_slide_image(project_id: str, filename: str) -> Response:
    path = resolve_path(project_id, filename)
    if path is None:
        raise HTTPException(status_code=404, detail="image_not_found")
    return FileResponse(
        path=str(path),
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=31536000",
            "Access-Control-Allow-Origin": "*",
        },
    )
