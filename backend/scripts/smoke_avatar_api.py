#!/usr/bin/env python3
"""Smoke-test avatar-first API surface.

Usage:
  STUDIO_API_BASE=http://127.0.0.1:3001 \\
  STUDIO_SMOKE_EMAIL=admin@studio.local \\
  STUDIO_SMOKE_PASSWORD=Admin123! \\
  python scripts/smoke_avatar_api.py

Exit 0 on all checks passing.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = os.environ.get("STUDIO_API_BASE", "http://127.0.0.1:3001").rstrip("/")
EMAIL = os.environ.get("STUDIO_SMOKE_EMAIL", "admin@studio.local")
PASSWORD = os.environ.get("STUDIO_SMOKE_PASSWORD", "Admin123!")

passed = 0
failed = 0


def log_ok(name: str, detail: str = "") -> None:
    global passed
    passed += 1
    extra = f" — {detail}" if detail else ""
    print(f"  OK  {name}{extra}")


def log_fail(name: str, detail: str) -> None:
    global failed
    failed += 1
    print(f"  FAIL {name} — {detail}")


def request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    body: dict[str, Any] | None = None,
    expect: int | tuple[int, ...] = 200,
) -> tuple[int, Any]:
    url = f"{BASE}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8") or "{}"
            status = resp.status
            try:
                payload: Any = json.loads(raw)
            except json.JSONDecodeError:
                payload = raw
    except HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8") if exc.fp else ""
        try:
            payload = json.loads(raw) if raw else {"error": str(exc)}
        except json.JSONDecodeError:
            payload = {"error": raw or str(exc)}
    except URLError as exc:
        raise SystemExit(f"Cannot reach {BASE}: {exc}") from exc

    expected = expect if isinstance(expect, tuple) else (expect,)
    if status not in expected:
        err = payload.get("error") if isinstance(payload, dict) else payload
        raise AssertionError(f"{method} {path} -> {status}, expected {expected}: {err}")
    return status, payload


def main() -> int:
    print(f"Smoke avatar API @ {BASE}\n")

    # --- public / health ---
    try:
        _, health = request("GET", "/api/health")
        assert health.get("status") == "healthy", health
        log_ok("GET /api/health", str(health.get("checks", {})))
    except Exception as exc:
        log_fail("GET /api/health", str(exc))

    try:
        _, root = request("GET", "/")
        assert root.get("status") == "ok", root
        log_ok("GET /", root.get("service", ""))
    except Exception as exc:
        log_fail("GET /", str(exc))

    try:
        _, models = request("GET", "/api/play/models")
        assert isinstance(models, list) and len(models) >= 1
        modalities = sorted({m.get("modality") for m in models})
        log_ok("GET /api/play/models", f"{len(models)} models, modalities={modalities}")
    except Exception as exc:
        log_fail("GET /api/play/models", str(exc))

    # --- retired surfaces should 404 ---
    retired = [
        "/api/creative/projects",
        "/api/brand/profiles",
        "/api/image-ads/packs",
        "/api/library/items",
        "/api/integrations/connections",
        "/api/v1/me",
    ]
    for path in retired:
        try:
            status, _ = request("GET", path, expect=(401, 404, 405, 422))
            # Unmounted → 404. Auth-gated leftover would be 401/422; treat as fail if 200.
            if status == 200:
                log_fail(f"retired {path}", "still returns 200")
            elif status == 404:
                log_ok(f"retired {path}", "404 unmounted")
            else:
                log_ok(f"retired {path}", f"status {status} (not open)")
        except Exception as exc:
            log_fail(f"retired {path}", str(exc))

    # --- auth ---
    token: str | None = None
    try:
        _, auth = request(
            "POST",
            "/api/auth/login",
            body={"email": EMAIL, "password": PASSWORD},
            expect=200,
        )
        token = auth.get("access_token") or auth.get("token")
        if not token and isinstance(auth.get("tokens"), dict):
            token = auth["tokens"].get("access_token")
        assert token, f"no token in login response keys={list(auth.keys()) if isinstance(auth, dict) else type(auth)}"
        log_ok("POST /api/auth/login", EMAIL)
    except Exception as exc:
        log_fail("POST /api/auth/login", str(exc))
        print("\nCannot continue authenticated checks without login.")
        print(f"Summary: {passed} passed, {failed} failed")
        return 1

    try:
        _, me = request("GET", "/api/auth/me", token=token)
        log_ok("GET /api/auth/me", me.get("email") or me.get("user", {}).get("email", ""))
    except Exception as exc:
        log_fail("GET /api/auth/me", str(exc))

    # --- workspace ---
    workspace_id: str | None = None
    try:
        _, workspaces = request("GET", "/api/workspaces", token=token)
        if isinstance(workspaces, dict) and "workspaces" in workspaces:
            rows = workspaces["workspaces"]
        else:
            rows = workspaces
        assert isinstance(rows, list) and rows, "no workspaces"
        workspace_id = str(rows[0]["id"])
        log_ok("GET /api/workspaces", f"{len(rows)} workspace(s), active={workspace_id[:8]}…")
    except Exception as exc:
        log_fail("GET /api/workspaces", str(exc))

    if workspace_id:
        try:
            _, billing = request(
                "GET",
                f"/api/billing?workspace_id={workspace_id}",
                token=token,
            )
            plan = billing.get("plan") if isinstance(billing, dict) else None
            log_ok("GET /api/billing", f"plan={plan}")
        except Exception as exc:
            log_fail("GET /api/billing", str(exc))

        try:
            _, faces = request(
                "GET",
                f"/api/play/faces?workspace_id={workspace_id}",
                token=token,
            )
            assert isinstance(faces, list)
            log_ok("GET /api/play/faces", f"{len(faces)} face(s)")
        except Exception as exc:
            log_fail("GET /api/play/faces", str(exc))

        try:
            _, gens = request(
                "GET",
                f"/api/play/generations?workspace_id={workspace_id}&limit=10",
                token=token,
            )
            assert isinstance(gens, list)
            log_ok("GET /api/play/generations", f"{len(gens)} generation(s)")
        except Exception as exc:
            log_fail("GET /api/play/generations", str(exc))

        # Validation smoke: empty prompt rejected
        try:
            request(
                "POST",
                "/api/play/generate",
                token=token,
                body={
                    "workspace_id": workspace_id,
                    "mode": "avatar",
                    "platform": "tiktok",
                    "prompt": "",
                },
                expect=(422,),
            )
            log_ok("POST /api/play/generate empty prompt", "422")
        except Exception as exc:
            log_fail("POST /api/play/generate empty prompt", str(exc))

        # Face generate without consent rejected
        try:
            request(
                "POST",
                "/api/play/faces/generate",
                token=token,
                body={
                    "workspace_id": workspace_id,
                    "prompt": "test face",
                    "label": "Smoke",
                    "consent_confirmed": False,
                },
                expect=(422,),
            )
            log_ok("POST /api/play/faces/generate no consent", "422")
        except Exception as exc:
            log_fail("POST /api/play/faces/generate no consent", str(exc))

        # Lipsync without face rejected
        try:
            request(
                "POST",
                "/api/play/generate",
                token=token,
                body={
                    "workspace_id": workspace_id,
                    "mode": "lipsync",
                    "platform": "tiktok",
                    "prompt": "Hello from smoke test.",
                },
                expect=(422,),
            )
            log_ok("POST /api/play/generate lipsync no face", "422")
        except Exception as exc:
            log_fail("POST /api/play/generate lipsync no face", str(exc))

    print(f"\nSummary: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
