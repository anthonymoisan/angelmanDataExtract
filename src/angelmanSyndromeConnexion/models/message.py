from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger, Integer, String, Text, Enum,
    Boolean, ForeignKey, TIMESTAMP
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db import Base  # Base SQLAlchemy


class Message(Base):
    __tablename__ = "T_Message"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("T_Conversation.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_people_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("T_People_Public.id", ondelete="RESTRICT"),
        nullable=False,
    )

    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reply_to_message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("T_Message.id", ondelete="SET NULL"),
        nullable=True,
    )

    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("normal", "edited", "deleted", name="message_status"),
        default="normal",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)

    # --- Relations (TOUJOURS avec des strings pour éviter les imports circulaires) ---

    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )

    sender: Mapped["PeoplePublic"] = relationship(
        "PeoplePublic",
    )

    attachments: Mapped[list["MessageAttachment"]] = relationship(
        "MessageAttachment",
        back_populates="message",
        cascade="all, delete-orphan",
    )

    reactions: Mapped[list["MessageReaction"]] = relationship(
        "MessageReaction",
        back_populates="message",
        cascade="all, delete-orphan",
    )

    reply_to: Mapped["Message | None"] = relationship(
        "Message",
        remote_side=[id],
        uselist=False,
    )
