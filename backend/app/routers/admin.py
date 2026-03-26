"""
Admin endpoints for manually triggering scrapes and inspecting task status.
In production, protect these behind an API key or restrict to internal network.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(x_admin_key: Optional[str] = Header(default=None)):
    if x_admin_key != settings.admin_key:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Key header")


class JobSpyRequest(BaseModel):
    search_term: str = "software engineer"
    location: str = "United States"
    results_wanted: int = 50


class GreenhouseRequest(BaseModel):
    companies: Optional[list[str]] = None  # None = use full default list


class LeverRequest(BaseModel):
    companies: Optional[list[str]] = None


@router.post("/scrape/all", dependencies=[Depends(require_admin)])
def trigger_scrape_all():
    """Trigger all scraper tasks (Greenhouse + Lever + JobSpy from profiles)."""
    from app.tasks.scrape_tasks import scrape_all_sources
    result = scrape_all_sources.delay()
    return {"task_id": result.id, "status": "queued", "description": "all sources"}


@router.post("/scrape/greenhouse", dependencies=[Depends(require_admin)])
def trigger_scrape_greenhouse(body: GreenhouseRequest = GreenhouseRequest()):
    """Trigger Greenhouse scraper, optionally limited to specific company tokens."""
    from app.tasks.scrape_tasks import scrape_greenhouse
    result = scrape_greenhouse.delay(companies=body.companies)
    n = len(body.companies) if body.companies else "all"
    return {"task_id": result.id, "status": "queued", "companies": n}


@router.post("/scrape/lever", dependencies=[Depends(require_admin)])
def trigger_scrape_lever(body: LeverRequest = LeverRequest()):
    """Trigger Lever scraper, optionally limited to specific company slugs."""
    from app.tasks.scrape_tasks import scrape_lever
    result = scrape_lever.delay(companies=body.companies)
    n = len(body.companies) if body.companies else "all"
    return {"task_id": result.id, "status": "queued", "companies": n}


@router.post("/scrape/jobspy", dependencies=[Depends(require_admin)])
def trigger_scrape_jobspy(body: JobSpyRequest = JobSpyRequest()):
    """Trigger a single JobSpy search."""
    from app.tasks.scrape_tasks import scrape_jobspy
    result = scrape_jobspy.delay(
        search_term=body.search_term,
        location=body.location,
        results_wanted=body.results_wanted,
    )
    return {"task_id": result.id, "status": "queued", "search_term": body.search_term}


@router.post("/scrape/jobspy/profiles", dependencies=[Depends(require_admin)])
def trigger_scrape_jobspy_profiles():
    """Trigger JobSpy searches derived from all user profile desired_titles."""
    from app.tasks.scrape_tasks import scrape_jobspy_all_profiles
    result = scrape_jobspy_all_profiles.delay()
    return {"task_id": result.id, "status": "queued", "description": "profile-driven jobspy"}


@router.get("/scrape/status/{task_id}", dependencies=[Depends(require_admin)])
def get_task_status(task_id: str):
    """Poll the status of a Celery task by its ID."""
    from app.tasks.worker import celery_app
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": str(result.result) if result.ready() else None,
    }


@router.get("/stats", dependencies=[Depends(require_admin)])
async def get_stats():
    """Return high-level counts for jobs, profiles, matches."""
    from app.database import AsyncSessionLocal
    from app.models.job import Job
    from app.models.profile import Profile
    from app.models.match import Match
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as db:
        job_count = (await db.execute(select(func.count()).select_from(Job))).scalar()
        profile_count = (await db.execute(select(func.count()).select_from(Profile))).scalar()
        match_count = (await db.execute(select(func.count()).select_from(Match))).scalar()
        embedded_jobs = (await db.execute(
            select(func.count()).select_from(Job).where(Job.embedding.is_not(None))
        )).scalar()
        embedded_profiles = (await db.execute(
            select(func.count()).select_from(Profile).where(Profile.resume_embedding.is_not(None))
        )).scalar()

    return {
        "jobs": {"total": job_count, "embedded": embedded_jobs, "pending_embed": job_count - embedded_jobs},
        "profiles": {"total": profile_count, "embedded": embedded_profiles},
        "matches": match_count,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Embedding & match endpoints
# ─────────────────────────────────────────────────────────────────────────────

class EmbedJobsRequest(BaseModel):
    batch_size: int = 200


@router.post("/embed/jobs/backfill", dependencies=[Depends(require_admin)])
def trigger_embed_jobs_backfill(body: EmbedJobsRequest = EmbedJobsRequest()):
    """
    Dispatch embed_job tasks for all jobs that are missing embeddings.
    Safe to re-run; already-embedded jobs are skipped.
    Processes up to batch_size jobs per call; call again to continue.
    """
    from app.tasks.embed_tasks import embed_all_jobs
    result = embed_all_jobs.delay(batch_size=body.batch_size)
    return {"task_id": result.id, "status": "queued", "batch_size": body.batch_size}


@router.post("/embed/profiles/backfill", dependencies=[Depends(require_admin)])
def trigger_embed_profiles_backfill():
    """Dispatch embed_profile tasks for all profiles missing embeddings."""
    from app.tasks.embed_tasks import embed_all_profiles
    result = embed_all_profiles.delay()
    return {"task_id": result.id, "status": "queued"}


@router.post("/matches/recompute", dependencies=[Depends(require_admin)])
def trigger_recompute_all_matches():
    """
    Recompute match scores for every user who has a profile embedding.
    Run this after a bulk scrape + embed cycle to refresh all feeds.
    """
    from app.tasks.embed_tasks import compute_all_user_matches
    result = compute_all_user_matches.delay()
    return {"task_id": result.id, "status": "queued"}
