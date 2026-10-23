"""SQLAlchemy models, split by domain. Prefer `from app.models import User`."""
from __future__ import annotations

from app.models.base import utcnow

from app.models.auth import (  # noqa: F401
    User,
    AuthEmailToken,
    RefreshToken,
    ContactMessage,
    MaintenanceSetting,
)

from app.models.video import (  # noqa: F401
    VideoProject,
    VideoScene,
    VideoRender,
    RenderJob,
    CaptionTrack,
    VideoAsset,
    GenerationCost,
)

from app.models.workspace import (  # noqa: F401
    Workspace,
    WorkspaceMember,
)

from app.models.billing import (  # noqa: F401
    Subscription,
    UsageEvent,
    StripeEvent,
    BillingAddOn,
    BillingCreditGrant,
)

from app.models.agency import (  # noqa: F401
    AuditEvent,
    ShareLink,
)

from app.models.jobs import (  # noqa: F401
    BackgroundJob,
)

from app.models.notifications import (  # noqa: F401
    Notification,
    NotificationPreference,
)

from app.models.devices import (  # noqa: F401
    DevicePushToken,
)

from app.models.iap import (  # noqa: F401
    IapTransaction,
)

from app.models.voices import (  # noqa: F401
    WorkspaceVoice,
)

__all__ = [
    "utcnow",
    "User",
    "AuthEmailToken",
    "RefreshToken",
    "ContactMessage",
    "MaintenanceSetting",
    "VideoProject",
    "VideoScene",
    "VideoRender",
    "RenderJob",
    "CaptionTrack",
    "VideoAsset",
    "GenerationCost",
    "Workspace",
    "WorkspaceMember",
    "Subscription",
    "UsageEvent",
    "StripeEvent",
    "BillingAddOn",
    "BillingCreditGrant",
    "AuditEvent",
    "ShareLink",
    "BackgroundJob",
    "Notification",
    "NotificationPreference",
    "DevicePushToken",
    "IapTransaction",
    "WorkspaceVoice",
]
