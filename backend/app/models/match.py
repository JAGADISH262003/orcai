from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.agency import Agency
    from app.models.contract import Contract
    from app.models.offer import Offer
    from app.models.seeker import Seeker
    from app.models.user import User


class Match(Base, TimestampMixin):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("contract_id", "seeker_id", name="uq_match_contract_seeker"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), index=True)
    seeker_id: Mapped[int] = mapped_column(ForeignKey("seekers.id"), index=True)

    score: Mapped[float] = mapped_column(Float, default=0.0)  # 0..100
    tier: Mapped[str] = mapped_column(String(8), default="C")  # A | B | C
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending|approved|rejected|submitted|placed
    hitl_required: Mapped[bool] = mapped_column(default=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)  # AI uncertainty rationale
    hitl_status: Mapped[str | None] = mapped_column(String(20), nullable=True)  # pending_review|approved|rejected
    human_review: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agency: Mapped["Agency"] = relationship(back_populates="matches")
    contract: Mapped["Contract"] = relationship(back_populates="matches")
    seeker: Mapped["Seeker"] = relationship(back_populates="matches")
    reviewer: Mapped[Optional["User"]] = relationship()
    offers: Mapped[list["Offer"]] = relationship(back_populates="match")

    def mark_status(self, status: str) -> None:
        self.status = status
        if status in ("pending",):
            self.hitl_status = "pending_review" if self.hitl_required else None
