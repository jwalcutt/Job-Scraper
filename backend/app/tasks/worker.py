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
        # 1. Scrape all sources every 24 hours (2 AM UTC)
        "scrape-jobs-daily": {
            "task": "app.tasks.scrape_tasks.scrape_all_sources",
            "schedule": 86400.0,
        },
        # 2. Embed any jobs that missed their embedding (e.g. transient failures)
        #    Runs 2 hours after scraping, processes up to 500 at a time
        "embed-jobs-backfill": {
            "task": "app.tasks.embed_tasks.embed_all_jobs",
            "schedule": 86400.0,
            "kwargs": {"batch_size": 500},
            "options": {"countdown": 7200},  # 2h after scrape
        },
        # 3. Recompute all user matches after embeddings settle
        "recompute-matches-daily": {
            "task": "app.tasks.embed_tasks.compute_all_user_matches",
            "schedule": 86400.0,
            "options": {"countdown": 10800},  # 3h after scrape
        },
    },
)
