"""Best-effort delete for leftover xAI custom voices (legacy workspace rows).

New clones use ElevenLabs. Keep this thin so old provider_voice_id values can
still be torn down on user delete.
"""
from __future__ import annotations

import httpx

from app.config import Settings


class XaiCustomVoiceError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


async def delete_custom_voice(voice_id: str, settings: Settings) -> None:
    """DELETE /v1/custom-voices/{voice_id}. Ignores 404. No-op without an xAI key."""
    key = (voice_id or "").strip()
    if not key:
        return
    if not settings.xai_api_key:
        return
    url = f"https://api.x.ai/v1/custom-voices/{key}"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.delete(
            url,
            headers={"Authorization": f"Bearer {settings.xai_api_key}"},
        )
    if response.status_code in (200, 204, 404):
        return
    raise XaiCustomVoiceError(
        f"xAI custom voice delete failed with HTTP {response.status_code}",
        status_code=response.status_code,
    )


__all__ = ["XaiCustomVoiceError", "delete_custom_voice"]
