"""Apple IAP product catalog mapped to Studio plans and credit packs.

App Store Connect product IDs must match these defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.plans import CREDIT_PACK_CATALOG, CreditPack, PAID_PLAN_NAMES, PLAN_CATALOG, RETIRED_CREDIT_PACKS


IapKind = Literal["plan", "pack"]

# com.example.studio.plan.* were created as Non-Consumable. com.example.studio.pack.* drafts are
# unused. Live IAP uses com.example.studio.sub.* (plans) and com.example.studio.credit.* (packs).
PLAN_APPLE_PRODUCT_IDS: dict[str, str] = {
    "starter": "com.example.studio.sub.starter",
    "creator": "com.example.studio.sub.creator",
    "studio": "com.example.studio.sub.studio",
}

PACK_APPLE_PRODUCT_IDS: dict[str, str] = {
    "video_10": "com.example.studio.credit.video_10",
    "video_25": "com.example.studio.credit.video_25",
    "image_50": "com.example.studio.credit.image_50",
    "voice_30m": "com.example.studio.credit.voice_30m",
}

# Burned App Store IDs. Not for sale. Keep for confirm/refund of old purchases.
RETIRED_PACK_APPLE_PRODUCT_IDS: dict[str, str] = {
    "lipsync_10": "com.example.studio.credit.lipsync_10",
    "scripts_25": "com.example.studio.credit.scripts_25",
    "creator_burst": "com.example.studio.credit.creator_burst",
}


@dataclass(frozen=True)
class IapProduct:
    apple_product_id: str
    kind: IapKind
    """plan name or pack name."""
    sku: str
    title: str
    description: str
    """StoreKit type hint for the client."""
    store_type: Literal["subscription", "consumable"]
    price_cents: int


def _pack_product(pack: CreditPack, apple_ids: dict[str, str]) -> IapProduct | None:
    apple_id = apple_ids.get(pack.name)
    if not apple_id:
        return None
    return IapProduct(
        apple_product_id=apple_id,
        kind="pack",
        sku=pack.name,
        title=pack.label,
        description=pack.description,
        store_type="consumable",
        price_cents=pack.price_cents,
    )


def default_iap_catalog() -> list[IapProduct]:
    products: list[IapProduct] = []
    for plan in PLAN_CATALOG:
        if plan.price_monthly <= 0:
            continue
        apple_id = PLAN_APPLE_PRODUCT_IDS.get(plan.name)
        if not apple_id:
            continue
        products.append(
            IapProduct(
                apple_product_id=apple_id,
                kind="plan",
                sku=plan.name,
                title=plan.label,
                description=f"{plan.label} monthly plan",
                store_type="subscription",
                price_cents=plan.price_monthly,
            )
        )
    for pack in CREDIT_PACK_CATALOG:
        product = _pack_product(pack, PACK_APPLE_PRODUCT_IDS)
        if product is not None:
            products.append(product)
    return products


def product_by_apple_id(apple_product_id: str) -> IapProduct | None:
    key = apple_product_id.strip()
    live = next((p for p in default_iap_catalog() if p.apple_product_id == key), None)
    if live is not None:
        return live
    for pack in RETIRED_CREDIT_PACKS:
        product = _pack_product(pack, RETIRED_PACK_APPLE_PRODUCT_IDS)
        if product is not None and product.apple_product_id == key:
            return product
    return None


def is_paid_plan(name: str) -> bool:
    return name in PAID_PLAN_NAMES
