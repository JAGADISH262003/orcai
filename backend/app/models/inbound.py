from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.seeker import Seeker


class InboundMessage(Base, TimestampMixin):
    """Raw messages arriving via WhatsApp / Telegram before they become Seeker records."""

    __tablename__ = "inbound_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)
    channel: Mapped[str] = mapped_column(String(20))  # whatsapp | telegram
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    sender_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    body: Mapped[str] = mapped_column(Text, default="")
    media_paths: Mapped[list[Any]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="received")  # received|parsed|seeker_created|rejected
    seeker_id: Mapped[int | None] = mapped_column(ForeignKey("seekers.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    seeker: Mapped["Seeker | None"] = relationship()
