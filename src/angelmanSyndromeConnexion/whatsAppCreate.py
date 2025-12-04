from __future__ import annotations

from datetime import datetime
from angelmanSyndromeConnexion.models.people_public import PeoplePublic  # wrapper T_People_Public
from angelmanSyndromeConnexion.models.conversation import Conversation
from angelmanSyndromeConnexion.models.conversationMember import ConversationMember
from angelmanSyndromeConnexion.models.message import Message
from angelmanSyndromeConnexion.models.messageReaction import MessageReaction
from datetime import datetime, timezone

from sqlalchemy import select, func

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

# Create a new Conversation
def _createConversation(session,title,is_group) -> Conversation:
    conv = Conversation(
            title=title,
            is_group=is_group,
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

def addMessage(session,conv, sender_people_id,body_text,reply_to_message_id,has_attachments,status) -> Message:
    message = Message(
        conversation_id=conv.id,
        sender_people_id=sender_people_id,
        body_text=body_text,
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


