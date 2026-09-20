from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.models.agency_settings import AgencySettings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    email_from_name: str | None = None
    email_from_address: str | None = None
    email_signature: str | None = None
    whatsapp_number: str | None = None
    telegram_bot_token: str | None = None
    default_currency: str | None = None
    timezone: str | None = None
    notification_preferences: dict[str, Any] | None = None
    branding_logo_url: str | None = None
    branding_primary_color: str | None = None


def _get_or_create_settings(db: DbDep, agency_id: int) -> AgencySettings:
    s = db.scalars(select(AgencySettings).where(AgencySettings.agency_id == agency_id)).first()
    if not s:
        s = AgencySettings(agency_id=agency_id)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def _out(s: AgencySettings) -> dict[str, Any]:
    return {
        "id": s.id,
        "agency_id": s.agency_id,
        "email_from_name": s.email_from_name,
        "email_from_address": s.email_from_address,
        "email_signature": s.email_signature,
        "whatsapp_number": s.whatsapp_number,
        "telegram_bot_token": s.telegram_bot_token,
        "default_currency": s.default_currency,
        "timezone": s.timezone,
        "notification_preferences": s.notification_preferences,
        "branding_logo_url": s.branding_logo_url,
        "branding_primary_color": s.branding_primary_color,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


@router.get("")
def get_settings(user: CurrentUser, db: DbDep) -> dict[str, Any]:
    return _out(_get_or_create_settings(db, user.agency_id))


@router.patch("")
def update_settings(data: SettingsUpdate, user: CurrentUser, db: DbDep) -> dict[str, Any]:
    s = _get_or_create_settings(db, user.agency_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return _out(s)
