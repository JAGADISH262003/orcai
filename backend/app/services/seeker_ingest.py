"""Shared seeker creation/upsert with dedupe + consent logging."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.consent import ConsentRecord
from app.models.seeker import Seeker
from app.services.dedupe import build_dedupe_key, find_duplicate


def upsert_seeker(
    db: Session,
    agency_id: int,
    data: dict,
    *,
    source: str = "manual",
    source_channel: str | None = None,
    consent_channel: str | None = None,
    consent_basis: str = "explicit_opt_in",
) -> tuple[Seeker, bool]:
    """Create a seeker unless a duplicate exists. Returns (seeker, created)."""
    existing, _ = find_duplicate(
        db,
        agency_id,
        data.get("email"),
        data.get("phone"),
        data.get("name"),
    )
    if existing:
        if data.get("name") and not existing.name:
            existing.name = data["name"]
        if data.get("phone") and not existing.phone:
            existing.phone = data["phone"]
        if data.get("skills") and existing.skills:
            existing.skills = sorted(set(existing.skills + data["skills"]))
        db.commit()
        return existing, False

    key = build_dedupe_key(data.get("email"), data.get("phone"), data.get("name"))
    seeker = Seeker(
        agency_id=agency_id,
        name=data.get("name"),
        email=data.get("email"),
        phone=data.get("phone"),
        visa_status=data.get("visa_status"),
        location=data.get("location"),
        headline=data.get("headline"),
        skills=data.get("skills") or [],
        experience_years=data.get("experience_years"),
        summary=data.get("summary"),
        education=data.get("education"),
        source=source,
        source_channel=source_channel,
        resume_text=data.get("resume_text"),
        is_verified=False,
        is_active=True,
        dedupe_key=key,
    )
    db.add(seeker)
    db.flush()

    db.add(
        ConsentRecord(
            agency_id=agency_id,
            seeker_id=seeker.id,
            basis=consent_basis,
            channel=consent_channel or source_channel,
            consent_given_at=datetime.now(UTC),
            retention_days=30,
            status="active",
        )
    )
    db.commit()
    db.refresh(seeker)
    return seeker, True
