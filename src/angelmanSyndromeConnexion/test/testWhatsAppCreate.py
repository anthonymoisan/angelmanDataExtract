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

from datetime import datetime
from zoneinfo import ZoneInfo
from angelmanSyndromeConnexion import models  # noqa: F401  <-- important
from angelmanSyndromeConnexion.models.people_public import PeoplePublic
from app.db import get_session  # ton helper de session (context manager)
from angelmanSyndromeConnexion.whatsAppCreate import (
    addConversationMember,
    addMessage,
    addMessageReaction,   
    get_or_create_private_conversation,
    createConversationDump,
    createConversationMemberDump,
    createMessageDump,
    create_group_conversation,
)
import pandas as pd

from angelmanSyndromeConnexion.whatsAppUpdate import setMemberMetaData

import traceback

def utc_now() -> datetime:
    return datetime.now(ZoneInfo("Europe/Paris"))


def runManuel():
    with get_session() as session:
        # 1) Créer 3 personnes publiques (T_People_Public)
        alice = PeoplePublic(
            city="Paris",
            age_years=35,
            pseudo="MamanAngel",
            status="active",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        bob = PeoplePublic(
            city="Lyon",
            age_years=38,
            pseudo="PapaLion",
            status="active",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        jean = PeoplePublic(
            city="Marseille",
            age_years=50,
            pseudo="Jeannot",
            status="active",
            created_at=utc_now(),
            updated_at=utc_now(),
        ) 

        session.add_all([alice, bob, jean ])
        session.flush()  # pour récupérer alice.id et bob.id

        logger.info(f"PeoplePublic créés : {alice.id=}, {bob.id=},{jean.id=}")
        
        # 2) Créer une conversation (type WhatsApp / groupe)
        conv = get_or_create_private_conversation(
            session,
            alice.id,
            bob.id,
            title="Familles Angelman France",
        )
        logger.info(f"Conversation créée : {conv.id=}")
        
        # 3) Ajouter les membres dans T_Conversation_Member
        alice_member = addConversationMember(
            session,
            conversation_id=conv.id,
            people_public_id=alice.id,
            role="admin",         # "admin" ou "member"
        )

        bob_member = addConversationMember(
            session,
            conversation_id=conv.id,
            people_public_id=bob.id,
            role="member",
        )

        
        # 4) Créer quelques messages dans T_Message
        msg1 = addMessage(
            session,
            conv,
            sender_people_id=alice.id,
            body_text="Bonjour à tous, je suis nouvelle ici 💙",
            reply_to_message_id=None,
            has_attachments=False,
            status="normal",
        )

        msg2 = addMessage(
            session,
            conv,
            sender_people_id=bob.id,
            body_text="Bienvenue ! Comment va votre enfant ? 🙂",
            reply_to_message_id=None,  # ou msg1.id après flush si tu veux un reply
            has_attachments=False,
            status="normal",
        )

        msg13 = addMessage(
            session,
            conv,
            sender_people_id=bob.id,
            body_text="Quel âge à votre enfant ?",
            reply_to_message_id=None,  # ou msg1.id après flush si tu veux un reply
            has_attachments=False,
            status="normal",
        )

        logger.info(f"Messages créés : {msg1.id=}, {msg2.id=}, {msg13.id=}")

        # 5) Exemple de réaction (emoji) sur un message
        reaction = addMessageReaction(
            session,
            message_id=msg2.id,
            people_public_id=alice.id,
            emoji="👍",
        )
        
        # 7) Marquer "dernier message lu" pour Alice par exemple
        setMemberMetaData(session,alice_member,msg2.id)

        #) 2ème conversation
        conv2 = get_or_create_private_conversation(
            session,
            jean.id,
            bob.id,
            title="Les Amours",
        )
        logger.info(f"Conversation créée : {conv2.id=}")

        jean_member = addConversationMember(
            session,
            conversation_id=conv2.id,
            people_public_id=jean.id,
            role="admin",         # "admin" ou "member"
        )

        bob_member2 = addConversationMember(
            session,
            conversation_id=conv2.id,
            people_public_id=bob.id,
            role="member",
        )

        msg3 = addMessage(
            session,
            conv2,
            sender_people_id=jean.id,
            body_text="Bonjour à vous les amours",
            reply_to_message_id=None,
            has_attachments=False,
            status="normal",
        )

        msg4 = addMessage(
            session,
            conv2,
            sender_people_id=bob.id,
            body_text="Merci, c'est top cette application",
            reply_to_message_id=None,  # ou msg1.id après flush si tu veux un reply
            has_attachments=False,
            status="normal",
        )

        logger.info(f"Messages créés : {msg3.id=}, {msg4.id=}")

        setMemberMetaData(session,jean_member,msg3.id)

        msg5 = addMessage(
            session,
            conv2,
            sender_people_id=jean.id,
            body_text="Cela doit marcher",
            reply_to_message_id=msg4.id,  # ou msg1.id après flush si tu veux un reply
            has_attachments=False,
            status="normal",
        )

        logger.info(f"Message créé : {msg5.id=}")

        #pour tester qu'on ne crée pas une nouvelle conversation entre deux personnes qui ont déjà une conversation
        conv3 = get_or_create_private_conversation(
            session,
            jean.id,
            bob.id,
            title="Les Amours infinis",
        )
        logger.info(f"Conversation envoyée : {conv3.id=}")

        logger.info("✅ Seed de conversation terminé avec succès !")

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
                row["body_text"],
                row["created_at_message"],
            )

def createMessagesConversationsFromExcel(wkdir):
    dropTable("T_Message_Attachment",bAngelmanResult=False)
    dropTable("T_Message_Reaction",bAngelmanResult=False)
    dropTable("T_Message",bAngelmanResult=False)
    dropTable("T_Conversation_Member",bAngelmanResult=False)
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

    runExcel()

def create_GroupConversation():
     with get_session() as session:
        convGroup1 = create_group_conversation(session, 1, [2,3,4], "Group10")

# Set up logger
logger = setup_logger(debug=False)
    

def main():
    start = time.time()
    try:
        wkdir = os.path.dirname(__file__)
        
        #createMessagesConversationsFromExcel(wkdir=wkdir)
        create_GroupConversation()
        
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