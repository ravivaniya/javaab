import logging

logger = logging.getLogger(__name__)


class LanguageService:
    """
    Detect primary language by Unicode-block sampling.

    Native scripts win immediately; Roman transliteration of hi/gu still
    falls through to "en" (acceptable per the i18n note in CLAUDE.md —
    if a student types in Roman script the model still handles it).
    """

    # Devanagari (Hindi)
    _DEVANAGARI_START, _DEVANAGARI_END = 0x0900, 0x097F
    # Gujarati script
    _GUJARATI_START, _GUJARATI_END = 0x0A80, 0x0AFF

    def detect_language(self, text: str) -> str:
        if not text:
            return "en"

        hi_count = 0
        gu_count = 0
        for ch in text:
            code = ord(ch)
            if self._GUJARATI_START <= code <= self._GUJARATI_END:
                gu_count += 1
            elif self._DEVANAGARI_START <= code <= self._DEVANAGARI_END:
                hi_count += 1

        # Whichever script dominates wins; tie favors Gujarati (smaller pool of users).
        if gu_count == 0 and hi_count == 0:
            return "en"
        return "gu" if gu_count >= hi_count else "hi"
