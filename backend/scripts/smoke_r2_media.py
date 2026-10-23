"""Live smoke test for R2 media + voiceover path. Run from backend/: python scripts/smoke_r2_media.py"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

import httpx

# Allow `python scripts/smoke_r2_media.py` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.media_store import (  # noqa: E402
    assert_media_reachable,
    ensure_local_media,
    get_r2_bytes,
    key_from_storage_url,
    r2_client,
    store_bytes,
)
from app.sync_labs import absolute_media_url  # noqa: E402
from app.voiceover import generate_xai_voiceover_mp3  # noqa: E402


def report(results: list[tuple[str, bool, str]], name: str, passed: bool, detail: str = "") -> None:
    results.append((name, passed, detail))
    prefix = "PASS" if passed else "FAIL"
    print(f"{prefix}  {name}" + (f" — {detail}" if detail else ""))


async def main() -> int:
    settings = Settings()
    results: list[tuple[str, bool, str]] = []
    cleanup_keys: list[str] = []
    cleanup_local: list[Path] = []

    print("=== CONFIG ===")
    print("r2_enabled:", settings.r2_enabled)
    print("media_public_base_url:", settings.media_public_base_url)
    print("xai_api_key:", bool(settings.xai_api_key))
    print("sync_labs_api_key:", bool(settings.sync_labs_api_key))
    print("public_api_base_url:", settings.public_api_base_url)

    if not settings.r2_enabled:
        report(results, "r2_enabled", False, "R2 env incomplete")
        return 1
    report(results, "r2_enabled", True, settings.media_public_base_url)

    # 1) Synthetic voiceover object
    print("\n=== 1) voiceovers/* store + public GET ===")
    fake_mp3 = b"ID3" + b"\x00" * 200 + b"studio-smoke-" + uuid.uuid4().bytes
    filename = f"smoke-voiceover-{uuid.uuid4().hex[:10]}.mp3"
    try:
        url = store_bytes(
            content=fake_mp3,
            subdir="voiceovers",
            filename=filename,
            settings=settings,
            content_type="audio/mpeg",
        )
        cleanup_keys.append(f"voiceovers/{filename}")
        cleanup_local.append(settings.media_path / "voiceovers" / filename)
        report(results, "voiceover store_bytes URL", url.startswith("https://"), url)
        key = key_from_storage_url(url, settings)
        body = get_r2_bytes(key or "", settings)
        report(results, "voiceover R2 get matches", body == fake_mp3, f"{len(body)} bytes")
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url)
        report(
            results,
            "voiceover public GET",
            resp.status_code == 200 and resp.content == fake_mp3,
            f"HTTP {resp.status_code}",
        )
        abs_url = absolute_media_url(url, settings)
        report(results, "absolute_media_url identity", abs_url == url, abs_url)
        reachable = await assert_media_reachable(url, settings, label="Smoke voiceover")
        report(results, "assert_media_reachable voiceover", True, reachable)
        local = ensure_local_media(url, settings)
        report(results, "ensure_local_media voiceover", local.exists() and local.read_bytes() == fake_mp3, str(local))
    except Exception as exc:  # noqa: BLE001
        report(results, "voiceover path", False, f"{type(exc).__name__}: {exc}")

    # 2) Avatar-shaped object
    print("\n=== 2) avatar-assets/* store + public GET ===")
    fake_jpg = b"\xff\xd8\xff\xe0" + b"studio-avatar-smoke" + b"\x00" * 100 + b"\xff\xd9"
    av_name = f"smoke-avatar-{uuid.uuid4().hex[:10]}.jpg"
    try:
        av_url = store_bytes(
            content=fake_jpg,
            subdir="avatar-assets",
            filename=av_name,
            settings=settings,
            content_type="image/jpeg",
        )
        cleanup_keys.append(f"avatar-assets/{av_name}")
        cleanup_local.append(settings.media_path / "avatar-assets" / av_name)
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(av_url)
        report(
            results,
            "avatar public GET",
            resp.status_code == 200 and resp.content == fake_jpg,
            av_url,
        )
        await assert_media_reachable(av_url, settings, label="Smoke avatar")
        report(results, "assert_media_reachable avatar", True)
    except Exception as exc:  # noqa: BLE001
        report(results, "avatar path", False, f"{type(exc).__name__}: {exc}")

    # 3) Real xAI TTS
    print("\n=== 3) Real xAI TTS generate_xai_voiceover_mp3 ===")
    real_url: str | None = None
    real_path: Path | None = None
    if not settings.xai_api_key:
        report(results, "real xAI TTS", False, "XAI_API_KEY not configured")
    else:
        try:
            real_path, real_url = await generate_xai_voiceover_mp3(
                script="This is a short Studio storage smoke test for voiceover audio.",
                voice="female",
                tone="ugc-style",
                concept_id=f"smoke-{uuid.uuid4().hex[:8]}",
                settings=settings,
            )
            if real_url:
                real_key = key_from_storage_url(real_url, settings)
                if real_key:
                    cleanup_keys.append(real_key)
            if real_path:
                cleanup_local.append(real_path)
            report(results, "real TTS public URL", bool(real_url and real_url.startswith("https://")), real_url or "")
            size = real_path.stat().st_size if real_path and real_path.exists() else 0
            report(results, "real TTS local cache", size > 1000, f"{size} bytes")
            assert real_url is not None
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(real_url)
            report(
                results,
                "real TTS public GET",
                resp.status_code == 200 and len(resp.content) > 1000,
                f"HTTP {resp.status_code}, {len(resp.content)} bytes, {resp.headers.get('content-type')}",
            )
            await assert_media_reachable(real_url, settings, label="Real voiceover")
            report(results, "real TTS preflight", True)
        except Exception as exc:  # noqa: BLE001
            report(results, "real xAI TTS", False, f"{type(exc).__name__}: {exc}")

    # 4) Live API status
    print("\n=== 4) Live API provider/tts status ===")
    bases = ["http://127.0.0.1:3002", "http://127.0.0.1:3001", settings.public_api_base_url.rstrip("/")]
    api_hit = False
    for base in bases:
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
                r = await client.get(f"{base}/api/video/providers/status")
                if r.status_code != 200:
                    print(f"  {base}/video/providers/status HTTP {r.status_code}")
                    continue
                data = r.json()
                api_hit = True
                print(f"  {base}: media_backend={data.get('media_backend')} media_base_url={data.get('media_base_url')}")
                providers = {p.get("provider"): p for p in data.get("providers") or []}
                r2 = providers.get("cloudflare_r2")
                if r2 and r2.get("configured"):
                    report(results, f"API R2 ready ({base})", True, r2.get("message") or "")
                elif r2:
                    report(results, f"API R2 ready ({base})", False, r2.get("message") or "not configured")
                else:
                    report(results, f"API R2 ready ({base})", False, "cloudflare_r2 provider missing — restart backend")

                t = await client.get(f"{base}/api/tts/status")
                if t.status_code == 200:
                    td = t.json()
                    print(f"  TTS: backend={td.get('media_backend')} public={td.get('media_public_base_url')} xai={td.get('xai_api_key_configured')}")
                    report(results, f"API TTS media_backend=r2 ({base})", td.get("media_backend") == "r2", str(td.get("media_backend")))
                break
        except Exception as exc:  # noqa: BLE001
            print(f"  {base}: unreachable ({type(exc).__name__})")
    if not api_hit:
        report(results, "live API reachable", False, "no API responded on 3002/3001/public")

    # Cleanup
    print("\n=== CLEANUP ===")
    try:
        client = r2_client(settings)
        for key in cleanup_keys:
            try:
                client.delete_object(Bucket=settings.r2_bucket_name, Key=key)
                print("deleted r2", key)
            except Exception as exc:  # noqa: BLE001
                print("cleanup r2 warn", key, exc)
    except Exception as exc:  # noqa: BLE001
        print("cleanup client warn", exc)
    for path in cleanup_local:
        try:
            if path and path.exists():
                path.unlink(missing_ok=True)
                print("deleted local", path)
        except Exception as exc:  # noqa: BLE001
            print("cleanup local warn", path, exc)

    print("\n=== SUMMARY ===")
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"{passed} passed, {failed} failed")
    for name, ok, detail in results:
        print(("PASS" if ok else "FAIL"), name, detail or "")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
