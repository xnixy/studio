"""Voice clone upload sniffing, including iOS Voice Memos .m4a."""
from __future__ import annotations

import pytest

from app.audio_upload import sniff_audio_upload


def _ftyp_m4a(size: int = 32) -> bytes:
    # MPEG-4 box: size + 'ftyp' + 'M4A ' brand. Voice Memos uses this container.
    brand = b"M4A "
    payload = b"ftyp" + brand + b"\x00\x00\x00\x00" + brand
    header = (8 + len(payload)).to_bytes(4, "big")
    body = header + payload
    return body + b"\x00" * max(0, size - len(body))


def test_sniff_voice_memos_m4a_filename() -> None:
    mime, ext = sniff_audio_upload(_ftyp_m4a(), "audio/mp4", "New Recording.m4a")
    assert ext == ".m4a"
    assert mime == "audio/mp4"


def test_sniff_voice_memos_no_extension() -> None:
    mime, ext = sniff_audio_upload(_ftyp_m4a(), "audio/mp4", "C0A1B2C3")
    assert ext == ".m4a"
    assert mime == "audio/mp4"


def test_sniff_voice_memos_latm_mime() -> None:
    mime, ext = sniff_audio_upload(_ftyp_m4a(), "audio/mp4a-latm", "")
    assert ext == ".m4a"
    assert mime == "audio/mp4"


def test_sniff_m4a_from_magic_when_mime_unknown() -> None:
    mime, ext = sniff_audio_upload(_ftyp_m4a(), "application/x-itunes-itls", "")
    assert ext == ".m4a"
    assert mime == "audio/mp4"


def test_sniff_caf_magic_beats_m4a_filename() -> None:
    mime, ext = sniff_audio_upload(b"caff" + b"\x00" * 20, "audio/mp4", "voice-sample.m4a")
    assert ext == ".caf"
    assert mime == "audio/x-caf"


def test_sniff_adts_aac() -> None:
    adts = bytes([0xFF, 0xF1, 0x50, 0x80, 0x00, 0x1F, 0xFC]) + b"\x00" * 16
    mime, ext = sniff_audio_upload(adts, "application/octet-stream", "voice-sample.m4a")
    assert ext == ".aac"
    assert mime == "audio/aac"


def test_sniff_aiff_magic() -> None:
    payload = b"FORM" + (24).to_bytes(4, "big") + b"AIFF" + b"\x00" * 16
    mime, ext = sniff_audio_upload(payload, "audio/mp4", "voice-sample.m4a")
    assert ext == ".aiff"


def test_prepare_clone_audio_transcodes_wav_when_ffmpeg_available() -> None:
    import io
    import wave

    from app.audio_upload import prepare_clone_audio_for_provider, transcode_clone_sample_to_wav
    from app.video_renderer import ffmpeg_path

    if not ffmpeg_path():
        pytest.skip("ffmpeg is not available")

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\x00\x00" * 44100)
    raw = buf.getvalue()
    wav = transcode_clone_sample_to_wav(raw, extension=".wav")
    assert wav is not None
    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"
    payload, name, mime = prepare_clone_audio_for_provider(raw, extension=".wav")
    assert name == "reference.wav"
    assert mime == "audio/wav"
    assert payload[:4] == b"RIFF"


def test_transcode_wav_bytes_mislabeled_as_m4a() -> None:
    import io
    import wave

    from app.audio_upload import transcode_clone_sample_to_wav
    from app.video_renderer import ffmpeg_path

    if not ffmpeg_path():
        pytest.skip("ffmpeg is not available")

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\x00\x00" * 44100)
    wav = transcode_clone_sample_to_wav(buf.getvalue(), extension=".m4a")
    assert wav is not None
    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"


def test_transcode_caf_mislabeled_as_m4a() -> None:
    import subprocess
    import tempfile
    from pathlib import Path

    from app.audio_upload import transcode_clone_sample_to_wav
    from app.video_renderer import ffmpeg_path

    binary = ffmpeg_path()
    if not binary:
        pytest.skip("ffmpeg is not available")

    with tempfile.TemporaryDirectory() as tmpdir:
        caf = Path(tmpdir) / "in.caf"
        proc = subprocess.run(
            [
                binary,
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=1",
                "-c:a",
                "pcm_s16le",
                "-f",
                "caf",
                str(caf),
            ],
            capture_output=True,
            timeout=20,
            check=False,
        )
        if proc.returncode != 0 or not caf.is_file():
            pytest.skip("ffmpeg could not write a CAF fixture")
        wav = transcode_clone_sample_to_wav(caf.read_bytes(), extension=".m4a")
    assert wav is not None
    assert wav[:4] == b"RIFF"


def test_sniff_rejects_unknown_without_magic() -> None:
    with pytest.raises(ValueError, match="M4A"):
        sniff_audio_upload(b"not-audio", "application/pdf", "notes.pdf")
