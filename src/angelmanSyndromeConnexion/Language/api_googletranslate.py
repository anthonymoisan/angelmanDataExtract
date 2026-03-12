from __future__ import annotations

from googletrans import Translator, LANGUAGES
from tools.logger import setup_logger
import httpx
import time

logger = setup_logger(debug=False)
translator = Translator()


def translate_text(sentence: str, source_lang: str, target_lang: str) -> str:
    result = translator.translate(
        sentence,
        src=source_lang,
        dest=target_lang,
    )
    return result.text

def detect_text(sentence: str, max_retries: int = 3, sleep_base: float = 1.5) -> str | None:
    """
    Détecte la langue d'une phrase.

    Robustesse :
    - retry automatique
    - gestion timeout
    - nettoyage phrase
    - retourne None si impossible
    """

    if not sentence:
        return None

    sentence = sentence.strip()

    if not sentence:
        return None

    for attempt in range(1, max_retries + 1):

        try:
            detection = translator.detect(sentence)
            return detection.lang

        except httpx.ReadTimeout:
            logger.warning(
                "Timeout detect_text (tentative %s/%s)",
                attempt,
                max_retries
            )

        except Exception as e:
            logger.warning(
                "Erreur detect_text (tentative %s/%s): %s",
                attempt,
                max_retries,
                str(e)
            )

        # backoff progressif
        if attempt < max_retries:
            sleep_time = sleep_base * attempt
            time.sleep(sleep_time)

    logger.error("Impossible de détecter la langue : %s", sentence[:80])

    return None

def detect_and_translate_text(sentence: str, target_lang: str) -> dict:
    detection = translator.detect(sentence)
    source_lang = detection.lang
    source_lang_name = LANGUAGES.get(source_lang, "unknown")

    result = translator.translate(sentence, dest=target_lang)

    return {
        "translated_text": result.text,
        "detected_source_lang": source_lang,
        "detected_source_lang_name": source_lang_name,
        "target_lang": target_lang,
    }