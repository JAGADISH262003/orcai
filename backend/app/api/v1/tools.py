"""Bulk import, enrichment, portal, artifacts, and compliance API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.api.deps import CurrentAgency, DbDep, require_permission
from app.core.rbac import Permission
from app.models.user import User
from app.services.audit import audit

router = APIRouter(prefix="/tools", tags=["tools"])


# --- Bulk Import ---

class BulkImportIn(BaseModel):
    mapping: dict[str, int] | None = None
    consent_basis: str = "affidavit"
    encoding: str = "utf-8"


@router.post("/import/csv")
async def import_csv(
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.SEEKERS_WRITE))],
    file: UploadFile = File(...),  # noqa: B008
    mapping: str | None = Query(default=None),
    consent_basis: str = Query(default="affidavit"),
):
    content = await file.read()
    import json
    parsed_mapping = json.loads(mapping) if mapping else None

    from app.services.bulk_import import import_csv as do_import
    result = do_import(db, agency.id, content, mapping=parsed_mapping, consent_basis=consent_basis)
    audit(db, agency_id=agency.id, user_id=user.id, action="bulk.import",
          meta={"file": file.filename, "imported": result["imported"]})
    db.commit()
    return result


@router.post("/import/csv/preview")
async def preview_csv(file: UploadFile = File(...)):  # noqa: B008
    content = await file.read()
    from app.services.bulk_import import preview_csv as do_preview
    return do_preview(content)


@router.post("/import/zip")
async def import_zip(
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.SEEKERS_WRITE))],
    file: UploadFile = File(...),  # noqa: B008
    consent_basis: str = Query(default="affidavit"),
):
    content = await file.read()
    from app.services.bulk_import import import_zip as do_import
    result = do_import(db, agency.id, content, consent_basis=consent_basis)
    audit(db, agency_id=agency.id, user_id=user.id, action="bulk.import_zip",
          meta={"file": file.filename, "imported": result["imported"]})
    db.commit()
    return result


# --- Enrichment ---

class EnrichIn(BaseModel):
    email: str | None = None
    name: str | None = None
    company: str | None = None
    linkedin_url: str | None = None
    providers: list[str] = Field(default=["apollo", "pdl", "hunter"])


@router.post("/enrich")
async def enrich_candidate(
    payload: EnrichIn,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.SEEKERS_WRITE))],
):
    from app.services.enrichment import enrich_candidate as do_enrich
    result = do_enrich(
        agency.id, email=payload.email, name=payload.name,
        company=payload.company, linkedin_url=payload.linkedin_url,
        providers=payload.providers,
    )
    audit(db, agency_id=agency.id, user_id=user.id, action="enrich.candidate",
          meta={"providers": payload.providers})
    db.commit()
    return result


# --- Candidate Portal ---

@router.get("/portal/{seeker_id}/token")
def generate_portal_token(
    seeker_id: int,
    db: DbDep,
    agency: CurrentAgency,
    user: Annotated[User, Depends(require_permission(Permission.SEEKERS_WRITE))],
):
    from app.services.portal import generate_portal_token as gen_token
    token = gen_token(seeker_id, agency.id)
    return {"token": token, "url": f"/portal/{token}"}


@router.get("/portal/profile")
def get_portal_profile(
    token: str,
    db: DbDep,
):
    from app.services.portal import get_portal_profile as get_profile
    from app.services.portal import verify_portal_token
    data = verify_portal_token(token)
    if data is None:
        raise HTTPException(status_code=401, detail="Invalid or expired portal token")
    result = get_profile(db, data["seeker_id"], data["agency_id"])
    if "error" in result:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return result


# --- Artifacts ---

@router.get("/artifacts/mis/{contract_id}")
def get_mis_report(
    contract_id: int,
    db: DbDep,
    agency: CurrentAgency,
):
    from app.services.artifacts import generate_mis_report
    csv_content = generate_mis_report(db, agency.id, contract_id=contract_id)
    from fastapi.responses import Response
    return Response(content=csv_content, media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=mis_report_{contract_id}.csv"})


@router.get("/artifacts/mis")
def get_mis_report_all(db: DbDep, agency: CurrentAgency):
    from app.services.artifacts import generate_mis_report
    csv_content = generate_mis_report(db, agency.id)
    from fastapi.responses import Response
    return Response(content=csv_content, media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=mis_report_all.csv"})


@router.get("/artifacts/hotlist")
def get_hotlist(
    db: DbDep,
    agency: CurrentAgency,
    status: str = Query(default="placed"),
):
    from app.services.artifacts import generate_hotlist
    csv_content = generate_hotlist(db, agency.id, status=status)
    from fastapi.responses import Response
    return Response(content=csv_content, media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=hotlist_{status}.csv"})


@router.get("/artifacts/rtr/{match_id}")
def get_rtr(match_id: int, db: DbDep, agency: CurrentAgency):
    from app.services.artifacts import generate_rtr_content
    content = generate_rtr_content(db, match_id)
    if "error" in content:
        raise HTTPException(status_code=404, detail="Match not found")
    return content


class OfferLetterIn(BaseModel):
    candidate_name: str
    position_title: str
    company_name: str
    start_date: str
    salary: str
    location: str
    is_remote: bool = False


@router.post("/artifacts/offer-letter")
def get_offer_letter(payload: OfferLetterIn):
    from app.services.artifacts import generate_offer_letter
    return generate_offer_letter(
        payload.candidate_name, payload.position_title, payload.company_name,
        payload.start_date, payload.salary, payload.location, payload.is_remote,
    )


# --- US Compliance ---

class I9In(BaseModel):
    employee_name: str
    address: str
    date_of_birth: str
    ssn_last4: str
    phone: str
    citizenship_status: str
    alien_registration_number: str | None = None
    uscis_number: str | None = None
    i94_number: str | None = None
    passport_country: str | None = None
    passport_number: str | None = None
    work_authorization_expiry: str | None = None


@router.post("/compliance/i9")
def get_i9(payload: I9In):
    from app.services.compliance import generate_i9_section1
    return generate_i9_section1(**payload.model_dump())


class MSAIn(BaseModel):
    client_name: str
    vendor_name: str
    effective_date: str
    rate_type: str = "hourly"
    rate_amount: str | None = None
    payment_terms: str = "Net 30"
    term_length: str = "12 months"
    governing_law: str = "State of California"


@router.post("/compliance/msa")
def get_msa(payload: MSAIn):
    from app.services.compliance import generate_msa
    return generate_msa(**payload.model_dump())


class EVerifyIn(BaseModel):
    employee_name: str
    employer_name: str
    employer_ein: str
    i9_date: str


@router.post("/compliance/everify")
def get_everify(payload: EVerifyIn):
    from app.services.compliance import generate_everify_request
    return generate_everify_request(**payload.model_dump())
