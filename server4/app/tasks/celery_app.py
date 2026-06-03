"""Celery application configuration for background research tasks."""

from celery import Celery
from app.config import settings, _fix_rediss_url

celery_app = Celery(
    "server4_tasks",
    broker=_fix_rediss_url(settings.CELERY_BROKER_URL),
    backend=_fix_rediss_url(settings.CELERY_RESULT_BACKEND),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=max(settings.CELERY_TASK_TIME_LIMIT - 60, 60),
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.research_tasks.generate_deck_content": {"queue": "content"},
        "app.tasks.research_tasks.research_slide_task": {"queue": "research"},
        "app.tasks.unified_tasks.generate_unified_deck": {"queue": "content"},
        # Slice 2 (Durable V4): the v4 generation task self-routes per
        # mode at dispatch time via apply_async(queue=...). The default
        # queue here is the standard one as a safety net if a caller
        # forgets to set the queue explicitly.
        "app.tasks.v4_generation_tasks.run_v4_generation": {"queue": "content-fast"},
        "app.tasks.v4_generation_tasks.reap_stalled_v4_generations": {"queue": "content-fast"},
    },
    # Slice 2 (Durable V4): periodically reap V4 jobs that crashed
    # mid-generation. The export worker has its own reaper for export
    # jobs; this one targets ``presentations`` rows whose v4 worker
    # didn't update progress within ``V4_STALLED_JOB_REAP_MINUTES``.
    beat_schedule={
        "reap-stalled-v4-generations": {
            "task": "app.tasks.v4_generation_tasks.reap_stalled_v4_generations",
            "schedule": 300.0,  # every 5 minutes
        },
    },
)
