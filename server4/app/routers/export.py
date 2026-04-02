"""Export endpoints — PPTX, PDF, HTML, PNG with SAS-protected downloads."""

from datetime import datetime

from bson import ObjectId
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.dependencies import optional_auth, require_auth
from app.models.render import (
    ExportFormat,
    ExportRequest,
    ExportJobResponse,
    ExportStatus,
)
from app.services.storage.blob_service import BlobStorageService

router = APIRouter(prefix="/api/export", tags=["Export"])

SLIDE_COUNT_THRESHOLD = 12

# Format → Celery task mapping
ASYNC_TASK_MAP = {
    ExportFormat.HTML: "export.generate_html",
    ExportFormat.PNG: "export.generate_png",
}

SYNC_TASK_MAP = {
    ExportFormat.PPTX: "export.generate_pptx",
    ExportFormat.PDF: "export.generate_pdf",
}

CONTENT_TYPE_MAP = {
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "pdf": "application/pdf",
    "html": "text/html",
    "zip": "application/zip",
}


async def _fetch_presentation_data(
    presentation_id: str, user_id: str, db
) -> tuple[dict, list[dict], dict]:
    """Fetch presentation, slides, and theme. Returns (pres, slides, theme)."""
    pres = await db.presentations.find_one({"_id": presentation_id, "user_id": user_id})
    if not pres:
        raise HTTPException(status_code=404, detail="Presentation not found")

    slides = (
        await db.slides.find({"presentation_id": presentation_id})
        .sort("index", 1)
        .to_list(None)
    )

    theme_id = pres.get("theme_id")
    theme = {}
    if theme_id:
        theme = await db.themes.find_one({"_id": theme_id}) or {}

    return pres, slides, theme


def _build_metadata(pres: dict) -> dict:
    """Build metadata dict for builders."""
    return {
        "title": pres.get("title", "Presentation"),
        "author": pres.get("author", ""),
        "company": pres.get("company", ""),
    }


async def _complete_job(db, job_id: str, download_url: str, file_size: int) -> None:
    """Mark export job as completed."""
    await db.export_jobs.update_one(
        {"_id": job_id},
        {
            "$set": {
                "status": ExportStatus.COMPLETED.value,
                "download_url": download_url,
                "file_size": file_size,
                "completed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        },
    )


async def _fail_job(db, job_id: str, error: str) -> None:
    """Mark export job as failed."""
    await db.export_jobs.update_one(
        {"_id": job_id},
        {
            "$set": {
                "status": ExportStatus.FAILED.value,
                "error": error,
                "updated_at": datetime.utcnow(),
            }
        },
    )


def _dispatch_celery(task_name: str, args: list) -> str:
    """Dispatch a Celery task and return the task ID."""
    from celery_worker import celery_app

    result = celery_app.send_task(task_name, args=args)
    return result.id


# ── Sync export handlers ──────────────────────────────────────────


async def _handle_pptx_sync(db, job_id, pres, slides, theme):
    """Generate PPTX synchronously and upload to blob storage."""
    from app.mcp.render_mcp.builders.pptx_builder import PptxBuilder

    builder = PptxBuilder()
    pptx_bytes = builder.build(slides, theme, _build_metadata(pres))

    blob_service = BlobStorageService()
    blob_name = f"exports/{pres['_id']}/presentation.pptx"
    await blob_service.upload_file(
        file_data=pptx_bytes,
        filename=blob_name,
        content_type=CONTENT_TYPE_MAP["pptx"],
    )
    download_url = blob_service.generate_sas_download_url(blob_name, expiry_hours=1)
    await blob_service.close()

    await _complete_job(db, job_id, download_url, len(pptx_bytes))


async def _handle_pdf_sync(db, job_id, pres, slides, theme):
    """Generate PDF synchronously and upload to blob storage."""
    from app.mcp.render_mcp.builders.pdf_builder import PdfBuilder

    builder = PdfBuilder()
    pdf_bytes = builder.build(slides, theme, _build_metadata(pres))

    blob_service = BlobStorageService()
    blob_name = f"exports/{pres['_id']}/presentation.pdf"
    await blob_service.upload_file(
        file_data=pdf_bytes,
        filename=blob_name,
        content_type=CONTENT_TYPE_MAP["pdf"],
    )
    download_url = blob_service.generate_sas_download_url(blob_name, expiry_hours=1)
    await blob_service.close()

    await _complete_job(db, job_id, download_url, len(pdf_bytes))


# ── Routes ────────────────────────────────────────────────────────


@router.post("/{presentation_id}")
async def create_export_job(
    presentation_id: str,
    body: ExportRequest,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> ExportJobResponse:
    """Create an export job. Sync for small PPTX/PDF, async for rest."""
    pres, slides, theme = await _fetch_presentation_data(
        presentation_id, user["user_id"], db
    )

    # Premium format check
    if body.format in (ExportFormat.HTML, ExportFormat.PNG):
        if pres.get("mode") != "premium":
            raise HTTPException(
                status_code=403,
                detail=f"{body.format.value.upper()} export is Premium-only",
            )

    job_id = str(ObjectId())
    slide_count = pres.get("slide_count", len(slides))
    job = {
        "_id": job_id,
        "presentation_id": presentation_id,
        "user_id": user["user_id"],
        "format": body.format.value,
        "status": ExportStatus.PENDING.value,
        "include_notes": body.include_notes,
        "quality": body.quality,
        "download_url": None,
        "file_size": None,
        "blob_name": None,
        "error": None,
        "celery_task_id": None,
        "created_at": datetime.utcnow(),
        "completed_at": None,
        "updated_at": datetime.utcnow(),
    }
    await db.export_jobs.insert_one(job)

    # ── Async path: HTML, PNG, or large PPTX/PDF ──
    if body.format in ASYNC_TASK_MAP:
        task_name = ASYNC_TASK_MAP[body.format]
        task_id = _dispatch_celery(
            task_name,
            args=[presentation_id, theme, slides, _build_metadata(pres)],
        )
        await db.export_jobs.update_one(
            {"_id": job_id},
            {"$set": {"celery_task_id": task_id, "status": ExportStatus.PENDING.value}},
        )
        return ExportJobResponse(
            id=job_id,
            presentation_id=presentation_id,
            format=body.format,
            status=ExportStatus.PENDING,
            download_url=None,
            file_size=None,
            error=None,
            created_at=job["created_at"],
            completed_at=None,
        )

    # Large PPTX/PDF → async to avoid HTTP timeout
    if body.format in SYNC_TASK_MAP and slide_count > SLIDE_COUNT_THRESHOLD:
        task_name = SYNC_TASK_MAP[body.format]
        task_id = _dispatch_celery(
            task_name,
            args=[presentation_id, theme, slides, _build_metadata(pres)],
        )
        await db.export_jobs.update_one(
            {"_id": job_id},
            {"$set": {"celery_task_id": task_id, "status": ExportStatus.PENDING.value}},
        )
        return ExportJobResponse(
            id=job_id,
            presentation_id=presentation_id,
            format=body.format,
            status=ExportStatus.PENDING,
            download_url=None,
            file_size=None,
            error=None,
            created_at=job["created_at"],
            completed_at=None,
        )

    # ── Sync path: small PPTX/PDF ──
    try:
        if body.format == ExportFormat.PPTX:
            await _handle_pptx_sync(db, job_id, pres, slides, theme)
        elif body.format == ExportFormat.PDF:
            await _handle_pdf_sync(db, job_id, pres, slides, theme)
        else:
            await _fail_job(db, job_id, f"Unsupported format: {body.format.value}")
    except Exception as e:
        await _fail_job(db, job_id, str(e))
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

    # Fetch updated job for response
    updated_job = await db.export_jobs.find_one({"_id": job_id})
    if not updated_job:
        raise HTTPException(status_code=500, detail="Job record lost after export")
    return ExportJobResponse(
        id=str(updated_job["_id"]),
        presentation_id=updated_job["presentation_id"],
        format=updated_job["format"],
        status=updated_job["status"],
        download_url=updated_job.get("download_url"),
        file_size=updated_job.get("file_size"),
        error=updated_job.get("error"),
        created_at=updated_job["created_at"],
        completed_at=updated_job.get("completed_at"),
    )


@router.get("/status/{job_id}")
async def get_export_status(
    job_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> ExportJobResponse:
    """Get export job status. Regenerates SAS token if completed."""
    job = await db.export_jobs.find_one({"_id": job_id, "user_id": user["user_id"]})
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")

    # If completed, regenerate fresh SAS token (old one may have expired)
    if job["status"] == ExportStatus.COMPLETED.value and job.get("blob_name"):
        try:
            blob_service = BlobStorageService()
            job["download_url"] = blob_service.generate_sas_download_url(
                job["blob_name"], expiry_hours=1
            )
            await blob_service.close()
        except Exception:
            pass  # Use existing URL if SAS regeneration fails

    return ExportJobResponse(
        id=str(job["_id"]),
        presentation_id=job["presentation_id"],
        format=job["format"],
        status=job["status"],
        download_url=job.get("download_url"),
        file_size=job.get("file_size"),
        error=job.get("error"),
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
    )


@router.get("/download/{job_id}")
async def download_export(
    job_id: str,
    user: dict = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(lambda: get_db()),
) -> dict:
    """Get download URL with fresh SAS token."""
    job = await db.export_jobs.find_one({"_id": job_id, "user_id": user["user_id"]})
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")

    if job["status"] != ExportStatus.COMPLETED.value:
        raise HTTPException(
            status_code=400, detail=f"Export not ready. Status: {job['status']}"
        )

    blob_name = job.get("blob_name")
    if not blob_name:
        raise HTTPException(status_code=500, detail="Export file metadata missing")

    # Generate fresh SAS token
    try:
        blob_service = BlobStorageService()
        download_url = blob_service.generate_sas_download_url(blob_name, expiry_hours=1)
        await blob_service.close()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"SAS token generation failed: {str(e)}"
        )

    return {
        "download_url": download_url,
        "filename": f"presentation.{job['format']}",
        "file_size": job.get("file_size"),
    }
