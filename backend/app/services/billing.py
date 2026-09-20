"""Billing integration: Stripe and Razorpay payment processing.

Provides checkout sessions, subscription management, and webhook verification.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger("orcai.billing")
settings = get_settings()


# --- Stripe ---

def stripe_create_checkout(agency_id: int, price_id: str, success_url: str, cancel_url: str, trial_days: int = 14) -> dict[str, Any]:
    key = settings.STRIPE_SECRET_KEY
    if not key:
        return {"ok": False, "error": "stripe_not_configured"}
    payload = {
        "mode": "subscription",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "line_items": [{"price": price_id, "quantity": 1}],
        "metadata": {"agency_id": str(agency_id)},
        "subscription_data": {"trial_period_days": trial_days, "metadata": {"agency_id": str(agency_id)}},
    }
    try:
        resp = httpx.post("https://api.stripe.com/v1/checkout/sessions", data=payload, auth=(key, ""), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return {"ok": True, "session_id": data["id"], "url": data["url"]}
    except Exception as exc:
        logger.error("Stripe checkout error: %s", exc)
        return {"ok": False, "error": str(exc)}


def stripe_create_portal(customer_id: str, return_url: str) -> dict[str, Any]:
    key = settings.STRIPE_SECRET_KEY
    if not key:
        return {"ok": False, "error": "stripe_not_configured"}
    try:
        resp = httpx.post("https://api.stripe.com/v1/billing_portal/sessions",
                          data={"customer": customer_id, "return_url": return_url}, auth=(key, ""), timeout=15)
        resp.raise_for_status()
        return {"ok": True, "url": resp.json()["url"]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def stripe_cancel_subscription(subscription_id: str) -> dict[str, Any]:
    key = settings.STRIPE_SECRET_KEY
    if not key:
        return {"ok": False, "error": "stripe_not_configured"}
    try:
        resp = httpx.post(f"https://api.stripe.com/v1/subscriptions/{subscription_id}",
                          data={"cancel_at_period_end": "true"}, auth=(key, ""), timeout=15)
        resp.raise_for_status()
        return {"ok": True, "data": resp.json()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def stripe_verify_webhook(payload: bytes, signature: str) -> dict | None:
    secret = settings.STRIPE_WEBHOOK_SECRET
    if not secret:
        return None
    parts = {}
    for item in signature.split(","):
        k, v = item.split("=", 1)
        parts[k] = v
    ts = parts.get("t", "")
    msg = f"{ts}.".encode() + payload
    expected = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    if hmac.compare_digest(expected, parts.get("v1", "")):
        return json.loads(payload)
    return None


# --- Razorpay ---

def razorpay_create_subscription(agency_id: int, plan_id: str, email: str, name: str) -> dict[str, Any]:
    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET
    if not key_id or not key_secret:
        return {"ok": False, "error": "razorpay_not_configured"}
    try:
        cust = httpx.post("https://api.razorpay.com/v1/customers",
                          json={"email": email, "name": name, "notes": {"agency_id": str(agency_id)}},
                          auth=(key_id, key_secret), timeout=15)
        cust.raise_for_status()
        cid = cust.json()["id"]
    except Exception as exc:
        return {"ok": False, "error": f"customer creation failed: {exc}"}
    try:
        resp = httpx.post("https://api.razorpay.com/v1/subscriptions",
                          json={"plan_id": plan_id, "customer_id": cid, "total_count": 12,
                                "notes": {"agency_id": str(agency_id)}},
                          auth=(key_id, key_secret), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return {"ok": True, "subscription_id": data["id"], "short_url": data.get("short_url")}
    except Exception as exc:
        logger.error("Razorpay subscription error: %s", exc)
        return {"ok": False, "error": str(exc)}


def razorpay_cancel_subscription(subscription_id: str) -> dict[str, Any]:
    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET
    if not key_id or not key_secret:
        return {"ok": False, "error": "razorpay_not_configured"}
    try:
        resp = httpx.post(f"https://api.razorpay.com/v1/subscriptions/{subscription_id}/cancel",
                          auth=(key_id, key_secret), timeout=15)
        resp.raise_for_status()
        return {"ok": True, "data": resp.json()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def razorpay_verify_webhook(payload: bytes, signature: str, secret: str | None = None) -> dict | None:
    s = secret or settings.RAZORPAY_WEBHOOK_SECRET
    if not s:
        return None
    expected = hmac.new(s.encode(), payload, hashlib.sha256).hexdigest()
    if hmac.compare_digest(expected, signature):
        return json.loads(payload)
    return None
