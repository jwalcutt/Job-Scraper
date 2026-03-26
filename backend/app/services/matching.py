"""
Vector similarity search using pgvector.
Retrieves top-k jobs for a user profile, applies hard filters,
and optionally re-ranks with LLM explanations.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.models.profile import Profile, RemotePreference
from app.models.job import Job
from app.models.match import Match


async def compute_matches(user_id: int, db: AsyncSession, top_k: int = 100) -> list[Match]:
    """
    Run vector similarity search for a user and upsert results into matches table.
    Called by the Celery embed_tasks worker after profile embedding is updated.
    """
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = result.scalar_one_or_none()

    if not profile or profile.resume_embedding is None:
        return []

    # Build WHERE clause for hard filters
    filters = ["j.scraped_at > NOW() - INTERVAL '30 days'"]

    if profile.remote_preference == RemotePreference.REMOTE:
        filters.append("j.is_remote = true")
    elif profile.remote_preference == RemotePreference.ONSITE:
        filters.append("j.is_remote = false")

    if profile.desired_salary_min:
        filters.append(f"(j.salary_max IS NULL OR j.salary_max >= {profile.desired_salary_min})")

    where_clause = " AND ".join(filters)

    # pgvector cosine distance: <=> operator; lower = more similar
    sql = text(f"""
        SELECT j.id, 1 - (j.embedding <=> :embedding) AS score
        FROM jobs j
        WHERE j.embedding IS NOT NULL
          AND {where_clause}
        ORDER BY j.embedding <=> :embedding
        LIMIT :top_k
    """)

    rows = (await db.execute(sql, {"embedding": str(profile.resume_embedding), "top_k": top_k})).all()

    # Upsert matches
    matches = []
    for job_id, score in rows:
        existing = (await db.execute(
            select(Match).where(Match.user_id == user_id, Match.job_id == job_id)
        )).scalar_one_or_none()

        if existing:
            existing.score = float(score)
            existing.computed_at = datetime.now(timezone.utc)
            matches.append(existing)
        else:
            m = Match(user_id=user_id, job_id=job_id, score=float(score))
            db.add(m)
            matches.append(m)

    await db.commit()
    return matches
