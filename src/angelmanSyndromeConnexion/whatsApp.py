# app/models/messages.py
from __future__ import annotations

from datetime import datetime
from angelmanSyndromeConnexion.models.people_public import PeoplePublic  # wrapper T_People_Public
from angelmanSyndromeConnexion.models.conversation import Conversation
from angelmanSyndromeConnexion.models.conversationMember import ConversationMember
from angelmanSyndromeConnexion.models.message import Message
from angelmanSyndromeConnexion.models.messageReaction import MessageReaction

from sqlalchemy import select, desc, or_


# Create a new Conversation
def createConversation(session,title,is_group,created_at) -> Conversation:
    conv = Conversation(
            title=title,
            is_group=is_group,
            created_at=created_at,
            last_message_at=None,
        )
    session.add(conv)
    session.flush()
    return conv

def addConversationMember(session,conversation_id,people_public_id,role,joined_at) -> ConversationMember :
    convMember = ConversationMember(
        conversation_id=conversation_id,
        people_public_id=people_public_id,
        role=role,         # "admin" ou "member"
        last_read_message_id=None,
        last_read_at=None,
        is_muted=False,
        joined_at=joined_at,
    )
    session.add(convMember)
    session.flush()
    return convMember

def addMessage(session,conv, sender_people_id,body_text,reply_to_message_id,has_attachments,status,created_at,edited_at,deleted_at) -> Message:
    message = Message(
        conversation_id=conv.id,
        sender_people_id=sender_people_id,
        body_text=body_text,
        reply_to_message_id=reply_to_message_id,
        has_attachments=has_attachments,
        status=status,
        created_at=created_at,
        edited_at=edited_at,
        deleted_at=deleted_at,
    )
    session.add(message)
    session.flush()

    #update metadata
    conv.last_message_at = created_at
    session.commit()
    return message

def addMessageReaction(session,message_id, people_public_id,emoji,created_at) -> MessageReaction:
    messageReaction = MessageReaction(
        message_id=message_id,
        people_public_id=people_public_id,
        emoji=emoji,
        created_at=created_at,
    )
    session.add(messageReaction)
    session.flush()
    return messageReaction

#update des metaData pour un membre donné
def setMemberMetaData(session,member,last_read_message_id,last_read_at):
    member.last_read_message_id = last_read_message_id
    member.last_read_at = last_read_at
    session.commit()

def get_conversations_for_person_sorted(session, people_public_id: int):
    """
    Retourne toutes les conversations où `people_public_id` est membre,
    triées de la plus récente à la plus ancienne :
      - d'abord sur last_message_at DESC
      - puis fallback sur created_at DESC
    """

    # Sous-requête : IDs des conversations où la personne est membre
    subq = select(ConversationMember.conversation_id).where(
        ConversationMember.people_public_id == people_public_id
    )

    # Requête principale
    stmt = (
        select(Conversation)
        .where(Conversation.id.in_(subq))
        .order_by(
            desc(Conversation.last_message_at),
            desc(Conversation.created_at),
        )
    )

    conversations = session.scalars(stmt).all()
    return conversations