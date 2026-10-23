"""Map provider failures to user-safe API messages; log full detail server-side only."""
from __future__ import annotations

import logging
from typing import Literal

from fastapi import HTTPException

logger = logging.getLogger("studio.providers")

ProviderKind = Literal["media", "voice", "text", "generic"]

_USER_MESSAGES: dict[ProviderKind, str] = {
    "media": "We couldn’t finish that media step. Please try again in a few minutes.",
    "voice": "We couldn’t record voice right now. Please try again in a few minutes.",
    "text": "We couldn’t generate that text right now. Please try again in a few minutes.",
    "generic": "Something went wrong. Please try again in a few minutes.",
}

_USER_NOT_CONFIGURED = "This feature isn’t available right now. Please contact support."
_USER_BAD_KEY = "The AI provider rejected this request. Try again later or contact support."
_USER_BUSY = "Generation is busy right now. Please wait a moment and try again."
# Prompt/content rejections are permanent for that wording. Telling people to
# "try again in a few minutes" sends them into a retry loop that always fails.
_USER_REJECTED = "The model would not generate this one. Change the wording or the reference image and try again."

# Provider phrasings that mean "this prompt or image, not this moment".
_REJECTION_NEEDLES: tuple[str, ...] = (
    "safety",
    "content policy",
    "content_policy",
    "policy violation",
    "moderation",
    "blocked",
    "prohibited",
    "violat",
    "sensitive",
    "nsfw",
    "person_generation",
    "persongeneration",
    "celebrity",
    "invalid prompt",
    "prompt is invalid",
    "unsupported prompt",
    "rejected the face",
    "could not load the face",
)


def public_status_message(raw: str | None, *, fallback: str) -> str:
    """Map a provider's terminal status text to user-safe copy.

    Poll results carry a message instead of an exception, so they bypassed
    public_provider_error and leaked vendor wording straight to the user
    ("the input image may contain sensitive information"). Only rejections are
    rewritten; anything else keeps the provider's own words, which are usually
    the most actionable thing we have.
    """
    text = (raw or "").strip()
    if not text:
        return fallback
    if any(needle in text.lower() for needle in _REJECTION_NEEDLES):
        return _USER_REJECTED
    return text


def public_provider_error(exc: BaseException, *, kind: ProviderKind = "generic") -> tuple[int, str]:
    """
    Log the full provider exception for operators.

    Returns (HTTP status, user-facing detail) with no vendor, team IDs, or raw JSON.
    """
    # stdout so FastAPI Cloud retains operator detail (never returned to clients).
    print(f"provider_error kind={kind} error={exc}", flush=True)
    logger.warning("provider_error kind=%s error=%s", kind, exc)

    text = str(exc).lower()
    # Missing local/server config (our Settings), not every upstream string with "api key".
    if "not configured" in text or "is not configured" in text:
        return 503, _USER_NOT_CONFIGURED
    if (
        "invalid api key" in text
        or "incorrect api key" in text
        or "api key not valid" in text
        or "unauthorized" in text
        or "401" in text
        or "authentication" in text
        or "permission denied" in text
        or "forbidden" in text
    ):
        return 503, _USER_BAD_KEY
    if "429" in text or "rate limit" in text or "resource_exhausted" in text or "quota" in text:
        return 503, _USER_BUSY
    # Prompt / image rejection: retrying the same words never works.
    if any(needle in text for needle in _REJECTION_NEEDLES):
        return 422, _USER_REJECTED
    # Credits / spend / upstream 5xx / parse failures → generic temporary message.
    # 503, never 502: Cloudflare treats an origin 502 as a broken gateway and serves its
    # own "the origin returned an invalid or incomplete response" page, which throws away
    # our JSON detail. The upstream provider failed, not this gateway.
    return 503, _USER_MESSAGES.get(kind, _USER_MESSAGES["generic"])


def public_error_message(exc: BaseException, *, kind: ProviderKind = "generic") -> str:
    """User-safe string only (for asset.error_message, notices, etc.)."""
    return public_provider_error(exc, kind=kind)[1]


def http_provider_exception(exc: BaseException, *, kind: ProviderKind = "generic") -> HTTPException:
    """Build an HTTPException with a public detail (does not raise)."""
    status_code, detail = public_provider_error(exc, kind=kind)
    return HTTPException(status_code=status_code, detail=detail)
