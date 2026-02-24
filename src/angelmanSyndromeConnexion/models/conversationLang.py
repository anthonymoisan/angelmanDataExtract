from __future__ import annotations

from sqlalchemy import BigInteger, CHAR, ForeignKey, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db import Base


class ConversationLang(Base):
    __tablename__ = "T_Conversation_Lang"

    __table_args__ = (
        Index("idx_conv_lang_lang", "lang"),
    )

    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "T_Conversation.id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        primary_key=True,
    )

    lang: Mapped[str] = mapped_column(
        CHAR(2),
        primary_key=True,
        nullable=False,
    )

    # Relation ORM vers la conversation
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="langs",
    )
