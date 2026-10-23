"""Intimate-contact prompts are refused. Product examples are not."""

from app.intimate_contact import INTIMATE_CONTACT_REFUSAL, intimate_contact_refusal

SERUM = (
    "Kitchen island, soft daylight, black tee. She holds the serum bottle and says: "
    "if your vitamin C still peels, switch this. One pump, no sting, glass-skin by week two."
)
SHIPPING = (
    "Desk setup, soft window light, black hoodie, phone in hand. He looks at camera and says: "
    "free shipping this week only. Order before midnight and it ships today."
)
GYM = (
    "Gym floor, bright overhead lights, black tank top. He faces the camera and says: "
    "if your pre-workout still tastes like chalk, try this. Clean energy, no crash, "
    "and I actually look forward to the gym. Link below."
)
HEADSHOT = (
    "Founder headshot portrait, clean soft gray studio backdrop, friendly smile, "
    "soft key light, sharp eyes, natural skin, no text"
)


def test_kiss_and_hug_are_refused() -> None:
    for prompt in (
        "They kiss on the sidewalk",
        "She is kissing him goodbye",
        "a quick hug at the door",
        "hugging her friend",
        "they embrace",
        "cuddling on the couch",
        "they make out",
        "making out under the awning",
        "he caresses her cheek",
        "she nuzzles his shoulder",
        "no intimate contact in frame",
    ):
        assert intimate_contact_refusal(prompt) == INTIMATE_CONTACT_REFUSAL


def test_product_examples_pass() -> None:
    for prompt in (SERUM, SHIPPING, GYM, HEADSHOT, "a huge neon sign", "make out the label"):
        assert intimate_contact_refusal(prompt) is None


def test_empty_is_not_a_refusal() -> None:
    assert intimate_contact_refusal("", "  ") is None
