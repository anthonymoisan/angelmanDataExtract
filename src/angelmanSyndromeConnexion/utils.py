from __future__ import annotations
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash
import hashlib
from typing import Union
from cryptography.fernet import Fernet
import sys, os
from configparser import ConfigParser
import pandas as pd
import numpy as np
from datetime import datetime,date
from tkinter import Image
from sqlalchemy import text
from PIL import Image, ImageOps
from PIL import UnidentifiedImageError

from .  import error
import io
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger import setup_logger
from utilsTools import _run_query



logger = setup_logger(debug=False)

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

wkdir = os.path.dirname(__file__)
config = ConfigParser()
filePath = f"{wkdir}/../../angelman_viz_keys/Config4.ini"
config.read(filePath)
key = config['CleChiffrement']['KEY']

cipher = Fernet(key)

# --- helpers ---

# utils.py — extrait à ajouter


MAX_SIDE = 1080
TARGET_FORMAT = "WEBP"  # ou "JPEG"
QUALITY = 80

# Compat Pillow
RESAMPLE = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.BICUBIC)

def recompress_image(blob, target_format=TARGET_FORMAT, quality=QUALITY):
    if not blob:
        return None, None

    im = Image.open(io.BytesIO(blob))
    im = ImageOps.exif_transpose(im)

    # Redimension proportionnel si nécessaire
    w, h = im.size
    scale = min(1.0, MAX_SIDE / max(w, h))
    if scale < 1.0:
        im = im.resize((int(w * scale), int(h * scale)), RESAMPLE)

    # Gestion alpha selon format cible
    tf = target_format.upper()
    if tf == "WEBP":
        # WebP supporte l'alpha
        if im.mode in ("RGBA", "LA"):
            im = im.convert("RGBA")
        else:
            im = im.convert("RGB")
    elif tf == "JPEG":
        # JPEG ne gère pas l'alpha -> aplatir sur blanc
        if im.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
    else:
        raise ValueError("Format non géré")

    out = io.BytesIO()
    if tf == "WEBP":
        im.save(out, format="WEBP", quality=quality, method=6)  # method=6 = plus efficace
        mime = "image/webp"
    elif tf == "JPEG":
        im.save(out, format="JPEG", quality=quality, optimize=True, progressive=True)
        mime = "image/jpeg"

    return out.getvalue(), mime

SQL_SELECT = text("""
    SELECT id, photo, photo_mime
    FROM T_ASPeople
    WHERE photo IS NOT NULL
""")
rows = _run_query(SQL_SELECT, return_result=True)

for pid, blob, mime in rows:
    try:
        new_blob, new_mime = recompress_image(blob)
        if new_blob and len(new_blob) < len(blob):
            SQL_UPDATE = text("""
                UPDATE T_ASPeople
                SET photo = :p, photo_mime = :m
                WHERE id = :id
            """)
            params = {"p": new_blob, "m": new_mime, "id": pid}
            _run_query(SQL_UPDATE, params=params)
    except UnidentifiedImageError:
        logger.warning("Blob non image ignoré (id=%s)", pid)
    except Exception as e:
        logger.warning("[WARN] id=%s: %s", pid, e, exc_info=True)


# Paramètres raisonnables (à ajuster selon tes contraintes perf/sécu)
# - time_cost (t) : nombre d’itérations
# - memory_cost (m) : en KiB (ex. 19456 KiB ≈ 19 Mo)
# - parallelism (p) : parallélisme
_ph = PasswordHasher(
    time_cost=2,       # t
    memory_cost=19456, # m (KiB)
    parallelism=1,     # p
)

def hash_password_argon2(password: str) -> tuple[bytes, dict]:
    """
    Retourne (password_hash_bytes, password_meta_dict)
    - password_hash_bytes : la chaîne PHC Argon2id encodée en UTF-8 (bytes)
      ex: b"$argon2id$v=19$m=19456,t=2,p=1$...$..."
    - password_meta_dict : paramètres utiles stockables en JSON
    """
    if not isinstance(password, str) or not password:
        raise ValueError("password doit être une chaîne non vide")

    phc = _ph.hash(password)  # str PHC
    meta = {
        "algo": "argon2id",
        "v": 19,        # version
        "t": _ph.time_cost,
        "m": _ph.memory_cost,
        "p": _ph.parallelism,
    }
    return phc.encode("utf-8"), meta


def verify_password_argon2(password: str, stored_hash_bytes: bytes) -> bool:
    """
    Vérifie un mot de passe contre un hash PHC (bytes).
    Retourne True/False.
    """
    if not isinstance(stored_hash_bytes, (bytes, bytearray)):
        raise ValueError("stored_hash_bytes doit être bytes")
    try:
        stored_phc = stored_hash_bytes.decode("utf-8")
        _ph.verify(stored_phc, password)
        return True
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False


def password_needs_rehash(stored_hash_bytes: bytes) -> bool:
    """
    Indique si le hash devrait être recalculé (paramètres devenus insuffisants).
    Pratique pour migrer progressivement vers des paramètres plus forts.
    """
    if not isinstance(stored_hash_bytes, (bytes, bytearray)):
        return True
    try:
        stored_phc = stored_hash_bytes.decode("utf-8")
        return _ph.check_needs_rehash(stored_phc)
    except InvalidHash:
        return True

def norm_email(e: str) -> str:
    return e.strip().lower()

def email_sha256(e: str) -> bytes:
    return hashlib.sha256(norm_email(e).encode("utf-8")).digest()

def encrypt_str(s: str) -> bytes:
    return cipher.encrypt(s.encode("utf-8"))  # -> bytes pour VARBINARY

def encrypt_number(n) -> bytes | None:
    if n is None:
        return None
    # on sérialise en str pour rester cohérent
    return cipher.encrypt(str(n).encode("utf-8"))

def decrypt_number(b: bytes | memoryview | None) -> float | None:
    if b is None:
        return None
    if isinstance(b, memoryview):
        b = b.tobytes()
    try:
        s = cipher.decrypt(b).decode("utf-8")
        return float(s)
    except Exception:
        return None


def encrypt_date_like(d) -> bytes:
    # accepte date / datetime / pandas.Timestamp / str
    from datetime import date, datetime
    import pandas as pd

    if isinstance(d, pd.Timestamp):
        d = d.date()
    elif isinstance(d, datetime):
        d = d.date()
    elif isinstance(d, str):
        # garde juste la partie date si "YYYY-MM-DDTHH:MM:SS"
        d = d.split('T')[0].split(' ')[0]
        return cipher.encrypt(d.encode('utf-8'))
    elif isinstance(d, date):
        pass
    else:
        raise TypeError("Type de date non supporté")

    return cipher.encrypt(d.isoformat().encode('utf-8'))


def createTable(sql_script):
    script_path = os.path.join(os.path.dirname(__file__), "SQL", sql_script)
    with open(script_path, "r", encoding="utf-8") as file:
        logger.info("--- Create Table.")
        _run_query(file.read())


def coerce_to_date(d) -> date:
    # déjà une date (pas datetime)
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    # datetime -> date
    if isinstance(d, datetime):
        return d.date()
    # pandas Timestamp
    if isinstance(d, pd.Timestamp):
        return d.date()
    # numpy datetime64
    if isinstance(d, np.datetime64):
        return pd.to_datetime(d).date()
    # string "YYYY-MM-DD" ou "YYYY-MM-DDTHH:MM:SS"
    if isinstance(d, str):
        s = d.strip()
        try:
            return date.fromisoformat(s.split("T")[0].split(" ")[0])
        except Exception:
            # tente quelques formats courants si besoin
            for fmt in ("%d/%m/%Y", "%m/%d/%Y"):
                try:
                    return datetime.strptime(s, fmt).date()
                except Exception:
                    pass
            raise error.BadDateFormatError(f"Format de date invalide: {d!r}")
    raise TypeError(f"Type de date non supporté: {type(d)}")

CANONICAL_MIME = {
    "JPEG": "image/jpeg",
    "PNG":  "image/png",
    "WEBP": "image/webp",
}

ALIASES = {
    "image/jpg": "image/jpeg",
    "image/pjpeg": "image/jpeg",
}

def detect_mime_from_bytes(b: bytes) -> str | None:
    try:
        with Image.open(io.BytesIO(b)) as im:
            fmt = (im.format or "").upper()
        return CANONICAL_MIME.get(fmt)
    except Exception:
        return None

def normalize_mime(mime: str | None) -> str | None:
    if mime is None:
        return None
    return ALIASES.get(mime, mime)

class DecryptError(Exception):
    pass

def decrypt_bytes_to_str_strict(b: Union[bytes, memoryview, str]) -> str:
    if b is None:
        raise DecryptError("Valeur None non déchiffrable")
    if isinstance(b, str):
        return b
    if isinstance(b, memoryview):
        b = b.tobytes()
    if not isinstance(b, (bytes, bytearray)) or len(b) == 0:
        raise DecryptError("Type/longueur invalide pour déchiffrement")
    try:
        return cipher.decrypt(bytes(b)).decode("utf-8")
    except Exception as e:
        raise DecryptError(f"Échec de déchiffrement: {e}") from e

def dropTable(table_name):
    safe_table = table_name.replace("`", "``")
    sql = text(f"DROP TABLE IF EXISTS `{safe_table}`")
    _run_query(sql)