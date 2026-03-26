"""
Celery tasks for LLM-powered features:
  - Generate match explanations for a user's top-N matches
  - Re-rank + explain a user's matches via Claude
  - Batch explanation generation across all users
"""
import asyncio
import logging
from app.tasks.worker import celery_app

logger = logging.getLogger(__name__)


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.llm_tasks.explain_matches_for_user", bind=True, max_retries=2)
def explain_matches_for_user(self, user_id: int, top_k: int = 10, force: bool = False):
    """
    Generate one-sentence explanations for a user's top-k matches and
    persist them in matches.explanation.

    Args:
        user_id: Target user.
        top_k:   How many top matches to explain (default 10 to control API cost).
        force:   If True, overwrite existing explanations.
    """
    from app.database import AsyncSessionLocal
    from app.models.match import Match
    from app.models.job import Job
    from app.models.profile import Profile
    from app.services.llm import match_explanation
    from sqlalchemy import select, desc, and_

    async def _inner() -> str:
        async with AsyncSessionLocal() as db:
            profile_result = await db.execute(
                select(Profile).where(Profile.user_id == user_id)
            )
            profile = profile_result.scalar_one_or_none()
            if not profile:
                return "No profile found"

            conditions = [Match.user_id == user_id]
            if not force:
                conditions.append(Match.explanation.is_(None))

            match_rows = (await db.execute(
                select(Match, Job)
                .join(Job, Job.id == Match.job_id)
                .where(and_(*conditions))
                .order_by(desc(Match.score))
                .limit(top_k)
            )).all()

            count = 0
            for match, job in match_rows:
                explanation = match_explanation(profile, job)
                if explanation:
                    match.explanation = explanation
                    count += 1

            await db.commit()
            return f"Generated {count} explanations for user_id={user_id}"

    try:
        msg = _run(_inner())
        logger.info("[explain_matches] %s", msg)
        return msg
    except Exception as exc:
        logger.error("[explain_matches] user_id=%d: %s", user_id, exc)
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="app.tasks.llm_tasks.rerank_matches_for_user", bind=True, max_retries=2)
def rerank_matches_for_user(self, user_id: int, top_k: int = 20):
    """
    Re-rank a user's top-k matches using Claude and update scores + explanations.
    The re-ranking overwrites match scores with LLM-informed ranks (normalised 0–1).
    """
    from app.database import AsyncSessionLocal
    from app.models.match import Match
    from app.models.job import Job
    from app.models.profile import Profile
    from app.services.llm import rerank_and_explain
    from sqlalchemy import select, desc

    async def _inner() -> str:
        async with AsyncSessionLocal() as db:
            profile_result = await db.execute(
                select(Profile).where(Profile.user_id == user_id)
            )
            profile = profile_result.scalar_one_or_none()
            if not profile:
                return "No profile found"

            rows = (await db.execute(
                select(Match, Job)
                .join(Job, Job.id == Match.job_id)
                .where(Match.user_id == user_id)
                .order_by(desc(Match.score))
                .limit(top_k)
            )).all()

            if not rows:
                return "No matches to re-rank"

            jobs_with_scores = [(job, match.score) for match, job in rows]
            reranked = rerank_and_explain(profile, jobs_with_scores)

            # Normalise rank → score: rank 1 gets 1.0, last gets (n-k+1)/n
            n = len(reranked)
            match_by_job_id = {match.job_id: match for match, _ in rows}

            for item in reranked:
                match = match_by_job_id.get(item["job_id"])
                if match:
                    # Blend: 70% original vector score + 30% rank-based score
                    rank_score = (n - item["rank"] + 1) / n
                    match.score = round(0.7 * item["score"] + 0.3 * rank_score, 4)
                    if item.get("explanation"):
                        match.explanation = item["explanation"]

            await db.commit()
            return f"Re-ranked {n} matches for user_id={user_id}"

    try:
        msg = _run(_inner())
        logger.info("[rerank_matches] %s", msg)
        return msg
    except Exception as exc:
        logger.error("[rerank_matches] user_id=%d: %s", user_id, exc)
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="app.tasks.llm_tasks.explain_all_users")
def explain_all_users(top_k: int = 10, force: bool = False) -> str:
    """
    Dispatch explain_matches_for_user for every user who has matches.
    Called by the admin endpoint or on a schedule.
    """
    from app.database import AsyncSessionLocal
    from app.models.match import Match
    from sqlalchemy import select, distinct

    async def _get_user_ids() -> list[int]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(distinct(Match.user_id)))
            return [row[0] for row in result.all()]

    user_ids = _run(_get_user_ids())
    for uid in user_ids:
        explain_matches_for_user.delay(uid, top_k=top_k, force=force)

    msg = f"Queued explanation tasks for {len(user_ids)} users"
    logger.info(msg)
    return msg


@celery_app.task(name="app.tasks.llm_tasks.rerank_all_users")
def rerank_all_users(top_k: int = 20) -> str:
    """Dispatch rerank_matches_for_user for every user who has matches."""
    from app.database import AsyncSessionLocal
    from app.models.match import Match
    from sqlalchemy import select, distinct

    async def _get_user_ids() -> list[int]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(distinct(Match.user_id)))
            return [row[0] for row in result.all()]

    user_ids = _run(_get_user_ids())
    for uid in user_ids:
        rerank_matches_for_user.delay(uid, top_k=top_k)

    return f"Queued re-rank tasks for {len(user_ids)} users"
