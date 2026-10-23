"""Chat-first playground: stills, Talking, and Scene."""
from __future__ import annotations

import hashlib
import json
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_session
from app.dependencies import get_current_user, get_optional_user
from app.image_providers import ImageProviderError, generate_image, persist_generated_image
from app.intimate_contact import intimate_contact_refusal
from app.media_store import MediaStoreError, assert_media_reachable, public_media_url
from app.models import AuditEvent, User, VideoAsset, VideoProject
from app.play_models import catalog_public, get_play_model, token_cost_for
from app.stock_voices import DEFAULT_STOCK_VOICE_ID
from app.provider_errors import http_provider_exception, public_error_message
from app.rate_limit import RateLimiter
from app.rate_limit_deps import enforce_rate_limit
from app.routers import play_assist, play_face_edit, play_faces, play_refs, play_voices
from app.routers.play_helpers import (
    PLAY_PROJECT_TITLE,
    get_or_create_play_project,
    is_face_asset,
    is_hidden_from_clips,
    map_generation,
    next_scene,
    normalize_play_mode,
)
from app.routers.play_video_generate import generate_play_video
from app.routers.video_helpers import add_generation_cost, get_asset, provider_aspect_ratio
from app.routers.video_scene_plan import duration_cap_label, sync_labs_duration_limit
from app.schemas.play import (
    PlayGenerateRequest,
    PlayGenerateResponse,
    PlayGenerationDto,
    PlayModelDto,
    PlayQuoteRequest,
    PlayQuoteResponse,
)
from app.voiceover import VoiceoverProviderError, generate_xai_voiceover_mp3
from app.play_billing import release_if_unsettled
from app.workspace_access import require_permission, reserve_usage_committed

router = APIRouter(prefix="/play", tags=["play"])
router.include_router(play_assist.router)
router.include_router(play_faces.router)
router.include_router(play_face_edit.router)
router.include_router(play_refs.router)
router.include_router(play_voices.router)

PLAY_GENERATE_RATE_LIMIT = 10
PLAY_GENERATE_RATE_WINDOW_SECONDS = 60
PLAY_IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60


def _resolve_play_idempotency_key(header_key: str | None, body_key: str | None) -> str | None:
    raw = (header_key or body_key or "").strip()
    if not raw:
        return None
    if len(raw) > 128:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Idempotency key must be at most 128 characters",
        )
    return raw


def _play_idempotency_redis_key(*, user_id: UUID, workspace_id: UUID, key: str) -> str:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:40]
    return f"play:idem:{user_id}:{workspace_id}:{digest}"


# In-flight marker so a retry that races the original request cannot reserve
# credits and start a second provider job under the same key.
PLAY_IDEMPOTENCY_INFLIGHT_TTL_SECONDS = 10 * 60
_PLAY_INFLIGHT_VALUE = "in-flight"


def _play_idempotency_inflight_key(*, user_id: UUID, workspace_id: UUID, key: str) -> str:
    return f"{_play_idempotency_redis_key(user_id=user_id, workspace_id=workspace_id, key=key)}:inflight"


async def _load_play_generate_idempotent(
    *,
    request: Request,
    session: AsyncSession,
    settings: Settings,
    user_id: UUID,
    workspace_id: UUID,
    key: str,
) -> PlayGenerateResponse | None:
    limiter: RateLimiter = request.app.state.rate_limiter
    raw = await limiter.get(_play_idempotency_redis_key(user_id=user_id, workspace_id=workspace_id, key=key))
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None
    asset_ids = data.get("asset_ids") if isinstance(data, dict) else None
    if not isinstance(asset_ids, list) or not asset_ids:
        return None
    generations: list[PlayGenerationDto] = []
    for raw_id in asset_ids:
        try:
            asset_id = UUID(str(raw_id))
        except (TypeError, ValueError):
            return None
        asset = await session.get(VideoAsset, asset_id)
        if asset is None or asset.workspace_id != workspace_id:
            return None
        generations.append(map_generation(asset, settings))
    if not generations:
        return None
    message = data.get("message") if isinstance(data, dict) else None
    return PlayGenerateResponse(
        generation=generations[0],
        generations=generations,
        message=str(message) if message else None,
    )


async def _store_play_generate_idempotent(
    *,
    request: Request,
    user_id: UUID,
    workspace_id: UUID,
    key: str,
    response: PlayGenerateResponse,
) -> None:
    generations = response.generations or ([response.generation] if response.generation else [])
    if not generations:
        return
    payload = json.dumps(
        {
            "asset_ids": [str(item.id) for item in generations],
            "message": response.message,
        }
    )
    limiter: RateLimiter = request.app.state.rate_limiter
    await limiter.set(
        _play_idempotency_redis_key(user_id=user_id, workspace_id=workspace_id, key=key),
        payload,
        PLAY_IDEMPOTENCY_TTL_SECONDS,
    )


@router.get("/models", response_model=list[PlayModelDto])
async def list_play_models(
    workspace_id: UUID | None = Query(default=None),
    user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
) -> list[PlayModelDto]:
    """Model catalog. When workspace_id is set, Advanced models are locked for free plans."""
    plan_name: str | None = None
    if workspace_id is not None and user is not None:
        await require_permission(session, workspace_id, user, "projects.read")
        from app.workspace_access import get_subscription

        sub = await get_subscription(session, workspace_id)
        plan_name = sub.plan
    return [PlayModelDto(**row) for row in catalog_public(plan_name=plan_name)]


@router.post("/quote", response_model=PlayQuoteResponse)
async def quote_play_generate(body: PlayQuoteRequest) -> PlayQuoteResponse:
    """Authoritative token quote for Create UI (matches reserve math)."""
    from app.play_pricing import compute_play_quote
    from app.routers.play_video_helpers import (
        clamp_duration_for_provider,
        estimate_speech_seconds,
        normalize_play_resolution,
        raw_speech_seconds,
    )
    from app.voiceover import expand_spoken_domains

    mode = normalize_play_mode(body.mode)
    try:
        play_model = get_play_model(
            body.model, mode if mode in ("image", "video", "avatar") else "video"
        )
    except KeyError:
        play_model = get_play_model(None, "video")
    provider = (play_model.provider or "xai").strip().lower()
    resolution = normalize_play_resolution(
        body.resolution, provider=provider, model_id=play_model.provider_model
    )
    duration = body.duration_seconds
    if mode in ("video", "avatar"):
        if duration is None and mode == "avatar":
            # Match generate: Auto sizes to spoken line for talking clips.
            duration = estimate_speech_seconds(body.prompt or "", mode="avatar")
        if duration is not None:
            duration = clamp_duration_for_provider(
                int(duration),
                provider=provider,
                model_id=play_model.provider_model,
                max_duration=play_model.max_duration_seconds or 15,
                resolution=resolution,
                # Veo still forces 8s when a face rides along. Grok 1.5 does not.
                has_reference_images=(
                    mode == "avatar" or body.has_face or body.ref_image_count > 0
                ),
            )
    quote = compute_play_quote(
        mode=mode,
        model_id=play_model.id,
        duration_seconds=duration,
        resolution=resolution,
        count=body.count if provider == "seedance" else 1,
        generate_audio=body.generate_audio,
        return_last_frame=body.return_last_frame if provider == "seedance" else False,
        ref_image_count=body.ref_image_count,
        ref_video_count=body.ref_video_count if provider == "seedance" else 0,
        ref_audio_count=body.ref_audio_count if provider == "seedance" else 0,
        continue_from=body.continue_from,
        cloned_voice=bool(body.cloned_voice),
        has_scene=False,
    )
    return PlayQuoteResponse(**quote.as_dict())


@router.post("/generate", response_model=PlayGenerateResponse, status_code=status.HTTP_201_CREATED)
async def play_generate(
    body: PlayGenerateRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> PlayGenerateResponse:
    await require_permission(session, body.workspace_id, user, "projects.write")

    idem_key = _resolve_play_idempotency_key(idempotency_key, body.client_request_id)
    inflight_key: str | None = None
    if idem_key:
        cached = await _load_play_generate_idempotent(
            request=request,
            session=session,
            settings=settings,
            user_id=user.id,
            workspace_id=body.workspace_id,
            key=idem_key,
        )
        if cached is not None:
            return cached

        # Claim the key before reserving credits. A retry arriving while the
        # first request is still running loses this race and gets 409 rather
        # than reserving a second time and starting a duplicate provider job.
        limiter: RateLimiter = request.app.state.rate_limiter
        inflight_key = _play_idempotency_inflight_key(
            user_id=user.id, workspace_id=body.workspace_id, key=idem_key
        )
        claimed = await limiter.set_if_absent(
            inflight_key, _PLAY_INFLIGHT_VALUE, PLAY_IDEMPOTENCY_INFLIGHT_TTL_SECONDS
        )
        if not claimed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That request is still running. Check Library in a moment.",
            )

    # Set once generation has actually committed (credits consumed, assets and
    # provider jobs created). A failure after that point must NOT free the key:
    # the retry would reserve and start everything a second time.
    committed: dict[str, bool] = {"value": False}
    try:
        return await _play_generate_inner(
            body=body,
            request=request,
            user=user,
            session=session,
            settings=settings,
            idem_key=idem_key,
            committed=committed,
        )
    except BaseException:
        if inflight_key and not committed["value"]:
            # Nothing was charged, so free the key rather than blocking the
            # user's retry for the full in-flight TTL.
            limiter: RateLimiter = request.app.state.rate_limiter
            await limiter.delete(inflight_key)
        raise


async def _play_generate_inner(
    *,
    body: PlayGenerateRequest,
    request: Request,
    user: User,
    session: AsyncSession,
    settings: Settings,
    idem_key: str | None,
    committed: dict[str, bool],
) -> PlayGenerateResponse:
    await enforce_rate_limit(
        request,
        f"play.generate:user:{user.id}",
        PLAY_GENERATE_RATE_LIMIT,
        PLAY_GENERATE_RATE_WINDOW_SECONDS,
        "Too many generate requests. You can start 10 per minute. Wait a bit and try again.",
    )

    prompt = body.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Prompt is required")
    refused = intimate_contact_refusal(prompt, body.scene)
    if refused:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=refused)

    incoming_mode = body.mode
    updates: dict[str, object] = {}
    normalized = normalize_play_mode(body.mode)
    if normalized != body.mode:
        updates["mode"] = normalized
    photo_alias = {
        "seedance-photo-fast": "seedance-avatar-fast",
        "seedance-photo": "seedance-avatar",
    }
    if body.model and body.model.strip() in photo_alias:
        updates["model"] = photo_alias[body.model.strip()]
    if updates:
        body = body.model_copy(update=updates)

    # Old Photo clients sent the spoken line in prompt and place in scene.
    if incoming_mode == "lipsync":
        from app.routers.play_video_helpers import split_avatar_user_prompt

        place = (body.scene or "").strip()
        spoken, leftover_scene = split_avatar_user_prompt(prompt)
        spoken = spoken or prompt.strip()
        scene_text = place or leftover_scene
        prompt = f"{scene_text}. says: {spoken}" if scene_text else f"says: {spoken}"

    # Only Talking parses "says:". Anywhere else it is literal text the provider
    # renders. Normalise here so a draft carried across modes cannot leak the token.
    if body.mode != "avatar":
        from app.routers.play_video_helpers import strip_says_marker

        prompt = strip_says_marker(prompt)
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Prompt is required"
            )

    try:
        play_model = get_play_model(body.model, body.mode)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    from app.plan_entitlements import require_play_model_for_workspace

    await require_play_model_for_workspace(session, body.workspace_id, play_model)

    # Always apply this request's platform → aspect (don't keep a stale project ratio).
    from app.routers.play_helpers import PLATFORM_PRESETS

    platform_key = (body.platform or "tiktok").strip().lower()
    if platform_key not in PLATFORM_PRESETS:
        platform_key = "tiktok"
    preset_platform, preset_aspect, preset_duration = PLATFORM_PRESETS[platform_key]

    project = await get_or_create_play_project(
        session,
        workspace_id=body.workspace_id,
        user=user,
        platform_key=platform_key,
    )
    project.platform = preset_platform
    project.aspect_ratio = preset_aspect
    # Clip length for this request (Play filters). Clamp to DB-safe project range.
    if body.duration_seconds is not None:
        project.target_duration_seconds = max(1, min(int(body.duration_seconds), 180))
    else:
        project.target_duration_seconds = max(1, min(int(preset_duration), 180))
    aspect_ratio = provider_aspect_ratio(preset_aspect)

    if (
        body.mode in {"avatar", "video"}
        and body.face_asset_id is None
        and (body.continue_from_asset_id is not None or body.revoice_of_asset_id is not None)
    ):
        inherited = await _face_id_from_source_clip(session=session, user=user, body=body)
        if inherited is not None:
            body = body.model_copy(update={"face_asset_id": inherited})

    if body.mode == "image":
        response = await _generate_image(
            session=session,
            settings=settings,
            user=user,
            body=body,
            project=project,
            play_model=play_model,
            prompt=prompt,
            aspect_ratio=aspect_ratio,
        )
    elif body.mode == "avatar":
        from app.routers.play_talking_clone import generate_talking_clone
        from app.routers.play_voices import resolve_play_generate_voice

        resolved = await resolve_play_generate_voice(
            session=session,
            workspace_id=body.workspace_id,
            voice=body.voice,
            face_asset_id=body.face_asset_id,
            settings=settings,
            honor_body_voice=body.continue_from_asset_id is not None
            or body.revoice_of_asset_id is not None,
        )
        response = await generate_talking_clone(
            session=session,
            settings=settings,
            user=user,
            body=body,
            project=project,
            play_model=play_model,
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            resolved=resolved,
        )
    else:
        # video (+ refs, batch, continue via play_video_generate)
        from app.routers.play_scene_dialogue import scene_needs_exact_voice
        from app.routers.play_scene_voice import generate_scene_voice
        from app.routers.play_voices import resolve_play_generate_voice

        if scene_needs_exact_voice(
            face_asset_id=body.face_asset_id,
            continue_from_asset_id=body.continue_from_asset_id,
            prompt=prompt,
        ):
            resolved = await resolve_play_generate_voice(
                session=session,
                workspace_id=body.workspace_id,
                voice=body.voice,
                face_asset_id=body.face_asset_id,
                settings=settings,
                honor_body_voice=body.continue_from_asset_id is not None
                or body.revoice_of_asset_id is not None,
            )
            response = await generate_scene_voice(
                session=session,
                settings=settings,
                user=user,
                body=body,
                project=project,
                play_model=play_model,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                resolved=resolved,
            )
        else:
            response = await generate_play_video(
                session=session,
                settings=settings,
                user=user,
                body=body,
                project=project,
                play_model=play_model,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
            )

    # Past this point credits are spent and provider jobs are running, so a
    # later failure must not hand the caller a fresh reservation on retry.
    committed["value"] = True
    if idem_key:
        await _store_play_generate_idempotent(
            request=request,
            user_id=user.id,
            workspace_id=body.workspace_id,
            key=idem_key,
            response=response,
        )
        limiter: RateLimiter = request.app.state.rate_limiter
        await limiter.delete(
            _play_idempotency_inflight_key(
                user_id=user.id, workspace_id=body.workspace_id, key=idem_key
            )
        )
    return response


async def _generate_image(
    *,
    session: AsyncSession,
    settings: Settings,
    user: User,
    body: PlayGenerateRequest,
    project: VideoProject,
    play_model,
    prompt: str,
    aspect_ratio: str,
) -> PlayGenerateResponse:
    provider = (play_model.provider or "xai").strip().lower()
    scene = await next_scene(session, project, prompt)
    from app.play_pricing import compute_play_quote

    quote = compute_play_quote(mode="image", model_id=play_model.id)
    tokens = max(1, int(quote.per_item))
    reservation = await reserve_usage_committed(
        session,
        body.workspace_id,
        user.id,
        quote.meter,
        tokens,
        {"operation": "play_image", "model_id": play_model.id, "token_cost": tokens, "quote": quote.as_dict()},
    )
    reservation_id = reservation.id
    asset = VideoAsset(
        workspace_id=body.workspace_id,
        video_project_id=project.id,
        video_scene_id=scene.id,
        asset_type="image",
        source=provider,
        status="processing",
        prompt=prompt,
        provider=provider,
        provider_model=play_model.provider_model,
        asset_metadata={
            "play": True,
            "play_mode": "image",
            "play_platform": body.platform,
            "model_id": play_model.id,
            "aspect_ratio": aspect_ratio,
            "resolution": "1k",
        },
    )
    session.add(asset)
    await session.flush()

    try:
        result = await generate_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            resolution="1k",
            settings=settings,
            model=play_model.id,
        )
    except ImageProviderError as exc:
        asset.status = "failed"
        asset.error_message = public_error_message(exc, kind="media")
        await session.commit()
        await release_if_unsettled(session, type(reservation), reservation_id)
        raise http_provider_exception(exc, kind="media") from exc
    except Exception:
        await release_if_unsettled(session, type(reservation), reservation_id)
        raise

    asset.status = "ready"
    asset.provider = result.provider
    asset.provider_model = result.model
    asset.provider_url = result.url
    asset.cost_usd_ticks = result.cost_usd_ticks
    try:
        stored_url = await persist_generated_image(
            result=result, settings=settings, subdir="play", stem=asset.id
        )
        asset.storage_url = stored_url
        if not asset.provider_url:
            asset.provider_url = stored_url
    except Exception as persist_exc:  # noqa: BLE001
        asset.asset_metadata = {
            **dict(asset.asset_metadata or {}),
            "persist_error": str(persist_exc)[:240],
        }

    add_generation_cost(
        session,
        workspace_id=body.workspace_id,
        user_id=user.id,
        feature="play_image",
        provider_model=result.model,
        provider_request_id=None,
        cost_usd_ticks=result.cost_usd_ticks,
        metadata={"asset_id": str(asset.id), "model_id": play_model.id, "provider": provider},
    )
    stored_ok = await session.get(type(reservation), reservation_id)
    if stored_ok is not None:
        stored_ok.status = "consumed"
    await session.commit()
    await session.refresh(asset)
    dto = map_generation(asset, settings)
    return PlayGenerateResponse(generation=dto, generations=[dto])


async def _face_id_from_source_clip(
    *,
    session: AsyncSession,
    user: User,
    body: PlayGenerateRequest,
) -> UUID | None:
    """Extend and revoice keep the prior clip's Face even if the client omitted it."""
    source_id = body.continue_from_asset_id or body.revoice_of_asset_id
    if source_id is None:
        return None
    missing = (
        "That clip is gone. Pick another to extend."
        if body.continue_from_asset_id is not None
        else "That clip is gone. Pick another to revoice."
    )
    source = await get_asset(
        source_id,
        user,
        session,
        "projects.read",
        missing=missing,
    )
    if source.workspace_id != body.workspace_id:
        return None
    meta = dict(source.asset_metadata or {})
    raw = meta.get("face_asset_id") or meta.get("source_image_asset_id")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return UUID(raw.strip())
    except ValueError:
        return None


@router.get("/generations", response_model=list[PlayGenerationDto])
async def list_play_generations(
    workspace_id: UUID = Query(...),
    limit: int = Query(40, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[PlayGenerationDto]:
    await require_permission(session, workspace_id, user, "projects.read")
    project = await session.scalar(
        select(VideoProject)
        .where(
            VideoProject.workspace_id == workspace_id,
            VideoProject.title == PLAY_PROJECT_TITLE,
        )
        .order_by(VideoProject.created_at.desc())
        .limit(1)
    )
    if project is None:
        return []
    # Faces and play refs live on the same project and must not appear in Clips.
    # Filtering in SQL rather than over-fetching: a workspace with a few hundred
    # recent faces used to push every real clip out of the fetch window.
    meta = VideoAsset.asset_metadata
    rows = (
        await session.scalars(
            select(VideoAsset)
            .where(
                VideoAsset.video_project_id == project.id,
                VideoAsset.asset_type.in_(("image", "video")),
                meta["mode"].astext.is_distinct_from("avatar_source_image"),
                meta["face_library"].astext.is_distinct_from("true"),
                meta["play_ref"].astext.is_distinct_from("true"),
            )
            .order_by(VideoAsset.created_at.desc())
            .limit(limit)
        )
    ).all()
    # Belt and braces: the predicates own the definition of hidden.
    clips = [row for row in rows if not is_hidden_from_clips(row)]
    return [map_generation(row, settings) for row in clips]


@router.get("/generations/{asset_id}", response_model=PlayGenerationDto)
async def get_play_generation(
    asset_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PlayGenerationDto:
    asset = await session.get(VideoAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation not found")
    await require_permission(session, asset.workspace_id, user, "projects.read")
    # Clip detail opens the player: persist + faststart remux so iOS can progressive-stream.
    if asset.status == "ready" and asset.asset_type == "video":
        try:
            import asyncio

            from app.routers.video_helpers import ensure_asset_streamable, maybe_auto_persist_asset

            if not asset.storage_url and asset.provider_url:
                await maybe_auto_persist_asset(asset, settings)
            # Always run streamable check (cheap if metadata.faststart already set).
            await asyncio.to_thread(ensure_asset_streamable, asset, settings)
            await session.commit()
            await session.refresh(asset)
        except Exception:  # noqa: BLE001 — still return best-effort URL
            await session.rollback()
            asset = await session.get(VideoAsset, asset_id) or asset
    return map_generation(asset, settings)


@router.delete("/generations/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_play_generation(
    asset_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a clip (play generation). Face library stills are blocked."""
    asset = await session.get(VideoAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found")
    await require_permission(session, asset.workspace_id, user, "projects.write")
    meta = dict(asset.asset_metadata or {})
    if meta.get("mode") == "avatar_source_image" or meta.get("face_library") is True:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Delete faces from the Avatars library, not here",
        )
    session.add(
        AuditEvent(
            workspace_id=asset.workspace_id,
            actor_id=user.id,
            action="play.generation_deleted",
            details={"asset_id": str(asset.id), "prompt": (asset.prompt or "")[:200]},
        )
    )
    await session.delete(asset)
    await session.commit()
