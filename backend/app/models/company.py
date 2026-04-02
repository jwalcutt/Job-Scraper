"""Company registry model — tracks career page URLs and ATS types."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    careers_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    # Detected ATS type: workday, icims, greenhouse, lever, taleo, successfactors, generic
    ats_type: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    logo_url: Mapped[Optional[str]] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
