from __future__ import annotations

import time
import httpx

from googletrans import Translator, LANGUAGES
from tools.logger import setup_logger

logger = setup_logger(debug=False)
translator = Translator()


def translate_text(
    sentence: str,
    source_lang: str,
    target_lang: str,
    max_retries: int = 3,
    sleep_base: float = 1.5,
) -> str | None:
    """
    Traduit une phrase d'une langue source vers une langue cible.

    Robustesse :
    - nettoyage des entrées
    - retry automatique
    - gestion timeout
    - retourne None si impossible
    """
    if not sentence:
        return None
    if not source_lang:
        return None
    if not target_lang:
        return None

    sentence = sentence.strip()
    source_lang = source_lang.strip().lower()
    target_lang = target_lang.strip().lower()

    if not sentence or not source_lang or not target_lang:
        return None

    for attempt in range(1, max_retries + 1):
        try:
            result = translator.translate(
                sentence,
                src=source_lang,
                dest=target_lang,
            )
            return result.text

        except httpx.ReadTimeout:
            logger.warning(
                "Timeout translate_text (tentative %s/%s) src=%s dest=%s",
                attempt,
                max_retries,
                source_lang,
                target_lang,
            )

        except Exception as e:
            logger.warning(
                "Erreur translate_text (tentative %s/%s) src=%s dest=%s: %s",
                attempt,
                max_retries,
                source_lang,
                target_lang,
                str(e),
            )

        if attempt < max_retries:
            time.sleep(sleep_base * attempt)

    logger.error(
        "Impossible de traduire la phrase (src=%s, dest=%s): %s",
        source_lang,
        target_lang,
        sentence[:80],
    )
    return None


def detect_text(
    sentence: str,
    max_retries: int = 3,
    sleep_base: float = 1.5,
) -> str | None:
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
                max_retries,
            )

        except Exception as e:
            logger.warning(
                "Erreur detect_text (tentative %s/%s): %s",
                attempt,
                max_retries,
                str(e),
            )

        if attempt < max_retries:
            time.sleep(sleep_base * attempt)

    logger.error("Impossible de détecter la langue : %s", sentence[:80])
    return None


def detect_and_translate_text(
    sentence: str,
    target_lang: str,
    max_retries: int = 3,
    sleep_base: float = 1.5,
) -> dict:
    """
    Détecte la langue source puis traduit vers la langue cible.

    Retourne toujours un dict homogène.
    En cas d'échec, success=False et translated_text=None.
    """
    if not sentence:
        return {
            "success": False,
            "translated_text": None,
            "detected_source_lang": None,
            "detected_source_lang_name": None,
            "target_lang": target_lang.strip().lower() if target_lang else None,
            "error": "sentence is empty",
        }

    if not target_lang:
        return {
            "success": False,
            "translated_text": None,
            "detected_source_lang": None,
            "detected_source_lang_name": None,
            "target_lang": None,
            "error": "target_lang is empty",
        }

    sentence = sentence.strip()
    target_lang = target_lang.strip().lower()

    if not sentence:
        return {
            "success": False,
            "translated_text": None,
            "detected_source_lang": None,
            "detected_source_lang_name": None,
            "target_lang": target_lang,
            "error": "sentence is empty after strip",
        }

    if not target_lang:
        return {
            "success": False,
            "translated_text": None,
            "detected_source_lang": None,
            "detected_source_lang_name": None,
            "target_lang": None,
            "error": "target_lang is empty after strip",
        }

    source_lang = detect_text(
        sentence=sentence,
        max_retries=max_retries,
        sleep_base=sleep_base,
    )

    source_lang_name = LANGUAGES.get(source_lang, "unknown") if source_lang else None

    # Si détection impossible, on peut tenter une traduction "auto"
    # pour ne pas bloquer complètement le flux.
    translated_text = None
    translation_error = None

    for attempt in range(1, max_retries + 1):
        try:
            if source_lang:
                result = translator.translate(
                    sentence,
                    src=source_lang,
                    dest=target_lang,
                )
            else:
                result = translator.translate(
                    sentence,
                    dest=target_lang,
                )

            translated_text = result.text
            break

        except httpx.ReadTimeout:
            translation_error = "timeout"
            logger.warning(
                "Timeout detect_and_translate_text (tentative %s/%s) src=%s dest=%s",
                attempt,
                max_retries,
                source_lang,
                target_lang,
            )

        except Exception as e:
            translation_error = str(e)
            logger.warning(
                "Erreur detect_and_translate_text (tentative %s/%s) src=%s dest=%s: %s",
                attempt,
                max_retries,
                source_lang,
                target_lang,
                str(e),
            )

        if attempt < max_retries:
            time.sleep(sleep_base * attempt)

    if translated_text is None:
        logger.error(
            "Impossible de détecter/traduire la phrase vers %s : %s",
            target_lang,
            sentence[:80],
        )
        return {
            "success": False,
            "translated_text": None,
            "detected_source_lang": source_lang,
            "detected_source_lang_name": source_lang_name,
            "target_lang": target_lang,
            "error": translation_error or "translation failed",
        }

    return {
        "success": True,
        "translated_text": translated_text,
        "detected_source_lang": source_lang,
        "detected_source_lang_name": source_lang_name,
        "target_lang": target_lang,
        "error": None,
    }