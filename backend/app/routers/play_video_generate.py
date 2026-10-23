"""Play video/avatar generation entrypoint."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.kling_media import kling_configured
from app.models import User, VideoProject
from app.routers.play_helpers import map_generation
from app.routers.play_video_helpers import (
    _build_video_prompt,
    _resolve_reference_materials,
    clamp_duration_for_provider,
    estimate_speech_seconds,
    normalize_play_resolution,
)
from app.routers.play_video_start import _start_one_video
from app.schemas.play import PlayGenerateRequest, PlayGenerateResponse, PlayGenerationDto

async def generate_play_video(
    *,
    session: AsyncSession,
    settings: Settings,
    user: User,
    body: PlayGenerateRequest,
    project: VideoProject,
    play_model,
    prompt: str,
    aspect_ratio: str,
    picture_only: bool = False,
    voice_audio_urls: list[str] | None = None,
    voice_audio_speakers: list[str] | None = None,
    extra_usage_event_ids: list[str] | None = None,
) -> PlayGenerateResponse:
    provider = (play_model.provider or "xai").strip().lower()
    import logging

    _log = logging.getLogger("studio.play")
    if provider == "gemini":
        if not settings.gemini_api_key:
            _log.warning("play generate blocked: gemini_api_key missing model=%s", play_model.id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini API key is not configured",
            )
    elif provider == "seedance":
        if not settings.seedance_api_key:
            _log.warning("play generate blocked: seedance_api_key missing model=%s", play_model.id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Seedance API key is not configured",
            )
    elif provider == "kling":
        if not kling_configured(settings):
            _log.warning("play generate blocked: kling keys missing model=%s", play_model.id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Kling API key is not configured",
            )
    elif not settings.xai_api_key:
        _log.warning("play generate blocked: xai_api_key missing model=%s", play_model.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="xAI API key is not configured",
        )

    batch_count = int(body.count or 1)
    if provider != "seedance":
        batch_count = 1
    batch_count = max(1, min(batch_count, 10))

    # Veo Lite (and any future engine without identity refs) reject face plates
    # with a 400 that used to surface as a confusing "re-save the face" message.
    if (
        body.mode == "video"
        and body.face_asset_id is not None
        and not getattr(play_model, "supports_face_reference", True)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{play_model.label} cannot use a face in Video mode. "
                "Clear the avatar, or pick a model that supports faces (for example Veo 3.1)."
            ),
        )

    materials = await _resolve_reference_materials(
        session=session,
        user=user,
        body=body,
        provider=provider,
        settings=settings,
        model_id=play_model.provider_model or play_model.id,
    )
    image_urls = list(materials.image_urls)
    image_roles = list(materials.image_roles)
    video_urls = materials.video_urls
    house_audio = [u for u in (voice_audio_urls or []) if u and str(u).strip()]
    speakers = list(voice_audio_speakers or [])
    if house_audio and not speakers:
        speakers = ["face"] * len(house_audio)
    audio_urls = [*house_audio, *materials.audio_urls]
    ref_ids = materials.ref_ids
    poster_url = materials.poster_url

    has_face_image = bool(body.mode in ("avatar", "video") and body.face_asset_id)
    if (
        body.mode == "avatar"
        and has_face_image
        and image_urls
        and body.continue_from_asset_id is None
        and not str(image_urls[0]).startswith("data:")
    ):
        from app.routers.play_clip_still import generate_talking_clip_still
        from app.routers.play_prompt_cast import ensure_listener_look, ensure_talking_frame
        from app.routers.play_video_helpers import split_avatar_user_prompt

        _spoken, scene_for_still = split_avatar_user_prompt(prompt)
        scene_for_still = ensure_talking_frame(ensure_listener_look(scene_for_still))
        still_url = await generate_talking_clip_still(
            face_image_url=image_urls[0],
            scene=scene_for_still,
            aspect_ratio=aspect_ratio,
            settings=settings,
        )
        if still_url:
            image_urls = [image_urls[0], still_url, *image_urls[1:]]
            image_roles = [
                *(image_roles[:1] or ["identity"]),
                "opening shot. Match place, clothes, pose, and camera to this still",
                *image_roles[1:],
            ]
    if has_face_image and not image_urls:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Could not load your face image for this clip. "
                "Open Faces, re-select the face, or re-upload it and try again."
            ),
        )
    generate_audio = True if body.generate_audio is None else bool(body.generate_audio)
    # House TTS is the soundtrack. Mute only when the user asked for silence and
    # there is no spoken file to drive the mouth.
    if picture_only and not house_audio:
        generate_audio = False

    max_d = play_model.max_duration_seconds or 15
    resolution = normalize_play_resolution(
        body.resolution, provider=provider, model_id=play_model.provider_model
    )
    # null duration_seconds = Auto: size the clip to the spoken line (Talking)
    # or a sensible default for plain video.
    if body.duration_seconds is not None:
        requested = int(body.duration_seconds)
        duration_source = "manual"
    elif body.mode == "avatar":
        requested = estimate_speech_seconds(prompt, mode="avatar")
        duration_source = "auto_speech"
    else:
        requested = min(8 if provider == "gemini" else 10, max_d)
        duration_source = "default"
    duration = clamp_duration_for_provider(
        requested,
        provider=provider,
        model_id=play_model.provider_model,
        max_duration=max_d,
        resolution=resolution,
        has_reference_images=bool(image_urls),
    )
    # Veo only renders reference-image clips at 8s. Say so rather than silently
    # overriding a length the user picked by hand.
    forced_length = duration != requested and provider == "gemini" and bool(image_urls)

    video_prompt, note = _build_video_prompt(
        mode=body.mode,
        provider=provider,
        prompt=prompt,
        has_identity_image=bool(image_urls) and (has_face_image or bool(body.continue_from_asset_id)),
        has_continue=body.continue_from_asset_id is not None,
        generate_audio=generate_audio,
        duration_seconds=duration,
        # Talking clips: steer native model audio (gender/style). Lip-sync uses TTS separately.
        voice=body.voice,
        aspect_ratio=aspect_ratio,
        image_roles=image_roles,
        voice_audio_speakers=speakers if house_audio else None,
    )
    # Stronger note when multi-ref without continue
    if image_urls or video_urls or audio_urls:
        if body.continue_from_asset_id:
            pass
        elif body.mode == "avatar" and body.face_asset_id:
            note = note or "Face plus extra refs."
        else:
            note = "Using your reference materials."
    # generate_audio already resolved above for prompt building
    return_last_frame = bool(body.return_last_frame) if body.return_last_frame is not None else False
    print(
        f"play_video_filters provider={provider} model={play_model.id} "
        f"duration_source={duration_source} requested_duration={requested} "
        f"effective_duration={duration} resolution={resolution} aspect={aspect_ratio} "
        f"audio={generate_audio} batch={batch_count}",
        flush=True,
    )
    if forced_length:
        length_note = f"This model renders clips with a face reference at {duration}s."
        note = f"{note} {length_note}".strip() if note else length_note
    elif duration_source == "auto_speech":
        auto_note = f"Length auto ~{duration}s from spoken line."
        note = f"{note} {auto_note}".strip() if note else auto_note
    for material_note in materials.notes:
        note = f"{note} {material_note}".strip() if note else material_note

    # Grok 1.5: xAI preset voice ids only. ElevenLabs stock and clones must
    # never land in reference_audios. Video substitutes ara/rex from gender.
    reference_audio_voice_ids: list[str] = []
    if provider == "xai" and generate_audio and (body.voice or "").strip():
        from app.routers.play_voices import grok_safe_voice_id, resolve_tts_voice

        resolved = await resolve_tts_voice(
            session=session,
            workspace_id=body.workspace_id,
            voice=body.voice,
            settings=settings,
        )
        reference_audio_voice_ids = [grok_safe_voice_id(resolved, settings)]

    generations: list[PlayGenerationDto] = []
    first_error: Exception | None = None

    for i in range(batch_count):
        try:
            asset = await _start_one_video(
                session=session,
                settings=settings,
                user=user,
                body=body,
                project=project,
                play_model=play_model,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                provider=provider,
                image_urls=image_urls,
                video_urls=video_urls,
                audio_urls=audio_urls,
                ref_ids=ref_ids,
                poster_url=poster_url,
                video_prompt=video_prompt,
                duration=duration,
                resolution=resolution,
                generate_audio=generate_audio,
                return_last_frame=return_last_frame,
                continue_still=materials.continue_still,
                reference_audio_voice_ids=reference_audio_voice_ids,
                house_audio_count=len(house_audio),
                extra_usage_event_ids=extra_usage_event_ids,
                batch_index=i,
                batch_count=batch_count,
            )
            generations.append(map_generation(asset, settings))
        except Exception as exc:
            if not generations:
                raise
            first_error = exc
            break

    if not generations:
        if first_error:
            raise first_error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not start video generation",
        )

    msg = note or "Video is processing. We poll until ready."
    if batch_count > 1:
        msg = f"Started {len(generations)} variant{'s' if len(generations) != 1 else ''}. {msg}"
    if first_error and generations:
        msg = f"{msg} One or more variants failed to start."

    return PlayGenerateResponse(
        generation=generations[0],
        generations=generations,
        message=msg,
    )
