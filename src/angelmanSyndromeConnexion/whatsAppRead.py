from __future__ import annotations

from angelmanSyndromeConnexion.models.conversation import Conversation
from angelmanSyndromeConnexion.models.conversationMember import ConversationMember
from angelmanSyndromeConnexion.models.people_public import PeoplePublic
from angelmanSyndromeConnexion.models.message import Message
from sqlalchemy.orm import aliased
from sqlalchemy import select, desc, asc, func, and_
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
        .where(
            Conversation.id.in_(subq),
            Conversation.is_group.is_(False),
            )
        .order_by(
            desc(Conversation.last_message_at),
            desc(Conversation.created_at),
        )
    )

    conversations = session.scalars(stmt).all()
    return conversations


def get_group_conversations_for_person_sorted(
    session,
    people_public_id: int,
):
    """
    Retourne toutes les groupes de conversations où `people_public_id` est membre,
    triées de la plus récente à la plus ancienne :
      - d'abord sur last_message_at DESC
      - puis fallback sur created_at DESC
    """
    stmt = (
        select(Conversation)
        .join(
            ConversationMember,
            ConversationMember.conversation_id == Conversation.id,
        )
        .where(
            ConversationMember.people_public_id == people_public_id,
            Conversation.is_group.is_(True),
        )
        .order_by(
            desc(func.coalesce(Conversation.last_message_at, Conversation.created_at)),
            desc(Conversation.created_at),
        )
        .distinct()
    )

    return session.scalars(stmt).all()


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


def get_unread_count(session, conversation_id: int, viewer_people_id: int) -> int:
    member = session.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.people_public_id == viewer_people_id,
        )
    ).scalar_one_or_none()

    if not member:
        raise PermissionError("viewer_people_id n'est pas membre de la conversation")

    last_read_id = int(member.last_read_message_id or 0)

    stmt = select(func.count()).select_from(Message).where(
        Message.conversation_id == conversation_id,
        Message.status != "deleted",
        Message.id > last_read_id,
        Message.sender_people_id != viewer_people_id,  # optionnel mais conseillé
    )
    return int(session.execute(stmt).scalar_one())

def get_conversations_summary_for_person(session, viewer_people_id: int):
    CM_viewer = aliased(ConversationMember)
    CM_other  = aliased(ConversationMember)

    PP_sender = aliased(PeoplePublic)   # pseudo auteur du dernier msg
    PP_other  = aliased(PeoplePublic)   # pseudo de l'autre membre

    LM = aliased(Message)

    last_msg_id_sq = (
        select(
            Message.conversation_id.label("conv_id"),
            func.max(Message.id).label("last_message_id"),
        )
        .where(Message.status != "deleted")
        .group_by(Message.conversation_id)
        .subquery()
    )

    unread_count_sq = (
        select(func.count(Message.id))
        .where(
            Message.conversation_id == Conversation.id,
            Message.status != "deleted",
            Message.id > func.coalesce(CM_viewer.last_read_message_id, 0),
            Message.sender_people_id != viewer_people_id,
        )
        .correlate(Conversation, CM_viewer)
        .scalar_subquery()
    )

    stmt = (
        select(
            Conversation.id.label("conversation_id"),
            Conversation.title.label("title"),
            Conversation.is_group.label("is_group"),
            Conversation.created_at.label("created_at"),
            Conversation.last_message_at.label("last_message_at"),

            unread_count_sq.label("unread_count"),

            CM_other.people_public_id.label("other_people_id"),
            CM_other.last_read_message_id.label("other_last_read_message_id"),
            PP_other.pseudo.label("other_pseudo"),  # ✅ IMPORTANT
            PP_other.is_connected.label("is_connected"),

            LM.id.label("last_message_id"),
            LM.sender_people_id.label("last_sender_people_id"),
            LM.body_text.label("last_body_text"),
            LM.created_at.label("last_created_at"),
            PP_sender.pseudo.label("last_sender_pseudo"),
        )
        .join(
            CM_viewer,
            and_(
                CM_viewer.conversation_id == Conversation.id,
                CM_viewer.people_public_id == viewer_people_id,
            ),
        )
        .join(
            CM_other,
            and_(
                CM_other.conversation_id == Conversation.id,
                CM_other.people_public_id != viewer_people_id,
            ),
        )
        .outerjoin(PP_other, PP_other.id == CM_other.people_public_id)  # ✅ join other pseudo
        .outerjoin(last_msg_id_sq, last_msg_id_sq.c.conv_id == Conversation.id)
        .outerjoin(LM, LM.id == last_msg_id_sq.c.last_message_id)
        .outerjoin(PP_sender, PP_sender.id == LM.sender_people_id)
        .where(Conversation.is_group.is_(False))   # ✅ AJOUT ICI
        .order_by(Conversation.last_message_at.desc(), Conversation.created_at.desc())
    )

    rows = session.execute(stmt).all()

    out = []
    for r in rows:
        # ✅ is_seen seulement si dernier message envoyé par viewer (en 1-1)
        is_seen = None
        if (r.is_group is False and r.last_message_id is not None):
            if (r.last_sender_people_id is not None and int(r.last_sender_people_id) == int(viewer_people_id)):
                other_last = int(r.other_last_read_message_id or 0)
                is_seen = int(r.last_message_id) <= other_last

        # ✅ Titre : 1-1 => "Chat avec <pseudo autre>", sinon titre existant
        if not r.is_group:
            other_pseudo = (r.other_pseudo or "").strip()
            title = f"Chat avec {other_pseudo}" if other_pseudo else (r.title or "Chat privé")
        else:
            title = r.title or "Groupe"

        out.append({
            "id": int(r.conversation_id),
            "title": title,
            "is_group": bool(r.is_group),
            "is_connected" : bool(r.is_connected),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "last_message_at": r.last_message_at.isoformat() if r.last_message_at else None,

            "unread_count": int(r.unread_count or 0),

            "other_people_id": int(r.other_people_id) if (r.other_people_id is not None and not r.is_group) else None,

            "last_message": None if r.last_message_id is None else {
                "message_id": int(r.last_message_id),
                "sender_people_id": int(r.last_sender_people_id) if r.last_sender_people_id is not None else None,
                "pseudo": r.last_sender_pseudo or "",
                "body_text": r.last_body_text or "",
                "created_at": r.last_created_at.isoformat() if r.last_created_at else None,
                "is_seen": is_seen,  # bool | None
            }
        })

    return out

def get_group_conversations_summary_for_person(session, viewer_people_id: int):
    CM_viewer = aliased(ConversationMember)

    PP_sender = aliased(PeoplePublic)  # pseudo auteur du dernier msg
    LM = aliased(Message)

    # Dernier message (id max) par conversation (hors deleted)
    last_msg_id_sq = (
        select(
            Message.conversation_id.label("conv_id"),
            func.max(Message.id).label("last_message_id"),
        )
        .where(Message.status != "deleted")
        .group_by(Message.conversation_id)
        .subquery()
    )

    # Unread count pour viewer
    unread_count_sq = (
        select(func.count(Message.id))
        .where(
            Message.conversation_id == Conversation.id,
            Message.status != "deleted",
            Message.id > func.coalesce(CM_viewer.last_read_message_id, 0),
            Message.sender_people_id != viewer_people_id,
        )
        .correlate(Conversation, CM_viewer)
        .scalar_subquery()
    )

    # Nombre de membres dans le groupe
    member_count_sq = (
        select(func.count(ConversationMember.people_public_id))
        .where(ConversationMember.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )

    stmt = (
        select(
            Conversation.id.label("conversation_id"),
            Conversation.title.label("title"),
            Conversation.is_group.label("is_group"),
            Conversation.idAdmin.label("idAdmin"),
            Conversation.created_at.label("created_at"),
            Conversation.last_message_at.label("last_message_at"),

            unread_count_sq.label("unread_count"),
            member_count_sq.label("member_count"),

            LM.id.label("last_message_id"),
            LM.sender_people_id.label("last_sender_people_id"),
            LM.body_text.label("last_body_text"),
            LM.created_at.label("last_created_at"),
            PP_sender.pseudo.label("last_sender_pseudo"),
        )
        .join(
            CM_viewer,
            and_(
                CM_viewer.conversation_id == Conversation.id,
                CM_viewer.people_public_id == viewer_people_id,
            ),
        )
        .outerjoin(last_msg_id_sq, last_msg_id_sq.c.conv_id == Conversation.id)
        .outerjoin(LM, LM.id == last_msg_id_sq.c.last_message_id)
        .outerjoin(PP_sender, PP_sender.id == LM.sender_people_id)
        .where(Conversation.is_group.is_(True))  # ✅ uniquement groupes
        .order_by(Conversation.last_message_at.desc(), Conversation.created_at.desc())
    )

    rows = session.execute(stmt).all()

    out = []
    for r in rows:
        title = (r.title or "").strip() or "Groupe"

        out.append({
            "id": int(r.conversation_id),
            "title": title,
            "is_group": True,
            "idAdmin" : int(r.idAdmin or 0),
            "member_count": int(r.member_count or 0),

            "created_at": r.created_at.isoformat() if r.created_at else None,
            "last_message_at": r.last_message_at.isoformat() if r.last_message_at else None,

            "unread_count": int(r.unread_count or 0),

            "last_message": None if r.last_message_id is None else {
                "message_id": int(r.last_message_id),
                "sender_people_id": int(r.last_sender_people_id) if r.last_sender_people_id is not None else None,
                "pseudo": r.last_sender_pseudo or "",
                "body_text": r.last_body_text or "",
                "created_at": r.last_created_at.isoformat() if r.last_created_at else None,
                "is_seen": None,  # en groupe => pas pertinent (sauf si tu implémentes read receipts par membre)
            }
        })

    return out
