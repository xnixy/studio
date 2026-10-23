"""Word-level ASR alignment via faster-whisper (+ forced match to known script)."""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_model_lock = threading.Lock()
_model_cache: dict[str, object] = {}


@dataclass(frozen=True)
class TimedWord:
    text: str
    start: float
    end: float
    confidence: float | None = None
    source: str = "asr"  # asr | forced | interpolated


def normalize_token(word: str) -> str:
    return re.sub(r"[^a-z0-9']", "", (word or "").lower())


def tokenize_script(*parts: str) -> list[str]:
    text = " ".join(p for p in parts if p)
    return _WORD_RE.findall(text)


def whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401

        return True
    except ImportError:
        return False


def _load_model(model_size: str, device: str, compute_type: str):
    """Load Whisper from local HF cache only — never download mid-export (that can take minutes)."""
    key = f"{model_size}:{device}:{compute_type}"
    with _model_lock:
        if key in _model_cache:
            return _model_cache[key]
        from faster_whisper import WhisperModel
        import os

        # Quieter / safer defaults on Windows; avoid symlink warnings in logs.
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

        logger.info("Loading faster-whisper model %s (%s / %s) from local cache", model_size, device, compute_type)
        try:
            # local_files_only avoids a multi-minute Hub download during "Process export".
            model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                local_files_only=True,
            )
        except Exception as exc:
            logger.warning(
                "Whisper model %s not available in local cache (%s). "
                "Skipping ASR captions for this render; silence/estimate timing will be used. "
                "Pre-download once with HF_TOKEN set if you want word-level captions.",
                model_size,
                exc,
            )
            raise RuntimeError("whisper_model_not_cached") from exc
        _model_cache[key] = model
        return model


def transcribe_words(
    audio_path: Path,
    *,
    model_size: str = "tiny",
    device: str = "cpu",
    compute_type: str = "int8",
    language: str = "en",
    initial_prompt: str | None = None,
) -> tuple[list[TimedWord], float | None, str]:
    """Run Whisper with word timestamps. Returns (words, duration_hint, engine_label)."""
    if not whisper_available():
        raise RuntimeError("faster-whisper is not installed")
    if not audio_path.exists():
        raise FileNotFoundError(str(audio_path))

    model = _load_model(model_size, device, compute_type)
    segments, info = model.transcribe(
        str(audio_path),
        language=language or None,
        word_timestamps=True,
        vad_filter=True,
        initial_prompt=(initial_prompt or "")[:400] or None,
        condition_on_previous_text=False,
    )
    words: list[TimedWord] = []
    last_end = 0.0
    for segment in segments:
        for w in segment.words or []:
            text = (w.word or "").strip()
            if not text:
                continue
            start = float(w.start or 0.0)
            end = float(w.end or start)
            if end < start:
                end = start
            conf = float(w.probability) if getattr(w, "probability", None) is not None else None
            words.append(TimedWord(text=text, start=start, end=end, confidence=conf, source="asr"))
            last_end = max(last_end, end)
    duration = float(getattr(info, "duration", None) or last_end or 0.0) or None
    return words, duration, f"faster-whisper:{model_size}"


def force_align_script_to_asr(script_words: list[str], asr_words: list[TimedWord]) -> list[TimedWord]:
    """Map known script tokens onto ASR timings (greedy + interpolation)."""
    if not script_words:
        return []
    if not asr_words:
        # No ASR: equal-time placeholders (caller should replace duration)
        n = len(script_words)
        return [
            TimedWord(text=w, start=i / max(n, 1), end=(i + 1) / max(n, 1), source="interpolated")
            for i, w in enumerate(script_words)
        ]

    asr_norm = [normalize_token(w.text) for w in asr_words]
    script_norm = [normalize_token(w) for w in script_words]
    n, m = len(script_norm), len(asr_norm)

    # DP alignment (Needleman–Wunsch style, match / skip ASR / skip script)
    MATCH, SKIP_ASR, SKIP_SCRIPT = 2, -1, -1
    score = [[0] * (m + 1) for _ in range(n + 1)]
    back: list[list[str]] = [[""] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        score[i][0] = i * SKIP_SCRIPT
        back[i][0] = "S"
    for j in range(1, m + 1):
        score[0][j] = j * SKIP_ASR
        back[0][j] = "A"

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            same = script_norm[i - 1] and script_norm[i - 1] == asr_norm[j - 1]
            # Partial credit for prefix match (TTS/ASR spelling drift)
            partial = (
                script_norm[i - 1]
                and asr_norm[j - 1]
                and (script_norm[i - 1].startswith(asr_norm[j - 1][:3]) or asr_norm[j - 1].startswith(script_norm[i - 1][:3]))
            )
            diag = score[i - 1][j - 1] + (MATCH if same else (1 if partial else -1))
            up = score[i - 1][j] + SKIP_SCRIPT
            left = score[i][j - 1] + SKIP_ASR
            best = max(diag, up, left)
            score[i][j] = best
            if best == diag:
                back[i][j] = "M"
            elif best == up:
                back[i][j] = "S"
            else:
                back[i][j] = "A"

    # Traceback
    pairs: list[tuple[int | None, int | None]] = []
    i, j = n, m
    while i > 0 or j > 0:
        move = back[i][j] if i >= 0 and j >= 0 else "S"
        if i > 0 and j > 0 and move == "M":
            pairs.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif j > 0 and (i == 0 or move == "A"):
            pairs.append((None, j - 1))
            j -= 1
        else:
            pairs.append((i - 1, None))
            i -= 1
    pairs.reverse()

    timed: list[TimedWord | None] = [None] * n
    for si, aj in pairs:
        if si is None or aj is None:
            continue
        aw = asr_words[aj]
        timed[si] = TimedWord(
            text=script_words[si],
            start=aw.start,
            end=max(aw.end, aw.start + 0.04),
            confidence=aw.confidence,
            source="forced",
        )

    # Interpolate gaps
    for idx in range(n):
        if timed[idx] is not None:
            continue
        # find prev/next known
        prev = next((k for k in range(idx - 1, -1, -1) if timed[k] is not None), None)
        nxt = next((k for k in range(idx + 1, n) if timed[k] is not None), None)
        if prev is not None and nxt is not None:
            span = max(0.05, timed[nxt].start - timed[prev].end)  # type: ignore[union-attr]
            gap = nxt - prev
            step = span / gap
            t0 = timed[prev].end + step * (idx - prev - 1)  # type: ignore[union-attr]
            t1 = t0 + step
            timed[idx] = TimedWord(text=script_words[idx], start=t0, end=t1, source="interpolated")
        elif prev is not None:
            t0 = timed[prev].end  # type: ignore[union-attr]
            timed[idx] = TimedWord(text=script_words[idx], start=t0, end=t0 + 0.18, source="interpolated")
        elif nxt is not None:
            t1 = timed[nxt].start  # type: ignore[union-attr]
            timed[idx] = TimedWord(text=script_words[idx], start=max(0.0, t1 - 0.18), end=t1, source="interpolated")
        else:
            timed[idx] = TimedWord(text=script_words[idx], start=idx * 0.25, end=(idx + 1) * 0.25, source="interpolated")

    # Ensure monotonic non-overlapping-ish
    out: list[TimedWord] = []
    cursor = 0.0
    for w in timed:
        assert w is not None
        start = max(cursor, w.start)
        end = max(start + 0.04, w.end)
        out.append(TimedWord(text=w.text, start=round(start, 3), end=round(end, 3), confidence=w.confidence, source=w.source))
        cursor = end
    return out


def group_words_into_cues(
    words: list[TimedWord],
    *,
    max_words: int = 8,
    max_chars: int = 42,
    max_duration: float = 3.2,
) -> list[tuple[str, float, float]]:
    """Group timed words into readable caption lines."""
    if not words:
        return []
    cues: list[tuple[str, float, float]] = []
    buf: list[TimedWord] = []
    for w in words:
        candidate = buf + [w]
        text = " ".join(x.text for x in candidate)
        duration = (w.end - buf[0].start) if buf else (w.end - w.start)
        if buf and (len(candidate) > max_words or len(text) > max_chars or duration > max_duration):
            cues.append((" ".join(x.text for x in buf), buf[0].start, buf[-1].end))
            buf = [w]
        else:
            buf = candidate
    if buf:
        cues.append((" ".join(x.text for x in buf), buf[0].start, buf[-1].end))
    return cues


def word_level_align(
    audio_path: Path,
    *,
    hook: str,
    script: str,
    cta: str,
    caption: str | None = None,
    model_size: str = "tiny",
    device: str = "cpu",
    compute_type: str = "int8",
    language: str = "en",
) -> dict[str, object]:
    """
    Full word-level pipeline:
    1) Whisper ASR with word timestamps
    2) Force-align known script onto ASR times
    3) Group into caption cues
    """
    script_words = tokenize_script(hook, script, cta, caption or "")
    prompt = " ".join(script_words[:80])
    asr_words, duration, engine = transcribe_words(
        audio_path,
        model_size=model_size,
        device=device,
        compute_type=compute_type,
        language=language,
        initial_prompt=prompt,
    )
    aligned = force_align_script_to_asr(script_words, asr_words)
    if duration and aligned:
        # stretch last word to duration if close
        last = aligned[-1]
        if last.end < duration and duration - last.end < 1.5:
            aligned[-1] = TimedWord(last.text, last.start, round(duration, 3), last.confidence, last.source)
    cues = group_words_into_cues(aligned)
    return {
        "engine": engine,
        "duration_seconds": round(duration or (aligned[-1].end if aligned else 0.0), 3),
        "words": [
            {
                "text": w.text,
                "start": w.start,
                "end": w.end,
                "confidence": w.confidence,
                "source": w.source,
            }
            for w in aligned
        ],
        "asr_words": [
            {"text": w.text, "start": w.start, "end": w.end, "confidence": w.confidence}
            for w in asr_words
        ],
        "cue_tuples": cues,
    }
