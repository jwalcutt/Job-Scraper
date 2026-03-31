from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job import Job
from app.models.match import Application, SavedJob
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/applications", tags=["applications"])

APPLICATION_STATUSES = ["applied", "phone_screen", "interview", "offer", "rejected", "withdrawn"]


class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    applied_at: datetime
    status: str
    notes: Optional[str]
    # Denormalised job fields so the frontend doesn't need a second request
    job_title: str
    job_company: str
    job_location: Optional[str]
    job_is_remote: bool
    job_url: Optional[str]
    job_salary_min: Optional[int]
    job_salary_max: Optional[int]

    model_config = {"from_attributes": True}


class ApplyRequest(BaseModel):
    notes: Optional[str] = None


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


def _build_response(app: Application, job: Job) -> ApplicationResponse:
    return ApplicationResponse(
        id=app.id,
        job_id=app.job_id,
        applied_at=app.applied_at,
        status=app.status,
        notes=app.notes,
        job_title=job.title,
        job_company=job.company,
        job_location=job.location,
        job_is_remote=job.is_remote,
        job_url=job.url,
        job_salary_min=job.salary_min,
        job_salary_max=job.salary_max,
    )


@router.get("", response_model=list[ApplicationResponse])
async def list_applications(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all applications for the current user, optionally filtered by status."""
    stmt = (
        select(Application, Job)
        .join(Job, Job.id == Application.job_id)
        .where(Application.user_id == current_user.id)
    )
    if status:
        stmt = stmt.where(Application.status == status)
    stmt = stmt.order_by(desc(Application.applied_at))
    rows = (await db.execute(stmt)).all()
    return [_build_response(app, job) for app, job in rows]


@router.post("/{job_id}", response_model=ApplicationResponse, status_code=201)
async def apply_to_job(
    job_id: int,
    body: ApplyRequest = ApplyRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record that the user has applied to a job. Idempotent — returns existing if already applied."""
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = (await db.execute(
        select(Application).where(
            Application.user_id == current_user.id,
            Application.job_id == job_id,
        )
    )).scalar_one_or_none()

    if existing:
        return _build_response(existing, job)

    app = Application(
        user_id=current_user.id,
        job_id=job_id,
        status="applied",
        notes=body.notes,
    )
    db.add(app)

    # Auto-save the job too if not already saved
    saved = (await db.execute(
        select(SavedJob).where(SavedJob.user_id == current_user.id, SavedJob.job_id == job_id)
    )).scalar_one_or_none()
    if not saved:
        db.add(SavedJob(user_id=current_user.id, job_id=job_id))

    await db.commit()
    await db.refresh(app)
    return _build_response(app, job)


@router.patch("/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: int,
    body: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update status or notes on an application."""
    result = await db.execute(
        select(Application, Job)
        .join(Job, Job.id == Application.job_id)
        .where(Application.id == application_id, Application.user_id == current_user.id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")

    app, job = row

    if body.status is not None:
        if body.status not in APPLICATION_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(APPLICATION_STATUSES)}",
            )
        app.status = body.status

    if body.notes is not None:
        app.notes = body.notes

    await db.commit()
    await db.refresh(app)
    return _build_response(app, job)


@router.delete("/{application_id}", status_code=204)
async def delete_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an application record."""
    result = await db.execute(
        select(Application).where(
            Application.id == application_id,
            Application.user_id == current_user.id,
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    await db.delete(app)
    await db.commit()
