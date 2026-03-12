from __future__ import annotations
import sys,os
import time
from pathlib import Path
# met le *parent* du script (souvent .../src) dans sys.path
SRC_DIR = Path(__file__).resolve().parents[2]  # .../src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.logger import setup_logger
from tools.utilsTools import dropTable,createTable
from angelmanSyndromeConnexion import error
from sqlalchemy import select
from datetime import datetime
from zoneinfo import ZoneInfo
from angelmanSyndromeConnexion import models  # noqa: F401  <-- important
from angelmanSyndromeConnexion.models.people_public import PeoplePublic
from angelmanSyndromeConnexion.models.conversation import Conversation
from app.db import get_session  # ton helper de session (context manager)
from tools.crypto_utils import encrypt_str
from angelmanSyndromeConnexion.whatsAppCreate import (
    addConversationMember,
    addMessage,
    addMessageReaction,   
    get_or_create_private_conversation,
    createConversationDump,
    createConversationMemberDump,
    createMessageDump,
    create_group_conversation,
    createConversationLangDump,
)
import pandas as pd

from angelmanSyndromeConnexion.whatsAppUpdate import setMemberMetaData

from angelmanSyndromeConnexion.whatsAppMessageUpload import (
    UploadError,
    attach_files_to_message,
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE,
)

from pathlib import Path
from werkzeug.datastructures import FileStorage
import mimetypes


import traceback

def utc_now() -> datetime:
    return datetime.now(ZoneInfo("Europe/Paris"))

def runExcel():
    wkdir = os.path.dirname(__file__)
    df = pd.read_excel(f"{wkdir}/../../../data/Picture/Conversation_all_pairs.xlsx")
    convs = (
        df[["IdConversation", "title", "created_at", "last_message_at"]]
        .drop_duplicates()
        .sort_values("IdConversation")
    )

    members = (
        df[["IdConversation", "people_public_id","last_read_message_id", "last_read_at","joined_at"]]
            .drop_duplicates()
            .sort_values("IdConversation")
    )

    messages = (
        df[["IdConversation","idMessage","sender_people_id","body_text","created_at_message"]]
    )

    convLangs = (
        df[["IdConversation", "Lang"]]
    )
    
    with get_session() as session:
        for _, row in convs.iterrows():
            conv = createConversationDump(
                session,
                row["title"],
                0,
                row["created_at"],
                row["last_message_at"],
            )

        for _, row in members.iterrows():
            #logger.info(row)
            memb = createConversationMemberDump(
                session,
                row["IdConversation"],
                row["people_public_id"],
                row["last_read_message_id"],
                row["last_read_at"],
                row["joined_at"],
            )
        for _, row in messages.iterrows():
            message = createMessageDump(
                session,
                row["IdConversation"],
                row["sender_people_id"],
                encrypt_str(row["body_text"]),
                row["created_at_message"],
            )
        
        for _, row in convLangs.iterrows():
            convLang = createConversationLangDump(
                session,
                row["IdConversation"],
                row["Lang"],
            )

def createMessagesConversationsFromExcel(wkdir):
    dropTable("T_Message_Attachment",bAngelmanResult=False)
    dropTable("T_Message_Reaction",bAngelmanResult=False)
    dropTable("T_Message",bAngelmanResult=False)
    dropTable("T_Conversation_Member",bAngelmanResult=False)
    dropTable("T_Conversation_Lang",bAngelmanResult=False)
    dropTable("T_Conversation",bAngelmanResult=False)
    #dropTable("T_People_Public",bAngelmanResult=False)
    
    script_path = os.path.join(f"{wkdir}/../SQL/","createConversation.sql")
    createTable(script_path,bAngelmanResult=False)
    script_path = os.path.join(f"{wkdir}/../SQL/","createConversationMember.sql")
    createTable(script_path,bAngelmanResult=False)
    script_path = os.path.join(f"{wkdir}/../SQL/","createMessage.sql")
    createTable(script_path,bAngelmanResult=False)
    script_path = os.path.join(f"{wkdir}/../SQL/","createMessageAttachment.sql")
    createTable(script_path,bAngelmanResult=False)
    script_path = os.path.join(f"{wkdir}/../SQL/","createMessageReaction.sql")
    createTable(script_path,bAngelmanResult=False)
    script_path = os.path.join(f"{wkdir}/../SQL/","createConversationLang.sql")
    createTable(script_path,bAngelmanResult=False)

    runExcel()

def create_GroupConversation():
     with get_session() as session:
        #convGroup1 = create_group_conversation(session, 9, ["en", "fr"],[9], "Group ENGLISH and FRENCH")       
        #addMessage(session,convGroup1, 9,"Do you have an idea about this bedroom",None,None,"normal")
        convs = session.execute(
            select(Conversation)
        ).scalars().all()
        for conv in convs:
            createConversationLangDump(session, conv.id, 'fr')


def create_AttachementMessage():
    '''
    Attention pas fonctionnelle en local mais fonctionne avec les points d'entrée privé et public
    '''
    file_path = Path(r"C:\Users\antho\Documents\FAST\Modele WP Marmite\AS Connect\Images\Couverture.png")

    mime_type, _ = mimetypes.guess_type(str(file_path))
    mime_type = mime_type or "application/octet-stream"

    with open(file_path, "rb") as fh:
        test_file = FileStorage(
            stream=fh,
            filename=file_path.name,
            name="file",
            content_type=mime_type,
        )

        with get_session() as session:
            try:
                message, attachments = attach_files_to_message(
                    session=session,
                    message_id=533,
                    actor_people_id=4011,
                    uploaded_files=[test_file],
                    allowed_mime_types=ALLOWED_MIME_TYPES,
                    max_file_size=MAX_FILE_SIZE,
                )

                logger.info("Attachement OK")

                
            except UploadError as e:
                session.rollback()
                logger.info(str(e))

            except Exception as e:
                session.rollback()
                logger.info(str(e))

# Set up logger
logger = setup_logger(debug=False)
    

def main():
    start = time.time()
    try:
        wkdir = os.path.dirname(__file__)
        
        #createMessagesConversationsFromExcel(wkdir=wkdir)
        #create_GroupConversation()
        #create_AttachementMessage()

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