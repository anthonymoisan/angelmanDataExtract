from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger, Integer, Enum, Boolean, ForeignKey, TIMESTAMP
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db import Base


class ConversationMember(Base):
    __tablename__ = "T_Conversation_Member"

    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("T_Conversation.id", ondelete="CASCADE"),
        primary_key=True,
    )
    people_public_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("T_People_Public.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped[str] = mapped_column(
        Enum("member", "admin", name="conv_member_role"),
        default="member",
        nullable=False,
    )

    last_read_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_read_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    joined_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)

    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="members",
    )
    person: Mapped["PeoplePublic"] = relationship("PeoplePublic")
