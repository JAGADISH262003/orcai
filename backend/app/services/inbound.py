"""Process inbound chat messages into Seekers.

Rules (deterministic; LLM enrichment optional):
  - Body is assumed to describe a candidate. If it contains keywords (I am /
    experience / resume / skills) we parse it into a candidate profile.
  - Dedupe is applied within the agency.
"""

import logging
import re
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.agency import Agency
from app.models.inbound import InboundMessage
from app.services.seeker_ingest import upsert_seeker

logger = logging.getLogger("orcai.inbound")

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s.\-()]{8,18}\d)")


def _looks_like_candidate(body: str) -> bool:
    low = body.lower()
    markers = [
        "i am", "i'm", "experience", "resume", "skills", "years of", "role", "looking for",
        "position", "visa", "developer", "engineer", "architect", "analyst", "consultant",
    ]
    return any(m in low for m in markers)


def disposition_classifier(body: str) -> dict:
    """Best-effort signal extraction from free-form chat text."""
    data: dict = {
        "name": None,
        "email": None,
        "phone": None,
        "visa_status": None,
        "location": None,
        "headline": None,
        "skills": [],
        "experience_years": None,
        "summary": body[:1200],
    }

    # Name from greeting pattern
    m = re.search(r"\b(?:i am|i'm|my name is|this is)\s+([A-Za-z][A-Za-z ]{1,40})", body, re.IGNORECASE)
    if m:
        data["name"] = " ".join([w.capitalize() for w in m.group(1).split()])

    email_m = _EMAIL_RE.search(body)
    phone_m = _PHONE_RE.search(body)
    if email_m:
        data["email"] = email_m.group(0)
    if phone_m:
        data["phone"] = phone_m.group(0)

    visa_m = re.search(r"\b(H1B|OPT|GC EAD|GC|L1|TN|F1|Citizen)\b", body, re.IGNORECASE)
    if visa_m:
        data["visa_status"] = visa_m.group(1).upper()

    exp_m = re.search(r"(\d{1,2})\s*\+?\s*years?", body, re.IGNORECASE)
    if exp_m:
        data["experience_years"] = float(exp_m.group(1))

    from app.services.contract_parser import SKILLS_LEXICON

    try:
        data["skills"] = [
            s
            for s in SKILLS_LEXICON
            if re.search(r"\b" + re.escape(s) + r"\b", body, re.IGNORECASE)
        ]
    except Exception as exc:
        logger.warning("Skill extraction failed: %s", exc)

    return data


def process_inbound(db: Session, agency: Agency, msg: InboundMessage) -> InboundMessage:
    """Classify body and promote to a Seeker when plausible."""
    if not msg.body.strip():
        msg.status = "received"
        db.commit()
        return msg

    if _looks_like_candidate(msg.body):
        data = disposition_classifier(msg.body)
        seeker, created = upsert_seeker(
            db,
            agency.id,
            data,
            source="inbound",
            source_channel=msg.channel,
            consent_channel=msg.channel,
        )
        msg.status = "seeker_created"
        msg.seeker_id = seeker.id
        msg.note = "New seeker promoted from inbound message" if created else "Matched to existing seeker"
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    msg.status = "received"
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def record_inbound(
    db: Session,
    agency_slug: str,
    channel: str,
    external_id: str | None,
    phone_number: str | None,
    sender_name: str | None,
    body: str,
) -> InboundMessage:
    agency = db.query(Agency).filter(Agency.slug == agency_slug).first()
    if agency is None:
        raise ValueError(f"Unknown agency slug: {agency_slug}")
    msg = InboundMessage(
        agency_id=agency.id,
        channel=channel,
        external_id=external_id,
        phone_number=phone_number,
        sender_name=sender_name,
        body=body,
        received_at=datetime.now(UTC),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return process_inbound(db, agency, msg)
