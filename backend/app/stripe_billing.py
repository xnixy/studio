from __future__ import annotations

import asyncio
from typing import Any

from app.config import Settings


class StripeBillingError(RuntimeError):
    pass


def _stripe_module(settings: Settings):
    try:
        import stripe
    except ImportError as exc:
        raise StripeBillingError("Stripe SDK is not installed") from exc
    if not settings.stripe_secret_key:
        raise StripeBillingError("Stripe is not configured")
    stripe.api_key = settings.stripe_secret_key
    return stripe


async def create_checkout_session(
    *,
    settings: Settings,
    price_id: str,
    workspace_id: str,
    plan: str,
    customer_id: str | None,
    customer_email: str,
) -> str:
    stripe = _stripe_module(settings)

    def create():
        params: dict[str, Any] = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": f"{settings.app_base_url.rstrip('/')}/growth?checkout=success",
            "cancel_url": f"{settings.app_base_url.rstrip('/')}/growth?checkout=cancelled",
            "allow_promotion_codes": True,
            "metadata": {"workspace_id": workspace_id, "plan": plan, "kind": "subscription"},
            "subscription_data": {"metadata": {"workspace_id": workspace_id, "plan": plan}},
        }
        if customer_id:
            params["customer"] = customer_id
        else:
            params["customer_email"] = customer_email
        return stripe.checkout.Session.create(**params)

    session = await asyncio.to_thread(create)
    if not session.url:
        raise StripeBillingError("Stripe did not return a checkout URL")
    return str(session.url)


async def create_pack_checkout_session(
    *,
    settings: Settings,
    price_id: str,
    workspace_id: str,
    pack_name: str,
    customer_id: str | None,
    customer_email: str,
) -> str:
    """One-time payment for a credit pack (mode=payment)."""
    stripe = _stripe_module(settings)

    def create():
        params: dict[str, Any] = {
            "mode": "payment",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": f"{settings.app_base_url.rstrip('/')}/growth?tab=billing&pack=success",
            "cancel_url": f"{settings.app_base_url.rstrip('/')}/growth?tab=billing&pack=cancelled",
            "allow_promotion_codes": True,
            "metadata": {
                "workspace_id": workspace_id,
                "kind": "credit_pack",
                "pack_name": pack_name,
                "price_id": price_id,
            },
            "payment_intent_data": {
                "metadata": {
                    "workspace_id": workspace_id,
                    "kind": "credit_pack",
                    "pack_name": pack_name,
                    "price_id": price_id,
                }
            },
        }
        if customer_id:
            params["customer"] = customer_id
        else:
            params["customer_email"] = customer_email
        return stripe.checkout.Session.create(**params)

    session = await asyncio.to_thread(create)
    if not session.url:
        raise StripeBillingError("Stripe did not return a checkout URL")
    return str(session.url)


async def create_portal_session(*, settings: Settings, customer_id: str) -> str:
    stripe = _stripe_module(settings)

    def create():
        return stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{settings.app_base_url.rstrip('/')}/growth",
        )

    session = await asyncio.to_thread(create)
    if not session.url:
        raise StripeBillingError("Stripe did not return a portal URL")
    return str(session.url)


def construct_webhook_event(payload: bytes, signature: str, settings: Settings) -> dict[str, Any]:
    stripe = _stripe_module(settings)
    if not settings.stripe_webhook_secret:
        raise StripeBillingError("Stripe webhook secret is not configured")
    try:
        event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise StripeBillingError("Invalid Stripe webhook signature") from exc
    return event.to_dict_recursive() if hasattr(event, "to_dict_recursive") else dict(event)
