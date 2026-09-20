from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.models.activity import Activity

router = APIRouter(prefix="/activity", tags=["activity"])


class ActivityIn(BaseModel):
    entity_type: str
    entity_id: int
    action: str
    details: dict[str, Any] = {}


def _out(a: Activity) -> dict[str, Any]:
    return {
        "id": a.id,
        "agency_id": a.agency_id,
        "user_id": a.user_id,
        "entity_type": a.entity_type,
        "entity_id": a.entity_id,
        "action": a.action,
        "details": a.details,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("")
def list_activities(
    user: CurrentUser,
    db: DbDep,
    entity_type: str | None = None,
    entity_id: int | None = None,
    action: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    q = select(Activity).where(Activity.agency_id == user.agency_id)
    if entity_type:
        q = q.where(Activity.entity_type == entity_type)
    if entity_id:
        q = q.where(Activity.entity_id == entity_id)
    if action:
        q = q.where(Activity.action == action)
    q = q.order_by(Activity.created_at.desc()).limit(limit).offset(offset)
    return [_out(r) for r in db.scalars(q).all()]


@router.post("/log", status_code=201)
def log_activity(
    data: ActivityIn,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, Any]:
    activity = Activity(
        agency_id=user.agency_id,
        user_id=user.id,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        action=data.action,
        details=data.details,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return _out(activity)
