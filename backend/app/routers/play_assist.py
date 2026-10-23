"""Conversational pre-flight for Create: settle the clip before anyone pays.

Rules own kind, chips, length, and the confirm summary. Grok only drafts a
spoken line when the user gave a topic and no words. Nothing here reserves
credits or touches a provider that costs money.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.intimate_contact import intimate_contact_refusal
from app.database import get_session
from app.dependencies import get_current_user
from app.models import User
from app.rate_limit_deps import enforce_rate_limit
from app.routers.play_assist_kind import (
    KIND_AVATAR,
    KIND_VIDEO,
    build_clip_reply,
    classify_clip_kind,
    clip_kind_options,
    is_kind_chip,
    last_user_text,
    line_draft_system_prompt,
    merge_clip_fields,
    needs_line_draft,
)
from app.routers.play_assist_rules import (
    ASSIST_MAX_TURNS,
    build_summary,
    settle_draft,
    transcript_for,
)
from app.schemas.play import (
    PlayAssistChoice,
    PlayAssistDraft,
    PlayAssistOptions,
    PlayAssistRequest,
    PlayAssistResponse,
)
from app.workspace_access import require_permission
from app.xai_chat import XaiChatError, xai_chat_raw

logger = logging.getLogger(__name__)

router = APIRouter()

ASSIST_RATE_LIMIT = 90
ASSIST_RATE_WINDOW_SECONDS = 60


def _parse_reply(raw: str) -> dict:
    """Read the planner's JSON answer, tolerating fences and stray prose."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return {}
    try:
        parsed = json.loads(text[start : end + 1])
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _settle_options(raw: object) -> PlayAssistOptions | None:
    """Read a model-offered choice block, or nothing if it is unusable."""
    if not isinstance(raw, dict):
        return None
    header = str(raw.get("header") or "").strip()[:32]
    rows = raw.get("choices")
    if not header or not isinstance(rows, list):
        return None
    choices: list[PlayAssistChoice] = []
    for row in rows[:4]:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or "").strip()[:48]
        value = str(row.get("value") or label).strip()[:200]
        if not label:
            continue
        choices.append(PlayAssistChoice(label=label, value=value, selected=bool(row.get("selected"))))
    if len(choices) < 2:
        return None
    if not any(c.selected for c in choices):
        choices[0].selected = True
    return PlayAssistOptions(header=header, choices=choices)


def fallback_when_line_draft_fails(
    *,
    kind: str,
    draft: PlayAssistDraft,
    last_user: str,
) -> tuple[str, PlayAssistDraft]:
    """Grok is a free helper. A miss must not block generate.

    Talking 422s without a spoken line, so topic-only Talking becomes A scene.
    """
    if kind == KIND_AVATAR and not draft.line.strip():
        kind = KIND_VIDEO
        draft = settle_draft(
            current=draft,
            proposed=PlayAssistDraft(
                scene=draft.scene or last_user,
                line="",
                duration_seconds=draft.duration_seconds,
                voice=draft.voice,
                kind=kind,
            ),
            mode=kind,
            last_user=last_user,
        )
    return kind, draft


def _ready_for(draft: PlayAssistDraft, *, mode: str, kind: str | None) -> bool:
    if mode == "image":
        return bool(draft.scene.strip())
    job = kind or mode
    if job == KIND_AVATAR:
        return bool(draft.line.strip())
    if job == KIND_VIDEO:
        return bool(draft.scene.strip() or draft.line.strip())
    return bool(draft.scene.strip() or draft.line.strip())


@router.post("/assist", response_model=PlayAssistResponse)
async def play_assist(
    body: PlayAssistRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PlayAssistResponse:
    """Talk a draft into shape. Costs no credits by design."""
    await require_permission(session, body.workspace_id, user, "projects.write")
    await enforce_rate_limit(
        request,
        f"play.assist:user:{user.id}",
        ASSIST_RATE_LIMIT,
        ASSIST_RATE_WINDOW_SECONDS,
        "That is a lot of back and forth. Wait a moment and try again.",
    )

    if not (
        body.draft.scene.strip() or body.draft.line.strip() or body.messages or body.source
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Describe the clip first",
        )

    last_user = last_user_text(body.messages)
    source_prompt = body.source.prompt if body.source else ""
    refused = intimate_contact_refusal(
        last_user,
        body.draft.scene,
        body.draft.line,
        source_prompt,
        *(m.content for m in body.messages if m.role == "user"),
    )
    if refused:
        return PlayAssistResponse(
            reply=refused,
            draft=PlayAssistDraft(),
            options=None,
            ready=False,
            summary=[],
        )

    turns = sum(1 for m in body.messages if m.role == "assistant")
    forced_ready = turns >= ASSIST_MAX_TURNS

    if body.mode == "image":
        draft = settle_draft(
            current=body.draft,
            proposed=PlayAssistDraft(
                scene=body.draft.scene or last_user,
                line="",
                duration_seconds=None,
                voice=body.draft.voice,
            ),
            mode="image",
            last_user=last_user,
        )
        reply = "One still. Generate if that is right."
        return PlayAssistResponse(
            reply=reply,
            draft=draft,
            options=None,
            ready=bool(draft.scene.strip()) or forced_ready,
            summary=build_summary(draft, mode="image"),
        )

    kind = classify_clip_kind(
        last_user=last_user,
        draft=body.draft,
        request_mode=body.mode,
        source=body.source,
    )
    scene, line = merge_clip_fields(kind=kind, draft=body.draft, last_user=last_user)
    draft = settle_draft(
        current=body.draft,
        proposed=PlayAssistDraft(
            scene=scene,
            line=line,
            duration_seconds=body.draft.duration_seconds,
            voice=body.draft.voice,
            kind=kind,
        ),
        mode=kind,
        last_user=last_user,
    )

    grok_missed = False
    if needs_line_draft(kind, draft) and not is_kind_chip(last_user) and not forced_ready:
        try:
            raw = await xai_chat_raw(
                system=line_draft_system_prompt(),
                messages=transcript_for(
                    draft, body.messages, mode=kind, source=body.source
                ),
                settings=settings,
            )
        except XaiChatError as exc:
            logger.warning("play.assist provider error: %s", exc)
            grok_missed = True
            raw = ""
        parsed = _parse_reply(raw)
        proposed = parsed.get("draft") if isinstance(parsed.get("draft"), dict) else {}
        draft = settle_draft(
            current=draft,
            proposed=PlayAssistDraft(
                scene=str(proposed.get("scene") or draft.scene or ""),
                line=str(proposed.get("line") or draft.line or ""),
                duration_seconds=draft.duration_seconds,
                voice=draft.voice,
                kind=kind,
            ),
            mode=kind,
            last_user=last_user,
        )
        reply = str(parsed.get("reply") or "").strip() or build_clip_reply(draft, kind=kind)
        if grok_missed or needs_line_draft(kind, draft):
            grok_missed = True
            kind, draft = fallback_when_line_draft_fails(
                kind=kind, draft=draft, last_user=last_user
            )
            reply = "Could not work that out. Generate as written, or send again."
    else:
        reply = build_clip_reply(draft, kind=kind)

    # Max-turn Talking with no line used to keep ready=false forever.
    kind, draft = fallback_when_line_draft_fails(
        kind=kind, draft=draft, last_user=last_user
    )
    ready = _ready_for(draft, mode=body.mode, kind=kind) or forced_ready or grok_missed
    if kind == KIND_AVATAR and not draft.line.strip():
        ready = False

    print(
        f"play.assist kind={kind} grok_missed={grok_missed} ready={ready} "
        f"line={bool(draft.line.strip())} scene={bool(draft.scene.strip())}",
        flush=True,
    )
    return PlayAssistResponse(
        reply=reply[:2000],
        draft=draft,
        options=clip_kind_options(kind),
        ready=ready,
        summary=build_summary(draft, mode=kind),
    )
