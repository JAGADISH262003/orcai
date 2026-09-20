from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.agency import Agency
    from app.models.client import Client
    from app.models.match import Match
    from app.models.user import User


class ClientPortalSession(Base, TimestampMixin):
    __tablename__ = "client_portal_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True)
    last_accessed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    agency: Mapped["Agency"] = relationship()
    client: Mapped["Client"] = relationship()
    feedbacks: Mapped[list["ClientFeedback"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class ClientFeedback(Base, TimestampMixin):
    __tablename__ = "client_feedbacks"
    __table_args__ = (
        UniqueConstraint("client_id", "match_id", name="uq_client_feedback_match"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("client_portal_sessions.id"), nullable=True, index=True
    )
    rating: Mapped[int] = mapped_column()
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending|reviewed|accepted|rejected
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    agency: Mapped["Agency"] = relationship()
    client: Mapped["Client"] = relationship()
    match: Mapped["Match"] = relationship()
    reviewer: Mapped["User | None"] = relationship()
    session: Mapped["ClientPortalSession | None"] = relationship(
        back_populates="feedbacks"
    )
