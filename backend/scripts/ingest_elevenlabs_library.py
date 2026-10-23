#!/usr/bin/env python3
"""Add hosted Voice Library copies to the Studio ElevenLabs account.

Library saves use monthly add/edit ops, not Instant Voice Clone slots.
Creator has about 95 ops/month. This pass is ~67. Leave headroom for
customer clones. Re-run later for the rest of the ~120 catalog.

Usage (from backend/):
  uv run python scripts/ingest_elevenlabs_library.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "app" / "library_voices.json"
ENV_FILE = ROOT / ".env"
API_BASE = "https://api.elevenlabs.io"
SLEEP_S = 0.35


def _load_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if key:
        return key
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("ELEVENLABS_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("ELEVENLABS_API_KEY is not set")


def _request(key: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict | str]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    req = Request(
        f"{API_BASE}{path}",
        data=payload,
        method=method,
        headers={
            "xi-api-key": key,
            "Accept": "application/json",
            **({"Content-Type": "application/json"} if payload else {}),
        },
    )
    try:
        with urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw) if raw else {}
            return resp.status, data if isinstance(data, dict) else {"raw": data}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
        return exc.code, parsed
    except URLError as exc:
        raise SystemExit(f"ElevenLabs request failed: {exc}") from exc


def _detail(payload: dict | str) -> str:
    if isinstance(payload, str):
        return payload[:240]
    if not isinstance(payload, dict):
        return str(payload)[:240]
    detail = payload.get("detail")
    if isinstance(detail, dict):
        return str(detail.get("message") or detail.get("status") or detail)[:240]
    if isinstance(detail, str):
        return detail[:240]
    return str(payload)[:240]


def main() -> int:
    dry = "--dry-run" in sys.argv
    key = _load_key()
    rows = json.loads(CATALOG.read_text())
    if not isinstance(rows, list):
        raise SystemExit("library_voices.json must be a list")

    status, listed = _request(key, "GET", "/v1/voices?show_legacy=false")
    if status != 200 or not isinstance(listed, dict):
        raise SystemExit(f"Could not list account voices (HTTP {status}): {_detail(listed)}")
    existing = {
        str(v.get("voice_id") or "")
        for v in (listed.get("voices") or [])
        if isinstance(v, dict)
    }
            print(f"account already has {len(existing)} voices; catalog has {len(rows)}", flush=True)

    added = 0
    skipped = 0
    failed = 0
    changed = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or row.get("id") or "voice")
        voice_id = str(row.get("elevenlabs_voice_id") or "").strip()
        owner_id = str(row.get("public_owner_id") or "").strip()
        if not voice_id or not owner_id:
            failed += 1
            print(f"skip {name}: missing ids")
            continue
        if voice_id in existing:
            skipped += 1
            continue
        if dry:
            print(f"dry-run would add {name}")
            added += 1
            continue
        code, payload = _request(
            key,
            "POST",
            f"/v1/voices/add/{owner_id}/{voice_id}",
            {"new_name": name, "bookmarked": False},
        )
        if code in {200, 201} and isinstance(payload, dict):
            new_id = str(payload.get("voice_id") or voice_id).strip()
            if new_id and new_id != voice_id:
                row["elevenlabs_voice_id"] = new_id
                changed = True
            existing.add(new_id or voice_id)
            added += 1
            print(f"added {name}")
        elif code == 400 and "already" in _detail(payload).lower():
            skipped += 1
            existing.add(voice_id)
            print(f"already on account: {name}")
        else:
            failed += 1
            detail = _detail(payload)
            print(f"failed {name} HTTP {code}: {detail}")
            lowered = detail.lower()
            if code in {401, 403} or "limit" in lowered or "quota" in lowered:
                print("stopping. monthly add/edit ops or auth likely exhausted.")
                break
        time.sleep(SLEEP_S)

    if changed:
        CATALOG.write_text(json.dumps(rows, indent=2) + "\n")
        print("updated library_voices.json with account voice ids")
    print(f"done added={added} skipped={skipped} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
