# Studio

Studio is a self-hostable app for making short AI video clips and still images from a chat-style box.

Pick a **Face** (a head-and-shoulders photo), type what should happen, and Studio turns it into:

- **Talking** clips: the Face says your line, lip-synced to a stock or cloned voice
- **Scene** clips: a short video of whatever you describe, with or without a Face
- **Stills**: single images

It comes with a web app, an iOS app, workspaces, credits and plans, and an admin console.

| Part | Stack | Folder |
|------|-------|--------|
| Web app | React, Vite, TypeScript, Tailwind | [`frontend/`](frontend) |
| iOS app | Expo (React Native) with SwiftUI chrome | [`mobile/`](mobile) |
| API | FastAPI, SQLAlchemy, Alembic | [`backend/`](backend) |
| Workers | Python job and render workers (same code as the API) | [`backend/app/`](backend/app) |
| Data | PostgreSQL 16, Redis 7 | via Docker |

> Generating media calls paid third-party AI APIs. You bring your own keys. Without keys the app still runs, you can sign in and click around, but generate requests will fail.

## Quick start (Docker)

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine with Compose).

```bash
git clone <this repo> studio
cd studio

# The containers read this file. The defaults work for local use.
cp backend/.env.example backend/.env

docker compose up --build
```

When it is up:

| What | URL |
|------|-----|
| Web app | <http://localhost:8080> |
| API health | <http://localhost:3001/api/health> |
| API reference (Scalar) | <http://localhost:3001/api/docs> |

Sign in with the built-in admin account:

| Email | Password |
|-------|----------|
| `admin@studio.local` | `Admin123!` |

This account is created on first start and only gets that default password outside production.

**New sign-ups need email.** Registering a new account sends a confirmation link, and you cannot sign in until you open it. Locally, either use the admin account, or set `SMTP_*` (any SMTP server works, for example [Mailpit](https://mailpit.axllent.org/) on `localhost:1025` with `SMTP_USE_TLS=false`) or `SENDGRID_*` in `backend/.env`.

### Add your AI keys

Put keys in `backend/.env`, then restart (`docker compose up -d --force-recreate backend job-worker render-worker`).

| Feature | Variable | Provider |
|---------|----------|----------|
| Video clips (Talking and Scene) | `SEEDANCE_API_KEY` | Seedance |
| Prompt helper, stills, Face edit | `XAI_API_KEY` | xAI (Grok) |
| Stills (Nano Banana) | `GEMINI_API_KEY` | Google Gemini |
| Stock voices, voice cloning, speech | `ELEVENLABS_API_KEY` | ElevenLabs |
| Word-level captions | none, runs locally | faster-whisper |

`KLING_*` and `SYNC_LABS_*` are only kept so older in-flight jobs can finish. You can leave them empty.

The API prints which providers it found on startup (`provider keys: xai=True ...`).

## Develop without Docker

Run Postgres and Redis in Docker, and the rest on your machine. You need **Python 3.12+**, [**uv**](https://docs.astral.sh/uv/), and **Node.js 20.19+ (or 22.12+)**.

```bash
docker compose up -d postgres redis
cp backend/.env.example backend/.env
```

**API** (terminal 1):

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 3001
```

**Workers** (terminal 2). Clips are polled and finished by the job worker, so generation stalls if it is not running:

```bash
cd backend
uv run python -m app.job_worker --poll-seconds 5
# optional, only for the older project render pipeline:
uv run python -m app.render_worker --poll-seconds 5
```

**Web app** (terminal 3):

```bash
cd frontend
cp .env.example .env.local   # VITE_API_BASE_URL=/api, proxied to :3001 by Vite
npm install
npm run dev
```

Open <http://localhost:5173>.

A dev container is also included (`.devcontainer/`) if you use VS Code or another editor that supports it.

## iOS app

See [`mobile/README.md`](mobile/README.md). In short: `cd mobile && npm install && npx expo run:ios`, with the API running and reachable from your device.

## Tests

```bash
cd backend && uv run pytest -q     # API tests
cd frontend && npm run build       # type check and production build
cd mobile && npx tsc --noEmit      # type check
```

Postman collections for the HTTP API live in [`postman/`](postman).

## Configuration

All backend settings are environment variables. [`backend/.env.example`](backend/.env.example) lists every one with a comment. The ones you are most likely to touch:

| Variable | What it does |
|----------|--------------|
| `DATABASE_URL`, `REDIS_URL` | Postgres and Redis connections |
| `JWT_SIGNING_KEY` | Signs login tokens. At least 32 characters. **Change it** for anything public |
| `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD` | The admin account created on first start |
| `APP_BASE_URL` | Where the web app lives. Used in email links |
| `PUBLIC_API_BASE_URL` | Public URL of the API. AI providers download audio and video from here, so it must be reachable from the internet when you generate |
| `FRONTEND_ORIGINS` | Comma-separated origins allowed to call the API from a browser |
| `R2_*` | Optional Cloudflare R2 bucket for media. Without it, media is stored on local disk under `MEDIA_DIR` |
| `STRIPE_*` | Optional web billing. Create your own products and prices in Stripe |
| `SENDGRID_*` or `SMTP_*` | Outgoing email (sign-up confirmation, password reset) |
| `TURNSTILE_*` | Cloudflare Turnstile captcha on sign-up and contact. Optional locally, required in production |
| `APPLE_IAP_*` | In-app purchases for the iOS app. See [`docs/IOS_IAP.md`](docs/IOS_IAP.md) |

Web app (`frontend/.env.local`):

| Variable | What it does |
|----------|--------------|
| `VITE_API_BASE_URL` | `/api` in local dev. For a deployed site on a different origin, the full API URL, e.g. `https://api.example.com/api` |
| `VITE_TURNSTILE_SITE_KEY` | Optional Turnstile site key |

**A note on `PUBLIC_API_BASE_URL` when developing:** Talking clips send generated speech to the video provider as a URL. If your API is only on `localhost`, the provider cannot fetch it. Use a tunnel (for example Cloudflare Tunnel or ngrok) or configure `R2_*` so media is served from a public bucket.

## How it fits together

```
browser / iOS app ──> FastAPI (/api) ──> Postgres, Redis
                           │
                           └─ queues jobs ──> job worker ──> AI providers
                                                   │
                                                   └─ stores result (local disk or R2), refunds credits on failure
```

- There is no cron. Workers poll the database for jobs.
- Media URLs are always `/api/media/...` and need a signed URL or a signed-in user who can see that workspace.
- Interactive API docs are turned off when `APP_ENV=production`.

API route groups:

| Prefix | Area |
|--------|------|
| `/api/auth` | Sign up, sign in, profile |
| `/api/workspaces` | Workspaces and members |
| `/api/play` | Create: Faces, references, generate, prompt helper |
| `/api/video` | Clip status and polling |
| `/api/billing` | Plans, credits, Stripe checkout and webhook, Apple IAP |
| `/api/media` | Private media |
| `/api/admin` | Admin console |
| `/api/public/shares` | Password-protected share links |
| `/api/notifications`, `/api/devices` | In-app and push notifications |

## Project layout

```
backend/        FastAPI app, workers, Alembic migrations, tests, scripts
frontend/       React web app (marketing pages, docs, Create, Library, admin)
mobile/         Expo iOS app
docs/           iOS in-app purchase setup
postman/        API test collections
AGENTS.md       Code conventions and product rules (read before larger changes)
```

## Running it in production

There is no deploy setup in this repo, so host it wherever you like. You need:

1. The `backend/` image (see `backend/Dockerfile`) running the API.
2. The same image running `python -m app.job_worker` as a separate always-on process.
3. Postgres and Redis.
4. The `frontend/` build (`npm run build`, output in `frontend/dist`) on any static host, or the included nginx image.

Minimum production settings:

```bash
APP_ENV=production
JWT_SIGNING_KEY=...            # long random string
SEED_ADMIN_PASSWORD=...        # required in production
TURNSTILE_SECRET_KEY=...       # required in production
FRONTEND_ORIGINS=https://your-domain.com
APP_BASE_URL=https://your-domain.com
PUBLIC_API_BASE_URL=https://api.your-domain.com
REFRESH_COOKIE_SAMESITE=none   # when the web app and API are on different origins
TRUST_PROXY_HEADERS=true       # only behind a proxy such as Cloudflare or nginx
```

Run `alembic upgrade head` once per release (the Docker image does this on start).

## Before you launch your own service

- **Branding.** The name "Studio" and the placeholder icons are meant to be replaced. Icons are generated by `frontend/scripts/make_icons.py`. Domains in the code use `example.com`.
- **Legal pages.** Privacy and Terms (`frontend/src/pages/PrivacyPage.tsx`, `TermsPage.tsx`) are sample text. Replace them with your own.
- **iOS identifiers.** The bundle ID is `com.example.studio.app`, and the Apple team ID in `frontend/public/apple-app-site-association` is `YOUR_TEAM_ID`. Change both to yours.
- **Plans and prices** live in `backend/app/plans.py` and `frontend/src/marketing/plans.ts`. Keep them in sync.

## License

[MIT](LICENSE)
