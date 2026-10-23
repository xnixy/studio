from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import MaintenanceSetting, User
from app.security import hash_password


async def seed_data(session: AsyncSession, settings: Settings) -> None:
    maintenance = await session.get(MaintenanceSetting, 1)
    if maintenance is None:
        session.add(
            MaintenanceSetting(
                id=1,
                enabled=False,
                message="The site is currently under maintenance. Please check back soon.",
            )
        )

    admin_email = settings.seed_admin_email.strip().lower()
    admin = await session.scalar(select(User).where(User.email == admin_email))
    now = datetime.now(timezone.utc)
    if admin is None:
        admin_password = settings.seed_admin_password
        if not admin_password and not settings.is_production:
            admin_password = "Admin123!"
        if not admin_password:
            raise RuntimeError("SEED_ADMIN_PASSWORD must be configured outside development")

        session.add(
            User(
                email=admin_email,
                password_hash=hash_password(admin_password),
                full_name="Administrator",
                role="admin",
                permissions={},
                email_verified_at=now,
            )
        )
    elif getattr(admin, "email_verified_at", None) is None:
        # Seed admin must always be able to sign in after email verification gate.
        admin.email_verified_at = now

    await session.commit()
