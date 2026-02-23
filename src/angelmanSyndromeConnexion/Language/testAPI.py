from __future__ import annotations
import sys,os
from pathlib import Path

# met le *parent* du script (souvent .../src) dans sys.path
SRC_DIR = Path(__file__).resolve().parents[2]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.logger import setup_logger
from configparser import ConfigParser
import time
from angelmanSyndromeConnexion import error
import deepl

logger = setup_logger(debug=False)

_cfg = ConfigParser()
_cfg.read(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "angelman_viz_keys", "Config5.ini")))
_PUBLIC_KEY = (_cfg.get("PUBLIC", "APP_DEEPL_KEY", fallback="") or "").strip()

def main():
    start = time.time()
    try:
        
        auth_key = _PUBLIC_KEY
        translator = deepl.Translator(auth_key)

        result = translator.translate_text(
             "Bonjour, comment allez-vous ?",
             source_lang="FR",
             target_lang="EN-GB"
        )

        logger.info(result.text)
        elapsed = time.time() - start
        
        logger.info(f"\n✅ Traduction time in {elapsed:.2f} secondes.")
        sys.exit(0)
    except error.AppError as e:
        logger.critical("🚨 Error in the traduction process. %s : %s - %s",e.code, e.http_status, str(e))
        sys.exit(1)
    except Exception:
        logger.critical("🚨 Error in the traduction process.")
        sys.exit(1)

if __name__ == "__main__":
     main()
