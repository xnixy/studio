"""Generate natural-looking demo avatar faces via Nano Banana Pro (Gemini).

Bypasses plan token limits (dev asset pipeline). Uploads to R2 under examples/avatars/
and writes frontend/public/examples/avatars/ plus a small JSON catalog.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.gemini_media import generate_gemini_image
from app.media_store import store_bytes

# Natural, varied, photoreal. No heavy makeup / celebrity look.
FACES: list[dict[str, str]] = [
    {
        "id": "maya",
        "label": "Maya",
        "prompt": (
            "a real 30-year-old Caucasian woman with natural blonde hair, light freckles, "
            "minimal makeup, soft smile, everyday look, photoreal head-and-shoulders portrait, "
            "natural window light, simple soft background"
        ),
    },
    {
        "id": "jordan",
        "label": "Jordan",
        "prompt": (
            "a real 28-year-old Black man with short natural hair, warm friendly expression, "
            "natural skin texture, casual crewneck, photoreal head-and-shoulders portrait, "
            "soft daylight, simple soft background"
        ),
    },
    {
        "id": "aiko",
        "label": "Aiko",
        "prompt": (
            "a real 26-year-old East Asian woman with dark hair loosely tied, natural look, "
            "soft smile, no heavy makeup, photoreal head-and-shoulders portrait, "
            "gentle daylight, simple soft background"
        ),
    },
    {
        "id": "diego",
        "label": "Diego",
        "prompt": (
            "a real 30-year-old Latino man with short dark hair, light stubble, easy smile, "
            "natural skin, casual shirt, photoreal head-and-shoulders portrait, "
            "soft outdoor light, simple soft background"
        ),
    },
    {
        "id": "priya",
        "label": "Priya",
        "prompt": (
            "a real 27-year-old South Asian woman with dark hair, natural skin tone, "
            "light natural makeup, calm smile, photoreal head-and-shoulders portrait, "
            "soft indoor light, simple soft background"
        ),
    },
]


async def main() -> None:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise SystemExit("GEMINI_API_KEY missing")

    public_dir = ROOT.parent / "frontend" / "public" / "examples" / "avatars"
    public_dir.mkdir(parents=True, exist_ok=True)

    catalog: list[dict[str, str]] = []
    for face in FACES:
        print(f"generating {face['label']} …", flush=True)
        enhanced = (
            f"Photorealistic natural portrait of {face['prompt']}. "
            "Front-facing head and shoulders, clear face, real skin texture and pores, "
            "soft natural lighting, shallow depth of field, plain out-of-focus background. "
            "Looks like a real person, not CGI, no beauty filter. "
            "No text, no watermark, no logo, no celebrity."
        )
        result = await generate_gemini_image(
            prompt=enhanced,
            aspect_ratio="1:1",
            resolution="1k",
            settings=settings,
            model="gemini-3-pro-image",
        )
        ext = ".jpg" if "jpeg" in (result.mime_type or "") or "jpg" in (result.mime_type or "") else ".jpg"
        filename = f"{face['id']}{ext}"
        # Local public SPA assets (stable for landing)
        local_path = public_dir / filename
        local_path.write_bytes(result.content)
        print(f"  local {local_path} ({len(result.content)} bytes)", flush=True)

        # R2 / storage for CDN parity with other examples
        try:
            remote = store_bytes(
                content=result.content,
                subdir="examples/avatars",
                filename=filename,
                settings=settings,
                content_type=result.mime_type or "image/jpeg",
            )
            print(f"  remote {remote}", flush=True)
        except Exception as exc:  # noqa: BLE001
            remote = f"/examples/avatars/{filename}"
            print(f"  store_bytes failed: {exc}; using local path only", flush=True)

        catalog.append(
            {
                "id": face["id"],
                "label": face["label"],
                "prompt": face["prompt"],
                "localUrl": f"/examples/avatars/{filename}",
                "url": remote if str(remote).startswith("http") else f"/examples/avatars/{filename}",
            }
        )

    catalog_path = public_dir / "catalog.json"
    catalog_path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(f"wrote {catalog_path}", flush=True)
    print("done", len(catalog), "faces", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
