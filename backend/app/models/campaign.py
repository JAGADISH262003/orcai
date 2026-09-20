from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.agency import Agency
    from app.models.seeker import Seeker


class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="draft"
    )  # draft|active|paused|completed|cancelled
    channel: Mapped[str] = mapped_column(
        String(20), default="email"
    )  # email|whatsapp|telegram|sms
    template_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    template_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_count: Mapped[int] = mapped_column(default=0)
    sent_count: Mapped[int] = mapped_column(default=0)
    opened_count: Mapped[int] = mapped_column(default=0)
    replied_count: Mapped[int] = mapped_column(default=0)

    agency: Mapped["Agency"] = relationship()
    recipients: Mapped[list["CampaignRecipient"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class CampaignRecipient(Base, TimestampMixin):
    __tablename__ = "campaign_recipients"

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    seeker_id: Mapped[int] = mapped_column(ForeignKey("seekers.id"), index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="queued"
    )  # queued|sent|delivered|opened|replied|bounced|unsubscribed
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(nullable=True)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    agency: Mapped["Agency"] = relationship()
    campaign: Mapped["Campaign"] = relationship(back_populates="recipients")
    seeker: Mapped["Seeker"] = relationship()
