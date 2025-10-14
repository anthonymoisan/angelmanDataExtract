# tools/crypto_utils.py
from __future__ import annotations

import hashlib
import os
from configparser import ConfigParser
from datetime import date, datetime
from typing import Union

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash
from cryptography.fernet import Fernet

# --- Chargement clé Fernet depuis Config4.ini ---
_wkdir = os.path.dirname(__file__)
_cfg = ConfigParser()
_cfg.read(os.path.abspath(os.path.join(_wkdir, "..", "..", "angelman_viz_keys", "Config4.ini")))
_key = _cfg["CleChiffrement"]["KEY"]
_cipher = Fernet(_key)

# --- Argon2 (paramètres recommandés) ---
_ph = PasswordHasher(
    time_cost=2,       # itérations
    memory_cost=19456, # ~19 MiB
    parallelism=1,
)

# -----------------------------
#  Hashing & vérification (Argon2)
# -----------------------------
def hash_password_argon2(password: str) -> tuple[bytes, dict]:
    """
    Retourne (password_hash_bytes, meta_dict).
    - hash : chaîne PHC encodée UTF-8 (bytes)
    - meta : paramètres utiles (JSON-sérialisable)
    """
    if not isinstance(password, str) or not password:
        raise ValueError("password doit être une chaîne non vide")
    phc = _ph.hash(password)
    meta = {"algo": "argon2id", "v": 19, "t": _ph.time_cost, "m": _ph.memory_cost, "p": _ph.parallelism}
    return phc.encode("utf-8"), meta

def verify_password_argon2(password: str, stored_hash_bytes: bytes) -> bool:
    if not isinstance(stored_hash_bytes, (bytes, bytearray)):
        raise ValueError("stored_hash_bytes doit être bytes")
    try:
        _ph.verify(stored_hash_bytes.decode("utf-8"), password)
        return True
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False

def password_needs_rehash(stored_hash_bytes: bytes) -> bool:
    if not isinstance(stored_hash_bytes, (bytes, bytearray)):
        return True
    try:
        return _ph.check_needs_rehash(stored_hash_bytes.decode("utf-8"))
    except InvalidHash:
        return True

# -----------------------------
#  Outils e-mail & SHA-256
# -----------------------------
def _norm_email(e: str) -> str:
    return (e or "").strip().lower()

def email_sha256(e: str) -> bytes:
    return hashlib.sha256(_norm_email(e).encode("utf-8")).digest()

# -----------------------------
#  Chiffrement / Déchiffrement (Fernet)
# -----------------------------
def encrypt_str(s: str) -> bytes:
    return _cipher.encrypt(s.encode("utf-8"))

def encrypt_number(n) -> bytes | None:
    if n is None:
        return None
    return _cipher.encrypt(str(n).encode("utf-8"))

def decrypt_number(b: bytes | memoryview | None) -> float | None:
    if b is None:
        return None
    if isinstance(b, memoryview):
        b = b.tobytes()
    try:
        return float(_cipher.decrypt(b).decode("utf-8"))
    except Exception:
        return None

def encrypt_date_like(d) -> bytes:
    """
    Accepte date/datetime/pandas.Timestamp/str('YYYY-MM-DD' ou ISO datetime)
    et renvoie un blob chiffré (bytes).
    """
    # import paresseux pour ne pas rendre pandas obligatoire si non utilisé
    try:
        import pandas as pd  # type: ignore
    except Exception:  # pandas absent : on continue sans
        pd = None  # type: ignore

    if pd is not None and isinstance(d, pd.Timestamp):
        d = d.date()
    elif isinstance(d, datetime):
        d = d.date()
    elif isinstance(d, str):
        d = d.split("T")[0].split(" ")[0]
        return _cipher.encrypt(d.encode("utf-8"))
    elif not isinstance(d, date):
        raise TypeError("Type de date non supporté")

    return _cipher.encrypt(d.isoformat().encode("utf-8"))

class DecryptError(Exception):
    pass

def decrypt_bytes_to_str_strict(b: Union[bytes, memoryview, str]) -> str:
    if b is None:
        raise DecryptError("Valeur None non déchiffrable")
    if isinstance(b, str):
        return b
    if isinstance(b, memoryview):
        b = b.tobytes()
    if not isinstance(b, (bytes, bytearray)) or not b:
        raise DecryptError("Type/longueur invalide pour déchiffrement")
    try:
        return _cipher.decrypt(bytes(b)).decode("utf-8")
    except Exception as e:
        raise DecryptError(f"Échec de déchiffrement: {e}") from e
