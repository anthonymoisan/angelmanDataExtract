from __future__ import annotations

from angelmanSyndromeConnexion.models.message import Message
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from angelmanSyndromeConnexion.models.conversation import Conversation
from angelmanSyndromeConnexion.models.conversationMember import ConversationMember
from angelmanSyndromeConnexion.models.message import Message
from angelmanSyndromeConnexion.models.people_public import PeoplePublic

def deleteMessageSoft(session, message_id: int) -> bool:
    """
    Suppression logique : conserve le message mais l'indique comme supprimé.
    """
    msg = session.get(Message, message_id)
    if not msg:
        return False

    msg.status = "deleted"
    msg.deleted_at = utc_now()
    msg.body_text = "Message supprimé"

    session.commit()
    return True

def utc_now() -> datetime:
    return datetime.now(ZoneInfo("Europe/Paris"))


def leave_conversation(
    session: Session,
    conversation_id: int,
    people_public_id: int,
    soft_delete_own_messages: bool = True,
    delete_empty_conversation: bool = True,
) -> bool:
    """
    Permet à une personne (people_public_id) de quitter une conversation.

    - Optionnellement passe *en soft delete* tous ses messages dans cette conversation
      via deleteMessageSoft(...)
    - Supprime son entrée dans T_Conversation_Member
    - Recalcule last_message_at pour la conversation
    - Optionnel : supprime la conversation si plus de membres + plus de messages non supprimés

    Retourne True si la sortie a bien été effectuée, False si la personne
    n'était pas membre de la conversation.
    """

    # 0) Vérifier que la conversation existe
    conv = session.get(Conversation, conversation_id)
    if not conv:
        return False

    # 1) Vérifier que la personne est bien membre
    member = session.get(
        ConversationMember,
        {
            "conversation_id": conversation_id,
            "people_public_id": people_public_id,
        },
    )
    if not member:
        return False

    person = session.get(
        PeoplePublic,
        people_public_id
    )

    # 2) Soft-delete de tous ses messages s'il le faut
    if soft_delete_own_messages:
        messages = (
            session.execute(
                select(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.sender_people_id == people_public_id,
                    Message.status != "deleted",   # évite de retraiter ceux déjà supprimés
                )
                .order_by(Message.created_at.asc())
            )
        ).scalars().all()

        for msg in messages:
            deleteMessageSoft(session, msg.id)

    # 3) Supprimer son appartenance à la conversation
    session.delete(member)
    session.commit()

    # 4) Mise à jour des données de la conversation
    conv.last_message_at = utc_now()
    conv.title = person.pseudo + "a quitté la conversation"    

    # 5) Optionnel : si plus de membres + plus de messages non supprimés → supprimer la conversation
    if delete_empty_conversation:
        remaining_members = session.execute(
            select(func.count())
            .select_from(ConversationMember)
            .where(ConversationMember.conversation_id == conversation_id)
        ).scalar_one()

        if remaining_members == 0:
            session.delete(conv)

    session.commit()
    return True

def leave_group_conversation(
    session: Session,
    conversation_id: int,
    people_public_id: int,
    soft_delete_own_messages: bool = True,
    delete_empty_conversation: bool = True,
) -> bool:
    """
    Permet à une personne de quitter une conversation de groupe.

    - Optionnellement soft-delete ses messages dans ce groupe
    - Supprime son membership (T_ConversationMember)
    - Recalcule last_message_at
    - Optionnel : supprime la conversation si plus aucun membre
    - Optionnel : ajoute un message système "X a quitté le groupe"

    Retourne True si OK, False si conversation inexistante ou pas membre.
    """

    # 0) Vérifier la conversation
    conv = session.get(Conversation, conversation_id)
    if not conv:
        return False

    # (optionnel) sécuriser : la fonction ne s'applique qu'aux groupes
    if not conv.is_group:
        return False

    # 1) Vérifier membership
    member = session.get(
        ConversationMember,
        {"conversation_id": conversation_id, "people_public_id": people_public_id},
    )
    if not member:
        return False

    person = session.get(PeoplePublic, people_public_id)

    # 2) Soft-delete de ses messages
    if soft_delete_own_messages:
        messages = session.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sender_people_id == people_public_id,
                Message.status != "deleted",
            )
            .order_by(Message.created_at.asc())
        ).scalars().all()

        for msg in messages:
            deleteMessageSoft(session, msg.id)

    # 3) Supprimer le membre
    session.delete(member)
    session.flush()  # flush avant recalculs / message système

    # 4) Recalculer last_message_at = dernier message non deleted
    last_msg_at = session.execute(
        select(func.max(Message.created_at))
        .where(
            Message.conversation_id == conversation_id,
            Message.status != "deleted",
        )
    ).scalar_one()

    conv.last_message_at = last_msg_at  # peut être None si plus aucun message

    # 6) Optionnel : supprimer la conversation si plus de membres
    if delete_empty_conversation:
        remaining_members = session.execute(
            select(func.count())
            .select_from(ConversationMember)
            .where(ConversationMember.conversation_id == conversation_id)
        ).scalar_one()

        if remaining_members == 0:
            # si tu veux aussi nettoyer les messages, c'est ici (selon ta logique)
            session.delete(conv)

    session.commit()
    return True

def delete_group_conversation(
    session: Session,
    conversation_id: int,
    people_public_id: int,
    hard_delete: bool = True,
) -> bool:
    conv = session.get(Conversation, conversation_id)
    if not conv or not conv.is_group:
        return False

    member = session.get(
        ConversationMember,
        {"conversation_id": conversation_id, "people_public_id": people_public_id},
    )
    if not member:
        return False

    try:
        if hard_delete:
            session.execute(
                Message.__table__.delete().where(Message.conversation_id == conversation_id)
            )
        else:
            session.execute(
                Message.__table__.update()
                .where(Message.conversation_id == conversation_id)
                .where(Message.status != "deleted")
                .values(status="deleted")
            )

        session.execute(
            ConversationMember.__table__.delete().where(
                ConversationMember.conversation_id == conversation_id
            )
        )

        session.delete(conv)
        session.commit()
        return True

    except Exception:
        session.rollback()
        raise
