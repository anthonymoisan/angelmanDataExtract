from __future__ import annotations

from flask import Blueprint, request, jsonify
from sqlalchemy import select,func

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
    toggleMessageReaction,
    create_group_conversation,
)
from angelmanSyndromeConnexion.whatsAppRead import(
    get_conversations_for_person_sorted,
    get_messages_for_conversation,
    get_member_ids_for_conversation,
    get_last_message_for_conversation,
    get_unread_count_chat,
    get_unread_count_GroupChat,
    get_conversations_summary_for_person,
    get_group_conversations_for_person_sorted,
    get_group_conversations_summary_for_person,
)

from angelmanSyndromeConnexion.whatsAppUpdate import(
    setMemberMetaData,
    updateMessage,
)

from angelmanSyndromeConnexion.whatsAppDelete import(
    deleteMessageSoft,
    leave_conversation,
    leave_group_conversation,
    delete_group_conversation,
)

from app.common.security import require_public_app_key

from tools.crypto_utils import decrypt_or_plain


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
        "people_public_admin_id" : conv.idAdmin,
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
    body = None
    if msg.body_text is not None:
        body = decrypt_or_plain(msg.body_text)

    return {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "sender_people_id": msg.sender_people_id,
        "body_text": body,
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

    data = request.get_json(silent=True) or {}
    p1_id = data.get("p1_id")
    p2_id = data.get("p2_id")
    title = data.get("title")

    if p1_id == p2_id:
        return jsonify({"error": "p1_id et p2_id doivent être différents"}), 400
    
    if p1_id is None or p2_id is None:
        return jsonify({"error": "p1_id et p2_id sont requis"}), 400

    try:
        p1_id = int(p1_id)
        p2_id = int(p2_id)
        title = f"Conversation {p1_id}-{p2_id}"
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


@bp.post("/conversations/group")
@require_public_app_key
def api_create_group_conversation_all_people():
    """
    POST /api/public/conversations/group
    Body:
      {
        "title": "Groupe 6",
        "people_public_admin_id": 12,
        "listIdPeoplesMember": [34, 56, 78]
        Pour le moment les conversations de groupe sont créés dans la langue de l'admin
      }
    """

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    people_public_admin_id = data.get("people_public_admin_id")
    list_ids = data.get("listIdPeoplesMember")

    if not title or not isinstance(title, str):
        return jsonify({"error": "Champ 'title' requis (string)."}), 400

    if people_public_admin_id is None or not isinstance(people_public_admin_id, int):
        return jsonify({"error": "Champ 'people_public_id' requis (int)."}), 400

    if list_ids is None or not isinstance(list_ids, list) or not all(isinstance(x, int) for x in list_ids):
        return jsonify({"error": "Champ 'listIdPeoplesMember' requis (list[int])."}), 400

    
    with get_session() as session:
        # Vérifier que l'admin existe
        admin_exists = session.execute(
            select(PeoplePublic.id).where(PeoplePublic.id == people_public_admin_id)
        ).scalar_one_or_none()
        if not admin_exists:
            return jsonify({"error": "Admin PeoplePublic introuvable"}), 404
        
        lang_admin = session.execute(
            select(PeoplePublic.lang).where(PeoplePublic.id == people_public_admin_id)
        ).scalar_one_or_none()

        # Vérifier que tous les membres existent (optionnel mais recommandé)
        unique_members = {pid for pid in list_ids if pid and pid != people_public_admin_id}
        if unique_members:
            existing = set(session.execute(
                select(PeoplePublic.id).where(PeoplePublic.id.in_(unique_members))
            ).scalars().all())

            missing = sorted(list(unique_members - existing))
            if missing:
                return jsonify({
                    "error": "Certains PeoplePublic sont introuvables",
                    "missing_ids": missing
                }), 404

        conv = create_group_conversation(
            session=session,
            people_public_admin_id=people_public_admin_id,
            langs = [lang_admin],
            listIdPeoplesMember=list_ids,
            title=title,
        )

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
        msg = session.execute(select(Message).where(Message.id == message_id)).scalar_one_or_none()
        if not msg:
            return jsonify({"error": "Message introuvable"}), 404

        person = session.execute(select(PeoplePublic).where(PeoplePublic.id == people_public_id)).scalar_one_or_none()
        if not person:
            return jsonify({"error": "PeoplePublic introuvable"}), 404

        deleted, reaction = toggleMessageReaction(session, message_id, people_public_id, emoji)

        if deleted:
            return jsonify({
                "message_id": message_id,
                "people_public_id": people_public_id,
                "emoji": emoji,
                "deleted": True
            }), 200

        return jsonify({**reaction_to_dict(reaction), "deleted": False}), 201

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

@bp.get("/people/<int:people_public_id>/conversationsGroup")
@require_public_app_key
def api_get_conversationsGroup_for_person_public(people_public_id: int):
    """
    GET /api/public/people/<people_public_id>/conversationsGroup
    Retourne la liste des conversations de groupe où la personne est membre,
    triées par last_message_at DESC puis created_at DESC.
    """
    with get_session() as session:
        person = session.execute(
            select(PeoplePublic).where(PeoplePublic.id == people_public_id)
        ).scalar_one_or_none()

        if not person:
            return jsonify({"error": "PeoplePublic introuvable"}), 404

        conversations = get_group_conversations_for_person_sorted(session, people_public_id)

        return jsonify([conversation_to_dict(c) for c in conversations]), 200
    

@bp.get("/conversations/<int:conversation_id>/messages")
@require_public_app_key
def api_get_messages_for_conversation_public(conversation_id: int):
    """
    GET /api/public/conversations/<conversation_id>/messages
    Optionnel: ?viewer_people_id=<id>
    - Retourne la liste des messages triés ASC
    - Ajoute is_seen sur les messages envoyés par viewer (si 1–1)
    """
    viewer_people_id = request.args.get("viewer_people_id", type=int)

    with get_session() as session:
        conv = session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        ).scalar_one_or_none()

        if not conv:
            return jsonify({"error": "Conversation introuvable"}), 404

        # --- Determine other_last_read_message_id (seulement 1–1 et viewer connu) ---
        other_last_read_message_id = 0
        if viewer_people_id is not None and not conv.is_group:
            # Récupère l'autre membre (celui != viewer)
            other_member = session.execute(
                select(ConversationMember)
                .where(ConversationMember.conversation_id == conversation_id)
                .where(ConversationMember.people_public_id != viewer_people_id)
            ).scalars().first()

            if other_member and other_member.last_read_message_id:
                other_last_read_message_id = int(other_member.last_read_message_id)

        rows = get_messages_for_conversation(session, conversation_id)

        messages_by_id: dict[int, dict] = {}

        for r in rows:
            msg = messages_by_id.get(r.message_id)
            if msg is None:
                msg = {
                    "message_id": r.message_id,
                    "body_text": decrypt_or_plain(r.body_text) if r.body_text else None,
                    "pseudo": r.author_pseudo,
                    "sender_people_id": r.sender_people_id,
                    "created_at": _dt_to_str(r.created_at),
                    "reply_to_message_id": r.reply_to_message_id,
                    "reply_body_text": decrypt_or_plain(r.reply_body_text) if r.reply_body_text else None,
                    "reactions": [],
                }

                # ✅ Ajout "vu" (Option A) : seulement si viewer connu et message envoyé par viewer
                if viewer_people_id is not None and not conv.is_group:
                    if r.sender_people_id == viewer_people_id:
                        msg["is_seen"] = (r.message_id <= other_last_read_message_id)
                    else:
                        # tu peux omettre ce champ, ou le mettre à None
                        msg["is_seen"] = None

                messages_by_id[r.message_id] = msg

            if getattr(r, "reaction_emoji", None) is not None:
                msg["reactions"].append(
                    {
                        "emoji": r.reaction_emoji,
                        "people_public_id": r.reaction_people_id,
                        "pseudo": r.reaction_pseudo,
                    }
                )
        messages = list(messages_by_id.values())
        return jsonify(messages), 200

@bp.post("/conversations/<int:conversation_id>/read")
@require_public_app_key
def api_mark_conversation_read_public(conversation_id: int):
    """
    POST /api/public/conversations/<conversation_id>/read
    Body:
    {
      "people_public_id": <int>,
      "last_read_message_id": <int>
    }
    """
    payload = request.get_json(silent=True) or {}
    people_public_id = payload.get("people_public_id")
    last_read_message_id = payload.get("last_read_message_id")

    if not isinstance(people_public_id, int) or not isinstance(last_read_message_id, int):
        return jsonify({"error": "people_public_id et last_read_message_id sont requis"}), 400

    with get_session() as session:
        # Vérifie conversation
        conv = session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        ).scalar_one_or_none()
        if not conv:
            return jsonify({"error": "Conversation introuvable"}), 404

        # Vérifie membership
        cm = session.execute(
            select(ConversationMember)
            .where(ConversationMember.conversation_id == conversation_id)
            .where(ConversationMember.people_public_id == people_public_id)
        ).scalar_one_or_none()

        if not cm:
            return jsonify({"error": "Membre introuvable dans cette conversation"}), 404

        # ✅ ne jamais reculer
        current = int(cm.last_read_message_id or 0)
        if last_read_message_id > current:
            cm.last_read_message_id = last_read_message_id
            cm.last_read_at = func.now()
            session.commit()

        return jsonify({"ok": True}), 200


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

@bp.post("/conversations/group/<int:conversation_id>/leave")
@require_public_app_key
def api_leave_conversationGroupe_private(conversation_id: int):
    """
    POST /api/public/conversations/group/<conversation_id>/leave
    Body JSON :
    {
      "people_public_id": 1,
      "soft_delete_own_messages": true,   (optionnel, défaut: true)
      "delete_empty_conversation": true   (optionnel, défaut: true)
    }

    people_public_id est déduit de l'utilisateur authentifié.
    """
    data = request.get_json(silent=True) or {}

    people_public_id = data.get("people_public_id")
    soft_delete_own_messages = bool(data.get("soft_delete_own_messages", True))
    delete_empty_conversation = bool(data.get("delete_empty_conversation", True))

    if people_public_id is None:
        return jsonify({"error": "Utilisateur non authentifié"}), 401

    with get_session() as session:
        ok = leave_group_conversation(
            session,
            conversation_id=conversation_id,
            people_public_id=int(people_public_id),
            soft_delete_own_messages=soft_delete_own_messages,
            delete_empty_conversation=delete_empty_conversation,
        )

        if not ok:
            return jsonify({"error": "Conversation Group introuvable ou non membre"}), 404

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
    Optionnel: ?viewer_people_id=<id>

    - Retourne le dernier message non supprimé
    - Ajoute is_seen (Option A) si viewer_people_id est membre
    - Refuse si viewer_people_id n'est pas membre
    """
    viewer_people_id = request.args.get("viewer_people_id", type=int)

    with get_session() as session:
        conv = session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        ).scalar_one_or_none()

        if not conv:
            return jsonify({"error": "Conversation introuvable"}), 404

        # ✅ 1) Si viewer_people_id est fourni : vérifier qu'il est membre
        viewer_member = None
        if viewer_people_id is not None:
            viewer_member = session.execute(
                select(ConversationMember).where(
                    ConversationMember.conversation_id == conversation_id,
                    ConversationMember.people_public_id == viewer_people_id,
                )
            ).scalar_one_or_none()

            if not viewer_member:
                # Choix possible: 403 (forbidden) ou 404 (ne pas révéler l'existence)
                return jsonify({"error": "forbidden"}), 403

        row = get_last_message_for_conversation(session, conversation_id)
        if row is None:
            return jsonify({"last_message": None}), 200

        # --------------------
        # ✅ 2) Calcul du "vu" (Option A)
        # --------------------
        is_seen = None

        if viewer_people_id is not None and not conv.is_group:
            # "other_member" = l'autre participant (pour conv privées)
            other_member = session.execute(
                select(ConversationMember).where(
                    ConversationMember.conversation_id == conversation_id,
                    ConversationMember.people_public_id != viewer_people_id,
                )
            ).scalars().first()

            other_last_read_message_id = int(other_member.last_read_message_id or 0) if other_member else 0

            sender_people_id = row.sender_people_id  # ou row["sender_people_id"] selon ta version

            # Option A : on ne calcule is_seen que si le dernier message est envoyé par le viewer
            if sender_people_id is not None and int(sender_people_id) == int(viewer_people_id):
                is_seen = int(row.message_id) <= other_last_read_message_id

        return jsonify({
            "message_id": int(row.message_id),
            "sender_people_id": int(row.sender_people_id) if row.sender_people_id is not None else None,
            "body_text": decrypt_or_plain(row.body_text),
            "pseudo": decrypt_or_plain(row.pseudo),
            "created_at": _dt_to_str(row.created_at),
            "is_seen": is_seen,  # bool | null
        }), 200

@bp.get("/people/<int:people_public_id>/conversationsUnRead")
@require_public_app_key
def api_get_conversations_for_person_publicUnRead(people_public_id: int):
    with get_session() as session:
        # 🔒 vérifier que la personne existe
        person = session.execute(
            select(PeoplePublic).where(PeoplePublic.id == people_public_id)
        ).scalar_one_or_none()
        if not person:
            return jsonify({"error": "PeoplePublic introuvable"}), 404

        conversations = get_conversations_for_person_sorted(session, people_public_id)

        out = []
        for c in conversations:
            # unread_count pour CE viewer (= people_public_id)
            unread = get_unread_count_chat(session, c.id, people_public_id)

            out.append({
                **conversation_to_dict(c),
                "unread_count": unread,
            })

        return jsonify(out), 200

@bp.get("/people/<int:people_public_id>/conversationsUnReadGroup")
@require_public_app_key
def api_get_conversations_for_person_publicUnReadGroup(people_public_id: int):
    with get_session() as session:
        # 🔒 vérifier que la personne existe
        person = session.execute(
            select(PeoplePublic).where(PeoplePublic.id == people_public_id)
        ).scalar_one_or_none()
        if not person:
            return jsonify({"error": "PeoplePublic introuvable"}), 404

        conversations = get_group_conversations_for_person_sorted(session, people_public_id)

        out = []
        for c in conversations:
            # unread_count pour CE viewer (= people_public_id)
            unread = get_unread_count_GroupChat(session, c.id, people_public_id)

            out.append({
                **conversation_to_dict(c),
                "unread_count": unread,
            })

        return jsonify(out), 200




@bp.get("/people/<int:people_public_id>/conversationsSummary")
@require_public_app_key
def api_get_conversations_summary_public(people_public_id: int):
    """
    GET /api/public/people/<id>/conversationsSummary

    Retourne une liste prête à afficher :
      - conversation fields
      - unread_count
      - other_people_id (si 1-1)
      - last_message { message_id, sender_people_id, pseudo, body_text, created_at, is_seen }
    """
    with get_session() as session:
        person = session.execute(
            select(PeoplePublic).where(PeoplePublic.id == people_public_id)
        ).scalar_one_or_none()
        if not person:
            return jsonify({"error": "PeoplePublic introuvable"}), 404

        data = get_conversations_summary_for_person(session, people_public_id)
        return jsonify(data), 200
    

@bp.get("/people/<int:people_public_id>/conversationsGroupSummary")
@require_public_app_key
def api_get_conversationsGroup_summary_public(people_public_id: int):
    """
    GET /api/public/people/<id>/conversationsGroupSummary

    Retourne une liste prête à afficher :
      - conversation fields
      - unread_count
      - nombre de membres
      - last_message { message_id, sender_people_id, pseudo, body_text, created_at, is_seen }
    """
    with get_session() as session:
        person = session.execute(
            select(PeoplePublic).where(PeoplePublic.id == people_public_id)
        ).scalar_one_or_none()
        if not person:
            return jsonify({"error": "PeoplePublic introuvable"}), 404

        data = get_group_conversations_summary_for_person(session, people_public_id)
        return jsonify(data), 200
    
@bp.delete("/conversations/group/<int:conversation_id>")
@require_public_app_key
def api_public_delete_group_conversation(conversation_id: int):
    """
    DELETE /api/public/conversations/group/<conversation_id>
    Body:
      {
        "people_public_admin_id": 12,
        "hard_delete": true
      }
    """
    data = request.get_json(silent=True) or {}

    people_public_admin_id = data.get("people_public_admin_id")
    hard_delete = data.get("hard_delete", True)

    if people_public_admin_id is None or not isinstance(people_public_admin_id, int):
        return jsonify({"error": "Champ 'people_public_admin_id' requis (int)."}), 400

    if not isinstance(hard_delete, bool):
        return jsonify({"error": "Champ 'hard_delete' doit être un booléen."}), 400

    with get_session() as session:
        ok = delete_group_conversation(
            session=session,
            conversation_id=conversation_id,
            people_public_admin_id=people_public_admin_id,
            hard_delete=hard_delete,
        )

        if not ok:
            # Comme ta méthode renvoie False pour plusieurs causes,
            # on renvoie un message générique "forbidden or not found".
            return jsonify({
                "error": "Suppression impossible (conversation introuvable, pas un groupe, pas membre, ou pas admin)."
            }), 403

        return jsonify({"success": True}), 200

  