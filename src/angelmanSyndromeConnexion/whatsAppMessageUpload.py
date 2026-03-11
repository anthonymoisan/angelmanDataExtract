from __future__ import annotations

import mimetypes
import os
import uuid
from pathlib import Path

from flask import current_app
from sqlalchemy import select
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from angelmanSyndromeConnexion.models.message import Message
from angelmanSyndromeConnexion.models.conversationMember import ConversationMember
from angelmanSyndromeConnexion.whatsAppCreate import addMessageAttachment


MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 Mo

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "video/mp4",
}


class UploadError(Exception):
    def __init__(self, message: str, status_code: int = 400, payload: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}

    def to_dict(self) -> dict:
        return {
            "ok": False,
            "error": self.message,
            **self.payload,
        }


def _ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def _get_file_size(uploaded_file: FileStorage) -> int:
    uploaded_file.stream.seek(0, os.SEEK_END)
    size = uploaded_file.stream.tell()
    uploaded_file.stream.seek(0)
    return size


def _detect_mime_type(uploaded_file: FileStorage) -> str:
    mime_type = (uploaded_file.mimetype or "").strip().lower()
    if mime_type:
        return mime_type

    guessed_mime, _ = mimetypes.guess_type(uploaded_file.filename or "")
    return (guessed_mime or "application/octet-stream").lower()


def _build_storage_paths(original_filename: str) -> tuple[str, str]:
    safe_name = secure_filename(original_filename or "file")
    ext = Path(safe_name).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"

    relative_dir = os.path.join("uploads", "message_attachments").replace("\\", "/")
    absolute_dir = os.path.join(current_app.root_path, relative_dir)
    _ensure_dir(absolute_dir)

    relative_path = os.path.join(relative_dir, unique_name).replace("\\", "/")
    absolute_path = os.path.join(current_app.root_path, relative_path)

    return absolute_path, relative_path


def _normalize_uploaded_files(uploaded_files: list[FileStorage] | None) -> list[FileStorage]:
    if not uploaded_files:
        return []

    return [f for f in uploaded_files if f is not None and getattr(f, "filename", None)]


def _validate_one_file(
    uploaded_file: FileStorage,
    allowed_mime_types: set[str] | None,
    max_file_size: int,
) -> tuple[int, str]:
    if not uploaded_file.filename:
        raise UploadError("empty filename", 400)

    file_size = _get_file_size(uploaded_file)

    if file_size <= 0:
        raise UploadError("empty file", 400)

    if file_size > max_file_size:
        raise UploadError(
            "file too large",
            413,
            {
                "file_name": uploaded_file.filename,
                "max_size_bytes": max_file_size,
                "max_size_mb": max_file_size // (1024 * 1024),
            },
        )

    mime_type = _detect_mime_type(uploaded_file)

    if allowed_mime_types is not None and mime_type not in allowed_mime_types:
        raise UploadError(
            "unsupported file type",
            400,
            {
                "file_name": uploaded_file.filename,
                "mime_type": mime_type,
            },
        )

    return file_size, mime_type


def attach_files_to_message(
    session,
    *,
    message_id: int,
    actor_people_id: int,
    uploaded_files: list[FileStorage],
    allowed_mime_types: set[str] | None = None,
    max_file_size: int = MAX_FILE_SIZE,
):
    """
    Attache une ou plusieurs pièces jointes à un message existant.
    Règle ici : seul l'auteur du message peut ajouter des PJ.
    """
    files = _normalize_uploaded_files(uploaded_files)
    if not files:
        raise UploadError("at least one file is required", 400)

    message = session.execute(
        select(Message).where(Message.id == message_id)
    ).scalar_one_or_none()

    if message is None:
        raise UploadError("message not found", 404)

    if int(message.sender_people_id) != int(actor_people_id):
        raise UploadError("only the author can attach files to this message", 403)

    member = session.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == message.conversation_id,
            ConversationMember.people_public_id == actor_people_id,
        )
    ).scalar_one_or_none()

    if member is None:
        raise UploadError("actor is not a member of the conversation", 403)

    file_infos: list[tuple[FileStorage, int, str]] = []
    for f in files:
        file_infos.append((f, *_validate_one_file(
            uploaded_file=f,
            allowed_mime_types=allowed_mime_types,
            max_file_size=max_file_size,
        )))

    saved_paths: list[str] = []
    attachments = []

    try:
        for f, file_size, mime_type in file_infos:
            absolute_path, relative_path = _build_storage_paths(f.filename)
            f.save(absolute_path)
            saved_paths.append(absolute_path)

            attachment = addMessageAttachment(
                session=session,
                message_id=message.id,
                file_path=relative_path,
                mime_type=mime_type,
                file_name=f.filename,
                file_size=file_size,
            )
            attachments.append(attachment)

        message.has_attachments = True
        session.commit()

        return message, attachments

    except Exception:
        session.rollback()
        for path in saved_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
        raise