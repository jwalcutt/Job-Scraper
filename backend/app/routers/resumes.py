"""Resume versioning — store multiple resume versions with independent embeddings."""
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.profile import Profile
from app.models.resume import Resume
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/profile/resumes", tags=["resumes"])

MAX_RESUMES_PER_USER = 10


class ResumeResponse(BaseModel):
    id: int
    label: str
    is_active: bool
    has_embedding: bool
    character_count: int
    uploaded_at: datetime

    model_config = {"from_attributes": True}


def _to_response(r: Resume) -> ResumeResponse:
    return ResumeResponse(
        id=r.id,
        label=r.label,
        is_active=r.is_active,
        has_embedding=r.embedding is not None,
        character_count=len(r.resume_text),
        uploaded_at=r.uploaded_at,
    )


@router.get("", response_model=list[ResumeResponse])
async def list_resumes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(Resume.uploaded_at.desc())
    )
    return [_to_response(r) for r in result.scalars().all()]


@router.post("", response_model=ResumeResponse, status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    label: str = "Default",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a new resume version. PDF and DOCX are supported."""
    if file.content_type not in (
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    count = (await db.execute(
        select(Resume.id).where(Resume.user_id == current_user.id)
    )).all()
    if len(count) >= MAX_RESUMES_PER_USER:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_RESUMES_PER_USER} resumes allowed")

    content = await file.read()

    if file.content_type == "application/pdf":
        from app.services.resume_parser import extract_text_from_pdf
        text = extract_text_from_pdf(content)
    else:
        from app.services.resume_parser import extract_text_from_docx
        text = extract_text_from_docx(content)

    resume = Resume(
        user_id=current_user.id,
        label=label,
        resume_text=text,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    # Queue embedding
    from app.tasks.embed_tasks import embed_resume
    embed_resume.delay(resume.id)

    return _to_response(resume)


@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    was_active = resume.is_active
    await db.delete(resume)
    await db.commit()

    # If the deleted resume was active, sync the profile: clear resume data
    if was_active:
        profile_result = await db.execute(
            select(Profile).where(Profile.user_id == current_user.id)
        )
        profile = profile_result.scalar_one_or_none()
        if profile:
            profile.resume_text = None
            profile.resume_embedding = None
            await db.commit()

    return {"deleted": True}


@router.patch("/{resume_id}/activate", response_model=ResumeResponse)
async def activate_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set a resume as the active one used for matching. Deactivates all others."""
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Deactivate all other resumes for this user
    all_resumes = await db.execute(
        select(Resume).where(Resume.user_id == current_user.id)
    )
    for r in all_resumes.scalars().all():
        r.is_active = r.id == resume_id

    # Sync the activated resume's text and embedding into the profile
    profile_result = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile:
        profile.resume_text = resume.resume_text
        profile.resume_embedding = resume.embedding

    await db.commit()
    await db.refresh(resume)

    # Recompute matches if the profile embedding changed
    if profile and resume.embedding is not None:
        from app.tasks.embed_tasks import compute_user_matches
        compute_user_matches.delay(current_user.id)

    return _to_response(resume)
