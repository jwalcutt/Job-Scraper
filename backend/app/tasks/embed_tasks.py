"""
Celery tasks for embedding generation and match computation.
"""
import asyncio
from app.tasks.worker import celery_app


def _run(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.embed_tasks.embed_profile")
def embed_profile(profile_id: int):
    """Recompute embedding for a profile, then trigger match computation."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.database import AsyncSessionLocal
    from app.models.profile import Profile
    from app.services.embedding import embed_profile as compute_profile_embedding
    from sqlalchemy import select

    async def _inner():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Profile).where(Profile.id == profile_id))
            profile = result.scalar_one_or_none()
            if not profile:
                return

            profile.resume_embedding = compute_profile_embedding(profile)
            await db.commit()

            # Trigger match computation for this user
            compute_user_matches.delay(profile.user_id)

    _run(_inner())


@celery_app.task(name="app.tasks.embed_tasks.embed_job")
def embed_job(job_id: int):
    """Compute and store embedding for a single job."""
    from app.database import AsyncSessionLocal
    from app.models.job import Job
    from app.services.embedding import embed_job as compute_job_embedding
    from sqlalchemy import select

    async def _inner():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return
            job.embedding = compute_job_embedding(job)
            await db.commit()

    _run(_inner())


@celery_app.task(name="app.tasks.embed_tasks.compute_user_matches")
def compute_user_matches(user_id: int):
    """Run vector similarity search and upsert match scores."""
    from app.database import AsyncSessionLocal
    from app.services.matching import compute_matches

    async def _inner():
        async with AsyncSessionLocal() as db:
            await compute_matches(user_id, db)

    _run(_inner())
