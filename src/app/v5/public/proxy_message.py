from __future__ import annotations

from flask import Blueprint, request, jsonify
from sqlalchemy import select

from app.db import get_session

from angelmanSyndromeConnexion.models.people_public import PeoplePublic
from angelmanSyndromeConnexion.models.conversation import Conversation
from angelmanSyndromeConnexion.models.conversationMember import ConversationMember
from angelmanSyndromeConnexion.models.message import Message
from angelmanSyndromeConnexion.models.messageReaction import MessageReaction

from angelmanSyndromeConnexion.whatsAppCreate import (
    get_or_create_private_conversation,
    addConversationMember,
    addMessage,
    addMessageReaction,
)
from angelmanSyndromeConnexion.whatsAppRead import(
    get_conversations_for_person_sorted,
    get_messages_for_conversation,
    get_member_ids_for_conversation,
    get_last_message_for_conversation,
)

from angelmanSyndromeConnexion.whatsAppUpdate import(
    setMemberMetaData,
    updateMessage,
)

from angelmanSyndromeConnexion.whatsAppDelete import(
    deleteMessageSoft,
    leave_conversation,
)

from app.common.security import require_public_app_key

bp = Blueprint("messages_public", __name__, url_prefix="/api/public")


# -----------------------
# Helpers de sérialisation
# -----------------------

def _dt_to_str(dt):
    return dt.isoformat() if dt is not None else None


def conversation_to_dict(conv: Conversation):
    return {
        "id": conv.id,
        "title": conv.title,
        "is_group": conv.is_group,
        "created_at": _dt_to_str(conv.created_at),
        "last_message_at": _dt_to_str(conv.last_message_at),
    }


def member_to_dict(m: ConversationMember):
    return {
        "conversation_id": m.conversation_id,
        "people_public_id": m.people_public_id,
        "role": m.role,
        "last_read_message_id": m.last_read_message_id,
        "last_read_at": _dt_to_str(m.last_read_at),
        "is_muted": m.is_muted,
        "joined_at": _dt_to_str(m.joined_at),
    }


def message_to_dict(msg: Message):
    return {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "sender_people_id": msg.sender_people_id,
        "body_text": msg.body_text,
        "reply_to_message_id": msg.reply_to_message_id,
        "has_attachments": msg.has_attachments,
        "status": msg.status,
        "created_at": _dt_to_str(msg.created_at),
        "edited_at": _dt_to_str(msg.edited_at),
        "deleted_at": _dt_to_str(msg.deleted_at),
    }


def reaction_to_dict(r: MessageReaction):
    return {
        "message_id": r.message_id,
        "people_public_id": r.people_public_id,
        "emoji": r.emoji,
        "created_at": _dt_to_str(r.created_at),
    }


# =========================================
# 1️⃣ Conversation privée (get or create)
# =========================================

@bp.post("/conversations/private")
@require_public_app_key
def api_get_or_create_private_conversation():
    """
    POST /api/public/conversations/private
    Body JSON :
    {
      "p1_id": 1,
      "p2_id": 2,
      "title": "Optionnel"
    }
    """

    p1_id = data.get("p1_id")
    p2_id = data.get("p2_id")
    title = data.get("title")
    data = request.get_json(silent=True) or {}

    if p1_id is None or p2_id is None:
        return jsonify({"error": "p1_id et p2_id sont requis"}), 400

    try:
        p1_id = int(p1_id)
        p2_id = int(p2_id)
    except ValueError:
        return jsonify({"error": "p1_id et p2_id doivent être des entiers"}), 400

    with get_session() as session:
        # Optionnel : vérifier que les people existent
        for pid in (p1_id, p2_id):
            exists = session.execute(
                select(PeoplePublic).where(PeoplePublic.id == pid)
            ).scalar_one_or_none()
            if not exists:
                return jsonify({"error": f"PeoplePublic {pid} introuvable"}), 404

        conv = get_or_create_private_conversation(session, p1_id, p2_id, title)
        return jsonify(conversation_to_dict(conv)), 200


# =========================================
# 2️⃣ Ajouter un membre à une conversation
# =========================================

@bp.post("/conversations/<int:conversation_id>/members")
@require_public_app_key
def api_add_conversation_member(conversation_id: int):
    """
    POST /api/public/conversations/<conversation_id>/members
    Body JSON :
    {
      "people_public_id": 123,
      "role": "member" | "admin"
    }
    """
    data = request.get_json(silent=True) or {}
    people_public_id = data.get("people_public_id")
    role = data.get("role", "member")

    if people_public_id is None:
        return jsonify({"error": "people_public_id est requis"}), 400

    try:
        people_public_id = int(people_public_id)
    except ValueError:
        return jsonify({"error": "people_public_id doit être un entier"}), 400

    with get_session() as session:
        conv = session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        ).scalar_one_or_none()

        if not conv:
            return jsonify({"error": "Conversation introuvable"}), 404

        person = session.execute(
            select(PeoplePublic).where(PeoplePublic.id == people_public_id)
        ).scalar_one_or_none()

        if not person:
            return jsonify({"error": "PeoplePublic introuvable"}), 404

        member = addConversationMember(session, conversation_id, people_public_id, role)
        # addConversationMember ne commit pas => on laisse le contextmanager faire

        return jsonify(member_to_dict(member)), 201


# =========================================
# 3️⃣ Ajouter un message dans une conversation
# =========================================

@bp.post("/conversations/<int:conversation_id>/messages")
@require_public_app_key
def api_add_message(conversation_id: int):
    """
    POST /api/public/conversations/<conversation_id>/messages
    Body JSON :
    {
      "sender_people_id": 123,
      "body_text": "Hello 👋",
      "reply_to_message_id": 45 (optionnel),
      "has_attachments": false,
      "status": "normal"
    }
    """
    data = request.get_json(silent=True) or {}

    sender_people_id = data.get("sender_people_id")
    body_text = data.get("body_text")
    reply_to_message_id = data.get("reply_to_message_id")
    has_attachments = bool(data.get("has_attachments", False))
    status = data.get("status", "normal")

    if sender_people_id is None:
        return jsonify({"error": "sender_people_id est requis"}), 400

    try:
        sender_people_id = int(sender_people_id)
    except ValueError:
        return jsonify({"error": "sender_people_id doit être un entier"}), 400

    if reply_to_message_id is not None:
        try:
            reply_to_message_id = int(reply_to_message_id)
        except ValueError:
            return jsonify({"error": "reply_to_message_id doit être un entier"}), 400

    with get_session() as session:
        conv = session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        ).scalar_one_or_none()
        if not conv:
            return jsonify({"error": "Conversation introuvable"}), 404

        sender = session.execute(
            select(PeoplePublic).where(PeoplePublic.id == sender_people_id)
        ).scalar_one_or_none()
        if not sender:
            return jsonify({"error": "PeoplePublic introuvable"}), 404

        # Optionnel : vérifier que le sender est membre de la conversation
        member = session.execute(
            select(ConversationMember).where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.people_public_id == sender_people_id,
            )
        ).scalar_one_or_none()
        if not member:
            return jsonify({"error": "L'expéditeur n'est pas membre de la conversation"}), 403

        msg = addMessage(
            session,
            conv,
            sender_people_id=sender_people_id,
            body_text=body_text,
            reply_to_message_id=reply_to_message_id,
            has_attachments=has_attachments,
            status=status,
        )

        return jsonify(message_to_dict(msg)), 201


# =========================================
# 4️⃣ Ajouter une réaction à un message
# =========================================

@bp.post("/messages/<int:message_id>/reactions")
@require_public_app_key
def api_add_message_reaction(message_id: int):
    """
    POST /api/public/messages/<message_id>/reactions
    Body JSON :
    {
      "people_public_id": 123,
      "emoji": "👍"
    }
    """
    data = request.get_json(silent=True) or {}
    people_public_id = data.get("people_public_id")
    emoji = data.get("emoji")

    if people_public_id is None or not emoji:
        return jsonify({"error": "people_public_id et emoji sont requis"}), 400

    try:
        people_public_id = int(people_public_id)
    except ValueError:
        return jsonify({"error": "people_public_id doit être un entier"}), 400

    with get_session() as session:
        msg = session.execute(
            select(Message).where(Message.id == message_id)
        ).scalar_one_or_none()
        if not msg:
            return jsonify({"error": "Message introuvable"}), 404

        person = session.execute(
            select(PeoplePublic).where(PeoplePublic.id == people_public_id)
        ).scalar_one_or_none()
        if not person:
            return jsonify({"error": "PeoplePublic introuvable"}), 404

        reaction = addMessageReaction(
            session,
            message_id=message_id,
            people_public_id=people_public_id,
            emoji=emoji,
        )

        return jsonify(reaction_to_dict(reaction)), 201


@bp.get("/people/<int:people_public_id>/conversations")
@require_public_app_key
def api_get_conversations_for_person_public(people_public_id: int):
    """
    GET /api/public/people/<people_public_id>/conversations
    Retourne la liste des conversations où la personne est membre,
    triées par last_message_at DESC puis created_at DESC.
    """
    with get_session() as session:
        person = session.execute(
            select(PeoplePublic).where(PeoplePublic.id == people_public_id)
        ).scalar_one_or_none()

        if not person:
            return jsonify({"error": "PeoplePublic introuvable"}), 404

        conversations = get_conversations_for_person_sorted(session, people_public_id)

        return jsonify([conversation_to_dict(c) for c in conversations]), 200

@bp.get("/conversations/<int:conversation_id>/messages")
@require_public_app_key
def api_get_messages_for_conversation_public(conversation_id: int):
    """
    GET /api/public/conversations/<conversation_id>/messages
    Retourne la liste des messages de la conversation,
    triés par created_at ASC,
    avec gestion des messages reply.
    """
    with get_session() as session:

        conv = session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        ).scalar_one_or_none()

        if not conv:
            return jsonify({"error": "Conversation introuvable"}), 404

        rows = get_messages_for_conversation(session, conversation_id)

        messages = [
            {
                "message_id": r.id,
                "body_text": r.body_text,
                "pseudo": r.pseudo,
                "sender_people_id": r.sender_people_id,
                "created_at": _dt_to_str(r.created_at),
                "reply_to_message_id": r.reply_to_message_id,
                "reply_body_text": r.reply_body_text,
            }
            for r in rows
        ]

        return jsonify(messages), 200

@bp.post("/conversations/<int:conversation_id>/members/<int:people_public_id>/metadata")
@require_public_app_key
def api_update_member_metadata_public(conversation_id: int, people_public_id: int):
    """
    POST /api/public/conversations/<conversation_id>/members/<people_public_id>/metadata
    Body JSON :
    {
       "last_read_message_id": 123
    }
    """
    data = request.get_json(silent=True) or {}
    last_read_message_id = data.get("last_read_message_id")

    if last_read_message_id is None:
        return jsonify({"error": "last_read_message_id est requis"}), 400

    try:
        last_read_message_id = int(last_read_message_id)
    except ValueError:
        return jsonify({"error": "last_read_message_id doit être un entier"}), 400

    with get_session() as session:
        member = session.execute(
            select(ConversationMember).where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.people_public_id == people_public_id,
            )
        ).scalar_one_or_none()

        if not member:
            return jsonify({"error": "Membre introuvable"}), 404

        setMemberMetaData(session, member, last_read_message_id)

        return jsonify(member_to_dict(member)), 200

@bp.post("/messages/<int:message_id>/edit")
@require_public_app_key
def api_edit_message_public(message_id: int):
    """
    POST /api/public/messages/<message_id>/edit
    Body JSON :
    {
        "editor_people_id": 1,
        "new_text": "Message modifié"
    }
    """
    data = request.get_json(silent=True) or {}
    editor_people_id = data.get("editor_people_id")
    new_text = data.get("new_text")

    if not editor_people_id or not new_text:
        return jsonify({"error": "editor_people_id et new_text sont requis"}), 400

    try:
        editor_people_id = int(editor_people_id)
    except ValueError:
        return jsonify({"error": "editor_people_id doit être un entier"}), 400

    with get_session() as session:
        try:
            message = updateMessage(session, message_id, editor_people_id, new_text)
        except ValueError as e:
            return jsonify({"error": str(e)}), 404
        except PermissionError as e:
            return jsonify({"error": str(e)}), 403

        return jsonify(message_to_dict(message)), 200

@bp.delete("/messages/<int:message_id>")
@require_public_app_key
def api_soft_delete_message_public(message_id: int):
    """
    DELETE /api/public/messages/<message_id>
    Suppression logique d'un message (soft delete).
    """
    with get_session() as session:
        msg = session.execute(
            select(Message).where(Message.id == message_id)
        ).scalar_one_or_none()

        if not msg:
            return jsonify({"error": "Message introuvable"}), 404

        ok = deleteMessageSoft(session, message_id)
        if not ok:
            return jsonify({"error": "Message introuvable"}), 404

        msg = session.execute(
            select(Message).where(Message.id == message_id)
        ).scalar_one_or_none()

        return jsonify(message_to_dict(msg)), 200

@bp.post("/conversations/<int:conversation_id>/leave")
@require_public_app_key
def api_leave_conversation_public(conversation_id: int):
    """
    POST /api/public/conversations/<conversation_id>/leave
    Body JSON :
    {
      "people_public_id": 1,
      "soft_delete_own_messages": true,   (optionnel)
      "delete_empty_conversation": true   (optionnel)
    }
    """
    data = request.get_json(silent=True) or {}

    people_public_id = data.get("people_public_id")
    soft_delete_own_messages = bool(data.get("soft_delete_own_messages", True))
    delete_empty_conversation = bool(data.get("delete_empty_conversation", True))

    if people_public_id is None:
        return jsonify({"error": "people_public_id est requis"}), 400

    try:
        people_public_id = int(people_public_id)
    except ValueError:
        return jsonify({"error": "people_public_id doit être un entier"}), 400

    with get_session() as session:
        ok = leave_conversation(
            session,
            conversation_id=conversation_id,
            people_public_id=people_public_id,
            soft_delete_own_messages=soft_delete_own_messages,
            delete_empty_conversation=delete_empty_conversation,
        )

        if not ok:
            return jsonify(
                {"error": "Conversation introuvable ou personne non membre"}
            ), 404

        return jsonify({"success": True}), 200

@bp.get("/conversations/<int:conversation_id>/members/ids")
@require_public_app_key
def api_get_member_ids_public(conversation_id: int):
    """
    GET /api/public/conversations/<conversation_id>/members/ids
    Retourne la liste des IDs people_public_id présents dans la conversation.
    """
    with get_session() as session:

        conv = session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        ).scalar_one_or_none()

        if not conv:
            return jsonify({"error": "Conversation introuvable"}), 404

        ids = get_member_ids_for_conversation(session, conversation_id)

        return jsonify({"conversation_id": conversation_id, "member_ids": ids}), 200
    
@bp.get("/conversations/<int:conversation_id>/messages/last")
@require_public_app_key
def api_get_last_message_public(conversation_id: int):
    """
    GET /api/public/conversations/<conversation_id>/messages/last
    Retourne le dernier message (non supprimé).
    """
    with get_session() as session:

        conv = session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        ).scalar_one_or_none()

        if not conv:
            return jsonify({"error": "Conversation introuvable"}), 404

        row = get_last_message_for_conversation(session, conversation_id)

        if row is None:
            return jsonify({"last_message": None}), 200

        return jsonify({
            "body_text": row.body_text,
            "pseudo": row.pseudo,
            "created_at": _dt_to_str(row.created_at)
        }), 200
