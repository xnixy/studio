from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.models import User
from app.media_store import extension_from_url, local_path_from_media_url, media_url_for, safe_media_name
from app.plans import PLAN_CATALOG, apply_addons, plan_for
from app.voiceover import estimate_voiceover_seconds
from app.routers._platform_shared import next_month, week_start
from app.routers.billing import plan_from_subscription_object
from app.routers import system as system_router
from app.routers.video_scene_plan import clean_storyboard_visual, repair_scene, sync_labs_duration_limit
from app.schemas import (
    CheckoutRequest,
    ContactRequest,
    LoginRequest,
    RegisterRequest,
    WorkspaceCreateRequest,
)
from app.security import create_access_token, decode_access_token, hash_password, verify_password
from app.voiceover import safe_filename, voice_id_for, voiceover_text, estimate_voiceover_seconds
from app.video_renderer import selected_scene_video_assets, sync_scene_timings_to_total, vtt_timestamp, write_caption_sidecars, write_concat_file
from app.workspace_access import ROLE_PERMISSIONS
from app.xai_media import clamp_extension_duration, clamp_video_duration, cost_ticks_from_response, first_media_url, video_duration_seconds_from_response


def test_register_full_name_is_normalized() -> None:
    payload = RegisterRequest(
        email="user@example.com",
        password="Password123!",
        full_name="  Ada  Lovelace  ",
    )

    assert payload.full_name == "Ada Lovelace"


def test_register_requires_full_name() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(email="user@example.com", password="Password123!", full_name="  ")


def test_login_accepts_documented_local_admin_email() -> None:
    payload = LoginRequest(email="ADMIN@STUDIO.LOCAL", password="Admin123!")

    assert payload.email == "admin@studio.local"


def test_login_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(email="not an email", password="Admin123!")


def test_contact_topic_validation() -> None:
    ContactRequest(name="User", email="user@example.com", topic="general", message="A useful message")

    with pytest.raises(ValidationError):
        ContactRequest(name="User", email="user@example.com", topic="billing", message="A useful message")








def test_xai_voiceover_mapping_and_text() -> None:
    from app.voiceover import clamp_speech_speed, speech_speed_for

    settings = Settings(
        XAI_TTS_FEMALE_VOICE_ID="eve",
        XAI_TTS_MALE_VOICE_ID="rex",
    )

    assert voice_id_for("female", settings) == "eve"
    assert voice_id_for("male", settings) == "rex"
    assert voice_id_for("ara", settings) == "ara"
    assert voice_id_for("Leo", settings) == "leo"
    # Scripts are read exactly as written; no preset injects SSML wrappers.
    assert voiceover_text("Try this product today.") == "Try this product today."
    assert speech_speed_for() == 1.0
    assert speech_speed_for(1.2) == 1.2
    assert clamp_speech_speed(2.0) == 1.5
    assert clamp_speech_speed(0.5) == 0.7



def test_frontend_origins_accept_comma_separated_env_value() -> None:
    settings = Settings(FRONTEND_ORIGINS="http://localhost:5173/, https://example.com")

    assert settings.frontend_origin_list == ["http://localhost:5173", "https://example.com"]


def test_password_hash_round_trip() -> None:
    password_hash = hash_password("Password123!")

    assert verify_password("Password123!", password_hash)
    assert not verify_password("nope", password_hash)


def test_access_token_round_trip() -> None:
    settings = Settings(JWT_SIGNING_KEY="test-signing-key-that-is-long-enough", JWT_ISSUER="issuer", JWT_AUDIENCE="audience")
    user = User(id=uuid4(), email="admin@example.com", password_hash="hash", role="admin", permissions={}, created_at=datetime.now(timezone.utc))

    token = create_access_token(user, settings)
    payload = decode_access_token(token, settings)

    assert payload["sub"] == str(user.id)
    assert payload["role"] == "admin"






def test_plan_addons_increase_effective_limits() -> None:
    from app.plans import apply_limit_grants, credit_pack_for

    base = plan_for("starter")
    effective = apply_addons(
        base,
        {
            "seats": 4,
            "priority_rendering": 1,
            "video_credits": 5,
            "image_generations": 8,
            "avatar_lipsyncs": 3,
            "script_generations": 10,
            "voiceover_minutes": 5,
        },
    )

    assert effective.seat_limit == base.seat_limit + 4
    assert effective.priority_rendering is True
    assert effective.video_credit_limit == base.video_credit_limit + 5 * 5
    assert effective.image_generation_limit == base.image_generation_limit + 8 * 3
    assert effective.avatar_lipsync_limit == base.avatar_lipsync_limit + 3 * 5
    assert effective.script_generation_limit == base.script_generation_limit + 10
    assert effective.voiceover_seconds_limit == base.voiceover_seconds_limit + 5 * 60

    pack = credit_pack_for("creator_burst")
    assert pack is not None
    with_pack = apply_limit_grants(base, pack.grants)
    assert with_pack.video_credit_limit == base.video_credit_limit + pack.grants["video_credit_limit"]
    assert with_pack.image_generation_limit == base.image_generation_limit + pack.grants["image_generation_limit"]
    assert with_pack.avatar_lipsync_limit == base.avatar_lipsync_limit + pack.grants["avatar_lipsync_limit"]
    assert with_pack.voiceover_seconds_limit == base.voiceover_seconds_limit + pack.grants["voiceover_seconds_limit"]




def test_force_align_script_to_asr_words() -> None:
    from app.asr_alignment import TimedWord, force_align_script_to_asr, group_words_into_cues

    script = ["Stop", "wasting", "money", "on", "coffee"]
    asr = [
        TimedWord("Stop", 0.0, 0.2),
        TimedWord("wasting", 0.25, 0.55),
        TimedWord("money", 0.6, 0.9),
        TimedWord("on", 0.95, 1.05),
        TimedWord("coffee", 1.1, 1.5),
    ]
    aligned = force_align_script_to_asr(script, asr)
    assert len(aligned) == 5
    assert aligned[0].text == "Stop"
    assert aligned[0].start == 0.0
    assert aligned[-1].text == "coffee"
    assert aligned[-1].end >= 1.5
    # Insert a gap and ensure interpolation fills it
    asr_gap = [asr[0], asr[1], asr[3], asr[4]]  # missing "money"
    filled = force_align_script_to_asr(script, asr_gap)
    assert len(filled) == 5
    assert filled[2].text == "money"
    assert filled[2].source in {"forced", "interpolated"}
    cues = group_words_into_cues(aligned, max_words=3)
    assert cues
    assert cues[0][1] <= cues[0][2]


def test_platform_permissions_are_play_scoped() -> None:
    for role in ("owner", "admin", "editor"):
        assert "projects.read" in ROLE_PERMISSIONS[role]
        assert "projects.write" in ROLE_PERMISSIONS[role]
        assert "shares.read" in ROLE_PERMISSIONS[role]
    assert "billing.manage" in ROLE_PERMISSIONS["owner"]
    assert "audit.read" in ROLE_PERMISSIONS["owner"]
    assert "audit.read" not in ROLE_PERMISSIONS["editor"]
    assert "projects.read" in ROLE_PERMISSIONS["viewer"]
    assert "projects.write" not in ROLE_PERMISSIONS["viewer"]
    # Retired surfaces must not reappear in role grants.
    for role, perms in ROLE_PERMISSIONS.items():
        assert "monitoring.manage" not in perms
        assert "integrations.manage" not in perms
        assert "library.write" not in perms
        assert "recommendations.write" not in perms




def test_plan_catalog_is_free_plus_three_paid() -> None:
    free = plan_for("free")
    starter = plan_for("starter")
    creator = plan_for("creator")
    studio = plan_for("studio")
    names = {p.name for p in PLAN_CATALOG}
    assert names == {"free", "starter", "creator", "studio"}
    assert free.price_monthly == 0
    assert free.image_generation_limit >= 1
    assert free.avatar_lipsync_limit >= 1
    assert starter.price_monthly == 3_900
    assert creator.price_monthly == 9_900
    assert studio.price_monthly == 17_900
    assert creator.image_generation_limit > free.image_generation_limit
    assert studio.seat_limit >= creator.seat_limit
    assert studio.video_credit_limit > creator.video_credit_limit
    assert studio.priority_rendering is True
    # Unknown names fall back to free (no legacy aliases).
    assert plan_for("agency").name == "free"
    assert plan_for("pro").name == "free"


def test_job_backoff_and_lease_helpers() -> None:
    from app.jobs.base import backoff_seconds, lease_for, read_permission_for, write_permission_for
    from datetime import timedelta

    assert backoff_seconds(1) == 30
    assert backoff_seconds(2) == 60
    assert backoff_seconds(3) == 120
    assert backoff_seconds(20) == 3600
    assert lease_for("echo") == timedelta(minutes=5)
    assert lease_for("unknown") == timedelta(minutes=15)
    assert read_permission_for("echo") == "projects.read"
    assert write_permission_for("echo") == "projects.write"






def test_scene_repair_and_sync_duration_limit() -> None:
    scene = type("Scene", (), {
        "visual_prompt": None,
        "on_screen_text": "Fallback product view",
        "spoken_text": "Narration",
        "scene_metadata": {},
    })()

    assert repair_scene(scene)
    assert scene.visual_prompt == "Fallback product view"
    assert sync_labs_duration_limit("sync-3") == 120.0
    assert sync_labs_duration_limit("sync-4") is None
    # repair_scene's only cleanup path: storyboard lines still carry time codes.
    assert clean_storyboard_visual("0-4s: Close-up of ErgoStand mat") == "Close-up of ErgoStand mat"


def test_url_safety_blocks_private_and_allows_public() -> None:
    import pytest
    from app.url_safety import UnsafeUrlError, assert_public_http_url

    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("ftp://example.com")
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("http://localhost/path")
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("http://127.0.0.1/")
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("http://192.168.1.10/")
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("http://169.254.169.254/latest/meta-data")
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("https://example.com:8443/")
    try:
        assert assert_public_http_url("https://example.com/path").startswith("https://")
    except UnsafeUrlError as exc:
        if "resolve" in str(exc).lower():
            pytest.skip("DNS unavailable for example.com")
        raise


def test_echo_handler_returns_payload_message() -> None:
    import asyncio
    from types import SimpleNamespace
    from app.jobs.echo import EchoHandler
    from app.jobs.base import JobContext

    job = SimpleNamespace(payload={"message": "hello"}, attempts=1, cancel_requested=False)
    ctx = JobContext(session=None, job=job, workspace_id=uuid4())  # type: ignore[arg-type]
    result = asyncio.run(EchoHandler().run(ctx))
    assert result["echo"] == "hello"
    assert result["attempts"] == 1


def test_week_start_returns_utc_monday() -> None:
    value = datetime(2026, 7, 10, 14, 45, tzinfo=timezone.utc)

    assert week_start(value) == datetime(2026, 7, 6, tzinfo=timezone.utc)


def test_stripe_subscription_plan_mapping_prefers_metadata_then_price_id() -> None:
    settings = Settings(
        STRIPE_STARTER_PRICE_ID="price_starter",
        STRIPE_CREATOR_PRICE_ID="price_creator",
        STRIPE_STUDIO_PRICE_ID="price_studio",
    )

    assert plan_from_subscription_object({"metadata": {"plan": "studio"}}, settings) == "studio"
    assert (
        plan_from_subscription_object(
            {"items": {"data": [{"price": {"id": "price_creator"}}]}},
            settings,
        )
        == "creator"
    )
    assert plan_from_subscription_object({"items": {"data": [{"price": {"id": "unknown"}}]}}, settings) is None







def test_billing_period_next_month_handles_year_rollover() -> None:
    assert next_month(datetime(2026, 11, 1, tzinfo=timezone.utc)) == datetime(2026, 12, 1, tzinfo=timezone.utc)
    assert next_month(datetime(2026, 12, 1, tzinfo=timezone.utc)) == datetime(2027, 1, 1, tzinfo=timezone.utc)




def test_xai_media_helpers_parse_urls_costs_and_durations() -> None:
    assert first_media_url({"data": [{"url": "https://example.com/image.jpg"}]}) == "https://example.com/image.jpg"
    assert first_media_url({"video": {"url": "https://example.com/video.mp4", "duration": 8}}) == "https://example.com/video.mp4"
    assert cost_ticks_from_response({"usage": {"cost_in_usd_ticks": "10000000000"}}) == 10000000000
    assert video_duration_seconds_from_response({"video": {"duration": 8.4}}) == 8
    assert clamp_video_duration(30) == 15
    assert clamp_video_duration(0) == 1
    assert clamp_extension_duration(1) == 2
    assert clamp_extension_duration(30) == 10


def test_media_store_helpers_keep_paths_inside_media_dir(tmp_path) -> None:
    # Explicitly disable R2 so local-path assertions stay independent of developer .env.
    settings = Settings(
        MEDIA_DIR=str(tmp_path),
        R2_ACCOUNT_ID=None,
        R2_ACCESS_KEY_ID=None,
        R2_SECRET_ACCESS_KEY=None,
        R2_BUCKET_NAME=None,
        R2_PUBLIC_BASE_URL=None,
    )
    output_path = tmp_path / "video-assets" / "clip.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"demo")

    assert safe_media_name("../Clip Name!") == "clip-name"
    assert extension_from_url("https://example.com/output.mp4?token=1", ".bin") == ".mp4"
    assert media_url_for(output_path, settings) == "/api/media/video-assets/clip.mp4"
    assert local_path_from_media_url("/api/media/video-assets/clip.mp4", settings) == output_path
    assert local_path_from_media_url("https://example.com/clip.mp4", settings) is None
    assert not settings.r2_enabled


def test_media_store_uses_private_api_urls_when_r2_configured(tmp_path) -> None:
    """User media stays on /api/media even when R2 is enabled (private bucket model)."""
    settings = Settings(
        MEDIA_DIR=str(tmp_path),
        R2_ACCOUNT_ID="acct",
        R2_ACCESS_KEY_ID="key",
        R2_SECRET_ACCESS_KEY="secret",
        R2_BUCKET_NAME="studio-media",
        R2_PUBLIC_BASE_URL="https://media.example.com",
    )
    assert settings.r2_enabled
    assert settings.media_public_base_url.endswith("/api/media")

    from app.media_store import is_public_marketing_key, public_url_for_key, write_local_bytes

    url = public_url_for_key("voiceovers/demo.mp3", settings)
    assert url == "/api/media/voiceovers/demo.mp3"
    assert is_public_marketing_key("examples/avatars/maya.jpg")
    assert not is_public_marketing_key("voiceovers/demo.mp3")

    path = write_local_bytes("voiceovers/demo.mp3", b"id3", settings)
    assert path.exists()
    assert local_path_from_media_url(url, settings) == path


def test_video_renderer_concat_file_uses_absolute_paths(tmp_path) -> None:
    first = tmp_path / "one.mp4"
    second = tmp_path / "two.mp4"
    concat = tmp_path / "render.concat.txt"

    write_concat_file([first, second], concat)

    text = concat.read_text(encoding="utf-8")
    assert first.resolve().as_posix() in text
    assert second.resolve().as_posix() in text


def test_video_renderer_syncs_scene_timings_to_voiceover_duration() -> None:
    scenes = [
        type("Scene", (), {"sequence_index": 0, "start_time_ms": 0, "end_time_ms": 3000})(),
        type("Scene", (), {"sequence_index": 1, "start_time_ms": 3000, "end_time_ms": 9000})(),
    ]
    project = type("Project", (), {"scenes": scenes})()

    sync_scene_timings_to_total(project, 12.0)

    assert scenes[0].start_time_ms == 0
    assert scenes[0].end_time_ms == 4000
    assert scenes[1].start_time_ms == 4000
    assert scenes[1].end_time_ms == 12000


def test_video_renderer_selects_latest_ready_clip_per_scene() -> None:
    first_scene_id = uuid4()
    second_scene_id = uuid4()
    scenes = [
        type("Scene", (), {"id": first_scene_id, "sequence_index": 0})(),
        type("Scene", (), {"id": second_scene_id, "sequence_index": 1})(),
    ]
    older = type(
        "Asset",
        (),
        {
            "asset_type": "video",
            "status": "ready",
            "video_scene_id": first_scene_id,
            "storage_url": "/api/media/video-assets/older.mp4",
            "provider_url": None,
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        },
    )()
    newer = type(
        "Asset",
        (),
        {
            "asset_type": "video",
            "status": "ready",
            "video_scene_id": first_scene_id,
            "storage_url": "/api/media/video-assets/newer.mp4",
            "provider_url": None,
            "created_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        },
    )()
    second = type(
        "Asset",
        (),
        {
            "asset_type": "video",
            "status": "ready",
            "video_scene_id": second_scene_id,
            "storage_url": "/api/media/video-assets/second.mp4",
            "provider_url": None,
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        },
    )()
    project = type("Project", (), {"scenes": scenes, "assets": [older, newer, second]})()

    selected = selected_scene_video_assets(project)

    assert [asset.storage_url for _, asset in selected] == ["/api/media/video-assets/newer.mp4", "/api/media/video-assets/second.mp4"]


def test_video_renderer_writes_caption_sidecars(tmp_path) -> None:
    from app.video_renderer import caption_text_for_scene

    settings = Settings(MEDIA_DIR=str(tmp_path))
    render = type("Render", (), {"id": uuid4()})()
    scenes = [
        type("Scene", (), {"sequence_index": 0, "start_time_ms": 0, "end_time_ms": 2500, "on_screen_text": "Hook line", "spoken_text": None, "visual_prompt": None})(),
        type("Scene", (), {"sequence_index": 1, "start_time_ms": 2500, "end_time_ms": 5000, "on_screen_text": "visual junk", "spoken_text": "Proof line", "visual_prompt": None})(),
    ]
    project = type("Project", (), {"scenes": scenes})()

    urls = write_caption_sidecars(project, render, settings)

    assert vtt_timestamp(2500) == "00:00:02.500"
    assert urls["captions_vtt_url"].endswith(".vtt")
    assert urls["captions_srt_url"].endswith(".srt")
    vtt = (tmp_path / "renders" / f"{render.id}.vtt").read_text(encoding="utf-8")
    assert "Hook line" in vtt
    assert "Proof line" in vtt
    assert "visual junk" not in vtt
    assert caption_text_for_scene(scenes[1]) == "Proof line"

    # Override rows (voiceover-aligned) take precedence for sidecars.
    override = [(0, 1000, "Timed cue A"), (1000, 2000, "Timed cue B")]
    urls2 = write_caption_sidecars(project, render, settings, rows=override)
    vtt2 = (tmp_path / "renders" / f"{render.id}.vtt").read_text(encoding="utf-8")
    assert "Timed cue A" in vtt2
    assert urls2["captions_vtt_url"].endswith(".vtt")


@pytest.mark.asyncio
async def test_render_status_reports_missing_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(system_router, "ffmpeg_path", lambda: None)

    status = await system_router.render_status(_=None)  # type: ignore[arg-type]

    assert status.available is False
    assert status.path is None


@pytest.mark.asyncio
async def test_render_status_reports_ffmpeg_version(monkeypatch: pytest.MonkeyPatch) -> None:
    class Result:
        stdout = "ffmpeg version 6.1\nconfiguration: --enable-gpl"

    monkeypatch.setattr(system_router, "ffmpeg_path", lambda: "/usr/bin/ffmpeg")
    monkeypatch.setattr(system_router.subprocess, "run", lambda *_, **__: Result())

    status = await system_router.render_status(_=None)  # type: ignore[arg-type]

    assert status.available is True
    assert status.path == "/usr/bin/ffmpeg"
    assert status.version == "ffmpeg version 6.1"


def test_password_strength_rejects_weak_passwords() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(email="user@example.com", password="password", full_name="Ada")
    with pytest.raises(ValidationError):
        RegisterRequest(email="user@example.com", password="alllowercase1", full_name="Ada")
    with pytest.raises(ValidationError):
        RegisterRequest(email="user@example.com", password="password1", full_name="Ada")
    ok = RegisterRequest(
        email="user@example.com",
        password="Password123!",
        full_name="Ada",
    )
    assert ok.password == "Password123!"


def test_media_signing_round_trip() -> None:
    from app.media_signing import media_signature, sign_media_url, strip_media_query, verify_media_signature

    settings = Settings(JWT_SIGNING_KEY="test-signing-key-that-is-long-enough")
    signed = sign_media_url("/api/media/renders/demo.mp4", settings, ttl_seconds=600)
    assert signed is not None
    assert "sig=" in signed
    assert "exp=" in signed
    assert strip_media_query(signed).startswith("/api/media/renders/demo.mp4")
    # parse and verify
    from urllib.parse import parse_qs, urlsplit

    qs = parse_qs(urlsplit(signed).query)
    assert verify_media_signature("renders/demo.mp4", qs["exp"][0], qs["sig"][0], settings)
    assert not verify_media_signature("renders/demo.mp4", qs["exp"][0], "deadbeef", settings)
    assert media_signature("renders/demo.mp4", int(qs["exp"][0]), settings) == qs["sig"][0]


def test_webhook_url_rejects_private_targets() -> None:
    from app.url_safety import UnsafeUrlError, assert_public_http_url

    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("https://127.0.0.1/hooks")
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("https://localhost/hooks")
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("https://10.0.0.5/hooks")
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("https://169.254.169.254/latest/meta-data/")
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("ftp://example.com/hooks")


def test_ws_ticket_round_trip() -> None:
    from uuid import uuid4

    from app.routers.ws_renders import create_ws_ticket, verify_ws_ticket

    settings = Settings(JWT_SIGNING_KEY="test-signing-key-that-is-long-enough")
    user_id = uuid4()
    workspace_id = uuid4()
    ticket = create_ws_ticket(user_id=user_id, workspace_id=workspace_id, settings=settings)
    parsed = verify_ws_ticket(ticket, settings)
    assert parsed == (user_id, workspace_id)
    assert verify_ws_ticket(ticket + "x", settings) is None


def test_production_rejects_default_jwt_and_unverified_iap() -> None:
    from app.config import Settings

    bad = Settings(
        APP_ENV="production",
        JWT_SIGNING_KEY="development-signing-key-change-me-32chars",
        REDIS_URL="redis://localhost:6379/0",
        SEED_ADMIN_PASSWORD="ProdAdmin!ChangeMe1",
        TURNSTILE_SECRET_KEY="turnstile-secret",
    )
    with pytest.raises(RuntimeError, match="JWT_SIGNING_KEY"):
        bad.assert_production_secrets()

    # Explicit empty secrets so local backend/.env does not leak into this case.
    no_redis = Settings(
        APP_ENV="production",
        JWT_SIGNING_KEY="prod-secret-key-that-is-long-enough-xyz12",
        REDIS_URL="",
        SEED_ADMIN_PASSWORD="ProdAdmin!ChangeMe1",
        TURNSTILE_SECRET_KEY="turnstile-secret",
        STRIPE_SECRET_KEY="",
        STRIPE_WEBHOOK_SECRET="",
    )
    with pytest.raises(RuntimeError, match="REDIS_URL"):
        no_redis.assert_production_secrets()

    iap = Settings(
        APP_ENV="production",
        JWT_SIGNING_KEY="prod-secret-key-that-is-long-enough-xyz12",
        REDIS_URL="redis://localhost:6379/0",
        SEED_ADMIN_PASSWORD="ProdAdmin!ChangeMe1",
        TURNSTILE_SECRET_KEY="turnstile-secret",
        STRIPE_SECRET_KEY="",
        STRIPE_WEBHOOK_SECRET="",
        APPLE_IAP_ALLOW_UNVERIFIED=True,
    )
    with pytest.raises(RuntimeError, match="APPLE_IAP_ALLOW_UNVERIFIED"):
        iap.assert_production_secrets()

    stripe_no_wh = Settings(
        APP_ENV="production",
        JWT_SIGNING_KEY="prod-secret-key-that-is-long-enough-xyz12",
        REDIS_URL="redis://localhost:6379/0",
        SEED_ADMIN_PASSWORD="ProdAdmin!ChangeMe1",
        TURNSTILE_SECRET_KEY="turnstile-secret",
        STRIPE_SECRET_KEY="sk_test_x",
        STRIPE_WEBHOOK_SECRET="",
    )
    with pytest.raises(RuntimeError, match="STRIPE_WEBHOOK_SECRET"):
        stripe_no_wh.assert_production_secrets()

    ok = Settings(
        APP_ENV="production",
        JWT_SIGNING_KEY="prod-secret-key-that-is-long-enough-xyz12",
        REDIS_URL="redis://localhost:6379/0",
        SEED_ADMIN_PASSWORD="ProdAdmin!ChangeMe1",
        TURNSTILE_SECRET_KEY="turnstile-secret",
        STRIPE_SECRET_KEY="",
        STRIPE_WEBHOOK_SECRET="",
        APPLE_IAP_ALLOW_UNVERIFIED=False,
    )
    ok.assert_production_secrets()


def test_pack_name_from_checkout_prefers_price_id() -> None:
    from app.routers.billing import _pack_name_from_checkout

    settings = Settings(
        JWT_SIGNING_KEY="test-signing-key-that-is-long-enough",
        STRIPE_PACK_VIDEO_10_PRICE_ID="price_video_10",
    )
    assert (
        _pack_name_from_checkout(
            {},
            {"pack_name": "video_10", "price_id": "price_video_10", "kind": "credit_pack"},
            settings,
        )
        == "video_10"
    )
    # Unknown pack name rejected when price ids are configured and price missing
    assert (
        _pack_name_from_checkout({}, {"pack_name": "not_a_real_pack", "kind": "credit_pack"}, settings) is None
    )
    # Known pack without price_id still accepted when it is in the configured map
    assert _pack_name_from_checkout({}, {"pack_name": "video_10"}, settings) == "video_10"
    # Retired SKU still fulfills from Stripe price id
    retired = Settings(
        JWT_SIGNING_KEY="test-signing-key-that-is-long-enough",
        STRIPE_PACK_LIPSYNC_10_PRICE_ID="price_lipsync_10",
    )
    assert (
        _pack_name_from_checkout(
            {},
            {"pack_name": "lipsync_10", "price_id": "price_lipsync_10", "kind": "credit_pack"},
            retired,
        )
        == "lipsync_10"
    )


def test_media_url_matches_exact_key_only() -> None:
    from app.routers.media import _url_matches_media_key

    assert _url_matches_media_key("/api/media/play/abc.mp4", "play/abc.mp4")
    assert not _url_matches_media_key("/api/media/play/abc.mp4", "abc.mp4")
    assert not _url_matches_media_key("/api/media/play/other-abc.mp4", "play/abc.mp4")
    assert not _url_matches_media_key(None, "play/abc.mp4")


def test_client_ip_ignores_forwarded_without_trust(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.dependencies import get_client_ip
    from starlette.requests import Request

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [(b"x-forwarded-for", b"9.9.9.9")],
        "client": ("1.2.3.4", 12345),
        "server": ("test", 80),
    }
    request = Request(scope)
    monkeypatch.setattr("app.dependencies.get_settings", lambda: Settings(TRUST_PROXY_HEADERS="false", JWT_SIGNING_KEY="test-signing-key-that-is-long-enough"))
    assert get_client_ip(request) == "1.2.3.4"
    monkeypatch.setattr("app.dependencies.get_settings", lambda: Settings(TRUST_PROXY_HEADERS="true", JWT_SIGNING_KEY="test-signing-key-that-is-long-enough"))
    assert get_client_ip(request) == "9.9.9.9"


def _email_settings(**kwargs) -> Settings:
    """Build settings with email backends isolated from developer .env."""
    base = {
        "JWT_SIGNING_KEY": "test-signing-key-that-is-long-enough",
        "SENDGRID_API_KEY": "",
        "SENDGRID_FROM_EMAIL": "",
        "SMTP_HOST": "",
        "SMTP_FROM_EMAIL": "",
        "CONTACT_NOTIFY_EMAIL": "",
    }
    base.update(kwargs)
    return Settings(**base)


def test_email_delivery_configured_prefers_sendgrid() -> None:
    from app.email_delivery import email_delivery_configured, email_from_address

    bare = _email_settings()
    assert not email_delivery_configured(bare)
    assert email_from_address(bare) is None

    sendgrid = _email_settings(SENDGRID_API_KEY="SG.test", SENDGRID_FROM_EMAIL="hello@example.com")
    assert email_delivery_configured(sendgrid)
    assert email_from_address(sendgrid) == "hello@example.com"

    smtp_fallback_from = _email_settings(SENDGRID_API_KEY="SG.test", SMTP_FROM_EMAIL="ops@example.com")
    assert email_from_address(smtp_fallback_from) == "ops@example.com"

    smtp_only = _email_settings(SMTP_HOST="smtp.example.com", SMTP_FROM_EMAIL="ops@example.com")
    assert email_delivery_configured(smtp_only)


def test_send_email_sendgrid_posts_mail_send(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    import httpx

    from app.email_delivery import send_email

    captured: dict = {}

    class FakeResponse:
        status_code = 202
        text = ""
        reason_phrase = "Accepted"

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    settings = _email_settings(
        SENDGRID_API_KEY="SG.secret",
        SENDGRID_FROM_EMAIL="hello@example.com",
        SENDGRID_FROM_NAME="Studio",
    )
    asyncio.run(send_email("Subject", "Body text", ["user@example.com"], settings))

    assert captured["url"] == "https://api.sendgrid.com/v3/mail/send"
    assert captured["headers"]["Authorization"] == "Bearer SG.secret"
    assert captured["json"]["subject"] == "Subject"
    assert captured["json"]["from"] == {"email": "hello@example.com", "name": "Studio"}
    assert captured["json"]["personalizations"][0]["to"] == [{"email": "user@example.com"}]
    assert captured["json"]["content"][0] == {"type": "text/plain", "value": "Body text"}
    assert captured["json"]["tracking_settings"] == {
        "click_tracking": {"enable": False, "enable_text": False},
        "open_tracking": {"enable": False},
    }


def test_send_email_sendgrid_raises_on_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    import httpx

    from app.email_delivery import EmailDeliveryError, send_email

    class FakeResponse:
        status_code = 401
        text = '{"errors":[{"message":"permission denied"}]}'
        reason_phrase = "Unauthorized"

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json=None, headers=None):
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    settings = _email_settings(SENDGRID_API_KEY="SG.bad", SENDGRID_FROM_EMAIL="hello@example.com")
    with pytest.raises(EmailDeliveryError, match="SendGrid error 401"):
        asyncio.run(send_email("Subject", "Body", ["user@example.com"], settings))


def test_send_email_unconfigured_raises() -> None:
    import asyncio

    from app.email_delivery import EmailDeliveryError, send_email

    settings = _email_settings()
    with pytest.raises(EmailDeliveryError, match="not configured"):
        asyncio.run(send_email("Subject", "Body", ["user@example.com"], settings))


def test_email_templates_cover_product_surfaces() -> None:
    from app import email_templates as t

    assert t.welcome("http://x")[0]
    assert t.verify_email("http://x/v")[0]
    assert t.password_changed()[0]
    assert t.password_reset("http://x/r")[0]
    assert t.contact_ops_notify(name="A", email="a@b.c", topic="general", message="hi", contact_id="1")[0]
    assert t.contact_ack(name="A")[0]
    assert t.workspace_added(workspace_name="W", role="editor", app_base_url="http://x")[0]
    assert t.client_access_granted(client_name="C", role="client", app_base_url="http://x")[0]
    assert t.subscription_active(plan="studio", app_base_url="http://x")[0]
    assert t.payment_failed(app_base_url="http://x")[0]
    assert t.credit_pack_purchased(pack_label="Video 10", app_base_url="http://x")[0]
    assert t.review_requested(title="T", summary=None, app_base_url="http://x")[0]
    assert t.share_link(title="T", share_url="http://x/s", sender_email="a@b.c")[0]
    assert t.report_published(title="T", client_name="C", app_base_url="http://x")[0]
    assert t.render_complete(project_title="P", studio_url="http://x")[0]
    assert t.render_failed(project_title="P", error="boom", studio_url="http://x")[0]
    assert t.account_disabled()[0]


def test_safe_send_email_returns_false_when_unconfigured() -> None:
    import asyncio

    from app.email_notify import safe_send_email

    sent, err = asyncio.run(safe_send_email("S", "B", ["a@b.com"], _email_settings()))
    assert sent is False
    assert err and "not configured" in err

def test_media_public_marketing_key_and_signing() -> None:
    from app.media_signing import media_signature, verify_media_signature
    from app.media_store import is_public_marketing_key, public_url_for_key

    settings = Settings(JWT_SIGNING_KEY='test-signing-key-that-is-long-enough')
    assert is_public_marketing_key('examples/avatars/maya.jpg')
    assert not is_public_marketing_key('play/secret.mp4')
    assert public_url_for_key('play/secret.mp4', settings) == '/api/media/play/secret.mp4'
    exp = 9_999_999_999
    sig = media_signature('play/secret.mp4', exp, settings)
    assert verify_media_signature('play/secret.mp4', exp, sig, settings)
    assert not verify_media_signature('play/other.mp4', exp, sig, settings)
