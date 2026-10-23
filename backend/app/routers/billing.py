"""billing API routes."""
from __future__ import annotations

# Re-export shared helpers + models into local namespace for route handlers.
from app.routers._platform_shared import *  # noqa: F403
from fastapi import APIRouter

from app.credit_packs import map_credit_grant, pack_dtos
from app.models import BillingCreditGrant
from app.plans import credit_pack_for, sale_credit_pack_for
from app.schemas import (
    BillingCreditGrantDto,
    CreditPackCheckoutRequest,
    CreditPackDto,
)
from app.stripe_billing import create_pack_checkout_session
from app.workspace_access import month_start

router = APIRouter(tags=["billing"])

PACK_PURCHASES_PER_MONTH_CAP = 12


async def fulfill_credit_pack(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    pack_name: str,
    checkout_session_id: str | None,
    customer_id: str | None,
    user_id: UUID | None = None,
) -> BillingCreditGrant | None:
    """Idempotently record a paid pack grant for the current usage month."""
    pack = credit_pack_for(pack_name)
    if pack is None:
        raise ValueError(f"Unknown credit pack: {pack_name}")
    root = await billing_workspace(session, workspace_id)
    if checkout_session_id:
        existing = await session.scalar(
            select(BillingCreditGrant).where(BillingCreditGrant.stripe_checkout_session_id == checkout_session_id)
        )
        if existing is not None:
            return existing
    now = datetime.now(timezone.utc)
    start = month_start(now)
    end = next_month(start)
    grant = BillingCreditGrant(
        workspace_id=root.id,
        pack_name=pack.name,
        label=pack.label,
        grants=dict(pack.grants),
        amount_cents=pack.price_cents,
        stripe_checkout_session_id=checkout_session_id,
        status="active",
        period_start=start,
        period_end=end,
        purchased_by_id=user_id,
    )
    session.add(grant)
    subscription = await get_subscription(session, root.id, lock=True)
    if customer_id:
        subscription.stripe_customer_id = customer_id
    await session.flush()
    return grant


@router.get("/billing", response_model=BillingStatusDto)
async def billing_status(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> BillingStatusDto:
    await get_membership(session, workspace_id, user)
    return await billing_payload(session, workspace_id, settings)


@router.get("/billing/usage", response_model=list[UsageEventDto])
async def billing_usage(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[UsageEventDto]:
    await get_membership(session, workspace_id, user)
    root = await billing_workspace(session, workspace_id)
    rows = (
        await session.scalars(
            select(UsageEvent).where(UsageEvent.workspace_id == root.id).order_by(UsageEvent.created_at.desc()).limit(100)
        )
    ).all()
    return [UsageEventDto(id=row.id, event_type=row.event_type, quantity=row.quantity, status=row.status, created_at=row.created_at) for row in rows]


@router.get("/billing/packs", response_model=list[CreditPackDto])
async def list_credit_packs(
    settings: Settings = Depends(get_settings),
    _: User = Depends(get_current_user),
) -> list[CreditPackDto]:
    return pack_dtos(settings)


@router.post("/billing/packs/checkout", response_model=BillingSessionDto)
async def create_pack_checkout(
    payload: CreditPackCheckoutRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> BillingSessionDto:
    root = await billing_workspace(session, payload.workspace_id)
    await require_permission(session, root.id, user, "billing.manage")
    pack = sale_credit_pack_for(payload.pack)
    if pack is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown credit pack")
    from app.workspace_access import effective_plan_name

    subscription = await get_subscription(session, root.id)
    if effective_plan_name(subscription) == "free":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Upgrade to a paid plan before buying credit packs.",
        )
    purchased = int(
        await session.scalar(
            select(func.count())
            .select_from(BillingCreditGrant)
            .where(
                BillingCreditGrant.workspace_id == root.id,
                BillingCreditGrant.status == "active",
                BillingCreditGrant.created_at >= month_start(),
            )
        )
        or 0
    )
    if purchased >= PACK_PURCHASES_PER_MONTH_CAP:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Pack purchase limit reached ({PACK_PURCHASES_PER_MONTH_CAP}/month). Upgrade your plan for higher base limits.",
        )
    price_id = settings.stripe_pack_price_ids.get(pack.name)
    if not settings.stripe_secret_key or not price_id:
        return BillingSessionDto(
            url=None,
            configured=False,
            message=f"Stripe price is not configured for pack {pack.label}.",
        )
    try:
        url = await create_pack_checkout_session(
            settings=settings,
            price_id=price_id,
            workspace_id=str(root.id),
            pack_name=pack.name,
            customer_id=subscription.stripe_customer_id,
            customer_email=user.email,
        )
    except StripeBillingError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    await audit(session, root.id, user.id, "billing.pack_checkout_created", pack=pack.name)
    await session.commit()
    return BillingSessionDto(url=url, configured=True, message="Pack checkout session created")


@router.get("/billing/grants", response_model=list[BillingCreditGrantDto])
async def list_credit_grants(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[BillingCreditGrantDto]:
    await get_membership(session, workspace_id, user)
    root = await billing_workspace(session, workspace_id)
    rows = (
        await session.scalars(
            select(BillingCreditGrant)
            .where(BillingCreditGrant.workspace_id == root.id)
            .order_by(BillingCreditGrant.created_at.desc())
            .limit(50)
        )
    ).all()
    return [map_credit_grant(row) for row in rows]


@router.post("/billing/checkout", response_model=BillingSessionDto)
async def create_checkout(
    payload: CheckoutRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> BillingSessionDto:
    root = await billing_workspace(session, payload.workspace_id)
    await require_permission(session, root.id, user, "billing.manage")
    if payload.plan == "free":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use the billing portal to cancel or downgrade a paid plan")
    price_id = settings.stripe_price_ids.get(payload.plan)
    if not settings.stripe_secret_key or not price_id:
        return BillingSessionDto(url=None, configured=False, message=f"Stripe price ID is not configured for {plan_for(payload.plan).label}.")
    subscription = await get_subscription(session, root.id)
    try:
        url = await create_checkout_session(
            settings=settings,
            price_id=price_id,
            workspace_id=str(root.id),
            plan=payload.plan,
            customer_id=subscription.stripe_customer_id,
            customer_email=user.email,
        )
    except StripeBillingError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    await audit(session, root.id, user.id, "billing.checkout_created", plan=payload.plan)
    await session.commit()
    return BillingSessionDto(url=url, configured=True, message="Checkout session created")


@router.post("/billing/portal", response_model=BillingSessionDto)
async def create_portal(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> BillingSessionDto:
    root = await billing_workspace(session, workspace_id)
    await require_permission(session, root.id, user, "billing.manage")
    subscription = await get_subscription(session, root.id)
    if not subscription.stripe_customer_id:
        return BillingSessionDto(url=None, configured=False, message="No Stripe customer exists for this billing workspace yet.")
    try:
        url = await create_portal_session(settings=settings, customer_id=subscription.stripe_customer_id)
    except StripeBillingError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return BillingSessionDto(url=url, configured=True, message="Portal session created")


def timestamp(value: object) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc)
    return None


def plan_from_subscription_object(data: dict[str, Any], settings: Settings) -> str | None:
    metadata = data.get("metadata") or {}
    if metadata.get("plan"):
        return str(metadata["plan"])
    items = ((data.get("items") or {}).get("data") or [])
    price_id = (((items[0] if items else {}).get("price") or {}).get("id"))
    reverse = {value: key for key, value in settings.stripe_price_ids.items()}
    return reverse.get(price_id)


def _pack_name_from_checkout(data: dict[str, Any], metadata: dict[str, Any], settings: Settings) -> str | None:
    """Resolve credit pack from Stripe price id first, then validated metadata."""
    reverse = {price_id: name for name, price_id in settings.stripe_pack_price_ids.items()}
    # Prefer price_id we stamped on metadata when creating the session
    meta_price = str(metadata.get("price_id") or "").strip()
    if meta_price and meta_price in reverse:
        return reverse[meta_price]
    # Expanded line items when present (some webhook payloads include them)
    line_items = (data.get("line_items") or {}).get("data") if isinstance(data.get("line_items"), dict) else None
    if isinstance(line_items, list):
        for item in line_items:
            price = (item or {}).get("price") if isinstance(item, dict) else None
            price_id = price.get("id") if isinstance(price, dict) else None
            if price_id and price_id in reverse:
                return reverse[price_id]
    # Fallback: metadata pack_name only when it matches a known catalog pack
    meta_pack = str(metadata.get("pack_name") or "").strip()
    if meta_pack and credit_pack_for(meta_pack) is not None:
        # If we have configured price ids, require the pack to be one of them
        if settings.stripe_pack_price_ids and meta_pack not in settings.stripe_pack_price_ids:
            return None
        return meta_pack
    return None


def _plan_name_from_checkout(metadata: dict[str, Any], settings: Settings) -> str | None:
    raw = str(metadata.get("plan") or "").strip().lower()
    if not raw:
        return None
    if raw in settings.stripe_price_ids:
        return raw
    # Allow plan name even when price ids not configured (dev), but only known catalog plans
    from app.plans import plan_for

    plan = plan_for(raw)
    if plan.name == raw and plan.price_monthly > 0:
        return plan.name
    return None


@router.post("/billing/webhook", response_model=MessageResponse)
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        event = construct_webhook_event(payload, signature, settings)
    except StripeBillingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    event_id = str(event.get("id"))
    event_type = str(event.get("type"))
    # Idempotency: insert-or-get event row; skip if already processed.
    stored = await session.get(StripeEvent, event_id)
    if stored is not None and stored.processed_at is not None:
        return MessageResponse(message="Webhook already processed")
    if stored is None:
        stored = StripeEvent(id=event_id, event_type=event_type)
        session.add(stored)
        try:
            await session.commit()
        except Exception:
            # Concurrent delivery already inserted this event id
            await session.rollback()
            stored = await session.get(StripeEvent, event_id)
            if stored is not None and stored.processed_at is not None:
                return MessageResponse(message="Webhook already processed")
            if stored is None:
                raise
    data = dict(((event.get("data") or {}).get("object") or {}))
    notify: dict[str, object] | None = None
    try:
        if event_type == "checkout.session.completed":
            metadata = dict(data.get("metadata") or {})
            kind = str(metadata.get("kind") or "")
            mode = str(data.get("mode") or "")
            workspace_raw = metadata.get("workspace_id")
            if not workspace_raw:
                raise ValueError("checkout.session.completed missing workspace_id metadata")
            workspace_id = UUID(str(workspace_raw))
            customer = data.get("customer")
            customer_id = str(customer) if customer else None
            # Only treat as credit pack when explicitly marked (not any payment-mode session).
            if kind == "credit_pack" or (mode == "payment" and metadata.get("pack_name")):
                pack_name = _pack_name_from_checkout(data, metadata, settings)
                if not pack_name:
                    raise ValueError("checkout.session.completed credit pack could not be resolved from price/metadata")
                session_id = str(data.get("id") or "") or None
                grant = await fulfill_credit_pack(
                    session,
                    workspace_id=workspace_id,
                    pack_name=pack_name,
                    checkout_session_id=session_id,
                    customer_id=customer_id,
                )
                pack_label = grant.label if grant is not None else pack_name
                notify = {"kind": "credit_pack", "workspace_id": workspace_id, "pack_label": pack_label}
            elif mode == "subscription" or kind == "subscription":
                subscription = await get_subscription(session, workspace_id, lock=True)
                plan_name = _plan_name_from_checkout(metadata, settings)
                if plan_name:
                    subscription.plan = plan_name
                subscription.status = "active"
                if customer_id:
                    subscription.stripe_customer_id = customer_id
                sub_id = data.get("subscription")
                if sub_id:
                    subscription.stripe_subscription_id = str(sub_id)
                notify = {"kind": "subscription_active", "workspace_id": workspace_id, "plan": subscription.plan}
            else:
                raise ValueError(f"Unhandled checkout mode/kind: mode={mode!r} kind={kind!r}")
        elif event_type.startswith("customer.subscription."):
            stripe_subscription_id = str(data.get("id"))
            subscription = await session.scalar(select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id))
            metadata = data.get("metadata") or {}
            if subscription is None and metadata.get("workspace_id"):
                subscription = await get_subscription(session, UUID(str(metadata["workspace_id"])), lock=True)
            if subscription is not None:
                selected_plan = plan_from_subscription_object(data, settings)
                if selected_plan:
                    subscription.plan = selected_plan
                subscription.status = "canceled" if event_type == "customer.subscription.deleted" else str(data.get("status") or "active")
                subscription.stripe_customer_id = str(data.get("customer") or subscription.stripe_customer_id)
                subscription.stripe_subscription_id = stripe_subscription_id
                subscription.current_period_start = timestamp(data.get("current_period_start"))
                subscription.current_period_end = timestamp(data.get("current_period_end"))
                subscription.cancel_at_period_end = bool(data.get("cancel_at_period_end"))
                if event_type == "customer.subscription.deleted":
                    notify = {
                        "kind": "subscription_canceled",
                        "workspace_id": subscription.workspace_id,
                        "plan": subscription.plan,
                    }
        elif event_type in {"invoice.payment_failed", "invoice.paid"}:
            customer_id = str(data.get("customer"))
            subscription = await session.scalar(select(Subscription).where(Subscription.stripe_customer_id == customer_id))
            if subscription is not None:
                subscription.status = "past_due" if event_type == "invoice.payment_failed" else "active"
                notify = {
                    "kind": "payment_failed" if event_type == "invoice.payment_failed" else "payment_succeeded",
                    "workspace_id": subscription.workspace_id,
                }
        stored.processed_at = datetime.now(timezone.utc)
        stored.error_message = None
        await session.commit()
    except Exception as exc:
        await session.rollback()
        stored = await session.get(StripeEvent, event_id)
        if stored is not None:
            stored.error_message = str(exc)[:1000]
            await session.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stripe webhook processing failed") from exc

    if notify is not None:
        from app import email_templates as templates
        from app.email_notify import safe_send_email, workspace_admin_emails

        workspace_id = notify.get("workspace_id")
        if isinstance(workspace_id, UUID):
            recipients = await workspace_admin_emails(session, workspace_id)
            kind = str(notify.get("kind") or "")
            if kind == "subscription_active":
                subject, body = templates.subscription_active(
                    plan=str(notify.get("plan") or "plan"), app_base_url=settings.app_base_url
                )
                await safe_send_email(subject, body, recipients, settings)
            elif kind == "subscription_canceled":
                subject, body = templates.subscription_canceled(
                    plan=str(notify.get("plan") or "plan"), app_base_url=settings.app_base_url
                )
                await safe_send_email(subject, body, recipients, settings)
            elif kind == "payment_failed":
                subject, body = templates.payment_failed(app_base_url=settings.app_base_url)
                await safe_send_email(subject, body, recipients, settings)
            elif kind == "payment_succeeded":
                subject, body = templates.payment_succeeded(app_base_url=settings.app_base_url)
                await safe_send_email(subject, body, recipients, settings)
            elif kind == "credit_pack":
                subject, body = templates.credit_pack_purchased(
                    pack_label=str(notify.get("pack_label") or "credit pack"),
                    app_base_url=settings.app_base_url,
                )
                await safe_send_email(subject, body, recipients, settings)

    return MessageResponse(message="Webhook processed")
