"""iOS In-App Purchase catalog + purchase confirmation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.exc import IntegrityError

from app.apple_iap import (
    AppleIapError,
    decode_transaction_jws,
    fetch_transaction_info,
    period_end_from_tx_info,
    tx_is_revoked,
)
from app.config import Settings, get_settings
from app.database import get_session
from app.dependencies import get_current_user
from app.iap_catalog import default_iap_catalog, product_by_apple_id
from app.models import BillingCreditGrant, IapTransaction, Subscription, User
from app.plans import plan_for
from app.routers.billing import fulfill_credit_pack
from app.routers._platform_shared import audit
from app.workspace_access import billing_workspace, get_subscription, require_permission

router = APIRouter(prefix="/billing/iap", tags=["iap"])


class IapProductDto(BaseModel):
    apple_product_id: str
    kind: Literal["plan", "pack"]
    sku: str
    title: str
    description: str
    store_type: Literal["subscription", "consumable"]
    price_cents: int


class IapConfirmRequest(BaseModel):
    workspace_id: UUID
    apple_product_id: str = Field(min_length=3, max_length=120)
    transaction_id: str = Field(min_length=3, max_length=64)
    """StoreKit 2 signed transaction JWS when available (not trusted alone in production)."""
    signed_transaction: str | None = Field(default=None, max_length=20000)


class IapConfirmResponse(BaseModel):
    ok: bool
    kind: str
    sku: str
    message: str
    already_processed: bool = False


@router.get("/products", response_model=list[IapProductDto])
async def list_iap_products(
    _: User = Depends(get_current_user),
) -> list[IapProductDto]:
    return [
        IapProductDto(
            apple_product_id=p.apple_product_id,
            kind=p.kind,
            sku=p.sku,
            title=p.title,
            description=p.description,
            store_type=p.store_type,
            price_cents=p.price_cents,
        )
        for p in default_iap_catalog()
    ]


@router.post("/confirm", response_model=IapConfirmResponse)
async def confirm_iap_purchase(
    payload: IapConfirmRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> IapConfirmResponse:
    root = await billing_workspace(session, payload.workspace_id)
    await require_permission(session, root.id, user, "billing.manage")

    product = product_by_apple_id(payload.apple_product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown Apple product")

    existing = await session.scalar(
        select(IapTransaction).where(IapTransaction.transaction_id == payload.transaction_id.strip())
    )
    if existing is not None:
        return IapConfirmResponse(
            ok=True,
            kind=existing.kind,
            sku=existing.sku,
            message="Purchase already applied",
            already_processed=True,
        )

    tx_info = await _resolve_transaction(
        settings,
        transaction_id=payload.transaction_id.strip(),
        expected_product_id=product.apple_product_id,
    )
    if tx_is_revoked(tx_info):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This Apple transaction was revoked or refunded",
        )
    period_end = period_end_from_tx_info(tx_info)

    if product.kind == "pack":
        await _fulfill_pack(
            session,
            workspace_id=root.id,
            pack_name=product.sku,
            transaction_id=payload.transaction_id.strip(),
            user_id=user.id,
        )
    else:
        await _fulfill_plan(
            session,
            workspace_id=root.id,
            plan_name=product.sku,
            original_transaction_id=str(tx_info.get("originalTransactionId") or payload.transaction_id),
            period_end=period_end,
        )

    session.add(
        IapTransaction(
            transaction_id=payload.transaction_id.strip(),
            original_transaction_id=str(tx_info.get("originalTransactionId") or "") or None,
            apple_product_id=product.apple_product_id,
            kind=product.kind,
            sku=product.sku,
            workspace_id=root.id,
            user_id=user.id,
            environment=str(tx_info.get("environment") or "Sandbox"),
            raw_payload=tx_info,
        )
    )
    await audit(
        session,
        root.id,
        user.id,
        "billing.iap_confirmed",
        kind=product.kind,
        sku=product.sku,
        transaction_id=payload.transaction_id.strip(),
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing_race = await session.scalar(
            select(IapTransaction).where(IapTransaction.transaction_id == payload.transaction_id.strip())
        )
        if existing_race is not None:
            return IapConfirmResponse(
                ok=True,
                kind=existing_race.kind,
                sku=existing_race.sku,
                message="Purchase already applied",
                already_processed=True,
            )
        raise
    return IapConfirmResponse(
        ok=True,
        kind=product.kind,
        sku=product.sku,
        message=f"{product.title} applied",
        already_processed=False,
    )


async def _resolve_transaction(
    settings: Settings,
    *,
    transaction_id: str,
    expected_product_id: str,
) -> dict[str, Any]:
    """Verify purchases via App Store Server API only.

    Client-supplied JWS is never trusted for fulfillment (signature is not verified
    without the Apple cert chain). Dev-only unverified mode requires both
    APPLE_IAP_ALLOW_UNVERIFIED and a non-production APP_ENV.
    """
    has_creds = bool(
        settings.apple_iap_key_id and settings.apple_iap_issuer_id and settings.apple_iap_private_key
    )
    if has_creds:
        try:
            info = await fetch_transaction_info(settings, transaction_id)
        except AppleIapError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    elif settings.apple_iap_allow_unverified and not settings.is_production:
        info = {
            "transactionId": transaction_id,
            "productId": expected_product_id,
            "environment": "Xcode",
            "unverified": True,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Apple IAP verification is not configured",
        )

    product_id = str(info.get("productId") or info.get("product_id") or "")
    if product_id and product_id != expected_product_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction product does not match purchase",
        )
    tid = str(info.get("transactionId") or info.get("transaction_id") or "")
    if tid and tid != transaction_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction id does not match purchase",
        )
    return info


async def _fulfill_pack(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    pack_name: str,
    transaction_id: str,
    user_id: UUID,
) -> None:
    grant = await fulfill_credit_pack(
        session,
        workspace_id=workspace_id,
        pack_name=pack_name,
        checkout_session_id=f"iap:{transaction_id}",
        customer_id=None,
        user_id=user_id,
    )
    if grant is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not grant pack")


async def _fulfill_plan(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    plan_name: str,
    original_transaction_id: str,
    period_end: datetime | None = None,
) -> None:
    plan = plan_for(plan_name)
    if plan.price_monthly <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan")
    sub = await get_subscription(session, workspace_id, lock=True)
    sub.plan = plan.name
    sub.status = "active"
    now = datetime.now(timezone.utc)
    sub.current_period_start = now
    sub.current_period_end = period_end or (now + timedelta(days=31))
    # Durable Apple subscription key (renewals keep the same originalTransactionId).
    # Do not overwrite a real Stripe subscription id if one is already present.
    apple_key = f"apple:{original_transaction_id}"[:255]
    if not sub.stripe_subscription_id or str(sub.stripe_subscription_id).startswith("apple:"):
        sub.stripe_subscription_id = apple_key
    sub.cancel_at_period_end = False


class AppleNotificationBody(BaseModel):
    """App Store Server Notifications V2 body."""

    signedPayload: str = Field(min_length=20, max_length=500_000)


async def _refund_iap_pack_grant(
    session: AsyncSession,
    *,
    transaction_id: str,
    original_transaction_id: str,
) -> None:
    """Mark the matching Apple pack grant refunded so unused credits drop off."""
    keys = [
        f"iap:{tid}"
        for tid in (transaction_id, original_transaction_id)
        if (tid or "").strip()
    ]
    if not keys:
        return
    rows = (
        await session.scalars(
            select(BillingCreditGrant).where(
                BillingCreditGrant.stripe_checkout_session_id.in_(keys),
                BillingCreditGrant.status == "active",
            )
        )
    ).all()
    for grant in rows:
        grant.status = "refunded"


@router.post("/notifications", include_in_schema=False)
async def apple_iap_notifications(
    payload: AppleNotificationBody,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Handle App Store Server Notifications V2 (renew / expire / refund / revoke).

    Configure this URL in App Store Connect:
      Production: https://api.example.com/api/billing/iap/notifications
      Sandbox:    same URL (handler accepts both environments)

    signedPayload and nested signedTransactionInfo are verified against Apple's
    x5c chain (Apple Root CA - G3). Unverified payloads are rejected.
    """
    try:
        outer = decode_transaction_jws(payload.signedPayload)
    except AppleIapError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid notification payload: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid notification payload",
        ) from exc

    notification_type = str(outer.get("notificationType") or outer.get("notification_type") or "")
    data = outer.get("data") if isinstance(outer.get("data"), dict) else {}
    signed_tx = data.get("signedTransactionInfo") if isinstance(data, dict) else None
    tx_info: dict[str, Any] = {}
    if isinstance(signed_tx, str) and signed_tx:
        try:
            tx_info = decode_transaction_jws(signed_tx)
        except AppleIapError:
            # Outer envelope verified; missing/invalid nested tx still usable for type-only events.
            tx_info = {}

    original_tx = str(
        tx_info.get("originalTransactionId")
        or tx_info.get("original_transaction_id")
        or ""
    ).strip()
    product_id = str(tx_info.get("productId") or tx_info.get("product_id") or "").strip()
    period_end = period_end_from_tx_info(tx_info)

    transaction_id = str(
        tx_info.get("transactionId") or tx_info.get("transaction_id") or ""
    ).strip()
    ntype = notification_type.upper()

    if not original_tx and ntype != "REFUND":
        # Acknowledge unknown shape so Apple does not retry forever.
        return {"status": "ignored", "reason": "no_original_transaction"}

    apple_key = f"apple:{original_tx}"[:255] if original_tx else ""
    sub = (
        await session.scalar(select(Subscription).where(Subscription.stripe_subscription_id == apple_key))
        if apple_key
        else None
    )
    if sub is None and ntype != "REFUND":
        return {"status": "ignored", "reason": "unknown_subscription"}

    now = datetime.now(timezone.utc)

    if ntype in {"DID_RENEW", "SUBSCRIBED", "OFFER_REDEEMED", "DID_CHANGE_RENEWAL_PREF"}:
        product = product_by_apple_id(product_id) if product_id else None
        if product and product.kind == "plan":
            sub.plan = product.sku
        sub.status = "active"
        sub.cancel_at_period_end = False
        if period_end:
            sub.current_period_end = period_end
        else:
            sub.current_period_end = now + timedelta(days=31)
        sub.current_period_start = now
    elif ntype == "DID_CHANGE_RENEWAL_STATUS":
        subtype = str(outer.get("subtype") or "").upper()
        if subtype == "AUTO_RENEW_DISABLED":
            sub.cancel_at_period_end = True
        elif subtype == "AUTO_RENEW_ENABLED":
            sub.cancel_at_period_end = False
    elif ntype in {"EXPIRED", "GRACE_PERIOD_EXPIRED", "REVOKE"}:
        sub.status = "canceled"
        sub.plan = "free"
        sub.cancel_at_period_end = False
        if period_end:
            sub.current_period_end = period_end
    elif ntype == "REFUND":
        product = product_by_apple_id(product_id) if product_id else None
        if product and product.kind == "plan" and sub is not None:
            sub.status = "canceled"
            sub.plan = "free"
        if not product or product.kind == "pack":
            await _refund_iap_pack_grant(
                session,
                transaction_id=transaction_id,
                original_transaction_id=original_tx,
            )
    elif ntype == "DID_FAIL_TO_RENEW":
        sub.status = "past_due"
    else:
        await session.commit()
        return {"status": "ok", "notificationType": notification_type or "unknown"}

    await session.commit()
    return {"status": "ok", "notificationType": ntype}
