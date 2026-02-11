from __future__ import annotations

from datetime import datetime
from angelmanSyndromeConnexion.models.message import Message
from sqlalchemy import select
from zoneinfo import ZoneInfo
from tools.crypto_utils import encrypt_str

def utc_now() -> datetime:
    return datetime.now(ZoneInfo("Europe/Paris"))

#update des metaData pour un membre donné
def setMemberMetaData(session,member,last_read_message_id):
    member.last_read_message_id = last_read_message_id
    member.last_read_at = utc_now()
    session.commit()

def updateMessage(session, message_id: int, editor_people_id: int, new_text: str) -> Message:
    """
    Modifie un message si (et seulement si) l'auteur est celui qui édite.
    - conversation associé
    - message_id : ID du message à modifier
    - editor_people_id : ID de la personne qui tente d’éditer
    - new_text : contenu modifié
    """

    # 1️⃣ Charger le message
    message = session.execute(
        select(Message).where(Message.id == message_id)
    ).scalar_one_or_none()

    if not message:
        raise ValueError("Message introuvable")

    # 2️⃣ Empêcher la modification s’il a été supprimé
    if message.deleted_at is not None:
        raise PermissionError("Impossible de modifier un message supprimé")

    # 3️⃣ Vérifier que c’est bien l’auteur
    if message.sender_people_id != editor_people_id:
        raise PermissionError("Vous ne pouvez modifier que vos propres messages")

    # 4️⃣ Appliquer les modifications
    message.body_text = encrypt_str(new_text)
    message.status = "edited"
    message.edited_at = utc_now()
    session.commit()
    session.refresh(message)

    return message