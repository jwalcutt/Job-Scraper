"""
Vector similarity search using pgvector ORM operators.
Retrieves top-k jobs for a user profile, applies hard filters,
and upserts scored results into the matches table.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.match import Match
from app.models.profile import Profile, RemotePreference


async def compute_matches(user_id: int, db: AsyncSession, top_k: int = 100) -> int:
    """
    Run pgvector cosine similarity search for a user and upsert results.
    Uses SQLAlchemy ORM operators so the embedding is passed as a typed value,
    not a raw string — avoiding asyncpg binding errors.

    Returns the number of matches upserted.
    """
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = result.scalar_one_or_none()

    if not profile or profile.resume_embedding is None:
        return 0

    embedding = profile.resume_embedding  # list[float] stored by pgvector

    # ── Hard filters ─────────────────────────────────────────────────────────
    cutoff = datetime.now(timezone.utc) - timedelta(days=60)
    conditions = [
        Job.embedding.is_not(None),
        Job.scraped_at > cutoff,
    ]

    if profile.remote_preference == RemotePreference.REMOTE:
        conditions.append(Job.is_remote.is_(True))
    elif profile.remote_preference == RemotePreference.ONSITE:
        conditions.append(Job.is_remote.is_(False))

    if profile.desired_salary_min:
        # Allow jobs with no salary info OR jobs where max salary meets minimum
        conditions.append(
            or_(Job.salary_max.is_(None), Job.salary_max >= profile.desired_salary_min)
        )

    # ── Vector search via pgvector ORM cosine_distance operator ──────────────
    # cosine_distance returns 0 (identical) → 2 (opposite); score = 1 - distance
    stmt = (
        select(
            Job.id,
            (1 - Job.embedding.cosine_distance(embedding)).label("score"),
        )
        .where(and_(*conditions))
        .order_by(Job.embedding.cosine_distance(embedding))
        .limit(top_k)
    )

    rows = (await db.execute(stmt)).all()

    if not rows:
        return 0

    # ── Upsert matches using PostgreSQL ON CONFLICT ───────────────────────────
    now = datetime.now(timezone.utc)
    values = [
        {"user_id": user_id, "job_id": job_id, "score": float(score), "computed_at": now}
        for job_id, score in rows
    ]

    upsert_stmt = (
        pg_insert(Match)
        .values(values)
        .on_conflict_do_update(
            constraint="uq_matches_user_job",
            set_={"score": pg_insert(Match).excluded.score, "computed_at": now},
        )
    )
    await db.execute(upsert_stmt)
    await db.commit()

    return len(rows)
