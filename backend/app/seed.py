"""Idempotent demo seeder. Run: python -m app.seed."""

import asyncio
from datetime import UTC

from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.core.workflows import entry_stage
from app.models import Agency, Client, Contract, Seeker, Subscription, User
from app.services.contract_parser import parse_contract_with_ai
from app.services.matcher import compute_match
from app.services.seeker_ingest import upsert_seeker

settings = get_settings()

DEMO_AGENCY = "taproot-consulting"
DEMO_EMAIL = "owner@taproot.io"
DEMO_PASSWORD = "Orcai@12345"

DEMO_CONTRACTS = [
    {
        "raw_text": (
            "Client: Wells Fargo. Role: Senior Java Fullstack Engineer. "
            "Requirements: Spring Boot, Angular, AWS. 8+ yrs exp. "
            "Rate: $85/hr bill rate. Immediate start. Location: Phoenix, AZ. Onsite."
        ),
        "client": "Wells Fargo",
    },
    {
        "raw_text": (
            "Client: JPMorgan Chase. Role: Senior Data Engineer. "
            "Requirements: Python, Pyspark, AWS, Snowflake, ETL. 6+ yrs exp. "
            "Rate: $90/hr bill, $65/hr pay. Remote. Duration 12 months."
        ),
        "client": "JPMorgan Chase",
    },
    {
        "raw_text": (
            "Client: Intuit. Role: AWS DevOps Lead. Requirements: AWS, Kubernetes, "
            "Terraform, CI/CD, Docker. 7+ yrs exp. Rate: $85/hr. Hybrid - Mountain View, CA."
        ),
        "client": "Intuit",
    },
]

DEMO_SEEKERS = [
    {
        "name": "Kiran Kumar",
        "email": "kiran.kumar@example.com",
        "phone": "+1 480 555 0114",
        "visa_status": "H1B",
        "location": "Phoenix, AZ",
        "headline": "Senior Java Fullstack Architect",
        "skills": ["java", "spring boot", "angular", "aws", "microservices"],
        "experience_years": 9.0,
        "summary": "9 years building enterprise insurance platforms.",
        "resume_text": "Senior Java Architect. 2015-2024 Wells Fargo. Skills: Java, Spring Boot, Angular, AWS, Microservices. H1B.",
    },
    {
        "name": "Priya Sharma",
        "email": "priya.sharma@example.com",
        "phone": "+1 646 555 0115",
        "visa_status": "OPT",
        "location": "Remote",
        "headline": "Senior Data Engineer",
        "skills": ["python", "pyspark", "aws", "snowflake", "etl", "sql"],
        "experience_years": 6.0,
        "summary": "Data platform engineering across fintech.",
        "resume_text": "Senior Data Engineer. 2018-2024 JPMorgan. Skills: Python, Pyspark, AWS, Snowflake, ETL. OPT.",
    },
    {
        "name": "Rahul Verma",
        "email": "rahul.verma@example.com",
        "phone": "+1 737 555 0116",
        "visa_status": "H1B",
        "location": "Mountain View, CA",
        "headline": "AWS DevOps Lead",
        "skills": ["aws", "kubernetes", "terraform", "ci/cd", "docker", "jenkins"],
        "experience_years": 8.0,
        "summary": "Platform / SRE engineering leader.",
        "resume_text": "AWS DevOps Lead. 2016-2024 Intuit. Skills: AWS, Kubernetes, Terraform, CI/CD, Docker. H1B.",
    },
    {
        "name": "Ananya Reddy",
        "email": "ananya.reddy@example.com",
        "phone": "+1 602 555 0117",
        "visa_status": "GC EAD",
        "location": "Phoenix, AZ",
        "headline": "React Native Engineer",
        "skills": ["react native", "typescript", "javascript", "react"],
        "experience_years": 5.0,
        "summary": "Mobile app engineer.",
        "resume_text": "React Native Engineer. Skills: React Native, TypeScript. GC EAD.",
    },
    {
        "name": "Venkat Rao",
        "email": "venkat.rao@example.com",
        "phone": "+1 212 555 0118",
        "visa_status": "GC EAD",
        "location": "Remote",
        "headline": "Cloud Migration Specialist",
        "skills": ["aws", "azure", "gcp", "terraform", "microservices"],
        "experience_years": 7.0,
        "summary": "Cloud migration consultant.",
        "resume_text": "Cloud migration specialist. 2019-2021 freelancing (client history unclear). "
        "AWS, Azure. Career break in 2021. GC EAD.",
    },
]


async def _seed() -> None:
    from datetime import datetime, timedelta

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        agency = db.query(Agency).filter(Agency.slug == DEMO_AGENCY).first()
        if agency is None:
            agency = Agency(name="TapRoot Consulting", slug=DEMO_AGENCY, tier="growth")
            db.add(agency)
            db.flush()
            db.add(
                Subscription(
                    agency_id=agency.id,
                    tier="growth",
                    price_per_month=14999,
                    billing_cycle_start=datetime.now(UTC).date(),
                    billing_cycle_end=datetime.now(UTC).date() + timedelta(days=30),
                    status="active",
                    seats=15,
                )
            )
            db.add(
                User(
                    agency_id=agency.id,
                    email=DEMO_EMAIL,
                    name="Owner Demo",
                    hashed_password=hash_password(DEMO_PASSWORD),
                    role="owner",
                    is_active=True,
                )
            )
            db.commit()
            print(f"Created demo agency '{DEMO_AGENCY}' user {DEMO_EMAIL} / {DEMO_PASSWORD}")
        agency.ensure_workflow_config()
        db.flush()

        # Clients
        client_map: dict[str, Client] = {}
        for data in DEMO_CONTRACTS:
            cname = data["client"]
            client = db.query(Client).filter(Client.agency_id == agency.id, Client.name == cname).first()
            if client is None:
                client = Client(agency_id=agency.id, name=cname)
                db.add(client)
                db.flush()
            client_map[cname] = client

        # Contracts
        for data in DEMO_CONTRACTS:
            client = client_map[data["client"]]
            existing = (
                db.query(Contract)
                .filter(Contract.agency_id == agency.id, Contract.client_id == client.id)
                .first()
            )
            if existing:
                continue
            parsed = await parse_contract_with_ai(data["raw_text"])
            contract = Contract(
                agency_id=agency.id,
                client_id=client.id,
                raw_text=data["raw_text"],
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
            print(f"  + contract: {contract.title}")

        # Seekers
        for data in DEMO_SEEKERS:
            upsert_seeker(
                db,
                agency.id,
                data,
                source="inbound" if data["name"] == "Venkat Rao" else "manual",
                source_channel="whatsapp" if data["name"] == "Venkat Rao" else "manual",
                consent_basis="explicit_opt_in",
            )
            print(f"  + seeker: {data['name']}")

        # Matching
        contracts = db.query(Contract).filter(Contract.agency_id == agency.id).all()
        seekers = db.query(Seeker).filter(Seeker.agency_id == agency.id).all()
        from app.models.match import Match

        for contract in contracts:
            for seeker in seekers:
                result = compute_match(contract, seeker, entry_status=entry_stage(agency.workflow_type))
                existing = (
                    db.query(Match)
                    .filter(Match.contract_id == contract.id, Match.seeker_id == seeker.id)
                    .first()
                )
                if existing:
                    continue
                db.add(
                    Match(
                        agency_id=agency.id,
                        contract_id=contract.id,
                        seeker_id=seeker.id,
                        score=result["score"],
                        tier=result["tier"],
                        status=result["default_status"],
                        hitl_required=result["hitl_required"],
                        hitl_status=(
                            "pending_review" if result["hitl_required"] else None
                        ),
                        rationale=result["rationale"],
                    )
                )
        db.commit()
        print("  + matches computed")
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(_seed())
