from __future__ import annotations
import os
from pathlib import Path
import deepl
from configparser import ConfigParser


_cfg = ConfigParser()
_cfg.read(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "angelman_viz_keys", "Config5.ini")))
_PUBLIC_KEY = (_cfg.get("PUBLIC", "APP_DEEPL_KEY", fallback="") or "").strip()

auth_key = _PUBLIC_KEY
translator = deepl.Translator(auth_key)

def translateDeepl(sentence,source_lang,target_lang):
    result = translator.translate_text(
             sentence,
             source_lang=source_lang,
             target_lang=target_lang
        )
    return result.text