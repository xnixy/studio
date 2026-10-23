from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    # populate_by_name: accept both field names and env aliases (GEMINI_API_KEY, etc.).
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/studio", alias="DATABASE_URL")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    run_db_migrations_on_startup: bool = Field(default=False, alias="RUN_DB_MIGRATIONS_ON_STARTUP")
    frontend_origins: str = Field(default="http://localhost:5173,https://example.com", alias="FRONTEND_ORIGINS")
    # When true (behind Cloudflare/nginx), trust CF-Connecting-IP / X-Forwarded-For for rate limits.
    trust_proxy_headers: bool = Field(default=False, alias="TRUST_PROXY_HEADERS")

    jwt_signing_key: str = Field(default="development-signing-key-change-me-32chars", alias="JWT_SIGNING_KEY")
    jwt_issuer: str = Field(default="studio-api", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="studio-web", alias="JWT_AUDIENCE")
    access_token_minutes: int = Field(default=15, alias="ACCESS_TOKEN_MINUTES")
    refresh_token_days: int = Field(default=14, alias="REFRESH_TOKEN_DAYS")

    refresh_cookie_name: str = Field(default="studio_refresh", alias="REFRESH_COOKIE_NAME")
    # "lax" when SPA shares origin with API (proxy). "none" for example.com → api.example.com.
    refresh_cookie_samesite: str = Field(default="lax", alias="REFRESH_COOKIE_SAMESITE")
    # Optional dedicated HMAC key for media signatures (falls back to JWT_SIGNING_KEY).
    media_signing_key: str | None = Field(default=None, alias="MEDIA_SIGNING_KEY")
    seed_admin_email: str = Field(default="admin@studio.local", alias="SEED_ADMIN_EMAIL")
    seed_admin_password: str | None = Field(default=None, alias="SEED_ADMIN_PASSWORD")
    stripe_secret_key: str | None = Field(default=None, alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str | None = Field(default=None, alias="STRIPE_WEBHOOK_SECRET")
    stripe_starter_price_id: str | None = Field(default=None, alias="STRIPE_STARTER_PRICE_ID")
    stripe_creator_price_id: str | None = Field(default=None, alias="STRIPE_CREATOR_PRICE_ID")
    stripe_studio_price_id: str | None = Field(default=None, alias="STRIPE_STUDIO_PRICE_ID")
    # One-time credit packs. Retired SKUs stay so Stripe webhooks can still grant.
    stripe_pack_video_10_price_id: str | None = Field(default=None, alias="STRIPE_PACK_VIDEO_10_PRICE_ID")
    stripe_pack_video_25_price_id: str | None = Field(default=None, alias="STRIPE_PACK_VIDEO_25_PRICE_ID")
    stripe_pack_image_50_price_id: str | None = Field(default=None, alias="STRIPE_PACK_IMAGE_50_PRICE_ID")
    stripe_pack_voice_30m_price_id: str | None = Field(default=None, alias="STRIPE_PACK_VOICE_30M_PRICE_ID")
    stripe_pack_lipsync_10_price_id: str | None = Field(default=None, alias="STRIPE_PACK_LIPSYNC_10_PRICE_ID")
    stripe_pack_scripts_25_price_id: str | None = Field(default=None, alias="STRIPE_PACK_SCRIPTS_25_PRICE_ID")
    stripe_pack_creator_burst_price_id: str | None = Field(default=None, alias="STRIPE_PACK_CREATOR_BURST_PRICE_ID")
    app_base_url: str = Field(default="http://localhost:5173", alias="APP_BASE_URL")
    public_api_base_url: str = Field(default="http://localhost:3002", alias="PUBLIC_API_BASE_URL")
    # Email: prefer SendGrid Web API when SENDGRID_API_KEY is set; otherwise SMTP.
    sendgrid_api_key: str | None = Field(default=None, alias="SENDGRID_API_KEY")
    sendgrid_from_email: str | None = Field(default=None, alias="SENDGRID_FROM_EMAIL")
    sendgrid_from_name: str = Field(default="Studio", alias="SENDGRID_FROM_NAME")
    # Ops inbox for contact form notifications (comma-separated allowed).
    contact_notify_email: str | None = Field(default=None, alias="CONTACT_NOTIFY_EMAIL")
    # Cloudflare Turnstile (register + contact). Site key is public; secret stays server-side.
    turnstile_site_key: str | None = Field(default=None, alias="TURNSTILE_SITE_KEY")
    turnstile_secret_key: str | None = Field(default=None, alias="TURNSTILE_SECRET_KEY")
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from_email: str | None = Field(default=None, alias="SMTP_FROM_EMAIL")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    media_dir: str = Field(default="media", alias="MEDIA_DIR")
    # Cloudflare R2 (S3-compatible). When fully configured, media is stored in R2
    # and public URLs use R2_PUBLIC_BASE_URL (custom domain or r2.dev).
    r2_account_id: str | None = Field(default=None, alias="R2_ACCOUNT_ID")
    r2_access_key_id: str | None = Field(default=None, alias="R2_ACCESS_KEY_ID")
    r2_secret_access_key: str | None = Field(default=None, alias="R2_SECRET_ACCESS_KEY")
    r2_bucket_name: str | None = Field(default=None, alias="R2_BUCKET_NAME")
    r2_public_base_url: str | None = Field(default=None, alias="R2_PUBLIC_BASE_URL")
    r2_endpoint_url: str | None = Field(default=None, alias="R2_ENDPOINT_URL")
    r2_region: str = Field(default="auto", alias="R2_REGION")
    xai_api_key: str | None = Field(default=None, alias="XAI_API_KEY")
    xai_chat_url: str = Field(default="https://api.x.ai/v1/chat/completions", alias="XAI_CHAT_URL")
    xai_text_model: str = Field(default="grok-4.6", alias="XAI_TEXT_MODEL")
    xai_tts_url: str = Field(default="https://api.x.ai/v1/tts", alias="XAI_TTS_URL")
    xai_tts_voices_url: str = Field(default="https://api.x.ai/v1/tts/voices", alias="XAI_TTS_VOICES_URL")
    xai_tts_language: str = Field(default="en", alias="XAI_TTS_LANGUAGE")
    elevenlabs_api_key: str | None = Field(default=None, alias="ELEVENLABS_API_KEY")
    xai_image_edit_url: str = Field(
        default="https://api.x.ai/v1/images/edits", alias="XAI_IMAGE_EDIT_URL"
    )
    xai_tts_female_voice_id: str = Field(default="ara", alias="XAI_TTS_FEMALE_VOICE_ID")
    xai_tts_male_voice_id: str = Field(default="rex", alias="XAI_TTS_MALE_VOICE_ID")
    xai_image_url: str = Field(default="https://api.x.ai/v1/images/generations", alias="XAI_IMAGE_URL")
    xai_image_model: str = Field(default="grok-imagine-image-2.0", alias="XAI_IMAGE_MODEL")
    xai_video_generation_url: str = Field(default="https://api.x.ai/v1/videos/generations", alias="XAI_VIDEO_GENERATION_URL")
    xai_video_extension_url: str = Field(default="https://api.x.ai/v1/videos/extensions", alias="XAI_VIDEO_EXTENSION_URL")
    xai_video_status_url: str = Field(default="https://api.x.ai/v1/videos", alias="XAI_VIDEO_STATUS_URL")
    # grok-imagine-video-1.5: text, image, and reference-to-video (face lock)
    # at up to 15s. The original grok-imagine-video redraws faces.
    xai_video_model: str = Field(default="grok-imagine-video-1.5", alias="XAI_VIDEO_MODEL")
    # Seedance video via seevio.ai. 2.5 is the recommended model (4-30s, 720p).
    # seedance2.ai rebranded in July 2026; api.seedance2.ai is the old host.
    # Key: https://seevio.ai/dashboard/user/api-keys
    seedance_api_key: str | None = Field(default=None, alias="SEEDANCE_API_KEY")
    seedance_api_base_url: str = Field(default="https://api.seevio.ai", alias="SEEDANCE_API_BASE_URL")
    seedance_video_model: str = Field(default="seedance-2-5", alias="SEEDANCE_VIDEO_MODEL")
    # Kling AI video (official Singapore API). Prefer KLING_API_KEY; or AccessKey+SecretKey JWT.
    # Console: https://kling.ai/dev
    kling_api_key: str | None = Field(default=None, alias="KLING_API_KEY")
    kling_access_key: str | None = Field(default=None, alias="KLING_ACCESS_KEY")
    kling_secret_key: str | None = Field(default=None, alias="KLING_SECRET_KEY")
    kling_api_base_url: str = Field(
        default="https://api-singapore.klingai.com",
        alias="KLING_API_BASE_URL",
    )
    kling_video_model: str = Field(default="kling-v3", alias="KLING_VIDEO_MODEL")
    # Google Gemini image (Nano Banana family) via Interactions API
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_interactions_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/interactions",
        alias="GEMINI_INTERACTIONS_URL",
    )
    gemini_image_model: str = Field(default="gemini-3.1-flash-image", alias="GEMINI_IMAGE_MODEL")
    gemini_video_model: str = Field(default="veo-3.1-generate-preview", alias="GEMINI_VIDEO_MODEL")
    sync_labs_api_key: str | None = Field(default=None, alias="SYNC_LABS_API_KEY")
    sync_labs_base_url: str = Field(default="https://api.sync.so", alias="SYNC_LABS_BASE_URL")
    sync_labs_model: str = Field(default="sync-3", alias="SYNC_LABS_MODEL")
    # Word-level caption ASR (faster-whisper). Optional — falls back to silence/word estimate.
    asr_enabled: bool = Field(default=True, alias="ASR_ENABLED")
    asr_whisper_model: str = Field(default="tiny", alias="ASR_WHISPER_MODEL")  # tiny|base|small|...
    asr_device: str = Field(default="cpu", alias="ASR_DEVICE")  # cpu|cuda
    asr_compute_type: str = Field(default="int8", alias="ASR_COMPUTE_TYPE")  # int8|float16|float32
    asr_language: str = Field(default="en", alias="ASR_LANGUAGE")
    # Integrations: Fernet key material (falls back to JWT_SIGNING_KEY if unset)
    integration_token_key: str | None = Field(default=None, alias="INTEGRATION_TOKEN_KEY")
    shopify_api_version: str = Field(default="2024-10", alias="SHOPIFY_API_VERSION")
    shopify_client_id: str | None = Field(default=None, alias="SHOPIFY_CLIENT_ID")
    shopify_client_secret: str | None = Field(default=None, alias="SHOPIFY_CLIENT_SECRET")
    meta_app_id: str | None = Field(default=None, alias="META_APP_ID")
    meta_app_secret: str | None = Field(default=None, alias="META_APP_SECRET")
    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: str | None = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    # Apple IAP (App Store Server API). PEM private key; use \\n for newlines in env.
    apple_iap_bundle_id: str = Field(default="com.example.studio.app", alias="APPLE_IAP_BUNDLE_ID")
    apple_iap_issuer_id: str | None = Field(default=None, alias="APPLE_IAP_ISSUER_ID")
    apple_iap_key_id: str | None = Field(default=None, alias="APPLE_IAP_KEY_ID")
    apple_iap_private_key: str | None = Field(default=None, alias="APPLE_IAP_PRIVATE_KEY")
    # Dev only: accept client-reported purchases when Apple API is not configured.
    apple_iap_allow_unverified: bool = Field(default=False, alias="APPLE_IAP_ALLOW_UNVERIFIED")
    # Optional Sentry DSN for API error reporting (no-op when empty).
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    sentry_traces_sample_rate: float = Field(default=0.05, alias="SENTRY_TRACES_SAMPLE_RATE")

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        value = value.strip()
        if value.startswith("postgres://"):
            value = "postgresql+asyncpg://" + value[len("postgres://") :]
        elif value.startswith("postgresql://"):
            value = "postgresql+asyncpg://" + value[len("postgresql://") :]

        parsed = urlsplit(value)
        query = []
        for key, item in parse_qsl(parsed.query, keep_blank_values=True):
            if key == "channel_binding":
                continue
            if key == "sslmode":
                key = "ssl"
            query.append((key, item))
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))
    @field_validator("jwt_signing_key")
    @classmethod
    def validate_signing_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SIGNING_KEY must be at least 32 characters")
        return value

    @property
    def frontend_origin_list(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    def assert_production_secrets(self) -> None:
        """Fail fast when production is misconfigured with known-default secrets."""
        if not self.is_production:
            return
        default_jwt = "development-signing-key-change-me-32chars"
        if self.jwt_signing_key.strip() == default_jwt:
            raise RuntimeError(
                "JWT_SIGNING_KEY must be set to a unique secret in production "
                "(not the development default)."
            )
        if len(self.jwt_signing_key.strip()) < 32:
            raise RuntimeError("JWT_SIGNING_KEY must be at least 32 characters in production.")
        if not (self.redis_url or "").strip():
            raise RuntimeError(
                "REDIS_URL is required in production (auth rate limits fail closed without Redis)."
            )
        if not (self.seed_admin_password or "").strip():
            raise RuntimeError(
                "SEED_ADMIN_PASSWORD must be set in production (used only if admin is missing)."
            )
        if self.stripe_secret_key and not (self.stripe_webhook_secret or "").strip():
            raise RuntimeError(
                "STRIPE_WEBHOOK_SECRET is required when STRIPE_SECRET_KEY is set in production."
            )
        if not (self.turnstile_secret_key or "").strip():
            raise RuntimeError(
                "TURNSTILE_SECRET_KEY is required in production (register + contact bot protection)."
            )
        if self.apple_iap_allow_unverified:
            raise RuntimeError(
                "APPLE_IAP_ALLOW_UNVERIFIED must be false in production."
            )
        samesite = (self.refresh_cookie_samesite or "lax").strip().lower()
        if samesite not in {"lax", "strict", "none"}:
            raise RuntimeError(
                "REFRESH_COOKIE_SAMESITE must be lax, strict, or none."
            )
        # Split hosting (Pages on example.com, API on api.example.com) needs None.
        # Same-origin /api proxy can keep Lax.
        if samesite == "none" and not self.jwt_signing_key:
            raise RuntimeError("JWT_SIGNING_KEY required with REFRESH_COOKIE_SAMESITE=none.")

    @property
    def media_path(self) -> Path:
        media_dir = Path(self.media_dir)
        return media_dir if media_dir.is_absolute() else BACKEND_DIR / media_dir

    @property
    def r2_enabled(self) -> bool:
        """Private R2 bucket for user media. Public CDN base is optional (marketing only)."""
        return bool(
            self.r2_account_id
            and self.r2_access_key_id
            and self.r2_secret_access_key
            and self.r2_bucket_name
        )

    @property
    def r2_endpoint(self) -> str:
        if self.r2_endpoint_url:
            return self.r2_endpoint_url.rstrip("/")
        if not self.r2_account_id:
            raise ValueError("R2_ACCOUNT_ID is required when using Cloudflare R2")
        return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"

    @property
    def media_public_base_url(self) -> str:
        # User media is always served via /api/media (ACL + signed URLs).
        # R2_PUBLIC_BASE_URL is only for intentional public marketing assets (examples/).
        return f"{self.public_api_base_url.rstrip('/')}/api/media"

    @property
    def stripe_price_ids(self) -> dict[str, str]:
        values = {
            "starter": self.stripe_starter_price_id,
            "creator": self.stripe_creator_price_id,
            "studio": self.stripe_studio_price_id,
        }
        return {name: value for name, value in values.items() if value}

    @property
    def stripe_pack_price_ids(self) -> dict[str, str]:
        values = {
            "video_10": self.stripe_pack_video_10_price_id,
            "video_25": self.stripe_pack_video_25_price_id,
            "image_50": self.stripe_pack_image_50_price_id,
            "lipsync_10": self.stripe_pack_lipsync_10_price_id,
            "voice_30m": self.stripe_pack_voice_30m_price_id,
            "scripts_25": self.stripe_pack_scripts_25_price_id,
            "creator_burst": self.stripe_pack_creator_burst_price_id,
        }
        return {name: value for name, value in values.items() if value}


@lru_cache
def get_settings() -> Settings:
    return Settings()
