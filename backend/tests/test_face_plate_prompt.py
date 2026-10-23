"""Generated face plates must stay in deep focus.

Talking clips send the plate as a reference image, and reference-to-video models
inherit its optics. Bokeh here reappears as a blurred background in every clip
made from the face, so the plate prompt must never ask for it.
"""
from app.routers.play_faces import face_plate_prompt


def test_plate_keeps_the_user_subject():
    assert "woman with short curly hair" in face_plate_prompt("woman with short curly hair")


def test_plate_asks_for_deep_focus():
    text = face_plate_prompt("man in his 40s").lower()
    assert "deep depth of field" in text
    assert "sharp focus" in text


def test_plate_never_asks_for_background_blur():
    text = face_plate_prompt("man in his 40s").lower()
    for banned in ("shallow depth of field", "out-of-focus", "out of focus", "bokeh", "blur"):
        assert banned not in text, f"face plate must not request {banned!r}"


def test_plate_trims_the_raw_prompt():
    assert face_plate_prompt("  woman in a denim jacket  ").startswith(
        "Photorealistic portrait of woman in a denim jacket."
    )


def test_plate_stays_head_and_shoulders_not_full_body():
    # A full-body Face plate makes Seedance compose full-figure Talking clips.
    # The NYC street clip already did that from a headshot. Do not bake a body
    # into the library Face to fix a generate framing bug.
    text = face_plate_prompt("woman in yoga pants").lower()
    assert "head and shoulders" in text
    assert "full body" not in text
    assert "full-body" not in text
    assert "full figure" not in text
