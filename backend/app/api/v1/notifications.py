from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select, update

from app.api.deps import CurrentUser, DbDep
from app.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _out(n: Notification) -> dict[str, Any]:
    return {
        "id": n.id,
        "title": n.title,
        "message": n.message,
        "notification_type": n.notification_type,
        "is_read": n.is_read,
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "related_entity_type": n.related_entity_type,
        "related_entity_id": n.related_entity_id,
        "action_url": n.action_url,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("")
def list_notifications(
    user: CurrentUser,
    db: DbDep,
    unread_only: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    q = select(Notification).where(Notification.agency_id == user.agency_id)
    if user.role not in ("owner", "admin"):
        q = q.where(Notification.user_id == user.id)
    if unread_only:
        q = q.where(Notification.is_read == False)  # noqa: E712
    q = q.order_by(Notification.created_at.desc()).limit(limit)
    return [_out(n) for n in db.scalars(q).all()]


@router.get("/unread-count")
def unread_count(user: CurrentUser, db: DbDep) -> dict[str, int]:
    q = select(func.count(Notification.id)).where(
        Notification.agency_id == user.agency_id,
        Notification.is_read == False,  # noqa: E712
    )
    if user.role not in ("owner", "admin"):
        q = q.where(Notification.user_id == user.id)
    count = db.scalar(q) or 0
    return {"count": count}


@router.patch("/{notification_id}/read")
def mark_read(notification_id: int, user: CurrentUser, db: DbDep) -> dict[str, str]:
    n = db.get(Notification, notification_id)
    if not n or n.agency_id != user.agency_id:
        raise HTTPException(404, "Notification not found")
    n.is_read = True
    n.read_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.post("/read-all")
def mark_all_read(user: CurrentUser, db: DbDep) -> dict[str, str]:
    now = datetime.utcnow()
    stmt = (
        update(Notification)
        .where(
            Notification.agency_id == user.agency_id,
            Notification.is_read == False,  # noqa: E712
        )
        .values(is_read=True, read_at=now)
    )
    db.execute(stmt)
    db.commit()
    return {"ok": True}
