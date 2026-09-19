from datetime import date
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.match import Match


class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"), nullable=True, index=True)

    # Raw source text (pasted contract / requisition)
    raw_text: Mapped[str] = mapped_column(Text, default="")

    # Parsed / structured fields (populated by the AI or deterministic extractor)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # draft|active|filled|closed
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    is_remote: Mapped[bool | None] = mapped_column(nullable=True)
    duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rate_bill: Mapped[float | None] = mapped_column(Float, nullable=True)  # client bill rate
    rate_pay: Mapped[float | None] = mapped_column(Float, nullable=True)  # candidate pay rate
    currency: Mapped[str] = mapped_column(String(8), default="USD")  # USD | INR
    experience_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    openings: Mapped[int] = mapped_column(Integer, default=1)
    start_by: Mapped[date | None] = mapped_column(nullable=True)
    skills: Mapped[list[Any]] = mapped_column(JSON, default=list)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_method: Mapped[str | None] = mapped_column(String(30), nullable=True)  # ai|deterministic

    client: Mapped[Optional["Client"]] = relationship(back_populates="contracts")
    matches: Mapped[list["Match"]] = relationship(back_populates="contract", cascade="all, delete-orphan")
