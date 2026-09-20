from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.models.interview import Interview

router = APIRouter(prefix="/interviews", tags=["interviews"])


class InterviewIn(BaseModel):
    contract_id: int
    seeker_id: int
    match_id: int | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int = 30
    interview_type: str = "video"
    interviewer_name: str | None = None
    interviewer_email: str | None = None
    location: str | None = None
    meeting_link: str | None = None
    notes: str | None = None


class InterviewUpdate(BaseModel):
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    interview_type: str | None = None
    status: str | None = None
    interviewer_name: str | None = None
    interviewer_email: str | None = None
    location: str | None = None
    meeting_link: str | None = None
    feedback: str | None = None
    rating: int | None = None
    outcome: str | None = None
    notes: str | None = None


def _out(iv: Interview) -> dict[str, Any]:
    return {
        "id": iv.id,
        "agency_id": iv.agency_id,
        "contract_id": iv.contract_id,
        "seeker_id": iv.seeker_id,
        "match_id": iv.match_id,
        "scheduled_at": iv.scheduled_at.isoformat() if iv.scheduled_at else None,
        "duration_minutes": iv.duration_minutes,
        "interview_type": iv.interview_type,
        "status": iv.status,
        "interviewer_name": iv.interviewer_name,
        "interviewer_email": iv.interviewer_email,
        "location": iv.location,
        "meeting_link": iv.meeting_link,
        "feedback": iv.feedback,
        "rating": iv.rating,
        "outcome": iv.outcome,
        "notes": iv.notes,
        "created_at": iv.created_at.isoformat() if iv.created_at else None,
    }


@router.get("")
def list_interviews(
    user: CurrentUser,
    db: DbDep,
    status: str | None = None,
    seeker_id: int | None = None,
    contract_id: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    q = select(Interview).where(Interview.agency_id == user.agency_id)
    if status:
        q = q.where(Interview.status == status)
    if seeker_id:
        q = q.where(Interview.seeker_id == seeker_id)
    if contract_id:
        q = q.where(Interview.contract_id == contract_id)
    q = q.order_by(Interview.scheduled_at.desc().nullslast()).limit(limit)
    return [_out(r) for r in db.scalars(q).all()]


@router.post("", status_code=201)
def create_interview(
    data: InterviewIn,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, Any]:
    iv = Interview(
        agency_id=user.agency_id,
        contract_id=data.contract_id,
        seeker_id=data.seeker_id,
        match_id=data.match_id,
        scheduled_at=data.scheduled_at,
        duration_minutes=data.duration_minutes,
        interview_type=data.interview_type,
        interviewer_name=data.interviewer_name,
        interviewer_email=data.interviewer_email,
        location=data.location,
        meeting_link=data.meeting_link,
        notes=data.notes,
    )
    db.add(iv)
    db.commit()
    db.refresh(iv)
    return _out(iv)


@router.get("/{interview_id}")
def get_interview(
    interview_id: int,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, Any]:
    iv = db.get(Interview, interview_id)
    if not iv or iv.agency_id != user.agency_id:
        raise HTTPException(404, "Interview not found")
    return _out(iv)


@router.patch("/{interview_id}")
def update_interview(
    interview_id: int,
    data: InterviewUpdate,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, Any]:
    iv = db.get(Interview, interview_id)
    if not iv or iv.agency_id != user.agency_id:
        raise HTTPException(404, "Interview not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(iv, k, v)
    db.commit()
    db.refresh(iv)
    return _out(iv)


@router.delete("/{interview_id}")
def delete_interview(
    interview_id: int,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, str]:
    iv = db.get(Interview, interview_id)
    if not iv or iv.agency_id != user.agency_id:
        raise HTTPException(404, "Interview not found")
    db.delete(iv)
    db.commit()
    return {"ok": True}
