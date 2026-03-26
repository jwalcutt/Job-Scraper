"""
Celery tasks for job scraping.
"""
import asyncio
import logging
from app.tasks.worker import celery_app

logger = logging.getLogger(__name__)


def _run(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _upsert_jobs(jobs_data: list[dict]) -> tuple[int, int]:
    """
    Persist a list of job dicts into the database.
    Returns (new_count, updated_count).
    """
    from app.database import AsyncSessionLocal
    from app.models.job import Job
    from app.tasks.embed_tasks import embed_job
    from sqlalchemy import select

    async def _inner() -> tuple[int, int]:
        new_count = 0
        updated_count = 0
        async with AsyncSessionLocal() as db:
            new_job_ids: list[int] = []
            for data in jobs_data:
                if not data.get("external_id") or not data.get("source"):
                    continue
                result = await db.execute(
                    select(Job).where(
                        Job.source == data["source"],
                        Job.external_id == data["external_id"],
                    )
                )
                existing = result.scalar_one_or_none()
                if existing:
                    # Refresh mutable fields; preserve embedding unless description changed
                    desc_changed = data.get("description") and data["description"] != existing.description
                    existing.title = data.get("title", existing.title)
                    existing.description = data.get("description", existing.description)
                    existing.location = data.get("location", existing.location)
                    existing.is_remote = data.get("is_remote", existing.is_remote)
                    existing.salary_min = data.get("salary_min", existing.salary_min)
                    existing.salary_max = data.get("salary_max", existing.salary_max)
                    if desc_changed:
                        existing.embedding = None  # will be re-embedded
                        new_job_ids.append(existing.id)
                    updated_count += 1
                else:
                    valid_fields = {k: v for k, v in data.items() if hasattr(Job, k)}
                    job = Job(**valid_fields)
                    db.add(job)
                    await db.flush()
                    new_job_ids.append(job.id)
                    new_count += 1

            await db.commit()

            for job_id in new_job_ids:
                embed_job.delay(job_id)

        return new_count, updated_count

    return _run(_inner())


# ─────────────────────────────────────────────────────────────────────────────
# Individual scraper tasks
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.scrape_tasks.scrape_greenhouse", bind=True, max_retries=2)
def scrape_greenhouse(self, companies: list[str] | None = None):
    """Fetch jobs from Greenhouse-powered career pages."""
    from app.services.scraping.greenhouse_scraper import fetch_all_greenhouse_jobs
    jobs = fetch_all_greenhouse_jobs(companies=companies)
    new, updated = _upsert_jobs(jobs)
    msg = f"Greenhouse: {len(jobs)} fetched, {new} new, {updated} updated"
    logger.info(msg)
    return msg


@celery_app.task(name="app.tasks.scrape_tasks.scrape_lever", bind=True, max_retries=2)
def scrape_lever(self, companies: list[str] | None = None):
    """Fetch jobs from Lever-powered career pages."""
    from app.services.scraping.lever_scraper import fetch_all_lever_jobs
    jobs = fetch_all_lever_jobs(companies=companies)
    new, updated = _upsert_jobs(jobs)
    msg = f"Lever: {len(jobs)} fetched, {new} new, {updated} updated"
    logger.info(msg)
    return msg


@celery_app.task(name="app.tasks.scrape_tasks.scrape_jobspy", bind=True, max_retries=2)
def scrape_jobspy(
    self,
    search_term: str = "software engineer",
    location: str = "United States",
    results_wanted: int = 50,
):
    """Scrape one search term via JobSpy (Indeed + ZipRecruiter)."""
    from app.services.scraping.jobspy_scraper import fetch_jobspy_jobs
    jobs = fetch_jobspy_jobs(
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
    )
    new, updated = _upsert_jobs(jobs)
    msg = f"JobSpy '{search_term}': {len(jobs)} fetched, {new} new, {updated} updated"
    logger.info(msg)
    return msg


@celery_app.task(name="app.tasks.scrape_tasks.scrape_jobspy_all_profiles")
def scrape_jobspy_all_profiles():
    """
    Pull distinct desired_titles from all user profiles and spawn one
    scrape_jobspy task per unique title (capped at 30).
    """
    from app.database import AsyncSessionLocal
    from app.services.scraping.jobspy_scraper import collect_search_terms_from_profiles

    async def _get_terms() -> list[str]:
        async with AsyncSessionLocal() as db:
            return await collect_search_terms_from_profiles(db)

    terms = _run(_get_terms())
    for term in terms:
        scrape_jobspy.delay(term)
    return f"Queued JobSpy scrapes for {len(terms)} search terms"


# ─────────────────────────────────────────────────────────────────────────────
# Master orchestrator (called by Celery Beat)
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.scrape_tasks.scrape_all_sources")
def scrape_all_sources():
    """Trigger all scraper tasks. Called by Celery Beat every 24 h."""
    scrape_greenhouse.delay()
    scrape_lever.delay()
    scrape_jobspy_all_profiles.delay()
    return "All scrape tasks queued"
