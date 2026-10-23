"""Prompting and server-side settling for the Create pre-flight conversation.

Split from the route so the rules stay readable and testable without HTTP. The
planner proposes; everything here decides. Anything that costs credits or that a
user would be annoyed to discover after paying is clamped on this side.
"""
from __future__ import annotations

from app.routers.play_video_helpers import (
    TOPIC_ONLY_AUTO_SECONDS,
    ensure_listener_look,
    ensure_talking_frame,
    estimate_speech_seconds,
    strip_says_marker,
)
from app.schemas.play import PlayAssistDraft, PlayAssistMessage, PlayAssistSource

# Two assistant turns is enough to draft a line and confirm one assumption. More
# than that and the pre-flight is costing more attention than the clip is worth.
ASSIST_MAX_TURNS = 3

_COMMON = (
    "You help someone set up one short vertical clip before it is generated. "
    "Keep their language, product names, and claims. "
    "Never invent offers, prices, discounts, statistics, or facts they did not give you. "
    "Be brief: one or two sentences, no lists, no markdown, no em dashes. "
    "Ask at most one question per reply, and only when the answer would change the clip. "
    "Prefer stating an assumption over asking. "
    'Reply with JSON only: {"reply": str, "draft": {"scene": str, "line": str, '
    '"duration_seconds": int}, "ready": bool, "options": {"header": str, '
    '"choices": [{"label": str, "value": str, "selected": bool}]}}. '
    '"ready" is true when the clip could be generated as it stands. '
    # Options are an accept-or-override on a decision already taken, never a
    # question that blocks. Most people are in a hurry and every required tap is
    # somewhere to give up.
    '"options" is optional and holds at most one decision you already made for them: '
    "mark your pick selected, offer up to three alternatives, and keep every label "
    "under four words. Omit it when nothing is genuinely open."
)

# Short-form formats are recognisable shapes with their own shot language, not
# descriptions of a room. Read literally, "pov: ur crush texts back" became a
# person standing in a place called pov. This lives with the planner rather than
# the prompt builder on purpose: the planner can ask what the clip should show,
# and AGENTS.md keeps scene-specific notes out of the builder.
_FORMATS = (
    "Short-form formats carry their own staging. If the request names one, translate it into "
    "concrete scene and shot language instead of repeating the label: "
    "pov is a first person point of view on the viewer, "
    "grwm is getting ready with a mirror or close framing, "
    "storytime is talking straight to camera with a hook, "
    "day in my life is a moment from that day rather than the whole day, "
    "part 2 and reply to someone continue an earlier video, so ask what came first. "
    "Never put the label itself, a hashtag, or an @handle in the scene or the line. "
    "When the request is explicit about staging, their wording wins."
)

_MODE_RULES = {
    "avatar": (
        "This is a talking clip: one person saying one line. "
        "The scene is place, light, wardrobe, and one simple action. "
        "If they are speaking to someone in the scene, put that in the scene in one short "
        "sentence: they look at that person, not past them and not at the camera. "
        "If they did not name a camera, add one short sentence: shot at eye level, not from "
        "above, face large in the frame. Do not ask them. Do not write a shot list or blur "
        "notes. If they named a drone, a wide, or a full figure, keep theirs. "
        "Their wording for place and clothes wins. "
        "If they gave a topic but no words, write the line for them and say so in the reply. "
        "Keep the line natural spoken words with the hook first. "
        "Never cut, trim, or shorten the line to hit a length. "
        "Set duration_seconds so the spoken line fits (4 to 30)."
    ),
    "video": (
        "This is a scene, not a talking head, and it may have more than one person. "
        "Put everything in 'scene': subject, motion, camera, lighting, pace. "
        "Leave 'line' empty. Quoted dialogue belongs inside the scene text. "
        "If people are talking to each other, add one short sentence that they look at "
        "the person they are talking to, not past them and not at the camera, unless it "
        "is a presenter clip. Do not write a shot list."
    ),
    "image": (
        "This is a single still. Put subject, composition, lighting, and style in 'scene'. "
        "Leave 'line' empty. There is no speech and no motion."
    ),
}


_SOURCE_RULES = {
    "continue": (
        "This continues an existing clip. The previous prompt is given. Propose what happens "
        "next as a new beat, not a repeat, and keep the same person, place, wardrobe, and "
        "camera language unless they ask to change it."
    ),
    "revoice": (
        "This puts new words over a face from an existing clip. Only the script changes: "
        "do not describe a scene, a camera, or an action, because every word is read aloud."
    ),
    "retry": (
        "The previous attempt failed and the reason is given. Work out what in the request "
        "caused it and offer a version that avoids it. Say plainly what you changed. "
        "If the reason is not something a prompt can fix, say so rather than guessing."
    ),
}


def source_rules(kind: str | None) -> str:
    return _SOURCE_RULES.get(kind or "", "")


def system_prompt(mode: str, *, forced_ready: bool = False, source_kind: str | None = None) -> str:
    if mode == "lipsync":
        mode = "avatar"
    rules = _MODE_RULES.get(mode, _MODE_RULES["video"])
    follow_on = source_rules(source_kind)
    if follow_on:
        rules = f"{rules} {follow_on}"
    tail = (
        " This is the last exchange: stop asking questions, settle the draft, and set ready true."
        if forced_ready
        else ""
    )
    return f"{_COMMON} {rules} {_FORMATS}{tail}"


def transcript_for(
    draft: PlayAssistDraft,
    messages: list[PlayAssistMessage],
    *,
    mode: str,
    source: PlayAssistSource | None = None,
) -> list[dict[str, str]]:
    """Conversation with the current draft stated first.

    The draft leads rather than trailing, so a long back and forth cannot push
    the thing being edited out of the model's attention.
    """
    state = [f"Mode: {mode}"]
    if draft.kind:
        state.append(f"Kind: {draft.kind}")
    if draft.scene.strip():
        state.append(f"Scene: {draft.scene.strip()}")
    if draft.line.strip():
        state.append(f"Line: {draft.line.strip()}")
    else:
        state.append("Line: (none yet)")
    if draft.duration_seconds:
        state.append(f"Length: {draft.duration_seconds}s")
    if source is not None:
        prior = (source.prompt or "").strip()
        if source.kind == "continue" and prior:
            state.append(f"Previous clip: {prior}")
        if source.kind == "retry":
            if prior:
                state.append(f"Previous clip: {prior}")
            reason = (source.error or "").strip()
            if reason:
                state.append(f"It failed with: {reason}")
        if source.kind == "revoice" and prior:
            state.append(f"Previous clip: {prior}")

    turns: list[dict[str, str]] = [{"role": "user", "content": "\n".join(state)}]
    for m in messages:
        turns.append({"role": m.role, "content": m.content})
    return turns


def settle_draft(
    *,
    current: PlayAssistDraft,
    proposed: PlayAssistDraft,
    mode: str,
    last_user: str = "",
) -> PlayAssistDraft:
    """Turn a proposal into the draft the composer will actually send."""
    from app.routers.play_assist_kind import KIND_VALUES

    if mode == "lipsync":
        mode = "avatar"
    scene = strip_says_marker(proposed.scene or "").strip()
    line = strip_says_marker(proposed.line or "").strip()
    kind = proposed.kind or current.kind
    if kind == "lipsync":
        kind = "avatar"
    if kind not in KIND_VALUES:
        kind = None
    job = mode
    if mode != "image" and kind:
        job = kind

    if job in {"video", "image"}:
        # No spoken half in these modes; anything the planner put there is scene.
        if line and not scene:
            scene, line = line, ""
        else:
            line = ""

    seconds = proposed.duration_seconds or current.duration_seconds

    if job == "avatar":
        if line:
            joined = f"{scene}. says: {line}" if scene else f"says: {line}"
            seconds = estimate_speech_seconds(joined)
        elif not seconds:
            seconds = TOPIC_ONLY_AUTO_SECONDS

    if job in {"avatar", "video"}:
        scene = ensure_listener_look(scene)
    if job == "avatar":
        scene = ensure_talking_frame(scene)

    model = None
    resolution = None
    extend_rest = False
    platform = current.platform
    if job in {"avatar", "video"}:
        from app.routers.play_assist_lane import settle_clip_lane

        model, resolution, lane_seconds, extend_rest, asked_platform = settle_clip_lane(
            kind=job,
            scene=scene,
            line=line,
            last_user=last_user,
            asked_model=proposed.model or current.model,
            asked_resolution=proposed.resolution or current.resolution,
        )
        seconds = lane_seconds
        if asked_platform:
            platform = asked_platform

    return PlayAssistDraft(
        scene=scene,
        line=line,
        duration_seconds=seconds,
        voice=current.voice,
        kind=None if job == "image" else kind or (job if job in KIND_VALUES else None),
        model=model,
        resolution=resolution,
        extend_rest=extend_rest,
        platform=platform,
    )


def build_summary(draft: PlayAssistDraft, *, mode: str) -> list[str]:
    """Server-stated facts for the confirm card. Never model text.

    The user is about to spend credits, so what they read has to be what the
    generate call will do, not what a chat reply claimed it would do.
    """
    bits: list[str] = []
    job = (draft.kind or mode or "").strip().lower()
    if job == "lipsync":
        job = "avatar"
    if job == "avatar":
        bits.append("Talking")
    elif job == "image":
        bits.append("Still")
    else:
        bits.append("Scene")

    mid = (draft.model or "").lower()
    if "2-5" in mid or mid in {"seedance-avatar", "seedance-2-5"}:
        bits.append("2.5")
    elif job != "image":
        bits.append("Fast")
    if draft.resolution and job != "image":
        bits.append(draft.resolution)

    if draft.duration_seconds:
        bits.append(f"~{draft.duration_seconds}s")

    if draft.extend_rest:
        bits.append("then Extend")
    return bits
