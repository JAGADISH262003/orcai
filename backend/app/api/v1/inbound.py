import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.deps import CurrentAgency, DbDep
from app.core.config import get_settings
from app.models.agency import Agency
from app.models.inbound import InboundMessage
from app.schemas.inbound import InboundIn, InboundOut
from app.services.inbound import record_inbound
from app.services.jobs import run_handler_inline, submit_job
from app.services.messaging import send_telegram_message, send_whatsapp_message

logger = logging.getLogger("orcai.inbound")

router = APIRouter(prefix="/inbound", tags=["inbound"])
settings = get_settings()


def inbound_out(m: InboundMessage) -> InboundOut:
    return InboundOut(
        id=m.id,
        channel=m.channel,
        sender_name=m.sender_name,
        phone_number=m.phone_number,
        body=m.body,
        status=m.status,
        seeker_id=m.seeker_id,
        received_at=m.received_at,
    )


def _verify_whatsapp(request: Request, raw_body: bytes) -> bool:
    secret = settings.WHATSAPP_APP_SECRET
    if not secret:
        return True  # secret not configured -> dev mode, accept
    signature = request.headers.get("x-hub-signature-256", "")
    expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


def _verify_telegram(request: Request) -> bool:
    secret = settings.TELEGRAM_SECRET_TOKEN
    if not secret:
        return True
    sent = request.headers.get("x-telegram-bot-api-secret-token", "")
    return hmac.compare_digest(sent, secret)


@router.get("", response_model=list[InboundOut])
def list_inbound(db: DbDep, agency: CurrentAgency, channel: str | None = None, status: str | None = None):
    q = db.query(InboundMessage).filter(InboundMessage.agency_id == agency.id)
    if channel:
        q = q.filter(InboundMessage.channel == channel)
    if status:
        q = q.filter(InboundMessage.status == status)
    rows = q.order_by(InboundMessage.received_at.desc()).limit(200).all()
    return [inbound_out(m) for m in rows]


@router.post("/message", status_code=202)
async def ingest_generic(
    payload: InboundIn,
    db: DbDep,
    async_: bool = Query(default=True, alias="async"),
):
    """Public API to simulate inbound from WhatsApp/Telegram/Indeed for an agency slug.
    Ingestion runs as a background job by default."""
    agency = db.query(Agency).filter(Agency.slug == payload.agency_slug).first()
    if agency is None:
        raise HTTPException(status_code=404, detail=f"Unknown agency slug: {payload.agency_slug}")

    params = {
        "agency_id": agency.id,
        "channel": payload.channel,
        "external_id": payload.external_id,
        "phone_number": payload.phone_number,
        "sender_name": payload.sender_name,
        "body": payload.body,
    }
    if async_:
        return submit_job(db, agency_id=agency.id, type_="inbound.ingest", params=params)

    result = await run_handler_inline(db, "inbound.ingest", agency.id, params)
    msg = db.get(InboundMessage, result["inbound_id"])
    return inbound_out(msg)


@router.get("/whatsapp/verify")
def whatsapp_verify(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and settings.WHATSAPP_VERIFY_TOKEN and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return int(hub_challenge or 0)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request, payload: dict[str, Any], db: DbDep):
    if not _verify_whatsapp(request, await request.body()):
        raise HTTPException(status_code=401, detail="Invalid signature")

    agency = db.query(Agency).order_by(Agency.id.asc()).first()
    if agency is None:
        return {"status": "ok", "processed": 0}

    seen = 0
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value", {})
            contacts = value.get("contacts", [])
            for msg in value.get("messages", []) or []:
                name = None
                phone = None
                for c in contacts:
                    phone = c.get("wa_id") or phone
                    prof = c.get("profile", {})
                    name = prof.get("name") or name
                text = ""
                if msg.get("type") == "text":
                    text = msg.get("text", {}).get("body", "")
                if text:
                    record_inbound(db, agency.slug, "whatsapp", msg.get("id"), phone, name, text)
                    seen += 1
                    # Send acknowledgement reply
                    if phone:
                        try:
                            send_whatsapp_message(phone, f"Thanks for reaching out, {name or 'there'}! We've received your message and will get back to you shortly.")
                        except Exception:
                            logger.warning("Failed to send WhatsApp acknowledgement to %s", phone)
    return {"status": "ok", "processed": seen}


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request, payload: dict[str, Any], db: DbDep):
    if not _verify_telegram(request):
        raise HTTPException(status_code=401, detail="Invalid secret token")

    message = payload.get("message", {})
    text = message.get("text", "")
    sender = message.get("from", {})
    name = f"{sender.get('first_name', '')} {sender.get('last_name', '')}".strip() or None
    chat_id = message.get("chat", {}).get("id")
    agency = db.query(Agency).order_by(Agency.id.asc()).first()
    if agency and text:
        record_inbound(db, agency.slug, "telegram", str(chat_id), str(chat_id), name, text)
        # Send acknowledgement reply
        if chat_id:
            try:
                send_telegram_message(str(chat_id), f"Thanks for reaching out, {name or 'there'}! We've received your message and will get back to you shortly.")
            except Exception:
                logger.warning("Failed to send Telegram acknowledgement to %s", chat_id)
    return {"status": "ok"}
