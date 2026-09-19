from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentAgency, DbDep, require_permission
from app.api.v1.matches import match_out
from app.core.rbac import Permission
from app.models.match import Match
from app.models.user import User
from app.schemas.match import MatchOut, MatchReviewIn
from app.services.audit import audit

router = APIRouter(prefix="/hitl", tags=["hitl"])

RequireHitlReview = Annotated[User, Depends(require_permission(Permission.HITL_REVIEW))]


@router.get("", response_model=list[MatchOut])
def hitl_queue(db: DbDep, agency: CurrentAgency, _user: RequireHitlReview):
    rows = (
        db.query(Match)
        .filter(
            Match.agency_id == agency.id,
            Match.hitl_required,
            Match.hitl_status.in_(["pending_review", None]),
        )
        .order_by(Match.score.asc())
        .all()
    )
    return [match_out(m) for m in rows]


@router.patch("/{match_id}/review", response_model=MatchOut)
def review_match(
    match_id: int,
    payload: MatchReviewIn,
    db: DbDep,
    agency: CurrentAgency,
    user: RequireHitlReview,
):
    m = db.get(Match, match_id)
    if m is None or m.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Match not found")

    if payload.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision must be approve or reject")

    m.hitl_status = "approved" if payload.decision == "approve" else "rejected"
    m.status = "approved" if payload.decision == "approve" else "rejected"
    m.human_review = payload.review
    m.reviewed_by = user.id
    m.reviewed_at = datetime.now(UTC)
    audit(db, agency_id=agency.id, user_id=user.id, action="hitl.review",
          entity_type="match", entity_id=m.id, meta={"decision": payload.decision})
    db.commit()
    db.refresh(m)
    return match_out(m)


@router.post("/{match_id}/approve", response_model=MatchOut)
def fast_approve(match_id: int, db: DbDep, agency: CurrentAgency, user: RequireHitlReview):
    m = db.get(Match, match_id)
    if m is None or m.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Match not found")
    m.hitl_status = "approved"
    m.status = "approved"
    m.reviewed_by = user.id
    m.reviewed_at = datetime.now(UTC)
    m.human_review = "Approved by recruiter with no edits."
    audit(db, agency_id=agency.id, user_id=user.id, action="hitl.approve", entity_type="match", entity_id=m.id)
    db.commit()
    db.refresh(m)
    return match_out(m)


@router.delete("/{match_id}", status_code=204)
def clear_from_queue(match_id: int, db: DbDep, agency: CurrentAgency):
    m = db.get(Match, match_id)
    if m is None or m.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Match not found")
    db.delete(m)
    db.commit()
