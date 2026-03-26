"""
Celery tasks for embedding generation and match computation.
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


# ─────────────────────────────────────────────────────────────────────────────
# Single-item tasks (called per job/profile by scrapers and profile updates)
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.embed_tasks.embed_job", bind=True, max_retries=3)
def embed_job(self, job_id: int):
    """Compute and persist the embedding for a single job."""
    from app.database import task_session
    from app.models.job import Job
    from app.services.embedding import embed_job as compute_embedding
    from sqlalchemy import select

    async def _inner():
        async with task_session() as db:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return
            try:
                job.embedding = compute_embedding(job)
                await db.commit()
                logger.debug("[embed_job] job_id=%d done", job_id)
            except Exception as exc:
                logger.error("[embed_job] job_id=%d failed: %s", job_id, exc)
                raise self.retry(exc=exc, countdown=30)

    _run(_inner())


@celery_app.task(name="app.tasks.embed_tasks.embed_profile", bind=True, max_retries=3)
def embed_profile(self, profile_id: int):
    """Recompute the embedding for a profile, then trigger match computation."""
    from app.database import task_session
    from app.models.profile import Profile
    from app.services.embedding import embed_profile as compute_embedding
    from sqlalchemy import select

    async def _inner():
        async with task_session() as db:
            result = await db.execute(select(Profile).where(Profile.id == profile_id))
            profile = result.scalar_one_or_none()
            if not profile:
                return
            try:
                profile.resume_embedding = compute_embedding(profile)
                await db.commit()
                logger.info("[embed_profile] profile_id=%d done", profile_id)
                compute_user_matches.delay(profile.user_id)
            except Exception as exc:
                logger.error("[embed_profile] profile_id=%d failed: %s", profile_id, exc)
                raise self.retry(exc=exc, countdown=30)

    _run(_inner())


@celery_app.task(name="app.tasks.embed_tasks.compute_user_matches", bind=True, max_retries=2)
def compute_user_matches(self, user_id: int):
    """Run vector similarity search and upsert match scores for one user."""
    from app.database import task_session
    from app.services.matching import compute_matches

    async def _inner():
        async with task_session() as db:
            count = await compute_matches(user_id, db)
            logger.info("[compute_user_matches] user_id=%d → %d matches", user_id, count)

    try:
        _run(_inner())
    except Exception as exc:
        logger.error("[compute_user_matches] user_id=%d failed: %s", user_id, exc)
        raise self.retry(exc=exc, countdown=60)


# ─────────────────────────────────────────────────────────────────────────────
# Batch tasks (called by admin endpoints or on a schedule)
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.embed_tasks.embed_all_jobs")
def embed_all_jobs(batch_size: int = 200) -> str:
    """
    Find all jobs with no embedding and dispatch individual embed_job tasks.
    Safe to re-run; already-embedded jobs are skipped.
    """
    from app.database import task_session
    from app.models.job import Job
    from sqlalchemy import select

    async def _get_ids() -> list[int]:
        async with task_session() as db:
            result = await db.execute(
                select(Job.id).where(Job.embedding.is_(None)).limit(batch_size)
            )
            return [row.id for row in result.all()]

    ids = _run(_get_ids())
    for job_id in ids:
        embed_job.delay(job_id)

    msg = f"Queued embedding for {len(ids)} jobs (batch_size={batch_size})"
    logger.info(msg)
    return msg


@celery_app.task(name="app.tasks.embed_tasks.embed_all_profiles")
def embed_all_profiles() -> str:
    """
    Find all profiles with no embedding and dispatch individual embed_profile tasks.
    """
    from app.database import task_session
    from app.models.profile import Profile
    from sqlalchemy import select

    async def _get_ids() -> list[int]:
        async with task_session() as db:
            result = await db.execute(
                select(Profile.id).where(Profile.resume_embedding.is_(None))
            )
            return [row.id for row in result.all()]

    ids = _run(_get_ids())
    for profile_id in ids:
        embed_profile.delay(profile_id)

    msg = f"Queued embedding for {len(ids)} profiles"
    logger.info(msg)
    return msg


@celery_app.task(name="app.tasks.embed_tasks.compute_all_user_matches")
def compute_all_user_matches() -> str:
    """
    Dispatch compute_user_matches for every user who has a profile embedding.
    Run this after a bulk job scrape to refresh everyone's matches.
    """
    from app.database import task_session
    from app.models.profile import Profile
    from sqlalchemy import select

    async def _get_user_ids() -> list[int]:
        async with task_session() as db:
            result = await db.execute(
                select(Profile.user_id).where(Profile.resume_embedding.is_not(None))
            )
            return [row.user_id for row in result.all()]

    user_ids = _run(_get_user_ids())
    for user_id in user_ids:
        compute_user_matches.delay(user_id)

    msg = f"Queued match recomputation for {len(user_ids)} users"
    logger.info(msg)
    return msg
