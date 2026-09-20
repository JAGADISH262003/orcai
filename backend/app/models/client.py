from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.agency import Agency


class Client(Base, TimestampMixin):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    agency: Mapped["Agency"] = relationship(back_populates="clients")
    contracts = relationship("Contract", back_populates="client", cascade="all, delete-orphan")
