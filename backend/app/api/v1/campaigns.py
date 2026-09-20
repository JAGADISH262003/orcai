"""Sourcing Campaigns API — CRUD, start/pause, recipients, analytics."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import CurrentAgency, DbDep, require_permission
from app.core.rbac import Permission
from app.models.campaign import Campaign, CampaignRecipient
from app.models.seeker import Seeker
from app.models.user import User
from app.schemas.campaign import (
    AddRecipientsIn,
    CampaignAnalyticsOut,
    CampaignIn,
    CampaignOut,
    CampaignRecipientOut,
    CampaignUpdateIn,
)
from app.services.audit import audit
from app.services.jobs import submit_job

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _campaign_to_out(c: Campaign) -> CampaignOut:
    return CampaignOut.model_validate(c)


def _recipient_to_out(r: CampaignRecipient, db: Session) -> CampaignRecipientOut:
    seeker = db.get(Seeker, r.seeker_id)
    return CampaignRecipientOut(
        id=r.id,
        agency_id=r.agency_id,
        campaign_id=r.campaign_id,
        seeker_id=r.seeker_id,
        status=r.status,
        sent_at=r.sent_at,
        opened_at=r.opened_at,
        replied_at=r.replied_at,
        response_text=r.response_text,
        created_at=r.created_at,
        seeker_name=seeker.name if seeker else None,
        seeker_email=seeker.email if seeker else None,
    )


@router.get("", response_model=list[CampaignOut])
def list_campaigns(
    db: DbDep,
    agency: CurrentAgency,
    status: str | None = Query(default=None),
    channel: str | None = Query(default=None),
):
    q = db.query(Campaign).filter(Campaign.agency_id == agency.id)
    if status:
        q = q.filter(Campaign.status == status)
    if channel:
        q = q.filter(Campaign.channel == channel)
    return [_campaign_to_out(c) for c in q.order_by(Campaign.created_at.desc()).all()]


@router.post("", response_model=CampaignOut, status_code=201)
def create_campaign(
    payload: CampaignIn,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.SEEKERS_WRITE))],
):
    campaign = Campaign(
        agency_id=agency.id,
        name=payload.name,
        description=payload.description,
        channel=payload.channel,
        template_subject=payload.template_subject,
        template_body=payload.template_body,
        status="draft",
    )
    db.add(campaign)
    audit(db, agency_id=agency.id, user_id=user.id, action="campaign.create",
          entity_type="campaign", entity_id=campaign.id)
    db.commit()
    db.refresh(campaign)
    return _campaign_to_out(campaign)


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, db: DbDep, agency: CurrentAgency):
    c = db.get(Campaign, campaign_id)
    if c is None or c.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign_to_out(c)


@router.patch("/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    campaign_id: int,
    payload: CampaignUpdateIn,
    db: DbDep,
    agency: CurrentAgency,
):
    c = db.get(Campaign, campaign_id)
    if c is None or c.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if c.status not in ("draft", "paused"):
        raise HTTPException(status_code=400, detail="Can only update draft or paused campaigns")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return _campaign_to_out(c)


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: int, db: DbDep, agency: CurrentAgency):
    c = db.get(Campaign, campaign_id)
    if c is None or c.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if c.status in ("active",):
        raise HTTPException(status_code=400, detail="Cannot delete active campaign. Pause or cancel first.")
    db.delete(c)
    db.commit()


@router.post("/{campaign_id}/start", response_model=CampaignOut)
def start_campaign(
    campaign_id: int,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.SEEKERS_WRITE))],
):
    c = db.get(Campaign, campaign_id)
    if c is None or c.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if c.status not in ("draft", "paused"):
        raise HTTPException(status_code=400, detail="Campaign is not in a startable state")
    if not c.template_body:
        raise HTTPException(status_code=400, detail="Campaign must have a template body")

    # Queue all recipients
    recipients = (
        db.query(CampaignRecipient)
        .filter(
            CampaignRecipient.campaign_id == campaign_id,
            CampaignRecipient.status == "queued",
        )
        .all()
    )
    c.target_count = len(recipients)
    c.status = "active"

    audit(db, agency_id=agency.id, user_id=user.id, action="campaign.start",
          entity_type="campaign", entity_id=campaign_id,
          meta={"target_count": c.target_count})
    db.commit()
    db.refresh(c)

    # Dispatch messages in background
    submit_job(db, agency_id=agency.id, type_="campaign.send",
               params={"campaign_id": campaign_id})

    return _campaign_to_out(c)


@router.post("/{campaign_id}/pause", response_model=CampaignOut)
def pause_campaign(
    campaign_id: int,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.SEEKERS_WRITE))],
):
    c = db.get(Campaign, campaign_id)
    if c is None or c.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if c.status != "active":
        raise HTTPException(status_code=400, detail="Campaign is not active")

    c.status = "paused"
    audit(db, agency_id=agency.id, user_id=user.id, action="campaign.pause",
          entity_type="campaign", entity_id=campaign_id)
    db.commit()
    db.refresh(c)
    return _campaign_to_out(c)


@router.post("/{campaign_id}/recipients/add", response_model=list[CampaignRecipientOut])
def add_recipients(
    campaign_id: int,
    payload: AddRecipientsIn,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.SEEKERS_WRITE))],
):
    c = db.get(Campaign, campaign_id)
    if c is None or c.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if c.status not in ("draft", "paused"):
        raise HTTPException(status_code=400, detail="Can only add recipients to draft or paused campaigns")

    existing_ids = {
        r.seeker_id
        for r in db.query(CampaignRecipient.seeker_id)
        .filter(CampaignRecipient.campaign_id == campaign_id)
        .all()
    }

    added = []
    for seeker_id in payload.seeker_ids:
        if seeker_id in existing_ids:
            continue
        seeker = db.get(Seeker, seeker_id)
        if seeker is None or seeker.agency_id != agency.id:
            continue
        recipient = CampaignRecipient(
            agency_id=agency.id,
            campaign_id=campaign_id,
            seeker_id=seeker_id,
            status="queued",
        )
        db.add(recipient)
        added.append(recipient)

    if added:
        c.target_count = len(
            db.query(CampaignRecipient)
            .filter(CampaignRecipient.campaign_id == campaign_id)
            .all()
        )

    audit(db, agency_id=agency.id, user_id=user.id, action="campaign.recipients.add",
          entity_type="campaign", entity_id=campaign_id,
          meta={"added": len(added)})
    db.commit()

    for r in added:
        db.refresh(r)

    return [_recipient_to_out(r, db) for r in added]


@router.get("/{campaign_id}/recipients", response_model=list[CampaignRecipientOut])
def list_recipients(
    campaign_id: int,
    db: DbDep,
    agency: CurrentAgency,
):
    c = db.get(Campaign, campaign_id)
    if c is None or c.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Campaign not found")

    recipients = (
        db.query(CampaignRecipient)
        .filter(CampaignRecipient.campaign_id == campaign_id)
        .order_by(CampaignRecipient.created_at.desc())
        .all()
    )
    return [_recipient_to_out(r, db) for r in recipients]


@router.get("/{campaign_id}/analytics", response_model=CampaignAnalyticsOut)
def get_campaign_analytics(
    campaign_id: int,
    db: DbDep,
    agency: CurrentAgency,
):
    c = db.get(Campaign, campaign_id)
    if c is None or c.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Campaign not found")

    recipients = (
        db.query(CampaignRecipient)
        .filter(CampaignRecipient.campaign_id == campaign_id)
        .all()
    )

    status_breakdown: dict[str, int] = {}
    for r in recipients:
        status_breakdown[r.status] = status_breakdown.get(r.status, 0) + 1

    open_rate = (c.opened_count / c.sent_count * 100) if c.sent_count > 0 else 0.0
    reply_rate = (c.replied_count / c.sent_count * 100) if c.sent_count > 0 else 0.0

    # Build daily timeline from recipients
    from collections import defaultdict

    daily: dict[str, dict[str, int]] = defaultdict(lambda: {"sent": 0, "opened": 0, "replied": 0})
    for r in recipients:
        if r.sent_at:
            day = r.sent_at.strftime("%Y-%m-%d")
            daily[day]["sent"] += 1
        if r.opened_at:
            day = r.opened_at.strftime("%Y-%m-%d")
            daily[day]["opened"] += 1
        if r.replied_at:
            day = r.replied_at.strftime("%Y-%m-%d")
            daily[day]["replied"] += 1

    timeline = [
        {"date": day, **counts}
        for day, counts in sorted(daily.items())
    ]

    return CampaignAnalyticsOut(
        campaign_id=c.id,
        name=c.name,
        status=c.status,
        channel=c.channel,
        target_count=c.target_count,
        sent_count=c.sent_count,
        opened_count=c.opened_count,
        replied_count=c.replied_count,
        bounced_count=status_breakdown.get("bounced", 0),
        unsubscribed_count=status_breakdown.get("unsubscribed", 0),
        open_rate=round(open_rate, 2),
        reply_rate=round(reply_rate, 2),
        status_breakdown=status_breakdown,
        timeline=timeline,
    )
