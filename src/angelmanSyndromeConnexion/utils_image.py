# angelmanSyndromeConnexion/utils_image.py
from __future__ import annotations

import io
import os
from configparser import ConfigParser
from datetime import date, datetime

import numpy as np
import pandas as pd
from PIL import Image, ImageOps
from PIL import UnidentifiedImageError
from sqlalchemy import text

from tools.logger import setup_logger
from tools.utilsTools import _run_query

logger = setup_logger(debug=False)

# -----------------------------
#  Images (recompression / MIME)
# -----------------------------
MAX_SIDE = 1080
TARGET_FORMAT = "WEBP"  # ou "JPEG"
QUALITY = 80
RESAMPLE = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.BICUBIC)

def recompress_image(blob, target_format: str = TARGET_FORMAT, quality: int = QUALITY):
    if not blob:
        return None, None

    im = Image.open(io.BytesIO(blob))
    im = ImageOps.exif_transpose(im)

    w, h = im.size
    scale = min(1.0, MAX_SIDE / max(w, h))
    if scale < 1.0:
        im = im.resize((int(w * scale), int(h * scale)), RESAMPLE)

    tf = target_format.upper()
    if tf == "WEBP":
        im = im.convert("RGBA" if im.mode in ("RGBA", "LA") else "RGB")
    elif tf == "JPEG":
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
        im.save(out, format="WEBP", quality=quality, method=6)
        mime = "image/webp"
    else:
        im.save(out, format="JPEG", quality=quality, optimize=True, progressive=True)
        mime = "image/jpeg"

    return out.getvalue(), mime

CANONICAL_MIME = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
ALIASES = {"image/jpg": "image/jpeg", "image/pjpeg": "image/jpeg"}

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

# -----------------------------
#  Dates / coercion
# -----------------------------
def coerce_to_date(d) -> date:
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, pd.Timestamp):
        return d.date()
    if isinstance(d, np.datetime64):
        return pd.to_datetime(d).date()
    if isinstance(d, str):
        s = d.strip()
        try:
            return date.fromisoformat(s.split("T")[0].split(" ")[0])
        except Exception:
            for fmt in ("%d/%m/%Y", "%m/%d/%Y"):
                try:
                    return datetime.strptime(s, fmt).date()
                except Exception:
                    pass
            from . import error
            raise error.BadDateFormatError(f"Format de date invalide: {d!r}")
    raise TypeError(f"Type de date non supporté: {type(d)}")

# (facultatif) utilitaire de migration de photos – exemple d’usage:
def recompress_all_people_photos():
    SQL_SELECT = text("SELECT id, photo, photo_mime FROM T_ASPeople WHERE photo IS NOT NULL")
    rows = _run_query(SQL_SELECT, return_result=True)
    for pid, blob, mime in rows:
        try:
            new_blob, new_mime = recompress_image(blob)
            if new_blob and len(new_blob) < len(blob):
                SQL_UPDATE = text("UPDATE T_ASPeople SET photo = :p, photo_mime = :m WHERE id = :id")
                _run_query(SQL_UPDATE, params={"p": new_blob, "m": new_mime, "id": pid})
        except UnidentifiedImageError:
            logger.warning("Blob non image ignoré (id=%s)", pid)
        except Exception as e:
            logger.warning("[WARN] id=%s: %s", pid, e, exc_info=True)
