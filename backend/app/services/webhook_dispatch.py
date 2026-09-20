"""Webhook dispatch service: sends event payloads to registered webhooks with HMAC signing."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import ipaddress
import json
import logging
import time
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.models.webhook import Webhook, WebhookDelivery

logger = logging.getLogger("orcai.webhooks")

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = [5, 30, 120]

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
]


def validate_webhook_url(url: str) -> bool:
    """Validate a webhook URL against SSRF risks.

    Returns True if the URL is safe to dispatch to, False otherwise.
    Blocks private/link-local IPs and non-HTTP/HTTPS schemes.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    if hostname == "169.254.169.254":
        return False

    try:
        resolved = ipaddress.ip_address(hostname)
    except ValueError:
        # hostname is a domain name, not an IP literal — allow
        return True

    for net in _BLOCKED_NETWORKS:
        if resolved in net:
            return False

    return True


def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    """Create HMAC-SHA256 signature for the payload."""
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


async def dispatch_event(db: Session, *, agency_id: int, event_type: str, payload: dict) -> list[dict]:
    """Find all active webhooks matching the event and dispatch payloads."""
    webhooks = db.query(Webhook).filter(
        Webhook.agency_id == agency_id,
        Webhook.is_active == True,  # noqa: E712
    ).all()

    results: list[dict] = []
    for wh in webhooks:
        if event_type in (wh.events or []):
            result = await _deliver(wh, event_type, payload, db)
            results.append(result)
    return results


async def _deliver(
    wh: Webhook,
    event_type: str,
    payload: dict,
    db: Session,
    retries: int = 0,
) -> dict:
    """Deliver a webhook payload with HMAC signature and retry logic."""
    body = json.dumps({"event": event_type, "data": payload}, default=str)
    payload_bytes = body.encode()
    signature = _sign_payload(payload_bytes, wh.secret)

    headers = {
        "Content-Type": "application/json",
        "X-ORCAI-Signature": signature,
        "X-ORCAI-Event": event_type,
    }

    start = time.monotonic()
    try:
        resp = httpx.post(wh.url, content=payload_bytes, headers=headers, timeout=15)
        duration_ms = int((time.monotonic() - start) * 1000)

        delivery = WebhookDelivery(
            webhook_id=wh.id,
            event_type=event_type,
            payload=payload,
            response_status=resp.status_code,
            response_body=resp.text[:2000],
            delivered_at=datetime.now(UTC).replace(tzinfo=None),
            duration_ms=duration_ms,
        )
        db.add(delivery)
        wh.last_triggered_at = datetime.now(UTC).replace(tzinfo=None)

        if resp.status_code >= 400:
            wh.failure_count += 1
            if retries < MAX_RETRIES:
                logger.warning(
                    "Webhook %s returned %d, retrying (%d/%d)",
                    wh.id, resp.status_code, retries + 1, MAX_RETRIES,
                )
                await asyncio.sleep(RETRY_DELAY_SECONDS[min(retries, len(RETRY_DELAY_SECONDS) - 1)])
                return await _deliver(wh, event_type, payload, db, retries=retries + 1)
            logger.error("Webhook %s failed after %d retries", wh.id, MAX_RETRIES)
            return {"ok": False, "webhook_id": wh.id, "status": resp.status_code}

        logger.info("Webhook %s delivered %s (%dms)", wh.id, event_type, duration_ms)
        return {"ok": True, "webhook_id": wh.id, "status": resp.status_code}

    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        wh.failure_count += 1
        delivery = WebhookDelivery(
            webhook_id=wh.id,
            event_type=event_type,
            payload=payload,
            response_status=None,
            response_body=str(exc)[:2000],
            delivered_at=datetime.now(UTC).replace(tzinfo=None),
            duration_ms=duration_ms,
        )
        db.add(delivery)
        logger.error("Webhook %s delivery error: %s", wh.id, exc)

        if retries < MAX_RETRIES:
            await asyncio.sleep(RETRY_DELAY_SECONDS[min(retries, len(RETRY_DELAY_SECONDS) - 1)])
            return await _deliver(wh, event_type, payload, db, retries=retries + 1)
        return {"ok": False, "webhook_id": wh.id, "error": str(exc)}
