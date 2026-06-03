"""
Translation layer. STRINGS is a mutable dict shared across all modules.
Call set_language() once at startup before accessing any UI strings.
"""
from translations.en import STRINGS as _EN

STRINGS: dict[str, str] = dict(_EN)


def set_language(lang: str) -> None:
    if lang == "nl":
        from translations.nl import STRINGS as _NL
        STRINGS.clear()
        STRINGS.update(_NL)
    elif lang != "en":
        print(f"Warning: unknown language '{lang}', defaulting to English.")
