"""
V4 Interactive Endpoints — answer submission and company-icon upload.

Imported into the FastAPI app via the existing `router` (re-exported below
unchanged). Lives in a separate file so it doesn't bloat generation_v4.py.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import structlog
from fastapi import Depends, File, Form, HTTPException, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.database import get_db
from app.dependencies import optional_auth
from app.routers.generation_v4 import router as v4_router
from app.services.v4.interactive_prompt import store_answer

logger = structlog.get_logger()


# ── ANSWER SUBMISSION ─────────────────────────────────────────────


class _AnswerBody(BaseModel):
    question_id: str
    payload: dict[str, Any] | None = None
    skipped: bool = False


@v4_router.post("/generation/{project_id}/answer")
async def submit_generation_answer(
    project_id: str,
    body: _AnswerBody,
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Frontend POSTs the user's answer to a mid-generation `awaiting_input`
    prompt here. The pipeline polls Redis for the answer and resumes."""
    user_id = user["user_id"] if user else "dev-test-user"
    proj = await db.presentations.find_one({"_id": project_id}, {"user_id": 1, "mode": 1})
    if not proj:
        raise HTTPException(status_code=404, detail="project not found")
    if proj.get("user_id") not in (user_id, "dev-test-user") and user_id != "dev-test-user":
        raise HTTPException(status_code=404, detail="project not found")

    payload: dict[str, Any] = dict(body.payload or {})
    if body.skipped:
        payload["skipped"] = True
    ok = await store_answer(project_id, body.question_id, payload)
    if not ok:
        raise HTTPException(status_code=503, detail="answer broker unavailable")
    logger.info("v4_answer_submitted", project_id=project_id, question_id=body.question_id, skipped=body.skipped)
    return {"ok": True, "question_id": body.question_id}


# ── COMPANY ICON UPLOAD (premium only) ────────────────────────────


_ICON_ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
_ICON_MAX_BYTES = 2 * 1024 * 1024
_ICON_DIR = Path("uploads") / "company_icons"


@v4_router.post("/projects/{project_id}/company-icon")
async def upload_company_icon(
    project_id: str,
    file: UploadFile = File(...),
    user: dict | None = Depends(optional_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Upload an optional company icon. Premium-only feature.

    Stored at `uploads/company_icons/{project_id}{ext}` and the URL is recorded
    on the presentation doc as `company_icon_url`. The pipeline reads this
    field at generation time and threads it onto the title and team slides.
    """
    user_id = user["user_id"] if user else "dev-test-user"
    user_role = (user or {}).get("role", "guest")
    is_premium_user = user_role == "premium" or user_id == "dev-test-user"

    proj = await db.presentations.find_one({"_id": project_id}, {"user_id": 1, "mode": 1})
    if not proj:
        raise HTTPException(status_code=404, detail="project not found")
    if proj.get("user_id") not in (user_id, "dev-test-user") and user_id != "dev-test-user":
        raise HTTPException(status_code=404, detail="project not found")
    if proj.get("mode") != "premium":
        raise HTTPException(status_code=403, detail="company icon is a premium-only feature")
    if not is_premium_user:
        raise HTTPException(status_code=403, detail="premium subscription required")

    if not file.filename:
        raise HTTPException(status_code=400, detail="filename required")
    ext = Path(file.filename).suffix.lower()
    if ext not in _ICON_ALLOWED_EXT:
        raise HTTPException(
            status_code=415,
            detail=f"unsupported icon type {ext}; allowed={sorted(_ICON_ALLOWED_EXT)}",
        )
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty file")
    if len(raw) > _ICON_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"icon exceeds {_ICON_MAX_BYTES // (1024*1024)}MB limit",
        )

    _ICON_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(raw).hexdigest()[:12]
    out_path = _ICON_DIR / f"{project_id}-{digest}{ext}"
    out_path.write_bytes(raw)

    icon_url = f"/uploads/company_icons/{out_path.name}"
    await db.presentations.update_one(
        {"_id": project_id},
        {"$set": {
            "company_icon_url": icon_url,
            "company_icon_uploaded_at": datetime.now(timezone.utc),
            "company_icon_bytes": len(raw),
            "updated_at": datetime.now(timezone.utc),
        }},
    )
    return {
        "ok": True,
        "company_icon_url": icon_url,
        "bytes": len(raw),
        "ext": ext,
    }
