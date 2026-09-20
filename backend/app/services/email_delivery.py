"""Email delivery service: SMTP-based email sending with templates.

Supports:
  - Transactional emails (invite, password reset, notifications)
  - Bulk candidate outreach
  - HTML + plain text templates
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings

logger = logging.getLogger("orcai.email")
settings = get_settings()


def _get_smtp():
    if not settings.SMTP_HOST:
        return None
    return smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)


def send_email(
    to: str | list[str],
    subject: str,
    body_html: str,
    body_text: str | None = None,
    from_addr: str | None = None,
    reply_to: str | None = None,
) -> bool:
    """Send an email via SMTP. Returns True on success, False on failure."""
    host = settings.SMTP_HOST
    if not host:
        logger.warning("SMTP not configured — email not sent to %s", to)
        return False

    recipients = [to] if isinstance(to, str) else to
    from_addr = from_addr or settings.SMTP_FROM

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(recipients)
    if reply_to:
        msg["Reply-To"] = reply_to

    if body_text:
        msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        server = smtplib.SMTP(host, settings.SMTP_PORT)
        if settings.SMTP_TLS:
            server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(from_addr, recipients, msg.as_string())
        server.quit()
        logger.info("Email sent to %s: %s", recipients, subject)
        return True
    except Exception as exc:
        logger.error("Email send failed to %s: %s", recipients, exc)
        return False


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

_INVITE_HTML = """
<html><body style="font-family: sans-serif; max-width: 500px; margin: 0 auto;">
<h2 style="color: #4f46e5;">Welcome to ORCAI</h2>
<p>You've been invited to join <strong>{agency_name}</strong> as a <strong>{role}</strong>.</p>
<p>Your temporary password: <code style="background: #f3f4f6; padding: 4px 8px; border-radius: 4px;">{temp_password}</code></p>
<p><a href="{login_url}" style="background: #4f46e5; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none;">Log in to ORCAI</a></p>
<p style="color: #6b7280; font-size: 12px;">This password is temporary. Please change it after your first login.</p>
</body></html>
"""

_RESET_HTML = """
<html><body style="font-family: sans-serif; max-width: 500px; margin: 0 auto;">
<h2 style="color: #4f46e5;">Password Reset Request</h2>
<p>We received a request to reset your password for your ORCAI account.</p>
<p>Your reset token: <code style="background: #f3f4f6; padding: 4px 8px; border-radius: 4px;">{reset_token}</code></p>
<p><a href="{reset_url}" style="background: #4f46e5; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none;">Reset Password</a></p>
<p style="color: #6b7280; font-size: 12px;">This token expires in 1 hour. If you didn't request this, ignore this email.</p>
</body></html>
"""

_NOTIFICATION_HTML = """
<html><body style="font-family: sans-serif; max-width: 500px; margin: 0 auto;">
<h2 style="color: #4f46e5;">{title}</h2>
<p>{message}</p>
{action_html}
</body></html>
"""


def send_invite_email(
    to_email: str,
    agency_name: str,
    role: str,
    temp_password: str,
    login_url: str | None = None,
) -> bool:
    if login_url is None:
        from app.core.config import get_settings
        s = get_settings()
        login_url = s.cors_origins[0] + "/login" if s.cors_origins else "http://localhost:3000/login"
    html = _INVITE_HTML.format(
        agency_name=agency_name,
        role=role,
        temp_password=temp_password,
        login_url=login_url,
    )
    return send_email(to_email, f"You're invited to {agency_name} on ORCAI", html)


def send_password_reset_email(
    to_email: str,
    reset_token: str,
    reset_url: str | None = None,
) -> bool:
    if reset_url is None:
        from app.core.config import get_settings
        s = get_settings()
        reset_url = s.cors_origins[0] + "/reset" if s.cors_origins else "http://localhost:3000/reset"
    html = _RESET_HTML.format(reset_token=reset_token, reset_url=reset_url)
    return send_email(to_email, "ORCAI — Password Reset Request", html)


def send_notification_email(
    to_email: str,
    title: str,
    message: str,
    action_url: str | None = None,
    action_label: str = "View Details",
) -> bool:
    action_html = ""
    if action_url:
        action_html = f'<p><a href="{action_url}" style="background: #4f46e5; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none;">{action_label}</a></p>'
    html = _NOTIFICATION_HTML.format(title=title, message=message, action_html=action_html)
    return send_email(to_email, f"ORCAI — {title}", html)
