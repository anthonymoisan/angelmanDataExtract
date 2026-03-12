from __future__ import annotations

from googletrans import Translator, LANGUAGES

translator = Translator()


def translate_text(sentence: str, source_lang: str, target_lang: str) -> str:
    result = translator.translate(
        sentence,
        src=source_lang,
        dest=target_lang,
    )
    return result.text


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