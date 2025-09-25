import hashlib
from cryptography.fernet import Fernet
import sys, os
from configparser import ConfigParser
import pandas as pd
import numpy as np
from datetime import datetime,date
from tkinter import Image
from sqlalchemy import text
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
def norm_email(e: str) -> str:
    return e.strip().lower()

def email_sha256(e: str) -> bytes:
    return hashlib.sha256(norm_email(e).encode("utf-8")).digest()

def encrypt_str(s: str) -> bytes:
    return cipher.encrypt(s.encode("utf-8"))  # -> bytes pour VARBINARY

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

# Déchiffrement bytes -> str (UTF-8)
def decrypt_bytes_to_str(b: bytes | memoryview | None) -> str | None:
    if b is None:
        return None
    if isinstance(b, memoryview):
        b = b.tobytes()
    return cipher.decrypt(b).decode("utf-8")

def dropTable(table_name):
    safe_table = table_name.replace("`", "``")
    sql = text(f"DROP TABLE IF EXISTS `{safe_table}`")
    _run_query(sql)