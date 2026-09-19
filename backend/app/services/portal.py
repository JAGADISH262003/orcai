"""Candidate self-service portal: public profile links, status tracking.

Candidates get a tokenized link to:
  - View their match status across jobs
  - Update their profile / resume
  - Manage consent (withdraw, update)
  - See which stage they're at in the pipeline
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.match import Match
from app.models.seeker import Seeker

logger = logging.getLogger("orcai.portal")
settings = get_settings()


def generate_portal_token(seeker_id: int, agency_id: int) -> str:
    """Generate a signed, time-limited portal token for a candidate."""
    expiry = int(time.time()) + (settings.PORTAL_TOKEN_EXPIRE_HOURS * 3600)
    payload = f"{seeker_id}:{agency_id}:{expiry}"
    sig = hmac.new(settings.PORTAL_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    raw = f"{payload}:{sig}"
    return secrets.token_urlsafe(2) + "." + raw.replace(":", ".")


def verify_portal_token(token: str) -> dict | None:
    """Verify a portal token. Returns {seeker_id, agency_id} or None."""
    try:
        parts = token.split(".", 2)
        if len(parts) != 3:
            return None
        raw = parts[1].replace(".", ":")
        segments = raw.split(":")
        if len(segments) != 4:
            return None
        seeker_id, agency_id, expiry_str, sig = segments
        payload = f"{seeker_id}:{agency_id}:{expiry_str}"
        expected = hmac.new(settings.PORTAL_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(sig, expected):
            return None
        if int(time.time()) > int(expiry_str):
            return None
        return {"seeker_id": int(seeker_id), "agency_id": int(agency_id)}
    except Exception:
        return None


def get_portal_profile(db: Session, seeker_id: int, agency_id: int) -> dict:
    """Get candidate's public portal profile with match statuses."""
    seeker = db.query(Seeker).filter(Seeker.id == seeker_id, Seeker.agency_id == agency_id).first()
    if seeker is None:
        return {"error": "not_found"}

    matches = (
        db.query(Match)
        .filter(Match.seeker_id == seeker_id, Match.agency_id == agency_id)
        .all()
    )

    match_statuses = []
    for m in matches:
        contract = m.contract
        match_statuses.append({
            "match_id": m.id,
            "contract_title": contract.title if contract else None,
            "client_name": contract.client.name if contract and contract.client else None,
            "score": m.score,
            "tier": m.tier,
            "status": m.status,
            "updated_at": m.reviewed_at.isoformat() if m.reviewed_at else m.created_at.isoformat(),
        })

    return {
        "seeker_id": seeker.id,
        "name": seeker.name,
        "email": seeker.email,
        "headline": seeker.headline,
        "location": seeker.location,
        "visa_status": seeker.visa_status,
        "skills": seeker.skills or [],
        "experience_years": seeker.experience_years,
        "matches": match_statuses,
        "total_matches": len(match_statuses),
    }


def update_portal_profile(
    db: Session,
    seeker_id: int,
    agency_id: int,
    updates: dict,
) -> dict:
    """Candidate updates their own profile (limited fields)."""
    seeker = db.query(Seeker).filter(Seeker.id == seeker_id, Seeker.agency_id == agency_id).first()
    if seeker is None:
        return {"error": "not_found"}

    allowed = {"phone", "location", "visa_status", "headline", "summary", "skills", "experience_years"}
    changed = {}
    for field in allowed:
        if field in updates and updates[field] is not None:
            setattr(seeker, field, updates[field])
            changed[field] = updates[field]

    if changed:
        seeker.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(seeker)

    return {"updated": changed}
