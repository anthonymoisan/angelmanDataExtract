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

from datetime import datetime, timezone
from angelmanSyndromeConnexion import models  # noqa: F401  <-- important
from app.db import get_session  # ton helper de session (context manager)

from angelmanSyndromeConnexion.whatsAppRead import (
    get_conversations_for_person_sorted,
    get_all_conversation_members,
    get_all_peoplePublic,
    get_messages_for_conversation,
    get_member_ids_for_conversation,
    get_last_message_for_conversation,
)

import traceback

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

# Set up logger
logger = setup_logger(debug=False)

def run():
    now = utc_now()

    with get_session() as session:

        allPeople = get_all_peoplePublic(session)
        p = allPeople[0]
        #for p in allPeople:
        convs = get_conversations_for_person_sorted(session, p.id)
        logger.info("\nConversations triées pour %s :",p.pseudo)
        c = convs[1]
        #for c in convs:
        logger.info(f"- [{c.id}] {c.title} | last_message_at={c.last_message_at}")
        
        rows = get_messages_for_conversation(session, c.id)

        for r in rows:
            print(
                f"[{r.message_id}] {r.author_pseudo} : {r.body_text} "
                f"(reply_to={r.reply_to_message_id}, reply_body={r.reply_body_text})"
            )
            if r.reaction_emoji is not None:
                print(
                    f"   -> réaction {r.reaction_emoji} par {r.reaction_pseudo} "
                    f"(people_id={r.reaction_people_id})"
                )



                
        

        #member_ids = get_member_ids_for_conversation(session,1)  
        #lastMessage = get_last_message_for_conversation(session,1)
        #logger.info(lastMessage)

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