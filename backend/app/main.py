from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import BACKEND_DIR, get_settings
from app.database import SessionLocal
from app.rate_limit import RateLimiter

logger = logging.getLogger("studio")
from app.routers.admin_jobs import router as admin_jobs_router
from app.routers.admin_ops import router as admin_ops_router
from app.routers.admin_overview import router as admin_overview_router
from app.routers.admin_tenants import router as admin_tenants_router
from app.routers.admin_users import router as admin_users_router
from app.routers.auth import router as auth_router
from app.routers.billing import router as billing_router
from app.routers.billing_addons import router as billing_addons_router
from app.routers.contact import router as contact_router
from app.routers.jobs import router as jobs_router
from app.routers.media import router as media_router
from app.routers.public_shares import router as public_shares_router
from app.routers.system import router as system_router
from app.routers.video import router as video_router
from app.routers.workspaces_api import router as workspaces_router
from app.routers.notifications import router as notifications_router
from app.routers.devices import router as devices_router
from app.routers.iap import router as iap_router
from app.routers.play import router as play_router
from app.routers.ws_renders import router as ws_renders_router
from app.seed import seed_data
from app.events.hub import event_hub

settings = get_settings()
settings.assert_production_secrets()
settings.media_path.mkdir(parents=True, exist_ok=True)


def _init_sentry() -> None:
    dsn = (settings.sentry_dsn or "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        logger.warning("SENTRY_DSN set but sentry-sdk is not installed")
        return
    sentry_sdk.init(
        dsn=dsn,
        environment=settings.app_env,
        traces_sample_rate=max(0.0, min(1.0, float(settings.sentry_traces_sample_rate))),
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        send_default_pii=False,
    )
    logger.info("sentry initialized")


_init_sentry()


def _upgrade_database() -> None:
    """Locate alembic.ini whether running from source or an installed image layout."""
    from pathlib import Path

    candidates = [
        BACKEND_DIR / "alembic.ini",
        Path.cwd() / "alembic.ini",
    ]
    for parent in Path(__file__).resolve().parents:
        candidates.append(parent / "alembic.ini")
    ini_path = next((p for p in candidates if p.is_file()), None)
    if ini_path is None:
        raise FileNotFoundError("alembic.ini not found for database migrations")
    config = AlembicConfig(str(ini_path))
    script_location = ini_path.parent / "alembic"
    if script_location.is_dir():
        config.set_main_option("script_location", str(script_location))
    command.upgrade(config, "head")

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.run_db_migrations_on_startup:
        try:
            await asyncio.to_thread(_upgrade_database)
        except Exception as exc:
            # Surface migration failures clearly in platform logs during deploy verify.
            logger.exception("database migration failed: %s", exc)
            raise
    limiter = RateLimiter(settings.redis_url)
    await limiter.connect()
    app.state.rate_limiter = limiter
    await event_hub.start(settings.redis_url)

    # Operator visibility in Cloud logs (booleans only — never log secret values).
    # Print to stdout so FastAPI Cloud captures it even if app logger level is muted.
    from app.kling_media import kling_configured

    print(
        "provider keys:"
        f" xai={bool(settings.xai_api_key)}"
        f" gemini={bool(settings.gemini_api_key)}"
        f" seedance={bool(settings.seedance_api_key)}"
        f" kling={kling_configured(settings)}"
        f" sync_labs={bool(settings.sync_labs_api_key)}"
        f" apple_iap={bool(settings.apple_iap_key_id and settings.apple_iap_issuer_id and settings.apple_iap_private_key)}",
        flush=True,
    )
    logger.info(
        "provider keys: xai=%s gemini=%s seedance=%s kling=%s sync_labs=%s",
        bool(settings.xai_api_key),
        bool(settings.gemini_api_key),
        bool(settings.seedance_api_key),
        kling_configured(settings),
        bool(settings.sync_labs_api_key),
    )

    async with SessionLocal() as session:
        await seed_data(session, settings)
        # Free plan quota locked by abandoned mid-flight AI jobs (crash / deploy).
        from app.workspace_access import release_stale_reservations

        released = await release_stale_reservations(session)
        if released:
            logger.info("released %s stale usage reservation(s)", released)
        await session.commit()

    yield
    # Shut down Redis-backed services before the event loop closes (quiet reloads).
    try:
        await event_hub.stop()
    except Exception:
        logger.warning("event hub stop failed", exc_info=True)
    try:
        await limiter.close()
    except Exception:
        logger.warning("rate limiter close failed", exc_info=True)


# Interactive docs and OpenAPI schema are disabled in production to reduce recon surface.
# Local/dev keep Scalar at /api/docs plus classic Swagger/ReDoc.
_docs_url = None if settings.is_production else "/docs"
_redoc_url = None if settings.is_production else "/redoc"
_openapi_url = None if settings.is_production else "/openapi.json"

app = FastAPI(
    title="Studio API",
    description=(
        "HTTP API for studio: avatar-first create (faces, clips), auth, workspaces, billing, "
        "and media. Interactive docs auto-update from this OpenAPI schema."
    ),
    version="0.2.0",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
    swagger_ui_parameters={"persistAuthorization": True},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Api-Key",
        "Stripe-Signature",
        "Accept",
        "X-Studio-Client",
        # Web generate sends this on every submit so a resubmit cannot start a
        # second paid job. Missing here, the preflight failed and the browser
        # reported a network error, so generate never worked from the browser
        # at all. Native fetch does not enforce CORS, which is why only web saw it.
        "Idempotency-Key",
        # Progressive video / AVPlayer-style range probes (web + some native stacks).
        "Range",
        "If-Range",
    ],
    expose_headers=[
        "Accept-Ranges",
        "Content-Range",
        "Content-Length",
        "Content-Type",
        "Content-Disposition",
    ],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    # Structured details (e.g. plan_advanced_required) pass code + message for clients.
    if isinstance(exc.detail, dict):
        message = str(exc.detail.get("message") or exc.detail.get("detail") or "Request failed")
        body: dict = {"error": message, **{k: v for k, v in exc.detail.items() if k != "message"}}
        if "message" not in body:
            body["message"] = message
        return JSONResponse(body, status_code=exc.status_code, headers=exc.headers)
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse({"error": detail}, status_code=exc.status_code, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    message = first.get("msg", "Validation failed")
    return JSONResponse({"error": message}, status_code=422)


# Paths allowed while maintenance mode is on (health, public config, auth, billing webhooks).
_MAINTENANCE_ALLOW_PREFIXES = (
    "/api/health",
    "/api/public-config",
    "/api/maintenance",
    "/api/auth/",
    "/api/billing/webhook",
    "/api/billing/iap/notifications",
    "/api/contact",
)
_MAINTENANCE_ALLOW_EXACT = {"/", "/api/health", "/api/public-config", "/api/maintenance", "/api/contact"}


@app.middleware("http")
async def maintenance_gate(request: Request, call_next):
    path = request.url.path
    if request.method == "OPTIONS":
        return await call_next(request)
    if path in _MAINTENANCE_ALLOW_EXACT or any(path.startswith(p) for p in _MAINTENANCE_ALLOW_PREFIXES):
        return await call_next(request)
    # Admin can still operate during maintenance.
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        # Defer full admin check to route handlers when not in maintenance;
        # only short-circuit when flag is on (cheap DB read).
        pass
    try:
        async with SessionLocal() as session:
            from app.models import MaintenanceSetting

            setting = await session.get(MaintenanceSetting, 1)
            if setting is None or not setting.enabled:
                return await call_next(request)
            message = setting.message or "The site is currently under maintenance. Please check back soon."
    except Exception:
        # If maintenance lookup fails, do not block traffic.
        return await call_next(request)

    # Allow admins through (best-effort decode without full dependency stack).
    if auth.lower().startswith("bearer "):
        try:
            from app.security import decode_access_token

            claims = decode_access_token(auth.split(" ", 1)[1], settings)
            if claims and claims.get("role") == "admin":
                return await call_next(request)
        except Exception:
            pass

    return JSONResponse({"error": message}, status_code=503)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # Media is loaded by the SPA / mobile clients on other origins; use cross-origin
    # so <video>/<img> are not blocked. Other API responses stay same-site.
    path = request.url.path
    if path.startswith("/api/media/"):
        response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
    else:
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"
    # Docs HTML needs scripts/styles from Scalar CDN; API JSON stays locked down.
    if path in {"/api/docs", "/docs", "/redoc"} or path.startswith("/docs/") or path.startswith("/redoc"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.scalar.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.scalar.com https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; base-uri 'none'"
        )
    else:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def _mount(router) -> None:
    app.include_router(router, prefix="/api")


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Lightweight root used by some platform health checks."""
    return {"service": "studio-api", "status": "ok"}


# Core product surface (avatar-first create + account).
_mount(system_router)
_mount(media_router)
_mount(auth_router)
_mount(admin_overview_router)
_mount(admin_users_router)
_mount(admin_tenants_router)
_mount(admin_jobs_router)
_mount(admin_ops_router)
_mount(contact_router)
_mount(workspaces_router)
_mount(billing_router)
_mount(billing_addons_router)
_mount(jobs_router)
_mount(public_shares_router)
_mount(video_router)  # asset poll / media helpers used by Play
_mount(notifications_router)
_mount(devices_router)
_mount(iap_router)
_mount(play_router)
_mount(ws_renders_router)


def _register_api_docs() -> None:
    """Modern interactive API reference (Scalar). Disabled entirely in production."""
    if settings.is_production:
        return

    @app.get("/api/openapi.json", include_in_schema=False, tags=["docs"])
    async def openapi_under_api_prefix():
        # Same schema as /openapi.json for same-origin proxies that only forward /api/*
        return app.openapi()

    try:
        from scalar_fastapi import get_scalar_api_reference
    except ImportError:  # pragma: no cover - optional until image rebuild
        return

    @app.get("/api/docs", include_in_schema=False, tags=["docs"])
    async def scalar_api_docs():
        return get_scalar_api_reference(
            openapi_url="/api/openapi.json",
            title="Studio API",
            # Prefer local servers from OpenAPI; no external proxy required on same origin.
            scalar_proxy_url=None,
        )

    @app.get("/docs/scalar", include_in_schema=False, tags=["docs"])
    async def scalar_api_docs_alias():
        return get_scalar_api_reference(
            openapi_url="/api/openapi.json",
            title="Studio API",
            scalar_proxy_url=None,
        )


_register_api_docs()
