"""Outbound messaging API: send WhatsApp, Telegram, and SMS messages."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import CurrentAgency, DbDep, require_permission
from app.core.rbac import Permission
from app.models.user import User
from app.services.audit import audit

router = APIRouter(prefix="/messaging", tags=["messaging"])


class WhatsAppSendIn(BaseModel):
    to_phone: str
    text: str
    template_name: str | None = None


class TelegramSendIn(BaseModel):
    chat_id: str
    text: str


class SMSSendIn(BaseModel):
    to_phone: str
    body: str


@router.post("/whatsapp")
def send_whatsapp(
    payload: WhatsAppSendIn,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.MATCHES_WRITE))],
):
    from app.services.messaging import send_whatsapp_message
    result = send_whatsapp_message(payload.to_phone, payload.text, template_name=payload.template_name)
    audit(db, agency_id=agency.id, user_id=user.id, action="messaging.whatsapp",
          meta={"to": payload.to_phone, "ok": result.get("ok")})
    db.commit()
    return result


@router.post("/telegram")
def send_telegram(
    payload: TelegramSendIn,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.MATCHES_WRITE))],
):
    from app.services.messaging import send_telegram_message
    result = send_telegram_message(payload.chat_id, payload.text)
    audit(db, agency_id=agency.id, user_id=user.id, action="messaging.telegram",
          meta={"chat_id": payload.chat_id, "ok": result.get("ok")})
    db.commit()
    return result


@router.post("/sms")
def send_sms_endpoint(
    payload: SMSSendIn,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.MATCHES_WRITE))],
):
    from app.services.sms import send_sms
    result = send_sms(payload.to_phone, payload.body)
    audit(db, agency_id=agency.id, user_id=user.id, action="messaging.sms",
          meta={"to": payload.to_phone, "ok": result.get("ok")})
    db.commit()
    return result
