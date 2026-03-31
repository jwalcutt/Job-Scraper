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
    from sqlalchemy import select

    from app.database import task_session as AsyncSessionLocal
    from app.models.job import Job
    from app.tasks.embed_tasks import embed_job

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
    from app.database import task_session as AsyncSessionLocal
    from app.services.scraping.jobspy_scraper import collect_search_terms_from_profiles

    async def _get_terms() -> list[str]:
        async with AsyncSessionLocal() as db:
            return await collect_search_terms_from_profiles(db)

    terms = _run(_get_terms())
    for term in terms:
        scrape_jobspy.delay(term)
    return f"Queued JobSpy scrapes for {len(terms)} search terms"


# ─────────────────────────────────────────────────────────────────────────────
# Company career page scraper tasks (Phase 7)
# ─────────────────────────────────────────────────────────────────────────────

_MIN_DOMAIN_DELAY = 5.0  # seconds between requests to the same domain


@celery_app.task(
    name="app.tasks.scrape_tasks.scrape_company_careers",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def scrape_company_careers(self, company_id: int):
    """
    Scrape a single company's career page and upsert jobs.
    Respects robots.txt and records last_scraped_at on success.
    """
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.database import task_session as AsyncSessionLocal
    from app.models.company import Company

    async def _inner():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Company).where(Company.id == company_id))
            company = result.scalar_one_or_none()
            if not company or not company.is_active:
                return f"Company {company_id} not found or inactive"

            from app.services.scraping.playwright_scraper import scrape_career_page
            jobs = await scrape_career_page(
                careers_url=company.careers_url,
                company_name=company.name,
                ats_type=company.ats_type,
            )

            company.last_scraped_at = datetime.now(timezone.utc)
            await db.commit()

            return jobs

    try:
        jobs = _run(_inner())
        if isinstance(jobs, str):
            return jobs  # informational message (inactive etc.)

        # Apply inter-domain delay (crude but sufficient for Celery task queue)
        import time
        time.sleep(_MIN_DOMAIN_DELAY)

        new, updated = _upsert_jobs(jobs)
        msg = f"Company {company_id}: {len(jobs)} fetched, {new} new, {updated} updated"
        logger.info(msg)
        return msg
    except Exception as exc:
        logger.warning("Company %d scrape failed: %s — retrying", company_id, exc)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)


@celery_app.task(name="app.tasks.scrape_tasks.scrape_all_company_careers")
def scrape_all_company_careers():
    """
    Fan-out: queue one scrape_company_careers task per active company.
    Called by Celery Beat alongside other scrapers.
    """
    from sqlalchemy import select

    from app.database import task_session as AsyncSessionLocal
    from app.models.company import Company

    async def _get_company_ids() -> list[int]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Company.id).where(Company.is_active.is_(True))
            )
            return [row[0] for row in result.all()]

    company_ids = _run(_get_company_ids())
    for cid in company_ids:
        scrape_company_careers.delay(cid)

    msg = f"Queued career-page scrapes for {len(company_ids)} companies"
    logger.info(msg)
    return msg


@celery_app.task(name="app.tasks.scrape_tasks.seed_company_registry")
def seed_company_registry():
    """One-shot task: populate the companies table from the built-in seed list."""
    from app.database import task_session as AsyncSessionLocal
    from app.services.scraping.company_registry import seed_companies

    async def _inner() -> int:
        async with AsyncSessionLocal() as db:
            return await seed_companies(db)

    n = _run(_inner())
    msg = f"Seeded {n} new companies into registry"
    logger.info(msg)
    return msg


# ─────────────────────────────────────────────────────────────────────────────
# Master orchestrator (called by Celery Beat)
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.scrape_tasks.scrape_all_sources")
def scrape_all_sources():
    """Trigger all scraper tasks. Called by Celery Beat every 24 h."""
    scrape_greenhouse.delay()
    scrape_lever.delay()
    scrape_jobspy_all_profiles.delay()
    scrape_all_company_careers.delay()
    return "All scrape tasks queued"
