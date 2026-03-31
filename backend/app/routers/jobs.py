import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job import Job
from app.models.match import Match, SavedJob
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/jobs", tags=["jobs"])

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


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
    explanation: Optional[str] = None
    description_preview: Optional[str] = None

    model_config = {"from_attributes": True}


class SkillsGapResponse(BaseModel):
    matching: list[str]
    missing: list[str]


def _strip_html(s: str) -> str:
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", s)).strip()


def _build_job_response(
    job: Job,
    score: Optional[float] = None,
    explanation: Optional[str] = None,
) -> JobResponse:
    preview = None
    if job.description:
        text_clean = _strip_html(job.description)
        preview = text_clean[:300] + ("…" if len(text_clean) > 300 else "")

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


# ─────────────────────────────────────────────────────────────────────────────
# Matches
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/matches", response_model=list[JobResponse])
async def get_matches(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
    title: Optional[str] = Query(default=None, description="Filter by job title (partial match)"),
    company: Optional[str] = Query(default=None, description="Filter by company name (partial match)"),
    remote: Optional[bool] = Query(default=None, description="Filter remote / onsite"),
    source: Optional[str] = Query(default=None, description="Filter by source (greenhouse, lever, jobspy_indeed, …)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the user's top matched jobs with optional keyword filters."""
    stmt = (
        select(Job, Match.score, Match.explanation)
        .join(Match, Match.job_id == Job.id)
        .where(Match.user_id == current_user.id)
        .where(Match.score >= min_score)
    )

    if title:
        stmt = stmt.where(Job.title.ilike(f"%{title}%"))
    if company:
        stmt = stmt.where(Job.company.ilike(f"%{company}%"))
    if remote is not None:
        stmt = stmt.where(Job.is_remote == remote)
    if source:
        stmt = stmt.where(Job.source == source)

    stmt = stmt.order_by(desc(Match.score)).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).all()
    return [_build_job_response(job, score, explanation) for job, score, explanation in rows]


@router.get("/matches/status")
async def get_matches_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tell the frontend whether the user's embedding + matches are ready."""
    from app.models.profile import Profile

    profile_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()

    match_count = (await db.execute(
        select(func.count()).select_from(Match).where(Match.user_id == current_user.id)
    )).scalar()

    explained_count = (await db.execute(
        select(func.count()).select_from(Match)
        .where(Match.user_id == current_user.id)
        .where(Match.explanation.is_not(None))
    )).scalar()

    return {
        "has_embedding": profile is not None and profile.resume_embedding is not None,
        "match_count": match_count,
        "explained_count": explained_count,
        "profile_complete": bool(
            profile and (profile.resume_text or profile.desired_titles or profile.skills)
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Full-text search across all jobs
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/search", response_model=list[JobResponse])
async def search_jobs(
    q: str = Query(min_length=2, description="Search query"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    remote: Optional[bool] = Query(default=None),
    source: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Full-text search across all jobs using PostgreSQL tsvector.
    Returns jobs ranked by text relevance (ts_rank). Not personalised.
    """
    # plainto_tsquery is safer than to_tsquery — handles arbitrary user input
    tsvector = func.to_tsvector(
        "english",
        func.concat(
            func.coalesce(Job.title, ""), " ",
            func.coalesce(Job.company, ""), " ",
            func.coalesce(Job.description, ""),
        ),
    )
    tsquery = func.plainto_tsquery("english", q)

    stmt = (
        select(Job, func.ts_rank(tsvector, tsquery).label("rank"))
        .where(tsvector.op("@@")(tsquery))
    )

    if remote is not None:
        stmt = stmt.where(Job.is_remote == remote)
    if source:
        stmt = stmt.where(Job.source == source)

    stmt = stmt.order_by(desc("rank")).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).all()

    # Attach the user's match score if one exists
    job_ids = [job.id for job, _ in rows]
    match_scores: dict[int, tuple[float, Optional[str]]] = {}
    if job_ids:
        match_rows = (await db.execute(
            select(Match.job_id, Match.score, Match.explanation)
            .where(Match.user_id == current_user.id)
            .where(Match.job_id.in_(job_ids))
        )).all()
        match_scores = {jid: (score, explanation) for jid, score, explanation in match_rows}

    return [
        _build_job_response(job, *match_scores.get(job.id, (None, None)))
        for job, _ in rows
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Saved jobs
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Single job
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Single job detail — includes full description_preview (up to 300 chars)."""
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    match_result = await db.execute(
        select(Match).where(Match.user_id == current_user.id, Match.job_id == job_id)
    )
    match = match_result.scalar_one_or_none()
    return _build_job_response(
        job,
        match.score if match else None,
        match.explanation if match else None,
    )


@router.get("/{job_id}/skills-gap", response_model=SkillsGapResponse)
async def get_skills_gap(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compare the user's skills to a job's requirements via Claude.
    Returns matching and missing skills. Requires ANTHROPIC_API_KEY.
    """
    from app.models.profile import Profile
    from app.services.llm import skills_gap

    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    profile_result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = skills_gap(profile, job)
    return SkillsGapResponse(**result)


# ─────────────────────────────────────────────────────────────────────────────
# Save / unsave
# ─────────────────────────────────────────────────────────────────────────────

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
