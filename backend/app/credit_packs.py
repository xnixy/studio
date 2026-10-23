"""Credit pack DTOs and grant mapping helpers (shared by billing routes)."""
from __future__ import annotations

from app.config import Settings
from app.models import BillingCreditGrant
from app.plans import CREDIT_PACK_CATALOG
from app.schemas import BillingCreditGrantDto, CreditPackDto


def map_credit_grant(row: BillingCreditGrant) -> BillingCreditGrantDto:
    return BillingCreditGrantDto(
        id=row.id,
        workspace_id=row.workspace_id,
        pack_name=row.pack_name,
        label=row.label,
        grants=dict(row.grants or {}),
        amount_cents=row.amount_cents,
        status=row.status,  # type: ignore[arg-type]
        period_start=row.period_start,
        period_end=row.period_end,
        created_at=row.created_at,
    )


def pack_dtos(settings: Settings) -> list[CreditPackDto]:
    configured = settings.stripe_pack_price_ids
    return [
        CreditPackDto(
            name=pack.name,  # type: ignore[arg-type]
            label=pack.label,
            description=pack.description,
            price_cents=pack.price_cents,
            grants=dict(pack.grants),
            stripe_configured=bool(settings.stripe_secret_key and configured.get(pack.name)),
        )
        for pack in CREDIT_PACK_CATALOG
    ]
