from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.agency import Agency


class AgencySettings(Base, TimestampMixin):
    __tablename__ = "agency_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), unique=True)

    email_from_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email_from_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_signature: Mapped[str | None] = mapped_column(Text, nullable=True)

    whatsapp_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    telegram_bot_token: Mapped[str | None] = mapped_column(String(200), nullable=True)

    default_currency: Mapped[str] = mapped_column(String(8), default="USD")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    notification_preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    branding_logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    branding_primary_color: Mapped[str] = mapped_column(String(7), default="#5e6ad2")

    agency: Mapped["Agency"] = relationship(back_populates="settings_rel")
