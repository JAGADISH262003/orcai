from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    """Return current UTC time as a naive datetime.

    SQLite stores naive datetimes so comparisons require naive on both sides.
    PostgreSQL ``DateTime(timezone=True)`` columns accept naive UTC values and
    the ``server_default=func.now()`` still supplies a proper timestamptz.
    """
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now()
    )
