"""Refuse prompts that show people in intimate contact.

App Review 1.1 rejects a generator that will depict hugging, kissing, or
similar contact. Product examples (serum, shipping, gym, headshot) must pass.
"""

from __future__ import annotations

import re

INTIMATE_CONTACT_REFUSAL = (
    "That scene is not allowed. Keep people apart. No hugging, kissing, or intimate contact."
)

# "make out the label" / "make out of" is ordinary English, not contact.
_INTIMATE_RE = re.compile(
    r"\b("
    r"kiss(?:ing|ed|es)?"
    r"|hug(?:ging|ged|s)?"
    r"|embrac(?:e|es|ed|ing)"
    r"|cuddl(?:e|es|ed|ing)"
    r"|caress(?:ing|ed|es)?"
    r"|nuzzl(?:e|es|ed|ing)"
    r"|mak(?:e|es|ing) out(?!\s+(?:of|the|a|an)\b)"
    r"|intimate contact"
    r")\b",
    re.IGNORECASE,
)


def intimate_contact_refusal(*parts: str) -> str | None:
    """Return the user-facing refusal when any part asks for intimate contact."""
    text = "\n".join(part.strip() for part in parts if part and part.strip())
    if not text or _INTIMATE_RE.search(text) is None:
        return None
    return INTIMATE_CONTACT_REFUSAL
