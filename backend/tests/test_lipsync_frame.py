"""Lip-sync stills are cover-cropped to the selected Create format."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.lipsync_frame import (
    aspect_close,
    cover_scale_filter,
    fit_lipsync_still,
    parse_probe_size,
    probe_image_size,
)
from app.video_renderer import ffmpeg_path


def test_cover_filter_top_pins_the_head() -> None:
    assert cover_scale_filter(1080, 1080, top=True) == (
        "scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080:0:0,setsar=1"
    )


def test_parse_probe_size_reads_the_video_stream() -> None:
    text = (
        "Input #0, image2, from 'face.jpg':\n"
        "  Stream #0:0: Video: mjpeg (Baseline), yuvj420p(pc), 1024x1024, 25 fps\n"
    )
    assert parse_probe_size(text) == (1024, 1024)


def test_square_is_not_close_to_vertical() -> None:
    assert aspect_close(1024, 1024, 1080, 1920) is False
    assert aspect_close(1080, 1920, 1080, 1920) is True
    assert aspect_close(720, 1280, 1080, 1920) is True


def test_fit_cover_crops_square_to_vertical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    binary = ffmpeg_path()
    if not binary:
        pytest.skip("ffmpeg is not available")
    from app.config import Settings

    src = tmp_path / "square.jpg"
    result = subprocess.run(
        [
            binary,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=512x512",
            "-frames:v",
            "1",
            str(src),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0 or not src.exists():
        pytest.skip("ffmpeg could not write a test still")

    settings = Settings(MEDIA_DIR=str(tmp_path / "media"))
    monkeypatch.setattr(type(settings), "r2_enabled", property(lambda self: False))
    settings.media_path.mkdir(parents=True, exist_ok=True)
    stored = tmp_path / "media" / "faces" / "square.jpg"
    stored.parent.mkdir(parents=True, exist_ok=True)
    stored.write_bytes(src.read_bytes())

    out = fit_lipsync_still(
        image_url="/api/media/faces/square.jpg",
        aspect_ratio="9:16",
        settings=settings,
        stem="ls-test",
    )
    assert out != "/api/media/faces/square.jpg"
    fitted = settings.media_path / "lipsync-frames" / "ls-test.jpg"
    assert fitted.exists()
    size = probe_image_size(fitted)
    assert size == (1080, 1920)
