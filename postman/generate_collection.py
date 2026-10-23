#!/usr/bin/env python3
"""Generate Studio Postman collection (phases 1–3) as Collection v2.1 JSON."""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).with_name("studio-api.postman_collection.json")


def tests(*lines: str) -> list[dict]:
    return [
        {
            "listen": "test",
            "script": {"type": "text/javascript", "exec": list(lines)},
        }
    ]


def prerequest(*lines: str) -> list[dict]:
    return [
        {
            "listen": "prerequest",
            "script": {"type": "text/javascript", "exec": list(lines)},
        }
    ]


def skip_if_heavy_off() -> list[dict]:
    return prerequest(
        "if (String(pm.environment.get('runHeavy') || '').toLowerCase() !== 'true') {",
        "  if (typeof pm.execution !== 'undefined' && typeof pm.execution.skipRequest === 'function') {",
        "    pm.execution.skipRequest();",
        "  } else {",
        "    throw new Error('Phase 3 skipped: set runHeavy=true to enable (or upgrade Postman CLI for skipRequest)');",
        "  }",
        "}",
    )


def ensure_run_suffix() -> list[dict]:
    """Stamp unique resource names so re-runs avoid unique DB constraints."""
    return prerequest(
        "if (!pm.collectionVariables.get('runSuffix')) {",
        "  pm.collectionVariables.set('runSuffix', Date.now().toString(36));",
        "}",
    )


def req(
    name: str,
    method: str,
    url: str,
    *,
    body: str | None = None,
    auth: str | None = None,  # None = collection bearer, "noauth", "apikey"
    events: list[dict] | None = None,
    description: str | None = None,
    headers: list[dict] | None = None,
) -> dict:
    request: dict = {
        "method": method,
        "header": headers or [],
        "url": url,
    }
    if description:
        request["description"] = description
    if auth == "noauth":
        request["auth"] = {"type": "noauth"}
    elif auth == "apikey":
        request["auth"] = {
            "type": "apikey",
            "apikey": [
                {"key": "key", "value": "X-Api-Key", "type": "string"},
                {"key": "value", "value": "{{apiKey}}", "type": "string"},
                {"key": "in", "value": "header", "type": "string"},
            ],
        }
    if body is not None:
        request["header"] = [
            *request["header"],
            {"key": "Content-Type", "value": "application/json"},
        ]
        request["body"] = {"mode": "raw", "raw": body}
    item: dict = {"name": name, "request": request}
    if events:
        item["event"] = events
    return item


def status_ok(code: int = 200) -> list[str]:
    return [
        f"pm.test('status is {code}', function () {{",
        f"  pm.response.to.have.status({code});",
        "});",
    ]


def status_one_of(*codes: int) -> list[str]:
    listed = ", ".join(str(c) for c in codes)
    return [
        f"pm.test('status is one of [{listed}]', function () {{",
        f"  pm.expect([{listed}]).to.include(pm.response.code);",
        "});",
    ]


def json_error() -> list[str]:
    return [
        "pm.test('error envelope', function () {",
        "  const body = pm.response.json();",
        "  pm.expect(body).to.have.property('error');",
        "  pm.expect(body.error).to.be.a('string').and.not.empty;",
        "});",
    ]


def save_id(var: str, path: str = "id") -> list[str]:
    return [
        f"pm.test('saves {var}', function () {{",
        "  const body = pm.response.json();",
        f"  const value = body.{path};",
        "  pm.expect(value).to.be.ok;",
        f"  pm.environment.set('{var}', value);",
        f"  pm.collectionVariables.set('{var}', value);",
        "});",
    ]


def folder(name: str, items: list[dict], description: str | None = None) -> dict:
    f: dict = {"name": name, "item": items}
    if description:
        f["description"] = description
    return f


# ---------------------------------------------------------------------------
# Phase 1
# ---------------------------------------------------------------------------

phase1 = [
    folder(
        "01 System",
        [
            req(
                "Health",
                "GET",
                "{{baseUrl}}/api/health",
                auth="noauth",
                events=tests(
                    *status_ok(200),
                    "pm.test('reports healthy', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body.status).to.eql('healthy');",
                    "  pm.expect(body.checks).to.be.an('object');",
                    "  pm.expect(body.checks).to.have.property('postgres');",
                    "});",
                ),
            ),
            req(
                "Maintenance status",
                "GET",
                "{{baseUrl}}/api/maintenance",
                auth="noauth",
                events=tests(
                    *status_ok(200),
                    "pm.test('has enabled flag', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body).to.have.property('enabled');",
                    "  pm.expect(body.enabled).to.be.a('boolean');",
                    "});",
                ),
            ),
        ],
    ),
    folder(
        "02 Auth",
        [
            req(
                "Login (admin)",
                "POST",
                "{{baseUrl}}/api/auth/login",
                auth="noauth",
                body='{\n  "email": "{{adminEmail}}",\n  "password": "{{adminPassword}}"\n}',
                events=tests(
                    *status_ok(200),
                    "pm.test('returns access token and admin user', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body.access_token).to.be.a('string').and.not.empty;",
                    "  pm.expect(body.user).to.be.an('object');",
                    "  pm.expect(body.user.email).to.eql(pm.environment.get('adminEmail').toLowerCase());",
                    "  pm.expect(body.user.role).to.eql('admin');",
                    "  pm.environment.set('accessToken', body.access_token);",
                    "  pm.collectionVariables.set('accessToken', body.access_token);",
                    "});",
                ),
                description="Seed admin login. Saves accessToken for the rest of the collection.",
            ),
            req(
                "Me",
                "GET",
                "{{baseUrl}}/api/auth/me",
                events=tests(
                    *status_ok(200),
                    "pm.test('returns current user', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body.user).to.be.an('object');",
                    "  pm.expect(body.user.email).to.eql(pm.environment.get('adminEmail').toLowerCase());",
                    "  pm.expect(body.user.role).to.eql('admin');",
                    "});",
                ),
            ),
            req(
                "Login with wrong password",
                "POST",
                "{{baseUrl}}/api/auth/login",
                auth="noauth",
                body='{\n  "email": "{{adminEmail}}",\n  "password": "WrongPassword1!"\n}',
                events=tests(*status_ok(401), *json_error()),
            ),
            req(
                "Me without token",
                "GET",
                "{{baseUrl}}/api/auth/me",
                auth="noauth",
                events=tests(*status_ok(401), *json_error()),
            ),
        ],
    ),
    folder(
        "03 Workspaces",
        [
            req(
                "List workspaces",
                "GET",
                "{{baseUrl}}/api/workspaces",
                events=tests(
                    *status_ok(200),
                    "pm.test('returns at least one workspace and saves id', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body).to.be.an('array').that.is.not.empty;",
                    "  pm.expect(body[0]).to.have.property('id');",
                    "  pm.environment.set('workspaceId', body[0].id);",
                    "  pm.collectionVariables.set('workspaceId', body[0].id);",
                    "});",
                ),
                description="Uses the first membership (personal workspace).",
            ),
        ],
    ),
    folder(
        "04 Creative",
        [
            req(
                "List creative projects",
                "GET",
                "{{baseUrl}}/api/creative/projects?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('array and optional project/concept ids', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body).to.be.an('array');",
                    "  if (body.length > 0) {",
                    "    pm.environment.set('projectId', body[0].id);",
                    "    pm.collectionVariables.set('projectId', body[0].id);",
                    "    const concepts = body[0].concepts || [];",
                    "    if (concepts.length > 0) {",
                    "      pm.environment.set('conceptId', concepts[0].id);",
                    "      pm.collectionVariables.set('conceptId', concepts[0].id);",
                    "    }",
                    "  }",
                    "});",
                ),
            ),
            req(
                "Get creative project",
                "GET",
                "{{baseUrl}}/api/creative/projects/{{projectId}}",
                events=[
                    *prerequest(
                        "const id = pm.environment.get('projectId') || pm.collectionVariables.get('projectId');",
                        "if (!id) throw new Error('projectId empty — seed/list projects first');",
                    ),
                    *tests(
                        *status_ok(200),
                        "pm.test('project shape', function () {",
                        "  const body = pm.response.json();",
                        "  pm.expect(body).to.have.property('product_input');",
                        "  pm.expect(body).to.have.property('workspace_id');",
                        "  pm.expect(body.concepts).to.be.an('array');",
                        "  if (body.concepts && body.concepts.length) {",
                        "    pm.environment.set('conceptId', body.concepts[0].id);",
                        "    pm.collectionVariables.set('conceptId', body.concepts[0].id);",
                        "  }",
                        "});",
                    ),
                ],
            ),
        ],
    ),
    folder(
        "05 Billing & jobs",
        [
            req(
                "Billing status",
                "GET",
                "{{baseUrl}}/api/billing?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('billing payload', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body).to.have.property('plan');",
                    "  pm.expect(body).to.have.property('status');",
                    "  pm.expect(body.plans).to.be.an('array');",
                    "  pm.environment.set('originalPlan', body.plan);",
                    "  pm.collectionVariables.set('originalPlan', body.plan);",
                    "});",
                ),
            ),
            req(
                "List credit packs",
                "GET",
                "{{baseUrl}}/api/billing/packs",
                events=tests(
                    *status_ok(200),
                    "pm.test('packs is array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Billing usage",
                "GET",
                "{{baseUrl}}/api/billing/usage?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('usage is array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "List jobs",
                "GET",
                "{{baseUrl}}/api/jobs?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('jobs is an array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Job stats",
                "GET",
                "{{baseUrl}}/api/jobs/stats?workspace_id={{workspaceId}}",
                events=tests(*status_ok(200)),
            ),
        ],
    ),
    folder(
        "06 System (auth)",
        [
            req(
                "TTS status",
                "GET",
                "{{baseUrl}}/api/tts/status",
                events=tests(
                    *status_ok(200),
                    "pm.test('tts config shape', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body).to.have.property('xai_api_key_configured');",
                    "  pm.expect(body).to.have.property('media_backend');",
                    "});",
                ),
            ),
            req(
                "Render status",
                "GET",
                "{{baseUrl}}/api/render/status",
                events=tests(
                    *status_ok(200),
                    "pm.test('ffmpeg availability flag', function () {",
                    "  pm.expect(pm.response.json()).to.have.property('available');",
                    "});",
                ),
            ),
            req(
                "Video providers status",
                "GET",
                "{{baseUrl}}/api/video/providers/status",
                auth="noauth",
                events=tests(
                    *status_ok(200),
                    "pm.test('providers list', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body).to.have.property('ffmpeg_available');",
                    "  pm.expect(body.providers).to.be.an('array');",
                    "});",
                ),
            ),
        ],
    ),
    folder(
        "07 Admin (read)",
        [
            req(
                "Admin overview",
                "GET",
                "{{baseUrl}}/api/admin/overview",
                events=tests(
                    *status_ok(200),
                    "pm.test('overview counters', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body).to.have.property('users');",
                    "  pm.expect(body.users).to.be.at.least(1);",
                    "});",
                ),
            ),
            req(
                "Admin users",
                "GET",
                "{{baseUrl}}/api/admin/users",
                events=tests(
                    *status_ok(200),
                    "pm.test('users array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array').that.is.not.empty;",
                    "});",
                ),
            ),
            req(
                "Admin workspaces",
                "GET",
                "{{baseUrl}}/api/admin/workspaces",
                events=tests(
                    *status_ok(200),
                    "pm.test('admin workspaces array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array').that.is.not.empty;",
                    "});",
                ),
            ),
            req(
                "Admin audit",
                "GET",
                "{{baseUrl}}/api/admin/audit?limit=20&offset=0",
                events=tests(
                    *status_ok(200),
                    "pm.test('audit page', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body).to.be.an('object');",
                    "  pm.expect(body.items).to.be.an('array');",
                    "  pm.expect(body).to.have.property('total');",
                    "  pm.expect(body).to.have.property('limit');",
                    "  pm.expect(body).to.have.property('offset');",
                    "});",
                ),
            ),
        ],
    ),
]

# ---------------------------------------------------------------------------
# Phase 2 setup + CRUD
# ---------------------------------------------------------------------------

phase2 = [
    folder(
        "08 Plan setup (Phase 2)",
        [
            req(
                "Feature gate on free (brand list expects 403 if still free)",
                "GET",
                "{{baseUrl}}/api/brand/profiles?workspace_id={{workspaceId}}",
                events=tests(
                    *status_one_of(200, 403),
                    "pm.test('if free, error mentions plan', function () {",
                    "  if (pm.response.code === 403) {",
                    "    const body = pm.response.json();",
                    "    pm.expect(body.error || '').to.match(/plan|Brand|Upgrade/i);",
                    "  }",
                    "});",
                ),
                description="Documents free-plan content-only gate. 200 is OK if already upgraded.",
            ),
            req(
                "Upgrade workspace to studio (local test)",
                "PATCH",
                "{{baseUrl}}/api/admin/workspaces/{{workspaceId}}",
                body='{\n  "plan": "studio",\n  "subscription_status": "active",\n  "limit_overrides": {\n    "script_generation_limit": 500,\n    "voiceover_seconds_limit": 3600,\n    "competitor_limit": 50,\n    "monitoring_scan_limit": 100\n  }\n}',
                events=tests(
                    *status_ok(200),
                    "pm.test('plan is studio', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body.plan).to.eql('studio');",
                    "});",
                ),
                description="Admin-only. Raises limits on local free seed. Leaves plan as studio unless cleanup restores it.",
            ),
            req(
                "Billing status after upgrade",
                "GET",
                "{{baseUrl}}/api/billing?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('plan is studio', function () {",
                    "  pm.expect(pm.response.json().plan).to.eql('studio');",
                    "});",
                ),
            ),
        ],
        description="Upgrades seed workspace to studio for higher limits. Uses admin PATCH.",
    ),
    folder(
        "09 Brand",
        [
            req(
                "Create brand profile",
                "POST",
                "{{baseUrl}}/api/brand/profiles",
                body=(
                    '{\n'
                    '  "workspace_id": "{{workspaceId}}",\n'
                    '  "name": "Postman Smoke Brand {{runSuffix}}",\n'
                    '  "status": "draft",\n'
                    '  "voice_tone": "confident",\n'
                    '  "approved_claims": ["clinically tested materials"],\n'
                    '  "prohibited_claims": ["cures disease"],\n'
                    '  "hooks": ["Stop scrolling if your feet hurt"],\n'
                    '  "ctas": ["Shop the mat"]\n'
                    "}"
                ),
                events=[*ensure_run_suffix(), *tests(*status_ok(201), *save_id("brandProfileId"))],
            ),
            req(
                "List brand profiles",
                "GET",
                "{{baseUrl}}/api/brand/profiles?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('profiles array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array').that.is.not.empty;",
                    "});",
                ),
            ),
            req(
                "Compliance check",
                "POST",
                "{{baseUrl}}/api/brand/compliance-check",
                body=(
                    '{\n'
                    '  "workspace_id": "{{workspaceId}}",\n'
                    '  "brand_profile_id": "{{brandProfileId}}",\n'
                    '  "text": "Our mat cures disease overnight with magic.",\n'
                    '  "resource_type": "custom"\n'
                    "}"
                ),
                events=tests(
                    *status_ok(200),
                    "pm.test('risk fields present', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body).to.have.property('risk_level');",
                    "  pm.expect(body).to.have.property('summary');",
                    "});",
                ),
            ),
            req(
                "Create brand fact",
                "POST",
                "{{baseUrl}}/api/brand/facts",
                body=(
                    '{\n'
                    '  "brand_profile_id": "{{brandProfileId}}",\n'
                    '  "category": "general",\n'
                    '  "fact_key": "material",\n'
                    '  "fact_value": "Medical-grade foam",\n'
                    '  "status": "pending",\n'
                    '  "confidence": 70\n'
                    "}"
                ),
                events=tests(*status_ok(201), *save_id("brandFactId")),
            ),
            req(
                "Review brand fact",
                "POST",
                "{{baseUrl}}/api/brand/facts/{{brandFactId}}/review",
                body='{\n  "status": "approved",\n  "review_notes": "postman smoke"\n}',
                events=tests(
                    *status_ok(200),
                    "pm.test('fact approved', function () {",
                    "  pm.expect(pm.response.json().status).to.eql('approved');",
                    "});",
                ),
            ),
            req(
                "Delete brand profile",
                "DELETE",
                "{{baseUrl}}/api/brand/profiles/{{brandProfileId}}",
                events=tests(*status_ok(200)),
            ),
        ],
    ),
    folder(
        "10 Research",
        [
            req(
                "Create competitor",
                "POST",
                "{{baseUrl}}/api/research/competitors",
                body=(
                    '{\n'
                    '  "workspace_id": "{{workspaceId}}",\n'
                    '  "name": "Postman Smoke Competitor {{runSuffix}}",\n'
                    '  "website_url": "https://example.com",\n'
                    '  "social_urls": ["https://tiktok.com/@example"],\n'
                    '  "notes": "created by postman smoke"\n'
                    "}"
                ),
                events=[*ensure_run_suffix(), *tests(*status_ok(201), *save_id("competitorId"))],
            ),
            req(
                "List competitors",
                "GET",
                "{{baseUrl}}/api/research/competitors?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('competitors array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array').that.is.not.empty;",
                    "});",
                ),
            ),
            req(
                "Create observation",
                "POST",
                "{{baseUrl}}/api/research/competitors/{{competitorId}}/observations",
                body=(
                    '{\n'
                    '  "format": "UGC ad",\n'
                    '  "hook": "I stopped standing on hard floors",\n'
                    '  "angle": "before/after comfort",\n'
                    '  "offer": "20% off",\n'
                    '  "source_url": "https://example.com/ad"\n'
                    "}"
                ),
                events=tests(*status_ok(201), *save_id("observationId")),
            ),
            req(
                "Create watchlist",
                "POST",
                "{{baseUrl}}/api/research/trends/watchlists",
                body=(
                    '{\n'
                    '  "workspace_id": "{{workspaceId}}",\n'
                    '  "name": "Postman Smoke Watchlist {{runSuffix}}",\n'
                    '  "keywords": ["standing desk", "anti fatigue"],\n'
                    '  "competitors": ["Postman Smoke Competitor"],\n'
                    '  "niches": ["home office"],\n'
                    '  "enabled": true\n'
                    "}"
                ),
                events=[*ensure_run_suffix(), *tests(*status_ok(201), *save_id("watchlistId"))],
            ),
            req(
                "List watchlists",
                "GET",
                "{{baseUrl}}/api/research/trends/watchlists?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('watchlists array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Delete watchlist",
                "DELETE",
                "{{baseUrl}}/api/research/trends/watchlists/{{watchlistId}}",
                events=tests(*status_ok(200)),
            ),
            req(
                "Delete observation",
                "DELETE",
                "{{baseUrl}}/api/research/competitors/{{competitorId}}/observations/{{observationId}}",
                events=tests(*status_ok(200)),
            ),
            req(
                "Delete competitor",
                "DELETE",
                "{{baseUrl}}/api/research/competitors/{{competitorId}}",
                events=tests(*status_ok(200)),
            ),
        ],
    ),
    folder(
        "11 Agency",
        [
            req(
                "Create client",
                "POST",
                "{{baseUrl}}/api/agency/clients",
                body=(
                    '{\n'
                    '  "workspace_id": "{{workspaceId}}",\n'
                    '  "name": "Postman Smoke Client {{runSuffix}}",\n'
                    '  "company_name": "Smoke LLC",\n'
                    '  "status": "active",\n'
                    '  "contact_email": "client-smoke@example.com"\n'
                    "}"
                ),
                events=[*ensure_run_suffix(), *tests(*status_ok(201), *save_id("clientId"))],
            ),
            req(
                "List clients",
                "GET",
                "{{baseUrl}}/api/agency/clients?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('clients array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array').that.is.not.empty;",
                    "});",
                ),
            ),
            req(
                "Create review",
                "POST",
                "{{baseUrl}}/api/agency/reviews",
                body=(
                    '{\n'
                    '  "workspace_id": "{{workspaceId}}",\n'
                    '  "client_id": "{{clientId}}",\n'
                    '  "title": "Postman smoke review {{runSuffix}}",\n'
                    '  "summary": "Automated review request",\n'
                    '  "resource_type": "custom"\n'
                    "}"
                ),
                events=[
                    *prerequest(
                        "const id = pm.environment.get('clientId') || pm.collectionVariables.get('clientId');",
                        "if (!id) throw new Error('clientId empty — create client first');",
                    ),
                    *tests(*status_ok(201), *save_id("reviewId")),
                ],
            ),
            req(
                "List reviews",
                "GET",
                "{{baseUrl}}/api/agency/reviews?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('reviews array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Create share link",
                "POST",
                "{{baseUrl}}/api/agency/shares",
                body=(
                    '{\n'
                    '  "workspace_id": "{{workspaceId}}",\n'
                    '  "client_id": "{{clientId}}",\n'
                    '  "title": "Postman smoke share {{runSuffix}}",\n'
                    '  "resource_type": "custom",\n'
                    '  "expires_in_hours": 24,\n'
                    '  "allow_download": false,\n'
                    '  "snapshot": {"note": "smoke"}\n'
                    "}"
                ),
                events=tests(
                    *status_ok(201),
                    *save_id("shareId"),
                    "pm.test('share_url or prefix present', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body.token_prefix || body.share_url).to.be.ok;",
                    "  if (body.share_url) {",
                    "    const parts = String(body.share_url).split('/');",
                    "    const token = parts[parts.length - 1];",
                    "    if (token && token.length > 10) {",
                    "      pm.environment.set('shareToken', token);",
                    "      pm.collectionVariables.set('shareToken', token);",
                    "    }",
                    "  }",
                    "});",
                ),
            ),
            req(
                "List shares",
                "GET",
                "{{baseUrl}}/api/agency/shares?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('shares array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Create client report",
                "POST",
                "{{baseUrl}}/api/agency/reports",
                body=(
                    '{\n'
                    '  "workspace_id": "{{workspaceId}}",\n'
                    '  "client_id": "{{clientId}}",\n'
                    '  "title": "Postman smoke report {{runSuffix}}",\n'
                    '  "report_type": "custom",\n'
                    '  "content": {"summary": "smoke report"}\n'
                    "}"
                ),
                events=tests(*status_ok(201), *save_id("reportId")),
            ),
            req(
                "List reports",
                "GET",
                "{{baseUrl}}/api/agency/reports?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('reports array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Agency activity",
                "GET",
                "{{baseUrl}}/api/agency/activity?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('activity array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Revoke share",
                "POST",
                "{{baseUrl}}/api/agency/shares/{{shareId}}/revoke",
                events=tests(*status_ok(200)),
            ),
            req(
                "Delete client",
                "DELETE",
                "{{baseUrl}}/api/agency/clients/{{clientId}}",
                events=tests(*status_ok(200)),
            ),
        ],
    ),
    folder(
        "12 Integrations & public API",
        [
            req(
                "OAuth status",
                "GET",
                "{{baseUrl}}/api/integrations/oauth/status",
                events=tests(*status_ok(200)),
            ),
            req(
                "List connections",
                "GET",
                "{{baseUrl}}/api/integrations/connections?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('connections array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "List webhooks",
                "GET",
                "{{baseUrl}}/api/integrations/webhooks?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('webhooks array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Create API key",
                "POST",
                "{{baseUrl}}/api/integrations/api-keys",
                body=(
                    '{\n'
                    '  "workspace_id": "{{workspaceId}}",\n'
                    '  "name": "postman-smoke-{{runSuffix}}",\n'
                    '  "scopes": [\n'
                    '    "read",\n'
                    '    "performance.read",\n'
                    '    "monitoring.read",\n'
                    '    "library.read",\n'
                    '    "recommendations.read",\n'
                    '    "integrations.read"\n'
                    '  ]\n'
                    "}"
                ),
                events=[
                    *ensure_run_suffix(),
                    *tests(
                        *status_ok(201),
                        "pm.test('saves api key', function () {",
                        "  const body = pm.response.json();",
                        "  pm.expect(body.id).to.be.ok;",
                        "  pm.expect(body.raw_key).to.be.a('string').and.match(/^studio_/);",
                        "  pm.environment.set('apiKeyId', body.id);",
                        "  pm.collectionVariables.set('apiKeyId', body.id);",
                        "  pm.environment.set('apiKey', body.raw_key);",
                        "  pm.collectionVariables.set('apiKey', body.raw_key);",
                        "});",
                    ),
                ],
            ),
            req(
                "Public API me",
                "GET",
                "{{baseUrl}}/api/v1/me",
                auth="apikey",
                events=tests(
                    *status_ok(200),
                    "pm.test('principal shape', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body).to.have.property('workspace_id');",
                    "  pm.expect(body).to.have.property('scopes');",
                    "});",
                ),
            ),
            req(
                "Public API metrics",
                "GET",
                "{{baseUrl}}/api/v1/metrics?limit=10",
                auth="apikey",
                events=tests(
                    *status_ok(200),
                    "pm.test('metrics array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Public API jobs",
                "GET",
                "{{baseUrl}}/api/v1/jobs?limit=10",
                auth="apikey",
                events=tests(
                    *status_ok(200),
                    "pm.test('jobs array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Public API trends",
                "GET",
                "{{baseUrl}}/api/v1/trends?limit=10",
                auth="apikey",
                events=tests(
                    *status_ok(200),
                    "pm.test('trends array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Public API library",
                "GET",
                "{{baseUrl}}/api/v1/library",
                auth="apikey",
                events=tests(
                    *status_ok(200),
                    "pm.test('library array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Public API recommendations",
                "GET",
                "{{baseUrl}}/api/v1/recommendations",
                auth="apikey",
                events=tests(
                    *status_ok(200),
                    "pm.test('recommendations array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Public API monitoring targets",
                "GET",
                "{{baseUrl}}/api/v1/monitoring/targets",
                auth="apikey",
                events=tests(
                    *status_ok(200),
                    "pm.test('targets array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Public API integrations",
                "GET",
                "{{baseUrl}}/api/v1/integrations",
                auth="apikey",
                events=tests(
                    *status_ok(200),
                    "pm.test('integrations array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Revoke API key",
                "DELETE",
                "{{baseUrl}}/api/integrations/api-keys/{{apiKeyId}}",
                events=tests(*status_ok(200)),
            ),
        ],
    ),
    folder(
        "13 Monitoring & intelligence",
        [
            req(
                "Create monitored competitor",
                "POST",
                "{{baseUrl}}/api/monitoring/competitors",
                body=(
                    '{\n'
                    '  "workspace_id": "{{workspaceId}}",\n'
                    '  "name": "Postman Monitored Brand {{runSuffix}}",\n'
                    '  "website_url": "https://example.com",\n'
                    '  "platforms": ["meta", "tiktok"],\n'
                    '  "monitoring_enabled": false,\n'
                    '  "scan_interval_hours": 24,\n'
                    '  "status": "active"\n'
                    "}"
                ),
                events=[*ensure_run_suffix(), *tests(*status_ok(201), *save_id("monitorTargetId"))],
            ),
            req(
                "List monitored competitors",
                "GET",
                "{{baseUrl}}/api/monitoring/competitors?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('targets array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Get monitored competitor",
                "GET",
                "{{baseUrl}}/api/monitoring/competitors/{{monitorTargetId}}",
                events=tests(*status_ok(200)),
            ),
            req(
                "List trend entities",
                "GET",
                "{{baseUrl}}/api/trends/entities?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('entities array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "List library items",
                "GET",
                "{{baseUrl}}/api/library/items?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('library array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Create library item",
                "POST",
                "{{baseUrl}}/api/library/items",
                body=(
                    '{\n'
                    '  "workspace_id": "{{workspaceId}}",\n'
                    '  "title": "Postman smoke hook {{runSuffix}}",\n'
                    '  "item_type": "hook",\n'
                    '  "hook_text": "Your floor is the problem",\n'
                    '  "platform": "tiktok",\n'
                    '  "status": "candidate",\n'
                    '  "tags": ["smoke"]\n'
                    "}"
                ),
                events=[*ensure_run_suffix(), *tests(*status_ok(201), *save_id("libraryItemId"))],
            ),
            req(
                "List alert subscriptions",
                "GET",
                "{{baseUrl}}/api/alerts/subscriptions?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('subscriptions array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Delete monitored competitor",
                "DELETE",
                "{{baseUrl}}/api/monitoring/competitors/{{monitorTargetId}}",
                events=tests(*status_ok(200)),
            ),
        ],
    ),
    folder(
        "14 Video (cheap)",
        [
            req(
                "List video projects",
                "GET",
                "{{baseUrl}}/api/video/projects?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('video projects array', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body).to.be.an('array');",
                    "  if (body.length > 0) {",
                    "    pm.environment.set('videoProjectId', body[0].id);",
                    "    pm.collectionVariables.set('videoProjectId', body[0].id);",
                    "  }",
                    "});",
                ),
            ),
            req(
                "List brand templates",
                "GET",
                "{{baseUrl}}/api/video/brand-templates?workspace_id={{workspaceId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('templates array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array');",
                    "});",
                ),
            ),
            req(
                "Create brand template",
                "POST",
                "{{baseUrl}}/api/video/brand-templates",
                body=(
                    '{\n'
                    '  "workspace_id": "{{workspaceId}}",\n'
                    '  "name": "Postman Smoke Template {{runSuffix}}",\n'
                    '  "primary_color": "#111827",\n'
                    '  "secondary_color": "#f9fafb",\n'
                    '  "accent_color": "#d4a017",\n'
                    '  "font_family": "Inter"\n'
                    "}"
                ),
                events=[*ensure_run_suffix(), *tests(*status_ok(201), *save_id("brandTemplateId"))],
            ),
            req(
                "Stock library",
                "GET",
                "{{baseUrl}}/api/video/stock-library",
                events=tests(*status_ok(200)),
            ),
            req(
                "Create video from concept",
                "POST",
                "{{baseUrl}}/api/video/projects/from-concept",
                body=(
                    '{\n'
                    '  "concept_id": "{{conceptId}}",\n'
                    '  "title": "Postman smoke video {{runSuffix}}",\n'
                    '  "platform": "tiktok",\n'
                    '  "aspect_ratio": "9:16",\n'
                    '  "target_duration_seconds": 30\n'
                    "}"
                ),
                events=[
                    *prerequest(
                        "const id = pm.environment.get('conceptId') || pm.collectionVariables.get('conceptId');",
                        "if (!id) throw new Error('conceptId empty — need a creative project with concepts');",
                    ),
                    *tests(
                        *status_ok(201),
                        *save_id("videoProjectId"),
                        "pm.test('has scenes', function () {",
                        "  const body = pm.response.json();",
                        "  pm.expect(body.scenes || body.id).to.be.ok;",
                        "});",
                    ),
                ],
            ),
            req(
                "Get video project",
                "GET",
                "{{baseUrl}}/api/video/projects/{{videoProjectId}}",
                events=tests(
                    *status_ok(200),
                    "pm.test('video project shape', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body).to.have.property('id');",
                    "  if (body.scenes && body.scenes.length) {",
                    "    pm.environment.set('sceneId', body.scenes[0].id);",
                    "    pm.collectionVariables.set('sceneId', body.scenes[0].id);",
                    "  }",
                    "});",
                ),
            ),
            req(
                "Delete video project",
                "DELETE",
                "{{baseUrl}}/api/video/projects/{{videoProjectId}}",
                events=tests(*status_ok(200)),
            ),
        ],
    ),
    folder(
        "15 Contact & workspace members",
        [
            req(
                "Submit contact",
                "POST",
                "{{baseUrl}}/api/contact",
                auth="noauth",
                body=(
                    '{\n'
                    '  "name": "Postman Smoke",\n'
                    '  "email": "postman-smoke@example.com",\n'
                    '  "topic": "general",\n'
                    '  "message": "Automated contact submission from Postman smoke suite."\n'
                    "}"
                ),
                events=tests(
                    *status_ok(201),
                    "pm.test('message received', function () {",
                    "  const body = pm.response.json();",
                    "  pm.expect(body).to.have.property('id');",
                    "  pm.expect(body).to.have.property('message');",
                    "});",
                ),
            ),
            req(
                "List workspace members",
                "GET",
                "{{baseUrl}}/api/workspaces/{{workspaceId}}/members",
                events=tests(
                    *status_ok(200),
                    "pm.test('members array', function () {",
                    "  pm.expect(pm.response.json()).to.be.an('array').that.is.not.empty;",
                    "});",
                ),
            ),
        ],
    ),
]

# ---------------------------------------------------------------------------
# Phase 3 — heavy / paid (skipped unless runHeavy=true)
# ---------------------------------------------------------------------------

phase3 = [
    folder(
        "16 Phase 3 Heavy (opt-in)",
        [
            req(
                "Create ad project (uses script quota / may call xAI)",
                "POST",
                "{{baseUrl}}/api/creative/projects",
                body=(
                    '{\n'
                    '  "workspace_id": "{{workspaceId}}",\n'
                    '  "product_input": "Standing desk mat for remote workers who need all-day foot support",\n'
                    '  "keywords": ["standing desk", "anti fatigue"],\n'
                    '  "competitors": [],\n'
                    '  "references": []\n'
                    "}"
                ),
                events=[
                    *skip_if_heavy_off(),
                    *tests(
                        *status_one_of(201, 402, 502),
                        "pm.test('created or expected provider/quota failure', function () {",
                        "  if (pm.response.code === 201) {",
                        "    const body = pm.response.json();",
                        "    pm.environment.set('heavyProjectId', body.id);",
                        "    pm.collectionVariables.set('heavyProjectId', body.id);",
                        "    if (body.concepts && body.concepts[0]) {",
                        "      pm.environment.set('heavyConceptId', body.concepts[0].id);",
                        "      pm.collectionVariables.set('heavyConceptId', body.concepts[0].id);",
                        "    }",
                        "  }",
                        "});",
                    ),
                ],
                description="Burns script_generation quota. May call xAI when XAI_API_KEY is set.",
            ),
            req(
                "Create concept on project",
                "POST",
                "{{baseUrl}}/api/creative/projects/{{heavyProjectId}}/concepts",
                events=[
                    *skip_if_heavy_off(),
                    *prerequest(
                        "if (String(pm.environment.get('runHeavy') || '').toLowerCase() !== 'true') return;",
                        "const id = pm.environment.get('heavyProjectId') || pm.collectionVariables.get('heavyProjectId');",
                        "if (!id) {",
                        "  if (typeof pm.execution !== 'undefined' && pm.execution.skipRequest) pm.execution.skipRequest();",
                        "  else throw new Error('heavyProjectId missing — prior create failed or was skipped');",
                        "}",
                    ),
                    *tests(
                        *status_one_of(201, 402, 502),
                        "if (pm.response.code === 201) {",
                        "  const body = pm.response.json();",
                        "  pm.environment.set('heavyConceptId', body.id);",
                        "  pm.collectionVariables.set('heavyConceptId', body.id);",
                        "}",
                    ),
                ],
            ),
            req(
                "Create voiceover (xAI TTS)",
                "POST",
                "{{baseUrl}}/api/creative/concepts/{{heavyConceptId}}/voiceovers",
                body='{\n  "voice": "female",\n  "tone": "casual"\n}',
                events=[
                    *skip_if_heavy_off(),
                    *prerequest(
                        "if (String(pm.environment.get('runHeavy') || '').toLowerCase() !== 'true') return;",
                        "const id = pm.environment.get('heavyConceptId') || pm.collectionVariables.get('heavyConceptId') || pm.environment.get('conceptId');",
                        "if (!id) {",
                        "  if (typeof pm.execution !== 'undefined' && pm.execution.skipRequest) pm.execution.skipRequest();",
                        "  else throw new Error('concept id missing for voiceover');",
                        "}",
                        "pm.environment.set('heavyConceptId', id);",
                    ),
                    *tests(
                        *status_one_of(201, 402, 502, 503),
                        "pm.test('voiceover response handled', function () {",
                        "  pm.expect(pm.response.code).to.be.oneOf([201, 402, 502, 503]);",
                        "});",
                    ),
                ],
                description="Calls xAI TTS when configured. Accepts provider/quota failures.",
            ),
            req(
                "Aligned captions",
                "GET",
                "{{baseUrl}}/api/creative/concepts/{{heavyConceptId}}/captions/aligned",
                events=[
                    *skip_if_heavy_off(),
                    *tests(*status_one_of(200, 404, 422)),
                ],
            ),
            req(
                "Generate scene image (xAI)",
                "POST",
                "{{baseUrl}}/api/video/projects/{{videoProjectId}}/scenes/{{sceneId}}/image",
                body='{\n  "prompt": null\n}',
                events=[
                    *skip_if_heavy_off(),
                    *prerequest(
                        "if (String(pm.environment.get('runHeavy') || '').toLowerCase() !== 'true') return;",
                        "const vp = pm.environment.get('videoProjectId');",
                        "const sc = pm.environment.get('sceneId');",
                        "if (!vp || !sc) {",
                        "  if (typeof pm.execution !== 'undefined' && pm.execution.skipRequest) pm.execution.skipRequest();",
                        "}",
                    ),
                    *tests(*status_one_of(201, 400, 402, 404, 502)),
                ],
                description="Requires an existing video project + scene. Creates a new video project if Phase 2 deleted the prior one — may 404.",
            ),
            req(
                "Billing checkout (Stripe — may require real Stripe)",
                "POST",
                "{{baseUrl}}/api/billing/checkout",
                body=(
                    '{\n'
                    '  "workspace_id": "{{workspaceId}}",\n'
                    '  "plan": "starter"\n'
                    "}"
                ),
                events=[
                    *skip_if_heavy_off(),
                    *tests(
                        *status_one_of(200, 400, 402, 503),
                        "pm.test('checkout response is structured', function () {",
                        "  const body = pm.response.json();",
                        "  if (pm.response.code === 200) {",
                        "    pm.expect(body).to.have.property('url');",
                        "  } else {",
                        "    pm.expect(body).to.have.property('error');",
                        "  }",
                        "});",
                    ),
                ],
                description="Does not complete payment. Opens a Stripe session URL when Stripe is configured.",
            ),
        ],
        description=(
            "Opt-in only. Set environment runHeavy=true before running.\n\n"
            "These requests may call xAI/Sync Labs/Stripe and consume quotas. "
            "Failures due to missing keys or quota are accepted as non-hard failures where noted."
        ),
    ),
    folder(
        "17 Cleanup (optional)",
        [
            req(
                "Restore original plan",
                "PATCH",
                "{{baseUrl}}/api/admin/workspaces/{{workspaceId}}",
                body='{\n  "plan": "{{originalPlan}}",\n  "subscription_status": "active",\n  "limit_overrides": {}\n}',
                events=[
                    *prerequest(
                        "if (String(pm.environment.get('restorePlan') || '').toLowerCase() !== 'true') {",
                        "  if (typeof pm.execution !== 'undefined' && typeof pm.execution.skipRequest === 'function') {",
                        "    pm.execution.skipRequest();",
                        "  }",
                        "}",
                        "const plan = pm.environment.get('originalPlan') || 'free';",
                        "pm.environment.set('originalPlan', plan);",
                    ),
                    *tests(
                        *status_one_of(200),
                        "pm.test('plan restored or still studio', function () {",
                        "  // no-op if skipped",
                        "  if (pm.response.code === 200) {",
                        "    pm.expect(pm.response.json().plan).to.be.ok;",
                        "  }",
                        "});",
                    ),
                ],
                description="Only runs when restorePlan=true. Default leaves workspace on studio for further local testing.",
            ),
        ],
    ),
]

collection = {
    "info": {
        "_postman_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "name": "Studio API (all phases)",
        "description": (
            "Full HTTP test suite for the Studio FastAPI backend.\n\n"
            "**Phase 1** — smoke (health, auth, workspaces, creative read, billing, admin reads)\n"
            "**Phase 2** — CRUD (upgrades plan to studio, brand, research, agency, public API, monitoring, video draft)\n"
            "**Phase 3** — heavy/opt-in (xAI, Stripe); skipped unless `runHeavy=true`\n\n"
            "Run with Postman CLI:\n\n"
            "```\n"
            "postman collection run postman/studio-api.postman_collection.json "
            "-e postman/studio.local.postman_environment.json\n"
            "```\n\n"
            "Regenerate this file: `python postman/generate_collection.py`"
        ),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "auth": {
        "type": "bearer",
        "bearer": [{"key": "token", "value": "{{accessToken}}", "type": "string"}],
    },
    "variable": [
        {"key": "accessToken", "value": ""},
        {"key": "workspaceId", "value": ""},
        {"key": "projectId", "value": ""},
        {"key": "conceptId", "value": ""},
        {"key": "videoProjectId", "value": ""},
        {"key": "sceneId", "value": ""},
        {"key": "brandProfileId", "value": ""},
        {"key": "brandFactId", "value": ""},
        {"key": "competitorId", "value": ""},
        {"key": "observationId", "value": ""},
        {"key": "watchlistId", "value": ""},
        {"key": "clientId", "value": ""},
        {"key": "reviewId", "value": ""},
        {"key": "shareId", "value": ""},
        {"key": "reportId", "value": ""},
        {"key": "apiKey", "value": ""},
        {"key": "apiKeyId", "value": ""},
        {"key": "monitorTargetId", "value": ""},
        {"key": "libraryItemId", "value": ""},
        {"key": "brandTemplateId", "value": ""},
        {"key": "originalPlan", "value": "free"},
        {"key": "heavyProjectId", "value": ""},
        {"key": "heavyConceptId", "value": ""},
        {"key": "runSuffix", "value": ""},
    ],
    "item": phase1 + phase2 + phase3,
}


def main() -> None:
    OUT.write_text(json.dumps(collection, indent=2) + "\n", encoding="utf-8")
    # Count requests
    def count(items: list) -> int:
        n = 0
        for it in items:
            if "item" in it:
                n += count(it["item"])
            else:
                n += 1
        return n

    print(f"Wrote {OUT} ({count(collection['item'])} requests)")


if __name__ == "__main__":
    main()
