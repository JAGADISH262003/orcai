"""Output artifact generation: MIS reports, hotlist Excel, RTR PDF, offer letters.

Generates downloadable documents for recruitment workflows.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.match import Match

logger = logging.getLogger("orcai.artifacts")


# ---------------------------------------------------------------------------
# MIS Report (CSV)
# ---------------------------------------------------------------------------

def generate_mis_report(db: Session, agency_id: int, contract_id: int | None = None) -> str:
    """Generate a MIS report as CSV with match pipeline data."""
    q = db.query(Match).filter(Match.agency_id == agency_id)
    if contract_id:
        q = q.filter(Match.contract_id == contract_id)
    matches = q.order_by(Match.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Match ID", "Contract", "Client", "Candidate", "Score", "Tier",
        "Pipeline Status", "HITL Required", "HITL Status", "Created", "Reviewed",
    ])
    for m in matches:
        contract = m.contract
        seeker = m.seeker
        writer.writerow([
            m.id,
            contract.title if contract else "",
            contract.client.name if contract and contract.client else "",
            seeker.name if seeker else "",
            m.score,
            m.tier,
            m.status,
            "Yes" if m.hitl_required else "No",
            m.hitl_status or "",
            m.created_at.strftime("%Y-%m-%d") if m.created_at else "",
            m.reviewed_at.strftime("%Y-%m-%d") if m.reviewed_at else "",
        ])
    return output.getvalue()


# ---------------------------------------------------------------------------
# Hotlist Excel (CSV format)
# ---------------------------------------------------------------------------

def generate_hotlist(db: Session, agency_id: int, status: str = "placed") -> str:
    """Generate a hotlist of candidates at a specific pipeline stage."""
    matches = (
        db.query(Match)
        .filter(Match.agency_id == agency_id, Match.status == status)
        .order_by(Match.score.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Rank", "Candidate Name", "Email", "Phone", "Visa Status",
        "Location", "Headline", "Skills", "Experience (yrs)", "Score",
        "Tier", "Contract", "Client",
    ])
    for rank, m in enumerate(matches, 1):
        seeker = m.seeker
        contract = m.contract
        writer.writerow([
            rank,
            seeker.name if seeker else "",
            seeker.email if seeker else "",
            seeker.phone if seeker else "",
            seeker.visa_status if seeker else "",
            seeker.location if seeker else "",
            seeker.headline if seeker else "",
            ", ".join(seeker.skills or []),
            seeker.experience_years or "",
            m.score,
            m.tier,
            contract.title if contract else "",
            contract.client.name if contract and contract.client else "",
        ])
    return output.getvalue()


# ---------------------------------------------------------------------------
# RTR (Ready-to-Release) PDF content
# ---------------------------------------------------------------------------

def generate_rtr_content(db: Session, match_id: int) -> dict[str, Any]:
    """Generate RTR (Ready-to-Release) document content for a match."""
    match = db.get(Match, match_id)
    if match is None:
        return {"error": "not_found"}

    seeker = match.seeker
    contract = match.contract
    client = contract.client if contract else None

    content = {
        "title": "Ready-to-Release (RTR) Document",
        "date": datetime.now(UTC).strftime("%B %d, %Y"),
        "candidate": {
            "name": seeker.name if seeker else "",
            "email": seeker.email if seeker else "",
            "phone": seeker.phone if seeker else "",
            "visa_status": seeker.visa_status if seeker else "",
            "location": seeker.location if seeker else "",
            "headline": seeker.headline if seeker else "",
            "skills": seeker.skills or [],
            "experience_years": seeker.experience_years,
        },
        "position": {
            "title": contract.title if contract else "",
            "client": client.name if client else "",
            "location": contract.location if contract else "",
            "rate_bill": contract.rate_bill,
            "rate_pay": contract.rate_pay,
            "currency": contract.currency if contract else "USD",
            "duration_months": contract.duration_months,
            "skills_required": contract.skills or [],
        },
        "match": {
            "score": match.score,
            "tier": match.tier,
            "rationale": match.rationale or "",
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }

    # Build plain text version
    text_lines = [
        content["title"],
        f"Date: {content['date']}",
        "",
        "CANDIDATE INFORMATION",
        f"  Name: {content['candidate']['name']}",
        f"  Email: {content['candidate']['email']}",
        f"  Phone: {content['candidate']['phone']}",
        f"  Visa: {content['candidate']['visa_status']}",
        f"  Location: {content['candidate']['location']}",
        f"  Headline: {content['candidate']['headline']}",
        f"  Skills: {', '.join(content['candidate']['skills'])}",
        f"  Experience: {content['candidate']['experience_years']} years",
        "",
        "POSITION DETAILS",
        f"  Title: {content['position']['title']}",
        f"  Client: {content['position']['client']}",
        f"  Location: {content['position']['location']}",
        f"  Rate: {content['position']['currency']} {content['position']['rate_bill']}/hr bill, "
        f"{content['position']['currency']} {content['position']['rate_pay']}/hr pay",
        f"  Duration: {content['position']['duration_months']} months",
        f"  Required Skills: {', '.join(content['position']['skills_required'])}",
        "",
        "MATCH ASSESSMENT",
        f"  Score: {content['match']['score']}%",
        f"  Tier: {content['match']['tier']}",
        f"  Rationale: {content['match']['rationale']}",
    ]
    content["text"] = "\n".join(text_lines)
    return content


# ---------------------------------------------------------------------------
# Offer Letter Template
# ---------------------------------------------------------------------------

def generate_offer_letter(
    candidate_name: str,
    position_title: str,
    company_name: str,
    start_date: str,
    salary: str,
    location: str,
    is_remote: bool = False,
) -> dict[str, str]:
    """Generate an offer letter in HTML and plain text."""
    work_mode = "Remote" if is_remote else f"In-office ({location})"

    html = f"""
    <html><body style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 40px;">
    <div style="text-align: center; border-bottom: 2px solid #4f46e5; padding-bottom: 20px; margin-bottom: 30px;">
        <h1 style="color: #4f46e5; margin: 0;">{company_name}</h1>
        <p style="color: #6b7280; font-size: 12px;">LETTER OF OFFER</p>
    </div>
    <p>Date: {datetime.now(UTC).strftime("%B %d, %Y")}</p>
    <p>Dear <strong>{candidate_name}</strong>,</p>
    <p>We are pleased to offer you the position of <strong>{position_title}</strong> at <strong>{company_name}</strong>.</p>
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
        <tr><td style="padding: 8px; border-bottom: 1px solid #e5e7eb; font-weight: bold;">Position</td><td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{position_title}</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #e5e7eb; font-weight: bold;">Work Mode</td><td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{work_mode}</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #e5e7eb; font-weight: bold;">Compensation</td><td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{salary}</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #e5e7eb; font-weight: bold;">Start Date</td><td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{start_date}</td></tr>
    </table>
    <p>This offer is contingent upon successful completion of background verification and reference checks.</p>
    <p>Please sign below to accept this offer.</p>
    <br/><br/>
    <div style="border-top: 1px solid #ccc; width: 250px; padding-top: 5px;">
        <p style="font-size: 12px; color: #6b7280;">Authorized Signature</p>
    </div>
    </body></html>
    """

    text = (
        f"LETTER OF OFFER\n"
        f"{company_name}\n\n"
        f"Date: {datetime.now(UTC).strftime('%B %d, %Y')}\n\n"
        f"Dear {candidate_name},\n\n"
        f"We are pleased to offer you the position of {position_title} at {company_name}.\n\n"
        f"Position: {position_title}\n"
        f"Work Mode: {work_mode}\n"
        f"Compensation: {salary}\n"
        f"Start Date: {start_date}\n\n"
        f"This offer is contingent upon successful completion of background verification and reference checks.\n\n"
        f"Please sign below to accept this offer.\n\n\n"
        f"_________________________\n"
        f"Authorized Signature\n"
    )

    return {"html": html, "text": text, "title": f"Offer Letter - {position_title}"}
