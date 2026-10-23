"""Authoritative Play token quotes (model × length × quality × extras × batch)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Literal

from app.play_models import (
    PlayModality,
    get_play_model,
)

PlayMeter = Literal[
    "play_video",
    "play_avatar",
    "play_still",
    "play_lipsync",
    "play_face",
    # legacy aliases still accepted by usage layer
    "video_generation",
    "image_generation",
    "avatar_lipsync",
]


@dataclass(frozen=True)
class PlayTokenQuote:
    meter: str
    per_item: int
    count: int
    total: int
    base: int
    breakdown: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "meter": self.meter,
            "per_item": self.per_item,
            "count": self.count,
            "total": self.total,
            "base": self.base,
            "breakdown": self.breakdown,
        }


def meter_for_mode(mode: str, *, face_generate: bool = False) -> str:
    if face_generate:
        return "play_face"
    m = (mode or "").strip().lower()
    if m == "avatar" or m == "lipsync":
        return "play_avatar"
    if m == "video":
        return "play_video"
    if m == "image":
        return "play_still"
    return "play_video"


def _duration_factor(seconds: int | None, *, provider: str) -> float:
    if seconds is None or seconds <= 0:
        return 1.0
    # Reference length 5s; longer clips cost more (clamp so short clips still pay base).
    raw = float(seconds) / 5.0
    return max(0.8, min(3.0, raw))


def _resolution_factor(resolution: str | None, *, provider: str) -> float:
    r = (resolution or "720p").strip().lower()
    table = {
        "480p": 0.85,
        "480": 0.85,
        "720p": 1.0,
        "720": 1.0,
        "1080p": 1.5,
        "1080": 1.5,
        "fhd": 1.5,
        "4k": 2.5,
        "2160p": 2.5,
    }
    return table.get(r, 1.0)


def _refs_extra(
    *,
    ref_images: int,
    ref_videos: int,
    ref_audios: int,
    provider: str,
) -> int:
    # Face is charged via identity mode, not ref extras.
    img = max(0, int(ref_images))
    vid = max(0, int(ref_videos))
    aud = max(0, int(ref_audios))
    extra = 0
    if provider == "seedance":
        extra += min(img, 9)  # +1 per image ref
        extra += min(vid, 3) * 2
        extra += min(aud, 3) * 2
    elif provider in {"xai", "gemini", "kling"}:
        extra += min(img, 7)  # image refs only for most
    return extra


def compute_play_quote(
    *,
    mode: str,
    model_id: str | None,
    duration_seconds: int | None = None,
    resolution: str | None = None,
    count: int = 1,
    generate_audio: bool | None = True,
    return_last_frame: bool | None = False,
    ref_image_count: int = 0,
    ref_video_count: int = 0,
    ref_audio_count: int = 0,
    continue_from: bool = False,
    face_generate: bool = False,
    cloned_voice: bool = False,
    has_scene: bool = False,
) -> PlayTokenQuote:
    """Compute tokens for one Play generate (authoritative for reserve + UI)."""
    modality: PlayModality
    m = (mode or "video").strip().lower()
    if m == "lipsync":
        m = "avatar"
    if m in {"image", "video", "avatar"}:
        modality = m  # type: ignore[assignment]
    else:
        modality = "video"

    try:
        play_model = get_play_model(model_id, modality if not face_generate else "image")
    except KeyError:
        play_model = get_play_model(None, "video")

    base = max(1, int(play_model.token_cost or 1))
    provider = (play_model.provider or "xai").strip().lower()
    batch = max(1, min(int(count or 1), 10))

    if face_generate or modality == "image":
        per_item = base
        breakdown = {"base": base, "note": "still"}
        meter = meter_for_mode("image", face_generate=face_generate)
        return PlayTokenQuote(
            meter=meter,
            per_item=per_item,
            count=1,
            total=per_item,
            base=base,
            breakdown=breakdown,
        )

    f_dur = _duration_factor(duration_seconds, provider=provider)
    f_res = _resolution_factor(resolution, provider=provider)
    f_audio = 1.0 if (generate_audio is None or generate_audio) else 0.9
    f_last = 1.1 if return_last_frame else 1.0
    f_extend = 1.0  # full generation
    refs_extra = _refs_extra(
        ref_images=ref_image_count,
        ref_videos=ref_video_count,
        ref_audios=ref_audio_count,
        provider=provider,
    )

    scaled = base * f_dur * f_res * f_audio * f_last * f_extend
    per_item = max(1, int(math.ceil(scaled)) + refs_extra)
    total = per_item * batch

    breakdown = {
        "base": base,
        "duration_seconds": duration_seconds,
        "duration_factor": round(f_dur, 3),
        "resolution": resolution or "720p",
        "resolution_factor": round(f_res, 3),
        "audio_factor": f_audio,
        "last_frame_factor": f_last,
        "refs_extra": refs_extra,
        "continue_from": continue_from,
        "provider": provider,
        "model_id": play_model.id,
    }

    quote = PlayTokenQuote(
        meter=meter_for_mode(modality),
        per_item=per_item,
        count=batch,
        total=total,
        base=base,
        breakdown=breakdown,
    )
    if cloned_voice and modality in {"avatar", "video", "lipsync"}:
        voiceover_seconds = max(5, int(duration_seconds or 8))
        merged = dict(quote.breakdown)
        merged.update(
            {
                "cloned_voice": True,
                "voiceover_seconds": voiceover_seconds,
            }
        )
        return PlayTokenQuote(
            meter=quote.meter,
            per_item=quote.per_item,
            count=quote.count,
            total=quote.total,
            base=quote.base,
            breakdown=merged,
        )
    return quote
