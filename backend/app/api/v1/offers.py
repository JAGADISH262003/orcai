from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import CurrentAgency, CurrentUser, DbDep, require_permission
from app.core.rbac import Permission
from app.models.contract import Contract
from app.models.match import Match
from app.models.offer import Offer, OfferApproval
from app.models.seeker import Seeker
from app.models.user import User
from app.schemas.offer import OfferApprovalOut, OfferIn, OfferOut, OfferPipelineColumn
from app.services.audit import audit

router = APIRouter(prefix="/offers", tags=["offers"])

PIPELINE_STATUSES = [
    ("draft", "Draft"),
    ("pending_approval", "Pending Approval"),
    ("approved", "Approved"),
    ("sent", "Sent"),
    ("accepted", "Accepted"),
    ("rejected", "Rejected"),
]


def offer_out(o: Offer) -> OfferOut:
    approvals = []
    for a in o.approvals:
        approvals.append(OfferApprovalOut(
            id=a.id, offer_id=a.offer_id, approver_id=a.approver_id,
            status=a.status, comments=a.comments, decided_at=a.decided_at,
            created_at=a.created_at, approver_name=a.approver.name if a.approver else None,
        ))
    return OfferOut(
        id=o.id, agency_id=o.agency_id, contract_id=o.contract_id,
        seeker_id=o.seeker_id, match_id=o.match_id, status=o.status,
        offered_salary=o.offered_salary, offered_currency=o.offered_currency,
        start_date=o.start_date, offer_expiry=o.offer_expiry,
        terms=o.terms, notes=o.notes, approved_by=o.approved_by,
        approved_at=o.approved_at, sent_at=o.sent_at, responded_at=o.responded_at,
        created_at=o.created_at,
        contract_title=o.contract.title if o.contract else None,
        seeker_name=o.seeker.name if o.seeker else None, approvals=approvals,
    )


@router.get("", response_model=list[OfferOut])
def list_offers(db: DbDep, agency: CurrentAgency, status: str | None = Query(default=None),
                contract_id: int | None = Query(default=None), seeker_id: int | None = Query(default=None),
                limit: int = Query(default=100, le=500)):
    q = db.query(Offer).filter(Offer.agency_id == agency.id)
    if status:
        q = q.filter(Offer.status == status)
    if contract_id:
        q = q.filter(Offer.contract_id == contract_id)
    if seeker_id:
        q = q.filter(Offer.seeker_id == seeker_id)
    return [offer_out(o) for o in q.order_by(Offer.created_at.desc()).limit(limit).all()]


@router.get("/pipeline", response_model=list[OfferPipelineColumn])
def offer_pipeline(db: DbDep, agency: CurrentAgency):
    columns = []
    for status_key, label in PIPELINE_STATUSES:
        rows = db.query(Offer).filter(
            Offer.agency_id == agency.id, Offer.status == status_key
        ).order_by(Offer.created_at.desc()).all()
        columns.append(OfferPipelineColumn(status=status_key, label=label, offers=[offer_out(o) for o in rows]))
    return columns


@router.post("", response_model=OfferOut, status_code=201)
def create_offer(payload: OfferIn, db: DbDep, agency: CurrentAgency,
                 user: Annotated[User, Depends(require_permission(Permission.CONTRACTS_WRITE))]):
    contract = db.get(Contract, payload.contract_id)
    if contract is None or contract.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Contract not found")
    seeker = db.get(Seeker, payload.seeker_id)
    if seeker is None or seeker.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Seeker not found")
    if payload.match_id:
        match = db.get(Match, payload.match_id)
        if match is None or match.agency_id != agency.id:
            raise HTTPException(status_code=404, detail="Match not found")
    offer = Offer(agency_id=agency.id, contract_id=payload.contract_id, seeker_id=payload.seeker_id,
                  match_id=payload.match_id, offered_salary=payload.offered_salary,
                  offered_currency=payload.offered_currency, start_date=payload.start_date,
                  offer_expiry=payload.offer_expiry, terms=payload.terms, notes=payload.notes, status="draft")
    db.add(offer)
    audit(db, agency_id=agency.id, user_id=user.id, action="offer.create", entity_type="offer", entity_id=offer.id)
    db.commit()
    db.refresh(offer)
    return offer_out(offer)


@router.get("/{offer_id}", response_model=OfferOut)
def get_offer(offer_id: int, db: DbDep, agency: CurrentAgency):
    o = db.get(Offer, offer_id)
    if o is None or o.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Offer not found")
    return offer_out(o)


@router.patch("/{offer_id}", response_model=OfferOut)
def update_offer(offer_id: int, payload: OfferIn, db: DbDep, agency: CurrentAgency,
                 user: Annotated[User, Depends(require_permission(Permission.CONTRACTS_WRITE))]):
    o = db.get(Offer, offer_id)
    if o is None or o.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Offer not found")
    if o.status not in ("draft", "pending_approval"):
        raise HTTPException(status_code=400, detail="Cannot edit offer in current status")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(o, field, value)
    audit(db, agency_id=agency.id, user_id=user.id, action="offer.update", entity_type="offer", entity_id=o.id)
    db.commit()
    db.refresh(o)
    return offer_out(o)


@router.delete("/{offer_id}", status_code=204)
def delete_offer(offer_id: int, db: DbDep, agency: CurrentAgency,
                 user: Annotated[User, Depends(require_permission(Permission.CONTRACTS_WRITE))]):
    o = db.get(Offer, offer_id)
    if o is None or o.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Offer not found")
    if o.status not in ("draft", "pending_approval"):
        raise HTTPException(status_code=400, detail="Cannot delete offer in current status")
    audit(db, agency_id=agency.id, user_id=user.id, action="offer.delete", entity_type="offer", entity_id=o.id)
    db.delete(o)
    db.commit()


class ApprovalCommentIn(BaseModel):
    comments: str | None = None


@router.post("/{offer_id}/submit", response_model=OfferOut)
def submit_offer(offer_id: int, db: DbDep, agency: CurrentAgency,
                 user: Annotated[User, Depends(require_permission(Permission.CONTRACTS_WRITE))]):
    o = db.get(Offer, offer_id)
    if o is None or o.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Offer not found")
    if o.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft offers can be submitted")
    admins = db.query(User).filter(User.agency_id == agency.id, User.role.in_(["owner", "admin"])).all()
    if not admins:
        raise HTTPException(status_code=400, detail="No admin users found")
    for admin in admins:
        db.add(OfferApproval(agency_id=agency.id, offer_id=o.id, approver_id=admin.id, status="pending"))
    o.status = "pending_approval"
    audit(db, agency_id=agency.id, user_id=user.id, action="offer.submit", entity_type="offer", entity_id=o.id)
    db.commit()
    db.refresh(o)
    return offer_out(o)


@router.post("/{offer_id}/approve", response_model=OfferOut)
def approve_offer(offer_id: int, payload: ApprovalCommentIn, db: DbDep, agency: CurrentAgency,
                  user: Annotated[User, Depends(require_permission(Permission.CONTRACTS_WRITE))]):
    o = db.get(Offer, offer_id)
    if o is None or o.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Offer not found")
    if o.status != "pending_approval":
        raise HTTPException(status_code=400, detail="Offer is not pending approval")
    my_approval = db.query(OfferApproval).filter(
        OfferApproval.offer_id == o.id, OfferApproval.approver_id == user.id, OfferApproval.status == "pending"
    ).first()
    if my_approval is None:
        raise HTTPException(status_code=400, detail="No pending approval for you")
    my_approval.status = "approved"
    my_approval.comments = payload.comments
    my_approval.decided_at = datetime.now(UTC)
    all_pending = db.query(OfferApproval).filter(OfferApproval.offer_id == o.id, OfferApproval.status == "pending").count()
    if all_pending == 0:
        o.status = "approved"
        o.approved_by = user.id
        o.approved_at = datetime.now(UTC)
    audit(db, agency_id=agency.id, user_id=user.id, action="offer.approve", entity_type="offer", entity_id=o.id)
    db.commit()
    db.refresh(o)
    return offer_out(o)


@router.post("/{offer_id}/reject", response_model=OfferOut)
def reject_offer(offer_id: int, payload: ApprovalCommentIn, db: DbDep, agency: CurrentAgency,
                 user: Annotated[User, Depends(require_permission(Permission.CONTRACTS_WRITE))]):
    o = db.get(Offer, offer_id)
    if o is None or o.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Offer not found")
    if o.status not in ("pending_approval", "approved", "sent"):
        raise HTTPException(status_code=400, detail="Offer cannot be rejected in current status")
    if o.status == "pending_approval":
        my_approval = db.query(OfferApproval).filter(
            OfferApproval.offer_id == o.id, OfferApproval.approver_id == user.id, OfferApproval.status == "pending"
        ).first()
        if my_approval:
            my_approval.status = "rejected"
            my_approval.comments = payload.comments
            my_approval.decided_at = datetime.now(UTC)
    o.status = "rejected"
    o.responded_at = datetime.now(UTC)
    audit(db, agency_id=agency.id, user_id=user.id, action="offer.reject", entity_type="offer", entity_id=o.id)
    db.commit()
    db.refresh(o)
    return offer_out(o)


@router.post("/{offer_id}/send", response_model=OfferOut)
def send_offer(offer_id: int, db: DbDep, agency: CurrentAgency,
               user: Annotated[User, Depends(require_permission(Permission.CONTRACTS_WRITE))]):
    o = db.get(Offer, offer_id)
    if o is None or o.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Offer not found")
    if o.status != "approved":
        raise HTTPException(status_code=400, detail="Only approved offers can be sent")

    # Generate offer letter and send via email
    seeker = o.seeker
    contract = o.contract
    client = contract.client if contract else None
    from app.services.artifacts import generate_offer_letter
    salary_str = f"{o.offered_currency} {o.offered_salary:,.0f}/year" if o.offered_salary else "TBD"
    letter = generate_offer_letter(
        candidate_name=seeker.name if seeker else "Candidate",
        position_title=contract.title if contract else "Position",
        company_name=client.name if client else "Company",
        start_date=o.start_date or "TBD",
        salary=salary_str,
        location=contract.location if contract else "TBD",
        is_remote=contract.is_remote if contract else False,
    )
    from app.services.email_delivery import send_email
    email_ok = False
    if seeker and seeker.email:
        email_ok = send_email(
            to=seeker.email,
            subject=f"Offer Letter — {contract.title if contract else 'Position'} at {client.name if client else 'Company'}",
            body_html=letter.get("html", ""),
            body_text=letter.get("text", ""),
        )

    o.status = "sent"
    o.sent_at = datetime.now(UTC)
    audit(db, agency_id=agency.id, user_id=user.id, action="offer.send", entity_type="offer", entity_id=o.id,
          meta={"email_sent": email_ok})
    db.commit()
    db.refresh(o)
    return offer_out(o)


@router.post("/{offer_id}/accept", response_model=OfferOut)
def accept_offer(offer_id: int, db: DbDep, agency: CurrentAgency, user: CurrentUser):
    o = db.get(Offer, offer_id)
    if o is None or o.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Offer not found")
    if o.status != "sent":
        raise HTTPException(status_code=400, detail="Only sent offers can be accepted")
    o.status = "accepted"
    o.responded_at = datetime.now(UTC)
    audit(db, agency_id=agency.id, user_id=user.id, action="offer.accept", entity_type="offer", entity_id=o.id)
    db.commit()
    db.refresh(o)
    return offer_out(o)


@router.post("/{offer_id}/withdraw", response_model=OfferOut)
def withdraw_offer(offer_id: int, db: DbDep, agency: CurrentAgency,
                   user: Annotated[User, Depends(require_permission(Permission.CONTRACTS_WRITE))]):
    o = db.get(Offer, offer_id)
    if o is None or o.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Offer not found")
    if o.status not in ("draft", "pending_approval", "approved"):
        raise HTTPException(status_code=400, detail="Offer cannot be withdrawn in current status")
    o.status = "withdrawn"
    audit(db, agency_id=agency.id, user_id=user.id, action="offer.withdraw", entity_type="offer", entity_id=o.id)
    db.commit()
    db.refresh(o)
    return offer_out(o)


@router.get("/{offer_id}/letter")
def generate_offer_letter_endpoint(offer_id: int, db: DbDep, agency: CurrentAgency):
    o = db.get(Offer, offer_id)
    if o is None or o.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Offer not found")
    seeker = o.seeker
    contract = o.contract
    client = contract.client if contract else None
    from app.services.artifacts import generate_offer_letter
    salary_str = f"{o.offered_currency} {o.offered_salary:,.0f}/year" if o.offered_salary else "TBD"
    return generate_offer_letter(
        candidate_name=seeker.name if seeker else "Candidate",
        position_title=contract.title if contract else "Position",
        company_name=client.name if client else "Company",
        start_date=o.start_date or "TBD",
        salary=salary_str,
        location=contract.location if contract else "TBD",
        is_remote=contract.is_remote if contract else False,
    )
