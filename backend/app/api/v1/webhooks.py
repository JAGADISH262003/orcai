"""Webhook management API: CRUD, test, and delivery history."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.api.deps import CurrentAgency, DbDep, require_permission
from app.core.rbac import Permission
from app.models.user import User
from app.models.webhook import Webhook, WebhookDelivery
from app.services.audit import audit

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

EVENT_TYPES = [
    "contract.created",
    "contract.status_changed",
    "match.created",
    "match.status_changed",
    "offer.sent",
    "seeker.created",
    "seeker.updated",
    "interview.scheduled",
    "interview.completed",
    "invoice.created",
]


class WebhookCreateIn(BaseModel):
    name: str
    url: str
    secret: str
    events: list[str] = []
    is_active: bool = True


class WebhookUpdateIn(BaseModel):
    name: str | None = None
    url: str | None = None
    secret: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None


class WebhookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agency_id: int
    name: str
    url: str
    events: list[str]
    is_active: bool
    last_triggered_at: str | None = None
    failure_count: int


class DeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    webhook_id: int
    event_type: str
    payload: dict
    response_status: int | None = None
    response_body: str | None = None
    delivered_at: str | None = None
    duration_ms: int | None = None


@router.get("/event-types")
def list_event_types():
    return {"events": EVENT_TYPES}


@router.get("", response_model=list[WebhookOut])
def list_webhooks(
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.SETTINGS_WRITE))],
):
    webhooks = db.query(Webhook).filter(Webhook.agency_id == agency.id).all()
    return [
        WebhookOut(
            id=wh.id,
            agency_id=wh.agency_id,
            name=wh.name,
            url=wh.url,
            events=wh.events or [],
            is_active=wh.is_active,
            last_triggered_at=wh.last_triggered_at.isoformat() if wh.last_triggered_at else None,
            failure_count=wh.failure_count,
        )
        for wh in webhooks
    ]


@router.post("", response_model=WebhookOut)
def create_webhook(
    payload: WebhookCreateIn,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.SETTINGS_WRITE))],
):
    wh = Webhook(
        agency_id=agency.id,
        name=payload.name,
        url=payload.url,
        secret=payload.secret,
        events=payload.events,
        is_active=payload.is_active,
    )
    db.add(wh)
    db.flush()
    audit(db, agency_id=agency.id, user_id=user.id, action="webhook.created", meta={"webhook_id": wh.id})
    db.commit()
    db.refresh(wh)
    return WebhookOut(
        id=wh.id,
        agency_id=wh.agency_id,
        name=wh.name,
        url=wh.url,
        events=wh.events or [],
        is_active=wh.is_active,
        last_triggered_at=None,
        failure_count=0,
    )


@router.patch("/{webhook_id}", response_model=WebhookOut)
def update_webhook(
    webhook_id: int,
    payload: WebhookUpdateIn,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.SETTINGS_WRITE))],
):
    wh = db.query(Webhook).filter(Webhook.id == webhook_id, Webhook.agency_id == agency.id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(wh, field, value)
    db.flush()
    audit(db, agency_id=agency.id, user_id=user.id, action="webhook.updated", meta={"webhook_id": wh.id})
    db.commit()
    db.refresh(wh)
    return WebhookOut(
        id=wh.id,
        agency_id=wh.agency_id,
        name=wh.name,
        url=wh.url,
        events=wh.events or [],
        is_active=wh.is_active,
        last_triggered_at=wh.last_triggered_at.isoformat() if wh.last_triggered_at else None,
        failure_count=wh.failure_count,
    )


@router.delete("/{webhook_id}")
def delete_webhook(
    webhook_id: int,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.SETTINGS_WRITE))],
):
    wh = db.query(Webhook).filter(Webhook.id == webhook_id, Webhook.agency_id == agency.id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(wh)
    audit(db, agency_id=agency.id, user_id=user.id, action="webhook.deleted", meta={"webhook_id": webhook_id})
    db.commit()
    return {"ok": True}


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.SETTINGS_WRITE))],
):
    wh = db.query(Webhook).filter(Webhook.id == webhook_id, Webhook.agency_id == agency.id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")

    from app.services.webhook_dispatch import _deliver

    test_payload = {"event": "webhook.test", "agency_id": agency.id, "timestamp": "now"}
    result = await _deliver(wh, "webhook.test", test_payload, db)
    db.commit()
    return result


@router.get("/{webhook_id}/deliveries", response_model=list[DeliveryOut])
def list_deliveries(
    webhook_id: int,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.SETTINGS_WRITE))],
):
    wh = db.query(Webhook).filter(Webhook.id == webhook_id, Webhook.agency_id == agency.id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")

    deliveries = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.id.desc())
        .limit(50)
        .all()
    )
    return [
        DeliveryOut(
            id=d.id,
            webhook_id=d.webhook_id,
            event_type=d.event_type,
            payload=d.payload or {},
            response_status=d.response_status,
            response_body=d.response_body,
            delivered_at=d.delivered_at.isoformat() if d.delivered_at else None,
            duration_ms=d.duration_ms,
        )
        for d in deliveries
    ]
