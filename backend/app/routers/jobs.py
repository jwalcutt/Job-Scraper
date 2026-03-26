from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.match import Match, SavedJob
from app.services.auth import get_current_user

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobResponse(BaseModel):
    id: int
    company: str
    title: str
    location: Optional[str]
    is_remote: bool
    salary_min: Optional[int]
    salary_max: Optional[int]
    url: Optional[str]
    source: str
    posted_at: Optional[datetime]
    score: Optional[float] = None

    model_config = {"from_attributes": True}


@router.get("/matches", response_model=list[JobResponse])
async def get_matches(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the user's top matched jobs, ordered by score."""
    result = await db.execute(
        select(Job, Match.score)
        .join(Match, Match.job_id == Job.id)
        .where(Match.user_id == current_user.id)
        .order_by(desc(Match.score))
        .limit(limit)
        .offset(offset)
    )
    rows = result.all()
    return [JobResponse(**{**{c: getattr(job, c) for c in JobResponse.model_fields if c != "score"}, "score": score}) for job, score in rows]


@router.get("/saved", response_model=list[JobResponse])
async def get_saved_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Job)
        .join(SavedJob, SavedJob.job_id == Job.id)
        .where(SavedJob.user_id == current_user.id)
        .order_by(desc(SavedJob.saved_at))
    )
    jobs = result.scalars().all()
    return [JobResponse(**{c: getattr(j, c) for c in JobResponse.model_fields if c != "score"}) for j in jobs]


@router.post("/{job_id}/save")
async def save_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavedJob).where(SavedJob.user_id == current_user.id, SavedJob.job_id == job_id)
    )
    if not result.scalar_one_or_none():
        db.add(SavedJob(user_id=current_user.id, job_id=job_id))
        await db.commit()
    return {"saved": True}


@router.delete("/{job_id}/save")
async def unsave_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SavedJob).where(SavedJob.user_id == current_user.id, SavedJob.job_id == job_id)
    )
    saved = result.scalar_one_or_none()
    if saved:
        await db.delete(saved)
        await db.commit()
    return {"saved": False}
