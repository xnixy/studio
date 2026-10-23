"""Web and native deep links used in transactional email."""

from __future__ import annotations

from urllib.parse import urlencode

# Custom scheme declared in mobile/app.json (`scheme: "studio"`).
APP_REGISTER_SCHEME = "studio"


def build_signed_in_home_url(app_base_url: str) -> str:
    """Web Create. `/studio/overview` is gone and 404s for new accounts."""
    return f"{(app_base_url or '').rstrip('/')}/play"


def build_verify_email_url(app_base_url: str, *, token: str) -> str:
    """HTTPS verify URL. Opens web, or the iOS app when Universal Links are live."""
    base = f"{(app_base_url or '').rstrip('/')}/verify-email"
    return f"{base}?{urlencode({'token': (token or '').strip()})}"


def build_verify_email_app_url(*, token: str) -> str:
    """Custom scheme deep link for email verification in the installed app."""
    return f"{APP_REGISTER_SCHEME}://verify-email?{urlencode({'token': (token or '').strip()})}"
