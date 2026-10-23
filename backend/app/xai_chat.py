"""xAI chat-completions text calls (prompt polish)."""
from __future__ import annotations

import re
from typing import Any

import httpx

from app.config import Settings
from app.xai_media import provider_error_message


class XaiChatError(RuntimeError):
    pass


_FENCE_RE = re.compile(r"^\s*```[a-zA-Z]*\s*|\s*```\s*$")
_DASH_RE = re.compile(r"\s*[—–]\s*")


def _clean_completion(text: str) -> str:
    """Strip the wrappers models add around a bare string."""
    cleaned = _FENCE_RE.sub("", text or "").strip()
    if len(cleaned) >= 2 and cleaned[0] in "\"'“" and cleaned[-1] in "\"'”":
        cleaned = cleaned[1:-1].strip()
    # Product copy rule: no em or en dashes in user-facing text.
    cleaned = _DASH_RE.sub(", ", cleaned)
    return cleaned.strip()


async def xai_chat_raw(
    *,
    system: str,
    messages: list[dict[str, str]],
    settings: Settings,
    temperature: float = 0.4,
    max_tokens: int = 700,
) -> str:
    """Multi-turn completion returned verbatim.

    ``xai_chat_text`` cleans the reply for direct display: it strips fences and
    surrounding quotes and rewrites dashes. That is wrong for a structured reply
    the caller has to parse, so this returns the raw content and leaves the
    interpretation to the caller.
    """
    return await _post_chat(
        system=system,
        messages=messages,
        settings=settings,
        temperature=temperature,
        max_tokens=max_tokens,
        clean=False,
    )


async def xai_chat_text(
    *,
    system: str,
    user: str,
    settings: Settings,
    temperature: float = 0.4,
    max_tokens: int = 350,
) -> str:
    return await _post_chat(
        system=system,
        messages=[{"role": "user", "content": user}],
        settings=settings,
        temperature=temperature,
        max_tokens=max_tokens,
        clean=True,
    )


async def _post_chat(
    *,
    system: str,
    messages: list[dict[str, str]],
    settings: Settings,
    temperature: float,
    max_tokens: int,
    clean: bool,
) -> str:
    if not settings.xai_api_key:
        raise XaiChatError("xAI is not configured")

    payload: dict[str, Any] = {
        "model": settings.xai_text_model,
        "messages": [{"role": "system", "content": system}, *messages],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            response = await client.post(
                settings.xai_chat_url,
                headers={"Authorization": f"Bearer {settings.xai_api_key}"},
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise XaiChatError(f"xAI request failed: {exc}") from exc

    try:
        data = response.json()
    except ValueError:
        data = {}

    if response.status_code >= 400:
        detail = provider_error_message(data) or f"HTTP {response.status_code}"
        raise XaiChatError(f"xAI chat error: {detail}")

    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise XaiChatError("xAI returned no choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    text = str(content or "")
    result = _clean_completion(text) if clean else text.strip()
    if not result:
        raise XaiChatError("xAI returned empty content")
    return result
