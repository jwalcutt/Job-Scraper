"""Job alerts — saved searches that trigger periodic email digests."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job_alert import JobAlert
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])

MAX_ALERTS_PER_USER = 20


class AlertCreate(BaseModel):
    title: Optional[str] = None
    location: Optional[str] = None
    remote: Optional[bool] = None
    min_score: float = 0.6


class AlertResponse(BaseModel):
    id: int
    title: Optional[str]
    location: Optional[str]
    remote: Optional[bool]
    min_score: float
    is_active: bool
    last_alerted_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JobAlert)
        .where(JobAlert.user_id == current_user.id)
        .order_by(JobAlert.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=AlertResponse, status_code=201)
async def create_alert(
    body: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = (await db.execute(
        select(JobAlert.id).where(JobAlert.user_id == current_user.id)
    )).all()
    if len(count) >= MAX_ALERTS_PER_USER:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_ALERTS_PER_USER} alerts allowed")

    alert = JobAlert(
        user_id=current_user.id,
        title=body.title,
        location=body.location,
        remote=body.remote,
        min_score=body.min_score,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JobAlert).where(JobAlert.id == alert_id, JobAlert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.delete(alert)
    await db.commit()
    return {"deleted": True}


@router.patch("/{alert_id}", response_model=AlertResponse)
async def toggle_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle an alert's active state."""
    result = await db.execute(
        select(JobAlert).where(JobAlert.id == alert_id, JobAlert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_active = not alert.is_active
    await db.commit()
    await db.refresh(alert)
    return alert
