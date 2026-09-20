"""Audit log viewing endpoint and subscription enforcement."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Query
from sqlalchemy import func

from app.api.deps import CurrentAgency, DbDep
from app.models.audit import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit_logs(
    db: DbDep,
    agency: CurrentAgency,
    action: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
):
    q = db.query(AuditLog).filter(AuditLog.agency_id == agency.id)
    if action:
        q = q.filter(AuditLog.action == action)
    rows = q.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "action": log.action,
            "user_id": log.user_id,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "meta": log.meta,
            "ip": log.ip,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in rows
    ]


@router.get("/stats")
def audit_stats(db: DbDep, agency: CurrentAgency):

    week_ago = datetime.now(UTC) - timedelta(days=7)
    total = db.query(func.count(AuditLog.id)).filter(AuditLog.agency_id == agency.id).scalar() or 0
    this_week = (
        db.query(func.count(AuditLog.id))
        .filter(AuditLog.agency_id == agency.id, AuditLog.created_at >= week_ago)
        .scalar()
        or 0
    )
    actions = (
        db.query(AuditLog.action, func.count(AuditLog.id))
        .filter(AuditLog.agency_id == agency.id)
        .group_by(AuditLog.action)
        .all()
    )
    return {
        "total_events": total,
        "events_this_week": this_week,
        "by_action": {a: c for a, c in actions},
    }
