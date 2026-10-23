"""admin_ops platform admin routes."""
from __future__ import annotations

from app.routers._admin_shared import *  # noqa: F403
from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/contacts", response_model=list[AdminContactDto])
async def list_contacts(
    limit: int = Query(default=200, ge=1, le=500),
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> list[AdminContactDto]:
    contacts = (
        await session.scalars(select(ContactMessage).order_by(ContactMessage.created_at.desc()).limit(limit))
    ).all()
    return [
        AdminContactDto(
            id=contact.id,
            name=contact.name,
            email=contact.email,
            topic=contact.topic,  # type: ignore[arg-type]
            message=contact.message,
            created_at=contact.created_at,
            resolved_at=getattr(contact, "resolved_at", None),
        )
        for contact in contacts
    ]


@router.post("/contacts/{contact_id}/resolve", response_model=AdminContactDto)
async def resolve_contact(
    contact_id: UUID,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> AdminContactDto:
    contact = await session.get(ContactMessage, contact_id)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    contact.resolved_at = _utcnow()
    await session.commit()
    await session.refresh(contact)
    return AdminContactDto(
        id=contact.id,
        name=contact.name,
        email=contact.email,
        topic=contact.topic,  # type: ignore[arg-type]
        message=contact.message,
        created_at=contact.created_at,
        resolved_at=contact.resolved_at,
    )


@router.get("/maintenance", response_model=MaintenanceStatus)
async def get_admin_maintenance(
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> MaintenanceStatus:
    setting = await session.get(MaintenanceSetting, 1)
    return MaintenanceStatus(enabled=setting.enabled if setting else False, message=setting.message if setting else None)


@router.post("/maintenance", response_model=MaintenanceStatus)
async def set_admin_maintenance(
    payload: MaintenanceUpdateRequest,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> MaintenanceStatus:
    setting = await session.get(MaintenanceSetting, 1)
    if setting is None:
        setting = MaintenanceSetting(id=1)
        session.add(setting)
    setting.enabled = payload.enabled
    setting.message = payload.message.strip() if payload.message and payload.message.strip() else None
    await session.commit()
    await session.refresh(setting)
    return MaintenanceStatus(enabled=setting.enabled, message=setting.message)
