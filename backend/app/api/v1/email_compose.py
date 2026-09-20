from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.models.email_message import EmailMessage
from app.services.email_delivery import send_email

router = APIRouter(prefix="/email", tags=["email"])

EMAIL_TEMPLATES = [
    {"name": "invite", "description": "Invite a new team member", "variables": ["agency_name", "role", "temp_password"]},
    {"name": "password_reset", "description": "Password reset request", "variables": ["reset_token"]},
    {"name": "interview_scheduled", "description": "Interview scheduled notification", "variables": ["candidate_name", "interview_date", "meeting_link"]},
    {"name": "offer_letter", "description": "Job offer letter", "variables": ["candidate_name", "position", "company_name"]},
    {"name": "follow_up", "description": "Follow-up email", "variables": ["candidate_name", "position", "agency_name"]},
]


class EmailSendIn(BaseModel):
    to: str
    subject: str
    body_html: str
    body_text: str | None = None
    template_name: str | None = None
    related_entity_type: str | None = None
    related_entity_id: int | None = None


class EmailPreviewIn(BaseModel):
    template_name: str
    variables: dict[str, str] = {}


def _out(em: EmailMessage) -> dict[str, Any]:
    return {
        "id": em.id,
        "agency_id": em.agency_id,
        "user_id": em.user_id,
        "to_email": em.to_email,
        "to_name": em.to_name,
        "subject": em.subject,
        "body_html": em.body_html,
        "body_text": em.body_text,
        "template_name": em.template_name,
        "template_vars": em.template_vars,
        "status": em.status,
        "sent_at": em.sent_at.isoformat() if em.sent_at else None,
        "related_entity_type": em.related_entity_type,
        "related_entity_id": em.related_entity_id,
        "created_at": em.created_at.isoformat() if em.created_at else None,
    }


@router.post("/send", status_code=201)
def send_email_endpoint(
    data: EmailSendIn,
    user: CurrentUser,
    db: DbDep,
) -> dict[str, Any]:
    success = send_email(
        to=data.to,
        subject=data.subject,
        body_html=data.body_html,
        body_text=data.body_text,
    )
    em = EmailMessage(
        agency_id=user.agency_id,
        user_id=user.id,
        to_email=data.to,
        subject=data.subject,
        body_html=data.body_html,
        body_text=data.body_text,
        template_name=data.template_name,
        status="sent" if success else "failed",
        sent_at=datetime.now(UTC) if success else None,
        related_entity_type=data.related_entity_type,
        related_entity_id=data.related_entity_id,
    )
    db.add(em)
    db.commit()
    db.refresh(em)
    return _out(em)


@router.get("/history")
def list_email_history(
    user: CurrentUser,
    db: DbDep,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    q = select(EmailMessage).where(EmailMessage.agency_id == user.agency_id)
    if status:
        q = q.where(EmailMessage.status == status)
    q = q.order_by(EmailMessage.created_at.desc()).limit(limit).offset(offset)
    return [_out(r) for r in db.scalars(q).all()]


@router.get("/templates")
def list_templates() -> list[dict[str, Any]]:
    return EMAIL_TEMPLATES


@router.post("/preview")
def preview_email(data: EmailPreviewIn) -> dict[str, str]:
    template = next((t for t in EMAIL_TEMPLATES if t["name"] == data.template_name), None)
    if not template:
        raise HTTPException(404, "Template not found")
    placeholders = {v: f"{{{{{v}}}}}" for v in template["variables"]}
    preview_vars = {**placeholders, **data.variables}
    body = f"Template: {data.template_name}\nVariables: {preview_vars}"
    return {"subject": f"[Preview] {data.template_name}", "body": body}
