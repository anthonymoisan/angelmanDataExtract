from __future__ import annotations

from angelmanSyndromeConnexion.models.conversation import Conversation
from angelmanSyndromeConnexion.models.conversationMember import ConversationMember
from angelmanSyndromeConnexion.models.people_public import PeoplePublic
from angelmanSyndromeConnexion.models.message import Message

from sqlalchemy import select, desc, asc

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
      - body_text
      - pseudo de l'auteur
      - created_at
    """
    stmt = (
        select(
            Message.body_text,
            PeoplePublic.pseudo,
            Message.created_at,
        )
        .join(PeoplePublic, Message.sender_people_id == PeoplePublic.id)
        .where(Message.conversation_id == conversation_id)
        .order_by(asc(Message.created_at))
    )

    rows = session.execute(stmt).all()
    # rows = list de tuples (body_text, pseudo, created_at)
    return rows