from __future__ import annotations

import shutil
import subprocess
import re
from pathlib import Path

from app.config import Settings
from app.media_store import MediaStoreError, ensure_local_media, store_file
from app.models import VideoAsset, VideoProject, VideoRender, VideoScene


class VideoRenderError(RuntimeError):
    pass


DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def ffmpeg_path() -> str | None:
    system_binary = shutil.which("ffmpeg")
    if system_binary:
        return system_binary

    try:
        from imageio_ffmpeg import get_ffmpeg_exe
    except ImportError:
        return None

    packaged_binary = get_ffmpeg_exe()
    if packaged_binary and Path(packaged_binary).exists():
        return packaged_binary
    return None


def ready_scene_video_assets(project: VideoProject) -> list[VideoAsset]:
    scene_order = {scene.id: scene.sequence_index for scene in project.scenes}
    videos = [
        asset
        for asset in project.assets
        if asset.asset_type == "video" and asset.status == "ready" and asset.video_scene_id in scene_order and (asset.storage_url or asset.provider_url)
    ]
    return sorted(videos, key=lambda asset: (scene_order.get(asset.video_scene_id, 0), getattr(asset, "source", None) == "sync_labs", asset.created_at))


def selected_scene_video_assets(project: VideoProject) -> list[tuple[VideoScene, VideoAsset]]:
    scenes = sorted(project.scenes, key=lambda item: item.sequence_index)
    latest_by_scene: dict[object, VideoAsset] = {}
    for asset in ready_scene_video_assets(project):
        latest_by_scene[asset.video_scene_id] = asset

    missing = [str(scene.sequence_index + 1) for scene in scenes if scene.id not in latest_by_scene]
    if missing:
        raise VideoRenderError(f"Every scene needs a ready persisted video clip before rendering. Missing scene clip(s): {', '.join(missing)}")

    return [(scene, latest_by_scene[scene.id]) for scene in scenes]


def render_output_path(render: VideoRender, settings: Settings) -> Path:
    output_dir = settings.media_path / "renders"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{render.id}.mp4"


def caption_text_for_scene(scene: VideoScene) -> str:
    # Prefer spoken narration for burn-in/subtitles so cards match the voiceover, not the visual direction.
    return (scene.spoken_text or scene.on_screen_text or scene.visual_prompt or "").strip()


def sync_scene_timings_to_total(project: VideoProject, total_seconds: float) -> None:
    scenes = sorted(project.scenes, key=lambda item: item.sequence_index)
    if not scenes or total_seconds <= 0:
        return

    total_ms = max(len(scenes), round(total_seconds * 1000))
    current_durations = [max(1, scene.end_time_ms - scene.start_time_ms) for scene in scenes]
    current_total = sum(current_durations)
    cursor = 0
    for index, scene in enumerate(scenes):
        scene.start_time_ms = cursor
        if index == len(scenes) - 1:
            scene.end_time_ms = total_ms
        else:
            remaining_scenes = len(scenes) - index - 1
            next_cursor = round(sum(current_durations[: index + 1]) / current_total * total_ms)
            scene.end_time_ms = min(max(cursor + 1, next_cursor), total_ms - remaining_scenes)
        cursor = scene.end_time_ms


def scene_duration_seconds(scene: VideoScene) -> float:
    return max(0.001, (scene.end_time_ms - scene.start_time_ms) / 1000)


def caption_rows(project: VideoProject) -> list[tuple[int, int, str]]:
    rows = []
    for scene in sorted(project.scenes, key=lambda item: item.sequence_index):
        text = caption_text_for_scene(scene)
        if text:
            rows.append((scene.start_time_ms, scene.end_time_ms, text))
    return rows


def vtt_timestamp(milliseconds: int) -> str:
    total_ms = max(0, int(milliseconds))
    hours = total_ms // 3_600_000
    total_ms %= 3_600_000
    minutes = total_ms // 60_000
    total_ms %= 60_000
    seconds = total_ms // 1000
    ms = total_ms % 1000
    return f"{hours:02}:{minutes:02}:{seconds:02}.{ms:03}"


def ass_timestamp(milliseconds: int) -> str:
    total_ms = max(0, int(milliseconds))
    hours = total_ms // 3_600_000
    total_ms %= 3_600_000
    minutes = total_ms // 60_000
    total_ms %= 60_000
    seconds = total_ms // 1000
    centiseconds = (total_ms % 1000) // 10
    return f"{hours}:{minutes:02}:{seconds:02}.{centiseconds:02}"


def ass_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")


def write_caption_sidecars(
    project: VideoProject,
    render: VideoRender,
    settings: Settings,
    rows: list[tuple[int, int, str]] | None = None,
) -> dict[str, str]:
    output_dir = settings.media_path / "renders"
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = rows if rows is not None else caption_rows(project)
    if not rows:
        return {}

    vtt_path = output_dir / f"{render.id}.vtt"
    srt_path = output_dir / f"{render.id}.srt"
    vtt_body = ["WEBVTT", ""]
    srt_body: list[str] = []
    for index, (start, end, text) in enumerate(rows, start=1):
        vtt_body.extend([f"{vtt_timestamp(start)} --> {vtt_timestamp(end)}", text, ""])
        srt_body.extend(
            [
                str(index),
                f"{vtt_timestamp(start).replace('.', ',')} --> {vtt_timestamp(end).replace('.', ',')}",
                text,
                "",
            ]
        )
    vtt_path.write_text("\n".join(vtt_body), encoding="utf-8")
    srt_path.write_text("\n".join(srt_body), encoding="utf-8")
    return {
        "captions_vtt_url": store_file(path=vtt_path, settings=settings, content_type="text/vtt"),
        "captions_srt_url": store_file(path=srt_path, settings=settings, content_type="application/x-subrip"),
    }


def write_burn_in_ass(
    project: VideoProject,
    render: VideoRender,
    settings: Settings,
    rows: list[tuple[int, int, str]] | None = None,
) -> Path | None:
    rows = rows if rows is not None else caption_rows(project)
    if not rows:
        return None

    output_dir = settings.media_path / "renders"
    output_dir.mkdir(parents=True, exist_ok=True)
    ass_path = output_dir / f"{render.id}.burnin.ass"
    body = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Arial,64,&H00FFFFFF,&H000000FF,&HCC000000,&H99000000,1,0,0,0,100,100,0,0,1,4,1,2,80,80,150,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for start, end, text in rows:
        body.append(f"Dialogue: 0,{ass_timestamp(start)},{ass_timestamp(end)},Default,,0,0,0,,{ass_text(text)}")
    ass_path.write_text("\n".join(body) + "\n", encoding="utf-8")
    return ass_path


def ffmpeg_filter_path(path: Path) -> str:
    value = path.resolve().as_posix()
    return value.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def media_duration_seconds(path: Path) -> float | None:
    binary = ffmpeg_path()
    if not binary:
        raise VideoRenderError("FFmpeg is not available in this environment")

    result = subprocess.run([binary, "-hide_banner", "-i", str(path)], capture_output=True, text=True, timeout=15, check=False)
    text = f"{result.stderr}\n{result.stdout}"
    match = DURATION_RE.search(text)
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def burn_in_captions(
    project: VideoProject,
    render: VideoRender,
    settings: Settings,
    source_path: Path,
    rows: list[tuple[int, int, str]] | None = None,
) -> bool:
    binary = ffmpeg_path()
    if not binary:
        raise VideoRenderError("FFmpeg is not available in this environment")

    ass_path = write_burn_in_ass(project, render, settings, rows=rows)
    if ass_path is None:
        return False

    captioned_path = source_path.with_suffix(".captioned.mp4")
    command = [
        binary,
        "-y",
        "-i",
        str(source_path),
        "-vf",
        f"subtitles='{ffmpeg_filter_path(ass_path)}'",
        "-c:v",
        "libx264",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(captioned_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
    if result.returncode != 0:
        raise VideoRenderError(f"FFmpeg caption burn-in failed: {(result.stderr or result.stdout)[-800:]}")
    captioned_path.replace(source_path)
    return True


def local_scene_video_paths(project: VideoProject, settings: Settings) -> list[tuple[VideoScene, Path]]:
    scene_paths: list[tuple[VideoScene, Path]] = []
    for scene, asset in selected_scene_video_assets(project):
        url = asset.storage_url or asset.provider_url
        if not url:
            continue
        try:
            path = ensure_local_media(url, settings)
        except MediaStoreError as exc:
            raise MediaStoreError(f"Scene {scene.sequence_index + 1} video is not available for rendering: {exc}") from exc
        scene_paths.append((scene, path))
    return scene_paths


def local_video_paths(project: VideoProject, settings: Settings) -> list[Path]:
    return [path for _, path in local_scene_video_paths(project, settings)]


def write_concat_file(paths: list[Path], concat_path: Path) -> None:
    lines = []
    for path in paths:
        escaped = path.resolve().as_posix().replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    concat_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def extract_video_poster_frame(
    source_path: Path,
    output_path: Path,
    *,
    at_seconds: float = 0.4,
) -> None:
    """Grab one JPEG frame from a video for list thumbnails / poster stills."""
    binary = ffmpeg_path()
    if not binary:
        raise VideoRenderError("FFmpeg is not available in this environment")
    if not source_path.exists():
        raise VideoRenderError(f"Source video missing: {source_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Seek before -i for speed; slight offset avoids pure-black first frames.
    seek = max(0.0, float(at_seconds))
    command = [
        binary,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{seek:.2f}",
        "-i",
        str(source_path),
        "-frames:v",
        "1",
        "-q:v",
        "3",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    if result.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
        # Retry from t=0 if mid-seek failed (very short clips).
        command[command.index(f"{seek:.2f}")] = "0"
        result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    if result.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
        detail = (result.stderr or result.stdout or "").strip()[:300]
        raise VideoRenderError(f"Failed to extract poster frame: {detail or 'unknown ffmpeg error'}")


def mp4_has_faststart(path: Path, *, probe_bytes: int = 2 * 1024 * 1024) -> bool:
    """True when the moov box appears before mdat (progressive-stream friendly).

    iOS AVPlayer progressive HTTP play requires moov near the start. Provider MP4s
    often leave moov at the end; those need ``remux_mp4_faststart``.
    """
    if not path.exists() or path.stat().st_size == 0:
        return False
    with path.open("rb") as fh:
        data = fh.read(probe_bytes)
    i = 0
    n = len(data)
    while i + 8 <= n:
        size = int.from_bytes(data[i : i + 4], "big")
        typ = data[i + 4 : i + 8]
        if typ == b"moov":
            return True
        if typ == b"mdat":
            # Media data before moov → not faststart.
            return False
        if size == 0:
            break
        if size == 1:
            # 64-bit extended size
            if i + 16 > n:
                break
            size = int.from_bytes(data[i + 8 : i + 16], "big")
            if size < 16:
                break
        elif size < 8:
            break
        i += size
    # moov not in probe window and mdat not seen early — treat as not ready for stream.
    return False


def remux_mp4_faststart(source_path: Path, output_path: Path | None = None) -> Path:
    """Move the MP4 moov atom to the start for progressive HTTP streaming (iOS AVPlayer).

    Provider downloads often leave moov at the end; AVPlayer then fails or stalls on
    Range-based progressive play. Stream-copy remux is cheap when ffmpeg is available.
    Returns the path written (``output_path`` or an in-place sibling). On failure raises
    ``VideoRenderError`` so callers can keep the original bytes.
    """
    binary = ffmpeg_path()
    if not binary:
        raise VideoRenderError("FFmpeg is not available in this environment")
    if not source_path.exists() or source_path.stat().st_size == 0:
        raise VideoRenderError(f"Source video missing: {source_path}")
    if mp4_has_faststart(source_path):
        return source_path
    dest = output_path or source_path.with_name(f"{source_path.stem}.faststart{source_path.suffix}")
    command = [
        binary,
        "-y",
        "-i",
        str(source_path),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
    if result.returncode != 0 or not dest.exists() or dest.stat().st_size == 0:
        detail = (result.stderr or result.stdout or "").strip()[-400:]
        raise VideoRenderError(f"FFmpeg faststart remux failed: {detail or 'unknown error'}")
    if not mp4_has_faststart(dest):
        raise VideoRenderError("FFmpeg faststart remux completed but moov is still not at start")
    return dest


def strip_audio_from_video(source_path: Path, output_path: Path) -> None:
    """Drop provider-baked audio so scene clips stay silent until our voiceover is mixed at export."""
    binary = ffmpeg_path()
    if not binary:
        raise VideoRenderError("FFmpeg is not available in this environment")
    if not source_path.exists():
        raise VideoRenderError(f"Source video missing: {source_path}")
    command = [
        binary,
        "-y",
        "-i",
        str(source_path),
        "-an",
        "-c:v",
        "copy",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
    if result.returncode != 0:
        # Re-encode if stream copy fails (odd codecs).
        command = [
            binary,
            "-y",
            "-i",
            str(source_path),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
    if result.returncode != 0:
        raise VideoRenderError(f"FFmpeg audio strip failed: {(result.stderr or result.stdout)[-800:]}")


def normalize_scene_clip(binary: str, source_path: Path, output_path: Path, duration_seconds: float) -> None:
    command = [
        binary,
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(source_path),
        "-t",
        f"{duration_seconds:.3f}",
        "-an",
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
    if result.returncode != 0:
        raise VideoRenderError(f"FFmpeg scene normalization failed: {(result.stderr or result.stdout)[-800:]}")


def render_concat_mp4(
    project: VideoProject,
    render: VideoRender,
    settings: Settings,
    audio_path: Path | None = None,
    caption_override_rows: list[tuple[int, int, str]] | None = None,
) -> tuple[Path, str, bool, dict[str, object]]:
    binary = ffmpeg_path()
    if not binary:
        raise VideoRenderError("FFmpeg is not available in this environment")

    sync_metadata: dict[str, object] = {"scene_timing_source": "project_timeline"}
    if audio_path:
        if not audio_path.exists():
            raise VideoRenderError("Voiceover audio file is missing")
        audio_duration = media_duration_seconds(audio_path)
        if audio_duration:
            sync_scene_timings_to_total(project, audio_duration)
            sync_metadata = {"scene_timing_source": "voiceover_audio", "voiceover_duration_seconds": round(audio_duration, 3)}

    inputs = local_scene_video_paths(project, settings)
    if not inputs:
        raise VideoRenderError("No ready persisted scene video clips are available to render")
    sync_metadata["normalized_scene_count"] = len(inputs)
    sync_metadata["scene_timings"] = [
        {
            "scene_id": str(scene.id),
            "sequence_index": scene.sequence_index,
            "start_time_ms": scene.start_time_ms,
            "end_time_ms": scene.end_time_ms,
        }
        for scene, _ in inputs
    ]

    output_path = render_output_path(render, settings)
    concat_output_path = output_path.with_suffix(".video-only.mp4") if audio_path else output_path
    concat_path = output_path.with_suffix(".concat.txt")
    normalized_inputs: list[Path] = []
    for index, (scene, source_path) in enumerate(inputs, start=1):
        segment_path = output_path.with_suffix(f".scene-{index}.mp4")
        normalize_scene_clip(binary, source_path, segment_path, scene_duration_seconds(scene))
        normalized_inputs.append(segment_path)

    write_concat_file(normalized_inputs, concat_path)

    command = [
        binary,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        "-c",
        "copy",
        str(concat_output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
    if result.returncode != 0:
        fallback = [
            binary,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(concat_output_path),
        ]
        result = subprocess.run(fallback, capture_output=True, text=True, timeout=600, check=False)
    if result.returncode != 0:
        raise VideoRenderError(f"FFmpeg render failed: {(result.stderr or result.stdout)[-800:]}")
    if audio_path:
        mux_command = [
            binary,
            "-y",
            "-i",
            str(concat_output_path),
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        result = subprocess.run(mux_command, capture_output=True, text=True, timeout=600, check=False)
        if result.returncode != 0:
            raise VideoRenderError(f"FFmpeg audio mix failed: {(result.stderr or result.stdout)[-800:]}")
    captions_burned_in = burn_in_captions(project, render, settings, output_path, rows=caption_override_rows)
    output_url = store_file(path=output_path, settings=settings, content_type="video/mp4")
    return output_path, output_url, captions_burned_in, sync_metadata
