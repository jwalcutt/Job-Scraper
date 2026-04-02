"""
Celery tasks for data quality and coverage improvements.
- Expired job pruning
- Cross-source duplicate detection
- Company logo fetching
- Job detail enrichment for short descriptions
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.tasks.worker import celery_app

logger = logging.getLogger(__name__)


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ─────────────────────────────────────────────────────────────────────────────
# Expired job pruning
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.data_quality_tasks.prune_expired_jobs")
def prune_expired_jobs(max_age_days: int = 60) -> str:
    """
    Delete jobs older than max_age_days that have no saved_jobs or applications.
    Matches and user_events cascade-delete with the job.
    """
    from sqlalchemy import and_, delete, select

    from app.database import task_session
    from app.models.job import Job
    from app.models.match import Application, SavedJob

    async def _inner() -> str:
        async with task_session() as db:
            cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

            # Find jobs that are old and not saved/applied-to
            stmt = (
                delete(Job)
                .where(
                    and_(
                        Job.scraped_at < cutoff,
                        ~Job.id.in_(select(SavedJob.job_id)),
                        ~Job.id.in_(select(Application.job_id)),
                    )
                )
                .returning(Job.id)
            )
            result = await db.execute(stmt)
            deleted_ids = result.scalars().all()
            await db.commit()

            msg = f"Pruned {len(deleted_ids)} expired jobs (older than {max_age_days} days)"
            logger.info(msg)
            return msg

    return _run(_inner())


# ─────────────────────────────────────────────────────────────────────────────
# Duplicate detection across sources
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.data_quality_tasks.deduplicate_jobs")
def deduplicate_jobs() -> str:
    """
    Find near-duplicate job postings from different sources by matching on
    (company, title, ~posted_at within 3 days). Keeps the one with the longest
    description and deletes the rest (if not saved/applied-to).
    """
    from sqlalchemy import and_, delete, func, select

    from app.database import task_session
    from app.models.job import Job
    from app.models.match import Application, SavedJob

    async def _inner() -> str:
        async with task_session() as db:
            # Find groups of potential duplicates: same company+title, posted within 3 days
            # Use a self-join approach
            j1 = Job.__table__.alias("j1")
            j2 = Job.__table__.alias("j2")

            stmt = select(j1.c.id, j2.c.id).where(
                and_(
                    j1.c.id < j2.c.id,
                    func.lower(j1.c.company) == func.lower(j2.c.company),
                    func.lower(j1.c.title) == func.lower(j2.c.title),
                    j1.c.source != j2.c.source,
                    # Both posted within 3 days of each other (or both null)
                    func.abs(
                        func.extract("epoch", j1.c.posted_at) -
                        func.extract("epoch", j2.c.posted_at)
                    ) < 259200,  # 3 days in seconds
                )
            ).limit(1000)

            rows = (await db.execute(stmt)).all()

            if not rows:
                return "No duplicates found"

            # For each pair, keep the one with the longer description
            to_delete: set[int] = set()
            all_ids = set()
            for id1, id2 in rows:
                all_ids.update([id1, id2])

            # Load descriptions for the candidates
            jobs_result = await db.execute(
                select(Job.id, func.length(func.coalesce(Job.description, ""))).where(
                    Job.id.in_(all_ids)
                )
            )
            desc_lengths = {jid: length for jid, length in jobs_result.all()}

            # Protected jobs (saved or applied-to)
            protected = set()
            saved = (await db.execute(
                select(SavedJob.job_id).where(SavedJob.job_id.in_(all_ids))
            )).scalars().all()
            applied = (await db.execute(
                select(Application.job_id).where(Application.job_id.in_(all_ids))
            )).scalars().all()
            protected.update(saved)
            protected.update(applied)

            for id1, id2 in rows:
                if id1 in to_delete or id2 in to_delete:
                    continue
                # Never delete protected jobs
                if id1 in protected and id2 in protected:
                    continue
                if id1 in protected:
                    to_delete.add(id2)
                elif id2 in protected:
                    to_delete.add(id1)
                else:
                    # Keep the one with the longer description
                    if desc_lengths.get(id1, 0) >= desc_lengths.get(id2, 0):
                        to_delete.add(id2)
                    else:
                        to_delete.add(id1)

            if to_delete:
                await db.execute(delete(Job).where(Job.id.in_(to_delete)))
                await db.commit()

            msg = f"Deduplicated: removed {len(to_delete)} duplicate jobs from {len(rows)} pairs"
            logger.info(msg)
            return msg

    return _run(_inner())


# ─────────────────────────────────────────────────────────────────────────────
# Company logo fetching
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.data_quality_tasks.fetch_company_logos")
def fetch_company_logos() -> str:
    """
    For companies without a logo_url, attempt to fetch one via Clearbit Logo API.
    Extracts the domain from the company's careers_url.
    """
    from urllib.parse import urlparse

    import httpx
    from sqlalchemy import select

    from app.database import task_session
    from app.models.company import Company

    async def _inner() -> str:
        async with task_session() as db:
            result = await db.execute(
                select(Company).where(
                    Company.logo_url.is_(None),
                    Company.careers_url.is_not(None),
                    Company.is_active.is_(True),
                )
            )
            companies = result.scalars().all()

            if not companies:
                return "No companies need logos"

            updated = 0
            async with httpx.AsyncClient(timeout=10) as client:
                for company in companies:
                    try:
                        parsed = urlparse(company.careers_url)
                        domain = parsed.hostname
                        if not domain:
                            continue
                        # Strip common subdomains
                        parts = domain.split(".")
                        if len(parts) > 2 and parts[0] in ("www", "jobs", "careers", "boards"):
                            domain = ".".join(parts[1:])

                        logo_url = f"https://logo.clearbit.com/{domain}"
                        # Verify the logo actually exists
                        resp = await client.head(logo_url)
                        if resp.status_code == 200:
                            company.logo_url = logo_url
                            updated += 1
                    except Exception as exc:
                        logger.debug("[fetch_logos] %s failed: %s", company.name, exc)
                        continue

            await db.commit()
            msg = f"Fetched logos for {updated}/{len(companies)} companies"
            logger.info(msg)
            return msg

    return _run(_inner())


# ─────────────────────────────────────────────────────────────────────────────
# Job detail enrichment
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.data_quality_tasks.enrich_short_descriptions")
def enrich_short_descriptions(min_length: int = 200, batch_size: int = 50) -> str:
    """
    For jobs with very short descriptions (<min_length chars), attempt to
    fetch the full job page and extract a better description.
    """
    import re

    import httpx
    from sqlalchemy import func, select

    from app.database import task_session
    from app.models.job import Job

    async def _inner() -> str:
        async with task_session() as db:
            result = await db.execute(
                select(Job).where(
                    Job.url.is_not(None),
                    func.length(func.coalesce(Job.description, "")) < min_length,
                ).limit(batch_size)
            )
            jobs = result.scalars().all()

            if not jobs:
                return "No jobs need enrichment"

            enriched = 0
            async with httpx.AsyncClient(
                timeout=15,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; JobMatcher/1.0)"},
            ) as client:
                for job in jobs:
                    try:
                        resp = await client.get(job.url)
                        if resp.status_code != 200:
                            continue

                        html = resp.text
                        # Try extracting text from common job description containers
                        # Remove script and style tags first
                        html_clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
                        # Remove all HTML tags
                        text = re.sub(r"<[^>]+>", " ", html_clean)
                        text = re.sub(r"\s+", " ", text).strip()

                        # Only update if we got substantially more content
                        if len(text) > len(job.description or "") + 100 and len(text) > min_length:
                            # Take a reasonable amount of text (not the whole page)
                            job.description = text[:5000]
                            job.embedding = None  # Invalidate for re-embedding
                            enriched += 1
                    except Exception as exc:
                        logger.debug("[enrich] job %d failed: %s", job.id, exc)
                        continue

            await db.commit()
            msg = f"Enriched {enriched}/{len(jobs)} short job descriptions"
            logger.info(msg)
            return msg

    return _run(_inner())
