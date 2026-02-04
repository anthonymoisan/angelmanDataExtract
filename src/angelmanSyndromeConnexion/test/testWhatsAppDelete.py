from __future__ import annotations
import sys,os
import time
from pathlib import Path
# met le *parent* du script (souvent .../src) dans sys.path
SRC_DIR = Path(__file__).resolve().parents[2]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.logger import setup_logger
from angelmanSyndromeConnexion import error

from angelmanSyndromeConnexion import models  # noqa: F401  <-- important
from app.db import get_session  # ton helper de session (context manager)

from angelmanSyndromeConnexion.whatsAppDelete import(
    deleteMessageSoft,
    leave_conversation,
    leave_group_conversation,
    delete_group_conversation,
)

import traceback

# Set up logger
logger = setup_logger(debug=False)

def run():
    
    with get_session() as session:
        #deleteMessageSoft(session,6) 
        #leave_conversation(session,1,1)
        #leave_group_conversation(session,11,1)
        delete_group_conversation(session,18,1)
    
    logger.info("✅ Seed de conversation terminé avec succès !")


def main():
    start = time.time()
    try:
        run()
        elapsed = time.time() - start
        logger.info(f"\n✅ Tables for WhatsApp are ok with an execution time in {elapsed:.2f} secondes.")
        sys.exit(0)
    except error.AppError as e:
        logger.critical("🚨 Error in WhatsApp process. %s : %s - %s",e.code, e.http_status, str(e))
        traceback.print_exc()
        sys.exit(1)
    except Exception as e :
        logger.critical("🚨 Error in WhatsApp process: %s", e)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
     main()