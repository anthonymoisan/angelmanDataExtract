# app/db.py
from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime  # (si tu t’en sers ailleurs)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from tools.utilsTools import get_db_params, _build_db_url

try:
    # sshtunnel n’est nécessaire que en local
    from sshtunnel import SSHTunnelForwarder
except ImportError:
    SSHTunnelForwarder = None  # pour éviter un crash si pas installé

# -------------------------------------------------------------------
# Détection LOCAL vs PythonAnywhere
# -------------------------------------------------------------------

LOCAL_CONNEXION = not os.environ.get(
    "PYTHONANYWHERE_DOMAIN", ""
).lower().startswith("eu.pythonanywhere")

# Lecture de la config DB (host, user, password, etc.)
cfg = get_db_params(bAngelmanResult=False)

# -------------------------------------------------------------------
# Tunnel SSH éventuel (LOCAL uniquement)
# -------------------------------------------------------------------

_tunnel = None

def _init_db_url() -> str:
    global _tunnel

    if LOCAL_CONNEXION:
        if SSHTunnelForwarder is None:
            raise RuntimeError(
                "sshtunnel n’est pas installé alors que LOCAL_CONNEXION=True. "
                "pip install sshtunnel ou mets LOCAL_CONNEXION=False."
            )

        # On ouvre le tunnel UNE FOIS pour tout le process
        if _tunnel is None:
            _tunnel = SSHTunnelForwarder(
                (cfg["ssh_host"]),
                ssh_username=cfg["ssh_user"],
                ssh_password=cfg["ssh_pass"],
                remote_bind_address=(cfg["db_host"], 3306),
            )
            _tunnel.start()

        local_port = _tunnel.local_bind_port
        return _build_db_url(cfg, local_port)

    # Sur PythonAnywhere → pas de tunnel, on se connecte directement
    return _build_db_url(cfg)


DB_URL = _init_db_url()

# -------------------------------------------------------------------
# SQLAlchemy Engine + Session
# -------------------------------------------------------------------

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,  # Mets True si tu veux voir les requêtes SQL
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

# -------------------------------------------------------------------
# Utilitaires pour Flask / scripts
# -------------------------------------------------------------------

def get_db():
    """
    Générateur de Session pour intégration type FastAPI/Flask (dependency).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_session() -> Session:
    """
    Usage typique :

    from app.db import get_session

    with get_session() as db:
        obj = db.query(MyModel).first()
    """
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
