from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.agency import Agency
    from app.models.consent import ConsentRecord
    from app.models.match import Match
    from app.models.offer import Offer


class Seeker(Base, TimestampMixin):
    __tablename__ = "seekers"
    __table_args__ = (UniqueConstraint("agency_id", "dedupe_key", name="uq_agency_seeker_dedupe"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)

    # Identity
    name: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    dedupe_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    visa_status: Mapped[str | None] = mapped_column(String(60), nullable=True)  # H1B|OPT|GC EAD|Citizen...
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    headline: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Profile
    skills: Mapped[list[Any]] = mapped_column(JSON, default=list)
    experience_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    education: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Sourcing
    source: Mapped[str] = mapped_column(String(30), default="manual", index=True)  # manual|import|inbound|apollo
    source_channel: Mapped[str | None] = mapped_column(String(60), nullable=True)  # whatsapp|telegram|indeed|file
    resume_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_method: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Trust / compliance
    is_verified: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)

    agency: Mapped["Agency"] = relationship(back_populates="seekers")
    matches: Mapped[list["Match"]] = relationship(back_populates="seeker", cascade="all, delete-orphan")
    offers: Mapped[list["Offer"]] = relationship(back_populates="seeker", cascade="all, delete-orphan")
    consents: Mapped[list["ConsentRecord"]] = relationship(back_populates="seeker", cascade="all, delete-orphan")
