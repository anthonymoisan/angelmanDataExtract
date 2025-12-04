from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger, Integer, String, TIMESTAMP, ForeignKey
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db import Base


class MessageReaction(Base):
    __tablename__ = "T_Message_Reaction"

    message_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("T_Message.id", ondelete="CASCADE"),
        primary_key=True,
    )
    people_public_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("T_People_Public.id", ondelete="CASCADE"),
        primary_key=True,
    )
    emoji: Mapped[str] = mapped_column(String(16), primary_key=True)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)

    message: Mapped["Message"] = relationship(
        "Message",
        back_populates="reactions",
    )
