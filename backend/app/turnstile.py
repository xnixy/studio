"""Cloudflare Turnstile siteverify helpers."""

from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException, status

from app.config import Settings

logger = logging.getLogger(__name__)

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class TurnstileError(Exception):
    """Turnstile verification failed or is unavailable."""


async def verify_turnstile_token(
    token: str | None,
    *,
    settings: Settings,
    remote_ip: str | None = None,
    required: bool = True,
) -> None:
    """Validate a Turnstile response token.

    When secret is unset:
    - development: skip (so local work is not blocked)
    - other envs: hard fail if required
    """
    secret = (settings.turnstile_secret_key or "").strip()
    if not secret:
        if settings.app_env.strip().lower() in {"development", "test", "testing"}:
            logger.debug("Turnstile secret not configured; skipping verify in %s", settings.app_env)
            return
        if required:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Captcha is not configured. Please try again later.",
            )
        return

    cleaned = (token or "").strip()
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please complete the captcha")

    data: dict[str, str] = {"secret": secret, "response": cleaned}
    if remote_ip:
        data["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(SITEVERIFY_URL, data=data)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Turnstile siteverify request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Captcha check failed. Please try again.",
        ) from exc

    if not bool(payload.get("success")):
        codes = payload.get("error-codes") or []
        logger.info("Turnstile rejected token: %s", codes)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Captcha failed. Please try again.")


def turnstile_public_config(settings: Settings) -> dict[str, object]:
    site_key = (settings.turnstile_site_key or "").strip()
    secret = (settings.turnstile_secret_key or "").strip()
    enabled = bool(site_key and secret) or (
        bool(site_key) and settings.app_env.strip().lower() in {"development", "test", "testing"}
    )
    # Show widget when site key is set; backend still skips verify only when secret missing in dev.
    return {
        "turnstile_site_key": site_key or None,
        "turnstile_enabled": bool(site_key),
        "turnstile_required": bool(secret) or settings.app_env.strip().lower() not in {"development", "test", "testing"},
    }
