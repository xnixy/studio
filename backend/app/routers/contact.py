from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import email_templates as templates
from app.config import Settings, get_settings
from app.database import get_session
from app.email_notify import safe_send_email
from app.models import ContactMessage
from app.rate_limit_deps import rate_limit_ip
from app.dependencies import get_client_ip
from app.schemas import ContactRequest, ContactResponse
from app.turnstile import verify_turnstile_token

router = APIRouter(prefix="/contact", tags=["contact"])


def _ops_recipients(settings: Settings) -> list[str]:
    raw = (settings.contact_notify_email or "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def submit_contact(
    payload: ContactRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ContactResponse:
    await rate_limit_ip(
        request,
        "contact",
        5,
        10 * 60,
        "Too many contact submissions. Please try again later.",
        require_redis=True,
    )
    await verify_turnstile_token(
        payload.turnstile_token,
        settings=settings,
        remote_ip=get_client_ip(request),
    )

    contact = ContactMessage(
        name=payload.name.strip(),
        email=payload.email.lower(),
        topic=payload.topic,
        message=payload.message.strip(),
    )
    session.add(contact)
    await session.commit()
    await session.refresh(contact)

    ops = _ops_recipients(settings)
    if ops:
        subject, body = templates.contact_ops_notify(
            name=contact.name,
            email=contact.email,
            topic=contact.topic,
            message=contact.message,
            contact_id=str(contact.id),
        )
        await safe_send_email(subject, body, ops, settings)

    ack_subject, ack_body = templates.contact_ack(name=contact.name)
    await safe_send_email(ack_subject, ack_body, contact.email, settings)

    return ContactResponse(
        id=contact.id,
        message="Message received. We read every message and reply as soon as we can.",
    )
