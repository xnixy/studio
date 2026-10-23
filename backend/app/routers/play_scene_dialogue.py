"""Spoken lines for A scene exact-voice (TTS then Seedance).

Quotes, ``says:``, and natural ``and says LINE`` all drive the Voice chip.
Unquoted "talk about the drop" with no line stays native model audio.
Signage quotes are not spoken.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.voiceover import expand_spoken_domains

Speaker = Literal["face", "other"]

_QUOTE_RE = re.compile(r'["“]([^"“”]{2,})["”]')
_WRITTEN_LEAD_RE = re.compile(
    r"\b(sign|signage|poster|banner|billboard|label|sticker|screen|display|"
    r"caption|subtitle|logo|menu|placard|note|card|headline|title)s?\b"
    r".{0,48}(?:reads?|reading|says?)\s*$",
    re.IGNORECASE | re.DOTALL,
)
_OTHER_ROLE_RE = re.compile(
    r"\b(friend|reporter|interviewer|stranger|someone)\b",
    re.IGNORECASE,
)
_ASKS_RE = re.compile(r"\basks?\b", re.IGNORECASE)
_SPOKEN_TAIL_RE = re.compile(
    r"(?i)^(i|i'm|i’m|im|we|you|do|did|don't|dont|have you|can you|did you)\b"
)
_FRIEND_ATTR_RE = re.compile(
    r"(?:the |her |his )?friend (?:replies|says|asks)\s*",
    re.I,
)
_FRIEND_LOOKS_RE = re.compile(
    r"\b(?:the |her |his )?(?:friend|reporter|interviewer)\b"
    r"[^.!?\n]{0,48}\b(?:a )?(?:man|woman|guy|girl|male|female|boy|lady)\b",
    re.I,
)


@dataclass(frozen=True, slots=True)
class SceneLine:
    speaker: Speaker
    text: str


def _face_pronouns(face_is_male: bool) -> re.Pattern[str]:
    if face_is_male:
        return re.compile(r"\b(he|him|his|i|we)\b", re.IGNORECASE)
    return re.compile(r"\b(she|her|hers|i|we)\b", re.IGNORECASE)


def _other_pronouns(face_is_male: bool) -> re.Pattern[str]:
    if face_is_male:
        return re.compile(r"\b(she|her|hers)\b", re.IGNORECASE)
    return re.compile(r"\b(he|him|his)\b", re.IGNORECASE)


def _speaker_from_lead(lead: str, *, face_is_male: bool) -> Speaker:
    text = (lead or "").strip()
    if not text:
        return "face"
    parts = re.split(r"(?<=[.!?])\s+", text)
    text = parts[-1].strip() if parts else text
    if _WRITTEN_LEAD_RE.search(text):
        return "face"
    face_hit = bool(_face_pronouns(face_is_male).search(text))
    other_hit = bool(_other_pronouns(face_is_male).search(text))
    friend_hit = bool(_OTHER_ROLE_RE.search(text))
    asks = bool(_ASKS_RE.search(text))
    if other_hit and not face_hit:
        return "other"
    if friend_hit and not face_hit:
        return "other"
    if asks and not face_hit:
        return "other"
    return "face"


def other_speaker_gender(face_gender: str | None) -> str:
    """Friend / reporter look and stock voice. Opposite of the Face picker."""
    return "female" if (face_gender or "").strip().lower() == "male" else "male"


def _looks_like_spoken_tail(text: str) -> bool:
    raw = (text or "").strip().lstrip(" .,;:")
    quoted = _QUOTE_RE.match(raw)
    if quoted:
        raw = quoted.group(1).strip()
    if len(raw.split()) < 4:
        return False
    return "?" in raw or bool(_SPOKEN_TAIL_RE.search(raw))


def _unwrap_quoted(text: str) -> str:
    raw = (text or "").strip().strip(" .,;:")
    quoted = _QUOTE_RE.match(raw)
    if quoted:
        return quoted.group(1).strip()
    return raw.strip(' "“”')


def normalize_scene_dialogue_order(text: str) -> str:
    """Face speaks first when their line was written after 'the friend replies'.

    People paste the reply, then the question. TTS then Sync played that order, so
    the clip answered first and asked second, and the clone landed on the wrong beat.
    """
    raw = (text or "").strip()
    if not raw:
        return raw
    attr = _FRIEND_ATTR_RE.search(raw)
    if not attr:
        return raw
    rest = raw[attr.end() :]
    stripped = rest.lstrip()
    quote = _QUOTE_RE.match(stripped)
    if not quote:
        return raw
    quote_end = attr.end() + (len(rest) - len(stripped)) + quote.end()
    after = raw[quote_end:].strip().lstrip(" .,;:")
    if not _looks_like_spoken_tail(after):
        return raw
    spoken = _unwrap_quoted(after)
    if not spoken:
        return raw
    before = raw[: attr.start()].rstrip(" .,;:")
    attr_text = attr.group(0).strip()
    return f'{before}. "{spoken}" {attr_text} {quote.group(0)}'


def ensure_other_speaker_gender(scene: str, gender: str | None) -> str:
    """Friend's look must match the opposite-gender stock voice, or Brian plays on a woman."""
    text = (scene or "").strip()
    g = (gender or "").strip().lower()
    if not text or g not in {"male", "female"}:
        return text
    if not re.search(r"\b(friend|reporter|interviewer)\b", text, re.I):
        return text
    if _FRIEND_LOOKS_RE.search(text):
        return text
    noun = "man" if g == "male" else "woman"
    role = "friend"
    if re.search(r"\breporter\b", text, re.I) and not re.search(r"\bfriend\b", text, re.I):
        role = "reporter"
    sentence = f"The {role} is a {noun}."
    if sentence.lower() in text.lower():
        return text
    return f"{text.rstrip('.!?')} {sentence}"


def extract_scene_dialogue(prompt: str, *, face_gender: str | None = None) -> list[SceneLine]:
    """Spoken lines, tagged Face vs everyone else.

    Face gender comes from the Voice chip (Jessica → she, Brian → he). Unattributed
    quotes belong to the Face. A reporter/friend/he (when Face is she) is other.
    A single ``and says`` / ``says:`` line with no quotes is the Face.
    """
    body = prompt or ""
    face_is_male = (face_gender or "").strip().lower() == "male"
    lines: list[SceneLine] = []
    prev_end = 0
    for match in _QUOTE_RE.finditer(body):
        lead = body[prev_end : match.start()]
        prev_end = match.end()
        if _WRITTEN_LEAD_RE.search(lead):
            continue
        spoken = expand_spoken_domains(match.group(1).strip())
        if not spoken:
            continue
        lines.append(
            SceneLine(
                speaker=_speaker_from_lead(lead, face_is_male=face_is_male),
                text=spoken,
            )
        )
    if lines:
        return lines
    from app.routers.play_video_helpers import split_avatar_user_prompt

    spoken, _scene = split_avatar_user_prompt(body)
    spoken = expand_spoken_domains((spoken or "").strip())
    if spoken:
        return [SceneLine(speaker="face", text=spoken)]
    return []


def scene_needs_exact_voice(
    *,
    face_asset_id: UUID | None,
    continue_from_asset_id: UUID | None,
    prompt: str,
) -> bool:
    """TTS then Seedance when Scene has a Face and a spoken line.

    Quotes, ``says:``, or natural ``and says`` all count. Topic-only copy does
    not. Extend keeps exact voice too. Prior clip is @Video1; new TTS is @AudioN.
    """
    if face_asset_id is None:
        return False
    _ = continue_from_asset_id
    return bool(extract_scene_dialogue(prompt))
