"""Start a single Play video generation (provider call + asset row)."""
from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import User, VideoAsset, VideoProject
from app.play_billing import release_if_unsettled
from app.provider_errors import http_provider_exception, public_error_message
from app.routers.play_helpers import next_scene
from app.routers.video_helpers import add_generation_cost
from app.schemas.play import PlayGenerateRequest
from app.seedance_media import SeedanceMediaError, start_seedance_video
from app.workspace_access import reserve_usage_committed


async def _start_one_video(
    *,
    session: AsyncSession,
    settings: Settings,
    user: User,
    body: PlayGenerateRequest,
    project: VideoProject,
    play_model,
    prompt: str,
    aspect_ratio: str,
    provider: str,
    image_urls: list[str],
    video_urls: list[str],
    audio_urls: list[str],
    ref_ids: list[str],
    poster_url: str | None,
    video_prompt: str,
    duration: int,
    resolution: str,
    generate_audio: bool,
    return_last_frame: bool,
    continue_still: str | None,
    reference_audio_voice_ids: list[str] | None = None,
    house_audio_count: int = 0,
    extra_usage_event_ids: list[str] | None = None,
    batch_index: int,
    batch_count: int,
) -> VideoAsset:
    from app.play_pricing import compute_play_quote

    if (provider or "").strip().lower() != "seedance":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Clip is Seedance only.",
        )
    # Seedance extend uses video_urls. First-frame continue_still was for retired engines.
    _ = continue_still
    _ = reference_audio_voice_ids

    ref_imgs = len([u for u in image_urls if u])
    # Face is the first image whenever one is attached; don't double-charge it as a "ref extra".
    if body.face_asset_id and ref_imgs > 0:
        ref_imgs = max(0, ref_imgs - 1)
    # Quote from the request, not the picture-pass mute. generate_audio=False here
    # is the provider flag; the 0.9 mute discount is only for user-requested silence.
    quote_audio = True if body.generate_audio is None else bool(body.generate_audio)
    quote = compute_play_quote(
        mode=body.mode if body.mode in ("video", "avatar") else "video",
        model_id=play_model.id,
        duration_seconds=duration,
        resolution=resolution,
        count=1,  # each batch item reserved separately
        generate_audio=quote_audio,
        return_last_frame=return_last_frame,
        ref_image_count=ref_imgs,
        ref_video_count=len([u for u in video_urls if u]),
        ref_audio_count=max(0, len([u for u in audio_urls if u]) - max(0, int(house_audio_count))),
        continue_from=body.continue_from_asset_id is not None,
    )
    tokens = max(1, int(quote.per_item))
    reservation = await reserve_usage_committed(
        session,
        body.workspace_id,
        user.id,
        quote.meter,
        tokens,
        {
            "operation": "play_video",
            "model_id": play_model.id,
            "token_cost": tokens,
            "batch_index": batch_index,
            "quote": quote.as_dict(),
        },
    )
    reservation_id = reservation.id

    has_refs = bool(image_urls or video_urls or audio_urls)
    mode_label = (
        "continue_video"
        if body.continue_from_asset_id
        else (
            "reference_to_video"
            if has_refs
            else "text_to_video"
        )
    )

    try:
        scene = await next_scene(
            session,
            project,
            prompt if batch_count == 1 else f"{prompt} (variant {batch_index + 1})",
            spoken_text=prompt if body.mode == "avatar" else None,
        )
    except BaseException:
        # The reservation is already committed and there is no asset yet, so the
        # provider handler below cannot clean up after a failure here.
        await release_if_unsettled(session, type(reservation), reservation_id)
        raise

    asset = VideoAsset(
        workspace_id=body.workspace_id,
        video_project_id=project.id,
        video_scene_id=scene.id,
        asset_type="video",
        source=provider,
        status="processing",
        prompt=prompt,
        provider=provider,
        provider_model=play_model.provider_model,
        asset_metadata={
            "play": True,
            "play_mode": body.mode,
            "play_platform": body.platform,
            "model_id": play_model.id,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "duration_seconds": duration,
            "generate_audio": generate_audio,
            "return_last_frame": return_last_frame,
            "mode": mode_label,
            "face_asset_id": str(body.face_asset_id) if body.face_asset_id else None,
            "voice": body.voice or None,
            "reference_audio_voice_ids": list(reference_audio_voice_ids or []),
            "reference_asset_ids": ref_ids,
            "continue_from_asset_id": (
                str(body.continue_from_asset_id) if body.continue_from_asset_id else None
            ),
            "batch_index": batch_index,
            "batch_count": batch_count,
            "poster_url": poster_url,
            "face_image_url": poster_url,
            # What Seedance / the provider actually received. Hidden from the DTO.
            "provider_prompt": video_prompt,
            # Link reservation immediately so failed polls can always refund.
            # Clone TTS ids must be here before this commit, or a crash holds
            # voiceover seconds until the 45 min stale sweep.
            "usage_event_ids": [
                str(reservation_id),
                *[
                    sid
                    for sid in (extra_usage_event_ids or [])
                    if sid and sid != str(reservation_id)
                ],
            ],
            "image_ref_kind": (
                "data_url"
                if image_urls and image_urls[0].startswith("data:")
                else ("https" if image_urls else None)
            ),
            "identity_ref_count": len([u for u in image_urls if u]),
            "identity_inline": bool(image_urls and image_urls[0].startswith("data:")),
        },
    )
    session.add(asset)
    try:
        await session.flush()
    except BaseException:
        await release_if_unsettled(session, type(reservation), reservation_id)
        raise

    # A face plate is a likeness reference, never the literal opening frame — that is
    # true in Video mode too, where the face rides along with a multi-person scene.
    # Attached scene stills (no face) keep their existing first-frame behaviour.
    is_avatar_identity = bool(image_urls) and (
        body.mode == "avatar" or body.face_asset_id is not None
    )

    request_id: str | None = None
    result_model = play_model.provider_model
    cost_ticks: int | None = None
    try:
        # Avatar face → reference-to-video only (never image-to-video first frame).
        # Scene video with one still may use image-to-video as true first frame.
        if (
            video_urls
            or audio_urls
            or body.continue_from_asset_id
            or is_avatar_identity
            or len(image_urls) > 1
        ):
            gen_type = "reference-to-video"
        elif image_urls and body.mode == "video":
            gen_type = "image-to-video"
        elif image_urls:
            gen_type = "reference-to-video"
        else:
            gen_type = "text-to-video"
        s_result = await start_seedance_video(
            prompt=video_prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            settings=settings,
            model=play_model.provider_model,
            generation_type=gen_type,  # type: ignore[arg-type]
            image_urls=image_urls or None,
            video_urls=video_urls or None,
            audio_urls=audio_urls or None,
            generate_audio=generate_audio,
            return_last_frame=return_last_frame,
            identity_only=is_avatar_identity,
        )
        request_id = s_result.task_id
        result_model = s_result.model or play_model.provider_model
        if s_result.credits is not None:
            asset.asset_metadata = {
                **dict(asset.asset_metadata or {}),
                "seedance_credits": s_result.credits,
            }
    except SeedanceMediaError as exc:
        asset.status = "failed"
        asset.error_message = public_error_message(exc, kind="media")
        # Keep the provider's own words. The client message is masked, so without
        # this a start failure is undiagnosable after the fact.
        asset.asset_metadata = {
            **dict(asset.asset_metadata or {}),
            "provider_error_raw": str(exc)[:500],
            "provider_error_type": type(exc).__name__,
            "provider_error_stage": "start",
        }
        await session.commit()
        await release_if_unsettled(session, type(reservation), reservation_id)
        raise http_provider_exception(exc, kind="media") from exc
    except Exception:
        # The clauses above name only provider errors. A media, network, or DB
        # failure here would otherwise leave the committed reservation behind,
        # billing a clip that never started.
        await release_if_unsettled(session, type(reservation), reservation_id)
        raise

    asset.provider_request_id = request_id
    asset.provider_model = result_model
    asset.cost_usd_ticks = cost_ticks
    add_generation_cost(
        session,
        workspace_id=body.workspace_id,
        user_id=user.id,
        feature="play_video_start",
        provider_model=result_model,
        provider_request_id=request_id,
        cost_usd_ticks=cost_ticks,
        metadata={
            "asset_id": str(asset.id),
            "model_id": play_model.id,
            "provider": provider,
            "batch_index": batch_index,
        },
    )
    stored_ok = await session.get(type(reservation), reservation_id)
    if stored_ok is not None:
        stored_ok.status = "consumed"
    # Keep usage_event_ids on the asset (set at create) so async failure can refund.

    # Worker-owned provider polling so readiness does not depend on the client.
    # Skip in local/dev: APP often points at shared Neon while Fly prod workers
    # claim jobs. If those workers lack media keys they mark good clips failed
    # within seconds. HTTP poll from the app/API covers dev.
    env = (settings.app_env or "").strip().lower()
    if request_id and provider not in {""} and env not in {"development", "dev", "local", "test"}:
        try:
            from app.job_queue import enqueue_kwargs
            from app.models import BackgroundJob

            session.add(
                BackgroundJob(
                    **enqueue_kwargs(
                        workspace_id=body.workspace_id,
                        job_type="video.asset.poll",
                        payload={"asset_id": str(asset.id), "provider": provider},
                        created_by_id=user.id,
                        idempotency_key=f"video.asset.poll:{asset.id}",
                        max_attempts=5,
                        priority=40,
                    )
                )
            )
        except Exception:
            # Generate still succeeds; HTTP poll remains a backup.
            pass

    await session.commit()
    await session.refresh(asset)
    return asset


