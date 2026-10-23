from __future__ import annotations

from datetime import date, datetime
from typing import Literal  # noqa: F401 used by DeleteAccountRequest
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import AppEmail, Role, validate_password_strength

class UserDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: AppEmail
    full_name: str | None = None
    role: Role
    permissions: dict[str, bool] = Field(default_factory=dict)
    email_verified: bool = False


class AuthResponse(BaseModel):
    access_token: str
    user: UserDto
    """Present when the client requests a mobile session (X-Studio-Client: mobile).
    Web keeps using the HttpOnly refresh cookie only."""
    refresh_token: str | None = None


class MobileRefreshRequest(BaseModel):
    """Optional body for native clients that cannot use cookies."""
    refresh_token: str | None = Field(default=None, min_length=20, max_length=512)


class MobileLogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=20, max_length=512)


class RegisterRequest(BaseModel):
    email: AppEmail
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)
    turnstile_token: str | None = Field(default=None, max_length=2048)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str) -> str:
        cleaned = " ".join(value.split()).strip()
        if len(cleaned) < 1:
            raise ValueError("Name is required")
        return cleaned


class LoginRequest(BaseModel):
    email: AppEmail
    password: str = Field(min_length=1)


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=100)


class DeleteAccountRequest(BaseModel):
    """Confirm ownership before irreversible account deletion."""

    password: str = Field(min_length=1, max_length=128)
    confirm: Literal["DELETE"] = Field(description='Must be the string DELETE')


class PasswordUpdateRequest(BaseModel):
    current_password: str = Field(min_length=1)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)


class ForgotPasswordRequest(BaseModel):
    email: AppEmail


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class RoleUpdateRequest(BaseModel):
    role: Role

__all__ = [
    "UserDto",
    "AuthResponse",
    "MobileRefreshRequest",
    "MobileLogoutRequest",
    "RegisterRequest",
    "LoginRequest",
    "ProfileUpdateRequest",
    "DeleteAccountRequest",
    "PasswordUpdateRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "VerifyEmailRequest",
    "RoleUpdateRequest",
]
