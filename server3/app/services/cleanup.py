from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db.mongo import db
from app.services.azure_upload import azure_manager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Disable verbose APScheduler logging to reduce overhead
logging.getLogger('apscheduler.schedulers.base').setLevel(logging.WARNING)
logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
logging.getLogger('apscheduler.scheduler').setLevel(logging.WARNING)

async def cleanup_expired_files():
    """
    Background job to delete files older than 10 days.
    """
    try:
        now = datetime.utcnow()
        # Find expired files that are completed and not yet marked expired
        cursor = db.db.upload_sessions.find({
            "expires_at": {"$lt": now},
            "status": "completed"
        })
        
        async for session in cursor:
            upload_id = session["_id"]
            blob_name = session["blob_name"]
            
            try:
                # 1. Delete from Azure
                container_client = azure_manager.blob_service_client.get_container_client(azure_manager.container_name)
                container_client.delete_blob(blob_name)
                logger.info(f"Deleted expired blob: {blob_name}")
                
                # 2. Update DB status
                await db.db.upload_sessions.update_one(
                    {"_id": upload_id},
                    {"$set": {"status": "expired"}}
                )
            except Exception as e:
                logger.error(f"Failed to delete blob {blob_name}: {e}")
                
    except Exception as e:
        logger.error(f"Cleanup job failed: {e}")

def start_scheduler():
    scheduler = AsyncIOScheduler()
    # Run every hour
    scheduler.add_job(cleanup_expired_files, 'interval', hours=1)
    scheduler.start()
    logger.info("Cleanup scheduler started")
