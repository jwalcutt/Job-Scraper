"""
Vector similarity search using pgvector ORM operators.
Retrieves top-k jobs for a user profile, applies hard filters,
applies staleness decay and implicit-feedback re-weighting,
and upserts scored results into the matches table.
"""
import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.match import Match
from app.models.profile import Profile, RemotePreference
from app.models.user_event import UserEvent

# Staleness half-life: after this many days, the score decays by 50%
STALENESS_HALF_LIFE_DAYS = 14

# Implicit feedback weights applied to the base cosine score
FEEDBACK_BOOST_APPLIED = 0.05
FEEDBACK_BOOST_VIEWED = 0.02
FEEDBACK_PENALTY_DISMISSED = -0.06


async def compute_matches(user_id: int, db: AsyncSession, top_k: int = 100) -> int:
    """
    Run pgvector cosine similarity search for a user and upsert results.
    Uses SQLAlchemy ORM operators so the embedding is passed as a typed value,
    not a raw string — avoiding asyncpg binding errors.

    Post-processing applies:
    - Staleness decay: fresher jobs score higher (configurable half-life)
    - Salary hard filter: excludes jobs where salary_max < desired_salary_min
    - Implicit feedback: boosts/penalises based on user_events

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
        # Hard filter: exclude jobs where salary_max is known and below minimum
        conditions.append(
            or_(Job.salary_max.is_(None), Job.salary_max >= profile.desired_salary_min)
        )

    # ── Vector search via pgvector ORM cosine_distance operator ──────────────
    # Retrieve more candidates than needed so we can re-score and still fill top_k
    retrieve_k = min(top_k * 2, 500)
    stmt = (
        select(
            Job.id,
            (1 - Job.embedding.cosine_distance(embedding)).label("score"),
            Job.posted_at,
            Job.scraped_at,
        )
        .where(and_(*conditions))
        .order_by(Job.embedding.cosine_distance(embedding))
        .limit(retrieve_k)
    )

    rows = (await db.execute(stmt)).all()

    if not rows:
        return 0

    # ── Load implicit-feedback signals for this user ─────────────────────────
    job_ids = [r[0] for r in rows]
    event_rows = (await db.execute(
        select(UserEvent.job_id, UserEvent.event_type)
        .where(UserEvent.user_id == user_id, UserEvent.job_id.in_(job_ids))
    )).all()

    # Aggregate the strongest signal per job
    feedback: dict[int, float] = {}
    for jid, etype in event_rows:
        weight = {
            "job_applied": FEEDBACK_BOOST_APPLIED,
            "job_viewed": FEEDBACK_BOOST_VIEWED,
            "job_dismissed": FEEDBACK_PENALTY_DISMISSED,
        }.get(etype, 0.0)
        # Keep the max boost or penalty per job
        if jid not in feedback:
            feedback[jid] = weight
        else:
            feedback[jid] = max(feedback[jid], weight) if weight > 0 else min(feedback[jid], weight)

    # ── Apply staleness decay + feedback re-weighting ────────────────────────
    now = datetime.now(timezone.utc)
    scored: list[tuple[int, float]] = []
    for job_id, cosine_score, posted_at, scraped_at in rows:
        base_score = float(cosine_score)

        # Staleness decay: use posted_at if available, fall back to scraped_at
        ref_date = posted_at or scraped_at or now
        if ref_date.tzinfo is None:
            ref_date = ref_date.replace(tzinfo=timezone.utc)
        age_days = max((now - ref_date).total_seconds() / 86400, 0)
        decay = math.pow(0.5, age_days / STALENESS_HALF_LIFE_DAYS)

        # Combine: decayed cosine score + feedback adjustment, clamped to [0, 1]
        final_score = max(0.0, min(1.0, base_score * decay + feedback.get(job_id, 0.0)))
        scored.append((job_id, final_score))

    # Sort by final score descending and take top_k
    scored.sort(key=lambda x: x[1], reverse=True)
    scored = scored[:top_k]

    # ── Upsert matches using PostgreSQL ON CONFLICT ───────────────────────────
    values = [
        {"user_id": user_id, "job_id": job_id, "score": score, "computed_at": now}
        for job_id, score in scored
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

    return len(scored)
