"""
Celery tasks for email digest notifications.
Finds users with notifications enabled and new matches above their threshold
since their last notification, then sends a digest email.
"""
import asyncio
import logging
from datetime import datetime, timezone

from app.tasks.worker import celery_app

logger = logging.getLogger(__name__)


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.notification_tasks.send_digest_for_user")
def send_digest_for_user(user_id: int) -> str:
    """
    Send a match digest email to a single user if they have new matches
    above their notification threshold since last_notified_at.
    """
    from app.database import AsyncSessionLocal
    from app.models.profile import Profile
    from app.models.match import Match
    from app.models.job import Job
    from app.models.user import User
    from app.services.notifications import send_match_digest
    from sqlalchemy import select, desc, and_

    async def _inner() -> str:
        async with AsyncSessionLocal() as db:
            # Load user + profile
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if not user:
                return f"user {user_id} not found"

            profile_result = await db.execute(select(Profile).where(Profile.user_id == user_id))
            profile = profile_result.scalar_one_or_none()
            if not profile or not profile.notifications_enabled:
                return f"notifications disabled for user {user_id}"

            # Find matches above threshold, newer than last notification
            conditions = [
                Match.user_id == user_id,
                Match.score >= profile.notification_min_score,
            ]
            if profile.last_notified_at:
                conditions.append(Match.computed_at > profile.last_notified_at)

            rows = (await db.execute(
                select(Match, Job)
                .join(Job, Job.id == Match.job_id)
                .where(and_(*conditions))
                .order_by(desc(Match.score))
                .limit(10)
            )).all()

            if not rows:
                return f"no new matches for user {user_id}"

            matches_data = [
                {
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "score": match.score,
                    "url": job.url,
                    "explanation": match.explanation,
                }
                for match, job in rows
            ]

            to_email = profile.notification_email or user.email
            sent = send_match_digest(
                to_email=to_email,
                matches=matches_data,
                user_name=profile.full_name,
            )

            if sent:
                profile.last_notified_at = datetime.now(timezone.utc)
                await db.commit()
                return f"digest sent to {to_email} ({len(matches_data)} matches)"
            else:
                return f"digest skipped (SMTP not configured or send failed)"

    return _run(_inner())


@celery_app.task(name="app.tasks.notification_tasks.send_all_digests")
def send_all_digests() -> str:
    """
    Fan out digest tasks to all users who have notifications enabled.
    Called by Celery Beat after the daily match recompute settles.
    """
    from app.database import AsyncSessionLocal
    from app.models.profile import Profile
    from sqlalchemy import select

    async def _get_user_ids() -> list[int]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Profile.user_id).where(Profile.notifications_enabled == True)
            )
            return [row.user_id for row in result.all()]

    user_ids = _run(_get_user_ids())
    for uid in user_ids:
        send_digest_for_user.delay(uid)

    msg = f"Queued digest for {len(user_ids)} users"
    logger.info(msg)
    return msg
