"""Fit a lip-sync still to the selected Create format.

Sync Labs has no aspect parameter. Output size follows the input image, and
library faces are generated 1:1. Cover-crop the still to 9:16 or 1:1 before
the job so Vertical actually comes back vertical. A fit miss must never block
a paid generate: fall back to the original still.
"""
from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from pathlib import Path

from app.config import Settings
from app.media_store import MediaStoreError, ensure_local_media, safe_media_name, store_file
from app.video_renderer import ffmpeg_path

logger = logging.getLogger(__name__)

FRAME_PIXELS: dict[str, tuple[int, int]] = {
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
}

_STREAM_SIZE_RE = re.compile(r"Video:.*?(\d{2,5})x(\d{2,5})")


def cover_scale_filter(width: int, height: int, *, top: bool = False) -> str:
    """Same cover crop the scene renderer uses: fill, then crop to the frame.

    ``top`` keeps the head when a tall plate is cropped to square feed.
    """
    crop = f"crop={width}:{height}:0:0" if top else f"crop={width}:{height}"
    return f"scale={width}:{height}:force_original_aspect_ratio=increase,{crop},setsar=1"


def parse_probe_size(ffmpeg_text: str) -> tuple[int, int] | None:
    match = _STREAM_SIZE_RE.search(ffmpeg_text or "")
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def aspect_close(
    width: int,
    height: int,
    target_w: int,
    target_h: int,
    *,
    tol: float = 0.03,
) -> bool:
    if height <= 0 or target_h <= 0:
        return False
    return abs((width / height) - (target_w / target_h)) <= tol


def probe_image_size(path: Path) -> tuple[int, int] | None:
    binary = ffmpeg_path()
    if not binary:
        return None
    result = subprocess.run(
        [binary, "-hide_banner", "-i", str(path)],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    return parse_probe_size(f"{result.stderr}\n{result.stdout}")


def fit_lipsync_still(
    *,
    image_url: str,
    aspect_ratio: str,
    settings: Settings,
    stem: object,
) -> str:
    """Return a still URL in the requested aspect, or the original on any miss."""
    try:
        return _fit_lipsync_still(
            image_url=image_url,
            aspect_ratio=aspect_ratio,
            settings=settings,
            stem=stem,
        )
    except Exception:
        logger.warning("lipsync frame fit failed; using original still", exc_info=True)
        return image_url


def _fit_lipsync_still(
    *,
    image_url: str,
    aspect_ratio: str,
    settings: Settings,
    stem: object,
) -> str:
    target = FRAME_PIXELS.get((aspect_ratio or "").strip()) or FRAME_PIXELS["9:16"]
    binary = ffmpeg_path()
    if not binary:
        return image_url

    try:
        source = ensure_local_media(image_url, settings)
    except MediaStoreError:
        logger.warning("lipsync frame source is not local; using original still")
        return image_url

    size = probe_image_size(source)
    if size and aspect_close(size[0], size[1], target[0], target[1]):
        return image_url

    width, height = target
    top = bool(size and size[1] > size[0] and height <= width)
    with tempfile.TemporaryDirectory(prefix="studio-ls-frame-") as tmp:
        dest = Path(tmp) / "frame.jpg"
        command = [
            binary,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vf",
            cover_scale_filter(width, height, top=top),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(dest),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
        if result.returncode != 0 or not dest.exists() or dest.stat().st_size <= 0:
            detail = (result.stderr or result.stdout or "")[-400:]
            logger.warning("lipsync frame ffmpeg failed: %s", detail)
            return image_url
        return store_file(
            path=dest,
            subdir="lipsync-frames",
            filename=f"{safe_media_name(stem)}.jpg",
            settings=settings,
            content_type="image/jpeg",
        )
