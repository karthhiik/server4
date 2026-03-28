import logging
import mimetypes

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from fastapi.responses import RedirectResponse
from app.core.security import get_current_user
from app.services.permissions import check_upload_permissions
from app.services.azure_upload import azure_manager
from app.services.upload_security import (
    ChatUploadIntent,
    validate_chat_upload_request,
    validate_completed_chat_upload,
)
from app.db.mongo import db
from datetime import datetime
import uuid
from urllib.parse import urlparse, unquote
from shared_security.upload_security import UploadSecurityError

router = APIRouter()
logger = logging.getLogger(__name__)


def _extract_blob_name(file_url: str) -> str:
    parsed = urlparse((file_url or "").strip())
    path = unquote(parsed.path)
    container = azure_manager.container_name
    expected_prefix = f"/{container}/"
    if not path.startswith(expected_prefix):
        raise UploadSecurityError("Invalid file URL.")
    blob_name = path[len(expected_prefix):].strip()
    if not blob_name:
        raise UploadSecurityError("Invalid file URL.")
    return blob_name


def _normalize_declared_content_type(intent: ChatUploadIntent) -> str:
    if intent.declared_mime_type:
        return intent.declared_mime_type
    guessed, _ = mimetypes.guess_type(intent.safe_filename)
    return guessed or "application/octet-stream"

@router.get("/download")
async def download_file(
    file_url: str = Query(..., description="The full Azure Blob URL"),
    filename: str = Query(None, description="Filename for Content-Disposition"),
    user_id: str = Depends(get_current_user)
):
    """
    Generate a SAS token for downloading a file and redirect to it.
    """
    try:
        blob_name = _extract_blob_name(file_url)
    except UploadSecurityError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc

    session = await db.db.upload_sessions.find_one(
        {
            "$or": [
                {"file_url": file_url},
                {"blob_name": blob_name},
            ],
            "status": "completed",
        }
    )
    if not session:
        raise HTTPException(status_code=404, detail="File not found")

    if user_id not in {session.get("user_id"), session.get("recipient_id")}:
        logger.warning(
            "Denied chat download for user=%s blob=%s owner=%s recipient=%s",
            user_id,
            blob_name,
            session.get("user_id"),
            session.get("recipient_id"),
        )
        raise HTTPException(status_code=404, detail="File not found")

    try:
        sas_url = azure_manager.generate_read_sas(
            session["blob_name"],
            filename=filename or session.get("filename"),
        )
        return RedirectResponse(url=sas_url, status_code=307)
    except Exception as e:
        logger.error("Download Error for blob %s: %s", blob_name, e)
        raise HTTPException(status_code=500, detail="Failed to generate download link")

@router.post("/init")
async def init_upload(
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user)
):
    """
    Initialize an upload session.
    Payload: { filename, file_size, content_type, recipient_id, message_type }
    """
    filename = payload.get("filename")
    file_size = payload.get("file_size")
    content_type = payload.get("content_type")
    recipient_id = payload.get("recipient_id")

    if not all([filename, file_size, content_type, recipient_id]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    try:
        intent = validate_chat_upload_request(
            filename=filename,
            file_size=file_size,
            declared_mime_type=content_type,
        )
    except UploadSecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # 1. Check Permissions
    allowed, reason = await check_upload_permissions(
        user_id,
        recipient_id,
        intent.size_bytes,
        intent.declared_mime_type or _normalize_declared_content_type(intent),
    )
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    # 2. Generate Blob Path
    # Structure: chat/{date}/{uuid}.ext
    ext = intent.extension
    date_folder = datetime.now().strftime("%Y/%m/%d")
    upload_id = str(uuid.uuid4())
    blob_name = f"chat/{date_folder}/{upload_id}{ext}"

    # 3. Generate SAS URL
    try:
        sas_url = azure_manager.generate_upload_sas(blob_name)
    except Exception as e:
        # print(f"Azure Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate upload token")

    # 4. Save Session to DB
    from datetime import timedelta
    session = {
        "_id": upload_id,
        "user_id": user_id,
        "recipient_id": recipient_id,
        "filename": intent.safe_filename,
        "original_filename": filename,
        "file_size": intent.size_bytes,
        "content_type": _normalize_declared_content_type(intent),
        "message_type": "image" if intent.kind == "image" else ("audio" if intent.kind == "audio" else "file"),
        "upload_kind": intent.kind,
        "blob_name": blob_name,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=10) # Auto-delete policy
    }
    await db.db.upload_sessions.insert_one(session)

    return {
        "upload_id": upload_id,
        "sas_url": sas_url,
        "blob_name": blob_name
    }

@router.post("/finalize")
async def finalize_upload(
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user)
):
    """
    Finalize the upload by committing blocks.
    Payload: { upload_id, block_ids: [] }
    """
    upload_id = payload.get("upload_id")
    block_ids = payload.get("block_ids", [])

    if not upload_id or not block_ids:
        raise HTTPException(status_code=400, detail="Missing upload_id or block_ids")

    # 1. Get Session
    session = await db.db.upload_sessions.find_one({"_id": upload_id, "user_id": user_id})
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")

    if session["status"] == "completed":
         return {"status": "already_completed", "file_url": session.get("file_url")}

    # 2. Commit Blocks to Azure
    try:
        file_url = await azure_manager.commit_block_list(
            session["blob_name"], 
            block_ids, 
            session["content_type"]
        )

        blob_props = azure_manager.get_blob_properties(session["blob_name"])
        actual_size = int(getattr(blob_props, "size", 0) or 0)
        if actual_size != int(session["file_size"]):
            raise UploadSecurityError("Uploaded file size does not match the approved session.")

        blob_payload = azure_manager.download_blob_bytes(session["blob_name"])
        if len(blob_payload) != actual_size:
            raise UploadSecurityError("Uploaded file could not be verified.")

        validated = validate_completed_chat_upload(
            filename=session["filename"],
            payload=blob_payload,
            kind=session.get("upload_kind", "file"),
            declared_mime_type=session.get("content_type"),
        )
    except Exception as e:
        try:
            azure_manager.delete_blob(session["blob_name"])
        except Exception as cleanup_error:
            logger.error("Failed to cleanup invalid blob %s: %s", session["blob_name"], cleanup_error)

        rejection_reason = str(e)
        await db.db.upload_sessions.update_one(
            {"_id": upload_id},
            {
                "$set": {
                    "status": "rejected",
                    "rejected_at": datetime.utcnow(),
                    "rejection_reason": rejection_reason[:300],
                }
            },
        )
        if isinstance(e, UploadSecurityError):
            raise HTTPException(status_code=400, detail=str(e)) from e
        logger.error("Azure Commit Error for upload %s: %s", upload_id, e)
        raise HTTPException(status_code=500, detail="Failed to finalize file")

    # 3. Update Session
    await db.db.upload_sessions.update_one(
        {"_id": upload_id},
        {
            "$set": {
                "status": "completed",
                "file_url": file_url,
                "completed_at": datetime.utcnow(),
                "content_type": validated.detected_mime,
                "sha256": validated.sha256,
            }
        }
    )

    # 4. Return Final URL (Frontend will then send the WebSocket message)
    # Why? Because we want the Frontend to control the "Send" action to sync with Optimistic UI.
    # The Backend *could* send it, but letting the frontend do it keeps the flow consistent with text messages.
    
    return {
        "status": "completed",
        "file_url": file_url,
        "filename": session["filename"],
        "size": session["file_size"],
        "content_type": validated.detected_mime
    }
