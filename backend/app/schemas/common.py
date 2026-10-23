from __future__ import annotations

import re
from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$"
)


ContactTopic = Literal["general", "account"]


Role = Literal["user", "admin"]


WorkspaceRole = Literal["owner", "admin", "editor", "viewer"]


InvitableWorkspaceRole = Literal["admin", "editor", "viewer"]


WorkspaceType = Literal["personal", "brand"]


PlanName = Literal["free", "starter", "creator", "studio"]


# Stock catalog ids (first names) plus legacy gender aliases. Generate also
# accepts workspace clone UUIDs. Not an enum: the hosted list grows.
VoiceOption = str


# Mirrors frontend VoiceLanguage (xAI TTS language codes).
VoiceLanguage = Literal[
    "auto",
    "en",
    "es-ES",
    "es-MX",
    "fr",
    "de",
    "pt-BR",
    "pt-PT",
    "it",
    "ja",
    "ko",
    "zh",
    "hi",
    "ar-SA",
    "tr",
    "vi",
    "id",
    "ru",
    "bn",
]


VoiceoverStatus = Literal["provider_required", "ready", "failed"]


def normalize_email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 256 or not EMAIL_RE.match(value):
        raise ValueError("Enter a valid email address")
    return value


AppEmail = Annotated[str, AfterValidator(normalize_email)]


def validate_password_strength(value: str) -> str:
    """Require 8+ chars with upper, lower, and digit (or symbol)."""
    if len(value) < 8 or len(value) > 128:
        raise ValueError("Password must be between 8 and 128 characters")
    if value.lower() == value:
        raise ValueError("Password must include an uppercase letter")
    if value.upper() == value:
        raise ValueError("Password must include a lowercase letter")
    if not any(ch.isdigit() for ch in value) and not any(not ch.isalnum() for ch in value):
        raise ValueError("Password must include a number or symbol")
    # Block a few notoriously common passwords even if they meet complexity
    common = {
        "password1",
        "password123",
        "admin123!",
        "qwerty123",
        "welcome1",
        "letmein1",
        "changeme1",
    }
    if value.lower() in common:
        raise ValueError("Choose a less common password")
    return value


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    error: str


def normalize_signal_list(values: list[str]) -> list[str]:
    normalized = []
    for value in values:
        item = value.strip()
        if item and item not in normalized:
            normalized.append(item)
    return normalized[:20]

__all__ = [
    "EMAIL_RE",
    "ContactTopic",
    "Role",
    "WorkspaceRole",
    "InvitableWorkspaceRole",
    "WorkspaceType",
    "PlanName",
    "VoiceOption",
    "VoiceLanguage",
    "VoiceoverStatus",
    "normalize_email",
    "AppEmail",
    "validate_password_strength",
    "MessageResponse",
    "ErrorResponse",
    "normalize_signal_list",
]
