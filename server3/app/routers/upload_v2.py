from fastapi import APIRouter, Depends, HTTPException, Body, Query
from fastapi.responses import RedirectResponse
from app.core.security import get_current_user
from app.services.permissions import check_upload_permissions
from app.services.azure_upload import azure_manager
from app.db.mongo import db
from datetime import datetime
import uuid
import os
from urllib.parse import urlparse, unquote

router = APIRouter()

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
        # Extract blob name from URL
        # URL format: https://<account>.blob.core.windows.net/<container>/<blob_name>
        parsed = urlparse(file_url)
        path = unquote(parsed.path) # /<container>/<blob_name>
        
        # Remove container name from path
        container = azure_manager.container_name
        if path.startswith(f"/{container}/"):
            blob_name = path[len(f"/{container}/"):]
        else:
            # Fallback or error
            raise HTTPException(status_code=400, detail="Invalid file URL")

        # Generate SAS
        sas_url = azure_manager.generate_read_sas(blob_name, filename=filename)
        
        return RedirectResponse(url=sas_url)
    except Exception as e:
        print(f"Download Error: {e}")
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
    msg_type = payload.get("message_type", "file") # file, audio, image

    if not all([filename, file_size, content_type, recipient_id]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    # 1. Check Permissions
    allowed, reason = await check_upload_permissions(user_id, recipient_id, file_size, content_type)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    # 2. Generate Blob Path
    # Structure: chat/{date}/{uuid}.ext
    ext = os.path.splitext(filename)[1]
    date_folder = datetime.now().strftime("%Y/%m/%d")
    upload_id = str(uuid.uuid4())
    blob_name = f"chat/{date_folder}/{upload_id}{ext}"

    # 3. Generate SAS URL
    try:
        sas_url = azure_manager.generate_upload_sas(blob_name)
    except Exception as e:
        print(f"Azure Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate upload token")

    # 4. Save Session to DB
    from datetime import timedelta
    session = {
        "_id": upload_id,
        "user_id": user_id,
        "recipient_id": recipient_id,
        "filename": filename,
        "file_size": file_size,
        "content_type": content_type,
        "message_type": msg_type,
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
    except Exception as e:
        print(f"Azure Commit Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to finalize file")

    # 3. Update Session
    await db.db.upload_sessions.update_one(
        {"_id": upload_id},
        {"$set": {"status": "completed", "file_url": file_url, "completed_at": datetime.utcnow()}}
    )

    # 4. Return Final URL (Frontend will then send the WebSocket message)
    # Why? Because we want the Frontend to control the "Send" action to sync with Optimistic UI.
    # The Backend *could* send it, but letting the frontend do it keeps the flow consistent with text messages.
    
    return {
        "status": "completed",
        "file_url": file_url,
        "filename": session["filename"],
        "size": session["file_size"],
        "content_type": session["content_type"]
    }
