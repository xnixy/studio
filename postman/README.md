# Studio API tests (Postman CLI)

Automated HTTP suite for the FastAPI backend. Complements `/api/docs` (interactive) with **scripted multi-request checks** you can run unattended.

## Prerequisites

1. **API running** (Docker or local uvicorn), e.g. `http://localhost:3001`
2. **Postman CLI** on your `PATH` — `postman --version`
3. **Local seed admin** (non-production):

| Variable | Default |
|----------|---------|
| `adminEmail` | `admin@studio.local` |
| `adminPassword` | `Admin123!` |

## Files

| File | Purpose |
|------|---------|
| `studio-api.postman_collection.json` | Full collection (phases 1–3) — generated |
| `studio.local.postman_environment.json` | Local `baseUrl` + credentials + flags |
| `generate_collection.py` | Regenerates the collection JSON |

```powershell
python postman/generate_collection.py
```

## Run with Postman CLI

From the **repo root**:

```powershell
# Phase 1 + 2 (default). Phase 3 heavy requests are skipped.
postman collection run postman/studio-api.postman_collection.json `
  -e postman/studio.local.postman_environment.json
```

Other port:

```powershell
postman collection run postman/studio-api.postman_collection.json `
  -e postman/studio.local.postman_environment.json `
  --env-var "baseUrl=http://localhost:3002"
```

**Phase 3 heavy** (xAI TTS/image, script creation, Stripe checkout session — may cost quota/money):

```powershell
postman collection run postman/studio-api.postman_collection.json `
  -e postman/studio.local.postman_environment.json `
  --env-var "runHeavy=true"
```

**Restore plan to free after run** (default leaves workspace on **studio** so Phase 2 features stay unlocked):

```powershell
postman collection run postman/studio-api.postman_collection.json `
  -e postman/studio.local.postman_environment.json `
  --env-var "restorePlan=true"
```

Stop on first failure:

```powershell
postman collection run postman/studio-api.postman_collection.json `
  -e postman/studio.local.postman_environment.json `
  --bail
```

Reports:

```powershell
postman collection run postman/studio-api.postman_collection.json `
  -e postman/studio.local.postman_environment.json `
  -r cli,html,junit `
  --reporter-html-export postman/reports/smoke.html `
  --reporter-junit-export postman/reports/smoke.xml
```

Exit code: **0** if all executed assertions pass, non-zero on failure.

## Phases

| Phase | Folders | What |
|-------|---------|------|
| **1 Smoke** | 01–07 | Health, login, workspaces, creative list/get, billing, jobs, TTS/render, admin reads, 401 negatives |
| **2 CRUD** | 08–15 | Upgrade plan → studio, brand, research, agency clients/reviews/shares/reports, API keys + `/api/v1/*`, monitoring, library, video draft from concept, contact, invites |
| **3 Heavy** | 16 | Script project create, concept, voiceover, scene image, Stripe checkout — **skipped** unless `runHeavy=true` |
| **Cleanup** | 17 | Restore original plan if `restorePlan=true` |

### Plan upgrade (important)

Phase 2 starts with a plan upgrade for higher limits:

`PATCH /api/admin/workspaces/{{workspaceId}}` → `plan: studio`

That mutates your local seed workspace. Leave it, or set `restorePlan=true`.

## Environment variables

| Key | Default | Role |
|-----|---------|------|
| `baseUrl` | `http://localhost:3001` | API origin (no trailing `/api`) |
| `adminEmail` / `adminPassword` | seed admin | Login |
| `runHeavy` | `false` | Enable Phase 3 |
| `restorePlan` | `false` | Reset plan after run |
| `accessToken`, `workspaceId`, … | (set by tests) | Chained IDs |

## Import in Postman desktop

1. Import collection + environment  
2. Select **Studio local**  
3. Collection Runner → Run  

## Related

- Interactive docs: `http://localhost:3001/api/docs`
- OpenAPI: `http://localhost:3001/api/openapi.json`
- Unit tests: `backend/tests/`
