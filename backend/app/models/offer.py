from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.agency import Agency
    from app.models.contract import Contract
    from app.models.match import Match
    from app.models.seeker import Seeker
    from app.models.user import User


class Offer(Base, TimestampMixin):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), index=True)
    seeker_id: Mapped[int] = mapped_column(ForeignKey("seekers.id"), index=True)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id"), nullable=True, index=True)

    status: Mapped[str] = mapped_column(
        String(30), default="draft", index=True
    )  # draft|pending_approval|approved|sent|accepted|rejected|expired|withdrawn

    offered_salary: Mapped[float | None] = mapped_column(nullable=True)
    offered_currency: Mapped[str] = mapped_column(String(8), default="USD")
    start_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    offer_expiry: Mapped[str | None] = mapped_column(String(30), nullable=True)
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agency: Mapped["Agency"] = relationship(back_populates="offers")
    contract: Mapped["Contract"] = relationship(back_populates="offers")
    seeker: Mapped["Seeker"] = relationship(back_populates="offers")
    match: Mapped[Optional["Match"]] = relationship(back_populates="offers")
    approver: Mapped[Optional["User"]] = relationship()
    approvals: Mapped[list["OfferApproval"]] = relationship(
        back_populates="offer", cascade="all, delete-orphan"
    )


class OfferApproval(Base, TimestampMixin):
    __tablename__ = "offer_approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"), index=True)
    approver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending|approved|rejected
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    offer: Mapped["Offer"] = relationship(back_populates="approvals")
    approver: Mapped["User"] = relationship()
