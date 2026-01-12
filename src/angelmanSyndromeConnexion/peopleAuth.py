# src/angelmanSyndromeConnexion/peopleAuth.py
from __future__ import annotations

from typing import Optional, Tuple
from sqlalchemy import text
import unicodedata
from tools.logger import setup_logger
from tools.utilsTools import _run_query
import tools.crypto_utils as crypto  # email_sha256, verify_password_argon2

logger = setup_logger(debug=False)


def _to_bytes_phc(x) -> bytes:
    """
    S'assure que le hash PHC ($argon2id$...) est bien en bytes.
    Certains drivers DB peuvent renvoyer str, d'autres bytes/bytearray.
    """
    if isinstance(x, (bytes, bytearray)):
        return bytes(x)
    return str(x).encode("utf-8", "strict")


def _get_auth_row_by_email(email: str,bAngelmanResult=True) -> Optional[Tuple[int, bytes]]:
    """
    Retourne (id, password_hash_bytes) pour un email donné,
    ou None si l'utilisateur n'existe pas.
    """
    try:
        sha = crypto.email_sha256(email)  # BINARY(32) côté SQL
        row = _run_query(
            text("""
                SELECT person_id, password_hash
                FROM T_People_Identity
                WHERE email_sha = :sha
                LIMIT 1
            """),
            params={"sha": sha},
            return_result=True,
            bAngelmanResult = bAngelmanResult
        )
        if not row:
            return None
        pid, pwd_hash_db = row[0]
        return int(pid), _to_bytes_phc(pwd_hash_db)
    except Exception:
        logger.exception("Lookup utilisateur par email échoué")
        return None


def authenticate_email_password(email: str, password: str, bAngelmanResult:bool) -> bool:
    """
    True si (email, password) est valide, sinon False.
    Ne lève pas d'exception (utile pour endpoints).
    """
    try:
        row = _get_auth_row_by_email(email,bAngelmanResult=bAngelmanResult)
        if not row:
            return False
        _pid, stored_hash_bytes = row
        return bool(crypto.verify_password_argon2(password, stored_hash_bytes))
    except Exception:
        logger.exception("authenticate_email_password échec")
        return False


def authenticate_and_get_id(email: str, password: str, bAngelmanResult=False) -> Optional[int]:
    """
    Retourne l'ID de l'utilisateur si les identifiants sont valides, sinon None.
    """
    try:
        row = _get_auth_row_by_email(email, bAngelmanResult=bAngelmanResult)
        if not row:
            return None
        pid, stored_hash_bytes = row
        if crypto.verify_password_argon2(password, stored_hash_bytes):
            return pid
        return None
    except Exception:
        logger.exception("authenticate_and_get_id échec")
        return None

def _norm(s: str) -> str:
    """Normalise pour comparaison: trim, NFKC, lower()."""
    if s is None:
        return ""
    return unicodedata.normalize("NFKC", s).strip().lower()

def verifySecretAnswer(*, email: str | None = None, person_id: int | None = None, answer: str, bAngelmanResult=False) -> bool:
    """
    Vérifie la réponse secrète.
    - On n'expose JAMAIS la réponse.
    - Retourne True si ça correspond, False sinon.
    - Si l'utilisateur n'existe pas: retourne False (évite l'énumération de comptes).
    """
    if not answer or not isinstance(answer, str):
        # on laisse l'API gérer les messages, ici on renvoie simplement False
        return False

    # Construction SQL selon l'identifiant fourni
    params = {}
    if email:
        sha = crypto.email_sha256(email)
        where = "email_sha = :sha"
        params["sha"] = sha
    elif person_id is not None:
        where = "person_id = :person_id"
        params["person_id"] = int(person_id)
    else:
        # pas d'identifiant -> échec silencieux
        return False

    rowset = _run_query(
        text(f"SELECT secret_answer FROM T_People_Identity WHERE {where} LIMIT 1"),
        params=params,
        return_result=True,
        bAngelmanResult=bAngelmanResult
    )
    if not rowset or not rowset[0]:
        # utilisateur introuvable -> renvoyer False (ne rien divulguer)
        return False

    enc_ans = rowset[0][0]  # VARBINARY chiffré
    try:
        stored = crypto.decrypt_bytes_to_str_strict(enc_ans)  # str
    except Exception:
        # si déchiffrement impossible -> on considère faux
        return False

    return _norm(answer) == _norm(stored)


def update_person_connection_status(
    person_id: int,
    is_connected: bool,
) -> bool:
    
    params = {}

    params["id"] = int(person_id)
    params["is_connected"] = 1 if is_connected else 0
    
    try:  
        _run_query(
            text("""
                UPDATE T_People_Public
                SET is_connected = :is_connected
                WHERE id = :id
                  AND status = 'active'
            """),
            params=params,
            return_result=False,
            bAngelmanResult=False
        )
        return True
    except Exception:
        return False
    
    

