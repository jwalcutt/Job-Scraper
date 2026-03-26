"""
Celery tasks for job scraping. Phase 2 implementation lives here.
Stubs are provided so the worker starts cleanly; full scrapers added in Phase 2.
"""
import asyncio
from app.tasks.worker import celery_app


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _upsert_jobs(jobs_data: list[dict]):
    """Persist a list of job dicts into the database."""
    from app.database import AsyncSessionLocal
    from app.models.job import Job
    from app.tasks.embed_tasks import embed_job
    from sqlalchemy import select

    async def _inner():
        async with AsyncSessionLocal() as db:
            new_job_ids = []
            for data in jobs_data:
                result = await db.execute(
                    select(Job).where(Job.source == data["source"], Job.external_id == data["external_id"])
                )
                existing = result.scalar_one_or_none()
                if existing:
                    # Update description in case it changed
                    existing.description = data.get("description", existing.description)
                    existing.title = data.get("title", existing.title)
                else:
                    job = Job(**{k: v for k, v in data.items() if hasattr(Job, k)})
                    db.add(job)
                    await db.flush()
                    new_job_ids.append(job.id)

            await db.commit()

            # Queue embeddings for new jobs
            for job_id in new_job_ids:
                embed_job.delay(job_id)

    _run(_inner())


@celery_app.task(name="app.tasks.scrape_tasks.scrape_greenhouse")
def scrape_greenhouse():
    """Scrape jobs from Greenhouse-powered company career pages."""
    from app.services.scraping.greenhouse_scraper import fetch_all_greenhouse_jobs
    jobs = fetch_all_greenhouse_jobs()
    _upsert_jobs(jobs)
    return f"Scraped {len(jobs)} Greenhouse jobs"


@celery_app.task(name="app.tasks.scrape_tasks.scrape_lever")
def scrape_lever():
    """Scrape jobs from Lever-powered company career pages."""
    from app.services.scraping.lever_scraper import fetch_all_lever_jobs
    jobs = fetch_all_lever_jobs()
    _upsert_jobs(jobs)
    return f"Scraped {len(jobs)} Lever jobs"


@celery_app.task(name="app.tasks.scrape_tasks.scrape_jobspy")
def scrape_jobspy(search_term: str = "software engineer", location: str = "United States"):
    """Scrape jobs via JobSpy (Indeed, LinkedIn, ZipRecruiter)."""
    from app.services.scraping.jobspy_scraper import fetch_jobspy_jobs
    jobs = fetch_jobspy_jobs(search_term=search_term, location=location)
    _upsert_jobs(jobs)
    return f"Scraped {len(jobs)} JobSpy jobs for '{search_term}'"


@celery_app.task(name="app.tasks.scrape_tasks.scrape_all_sources")
def scrape_all_sources():
    """Trigger all scrapers. Called by Celery Beat scheduler."""
    scrape_greenhouse.delay()
    scrape_lever.delay()
    # JobSpy search terms will be dynamically built from user profiles in Phase 3
    scrape_jobspy.delay("software engineer", "United States")
    return "All scrape tasks queued"
