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
    # Match-specific fields (null when fetching saved jobs without a match)
    score: Optional[float] = None
    explanation: Optional[str] = None
    # First 300 chars of description for the feed preview
    description_preview: Optional[str] = None

    model_config = {"from_attributes": True}


def _build_job_response(job: Job, score: Optional[float] = None, explanation: Optional[str] = None) -> JobResponse:
    preview = None
    if job.description:
        # Strip HTML tags crudely; good enough for a short preview
        import re
        text = re.sub(r"<[^>]+>", " ", job.description)
        text = re.sub(r"\s+", " ", text).strip()
        preview = text[:300] + ("…" if len(text) > 300 else "")

    return JobResponse(
        id=job.id,
        company=job.company,
        title=job.title,
        location=job.location,
        is_remote=job.is_remote,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        url=job.url,
        source=job.source,
        posted_at=job.posted_at,
        score=score,
        explanation=explanation,
        description_preview=preview,
    )


@router.get("/matches", response_model=list[JobResponse])
async def get_matches(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0, description="Minimum match score (0–1)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the user's top matched jobs, ordered by descending score."""
    stmt = (
        select(Job, Match.score, Match.explanation)
        .join(Match, Match.job_id == Job.id)
        .where(Match.user_id == current_user.id)
        .where(Match.score >= min_score)
        .order_by(desc(Match.score))
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(stmt)).all()
    return [_build_job_response(job, score, explanation) for job, score, explanation in rows]


@router.get("/matches/status")
async def get_matches_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return metadata about the user's match state — useful for the frontend to know if matches are ready."""
    from sqlalchemy import func
    from app.models.profile import Profile

    profile_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()

    match_count = (await db.execute(
        select(func.count()).select_from(Match).where(Match.user_id == current_user.id)
    )).scalar()

    return {
        "has_embedding": profile is not None and profile.resume_embedding is not None,
        "match_count": match_count,
        "profile_complete": bool(
            profile
            and (profile.resume_text or profile.desired_titles or profile.skills)
        ),
    }


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
    return [_build_job_response(job) for job in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single job with full description (for a detail view)."""
    from fastapi import HTTPException

    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    match_result = await db.execute(
        select(Match).where(Match.user_id == current_user.id, Match.job_id == job_id)
    )
    match = match_result.scalar_one_or_none()
    return _build_job_response(job, match.score if match else None, match.explanation if match else None)


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
