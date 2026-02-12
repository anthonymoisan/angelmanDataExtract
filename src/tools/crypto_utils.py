# tools/crypto_utils.py
from __future__ import annotations
from typing import Dict, Literal, Any, Callable, Iterable, Tuple
import base64
import pandas as pd
import numpy as np
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

def decrypt_or_plain(v):
    if v is None:
        return None
    # v peut être bytes/memoryview/str selon la colonne/driver
    try:
        return decrypt_bytes_to_str_strict(v)
    except DecryptError:
        # fallback: si c'est déjà du texte
        if isinstance(v, (bytes, bytearray)):
            return v.decode("utf-8", errors="replace")
        if isinstance(v, memoryview):
            return v.tobytes().decode("utf-8", errors="replace")
        return str(v)


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

OutputMode = Literal["bytes", "b64"]
ColType    = Literal["str", "number", "date"]

def _is_datetime_dtype(ser: pd.Series) -> bool:
    return pd.api.types.is_datetime64_any_dtype(ser) or pd.api.types.is_period_dtype(ser)

def _is_numeric_dtype(ser: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(ser) and not pd.api.types.is_bool_dtype(ser)

def _looks_like_dates(ser: pd.Series, ratio: float = 0.8) -> bool:
    """Heuristique: assez de valeurs parsables en dates ? (2 essais, dayfirst False/True)"""
    if ser.empty:
        return False
    s = ser.dropna().astype(str).str.strip()
    if s.empty:
        return False
    parsed1 = pd.to_datetime(s, errors="coerce", utc=False, dayfirst=False)
    parsed2 = pd.to_datetime(s, errors="coerce", utc=False, dayfirst=True)
    ok_ratio = max(parsed1.notna().mean(), parsed2.notna().mean())
    return ok_ratio >= ratio

def _looks_like_numbers(ser: pd.Series, ratio: float = 0.9) -> bool:
    """Heuristique: la majorité est convertible en nombres ?"""
    if ser.empty:
        return False
    if pd.api.types.is_bool_dtype(ser):
        return False  # important: éviter True/False -> float
    s = ser.dropna().astype(str).str.strip()
    if s.empty:
        return False
    parsed = pd.to_numeric(s, errors="coerce")
    return parsed.notna().mean() >= ratio

def infer_crypto_spec(
    df: pd.DataFrame,
    *,
    include: Iterable[str] | None = None,
    exclude: Iterable[str] | None = None,
    date_ratio: float = 0.8,
    num_ratio: float = 0.9,
) -> Dict[str, ColType]:
    """
    Retourne un spec {col: 'str'|'number'|'date'} inféré depuis df.
    - include: liste blanche (si fournie, on limite à ces colonnes)
    - exclude: liste noire (prioritaire)
    - date_ratio: seuil de détection pour les dates à partir de strings
    - num_ratio: seuil de détection pour les nombres à partir de strings
    """
    include_set = set(include) if include else None
    exclude_set = set(exclude) if exclude else set()

    spec: Dict[str, ColType] = {}
    for col in df.columns:
        if include_set is not None and col not in include_set:
            continue
        if col in exclude_set:
            continue

        ser = df[col]

        # 1) dtypes explicites
        if _is_datetime_dtype(ser):
            spec[col] = "date"
            continue
        if _is_numeric_dtype(ser):
            spec[col] = "number"
            continue
        if pd.api.types.is_bool_dtype(ser):
            spec[col] = "str"      # ⚠️ éviter decrypt_number(True) -> crash
            continue
        if pd.api.types.is_categorical_dtype(ser):
            spec[col] = "str"
            continue
        if pd.api.types.is_string_dtype(ser) or ser.dtype == "object":
            # 2) heuristiques sur object/str
            if _looks_like_dates(ser, ratio=date_ratio):
                spec[col] = "date"
            elif _looks_like_numbers(ser, ratio=num_ratio):
                spec[col] = "number"
            else:
                spec[col] = "str"
            continue

        # 3) fallback
        spec[col] = "str"

    return spec

def encrypt_dataframe_auto(
    df: pd.DataFrame,
    *,
    output: OutputMode = "b64",
    include: Iterable[str] | None = None,
    exclude: Iterable[str] | None = None,
    date_ratio: float = 0.8,
    num_ratio: float = 0.9,
    inplace: bool = False,
    return_spec: bool = False,
) -> pd.DataFrame | Tuple[pd.DataFrame, Dict[str, ColType]]:
    """
    Comme encrypt_dataframe, mais sans spec: il est inféré automatiquement.
    - return_spec=True pour récupérer le spec utilisé (utile pour déchiffrer plus tard)
    """
    spec = infer_crypto_spec(df, include=include, exclude=exclude, date_ratio=date_ratio, num_ratio=num_ratio)
    out = encrypt_dataframe(df, spec, output=output, inplace=inplace)
    return (out, spec) if return_spec else out


def decrypt_dataframe_auto(
    df: pd.DataFrame,
    *,
    input_mode: OutputMode = "b64",
    include: Iterable[str] | None = None,
    exclude: Iterable[str] | None = None,
    date_ratio: float = 0.8,
    num_ratio: float = 0.9,
    inplace: bool = False,
    # Tu peux fournir un spec si tu l'as sauvegardé; sinon on ré-infère
    spec_override: Dict[str, ColType] | None = None,
    # Conversion finale automatique: number->float, date->str ISO, str->str
    auto_to_python: bool = True,
) -> pd.DataFrame:
    """
    Déchiffre sans spec explicite:
      - si spec_override fourni, on l'utilise;
      - sinon on infère à nouveau (mêmes heuristiques que chiffrement).
    """
    if spec_override is not None:
        spec = spec_override
    else:
        spec = infer_crypto_spec(df, include=include, exclude=exclude, date_ratio=date_ratio, num_ratio=num_ratio)

    to_python = None
    if auto_to_python:
        to_python = {c: ("number" if t == "number" else ("date" if t == "date" else "str"))
                     for c, t in spec.items()}
    return decrypt_dataframe(
        df,
        spec,
        input_mode=input_mode,
        to_python=to_python,
        inplace=inplace,
    )

# --- petits helpers Base64 ---
def _b64e(b: bytes | None) -> str | None:
    if b is None:
        return None
    return base64.b64encode(b).decode("utf-8")

def _b64d(s: str | bytes | None) -> bytes | None:
    if s is None:
        return None
    if isinstance(s, bytes):
        return s
    s = s.strip()
    if not s:
        return None
    return base64.b64decode(s)


def _isnull(x: Any) -> bool:
    # pandas considère "" comme non-nul -> on garde cette sémantique
    return x is None or (isinstance(x, float) and np.isnan(x))


# -----------------------
#  API: chiffrement
# -----------------------
def encrypt_dataframe(
    df: pd.DataFrame,
    spec: Dict[str, ColType],
    *,
    output: OutputMode = "b64",
    inplace: bool = False,
) -> pd.DataFrame:
    """
    Chiffre les colonnes du DataFrame selon 'spec' = {col: 'str'|'number'|'date'}.
    - output='b64' (par défaut) renvoie des chaînes Base64 (idéal CSV/JSON/DB texte)
    - output='bytes' renvoie des bytes (colonnes dtype 'object')
    - inplace=False (par défaut) n'altère pas df

    Ex:
      spec = {
        "firstname": "str",
        "amount": "number",
        "birthdate": "date",
      }
    """
    work = df if inplace else df.copy()

    # Map de fonctions de chiffrement -> bytes
    enc_by_type: Dict[ColType, Callable[[Any], bytes | None]] = {
        "str": lambda v: None if _isnull(v) else encrypt_str(str(v)),
        "number": lambda v: None if _isnull(v) else encrypt_number(v),
        "date": lambda v: None if _isnull(v) else encrypt_date_like(v),
    }

    for col, ctype in spec.items():
        if col not in work.columns:
            raise KeyError(f"Colonne absente du DataFrame: {col!r}")
        if ctype not in enc_by_type:
            raise ValueError(f"Type inconnu pour {col!r}: {ctype!r}")

        # Serie -> bytes (Fernet)
        ser_bytes = work[col].map(enc_by_type[ctype])

        # Sortie bytes ou Base64
        if output == "bytes":
            work[col] = ser_bytes
        elif output == "b64":
            work[col] = ser_bytes.map(_b64e)
        else:
            raise ValueError("output doit être 'bytes' ou 'b64'")

    return work


# -----------------------
#  API: déchiffrement
# -----------------------
def decrypt_dataframe(
    df: pd.DataFrame,
    spec: Dict[str, ColType],
    *,
    input_mode: OutputMode = "b64",
    to_python: Dict[str, ColType] | None = None,
    inplace: bool = False,
) -> pd.DataFrame:
    """
    Déchiffre les colonnes selon 'spec' = {col: 'str'|'number'|'date'}.

    - input_mode='b64' (par défaut) si les cellules contiennent du Base64.
      Sinon 'bytes' si elles contiennent directement les bytes Fernet.
    - to_python peut préciser la conversion finale par colonne:
        * 'str' (par défaut pour les 3 types)
        * 'number' -> float (ou None)
        * 'date'   -> string ISO 'YYYY-MM-DD'
      NB: si tu veux de vrais objets date/datetime, convertis ensuite côté appelant.

    Exemple:
      decrypt_dataframe(df, {"firstname": "str", "amount":"number", "birthdate":"date"},
                        input_mode="b64", to_python={"amount": "number", "birthdate": "date"})
    """
    work = df if inplace else df.copy()

    # Décode entrée -> bytes Fernet
    if input_mode == "b64":
        decode_in = lambda x: None if _isnull(x) else _b64d(x)
    elif input_mode == "bytes":
        decode_in = lambda x: None if _isnull(x) else (x if isinstance(x, (bytes, bytearray)) else bytes(x))
    else:
        raise ValueError("input_mode doit être 'b64' ou 'bytes'")

    # Déchiffreurs -> vers str/float/str(date ISO)
    def _dec_str(b: bytes | None) -> str | None:
        if b is None:
            return None
        return decrypt_bytes_to_str_strict(b)

    def _dec_num(b: bytes | None) -> float | None:
        if b is None:
            return None
        return decrypt_number(b)

    def _dec_date(b: bytes | None) -> str | None:
        if b is None:
            return None
        # decrypt_bytes_to_str_strict renvoie la chaîne claire (ex 'YYYY-MM-DD')
        return decrypt_bytes_to_str_strict(b)

    dec_by_type: Dict[ColType, Callable[[bytes | None], Any]] = {
        "str": _dec_str,
        "number": _dec_num,
        "date": _dec_date,
    }

    # Que faire comme type Python final ?
    to_py = to_python or {}

    for col, ctype in spec.items():
        if col not in work.columns:
            raise KeyError(f"Colonne absente du DataFrame: {col!r}")
        if ctype not in dec_by_type:
            raise ValueError(f"Type inconnu pour {col!r}: {ctype!r}")

        # -> bytes
        ser_bytes = work[col].map(decode_in)

        # -> clair Python
        ser_clear = ser_bytes.map(dec_by_type[ctype])

        # Conversion finale optionnelle par colonne
        target = to_py.get(col, "str")
        if target == "str":
            work[col] = ser_clear.astype("object")
        elif target == "number":
            # Convertit None -> NaN pour avoir une colonne numérique
            work[col] = pd.to_numeric(ser_clear, errors="coerce")
        elif target == "date":
            # Garde str ISO; si tu veux des datetime64, décommente:
            # work[col] = pd.to_datetime(ser_clear, errors="coerce").dt.date
            work[col] = ser_clear.astype("object")
        else:
            raise ValueError(f"to_python invalide pour {col!r}: {target!r}")

    return work
