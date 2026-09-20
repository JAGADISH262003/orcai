from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentAgency, DbDep, require_permission
from app.core.rbac import Permission
from app.models.contract import Contract
from app.models.user import User
from app.services.ai_screening import batch_screen, compute_skills_gap_analysis
from app.services.audit import audit
from app.services.skills_taxonomy import get_all_skills, get_skills_by_category

router = APIRouter(prefix="/ai", tags=["ai-screening"])


class ScreenRequest(BaseModel):
    contract_id: int
    seeker_ids: list[int] | None = None


class SkillsExtractRequest(BaseModel):
    text: str


class MarketIntelRequest(BaseModel):
    job_title: str
    skills: list[str]
    location: str | None = None


@router.post("/screen")
async def screen_resumes(
    payload: ScreenRequest,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.MATCHES_WRITE))],
):
    results = batch_screen(db, agency.id, payload.contract_id, payload.seeker_ids)
    audit(db, agency_id=agency.id, user_id=user.id, action="ai.screen",
          meta={"contract_id": payload.contract_id, "count": len(results)})
    db.commit()
    return {"results": results, "total": len(results)}


@router.post("/skills-extract")
async def extract_skills(
    payload: SkillsExtractRequest,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.MATCHES_WRITE))],
):
    from app.services.ai_screening import extract_skills_from_text
    skills = await extract_skills_from_text(payload.text)
    audit(db, agency_id=agency.id, user_id=user.id, action="ai.skills_extract")
    db.commit()
    return {"skills": skills}


@router.post("/market-intelligence")
async def market_intelligence(
    payload: MarketIntelRequest,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.MATCHES_READ))],
):
    from app.services.ai_screening import get_market_intelligence
    result = await get_market_intelligence(payload.job_title, payload.skills, payload.location)
    audit(db, agency_id=agency.id, user_id=user.id, action="ai.market_intelligence")
    db.commit()
    return result


@router.get("/skills-taxonomy")
def skills_taxonomy():
    return {
        "categories": get_skills_by_category(),
        "all_skills": get_all_skills(),
        "total_count": len(get_all_skills()),
    }


@router.post("/skills-gap")
async def skills_gap(
    contract_id: int,
    seeker_id: int,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.MATCHES_READ))],
):
    contract = db.get(Contract, contract_id)
    if contract is None or contract.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Contract not found")
    from app.models.seeker import Seeker
    seeker = db.get(Seeker, seeker_id)
    if seeker is None or seeker.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Seeker not found")
    return compute_skills_gap_analysis(
        contract.skills or [], seeker.skills or []
    )
