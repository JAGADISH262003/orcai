import secrets
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.core.rbac import role_has
from app.core.security import hash_password
from app.models.user import User

router = APIRouter(prefix="/team", tags=["team"])


class TeamUpdateIn(BaseModel):
    name: str | None = None
    role: str | None = None
    is_active: bool | None = None


def _out(u: User) -> dict[str, Any]:
    return {
        "id": u.id,
        "email": u.email,
        "name": u.name,
        "role": u.role,
        "phone": u.phone,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@router.get("")
def list_team(user: CurrentUser, db: DbDep) -> list[dict[str, Any]]:
    q = select(User).where(User.agency_id == user.agency_id).order_by(User.created_at)
    return [_out(u) for u in db.scalars(q).all()]


@router.patch("/{user_id}")
def update_team_member(
    user_id: int, data: TeamUpdateIn, user: CurrentUser, db: DbDep
) -> dict[str, Any]:
    if not role_has(user.role, "teams.manage"):
        raise HTTPException(403, "Insufficient permissions")
    target = db.get(User, user_id)
    if not target or target.agency_id != user.agency_id:
        raise HTTPException(404, "User not found")
    if data.name is not None:
        target.name = data.name
    if data.role is not None:
        if data.role not in ("owner", "admin", "recruiter", "client"):
            raise HTTPException(400, "Invalid role")
        target.role = data.role
    if data.is_active is not None:
        target.is_active = data.is_active
    db.commit()
    db.refresh(target)
    return _out(target)


@router.post("/{user_id}/reset-password")
def reset_team_password(user_id: int, user: CurrentUser, db: DbDep) -> dict[str, str]:
    if not role_has(user.role, "teams.manage"):
        raise HTTPException(403, "Insufficient permissions")
    target = db.get(User, user_id)
    if not target or target.agency_id != user.agency_id:
        raise HTTPException(404, "User not found")
    temp_password = secrets.token_urlsafe(16)
    target.hashed_password = hash_password(temp_password)
    db.commit()

    # Send email with new temp password
    from app.services.email_delivery import send_invite_email
    send_invite_email(
        to_email=target.email,
        agency_name="ORCAI",
        role=target.role,
        temp_password=temp_password,
    )

    return {"temp_password": temp_password}
