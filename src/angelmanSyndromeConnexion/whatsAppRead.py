from __future__ import annotations

from angelmanSyndromeConnexion.models.conversation import Conversation
from angelmanSyndromeConnexion.models.conversationMember import ConversationMember
from angelmanSyndromeConnexion.models.people_public import PeoplePublic
from angelmanSyndromeConnexion.models.message import Message
from sqlalchemy.orm import aliased
from sqlalchemy import select, desc, asc
from datetime import datetime
from angelmanSyndromeConnexion.models.messageReaction import MessageReaction

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

def get_all_conversation_members(session):
    """
    Retourne tous les enregistrements de T_Conversation_Member.
    """
    stmt = select(ConversationMember)
    return session.scalars(stmt).all()

def get_all_peoplePublic(session):
    '''
    Retourne tous les people Public
    '''
    return session.scalars(select(PeoplePublic)).all()


def get_messages_for_conversation(session, conversation_id: int):
    """
    Retourne tous les messages d'une conversation donnée,
    triés par date de création croissante, avec :
      - message_id
      - body_text
      - author_pseudo
      - created_at
      - sender_people_id
      - reply_to_message_id
      - reply_body_text
      - reaction_emoji
      - reaction_pseudo
      - reaction_people_id
    """

    ParentMsg = aliased(Message)          # pour le message auquel on répond
    ReactionAuthor = aliased(PeoplePublic)  # auteur de la réaction

    stmt = (
        select(
            Message.id.label("message_id"),
            Message.body_text.label("body_text"),
            PeoplePublic.pseudo.label("author_pseudo"),
            Message.created_at.label("created_at"),
            Message.sender_people_id.label("sender_people_id"),
            Message.reply_to_message_id.label("reply_to_message_id"),
            ParentMsg.body_text.label("reply_body_text"),
            MessageReaction.emoji.label("reaction_emoji"),
            ReactionAuthor.pseudo.label("reaction_pseudo"),
            MessageReaction.people_public_id.label("reaction_people_id"),
        )
        .join(PeoplePublic, Message.sender_people_id == PeoplePublic.id)
        .outerjoin(ParentMsg, Message.reply_to_message_id == ParentMsg.id)
        .outerjoin(MessageReaction, MessageReaction.message_id == Message.id)
        .outerjoin(ReactionAuthor, MessageReaction.people_public_id == ReactionAuthor.id)
        .where(Message.conversation_id == conversation_id)
        .order_by(asc(Message.created_at))
    )

    rows = session.execute(stmt).all()
    return rows

def get_member_ids_for_conversation(session, conversation_id: int) -> list[int]:
    stmt = (
        select(ConversationMember.people_public_id)
        .where(ConversationMember.conversation_id == conversation_id)
    )

    member_ids = session.scalars(stmt).all()
    return member_ids


def get_last_message_for_conversation(session, conversation_id: int):
    stmt = (
        select(
            Message.id.label("message_id"),
            Message.sender_people_id.label("sender_people_id"),
            Message.body_text.label("body_text"),
            PeoplePublic.pseudo.label("pseudo"),
            Message.created_at.label("created_at"),
        )
        .join(PeoplePublic, Message.sender_people_id == PeoplePublic.id)
        .where(
            Message.conversation_id == conversation_id,
            Message.status != "deleted",
        )
        .order_by(desc(Message.created_at), desc(Message.id))
        .limit(1)
    )

    # ✅ mapping: accès garanti par row["sender_people_id"]
    row = session.execute(stmt).mappings().first()
    return row  # soit None, soit un dict-like  # → Row(message_id=..., sender_people_id=..., body_text=..., pseudo=..., created_at=...)
