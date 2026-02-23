# app/models/people_public.py
from sqlalchemy import (
    Column, Integer, String, SmallInteger, Enum, TIMESTAMP, Boolean, CHAR, Index
)
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class PeoplePublic(Base):
    __tablename__ = "T_People_Public"

    __table_args__ = (
        Index("idx_people_lang", "lang"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    city = Column(String(255), nullable=False)
    age_years = Column(SmallInteger, nullable=False)
    pseudo = Column(String(255), nullable=False)

    # ✅ Nouveau champ langue
    lang = Column(CHAR(2), nullable=False, default="fr", server_default="fr")

    is_connected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    status = Column(
        Enum("active", "anonymized", "deleted"),
        nullable=False,
        default="active"
    )

    created_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        nullable=False
    )

    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False
    )

    def setLang(self, lang: str):
        if not isinstance(lang, str):
            raise ValueError("lang must be a string")

        lang = lang.strip().lower()

        if len(lang) != 2:
            raise ValueError("lang must be a 2-letter code (ex: 'fr', 'en')")

        self.lang = lang

