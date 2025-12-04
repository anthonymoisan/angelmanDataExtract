# app/models/people_public.py
from sqlalchemy import (
    Column, Integer, String, SmallInteger, Enum, TIMESTAMP
)
from sqlalchemy.sql import func
from app.db import Base

class PeoplePublic(Base):
    __tablename__ = "T_People_Public"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(255), nullable=False)
    age_years = Column(SmallInteger, nullable=False)
    pseudo = Column(String(255), nullable=False)

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
