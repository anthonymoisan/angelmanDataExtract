from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger, String, Boolean, TIMESTAMP
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db import Base


class Conversation(Base):
    __tablename__ = "T_Conversation"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_group: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)

    members: Mapped[list["ConversationMember"]] = relationship(
        "ConversationMember",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
