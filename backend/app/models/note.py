from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.agency import Agency
    from app.models.user import User


class Note(Base, TimestampMixin):
    __tablename__ = "notes"
    __table_args__ = (
        {"info": {"indexes": [("ix_notes_entity", "entity_type", "entity_id")]}},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    content: Mapped[str] = mapped_column(Text)
    is_pinned: Mapped[bool] = mapped_column(default=False)

    agency: Mapped["Agency"] = relationship(back_populates="notes")
    user: Mapped["User"] = relationship()
