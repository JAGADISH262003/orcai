"""WhatsApp Cloud API and Telegram Bot API outbound messaging.

Sends real messages to candidates/clients via configured channels.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger("orcai.messaging")
settings = get_settings()


# ---------------------------------------------------------------------------
# WhatsApp Cloud API
# ---------------------------------------------------------------------------

def send_whatsapp_message(
    to_phone: str,
    text: str,
    template_name: str | None = None,
    template_vars: dict[str, str] | None = None,
) -> dict:
    """Send a WhatsApp message via the Cloud API. Returns response dict."""
    phone_id = settings.WHATSAPP_PHONE_NUMBER_ID
    if not phone_id:
        logger.warning("WhatsApp not configured — message not sent to %s", to_phone)
        return {"ok": False, "error": "whatsapp_not_configured"}

    token = settings.WHATSAPP_APP_SECRET or settings.WHATSAPP_VERIFY_TOKEN
    if not token:
        return {"ok": False, "error": "whatsapp_token_missing"}

    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    if template_name:
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
                "components": [],
            },
        }
        if template_vars:
            payload["template"]["components"].append({
                "type": "body",
                "parameters": [{"type": "text", "text": v} for v in template_vars.values()],
            })
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"body": text},
        }

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        logger.info("WhatsApp sent to %s: %s", to_phone, data.get("messages", [{}])[0].get("id"))
        return {"ok": True, "message_id": data.get("messages", [{}])[0].get("id")}
    except Exception as exc:
        logger.error("WhatsApp send failed to %s: %s", to_phone, exc)
        return {"ok": False, "error": str(exc)}


def send_whatsapp_template(
    to_phone: str,
    template_name: str,
    language: str = "en",
    vars: list[str] | None = None,
) -> dict:
    phone_id = settings.WHATSAPP_PHONE_NUMBER_ID
    token = settings.WHATSAPP_APP_SECRET or settings.WHATSAPP_VERIFY_TOKEN
    if not phone_id or not token:
        return {"ok": False, "error": "whatsapp_not_configured"}

    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    components = []
    if vars:
        components.append({"type": "body", "parameters": [{"type": "text", "text": v} for v in vars]})

    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "template",
        "template": {"name": template_name, "language": {"code": language}, "components": components},
    }
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        return {"ok": True, "data": resp.json()}
    except Exception as exc:
        logger.error("WhatsApp template failed: %s", exc)
        return {"ok": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Telegram Bot API
# ---------------------------------------------------------------------------

def send_telegram_message(
    chat_id: str | int,
    text: str,
    parse_mode: str = "HTML",
    reply_markup: dict | None = None,
) -> dict:
    """Send a Telegram message via Bot API. Returns response dict."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("Telegram not configured — message not sent to %s", chat_id)
        return {"ok": False, "error": "telegram_not_configured"}

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        resp = httpx.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        msg_id = data.get("result", {}).get("message_id")
        logger.info("Telegram sent to %s: msg_id=%s", chat_id, msg_id)
        return {"ok": True, "message_id": msg_id}
    except Exception as exc:
        logger.error("Telegram send failed to %s: %s", chat_id, exc)
        return {"ok": False, "error": str(exc)}


def send_telegram_keyboard(
    chat_id: str | int,
    text: str,
    buttons: list[list[dict]],
) -> dict:
    reply_markup = {"inline_keyboard": buttons}
    return send_telegram_message(chat_id, text, reply_markup=reply_markup)


def answer_telegram_callback(callback_query_id: str, text: str, show_alert: bool = False) -> dict:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return {"ok": False}
    url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
    try:
        resp = httpx.post(url, json={
            "callback_query_id": callback_query_id,
            "text": text,
            "show_alert": show_alert,
        }, timeout=10)
        return resp.json()
    except Exception as exc:
        logger.error("Telegram callback answer failed: %s", exc)
        return {"ok": False}
