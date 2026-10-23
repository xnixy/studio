"""Plain-text transactional email subjects and bodies for Studio."""

from __future__ import annotations


def welcome(app_base_url: str) -> tuple[str, str]:
    from app.app_links import build_signed_in_home_url

    url = build_signed_in_home_url(app_base_url)
    return (
        "Welcome to Studio",
        "Welcome to Studio.\n\n"
        "Your email is confirmed. Open Create to make a clip or a still:\n\n"
        f"{url}\n\n"
        "If you didn’t create this account, tell us and we’ll sort it out.\n",
    )


def verify_email(verify_url: str, app_url: str | None = None) -> tuple[str, str]:
    lines = [
        "Confirm your Studio email (link is good for 48 hours):",
        "",
        "Open this link (site, or the Studio app if installed):",
        verify_url,
    ]
    if app_url:
        lines.extend(
            [
                "",
                "Already have the Studio iOS app? You can open verification there directly:",
                app_url,
            ]
        )
    lines.extend(
        [
            "",
            "If you did not sign up for Studio, you can ignore this.",
            "",
        ]
    )
    return ("Confirm your Studio email", "\n".join(lines))


def password_changed() -> tuple[str, str]:
    return (
        "Your Studio password changed",
        "Your Studio password was just updated.\n\n"
        "If that was you, you’re all set. "
        "If it wasn’t, reset the password now and contact support.\n",
    )


def password_reset(reset_url: str) -> tuple[str, str]:
    return (
        "Reset your Studio password",
        "Someone asked to reset your Studio password.\n\n"
        "Open this link within an hour to pick a new one:\n\n"
        f"{reset_url}\n\n"
        "If you didn’t ask for this, ignore the email. Your password stays the same.\n",
    )


def contact_ops_notify(*, name: str, email: str, topic: str, message: str, contact_id: str) -> tuple[str, str]:
    return (
        f"[Studio contact] {topic}: {name}",
        f"New contact form submission ({contact_id})\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Topic: {topic}\n\n"
        f"{message}\n",
    )


def contact_ack(*, name: str) -> tuple[str, str]:
    greeting = f"Hi {name},\n\n" if name.strip() else ""
    return (
        "We got your message",
        f"{greeting}Thanks for writing. We read every note and reply as soon as we can.\n\n"
        "the Studio team\n",
    )


def workspace_added(*, workspace_name: str, role: str, app_base_url: str) -> tuple[str, str]:
    url = f"{app_base_url.rstrip('/')}/growth"
    return (
        f"You’re on {workspace_name} in Studio",
        f"You now have access to “{workspace_name}” as {role}.\n\n"
        f"Open studio:\n{url}\n",
    )


def client_access_granted(*, client_name: str, role: str, app_base_url: str) -> tuple[str, str]:
    url = f"{app_base_url.rstrip('/')}/studio/agency"
    return (
        f"You can work on {client_name} in Studio",
        f"You were given access to “{client_name}” as {role}.\n\n"
        f"Open agency:\n{url}\n",
    )


def subscription_active(*, plan: str, app_base_url: str) -> tuple[str, str]:
    url = f"{app_base_url.rstrip('/')}/growth?tab=billing"
    return (
        f"Your Studio {plan} plan is live",
        f"This workspace is now on the {plan} plan.\n\n"
        f"Manage billing:\n{url}\n",
    )


def subscription_canceled(*, plan: str, app_base_url: str) -> tuple[str, str]:
    url = f"{app_base_url.rstrip('/')}/growth?tab=billing"
    return (
        "Your Studio subscription was canceled",
        f"The {plan} subscription on this workspace was canceled. "
        "You can resubscribe anytime from billing.\n\n"
        f"{url}\n",
    )


def payment_failed(*, app_base_url: str) -> tuple[str, str]:
    url = f"{app_base_url.rstrip('/')}/growth?tab=billing"
    return (
        "Action needed: Studio payment failed",
        "We couldn’t process a payment for your Studio subscription. "
        "Update your card so things don’t pause mid-week.\n\n"
        f"{url}\n",
    )


def payment_succeeded(*, app_base_url: str) -> tuple[str, str]:
    url = f"{app_base_url.rstrip('/')}/growth?tab=billing"
    return (
        "Studio payment received",
        "We got your payment. You’re all set.\n\n"
        f"Billing details:\n{url}\n",
    )


def credit_pack_purchased(*, pack_label: str, app_base_url: str) -> tuple[str, str]:
    url = f"{app_base_url.rstrip('/')}/growth?tab=billing"
    return (
        f"Credits added: {pack_label}",
        f"Your “{pack_label}” pack is active for this billing period.\n\n"
        f"View usage:\n{url}\n",
    )


def review_requested(*, title: str, summary: str | None, app_base_url: str) -> tuple[str, str]:
    url = f"{app_base_url.rstrip('/')}/studio/agency"
    body = f"Someone asked for a review on “{title}”.\n"
    if summary:
        body += f"\n{summary}\n"
    body += f"\nOpen studio:\n{url}\n"
    return (f"Review requested: {title}", body)


def review_decision(*, title: str, approval_state: str, notes: str | None, app_base_url: str) -> tuple[str, str]:
    url = f"{app_base_url.rstrip('/')}/studio/agency"
    body = f"Review “{title}” is now {approval_state}.\n"
    if notes:
        body += f"\nNotes:\n{notes}\n"
    body += f"\nOpen studio:\n{url}\n"
    return (f"Review {approval_state}: {title}", body)


def review_comment(*, title: str, author_email: str, excerpt: str, app_base_url: str) -> tuple[str, str]:
    url = f"{app_base_url.rstrip('/')}/studio/agency"
    return (
        f"New comment on {title}",
        f"{author_email} left a note on “{title}”:\n\n"
        f"{excerpt}\n\n"
        f"Open studio:\n{url}\n",
    )


def share_link(*, title: str, share_url: str, sender_email: str | None = None) -> tuple[str, str]:
    who = f"{sender_email} shared" if sender_email else "Someone shared"
    return (
        f"Shared with you: {title}",
        f"{who} “{title}” on Studio.\n\n"
        f"Open the link:\n{share_url}\n",
    )


def report_published(*, title: str, client_name: str, app_base_url: str) -> tuple[str, str]:
    url = f"{app_base_url.rstrip('/')}/studio/agency"
    return (
        f"Report ready: {title}",
        f"A report for {client_name} is ready: “{title}”.\n\n"
        f"Open studio:\n{url}\n",
    )


def render_complete(*, project_title: str, studio_url: str) -> tuple[str, str]:
    return (
        f"Export ready: {project_title}",
        f"Your export for “{project_title}” finished.\n\n"
        f"Open the project:\n{studio_url}\n",
    )


def render_failed(*, project_title: str, error: str | None, studio_url: str) -> tuple[str, str]:
    body = f"Export failed for “{project_title}”.\n"
    if error:
        body += f"\nWhat we saw: {error[:400]}\n"
    body += f"\nOpen the project:\n{studio_url}\n"
    return (f"Export failed: {project_title}", body)


def account_disabled() -> tuple[str, str]:
    return (
        "Your Studio account was disabled",
        "An admin disabled your Studio account. "
        "Contact support if that doesn’t look right.\n",
    )
