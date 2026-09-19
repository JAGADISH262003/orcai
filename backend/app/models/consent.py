from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.seeker import Seeker


class ConsentRecord(Base, TimestampMixin):
    __tablename__ = "consent_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)
    seeker_id: Mapped[int] = mapped_column(ForeignKey("seekers.id"), index=True)

    basis: Mapped[str] = mapped_column(String(40), default="explicit_opt_in")  # explicit_opt_in|affidavit|implied
    channel: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|withdrawn|erased
    consent_given_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retention_days: Mapped[int] = mapped_column(Integer, default=30)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    erased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    seeker: Mapped["Seeker"] = relationship(back_populates="consents")
