from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import CurrentAgency, CurrentUser, DbDep, require_permission
from app.core.rbac import Permission
from app.core.workflows import fill_stage, valid_match_statuses, workflow_by_type
from app.models.contract import Contract
from app.models.match import Match
from app.models.user import User
from app.schemas.match import MatchOut, MatchStatusIn
from app.services.audit import audit
from app.services.jobs import run_handler_inline, submit_job

router = APIRouter(prefix="/matches", tags=["matches"])


def match_out(m: Match) -> MatchOut:
    return MatchOut(
        id=m.id,
        contract_id=m.contract_id,
        seeker_id=m.seeker_id,
        score=m.score,
        tier=m.tier,
        status=m.status,
        hitl_required=m.hitl_required,
        rationale=m.rationale,
        hitl_status=m.hitl_status,
        human_review=m.human_review,
        reviewed_at=m.reviewed_at,
        created_at=m.created_at,
        seeker_name=m.seeker.name,
        seeker_headline=m.seeker.headline,
        seeker_skills=m.seeker.skills or [],
        contract_title=m.contract.title,
    )


@router.get("", response_model=list[MatchOut])
def list_matches(
    db: DbDep,
    agency: CurrentAgency,
    contract_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    hitl: bool | None = Query(default=None),
    tier: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
):
    q = db.query(Match).filter(Match.agency_id == agency.id)
    if contract_id:
        q = q.filter(Match.contract_id == contract_id)
    if status:
        q = q.filter(Match.status == status)
    if hitl is True:
        q = q.filter(Match.hitl_required)
    if tier:
        q = q.filter(Match.tier == tier)
    rows = q.order_by(Match.score.desc()).limit(limit).all()
    return [match_out(m) for m in rows]


@router.post("/run")
async def run_matching(
    db: DbDep,
    agency: CurrentAgency,
    user: CurrentUser,
    contract_id: int | None = Query(default=None),
    async_: bool = Query(default=True, alias="async"),
):
    """Run the matching engine as a background job by default. `?async=false` runs inline."""
    if contract_id:
        contract = db.get(Contract, contract_id)
        if contract is None or contract.agency_id != agency.id:
            raise HTTPException(status_code=404, detail="Contract not found")

    params = {"agency_id": agency.id, "contract_id": contract_id}
    audit(db, agency_id=agency.id, user_id=user.id, action="matching.run", meta=params)
    db.commit()

    if async_:
        job = submit_job(db, agency_id=agency.id, type_="matching.run", params=params)
        from fastapi.responses import JSONResponse

        from app.schemas.job import JobOut

        return JSONResponse(
            status_code=202,
            content=JobOut.model_validate(job).model_dump(mode="json"),
        )

    await run_handler_inline(db, "matching.run", agency.id, params)
    rows = (
        db.query(Match)
        .filter(Match.agency_id == agency.id)
        .order_by(Match.score.desc())
        .all()
    )
    return [match_out(m) for m in rows]


@router.get("/{match_id}", response_model=MatchOut)
def get_match(match_id: int, db: DbDep, agency: CurrentAgency):
    m = db.get(Match, match_id)
    if m is None or m.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Match not found")
    return match_out(m)


@router.patch("/{match_id}/status", response_model=MatchOut)
def set_match_status(
    match_id: int,
    payload: MatchStatusIn,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.MATCHES_WRITE))],
):
    m = db.get(Match, match_id)
    if m is None or m.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Match not found")
    valid = valid_match_statuses(agency.workflow_type)
    if payload.status not in valid:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(valid)}")
    m.status = payload.status
    # Filled contracts stop receiving matches
    wf = workflow_by_type(agency.workflow_type)
    if payload.status == fill_stage(agency.workflow_type):
        contract = db.get(Contract, m.contract_id)
        if contract:
            placed = (
                db.query(Match)
                .filter(Match.contract_id == contract.id, Match.status == wf["fill_stage"])
                .count()
            )
            if placed >= (contract.openings or 1):
                contract.status = "filled"
    audit(db, agency_id=agency.id, user_id=user.id, action="match.status", entity_type="match", entity_id=m.id, meta={"status": payload.status})
    db.commit()
    db.refresh(m)
    return match_out(m)
