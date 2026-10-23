"""Web and native deep-link builders for transactional email."""

from app.app_links import (
    build_signed_in_home_url,
    build_verify_email_app_url,
    build_verify_email_url,
)
from app import email_templates as templates


def test_signed_in_home_is_create() -> None:
    assert build_signed_in_home_url("https://example.com/") == "https://example.com/play"


def test_welcome_waits_for_verify_and_skips_studio() -> None:
    subject, body = templates.welcome("https://example.com")
    assert subject == "Welcome to Studio"
    assert "https://example.com/play" in body
    assert "/studio/" not in body.lower()
    assert "confirmed" in body.lower()


def test_verify_email_urls() -> None:
    web = build_verify_email_url("https://example.com", token="abc123tokenvalue")
    assert web.startswith("https://example.com/verify-email?")
    assert "token=abc123tokenvalue" in web
    app = build_verify_email_app_url(token="abc123tokenvalue")
    assert app.startswith("studio://verify-email?")
    assert "token=abc123tokenvalue" in app
