from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.models.user import User
from app.models.profile import Profile
from app.services.auth import get_current_user, hash_password, verify_password

router = APIRouter(prefix="/users", tags=["users"])


class UserResponse(BaseModel):
    id: int
    email: str

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class NotificationSettings(BaseModel):
    notifications_enabled: bool
    notification_email: Optional[EmailStr] = None
    notification_min_score: float = 0.8


class NotificationSettingsResponse(NotificationSettings):
    model_config = {"from_attributes": True}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/me/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    current_user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"message": "Password updated"}


@router.delete("/me", status_code=204)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently delete the account and all associated data.
    Cascades via FK relationships to profile, matches, saved jobs, applications.
    """
    await db.delete(current_user)
    await db.commit()


@router.get("/me/notifications", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return NotificationSettingsResponse(
        notifications_enabled=profile.notifications_enabled,
        notification_email=profile.notification_email,
        notification_min_score=profile.notification_min_score,
    )


@router.patch("/me/notifications", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    body: NotificationSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if not 0.0 <= body.notification_min_score <= 1.0:
        raise HTTPException(status_code=400, detail="notification_min_score must be between 0 and 1")

    profile.notifications_enabled = body.notifications_enabled
    profile.notification_email = body.notification_email
    profile.notification_min_score = body.notification_min_score
    await db.commit()
    await db.refresh(profile)

    return NotificationSettingsResponse(
        notifications_enabled=profile.notifications_enabled,
        notification_email=profile.notification_email,
        notification_min_score=profile.notification_min_score,
    )
