from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

import httpx

from app.config import Settings

SENDGRID_MAIL_SEND_URL = "https://api.sendgrid.com/v3/mail/send"


class EmailDeliveryError(RuntimeError):
    pass


def email_from_address(settings: Settings) -> str | None:
    """Resolved From address: SendGrid-specific override, then SMTP_FROM_EMAIL."""
    value = (settings.sendgrid_from_email or settings.smtp_from_email or "").strip()
    return value or None


def email_delivery_configured(settings: Settings) -> bool:
    """True when at least one delivery backend is fully configured."""
    from_email = email_from_address(settings)
    if not from_email:
        return False
    if settings.sendgrid_api_key:
        return True
    return bool(settings.smtp_host)


def _send_smtp_sync(subject: str, body: str, recipients: list[str], settings: Settings) -> None:
    from_email = email_from_address(settings)
    if not settings.smtp_host or not from_email:
        raise EmailDeliveryError("Email delivery is not configured")
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = ", ".join(recipients)
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as client:
            if settings.smtp_use_tls:
                client.starttls()
            if settings.smtp_username and settings.smtp_password:
                client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError(str(exc)) from exc


async def _send_sendgrid(
    subject: str,
    body: str,
    recipients: list[str],
    settings: Settings,
    *,
    html_body: str | None = None,
) -> None:
    from_email = email_from_address(settings)
    api_key = (settings.sendgrid_api_key or "").strip()
    if not api_key or not from_email:
        raise EmailDeliveryError("Email delivery is not configured")

    content: list[dict[str, str]] = [{"type": "text/plain", "value": body}]
    if html_body:
        content.append({"type": "text/html", "value": html_body})

    from_payload: dict[str, str] = {"email": from_email}
    name = (settings.sendgrid_from_name or "").strip()
    if name:
        from_payload["name"] = name

    payload = {
        "personalizations": [{"to": [{"email": email} for email in recipients]}],
        "from": from_payload,
        "subject": subject,
        "content": content,
        # Account-level click tracking rewrites every URL (including plain text)
        # through the branded tracker host (e.g. url8760.example.com/ls/click?upn=...).
        # That breaks verify and password-reset links when the branded
        # domain is misconfigured or when clients refuse the redirect. Transactional
        # mail must deliver the real destination URLs unchanged.
        "tracking_settings": {
            "click_tracking": {"enable": False, "enable_text": False},
            "open_tracking": {"enable": False},
        },
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(SENDGRID_MAIL_SEND_URL, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise EmailDeliveryError(f"SendGrid request failed: {exc}") from exc

    # SendGrid returns 202 Accepted on success with an empty body.
    if response.status_code not in {200, 202}:
        detail = (response.text or "").strip()
        if len(detail) > 400:
            detail = detail[:400] + "…"
        raise EmailDeliveryError(f"SendGrid error {response.status_code}: {detail or response.reason_phrase}")


async def send_email(
    subject: str,
    body: str,
    recipients: list[str],
    settings: Settings,
    *,
    html_body: str | None = None,
) -> None:
    """Send plain-text email (optional HTML) via SendGrid Web API, or SMTP fallback."""
    cleaned = [r.strip() for r in recipients if r and r.strip()]
    if not cleaned:
        return

    if not email_delivery_configured(settings):
        raise EmailDeliveryError("Email delivery is not configured")

    if settings.sendgrid_api_key:
        await _send_sendgrid(subject, body, cleaned, settings, html_body=html_body)
        return

    # SMTP path does not support HTML multipart unless we extend it; plain text only.
    await asyncio.to_thread(_send_smtp_sync, subject, body, cleaned, settings)
