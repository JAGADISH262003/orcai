"""Client Portal API — sessions, profile, and feedback."""

import hashlib
import secrets
from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import CurrentAgency, DbDep, require_permission
from app.core.rbac import Permission
from app.models.client import Client
from app.models.client_portal import ClientFeedback, ClientPortalSession
from app.models.contract import Contract
from app.models.match import Match
from app.models.seeker import Seeker
from app.models.user import User
from app.schemas.client_portal import (
    FeedbackIn,
    FeedbackOut,
    PortalProfileOut,
    PortalSessionIn,
    PortalSessionOut,
)
from app.services.audit import audit

router = APIRouter(prefix="/client-portal", tags=["client-portal"])


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _session_to_out(session: ClientPortalSession, db: Session) -> PortalSessionOut:
    client = db.get(Client, session.client_id)
    return PortalSessionOut(
        id=session.id,
        agency_id=session.agency_id,
        client_id=session.client_id,
        token_hash=session.token_hash,
        expires_at=session.expires_at,
        is_active=session.is_active,
        last_accessed_at=session.last_accessed_at,
        created_at=session.created_at,
        client_name=client.name if client else None,
    )


def _feedback_to_out(fb: ClientFeedback, db: Session) -> FeedbackOut:
    client = db.get(Client, fb.client_id)
    match = db.get(Match, fb.match_id)
    seeker_name = None
    contract_title = None
    if match:
        seeker = db.get(Seeker, match.seeker_id)
        seeker_name = seeker.name if seeker else None

        contract = db.get(Contract, match.contract_id)
        contract_title = contract.title if contract else None
    return FeedbackOut(
        id=fb.id,
        agency_id=fb.agency_id,
        client_id=fb.client_id,
        match_id=fb.match_id,
        session_id=fb.session_id,
        rating=fb.rating,
        feedback_text=fb.feedback_text,
        status=fb.status,
        reviewed_by=fb.reviewed_by,
        created_at=fb.created_at,
        client_name=client.name if client else None,
        match_seeker_name=seeker_name,
        match_contract_title=contract_title,
    )


@router.post("/sessions", response_model=PortalSessionOut, status_code=201)
def create_portal_session(
    payload: PortalSessionIn,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.CONTRACTS_WRITE))],
):
    client = db.get(Client, payload.client_id)
    if client is None or client.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Client not found")

    token = secrets.token_urlsafe(48)
    token_hash = _hash_token(token)
    from datetime import timedelta

    from app.models.mixins import utcnow

    expires_at = utcnow() + timedelta(days=payload.expiry_days)

    session = ClientPortalSession(
        agency_id=agency.id,
        client_id=payload.client_id,
        token_hash=token_hash,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(session)
    audit(db, agency_id=agency.id, user_id=user.id, action="portal.session.create",
          entity_type="client", entity_id=payload.client_id)
    db.commit()
    db.refresh(session)

    result = _session_to_out(session, db)
    # Return token only on creation (not stored after hashing)
    result_dict = result.model_dump(mode="json")
    result_dict["token"] = token
    return result_dict


@router.get("/sessions", response_model=list[PortalSessionOut])
def list_portal_sessions(
    db: DbDep,
    agency: CurrentAgency,
    client_id: int | None = Query(default=None),
):
    q = db.query(ClientPortalSession).filter(ClientPortalSession.agency_id == agency.id)
    if client_id:
        q = q.filter(ClientPortalSession.client_id == client_id)
    sessions = q.order_by(ClientPortalSession.created_at.desc()).all()
    return [_session_to_out(s, db) for s in sessions]


@router.get("/profile")
def get_portal_profile(
    token: str,
    db: DbDep,
):
    token_hash = _hash_token(token)
    session = db.query(ClientPortalSession).filter(
        ClientPortalSession.token_hash == token_hash,
        ClientPortalSession.is_active == True,  # noqa: E712
    ).first()
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired portal token")

    from datetime import datetime

    if session.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Portal session has expired")

    from app.models.mixins import utcnow

    session.last_accessed_at = utcnow()
    db.commit()

    client = db.get(Client, session.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    matches = (
        db.query(Match)
        .join(Contract, Match.contract_id == Contract.id)
        .filter(Contract.client_id == client.id, Match.agency_id == session.agency_id)
        .all()
    )

    submitted = []
    for m in matches:
        seeker = db.get(Seeker, m.seeker_id)
        contract = db.get(Contract, m.contract_id)
        submitted.append({
            "match_id": m.id,
            "seeker_name": seeker.name if seeker else None,
            "seeker_headline": seeker.headline if seeker else None,
            "contract_title": contract.title if contract else None,
            "score": m.score,
            "tier": m.tier,
            "status": m.status,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })

    return PortalProfileOut(
        client_id=client.id,
        client_name=client.name,
        client_industry=client.industry,
        contact_name=client.contact_name,
        contact_email=client.contact_email,
        submitted_matches=submitted,
    )


@router.post("/feedback", response_model=FeedbackOut, status_code=201)
def submit_feedback(
    payload: FeedbackIn,
    token: str,
    db: DbDep,
):
    token_hash = _hash_token(token)
    session = db.query(ClientPortalSession).filter(
        ClientPortalSession.token_hash == token_hash,
        ClientPortalSession.is_active == True,  # noqa: E712
    ).first()
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired portal token")

    from datetime import datetime

    if session.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Portal session has expired")

    match = db.get(Match, payload.match_id)
    if match is None or match.agency_id != session.agency_id:
        raise HTTPException(status_code=404, detail="Match not found")

    existing = (
        db.query(ClientFeedback)
        .filter(
            ClientFeedback.client_id == session.client_id,
            ClientFeedback.match_id == payload.match_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Feedback already submitted for this match")

    fb = ClientFeedback(
        agency_id=session.agency_id,
        client_id=session.client_id,
        match_id=payload.match_id,
        session_id=session.id,
        rating=payload.rating,
        feedback_text=payload.feedback_text,
        status="pending",
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return _feedback_to_out(fb, db)


@router.get("/feedback", response_model=list[FeedbackOut])
def list_feedback(
    db: DbDep,
    agency: CurrentAgency,
    client_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
):
    q = db.query(ClientFeedback).filter(ClientFeedback.agency_id == agency.id)
    if client_id:
        q = q.filter(ClientFeedback.client_id == client_id)
    if status:
        q = q.filter(ClientFeedback.status == status)
    feedbacks = q.order_by(ClientFeedback.created_at.desc()).all()
    return [_feedback_to_out(fb, db) for fb in feedbacks]
