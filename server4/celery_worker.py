"""
Celery worker for long-running export jobs (PPTX, PDF, HTML, PNG).
Start with: celery -A celery_worker.celery_app worker --loglevel=info
"""

import asyncio
import io
import zipfile
from datetime import datetime, timedelta

from celery import Celery
from pymongo import MongoClient

from app.config import settings

celery_app = Celery(
    "presentation_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minute hard limit
    task_soft_time_limit=240,  # 4 minute soft limit
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (memory safety)
    beat_schedule={
        "reap-stale-jobs": {
            "task": "export.reap_stale_jobs",
            "schedule": 300.0,  # Every 5 minutes
        },
    },
)


def _run_async(coro):
    """Run an async coroutine in a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _get_sync_db():
    """Get synchronous pymongo database for use in Celery tasks."""
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DB_NAME], client


def _update_job_status(job_id: str, status: str, **kwargs):
    """Update MongoDB export job status from Celery task (sync pymongo)."""
    db, client = _get_sync_db()
    updates = {"status": status, "updated_at": datetime.utcnow()}
    updates.update(kwargs)
    db.export_jobs.update_one({"_id": job_id}, {"$set": updates})
    client.close()


def _upload_and_complete(
    presentation_id: str, data: bytes, ext: str, job_id: str | None
):
    """Upload to blob storage, generate SAS URL, and mark job completed."""
    from app.services.storage.blob_service import BlobStorageService

    blob_service = BlobStorageService()
    blob_name = f"exports/{presentation_id}/presentation.{ext}"

    content_type_map = {
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pdf": "application/pdf",
        "html": "text/html",
        "zip": "application/zip",
    }

    _run_async(
        blob_service.upload_file(
            file_data=data,
            filename=blob_name,
            content_type=content_type_map.get(ext, "application/octet-stream"),
        )
    )

    download_url = blob_service.generate_sas_download_url(blob_name, expiry_hours=1)
    _run_async(blob_service.close())

    if job_id:
        _update_job_status(
            job_id,
            "completed",
            download_url=download_url,
            blob_name=blob_name,
            file_size=len(data),
            completed_at=datetime.utcnow(),
        )
    return download_url


# ── Export Tasks ──────────────────────────────────────────────────


@celery_app.task(bind=True, name="export.generate_pptx")
def generate_pptx_task(
    self, presentation_id: str, theme: dict, slides: list[dict], metadata: dict
):
    """Generate PPTX file and upload to blob storage."""
    from app.mcp.render_mcp.builders.pptx_builder import PptxBuilder

    job_id = _find_job_id(presentation_id, "pptx")
    if job_id:
        _update_job_status(job_id, "processing")

    try:
        self.update_state(state="BUILDING", meta={"format": "pptx", "progress": 10})

        builder = PptxBuilder()
        pptx_bytes = builder.build(slides, theme, metadata)

        self.update_state(state="UPLOADING", meta={"format": "pptx", "progress": 80})

        url = _upload_and_complete(presentation_id, pptx_bytes, "pptx", job_id)
        return {"file_path": url, "format": "pptx", "size_bytes": len(pptx_bytes)}

    except Exception as e:
        if job_id:
            _update_job_status(job_id, "failed", error=str(e))
        raise


@celery_app.task(bind=True, name="export.generate_pdf")
def generate_pdf_task(
    self, presentation_id: str, theme: dict, slides: list[dict], metadata: dict
):
    """Generate PDF file and upload to blob storage."""
    from app.mcp.render_mcp.builders.pdf_builder import PdfBuilder

    job_id = _find_job_id(presentation_id, "pdf")
    if job_id:
        _update_job_status(job_id, "processing")

    try:
        self.update_state(state="BUILDING", meta={"format": "pdf", "progress": 10})

        builder = PdfBuilder()
        pdf_bytes = builder.build(slides, theme, metadata)

        self.update_state(state="UPLOADING", meta={"format": "pdf", "progress": 80})

        url = _upload_and_complete(presentation_id, pdf_bytes, "pdf", job_id)
        return {"file_path": url, "format": "pdf", "size_bytes": len(pdf_bytes)}

    except Exception as e:
        if job_id:
            _update_job_status(job_id, "failed", error=str(e))
        raise


@celery_app.task(bind=True, name="export.generate_html")
def generate_html_task(
    self, presentation_id: str, theme: dict, slides: list[dict], metadata: dict
):
    """Generate HTML file and upload to blob storage."""
    from app.mcp.render_mcp.builders.html_builder import HtmlBuilder

    job_id = _find_job_id(presentation_id, "html")
    if job_id:
        _update_job_status(job_id, "processing")

    try:
        self.update_state(state="BUILDING", meta={"format": "html", "progress": 10})

        builder = HtmlBuilder()
        html_content = builder.build(slides, theme, metadata)
        html_bytes = html_content.encode("utf-8")

        self.update_state(state="UPLOADING", meta={"format": "html", "progress": 80})

        url = _upload_and_complete(presentation_id, html_bytes, "html", job_id)
        return {"file_path": url, "format": "html", "size_bytes": len(html_bytes)}

    except Exception as e:
        if job_id:
            _update_job_status(job_id, "failed", error=str(e))
        raise


@celery_app.task(bind=True, name="export.generate_png")
def generate_png_task(
    self, presentation_id: str, theme: dict, slides: list[dict], metadata: dict
):
    """Generate PNG images for all slides and upload as zip."""
    from app.mcp.render_mcp.builders.image_builder import ImageBuilder

    job_id = _find_job_id(presentation_id, "png")
    if job_id:
        _update_job_status(job_id, "processing")

    try:
        self.update_state(state="BUILDING", meta={"format": "png", "progress": 10})

        builder = ImageBuilder()
        images = _run_async(builder.render_all_slides(slides, theme))

        self.update_state(state="UPLOADING", meta={"format": "png", "progress": 70})

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, img in enumerate(images):
                zf.writestr(f"slide_{i + 1:03d}.png", img)
        zip_buf.seek(0)
        zip_data = zip_buf.read()

        url = _upload_and_complete(presentation_id, zip_data, "zip", job_id)
        return {"file_path": url, "format": "png_zip", "slide_count": len(images)}

    except Exception as e:
        if job_id:
            _update_job_status(job_id, "failed", error=str(e))
        raise


# ── Zombie Reaper ─────────────────────────────────────────────────


@celery_app.task(name="export.reap_stale_jobs")
def reap_stale_jobs():
    """Kill jobs stuck in PROCESSING for > 10 minutes (crashed workers)."""
    import structlog

    db, client = _get_sync_db()
    timeout = datetime.utcnow() - timedelta(minutes=10)
    result = db.export_jobs.update_many(
        {"status": "processing", "updated_at": {"$lt": timeout}},
        {
            "$set": {
                "status": "failed",
                "error": "Generation timed out (worker crash or OOM). Please retry.",
                "updated_at": datetime.utcnow(),
            }
        },
    )
    client.close()
    if result.modified_count > 0:
        structlog.get_logger().warning(
            "zombie_jobs_reaped", count=result.modified_count
        )
    return result.modified_count


# ── Thumbnail Tasks (Phase E3) ──────────────────────────────────


@celery_app.task(bind=True, name="thumbnail.generate")
def generate_thumbnail_task(self, presentation_id: str):
    """
    Generate presentation thumbnail asynchronously.

    Fires immediately after presentation record is created (parallel to
    slide generation). Waits for first slide to exist, then renders
    and uploads the thumbnail to Blob Storage.

    Updates presentation document with thumbnail_url when complete.
    """
    import time
    import structlog

    logger = structlog.get_logger()
    db, client = _get_sync_db()

    try:
        # Wait for first slide to be available (poll up to 60 seconds)
        first_slide = None
        for attempt in range(12):
            first_slide = db.slides.find_one(
                {"presentation_id": presentation_id},
                sort=[("index", 1)],
            )
            if first_slide:
                break
            time.sleep(5)

        if not first_slide:
            logger.warning(
                "thumbnail_no_slide_found",
                presentation_id=presentation_id,
                waited_seconds=60,
            )
            db.presentations.update_one(
                {"_id": presentation_id},
                {
                    "$set": {
                        "thumbnail_status": "no_slide",
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            client.close()
            return {"status": "no_slide", "presentation_id": presentation_id}

        # Get theme for rendering
        pres = db.presentations.find_one({"_id": presentation_id})
        theme = {}
        if pres and pres.get("theme_id"):
            theme = db.themes.find_one({"_id": pres["theme_id"]}) or {}

        # Render thumbnail via ThumbnailBuilder
        from app.mcp.render_mcp.builders.thumbnail_builder import ThumbnailBuilder

        builder = ThumbnailBuilder()
        thumb_bytes = _run_async(builder.generate_thumbnail(first_slide, theme))

        # Upload to Blob Storage
        blob_service = BlobStorageService()
        blob_name = f"thumbnails/{presentation_id}/cover.jpg"

        _run_async(
            blob_service.upload_file(
                file_data=thumb_bytes,
                filename="cover.jpg",
                content_type="image/jpeg",
                folder=f"thumbnails/{presentation_id}",
            )
        )

        thumbnail_url = blob_service.generate_sas_download_url(
            blob_name,
            expiry_hours=720,  # 30 days
        )
        _run_async(blob_service.close())

        # Update presentation with thumbnail URL
        db.presentations.update_one(
            {"_id": presentation_id},
            {
                "$set": {
                    "thumbnail_url": thumbnail_url,
                    "thumbnail_blob_name": blob_name,
                    "thumbnail_status": "ready",
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        logger.info(
            "thumbnail_generated",
            presentation_id=presentation_id,
            size_kb=len(thumb_bytes) // 1024,
        )

        client.close()
        return {
            "status": "completed",
            "thumbnail_url": thumbnail_url,
            "presentation_id": presentation_id,
        }

    except Exception as e:
        logger.error(
            "thumbnail_failed",
            presentation_id=presentation_id,
            error=str(e),
        )
        db.presentations.update_one(
            {"_id": presentation_id},
            {
                "$set": {
                    "thumbnail_status": "failed",
                    "thumbnail_error": str(e),
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        client.close()
        raise


# ── Helpers ───────────────────────────────────────────────────────


def _find_job_id(presentation_id: str, fmt: str) -> str | None:
    """Find the most recent pending export job for this presentation."""
    db, client = _get_sync_db()
    job = db.export_jobs.find_one(
        {"presentation_id": presentation_id, "format": fmt, "status": "pending"},
        sort=[("created_at", -1)],
    )
    client.close()
    return job["_id"] if job else None
