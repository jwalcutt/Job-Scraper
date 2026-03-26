from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.profile import Profile, RemotePreference
from app.services.auth import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    full_name: Optional[str]
    location: Optional[str]
    remote_preference: RemotePreference
    desired_titles: list[str]
    desired_salary_min: Optional[int]
    desired_salary_max: Optional[int]
    years_experience: Optional[int]
    skills: list[str]
    has_resume: bool

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    location: Optional[str] = None
    remote_preference: Optional[RemotePreference] = None
    desired_titles: Optional[list[str]] = None
    desired_salary_min: Optional[int] = None
    desired_salary_max: Optional[int] = None
    years_experience: Optional[int] = None
    skills: Optional[list[str]] = None


@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return ProfileResponse(
        **{c: getattr(profile, c) for c in ProfileResponse.model_fields if c != "has_resume"},
        has_resume=bool(profile.resume_text),
    )


@router.patch("", response_model=ProfileResponse)
async def update_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)

    return ProfileResponse(
        **{c: getattr(profile, c) for c in ProfileResponse.model_fields if c != "has_resume"},
        has_resume=bool(profile.resume_text),
    )


@router.post("/resume")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF or DOCX resume. Text is extracted and stored; embedding is queued."""
    if file.content_type not in ("application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    content = await file.read()

    # Lazy import to avoid loading these at startup
    if file.content_type == "application/pdf":
        from app.services.resume_parser import extract_text_from_pdf
        text = extract_text_from_pdf(content)
    else:
        from app.services.resume_parser import extract_text_from_docx
        text = extract_text_from_docx(content)

    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile.resume_text = text
    profile.resume_embedding = None  # Will be recomputed by worker
    await db.commit()

    # Queue embedding task
    from app.tasks.embed_tasks import embed_profile
    embed_profile.delay(profile.id)

    return {"message": "Resume uploaded successfully", "characters": len(text)}
