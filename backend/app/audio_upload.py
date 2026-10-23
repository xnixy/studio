"""Shared audio upload sniffing and duration probe for voice clones / TTS."""
from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from pathlib import Path

from app.video_renderer import ffmpeg_path

log = logging.getLogger(__name__)

MAX_CUSTOM_VOICE_UPLOAD_BYTES = 10 * 1024 * 1024
MIN_CLONE_SAMPLE_SECONDS = 20.0
MAX_CLONE_SAMPLE_SECONDS = 120.0

ALLOWED_AUDIO_CONTENT_TYPES = frozenset(
    {
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "audio/m4a",
        "audio/x-m4a",
        "audio/ogg",
        "audio/opus",
        "audio/flac",
        "audio/aac",
        "audio/mp4a-latm",
        "audio/3gpp",
        "audio/x-caf",
        "audio/caf",
        "audio/aiff",
        "audio/x-aiff",
        "audio/webm",
        "video/mp4",
        "video/webm",
        "application/octet-stream",
    }
)

ALLOWED_AUDIO_EXTENSIONS = frozenset(
    {
        ".wav",
        ".mp3",
        ".m4a",
        ".ogg",
        ".opus",
        ".flac",
        ".aac",
        ".mp4",
        ".webm",
        ".caf",
        ".aiff",
        ".aif",
    }
)

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_MEAN_VOLUME_RE = re.compile(r"mean_volume:\s*([-\d.]+)\s*dB", re.I)

_MIME_TO_EXT = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".m4a",
    "audio/m4a": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/mp4a-latm": ".m4a",
    "audio/aac": ".aac",
    "audio/aiff": ".aiff",
    "audio/x-aiff": ".aiff",
    "audio/3gpp": ".m4a",
    "audio/x-caf": ".caf",
    "audio/caf": ".caf",
    "video/mp4": ".m4a",
    "audio/ogg": ".ogg",
    "audio/opus": ".ogg",
    "audio/webm": ".webm",
    "video/webm": ".webm",
    "audio/flac": ".flac",
}


def _ext_from_magic(content: bytes) -> str | None:
    """Guess extension when iOS Voice Memos omit a filename suffix."""
    if content[:4] == b"caff":
        return ".caf"
    if content[:4] == b"FORM" and b"AIFF" in content[4:16]:
        return ".aiff"
    if len(content) >= 12 and content[4:8] == b"ftyp":
        return ".m4a"
    if b"ftyp" in content[:64]:
        return ".m4a"
    if content[:3] == b"ID3":
        return ".mp3"
    if len(content) >= 2 and content[0] == 0xFF and (content[1] & 0xF0) == 0xF0:
        layer = (content[1] >> 1) & 0x03
        return ".aac" if layer == 0 else ".mp3"
    if content[:4] == b"RIFF" and content[8:12] == b"WAVE":
        return ".wav"
    if content[:4] == b"OggS":
        return ".ogg"
    if content[:4] == b"fLaC":
        return ".flac"
    return None


def sniff_audio_upload(
    content: bytes,
    content_type: str | None,
    filename: str | None,
) -> tuple[str, str]:
    """Return (content_type, extension) for an accepted audio sample."""
    name = (filename or "").strip().lower()
    name_ext = ""
    if "." in name:
        name_ext = "." + name.rsplit(".", 1)[-1]
    # Prefer container magic. iOS often labels CAF as .m4a; ffmpeg then probes
    # the wrong demuxer and ElevenLabs reports a corrupted file.
    magic = _ext_from_magic(content)
    ext = magic or (name_ext if name_ext in ALLOWED_AUDIO_EXTENSIONS else "")
    if name_ext and name_ext not in ALLOWED_AUDIO_EXTENSIONS and not magic:
        raise ValueError("Use a WAV, MP3, M4A, or OGG audio file.")

    mime = (content_type or "").split(";")[0].strip().lower()
    if mime and mime not in ALLOWED_AUDIO_CONTENT_TYPES:
        if not ext:
            magic = _ext_from_magic(content)
            if magic:
                ext = magic
                mime = ""
            else:
                raise ValueError("Use a WAV, MP3, M4A, or OGG audio file.")

    if not ext:
        ext = _MIME_TO_EXT.get(mime) or _ext_from_magic(content) or ".wav"

    mime_from_ext = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".opus": "audio/ogg",
        ".flac": "audio/flac",
        ".aac": "audio/aac",
        ".aiff": "audio/aiff",
        ".aif": "audio/aiff",
        ".mp4": "audio/mp4",
        ".caf": "audio/x-caf",
        ".webm": "audio/webm",
    }
    if magic or not mime or mime == "application/octet-stream" or mime not in ALLOWED_AUDIO_CONTENT_TYPES:
        mime = mime_from_ext.get(ext, mime or "application/octet-stream")

    if not content:
        raise ValueError("Empty audio file")
    return mime, ext


def probe_audio_seconds(content: bytes, *, extension: str = ".mp3") -> float | None:
    """Best-effort duration via ffmpeg. None if probe is unavailable."""
    binary = ffmpeg_path()
    if not binary or not content:
        return None
    suffix = extension if extension.startswith(".") else f".{extension}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(content)
        tmp.flush()
        try:
            proc = subprocess.run(
                [binary, "-hide_banner", "-i", tmp.name],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.warning("audio duration probe failed: %s", exc)
            return None
    text = f"{proc.stdout}\n{proc.stderr}"
    match = _DURATION_RE.search(text)
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def probe_mean_volume_db(content: bytes, *, extension: str = ".mp3") -> float | None:
    """Return mean volume in dB, or None. Very quiet files are near -90 dB."""
    binary = ffmpeg_path()
    if not binary or not content:
        return None
    suffix = extension if extension.startswith(".") else f".{extension}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(content)
        tmp.flush()
        try:
            proc = subprocess.run(
                [
                    binary,
                    "-hide_banner",
                    "-i",
                    tmp.name,
                    "-af",
                    "volumedetect",
                    "-f",
                    "null",
                    "-",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.warning("audio volume probe failed: %s", exc)
            return None
    text = f"{proc.stdout}\n{proc.stderr}"
    match = _MEAN_VOLUME_RE.search(text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def validate_clone_sample(content: bytes, *, extension: str) -> float:
    """Raise ValueError if the sample is too short, too long, or near-silent.

    Returns measured duration in seconds when known, else MIN_CLONE_SAMPLE_SECONDS
    (caller already enforced a non-empty file).
    """
    seconds = probe_audio_seconds(content, extension=extension)
    if seconds is not None:
        if seconds < MIN_CLONE_SAMPLE_SECONDS:
            raise ValueError(
                f"Record at least {int(MIN_CLONE_SAMPLE_SECONDS)} seconds in a quiet room. "
                "Aim for 30 to 90 seconds of you talking."
            )
        if seconds > MAX_CLONE_SAMPLE_SECONDS:
            raise ValueError("Keep the sample under two minutes.")
    mean_db = probe_mean_volume_db(content, extension=extension)
    if mean_db is not None and mean_db < -45:
        raise ValueError(
            "That recording is too quiet or is mostly silence. "
            "Record again in a quiet room, closer to the mic."
        )
    return float(seconds) if seconds is not None else MIN_CLONE_SAMPLE_SECONDS


_PROVIDER_MIME = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/x-m4a",
    ".mp4": "audio/mp4",
    ".caf": "audio/x-caf",
    ".aac": "audio/aac",
    ".aiff": "audio/aiff",
    ".aif": "audio/aiff",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".flac": "audio/flac",
    ".webm": "audio/webm",
}

_READ_ERROR = "Could not read that recording. Record again, or upload a WAV or MP3 file."

# iOS often writes CAF/PCM/AAC under a .m4a name. Try the sniffed suffix first,
# then force demuxers ffmpeg can use when the container magic was missed.
_FFMPEG_INPUT_PREFIXES: tuple[tuple[str, ...], ...] = (
    (),
    ("-f", "caf"),
    ("-f", "aac"),
    ("-f", "ipod"),
    ("-f", "mp4"),
    ("-f", "wav"),
    ("-f", "aiff"),
)


def _run_clone_wav_ffmpeg(
    binary: str,
    src: Path,
    dest: Path,
    input_prefix: tuple[str, ...],
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            binary,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-probesize",
            "10M",
            "-analyzeduration",
            "5M",
            *input_prefix,
            "-i",
            str(src),
            "-ac",
            "1",
            "-ar",
            "32000",
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            str(dest),
        ],
        capture_output=True,
        timeout=20,
        check=False,
    )


def transcode_clone_sample_to_wav(content: bytes, *, extension: str) -> bytes | None:
    """Decode any accepted sample to 32 kHz mono 16-bit PCM WAV.

    iOS Voice Memos and expo-audio often write CAF or PCM labeled as m4a.
    Returns None when ffmpeg is not installed. Raises ValueError if ffmpeg
    cannot decode.
    """
    binary = ffmpeg_path()
    if not binary or not content:
        return None
    suffix = extension if extension.startswith(".") else f".{extension}"
    magic = _ext_from_magic(content)
    if magic:
        suffix = magic
    if suffix not in ALLOWED_AUDIO_EXTENSIONS:
        suffix = ".m4a"
    last_detail = ""
    wav = b""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / f"in{suffix}"
        dest = Path(tmpdir) / "reference.wav"
        src.write_bytes(content)
        try:
            for prefix in _FFMPEG_INPUT_PREFIXES:
                if dest.exists():
                    dest.unlink()
                proc = _run_clone_wav_ffmpeg(binary, src, dest, prefix)
                if proc.returncode == 0 and dest.is_file() and dest.stat().st_size >= 64:
                    wav = dest.read_bytes()
                    break
                last_detail = (proc.stderr or b"").decode("utf-8", "replace")[:200]
            else:
                log.warning("clone wav transcode rejected: %s", last_detail)
                raise ValueError(_READ_ERROR)
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.warning("clone wav transcode failed: %s", exc)
            raise ValueError(_READ_ERROR) from exc
    if len(wav) > MAX_CUSTOM_VOICE_UPLOAD_BYTES:
        raise ValueError("Voice sample must be 10 MB or smaller.")
    return wav


def prepare_clone_audio_for_provider(content: bytes, *, extension: str) -> tuple[bytes, str, str]:
    """Return (bytes, filename, mime) for ElevenLabs IVC."""
    wav = transcode_clone_sample_to_wav(content, extension=extension)
    if wav:
        return wav, "reference.wav", "audio/wav"
    suffix = extension if extension.startswith(".") else f".{extension}"
    if suffix not in ALLOWED_AUDIO_EXTENSIONS:
        suffix = ".m4a"
    mime = _PROVIDER_MIME.get(suffix, "application/octet-stream")
    return content, f"reference{suffix}", mime


__all__ = [
    "ALLOWED_AUDIO_CONTENT_TYPES",
    "ALLOWED_AUDIO_EXTENSIONS",
    "MAX_CLONE_SAMPLE_SECONDS",
    "MAX_CUSTOM_VOICE_UPLOAD_BYTES",
    "MIN_CLONE_SAMPLE_SECONDS",
    "probe_audio_seconds",
    "prepare_clone_audio_for_provider",
    "probe_mean_volume_db",
    "sniff_audio_upload",
    "transcode_clone_sample_to_wav",
    "validate_clone_sample",
]
