"""Job alert model — saved searches that trigger email digests."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobAlert(Base):
    __tablename__ = "job_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Saved search criteria
    title: Mapped[Optional[str]] = mapped_column(String(255))
    location: Mapped[Optional[str]] = mapped_column(String(255))
    remote: Mapped[Optional[bool]] = mapped_column()
    min_score: Mapped[float] = mapped_column(Float, default=0.6)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_alerted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="job_alerts")  # noqa: F821
