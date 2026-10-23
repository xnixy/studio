"""Hidden Talking composition still. Not a Face. Not billed. Not in Library.

Seedance invents a camera and a body when Talking only sends a head-and-shoulders
Face. This still is built from that Face plus the user's scene, then attached as
@Image2. Scene text owns place, clothes, pose, and camera. House does not
prescribe eye-level, 3/4, or a fisheye ban. If this fails, Talking still runs.
"""
from __future__ import annotations

import logging
import uuid

from app.config import Settings
from app.image_providers import GeneratedImage, persist_generated_image
from app.media_store import assert_media_reachable, public_media_url
from app.xai_media import edit_xai_image

log = logging.getLogger(__name__)

CLIP_STILL_MODEL = "grok-imagine-image-2.0"


def clip_still_prompt(*, scene: str) -> str:
    """Place, clothes, pose, and camera come only from the scene text."""
    place = (scene or "").strip() or "a simple real-life setting"
    return (
        "Photorealistic still of the same person as the source photo. "
        "Follow the scene text for place, clothes, pose, and camera. "
        "Do not invent a camera, lens, or how much of the body is in frame "
        "beyond what the scene writes. "
        "Mouth closed, at rest. Deep focus, whole frame sharp, no text, no watermark. "
        f"Scene: {place}"
    )


async def generate_talking_clip_still(
    *,
    face_image_url: str,
    scene: str,
    aspect_ratio: str,
    settings: Settings,
) -> str | None:
    """Return a public HTTPS still URL, or None so generate can continue."""
    source = (face_image_url or "").strip()
    if not source or not settings.xai_api_key:
        return None
    ratio = (aspect_ratio or "9:16").strip() or "9:16"
    try:
        public_face = await assert_media_reachable(source, settings, label="Face plate")
        result = await edit_xai_image(
            prompt=clip_still_prompt(scene=scene),
            image_url=public_face,
            settings=settings,
            model=CLIP_STILL_MODEL,
            aspect_ratio=ratio,
            resolution="1k",
        )
        generated = GeneratedImage(
            provider="xai",
            model=result.model or CLIP_STILL_MODEL,
            model_id=CLIP_STILL_MODEL,
            url=result.url,
            content=None,
            mime_type=None,
            cost_usd_ticks=result.cost_usd_ticks,
            raw=result.raw,
        )
        stored = await persist_generated_image(
            result=generated,
            settings=settings,
            subdir="clip-stills",
            stem=uuid.uuid4(),
        )
        public = await assert_media_reachable(
            public_media_url(stored, settings), settings, label="Clip still"
        )
        return public
    except Exception:
        log.warning("talking clip still failed; continuing without it", exc_info=True)
        return None
