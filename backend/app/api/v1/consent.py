from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentAgency, DbDep, require_permission
from app.core.rbac import Permission
from app.models.consent import ConsentRecord
from app.models.seeker import Seeker
from app.models.user import User
from app.schemas.billing import ConsentCreateIn, ConsentOut
from app.services.audit import audit

router = APIRouter(prefix="/consent", tags=["consent"])

RequireConsentWrite = Annotated[User, Depends(require_permission(Permission.SETTINGS_WRITE))]


def consent_out(c: ConsentRecord, seeker_name: str | None = None) -> ConsentOut:
    return ConsentOut(
        id=c.id,
        seeker_id=c.seeker_id,
        seeker_name=seeker_name,
        basis=c.basis,
        channel=c.channel,
        status=c.status,
        consent_given_at=c.consent_given_at,
        retention_days=c.retention_days,
        erased_at=c.erased_at,
    )


@router.get("", response_model=list[ConsentOut])
def list_consent(db: DbDep, agency: CurrentAgency):
    rows = (
        db.query(ConsentRecord)
        .filter(ConsentRecord.agency_id == agency.id)
        .order_by(ConsentRecord.consent_given_at.desc())
        .all()
    )
    names = {s.id: s.name for s in db.query(Seeker).filter(Seeker.agency_id == agency.id).all()}
    return [consent_out(c, names.get(c.seeker_id)) for c in rows]


@router.post("", response_model=ConsentOut, status_code=201)
def create_consent(payload: ConsentCreateIn, db: DbDep, agency: CurrentAgency):
    seeker = db.get(Seeker, payload.seeker_id)
    if seeker is None or seeker.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Seeker not found")
    c = ConsentRecord(
        agency_id=agency.id,
        seeker_id=payload.seeker_id,
        basis=payload.basis,
        channel=payload.channel,
        consent_given_at=datetime.now(UTC),
        retention_days=payload.retention_days,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return consent_out(c, seeker.name)


@router.patch("/{consent_id}/withdraw", response_model=ConsentOut)
def withdraw_consent(
    consent_id: int, db: DbDep, agency: CurrentAgency, user: RequireConsentWrite
):
    c = db.get(ConsentRecord, consent_id)
    if c is None or c.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Consent record not found")
    if c.status in ("withdrawn", "erased"):
        raise HTTPException(status_code=409, detail="Consent already revoked")
    c.status = "withdrawn"
    c.withdrawn_at = datetime.now(UTC)
    audit(db, agency_id=agency.id, user_id=user.id, action="consent.withdraw", entity_type="consent", entity_id=c.id)
    db.add(c)
    db.commit()
    db.refresh(c)
    seeker = db.get(Seeker, c.seeker_id)
    return consent_out(c, seeker.name if seeker else None)


@router.post("/{consent_id}/erase", response_model=ConsentOut)
def erase_seeker_data(
    consent_id: int, db: DbDep, agency: CurrentAgency, user: RequireConsentWrite
):
    """DPDPA S.7 right-to-erasure: soft-erases the seeker record permanently."""
    c = db.get(ConsentRecord, consent_id)
    if c is None or c.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Consent record not found")
    c.status = "erased"
    c.erased_at = datetime.now(UTC)

    seeker = db.get(Seeker, c.seeker_id)
    if seeker:
        seeker.is_active = False
        seeker.email = f"erased-{seeker.id}@orcai.invalid"
        seeker.phone = None
        seeker.resume_text = None
    audit(db, agency_id=agency.id, user_id=user.id, action="consent.erase",
          entity_type="consent", entity_id=c.id, meta={"seeker_id": c.seeker_id})
    db.add(c)
    db.commit()
    db.refresh(c)
    return consent_out(c)
