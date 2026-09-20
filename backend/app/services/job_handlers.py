"""Job handlers: one function per background work type.

Each handler receives its own DB session and a claimed `Job`; it performs the
work described by `job.params` and returns a JSON-serializable result dict.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.workflows import DEFAULT_WORKFLOW, entry_stage
from app.models.agency import Agency
from app.models.client import Client
from app.models.contract import Contract
from app.models.inbound import InboundMessage
from app.models.job import Job
from app.models.match import Match
from app.models.seeker import Seeker
from app.services.contract_parser import parse_contract_with_ai
from app.services.inbound import process_inbound
from app.services.jobs import register_handler
from app.services.matcher import compute_match
from app.services.resume_parser import extract_text, parse_resume_text
from app.services.seeker_ingest import upsert_seeker

logger = logging.getLogger("orcai.jobs")
settings = get_settings()

_DEFAULT_ENTRY = entry_stage(DEFAULT_WORKFLOW)


@register_handler("contract.parse")
async def contract_parse_job(db: Session, job: Job) -> dict:
    p = job.params
    agency_id = int(p["agency_id"])
    client = None
    if p.get("client_id"):
        client = db.get(Client, int(p["client_id"]))
        if client is None or client.agency_id != agency_id:
            raise ValueError("client not found")
    elif p.get("client_name"):
        name = p["client_name"].strip()
        client = (
            db.query(Client)
            .filter(Client.agency_id == agency_id, Client.name.ilike(f"%{name}%"))
            .first()
        )
        if client is None:
            client = Client(agency_id=agency_id, name=name)
            db.add(client)
            db.flush()

    parsed = await parse_contract_with_ai(p["raw_text"])
    contract = Contract(
        agency_id=agency_id,
        client_id=client.id if client else None,
        raw_text=p["raw_text"],
        title=parsed["title"],
        status="active",
        location=parsed["location"],
        is_remote=parsed["is_remote"],
        duration_months=parsed["duration_months"],
        rate_bill=parsed["rate_bill"],
        rate_pay=parsed["rate_pay"],
        currency=parsed["currency"],
        experience_min=parsed["experience_min"],
        openings=parsed["openings"],
        skills=parsed["skills"],
        ai_summary=parsed["ai_summary"],
        parse_method=parsed["parse_method"],
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    logger.info("contract %s parsed via %s", contract.id, parsed["parse_method"])
    return {"contract_id": contract.id, "client_id": contract.client_id, "title": contract.title}


@register_handler("seeker.import")
def seeker_import_job(db: Session, job: Job) -> dict:
    p = job.params
    agency_id = int(p["agency_id"])
    path = Path(p["path"])
    if not path.exists():
        raise FileNotFoundError(f"uploaded file missing: {path}")
    content = path.read_bytes()
    resume_text = extract_text(p.get("filename", "resume.txt"), content)
    if not resume_text.strip():
        raise ValueError("could not extract text from file")

    parsed = parse_resume_text(resume_text)
    if p.get("visa_status"):
        parsed["visa_status"] = p["visa_status"]
    parsed["resume_text"] = resume_text

    seeker, created = upsert_seeker(
        db,
        agency_id,
        parsed,
        source="import",
        source_channel=p.get("source_channel") or f"file:{p.get('filename', 'resume')}",
        consent_channel="file_upload",
        consent_basis="affidavit",
    )
    seeker.resume_path = str(path)
    db.commit()
    db.refresh(seeker)
    return {"seeker_id": seeker.id, "created": created}


@register_handler("matching.run")
def matching_run_job(db: Session, job: Job) -> dict:
    p = job.params
    agency_id = int(p["agency_id"])
    contract_id = p.get("contract_id")
    agency = db.get(Agency, agency_id)
    entry_status = entry_stage(agency.workflow_type) if agency else _DEFAULT_ENTRY

    def compute_for(contract: Contract) -> None:
        seekers = (
            db.query(Seeker)
            .filter(Seeker.agency_id == agency_id, Seeker.is_active)
            .all()
        )
        for seeker in seekers:
            result = compute_match(contract, seeker, entry_status=entry_status)
            match = (
                db.query(Match)
                .filter(Match.contract_id == contract.id, Match.seeker_id == seeker.id)
                .first()
            )
            if match is None:
                match = Match(agency_id=agency_id, contract_id=contract.id, seeker_id=seeker.id)
                db.add(match)
            match.score = result["score"]
            match.tier = result["tier"]
            match.hitl_required = result["hitl_required"]
            match.rationale = result["rationale"]
            match.status = result["default_status"]
            if match.hitl_required:
                match.hitl_status = "pending_review"

    if contract_id:
        contract = db.get(Contract, contract_id)
        if contract is None or contract.agency_id != agency_id:
            raise ValueError("contract not found")
        compute_for(contract)
    else:
        contracts = (
            db.query(Contract)
            .filter(Contract.agency_id == agency_id, Contract.status == "active")
            .all()
        )
        for c in contracts:
            compute_for(c)

    db.commit()
    total = db.query(Match).filter(Match.agency_id == agency_id).count()
    return {"matches": total, "contract_id": contract_id}


@register_handler("inbound.ingest")
def inbound_ingest_job(db: Session, job: Job) -> dict:
    p = job.params
    agency = db.get(Agency, int(p["agency_id"]))
    if agency is None:
        raise ValueError("agency not found")
    msg = InboundMessage(
        agency_id=agency.id,
        channel=p["channel"],
        external_id=p.get("external_id"),
        phone_number=p.get("phone_number"),
        sender_name=p.get("sender_name"),
        body=p.get("body", ""),
        received_at=datetime.now(UTC),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    msg = process_inbound(db, agency, msg)
    return {
        "inbound_id": msg.id,
        "seeker_id": msg.seeker_id,
        "status": msg.status,
    }


@register_handler("campaign.send")
def campaign_send_job(db: Session, job: Job) -> dict:
    p = job.params
    campaign_id = int(p["campaign_id"])
    from app.models.campaign import Campaign, CampaignRecipient
    from app.services.email_delivery import send_email
    from app.services.messaging import send_telegram_message, send_whatsapp_message
    from app.services.sms import send_sms

    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise ValueError("campaign not found")

    queued = (
        db.query(CampaignRecipient)
        .filter(
            CampaignRecipient.campaign_id == campaign_id,
            CampaignRecipient.status == "queued",
        )
        .all()
    )

    sent = 0
    for r in queued:
        seeker = db.get(Seeker, r.seeker_id)
        if seeker is None:
            r.status = "bounced"
            continue

        subject = campaign.template_subject or campaign.name or "Message from ORCAI"
        body = campaign.template_body or ""

        # Personalize template
        name = seeker.name or "Candidate"
        body = body.replace("{name}", name).replace("{company}", "").replace("{role}", "")
        subject = subject.replace("{name}", name)

        ok = False
        if campaign.channel == "email" and seeker.email:
            ok = send_email(to=seeker.email, subject=subject, body_html=f"<p>{body}</p>")
        elif campaign.channel == "sms" and seeker.phone:
            ok = send_sms(to=seeker.phone, body=body)
        elif campaign.channel == "whatsapp" and seeker.phone:
            result = send_whatsapp_message(to_phone=seeker.phone, text=body)
            ok = result.get("ok", False)
        elif campaign.channel == "telegram" and seeker.phone:
            result = send_telegram_message(chat_id=seeker.phone, text=body)
            ok = result.get("ok", False)

        if ok:
            r.status = "sent"
            r.sent_at = datetime.now(UTC)
            campaign.sent_count += 1
            sent += 1
        else:
            r.status = "bounced"

    if not queued:
        campaign.status = "completed"

    db.commit()
    return {"campaign_id": campaign_id, "sent": sent, "total": len(queued)}


@register_handler("scrape.jobs")
def scrape_jobs_job(db: Session, job: Job) -> dict:
    p = job.params
    from app.services.scraper_jobs import scrape_jobs
    results = scrape_jobs(
        source=p["source"],
        query=p.get("query", ""),
        location=p.get("location"),
        url=p.get("url"),
        feed_url=p.get("feed_url"),
        max_results=p.get("max_results", 25),
        country=p.get("country", "us"),
    )
    return {"scraped": len(results), "jobs": results}


@register_handler("scrape.candidates")
def scrape_candidates_job(db: Session, job: Job) -> dict:
    p = job.params
    from app.services.scraper_candidates import scrape_candidates
    results = scrape_candidates(
        source=p["source"],
        query=p.get("query", ""),
        location=p.get("location"),
        url=p.get("url"),
        max_results=p.get("max_results", 25),
        language=p.get("language"),
    )
    return {"scraped": len(results), "candidates": results}
