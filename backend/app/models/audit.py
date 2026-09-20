from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.agency import Agency
    from app.models.user import User


class AuditLog(Base, TimestampMixin):
    """Immutable-ish audit trail for compliance (who did what, when)."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_agency_created", "agency_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    action: Mapped[str] = mapped_column(String(80), index=True)  # auth.login, contract.create, ...
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)

    agency: Mapped["Agency"] = relationship(back_populates="audit_logs")
    user: Mapped["User | None"] = relationship()
