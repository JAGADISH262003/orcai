from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.agency import Agency
    from app.models.contract import Contract
    from app.models.match import Match
    from app.models.seeker import Seeker


class Interview(Base, TimestampMixin):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), index=True)
    seeker_id: Mapped[int] = mapped_column(ForeignKey("seekers.id"), index=True)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id"), nullable=True, index=True)

    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    interview_type: Mapped[str] = mapped_column(String(30), default="video")
    status: Mapped[str] = mapped_column(String(20), default="scheduled")

    interviewer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    interviewer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    meeting_link: Mapped[str | None] = mapped_column(String(500), nullable=True)

    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(30), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    agency: Mapped["Agency"] = relationship(back_populates="interviews")
    contract: Mapped["Contract"] = relationship()
    seeker: Mapped["Seeker"] = relationship()
    match: Mapped[Optional["Match"]] = relationship()
