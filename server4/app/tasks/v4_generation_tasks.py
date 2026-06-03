"""
Slice 2 (Durable V4 Generation) — Celery task wrapping ``_run_v4_pipeline``.

The legacy router path uses FastAPI ``BackgroundTasks`` to schedule the V4
pipeline inside the API process. That works fine until the worker process
restarts (Azure container recycles, deploy, OOM kill) — in which case the
in-flight deck dies silently and the user sees "Generating..." forever.

This task moves the same coroutine to a Celery worker so it survives:
  * router process restarts
  * code deploys (worker queue drains gracefully)
  * crashes (Celery acks_late → another worker picks the message back up)

The route still dispatches in-process when ``settings.V4_USE_CELERY_QUEUE``
is ``False`` so a deployment without a worker keeps working unchanged.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_event_loop() -> asyncio.AbstractEventLoop:
    """Return a usable event loop for this Celery worker process.

    Mirrors the pattern used in ``app.tasks.unified_tasks._get_event_loop``.
    Celery prefork workers do not reuse the asyncio loop across tasks; we
    create a fresh one per invocation so any prior task's cancelled
    coroutines cannot leak into ours.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def _import_pipeline_runner():
    """Import the existing router-resident async pipeline runner.

    Importing inside the task avoids pulling FastAPI app state into the
    worker bootstrap and keeps this module's import graph small.
    """
    from app.routers.generation_v4 import _run_v4_pipeline

    return _run_v4_pipeline


@celery_app.task(
    bind=True,
    name="app.tasks.v4_generation_tasks.run_v4_generation",
    max_retries=0,  # The pipeline already retries inside; idempotency-by-row is the contract.
    time_limit=900,  # Will be overridden by settings at task-definition time below.
    soft_time_limit=840,
    acks_late=True,
)
def run_v4_generation(
    self,
    *,
    project_id: str,
    user_id: str,
    user_query: str,
    analysis_dump: dict[str, Any],
    mode: str,
    purpose: str,
    industry: Optional[str],
    company_name: Optional[str],
    user_slide_types: Optional[list[str]],
    target_slide_count: Optional[int],
    structured_context: Optional[dict[str, Any]] = None,
    template_id: Optional[str] = None,
    generate_images: bool = False,
) -> dict[str, Any]:
    """Celery wrapper for the V4 pipeline.

    Parameters mirror ``app.routers.generation_v4._run_v4_pipeline`` exactly
    so the Celery and BackgroundTasks paths produce identical Mongo state.
    Returning a small JSON-serialisable dict gives the result backend
    something useful for ``celery_app.AsyncResult(task_id).result``.
    """
    return _execute_v4_generation(
        self,
        project_id=project_id,
        user_id=user_id,
        user_query=user_query,
        analysis_dump=analysis_dump,
        mode=mode,
        purpose=purpose,
        industry=industry,
        company_name=company_name,
        user_slide_types=user_slide_types,
        target_slide_count=target_slide_count,
        structured_context=structured_context,
        template_id=template_id,
        generate_images=generate_images,
    )


def _execute_v4_generation(
    task: Any,
    *,
    project_id: str,
    user_id: str,
    user_query: str,
    analysis_dump: dict[str, Any],
    mode: str,
    purpose: str,
    industry: Optional[str],
    company_name: Optional[str],
    user_slide_types: Optional[list[str]],
    target_slide_count: Optional[int],
    structured_context: Optional[dict[str, Any]] = None,
    template_id: Optional[str] = None,
    generate_images: bool = False,
) -> dict[str, Any]:
    """Pure-Python body of ``run_v4_generation`` — testable without Celery.

    ``task`` is the Celery bound-task self (or any object exposing
    ``update_state``); pass any duck-typed instance in tests.
    """
    loop = _get_event_loop()
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        task.update_state(
            state="STARTED",
            meta={"project_id": project_id, "mode": mode, "started_at": started_at},
        )
    except Exception:  # pragma: no cover - update_state is best-effort
        pass

    runner = _import_pipeline_runner()
    try:
        loop.run_until_complete(
            runner(
                project_id=project_id,
                user_id=user_id,
                user_query=user_query,
                analysis_dump=analysis_dump,
                mode=mode,
                purpose=purpose,
                industry=industry,
                company_name=company_name,
                user_slide_types=user_slide_types,
                target_slide_count=target_slide_count,
                structured_context=structured_context,
                template_id=template_id,
                generate_images=generate_images,
            )
        )
        completed_at = datetime.now(timezone.utc).isoformat()
        return {
            "ok": True,
            "project_id": project_id,
            "mode": mode,
            "started_at": started_at,
            "completed_at": completed_at,
        }
    except Exception as exc:  # noqa: BLE001
        # The pipeline itself catches its own exceptions and writes
        # ``generation_state == FAILED`` to Mongo. Reaching this branch
        # means something broke OUTSIDE the pipeline (import error,
        # event-loop creation failure, etc.). Mark the row failed too,
        # synchronously via pymongo so we don't depend on the broken
        # async loop.
        logger.exception(
            "v4_celery_task_failed_outside_pipeline",
            extra={"project_id": project_id, "error": str(exc)[:240]},
        )
        try:
            from pymongo import MongoClient
            from app.config import settings

            client = MongoClient(settings.MONGODB_URI)
            try:
                client[settings.MONGODB_DB_NAME].presentations.update_one(
                    {"_id": project_id},
                    {
                        "$set": {
                            "generation_state": "failed",
                            "generation_error": (
                                f"v4_celery_task_unhandled_exception: {str(exc)[:480]}"
                            ),
                            "updated_at": datetime.now(timezone.utc),
                        }
                    },
                )
            finally:
                client.close()
        except Exception:  # pragma: no cover - last-resort logging only
            logger.exception(
                "v4_celery_task_failed_to_mark_row_failed",
                extra={"project_id": project_id},
            )
        raise


# ── Slice 2 (Durable V4) — Stalled-job reaper ─────────────────────
#
# A worker that crashes mid-task leaves the presentation row stuck in
# ``generating_content``. This task is registered on the SAME Celery app
# (``app.tasks.celery_app``) so a single beat schedule can drive it.
# ``celery_worker.celery_app`` separately handles export-job reaping.

@celery_app.task(name="app.tasks.v4_generation_tasks.reap_stalled_v4_generations")
def reap_stalled_v4_generations() -> dict[str, Any]:
    """Mark V4 generations as failed when they have not progressed in N min.

    Mirrors the existing ``export.reap_stale_jobs`` shape so ops dashboards
    that already chart stale-job counts get the same contract.
    """
    from pymongo import MongoClient
    from app.config import settings

    cutoff_minutes = int(getattr(settings, "V4_STALLED_JOB_REAP_MINUTES", 20))
    cutoff = datetime.now(timezone.utc) - _timedelta_minutes(cutoff_minutes)

    client = MongoClient(settings.MONGODB_URI)
    try:
        db = client[settings.MONGODB_DB_NAME]
        # We only reap rows that look like they belong to V4 (created via
        # the v4 router). The ``celery_task_id`` presence guards us
        # against accidentally killing legacy non-celery generations.
        result = db.presentations.update_many(
            {
                "created_from": "ai_v4",
                "generation_state": {"$in": ["generating_content", "idle"]},
                "celery_task_id": {"$exists": True, "$ne": None},
                "updated_at": {"$lt": cutoff},
            },
            {
                "$set": {
                    "generation_state": "failed",
                    "generation_error": (
                        "V4 generation worker did not progress within "
                        f"{cutoff_minutes} minutes. The job was reaped; "
                        "you can safely retry."
                    ),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        if result.modified_count > 0:
            logger.warning(
                "v4_stalled_generations_reaped",
                extra={"count": result.modified_count, "cutoff_minutes": cutoff_minutes},
            )
        return {"reaped": int(result.modified_count), "cutoff_minutes": cutoff_minutes}
    finally:
        client.close()


def _timedelta_minutes(minutes: int):
    """Tiny helper so the import surface stays small at module top."""
    from datetime import timedelta

    return timedelta(minutes=int(max(1, minutes)))
