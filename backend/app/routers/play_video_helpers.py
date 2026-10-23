"""Play video generation helpers (refs, prompts, provider start)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.media_store import MediaStoreError, public_media_url, xai_image_ref
from app.models import User, VideoAsset
from app.routers.play_prompt_cast import (
    avatar_address_rule,
    avatar_cast_rule,
    avatar_frame_rule,
    avatar_speaker_rule,
    ensure_listener_look,
    ensure_talking_frame,
    scene_has_addressee,
)
from app.routers.video_helpers import get_asset
from app.schemas.play import PlayGenerateRequest

# Tests and assist import these names from this module.
_scene_has_addressee = scene_has_addressee
_avatar_address_rule = avatar_address_rule

# Talking (avatar) UI form: "Scene and wardrobe. She says: the spoken line."
# Lip-sync must stay pure script (no says-split there).
_AVATAR_SAYS_RE = re.compile(r"(?is)\bsays?\s*:\s*(.+)\s*$")
# Natural English the Create box actually gets: "and says LINE" / "She says LINE"
# / "and she says LINE". Colon remains the stored token. This only extracts.
# Never match "a sign that says". "and says" may follow a noun ("kitchen and says").
# "?" / "!" are sentence boundaries ("? She says no"), not only [.,;].
_AVATAR_NATURAL_SAYS_RE = re.compile(
    r"(?is)"
    r"(?:"
    r"(?:^|[.,;!?]\s+|,\s*)(?:he|she|they|i|we)\s+says?\s+"
    r"|"
    r"(?:^|\s+)and\s+(?:(?:he|she|they|i|we)\s+)?says?\s+"
    r")"
    r"(?!that\b)"
    r"(.+)$"
)
_TRAILING_CONJUNCTION_RE = re.compile(r"(?i)\s+(?:and|then|while|as)\s*$")
# The marker with nothing after it never matches the rule above (it needs a line),
# so it used to survive into the scene text and out to the provider.
_AVATAR_DANGLING_SAYS_RE = re.compile(r"(?is)[\s.,;:]*\bsays?\s*:\s*$")
# "say exactly LINE" / "read this aloud: LINE" — the meta prefix is not spoken.
_SAY_EXACTLY_RE = re.compile(
    r"(?is)(?:say exactly|read this(?: aloud)?)\s*:?\s+(.+)$"
)
_BARE_LINE_RE = re.compile(
    r"^(?:hey|hi|hello|welcome)\b|"
    r"^(?:i(?:['’]m| am)?|we(?:['’]re| are)?|you)\b",
    re.I,
)
_PLACE_START_RE = re.compile(
    r"^(?:"
    r"kitchen|bedroom|bathroom|office|cafe|caf[eé]|street|studio|beach|park|"
    r"gym|car|apartment|counter|mirror|living room|sidewalk|rooftop"
    r")\b",
    re.I,
)


def _looks_like_bare_spoken_line(text: str) -> bool:
    """First-person or greeting with no place lead-in. Those words are the line."""
    raw = (text or "").strip()
    if not raw or _PLACE_START_RE.search(raw):
        return False
    return bool(_BARE_LINE_RE.search(raw))
# A quoted span after "says:" pins where the line ends, so trailing stage
# directions stay scene direction instead of being read out loud.
_QUOTED_SPAN_RE = re.compile(r'["“]([^"“”]{2,})["”]')
# Drop speech lead-ins left in the scene half ("She", "He leans toward the camera and").
_AVATAR_SCENE_LEADIN_RE = re.compile(
    r"(?is)"
    r"(?:^|[,.\s]+)"
    r"(?:he|she|they|i|we)"
    r"(?:"
    r"\s+looks?\s+at\s+(?:the\s+)?camera\s+and|"
    r"\s+leans?\s+toward(?:s)?\s+(?:the\s+)?camera\s+and|"
    r"\s+faces?\s+(?:the\s+)?camera\s+and|"
    r"\s+turns?\s+to\s+(?:the\s+)?camera\s+and"
    r")?"
    r"\s*$"
)

# Per-provider reference-image ceilings. Kling image2video accepts exactly one
# image, so a second person from a reference is not possible there.
PROVIDER_MAX_REF_IMAGES: dict[str, int] = {
    "gemini": 3,
    "xai": 7,
    "seedance": 9,
    "kling": 1,
}


@dataclass(slots=True)
class ReferenceMaterials:
    """Resolved generation inputs, with each image's job kept distinct.

    ``continue_still`` is the opening frame for extend on first-frame providers.
    It is deliberately not in ``image_urls``: an identity reference and a first
    frame are different instructions to every provider we support.
    """

    image_urls: list[str]
    image_roles: list[str]
    video_urls: list[str]
    audio_urls: list[str]
    ref_ids: list[str]
    poster_url: str | None
    continue_still: str | None
    notes: list[str]


# Seedance material caps (seevio.ai API). Fast 3 files / 15s; 2.5 is 10 / 30s.
MAX_REF_IMAGES = 9
MAX_REF_VIDEOS = 3
MAX_REF_AUDIOS = 3
MAX_REF_TOTAL = 12
MAX_REF_VIDEO_AUDIO_SECONDS = 15.0


def seedance_material_caps(model_id: str | None) -> tuple[int, int, int, float]:
    """images, videos, audios, combined video+audio seconds."""
    from app.seedance_media import is_seedance_25

    if is_seedance_25(model_id):
        return 30, 10, 10, 30.0
    return MAX_REF_IMAGES, MAX_REF_VIDEOS, MAX_REF_AUDIOS, MAX_REF_VIDEO_AUDIO_SECONDS

# Play "Extend" / continue_from support by provider.
# seedance: prior video as motion ref
# gemini/kling: prior last frame (or extracted frame) as image-to-video start
# xai: native video extension API
EXTEND_PROVIDERS = frozenset({"seedance", "gemini", "kling", "xai"})


def supports_play_extend(provider: str | None) -> bool:
    return (provider or "").strip().lower() in EXTEND_PROVIDERS


def seedance_public_media_url(
    *,
    storage_url: str | None,
    provider_url: str | None,
    settings: Settings,
    label: str = "Media",
) -> str:
    """Seedance / Kling need a publicly reachable HTTPS URL (no data: URLs).

    Prefer durable storage_url over temporary provider CDNs (imgen.x.ai expires).
    """
    from app.media_store import _is_ephemeral_provider_cdn

    ordered: list[str] = []
    for u in (storage_url, provider_url):
        if u and str(u).strip():
            ordered.append(u.strip())
    # Durable first, skip ephemeral CDN until last.
    durable = [u for u in ordered if not _is_ephemeral_provider_cdn(u)]
    ephemeral = [u for u in ordered if _is_ephemeral_provider_cdn(u)]
    for candidate in durable + ephemeral:
        expanded = public_media_url(candidate, settings)
        if (
            expanded.startswith("https://")
            and "localhost" not in expanded
            and "127.0.0.1" not in expanded
            and not _is_ephemeral_provider_cdn(expanded)
        ):
            return expanded
    # Ephemeral only if nothing durable worked
    for candidate in ephemeral:
        expanded = public_media_url(candidate, settings)
        if expanded.startswith("https://") and "localhost" not in expanded:
            return expanded
    try:
        ref = xai_image_ref(
            storage_url=storage_url,
            provider_url=provider_url,
            settings=settings,
            label=label,
        )
    except MediaStoreError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if ref.startswith("data:"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"{label} must be on public HTTPS storage for this model "
                "(configure R2 or a public API base URL)."
            ),
        )
    if not ref.startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{label} needs a public HTTPS URL for this model",
        )
    return ref


def resolve_avatar_face_url(
    *,
    provider: str,
    storage_url: str | None,
    provider_url: str | None,
    settings: Settings,
    label: str = "Face",
) -> str:
    """Resolve a face plate for Talking clips for every provider.

    - Grok / Veo: always embed as data: URL (provider never needs to fetch our storage).
    - Seedance / Kling: durable public HTTPS only (APIs reject data: URLs).
    """
    p = (provider or "").strip().lower()
    if p in {"seedance", "kling"}:
        return seedance_public_media_url(
            storage_url=storage_url,
            provider_url=provider_url,
            settings=settings,
            label=label,
        )
    # xai, gemini, and any future provider that accepts data:image
    try:
        return xai_image_ref(
            storage_url=storage_url,
            provider_url=provider_url,
            settings=settings,
            label=label,
            prefer_data_url=True,
        )
    except MediaStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


def normalize_play_resolution(raw: str | None, *, provider: str, model_id: str | None = None) -> str:
    value = (raw or "720p").strip().lower()
    if provider == "seedance":
        from app.seedance_media import normalize_seedance_resolution

        return normalize_seedance_resolution(value, model=model_id)
    # Kling maps 720p→std, 1080p→pro.
    if provider == "kling":
        if value in {"1080p", "1080", "fhd", "pro", "4k"}:
            return "1080p"
        return "720p"
    # Grok video: 480p or 720p.
    if provider == "xai":
        if value in {"480p", "480"}:
            return "480p"
        return "720p"
    if value in {"1080p", "1080", "fhd"}:
        return "1080p"
    return "720p"


def _duration_from_meta(asset: VideoAsset) -> float | None:
    meta = dict(asset.asset_metadata or {})
    raw = meta.get("duration_seconds")
    if isinstance(raw, (int, float)) and raw > 0:
        return float(raw)
    return None


def _public_https_media(
    *,
    storage_url: str | None,
    provider_url: str | None,
    settings: Settings,
    label: str,
) -> str:
    """Public HTTPS URL for external video APIs (same rules as Seedance faces)."""
    return seedance_public_media_url(
        storage_url=storage_url,
        provider_url=provider_url,
        settings=settings,
        label=label,
    )


def _extract_last_frame_still(
    *,
    video_url: str | None,
    settings: Settings,
    asset_id: UUID,
) -> str | None:
    """Grab a late frame from a ready clip for Veo/Kling image-to-video continue."""
    if not video_url:
        return None
    try:
        import subprocess
        from pathlib import Path

        from app.media_store import ensure_local_media, store_file
        from app.video_renderer import ffmpeg_path

        binary = ffmpeg_path()
        if not binary:
            return None
        local = ensure_local_media(video_url, settings)
        if not local.exists() or local.stat().st_size <= 0:
            return None
        out = settings.media_path / "play" / f"{asset_id}-continue-frame.jpg"
        out.parent.mkdir(parents=True, exist_ok=True)
        # Last half-second (or near end) — good continuity bridge for i2v.
        cmd = [
            binary,
            "-y",
            "-sseof",
            "-0.4",
            "-i",
            str(local),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(out),
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        if not out.exists() or out.stat().st_size <= 0:
            return None
        stored = store_file(
            path=out,
            subdir="play",
            filename=f"{asset_id}-continue-frame.jpg",
            settings=settings,
            content_type="image/jpeg",
        )
        return public_media_url(stored, settings) if stored else None
    except Exception as exc:  # noqa: BLE001
        print(f"continue_frame extract failed asset={asset_id}: {exc}", flush=True)
        return None


def resolve_continue_still_url(
    *,
    prior: VideoAsset,
    settings: Settings,
) -> str | None:
    """Still used as first frame when extending with Veo / Kling."""
    meta = dict(prior.asset_metadata or {})
    for key in ("last_frame_url", "poster_url"):
        raw = meta.get(key)
        if isinstance(raw, str) and raw.strip():
            try:
                return _public_https_media(
                    storage_url=raw.strip(),
                    provider_url=None,
                    settings=settings,
                    label="Continue frame",
                )
            except HTTPException:
                continue
    video = prior.storage_url or prior.provider_url
    return _extract_last_frame_still(video_url=video, settings=settings, asset_id=prior.id)


async def _resolve_reference_materials(
    *,
    session: AsyncSession,
    user: User,
    body: PlayGenerateRequest,
    provider: str,
    settings: Settings,
    model_id: str | None = None,
) -> ReferenceMaterials:
    """Resolve face, continue frame, and user references into provider-ready URLs."""
    image_urls: list[str] = []
    image_roles: list[str] = []
    video_urls: list[str] = []
    audio_urls: list[str] = []
    ref_ids: list[str] = []
    poster_url: str | None = None
    continue_still: str | None = None
    notes: list[str] = []
    video_seconds = 0.0
    audio_seconds = 0.0
    roles = list(body.reference_roles or [])
    max_images, max_videos, max_audios, max_seconds = (
        seedance_material_caps(model_id) if (provider or "").strip().lower() == "seedance"
        else (MAX_REF_IMAGES, MAX_REF_VIDEOS, MAX_REF_AUDIOS, MAX_REF_VIDEO_AUDIO_SECONDS)
    )

    # Face first (identity) — same rules for every model.
    # Video mode may also carry a face: that is how a scene keeps one recognisable
    # person while still allowing other people, several speakers, and free-form
    # dialogue, none of which the single-subject Talking rails permit.
    if body.mode in {"avatar", "video", "lipsync"} and body.face_asset_id is not None:
        face = await get_asset(
            body.face_asset_id,
            user,
            session,
            "projects.read",
            missing="That face is gone. Pick another.",
        )
        if face.workspace_id != body.workspace_id or face.asset_type != "image" or face.status != "ready":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Face asset must be a ready image in this workspace",
            )
        face_ref = resolve_avatar_face_url(
            provider=provider,
            storage_url=face.storage_url,
            provider_url=face.provider_url,
            settings=settings,
            label="Face",
        )
        # Seedance/Kling: confirm the HTTPS face is actually fetchable before we bill.
        if (provider or "").strip().lower() in {"seedance", "kling"}:
            from app.media_store import assert_media_reachable

            try:
                face_ref = await assert_media_reachable(
                    face.storage_url or face.provider_url or face_ref,
                    settings,
                    label="Face",
                )
            except MediaStoreError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"{exc}. Re-upload the face or enable R2 so Seedance/Kling can fetch it."
                    ),
                ) from exc
        if not face_ref or not str(face_ref).strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not prepare the face image for this model. Re-select or re-upload the face.",
            )
        image_urls.append(face_ref)
        image_roles.append("identity")
        poster_url = face.storage_url or face.provider_url
        ref_ids.append(str(face.id))

    # Continue / extend prior clip
    if body.continue_from_asset_id is not None:
        if not supports_play_extend(provider):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Continue is not available for this model.",
            )
        prior = await get_asset(
            body.continue_from_asset_id,
            user,
            session,
            "projects.read",
            missing="That clip is gone. Start a new one instead of extending it.",
        )
        if (
            prior.workspace_id != body.workspace_id
            or prior.asset_type != "video"
            or prior.status != "ready"
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Continue needs a ready video clip in this account",
            )
        meta = dict(prior.asset_metadata or {})
        d = _duration_from_meta(prior)
        if d is not None:
            video_seconds += min(d, max_seconds)

        if provider == "seedance":
            # Full video as motion reference (+ optional last frame still).
            video_urls.append(
                _public_https_media(
                    storage_url=prior.storage_url,
                    provider_url=prior.provider_url,
                    settings=settings,
                    label="Source clip",
                )
            )
            last = meta.get("last_frame_url") or meta.get("poster_url")
            if isinstance(last, str) and last.strip() and len(image_urls) < max_images:
                try:
                    image_urls.append(
                        _public_https_media(
                            storage_url=last.strip(),
                            provider_url=None,
                            settings=settings,
                            label="Last frame",
                        )
                    )
                    image_roles.append("continuity")
                except HTTPException:
                    pass
        elif provider == "xai":
            # Grok native extension needs a public video URL.
            video_urls.append(
                _public_https_media(
                    storage_url=prior.storage_url,
                    provider_url=prior.provider_url,
                    settings=settings,
                    label="Source clip",
                )
            )
        else:
            # Veo / Kling: image-to-video from the last frame. The still is the
            # opening frame, which is a different job from an identity reference —
            # collapsing the two left Veo with no first frame at all while the
            # prompt still claimed to continue from one.
            still = resolve_continue_still_url(prior=prior, settings=settings)
            if not still:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Could not get a still frame from the prior clip to extend. "
                        "Try Seedance extend, or re-generate the clip first."
                    ),
                )
            continue_still = still

        if not poster_url:
            poster_url = (
                (meta.get("poster_url") if isinstance(meta.get("poster_url"), str) else None)
                or prior.storage_url
                or prior.provider_url
            )
        ref_ids.append(str(prior.id))

    for ref_index, asset_id in enumerate(body.reference_asset_ids or []):
        role = roles[ref_index].strip() if ref_index < len(roles) and roles[ref_index] else ""
        if len(image_urls) + len(video_urls) + len(audio_urls) >= MAX_REF_TOTAL:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"At most {MAX_REF_TOTAL} materials total (including face)",
            )
        asset = await get_asset(
            asset_id,
            user,
            session,
            "projects.read",
            missing="One of the attached references is gone. Remove it and try again.",
        )
        if asset.workspace_id != body.workspace_id or asset.status != "ready":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Each reference must be a ready asset in this account",
            )
        kind = asset.asset_type
        meta = dict(asset.asset_metadata or {})
        if meta.get("ref_kind") in ("image", "video", "audio"):
            kind = str(meta["ref_kind"])

        if kind == "image":
            if len(image_urls) >= max_images:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"At most {max_images} reference images",
                )
            if provider == "seedance":
                image_urls.append(
                    seedance_public_media_url(
                        storage_url=asset.storage_url,
                        provider_url=asset.provider_url,
                        settings=settings,
                        label="Reference image",
                    )
                )
            else:
                try:
                    image_urls.append(
                        xai_image_ref(
                            storage_url=asset.storage_url,
                            provider_url=asset.provider_url,
                            settings=settings,
                            label="Reference image",
                        )
                    )
                except MediaStoreError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=str(exc),
                    ) from exc
            image_roles.append(role or "reference")
        elif kind == "video":
            if provider != "seedance":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Video references need a Seedance model",
                )
            if len(video_urls) >= max_videos:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"At most {max_videos} reference videos",
                )
            d = _duration_from_meta(asset)
            if d is not None and video_seconds + d > max_seconds:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Reference videos must total {max_seconds:.0f}s or less",
                )
            if d is not None:
                video_seconds += d
            video_urls.append(
                seedance_public_media_url(
                    storage_url=asset.storage_url,
                    provider_url=asset.provider_url,
                    settings=settings,
                    label="Reference video",
                )
            )
        elif kind == "audio":
            if provider != "seedance":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Audio references need a Seedance model",
                )
            if len(audio_urls) >= max_audios:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"At most {max_audios} reference audio files",
                )
            d = _duration_from_meta(asset)
            if d is not None and audio_seconds + d > max_seconds:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Reference audio must total {max_seconds:.0f}s or less",
                )
            if d is not None:
                audio_seconds += d
            audio_urls.append(
                seedance_public_media_url(
                    storage_url=asset.storage_url,
                    provider_url=asset.provider_url,
                    settings=settings,
                    label="Reference audio",
                )
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="References must be image, video, or audio",
            )
        ref_ids.append(str(asset.id))

    if audio_urls and not image_urls and not video_urls:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Audio needs at least one image or video reference",
        )

    # Providers cap reference images well below our 9, and used to drop the excess
    # silently — the user paid for images the model never saw and was never told.
    cap = PROVIDER_MAX_REF_IMAGES.get((provider or "").strip().lower())
    if cap is not None and len(image_urls) > cap:
        dropped = len(image_urls) - cap
        image_urls = image_urls[:cap]
        image_roles = image_roles[:cap]
        notes.append(
            f"This model takes {cap} reference image{'s' if cap != 1 else ''}, "
            f"so {dropped} was not used." if dropped == 1 else
            f"This model takes {cap} reference image{'s' if cap != 1 else ''}, "
            f"so {dropped} were not used."
        )

    return ReferenceMaterials(
        image_urls=image_urls,
        image_roles=image_roles,
        video_urls=video_urls,
        audio_urls=audio_urls,
        ref_ids=ref_ids,
        poster_url=poster_url,
        continue_still=continue_still,
        notes=notes,
    )


def _voice_character_guidance(voice: str | None) -> str:
    """Steer native video audio toward a chosen voice gender/style (Video clips).

    Talking uses exact TTS plus Sync. Video still uses the video model's own audio.
    """
    from app.stock_voices import STOCK_VOICES, stock_voice_id_for

    raw = (voice or "").strip()
    if not raw:
        return ""
    try:
        from uuid import UUID

        UUID(raw)
        return "One natural speaking voice that matches the person on camera."
    except (ValueError, TypeError, AttributeError):
        pass

    key = stock_voice_id_for(raw)
    meta = STOCK_VOICES.get(key) or {}
    gender = str(meta.get("gender") or "").strip().lower()
    description = str(meta.get("description") or "").strip()

    if gender == "male":
        gender_line = "Adult male speaking voice."
    elif gender == "female":
        gender_line = "Adult female speaking voice."
    elif gender == "neutral":
        gender_line = "Natural gender-neutral speaking voice."
    else:
        gender_line = "One natural speaking voice that matches the person on camera."

    # Library blurbs can run long. Grok's prompt cap is 4096, so keep this a phrase.
    short = description.rstrip(".")[:60].strip()
    style = f" {short}." if short else ""
    return f"{gender_line}{style}".strip()


def _audio_tail(
    *,
    generate_audio: bool,
    talking: bool,
    provider: str = "",
    voice: str | None = None,
) -> str:
    """Single-track audio guidance. Stacked “include dialogue” + native audio → double voice."""
    if not generate_audio:
        return "Silent video. No speech, no music, no voiceover."
    character = _voice_character_guidance(voice) if talking else ""
    character_bit = f" {character}" if character else ""
    if talking:
        # Delivery is described positively. The old tail stacked negations ("no long
        # breath", "minimal room tone", "begin on the very first frames") which
        # suppressed the micro-pauses, breath, and pitch drift that make speech read
        # as human, and produced clipped, announcer-flat reads on every provider.
        # Tone only, no addressee: "talks to a friend on camera" pulled back toward
        # camera address on scenes where ADDRESS puts the eyeline on a listener.
        #
        # Stated as a default the scene can override, same as LOOK. Unconditional, it
        # gave a whispered secret, a festival shout, and a crying breakdown the same
        # relaxed conversational read — the scene could direct the picture but was
        # structurally unable to touch the audio.
        delivery = (
            "Delivery (default unless the scene text asks otherwise): "
            "relaxed natural speech. Not an announcer read."
        )
        if (provider or "").lower() == "gemini":
            return (
                "Audio: one voice at a time, lips match."
                f"{character_bit} {delivery} "
                "No hiss before the first word. No second narrator."
            )
        return (
            "One voice at a time, lips match."
            f"{character_bit} {delivery} "
            "No second narrator."
        )
    return (
        "Natural ambient sound that matches the action. "
        "No extra narrator voiceover unless the prompt asks for speech."
    )


def _seedance_drive_audio(speakers: list[str]) -> str:
    """Bind house TTS files. Seedance has no voice id. The MP3 is the voice.

    Official role mapping is ``@AudioN defines <who>'s voice and dialogue``.
    Quoting the line again tells the model to invent a new take.
    """
    bits: list[str] = []
    for index, speaker in enumerate(speakers, start=1):
        tag = f"@Audio{index}"
        if speaker == "face":
            bits.append(
                f"{tag} defines the voice and the spoken words of the person in @Image1. "
                f"Play {tag} as-is. Both the words and the voice come from {tag}."
            )
        else:
            bits.append(
                f"{tag} defines the voice and the spoken words of the friend, "
                "not the person in @Image1. Match that voice to how the friend looks. "
                f"Play {tag} as-is."
            )
    return (
        " ".join(bits)
        + " Play the takes in order. Do not overlap them. "
        "Mouths match those files from the first frame. Do not delay the first word. "
        "Do not invent a different voice or different words."
    )


def _quoted_dialogue_line(spoken: str) -> str:
    """Wrap the user line for native video-audio models that latch onto quoted speech."""
    text = spoken.strip()
    if not text:
        return text
    # Avoid nested quote mess if the user already quoted the whole line.
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("“") and text.endswith("”")):
        return text
    return f'"{text}"'


def raw_speech_seconds(text: str) -> float:
    """Unclamped spoken length estimate: ~2.4 words/sec + 1s pad for breath/open.

    One rate for every surface. The Talking auto length, the lip-sync length gate,
    and both clients must agree, otherwise the composer promises a length the API
    then rejects.
    """
    words = [w for w in (text or "").replace("\n", " ").split() if w]
    if not words:
        return 0.0
    return len(words) / 2.4 + 1.0


# Auto length for a Talking prompt that gives a topic instead of a line. Mid-range
# for every provider's choices and worth ~16 words at the shared rate, which is a
# sentence rather than the seven words the old scene-derived floor allowed.
TOPIC_ONLY_AUTO_SECONDS = 8


def estimate_speech_seconds(prompt: str, *, mode: str = "avatar") -> int:
    """Rough spoken length from the user prompt, clamped to a clip length.

    Talking mode uses only the line after ``says:`` when present so scene text
    does not inflate duration.
    """
    text = (prompt or "").strip()
    if not text:
        return 5
    if (mode or "").strip().lower() in {"avatar", "lipsync"}:
        spoken, _scene = split_avatar_user_prompt(text)
        if not spoken:
            # No line to measure. Falling back to the whole prompt measured the scene
            # description — text nobody speaks — so "3 things i wish i knew at 22"
            # became a 4 second clip that cut off mid sentence.
            return TOPIC_ONLY_AUTO_SECONDS
        text = spoken
    # Domains are spoken out before TTS ("example.com" becomes three words), and
    # both clients count post-expansion. Without this the composer promises a
    # longer clip than Auto actually renders.
    from app.voiceover import expand_spoken_domains

    seconds = raw_speech_seconds(expand_spoken_domains(text))
    if seconds <= 0:
        return 5
    return max(4, min(15, int(round(seconds))))


def clamp_duration_for_provider(
    seconds: int,
    *,
    provider: str,
    model_id: str | None = None,
    max_duration: int | None = None,
    resolution: str | None = None,
    has_reference_images: bool = False,
) -> int:
    """Clamp/snap auto or manual length to each provider's allowed set."""
    from app.gemini_video import normalize_veo_duration
    from app.kling_media import clamp_kling_duration

    p = (provider or "").strip().lower()
    max_d = int(max_duration or 15)
    if p == "gemini":
        # Veo rejects referenceImages at any length but 8s, and Talking always sends a
        # face plate. Decide that here too (not just at the API call) so the quote, the
        # "Clip length is exactly N seconds" prompt line, and the render all agree.
        if has_reference_images:
            return normalize_veo_duration(None, has_reference_images=True)
        hard_min, hard_max = 4, min(8, max_d)
        duration = max(hard_min, min(int(seconds), hard_max))
        return normalize_veo_duration(duration, resolution=resolution or "720p")
    if p == "seedance":
        from app.seedance_media import clamp_seedance_duration

        return min(clamp_seedance_duration(int(seconds), model=model_id), max_d)
    if p == "kling":
        duration = max(3, min(int(seconds), min(15, max_d)))
        return clamp_kling_duration(duration, model=model_id)
    # Grok 1.5: 1-15s for text, image, and reference-to-video.
    return max(1, min(int(seconds), min(15, max_d)))


def split_avatar_user_prompt(prompt: str) -> tuple[str, str]:
    """Split a Talking (avatar) user prompt into (spoken_line, scene_block).

    Preferred form (matches marketing examples + Create placeholders):
      "Kitchen island, soft light, black tee. She says: free shipping this week."

    Natural "and says LINE" / "and she says LINE" / "She says LINE" is the same
    split without the colon token. "?" and "!" count as sentence breaks, so
    "? She says no" extracts. With no speech verb there is no verbatim line. The whole text is the
    scene/topic and ``spoken_line`` is empty. Quoting the full text as dialogue
    makes the model read stage directions out loud.

    Quoting the line ends it explicitly, so anything after the closing quote goes
    back to the scene:
      'Kitchen island. She says: "free shipping." Then she lifts the box.'
    Without quotes the whole tail is the line, which is the documented UI form.
    """
    text = (prompt or "").strip()
    if not text:
        return "", ""
    match = _AVATAR_SAYS_RE.search(text)
    if not match:
        match = _SAY_EXACTLY_RE.search(text)
    if not match:
        match = _AVATAR_NATURAL_SAYS_RE.search(text)
    if not match:
        # No line was written. Drop a dangling marker so the token itself does not
        # become scene direction the provider has to interpret.
        cleaned = _AVATAR_DANGLING_SAYS_RE.sub("", text).strip()
        if _looks_like_bare_spoken_line(cleaned):
            return cleaned, ""
        return "", cleaned
    tail = match.group(1).strip()
    scene = text[: match.start()].strip()

    # A quote opening the line bounds it; the rest of the tail is stage direction.
    # Anchored on purpose: a mid-line quote is emphasis ('I call it "the fix"'),
    # not a boundary, and searching would clip the line down to that fragment.
    quoted = _QUOTED_SPAN_RE.match(tail)
    if quoted:
        spoken = quoted.group(1).strip()
        trailing = f"{tail[: quoted.start()]} {tail[quoted.end() :]}".strip(" .,;:\n\t")
    else:
        spoken = tail
        trailing = ""

    scene = _AVATAR_SCENE_LEADIN_RE.sub("", scene).strip().rstrip(".,;:")
    scene = _TRAILING_CONJUNCTION_RE.sub("", scene).strip().rstrip(".,;:")
    if trailing:
        scene = f"{scene}. {trailing}".strip(". ") if scene else trailing
    if not spoken:
        # A marker with nothing after it is not a marker. Returning the raw text
        # here put the literal token in the SCENE block sent to the provider.
        return "", scene
    if not scene:
        scene = "Natural setting, soft light, looking at camera"
    return spoken, scene


def strip_says_marker(prompt: str) -> str:
    """Drop the ``says:`` parser token, keeping the words on both sides.

    Only Talking parses this marker. Every other mode treats the prompt as plain
    text, and Lip-sync speaks it: a draft composed in Talking and carried into
    Lip-sync had TTS pronounce "says colon" out loud. The clients are supposed to
    flatten on mode switch, but all four composers have leaked it at least once,
    so the API normalises rather than trusting them.
    """
    text = (prompt or "").strip()
    if not text:
        return ""
    match = _AVATAR_SAYS_RE.search(text)
    if not match:
        return _AVATAR_DANGLING_SAYS_RE.sub("", text).strip()
    head = text[: match.start()].strip().rstrip(".,;:")
    tail = match.group(1).strip()
    if not tail:
        return head
    if not head:
        return tail
    return f"{head}. {tail}"


def _avatar_image_tag(provider: str) -> str:
    """Provider-specific label for the face ref, kept consistent in identity + speech text."""
    p = (provider or "").strip().lower()
    if p == "seedance":
        return "@Image1"
    if p == "gemini":
        return "the reference face image"
    if p == "kling":
        return "the input image"
    # xAI 1.5 binds identity only when the prompt uses this 1-based tag.
    if p == "xai":
        return "<IMAGE_1>"
    return "the first reference image"


def _avatar_identity_rules(
    *,
    image_tag: str | None = None,
    talking: bool = False,
    speaking: bool = True,
    scene: str = "",
) -> str:
    """Identity lock plus the default speaking role. Shared by Talking and Video.

    Copy the Face as photographed, including makeup and finish. Restyle belongs on
    Face edit, or in scene text that asks to change the look. Clothes still come
    from the scene when it names an outfit.

    Talking is one person saying one line. A friend in the scene is a listener.
    Treating that as a two-hander recast the Face as the friend and invented a
    new lead in the named clothes to say the line. Naming a friend on a solo
    street invented an over-the-shoulder extra. SPEAKER only mentions a listener
    when the scene has one.

    Video keeps a default, not a monopoly: an unattributed line belongs to the
    main person, and the scene can still cast a second speaker by writing them one.

    Provider-agnostic. ``image_tag`` comes from ``_avatar_image_tag`` so Seedance,
    Gemini, Kling, and xAI each get the label their own API binds identity with.
    """
    src = image_tag or "the reference image"
    speaker = avatar_speaker_rule(
        image_tag=src, scene=scene, talking=talking, speaking=speaking
    )
    return (
        f"IDENTITY (highest priority): The main person is the one in {src}. Same face every "
        f"frame, including makeup and finish. Do not restyle or de-filter unless the scene "
        f"text asks. Do not substitute a different person. Treat {src} as the identity "
        f"ground truth. Face, hair, skin, makeup only. Clothes come from the scene when it "
        f"names an outfit. If unclear who is who, they are already in frame when the shot "
        f"opens, never the one who walks up.\n"
        f"{speaker}"
    )


_CLOTHES_RE = re.compile(
    r"\b("
    r"yoga pants|leggings|jeans|shorts|skirt|dress|gown|"
    r"tank tops?|hoodie|sweater|blazer|jacket|coat|"
    r"t-shirts?|tees?|shirt|blouse|crop top|"
    # "yellow top" / "soft pink top" are outfits. Bare "on top" / "the top" are not.
    r"(?!on|the|at|to|from|table)[a-z]+\s+tops?|"
    r"swimsuit|bikini|suit|uniform|apron|robe|"
    r"dressed in|wearing|wears|outfit"
    r")\b",
    re.I,
)
def _scene_names_clothes(scene: str) -> bool:
    return bool(_CLOTHES_RE.search(scene or ""))


def _avatar_wardrobe_rule(scene: str) -> str:
    if not _scene_names_clothes(scene):
        return "Wardrobe from the selected avatar unless this scene names clothes. "
    return (
        "This scene names clothes. Dress who the sentence names. "
        "A friend's outfit stays on the friend, not the selected face. "
        "Unnamed clothes go on the selected face. Wear the clothes the scene names, "
        "not the outfit in the photo. "
        "If the scene only names some pieces, wear those and keep any other layer simple. "
        "Do not complete a matching set from the photo. "
    )


_SENTENCE_ENDINGS = (".", "!", "?", '"', "”", "'", "’")


def _scene_identity_rules(*, image_tag: str, speaking: bool = True, scene: str = "") -> str:
    """Video-mode alias for the shared identity + speaker rules.

    Kept as a separate name so the Video call sites still read as scene work, but the
    text is now identical to Talking. Two rule sets meant a prompt behaved differently
    depending on which mode it was sent through, and only one of them named a speaker.
    """
    return _avatar_identity_rules(image_tag=image_tag, speaking=speaking, scene=scene)


def _scene_speech_rules(*, driven_by_audio: bool = False) -> str:
    """Spoken-dialogue guidance for a Video scene that quotes lines.

    The plain scene audio tail only permits speech, it does not describe how to stage it.
    A quoted two-hander needs turn-taking and lip sync called out or the model narrates
    the exchange in voiceover instead of having the characters say it in the scene.

    House TTS already owns the take. Asking Seedance to speak the quotes too
    invents a second voice.
    """
    words = (
        "Voices and words come from the attached audio, in the order the files play. "
        "Mouths match those files. Do not invent a new take or different words. "
        if driven_by_audio
        else (
            "Spoken lines are said by the characters in the order written. "
            "Quoted words are spoken exactly. Do not paraphrase them. Lips match. "
            "Do not play the last line first. "
        )
    )
    return (
        f"DIALOGUE: {words}"
        "Speakers take turns. No narrator. Each speaker looks at the person they are talking "
        "to. Keep that person in the shot. If they sit beside them, turn to them instead of "
        "looking straight ahead. Do not turn to the lens unless the scene is a presenter "
        "talking to the viewer. Quoted text on a sign, poster, screen, label, caption, or "
        "logo appears on screen and is not spoken by anyone."
    )


def _expand_quoted_speech(text: str) -> str:
    """Expand domains inside quoted lines only, leaving visual direction alone.

    "example.com" must be spoken as "example dot com", but the same rewrite applied to a
    whole visual prompt ("laptop showing example.com") changes what is rendered on
    screen. Only quoted spans are ever read out loud, so only those are expanded.
    """
    from app.voiceover import expand_spoken_domains

    def _sub(match: re.Match[str]) -> str:
        return match.group(0).replace(match.group(1), expand_spoken_domains(match.group(1)))

    return _QUOTED_SPAN_RE.sub(_sub, text or "")


def _reference_manifest(
    *,
    provider: str,
    image_roles: list[str] | None,
    has_identity_image: bool = True,
) -> str:
    """Name every extra reference image so the model can act on it.

    Only the first image was ever mentioned, so a product shot or a second
    person attached as reference 2 or 3 arrived as unexplained pixels. Seedance
    addresses images as @ImageN; the others have no addressing scheme, so they
    get an ordinal instead.

    Image 1 is skipped only when it is the face, because the IDENTITY block already
    describes it. Without a face nothing described image 1 at all, so a Video clip
    carrying two product shots and no avatar shipped its first reference blind.
    """
    roles = [r for r in (image_roles or [])]
    if not roles or (has_identity_image and len(roles) < 2):
        return ""
    p = (provider or "").strip().lower()
    lines: list[str] = []
    start = 2 if has_identity_image else 1
    described = roles[1:] if has_identity_image else roles
    for index, role in enumerate(described, start=start):
        if p == "seedance":
            tag = f"@Image{index}"
        elif p == "xai":
            tag = f"<IMAGE_{index}>"
        else:
            tag = f"reference image {index}"
        if role == "continuity":
            lines.append(f"{tag}: the last frame of the previous clip, for visual continuity.")
        elif role and role != "reference":
            lines.append(f"{tag}: {role}.")
        else:
            lines.append(
                f"{tag}: a supporting reference. Use what it shows (person, product, or place) "
                "where the scene text calls for it."
            )
    return "REFERENCES:\n" + "\n".join(lines)


def _orientation_phrase(aspect_ratio: str | None) -> str:
    """Describe the frame the way the request set it, not a hardcoded assumption."""
    ratio = (aspect_ratio or "").strip()
    if ratio in {"1:1"}:
        return "square"
    if ratio in {"16:9", "4:3"}:
        return "horizontal"
    # 9:16, 3:4 (mapped from 4:5), and anything unknown default to the Play preset.
    return "vertical"


def _has_quoted_speech(text: str) -> bool:
    """True when the scene text quotes at least one spoken line.

    Double quotes only. Counting apostrophes made any two contractions look like
    dialogue ("she's carrying a bag, it's raining"), which staged a speaking scene
    for prompts with no spoken line in them at all.
    """
    return bool(re.search(r'["“]([^"“”]{2,})["”]', text or ""))


# Verbs that stage speech without quoting it. Deliberately narrow: these all take a
# speaker, so they imply someone on camera talking rather than describing a sound.
_SPEECH_INTENT_RE = re.compile(
    # No "pitch": "pitch black" / "a pitch deck" are scenery, not speech.
    r"\b(say|says|saying|talk|talks|talking|speak|speaks|speaking|tell|tells|telling"
    r"|ask|asks|asking|repl(?:y|ies|ying)|explains?|announces?|greets?"
    r"|whispers?|shouts?)\b",
    re.IGNORECASE,
)


# "a sign that says OPEN" is signage, not dialogue. Written surfaces take "says"
# without anyone speaking, and staging dialogue for them risks the sign being read
# aloud. Checked on the words just before the verb.
_WRITTEN_SURFACE_RE = re.compile(
    r"\b(sign|signage|poster|banner|billboard|label|sticker|screen|display|caption"
    r"|subtitle|logo|menu|placard|note|card|shirt|tattoo|headline|title)s?\b"
    r"(?:\s+\w+){0,3}?\s+(?:say|says|saying|reads?|reading)\b",
    re.IGNORECASE,
)


def _implies_speech(text: str) -> bool:
    """True when the scene asks for spoken words, quoted or not.

    Quotes alone missed the commonest form users actually type: "talk about the new
    drop" has no quotation marks, so the dialogue rules never fired and nothing named
    a speaker. With a second person in frame the model then picked one, and it was
    routinely the wrong one.
    """
    body = (text or "").strip()
    if not body:
        return False
    if _has_quoted_speech(body):
        return True
    # Strip signage phrasing before looking for speech verbs, so "a sign that says
    # OPEN" does not stage a conversation, while "a sign that says OPEN, she says
    # hello" still does.
    return bool(_SPEECH_INTENT_RE.search(_WRITTEN_SURFACE_RE.sub(" ", body)))


def _clip_focus_rules() -> str:
    """House default for every clip: sharp, not cinematic bokeh.

    Reference-to-video inherits the Face plate's optics, and Grok also invents a
    portrait-lens blur when the prompt is silent. Scene text can still ask for
    bokeh. Phrased as a default so that request can win.
    """
    return (
        "FOCUS (default unless the scene asks for bokeh): Deep focus. "
        "Face, people, and background all sharp. Not a cinematic blurred background."
    )


def _avatar_look_rules() -> str:
    """Product default for every Talking clip: ultra-real human, same Face as the photo.

    Makeup, filters, and finish stay on the Face. Change those in Face edit, or name
    the change in the scene text. Place, wardrobe, voice, and length still come only
    from the request.
    """
    # Stated as a default rather than a ban: the flat "not animation, CGI, cartoon"
    # rule made a stylized talking head unreachable at any prompt, since the scene
    # text could never win against it.
    #
    # Do not "naturalize" the Face. Photoreal used to strip beauty filters and
    # redraw a different skin. Copy the photo; put that same person in live action.
    #
    # Do not say "on camera" here. That was meant as live-action, but models treat
    # it as look-at-lens and it overrides ADDRESS on any conversation scene.
    return (
        "LOOK (default unless the scene text asks otherwise): Ultra-real human. "
        "Photoreal, not CGI. "
        f"{_clip_focus_rules()}"
    )


def _improvised_word_budget(seconds: int | None) -> int | None:
    """Words that fit the clip, at the one speech rate every surface uses.

    Mirrors ``raw_speech_seconds`` (2.4 w/s after a 1s open). Without a budget the
    model writes to the topic instead of to the clip, so "3 things I wish I knew"
    lands in a 4 second render and gets cut mid-sentence.
    """
    if not seconds or seconds <= 0:
        return None
    return max(4, int((seconds - 1) * 2.4))


def _avatar_improvise_rules(seconds: int | None = None) -> str:
    """Constraints for the branch where the model writes the words, not the user.

    The pre-flight in ``play_assist`` drafts the line where the user can read and
    edit it. This is the fallback for anything that reaches generate without one,
    and it carries the same contract: never invent offers, prices, or facts the
    request did not make.
    """
    budget = _improvised_word_budget(seconds)
    length = (
        f"Say roughly {budget} words, so the line finishes inside the clip. "
        if budget
        else "Say one short sentence that finishes inside the clip. "
    )
    return (
        "IMPROVISED LINE (the request gave a topic, not exact words): "
        f"{length}"
        "Open on the strongest words rather than a greeting or a wind-up. "
        "Stay on the topic in the scene text. Do not invent offers, prices, discounts, "
        "statistics, or product claims the request did not make. "
        "Hashtags, @handles, and emoji are written marks, not words to pronounce."
    )


_PICTURE_ONLY_PLATE = (
    "PICTURE ONLY: Alive, small natural motion, not frozen. Mouths at rest. "
    "Do not speak. Do not mouth words. Speech is added later."
)


def _avatar_scene_and_speech(
    *,
    scene_block: str,
    dialogue: str,
    audio: str,
    image_tag: str | None = None,
    extra_speech: str = "",
    seconds: int | None = None,
    speaking: bool = True,
    driven_by_audio: bool = False,
) -> str:
    scene = (scene_block or "").strip() or "Natural setting, soft light, looking at camera"
    src = image_tag or "the reference image"
    # ADDRESS is the house rule, but it used to sit after the line. Grok then
    # staged the line to camera and only found the friend mid-take. Name the
    # target next to the words when the scene already has a listener.
    # ADDRESS already owns eyeline. One short line next to the words so Grok
    # does not stage the line to camera first.
    has_listener = _scene_has_addressee(scene_block)
    if not speaking:
        look = "Look at that person. Keep them in the shot.\n" if has_listener else ""
        speech = (
            f"The SAME person from {src} stays in this scene the whole clip.\n"
            f"{look}"
            f"{_PICTURE_ONLY_PLATE}"
        )
    else:
        to_listener = (
            (
                "Address that person. Keep them in the shot.\n"
                if driven_by_audio
                else "Speak this line to that person. Keep them in the shot.\n"
            )
            if has_listener
            else ""
        )
        if driven_by_audio:
            speech = (
                f"The SAME person from {src} stays in this scene the whole clip.\n"
                f"{to_listener}"
                "Mouths follow the attached audio from the first frame. "
                "Do not invent a new take, a different voice, or different words."
            )
        elif dialogue:
            speech = (
                f"The SAME person from {src} speaks this line, starting immediately: {dialogue}\n"
                f"{to_listener}"
                "Lips locked to the words. Speak only that line. Stage notes are performed, never pronounced."
            )
        else:
            speech = (
                f"The SAME person from {src} starts talking about that topic immediately.\n"
                f"{to_listener}"
                "Speak one natural line in your own words. Never read the scene description, "
                "wardrobe, or camera notes out loud. Lips locked to the words.\n"
                f"{_avatar_improvise_rules(seconds)}"
            )
    cast = avatar_cast_rule(scene_block)
    cast_block = f"{cast}\n\n" if cast else ""
    body = (
        f"{_avatar_look_rules()}\n\n"
        f"{avatar_frame_rule()}\n\n"
        # ADDRESS used to sit after the line. Grok staged a lens-facing talking
        # head first, then never found the friend. Name the target before SCENE.
        f"{_avatar_address_rule(scene_block)}\n\n"
        f"{cast_block}"
        # "Place and wardrobe only" told the model to ignore the action and camera
        # work users write in the scene field. Identity is the only thing the scene
        # text may not change.
        f"SCENE (follow all of it. "
        f"{_avatar_wardrobe_rule(scene)}"
        f"It never changes who the person is):\n{scene}\n\n"
        f"{speech}"
    )
    if extra_speech:
        body = f"{body}\n{extra_speech}"
    return f"{body}\n\n{audio}".strip()


def _avatar_continue_bridge(*, provider: str) -> str:
    """Provider-specific continuity instruction before the scene + speech block."""
    p = (provider or "").strip().lower()
    if p == "seedance":
        return (
            "Continue the motion and story from @Video1. "
            "Keep visual continuity with the prior shot. "
            "Match lighting, subject, and camera language to the reference video."
        )
    if p == "xai":
        return "Continue this video seamlessly. Keep the same subject, lighting, and camera language."
    # Veo / Kling image-to-video from last frame.
    return (
        "Continue seamlessly from this opening frame (the last moment of the prior clip). "
        "Keep the same subject, lighting, wardrobe, and camera language. "
        "Do not jump to a new location unless the prompt asks for it."
    )


def _build_video_prompt(
    *,
    mode: str,
    provider: str,
    prompt: str,
    has_identity_image: bool,
    has_continue: bool,
    generate_audio: bool = True,
    duration_seconds: int | None = None,
    voice: str | None = None,
    aspect_ratio: str | None = None,
    image_roles: list[str] | None = None,
    voice_audio_speakers: list[str] | None = None,
) -> tuple[str, str | None]:
    from app.voiceover import expand_spoken_domains

    raw_prompt = prompt.strip()
    talking_like = mode in ("avatar", "lipsync")
    if not talking_like:
        from app.routers.play_scene_dialogue import normalize_scene_dialogue_order

        raw_prompt = normalize_scene_dialogue_order(raw_prompt)
    note: str | None = None
    speakers = [s for s in (voice_audio_speakers or []) if s]
    driven_by_audio = bool(speakers) and (provider or "").strip().lower() == "seedance"
    if driven_by_audio:
        audio = _seedance_drive_audio(speakers)
    else:
        audio = _audio_tail(
            generate_audio=generate_audio,
            talking=talking_like,
            provider=provider,
            voice=voice if talking_like else None,
        )
    # 1.5 binds a preset voice only when the prompt names <AUDIO_0>. Talking
    # always speaks; Video only when the scene quotes a line. The API field is
    # still sent whenever a voice is on the request (see start_xai_video).
    if (
        generate_audio
        and (provider or "").strip().lower() == "xai"
        and (voice or "").strip()
        and (mode == "avatar" or _has_quoted_speech(raw_prompt))
    ):
        audio = f"{audio} Spoken words use the voice from <AUDIO_0>."
    dur = int(duration_seconds) if duration_seconds and duration_seconds > 0 else None

    # Talking: separate spoken line from scene when the user used "says:".
    # Domains are expanded only in text that is actually spoken — never across the
    # whole prompt, which rewrote visual direction and on-screen text too.
    if talking_like:
        spoken_line, scene_block = split_avatar_user_prompt(raw_prompt)
        spoken_line = expand_spoken_domains(spoken_line)
    else:
        spoken_line = scene_block = _expand_quoted_speech(raw_prompt)
    scene_block = ensure_listener_look(scene_block)
    if talking_like and not has_continue:
        scene_block = ensure_talking_frame(scene_block)
    dialogue = _quoted_dialogue_line(spoken_line)

    # A written line longer than the clip used to be clamped in silence, so the render
    # simply stopped mid-word and looked broken. The improvised branch has a word
    # budget; a user-written line had nothing. Say what will happen and what to cut.
    # Advisory only: never trim their copy for them.
    length_note: str | None = None
    if mode in ("avatar", "lipsync") and spoken_line and dur:
        needed = raw_speech_seconds(spoken_line)
        if needed > dur + 0.5:
            fits = _improvised_word_budget(dur)
            length_note = (
                f"This line runs about {int(round(needed))}s but the clip is {dur}s, "
                f"so it will cut off. Trim to about {fits} words."
            )

    if has_continue:
        note = length_note or "Continuing from your last clip."
        # Talking continue must split scene vs line the same way as a fresh clip.
        # Dumping raw "says:" made models read stage directions or drop identity.
        if mode in ("avatar", "lipsync"):
            image_tag = (
                _avatar_image_tag(provider) if has_identity_image else "the person on camera"
            )
            scene_speech = _avatar_scene_and_speech(
                scene_block=scene_block,
                dialogue=dialogue,
                audio=audio,
                image_tag=image_tag,
                seconds=dur,
                speaking=generate_audio,
                driven_by_audio=driven_by_audio,
            )
            parts: list[str] = []
            if has_identity_image:
                parts.append(
                    _avatar_identity_rules(
                        image_tag=_avatar_image_tag(provider),
                        talking=True,
                        speaking=generate_audio,
                        scene=scene_block,
                    )
                )
                if (provider or "").strip().lower() == "seedance":
                    parts.append("Do not treat @Image1 as the first frame.")
            parts.append(_avatar_continue_bridge(provider=provider))
            parts.append(scene_speech)
            return "\n\n".join(parts), note

        # Plain video continue: keep the full prompt as scene direction.
        if provider == "seedance":
            video_prompt = (
                "Continue the motion and story from @Video1. "
                "Keep visual continuity with the prior shot.\n\n"
                f"{scene_block}\n\n"
                "Match lighting, subject, and camera language to the reference video."
            )
            if has_identity_image:
                video_prompt = (
                    "Use @Image1 as person identity when present (likeness only, not the opening frame). "
                    + video_prompt
                )
        elif provider == "xai":
            video_prompt = (
                "Continue this video seamlessly. Keep the same subject, lighting, and camera language.\n\n"
                f"{scene_block}"
            )
        else:
            video_prompt = (
                f"{_avatar_continue_bridge(provider=provider)}\n\n{scene_block}"
            )
        # An attached face was named only on the Seedance branch, so extending a
        # Video-mode clip on Veo / Kling / Grok shipped the face with nothing
        # telling the model whose likeness it was — exactly when a new person
        # gets invented.
        if has_identity_image and provider != "seedance":
            video_prompt = (
                f"{_scene_identity_rules(image_tag=_avatar_image_tag(provider), speaking=generate_audio, scene=scene_block)}\n\n{video_prompt}"
            )
        return f"{_clip_focus_rules()}\n\n{video_prompt} {audio}".strip(), note

    if talking_like and has_identity_image:
        # A line that will not fit is more urgent than the identity reminder.
        note = length_note or (
            "Face is identity only. Location and outfit come from your scene text, "
            "not the photo room."
        )
        image_tag = _avatar_image_tag(provider)
        scene_speech = _avatar_scene_and_speech(
            scene_block=scene_block,
            dialogue=dialogue,
            audio=audio,
            image_tag=image_tag,
            seconds=dur,
            speaking=generate_audio,
            driven_by_audio=driven_by_audio,
        )
        ident = _avatar_identity_rules(
            image_tag=image_tag, talking=True, speaking=generate_audio, scene=scene_block
        )
        if provider == "seedance":
            # reference-to-video: @Image1 is identity, never a studio first frame.
            # Audio tail already forbids a second narrator; only pace + ad-lib note here.
            # Duration comes from the request (manual picker or Auto from spoken length).
            # House TTS already owns the take. "Pace the full line" made Seedance
            # invent a new read from the quoted text.
            if generate_audio and driven_by_audio:
                pace = (
                    f"Clip length is exactly {dur} seconds. Mouths follow the attached audio "
                    "for that length.\n\n"
                    if dur
                    else "Mouths follow the attached audio at its own pace.\n\n"
                )
                adlib = "Do not invent words that are not in the attached audio.\n\n"
            elif generate_audio:
                pace = (
                    f"Clip length is exactly {dur} seconds. Pace the full line to that length.\n\n"
                    if dur
                    else "Speak at a natural conversational pace.\n\n"
                )
                adlib = "No mumbled ad-libs that fight the line.\n\n"
            else:
                pace = ""
                adlib = ""
            video_prompt = (
                f"{ident}\n"
                "Do not treat @Image1 as the first frame.\n\n"
                f"{pace}"
                f"{adlib}"
                f"{scene_speech}"
            )
        elif provider == "gemini":
            mouth = (
                "No synthetic intro sounds, hiss, or dead air before the words. "
                "Mouth movement matches the line from the first syllable.\n\n"
                if generate_audio
                else ""
            )
            video_prompt = (
                f"{ident}\n"
                f"Short {_orientation_phrase(aspect_ratio)} clip.\n\n"
                f"{mouth}"
                f"{scene_speech}"
            )
        elif provider == "kling":
            # Kling image2video always starts on the input image (see kling_media),
            # so ask for a move off the face plate instead of pretending otherwise.
            video_prompt = (
                f"{ident}\n"
                "The input image is this person and the opening frame. Hold it briefly, then move "
                "the camera and the person into the scene below. Keep the same face throughout "
                "(do not replace them with someone else).\n\n"
                f"{scene_speech}"
            )
        else:
            # Grok path: reference image carries the person; prompt locks likeness hard.
            video_prompt = f"{ident}\n\n{scene_speech}"
        return video_prompt, note

    if talking_like:
        note = length_note or "No face selected. Generating a talking-head style clip from text only."
        speaks = (
            _PICTURE_ONLY_PLATE
            if not generate_audio
            else (
                f"The person speaks immediately: {dialogue}"
                if dialogue
                else (
                    "The person starts talking about that topic immediately, in their own "
                    "words. Never read the scene description out loud. "
                    f"{_avatar_improvise_rules(dur)}"
                )
            )
        )
        look = _avatar_look_rules()
        frame = avatar_frame_rule()
        address = _avatar_address_rule(scene_block)
        cast = avatar_cast_rule(scene_block)
        cast_bit = f" {cast}" if cast else ""
        if (provider or "").lower() == "gemini":
            return (
                f"{look} {frame} Photoreal video. Scene: {scene_block}. {speaks} {address}{cast_bit} {audio}",
                note,
            )
        return (
            f"{look} {frame} Scene and wardrobe: {scene_block}. {speaks} "
            f"Photoreal video. {address}{cast_bit} {audio}",
            note,
        )

    # Video / still-adjacent scene generation (not lipsync; lipsync never hits this helper).
    note = "Text-to-video scene." if not has_identity_image else "Video with references."
    # House TTS already built `audio` as the @AudioN bind. A second ambient tail
    # told Seedance to invent native speech on top of those files.
    if driven_by_audio:
        scene_audio = audio
    else:
        scene_audio = _audio_tail(
            generate_audio=generate_audio, talking=False, provider=provider, voice=None
        )
    if (
        not driven_by_audio
        and generate_audio
        and (provider or "").strip().lower() == "xai"
        and (voice or "").strip()
        and _implies_speech(scene_block)
    ):
        from app.routers.play_scene_dialogue import extract_scene_dialogue

        has_other = any(row.speaker == "other" for row in extract_scene_dialogue(scene_block))
        if has_other:
            scene_audio = (
                f"{scene_audio} The person in the face photo uses the voice from <AUDIO_0>. "
                "The other speaker uses a different voice that matches how they look."
            )
        else:
            scene_audio = f"{scene_audio} Spoken words use the voice from <AUDIO_0>."
    parts: list[str] = [_clip_focus_rules()]
    if has_identity_image:
        parts.append(
            _scene_identity_rules(
                image_tag=_avatar_image_tag(provider),
                speaking=generate_audio,
                scene=scene_block,
            )
        )
        parts.append(_avatar_wardrobe_rule(scene_block).strip())
        note = "Scene with your face. Other people in the text stay separate characters."
    manifest = _reference_manifest(
        provider=provider,
        image_roles=image_roles,
        has_identity_image=has_identity_image,
    )
    if manifest:
        parts.append(manifest)
    # scene_block has domains expanded inside quoted lines only, so a URL the user
    # wants rendered on screen stays literal while a spoken one stays speakable.
    # Only close the sentence when the text does not already end in punctuation or a
    # quote, so a scene ending on a quoted line does not pick up a stray full stop.
    scene_text = scene_block.rstrip()
    parts.append(scene_text if scene_text.endswith(_SENTENCE_ENDINGS) else f"{scene_text}.")
    if generate_audio and _implies_speech(scene_block):
        parts.append(_scene_speech_rules(driven_by_audio=driven_by_audio))
    elif _implies_speech(scene_block):
        parts.append(_PICTURE_ONLY_PLATE)
    parts.append(scene_audio)
    return ("\n\n".join(parts), note)
