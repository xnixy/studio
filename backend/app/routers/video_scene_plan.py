"""Scene helpers for Play uploads and scene repair."""
from __future__ import annotations

import re

from app.models import VideoScene

SCENE_FIELD_RE = re.compile(r"""['"]scene['"]\s*:\s*(['"])(.+?)\1\s*[},]?$""")
TIME_PREFIX_RE = re.compile(r"""^\s*['"]?\d+\s*-\s*\d+\s*s['"]?\s*[:,\-]?\s*""", re.IGNORECASE)
AVATAR_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/pjpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}


def sniff_avatar_image(content: bytes, content_type: str | None, filename: str | None) -> tuple[str, str]:
    """Resolve (content_type, extension) from magic bytes, then headers/filename."""
    head = content[:16]
    if len(head) >= 3 and head[0:3] == b"\xff\xd8\xff":
        return "image/jpeg", ".jpg"
    if len(head) >= 8 and head[0:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", ".png"
    if len(head) >= 12 and head[0:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp", ".webp"
    if len(head) >= 12 and head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in (b"heic", b"heif", b"mif1", b"msf1", b"hevc"):
            return "image/heic", ".heic"

    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in AVATAR_IMAGE_TYPES:
        return ct, AVATAR_IMAGE_TYPES[ct]

    name = (filename or "").lower()
    if name.endswith((".jpg", ".jpeg")):
        return "image/jpeg", ".jpg"
    if name.endswith(".png"):
        return "image/png", ".png"
    if name.endswith(".webp"):
        return "image/webp", ".webp"
    if name.endswith((".heic", ".heif")):
        return "image/heic", ".heic"

    raise ValueError("unsupported_image_type")


def clean_storyboard_visual(item: str) -> str:
    """Extract the visual direction from a storyboard line (strip time codes / labels)."""
    value = item.strip()
    scene_match = SCENE_FIELD_RE.search(value)
    if scene_match:
        return scene_match.group(2).strip()
    _, separator, direction = value.partition(":")
    if separator and direction.strip():
        value = direction.strip()
    value = TIME_PREFIX_RE.sub("", value).strip()
    return value.strip(" {}[]'\"") or item.strip()


def repair_scene(scene: VideoScene) -> bool:
    if scene.visual_prompt and scene.visual_prompt.strip():
        return False
    source = str(dict(scene.scene_metadata or {}).get("source_storyboard") or "")
    scene.visual_prompt = clean_storyboard_visual(source) or (scene.on_screen_text or scene.spoken_text or "").strip()
    return bool(scene.visual_prompt)


def duration_cap_label(seconds: float) -> str:
    secs = max(1, int(round(seconds)))
    if secs % 60 == 0 and secs >= 60:
        minutes = secs // 60
        return "1 minute" if minutes == 1 else f"{minutes} minutes"
    return f"{secs}s"


def sync_labs_duration_limit(model: str) -> float | None:
    """In-flight Sync jobs still honor the old 2 minute cap."""
    return 120.0 if model.strip().lower() == "sync-3" else None


__all__ = [
    "sniff_avatar_image",
    "clean_storyboard_visual",
    "repair_scene",
    "duration_cap_label",
    "sync_labs_duration_limit",
]
