from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job import Job
from app.models.match import Application, Match
from app.models.profile import Profile
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


class ApplicationFunnel(BaseModel):
    applied: int = 0
    phone_screen: int = 0
    interview: int = 0
    offer: int = 0
    rejected: int = 0
    withdrawn: int = 0


class WeeklyScore(BaseModel):
    week: str
    avg_score: float
    match_count: int


class TopItem(BaseModel):
    name: str
    count: int


class SkillsGapSummary(BaseModel):
    skill: str
    frequency: int


class AnalyticsResponse(BaseModel):
    application_funnel: ApplicationFunnel
    weekly_scores: list[WeeklyScore]
    top_companies: list[TopItem]
    top_titles: list[TopItem]
    total_matches: int
    avg_match_score: Optional[float]


@router.get("/me", response_model=AnalyticsResponse)
async def get_user_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """User-facing analytics: application funnel, score trends, top matches."""

    # ── Application funnel ───────────────────────────────────────────────────
    funnel_rows = (await db.execute(
        select(Application.status, func.count())
        .where(Application.user_id == current_user.id)
        .group_by(Application.status)
    )).all()
    funnel_dict = {status: count for status, count in funnel_rows}
    funnel = ApplicationFunnel(**{
        k: funnel_dict.get(k, 0) for k in ApplicationFunnel.model_fields
    })

    # ── Weekly match score trend (last 12 weeks) ─────────────────────────────
    twelve_weeks_ago = datetime.now(timezone.utc) - timedelta(weeks=12)
    week_trunc = func.date_trunc("week", Match.computed_at)
    weekly_rows = (await db.execute(
        select(
            week_trunc.label("week"),
            func.avg(Match.score).label("avg_score"),
            func.count().label("match_count"),
        )
        .where(Match.user_id == current_user.id)
        .where(Match.computed_at >= twelve_weeks_ago)
        .group_by(week_trunc)
        .order_by(week_trunc)
    )).all()
    weekly_scores = [
        WeeklyScore(
            week=w.strftime("%Y-%m-%d") if w else "",
            avg_score=round(float(avg), 3),
            match_count=cnt,
        )
        for w, avg, cnt in weekly_rows
    ]

    # ── Top matching companies (by count of matches with score >= 0.5) ───────
    top_companies_rows = (await db.execute(
        select(Job.company, func.count().label("cnt"))
        .join(Match, Match.job_id == Job.id)
        .where(Match.user_id == current_user.id)
        .where(Match.score >= 0.5)
        .group_by(Job.company)
        .order_by(desc("cnt"))
        .limit(10)
    )).all()
    top_companies = [TopItem(name=name, count=cnt) for name, cnt in top_companies_rows]

    # ── Top matching job titles ──────────────────────────────────────────────
    top_titles_rows = (await db.execute(
        select(Job.title, func.count().label("cnt"))
        .join(Match, Match.job_id == Job.id)
        .where(Match.user_id == current_user.id)
        .where(Match.score >= 0.5)
        .group_by(Job.title)
        .order_by(desc("cnt"))
        .limit(10)
    )).all()
    top_titles = [TopItem(name=name, count=cnt) for name, cnt in top_titles_rows]

    # ── Overall stats ────────────────────────────────────────────────────────
    stats = (await db.execute(
        select(func.count(), func.avg(Match.score))
        .where(Match.user_id == current_user.id)
    )).one()
    total_matches = stats[0] or 0
    avg_match_score = round(float(stats[1]), 3) if stats[1] else None

    return AnalyticsResponse(
        application_funnel=funnel,
        weekly_scores=weekly_scores,
        top_companies=top_companies,
        top_titles=top_titles,
        total_matches=total_matches,
        avg_match_score=avg_match_score,
    )
