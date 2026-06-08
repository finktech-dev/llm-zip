import locale
import os
from typing import Protocol

from llmzip.i18n import en, es, pt, zh, ja

class LangModule(Protocol):
    STRINGS: dict[str, str]

_SUPPORTED: dict[str, LangModule] = {
    "en": en,
    "es": es,
    "pt": pt,
    "zh": zh,
    "ja": ja,
}

_active_lang: str = "en"
_active_module: LangModule = en


def configure(lang: str | None = None) -> None:
    """
    Set active language. Priority:
    1. lang argument (from --lang flag or config LANG=)
    2. LLMZIP_LANG env var
    3. System LANG env var
    4. English fallback
    """
    global _active_lang, _active_module

    resolved = (
        lang
        or os.environ.get("LLMZIP_LANG")
        or _detect_system_lang()
        or "en"
    ).lower()[:2]

    if resolved not in _SUPPORTED:
        resolved = "en"

    _active_lang = resolved
    _active_module = _SUPPORTED[resolved]


def t(key: str, **kwargs: str | int | float) -> str:
    """
    Translate a key using the active language module.
    Falls back to English if the key is missing in the active language.
    Supports named interpolation: t("compress.saved", tokens=100)
    """
    value = getattr(_active_module, "STRINGS", {}).get(key)

    if value is None:
        value = getattr(en, "STRINGS", {}).get(key, key)

    if kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, ValueError):
            return value

    return value


def current_lang() -> str:
    return _active_lang


def supported_langs() -> list[str]:
    return list(_SUPPORTED.keys())


def _detect_system_lang() -> str | None:
    system_lang = os.environ.get("LANG", "")
    if system_lang:
        return system_lang[:2].lower()
    try:
        loc = locale.getlocale()[0]
        if loc:
            return loc[:2].lower()
    except Exception:
        pass
    return None
