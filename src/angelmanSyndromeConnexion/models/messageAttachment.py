from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, String, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db import Base


class MessageAttachment(Base):
    __tablename__ = "T_Message_Attachment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    message_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("T_Message.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)

    # --- Relations ---
    message: Mapped["Message"] = relationship(
        "Message",
        back_populates="attachments",
    )