from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import utcnow

class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(32), default="free")
    status: Mapped[str] = mapped_column(String(32), default="active")
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    limit_overrides: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    workspace: Mapped[Workspace] = relationship(back_populates="subscription")

    __table_args__ = (
        CheckConstraint(
            "plan in ('free', 'starter', 'creator', 'studio')",
            name="ck_subscriptions_plan",
        ),
        CheckConstraint("status in ('active', 'trialing', 'past_due', 'unpaid', 'paused', 'canceled', 'incomplete', 'incomplete_expired')", name="ck_subscriptions_status"),
    )


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(80))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    event_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(24), default="consumed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_usage_events_quantity_positive"),
        CheckConstraint("status in ('reserved', 'consumed', 'released')", name="ck_usage_events_status"),
        # Reserve hot path: stale sweep (partial) and per-workspace usage sum.
        Index(
            "ix_usage_events_reserved_created_at",
            "created_at",
            postgresql_where=text("status = 'reserved'"),
        ),
        Index("ix_usage_events_workspace_event_created", "workspace_id", "event_type", "created_at"),
    )


class StripeEvent(Base):
    __tablename__ = "stripe_events"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(120))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BillingAddOn(Base):
    __tablename__ = "billing_addons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    addon_type: Mapped[str] = mapped_column(String(48))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price_cents: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="active")
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint(
            "addon_type in ('seats', 'video_credits', 'image_generations', 'avatar_lipsyncs', 'script_generations', 'voiceover_minutes', 'storage_gb', 'priority_rendering')",
            name="ck_billing_addons_type",
        ),
        CheckConstraint("quantity > 0", name="ck_billing_addons_quantity_positive"),
        CheckConstraint("unit_price_cents >= 0", name="ck_billing_addons_price_nonnegative"),
        CheckConstraint("status in ('active', 'canceled')", name="ck_billing_addons_status"),
        UniqueConstraint("workspace_id", "addon_type", name="uq_billing_addons_workspace_type"),
    )


class BillingCreditGrant(Base):
    """One-time credit pack purchase that boosts monthly limits until period end."""

    __tablename__ = "billing_credit_grants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    pack_name: Mapped[str] = mapped_column(String(48))
    label: Mapped[str] = mapped_column(String(120))
    grants: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict)
    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    stripe_checkout_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    purchased_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        CheckConstraint("amount_cents >= 0", name="ck_billing_credit_grants_amount_nonnegative"),
        CheckConstraint("status in ('active', 'refunded', 'expired')", name="ck_billing_credit_grants_status"),
    )

__all__ = [
    "Subscription",
    "UsageEvent",
    "StripeEvent",
    "BillingAddOn",
    "BillingCreditGrant",
]
