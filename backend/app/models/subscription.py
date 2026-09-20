from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.agency import Agency


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)
    tier: Mapped[str] = mapped_column(String(20))  # starter|growth|scale
    price_per_month: Mapped[float] = mapped_column(Float, default=0.0)
    billing_cycle_start: Mapped[date] = mapped_column(Date)
    billing_cycle_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|trialing|past_due|cancelled
    seats: Mapped[int] = mapped_column(Integer, default=1)

    agency: Mapped["Agency"] = relationship(back_populates="subscriptions")
