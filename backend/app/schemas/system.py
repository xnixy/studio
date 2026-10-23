from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import AppEmail, ContactTopic

class MaintenanceUpdateRequest(BaseModel):
    enabled: bool
    message: str | None = Field(default=None, max_length=500)


class MaintenanceStatus(BaseModel):
    enabled: bool
    message: str | None = None


class TtsStatusDto(BaseModel):
    xai_api_key_configured: bool
    tts_url: str
    media_dir: str
    media_backend: str = "local"
    media_public_base_url: str | None = None


class FfmpegStatusDto(BaseModel):
    available: bool
    path: str | None = None
    version: str | None = None


class ContactRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: AppEmail
    topic: ContactTopic
    message: str = Field(min_length=10, max_length=5000)
    turnstile_token: str | None = Field(default=None, max_length=2048)


class PublicConfigDto(BaseModel):
    """Non-secret client config (captcha site key, feature flags)."""

    turnstile_site_key: str | None = None
    turnstile_enabled: bool = False
    turnstile_required: bool = False


class ContactResponse(BaseModel):
    id: UUID
    message: str

__all__ = [
    "MaintenanceUpdateRequest",
    "MaintenanceStatus",
    "TtsStatusDto",
    "FfmpegStatusDto",
    "ContactRequest",
    "ContactResponse",
    "PublicConfigDto",
]
