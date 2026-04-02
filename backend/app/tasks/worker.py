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
        "app.tasks.llm_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.data_quality_tasks",
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
        # 4. Send email digests after matches are fresh (4h after scrape)
        "send-digests-daily": {
            "task": "app.tasks.notification_tasks.send_all_digests",
            "schedule": 86400.0,
            "options": {"countdown": 14400},
        },
        # 5. Check job alerts every 6 hours
        "check-job-alerts": {
            "task": "app.tasks.notification_tasks.check_job_alerts",
            "schedule": 21600.0,  # 6 hours
        },
        # 6. Prune expired jobs weekly (runs once per day, only deletes old ones)
        "prune-expired-jobs-weekly": {
            "task": "app.tasks.data_quality_tasks.prune_expired_jobs",
            "schedule": 604800.0,  # 7 days
        },
        # 7. Deduplicate jobs weekly
        "deduplicate-jobs-weekly": {
            "task": "app.tasks.data_quality_tasks.deduplicate_jobs",
            "schedule": 604800.0,
            "options": {"countdown": 3600},  # 1h after prune
        },
        # 8. Fetch company logos weekly
        "fetch-logos-weekly": {
            "task": "app.tasks.data_quality_tasks.fetch_company_logos",
            "schedule": 604800.0,
        },
        # 9. Enrich short job descriptions daily (after scrape + embed)
        "enrich-short-descriptions-daily": {
            "task": "app.tasks.data_quality_tasks.enrich_short_descriptions",
            "schedule": 86400.0,
            "options": {"countdown": 16200},  # 4.5h after scrape
        },
    },
)
