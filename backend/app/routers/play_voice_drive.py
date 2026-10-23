"""Store ElevenLabs TTS as public MP3s for Seedance @AudioN."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from app.audio_upload import probe_audio_seconds
from app.config import Settings
from app.media_store import MediaStoreError, assert_media_reachable, public_media_url, store_bytes
from app.video_renderer import ffmpeg_path
from app.voiceover import safe_filename

MIN_TTS_SECONDS = 2.0


def pad_mp3_to_min_seconds(data: bytes, *, min_seconds: float = MIN_TTS_SECONDS) -> bytes:
    """Seedance rejects tiny audio refs. Pad with silence when the take is under 2s."""
    measured = probe_audio_seconds(data, extension=".mp3")
    if measured is None or measured >= min_seconds:
        return data
    binary = ffmpeg_path()
    if not binary:
        return data
    pad = max(0.05, min_seconds - measured)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        src = root / "in.mp3"
        out = root / "out.mp3"
        src.write_bytes(data)
        filt = (
            f"[0:a]aformat=sample_rates=24000:channel_layouts=mono[a0];"
            f"anullsrc=r=24000:cl=mono:d={pad:.3f}[s];"
            f"[a0][s]concat=n=2:v=0:a=1[out]"
        )
        cmd = [
            binary,
            "-y",
            "-i",
            str(src),
            "-filter_complex",
            filt,
            "-map",
            "[out]",
            "-c:a",
            "libmp3lame",
            str(out),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return data
        padded = out.read_bytes()
        return padded or data


async def store_tts_public(
    *,
    tts_bytes: bytes,
    settings: Settings,
    workspace_id: str,
    stem: str,
) -> tuple[str, str, float]:
    """Write TTS to storage. Returns (public_url, storage_url, seconds)."""
    padded = pad_mp3_to_min_seconds(tts_bytes)
    measured = probe_audio_seconds(padded, extension=".mp3")
    seconds = float(measured) if measured and measured > 0 else MIN_TTS_SECONDS
    filename = f"{safe_filename(str(workspace_id))}-{stem}-{uuid4().hex[:10]}.mp3"
    storage = store_bytes(
        content=padded,
        subdir="voiceovers",
        filename=filename,
        settings=settings,
        content_type="audio/mpeg",
    )
    try:
        public = await assert_media_reachable(
            public_media_url(storage, settings), settings, label="Spoken audio"
        )
    except MediaStoreError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return public, storage, seconds


def clip_duration_from_audio(seconds: float, *, max_seconds: int) -> int:
    """Seedance min is 4s. Round TTS up so the picture is never shorter than the line."""
    cap = max(4, int(max_seconds or 15))
    needed = max(4, int(round(seconds + 0.49)))
    return min(cap, needed)
