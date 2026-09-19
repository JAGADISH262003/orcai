"""Seeker deduplication.

A seeker is identified within an agency by a canonical dedupe key:
  - primary: normalized email (or php number if no email)
  - fallback: normalized full name (lowercase, stripped of middle initials/punctuation)
"""

import re
import unicodedata

from sqlalchemy.orm import Session

from app.models.seeker import Seeker

_EMAIL_NORM_RE = re.compile(r"[^a-z0-9@.+]")


def normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    return _EMAIL_NORM_RE.sub("", email.lower().strip())


def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 10:
        return None
    return digits[-10:]  # keep last 10 digits, ignore country code differences


def normalize_name(name: str | None) -> str | None:
    if not name:
        return None
    name = unicodedata.normalize("NFKD", name)
    compact = re.sub(r"[^a-z ]", "", name.lower())
    parts = [p for p in compact.split() if p]
    if len(parts) < 1:
        return None
    # first + last only (drop middle names / initials)
    return " ".join([parts[0], parts[-1]])


def build_dedupe_key(email: str | None, phone: str | None, name: str | None) -> str | None:
    email_n = normalize_email(email)
    if email_n:
        return f"email:{email_n}"
    phone_n = normalize_phone(phone)
    if phone_n:
        return f"phone:{phone_n}"
    name_n = normalize_name(name)
    if name_n:
        return f"name:{name_n}"
    return None


def find_duplicate(
    db: Session, agency_id: int, email: str | None, phone: str | None, name: str | None
) -> tuple[Seeker | None, str | None]:
    """Return (existing seeker, matched_on) if a duplicate exists in the agency."""
    key = build_dedupe_key(email, phone, name)
    if key:
        existing = (
            db.query(Seeker)
            .filter(Seeker.agency_id == agency_id, Seeker.dedupe_key == key)
            .first()
        )
        if existing:
            return existing, "dedupe_key"

    email_n = normalize_email(email)
    if email_n:
        existing = (
            db.query(Seeker)
            .filter(Seeker.agency_id == agency_id, Seeker.email.ilike(f"%{email_n}%"))
            .first()
        )
        if existing:
            return existing, "email"

    phone_n = normalize_phone(phone)
    if phone_n:
        existing = (
            db.query(Seeker)
            .filter(Seeker.agency_id == agency_id, Seeker.phone is not None)
            .all()
        )
        for seeker in existing:
            if seeker.phone and normalize_phone(seeker.phone) == phone_n:
                return seeker, "phone"

    name_n = normalize_name(name)
    if name_n:
        existing = (
            db.query(Seeker)
            .filter(Seeker.agency_id == agency_id, Seeker.name.ilike(f"%{name_n.split()[0]}%"))
            .first()
        )
        if existing and normalize_name(existing.name) == name_n:
            return existing, "name"

    return None, None
