"""Celery application definition."""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "job_scraper",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.embed_tasks",
        "app.tasks.scrape_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        # Refresh job listings every 24 hours
        "scrape-jobs-daily": {
            "task": "app.tasks.scrape_tasks.scrape_all_sources",
            "schedule": 86400.0,
        },
    },
)
