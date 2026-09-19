from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.api.deps import CurrentAgency, DbDep, require_permission
from app.core.config import get_settings
from app.core.rbac import Permission
from app.models.seeker import Seeker
from app.models.user import User
from app.schemas.seeker import DedupeCheckOut, SeekerIn, SeekerOut, SeekerSearchOut
from app.services.audit import audit
from app.services.dedupe import build_dedupe_key, find_duplicate
from app.services.jobs import run_handler_inline, submit_job
from app.services.seeker_ingest import upsert_seeker

router = APIRouter(prefix="/seekers", tags=["seekers"])
settings = get_settings()

RequireSeekersWrite = Annotated[User, Depends(require_permission(Permission.SEEKERS_WRITE))]


def seeker_out(s: Seeker) -> SeekerOut:
    return SeekerOut(
        id=s.id,
        agency_id=s.agency_id,
        name=s.name,
        email=s.email,
        phone=s.phone,
        visa_status=s.visa_status,
        location=s.location,
        headline=s.headline,
        skills=s.skills or [],
        experience_years=s.experience_years,
        summary=s.summary,
        education=s.education,
        source=s.source,
        source_channel=s.source_channel,
        is_verified=s.is_verified,
        is_active=s.is_active,
        created_at=s.created_at,
    )


def search_out(s: Seeker) -> SeekerSearchOut:
    return SeekerSearchOut(
        id=s.id,
        name=s.name,
        headline=s.headline,
        visa_status=s.visa_status,
        location=s.location,
        skills=s.skills or [],
        experience_years=s.experience_years,
        source=s.source,
        is_verified=s.is_verified,
        created_at=s.created_at,
    )


def _upsert(db, agency_id: int, data: dict, *, source: str, source_channel: str | None, consent_channel: str | None, consent_basis: str = "explicit_opt_in"):
    return upsert_seeker(
        db,
        agency_id,
        data,
        source=source,
        source_channel=source_channel,
        consent_channel=consent_channel,
        consent_basis=consent_basis,
    )


@router.get("", response_model=list[SeekerSearchOut])
def list_seekers(
    db: DbDep,
    agency: CurrentAgency,
    q: str | None = Query(default=None),
    visa: str | None = Query(default=None),
    min_exp: float | None = Query(default=None),
    limit: int = Query(default=200, le=1000),
):
    query = db.query(Seeker).filter(Seeker.agency_id == agency.id, Seeker.is_active)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(
            Seeker.name.ilike(like)
            | Seeker.headline.ilike(like)
            | Seeker.email.ilike(like)
        )
    if visa:
        query = query.filter(Seeker.visa_status.ilike(f"%{visa}%"))
    if min_exp is not None:
        query = query.filter(Seeker.experience_years >= min_exp)
    rows = query.order_by(Seeker.created_at.desc()).limit(limit).all()
    return [search_out(s) for s in rows]


@router.post("", response_model=SeekerOut, status_code=201)
def create_seeker(
    payload: SeekerIn, db: DbDep, agency: CurrentAgency, user: RequireSeekersWrite
):
    seeker, _ = _upsert(
        db,
        agency.id,
        payload.model_dump(),
        source=payload.source,
        source_channel=payload.source_channel,
        consent_channel=None,
    )
    audit(db, agency_id=agency.id, user_id=user.id, action="seeker.create", entity_type="seeker", entity_id=seeker.id)
    db.commit()
    return seeker_out(seeker)


@router.post("/upload", status_code=202)
async def upload_resume(
    db: DbDep,
    agency: CurrentAgency,
    user: RequireSeekersWrite,
    file: UploadFile = File(...),  # noqa: B008
    visa_status: str | None = None,
    async_: bool = Query(default=True, alias="async"),
):
    """Upload a resume. Parsing + dedupe runs as a background job by default."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB)")

    # Per-tenant storage: uploads/<agency_id>/<file>
    filename = Path(file.filename or "resume.txt").name
    agency_dir = Path(settings.UPLOAD_DIR) / str(agency.id)
    agency_dir.mkdir(parents=True, exist_ok=True)
    dest = agency_dir / f"s_{agency.id}_{filename}"
    dest.write_bytes(content)

    params = {
        "agency_id": agency.id,
        "path": str(dest),
        "filename": filename,
        "visa_status": visa_status,
    }
    audit(db, agency_id=agency.id, user_id=user.id, action="seeker.upload", meta={"filename": filename})
    db.commit()

    if async_:
        return submit_job(db, agency_id=agency.id, type_="seeker.import", params=params)

    result = await run_handler_inline(db, "seeker.import", agency.id, params)
    seeker = db.get(Seeker, result["seeker_id"])
    return seeker_out(seeker)


@router.get("/dedupe-check", response_model=DedupeCheckOut)
def dedupe_check(
    db: DbDep,
    agency: CurrentAgency,
    email: str | None = Query(default=None),
    phone: str | None = Query(default=None),
    name: str | None = Query(default=None),
):
    existing, matched_on = find_duplicate(db, agency.id, email, phone, name)
    return DedupeCheckOut(
        is_duplicate=existing is not None,
        existing_seeker_id=existing.id if existing else None,
        existing_name=existing.name if existing else None,
        dedupe_key=existing.dedupe_key if existing else build_dedupe_key(email, phone, name),
        matched_on=matched_on,
    )


@router.get("/{seeker_id}", response_model=SeekerOut)
def get_seeker(seeker_id: int, db: DbDep, agency: CurrentAgency):
    s = db.get(Seeker, seeker_id)
    if s is None or s.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Seeker not found")
    return seeker_out(s)


@router.patch("/{seeker_id}", response_model=SeekerOut)
def update_seeker(seeker_id: int, payload: SeekerIn, db: DbDep, agency: CurrentAgency):
    s = db.get(Seeker, seeker_id)
    if s is None or s.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Seeker not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(s, field, value)
    db.commit()
    db.refresh(s)
    return seeker_out(s)


@router.delete("/{seeker_id}", status_code=204)
def delete_seeker(seeker_id: int, db: DbDep, agency: CurrentAgency):
    s = db.get(Seeker, seeker_id)
    if s is None or s.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Seeker not found")
    db.delete(s)
    db.commit()
