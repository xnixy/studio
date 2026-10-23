"""Fast vs 2.5 and resolution from speech length and chat. Not Options."""
from __future__ import annotations

import re

from app.play_models import CLIP_ADVANCED_MAX_SECONDS, CLIP_FAST_MAX_SECONDS

FAST_IDS = {
    "avatar": "seedance-avatar-fast",
    "video": "seedance-2-0-fast",
}
ADV_IDS = {
    "avatar": "seedance-avatar",
    "video": "seedance-2-5",
}

_ASK_25 = re.compile(
    r"\b(2\.5|seedance 2\.5|better quality|higher quality|longer|advanced)\b",
    re.I,
)
_ASK_FAST = re.compile(r"\b(fast(?:er)?|cheaper|quick(?:er)?)\b", re.I)
_RES = re.compile(r"\b(480p|720p|1080p|4k|4K|2160p)\b")
_SQUARE = re.compile(r"\b(square|1\s*[:x]\s*1|feed post)\b", re.I)


def _norm_res(raw: str | None) -> str | None:
    if not raw:
        return None
    r = raw.strip().lower().replace(" ", "")
    if r in {"480", "480p"}:
        return "480p"
    if r in {"720", "720p", "hd"}:
        return "720p"
    if r in {"1080", "1080p", "fhd"}:
        return "1080p"
    if r in {"4k", "2160", "2160p", "uhd"}:
        return "4k"
    return None


def speech_seconds_for_kind(*, kind: str, scene: str, line: str) -> float:
    from app.routers.play_video_helpers import raw_speech_seconds
    from app.voiceover import expand_spoken_domains

    if kind == "video":
        text = " ".join(part for part in (scene, line) if part)
    else:
        text = line or ""
    return raw_speech_seconds(expand_spoken_domains(text))


def settle_clip_lane(
    *,
    kind: str,
    scene: str,
    line: str,
    last_user: str = "",
    asked_model: str | None = None,
    asked_resolution: str | None = None,
) -> tuple[str, str, int, bool, str | None]:
    """Returns model_id, resolution, duration_seconds, extend_rest, platform."""
    if kind == "lipsync":
        kind = "avatar"
    job = kind if kind in FAST_IDS else "video"
    speech = speech_seconds_for_kind(kind=job, scene=scene, line=line)
    blob = last_user or ""
    want_25 = bool(_ASK_25.search(blob))
    want_fast = bool(_ASK_FAST.search(blob)) and not want_25
    res_hit = _RES.search(blob)
    resolution = _norm_res(asked_resolution) or _norm_res(res_hit.group(1) if res_hit else None) or "720p"
    platform = "feed" if _SQUARE.search(blob) else None

    hi_res = resolution in {"1080p", "4k"}
    over_fast = speech > CLIP_FAST_MAX_SECONDS + 0.4
    over_adv = speech > CLIP_ADVANCED_MAX_SECONDS + 0.4

    use_25 = False
    extend_rest = False
    if over_adv:
        use_25 = True
        extend_rest = True
        duration = CLIP_ADVANCED_MAX_SECONDS
        if hi_res:
            resolution = "720p"
    elif over_fast:
        use_25 = True
        duration = min(CLIP_ADVANCED_MAX_SECONDS, max(16, int(round(speech))))
        if hi_res:
            resolution = "720p"
    elif want_25 and not want_fast:
        use_25 = True
        duration = max(4, min(CLIP_ADVANCED_MAX_SECONDS, int(round(speech)) if speech else 8))
        if hi_res:
            resolution = "720p"
    else:
        duration = max(4, min(CLIP_FAST_MAX_SECONDS, int(round(speech)) if speech else 8))

    if asked_model:
        mid = asked_model.strip().lower()
        if "2-5" in mid or mid in ADV_IDS.values():
            use_25 = True
        elif "fast" in mid:
            use_25 = False

    model_id = ADV_IDS[job] if use_25 else FAST_IDS[job]
    if use_25 and resolution in {"1080p", "4k"}:
        resolution = "720p"
    return model_id, resolution, duration, extend_rest, platform
