"""Audit logging for compliance (who did what, when)."""

from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def audit(
    db: Session,
    *,
    agency_id: int,
    user_id: int | None = None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    meta: dict[str, Any] | None = None,
    ip: str | None = None,
) -> None:
    """Record an audit event. Does not commit — callers own their transaction."""
    db.add(
        AuditLog(
            agency_id=agency_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            meta=meta or {},
            ip=ip,
        )
    )
