"""Allowed Instant Voice Clone languages.

Clone samples follow Flash v2.5 / Multilingual v2 (32 languages). TTS after
clone uses Eleven v3, which can speak 70+ from that voice.

Clients mirror this list in `cloneVoice.ts` (web + mobile). Preview lines are
what we send to ElevenLabs after a clone succeeds, not the on-device read-aloud.
"""
from __future__ import annotations

ALLOWED_CLONE_LANGUAGES = frozenset(
    {
        "ar",
        "bg",
        "cs",
        "da",
        "de",
        "el",
        "en",
        "es",
        "fi",
        "fil",
        "fr",
        "hi",
        "hr",
        "hu",
        "id",
        "it",
        "ja",
        "ko",
        "ms",
        "nl",
        "no",
        "pl",
        "pt",
        "ro",
        "ru",
        "sk",
        "sv",
        "ta",
        "tr",
        "uk",
        "vi",
        "zh",
    }
)

CLONE_PREVIEW_SCRIPTS: dict[str, str] = {
    "ar": "مرحبا. هذه تجربة سريعة لهذا الصوت.",
    "bg": "Здравей. Това е кратък преглед на този глас за твоя клип.",
    "cs": "Ahoj. Tohle je krátká ukázka tohoto hlasu pro tvůj klip.",
    "da": "Hej. Dette er en kort preview af denne stemme til dit klip.",
    "de": "Hallo. Das ist eine kurze Vorschau dieser Stimme für deinen Clip.",
    "el": "Γεια. Αυτή είναι μια σύντομη δοκιμή αυτής της φωνής για το κλιπ σου.",
    "en": "Hi, this is a quick preview of this voice for your clip.",
    "es": "Hola. Esta es una prueba rápida de esta voz para tu clip.",
    "fi": "Hei. Tämä on lyhyt esikatselu tästä äänestä klippiäsi varten.",
    "fil": "Kumusta. Ito ay isang maikling preview ng boses na ito para sa clip mo.",
    "fr": "Bonjour. Voici un aperçu rapide de cette voix pour ton clip.",
    "hi": "नमस्ते. यह इस आवाज़ का छोटा सा पूर्वावलोकन है।",
    "hr": "Bok. Ovo je kratki pregled ovog glasa za tvoj klip.",
    "hu": "Szia. Ez egy rövid előnézet erről a hangról a klipedhez.",
    "id": "Hai. Ini pratinjau singkat suara ini untuk klipmu.",
    "it": "Ciao. Questa è una breve anteprima di questa voce per il tuo clip.",
    "ja": "こんにちは。これはこの声の短いプレビューです。",
    "ko": "안녕하세요. 이 목소리의 짧은 미리듣기입니다.",
    "ms": "Hai. Ini pratinjau ringkas suara ini untuk klip awak.",
    "nl": "Hoi. Dit is een korte preview van deze stem voor je clip.",
    "no": "Hei. Dette er en kort forhåndsvisning av denne stemmen til klippet ditt.",
    "pl": "Cześć. To krótki podgląd tego głosu do twojego klipu.",
    "pt": "Oi. Esta é uma prévia rápida desta voz para o seu clipe.",
    "ro": "Salut. Aceasta este o previzualizare scurtă a acestei voci pentru clipul tău.",
    "ru": "Привет. Это короткое превью этого голоса для твоего клипа.",
    "sk": "Ahoj. Toto je krátka ukážka tohto hlasu pre tvoj klip.",
    "sv": "Hej. Det här är en kort förhandsvisning av den här rösten för ditt klipp.",
    "ta": "வணக்கம். இது இந்த குரலின் சிறிய முன்னோட்டம்.",
    "tr": "Merhaba. Bu, klipin için bu sesin kısa bir önizlemesi.",
    "uk": "Привіт. Це короткий попередній перегляд цього голосу для твого кліпу.",
    "vi": "Xin chào. Đây là bản xem trước ngắn của giọng này cho clip của bạn.",
    "zh": "你好。这是这个声音的一段短预览。",
}

# Region tags and close aliases fold into a supported primary code.
_LANGUAGE_ALIASES = {
    "nb": "no",
    "nn": "no",
    "tl": "fil",
    "cmn": "zh",
    "zh-cn": "zh",
    "zh-tw": "zh",
    "pt-br": "pt",
    "pt-pt": "pt",
}


def normalize_clone_language(value: str | None) -> str:
    """Return a supported ISO 639-1 (or fil) code. Raises ValueError if unknown."""
    raw = (value or "en").strip().lower().replace("_", "-")
    if raw in _LANGUAGE_ALIASES:
        raw = _LANGUAGE_ALIASES[raw]
    primary = (raw.split("-", 1)[0] if raw else "en").strip()[:8] or "en"
    primary = _LANGUAGE_ALIASES.get(primary, primary)
    if primary not in ALLOWED_CLONE_LANGUAGES:
        raise ValueError("Pick a supported language for this voice.")
    return primary


def preview_script_for(language: str | None) -> str:
    """Short TTS line used after clone and on the Voices preview button."""
    try:
        key = normalize_clone_language(language or "en")
    except ValueError:
        key = "en"
    return CLONE_PREVIEW_SCRIPTS.get(key) or CLONE_PREVIEW_SCRIPTS["en"]


__all__ = [
    "ALLOWED_CLONE_LANGUAGES",
    "CLONE_PREVIEW_SCRIPTS",
    "normalize_clone_language",
    "preview_script_for",
]
