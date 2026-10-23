"""Face edit helpers: replace vs look, instruction guards."""
from __future__ import annotations

from app.routers.play_face_edit import FACE_EDIT_MODEL, _reject_edit_instruction, face_edit_prompt


def test_edit_model_is_imagine_2() -> None:
    assert FACE_EDIT_MODEL == "grok-imagine-image-2.0"


def test_look_prompt_asks_for_wardrobe_not_new_person() -> None:
    text = face_edit_prompt(instruction="white tee, glasses", kind="look").lower()
    assert "white tee" in text
    assert "wardrobe" in text or "hair" in text
    assert "makeup" in text or "finish" in text
    assert "second person" not in text
    assert "photorealistic head-and-shoulders portrait" not in text
    assert "edit the source photo" in text


def test_touchup_keeps_clothes() -> None:
    text = face_edit_prompt(instruction="better light", kind="touchup")
    assert "Same clothes" in text
    assert "better light" in text
    assert "Edit the source photo" in text


def test_hair_look_locks_face_geometry() -> None:
    text = face_edit_prompt(instruction="tied-back hair", kind="look").lower()
    assert "tied-back hair" in text
    assert "do not generate a new portrait" in text
    assert "keep eyes, nose, mouth, jaw" in text
    assert "do not rebuild the face to fit the hair" in text
    assert "photorealistic" not in text


def test_empty_instruction_rejected() -> None:
    assert _reject_edit_instruction("   ", kind="touchup") == "Describe the change first."
