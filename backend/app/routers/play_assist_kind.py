"""Rule-based Clip kind, chips, and replies. Grok does not pick the engine."""
from __future__ import annotations

import re

from app.routers.play_scene_dialogue import _WRITTEN_LEAD_RE, normalize_scene_dialogue_order
from app.routers.play_video_helpers import split_avatar_user_prompt, strip_says_marker
from app.schemas.play import (
    PlayAssistChoice,
    PlayAssistDraft,
    PlayAssistMessage,
    PlayAssistOptions,
    PlayAssistSource,
)

ClipKind = str

KIND_AVATAR = "avatar"
KIND_VIDEO = "video"
KIND_VALUES = (KIND_AVATAR, KIND_VIDEO)

CHIP_PREFIX = "kind:"
KIND_CHIPS: tuple[tuple[str, str], ...] = (
    ("Talking", KIND_AVATAR),
    ("Scene", KIND_VIDEO),
)

_PLACE_WORD = re.compile(
    r"\b("
    r"kitchen|bedroom|bathroom|office|cafe|caf[eé]|street|studio|beach|park|"
    r"gym|car|apartment|counter|mirror|living room|sidewalk|rooftop"
    r")\b",
    re.I,
)
_PHOTO_RE = re.compile(
    r"\b("
    r"keep (this |my |the )?(photo|still|face)|your photo|"
    r"exact words|say exactly|read this|lip-?sync"
    r")\b",
    re.I,
)
_VIDEO_RE = re.compile(
    r"\b("
    r"two people|two friends|three people|a crowd|no talking|"
    r"nobody talking|silent clip|product (shot|close-up)|hands open|"
    r"(?<!don't )(?<!dont )(?<!do not )make (?:me )?a scene|this is a scene|"
    r"(?:the |her |his )?friend (?:replies|says|asks)"
    r")\b",
    re.I,
)
_TALKING_RE = re.compile(r"\b(you talking|talking clip|talking head)\b", re.I)
_FIRST_PERSON = re.compile(r"^(i|i'm|i’m|im|we|we're|we’re|you)\b", re.I)
_QUOTED_SPEECH_RE = re.compile(r'["“]([^"“”]{2,})["”]')
_TRAILING_CONJ_RE = re.compile(r"(?i)\s+(?:and|then|while|as)\s*$")
_SCENE_PRONOUN_TAIL_RE = re.compile(r"(?is)(?:^|[,.\s]+)(?:he|she|they|i|we)\s*$")


def parse_kind_chip(text: str) -> str | None:
    raw = (text or "").strip()
    if raw.startswith(CHIP_PREFIX):
        value = raw[len(CHIP_PREFIX) :].strip().lower()
        if value == "lipsync":
            return KIND_AVATAR
        return value if value in KIND_VALUES else None
    return None


def is_kind_chip(text: str) -> bool:
    return parse_kind_chip(text) is not None


def clip_kind_options(kind: str) -> PlayAssistOptions:
    pick = kind if kind in KIND_VALUES else KIND_AVATAR
    return PlayAssistOptions(
        header="This clip",
        choices=[
            PlayAssistChoice(
                label=label,
                value=f"{CHIP_PREFIX}{value}",
                selected=value == pick,
            )
            for label, value in KIND_CHIPS
        ],
    )


def classify_clip_kind(
    *,
    last_user: str,
    draft: PlayAssistDraft,
    request_mode: str,
    source: PlayAssistSource | None = None,
) -> str:
    """Pick the paid job. Chip taps and follow-on kinds win over the model."""
    chip = parse_kind_chip(last_user)
    if chip:
        return chip
    if source is not None:
        if source.kind == "continue":
            return KIND_VIDEO
        if source.kind == "revoice":
            return KIND_AVATAR
    if request_mode == "lipsync":
        return KIND_AVATAR
    if request_mode == "image":
        return KIND_VIDEO
    if draft.kind == "lipsync":
        draft = draft.model_copy(update={"kind": KIND_AVATAR})
    if draft.kind in KIND_VALUES:
        # A follow-up ("make it funnier") keeps the pick unless they rename the job.
        blob = last_user.strip()
        if (
            not _PHOTO_RE.search(blob)
            and not _VIDEO_RE.search(blob)
            and not _TALKING_RE.search(blob)
            and not _looks_like_two_hander(blob)
        ):
            return draft.kind
    if request_mode == "video":
        guessed = _guess_kind_from_text(last_user, draft)
        return guessed if guessed != KIND_AVATAR else KIND_VIDEO
    return _guess_kind_from_text(last_user, draft)


def _guess_kind_from_text(last_user: str, draft: PlayAssistDraft) -> str:
    blob = " ".join(
        part for part in (last_user, draft.scene, draft.line) if (part or "").strip()
    ).strip()
    if not blob:
        return KIND_AVATAR
    if _PHOTO_RE.search(blob):
        return KIND_AVATAR
    if _TALKING_RE.search(blob):
        return KIND_AVATAR
    if _VIDEO_RE.search(blob):
        return KIND_VIDEO
    if _looks_like_two_hander(blob):
        return KIND_VIDEO
    if _looks_like_script(blob):
        return KIND_AVATAR
    return KIND_AVATAR


def _spoken_quote_count(text: str) -> int:
    """Quoted speech that is not signage / printed text."""
    raw = text or ""
    count = 0
    prev = 0
    for match in _QUOTED_SPEECH_RE.finditer(raw):
        lead = raw[prev : match.start()]
        prev = match.end()
        if _WRITTEN_LEAD_RE.search(lead):
            continue
        count += 1
    return count


# A second person who speaks. Bystanders in a crowd do not count: "people in
# the background and she says" is still Talking. Do not let the match cross a
# sentence end, or "a man in the back. She says hi" becomes Scene.
_OTHER_SPEAKER_RE = re.compile(
    r"\b(?:a |the |another |her |his )?"
    r"(?:man|men|woman|women|guy|girl|boy|lady|stranger|friend)\b"
    r"[^.?!\n]{0,48}"
    r"\b(?:asks?|says?|replies|replied|asked)\b",
    re.I,
)


def _looks_like_two_hander(text: str) -> bool:
    """Two spoken parts from two people. Talking is one speaker plus a listener."""
    raw = text or ""
    if _spoken_quote_count(raw) >= 2:
        return True
    if re.search(
        r"\b(?:the |her |his )?friend (?:replies|says|asks)\b",
        raw,
        re.I,
    ):
        return True
    return bool(_OTHER_SPEAKER_RE.search(raw))


def _looks_like_script(text: str) -> bool:
    words = text.split()
    if len(words) < 12:
        return False
    if _PLACE_WORD.search(" ".join(words[:8])):
        return False
    return bool(_FIRST_PERSON.search(text.strip()))


def _looks_like_refinement(text: str) -> bool:
    """Short follow-up. Keep the draft and fold this into SCENE."""
    raw = (text or "").strip()
    if not raw or is_kind_chip(raw):
        return False
    if _PHOTO_RE.search(raw) or _VIDEO_RE.search(raw) or _TALKING_RE.search(raw):
        return False
    if _looks_like_two_hander(raw):
        return False
    return len(raw.split()) <= 8


def fold_line_into_scene(scene: str, line: str) -> str:
    """Put a spoken line back into SCENE as quoted speech.

    A scene generate only sends SCENE. A Talking extract that then switches to
    A scene used to leave the words in ``line`` and generate a silent kitchen.
    """
    place = (scene or "").strip()
    spoken = (line or "").strip().strip(' "“”')
    if not spoken:
        return place
    if not place:
        return f'"{spoken}"'
    compact = " ".join(place.split()).lower()
    if spoken.lower() in compact:
        return place
    return f'{place.rstrip(" .,;:!?")}. "{spoken}"'


def split_clip_blob(text: str, kind: str) -> tuple[str, str]:
    """Return (scene, line) for this kind. Talking never invents a line here."""
    raw = strip_says_marker(text or "").strip()
    if not raw:
        return "", ""
    if kind == KIND_VIDEO:
        # Two people talking: keep both quotes in order. Extracting the first
        # line stuffed the second into SCENE and previewed one THEY SAY.
        if _looks_like_two_hander(raw):
            return normalize_scene_dialogue_order(raw), ""
        extracted = _extract_natural_speech(raw)
        if extracted:
            return fold_line_into_scene(*extracted), ""
        return raw, ""
    spoken, scene = split_avatar_user_prompt(text)
    if spoken:
        return scene, spoken
    extracted = _extract_natural_speech(raw)
    if extracted:
        return extracted
    placed = _split_place_then_words(raw)
    if placed:
        return placed
    return raw, ""


def _extract_natural_speech(text: str) -> tuple[str, str] | None:
    """Pull a spoken line from 'and says …', 'she says …', or quotes.

    Natural English matches generate (`split_avatar_user_prompt`). Signage quotes
    are skipped the same way Scene TTS skips them.
    """
    raw = (text or "").strip()
    if not raw:
        return None
    spoken, scene = split_avatar_user_prompt(raw)
    if spoken:
        return scene, spoken
    exact = re.search(
        r"(?is)(?:say exactly|read this(?: aloud)?)\s*:?\s+(.+)$",
        raw,
    )
    if exact:
        line = (exact.group(1) or "").strip()
        if line:
            return _clean_scene(raw[: exact.start()]), line
    prev = 0
    for quoted in _QUOTED_SPEECH_RE.finditer(raw):
        lead = raw[prev : quoted.start()]
        prev = quoted.end()
        if _WRITTEN_LEAD_RE.search(lead):
            continue
        line = quoted.group(1).strip()
        if not line:
            continue
        leftover = f"{raw[: quoted.start()]} {raw[quoted.end() :]}".strip()
        return _clean_scene(leftover), line
    return None


def _clean_scene(scene: str) -> str:
    text = (scene or "").strip()
    text = _SCENE_PRONOUN_TAIL_RE.sub("", text)
    text = _TRAILING_CONJ_RE.sub("", text)
    return text.strip().rstrip(".,;:")


def _split_place_then_words(text: str) -> tuple[str, str] | None:
    parts = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)
    if len(parts) < 2:
        return None
    head, rest = parts[0].strip(), parts[1].strip()
    if _PLACE_WORD.search(head) and len(rest.split()) >= 4:
        return head.rstrip(".,;:"), rest
    return None


def merge_clip_fields(
    *,
    kind: str,
    draft: PlayAssistDraft,
    last_user: str,
) -> tuple[str, str]:
    """Keep scene/line on a chip tap. Otherwise split the latest user text."""
    if kind == "lipsync":
        kind = KIND_AVATAR
    if is_kind_chip(last_user):
        scene = (draft.scene or "").strip()
        line = (draft.line or "").strip()
        if kind == KIND_VIDEO:
            return normalize_scene_dialogue_order(fold_line_into_scene(scene, line)), ""
        if kind == KIND_AVATAR and not line and scene:
            recovered_scene, recovered_line = split_clip_blob(scene, KIND_AVATAR)
            if recovered_line:
                return recovered_scene, recovered_line
        return scene, line
    if _looks_like_refinement(last_user) and (
        (draft.scene or "").strip() or (draft.line or "").strip()
    ):
        extra = last_user.strip()
        if kind == KIND_VIDEO:
            scene = (draft.scene or "").strip()
            scene = f"{scene}. {extra}" if scene else extra
            return normalize_scene_dialogue_order(scene), ""
        scene = (draft.scene or "").strip()
        line = (draft.line or "").strip()
        scene = f"{scene}. {extra}" if scene else extra
        return scene, line
    scene, line = split_clip_blob(last_user, kind)
    if kind == KIND_AVATAR:
        if not scene:
            scene = (draft.scene or "").strip()
        if not line:
            line = (draft.line or "").strip()
    if kind == KIND_VIDEO:
        if line:
            scene = fold_line_into_scene(scene, line)
        elif not scene:
            scene = fold_line_into_scene(draft.scene or "", draft.line or "")
        return normalize_scene_dialogue_order(scene), ""
    return scene, line


def last_user_text(messages: list[PlayAssistMessage]) -> str:
    for m in reversed(messages):
        if m.role == "user" and m.content.strip():
            return m.content.strip()
    return ""


def needs_line_draft(kind: str, draft: PlayAssistDraft) -> bool:
    return kind == KIND_AVATAR and not (draft.line or "").strip()


def build_clip_reply(draft: PlayAssistDraft, *, kind: str) -> str:
    """One or two sentences. No em dashes. Kind chips are the override."""
    if kind == KIND_VIDEO:
        return "Scene, not a talking head. Generate if that is right, or pick Talking."
    if draft.line.strip():
        return "Talking clip, this line. Generate if that is right, or pick Scene."
    return "Talking clip. I will draft the line next. Or pick Scene."


def line_draft_system_prompt() -> str:
    return (
        "Write one spoken line for a short talking clip from this topic. "
        "Keep their language, product names, and claims. "
        "Never invent offers, prices, discounts, statistics, or facts they did not give you. "
        "Natural spoken words, hook first. Never cut, trim, or shorten the line. "
        "Be brief: one or two sentences, no lists, no markdown, no em dashes. "
        'Reply with JSON only: {"reply": str, "draft": {"line": str, "scene": str}}. '
        "Keep scene as given unless they named a place you should copy. "
        "If someone is in the scene to talk to, the scene should say they look at that "
        "person, not past them and not at the camera. One short sentence. No shot list. "
        "Reply is one sentence saying you drafted the line."
    )
