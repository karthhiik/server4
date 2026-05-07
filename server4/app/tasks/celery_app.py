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
    },
)
