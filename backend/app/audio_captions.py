"""Broadcast-grade caption timing from audio duration + silence peaks (FFmpeg)."""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.video_renderer import ffmpeg_path, media_duration_seconds

logger = logging.getLogger(__name__)

SILENCE_RE = re.compile(
    r"silence_(?:start|end):\s*([0-9]+(?:\.[0-9]+)?)",
    re.IGNORECASE,
)
SILENCE_START_RE = re.compile(r"silence_start:\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
SILENCE_END_RE = re.compile(r"silence_end:\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)


@dataclass(frozen=True)
class CaptionCue:
    index: int
    text: str
    start: float
    end: float


def caption_chunks_from_text(*, hook: str, script: str, cta: str, caption: str | None = None) -> list[str]:
    parts: list[str] = []
    for piece in (hook, *script.replace("!", ".").replace("?", ".").split("."), cta, caption or ""):
        line = " ".join(str(piece or "").split()).strip()
        if not line:
            continue
        if len(line) > 90:
            # Split long lines on commas/spaces for readable cards
            while len(line) > 90:
                cut = line.rfind(" ", 0, 85)
                if cut < 40:
                    cut = 85
                parts.append(line[:cut].strip())
                line = line[cut:].strip()
            if line:
                parts.append(line)
        else:
            parts.append(line)
    # Dedupe consecutive duplicates
    cleaned: list[str] = []
    for p in parts:
        if not cleaned or cleaned[-1].lower() != p.lower():
            cleaned.append(p)
    return cleaned or ["…"]


def detect_silence_regions(audio_path: Path, *, noise_db: float = -32.0, min_silence: float = 0.22) -> list[tuple[float, float]]:
    """Return list of (silence_start, silence_end) using FFmpeg silencedetect."""
    binary = ffmpeg_path()
    if not binary or not audio_path.exists():
        return []
    command = [
        binary,
        "-hide_banner",
        "-i",
        str(audio_path),
        "-af",
        f"silencedetect=noise={noise_db}dB:d={min_silence}",
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    # silencedetect writes to stderr
    log = (result.stderr or "") + "\n" + (result.stdout or "")
    starts = [float(m.group(1)) for m in SILENCE_START_RE.finditer(log)]
    ends = [float(m.group(1)) for m in SILENCE_END_RE.finditer(log)]
    regions: list[tuple[float, float]] = []
    # Pair starts/ends in order
    i = j = 0
    while i < len(starts):
        s = starts[i]
        while j < len(ends) and ends[j] < s:
            j += 1
        if j < len(ends):
            regions.append((s, ends[j]))
            j += 1
        i += 1
    return regions


def speech_segments_from_silence(duration: float, silences: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Invert silence regions into speech segments covering [0, duration]."""
    if duration <= 0:
        return []
    if not silences:
        return [(0.0, duration)]
    segments: list[tuple[float, float]] = []
    cursor = 0.0
    for s_start, s_end in sorted(silences, key=lambda x: x[0]):
        s_start = max(0.0, min(duration, s_start))
        s_end = max(0.0, min(duration, s_end))
        if s_start > cursor + 0.05:
            segments.append((cursor, s_start))
        cursor = max(cursor, s_end)
    if cursor < duration - 0.05:
        segments.append((cursor, duration))
    # Drop tiny segments
    return [(a, b) for a, b in segments if b - a >= 0.35] or [(0.0, duration)]


def align_chunks_to_segments(chunks: list[str], segments: list[tuple[float, float]], duration: float) -> list[CaptionCue]:
    """Map caption text chunks onto speech segments (split long segments by word weight)."""
    if not chunks:
        return []
    if not segments:
        segments = [(0.0, max(duration, 1.0))]

    # Expand segments into time slots equal to chunk count by subdividing long speech
    weights = [max(1, len(c.split())) for c in chunks]
    total_w = sum(weights)
    # Prefer one chunk per sub-slice of total speech timeline
    speech_len = sum(b - a for a, b in segments) or duration or 1.0
    cues: list[CaptionCue] = []
    # Flatten speech into a continuous virtual timeline then map back
    flat_points: list[tuple[float, float]] = []  # virtual_t, real_t pairs along speech
    v = 0.0
    for a, b in segments:
        flat_points.append((v, a))
        v += b - a
        flat_points.append((v, b))

    def real_time(virt: float) -> float:
        virt = max(0.0, min(speech_len, virt))
        for i in range(len(flat_points) - 1):
            v0, r0 = flat_points[i]
            v1, r1 = flat_points[i + 1]
            if v0 <= virt <= v1 and v1 > v0:
                t = (virt - v0) / (v1 - v0)
                return r0 + t * (r1 - r0)
        return duration

    cursor_v = 0.0
    for index, (text, w) in enumerate(zip(chunks, weights, strict=False)):
        share = w / total_w
        slot = max(0.45, speech_len * share)
        start_v = cursor_v
        end_v = speech_len if index == len(chunks) - 1 else min(speech_len, cursor_v + slot)
        start = real_time(start_v)
        end = real_time(end_v)
        if end <= start:
            end = min(duration, start + 0.8)
        cues.append(CaptionCue(index=index + 1, text=text, start=round(start, 3), end=round(end, 3)))
        cursor_v = end_v
    # Ensure last cue ends at audio duration when possible
    if cues and duration > 0:
        last = cues[-1]
        cues[-1] = CaptionCue(last.index, last.text, last.start, round(max(last.end, duration), 3))
    return cues


def format_srt(cues: list[CaptionCue]) -> str:
    def ts(seconds: float) -> str:
        ms = max(0, int(round(seconds * 1000)))
        h, rem = divmod(ms, 3_600_000)
        m, rem = divmod(rem, 60_000)
        s, milli = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"

    blocks = []
    for cue in cues:
        blocks.append(f"{cue.index}\n{ts(cue.start)} --> {ts(cue.end)}\n{cue.text}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def format_vtt(cues: list[CaptionCue]) -> str:
    def ts(seconds: float) -> str:
        ms = max(0, int(round(seconds * 1000)))
        h, rem = divmod(ms, 3_600_000)
        m, rem = divmod(rem, 60_000)
        s, milli = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{milli:03d}"

    blocks = [f"{ts(c.start)} --> {ts(c.end)}\n{c.text}" for c in cues]
    return "WEBVTT\n\n" + "\n\n".join(blocks) + ("\n" if blocks else "")


def build_aligned_captions(
    *,
    audio_path: Path | None,
    hook: str,
    script: str,
    cta: str,
    caption: str | None = None,
    fallback_duration: float | None = None,
    prefer_asr: bool = True,
    asr_model: str = "tiny",
    asr_device: str = "cpu",
    asr_compute_type: str = "int8",
    asr_language: str = "en",
) -> dict[str, object]:
    """
    Caption timing pipeline (best → fallback):
    1) Word-level ASR (faster-whisper) + forced align to known script
    2) FFmpeg silence / speech segments
    3) Word-count estimate
    """
    chunks = caption_chunks_from_text(hook=hook, script=script, cta=cta, caption=caption)
    words_payload: list[dict[str, object]] = []
    asr_words_payload: list[dict[str, object]] = []
    asr_engine: str | None = None
    silences: list[tuple[float, float]] = []
    segments: list[tuple[float, float]] = []
    method = "word_estimate"
    duration: float | None = None
    cues: list[CaptionCue] = []

    # --- 1) Word-level ASR ---
    if prefer_asr and audio_path and audio_path.exists():
        try:
            from app.asr_alignment import word_level_align, whisper_available

            if whisper_available():
                asr = word_level_align(
                    audio_path,
                    hook=hook,
                    script=script,
                    cta=cta,
                    caption=caption,
                    model_size=asr_model,
                    device=asr_device,
                    compute_type=asr_compute_type,
                    language=asr_language,
                )
                asr_engine = str(asr.get("engine") or "faster-whisper")
                duration = float(asr.get("duration_seconds") or 0) or media_duration_seconds(audio_path)
                words_payload = list(asr.get("words") or [])  # type: ignore[arg-type]
                asr_words_payload = list(asr.get("asr_words") or [])  # type: ignore[arg-type]
                cue_tuples = list(asr.get("cue_tuples") or [])
                if cue_tuples:
                    cues = [
                        CaptionCue(index=i + 1, text=str(t[0]), start=float(t[1]), end=float(t[2]))
                        for i, t in enumerate(cue_tuples)
                    ]
                    method = "word_asr_forced"
        except Exception as exc:
            # Fall through to silence / estimate — never fail the export path
            logger.warning("caption ASR alignment failed; using estimate fallback: %s", exc)
            cues = []
            method = "word_estimate"

    # --- 2) Silence / duration fallback ---
    if not cues:
        if audio_path and audio_path.exists():
            duration = duration or media_duration_seconds(audio_path)
            silences = detect_silence_regions(audio_path)
            if duration and duration > 0:
                method = "silence_aligned" if silences else "audio_duration_weighted"
        if not duration or duration <= 0:
            word_count = sum(len(c.split()) for c in chunks)
            duration = float(fallback_duration or max(6.0, word_count / 2.55))
            method = "word_estimate"
        segments = speech_segments_from_silence(duration, silences)
        cues = align_chunks_to_segments(chunks, segments, duration)
    else:
        if not duration or duration <= 0:
            duration = float(cues[-1].end if cues else fallback_duration or 6.0)

    return {
        "method": method,
        "asr_engine": asr_engine,
        "duration_seconds": round(float(duration or 0.0), 3),
        "silence_regions": [{"start": a, "end": b} for a, b in silences],
        "speech_segments": [{"start": a, "end": b} for a, b in segments],
        "words": words_payload,
        "asr_words": asr_words_payload,
        "cues": [{"index": c.index, "text": c.text, "start": c.start, "end": c.end} for c in cues],
        "srt": format_srt(cues),
        "vtt": format_vtt(cues),
        "word_srt": format_word_srt(words_payload) if words_payload else None,
    }


def format_word_srt(words: list[dict[str, object]]) -> str:
    """One cue per word for debugging / karaoke-style burn-in."""
    cues: list[CaptionCue] = []
    for i, w in enumerate(words):
        text = str(w.get("text") or "").strip()
        if not text:
            continue
        start = float(w.get("start") or 0.0)
        end = float(w.get("end") or start + 0.08)
        cues.append(CaptionCue(index=len(cues) + 1, text=text, start=start, end=end))
    return format_srt(cues)
