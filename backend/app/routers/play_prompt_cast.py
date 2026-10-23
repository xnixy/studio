"""Solo vs listener house rules for Talking and spoken Scene.

A NYC street Talking clip invented a grey-hoodie extra because SPEAKER always
said "a friend is the listener" and ADDRESS was mostly listener language.
Solo scenes must never name a friend. Conversation scenes keep today's lock
so the Face is not recast as the listener.
"""
from __future__ import annotations

import re

_ADDRESSEE_RE = re.compile(
    r"\b("
    r"friends?|across from|across the table|beside (?:her|him|them|you)|"
    r"next to (?:her|him|them|you)|talking (?:to|with)|speaking (?:to|with)|"
    r"talks (?:to|with)|speaks (?:to|with)|asks (?:her|him|them|a |the )|"
    r"person across|someone across"
    r")\b",
    re.I,
)
# "talking to the camera / viewer / you" is presenter address, not a listener.
_CAMERA_ADDRESS_RE = re.compile(
    r"\b(?:talking|speaking|talks|speaks|talk|speak) (?:to|with) "
    r"(?:the )?(?:camera|lens|viewer|audience|you)\b",
    re.I,
)
_LISTENER_LOOK_RE = re.compile(
    r"(?i)\blook(?:s|ing)? at (?:each other|(?:her |his |their )?(?:friend|them|him|her|that person|the person they))"
)
_LISTENER_LOOK_LINE = (
    "They look at the person they are talking to, not past them and not at the camera."
)
# User-named cameras. Do not treat "talking to the camera" as a shot.
_SHOT_ALREADY_RE = re.compile(
    r"(?i)\b("
    r"eye[- ]level|from above|overhead|drone|aerial|bird'?s[- ]eye|"
    r"fisheye|wide shot|wide[- ]angle|full[- ]figure|full[- ]body|"
    r"close[- ]up|closeup|pov|first person|low[- ]angle|high[- ]angle|"
    r"waist[- ]up|medium shot|from the front|from below|selfie|"
    r"3/4|three[- ]quarter"
    r")\b"
)
_TALKING_FRAME_LINE = "Shot at eye level, not from above. Face large in the frame."


def scene_has_addressee(scene: str) -> bool:
    """True when the scene names who the line is spoken to, not a crowd or the lens."""
    cleaned = _CAMERA_ADDRESS_RE.sub(" ", scene or "")
    return bool(_ADDRESSEE_RE.search(cleaned))


def ensure_listener_look(scene: str) -> str:
    """One short look sentence when a listener is in the scene.

    Users write 'talking to a friend'. They will not write camera notes. Assist
    puts this on the draft they see. Generate also injects it so a skipped or
    edited card still lands eyeline in the SCENE text, not only ADDRESS.
    """
    text = (scene or "").strip()
    if not text or not scene_has_addressee(text):
        return text
    if _LISTENER_LOOK_RE.search(text) or "not past them" in text.lower():
        return text
    return f"{text.rstrip('.')} {_LISTENER_LOOK_LINE}"


def scene_has_shot(scene: str) -> bool:
    """True when the scene already names a camera or how much body is in frame."""
    return bool(_SHOT_ALREADY_RE.search(scene or ""))


def ensure_talking_frame(scene: str) -> str:
    """One short default shot on Talking when the user did not name a camera.

    People will not write eye-level. Assist puts this on the draft they see.
    Generate injects it too so a skipped card still has a shot in SCENE.
    A drone, a wide, or a full figure they did write is left alone.
    """
    text = (scene or "").strip()
    if scene_has_shot(text):
        return text
    if "face large in the frame" in text.lower():
        return text
    if not text:
        return _TALKING_FRAME_LINE
    return f"{text.rstrip('.')} {_TALKING_FRAME_LINE}"


def avatar_address_rule(scene: str = "") -> str:
    """Who the line is spoken to. Solo and conversation are different blocks.

    One listener-heavy paragraph made Seedance invent a friend on a solo street
    so it could obey "keep that person visible."
    """
    if scene_has_addressee(scene):
        return (
            "ADDRESS: Hold the eyeline the whole line. They speak to someone in the scene. "
            "Keep that person visible in the shot. The camera may sit off to the side. "
            "Turn her head to their face. If they sit beside her, look at them, not straight "
            "ahead, not past them, not the lens. Never turn to the camera while speaking "
            "with someone in the scene. Never switch eyeline mid-line."
        )
    return (
        "ADDRESS: They speak to the camera the whole line. No second person in the "
        "foreground. Do not invent a friend, interviewer, or over-the-shoulder listener. "
        "Bystanders in a crowd stay in the background and are not the addressee. "
        "Never switch eyeline mid-line."
    )


def avatar_frame_rule() -> str:
    """Do not invent a camera. SCENE owns angle, lens, and how much body is in frame.

    House used to prescribe eye-level / not fisheye after one NYC overhead clip.
    That fights a drone shot, a table-down, a wide walk, or a full-figure ask.
    Same pattern as CAST: do not invent what the scene did not write.
    """
    return (
        "FRAME: Do not invent a camera, lens, or how much of the body is in frame. "
        "Use only what the scene writes."
    )


def avatar_cast_rule(scene: str = "") -> str:
    """Solo only. Conversation already names the other person in SCENE."""
    if scene_has_addressee(scene):
        return ""
    return (
        "CAST: One person in the foreground. Other people stay in the background if "
        "the place has a crowd. Nobody steps into an interview shoulder or becomes a listener."
    )


def avatar_speaker_rule(
    *,
    image_tag: str,
    scene: str = "",
    talking: bool = False,
    speaking: bool = True,
) -> str:
    """Who says the line, and whether a friend is allowed to exist."""
    src = image_tag
    has_listener = scene_has_addressee(scene)
    if not speaking:
        if has_listener:
            return (
                f"SPEAKER: {src} is the main person. A friend is the listener and keeps their own "
                f"face. Other people may appear if the scene asks. They keep their own faces and never "
                f"take the {src} face. No one speaks on this pass."
            )
        return (
            f"SPEAKER: {src} is the only foreground person. Do not invent a friend, interviewer, "
            f"or extra lead. Other people stay in the background if the place has a crowd. They "
            f"keep their own faces and never take the {src} face. No one speaks on this pass."
        )
    if talking:
        if has_listener:
            return (
                f"SPEAKER: {src} says the spoken line. A friend is the listener, keeps their own "
                "face, and does not say this line. Do not invent a new lead in the scene's clothes. "
                f"Other people may appear if the scene asks. They keep their own faces and never "
                f"take the {src} face."
            )
        return (
            f"SPEAKER: {src} says the spoken line. They are the only foreground person. "
            "Do not invent a friend, interviewer, new lead, or over-the-shoulder listener. "
            f"A crowd in the place stays in the background. They keep their own faces and never "
            f"take the {src} face."
        )
    if has_listener:
        return (
            f"SPEAKER: {src} is the default speaker. Lines the text does not give someone else "
            f"are said by them. Other people may appear if the scene asks. They keep their own "
            f"faces, never take the {src} face, and speak only the lines the text gives them."
        )
    return (
        f"SPEAKER: {src} is the default speaker. Lines the text does not give someone else "
        f"are said by them. Other people may appear if the scene names them. Do not invent "
        f"extras the text did not write. They keep their own faces, never take the {src} face, "
        f"and speak only the lines the text gives them."
    )
