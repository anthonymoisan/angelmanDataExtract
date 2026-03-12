from __future__ import annotations
import sys,os
from pathlib import Path

# met le *parent* du script (souvent .../src) dans sys.path
SRC_DIR = Path(__file__).resolve().parents[2]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.logger import setup_logger

import time
from angelmanSyndromeConnexion import error
from api_deepl import translateDeepl
from api_googletranslate import translate_text, detect_and_translate_text

logger = setup_logger(debug=False)



def main():
    start = time.time()
    try:
    
        '''
        logger.info("Traduction avec Deepl")
        result = translateDeepl(
             "Bonjour, je pense qu'aujourd'hui, il va pleuvoir",
             source_lang="FR",
             target_lang="EN-GB"
        )
        logger.info(result)
        '''
        
        logger.info("------------")
        logger.info("Traduction avec Google Translate")
        result2 = translate_text(
             "Bonjour, je pense qu'aujourd'hui, il va pleuvoir",
             source_lang="fr",
             target_lang="en"
        )
        logger.info(result2)

        logger.info("------------")
        logger.info("Traduction avec Google Translate en détectant la langue de départ")
        result2 = detect_and_translate_text(
             "I will see after breaking the fast",
             target_lang="id"
        )
        logger.info(result2)


        
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
