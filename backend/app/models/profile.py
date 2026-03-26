from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, Enum, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
import enum

from app.config import settings
from app.database import Base


class RemotePreference(str, enum.Enum):
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ONSITE = "ONSITE"
    ANY = "ANY"


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    location: Mapped[Optional[str]] = mapped_column(String(255))
    remote_preference: Mapped[RemotePreference] = mapped_column(
        Enum(RemotePreference), default=RemotePreference.ANY
    )

    desired_titles: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    desired_salary_min: Mapped[Optional[int]] = mapped_column(Integer)
    desired_salary_max: Mapped[Optional[int]] = mapped_column(Integer)
    years_experience: Mapped[Optional[int]] = mapped_column(Integer)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    resume_text: Mapped[Optional[str]] = mapped_column(Text)
    resume_embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(settings.embedding_dim), nullable=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="profile")
