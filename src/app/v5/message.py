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

from app.common.security import ratelimit
from app.common.basic_auth import require_basic,require_internal

bp = Blueprint("v5_message", __name__)
bp.before_request(require_internal)

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
@ratelimit(3)
@require_basic
def api_get_or_create_private_conversation_private():
    """
    POST /api/private/conversations/private
    Body JSON :
    {
      "p1_id": 1,
      "p2_id": 2,
      "title": "Optionnel"
    }
    """

    data = request.get_json(silent=True) or {}
    
    p1_id = data.get("p1_id")
    p2_id = data.get("p2_id")
    title = data.get("title")

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
@ratelimit(3)
@require_basic
def api_add_conversation_member_private(conversation_id: int):
    """
    POST /api/private/conversations/<conversation_id>/members
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

        return jsonify(member_to_dict(member)), 201


# =========================================
# 3️⃣ Ajouter un message dans une conversation
# =========================================

@bp.post("/conversations/<int:conversation_id>/messages")
@ratelimit(3)
@require_basic
def api_add_message_private(conversation_id: int):
    """
    POST /api/private/conversations/<conversation_id>/messages
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
            return jsonify(
                {"error": "L'expéditeur n'est pas membre de la conversation"}
            ), 403

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
@ratelimit(3)
@require_basic
def api_add_message_reaction_private(message_id: int):
    """
    POST /api/private/messages/<message_id>/reactions
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
