"""Curated ElevenLabs stock voices shown in Create.

Product ids are ordinary first names. Grok still uses ara/rex as picture
stand-ins only. Those xAI ids must never appear in the picker.

The 19 perpetual defaults live in this module. Trending Voice Library
copies are in library_voices.json (shared by every workspace, not clones).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Sequence

# New ElevenLabs default voices (perpetual). Do not pin the retiring Rachel/Adam set.
STOCK_VOICES: dict[str, dict[str, str]] = {
    "jessica": {
        "name": "Jessica",
        "description": "Warm and conversational",
        "gender": "female",
        "accent": "american",
        "elevenlabs_voice_id": "cgSgspJ2msm6clMCkdW9",
    },
    "lily": {
        "name": "Lily",
        "description": "Soft British, easygoing",
        "gender": "female",
        "accent": "british",
        "elevenlabs_voice_id": "pFZP5JQG7iQjIQuC4Bku",
    },
    "alice": {
        "name": "Alice",
        "description": "Clear and engaging",
        "gender": "female",
        "accent": "british",
        "elevenlabs_voice_id": "Xb7hH8MSUJpSbSDYk0k2",
    },
    "matilda": {
        "name": "Matilda",
        "description": "Calm and professional",
        "gender": "female",
        "accent": "american",
        "elevenlabs_voice_id": "XrExE9yKIg1WjnnlVkGX",
    },
    "laura": {
        "name": "Laura",
        "description": "Gentle and even",
        "gender": "female",
        "accent": "american",
        "elevenlabs_voice_id": "FGY2WhTYpPnrIDTdsKH5",
    },
    "aria": {
        "name": "Aria",
        "description": "Expressive American",
        "gender": "female",
        "accent": "american",
        "elevenlabs_voice_id": "9BWtsMINqrJLrRamj77X",
    },
    "charlotte": {
        "name": "Charlotte",
        "description": "Bright European",
        "gender": "female",
        "accent": "swedish",
        "elevenlabs_voice_id": "XB0fDUnXU5powFXDhCwa",
    },
    "river": {
        "name": "River",
        "description": "Relaxed and even",
        "gender": "neutral",
        "accent": "american",
        "elevenlabs_voice_id": "SAz9YHcvj6GT2YYXdXww",
    },
    "brian": {
        "name": "Brian",
        "description": "Clear and professional",
        "gender": "male",
        "accent": "american",
        "elevenlabs_voice_id": "nPczCjzI2devNBz1zQrb",
    },
    "daniel": {
        "name": "Daniel",
        "description": "Warm British",
        "gender": "male",
        "accent": "british",
        "elevenlabs_voice_id": "onwK4e9ZLuTAKqWW03F9",
    },
    "liam": {
        "name": "Liam",
        "description": "Bright and energetic",
        "gender": "male",
        "accent": "american",
        "elevenlabs_voice_id": "TX3LPaxmHKxFdv7VOQHJ",
    },
    "will": {
        "name": "Will",
        "description": "Casual American",
        "gender": "male",
        "accent": "american",
        "elevenlabs_voice_id": "bIHbv24MWmeRgasZH58o",
    },
    "george": {
        "name": "George",
        "description": "Smooth and grounded",
        "gender": "male",
        "accent": "british",
        "elevenlabs_voice_id": "JBFqnCBsd6RMkjVDRZzb",
    },
    "bill": {
        "name": "Bill",
        "description": "Warm and steady",
        "gender": "male",
        "accent": "american",
        "elevenlabs_voice_id": "pqHfZKP75CvOlQylNhV4",
    },
    "callum": {
        "name": "Callum",
        "description": "Husky British",
        "gender": "male",
        "accent": "british",
        "elevenlabs_voice_id": "N2lVS1w4EtoT3dr4eOWO",
    },
    "charlie": {
        "name": "Charlie",
        "description": "Confident Australian",
        "gender": "male",
        "accent": "australian",
        "elevenlabs_voice_id": "IKne3meq5aSn9XLyUdCD",
    },
    "chris": {
        "name": "Chris",
        "description": "Easygoing American",
        "gender": "male",
        "accent": "american",
        "elevenlabs_voice_id": "iP95p4xoKVk53GoZ742B",
    },
    "eric": {
        "name": "Eric",
        "description": "Smooth American",
        "gender": "male",
        "accent": "american",
        "elevenlabs_voice_id": "cjVigY5qzO86Huf0OWal",
    },
    "roger": {
        "name": "Roger",
        "description": "Laid-back American",
        "gender": "male",
        "accent": "american",
        "elevenlabs_voice_id": "CwhRBWXzGAHq8TQ4Fs17",
    },
}

FEATURED_VOICE_IDS: tuple[str, ...] = ("jessica", "lily", "brian", "daniel", "liam")
DEFAULT_STOCK_VOICE_ID = "jessica"
DEFAULT_STOCK_MALE_VOICE_ID = "brian"
DEFAULT_STOCK_VOICE_IDS: frozenset[str] = frozenset(STOCK_VOICES)


def opposite_stock_voice_id(gender: str | None) -> str:
    """Built-in for a second speaker. Opposite of the Face picker gender."""
    if (gender or "").strip().lower() == "male":
        return DEFAULT_STOCK_VOICE_ID
    return DEFAULT_STOCK_MALE_VOICE_ID


def _load_library_voices() -> dict[str, dict[str, str]]:
    path = Path(__file__).with_name("library_voices.json")
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text())
    if not isinstance(raw, list):
        raise RuntimeError("library_voices.json must be a list")
    out: dict[str, dict[str, str]] = {}
    for row in raw:
        if not isinstance(row, dict):
            continue
        vid = str(row.get("id") or "").strip().lower()
        el = str(row.get("elevenlabs_voice_id") or "").strip()
        if not vid or not el:
            continue
        out[vid] = {
            "name": str(row.get("name") or vid.title()),
            "description": str(row.get("description") or ""),
            "gender": str(row.get("gender") or ""),
            "accent": str(row.get("accent") or ""),
            "language": str(row.get("language") or "en"),
            "elevenlabs_voice_id": el,
            "public_owner_id": str(row.get("public_owner_id") or ""),
        }
    overlap = DEFAULT_STOCK_VOICE_IDS & set(out)
    if overlap:
        raise RuntimeError(f"library voice ids collide with defaults: {sorted(overlap)}")
    return out


LIBRARY_VOICES = _load_library_voices()
STOCK_VOICES = {**STOCK_VOICES, **LIBRARY_VOICES}

# Retired xAI picker ids. Used to drop old Library talking / lip-sync clips and
# to fall leftover generate bodies back to the new default.
LEGACY_XAI_VOICE_IDS: frozenset[str] = frozenset(
    {
        "ara",
        "eve",
        "leo",
        "rex",
        "sal",
        "altair",
        "atlas",
        "carina",
        "castor",
        "celeste",
        "cosmo",
        "helios",
        "helix",
        "iris",
        "kepler",
        "lumen",
        "luna",
        "lux",
        "naksh",
        "orion",
        "perseus",
        "rigel",
        "sirius",
        "ursa",
        "zagan",
        "zenith",
        "wellness",
        "support",
        "male",
        "female",
    }
)

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_GENDER_SORT = {"female": 0, "male": 1, "neutral": 2}


def is_stock_voice_id(voice: str | None) -> bool:
    return (voice or "").strip().lower() in STOCK_VOICES


def is_legacy_xai_voice_id(voice: str | None) -> bool:
    return (voice or "").strip().lower() in LEGACY_XAI_VOICE_IDS


def stock_voice_id_for(voice: str | None) -> str:
    """Map a picker / generate voice value to a current stock product id."""
    key = (voice or "").strip().lower()
    if key in STOCK_VOICES:
        return key
    if key == "male":
        return DEFAULT_STOCK_MALE_VOICE_ID
    return DEFAULT_STOCK_VOICE_ID


def stock_voice_meta(voice_id: str) -> dict[str, str]:
    return STOCK_VOICES[stock_voice_id_for(voice_id)]


def elevenlabs_voice_id_for(voice: str | None) -> str:
    return stock_voice_meta(voice)["elevenlabs_voice_id"]


def _voice_sort_key(row: dict[str, str]) -> tuple[int, int, str]:
    vid = (row.get("id") or "").strip().lower()
    try:
        featured = FEATURED_VOICE_IDS.index(vid)
    except ValueError:
        featured = len(FEATURED_VOICE_IDS)
    gender = (row.get("gender") or "").strip().lower()
    gender_rank = _GENDER_SORT.get(gender, 9)
    name = (row.get("name") or vid).strip().lower()
    in_featured = 0 if featured < len(FEATURED_VOICE_IDS) else 1
    return (in_featured, featured if in_featured == 0 else 0, gender_rank, name)


def sort_builtin_voices(voices: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(voices, key=_voice_sort_key)


def builtin_voice_rows() -> list[dict[str, str]]:
    rows = [
        {
            "id": voice_id,
            "name": meta["name"],
            "description": meta["description"],
            "gender": meta.get("gender") or "",
            "accent": meta.get("accent") or "",
            "language": meta.get("language") or "multilingual",
            "provider": "elevenlabs",
            "elevenlabs_voice_id": meta["elevenlabs_voice_id"],
        }
        for voice_id, meta in STOCK_VOICES.items()
    ]
    return sort_builtin_voices(rows)


def should_purge_legacy_stock_clip(
    *,
    play_mode: str | None,
    voice: str | None,
    asset_type: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """True for Library talking / lip-sync videos that used an xAI stock voice.

    Faces are video_assets with play_mode avatar and no voice. Never match those.
    """
    meta = metadata or {}
    if meta.get("face_library") is True or meta.get("mode") == "avatar_source_image":
        return False
    if (asset_type or "video").strip().lower() != "video":
        return False
    mode = (play_mode or "").strip().lower()
    if mode not in {"avatar", "lipsync"}:
        return False
    raw = (voice or "").strip()
    if _UUID_RE.fullmatch(raw):
        return False
    if not raw:
        return mode == "avatar"
    return raw.lower() in LEGACY_XAI_VOICE_IDS


def clip_purge_fields(metadata: dict[str, Any] | None) -> tuple[str, str | None]:
    meta = metadata or {}
    play_mode = str(meta.get("play_mode") or "").strip() or None
    raw = meta.get("voice")
    voice = str(raw).strip() if raw is not None else None
    return play_mode or "", voice
