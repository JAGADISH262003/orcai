"""SMS messaging via Twilio API."""

from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger("orcai.sms")
settings = get_settings()

TWILIO_API_URL = "https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"


def send_sms(to: str, body: str) -> dict:
    """Send an SMS via Twilio. Returns response dict."""
    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
    auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
    from_number = getattr(settings, "TWILIO_FROM_NUMBER", None)

    if not all([account_sid, auth_token, from_number]):
        logger.warning("Twilio not configured - SMS not sent to %s", to)
        return {"ok": False, "error": "twilio_not_configured"}

    url = TWILIO_API_URL.format(account_sid=account_sid)
    payload = {"To": to, "From": from_number, "Body": body}

    try:
        resp = httpx.post(url, data=payload, auth=(account_sid, auth_token), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        logger.info("SMS sent to %s: sid=%s", to, data.get("sid"))
        return {"ok": True, "sid": data.get("sid")}
    except Exception as exc:
        logger.error("SMS send failed to %s: %s", to, exc)
        return {"ok": False, "error": str(exc)}


def send_interview_reminder(to: str, candidate_name: str, job_title: str, interview_time: str) -> dict:
    body = (
        f"Hi {candidate_name}, this is a reminder about your interview for {job_title} "
        f"scheduled at {interview_time}. Please be prepared and join on time."
    )
    return send_sms(to, body)


def send_offer_update(to: str, candidate_name: str, job_title: str, status: str) -> dict:
    body = (
        f"Hi {candidate_name}, update on your offer for {job_title}: {status}. "
        f"Please check your portal for details."
    )
    return send_sms(to, body)


def send_status_change(to: str, candidate_name: str, entity_type: str, new_status: str) -> dict:
    body = (
        f"Hi {candidate_name}, the status of your {entity_type} has been updated to: {new_status}."
    )
    return send_sms(to, body)
