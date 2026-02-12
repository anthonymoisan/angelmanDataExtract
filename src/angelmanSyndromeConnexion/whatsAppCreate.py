from __future__ import annotations

from datetime import datetime
from angelmanSyndromeConnexion.models.people_public import PeoplePublic  # wrapper T_People_Public
from angelmanSyndromeConnexion.models.conversation import Conversation
from angelmanSyndromeConnexion.models.conversationMember import ConversationMember
from angelmanSyndromeConnexion.models.message import Message
from angelmanSyndromeConnexion.models.messageReaction import MessageReaction
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List
from tools.crypto_utils import encrypt_str

from sqlalchemy import select, func, text

def utc_now() -> datetime:
    return datetime.now(ZoneInfo("Europe/Paris"))

def createConversationDump(session,title,is_group,created_at,last_message_at):
    conv = Conversation(
        title=title,
        is_group = is_group,
        created_at = created_at,
        last_message_at = last_message_at,
    )
    session.add(conv)
    session.flush()
    return conv

def createConversationMemberDump(session,conversation_id,people_public_id,last_read_message_id,last_read_at,joined_at):
    member = ConversationMember(
        conversation_id = conversation_id,
        people_public_id = people_public_id,
        last_read_message_id = last_read_message_id,
        last_read_at = last_read_at,
        joined_at = joined_at,
    )
    session.add(member)
    session.flush()  # obtenir les valeurs PK si besoin
    return member

def createMessageDump(session,conversation_id,sender_people_id,body_text,created_at):
    message = Message(
        conversation_id = conversation_id,
        sender_people_id = sender_people_id,
        body_text = body_text,
        created_at = created_at,
    )
    session.add(message)
    session.flush()
    return message

# Create a new Conversation
def _createConversation(session,title,is_group,is_global) -> Conversation:
    conv = Conversation(
            title=title,
            is_group=is_group,
            is_global = is_global,
            created_at=utc_now(),
            last_message_at=None,
        )
    session.add(conv)
    session.flush()
    return conv

def get_or_create_private_conversation(session, p1_id: int, p2_id: int, title: str | None = None):
    """
    Retourne la conversation privée entre deux personnes si elle existe.
    Sinon la crée puis renvoie la nouvelle conversation.
    """

    if p1_id == p2_id:
        raise ValueError("Impossible de créer une conversation privée avec soi-même (p1_id == p2_id)")

    # 1️⃣ Sélections directes (sans .subquery())
    sub1 = select(ConversationMember.conversation_id).where(
        ConversationMember.people_public_id == p1_id
    )

    sub2 = select(ConversationMember.conversation_id).where(
        ConversationMember.people_public_id == p2_id
    )

    # 2️⃣ Conversations communes (privées)
    conv = (
        session.execute(
            select(Conversation)
            .where(
                Conversation.id.in_(sub1),
                Conversation.id.in_(sub2),
                Conversation.is_group == False,
            )
        )
    ).scalars().all()

    # 3️⃣ S’il y a déjà une ou plusieurs conversations
    if conv:
        if len(conv) == 1:
            return conv[0]

        # Filtrer celles qui ont EXACTEMENT 2 membres
        conv_valides = []
        for c in conv:
            member_count = session.execute(
                select(func.count())
                .select_from(ConversationMember)
                .where(ConversationMember.conversation_id == c.id)
            ).scalar_one()

            if member_count == 2:
                conv_valides.append(c)

        if conv_valides:
            # Retourner la plus récente
            return sorted(conv_valides, key=lambda x: x.created_at, reverse=True)[0]

    # 4️⃣ Aucune conversation privée trouvée → on la crée
    conv_title = title or "Conversation privée"

    new_conv = _createConversation(
        session,
        title=conv_title,
        is_group=False,
        is_global=False,
    )


    addConversationMember(session, new_conv.id, p1_id, "member")
    addConversationMember(session, new_conv.id, p2_id, "member")

    session.commit()

    return new_conv

def addConversationMember(session,conversation_id,people_public_id,role) -> ConversationMember :
    # 🔍 1) Vérifier si la personne est déjà membre
    existing = session.execute(
        select(ConversationMember)
        .where(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.people_public_id == people_public_id
        )
    ).scalar_one_or_none()

    if existing:
        # 👍 La personne est déjà membre → renvoyer tel quel
        return existing

    # 🆕 2) Créer un nouveau membre
    convMember = ConversationMember(
        conversation_id=conversation_id,
        people_public_id=people_public_id,
        role=role,
        last_read_message_id=None,
        last_read_at=None,
        is_muted=False,
        joined_at=utc_now(),
    )

    session.add(convMember)
    session.flush()  # obtenir les valeurs PK si besoin

    return convMember

def bulk_add_new_person_to_all_global_group_conversations_conn(conn, people_public_id: int) -> None:
    # Insère un membership pour toutes les conversations globales de groupe
    # joined_at / last_read_at : mêmes valeurs pour tous (NOW())
    conn.execute(text("""
        INSERT INTO T_Conversation_Member
            (conversation_id, people_public_id, role, last_read_message_id, last_read_at, is_muted, joined_at)
        SELECT
            c.id,
            :pid,
            'member',
            NULL,
            NULL,
            0,
            NOW()
        FROM T_Conversation c
        WHERE c.is_group = 1 AND c.is_global = 1
    """), {"pid": people_public_id})

def create_group_conversation(session, people_public_admin_id, listIdPeoplesMember: List[int], title: str) -> Conversation:
    """
    Crée une conversation de groupe, définit l'admin (idAdmin),
    et ajoute les membres + l'admin dans ConversationMember.
    """
    now = utc_now()

    # 0) Nettoyage + dédoublonnage (inclure l'admin quoi qu'il arrive)
    unique_member_ids = {pid for pid in listIdPeoplesMember if pid}
    unique_member_ids.add(people_public_admin_id)
    
    # 🔎 Récupérer tous les IDs PeoplePublic en base
    all_people_ids = set(
        session.execute(
            select(PeoplePublic.id)
        ).scalars().all()
    )

    # ✅ Vérifier si c'est une conversation globale
    global_conversation = (unique_member_ids == all_people_ids)

    # 1) Créer la conversation avec l'admin
    conv = Conversation(
        title=title,
        is_group=True,
        is_global=global_conversation,
        idAdmin=people_public_admin_id,   # ✅ nouveau champ
        created_at=now,
        last_message_at=None,
    )
    session.add(conv)
    session.flush()  # 🔑 récupère conv.id

    # 3) Créer les ConversationMember (admin + members)
    members = []
    for pid in unique_member_ids:
        members.append(
            ConversationMember(
                conversation_id=conv.id,
                people_public_id=pid,
                role="admin" if pid == people_public_admin_id else "member",
                joined_at=now,
                last_read_message_id=None,
                last_read_at=None,
                is_muted=False,
            )
        )

    session.bulk_save_objects(members)

    session.commit()
    return conv

def addMessage(session,conv, sender_people_id,body_text,reply_to_message_id,has_attachments,status) -> Message:
    message = Message(
        conversation_id=conv.id,
        sender_people_id=sender_people_id,
        body_text=encrypt_str(body_text),
        reply_to_message_id=reply_to_message_id,
        has_attachments=has_attachments,
        status=status,
        created_at=utc_now(),
        edited_at=None,
        deleted_at=None,
    )
    session.add(message)
    session.flush()

    #update metadata
    conv.last_message_at = utc_now()
    session.commit()
    return message

def addMessageReaction(session,message_id, people_public_id,emoji) -> MessageReaction:
    messageReaction = MessageReaction(
        message_id=message_id,
        people_public_id=people_public_id,
        emoji=emoji,
        created_at=utc_now(),
    )
    session.add(messageReaction)
    session.flush()
    return messageReaction

def addOrToggleMessageReaction(session, message_id: int, people_public_id: int, emoji: str) -> dict:
    """
    Si la réaction existe → la SUPPRIME.
    Sinon → la CRÉE.

    Retourne un dict :
    {
        "action": "added" | "removed",
        "reaction": MessageReaction | None
    }
    """

    # 1️⃣ Vérifier si la réaction existe déjà
    existing = session.execute(
        select(MessageReaction).where(
            MessageReaction.message_id == message_id,
            MessageReaction.people_public_id == people_public_id,
            MessageReaction.emoji == emoji,
        )
    ).scalar_one_or_none()

    if existing:
        # 2️⃣ Elle existe → on la supprime (toggle OFF)
        session.delete(existing)
        session.commit()
        return {"action": "removed", "reaction": None}

    # 3️⃣ Sinon → on la crée (toggle ON)
    reaction = MessageReaction(
        message_id=message_id,
        people_public_id=people_public_id,
        emoji=emoji,
        created_at=utc_now(),
    )
    session.add(reaction)
    session.commit()
    session.refresh(reaction)

    return {"action": "added", "reaction": reaction}

def toggleMessageReaction(session, message_id: int, people_public_id: int, emoji: str) -> tuple[bool, MessageReaction | None]:
    """
    Toggle réaction :
      - si existe -> supprime et retourne (True, None)
      - sinon -> crée et retourne (False, reaction)

    Retour:
      deleted (bool), reaction (MessageReaction|None)
    """
    existing = session.execute(
        select(MessageReaction).where(
            MessageReaction.message_id == message_id,
            MessageReaction.people_public_id == people_public_id,
            MessageReaction.emoji == emoji,
        )
    ).scalar_one_or_none()

    if existing:
        session.delete(existing)
        session.commit()
        return True, None

    reaction = MessageReaction(
        message_id=message_id,
        people_public_id=people_public_id,
        emoji=emoji,
        created_at=utc_now(),
    )
    session.add(reaction)
    session.commit()
    session.refresh(reaction)
    return False, reaction

